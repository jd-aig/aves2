from .caffe_maker import K8sCaffeTrainMaker
from .caffempi_maker import K8sCaffeMpiTrainMaker
from .custom_maker import K8sCustomTrainMaker
from .horovod_maker import K8sHorovodTrainMaker
from .mxnet_maker import K8sMxnetTrainMaker
from .pytorch_maker import K8sPyTorchTrainMaker
from .sge_maker import K8sSGETrainMaker
from .tensorflow_maker import K8sTensorFlowTrainMaker
from .xgboost_maker import K8sXGBoostTrainMaker

from .storage_mixin import get_storage_mixin_cls

def get_train_maker(ml_framework_name):
    maker_name = 'K8s{name}TrainMaker'.format(name=ml_framework_name)
    return globals()[maker_name]
