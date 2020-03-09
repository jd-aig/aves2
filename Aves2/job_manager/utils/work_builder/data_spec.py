import os
import escapism

from jinja2 import PackageLoader, Environment, FileSystemLoader
from job_manager.utils.scripts_maker import TEMPLATE_PATH


def make_safe_name(name):
    safe_set = set(string.ascii_lowercase + string.digits)
    return escapism.escape(name, safe=safe_set, escape_char='-').lower()


class DataSpecType:
    OSS_FILE = 'OSSFile'
    K8S_PVC = 'K8SPVC'


class DataSpecKind:
    SOUCECODE = 'sourcecode'
    INPUT = 'input'
    OUTPUT = 'output'

    @classmethod
    def list(cls):
        return [cls.SOUCECODE, cls.INPUT, cls.OUTPUT]


class VirtualDataSpec(object):
    available_data_kind = DataSpecKind.list()
    base_path_map = {
        'sourcecode': '/AVES/src/',
        'input': '/AVES/data/',
        'output': '/AVES/output/'
    }

    def __init__(self, spec_type, src_path, filename, data_name, data_kind, readonly=True):
        if data_kind not in self.available_data_kind:
            raise Exception(f'Invalid datakind {data_kind}')
        self.spec_type = spec_type
        self.data_name = data_name
        self.data_kind = data_kind
        self.src_path = src_path
        self.filename = filename
        self.readonly = readonly

    @property
    def aves_path(self):
        """ data path in worker container
        """
        if self.data_kind in ['input', 'output']:
            dir_name = os.path.basename(self.src_path.rstrip('/'))
            dir_name = self.data_name
            return os.path.join(self.base_path_map[self.data_kind], dir_name)
        else:
            return self.base_path_map[self.data_kind]

    def gen_volume(self):
        return None

    def gen_volume_mount(self):
        return None

    def gen_prepare_data_cmd(self):
        return None

    def gen_gather_data_cmd(self):
        return None

    @property
    def data_prepare_cmd(self):
        cmd = self.gen_prepare_data_cmd()
        if cmd:
            return cmd
        else:
            return ''

    @property
    def data_gather_cmd(self):
        cmd = self.gen_gather_data_cmd()
        if cmd:
            return cmd
        else:
            return ''


class OSSFileDataSpec(VirtualDataSpec):
    def __init__(self, src_path, filename, data_name, data_kind, readonly=True, storage_config={}):
        spec_type = 'OSSFile'
        super(OSSFileDataSpec, self).__init__(spec_type, src_path, filename, data_name, data_kind, readonly)
        self.storage_config = storage_config

    def gen_prepare_data_cmd(self):
        tpl_path = TEMPLATE_PATH
        env = Environment(loader=FileSystemLoader(tpl_path))
        tpl = env.get_template(os.path.join('prepare_data_oss.sh.tmpl'))

        context = {
            'oss_endpoint': self.storage_config['endpoint'],
            'oss_profile': self.storage_config['profile_name'],
            'src': os.path.join(self.src_path, self.filename),
            'filename': self.filename,
            'dst': self.aves_path
        }
        return tpl.render(context)

    def gen_gather_data_cmd(self):
        tpl_path = TEMPLATE_PATH
        env = Environment(loader=FileSystemLoader(tpl_path))
        tpl = env.get_template(os.path.join('gather_data_oss.sh.tmpl'))

        context = {
            'oss_endpoint': self.storage_config['endpoint'],
            'oss_profile': self.storage_config['profile_name'],
            'src': self.aves_path,
            'dst': os.path.join(self.src_path, self.filename),
        }
        return tpl.render(context)


class K8SPvcDataSpec(VirtualDataSpec):
    def __init__(self, src_path, filename, data_name, data_kind, pvc_name, readonly=True):
        spec_type = 'K8SPVC'
        super(K8SPvcDataSpec, self).__init__(spec_type, src_path, filename, data_name, data_kind, readonly)
        self.pvc_name = pvc_name
        if self.data_kind == DataSpecKind.OUTPUT:
            self.readonly = False

    def gen_volume(self):
        return {
            'name': self.pvc_name,
            'persistentVolumeClaim': {
                'claimName': self.pvc_name
            }
        }

    def gen_volume_mount(self):
        mount_path = self.aves_path
        d = {
            'name': self.pvc_name,
            'mountPath': mount_path,
            'readOnly': self.readonly
        }
        subpath = self.src_path.lstrip('/') if self.src_path.rstrip('/').lstrip('/') else ''
        if subpath:
            d['subPath'] = subpath
        return d

    def gen_prepare_cmd(self):
        return "# mount pvc: {self.aves_path}"


class HostPathDataSpec(VirtualDataSpec):
    def __init__(self, src_path, filename, data_name, data_kind, readonly=True):
        spec_type = 'HostPath'
        super(HostPathDataSpec, self).__init__(spec_type, src_path, filename, data_name, data_kind, readonly)

        self.vol_name = '{0}-{1}'.format(self.data_kind, self.data_name.replace('_', ''))
        if self.data_kind == DataSpecKind.OUTPUT:
            self.readonly = False

    def gen_volume(self):
        return {
            'name': self.vol_name,
            'hostPath': {
                'path': self.src_path
            }
        }

    def gen_volume_mount(self):
        mount_path = self.aves_path
        d = {
            'name': self.vol_name,
            'mountPath': mount_path,
            'readOnly': self.readonly
        }
        return d

    def gen_prepare_cmd(self):
        return "# mount host path: {self.aves_path}"


registed_dataspec_class_map = {
    'OSSFile': OSSFileDataSpec,
    'K8SPVC': K8SPvcDataSpec,
    'HostPath': HostPathDataSpec,
}


def get_dataspec_class(spec_type):
    return registed_dataspec_class_map.get(spec_type)


def make_data_spec(name, data, data_kind):
    """
    :param name:
    :param data: dict. eg.
                {
                    'type': 'K8SPVC',
                    'path': '/mnist/',
                    'filename': ''
                    'storage_config': {}
                },
                {
                    'type': 'OSSFile',
                    'path': 's3://xxx',
                    'filename': ''
                    'storage_config': {
                        'endpoint': '',
                        'profile_name': ''
                    }
                },
    :param data_kind:
    """
    spec_class = get_dataspec_class(data['type'])
    params = [data['path'], data['filename'], name, data_kind]
    kparams = {}
    if data['type'] == 'K8SPVC':
        params.append(data['pvc'])
    elif data['type'] == 'OSSFile':
        kparams['storage_config'] = data['storage_config']
    return spec_class(*params, **kparams)
