import re
import os
import io
import copy
import time
import logging
import requests
from collections import defaultdict

from django.db import models
from django.conf import settings
from django_mysql.models import JSONField

from .utils.work_builder.base_maker import BaseMaker
from kubernetes_client.k8s_objects import make_pod, make_configmap
from kubernetes_client.client import k8s_client


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

    DISTRIBUTE_TYPES = (
        ('TF_PS', 'TF_PS'),
        ('HOROVOD', 'HOROVOD')
    )

    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=128, blank=False, null=False, default='')
    namespace = models.CharField(max_length=64, blank=False, null=False, default='default')
    job_id = models.CharField(max_length=128, blank=False, null=False, default='jobid', unique=True)
    engine = models.CharField(max_length=64, blank=False, null=False)
    is_distribute = models.BooleanField(blank=True, null=False, default=False)
    distribute_type = models.CharField(max_length=64, blank=True, null=True, choices=DISTRIBUTE_TYPES)
    # forcebot: 0上报mq，1不上报（测试模式)
    # debug: 是否开发模式，1，不删除job
    image = models.CharField(max_length=512, blank=False, null=False)
    package_uri = models.CharField(max_length=512, blank=True, null=False, default='')  # 是什么？
    resource_spec = JSONField(blank=False, default=json_field_default)
    storage_mode = models.CharField(max_length=32, blank=False, null=False, default='OSSFile')
    storage_config = JSONField(blank=True, null=False, default=json_field_default)
    envs = JSONField(blank=True, default=json_field_default)
    input_spec = JSONField(blank=False, default=json_field_default)
    output_spec = JSONField(blank=False, default=json_field_default)
    log_dir = models.CharField(max_length=512, blank=True, null=False, default='')  # fs模式则指定共享存储目录/s3模式指定s3路径
    mount_node_storage = models.BooleanField(blank=True, null=False, default=False)  # 是否挂载物理节点本地盘
    status = models.CharField(max_length=16, blank=True, null=False, choices=STATUS_MAP, default='NEW')
    token = models.CharField(max_length=16, blank=True, null=False, default='')
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

    @property
    def merged_id(self):
        return '{0}-{1}-{2}'.format(self.username, self.namespace, self.job_id)

    def _make_k8s_worker_name(self, role, role_index):
        return '{0}-{1}-{2}'.format(self.merged_id, role, role_index)

    def make_k8s_workers(self):
        if self.k8s_worker.count() > 0:
            logger.error('{0}: Fail to make k8s workers, already exist'.format(self))
            raise Exception('Not Allowed')

        k8s_workers = []
        no_master_role = True if 'master' not in self.resource_spec.keys() else False
        for role, spec in self.resource_spec.items():
            for role_index in range(int(spec.get('count', 1))):
                if not self.is_distribute:
                    is_main_node = True
                elif role in ['ps', 'master'] and role_index == 0:
                    is_main_node = True
                elif role in ['worker'] and role_index == 0 and no_master_role:
                    is_main_node = True
                else:
                    is_main_node = False
                worker = K8SWorker(
                    username=self.username,
                    namespace=self.namespace,
                    engine=self.engine,
                    avesjob=self,
                    worker_name=self._make_k8s_worker_name(role, role_index),
                    is_main_node = is_main_node,
                    avesrole=role,
                    role_index=role_index,
                    cpu_request=spec.get('cpu', 4),
                    cpu_limit=spec.get('cpu', 4),
                    mem_request=spec.get('memory', '8Gi').strip('Gi'),
                    mem_limit=spec.get('memory', '8Gi').strip('Gi'),
                    gpu_request=spec.get('gpu'),
                    entrypoint=spec.get('entry_point'),
                    args=spec.get('args', [])
                )
                k8s_workers.append(worker)
        K8SWorker.objects.bulk_create(k8s_workers)

    def update_status(self, status, msg=''):
        # TODO: send signal, send message
        self.status = status
        self.save()

    def start(self):
        """ Start aves job

        :return: (True/False, err_msg)
        """
        for worker_i in self.k8s_worker.all():
            pod, err = worker_i.start()
            if err:
                return False, err
        return True, None

    def cancel(self):
        """ Cancel avesjob and del related k8s resources

        :return: (True/False, err_msg)
        """
        for worker_i in self.k8s_worker.all():
            rt = worker_i.stop()
            if not rt:
                return False, '{0}: Fail to stop work {1}'.format(self, worker_i)
        return True, None

    def clean_work(self):
        logger.info('{0}: clean job. job workers will be cleaned'.format(self))
        for worker_i in self.k8s_worker.all():
            worker_i.stop()

    def get_dist_envs(self):
        if self.distribute_type == 'TF_PS':
            return self._get_dist_envs_for_tfps()
        if self.distribute_type == 'HOROVOD':
            return self._get_dist_envs_for_horovod()
        else:
            return {}

    def _get_dist_envs_for_tfps(self):
        all_workers = self.k8s_worker.all()
        ps = [str(i.id) for i in all_workers if i.avesrole == 'ps']
        workers = [str(i.id) for i in all_workers if i.avesrole == 'worker']

        pods, msg = k8s_client.get_namespaced_pod_list(self.namespace, selector={'jobId': self.job_id})
        ps_ips = ['{0}:2222'.format(i.status.pod_ip) for i in pods if i.metadata.labels.get('workerId') in ps]
        worker_ips = [ '{0}:2222'.format(i.status.pod_ip) for i in pods if i.metadata.labels.get('workerId') in workers]

        return {'AVES_TF_PS_HOSTS': ','.join(ps_ips), 'AVES_TF_WORKER_HOSTS': ','.join(worker_ips)}

    def _get_dist_envs_for_horovod(self):
        all_workers = self.k8s_worker.all()
        np = 0
        hosts = []
        pods, msg = k8s_client.get_namespaced_pod_list(self.namespace, selector={'jobId': self.job_id})
        pods_map = {int(i.metadata.labels.get('workerId')): i for i in pods}
        for w in all_workers:
            pod = pods_map[w.id]
            np += w.gpu_request
            hosts.append('{}:{}'.format(pod.status.pod_ip, w.gpu_request))
        # TODO: support setting ssh port
        d = {
                'AVES_MPI_NP': np,
                'AVES_MPI_HOST_LIST': ','.join(hosts),
                'AVES_MPI_SSH_PORT': 22
            }
        return d

    def __str__(self):
        return self.merged_id

    def __unicode__(self):
        return self.merged_id

    class Meta:
        db_table = 'avesjob'


