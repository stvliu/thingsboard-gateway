import logging
from thingsboard_gateway.connectors.ydt1363.exceptions import *
from thingsboard_gateway.connectors.ydt1363.constants import *

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# 命令管理器
class Commands:
    def __init__(self, models_package: str, config):
        logger.debug(f"Initializing Commands with config: {config}")
        logger.debug(f"Models package: {models_package}")
        self._models_package = models_package
        self._commands_by_cid = {}
        self._commands_by_key = {}
        
        logger.debug("Parsing attributes...")
        self._attributes = self._parse_commands(config.get('attributes', []))
        logger.debug(f"Parsed {len(self._attributes)} attributes")
        
        logger.debug("Parsing timeseries...")
        self._timeseries = self._parse_commands(config.get('timeseries', []))
        logger.debug(f"Parsed {len(self._timeseries)} timeseries")
        
        logger.debug("Parsing attribute updates...")
        self._attribute_updates = self._parse_commands(config.get('attributeUpdates', []))
        logger.debug(f"Parsed {len(self._attribute_updates)} attribute updates")
        
        logger.debug("Parsing server-side RPCs...")
        self._server_side_rpc = self._parse_commands(config.get('serverSideRpc', []))
        logger.debug(f"Parsed {len(self._server_side_rpc)} server-side RPCs")
        
        all_commands = self._attributes + self._timeseries + self._attribute_updates + self._server_side_rpc
        logger.debug(f"Building command dictionaries for {len(all_commands)} total commands...")
        
        for command in all_commands:
            self._commands_by_cid[(command.cid1, command.cid2)] = command
            self._commands_by_key[command.key] = command
        
        logger.info(f"Initialized Commands with {len(all_commands)} total commands")

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
                request_module = __import__(self._models_package, fromlist=[request_class_name])
                request_class = getattr(request_module, request_class_name)
                # self._collect_enums(request_class, self._enums)
                
            response_class = None  
            if response_class_name:
                response_module = __import__(self._models_package, fromlist=[response_class_name])
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
     
# 命令类        
class Command:
    def __init__(self, cid1, cid2, key, name, request_class, response_class):
        self.cid1 = cid1
        self.cid2 = cid2
        self.key = key
        self.name = name
        self.request_class = request_class
        self.response_class = response_class