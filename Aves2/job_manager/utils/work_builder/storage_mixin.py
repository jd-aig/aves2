import os
import datetime

from django.conf import settings

CONTAINER_WORKSPACE = settings.CONTAINER_WORKSPACE
CONTAINER_MOUNT_DIR = settings.CONTAINER_MOUNT_DIR
CONTAINER_RUN_LOG_DIR = settings.CONTAINER_RUN_LOG_DIR
NODE_LOCAL_DIR = settings.NODE_LOCAL_DIR
NODE_LOCAL_MOUNT_DIR = settings.NODE_LOCAL_MOUNT_DIR

CEPH_MONITOR = settings.CEPH_MONITOR
CEPH_MONITOR_PORT = settings.CEPH_MONITOR_PORT
CEPH_USER = settings.CEPH_USER
CEPH_SECRET = settings.CEPH_SECRET
S3_ACCESS_KEY_ID = settings.S3_ACCESS_KEY_ID
S3_SECRET_ACCESS_KEY = settings.S3_SECRET_ACCESS_KEY
S3_ENDPOINT = settings.S3_ENDPOINT


class JobEngine:
    TensorFlow = 'TensorFlow'
    Caffe = 'Caffe'
    CaffeMpi = 'CaffeMpi'
    SGE = 'SGE'
    PyTorch = 'PyTorch'
    Horovod = 'Horovod'
    XGBoost = 'XGBoost'
    Custom = 'Custom'
    Tensorboard = 'Tensorboard'
    TfProfiler = 'TfProfiler'
    Mxnet = 'Mxnet'

# JOB_ENGINE_LIST = [i for i in dir(JobEngine) if not i.startswith('__')]
JOB_ENGINE_LIST = [getattr(JobEngine,i) for i in dir(JobEngine) if not i.startswith('__')]

class FileSystemType:
    CEPH = 'cephfs'
    MFS = 'mfs'
    S3 = 's3://'


class StorageMixIn():
    def _is_oss_path(self, path):
        if path.startswith(FileSystemType.S3):
            return True
        else:
            return False

    def _gen_volume_mounts_for_shm(self):
        mount = {
            "name": "dshm",
            "mountPath": "/dev/shm"
        }
        return mount

    def _gen_volume_mounts_for_tz(self):
        mount = {
            "name": "tz-config",
            "mountPath": "/etc/localtime",
            "readOnly": True
        }
        return mount

    def _gen_volume_for_shm(self):
        volume = {
            "name": "dshm",
            "emptyDir": {
                "medium": "Memory"
            }
        }
        return volume

    def _gen_volume_for_tz(self):
        volume = {
            "name": "tz-config",
            "hostPath": {
                "type": "File",
                "path": "/etc/localtime"
            }
        }
        return volume

    def _gen_create_s3cfg_cmd(self):
        CFG_FILE = "/root/.s3cfg"
        CFG_MAP = {}
        s3_config = self.avesjob.storage_config
        CFG_MAP['access_key'] = s3_config['S3AccessKeyId']
        CFG_MAP['secret_key'] = s3_config['S3SecretAccessKey']
        CFG_MAP['host_base'] = s3_config['S3Endpoint']
        CFG_MAP['host_bucket'] = ""
        CFG_MAP['use_https'] = "False"

        cmd = "echo \""
        for k,v in CFG_MAP.items():
            cmd += "%s = %s\n" % (k, v)
        cmd += "\" > %s" % CFG_FILE
        return cmd

    def _gen_s3cmd_sync_cmd(self, src, dst):
        # if need quiet the output use this "s3cmd sync -q %s %s"
        return "s3cmd sync %s %s" % (src, dst)

    def _gen_s3cmd_sync_cmd_with_auth(self, src, dst):
        s3_config = self.avesjob.storage_config
        return "s3cmd --access_key=%s --secret_key=%s --host=%s --host-bucket= --no-ssl sync %s %s" % \
                (s3_config['S3AccessKeyId'], s3_config['S3SecretAccessKey'],
                s3_config['S3Endpoint'], src, dst)

    def _gen_oss_sync_package_cmd(self):
        if not self._is_oss_path(self.avesjob.package_uri):
            raise Exception('Invalid S3 path for package_uri: %s' % self.avesjob.package_uri)
        src = os.path.join(self.avesjob.package_uri, '')
        dst = os.path.join(CONTAINER_WORKSPACE, '')
        return self._gen_s3cmd_sync_cmd(src, dst)

    #
    # Public function can be override by child class
    #
    def _gen_volume_mounts(self):
        return []

    def _gen_volumes(self, role_name):
        return []

    def _gen_workspace_prepare_cmd(self, roleName, index):
        return ""

    def _gen_pre_exec_cmd(self):
        return ""

    def _gen_exec_cmd(self, roleName, index, entrypoint_func):
        return "%s ;" % entrypoint_func(index)

    def _gen_post_exec_cmd(self):
        return ""

    def _gen_args_from_dict(self, ioput_dict):
        return ""

    def _gen_storage_env(self):
        return []

    def _gen_grace_period(self):
        # default value in k8s
        return 30

