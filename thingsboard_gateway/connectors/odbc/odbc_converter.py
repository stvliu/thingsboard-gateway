"""
DHT11连接器的数据转换器抽象基类。
This file contains the abstract base class for the DHT11 connector's data converters.
"""

from abc import ABC, abstractmethod

class Dht11Converter(ABC):
    """
    DHT11数据转换器抽象基类。
    This class represents the abstract base class for DHT11 data converters.
    """
    
    @abstractmethod
    def convert(self, config, data):
        """
        转换数据的抽象方法,所有具体的转换器类都必须实现这个方法。
        The abstract method for converting data. All concrete converter classes must implement this method.
        
        :param config: 转换器配置 (Converter configuration)
        :param data: 原始数据 (Raw data)
        :return: 转换后的数据 (Converted data)
        """
        pass