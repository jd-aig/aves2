import os
import logging

from k8s_client.k8s_client import K8SClient
from job_manager.models import K8SWorker
from job_manager.tasks import k8s_event_process

logger = logging.getLogger('aves2')


def validate_event(event):
    kind = event.involved_object.kind
    if kind not in ["Pod", "Job", "ReplicationController"]:
        logger.info('involved object kind: %s not supported, ingore event' % kind)
        return False

    # 判断是不是旧的event
    # now = datetime.now(timezone.utc)
    # delta = now - event.last_timestamp
    # logger.info('event_time: %s, localtime: %s, delta: %s' % (event.last_timestamp, now, delta.total_seconds()))
    # if delta.total_seconds() > 5:
    #     logger.info('old event, ingore event')
    #     return False

    obj_name = event.involved_object.name
    arr = obj_name.split('-')
    if len(arr) < 4:
        logger.info('obj_name: %s is invalid, ingore event' % obj_name)
        return False
    merged_job_id = "{0}-{1}-{2}".format(arr[0], arr[1], arr[2])
    if not K8SWorker.objects.filter(worker_name__startswith=merged_job_id):
        logger.info('merged_job_id: %s not in db, ingore event' % merged_job_id)
        return False

    return True


def get_event_key(event):
    return "{0}-{1}-{2}".format(event.metadata.name, event.involved_object.name, event.last_timestamp)


def event_process(event):
    if not validate_event(event):
        return

    key = get_event_key(event)

    # 构建event_data
    event_data = {
        "event_type": event.type,
        "kind": event.involved_object.kind,
        "obj_name": event.involved_object.name,
        "reason": event.reason,
        "message": event.message
    }

    k8s_event_process.apply_async(args=(key, event_data))


def start_event_watch():
    k8s_client = K8SClient()

    while True:
        try:
            res, err_msg = k8s_client.watch_event(event_process)
            if not res:
                logger.error('Watch event start failed: %s' % err_msg)
        except Exception as e:
            logger.error('Exception raised when start event watch', exc_info=True)