MFS_AVES_RUNLOG_DIR="/mnt/mfs/aves/jobs/logs"
CEPH_AVES_RUNLOG_DIR="/mnt/cephfs/public/aves/jobs/logs"

class FsStorageMixIn(StorageMixIn):
    def _get_fs_type(self, path):
        if path == None:
            return None
        if path.startswith('/mnt/%s/' % FileSystemType.MFS):
            return FileSystemType.MFS
        elif path.startswith('/mnt/%s/' % FileSystemType.CEPH):
            return FileSystemType.CEPH
        elif path.startswith(FileSystemType.S3):
            return FileSystemType.S3
        else:
            return None

    def _is_package_need_mount(self):
        fs_type = self._get_fs_type(self.avesjob.package_uri)
        if fs_type == None:
            return False
        elif fs_type == FileSystemType.S3:
            raise Exception("package_uri %s not support s3 type" % self.avesjob.package_uri)
        else:
            return True

    def _gen_volume_mounts_for_runlog(self):
        return {"name": "runlog", "mountPath": CONTAINER_RUN_LOG_DIR}

    def _gen_volume_mounts_for_dict(self, volume_dict):
        mounts = []
        if volume_dict == None:
            return mounts

        for name in volume_dict.keys():
            path = volume_dict[name]['path']
            mounts.append({
                "name": "".join(e for e in name if e.isalnum()),
                "mountPath": os.path.join(CONTAINER_MOUNT_DIR, name)
            })

        return mounts

    def _gen_volume_mounts(self):
        mounts = []
        mounts += self._gen_volume_mounts_for_dict(self.avesjob.input_spec)
        mounts += self._gen_volume_mounts_for_dict(self.avesjob.output_spec)

        mounts.append(self._gen_volume_mounts_for_shm())
        mounts.append(self._gen_volume_mounts_for_tz())

        mounts.append(self._gen_volume_mounts_for_runlog())
        if self._is_package_need_mount():
            mounts.append({"name": "workspace", "mountPath": CONTAINER_WORKSPACE})
        return mounts

    def _gen_ceph_relpath(self, path):
        subpath = path.split("cephfs")
        if len(subpath) < 2:
            raise Exception("cephfs path %s is not valid" % path)

        return subpath[1]

    def _gen_ceph_monitor(self):
        monitors = []
        ip_list = CEPH_MONITOR.split(',')
        if len(ip_list) > 0 and len(ip_list[0]) == 0:
            raise Exception("invalid CEPH_MONITOR %s" % CEPH_MONITOR) 
        if not CEPH_MONITOR_PORT.isdecimal():
            raise Exception("invalid CEPH_MONITOR_PORT %s" % CEPH_MONITOR_PORT) 

        for ip in ip_list:
            monitors.append("%s:%s" % (ip, CEPH_MONITOR_PORT))

        return monitors

    def _gen_volume_for_dict(self, volume_dict):
        volumes = []
        if volume_dict == None:
            return volumes

        for name in volume_dict.keys():
            path = volume_dict[name]['path']
            volumes.append(self._gen_volume(name, path))

        return volumes

    def _gen_volume(self, name, path):
        fs_type = self._get_fs_type(path)
        if fs_type == FileSystemType.MFS:
            return self._gen_volume_for_mfs(name, path)
        elif fs_type == FileSystemType.CEPH:
            return self._gen_volume_for_ceph(name, path)
        else:
            raise Exception("invalid fs_type for path %s" % path)

    def _gen_volume_for_mfs(self, name, path):
        volume = {
            "name": "".join(e for e in name if e.isalnum()),
            "hostPath": {
                "path": path
            }
        }
        return volume

    def _gen_volume_for_ceph(self, name, path):
        volume = {
            "name": "".join(e for e in name if e.isalnum()),
            "cephfs": {
                "path": self._gen_ceph_relpath(path),
                "monitors": self._gen_ceph_monitor(),
                "user": CEPH_USER,
                "secretRef": {'name': CEPH_SECRET}
            }
        }
        return volume

    def _gen_volume_for_default_runlog(self, name):
        fs_type = self._get_fs_type(self.avesjob.package_uri)
        if fs_type == FileSystemType.MFS:
            return self._gen_volume_for_mfs(name, MFS_AVES_RUNLOG_DIR)
        elif fs_type == FileSystemType.CEPH or fs_type == None:
            # use ceph path as default if avesjob.package_uri is not on fs
            return self._gen_volume_for_ceph(name, CEPH_AVES_RUNLOG_DIR)

    def _gen_volumes(self, role_name):
        volumes = []
        volumes += self._gen_volume_for_dict(self.avesjob.input_spec)
        volumes += self._gen_volume_for_dict(self.avesjob.output_spec)

        volumes.append(self._gen_volume_for_shm())
        volumes.append(self._gen_volume_for_tz())

        if self._is_package_need_mount():
            volumes.append(self._gen_volume('workspace', self.avesjob.package_uri))

        if self.avesjob.log_dir:
            volumes.append(self._gen_volume('runlog', self.avesjob.log_dir))
        else:
            volumes.append(self._gen_volume_for_default_runlog('runlog'))
        return volumes

    def __download_pkg_cmd(self):
        if self.avesjob.package_uri.endswith('.tar.gz') or self.avesjob.package_uri.endswith('.tgz'):
            return "wget -q \'%s\' -O aves_pkg.tgz" % self.avesjob.package_uri
        elif self.avesjob.package_uri.endswith('.zip'):
            return "wget -q \'%s\' -O aves_pkg.zip" % self.avesjob.package_uri
        else:
            raise Exception('Unknown package type: %s' % self.avesjob.package_uri)

    def __unpack_pkg_cmd(self):
        if self.avesjob.package_uri.endswith('.tar.gz') or self.avesjob.package_uri.endswith('.tgz'):
            return 'tar zxf aves_pkg.tgz'
        elif self.avesjob.package_uri.endswith('.zip'):
            return 'unzip -x aves_pkg.zip'
        else:
            raise Exception('Unknown package type: %s' % self.avesjob.package_uri)

    def __gen_runlogdir(self, roleName, index):
        if self.avesjob.log_dir:
            runlogDir = os.path.join(CONTAINER_RUN_LOG_DIR, '%s-%d' % (roleName, index))
        else:
            runlogDir = os.path.join(CONTAINER_RUN_LOG_DIR, '%s/%s-%d' % (self.avesjob.merged_id, roleName, index))
        return runlogDir

    def __gen_tmstamp(self):
        return datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')

    def _gen_workspace_prepare_cmd(self, roleName, index):
        runlogDir = self.__gen_runlogdir(roleName, index)
        cmd = 'mkdir -p %s %s ; cd %s ;' % (CONTAINER_WORKSPACE, runlogDir, CONTAINER_WORKSPACE)
        if not self._is_package_need_mount() and self.avesjob.package_uri != None:
            cmd += "%s ;" % self.__download_pkg_cmd()
            cmd += "%s ;" % self.__unpack_pkg_cmd()
        return cmd

    def _gen_exec_cmd(self, roleName, index, entrypoint_func):
        runlogDir = self.__gen_runlogdir(roleName, index)
        tmstamp = self.__gen_tmstamp()
        return '%s 2>&1 | tee %s.log && ( exit ${PIPESTATUS[0]} ) ;' % \
                (entrypoint_func(index), os.path.join(runlogDir, tmstamp))

    def _gen_args_from_dict(self, ioput_dict):
        args = ''
        for name, value in ioput_dict.items():
            path = value['path']
            filename = name
            if value['filename']:
                filename = os.path.join(name, value['filename'])
            args += ' --%s %s' % (name, os.path.join(CONTAINER_MOUNT_DIR, filename))
        return args


