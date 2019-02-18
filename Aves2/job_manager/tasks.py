from __future__ import absolute_import, unicode_literals
import os
import time
import datetime
import logging
import traceback
import requests
import subprocess
import hashlib
import logging

import celery
from django.conf import settings
from celery import task, shared_task, chain, group
from celery_once import QueueOnce

from job_manager.models import AvesJob, K8SWorker


logger = logging.getLogger('aves2')


# Demo task
@celery.task(base=QueueOnce, once={'graceful': True, 'keys': ['x']})
def periodic_add(x, y):
    time.sleep(30)
    return x + y

@shared_task(name='startup_avesjob', bind=True)
def startup_avesjob(self, avesjob_id):
    """ 启动AVES训练任务
    """
    avesjob = AvesJob.objects.get(id=avesjob_id)
    avesjob.status == 'STARTING'
    avesjob.save()

    # TODO: report avesjob status: starting

    # make k8s workers
    avesjob.make_k8s_workers()

    # startup k8s worker
    logger.info('Startup k8s worker')
    for worker in avesjob.k8s_worker.all():
        worker.make_k8s_conf()
        worker.start()


@shared_task(name='cancel_avesjob', bind=True)
def cancel_avesjob(self, avesjob_id):
    """ 取消Aves训练任务
    """
    avesjob = AvesJob.objects.get(id=avesjob_id)
    # Update avesjob status
    logger.info('Update avesjob status')

    # Update k8sworker and delete pod : 
    # 1. use django: select_for_update  2. transaction.atomic
    k8s_workers = avesjob.k8sworker_set.all()
    for worker in k8s_workers:
        worker.stop()

    pass


@shared_task(name='finish_avesjob', bind=True)
def finish_avesjob(self, avesjob_id):
    """ 正常结束avesjob
    """
    avesjob = AvesJob.objects.get(id=avesjob_id)

    k8s_workers = avesjob.k8sworker_set.select_for_update.all()

    pass


def _update_avesjob_status(k8s_worker, event_data):
    """ Update avesjob status
    """
    avesjob = k8s_worker.avesjob
    k8s_worker_set = avesjob.k8s_worker.all()

    k8s_worker_status = k8s_worker_set.values_list("k8s_status", flat=True)
    avesjob_status = avesjob.status
    k8sworker_status_set = set(k8s_worker_status)

    # if 'Pending' in k8sworker_status_set:
    #     avesjob.status = 'STARTING'
    if "Failed" in k8sworker_status_set:
        avesjob.status = 'FAILURE'
        # TODO: 回收avesjob
    else:
        if len(k8sworker_status_set) == 1 and 'Running' in k8sworker_status_set:
            avesjob.status = 'RUNNING'
        elif len(k8sworker_status_set) == 1 and 'Succeeded' in k8sworker_status_set:
            avesjob.status = 'SUCCEED'
            # TODO: report avesjob status
            # cancel_avesjob
    avesjob.save()

    if avesjob.status in ['FAILURE', 'SUCCEED']:
        # TODO: cancel
        pass

    if avesjob.status != avesjob_status:
        # TODO: report avesjob status
        _report_avesjob_status()


def _report_avesjob_status():
    pass


@celery.task(base=QueueOnce, once={'graceful': True, 'keys': ['key']})
def k8s_pod_event_process(self, key, event_data):
    """ 处理k8s pod event
    """
    pod_name = event_data['pod_name']
    merged_job_id = event_data['merged_job_id']
    status_phase = event_data['status_phase']

    k8s_worker_set = K8SWorker.objects.filter(worker_name__startswith=merged_job_id)
    k8s_worker = None
    for obj in k8s_worker_set:
        if obj.worker_name in pod_name:
            k8s_worker = obj
            break
    
    if not k8s_worker:
        return
    k8s_worker.k8s_status = status_phase
    k8s_worker.save()

    _update_avesjob_status(k8s_worker, event_data)


@celery.task(base=QueueOnce, once={'graceful': True, 'keys': ['key']})
def k8s_event_process(self, key, event_data):
    """ 处理k8s event
    """
    event_type = event_data['event_type']
    kind = event_data['kind']
    obj_name = event_data['obj_name']
    reason = event_data['reason']
    message = event_data['message']

    arr = obj_name.split('-')
    # merged_job_id = '{0}-{1}-{2}'.format(arr[0], arr[1], arr[2])

    avesjob_set = AvesJob.objects.filter(username=arr[0], namespace=arr[1], job_id=arr[2])
    if not avesjob_set:
        return
    avesjob = avesjob_set[0]
    status = avesjob.status
    err_msg = "%s:[%s - %s]" % (obj_name, reason, message)

    if event_type=='Warning' and (avesjob.status=="STARTING" or avesjob.status=='FAILURE'):
        if reason in ['FailedMount', 'BackOff', 'BackoffLimitExceeded', 'FailedCreate']:
            if reason == 'FailedMount':
                err_msg = "reason: [%s]" % reason
            avesjob.status = 'FAILURE'
            avesjob.save()
        elif reason in ['FailedScheduling']:
            avesjob.status = 'STARTING'
            avesjob.save()
    elif event_type=='Warning' and avesjob.status=="RUNNING":
        if reason in ['FailedMount', 'BackOff', 'BackoffLimitExceeded', 'FailedCreate']:
            if reason == 'BackOff' or reason == 'BackoffLimitExceeded':
                err_msg = "reason: [%s]" % reason
            avesjob.status = 'FAILURE'
            avesjob.save()

    if avesjob.status in ['FAILURE', 'SUCCEED']:
        # TODO: cancel avesjob
        pass

    if status != avesjob.status:
        _report_avesjob_status(status, err_msg=err_msg)

