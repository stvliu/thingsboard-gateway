"""
HDE-AIR系列机柜空调下行数据转换器，将属性和RPC参数转换为空调支持的控制命令格式。
"""

from thingsboard_gateway.connectors.converter import Converter


class HdeAcDownlinkConverter(Converter):
    def __init__(self, logger):
        self.__logger = logger
        
    def convert(self, config, data):
        """
        将属性或RPC参数转换为控制命令。
        
        参数:
        - config: 命令配置，字典
        - data: 属性或RPC参数，字典
        
        返回:
        - 转换后的控制命令，字节数组
        """
        try:
            command = HdeAcDownlinkConverter.convert_command(self.__logger, config, data)
            return command
        except Exception as e:
            self.__logger.exception(e)
            return b''
        
    @staticmethod    
    def convert_object(logger, config, key):
        """
        转换配置中的对象类型参数。
        
        参数:
        - logger: 日志对象
        - config: 参数配置，字典
        - key: 要转换的参数名称
        
        返回:
        - 转换后的字节数组
        """
        value = config[key]
        if isinstance(value, str) and value.startswith('0x'):
            try:
                return bytes.fromhex(value[2:])
            except Exception as e:
                logger.exception(e)
                return b''  
        else:
            return bytearray(value)
        
    @staticmethod    
    def convert_command(logger, config, data):
        """
        转换下发的控制命令。
        
        参数:
        - logger: 日志对象
        - config: 命令配置，字典
        - data: 属性或RPC参数，字典
        
        返回:
        - 转换后的控制命令，字节数组
        """
        try:
            command = bytearray(HdeAcDownlinkConverter.convert_object(logger, config, 'command'))
            command.extend(HdeAcDownlinkConverter.__convert_value(data))
            return command
        except Exception as e:
            logger.exception(e)
            return b''
    
    @staticmethod    
    def __convert_value(data):  
        """
        转换属性或参数的值。
        
        参数:
        - data: 属性或参数的值，字典
        
        返回:  
        - 转换后的值，字节数组
        """
        value = data.get('params', 0)
        datatype = data.get('datatype', 'int8')
        factor = data.get('factor', 1)
        
        value = int(float(value) / factor)
        signed = datatype.startswith('int')
        byteorder = data.get('byteorder', 'big')
        length = data.get('length', 1)
        
        try:
            return value.to_bytes(length, byteorder=byteorder, signed=signed)
        except Exception as e:
            logger.exception(e)
            return b'\x00' * length