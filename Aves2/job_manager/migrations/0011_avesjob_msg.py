# Generated by Django 2.2 on 2020-03-19 15:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('job_manager', '0010_remove_k8sworker_host_ip'),
    ]

    operations = [
        migrations.AddField(
            model_name='avesjob',
            name='msg',
            field=models.CharField(blank=True, default='', max_length=512),
        ),
    ]
