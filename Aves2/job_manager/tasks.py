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


# @task
@celery.task(base=QueueOnce, once={'graceful': True, 'keys': ['x']})
def periodic_add(x, y):
    time.sleep(30)
    return x + y

@shared_task(name='startup_avesjob', bind=True)
def startup_avesjob(self, avesjob_id):
    """ 启动AVES训练任务
    """
    avesjob = AvesJob.objects.get(id=avesjob_id)
    k8s_workers = avesjob.make_k8s_workers()
    
    # startup k8s worker
    logger.info('Startup k8s worker')
    for worker in k8s_workers:
        worker.start()


@shared_task(name='startup_k8sworker', bind=True)
def startup_k8sworker(self, k8s_worker_id):
    k8s_worker = K8SWorker.objects.get(id=k8s_worker_id)
    k8s_worker.start()


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


@shared_task(name='k8s_event_process', bind=True)
def k8s_pod_event_process(self, event_data):
    """ 处理k8s event
    """
    print(event_data)
    # TODO1: Get pod_phase from event

    # TODO2: Get k8s_podname_prefix from event data

    # TODO3: Get k8sworker obj

    # TODO4: Update k8sworker status & avesjob status

    pass 