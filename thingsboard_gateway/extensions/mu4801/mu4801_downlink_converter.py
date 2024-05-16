"""
MU4801下行数据转换器
该转换器用于将Thingsboard下发的控制命令转换为MU4801设备能识别的格式。
"""

import struct
from io import BytesIO
from thingsboard_gateway.connectors.converter import Converter


class Mu4801DownlinkConverter(Converter):
    """
    MU4801下行数据转换器类
    继承自Converter基类
    """
    
    def __init__(self, connector, log):
        """
        初始化下行数据转换器
        
        参数:
        connector: 连接器对象
        log: 日志对象
        """
        self.__connector = connector
        self._log = log
        # 无需设备响应的方法列表
        self.unidirectional_methods = ['setLoadSwitch', 'setRectifierModule', 'setBatterySwitch', 'resetSystem', 'setDateTime']
        # 数据类型配置
        self.__datatypes = {
            'int16': {'size': 2, 'struct': 'h', 'byteorder': 'big', 'signed': True},
            'uint16': {'size': 2, 'struct': 'H', 'byteorder': 'big', 'signed': False},
            'int32': {'size': 4, 'struct': 'i', 'byteorder': 'big', 'signed': True},
            'uint32': {'size': 4, 'struct': 'I', 'byteorder': 'big', 'signed': False},
            'uint8': {'size': 1, 'struct': 'B', 'byteorder': 'big', 'signed': False},
            'float': {'size': 4, 'struct': 'f', 'byteorder': 'big', 'signed': True},
            'boolean': {'size': 1, 'struct': 'B', 'byteorder': 'big', 'signed': False},
            'string': {'size': None, 'struct': None, 'byteorder': None, 'signed': False}
        }

    def convert(self, config, data):
        """
        将控制命令转换为设备能识别的格式
        
        参数:
        config: 命令配置(包含命令模板、数据帧模板等)
        data: 控制命令数据
        
        返回:
        转换后的控制命令(字节串)
        """
        # 获取命令模板
        command_hex = config['command']
        # 获取数据帧模板
        frame_template = config['frame_template']
        
        # 构建数据帧
        buffer = BytesIO()
        
        # 遍历数据帧模板,逐个字段进行转换
        for param_config in frame_template:
            # 参数名
            name = param_config['name']
            # 参数数据类型
            value_type = param_config['dataType']
            
            # 优先从命令数据中获取参数值,其次从配置中获取
            if name in data['value']:
                value = data['value'][name]
            elif name in data:
                value = data[name]
            else:
                self._log.warning(f"Parameter '{name}' not found in data: {data}")
                continue
                
            # 获取数据类型配置
            datatype_config = self.__datatypes.get(value_type)
            if not datatype_config:
                self._log.error(f"Unsupported data type: {value_type}")
                continue
        
            if value_type == 'boolean':
                # 布尔类型需转换为整数
                bool_map = param_config.get('booleanMap', {'true': 1, 'false': 0})
                value = bool_map.get(str(value).lower(), value)
            
            if datatype_config['size'] is None:
                # 字符串类型直接写入缓冲区
                buffer.write(value.encode('ascii'))
            else:
                # 数值类型按指定的格式打包并写入缓冲区
                byteorder = datatype_config['byteorder']
                signed = datatype_config['signed']
                struct.pack_into(byteorder + datatype_config['struct'], buffer.getbuffer(), buffer.tell(), value)
                buffer.seek(datatype_config['size'], 1)
                
        # 将数据帧插入命令模板
        data_hex = buffer.getvalue().hex()
        command = bytes.fromhex(command_hex.format(data=data_hex))
        
        self._log.debug(f"Converted RPC command: {command.hex()}")
        return command

    def convert_rectifier_settings(self, config, data):
        """
        将整流模块设置转换为设备能识别的格式
        
        参数:
        config: 命令配置(包含命令模板、数据帧模板等)
        data: 整流模块设置数据
        
        返回:
        转换后的整流模块设置命令(字节串)
        """
        command_hex = config['command']
        frame_template = config['frame_template']
        
        # 构建数据帧
        buffer = BytesIO()
        
        # 遍历数据帧模板,逐个字段进行转换
        for param_config in frame_template:
            name = param_config['name']
            value_type = param_config['dataType']
            
            # 优先从命令数据中获取参数值,其次从配置中获取
            if name in data['value']:
                value = data['value'][name]
            elif name in data:
                value = data[name]
            else:
                self._log.warning(f"Parameter '{name}' not found in data: {data}")
                continue
                
            datatype_config = self.__datatypes.get(value_type)
            if not datatype_config:
                self._log.error(f"Unsupported data type: {value_type}")
                continue
        
            if value_type == 'boolean':
                # 布尔类型需转换为整数
                bool_map = param_config.get('booleanMap', {'true': 1, 'false': 0})
                value = bool_map.get(str(value).lower(), value)
            
            if datatype_config['size'] is None:
                # 字符串类型直接写入缓冲区
                buffer.write(value.encode('ascii'))
            else:
                # 数值类型按指定的格式打包并写入缓冲区
                byteorder = datatype_config['byteorder']
                signed = datatype_config['signed']
                struct.pack_into(byteorder + datatype_config['struct'], buffer.getbuffer(), buffer.tell(), value)
                buffer.seek(datatype_config['size'], 1)
                
        # 将数据帧插入命令模板
        data_hex = buffer.getvalue().hex()
        command = bytes.fromhex(command_hex.format(data=data_hex))
        
        self._log.debug(f"Converted rectifier settings command: {command.hex()}")
        return command
            
    @staticmethod
    def config_from_type(config):
        """
        根据参数类型修改配置中的参数值
        
        参数:
        config: 配置(dict)
        
        返回:
        修改后的配置(dict)
        """
        for key, value in config.items():
            if isinstance(value, str):
                if value.startswith("${") and value.endswith("}"):
                    # 将${...}形式的字符串转换为表达式并求值
                    value = eval(value[2:-1])
                config[key] = value
        return config