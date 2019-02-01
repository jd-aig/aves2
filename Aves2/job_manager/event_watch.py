import os
import logging

from k8s_client.k8s_client import K8SClient

logger = logging.getLogger('aves2')


def event_process(event):
    pass


def start_event_watch():
    k8s_client = K8SClient()

    while True:
        try:
            res, err_msg = k8s_client.watch_event(event_process)
            if not res:
                logger.error('Watch event start failed: %s' % err_msg)
        except Exception as e:
            logger.error('Exception raised when start event watch', exc_info=True)

