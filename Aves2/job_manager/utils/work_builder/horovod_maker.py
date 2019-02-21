from .base_maker import BaseMaker
from .k8s_objects import (
    make_job, make_rc
)

K8S_NV_GPU_RES = 'nvidia.com/gpu'

HOROVOD_WORKER_DEFAULT_PORT = 22
HOROVOD_MASTER_DEFAULT_PORT = 22


class K8sHorovodTrainMaker(BaseMaker):
    def __init__(self, *args, **kwargs):
        super(K8sHorovodTrainMaker, self).__init__(*args, **kwargs)

    def gen_k8s_worker_conf(self):
        """
        """
        if self.target_worker.avesrole == 'master':
            return self.gen_master_confs_for_k8s()
        elif self.target_worker.avesrole == 'worker':
            return self.gen_worker_confs_for_k8s()

    def gen_master_confs_for_k8s(self):
        """
        """
        job_conf = make_job(
            name=self.target_worker.worker_name,
            namespace=self.target_worker.namespace,
            job_id=self.avesjob.merged_id,
            image=self.avesjob.image,
            args=self.gen_master_exec_commands(self.target_worker.role_index),
            ports=self.gen_ports(),
            envs=self.gen_envs(),
            grace_period=self._gen_grace_period(),
            resources=self.gen_resource_spec(),
            volume_mounts=self._gen_volume_mounts(),
            volumes=self._gen_volumes(self.target_worker.worker_name),
            affinity=self.gen_affinity(),
            init_containers=self.gen_master_init_container_spec(),
        )
        return job_conf

    def gen_worker_confs_for_k8s(self):
        """

        :return: list. confs for each master
        """
        rc_conf = make_rc(
            name=self.target_worker.worker_name,
            namespace=self.target_worker.namespace,
            job_id=self.avesjob.merged_id,
            image=self.avesjob.image,
            cmd=self.gen_worker_exec_commands(),
            args=[],
            ports=self.gen_ports(),
            envs=self.gen_envs(),
            grace_period=self._gen_grace_period(),
            resources=self.gen_resource_spec(),
            volume_mounts=self._gen_volume_mounts(),
            volumes=self._gen_volumes(self.target_worker.worker_name),
            affinity=self.gen_affinity(),
        )
        return rc_conf

    def gen_worker_entrypoint(self, index):
        user_cmd = "/usr/sbin/sshd -D"
        return user_cmd

    def gen_master_entrypoint(self, index):
        # 该方法仅会在master的K8SWorker实例中被执行
        # 因此直接使用self.target_worker
        entrypoint = self.target_worker.entrypoint
        args = self.target_worker.args
        user_cmd = '%s %s' % (entrypoint, ' '.join(args))

        master_count = int(self.avesjob.resource_spec['master']['count'])
        master_gpu = self.avesjob.resource_spec['master'][K8S_NV_GPU_RES]
        host_list = '%s.%s:%s' % (self.target_worker.worker_name, self.target_worker.namespace, master_gpu)
        np = master_count * master_gpu
        if self.avesjob.is_distribute:
            for worker_i in self.avesjob.k8s_worker.filter(avesrole='worker'):
                host_list += ',%s.%s:%s' % (worker_i.worker_name, worker_i.namespace, worker_i.gpu_request)
                np += worker_i.gpu_request

        user_cmd = "/usr/sbin/sshd ;sleep 3; mpiexec -np %d -H %s -enable-recovery --allow-run-as-root " \
                    "-x NCCL_DEBUG=INFO -x LD_LIBRARY_PATH -x PATH " \
                    "-mca plm_rsh_args \"-p %s\" %s" % (np, host_list, 
                    HOROVOD_MASTER_DEFAULT_PORT, user_cmd)
        user_cmd += self._gen_input_args()
        if self.avesjob.output_spec:
            user_cmd += self._gen_output_args()
        return user_cmd

    def gen_master_init_container_spec(self):
        if self.avesjob.is_distribute:
            conditions = ""
            for worker_i in self.avesjob.k8s_worker.filter(avesrole='worker'):
                conditions += " nc -z %s.%s:%s && " % (worker_i.worker_name,
                                                       worker_i.namespace,
                                                       HOROVOD_WORKER_DEFAULT_PORT)
            conditions = conditions[0:-3]
            cmd = "while true; do if %s ; then break; fi; sleep 10; done" % conditions
            return [{
                         "name": "wait-worker-ready",
                         "image":"ai-image.jd.com/library/busybox:latest",
                         "command": ["sh", "-c", cmd],
                         "resources": {
                             "requests": {
                                 "cpu": 2,
                                 "memory": "64Mi"
                             },
                             "limits": {
                                 "cpu": 2,
                                 "memory": "64Mi"
                             }
                         }
                     }]
        else:
            return []

    def gen_ports(self):
        ports = self.target_worker.ports if self.target_worker.ports else [HOROVOD_WORKER_DEFAULT_PORT]
        if HOROVOD_WORKER_DEFAULT_PORT not in ports:
            ports.append(HOROVOD_WORKER_DEFAULT_PORT)
        return ports

    def gen_master_env(self):
        value = ''
        for worker_i in self.target_worker.avesjob.k8s_worker.filter(avesrole='master'):
            value += '%s.%s:%s,' % (worker_i.worker_name,
                                    worker_i.namespace,
                                    HOROVOD_MASTER_DEFAULT_PORT)
        value = value[0:-1]
        return {"name": "MASTER_HOSTS", "value": value}

    def gen_worker_env(self):
        value = ''
        for worker_i in self.target_worker.avesjob.k8s_worker.filter(avesrole='worker'):
            value += '%s.%s:%s,' % (worker_i.worker_name,
                                    worker_i.namespace,
                                    HOROVOD_WORKER_DEFAULT_PORT)
        value = value[0:-1]
        return {"name": "WORKER_HOSTS", "value": value}

    def gen_envs(self):
        envs = super(K8sHorovodTrainMaker, self).gen_envs()
        if self.target_worker.avesrole == 'master':
            envs.append(self.gen_master_env())
        elif self.target_worker.avesrole == 'worker':
            envs.append(self.gen_worker_env())
        return envs

    def gen_worker_exec_commands(self):
        return ["/usr/sbin/sshd", "-D"]

    def gen_master_exec_commands(self, index):
        return self._gen_exec_commands_for_role('master', index, self.gen_master_entrypoint)

