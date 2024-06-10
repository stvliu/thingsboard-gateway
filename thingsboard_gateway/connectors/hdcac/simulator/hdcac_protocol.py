from ydt1363_protocol import Ydt1363Protocol
import json
import serial
import logging
# 导入相关的数据类
from hdcac_models import *

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class HdcAcProtocol(Ydt1363Protocol):
    def __init__(self, device_addr, port, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None, config_file='hdcac.json'):
        self._log = logging.getLogger(self.__class__.__name__)
        with open(config_file, 'r') as f:
            config = json.load(f)
        config['models_package'] = self._get_models_package()
        super().__init__(
            config = config,
            device_addr = device_addr,
            port= port ,
            baudrate = baudrate,
            bytesize = bytesize,
            parity = parity,
            stopbits = stopbits,
            timeout = timeout
        )

    def _get_models_package(self):
        return 'hdcac_models'