"""
DL/T 643下行转换器
本模块提供了将Thingsboard平台下发的RPC命令转换为DL/T 643格式的功能。
"""

import json
from thingsboard_gateway.connectors.converter import Converter, log
import dlt643_converter
        
class DLT643DownlinkConverter(Converter):
    def __init__(self, config):
        """
        初始化转换器
        :param config: 转换器配置
        """
        self.__config = config.get("downlink_converter", {})
        self.rpc_topic = self.__config.get("rpc_topic", "v1/devices/me/rpc/request/+")
        self.rulesets = []
        self.__load_converters()
        
    def __load_converters(self):
        """
        加载转换规则
        """
        self.rulesets = self.__config.get("rulesets", [])
        log.info("Loaded %d RPC converter rulesets", len(self.rulesets))
        
    def convert(self, _, body):
        """
        转换RPC命令为DL/T 643格式
        :param _: 主题(未使用)
        :param body: RPC命令内容
        """
        try:
            rpc = json.loads(body)
            method = rpc["method"]
            params = rpc["params"]
            
            log.debug("Received RPC: %s", method)
            
            for ruleset in self.rulesets:
                if ruleset["rpc_method"] == method:
                    converter = getattr(dlt643_converter, method)
                    return converter(params, ruleset)
                
            log.warning("No converter found for RPC method %s", method)
            return None
        except Exception as e:
            log.exception(e)
            return None