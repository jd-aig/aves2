import re
import os
import io
import copy
import requests
import logging
import time
from collections import defaultdict

from django.db import models
from django_mysql.models import JSONField
from django.conf import settings

from .utils.work_builder import get_train_maker, get_storage_mixin_cls
from k8s_client.k8s_client import k8s_client
from job_manager.conf import exec_backend


logger = logging.getLogger('aves2')


def json_field_default():
    return {}

def json_field_default_list():
    return []


class AvesJob(models.Model):
    """
    """
    VALID_ENGINES = (
        'tensorflow',
        'pytorch',
        
    )

    STORAGE_MODE = ('Filesystem', 'OSS', 'OSSFile')

    STATUS_MAP = (
        ('NEW', '新建'),
        ('STARTING', '启动中'),
        ('PENDING', '等待中'),
        ('RUNNING', '运行中'),
        ('FINISHED', '已结束'),
        ('FAILURE', '已失败'),
        ('CANCELED', '已取消'),
    )

    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=128, blank=False, null=False, default='')
    namespace = models.CharField(max_length=64, blank=False, null=False, default='default')
    job_id = models.CharField(max_length=128, blank=False, null=False, default='jobid')
    engine = models.CharField(max_length=64, blank=False, null=False)
    is_distribute = models.BooleanField(blank=True, null=False, default=True)
    # forcebot: 0上报mq，1不上报（测试模式)
    # debug: 是否开发模式，1，不删除job
    image = models.CharField(max_length=512, blank=False, null=False)
    package_uri = models.CharField(max_length=512, blank=True, null=False, default='')  # 是什么？
    resource_spec = JSONField(blank=False, default=json_field_default)
    storage_mode = models.CharField(max_length=32, blank=False, null=False, default='Filesystem')
    storage_config = JSONField(blank=True, null=False, default=json_field_default)
    envs = JSONField(blank=True, default=json_field_default)
    input_spec = JSONField(blank=False, default=json_field_default)
    output_spec = JSONField(blank=False, default=json_field_default)
    log_dir = models.CharField(max_length=512, blank=True, null=False, default='')  # fs模式则指定共享存储目录/s3模式指定s3路径
    mount_node_storage = models.BooleanField(blank=True, null=False, default=False)  # 是否挂载物理节点本地盘
    status = models.CharField(max_length=16, blank=True, null=False, choices=STATUS_MAP, default='NEW')
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    @staticmethod
    def trans_request_data(data):
        data = copy.deepcopy(data)
        data['job_id'] = data['jobId']
        data.pop('jobId')
        data['package_uri'] = data['packageUri']
        data.pop('packageUri')
        data['resource_spec'] = data['resourceSpec']
        for role, role_spec in data['resource_spec'].items():
            role_spec['entry_point'] = role_spec['entryPoint']
            role_spec.pop('entryPoint')
            data['resource_spec'][role] = role_spec
        data.pop('resourceSpec')
        data['input_spec'] = data['inputSpec']
        data.pop('inputSpec')
        if 'outputSpec' in data:
            data['output_spec'] = data.get('outputSpec', {})
            data.pop('outputSpec')
        if 'logDir' in data:
            data['log_dir'] = data.get('logDir', '')
            data.pop('logDir')
        if 'storageMode' in data:
            data['storage_mode'] = data['storageMode']['mode']
            data['storage_config'] = data['storageMode']['config']
            data.pop('storageMode')
        if 'kind' in data:
            data.pop('kind')
        if 'cluster' in data:
            data.pop('cluster')
        if 'priority' in data:
            data.pop('priority')
        if 'forcebot' in data:
            data.pop('forcebot')
        if 'debug' in data:
            data.pop('debug')
        return data

    def cancel_avesjob(self):
        """ Cancel avesjob and del related k8s resources
        """
        err_msg = ''
        result = True

        for kind, handler in exec_backend.items():
            l_rs, rcs = handler['list']({'jobId': self.job_id}, namespace=self.namespace)
            if l_rs and rcs:
                for rc_i in rcs:
                    d_rs, d_msg = handler['delete'](rc_i.metadata.name, namespace=self.namespace)
                    if not d_rs:
                        err_msg += 'Failed to delete %s=%s Reason=%s ;' % (kind, rc_i.metadata.name, d_msg)
                        result = False

        return result, err_msg

    @property
    def merged_id(self):
        return '{0}-{1}-{2}'.format(self.username, self.namespace, self.job_id)

    def _make_k8s_worker_name(self, role, role_index):
        return '{0}-{1}-{2}'.format(self.merged_id, role, role_index)

    def make_k8s_workers(self):
        if self.k8s_worker.count() > 0:
            raise Exception('Not Allowed')

        k8s_workers = []
        for role, spec in self.resource_spec.items():
            for role_index in range(int(spec.get('count', 1))):
                worker = K8SWorker(
                    username=self.username,
                    namespace=self.namespace,
                    engine=self.engine,
                    avesjob=self,
                    worker_name=self._make_k8s_worker_name(role, role_index),
                    avesrole=role,
                    role_index=role_index,
                    cpu_request=spec.get('cpu', 4),
                    cpu_limit=spec.get('cpu', 4),
                    mem_request=spec.get('memory', '8Gi').strip('Gi'),
                    mem_limit=spec.get('memory', '8Gi').strip('Gi'),
                    gpu_request=spec.get('nvidia.com/gpu'),
                    entrypoint=spec.get('entry_point'),
                    args=spec.get('args', [])
                )
                k8s_workers.append(worker)
        K8SWorker.objects.bulk_create(k8s_workers)

    def update_status(self):
        pass

    def __str__(self):
        return self.merged_id

    def __unicode__(self):
        return self.merged_id

    class Meta:
        db_table = 'avesjob'


