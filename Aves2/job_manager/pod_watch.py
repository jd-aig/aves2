import os
import logging
import celery
from celery_once import QueueOnce

from operator import itemgetter
from datetime import datetime, timezone
from dateutil.tz import tzutc

from k8s_client.k8s_client import K8SClient
from job_manager.tasks import k8s_pod_event_process

logger = logging.getLogger('aves2')

def get_pod_event_key(event):
    pod_name = event['object'].metadata.name
    phase = event['object'].status.phase
    status = event['object'].status.to_dict()
    conds = status['conditions']
    # get the last condition
    if conds and len(conds) > 0:
        # fix issue: sometime last_transition_time could be None
        for cond in conds:
            if cond['last_transition_time'] == None:
                cond['last_transition_time']  = datetime(1, 1, 1, 0, 0, tzinfo=tzutc())
        #logger.debug(conds)
        conds.sort(key=itemgetter('last_transition_time'))
        #logger.debug(conds)
        last_cond_time = conds[-1]['last_transition_time']
        conds_size = len(conds)
    else:
        last_cond_time= ""
        conds_size = 0
    key = "%s;%s;%d;%s" % (pod_name, phase, conds_size, last_cond_time)
    return key


def pod_event_process(event):
    event_type = event['type']
    pod_name = event['object'].metadata.name
    namespace = event['object'].metadata.namespace
    status_phase = event['object'].status.phase

    key = get_pod_event_key(event)
    event_data = {
        "pod_name": pod_name,
        "namespace": namespace,
        "event_type": event_type,
        "status_phase": status_phase
    }

    if 'demo' in pod_name and namespace == 'logcollector':
        k8s_pod_event_process.apply_async(args=(key, event_data))


def start_pod_event_watch():
    k8s_client = K8SClient()

    while True:
        try:
            res, err_msg = k8s_client.watch_pod(pod_event_process)
            if not res:
                logger.error('Watch pod event start failed: %s' % err_msg)
        except Exception as e:
            logger.error('Exception raised when start pod event watch', exc_info=True)