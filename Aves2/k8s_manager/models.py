import re
import os
import io
import copy
import time
import logging
import requests
from collections import defaultdict

from django.db import models
from django.conf import settings
from django_mysql.models import JSONField

from kubernetes_client.k8s_objects import *
from kubernetes_client.client import k8s_client

logger = logging.getLogger('aves2')

class User(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=128, blank=False, null=False, default='')

    def __str__(self):
        return self.username

    class Meta:
        db_table = "user"


class K8SNamespace(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128, blank=False, null=False, default='')
    jd_group = models.CharField(max_length=128, blank=True, null=False, default='')
    jd_group_cn = models.CharField(max_length=128, blank=True, null=False, default='')

    def delete(self, *args, **kwargs):
        api_response, err_msg = k8s_client.delete_namespace(self.name)
        if err_msg is not None:
            return err_msg
        return super(K8SNamespace, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        api_response, err_msg = k8s_client.create_namespace(self.name)
        if err_msg is not None:
            return err_msg
        return super(K8SNamespace, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'k8s_namespace'


class K8SStorageClass(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128, blank=False, null=False, default='')
    note = models.CharField(max_length=128, blank=True, null=False, default='')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'k8s_storage_class'


class K8SPvc(models.Model):
    ACCESS_MODE = (
        ('ReadWriteMany', '可读写多次'),
        ('ReadWriteOnce', '可读写一次'),
    )

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128, blank=False, null=False, default='')
    namespace = models.ForeignKey('K8SNamespace', on_delete=models.CASCADE, related_name='k8s_pvc_namespace')
    storageclass = models.ForeignKey('K8SStorageClass', on_delete=models.CASCADE, related_name='k8s_storage_class')
    size = models.IntegerField(blank=False, null=False, default=0)  # Mi
    owner = models.ForeignKey('User', on_delete=models.CASCADE, related_name='k8s_owner')
    user = models.ManyToManyField(User, through='K8SPvcUserRel', related_name="k8s_user")
    mount_path = models.CharField(max_length=32, blank=False, null=False, default='/mnt/')
    access_mode = models.CharField(max_length=32, blank=True, null=True, choices=ACCESS_MODE)
    

    def save(self, *args, **kwargs):
        pvc = make_pvc(
            name=self.name,
            storage_class=self.storageclass.name,
            access_modes=[self.access_mode],
            storage=str(self.size) + "Mi",
        )
        
        api_response, err_msg = k8s_client.create_namespaced_pvc(pvc, self.namespace.name)
        if err_msg is not None:
            print(self.namespace)
            print(err_msg)
            return err_msg
        result = super(K8SPvc, self).save(*args, **kwargs)

        user_rel = K8SPvcUserRel(user=self.owner, pvc=self, access_mode=self.access_mode)
        user_rel.save()
        return result

    def delete(self, *args, **kwargs):
        api_response, err_msg = k8s_client.delete_namespaced_pvc(self.name, self.namespace.name)
        if err_msg is not None:
            return err_msg
        return super(K8SPvc, self).delete(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'k8s_pvc'


class K8SPvcUserRel(models.Model):
    ACCESS_MODE = (
        ('ReadWriteMany', '可读写多次'),
        ('ReadWriteOnce', '可读写一次'),
    )

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='user')
    pvc = models.ForeignKey('K8SPvc', on_delete=models.CASCADE, related_name='k8s_pvc')
    access_mode = models.CharField(max_length=32, blank=True, null=True, choices=ACCESS_MODE)

    class Meta:
        db_table = 'k8s_pvc_user_rel'

    def __str__(self):
        return "user: " + self.user.username + "pvc: " + self.pvc.name


class K8SResourceQuota(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128, blank=False, null=False, default='')
    namespace = models.ForeignKey('K8SNamespace', on_delete=models.CASCADE, related_name='k8s_resource_quota_namespace')
    limits_cpu = models.IntegerField(blank=False, null=False, default=0)
    limits_memory = models.IntegerField(blank=False, null=False, default=0)   # Mi
    requests_cpu = models.IntegerField(blank=False, null=False, default=0)
    requests_memory = models.IntegerField(blank=False, null=False, default=0)

    def save(self, *args, **kwargs):
        resource_quota = make_resource_quota(name=self.name,
                                             namespace=self.namespace.name,
                                             limits_cpu=self.limits_cpu,
                                             limits_memory=self.limits_memory,
                                             requests_cpu=self.requests_cpu,
                                             requests_memory=self.requests_memory)
        api_response, err_msg = k8s_client.create_namespaced_resource_quota(resource_quota, self.namespace.name)
        if err_msg is not None:
            return err_msg
        return super(K8SResourceQuota, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        api_response, err_msg = k8s_client.delete_namespaced_resource_quota(self.name, self.namespace.name)
        if err_msg is not None:
            return err_msg
        return super(K8SResourceQuota, self).delete(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "k8s_resource_quota"
