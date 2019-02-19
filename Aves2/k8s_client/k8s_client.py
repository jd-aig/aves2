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

    def create_job(self, config, namespace='default'):
        """ Create k8s Job
        """
        api = client.BatchV1Api()
        result = api.create_namespaced_job(namespace, config)

        logger.debug("create job succeeded result: %s" % result) 
        return True, result

    def delete_job(self, name, namespace='default'):
        """ Delete k8s job
        """
        api = client.BatchV1Api()
        body = client.V1DeleteOptions()
        body.propagation_policy = 'Background'
        result = api.delete_namespaced_job(name, namespace, body)

        logger.info('delete_namespaced_job name: %s succeeded' % (name))
        return True, None

    def list_job(self, selector=None, namespace='default'):
        """ List namespaced job
        """
        condition = None

        if selector:
            success, condition = self._build_condition(selector=selector)
            if not success:
                return False, condition

        api = client.BatchV1Api()
        if not condition:
            result = api.list_namespaced_job(namespace, watch=False)
        else:
            result = api.list_namespaced_job(namespace, label_selector=condition, watch=False)

        return True, result.items

    def create_svc(self, config, namespace='default'):
        """ Create k8s Service

        :param config: dict
        :param namespace: string
        """
        api = self.corev1api
        result = api.create_namespaced_service(namespace, config)

        logger.debug("create service succeeded result: %s" % result) 
        return True, result

    def delete_svc(self, name, namespace='default'):
        """ Delete k8s Service

        :param name: string, 'jobid-rolename-index'
        :param namespace:
        :return: True, None / False, err_msg
        """
        api = self.corev1api
        body = client.V1DeleteOptions()
        body.propagation_policy = 'Background'
        result = api.delete_namespaced_service(name, namespace, body)

        logger.info("delete_namespaced_service name:%s succeeded" % (name))
        return True, None

    def list_svc(self, selector=None, namespace='default'):
        """ List namespaced service with label_selector
        """
        condition = None

        if selector:
            success, condition = self._build_condition(selector=selector)
            if not success:
                return False, condition

        api = self.corev1api
        if not condition:
            result = api.list_namespaced_service(namespace, watch=False)
        else:
            result = api.list_namespaced_service(namespace, label_selector=condition, watch=False)

        return True, result.items

    def create_ingress(self, config, namespace='default'):
        """ Create k8s Ingress

        :param config : dict, k8s config
        :param namespace: string
        :return: [True, kubernetes.client.models.v1beta1_ingress.V1beta1Ingress]
                 or [False, err_msg]
        """
        api = self.ExtensionsV1beta1Api()
        result = api.create_namespaced_ingress(namespace, config)

        logger.debug("create ingress succeeded result: %s" % result)
        return True, result

    def delete_ingress(self):
        """ Delete k8s Ingress

        :param name: string, 'jobid-rolename-index'
        :param namespace:
        :return: True, None / False, err_msg
        """
        api = client.ExtensionsV1beta1Api()
        body = client.V1DeleteOptions()
        body.propagation_policy = 'Background'
        result = api.delete_namespaced_ingress(name, namespace, body)

        logger.info("delete_namespaced_ingress name:%s succeeded" % (name))
        return True, None

    def list_ingress(self, selector=None, namespace='default'):
        """ List namespaced ingress with selector
        """
        condition = None

        if selector:
            success, condition = self._build_condition(selector=selector)
            if not success:
                return False, condition

        api = client.ExtensionsV1beta1Api()
        if not condition:
            result = api.list_namespaced_ingress(namespace, watch=False)
        else:
            result = api.list_namespaced_ingress(namespace, label_selector=condition, watch=False)

        return True, result.items

    def create_rc(self, config, namespace='default'):
        """ Create k8s ReplicationController

        :param config : dict, k8s config
        :param namespace:
        :return: [True, kubernetes.client.models.v1_replication_controller.V1ReplicationController]
                 or [False, err_msg]
        """
        api = self.corev1api
        result = api.create_namespaced_replication_controller(namespace, config)

        logger.debug("create rc succeeded result: %s" % result)
        return True, result

    def delete_rc(self, name=None, namespace='default'):
        """ Delete k8s ReplicationController

        :param name: string, rc name
        :param namespace: string
        """
        api = self.corev1api
        body = client.V1DeleteOptions()
        # Acceptable values are:
        #'Orphan' - orphan the dependents;
        #'Background' - allow the garbage collector to delete the dependents in the background;
        #'Foreground' - a cascading policy that deletes all dependents in the foreground.
        body.propagation_policy = 'Background'
        result = api.delete_namespaced_replication_controller(name, namespace, body)

        logger.info("delete_namespaced_replication_controller name:%s succeeded" % (name))
        return True, None

    def list_rc(self, selector=None, namespace='default'):
        """ List namespaced ReplicationController with label_selector
        """
        condition = None

        if selector:
            success, condition = self._build_condition(selector=selector)
            if not success:
                return False, condition

        api = self.corev1api
        if not condition:
            result = api.list_namespaced_replication_controller(namespace, watch=False)
        else:
            result = api.list_namespaced_replication_controller(namespace, label_selector=condition, watch=False)

        return True, result.items

    def _build_condition(self, selector=None):
        if not selector:
            err_msg = 'Selector cannot be none'
            return False, err_msg

        condition = ''
        if selector:
            if not isinstance(selector, dict):
                err_msg = 'Selector must be dict'
                return False, err_msg

            for k, v in selector.items():
                condition += '%s=%s,' % (k, v)
            if len(condition) > 0:
                condition = condition[:-1]
        return True, condition 


k8s_client = K8SClient()