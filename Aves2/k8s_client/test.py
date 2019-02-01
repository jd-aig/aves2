import os

from k8s_client.objects import make_single_container_job
from k8s_client.k8s_client import K8SClient


def create_k8s_job(job_name, namespace, image_url, cmd, cmd_args):
    job_spec = make_single_container_job(
        job_name,
        cmd,
        cmd_args,
        image_url
    )
    k8s_client = K8SClient()
    rt, job, msg = k8s_client.create_single_container_job(job_spec, 'logcollector')


def process_cb(event):
    print(event['object'].metadata.name, event['object'].metadata.namespace)