import os
from django.conf import settings

from .base_maker import BaseMaker
from .k8s_objects import (
    make_job, make_rc
)

CONTAINER_WORKSPACE = settings.CONTAINER_WORKSPACE
K8S_NV_GPU_RES = settings.K8S_NV_GPU_RES

CAFFEMPI_WORKER_DEFAULT_PORT = 22

INIT_CONTAINER_IMG = "ai-image.jd.com/library/aves:centos-7.4.1708_python-3.6.5_django-1.11.7"
INIT_SCRIPT_PATH = "http://ai-fileserver.jd.com/share/tools/aves/export_hosts.py"
ENV_FILE_PATH = "/env/hosts.env"
SHARED_VOLUME = "env-sharedir"


class K8sCaffeMpiTrainMaker(BaseMaker):
    def __init__(self, *args, **kwargs):
        super(K8sCaffeMpiTrainMaker, self).__init__(*args, **kwargs)

    def gen_k8s_worker_conf(self):
        """
        """
        return self.gen_worker_confs_for_k8s()

    def _gen_sharedir_volume_mount(self):
        env_dir = os.path.dirname(ENV_FILE_PATH) 
        return {"name": SHARED_VOLUME, "mountPath": env_dir}

    def _gen_sharedir_volume(self):
        return {"name": SHARED_VOLUME, "emptyDir": {}}

    def _gen_init_container_volumemounts(self):
        mounts = []
        mounts.append(self._gen_sharedir_volume_mount())
        #mounts.append(self._gen_volume_mounts_for_runlog())
        return mounts

    def _gen_exec_commands_for_init_container(self, index):
        #runlogDir, tmstamp = self._gen_runlogdir_and_tmstamp('worker', index)
        #cmd = "mkdir -p %s; wget -q %s; " % (runlogDir, INIT_SCRIPT_PATH)
        cmd = "wget -q %s; " % INIT_SCRIPT_PATH
        script = os.path.basename(INIT_SCRIPT_PATH)
        worker_count = self._gen_world_size()
        # should not depend on local output log here, remove it, add in StorageMixIn if needed
        """
        cmd += "python %s %s %s %d %s 2>&1 | tee %s_init_container.log && ( exit ${PIPESTATUS[0]} ) ;" % \
                (script, self.namespace, self.jobId, worker_count, ENV_FILE_PATH,
                os.path.join(runlogDir, tmstamp))
        """
        cmd += "python %s %s %s %d %s ;" % \
                (script, self.target_worker.namespace, self.avesjob.merged_id, worker_count, ENV_FILE_PATH)
        return [cmd]

    def _gen_worker_init_container_spec(self, index):
        # add init_container in non-master worker to prepare MASTER_ADDR
        if index == 0:
            conf = [{
                "name": "prepare-env",
                "image": INIT_CONTAINER_IMG,
                "command": ["/bin/sh", "-c"],
                "args": self._gen_exec_commands_for_init_container(index),
                "volumeMounts": self._gen_init_container_volumemounts(),
                "resources": {
                    "requests": {
                        "cpu": 2,
                        "memory": "512Mi"
                        },
                    "limits": {
                        "cpu": 2,
                        "memory": "512Mi"
                        }
                    }
                }]
            return conf
        else:
           return []

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
            volume_mounts=self.gen_worker_volume_mounts(),
            volumes=self.gen_worker_volumes(),
            affinity=self.gen_affinity(),
            init_containers=self._gen_worker_init_container_spec(self.target_worker.role_index),
        )
        return job_conf

    def gen_worker_volume_mounts(self):
        mounts = self._gen_volume_mounts()
        mounts.append(self._gen_sharedir_volume_mount())
        return mounts

    def gen_worker_volumes(self):
        volumes = self._gen_volumes(self.target_worker.worker_name)
        volumes.append(self._gen_sharedir_volume())
        return volumes

    def _gen_world_size(self):
        return int(self.avesjob.resource_spec['worker']['count'])

    def _gen_wrapper_command(self):
        entrypoint = self.target_worker.entrypoint
        args = self.target_worker.args
        wrap_cmd = '%s %s ' % (entrypoint, ' '.join(args))
        wrap_cmd += self._gen_input_args()
        if self.avesjob.output_spec: 
            wrap_cmd += self._gen_output_args()
        wrap_cmd += self.gen_gpu()
        return wrap_cmd

    def gen_gpu(self):
        gpu_num = self.target_worker.gpu_request
        if not gpu_num:
            return ''
        else:
            gpu_arg = ','.join([str(i) for i in range(gpu_num)])
            return " --gpu %s" % gpu_arg

    def gen_master_worker_entrypoint(self, index):
        user_cmd = "source %s; " % ENV_FILE_PATH
        host = "$HOSTS"
        user_cmd += 'mpirun -host %s -mca btl_openib_want_cuda_gdr 1 -mca io ompio -np %s -npernode 1 -wdir %s ' % \
                (host, self._gen_world_size(), CONTAINER_WORKSPACE)
        user_cmd += self._gen_wrapper_command()
        return user_cmd

    def gen_worker_entrypoint(self, index):
        user_cmd = "/usr/sbin/sshd -D"
        return user_cmd

    def gen_ports(self):
        ports = self.target_worker.ports if self.target_worker.ports else [CAFFEMPI_WORKER_DEFAULT_PORT]
        if CAFFEMPI_WORKER_DEFAULT_PORT not in ports:
            ports.append(CAFFEMPI_WORKER_DEFAULT_PORT)
        return ports

    def gen_worker_exec_commands(self, index):
        if index == 0:
            return self._gen_exec_commands_for_role('worker', index, self.gen_master_worker_entrypoint)
        else:
            return self._gen_exec_commands_for_role('worker', index, self.gen_worker_entrypoint)


