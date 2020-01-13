import os
import json

from django.conf import settings

from job_manager.utils import scripts_maker

# /export/AVES/src/ -- Project Code
# /export/AVES/data/mnist/ -- input data param (get from oss or mount)
# /export/AVES/output/  -- output data param

class BaseMaker:
    def __init__(self, avesjob, target_worker):
        self.avesjob = avesjob
        self.target_worker = target_worker

    @staticmethod
    def _get_storage_type(data_path):
        if data_path.startswith('s3://'):
            return 'oss'
        elif data_path.startswith('http://') or data_path.startswith('https://'):
            return 'web'
        else:
            raise Exception('Invalid data_path: {0}'.format(data_path))

    # def gen_confdata_data_params(self):
    #     configname = 'data-params'
    #     filename = 'data_params.json'

    #     data = []
    #     for k, v in self.avesjob.input_spec.items():
    #         dir_name = os.path.basename(v['path'].rstrip('/'))
    #         d = {
    #             'name': k,
    #             'type': 'input',
    #             'storage': self._get_storage_type(v['path']),
    #             'src': v['path'],
    #             'dst': '/AVES/data/{0}'.format(dir_name)
    #         }
    #         data.append(d)

    #     for k, v in self.avesjob.output_spec.items():
    #         dir_name = os.path.basename(v['path'].rstrip('/'))
    #         d = {
    #             'name': k,
    #             'type': 'output',
    #             'storage': self._get_storage_type(v['path']),
    #             'src': v['path'],
    #             'dst': '/AVES/data/{0}'.format(dir_name)
    #         }
    #         data.append(d)

    #     content = json.dumps(data, indent=4)
    #     return configname, {filename: content}

    def gen_data_params(self):
        data = []
        for k, v in self.avesjob.input_spec.items():
            dir_name = os.path.basename(v['path'].rstrip('/'))
            d = {
                'name': k,
                'type': 'input',
                'storage': self._get_storage_type(v['path']),
                'src': v['path'],
                'dst': '/AVES/data/{0}'.format(dir_name),
                'endpoint': self.avesjob.storage_config.get('config', {}).get('S3Endpoint'),
            }
            data.append(d)

        for k, v in self.avesjob.output_spec.items():
            dir_name = os.path.basename(v['path'].rstrip('/'))
            d = {
                'name': k,
                'type': 'output',
                'storage': self._get_storage_type(v['path']),
                'src': v['path'],
                'dst': '/AVES/output/{0}'.format(dir_name),
                'endpoint': self.avesjob.storage_config.get('config', {}).get('S3Endpoint'),
            }
            data.append(d)
        return data

    def gen_confdata_aves_scripts(self):
        configname = '{id}-aves-scripts'.format(id=self.target_worker.id)
        data = {}
        aves_run_content = scripts_maker.gen_aves_run_script(self.gen_data_params())
        data['aves_run.sh'] = aves_run_content
        data['aves_config_aws.sh'] = scripts_maker.gen_config_aws_script()
        data['aves_get_dist_envs.py'] = scripts_maker.gen_aves_dist_envs_script()
        data['aves_report.py'] = scripts_maker.gen_aves_report_script()
        return configname, data

    def gen_pod_labels(self):
        d = {
            'app': 'aves-training',
            'jobId': '%s' % self.avesjob.job_id,
            'workerId': '%s' % self.target_worker.id,
            'workerName': '%s' % self.target_worker.worker_name,
            'username': '%s' % self.target_worker.username,
        }
        return d

    def gen_image(self):
        return self.avesjob.image

    def gen_command(self):
        return ['bash', '/aves_bin/aves_run.sh']

    def _gen_aves_args(self):
        is_distribute = 'yes' if self.avesjob.is_distribute else 'no'
        args = ['--is_distributed', is_distribute]

        if self.avesjob.is_distribute:
            args.extend(['--distribute_type', self.avesjob.distribute_type])
        return args

    def _gen_training_args(self):
        args = []
        for arg_i in self.target_worker.args:
            for k, v in arg_i.items():
                if not k.startswith('--'):
                    k = '--{0}'.format(k)
                args.extend([k, v])
        return args

    def _gen_data_args(self):
        args = []
        # TODO: s3://xxx/dataset/mnist vs s3://xxx/dataset/mnist.tar
        for key, data in self.avesjob.input_spec.items():
            dir_name = os.path.basename(data['path'].rstrip('/'))
            args.extend([
                '--{0}'.format(key),
                '/AVES/data/{0}'.format(dir_name)
            ])

        for key, data in self.avesjob.output_spec.items():
            dir_name = os.path.basename(data['path'].rstrip('/'))
            args.extend([
                '--{0}'.format(key),
                '/AVES/output/{0}'.format(dir_name)
            ])
        return args

    def _gen_train_args(self):
        args = self.target_worker.entrypoint.split() + \
               self._gen_training_args() + \
               self._gen_data_args()
        args = ' '.join(args)
        return [args]

    def gen_args(self):
        args = self._gen_aves_args() + self._gen_train_args()
        return args

    # def _gen_volume_data_params(self):
    #     volume = {
    #         'name': 'data-params',
    #         'configMap': {
    #             'name': 'data_params.json'
    #         }
    #     }
    #     return volume

    # def _gen_volume_mount_data_params(self):
    #     mount = {
    #         'name': 'data-params',
    #         'mountPath': '/AVES/cfg/data-params/'
    #     }
    #     return mount

    def _gen_volume_aves_scripts(self):
        volume = {
            'name': 'aves-scripts',
            'configMap': {
                'name': '{id}-aves-scripts'.format(id=self.target_worker.id),
                'items': [
                    {
                        'key': 'aves_run.sh',
                        'path': 'aves_run.sh'
                    },
                    {
                        'key': 'aves_config_aws.sh',
                        'path': 'aves_config_aws.sh'
                    },
                    {
                        'key': 'aves_get_dist_envs.py',
                        'path': 'aves_get_dist_envs.py'
                    },
                    {
                        'key': 'aves_report.py',
                        'path': 'aves_report.py'
                    }
                ]
            }
        }
        return volume

    def _gen_volume_mount_aves_scripts(self):
        mount = {
            'name': 'aves-scripts',
            'mountPath': '/aves_bin/'
        }
        return mount

    def _gen_volume_shm(self):
        volume = {
            "name": "dshm",
            "emptyDir": {
                "medium": "Memory"
            }
        }
        return volume

    def _gen_volume_mount_shm(self):
        mount = {
            "name": "dshm",
            "mountPath": "/dev/shm"
        }
        return mount

    def _gen_volume_tz(self):
        volume = {
            "name": "tz-config",
            "hostPath": {
                "type": "File",
                "path": "/etc/localtime"
            }
        }
        return volume

    def _gen_volume_mount_tz(self):
        mount = {
            "name": "tz-config",
            "mountPath": "/etc/localtime",
            "readOnly": True
        }
        return mount

    def gen_volumes(self):
        volumes = [
            self._gen_volume_shm(),
            self._gen_volume_tz(),
            self._gen_volume_aves_scripts(),
        ]
        return volumes

    def gen_volume_mounts(self):
        mounts = [
            self._gen_volume_mount_shm(),
            self._gen_volume_mount_tz(),
            self._gen_volume_mount_aves_scripts(),
        ]
        return mounts

    def _env_var(self, key, value):
        return {
            'name': key,
            'value': value
        }

    def _gen_common_envs(self):
        envs = []
        envs.append(self._env_var('AVES_MAIN_NODE', str(self.target_worker.is_main_node)))
        envs.append(self._env_var('AVES_JOB_ID', str(self.avesjob.id)))
        envs.append(self._env_var('AVES_WORK_POD_ID', str(self.target_worker.id)))
        envs.append(self._env_var('AVES_WORK_USER', 'root'))
        envs.append(self._env_var('AVES_WORK_PASS', 'root'))
        envs.append(self._env_var('AVES_WORK_ROLE', self.target_worker.avesrole))
        envs.append(self._env_var('AVES_WORK_INDEX', str(self.target_worker.role_index)))
        envs.append(self._env_var('AVES_PROJ_SRC', self.avesjob.package_uri))
        return envs

    def _gen_api_envs(self):
        envs = []
        envs.append(self._env_var('AVES_API_HOST', settings.AVES_API_HOST))
        envs.append(self._env_var('AVES_API_JOB_DIST_ENVS_URL', 'aves_job/{id}/distribute_envs/'.format(id=self.avesjob.id)))
        envs.append(self._env_var('AVES_API_JOB_REPORT_URL', 'aves_job/{id}/finish_job/'.format(id=self.avesjob.id)))
        envs.append(self._env_var('AVES_API_JOB_STATUS_REPORT_URL', 'aves_job/{id}/change_status/'.format(id=self.avesjob.id)))
        envs.append(self._env_var('AVES_API_WORKER_STATUS_REPORT_URL', 'aves_worker/{id}/change_status/'.format(id=self.target_worker.id)))
        envs.append(self._env_var('AVES_API_TOKEN', self.avesjob.token))
        return envs

    def _gen_pai_oss_envs(self):
        envs = []
        if self.avesjob.storage_mode == 'OSSFile':
            envs.append(self._env_var('AVES_PAI_OSS_SEC_ID', settings.DEFAULT_S3_ACCESS_KEY_ID))
            envs.append(self._env_var('AVES_PAI_OSS_SEC_KEY', settings.DEFAULT_S3_SECRET_ACCESS_KEY))
            envs.append(self._env_var('AVES_PAI_OSS_END', settings.DEFAULT_S3_ENDPOINT))
            envs.append(self._env_var('AVES_ENABLE_OSS', 'yes'))
        else:
            envs.append(self._env_var('AVES_ENABLE_OSS', 'no'))
        return envs

    def _gen_user_oss_envs(self):
        envs = []
        if self.avesjob.storage_mode == 'OSSFile':
            envs.append(self._env_var(
                'AVES_USER_OSS_SEC_ID',
                self.avesjob.storage_config['config']['S3AccessKeyId']
            ))
            envs.append(self._env_var(
                'AVES_USER_OSS_SEC_KEY',
                self.avesjob.storage_config['config']['S3SecretAccessKey']
            ))
            envs.append(self._env_var(
                'AVES_USER_OSS_END',
                self.avesjob.storage_config['config']['S3Endpoint']
            ))
        return envs

    def gen_envs(self):
        envs = []
        envs.append(self._env_var('PYTHONUNBUFFERED', 'x'))
        envs.append(self._env_var('JOBID', self.avesjob.merged_id))
        envs += self._gen_common_envs()
        envs += self._gen_api_envs()
        envs += self._gen_pai_oss_envs()
        envs += self._gen_user_oss_envs()
        for k, v in self.avesjob.envs.items():
            envs.append(self._env_var(k, v))
        return envs

    def gen_resource_spec(self):
        resource = {
            'requests': {},
            'limits': {},
        }
        if self.target_worker.cpu_request:
            resource['requests']['cpu'] = self.target_worker.cpu_request
        if self.target_worker.cpu_limit:
            resource['limits']['cpu'] = self.target_worker.cpu_limit
        if self.target_worker.mem_request:
            resource['requests']['memory'] = '%sGi' % self.target_worker.mem_request
        if self.target_worker.mem_limit:
            resource['limits']['memory'] = '%sGi' % self.target_worker.mem_limit
        if self.target_worker.gpu_request:
            resource['requests']['nvidia.com/gpu'] = self.target_worker.gpu_request
            resource['limits']['nvidia.com/gpu'] = self.target_worker.gpu_request
        return resource

    def gen_affinity(self):
        roleName = self.target_worker.avesrole
        roleSpec = self.avesjob.resource_spec[roleName]

        if 'ScheduleStrategy' not in roleSpec:
            return {}
        strategy = roleSpec['ScheduleStrategy']
        if 'resourceLevel' not in strategy:
            raise Exception("missing resourceLevel in ScheduleStrategy")
        node_affinity = strategy['resourceLevel']
        if 'requiredSelector' not in node_affinity:
            raise Exception("missing requiredSelector in ScheduleStrategy")
        required_node_affinity = node_affinity['requiredSelector']
        if type(required_node_affinity) is not list:
            raise Exception("requiredSelector in ScheduleStrategy must be list[dict{},dict{},...] type")

        matchExpressions = []
        for item in required_node_affinity:
            if set(item.keys()) != set(['key', 'operator', 'values']):
                raise Exception('requiredSelector item keys must be [key, operator, values]')
            sub_expression = {'key': item['key'], 'operator': item['operator'], 'values': item['values']}
            matchExpressions.append(sub_expression)
        return {
                    'nodeAffinity': {
                        'requiredDuringSchedulingIgnoredDuringExecution': {
                            'nodeSelectorTerms': [{
                                'matchExpressions': matchExpressions
                            }]
                        }
                    }
                }


    def get_pod_manifest(self):
        pass

    def get_configmap_manifest(self):
        pass

    def get_svc_manifest(self):
        pass

    def get_ingress_manifest(self):
        pass

