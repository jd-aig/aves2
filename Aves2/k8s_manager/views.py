from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.decorators import api_view, action

from k8s_manager.models import *
from k8s_manager.serializer import *

from k8s_manager.filter import *


class UserViewSet(viewsets.ModelViewSet):
    """A ViewSet for User
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer


class K8SNamespaceViewSet(viewsets.ModelViewSet):
    """ A ViewSet for K8SNamespace
    """
    queryset = K8SNamespace.objects.all()
    serializer_class = K8SNamespaceSerializer


class K8SStorageClassViewSet(viewsets.ModelViewSet):
    """ A ViewSet for K8SStorageClass
    """
    queryset = K8SStorageClass.objects.all()
    serializer_class = K8SStorageClassSerializer


class K8SPvcViewSet(viewsets.ModelViewSet):
    """ A ViewSet for K8SPvc
    """
    queryset = K8SPvc.objects.all()
    serializer_class = K8SPvcSerializer
    filter_backends = (DjangoFilterBackend)
    filterset_fields = ['user']
    filter_class = K8SPvcFilter

class K8SPvcUserRelViewSet(viewsets.ModelViewSet):
    """A ViewSet for K8SPvcUserRel
    """
    queryset = K8SPvcUserRel.objects.all()
    serializer_class = K8SPvcUserRelSerializer


class K8SResourceQuotaViewSet(viewsets.ModelViewSet):
    """A ViewSet for K8SResourceQuota
    """
    queryset = K8SResourceQuota.objects.all()
    serializer_class = K8SResourceQuotaSerializer
