from jsonschema import validate

from .job_schema import job_schema
from .data_schema import data_schema
from .worker_schema import worker_schema


def validate_job(job):
    try:
        validate(instance=job, schema=job_schema)

        # validate codeSpec
        data = job['codeSpec']
        validate(instance=data, schema=data_schema)

        # validate inputSpec
        for key, data in job['inputSpec'].items():
            validate(instance=data, schema=data_schema)

        # validate outputSpec
        for key, data in job['inputSpec'].items():
            validate(instance=data, schema=data_schema)

        # validate logDir
        data = job['logDir']
        validate(instance=data, schema=data_schema)

        # validate resourceSpec
        for key, data in job['resourceSpec'].items():
            validate(instance=data, schema=worker_schema)
    except Exception as e:
        return False, e

def trans_job_data(job):
    data = {}
    data['job_id'] = job['jobId']
    data['namespace'] = job['namespace']
    data['username'] = job['username']
    data['image'] = job['image']
    data['distribute_type'] = job.get('distributeType')
    data['is_distribute'] = True if data['distribute_type'] else False
    data['envs'] = job['envs']
    data['code_spec'] = job['codeSpec']
    data['input_spec'] = job['inputSpec']
    data['output_spec'] = job['outputSpec']
    data['log_dir'] = job['logDir']
    data['storage_mode'] = job['storageMode']

    data['resource_spec'] = {}
    for role, role_spec in job['resourceSpec'].items():
        if role == 'master':
            role = 'worker'
        role_spec['entry_point'] = role_spec['entryPoint']
        role_spec.pop('entryPoint')
        role_spec['gpu'] = role_spec['nvidia.com/gpu']
        role_spec.pop('nvidia.com/gpu')
        data['resource_spec'][role] = role_spec

    return data
