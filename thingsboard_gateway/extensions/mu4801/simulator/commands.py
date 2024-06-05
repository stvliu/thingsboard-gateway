import logging
from exceptions import *
from constants import *
from models import Command

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# 命令管理器
class Commands:
    def __init__(self, config):
        logger.debug(f"Initializing Commands with config: {config}")
        self._enums = {}
        self._commands_by_cid = {}
        self._commands_by_key = {}
        self._attributes = self._parse_commands(config['attributes'])
        self._timeseries = self._parse_commands(config['timeseries'])
        self._alarms = self._parse_commands(config['alarms'])
        self._server_side_rpc = self._parse_commands(config['serverSideRpc'])
        for command in self._attributes + self._timeseries + self._alarms + self._server_side_rpc:
            self._commands_by_cid[(command.cid1, command.cid2)] = command
            self._commands_by_key[command.key] = command

    def _parse_commands(self, cmd_configs):
        commands = []
        for cmd_config in cmd_configs:
            cid1 = cmd_config['cid1']
            cid2 = cmd_config['cid2']
            key = cmd_config['key']
            name = cmd_config['name']
            request_class_name = cmd_config.get('request')
            response_class_name = cmd_config.get('response')
            
            request_class = None
            if request_class_name:
                request_module = __import__('models', fromlist=[request_class_name])
                request_class = getattr(request_module, request_class_name)
                # self._collect_enums(request_class, self._enums)
                
            response_class = None  
            if response_class_name:
                response_module = __import__('models', fromlist=[response_class_name])
                response_class = getattr(response_module, response_class_name)
                # self._collect_enums(response_class, self._enums)
                
            cmd = Command(cid1, cid2, key, name, request_class, response_class)
            commands.append(cmd)

        return commands

    def get_command_by_cid(self, cid1, cid2):
        logger.debug(f"Looking up command with cid1={cid1}, cid2={cid2}")
        command = self._commands_by_cid.get((cid1, cid2))
        logger.debug(f"Found command: {command}")
        return command

    def get_command_by_key(self, command_key):
        logger.debug(f"Looking up command by key: {command_key}")
        command = self._commands_by_key.get(command_key)
        logger.debug(f"Found command: {command}")
        return command

    # def get_enums(self):
    #     return self._enums
    
    # def _collect_enums(self, data_class, enums):
    #     from dataclasses import fields
    #     for field in fields(data_class):
    #         if field.type is Enum:
    #             enums.update(field.type.enum_dict)
    #     from dataclasses import fields
    #     for field in fields(data_class):
    #         if field.type is Enum:
    #             enums.update(field.type.enum_dict)
   