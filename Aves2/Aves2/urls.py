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
from django.contrib import admin
from django.urls import path, include
from django.urls import re_path
from django.conf import settings
from django.conf.urls import url
from django.views import static
from django.views.generic.base import RedirectView
from django.contrib.auth import views as auth_views
from aves2_jd_sso import views as auth_views


urlpatterns = [
    path('', include('aves2_center.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(), name="user_login"),
    path('accounts/logout/', auth_views.logout_then_login, name='logout'),
    path('admin/', admin.site.urls),
    # path('k8s/', include('k8s_manager.urls')),
    path('center/', include('aves2_center.urls')),
    path('api/', include('job_manager.urls')),
]

if not settings.DEBUG:
  urlpatterns += [
      re_path(r'^static/(?P<path>.*)$', static.serve, {'document_root': settings.STATIC_ROOT}),
  ]

urlpatterns = [path('{}/'.format(settings.URL_PREFIX), include(urlpatterns))]
