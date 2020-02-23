import sys
import signal
import pickle
import pika
import time
import logging
from inspect import isfunction
from operator import itemgetter

from kubernetes import client, config, watch
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
        for event in watcher.stream(
                        api.list_pod_for_all_namespaces,
                        label_selector='app=aves-training',
                        pretty=True, watch=True):
            if event['type'] != 'MODIFIED':
                continue
            tasks.process_k8s_pod_event.apply_async((event,), serializer='pickle')
