from ydt1363_3_2005_protocol import Protocol, Command, CommandParam, CommandValue
import json
import logging

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')

class MU4801Protocol(Protocol):
    def __init__(self, device_addr, port, config_file='mu4801.json'):
        self._log = logging.getLogger(self.__class__.__name__)
        with open(config_file, 'r') as f:
            config = json.load(f)
        super().__init__(device_addr, port, config=config)