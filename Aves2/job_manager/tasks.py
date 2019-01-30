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

from django.conf import settings
from celery import task, shared_task, chain, group


logger = logging.getLogger('aves2')


@task
def periodic_add(x, y):
    time.sleep(30)
    return x + y

@shared_task(name='startup_avesjob', bind=True)
def startup_avesjob(self, avesjob_id):
    """ 启动AVES训练任务
    """
    avesjob = AvesJob.objects.get(id=avesjob_id)
    k8s_workers = avesjob.make_k8s_workers()

@shared_task(name='startup_k8sworker', bind=True)
def startup_k8sworer(self, k8s_worker_id):
    k8s_worker = K8SWorker.objects.get(id=k8s_worker_id)
    k8s_worker.start()

@shared_task(name='cancel_avesjob', bind=True)
def cancel_avesjob(self, avesjob_id):
    """ 取消Aves训练任务
    """
    avesjob = AvesJob.objects.get(id=avesjob_id)
    pass
