import re
import os
from urllib.parse import urlparse
from docker.types import ConfigReference, Resources, RestartPolicy


def make_config_datas(configmap_name, data):
    config_datas = []
    for cfg_fname, cfg_content in data.items():
        cfg_fname = '{0}-{1}'.format(configmap_name, cfg_fname)
        config_datas.append(dict(name=cfg_fname, data=cfg_content))
    return config_datas

def make_service(
    name,
    cmd,
    cmd_args,
    image,
    image_pull_policy='Always',
    image_pull_secret=None,
    port_list=None,
    env=[],
    networks=[],
    working_dir=None,
    configs=None,
    volumes=None,
    volume_mounts=None,
    labels={},
    cpu_limit=None,
    cpu_guarantee=None,
    mem_limit=None,
    mem_guarantee=None,
    gpu_limit=None,
    gpu_guarantee=None,
):
    args = (image,)
    kwargs = {}

    kwargs['name'] = name
    kwargs['command'] = cmd
    kwargs['args'] = cmd_args
    kwargs['container_labels'] = labels
    kwargs['env'] = ['{0}={1}'.format(i['name'], i['value']) for i in env] if env else []
    kwargs['labels'] = labels

    volume_d = {}
    config_d = {}
    volume_config_name_map = {}
    for _vol in volumes:
        if 'configMap' in _vol:
            config_prefix = _vol['configMap']['name']
            config_d[config_prefix] = {}
            volume_config_name_map[_vol['name']] = config_prefix
            for config_item in _vol['configMap']['items']:
                config_name = '{cfg_prefix}-{cfg_name}'.format(
                                    cfg_prefix=config_prefix,
                                    cfg_name=config_item['key']
                                )
                config_d[config_prefix][config_name] = {}
                config_d[config_prefix][config_name]['config_name'] = config_name
                config_d[config_prefix][config_name]['filename'] = config_item['path']
        else:
            volume_d[_vol['name']] = {}
            volume_d[_vol['name']]['vol'] = _vol

    for _mount in volume_mounts:
        if _mount['name'] in volume_config_name_map:
            for _, config_i in config_d[volume_config_name_map[_mount['name']]].items():
                config_i['filename'] = os.path.join(_mount['mountPath'], config_i['filename'])
        else:
            volume_d[_mount['name']]['mount'] = _mount

    # mounts
    # Mounts for the containers,
    # in the form source:target:options, where options is either ro or rw
    mounts = []
    for _, vol in volume_d.items():
        if 'hostPath' in vol['vol']:
            _src = vol['vol']['hostPath']['path']
            _target = vol['mount']['mountPath']
            _opt = 'ro' if vol['mount']['readOnly'] else 'rw'
            _mount_str = f"{_src}:{_target}:{_opt}"
            mounts.append(_mount_str)
    kwargs['mounts'] = mounts

    # config_refs
    # List of ConfigReference that will be exposed to the service.
    configs_name_map = {i.name: i for i in configs}
    config_refs = []
    for _, config_items in config_d.items():
        for _, config in config_items.items():
            config['config_id'] = configs_name_map[config['config_name']].id
            config_ref = ConfigReference(
                            config['config_id'],
                            config['config_name'],
                            config['filename']
                         )
            config_refs.append(config_ref)
    kwargs['configs'] = config_refs

    # resources
    # Resource limits and reservations.
    # resources = Resources(
    #                 cpu_limit=cpu_limit,
    #                 cpu_reservation=cpu_guarantee,
    #             )
    # kwargs['resources'] = resources

    kwargs['restart_policy'] = RestartPolicy()
    # TODO: replace hardcode network neuf-system
    kwargs['networks'] = networks
    return args, kwargs
