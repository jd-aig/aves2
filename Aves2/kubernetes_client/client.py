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

    def handle_api_exception(fn):
        def fn_wrap(*args, **kwargs):
            try:
                # fn returns:  [True, object] or [False, err_msg]
                return fn(*args, **kwargs)
            except ApiException as e:
                err_msg = 'Calling %s got exception %s' % (fn, str(e))
                logger.error(err_msg)
                return False, err_msg
        return fn_wrap

    def handle_api_exception_with_not_found(fn):
        def fn_wrap(*args, **kwargs):
            try:
                # fn returns:  [True, object] or [False, err_msg]
                return fn(*args, **kwargs)
            except ApiException as e:
                if e.status == 404:
                    # not found, just return True
                    logger.info("%s not found" % (fn))
                    return True, None
                err_msg = 'Calling %s got exception %s' % (fn, str(e))
                logger.error(err_msg)
                return False, err_msg
        return fn_wrap

    @handle_api_exception
    def create_namespaced_configmap(self, configmap_manifest, namespace):
        api = client.CoreV1Api()
        logger.info("create configmap in namespace {0}: {1}".format(namespace, configmap_manifest))
        result = api.create_namespaced_config_map(namespace, configmap_manifest, pretty=True)
        return True, result

    @handle_api_exception_with_not_found
    def delete_namespaced_configmap(self, name, namespace):
        api = client.CoreV1Api()
        result = api.delete_namespaced_config_map(name, namespace)
        return True, None

    @handle_api_exception
    def create_namespaced_pod(self, pod_manifest, namespace):
        """

        :param config : dict, k8s config
        :param namespace:
        :return: [True, kubernetes.client.models.v1_pod.V1Pod]
                 or [False, err_msg]
        """
        api = client.CoreV1Api()
        result = api.create_namespaced_pod(namespace, pod_manifest)

        logger.debug("create pod succeeded result: %s" % result)
        return True, result

    def _build_condition(self, selector=None):
        if selector is None:
            err_msg = 'selector must specified one'
            return False, err_msg
        condition = ''
        if selector:
            if not isinstance(selector, dict):
                err_msg = 'selector must be dict'
                return False, err_msg
            for k, v in selector.items():
                condition += '%s=%s,' % (k, v)
            if len(condition) > 0:
                condition = condition[:-1]
        return True, condition

    @handle_api_exception_with_not_found
    def delete_namespaced_pod(self, name, namespace):
        """

        :param name: string, rc name
        :param namespace: string
        :return: True, None or False, err_msg
        """
        api = client.CoreV1Api()
        body = client.V1DeleteOptions()
        # Acceptable values are:
        #'Orphan' - orphan the dependents;
        #'Background' - allow the garbage collector to delete the dependents in the background;
        #'Foreground' - a cascading policy that deletes all dependents in the foreground.
        body.propagation_policy = 'Background'
        result = api.delete_namespaced_pod(name, namespace, body=body)

        logger.info("delete_namespaced_pod name:%s succeeded" % (name))
        return True, None

    @handle_api_exception
    def get_namespaced_pod_list(self, namespace, selector=None):
        """
        :param selector: dict, label dict
        :return: True, [kubernetes.client.models.v1_pod.V1Pod]
                 or False, err_msg
        """
        condition = None
        if selector != None:
            success, condition = self._build_condition(selector=selector)
            if not success:
                err_msg = condition
                return False, err_msg

        api = client.CoreV1Api()
        if condition == None:
            result = api.list_namespaced_pod(namespace, watch=False)
        else:
            result = api.list_namespaced_pod(namespace, label_selector=condition, watch=False)

        return True, result.items


k8s_client = K8SClient()
