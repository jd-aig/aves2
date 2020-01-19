import django_filters
from django.utils import timezone
from rest_framework import serializers

from .models import *

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = '__all__'


class K8SNamespaceSerializer(serializers.ModelSerializer):

    class Meta:
        model = K8SNamespace
        fields = '__all__'


class K8SStorageClassSerializer(serializers.ModelSerializer):

    class Meta:
        model = K8SStorageClass
        fields = '__all__'


class K8SPvcSerializer(serializers.ModelSerializer):

    class Meta:
        model = K8SPvc
        fields = '__all__'


class K8SPvcUserRelSerializer(serializers.ModelSerializer):

    class Meta:
        model = K8SPvcUserRel
        fields = '__all__'


class K8SResourceQuotaSerializer(serializers.ModelSerializer):

    class Meta:
        model = K8SResourceQuota
        fields = '__all__'
