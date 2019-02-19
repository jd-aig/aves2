import os

from k8s_client.k8s_client import k8s_client


exec_backend = {
    'Job': {
        'create': k8s_client.create_job,
        'delete': k8s_client.delete_job,
        'list': k8s_client.list_job,
    },
    'ReplicationController': {
        'create': k8s_client.create_rc,
        'delete': k8s_client.delete_rc,
        'list': k8s_client.list_rc,
    },
    'Service': {
        'create': k8s_client.create_svc,
        'delete': k8s_client.delete_svc,
        'list': k8s_client.list_svc,
    },
    'Ingress': {
        'create': k8s_client.create_ingress,
        'delete': k8s_client.delete_ingress,
        'list': k8s_client.list_ingress
    }
}