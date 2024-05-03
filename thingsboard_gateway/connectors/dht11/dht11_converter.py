"""
文件名：dht11_converter.py
功能：将DHT11连接器读取到的原始数据转换为ThingsBoard平台要求的格式
"""

from thingsboard_gateway.connectors.converter import Converter


class DHT11Converter(Converter):
    """
    DHT11转换器类,继承自Converter基类
    负责将DHT11连接器读取到的原始数据转换为ThingsBoard平台要求的格式
    """

    def __init__(self, config, log):
        """
        初始化方法
        
        Args:
            config (dict): 转换器配置信息
            log (TBLogger): 日志对象
        """
        self.__config = config
        self._log = log

    def convert(self, config, data):
        """
        转换方法,将原始数据转换为ThingsBoard平台要求的格式
        
        Args:
            config (dict): 转换器配置信息
            data (dict): 原始数据,格式为 {'temperature': xxx, 'humidity': xxx}
            
        Returns:
            dict: 转换后的数据,格式为 {'deviceName': 'xxx', 'deviceType': 'xxx', 'telemetry': [{'temperature': xxx}, {'humidity': xxx}]}
        """
        device_name = self.__config['deviceName']
        device_type = self.__config['deviceType']
        telemetry = []
        
        for item in self.__config['telemetry']:
            key = item['key']
            if key in data:
                telemetry.append({key: data[key]})
            else:
                self._log.warning(f'Key "{key}" not found in data: {data}')
        
        return {
            'deviceName': device_name,
            'deviceType': device_type,
            'telemetry': telemetry
        }