"""
DHT11连接器的上行数据转换器。
This file contains the uplink data converter for the DHT11 connector.
"""

from thingsboard_gateway.gateway.statistics_service import StatisticsService

# 导入Dht11Converter类 (Import Dht11Converter class)
from thingsboard_gateway.connectors.dht11.dht11_converter import Dht11Converter

class Dht11UplinkConverter(Dht11Converter):
    """
    DHT11上行数据转换器类,继承自Dht11Converter。
    This class represents the DHT11 uplink data converter and inherits from Dht11Converter.
    """
    
    def __init__(self, config=None, log=None):
        """
        初始化方法,设置转换器的配置和日志。
        Initializes the converter with the given configuration and logger.
        
        :param config: 转换器配置 (Converter configuration)
        :param log: 日志对象 (Logger object)
        """
        self.__config = config
        self._log = log

    @StatisticsService.CollectStatistics(start_stat_type='receivedBytesFromDevices',
                                         end_stat_type='convertedBytesFromDevice')
    def convert(self, config, data):
        """
        转换数据的方法,将原始数据转换为ThingsBoard接受的格式。
        Converts the raw data into the format accepted by ThingsBoard.
        
        :param config: 转换器配置 (Converter configuration)
        :param data: 原始数据 (Raw data)
        :return: 转换后的数据 (Converted data)
        """
        result = {
            'deviceName': data.get('name', 'unknown'), # 从 data 字典中获取 'name' 作为 'deviceName'
            'deviceType': config.get('deviceType', 'thermometer'),
            'telemetry': [],
            'attributes': []
        }
        
        result['telemetry'].append({
            'ts': data['ts'],
            'values': {
                'temperature': data['temperature'],
                'humidity': data['humidity']
            }
        })
        
        return result