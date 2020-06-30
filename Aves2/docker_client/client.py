import codecs
import time
import json
import logging
import docker
from docker.errors import APIError
from inspect import isfunction

from django.conf import settings


logger = logging.getLogger('aves2')

DOCKER_URL = settings.DOCKER_URL


class DockerClient(object):
    client = docker.DockerClient(base_url=DOCKER_URL)

    def __init__(self):
        pass

    def handle_api_exception(fn):
        def fn_wrap(*args, **kwargs):
            try:
                # fn returns:  [response, msg]
                return fn(*args, **kwargs)
            except APIError as e:
                logger.error('Calling {0} got exception'.format(fn), exc_info=True)
                try:
                    err_msg = e.response.json()['message']
                except Exception:
                    err_msg = e.response.text
                return None, err_msg
        return fn_wrap

    @handle_api_exception
    def create_multiple_configs(self, config_datas):
        """ Create multiple docker configs

        :param config_datas: a list of config data dict,
                             eg. [{'name': 'cfg', 'data': 'content'}]
        :return configs: a list of docker.models.configs.Config
        """
        configs = []
        for data in config_datas:
            config = self.client.configs.create(**data)
            config.reload()
            configs.append(config)
        return configs, None

    @handle_api_exception
    def delete_configs(self, config_name_prefix):
        configs = self.client.configs.list(filters={'name': config_name_prefix})
        for config in configs:
            config.remove()
        return True, None

    @handle_api_exception
    def create_service(self, svc_args, svc_kwargs):
        """

        :param svc_args:
        :param svc_kwargs:
        :return: [Service, errmsg]
        """
        service = self.client.services.create(*svc_args, **svc_kwargs)
        service.reload()
        logger.debug("create docker service: %s" % service)
        return service, None

    @handle_api_exception
    def delete_service(self, name):
        services = self.client.services.list(filters=dict(name=name))
        for svc in services:
            if svc.name != name:
                continue
            svc.remove()
        return True, None

    @handle_api_exception
    def get_container_log(self, service_name, since_seconds=None, tail_lines=None):
        services = self.client.services.list(filters=dict(name=service_name))
        for service in services:
            if service.name != service_name:
                continue
            container_id = service.tasks()[0]['Status']['ContainerStatus']['ContainerID']
            container = self.client.containers.get(container_id)
            result = container.logs(tail=tail_lines, timestamps=True)
            result = result.decode()
            return result, None
        return 'Not found', None

    @handle_api_exception
    def get_container_status(self, service_name):
        services = self.client.services.list(filters=dict(name=service_name))
        for service in services:
            if service.name != service_name:
                continue
            containers = service.tasks()
            return containers, None
        return 'Not found', None

    @handle_api_exception
    def list_containers(self, labels):
        label_l = ['{0}={1}'.format(k, v) for k, v in labels.items()]
        filters = {'lable': label_l}
        containers = self.client.containers.list(all=True, filters=filters)
        return containers, None

if settings.ENABLE_K8S:
    doc_client = None
else:
    doc_client = DockerClient()
