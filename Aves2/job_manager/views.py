import os
import time
import datetime
import logging

from django.shortcuts import render
from django.conf import settings

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, list_route, detail_route

from job_manager.models import AvesJob, K8SWorker
from job_manager.forms import AvesJobForm
from job_manager.tasks import startup_avesjob

logger = logging.getLogger('aves2')


class AvesJobViewSet(viewsets.ViewSet):
    """ A ViewSet for AvesJob
    """
    def create(self, request):
        """ Create a avesjob record
        """
        avesjob_form = AvesJobForm(request.POST)

        if not avesjob_form.is_valid():
            err_msg = "Failed to create avesjob record, form_data: {data}, err_msg: {err_text}"\
                        .format(data=avesjob_form.data, err_text=avesjob_form.errors.as_text)
            return Response({'err_msg': avesjob_form.errors}, status=status.HTTP_400_BAD_REQUEST)

        avesjob = avesjob_form.save()

        # TODO: update merge_id

        # Startup avesjob
        startup_avesjob.delay(avesjob.id)

        return Response(status=status.HTTP_201_CREATED)