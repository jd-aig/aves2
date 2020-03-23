import logging

from django.shortcuts import render
from django.conf import settings
from django.template import loader
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.core.paginator import Paginator

from rest_framework.authtoken.models import Token
from job_manager.models import AvesJob, K8SWorker


logger = logging.getLogger('aves2')


@login_required
def home(request, page=1):
    if request.user.is_active and request.user.is_superuser:
        jobs = AvesJob.objects.all().order_by('-id')
    else:
        jobs = AvesJob.objects.all()\
                .filter(username=request.user.username).order_by('-id')
    paginator = Paginator(jobs, 10)
    if not page:
        page = 1
    else:
        page = int(page)
    page_data = paginator.page(page)
    context = {'jobs': page_data}
    return render(request, 'aves2_center/index.html', context)


@login_required
def token(request):
    try:
        token = Token.objects.get(user=request.user).key
    except Exception as e:
        token = Token.objects.create(user=request.user).key
    context = {'token': token}
    return render(request, 'aves2_center/token.html', context)
