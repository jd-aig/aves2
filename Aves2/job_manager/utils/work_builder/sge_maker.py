import os
from django.conf import settings

from .base_maker import BaseMaker
from .k8s_objects import (
    make_job, make_rc
)

K8S_NV_GPU_RES = settings.K8S_NV_GPU_RES

SGE_MASTER_DEFAULT_PORT = 2222
SGE_WORKER_DEFAULT_PORT = 2222


class K8sSGETrainMaker(BaseMaker):
    def __init__(self, *args, **kwargs):
        super(K8sSGETrainMaker, self).__init__(*args, **kwargs)

    def gen_k8s_worker_conf(self):
        """
        """
        if self.target_worker.avesrole == 'master':
            return self.gen_master_confs_for_k8s()
        elif self.target_worker.avesrole == 'exec':
            return self.gen_worker_confs_for_k8s()

    def gen_worker_confs_for_k8s(self):
        """
        """
        job_conf = make_job(
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

    def gen_master_confs_for_k8s(self):
        """
        """
        job_conf = make_job(
            name=self.target_worker.worker_name,
            namespace=self.target_worker.namespace,
            job_id=self.avesjob.merged_id,
            image=self.avesjob.image,
            args=self.gen_master_exec_commands(self.target_worker.role_index),
            ports=self.gen_master_ports(),
            envs=self.gen_envs(),
            grace_period=self._gen_grace_period(),
            resources=self.gen_resource_spec(),
            volume_mounts=self._gen_volume_mounts(),
            volumes=self._gen_volumes(self.target_worker.worker_name),
            affinity=self.gen_affinity(),
        )
        return job_conf

    def gen_worker_entrypoint(self, index):
        user_cmd = self._gen_init_cmds()
        user_cmd += ' --master_hosts ${MASTER_HOSTS} --exec_hosts ${EXEC_HOSTS} --role_name %s ' % 'exec'
        return user_cmd

    def gen_master_entrypoint(self, index):
        user_cmd = self._gen_init_cmds()
        user_cmd += ' --exec_hosts ${EXEC_HOSTS} --master_hosts ${MASTER_HOSTS} --role_name %s ' % 'master'
        user_cmd += self._gen_input_args()
        if self.avesjob.output_spec:
            user_cmd += self._gen_output_args()
        return user_cmd

    def gen_worker_ports(self):
        ports = self.target_worker.ports if self.target_worker.ports else [SGE_WORKER_DEFAULT_PORT]
        return ports

    def gen_master_ports(self):
        ports = self.target_worker.ports if self.target_worker.ports else [SGE_MASTER_DEFAULT_PORT]
        return ports

    def gen_ports(self):
        if self.target_worker.avesrole == 'master':
            return self.gen_master_ports()
        elif self.target_worker.avesrole == 'exec':
            return self.gen_worker_ports()

    def gen_master_env(self):
        port = self.target_worker.ports[0] if self.target_worker.ports else SGE_MASTER_DEFAULT_PORT
        value = ''
        for worker_i in self.target_worker.avesjob.k8s_worker.filter(avesrole='master'):
            value += '%s.%s:%s,' % (worker_i.worker_name,
                                    worker_i.namespace,
                                    port)
        value = value[0:-1]
        return {"name": "MASTER_HOSTS", "value": value}

    def gen_worker_env(self):
        port = self.target_worker.ports[0] if self.target_worker.ports else SGE_MASTER_DEFAULT_PORT
        value = ''
        for worker_i in self.target_worker.avesjob.k8s_worker.filter(avesrole='exec'):
            value += '%s.%s:%s,' % (worker_i.worker_name,
                                    worker_i.namespace,
                                    port)
        value = value[0:-1]
        return {"name": "EXEC_HOSTS", "value": value}

    def gen_envs(self):
        envs = super(K8sSGETrainMaker, self).gen_envs()
        if self.target_worker.avesrole == 'master':
            envs.append(self.gen_master_env())
        elif self.target_worker.avesrole == 'exec':
            envs.append(self.gen_worker_env())
        return envs

    def gen_worker_exec_commands(self, index):
        return self._gen_exec_commands_for_role('exec', index, self.gen_worker_entrypoint)

    def gen_master_exec_commands(self, index):
        return self._gen_exec_commands_for_role('master', index, self.gen_master_entrypoint)

