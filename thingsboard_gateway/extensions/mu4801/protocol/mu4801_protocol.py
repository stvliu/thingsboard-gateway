import serial
import logging
from thingsboard_gateway.extensions.mu4801.protocol.ydt1363_protocol import Ydt1363Protocol
# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')

class MU4801Protocol(Ydt1363Protocol):
    def __init__(self, config, device_addr, port, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None):
        self._log = logging.getLogger(self.__class__.__name__)
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

        