class K8SWorker(models.Model):
    """
    """
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=128, blank=False, null=False, default='')
    namespace = models.CharField(max_length=32, blank=False, null=False)
    engine = models.CharField(max_length=64, blank=False, null=False)
    avesjob = models.ForeignKey('AvesJob', on_delete=models.CASCADE, related_name='k8s_worker', blank=False, null=False)
    # worker_name = <avesjob.merged_id>-<avesrole>-<role_index>
    worker_name = models.CharField(max_length=256, blank=False, null=False, default='')
    avesrole = models.CharField(max_length=16, blank=False, null=False, default='worker')
    role_index = models.IntegerField(blank=False, null=False, default=0)
    cpu_request = models.IntegerField('REQCPU', blank=False, null=False, default=4)
    cpu_limit = models.IntegerField('LIMCPU', blank=True, null=True)
    mem_request = models.IntegerField('REQMEM(Gi)', blank=False, null=False, default=8)
    mem_limit = models.IntegerField('LIMMEM(Gi)', blank=True, null=True, default=8)
    gpu_request = models.IntegerField('REQGPU', blank=True, null=True)
    entrypoint = models.CharField(max_length=512, blank=True, null=False, default='')
    args = JSONField(blank=True, null=False, default=json_field_default_list)
    ports = JSONField(blank=True, null=False, default=json_field_default_list)
    k8s_status = models.CharField(max_length=32, blank=True, null=True, default='')
    worker_json = JSONField(blank=True, null=True, default=json_field_default)
    service_json = JSONField(blank=True, null=True, default=json_field_default)
    ingress_json = JSONField(blank=True, null=True, default=json_field_default)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    def make_k8s_conf(self, save=True):
        conf_maker = type(
            'conf_maker',
            (
                get_train_maker(self.engine),
                get_storage_mixin_cls(self.avesjob.storage_mode)
            ),
            {}
        )(self.avesjob, self)
        worker_conf = conf_maker.gen_k8s_worker_conf()
        svc_conf = conf_maker.gen_k8s_svc_conf()
        self.worker_json = worker_conf
        self.service_json = svc_conf
        if save:
            self.save()

    def _del_k8s_resource(self, conf):
        pass

    def _create_k8s_resource(self, conf):
        handler = exec_backend.get(conf['kind'])
        if handler:
            try:
                res, err_msg = handler['create'](config=conf, namespace=self.namespace)
            except Exception as e:
                logger.error('Create k8s resource failed, kind: {0}, name: {1}'.format(conf['kind'], conf['metadata']['name']))
                _del_k8s_resource(self, conf)
        else:
            logger.error("Unsupported resource kind: {0}, name: {1}".format(conf['kind'], conf['metadata']['name']))

    def start(self):
        worker_conf = self.worker_json
        svc_conf = self.service_json
        ingress_conf = self.ingress_json

        if worker_conf:
            self._create_k8s_resource(worker_conf)

        if svc_conf:
            self._create_k8s_resource(svc_conf)

        if ingress_conf:
            self._create_k8s_resource(ingress_conf)

    def stop(self):
        pass

    def __str__(self):
        return self.worker_name

    def __unicode__(self):
        return self.worker_name

    class Meta:
        db_table = 'k8sworker'

