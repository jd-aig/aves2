import re
import os
import io
import copy
import time
import json
import logging
import requests
from collections import defaultdict

from django.db import models
from django.conf import settings
from django_mysql.models import JSONField
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

from .utils.work_builder.base_maker import BaseMaker

if settings.ENABLE_K8S:
    from kubernetes_client.k8s_objects import make_pod, make_configmap
    from kubernetes_client.client import k8s_client
else:
    from docker_client.docker_objects import make_config_datas, make_service
    from docker_client.client import doc_client

logger = logging.getLogger('aves2')


def json_field_default():
    return {}


def json_field_default_list():
    return []


class JobStatus:
    NEW = 'NEW'
    STARTING = 'STARTING'
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    FINISHED = 'FINISHED'
    FAILURE = 'FAILURE'
    CANCELED = 'CANCELED'


class AvesJob(models.Model):
    """
    """
    VALID_ENGINES = (
        'tensorflow',
        'pytorch',
    )

    STORAGE_MODE = ('Filesystem', 'OSS', 'OSSFile')

    STATUS_MAP = (
        (JobStatus.NEW, '新建'),
        (JobStatus.STARTING, '启动中'),
        (JobStatus.PENDING, '等待中'),
        (JobStatus.RUNNING, '运行中'),
        (JobStatus.FINISHED, '已结束'),
        (JobStatus.FAILURE, '已失败'),
        (JobStatus.CANCELED, '已取消'),
    )

    DISTRIBUTE_TYPES = (
        ('TF_PS', 'TF_PS'),
        ('HOROVOD', 'HOROVOD')
    )

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128, blank=True, null=False, default='')
    describe = models.CharField(max_length=1024, blank=True, null=False, default='')
    username = models.CharField(max_length=128, blank=False, null=False, default='')
    namespace = models.CharField(max_length=64, blank=False, null=False, default='default')
    job_id = models.CharField(max_length=128, blank=False, null=False, default='none')
    engine = models.CharField(max_length=64, blank=False, null=False)
    is_distribute = models.BooleanField(blank=True, null=False, default=False)
    distribute_type = models.CharField(max_length=64, blank=True, null=True, choices=DISTRIBUTE_TYPES)
    debug = models.BooleanField(blank=True, null=False, default=True)
    image = models.CharField(max_length=512, blank=False, null=False)
    package_uri = models.CharField(max_length=512, blank=True, null=False, default='')
    resource_spec = JSONField(blank=False, default=json_field_default)
    storage_mode = models.CharField(max_length=32, blank=False, null=False, default='OSSFile')
    storage_config = JSONField(blank=True, null=False, default=json_field_default)
    envs = JSONField(blank=True, default=json_field_default)
    code_spec = JSONField(blank=False, default=json_field_default)
    input_spec = JSONField(blank=False, default=json_field_default)
    output_spec = JSONField(blank=False, default=json_field_default)
    log_dir = JSONField(blank=True, null=False, default=json_field_default)
    mount_node_storage = models.BooleanField(blank=True, null=False, default=False)  # 是否挂载物理节点本地盘
    status = models.CharField(max_length=16, blank=True, null=False, choices=STATUS_MAP, default=JobStatus.NEW)
    need_report = models.BooleanField(blank=True, null=False, default=False)
    token = models.CharField(max_length=16, blank=True, null=False, default='')
    msg = models.CharField(max_length=512, blank=True, null=False, default='')
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    @property
    def job_name(self):
        return self.name if self.name else self.merged_id

    @property
    def ready_to_run(self):
        ready = self.status in ['NEW', 'FINISHED', 'FAILURE', 'CANCELED']
        return ready

    @property
    def api_token(self):
        if not hasattr(self, '_user'):
            user = User.objects.get(username=self.username)
            setattr(self, '_user', user)
        if not hasattr(self, '_token'):
            try:
                token = Token.objects.get(user=self._user).key
                setattr(self, '_token', token)
            except Exception as e:
                token = Token.objects.create(user=self._user).key
                setattr(self, '_token', token)
        return self._token

    @property
    def all_workers(self):
        return self.aves_worker.all()

    @property
    def merged_id(self):
        return 'aves{0}-{1}-{2}-{3}'.format(self.id, self.username, self.namespace, self.job_id)

    def _make_aves_worker_name(self, role, role_index):
        return '{0}-{1}-{2}'.format(self.merged_id, role, role_index)

    def make_aves_workers(self):
        if self.aves_worker.count() > 0:
            logger.error('{0}: Fail to make aves workers, already exist'.format(self))
            raise Exception('Not Allowed')

        aves_workers = []
        no_master_role = True if 'master' not in self.resource_spec.keys() else False
        no_ps_role = True if 'ps' not in self.resource_spec.keys() else False
        for role, spec in self.resource_spec.items():
            for role_index in range(int(spec.get('count', 1))):
                if not self.is_distribute:
                    is_main_node = True
                elif role in ['ps', 'master'] and role_index == 0:
                    is_main_node = True
                elif role in ['worker'] and role_index == 0 and no_master_role and no_ps_role:
                    is_main_node = True
                else:
                    is_main_node = False
                worker = AvesWorker(
                    username=self.username,
                    namespace=self.namespace,
                    engine=self.engine,
                    avesjob=self,
                    worker_name=self._make_aves_worker_name(role, role_index),
                    is_main_node=is_main_node,
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
                aves_workers.append(worker)
        AvesWorker.objects.bulk_create(aves_workers)

    def update_status(self, status, msg=''):
        from .tasks import report_avesjob_status
        logger.info(f'Job status changed: {self}, {status}, {msg}')
        self.status = status
        self.msg = msg
        self.save()
        if self.need_report:
            report_avesjob_status.apply_async((self.job_id, status, msg))

    def start(self):
        """ Start aves job

        :return: (True/False, err_msg)
        """
        if self.aves_worker.count() == 0:
            try:
                self.make_aves_workers()
            except Exception as e:
                err = 'Fail to create aves workers'
                logger.error('fail to create aves workers', exc_info=True)
                return False, err

        for worker_i in self.aves_worker.all():
            pod, err = worker_i.start()
            if err:
                return False, err
        return True, None

    def cancel(self):
        """ Cancel avesjob and del related k8s/docker resources

        :return: (True/False, err_msg)
        """
        for worker_i in self.aves_worker.all():
            rt = worker_i.stop()
            if not rt:
                return False, '{0}: Fail to stop work {1}'.format(self, worker_i)
        return True, None

    def clean_work(self, force=False):
        logger.info('{0}: clean job. job workers will be cleaned'.format(self))
        for worker_i in self.aves_worker.all():
            if self.debug == True and worker_i.is_main_node and force == False:
                continue
            worker_i.stop()

    def get_dist_envs(self):
        if self.distribute_type == 'TF_PS':
            return self._get_dist_envs_for_tfps()
        if self.distribute_type == 'HOROVOD':
            return self._get_dist_envs_for_horovod()
        else:
            return {}

    def _get_dist_envs_for_tfps(self):
        """
        tensorflow-ps cluster envs:
            AVES_TF_PS_HOSTS: <PS0 IP1> <PS1 IP> ...
            AVES_TF_WORKER_HOSTS: <Worker0 IP> <Worker1 IP> <Worker2 IP> ...
        """
        all_workers = self.aves_worker.all()
        ps = [str(i.id) for i in all_workers if i.avesrole == 'ps']
        workers = [str(i.id) for i in all_workers if i.avesrole == 'worker']

        # TODO: make a better implementation
        if settings.ENABLE_K8S:
            pods, msg = k8s_client.get_namespaced_pod_list(self.namespace, selector={'avesJobId': self.id})
            ps_ips = ['{0}:2222'.format(i.status.pod_ip) for i in pods if i.metadata.labels.get('workerId') in ps]
            worker_ips = ['{0}:2222'.format(i.status.pod_ip) for i in pods if i.metadata.labels.get('workerId') in workers]
        else:
            containers, msg = doc_client.list_containers(labels={'avesJobId': self.id})
            ps_ips = ['{0}:2222'.format(i.attrs['NetworkSettings']['Networks'][settings.AVES2_TRAIN_NETWORK]['IPAMConfig']['IPv4Address']) for i in pods if i.labels.get('workerId') in ps]
            worker_ips = ['{0}:2222'.format(i.attrs['NetworkSettings']['Networks'][settings.AVES2_TRAIN_NETWORK]['IPAMConfig']['IPv4Address']) for i in pods if i.labels.get('workerId') in workers]

        return {'AVES_TF_PS_HOSTS': ','.join(ps_ips), 'AVES_TF_WORKER_HOSTS': ','.join(worker_ips)}

    def _get_dist_envs_for_horovod(self):
        """
        Horovod cluster envs:
            AVES_MPI_NP: Total number of processes to run
            AVES_MPI_HOST_LIST: <Worker0 IP>:<number of process>, <Worker1 IP>:<number of process>
            AVES_MPI_SSH_PORT: 22
        """
        all_workers = self.aves_worker.all()
        np = 0
        hosts = []
        # TODO: make a better implementation
        if settings.ENABLE_K8S:
            pods, msg = k8s_client.get_namespaced_pod_list(self.namespace, selector={'avesJobId': self.id})
            pods_map = {int(i.metadata.labels.get('workerId')): i for i in pods}
            for w in all_workers:
                per_num = w.gpu_request if w.gpu_request else 1
                pod = pods_map[w.id]
                np += per_num
                hosts.append('{}:{}'.format(pod.status.pod_ip, per_num))
        else:
            containers, msg = doc_client.list_containers(labels={'avesJobId': self.id})
            containers_map = {int(i.labels.get('workerId')): i for i in containers}
            for w in all_workers:
                per_num = w.gpu_request if w.gpu_request else 1
                container = containers_map[w.id]
                np += per_num
                ip = container.attrs['NetworkSettings']['Networks'][settings.AVES2_TRAIN_NETWORK]['IPAMConfig']['IPv4Address']
                hosts.append('{}:{}'.format(ip, per_num))
        # TODO: support setting ssh port
        d = {
                'AVES_MPI_NP': np,
                'AVES_MPI_HOST_LIST': ','.join(hosts),
                'AVES_MPI_SSH_PORT': 22
            }
        return d

    def is_finised(self):
        # TODO:
        pass

    def __str__(self):
        return self.merged_id

    def __unicode__(self):
        return self.merged_id

    class Meta:
        db_table = 'avesjob'


class WorkerStatus:
    NEW = 'NEW'
    STARTING = 'STARTING'
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    FINISHED = 'FINISHED'
    FAILURE = 'FAILURE'
    CANCELED = 'CANCELED'


class AvesWorker(models.Model):
    """
    """
    STATUS_MAP = (
        (WorkerStatus.NEW, '新建'),
        (WorkerStatus.STARTING, '启动中'),
        (WorkerStatus.PENDING, '等待中'),
        (WorkerStatus.RUNNING, '运行中'),
        (WorkerStatus.FINISHED, '已结束'),
        (WorkerStatus.FAILURE, '已失败'),
        (WorkerStatus.CANCELED, '已取消'),
    )

    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=128, blank=False, null=False, default='')
    namespace = models.CharField(max_length=32, blank=False, null=False)
    engine = models.CharField(max_length=64, blank=False, null=False)
    avesjob = models.ForeignKey('AvesJob', on_delete=models.CASCADE, related_name='aves_worker', blank=False, null=False)
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
    k8s_status = models.CharField(max_length=32, blank=True, null=False, choices=STATUS_MAP, default=WorkerStatus.NEW)
    worker_ip = models.CharField(max_length=32, blank=True, null=True)
    worker_json = JSONField(blank=True, null=True, default=json_field_default)
    service_json = JSONField(blank=True, null=True, default=json_field_default)
    ingress_json = JSONField(blank=True, null=True, default=json_field_default)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    def _kube_start(self):
        """ Start aves worker pod

        :return: result, err_msg
        """
        try:
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
        except Exception as e:
            logger.error('{0}: Fail to start. unhandled exception'.format(self), exc_info=True)
            return None, 'Fail to start worker {}'.format(self.worker_name)
        if rt:
            self.k8s_status = WorkerStatus.STARTING
            self.save()
        return rt, err

    def _swarm_start(self):
        try:
            m = BaseMaker(self.avesjob, self)
            config_datas = make_config_datas(*m.gen_confdata_aves_scripts())
            configs, err = doc_client.create_multiple_configs(config_datas)

            svc_args, svc_kwargs = \
                    make_service(
                        name=self.worker_name,
                        cmd=m.gen_command(),
                        cmd_args=m.gen_args(),
                        image=m.gen_image(),
                        env=m.gen_envs(),
                        networks=[settings.AVES2_TRAIN_NETWORK],
                        labels=m.gen_pod_labels(),
                        port_list=[],
                        configs=configs,
                        volumes=m.gen_volumes(),
                        volume_mounts=m.gen_volume_mounts(),
                        cpu_limit=self.cpu_request,
                        cpu_guarantee=self.cpu_limit,
                        mem_limit='{mem}Gi'.format(mem=self.mem_request),
                        mem_guarantee='{mem}Gi'.format(mem=self.mem_limit),
                        gpu_limit=self.gpu_request,
                        gpu_guarantee=self.gpu_request,
                    )
            docker_svc, err = doc_client.create_service(svc_args, svc_kwargs)
        except Exception:
            logger.error('{0}: Fail to start. unhandled exception'.format(self), exc_info=True)
            return None, 'Fail to start worker {}'.format(self.worker_name)
        if docker_svc:
            self.k8s_status = WorkerStatus.STARTING
            self.save()
        return docker_svc, err

    def start(self):
        if settings.ENABLE_K8S:
            return self._kube_start()
        else:
            return self._swarm_start()

    def _kube_stop(self):
        """ Stop aves worker pod

        :return: result, err_msg
        """
        logger.info('delete job pod: {0}'.format(self))
        m = BaseMaker(self.avesjob, self)
        configmap = make_configmap(*m.gen_confdata_aves_scripts())

        st1, msg1 = k8s_client.delete_namespaced_pod(self.worker_name, self.namespace)
        st2, msg2 = k8s_client.delete_namespaced_configmap(configmap.metadata.name, self.namespace)
        msg = None if not(msg1 or msg2) else '{0}\n{1}'.format(msg1, msg2)
        return st1 and st2, msg

    def _docker_stop(self):
        # TODO: rm service and config in celery task
        logger.info('delete job service: {0}'.format(self))
        m = BaseMaker(self.avesjob, self)
        config_datas = make_config_datas(*m.gen_confdata_aves_scripts())
        configmap_name, _ = m.gen_confdata_aves_scripts()
        st2, msg2 = doc_client.delete_service(self.worker_name)
        st1, msg1 = doc_client.delete_configs(configmap_name)
        msg = None if not(msg1 or msg2) else '{0}\n{1}'.format(msg1, msg2)
        return st1 and st2, msg

    def stop(self):
        if settings.ENABLE_K8S:
            return self._kube_stop()
        else:
            return self._docker_stop()

    @staticmethod
    def _extract_timestamp(log_line):
        """ Extract timestamp from log line and covert to seconds since the Epoch

        :param log_line: eg. "YYYY-MM-DD hh:mm:ss some message"
        :return seconds: return None if fail to match.
        """
        pattern = re.compile(r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s*\S*')
        match = pattern.match(log_line)
        if not match:
            return None
        datetime_str = match.group(1)
        seconds = time.mktime(time.strptime(datetime_str, "%Y-%m-%d %H:%M:%S"))
        return seconds

    def _kube_get_worker_log(self, since_seconds=None, follow=False, tail_lines=None):
        result, err = k8s_client.get_pod_log(
                            self.worker_name,
                            self.namespace,
                            since_seconds=since_seconds,
                            follow=follow,
                            tail_lines=tail_lines)
        return result if not err else err

    def _docker_get_worker_log(self, since_seconds=None, follow=False, tail_lines=None):
        result, err = doc_client.get_container_log(
                        self.worker_name,
                        since_seconds=since_seconds,
                        tail_lines=tail_lines)
        return result if not err else err

    def get_worker_log(self, since_seconds=None, follow=False, tail_lines=None):
        if settings.ENABLE_K8S:
            return self._kube_get_worker_log(
                            since_seconds=since_seconds,
                            follow=follow,
                            tail_lines=tail_lines)
        else:
            return self._docker_get_worker_log(
                            since_seconds=since_seconds,
                            tail_lines=tail_lines)

    def _k8s_get_worker_info(self):
        rt, err_msg = k8s_client.get_pod_status(self.worker_name, self.namespace)
        return rt.to_str(), err_msg

    def _docker_get_worker_info(self):
        rt, err_msg = doc_client.get_container_status(self.worker_name)
        return json.dumps(rt, indent=2), err_msg

    def get_worker_info(self):
        if settings.ENABLE_K8S:
            return self._k8s_get_worker_info()
        else:
            return self._docker_get_worker_info()

    def get_container_log_info(self):
        """ generate two url for PAI server to get container log infomation

        :return tuple: (readlong_url, loginfo_url) or None
        """
        if not hasattr(self, '_readlog_url'):
            pod_status, err = k8s_client.get_pod_status(self.worker_name, self.namespace)
            if err:
                return None
            host_ip = pod_status.host_ip
            container_id = pod_status.container_statuses[0].container_id \
                            .split('docker://')[-1]
            port = settings.LOG_SERVER_PORT
            readlog_prefix = settings.READLOG_URLPREFIX
            loginfo_prefix = settings.LOGINFO_URLPREFIX
            readlog_url = f"http://{host_ip}:{port}/{readlog_prefix}?filename={container_id}"
            loginfo_url = f"http://{host_ip}:{port}/{loginfo_prefix}?filename={container_id}"
            setattr(self, '_readlog_url', readlog_url)
            setattr(self, '_loginfo_url', loginfo_url)
        return (self._readlog_url, self._loginfo_url)

    def update_status(self, status, msg=''):
        # TODO: replace k8s status with status
        self.k8s_status = status
        self.save()

    def __str__(self):
        return self.worker_name

    def __unicode__(self):
        return self.worker_name

    class Meta:
        db_table = 'avesworker'
