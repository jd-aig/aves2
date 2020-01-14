import codecs
import json
import logging
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from inspect import isfunction

import kubernetes.client
from kubernetes import config
from kubernetes.client.rest import ApiException
from kubernetes.client import (
    V1Namespace, V1Secret, V1ObjectMeta, V1DeleteOptions,
    V1ResourceQuota, V1ResourceQuotaSpec,
    V1beta1CustomResourceDefinition, V1beta1CustomResourceDefinitionSpec,
    V1RoleBinding, V1RoleRef, V1Subject,
)


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
                # fn returns:  [response, msg]
                return fn(*args, **kwargs)
            except ApiException as e:
                logger.error('Calling {0} got exception'.format(fn) , exc_info=True)
                try:
                    # msg_str = codecs.decode(e.body, "unicode_escape")
                    msg_str = e.body.replace(r'\"', '')
                    err_msg = json.loads(msg_str)['message']
                except Exception:
                    logger.error('Fail to parse k8s api exception', exc_info=True)
                    err_msg = 'unknown'
                return None, err_msg
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
                    return None, None
                err_msg = 'Calling %s got exception %s' % (fn, str(e))
                logger.error(err_msg)
                return None, err_msg
        return fn_wrap

    @handle_api_exception
    def create_namespaced_configmap(self, configmap_manifest, namespace):
        api = client.CoreV1Api()
        logger.info("create configmap in namespace {0}: {1}".format(namespace, configmap_manifest))
        result = api.create_namespaced_config_map(namespace, configmap_manifest, pretty=True)
        return result, None

    @handle_api_exception_with_not_found
    def delete_namespaced_configmap(self, name, namespace):
        api = client.CoreV1Api()
        result = api.delete_namespaced_config_map(name, namespace)
        return result, None

    @handle_api_exception
    def create_namespaced_pod(self, pod_manifest, namespace):
        """

        :param config : dict, k8s config
        :param namespace:
        :return: [api_response, errmsg]
        """
        api = client.CoreV1Api()
        result = api.create_namespaced_pod(namespace, pod_manifest)

        logger.debug("create pod succeeded result: %s" % result)
        return result, None

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
        return result, None

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
                return None, err_msg

        api = client.CoreV1Api()
        if condition == None:
            result = api.list_namespaced_pod(namespace, watch=False)
        else:
            result = api.list_namespaced_pod(namespace, label_selector=condition, watch=False)

        return result.items, None

    @handle_api_exception
    def create_namespaced_pvc(self, pvc_manifest, namespace):
        api = kubernetes.client.CoreV1Api()
        result = api.create_namespaced_persistent_volume_claim(namespace=namespace, body=pvc_manifest)
        logger.info("create pvc succeeded result: %s" % result)
        return result, None

    @handle_api_exception_with_not_found
    def delete_namespaced_pvc(self, name, namespace):
        api = kubernetes.client.CoreV1Api()
        result = api.delete_namespaced_persistent_volume_claim(name=name, namespace=namespace)
        logger.info("delete_namespaced_pvc name:%s succeeded" % (name))
        return result, None

    @handle_api_exception
    def create_namespace(self, name):
        api = kubernetes.client.CoreV1Api()
        meta = V1ObjectMeta(name=name)
        namespace = V1Namespace(metadata=meta)
        result = api.create_namespace(body=namespace)
        logger.info("create namespace succeed result: %s" % result)
        return result, None

    @handle_api_exception_with_not_found
    def delete_namespace(self, name):
        api = kubernetes.client.CoreV1Api()
        result = api.delete_namespace(name)
        logger.info("delete namespace succeed name: %s" % name)
        return result, None

    @handle_api_exception
    def get_namespace_list(self):
        api = kubernetes.client.CoreV1Api()
        resp = api.list_namespace()
        return resp.items, None

    @handle_api_exception
    def get_namespaced_pvc_list(self, namespace):
        api = kubernetes.client.CoreV1Api()
        resp = api.list_namespaced_persistent_volume_claim(namespace=namespace)
        return resp.items, None

    @handle_api_exception
    def create_namespaced_resource_quota(self, resource_quota_manifest, namespace):
        api = kubernetes.client.CoreV1Api()
        result = api.create_namespaced_resource_quota(body=resource_quota_manifest, namespace=namespace)
        logger.info("create resource_quota in namespace {0}: {1}".format(namespace, resource_quota_manifest))
        return result, None

    @handle_api_exception
    def get_namespaced_resource_quota_list(self, namespace):
        api = kubernetes.client.CoreV1Api
        resp = api.list_namespaced_resource_quota(namespace)
        return resp.items, None

    @handle_api_exception_with_not_found
    def delete_namespaced_resource_quota(self, name, namespace):
        api = kubernetes.client.CoreV1Api()
        result = api.delete_namespaced_resource_quota(name, namespace)
        logger.info("delete resource_quota name: {0}".format(name))
        return result, None

k8s_client = K8SClient()
