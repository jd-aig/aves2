import os
from django.conf import settings

from .base_maker import BaseMaker
from .k8s_objects import (
    make_job, make_rc
)

K8S_NV_GPU_RES = settings.K8S_NV_GPU_RES

CAFFE_WORKER_DEFAULT_PORT = 2222


class K8sCaffeTrainMaker(BaseMaker):
    def __init__(self, *args, **kwargs):
        super(K8sCaffeTrainMaker, self).__init__(*args, **kwargs)

    def gen_k8s_worker_conf(self):
        """
        """
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
            ports=self.gen_ports(),
            envs=self.gen_envs(),
            resources=self.gen_resource_spec(),
            volume_mounts=self._gen_volume_mounts(),
            volumes=self._gen_volumes(self.target_worker.worker_name),
            affinity=self.gen_affinity()
        )
        return job_conf

    def gen_gpu(self):
        gpu_num = self.target_worker.gpu_request
        if not gpu_num:
            return ''
        else:
            gpu_arg = ','.join([str(i) for i in range(gpu_num)])
            return " --gpu %s" % gpu_arg

    def gen_worker_entrypoint(self, index):
        user_cmd = self._gen_init_cmds()
        user_cmd += self._gen_input_args()
        if not self.avesjob.output_spec:
            raise Exception('outputSpec is not defined')
        else:
            user_cmd += self._gen_output_args()

        user_cmd += self.gen_gpu()
        return user_cmd

    def gen_ports(self):
        ports = self.target_worker.ports if self.target_worker.ports else  [CAFFE_WORKER_DEFAULT_PORT]
        return ports

    def gen_worker_exec_commands(self, index):
        return self._gen_exec_commands_for_role('worker', index, self.gen_worker_entrypoint)

