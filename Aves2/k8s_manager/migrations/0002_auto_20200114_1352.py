# Generated by Django 2.1.5 on 2020-01-14 05:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('k8s_manager', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='k8sresourcequota',
            table='k8s_resource_quota',
        ),
    ]
