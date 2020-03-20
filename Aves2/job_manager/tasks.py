from __future__ import absolute_import, unicode_literals

import os
import time
import datetime
import json
import pika
import pickle
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

from job_manager.models import JobStatus, WorkerStatus, AvesJob, K8SWorker
from kubernetes_client import K8SPodPhase
from common_utils.rabbitmq import get_connection


logger = logging.getLogger('aves2')


# Demo task
@celery.task(base=QueueOnce, once={'graceful': True, 'keys': ['x']})
def periodic_add(x, y):
    time.sleep(30)
    return x + y


@shared_task(name='start_avesjob', bind=True)
def start_avesjob(self, job_id):
    avesjob = AvesJob.objects.get(id=job_id)
    if not avesjob.ready_to_run:
        return

    avesjob.update_status('STARTING', msg='')
    rt, err_msg = avesjob.start()
    if not rt:
        avesjob.update_status('FAILURE', msg=err_msg)


@shared_task(name='cancel_avesjob', bind=True)
def cancel_avesjob(self, job_id, force=False):
    """ 取消Aves训练任务
    """
    avesjob = AvesJob.objects.filter(id=job_id)
    namespace = avesjob.namespace
    msg = ''

    rt, err_msg = avesjob.cancel()
    avesjob.update_status('CANCELED')


@shared_task(name='process_k8s_pod_event', bind=True)
def process_k8s_pod_event(self, event):
    event_type = event.get('type')
    pod = event['object']
    pod_name = pod.metadata.name
    phase = pod.status.phase
    worker_id = pod.metadata.labels.get('workerId')
    logger.info(f"receive pod event type:{event_type} pod_name:{pod_name} phase:{phase}")

    worker = K8SWorker.objects.get(id=worker_id)
    if phase == K8SPodPhase.SUCCEEDED \
            and worker.k8s_status in [WorkerStatus.STARTING, WorkerStatus.RUNNING]:
        worker.update_status(WorkerStatus.FINISHED)
        job = worker.avesjob
        if job.status in [JobStatus.STARTING, JobStatus.RUNNING] and \
            job.k8s_worker.filter(k8s_status__in=[
                                    WorkerStatus.STARTING,
                                    WorkerStatus.RUNNING]).count() == 0:
            job.update_status(JobStatus.FINISHED, msg='Job finished')
    elif phase == K8SPodPhase.FAILED \
            and worker.k8s_status in [WorkerStatus.STARTING, WorkerStatus.RUNNING]:
        worker.update_status(WorkerStatus.FAILURE)
        job = worker.avesjob
        if job.status in [JobStatus.STARTING, JobStatus.RUNNING] and \
            job.k8s_worker.filter(k8s_status__in=[
                                    WorkerStatus.STARTING,
                                    WorkerStatus.RUNNING]).count() == 0:
            msg = f'{job.msg}; {pod_name} failed'.strip('; ')
            job.update_status(JobStatus.FAILURE, msg=msg)
    elif phase == K8SPodPhase.PENDING:
        container_statuses = pod.status.container_statuses
        if container_statuses and container_statuses[0].state.waiting:
            waiting_reason = container_statuses[0].state.waiting.reason
            if waiting_reason in ['ImagePullBackOff', 'ErrImagePull'] \
                    and worker.k8s_status in [WorkerStatus.STARTING, WorkerStatus.RUNNING]:
                worker.update_status(WorkerStatus.FAILURE, msg=waiting_reason)
                job = worker.avesjob
                msg = f'{job.msg}; {pod_name} {waiting_reason}'.strip('; ')
                job.update_status(JobStatus.FAILURE, msg=msg)
                job.clean_work(force=True)


@shared_task(name='report-avesjob-status', bind=True)
def report_avesjob_status(self, job_id, status, msg):
    report_data = {
        'jobId': job_id,
        'status': status,
        'msg': msg}
    body = json.dumps(report_data)

    connection = None
    try:
        connection = get_connection(settings.RABBITMQ_HOST, settings.RABBITMQ_USER, settings.RABBITMQ_PASS)
        channel = connection.channel()
        channel.exchange_declare(exchange=settings.STATUS_REPORT_EXCHANGE,
                                 exchange_type=settings.STATUS_REPORT_EXCHANGE_TYPE,
                                 durable=True)
        channel.basic_publish(exchange=settings.STATUS_REPORT_EXCHANGE,
                              routing_key=settings.STATUS_REPORT_ROUTING_KEY,
                              body=body,
                              properties=pika.BasicProperties(delivery_mode=2))
        logger.info(f'Send job status report {body}')
    except Exception as e:
        logger.error(f'Fail to send job status report: {body}', exc_info=True)
    finally:
        if connection:
            connection.close()
