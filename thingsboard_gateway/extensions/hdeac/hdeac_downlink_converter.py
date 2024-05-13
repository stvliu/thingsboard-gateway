"""
HDE-AIR系列机柜空调下行数据转换器，将属性和RPC参数转换为空调支持的控制命令格式。  
"""

import struct
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
            
    def convert_version_command(self, config):
        """
        转换获取通信协议版本号命令。
        
        参数:
        - config: 协议版本号命令配置，字典
        
        返回:  
        - 转换后的控制命令，字节数组
        """
        try:
            command = HdeAcDownlinkConverter.convert_object(self.__logger, config, 'command')
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
        - config: 参数配置,字典
        - key: 要转换的参数名称
        
        返回:
        - 转换后的字节数组  
        """
        value = config[key]
        if isinstance(value, str) and value.startswith('0x'):
            try:
                return bytearray.fromhex(value[2:])  
            except Exception as e:
                logger.exception(e)
                return bytearray()
        elif isinstance(value, list):
            return bytearray(value)  
        elif isinstance(value, bytearray):
            return value
        else:
            logger.warning('Unsupported config value type: %s', type(value))
            return bytearray()
        
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
            if 'params' in data:
                # 如果是遥控命令，则直接使用params作为参数
                if 'method' in data:
                    command = bytearray(HdeAcDownlinkConverter.convert_object(logger, config, 'set_command'))
                    params_value = HdeAcDownlinkConverter.__convert_value(logger, data)
                    if params_value is not None:
                        command.extend(params_value)
                else:
                    command = bytearray(HdeAcDownlinkConverter.convert_object(logger, config, 'command'))
                    params_value = HdeAcDownlinkConverter.__convert_value(logger, data)
                    if params_value is not None:
                        command.extend(params_value)
            elif 'set_command' in config:
                # 如果是设置参数命令，则根据set_command构造命令
                command = bytearray(HdeAcDownlinkConverter.convert_object(logger, config, 'set_command'))
                params_value = HdeAcDownlinkConverter.__convert_value(logger, data)
                if params_value is not None:
                    command.extend(params_value)
            else:
                # 其他命令直接使用command
                command = bytearray(HdeAcDownlinkConverter.convert_object(logger, config, 'command'))
                return command
        except Exception as e:
            logger.exception(e)
            return b''

    @staticmethod    
    def __convert_value(logger, data):
        """  
        转换属性或参数的值。
        
        参数:
        - logger: 日志对象
        - data: 属性或参数的值,字典
        
        返回:
        - 转换后的值,字节数组  
        """
        value = data.get('params') 
        if value is None:
            return None
            
        datatype = data.get('datatype', 'int8')
        factor = data.get('factor', 1)
        byteorder = data.get('byteorder', 'big') 
        length = data.get('length', 1)
        signed = datatype.startswith('int') 
        
        try:
            if datatype.startswith('float'):
                # 浮点数
                value = float(value) / factor
                return struct.pack('>f' if byteorder == 'big' else '<f', value)
            elif datatype.startswith('int'):
                # 整型数  
                value = int(value) // factor                                                
                return value.to_bytes(length, byteorder=byteorder, signed=signed)
            elif datatype == 'bool':
                # 布尔型
                value = bool(value)
                return struct.pack('?', value)
            elif datatype.startswith('string'):
                # 字符串
                value = str(value)
                return value.encode('ascii') 
            else:
                logger.warning('Unsupported data type: %s', datatype)  
                return None
        except Exception as e:
            logger.exception(e)
            return None