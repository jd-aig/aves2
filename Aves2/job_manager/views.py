import os
import time
import datetime
import logging

from django.shortcuts import render
from django.conf import settings

from rest_framework import mixins
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.decorators import api_view, list_route, detail_route, action

from job_manager.models import AvesJob, K8SWorker
from job_manager.serializer import AvesJobSerializer, K8SWorkerSerializer
from job_manager.forms import AvesJobForm
from job_manager.tasks import startup_avesjob, cancel_avesjob

from kubernetes_client.client import k8s_client

logger = logging.getLogger('aves2')


class AvesWorkerViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """ A ViewSete for AvesWorker(K8SWorker)
    """
    serializer_class = K8SWorkerSerializer

    def get_queryset(self):
        if self.request.user.is_active and self.request.user.is_superuser:
            return K8SWorker.objects.all()
        else:
            return K8SWorker.objects.all().filter(username=self.request.user.username)

    @action(detail=True, methods=['get'])
    def change_status(self, request, pk):
        worker = self.get_object()
        try:
            worker_status = request.GET['status']
            msg = request.GET.get('msg', '')
            logger.info(f'{worker}: worker status changed. status: {worker_status} msg: {msg}')
        except Exception:
            logger.error('Invalid request data', exc_info=True)
            raise APIException(detail='Invalid request data: status is required', code=400)

        worker.update_status(worker_status, msg)
        # TODO: update job status after check all worker
        return Response(status=status.HTTP_200_OK)


class AvesJobViewSet(viewsets.ModelViewSet):
    """ A ViewSet for AvesJob
    """
    serializer_class = AvesJobSerializer

    def get_queryset(self):
        if self.request.user.is_active and self.request.user.is_superuser:
            return AvesJob.objects.all()
        else:
            return AvesJob.objects.all().filter(username=self.request.user.username)

    def create(self, request, *args, **kwargs):
        user = request.user
        if not request.data.get('username'):
            request.data['username'] = user.username
        elif request.data['username'] != user.username and not user.is_superuser:
            return Response(status=status.status.HTTP_403_FORBIDDEN, headers=headers)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['get'])
    def start_job(self, request, pk):
        avesjob = self.get_object()
        if avesjob.status not in ['NEW', 'FINISHED', 'FAILURE', 'CANCELED']:
            err_msg = 'job is {0}'.format(avesjob.status)
            raise APIException(detail=err_msg)

        avesjob.update_status('STARTING', '')
        rt, err_msg = avesjob.start()
        if not rt:
            avesjob.update_status('FAILURE', err_msg)
            raise APIException(
                    detail='Fail to start job {0}. {1}'\
                           .format(avesjob, err_msg),
                    code=400)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def distribute_envs(self, request, pk):
        avesjob = self.get_object()
        namespace = avesjob.namespace
        selector = {'jobId': avesjob.job_id}

        data, msg = k8s_client.get_namespaced_pod_list(namespace, selector=selector)
        if not data:
            logger.error('Fail to get_namespaced_pod_list: namespace {0}, selector {1}. msg: {3}'.format(namespace, selector, msg))
            raise APIException(detail='Fail to get job info', code=500)

        if not data or not len(data) == avesjob.k8s_worker.count():
            raise APIException(detail='workers are not ready', code=400)

        for pod in data:
            if not (hasattr(pod.status, 'phase') and pod.status.phase == 'Running'):
                raise APIException(detail='worker {0} is not ready'.format(pod.metadata.name), code=400)

        envs = avesjob.get_dist_envs()
        return Response(envs)

    @action(detail=True, methods=['get'])
    def clean_job(self, request, pk):
        """
        """
        avesjob = self.get_object()
        namespace = avesjob.namespace

        avesjob.clean_work(force=True)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def finish_job(self, request, pk):
        """
        """
        avesjob = self.get_object()
        namespace = avesjob.namespace

        if not avesjob.status == 'RUNNING':
            logger.error(f'{avesjob}: try to stop a non-running job')
            raise APIException(detail='Job is not running', code=400)
        try:
            job_status = request.GET['status']
            msg = request.GET['msg']
            logger.info(f'{avesjob}: job finished. status: {job_status} msg: {msg}')
        except Exception:
            logger.error('Invalid request data', exc_info=True)
            raise APIException(detail='Invalid request data: status and msg are required', code=400)
        # update status
        avesjob.update_status(job_status)
        # clean k8s resource
        avesjob.clean_work()
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def cancel_job(self, request, pk):
        """ Cancel avesjob
        """
        avesjob = self.get_object()
        avesjob.cancel()
        avesjob.update_status('CANCELED')
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def change_status(self, request, pk):
        avesjob = self.get_object()
        try:
            job_status = request.GET['status']
            msg = request.GET.get('msg', '')
            logger.info(f'{avesjob}: worker status changed. status: {job_status} msg: {msg}')
        except Exception:
            logger.error('Invalid request data', exc_info=True)
            raise APIException(detail='Invalid request data: status is required', code=400)

        avesjob.update_status(job_status, msg)
        return Response(status=status.HTTP_200_OK)
