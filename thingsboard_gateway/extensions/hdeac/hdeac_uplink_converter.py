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
        result = {'deviceName': config['deviceName'], 'deviceType': 'hde-ac', 'attributes': [], 'telemetry': []}
        
        if 'attributes' in config:
            for attr in config['attributes']:
                result['attributes'].append({attr['key']: HdeAcUplinkConverter.__convert_value(logger, attr, data)})
        
        if 'timeseries' in config:        
            for ts in config['timeseries']:
                if ts['datatype'] == 'alarms':
                    alarms = {}  
                    for alarm in ts['values']:
                        if alarm['type'] == 'alarm':
                            alarms[alarm['key']] = HdeAcUplinkConverter.__convert_alarm(alarm, data)
                    result['telemetry'].append({ts['key']: alarms})
                elif ts['datatype'] == 'uint8':
                    values = {}
                    for value in ts['values']:
                        values[value['key']] = HdeAcUplinkConverter.__convert_value(logger, value, data) 
                    result['telemetry'].append({ts['key']: values})
                else:
                    result['telemetry'].append({ts['key']: HdeAcUplinkConverter.__convert_value(logger, ts, data)})
        
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
            return value * factor
        except Exception as e:
            logger.exception(e)
            return 0
    
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