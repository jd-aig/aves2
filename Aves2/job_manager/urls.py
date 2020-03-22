"""Aves2 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from django.conf.urls import url

from rest_framework.routers import DefaultRouter

from job_manager.views import AvesJobViewSet, AvesWorkerViewSet
from job_manager.views import client_check


router = DefaultRouter()
router.register(r'aves_job', AvesJobViewSet, base_name="aves_job")
router.register(r'aves_worker', AvesWorkerViewSet, base_name="aves_worker")

urlpatterns = [
    path('client_check', client_check, name='client_check')
]

urlpatterns += router.urls
