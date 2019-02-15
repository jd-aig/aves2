from django.forms import ModelForm
from job_manager.models import AvesJob


class AvesJobForm(ModelForm):
    class Meta:
        model = AvesJob
        fields = (
            'job_id', 'username', 'namespace', 'engine', 'image', 'resource_spec', 'envs', 'input_spec', 'output_spec', 'log_dir', 'package_uri', 'storage_config'
        )
