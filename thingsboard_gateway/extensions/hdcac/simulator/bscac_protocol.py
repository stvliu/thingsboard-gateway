from ydt1363_protocol import Ydt1363Protocol
import json
import logging
# 导入相关的数据类
from models import *

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class BscAcProtocol(Ydt1363Protocol):
    def __init__(self, device_addr, port, config_file='bscac.json'):
        self._log = logging.getLogger(self.__class__.__name__)
        with open(config_file, 'r') as f:
            config = json.load(f)
        config['models_package'] = self._get_models_package()
        super().__init__(device_addr, port, config=config)

    def _get_models_package(self):
        return 'models'