class K8SWorker(models.Model):
    """
    """
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
    namespace = models.CharField(max_length=32, blank=False, null=False)
    engine = models.CharField(max_length=64, blank=False, null=False)
    avesjob = models.ForeignKey('AvesJob', on_delete=models.CASCADE, related_name='k8s_worker', blank=False, null=False)
    # worker_name = <avesjob.merged_id>-<avesrole>-<role_index>
    worker_name = models.CharField(max_length=256, blank=False, null=False, default='')
    is_main_node = models.BooleanField(blank=True, null=False, default=True)
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
    k8s_status = models.CharField(max_length=32, blank=True, null=False, choices=STATUS_MAP, default='NEW')
    worker_ip = models.CharField(max_length=32, blank=True, null=True)
    worker_json = JSONField(blank=True, null=True, default=json_field_default)
    service_json = JSONField(blank=True, null=True, default=json_field_default)
    ingress_json = JSONField(blank=True, null=True, default=json_field_default)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    def start(self):
        """ Start k8s worker pod

        :return: result, err_msg
        """
        m = BaseMaker(self.avesjob, self)

        configmap = make_configmap(*m.gen_confdata_aves_scripts())
        k8s_client.delete_namespaced_configmap(configmap.metadata.name, self.namespace)
        conf, err = k8s_client.create_namespaced_configmap(configmap, self.namespace)

        pod = make_pod(
                  name=self.worker_name,
                  cmd=m.gen_command(),
                  args=m.gen_args(),
                  image=m.gen_image(),
                  env=m.gen_envs(),
                  labels=m.gen_pod_labels(),
                  port_list=[],
                  volumes=m.gen_volumes(),
                  volume_mounts=m.gen_volume_mounts(),
                  cpu_limit=self.cpu_request,
                  cpu_guarantee=self.cpu_limit,
                  mem_limit='{mem}Gi'.format(mem=self.mem_request),
                  mem_guarantee='{mem}Gi'.format(mem=self.mem_limit),
                  gpu_limit=self.gpu_request,
                  gpu_guarantee=self.gpu_request,
              )
        pod_obj, err = k8s_client.create_namespaced_pod(pod, self.namespace)
        rt = pod_obj is not None
        return rt, err

    def stop(self):
        """ Stop k8s worker pod

        :return: result, err_msg
        """
        logger.info('delete job pod: {0}'.format(self))
        m = BaseMaker(self.avesjob, self)
        configmap = make_configmap(*m.gen_confdata_aves_scripts())

        st1, msg1 = k8s_client.delete_namespaced_pod(self.worker_name, self.namespace)
        st2, msg2 = k8s_client.delete_namespaced_configmap(configmap.metadata.name, self.namespace)
        msg = None if not(msg1 or msg2) else '{0}\n{1}'.format(msg1, msg2)
        return st1 and st2, msg

    def update_status(self, status, msg=''):
        # TODO: replace k8s status with status
        self.k8s_status = status
        self.save()

    def __str__(self):
        return self.worker_name

    def __unicode__(self):
        return self.worker_name

    class Meta:
        db_table = 'k8sworker'

