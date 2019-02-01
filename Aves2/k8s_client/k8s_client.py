import logging
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from inspect import isfunction


logger = logging.getLogger('aves2')


class K8SClient(object):
    def __init__(self):
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()

    @property
    def corev1api(self):
        if hasattr(self, '_corev1api'):
            return self._corev1api
        else:
            _corev1api = client.CoreV1Api()
            setattr(self, '_corev1api', _corev1api)
            return self._corev1api

    def watch_pod(self, process_cb):
        """
        Block function to watch all the pod status change event in all namespace
        :param process_cb: callback function to process Event
        :return: True, None == Success, should not happen
                 False, err_msg == error happens
        """
        if not isfunction(process_cb):
            return False, "invalid process_cb"
        api = self.corev1api
        watcher = watch.Watch()
        for event in watcher.stream(api.list_pod_for_all_namespaces):
            logger.info("receive pod event type:%s pod_name:%s phase:%s" % \
                (event['type'], event['object'].metadata.name, event['object'].status.phase))
            logger.debug("event status: %s" % event['object'].status)

            process_cb(event)
        return True, None

    def watch_event(self, process_cb):
        """
        Block function to watch all k8s event in all namespace
        :param process_cb: callback function to process Event
        :return: True, None == Success, should not happen
                 False, err_msg == error happens
        """
        if not isfunction(process_cb):
            return False, "invalid process_cb"
        api = self.corev1api
        watcher = watch.Watch()
        for event in watcher.stream(api.list_event_for_all_namespaces):
            event = event['object']
            logger.info("receive event type:%s namespace:%s name:%s involved_object_kind:%s involved_object_name:%s reason:%s message:%s" % \
                (event.type, event.metadata.namespace, event.metadata.name, event.involved_object.kind, \
                event.involved_object.name, event.reason, event.message))
            process_cb(event)

        return True, None

    def create_single_container_job(self, job_menifest, namespace):
        """ Create a job with single container

        :param job_menifest:
        :param namespace:
        :return tuple: (bool, job, msg)
        """
        batch_v1 = client.BatchV1Api()
        try:
            job = batch_v1.create_namespaced_job(body=job_menifest, namespace=namespace)
        except ApiException as e:
            job_name = job_menifest.metadata.name
            if e.status == 409:
                msg = 'Fail to create job %s: already exists in %s'\
                      % (job_name, namespace)
                return False, None, msg
            else:
                msg = 'Fail to create job %s: %s' % (job_name, e)
                logger.error(e, exc_info=True)
                return False, None, msg
        return True, job, ''