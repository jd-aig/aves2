import logging

from django.shortcuts import render
from django.conf import settings
from django.template import loader
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login

from rest_framework.authtoken.models import Token
from job_manager.models import AvesJob, K8SWorker


logger = logging.getLogger('aves2')


@login_required
def home(request):
    if request.user.is_active and request.user.is_superuser:
        jobs = AvesJob.objects.all().order_by('-id')
    else:
        jobs = AvesJob.objects.all().filter(username=request.user.username) 
    context = {'jobs': jobs}
    return render(request, 'aves2_center/index.html', context)

@login_required
def token(request):
    try:
        token = Token.objects.get(user=request.user).key
    except Exception as e:
        Token.objects.crate(user=request.user).key
    context = {'token': token}
    return render(request, 'aves2_center/token.html', context)
