import os
from django.conf import settings

from .base_maker import BaseMaker
from .k8s_objects import (
    make_job, make_rc, make_pod
)

K8S_NV_GPU_RES = settings.K8S_NV_GPU_RES

TF_WORKER_DEFAULT_PORT = 2222
TF_PS_DEFAULT_PORT = 2222


class K8sTensorFlowTrainMaker(BaseMaker):
    def __init__(self, *args, **kwargs):
        super(K8sTensorFlowTrainMaker, self).__init__(*args, **kwargs)

    def gen_k8s_worker_conf(self):
        """
        """
        if self.target_worker.avesrole == 'ps':
            return self.gen_ps_confs_for_k8s()
        elif self.target_worker.avesrole == 'worker':
            return self.gen_worker_confs_for_k8s()

    def gen_worker_confs_for_k8s(self):
        """
        """
        job_conf = make_pod(
            name=self.target_worker.worker_name,
            namespace=self.target_worker.namespace,
            job_id=self.avesjob.merged_id,
            image=self.avesjob.image,
            args=self.gen_worker_exec_commands(self.target_worker.role_index),
            ports=self.gen_worker_ports(),
            envs=self.gen_envs(),
            grace_period=self._gen_grace_period(),
            resources=self.gen_resource_spec(),
            volume_mounts=self._gen_volume_mounts(),
            volumes=self._gen_volumes(self.target_worker.worker_name),
            affinity=self.gen_affinity(),
        )
        return job_conf

    def gen_ps_confs_for_k8s(self):
        """
        """
        rc_conf = make_pod(
            name=self.target_worker.worker_name,
            namespace=self.target_worker.namespace,
            job_id=self.avesjob.merged_id,
            image=self.avesjob.image,
            args=self.gen_ps_exec_commands(self.target_worker.role_index),
            ports=self.gen_ps_ports(),
            envs=self.gen_envs(),
            grace_period=self._gen_grace_period(),
            resources=self.gen_resource_spec(),
            volume_mounts=self._gen_volume_mounts(),
            volumes=self._gen_volumes(self.target_worker.worker_name),
            affinity=self.gen_affinity(),
        )
        return rc_conf

    def gen_worker_entrypoint(self, index):
        entrypoint = self.target_worker.entrypoint
        args = self.target_worker.args
        user_cmd = '%s %s' % (entrypoint, ' '.join(args))
        if self.avesjob.is_distribute:
            user_cmd += ' --ps_hosts ${PS_HOSTS} --worker_hosts ${WORKER_HOSTS} --job_name %s --task_index %d' % (
            'worker', self.target_worker.role_index)
        user_cmd += self._gen_input_args()
        if self.avesjob.output_spec:
            user_cmd += self._gen_output_args()
        return user_cmd

    def gen_ps_entrypoint(self, index):
        entrypoint = self.target_worker.entrypoint
        args = self.target_worker.args
        user_cmd = '%s %s' % (entrypoint, ' '.join(args))
        if self.avesjob.is_distribute:
            user_cmd += ' --ps_hosts ${PS_HOSTS} --worker_hosts ${WORKER_HOSTS} --job_name %s --task_index %d' % (
                'ps', self.target_worker.role_index)
        user_cmd += self._gen_input_args()
        if self.avesjob.output_spec:
            user_cmd += self._gen_output_args()
        return user_cmd

    def gen_ps_ports(self):
        ports = self.target_worker.ports if self.target_worker.ports else [TF_PS_DEFAULT_PORT]
        return ports

    def gen_worker_ports(self):
        ports = self.target_worker.ports if self.target_worker.ports else [TF_WORKER_DEFAULT_PORT]
        return ports

    def gen_ports(self):
        if self.target_worker.avesrole == 'ps':
            return self.gen_ps_ports()
        elif self.target_worker.avesrole == 'worker':
            return self.gen_worker_ports()

    def gen_ps_env(self):
        port = self.target_worker.ports[0] if self.target_worker.ports else TF_PS_DEFAULT_PORT
        value = ''
        for worker_i in self.target_worker.avesjob.k8s_worker.filter(avesrole='ps'):
            value += '%s.%s:%s,' % (worker_i.worker_name,
                                    worker_i.namespace,
                                    port)
        value = value[0:-1]
        return {"name": "PS_HOSTS", "value": value}

    def gen_worker_env(self):
        port = self.target_worker.ports[0] if self.target_worker.ports else TF_WORKER_DEFAULT_PORT
        value = ''
        for worker_i in self.target_worker.avesjob.k8s_worker.filter(avesrole='worker'):
            value += '%s.%s:%s,' % (worker_i.worker_name,
                                    worker_i.namespace,
                                    port)
        value = value[0:-1]
        return {"name": "WORKER_HOSTS", "value": value}

    def gen_envs(self):
        envs = super(K8sTensorFlowTrainMaker, self).gen_envs()
        if self.target_worker.avesrole == 'ps':
            envs.append(self.gen_ps_env())
        elif self.target_worker.avesrole == 'worker':
            envs.append(self.gen_worker_env())
        return envs

    def gen_worker_exec_commands(self, index):
        return self._gen_exec_commands_for_role('worker', index, self.gen_worker_entrypoint)

    def gen_ps_exec_commands(self, index):
        return self._gen_exec_commands_for_role('ps', index, self.gen_ps_entrypoint)

