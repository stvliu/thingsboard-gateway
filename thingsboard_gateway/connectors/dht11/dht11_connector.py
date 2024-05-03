"""
文件名:dht11_connector.py
功能:通过Adafruit_DHT库读取DHT11传感器数据,并将数据转换为ThingsBoard平台要求的格式
"""

import Adafruit_DHT
import time

from thingsboard_gateway.connectors.connector import Connector, log
from thingsboard_gateway.tb_utility.tb_utility import TBUtility


class Dht11Connector(Connector):
    """
    DHT11连接器类,继承自Connector基类
    负责通过Adafruit_DHT库读取DHT11传感器数据,并将数据转换为ThingsBoard平台要求的格式
    """

    def __init__(self, gateway, config, connector_type):
        """
        初始化方法
        
        Args:
            gateway (TBGatewayService): 网关服务对象
            config (dict): 连接器配置信息
            connector_type (str): 连接器类型(取值为"dht11")
        """
        super().__init__()
        self.gateway = gateway
        self.__config = config
        self.__connector_type = connector_type
        self.setName(config.get("name", "DHT11 Connector"))
        
        self.devices = {}
        self.__load_converters()
        self.__last_update_time = 0
        self.__update_period = self.__config['devices'][0].get('updatePeriod', 5)  # 默认更新周期为5秒
        
        log.info("Dht11 Connector initialized.")

    def __load_converters(self):
        """
        加载数据转换器
        """
        devices_config = self.__config.get('devices')
        if devices_config is not None:
            for device_config in devices_config:
                device_name = device_config['name']
                converter_name = device_config['converter']
                
                # 加载数据转换器
                converter = TBUtility.check_and_import(self.__connector_type, converter_name)
                if converter is not None:
                    # 保存数据转换器实例和传感器引脚
                    self.devices[device_name] = {
                        'converter': converter(device_config),
                        'pin': device_config['pinNumber']
                    }
                    log.info(f'[{device_name}] Data converter {converter_name} loaded.')
                else:
                    log.error(f'[{device_name}] Failed to load data converter {converter_name}.')
        else:
            log.error('No devices found in configuration.')

    def open(self):
        """
        连接器开启方法,开启连接器时被调用
        """
        log.info("Starting Dht11 Connector...")
        self.__last_update_time = time.time()
        self.gateway.add_device(self.getName(), {"connector": self})
        self.connected = True

    def close(self):
        """
        连接器关闭方法,关闭连接器时被调用
        """
        self.connected = False
        log.info("Dht11 Connector stopped.")
        self.gateway.send_connector_status(self.getName(), 'Offline')

    def get_name(self):
        """
        获取连接器名称的方法
        
        Returns:
            str: 连接器名称
        """
        return self.name

    def is_connected(self):
        """
        获取连接器连接状态的方法
        
        Returns:
            bool: 连接器当前是否已连接
        """
        return self.connected

    def on_attributes_update(self, content):
        """
        处理属性更新请求的方法
        
        Args:
            content (dict): 属性更新请求的内容
        """
        log.debug(f"Received attributes update request: {content}")
        device_name = content['device']
        for attribute_key, attribute_value in content['data'].items():
            log.debug(f"Updating attribute for device {device_name}: {attribute_key} = {attribute_value}")
            # 在此处理属性更新请求,比如更新设备的属性值

    def server_side_rpc_handler(self, content):
        """
        处理服务端RPC请求的方法
        
        Args:
            content (dict): RPC请求的内容
        """
        log.debug(f"Received RPC request: {content}")
        device_name = content['device']
        # 在此处理RPC请求,比如调用设备的方法

    def collect_and_send_data(self):
        """
        采集并发送DHT11传感器数据
        """
        for device_name, device_config in self.devices.items():
            pin = device_config['pin']
            
            # 读取DHT11传感器数据
            humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, pin)
            
            if humidity is None or temperature is None:
                log.error(f'[{device_name}] Failed to read data from DHT11 sensor (pin {pin}).')
                continue
            else:
                log.debug(f'[{device_name}] Temperature: {temperature}°C, Humidity: {humidity}%')
            
            # 封装传感器数据
            data = {
                'temperature': temperature,
                'humidity': humidity
            }
            
            # 转换传感器数据格式
            converter = device_config['converter']
            converted_data = converter.convert(device_config, data)
            
            # 发送数据到ThingsBoard平台
            self.gateway.send_to_storage(self.getName(), converted_data)

    def run(self):
        """
        连接器的主要逻辑,在独立的线程中运行
        """
        log.info("Dht11 Connector started.")
        self.gateway.send_connector_status(self.getName(), 'Running')
        
        while True:
            if self.connected:
                current_time = time.time()
                
                # 判断是否达到数据采集的时间间隔
                if current_time - self.__last_update_time >= self.__update_period:
                    self.collect_and_send_data()
                    self.__last_update_time = current_time
                else:
                    time.sleep(1)
            else:
                time.sleep(1)