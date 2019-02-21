"""
Helper methods for generating k8s API objects.
"""

def make_k8s_ports(ports):
    ports_conf = []
    for port in ports:
        ports_conf.append({"containerPort": port, "name": "%s-port" % port})
        # ports_conf.append({'port': port, 'targetPort': port, 'name': '%s-port' % port})
    return ports_conf

def make_k8s_svc_ports(ports):
    ports_conf = []
    for port in ports:
        # ports_conf.append({"containerPort": port, "name": "%s-port" % port})
        ports_conf.append({'port': port, 'targetPort': port, 'name': '%s-port' % port})
    return ports_conf

def make_ingress(
    name,
    job_id,
    host,
    path,
    svc_name,
    svc_port
):
    conf = {
        "apiVersion": "extensions/v1beta1",
        "kind": "Ingress",
        "metadata": {
            "name": name,
            "labels": {
                "jobId": job_id
            },
            "annotations": {
                "traefik.frontend.rule.type": "PathPrefix",
                "kubernetes.io/ingress.class": "traefik"
            }
        },
        "spec": {
            "rules": [{
                "host": host,
                "http": {
                    "paths": [{
                        "path": path,
                        "backend": {
                            "serviceName": svc_name,
                            "servicePort": svc_port
                        }
                    }]
                }
            }]
        }
    }
    return conf

def make_svc(
    name,
    job_id,
    ports=[]
):
    conf = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": name,
            "labels": {
                "jobId": job_id
            }
        },
        "spec": {
            "selector": {
                "app": name
            },
            "ports": make_k8s_svc_ports(ports)
        }
    }
    return conf

def make_job(
    name,
    namespace,
    job_id,
    image,
    cmd=["/bin/bash", "-c"],
    args=[],
    ports=[],
    envs=[],
    grace_period=30,
    resources={},
    volume_mounts=[],
    volumes=[],
    affinity={},
    init_containers=[],
    scheduler=None,
    hostipc=False,
):
    conf = {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "backoffLimit": 0,
            "parallelism": 1,
            "template": {
                "metadata": {
                    "name": name,
                    "labels": {
                        "app": name,
                        "jobId": job_id,
                        "hyperparam_id": None
                    }
                },
                "spec": {
                    "containers": [{
                        "name": name,
                        "image": image,
                        "imagePullPolicy": "Always",
                        "ports": make_k8s_ports(ports),
                        "env": envs,
                        "command": cmd,
                        "args": args,
                        "resources": resources,
                        "volumeMounts": volume_mounts
                    }],
                    "initContainers": init_containers,
                    "terminationGracePeriodSeconds": grace_period,
                    "volumes": volumes,
                    "restartPolicy": "Never",
                    "affinity": affinity,
                    "schedulerName": scheduler
                }
            }
        }
    }
    return conf

def make_rc(
    name,
    namespace,
    job_id,
    image,
    cmd=["/bin/bash", "-c"],
    args=[],
    ports=[],
    envs=[],
    grace_period=30,
    resources={},
    volume_mounts=[],
    volumes=[],
    affinity={},
    init_containers=[],
    scheduler=None,
    hostipc=False,
):
    conf = {
        "apiVersion": "v1",
        "kind": "ReplicationController",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "app": name
            },
            "template": {
                "metadata": {
                    "name": name,
                    "labels": {
                        "app": name,
                        "jobId": job_id
                    }
                },
                "spec": {
                    "containers": [{
                        "name": name,
                        "image": image,
                        "imagePullPolicy": "Always",
                        "ports": make_k8s_ports(ports),
                        "env": envs,
                        "command": cmd,
                        "args": args,
                        "resources": resources,
                        "volumeMounts": volume_mounts
                    }],
                    "initContainers": init_containers,
                    "terminationGracePeriodSeconds": grace_period,
                    "volumes": volumes,
                    "affinity": affinity,
                    "schedulerName": scheduler
                }
            }
        }
    }
    return conf

