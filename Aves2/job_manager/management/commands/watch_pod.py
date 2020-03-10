import sys
import signal
import pickle
import pika
import time
import logging
from inspect import isfunction
from operator import itemgetter

from kubernetes import client, config, watch
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from job_manager import tasks


def quit_handler(signum, frame):
    sys.exit(0)


class Command(BaseCommand):
    help = 'Watch k8s pod event'

    def handle(self, *args, **options):
        signal.signal(signal.SIGABRT, quit_handler)
        signal.signal(signal.SIGINT, quit_handler)
        signal.signal(signal.SIGTERM, quit_handler)

        api = client.CoreV1Api()
        watcher = watch.Watch()
        label = f'app={settings.AVES_JOB_LABEL}'
        while True:
            for event in watcher.stream(
                            api.list_pod_for_all_namespaces,
                            label_selector=label,
                            pretty=True, watch=True):
                event_type = event.get('type')
                pod = event['object']
                pod_name = pod.metadata.name
                phase = pod.status.phase

                self.stdout.write(f"receive pod event type:{event_type} pod_name:{pod_name} phase:{phase}")
                if event_type != 'MODIFIED':
                    continue
                try:
                    tasks.process_k8s_pod_event.apply_async(
                            (event,),
                            serializer='pickle')
                except Exception as e:
                    self.stdout.write(str(e))