class OssStorageMixIn(StorageMixIn):
    def _gen_volume_mounts(self):
        mounts = []
        mounts.append(self._gen_volume_mounts_for_shm())
        mounts.append(self._gen_volume_mounts_for_tz())
        return mounts

    def _gen_volumes(self, role_name):
        volumes = []
        volumes.append(self._gen_volume_for_shm())
        volumes.append(self._gen_volume_for_tz())
        return volumes

    def _gen_workspace_prepare_cmd(self, roleName, index):
        cmd = 'mkdir -p %s ; cd %s ;' % (CONTAINER_WORKSPACE, CONTAINER_WORKSPACE)
        cmd += "%s ; " % self._gen_create_s3cfg_cmd()
        cmd += "%s ; " % self._gen_oss_sync_package_cmd()
        return cmd

    def _gen_exec_cmd(self, roleName, index, entrypoint_func):
        return '%s ;' % entrypoint_func(index)

    def _gen_args_from_dict(self, ioput_dict):
        args = ''
        for name, value in ioput_dict.items():
            path = value['path']
            if not self._is_oss_path(path):
                raise Exception('Invalid S3 path: %s args_name: %s' % (path, name))
            if value['filename']:
                one_arg = ' --%s %s' % (name, os.path.join(path, value['filename']))
            else:
                one_arg = ' --%s %s' % (name, path)
            args += one_arg.rstrip('/')
        return args

    def _gen_storage_env(self):
        envs = []
        s3_config = self.storageMode['config']
        envs.append({"name": "AWS_ACCESS_KEY_ID", "value": s3_config['S3AccessKeyId']})
        envs.append({"name": "AWS_SECRET_ACCESS_KEY", "value": s3_config['S3SecretAccessKey']})
        envs.append({"name": "S3_ENDPOINT", "value": s3_config['S3Endpoint']})
        envs.append({"name": "S3_USE_HTTPS", "value": "0"})
        return envs


