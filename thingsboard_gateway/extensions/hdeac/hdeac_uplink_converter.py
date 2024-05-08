"""
HDE-AIR系列机柜空调上行数据转换器，将空调上报的数据转换为Thingsboard的遥测和属性格式。  
"""

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
    
    @staticmethod
    def convert_with_config(logger, config, data):
        """
        转换上报的数据。
        
        参数:
        - logger: 日志对象
        - config: 数据配置，字典
        - data: 原始数据，字节数组
        
        返回:
        - 转换后的数据，字典  
        """
        result = {'deviceName': config['deviceName'], 'deviceType': config.get('deviceType', 'default'), 'attributes': [], 'telemetry': []}
        
        if 'attributes' in config:
            for attr in config['attributes']:
                result['attributes'].append({attr['key']: HdeAcUplinkConverter.__convert_value(logger, attr, data)})
        
        if 'timeseries' in config:        
            for ts in config['timeseries']:
                if ts['datatype'] == 'alarms':
                    # 将告警状态进行特殊处理
                    alarms = {}  
                    for alarm in ts['values']:
                        if alarm['type'] == 'alarm':
                            alarms[alarm['key']] = HdeAcUplinkConverter.__convert_alarm(alarm, data)
                        elif alarm['type'] == 'value':
                            alarms[alarm['key']] = HdeAcUplinkConverter.__convert_value(logger, alarm, data)
                    result['telemetry'].append({ts['key']: alarms})
                elif ts['datatype'] == 'bits':
                    # 将开关量状态进行特殊处理
                    bits = {}  
                    for bit in ts['values']:
                        if bit['type'] == 'bool':
                            bits[bit['key']] = HdeAcUplinkConverter.__convert_bool(bit, data) 
                    result['telemetry'].append({ts['key']: bits})
                else:
                    # 其他遥测量直接转换
                    result['telemetry'].append({ts['key']: HdeAcUplinkConverter.__convert_value(logger, ts, data)})
                
        if 'attributes_from_response' in config:
            for attr in config['attributes_from_response']:
                result['attributes'].append({attr['key']: HdeAcUplinkConverter.__convert_value(logger, attr, data)})
            
        return result
    
    @staticmethod        
    def __convert_value(logger, config, data):
        """
        转换单个值。
        
        参数:
        - logger: 日志对象  
        - config: 值的配置，字典
        - data: 原始数据，字节数组
        
        返回:
        - 转换后的值，整数或浮点数  
        """
        start = config.get('start', 0)
        length = config.get('length', 1)
        datatype = config.get('datatype', 'int8')
        factor = config.get('factor', 1)
        signed = datatype.startswith('int')
        byteorder = config.get('byteorder', 'big')
        
        try:
            value = int.from_bytes(data[start:start+length], byteorder=byteorder, signed=signed)
            return round(value * factor, 6)
        except Exception as e:
            logger.exception(e)
            return 0
        
    @staticmethod
    def __convert_bool(config, data):
        """
        转换布尔值。
        
        参数:
        - config: 布尔值配置，字典
        - data: 原始数据，字节数组
        
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
        - config: 告警配置，字典
        - data: 原始数据，字节数组
        
        返回:
        - 转换后的告警值，布尔值
        """
        start = config.get('start', 0)  
        normal_value = config.get('normal_value', 0)
        alarm_value = config.get('alarm_value', 1)
        return data[start] == alarm_value