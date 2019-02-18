import os

from k8s_client.k8s_client import k8s_client


exec_backend = {
    'Job': {
        'create': k8s_client.create_job,
        'delete': k8s_client.delete_job
    },
    'ReplicationController': {
        'create': k8s_client.create_rc,
        'delete': k8s_client.delete_rc
    },
    'Service': {
        'create': k8s_client.create_svc,
        'delete': k8s_client.delete_svc
    },
    'Ingress': {
        'create': k8s_client.create_ingress,
        'delete': k8s_client.delete_ingress
    }
}