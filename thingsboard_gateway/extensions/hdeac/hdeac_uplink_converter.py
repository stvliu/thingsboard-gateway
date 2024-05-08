"""  
HDE-AIR系列机柜空调上行数据转换器,将空调上报的数据转换为Thingsboard的遥测和属性格式。
"""

import struct
from thingsboard_gateway.connectors.converter import Converter


class HdeAcUplinkConverter(Converter):
    def __init__(self, logger):  
        self.__logger = logger
        
    def convert(self, config, data):
        try:
            result = HdeAcUplinkConverter.convert_with_config(self.__logger, config, data)
            return result  
        except Exception as e:
            self.__logger.exception(e) 
            return {}
            
    def convert_history_alarms(self, config, data):  
        try:
            result = {'deviceName': config['deviceName'], 'deviceType': config.get('deviceType', 'default'), 'alarms': []}
            
            # 解析历史告警数据
            for i in range(len(data) // 8):
                alarm_data = data[i*8:(i+1)*8]  
                alarm = {}
                alarm['timestamp'] = struct.unpack('>I', alarm_data[:4])[0]
                alarm['values'] = []
                
                for alarm_config in config.get('values', []):
                    value = HdeAcUplinkConverter.__convert_alarm(alarm_config, alarm_data[4:])
                    if value is not None:  
                        alarm['values'].append({alarm_config['key']: value})
                        
                result['alarms'].append(alarm)
                
            return result
        except Exception as e:
            self.__logger.exception(e)
            return {}
            
    def parse_version(self, data):
        try:  
            if len(data) >= 2:
                version = int.from_bytes(data[0:2], byteorder='big') 
                return version  
        except Exception as e:
            self.__logger.exception(e)
        return None
        
    def parse_address(self, data):
        try:
            if len(data) >= 1:
                addr = data[0]  
                return addr
        except Exception as e:  
            self.__logger.exception(e)
        return None
    
    @staticmethod
    def convert_with_config(logger, config, data):
        """
        转换上报的数据。
        
        参数:
        - logger: 日志对象
        - config: 数据配置,字典
        - data: 原始数据,字节数组
        
        返回:
        - 转换后的数据,字典
        """
        result = {'deviceName': config['deviceName'], 'deviceType': config.get('deviceType', 'default'), 'attributes': [], 'telemetry': []}
        
        if 'attributes_from_response' in config:  
            for attr in config['attributes_from_response']:
                result['attributes'].append({attr['key']: HdeAcUplinkConverter.__convert_value(logger, attr, data)})
        
        if 'timeseries' in config:
            for ts in config['timeseries']:  
                if ts['datatype'] == 'bits':
                    # 将开关量状态进行特殊处理  
                    bits = {}
                    for bit in ts['values']:  
                        if bit['type'] == 'bool':
                            bits[bit['key']] = HdeAcUplinkConverter.__convert_bool(bit, data)
                    result['telemetry'].append({ts['key']: bits})
                else:
                    # 其他遥测量直接转换
                    result['telemetry'].append({ts['key']: HdeAcUplinkConverter.__convert_value(logger, ts, data)})
                
        if 'attributes' in config:
            for attr in config['attributes']:
                if attr['datatype'] == 'alarms':
                    # 将告警状态进行特殊处理
                    alarms = {}
                    for alarm in attr['values']:
                        if alarm['type'] == 'alarm':
                            alarms[alarm['key']] = HdeAcUplinkConverter.__convert_alarm(alarm, data)
                        elif alarm['type'] == 'value':
                            alarms[alarm['key']] = HdeAcUplinkConverter.__convert_value(logger, alarm, data)
                    result['attributes'].append({attr['key']: alarms})
                else:
                    result['attributes'].append({attr['key']: HdeAcUplinkConverter.__convert_value(logger, attr, data)})                  
            
        return result
    
    @staticmethod        
    def __convert_value(logger, config, data):  
        """
        转换单个值。
        
        参数:
        - logger: 日志对象
        - config: 值的配置,字典  
        - data: 原始数据,字节数组
        
        返回:
        - 转换后的值,整数、浮点数、布尔值或字符串
        """  
        start = config.get('start', 0)
        length = config.get('length', 1)
        datatype = config.get('datatype', 'int8')
        factor = config.get('factor', 1)
        signed = datatype.startswith('int')
        byteorder = config.get('byteorder', 'big')
        
        try:
            if datatype.startswith('float'):
                # 浮点数
                value = struct.unpack_from('>f' if byteorder == 'big' else '<f', data, start)[0]
            elif datatype.startswith('int'):  
                # 整型数
                value = int.from_bytes(data[start:start+length], byteorder=byteorder, signed=signed)
            elif datatype.startswith('uint'):
                # 无符号整型数  
                value = int.from_bytes(data[start:start+length], byteorder=byteorder, signed=False)
            elif datatype == 'bool':
                # 布尔型
                value = bool(data[start])
            elif datatype == 'string':
                # 字符串  
                value = data[start:start+length].decode('ascii')
            elif datatype == 'bcd':
                # BCD码
                value = int(data[start:start+length].hex())
            elif datatype == 'time':
                # 时间
                year = int.from_bytes(data[start:start+2], byteorder=byteorder)
                month = data[start+2]
                day = data[start+3]
                hour = data[start+4]
                minute = data[start+5]
                second = data[start+6]
                value = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
            else:
                logger.warning('Unsupported data type: %s', datatype)
                return None
                
            return round(value * factor, 6)
        except Exception as e:
            logger.exception(e)  
            return None
        
    @staticmethod
    def __convert_bool(config, data):
        """  
        转换布尔值。
        
        参数:
        - config: 布尔值配置,字典
        - data: 原始数据,字节数组
        
        返回:  
        - 转换后的布尔值
        """
        start = config.get('start', 0)
        on_value = config.get('on_value', 1)
        return data[start] == on_value
    
    @staticmethod  
    def __convert_alarm(config, data):
        """
        转换告警值。
        
        参数:  
        - config: 告警配置,字典
        - data: 原始数据,字节数组
        
        返回:
        - 转换后的告警值,布尔值  
        """
        start = config.get('start', 0)
        normal_value = config.get('normal_value', 0) 
        alarm_value = config.get('alarm_value', 1)
        return data[start] == alarm_value