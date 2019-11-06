from django.utils import timezone
from rest_framework import serializers

from .models import AvesJob


class AvesJobSerializer(serializers.ModelSerializer):

    class Meta:
        model = AvesJob
        fields = '__all__'
