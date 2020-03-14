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


class WorkerLogSerializer(serializers.ModelSerializer):
    readlog_url = serializers.SerializerMethodField()
    loginfo_url = serializers.SerializerMethodField()
    roleId = serializers.SerializerMethodField()
    pod_name = serializers.SerializerMethodField()

    class Meta:
        model = K8SWorker
        fields = ('pod_name', 'readlog_url', 'loginfo_url', 'roleId')

    def get_pod_name(self, obj):
        return obj.worker_name

    def get_readlog_url(self, obj):
        url_info = obj.get_container_log_info()
        if not url_info:
            return ''
        else:
            return url_info[0]

    def get_loginfo_url(self, obj):
        url_info = obj.get_container_log_info()
        if not url_info:
            return ''
        else:
            return url_info[1]

    def get_roleId(self, obj):
        return obj.role_index