WRAPPER_SCRIPT_PATH = "http://ai-fileserver.jd.com/share/tools/aves/aves_run_wrapper.sh"
WRAPPER_SCRIPT = os.path.basename(WRAPPER_SCRIPT_PATH)
OSS_SYNC_BASE = os.path.join(CONTAINER_WORKSPACE, "oss_sync")
CLEANUP_CMD = "/bin/rm -rf * .[!.]*"

class OssFileStorageMixIn(StorageMixIn):
    def __gen_volume_mounts_for_pv(self):
        mount = {
            "name": "pv-dir",
            "mountPath": CONTAINER_WORKSPACE
        }
        return mount

    def _gen_volume_mounts(self):
        mounts = []
        mounts.append(self.__gen_volume_mounts_for_pv())
        mounts.append(self._gen_volume_mounts_for_shm())
        mounts.append(self._gen_volume_mounts_for_tz())
        return mounts

    def __gen_volume_for_pv(self, role_name):
        pv_path = os.path.join(NODE_LOCAL_DIR, role_name)
        volume = {
            "hostPath": {
                "path": pv_path
            },
            "name": "pv-dir"
        }
        return volume

    def __unpack_pkg_cmd(self, comp_file, dst):
        if comp_file.endswith('.tar.gz') or comp_file.endswith('.tgz'):
            return 'mkdir -p %s && tar zxf %s -C %s' % (dst, comp_file, dst)
        elif comp_file.endswith('.zip'):
            return 'unzip -q %s -d %s' % (comp_file, dst)
        else:
            raise Exception('Unknown package type: %s' % comp_file)

    def __is_compressed_file(self, path):
        if path.endswith('.tar.gz') or path.endswith('.tgz') or \
                path.endswith('.zip'):
            return True
        else:
            return False

    def _gen_volumes(self, role_name):
        volumes = []
        volumes.append(self.__gen_volume_for_pv(role_name))
        volumes.append(self._gen_volume_for_shm())
        volumes.append(self._gen_volume_for_tz())
        return volumes

    def _gen_workspace_prepare_cmd(self, roleName, index):
        cmd = 'mkdir -p %s %s; cd %s ;' % (CONTAINER_WORKSPACE,
                OSS_SYNC_BASE, CONTAINER_WORKSPACE)
        cmd += "%s ; " % self._gen_create_s3cfg_cmd()
        cmd += "%s ; " % self._gen_oss_sync_package_cmd()
        cmd += "wget %s ; " % WRAPPER_SCRIPT_PATH
        # use exec to swap last cmd with root process to handle SIGTERM
        cmd += "exec /bin/sh %s " % WRAPPER_SCRIPT
        return cmd

    def _gen_pre_exec_cmd(self):
        pre_cmd = ''
        for name, value in self.avesjob.input_spec.items():
            path = value['path']
            filename = value['filename']
            dst_path = os.path.join(OSS_SYNC_BASE, name, '')
            if filename is None or len(filename) == 0:
                src_path = os.path.join(path, '')
            else:
                src_path = os.path.join(path, filename)

            if self.__is_compressed_file(src_path):
                comp_file = os.path.basename(src_path)
                # let's sync to ./ then unpack to dst_path
                pre_cmd += "%s; " % self._gen_s3cmd_sync_cmd(src_path, './')
                pre_cmd += "%s; " % self.__unpack_pkg_cmd(comp_file, dst_path)
            else:
                pre_cmd += "%s; " % self._gen_s3cmd_sync_cmd(src_path, dst_path)

        for name, value in self.avesjob.output_spec.items():
            pre_cmd += "mkdir %s; " % os.path.join(OSS_SYNC_BASE, name)
        cmd = "--pre_cmd \"%s\" " % pre_cmd
        return cmd

    def _gen_exec_cmd(self, roleName, index, entrypoint_func):
        return "--exec_cmd \"%s\" " % entrypoint_func(index)

    def _gen_post_exec_cmd(self):
        post_cmd = ''
        for name, value in self.avesjob.output_spec.items():
            path = value['path']
            src_path = os.path.join(OSS_SYNC_BASE, name, '')
            dst_path = os.path.join(path, '')
            post_cmd += "%s; " % self._gen_s3cmd_sync_cmd(src_path, dst_path)
        if len(post_cmd.strip()) == 0:
            cmd = "--post_cmd \"%s\" ;" % CLEANUP_CMD
        else:
            cmd = "--post_cmd \"%s %s\" ;" % (post_cmd, CLEANUP_CMD)
        return cmd

    def _gen_args_from_dict(self, ioput_dict):
        args = ''
        for name, value in ioput_dict.items():
            filename = name
            if value['filename']:
                filename = os.path.join(name, value['filename'])
            if ioput_dict == self.inputSpec and self.__is_compressed_file(filename):
                args += ' --%s %s' % (name, os.path.join(OSS_SYNC_BASE, name, ''))
            else:
                args += ' --%s %s' % (name, os.path.join(OSS_SYNC_BASE, filename))
        return args

    def _gen_storage_env(self):
        return []

    def _gen_grace_period(self):
        # 40MB/s average speed, 2min can upload about 5GB
        return 120

STORAGE_MIXIN_CLS_DICT = {
    "Filesystem": FsStorageMixIn,
    "OSS": OssStorageMixIn,
    "OSS_File": OssFileStorageMixIn,
}

def get_storage_mixin_cls(storage_mode):
    cls = STORAGE_MIXIN_CLS_DICT.get(storage_mode, None)
    if cls is None:
        raise Exception("Invalid storage mode:%s" % storage_mode)
    return cls
