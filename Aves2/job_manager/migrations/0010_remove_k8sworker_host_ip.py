# Generated by Django 2.2 on 2020-03-13 17:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('job_manager', '0009_k8sworker_host_ip'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='k8sworker',
            name='host_ip',
        ),
    ]
