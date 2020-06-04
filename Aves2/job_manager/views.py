import os
import time
import datetime
import logging

from django.http import StreamingHttpResponse, HttpResponse
from django.shortcuts import render
from django.conf import settings

from rest_framework import mixins
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.decorators import api_view, list_route, detail_route, action

from job_manager.models import AvesJob, AvesWorker
from job_manager.serializer import AvesJobSerializer, AvesWorkerSerializer, WorkerLogSerializer
from job_manager import tasks
from job_manager.aves2_schemas import validate_job, trans_job_data

from kubernetes_client.client import k8s_client

logger = logging.getLogger('aves2')


def obtain_post_data(request):
    # log_request_record(request)
    data = request.POST.copy()
    if data is not None:
        if data == {}:
            data = json.loads(request.body.decode('utf-8'))
    logger.info(data)
    return data


class AvesWorkerViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """ A ViewSete for AvesWorker
    """
    serializer_class = AvesWorkerSerializer

    def get_queryset(self):
        if self.request.user.is_active and self.request.user.is_superuser:
            return AvesWorker.objects.all()
        else:
            return AvesWorker.objects.all().filter(username=self.request.user.username)

    @action(detail=True, methods=['get'])
    def logs(self, request, pk):
        def gen_log(logs):
            for line in logs.splitlines():
                yield '%s\r\n' % line

        worker = self.get_object()
        # TODO: support query params '?tail_lines=100'
        rt = worker.get_worker_log(tail_lines=2000)
        return StreamingHttpResponse(gen_log(rt), content_type="text/plain")

    @action(detail=True, methods=['get'])
    def worker_info(self, request, pk):
        worker = self.get_object()
        rt, err_msg = k8s_client.get_pod_status(worker.worker_name, worker.namespace)
        if not err_msg:
            data = rt.to_str()
            return HttpResponse(data, content_type="text/plain")
        else:
            data = {'error_msg': err_msg}
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

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

        if not user.is_superuser:
            namespace = user.groups.all()[0].name
            request.data['namespace'] = namespace

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        tasks.start_avesjob.delay(serializer.data['id'])
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        instance.clean_work(force=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def start_job(self, request, pk):
        avesjob = self.get_object()
        if not avesjob.ready_to_run:
            err_msg = 'job is {0}'.format(avesjob.status)
            raise APIException(detail=err_msg)

        avesjob.update_status('STARTING', '')
        rt, err_msg = avesjob.start()
        if not rt:
            avesjob.update_status('FAILURE', err_msg)
            raise APIException(
                    detail='Fail to start job {0}. {1}'
                           .format(avesjob, err_msg),
                    code=400)
        # TODO: report avesjob status: starting
        # _report_avesjob_status(avesjob.merged_id, "STARTING")
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def distribute_envs(self, request, pk):
        avesjob = self.get_object()
        namespace = avesjob.namespace
        selector = {'avesJobId': avesjob.id}

        data, msg = k8s_client.get_namespaced_pod_list(namespace, selector=selector)
        if not data:
            logger.error('Fail to get_namespaced_pod_list: namespace {0}, selector {1}. msg: {2}'.format(namespace, selector, msg))
            raise APIException(detail='Fail to get job info', code=500)

        if not data or not len(data) == avesjob.aves_worker.count():
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
        # TODO: report status
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

    @action(detail=True, methods=['get'])
    def logs(self, request, pk):
        def gen_log(logs):
            for line in logs.splitlines():
                yield '%s\r\n' % line

        job = self.get_object()
        worker = job.aves_worker.filter(is_main_node=True)[0]
        # TODO: support query params '?tail_lines=100'
        rt = worker.get_worker_log(tail_lines=2000)
        return StreamingHttpResponse(gen_log(rt), content_type="text/plain")

    @action(detail=False, methods=['post'])
    def submit_avesjob(self, request):
        user = request.user
        data = obtain_post_data(request)

        ok, err = validate_job(data)
        if err:
            msg = str(err)
            logger.error('Submit job failed: {}'.format(err))
            rt = {'success': False, 'errorMessage': msg}
            return Response(rt)

        if data['username'] != user.username and not user.is_superuser:
            msg = 'cannot submit job with username {}'.format(data['username'])
            logger.error('Submit job failed: {}'.format(msg))
            rt = {'success': False, 'errorMessage': msg}
            return Response(rt)

        transed_data = trans_job_data(data)
        serializer = self.get_serializer(data=transed_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        tasks.start_avesjob.delay(serializer.data['id'])
        rt = {'success': True, 'errorMessage': ''}
        return Response(rt)

    @action(detail=False, methods=['post'])
    def delete_avesjob(self, request):
        # TODO: Not implemented delete_avesjob
        rt = {'success': False, 'errorMessage': ''}
        return Response(rt)

    @action(detail=False, methods=['post'])
    def cancel_avesjob(self, request):
        data = obtain_post_data(request)
        job_id = data.get('jobId')
        username = data.get('username')
        namespace = data.get('namespace', 'default')
        force = data.get('force', False)

        try:
            avesjob = AvesJob.objects.get(job_id=job_id)
        except AvesJob.DoesNotExist:
            msg = 'job_id {} not found'.format(job_id)
            logger.error('Cancel job failed: {}'.format(msg))
            rt = {'success': False, 'errorMessage': msg}
            return Response(rt)

        # TODO: cancel job in celery task
        try:
            avesjob.cancel()
            avesjob.update_status('CANCELED')
            rt = {'success': True, 'errorMessage': ''}
        except Exception as e:
            logger.error('Cancel job failed: {}'.format(avesjob), exc_info=True)
            rt = {'success': False, 'errorMessage': 'cancel job failed'}
        return Response(rt)

    @action(detail=False, methods=['get'])
    def get_loginfo(self, request):
        username = request.GET.get('username')
        namespace = request.GET.get('namespace')
        job_id = request.GET.get('job_id')
        role_id = request.GET.get('roleId')

        if not (username and namespace and job_id):
            err_msg = 'username namespace job_id are required'
            return Response(
                {'success': False, 'errorMessage': err_msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            avesjob = AvesJob.objects.get(job_id=job_id)
        except AvesJob.DoesNotExist:
            msg = 'job_id {} not found'.format(job_id)
            logger.error('Cancel job failed: {}'.format(msg))
            rt = {'success': False, 'errorMessage': msg}
            return Response(rt)

        worker_set = AvesWorker.objects.filter(avesjob__job_id=job_id)
        if role_id is not None:
            worker_set = worker_set.filter(role_index=roleId)
        serializer = WorkerLogSerializer(worker_set, many=True)
        return Response(serializer.data)
