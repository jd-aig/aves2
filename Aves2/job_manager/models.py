import re
import os
import io
import requests
import logging
import time

from django.db import models
from django_mysql.models import JSONField
from django.conf import settings


logger = logging.getLogger('aves2')


def json_field_default():
    return {}


class Engine(models.Model):
    """ 机器学习/深度学习引擎框架
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=32, blank=False, null=False)

    class Meta:
        db_table = 'engine'


class AvesJob(models.Model):
    """
    """
    VALID_ENGINES = (
        'tensorflow',
        'pytorch',
        
    )

    STATUS_MAP = (
        ('NEW', '新建'),
        ('STARTING', '启动中'),
        ('PENDING', '等待中'),
        ('RUNNING', '运行中'),
        ('FINISHED', '已结束'),
        ('CANCELED', '已取消'),
    )

    id = models.AutoField(primary_key=True)
    job_id = models.IntegerField(blank=False, null=False, default=0)
    username = models.CharField(max_length=128, blank=False, null=False, default='')
    namespace = models.CharField(max_length=64, blank=False, null=False, default='default')
    merge_id = models.CharField(max_length=256, blank=False, null=False, default='')
    engine = models.ForeignKey('Engine', on_delete=models.CASCADE, blank=False, null=False)
    image = models.CharField(max_length=512, blank=False, null=False)
    resource_spec = JSONField(blank=False, default=json_field_default)
    running_envs = JSONField(blank=True, default=json_field_default)
    data_mode = models.CharField(max_length=32, blank=False, null=False, default='file')
    mount_node_storage = models.BooleanField(blank=True, null=False, default=False)
    input_spec = JSONField(blank=False, default=json_field_default)
    output_spec = JSONField(blank=False, default=json_field_default)
    status = models.CharField(max_length=16, blank=True, null=False, choices=STATUS_MAP, default='new')
    is_distribute = models.BooleanField(blank=True, null=False, default=True)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    def make_k8s_workers(self):
        k8s_workers = []
        self.status = 'STARTING'
        self.save()
        return k8s_workers

    class Meta:
        db_table = 'avesjob'


class K8SWorker(models.Model):
    """
    """
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=128, blank=False, null=False, default='')
    avesjob = models.ForeignKey('AvesJob', on_delete=models.CASCADE, blank=False, null=False)
    merge_id = models.CharField(max_length=256, blank=False, null=False, default='')
    avesrole = models.CharField(max_length=16, blank=False, null=False, default='worker')
    namespace = models.CharField(max_length=32, blank=False, null=False)
    k8s_status = models.CharField(blank=True, null=True, default='')
    worker_json = JSONField(blank=True, null=True, default=json_field())
    service_json = JSONField(blank=True, null=True, default=json_field())
    ingress_json = JSONField(blank=True, null=True, default=json_field())
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    def start(self):
        pass

    def stop(self):
        pass

    class Meta:
        db_table = 'k8sworker'

