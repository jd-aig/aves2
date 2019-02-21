import os
from django.conf import settings

from .base_maker import BaseMaker
from .k8s_objects import (
    make_job, make_rc
)

PYTORCH_WORKER_DEFAULT_PORT = 2222
PYTORCH_MASTER_DEFAULT_PORT = 2222

INIT_CONTAINER_IMG = "ai-image.jd.com/library/aves:centos-7.4.1708_python-3.6.5_django-1.11.7"
INIT_SCRIPT_PATH = "http://ai-fileserver.jd.com/share/tools/aves/export_master_addr.py"
ENV_FILE_PATH = "/env/master_addr.env"
SHARED_VOLUME = "env-sharedir"


class K8sPyTorchTrainMaker(BaseMaker):
    def __init__(self, *args, **kwargs):
        super(K8sPyTorchTrainMaker, self).__init__(*args, **kwargs)

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
        master_worker = self.avesjob.k8s_worker.get(role_index=0)
        master_worker_name = master_worker.worker_name
        # should not depend on local output log here, remove it, add in StorageMixIn if needed
        """
        cmd += "python %s %s %s %s 2>&1 | tee %s_init_container.log && ( exit ${PIPESTATUS[0]} ) ;" % \
                (script, self.namespace, master_worker_name, ENV_FILE_PATH,
                os.path.join(runlogDir, tmstamp))
        """
        cmd += "python %s %s %s %s ;" % \
                (script, self.target_worker.namespace, master_worker_name, ENV_FILE_PATH)
        return [cmd]

    def _gen_worker_init_container_spec(self, index):
        # add init_container in non-master worker to prepare MASTER_ADDR
        if self.avesjob.is_distribute and index > 0:
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
            grace_period=self._gen_grace_period(),
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
        return self.avesjob.resource_spec['worker']['count']

    def _gen_dist_url(self):
        for name, value in self.avesjob.input_spec.items():
            filename = name
            if value['filename']:
                filename = os.path.join(name, value['filename'])
            args += ' --%s %s' % (name, os.path.join(CONTAINER_MOUNT_DIR, filename))
        input_count = len(self.avesjob.input_spec)
        if input_count < 1:
            raise Exception('At least one input args must be specified')
        url = "file://%s/%s" % (self.avesjob.merge_id)
        return 

    def gen_entrypoint(self, index):
        user_cmd = '%s %s' % (self.target_worker.entrypoint, ' '.join(self.target_worker.args))
        if self.avesjob.is_distribute:
            user_cmd += ' --rank %d --world-size %d' % (
                    index, int(self._gen_world_size()))
        user_cmd += self._gen_input_args()
        if self.avesjob.output_spec != {}:
            user_cmd += self._gen_output_args()

        return user_cmd

    def gen_master_worker_entrypoint(self, index):
        return self.gen_entrypoint(index)

    def gen_worker_entrypoint(self, index):
        cmd = "source %s; " % ENV_FILE_PATH
        cmd += self.gen_entrypoint(index)
        return cmd

    def gen_ports(self):
        ports = self.target_worker.ports if self.target_worker.ports else [PYTORCH_WORKER_DEFAULT_PORT]
        return ports

    def gen_worker_env(self):
        if not self.avesjob.is_distribute:
            return []

        roleSpec = self.avesjob.resource_spec['worker']
        env = [{
            "name": "MASTER_PORT",
            "value": str(roleSpec.get('port', PYTORCH_WORKER_DEFAULT_PORT))
            }]
        if self.target_worker.role_index == 0:
            env.append({
                "name": "MASTER_ADDR",
                "value": "127.0.0.1"
                })
        return env

    def gen_envs(self):
        envs = super(K8sPyTorchTrainMaker, self).gen_envs()
        envs.extend(self.gen_worker_env())
        return envs

    def gen_worker_exec_commands(self, index):
        if index == 0:
            return self._gen_exec_commands_for_role('worker', index, self.gen_master_worker_entrypoint)
        else:
            return self._gen_exec_commands_for_role('worker', index, self.gen_worker_entrypoint)

