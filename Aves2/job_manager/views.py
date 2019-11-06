import os
import time
import datetime
import logging

from django.shortcuts import render
from django.conf import settings

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.decorators import api_view, list_route, detail_route, action

from job_manager.models import AvesJob, K8SWorker
from job_manager.serializer import AvesJobSerializer
from job_manager.forms import AvesJobForm
from job_manager.tasks import startup_avesjob, cancel_avesjob

from kubernetes_client.client import k8s_client

logger = logging.getLogger('aves2')


class AvesJobViewSet(viewsets.ModelViewSet):
    """ A ViewSet for AvesJob
    """
    queryset = AvesJob.objects.all()
    serializer_class = AvesJobSerializer

    @action(detail=True, methods=['get'])
    def start_job(self, request, pk):
        avesjob = self.get_object()
        if not avesjob.start():
            raise APIException(detail='Fail to start job {0}'.format(avesjob), code=400)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def distribute_envs(self, request, pk):
        avesjob = self.get_object()
        namespace = avesjob.namespace
        selector = {'jobId': avesjob.job_id}

        rt, data = k8s_client.get_namespaced_pod_list(namespace, selector=selector)
        if not rt:
            logger.error('Fail to get_namespaced_pod_list: namespace {0}, selector {1}. msg: {3}'.format(namespace, selector, data))
            raise APIException(detail='Fail to get job info', code=500)

        if not data or not len(data) == avesjob.k8s_worker.count():
            raise APIException(detail='workers are not ready', code=400)

        for pod in data:
            if not (hasattr(pod.status, 'phase') and pod.status.phase == 'Running'):
                raise APIException(detail='worker {0} is not ready'.format(pod.metadata.name), code=400)

        envs = avesjob.get_dist_envs()
        return Response(envs)

    @action(detail=True, methods=['get'])
    def finish_job(self, request, pk):
        """
        """
        avesjob = self.get_object()
        namespace = avesjob.namespace

        if not avesjob.status == 'RUNNING':
            raise APIException(detail='Job is not running', code=400)
        try:
            status = request.GET['status']
            msg = request.GET['msg']
        except Exception:
            logger.error('Invalid request data', exc_info=True)
            raise APIException(detail='Invalid request data: status and msg are required', code=400)
        # update status
        avesjob.status = status
        avesjob.save()
        # clean k8s resource
        avesjob.clean()

    @action(detail=True, methods=['get'])
    def cancel_job(self, request, pk):
        """ Cancel avesjob
        """
        avesjob = self.get_object()
        avesjob.cancel()

        return Response(status=status.HTTP_200_OK)
