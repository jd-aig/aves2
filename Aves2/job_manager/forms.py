from django.forms import ModelForm
from job_manager.models import AvesJob


class AvesJobForm(ModelForm):
    class Meta:
        model = AvesJob
        fields = (
            'job_id',
            'username',
            'namespace',
            'engine',
            'image',
            'storage_mode',
            'storage_config',
            'resource_spec',
            'package_uri',
            'input_spec',
            'output_spec',
            'envs',
            'log_dir'
        )
