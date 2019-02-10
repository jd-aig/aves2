from .k8s_objects import (
    make_job, make_rc, make_ingress, make_k8s_ports, make_svc
)


class BaseMaker:
    def __init__(self, avesjob, target_worker):
        self.avesjob = avesjob
        self.target_worker = target_worker

    def gen_k8s_worker_conf(self):
        raise Exception('Not Implemented')

    def gen_k8s_svc_conf(self):
        svc_conf = make_svc(
            name=self.target_worker.worker_name,
            job_id=self.avesjob.merged_id,
            ports=self.gen_ports()
        )
        return svc_conf

    def _gen_input_args(self):
        return self._gen_args_from_dict(self.avesjob.input_spec)

    def _gen_output_args(self):
        return self._gen_args_from_dict(self.avesjob.output_spec)

    def _gen_exec_commands_for_role(self, avesrole, role_index, entrypoint_func):
        args = self._gen_workspace_prepare_cmd(avesrole, role_index)
        args += self._gen_pre_exec_cmd()
        args += self._gen_exec_cmd(avesrole, role_index, entrypoint_func)
        args += self._gen_post_exec_cmd()
        return [args.strip()]

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
            resource['requests']['mem'] = '%sGi' % self.target_worker.mem_request
        if self.target_worker.mem_limit:
            resource['limits']['mem'] = '%sGi' % self.target_worker.mem_limit
        if self.target_worker.gpu_request:
            resource['requests']['nvidia.com/gpu'] = self.target_worker.gpu_request
            resource['limits']['nvidia.com/gpu'] = self.target_worker.gpu_request
        return resource

    def _env_var(self, key, value):
        return {
            'name': key,
            'value': value
        }

    def gen_envs(self):
        envs = []
        envs.append(self._env_var('PYTHONUNBUFFERED', 'x'))
        envs.append(self._env_var('JOBID', self.avesjob.merged_id))
        envs += self._gen_storage_env()
        for k, v in self.avesjob.envs.items():
            envs.append(self._env_var(k, v))
        return envs

    def _gen_init_cmds(self):
        return '%s %s' % (self.target_worker.entrypoint, ' '.join(self.target_worker.args))

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

