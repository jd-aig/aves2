import sys
import signal
import pickle
import pika
import time
import logging
from inspect import isfunction
from operator import itemgetter

from django.conf import settings
from django.utils import timezone
from django.core.management.base import BaseCommand, CommandError

from job_manager import tasks
from job_manager.models import JobStatus, AvesJob, WorkerStatus, AvesWorker
from docker_client.client import doc_client

logger = logging.getLogger('cmd')


def quit_handler(signum, frame):
    sys.exit(0)


class Command(BaseCommand):
    help = 'watch service event'

    def handle(self, *args, **options):
        signal.signal(signal.SIGABRT, quit_handler)
        signal.signal(signal.SIGINT, quit_handler)
        signal.signal(signal.SIGTERM, quit_handler)


        label = f'app={settings.AVES_JOB_LABEL}'
        while True:
            for job in AvesJob.objects.filter(status__in=[JobStatus.STARTING]):
                if int((timezone.now() - job.update_time).total_seconds()) / 60 > 5:
                    for worker in job.all_workers:
                        status, err = doc_client.get_container_status(worker.worker_name)
                        if status:
                            if status[0].get('Status', {}).get('State', '') == 'rejected':
                                err_msg = status[0].get('Status', {}).get('Err', '')
                                job.all_workers.update(k8s_status=WorkerStatus.FAILURE)
                                logger.info(f'{job} failed: {worker} msg: {err}')
                                job.update_status(JobStatus.FAILURE, msg=err_msg)
                                job.clean_work(force=True)
                                break
                        elif status == []:
                            logger.info(f'{job} failed: workers are disappeared')
                            job.all_workers.update(k8s_status=WorkerStatus.FAILURE)
                            job.update_status(JobStatus.FAILURE, msg='workers are disappeared')
                            job.clean_work(force=True)
                            break
