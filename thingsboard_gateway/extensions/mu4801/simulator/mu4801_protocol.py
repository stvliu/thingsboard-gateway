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

    def parse_response(self, response, command_key):
        command = self._find_command_by_key(command_key)
        if not command:
            raise ValueError(f"Unsupported command: {command_key}")
        return super().parse_response(response, command)
    
    def recv_command(self):
        return self._receive_command()
