from django.utils import timezone
from rest_framework import serializers

from .models import AvesJob, K8SWorker


class AvesJobSerializer(serializers.ModelSerializer):
    job_name = serializers.SerializerMethodField()

    class Meta:
        model = AvesJob
        fields = '__all__'

    def get_job_name(self, obj):
        return obj.job_name


class K8SWorkerSerializer(serializers.ModelSerializer):

    class Meta:
        model = K8SWorker
        fields = '__all__'
