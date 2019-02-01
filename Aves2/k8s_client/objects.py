from kubernetes.client.models import (
    V1Job, V1JobSpec,
    V1Pod, V1PodSpec, V1PodSecurityContext, V1PodTemplateSpec,
    V1ObjectMeta,
    V1LocalObjectReference,
    V1Volume, V1VolumeMount, V1CephFSVolumeSource,
    V1Container, V1ContainerPort, V1SecurityContext, V1EnvVar, V1ResourceRequirements,
    V1PersistentVolumeClaim, V1PersistentVolumeClaimSpec,
    V1Endpoints, V1EndpointSubset, V1EndpointAddress, V1EndpointPort,
    V1Service, V1ServiceSpec, V1ServicePort,
    V1beta1Ingress, V1beta1IngressSpec, V1beta1IngressRule,
    V1beta1HTTPIngressRuleValue, V1beta1HTTPIngressPath,
    V1beta1IngressBackend,
)


def make_volume_cephfs(name, monitors, user, secret_ref_name,
                       path='/', read_only=False):
    secret_ref = V1LocalObjectReference()
    secret_ref.name = secret_ref_name

    cephfs = V1CephFSVolumeSource(monitors=monitors)
    cephfs.path = path
    cephfs.read_only = read_only
    cephfs.user = user
    cephfs.secret_ref = secret_ref

    volume = V1Volume(name=name)
    volume.cephfs = cephfs
    return volume

def make_volume_mount(name, mount_path, mount_propagation=None, read_only=False, sub_path=None):
    volumen_mount = V1VolumeMount(name=name, mount_path=mount_path)
    return volumen_mount

def make_single_container_job(
    name,
    cmd,
    args,
    image_spec,
    image_pull_policy='Always',
    labels={},
    parallelism=1,
    completions=1,
    backoff_limit=0,
    restart_policy='Never',
    env={},
    working_dir=None,
    volumes=[],
    volume_mounts=[],
    annotations={},
    cpu_limit=None,
    cpu_guarantee=None,
    mem_limit=None,
    mem_guarantee=None,
    gpu_limit=None,
    gpu_guarantee=None,
    extra_resource_limits=None,
    extra_resource_guarantees=None,
    lifecycle_hooks=None,
    init_containers=None,
    service_account=None,
):
    """ Make a k8s job menifest for running a single container

    :param name: Name of job. Must be unique within the namespace the object is
        going to be created in. Must be a valid DNS label.
    :param cmd: The command used to execute the job container
    :param image_spec: Image specification
    :param image_pull_policy: one of 'Always', 'IfNotPresent' or 'Never'.
    :param labels: V1ObjectMeta property. Map of string keys and values that
        can be used to organize and categorize (scope and select) objects
    :param parallelism: V1JobSpec property. Specifies the maximum desired number
        of pods the job should run at any given time.
    :param completions: V1JobSpec property. Specifies the desired number of
        successfully finished pods the job should be run with
    :param backoff_limit: V1JobSpec property. Specifies the number of retries
        before marking this job failed
    :param restart_policy: V1PodSpec property. Restart policy for all containers
        within the pod. One of Always, OnFailure, Never
    :param env: 
    :param working_dir:
    :param volumes:
    :param volume_mounts:
    :param annotations:
    :param cpu_limit:
    :param cpu_guarantee:
    :param mem_limit:
    :param mem_guarantee:
    :param gpu_limit:
    :param gpu_guarantee:
    :param extra_resource_limits:
    :param extra_resource_guarantees:
    :param lifecycle_hooks:
    :param init_containers:
    :param service_account:
    """
    job = V1Job()
    job.kind = 'Job'
    job.api_version = 'batch/v1'
    
    job.metadata = V1ObjectMeta()
    job.metadata.name = name
    job.metadata.labels = labels.copy()

    job.spec = V1JobSpec(template=V1PodTemplateSpec())
    job.spec.parallelism = parallelism
    job.spec.completions = completions
    job.spec.backoff_limit = backoff_limit

    job.spec.template.spec = V1PodSpec(containers=[])
    job.spec.template.spec.restart_policy = restart_policy 
    job.spec.template.spec.volumes = volumes

    job_container = V1Container(name=name)
    job_container.command = cmd
    job_container.args = args
    job_container.env = [V1EnvVar(k, v) for k, v in env.items()]
    job_container.image = image_spec
    job_container.image_pull_policy = image_pull_policy
    job_container.resources = V1ResourceRequirements()
    job_container.volume_mounts = volume_mounts
    if working_dir:
        job_container.working_dir = working_dir

    job_container.resources.requests = {}
    if cpu_guarantee:
        job_container.resources.requests['cpu'] = cpu_guarantee
    if mem_guarantee:
        job_container.resources.requests['memory'] = mem_guarantee
    if gpu_guarantee:
        job_container.resources.requests['alpha.kubernetes.io/nvidia-gpu'] = gpu_guarantee
    if extra_resource_guarantees:
        for k in extra_resource_guarantees:
            job_container.resources.requests[k] = extra_resource_guarantees[k]

    job_container.resources.limits = {}
    if cpu_limit:
        job_container.resources.limits['cpu'] = cpu_limit
    if mem_limit:
        job_container.resources.limits['memory'] = mem_limit
    if gpu_limit:
        job_container.resources.limits['alpha.kubernetes.io/nvidia-gpu'] = gpu_limit
    if extra_resource_limits:
        for k in extra_resource_limits:
            job_container.resources.limits[k] = extra_resource_limits[k]

    job.spec.template.spec.containers.append(job_container)

    return job
