"""
DHT11连接器的主要实现文件。
This file contains the main implementation of the DHT11 connector.
"""

import time
import Adafruit_DHT
from threading import Thread
from thingsboard_gateway.connectors.connector import Connector
from thingsboard_gateway.extensions.dht11.dht11_uplink_converter import Dht11UplinkConverter
from thingsboard_gateway.tb_utility.tb_loader import TBModuleLoader
from thingsboard_gateway.gateway.statistics_service import StatisticsService
from thingsboard_gateway.tb_utility.tb_logger import init_logger

class Dht11Connector(Connector, Thread):
    """
    DHT11连接器类,继承自Connector和Thread。
    This class represents the DHT11 connector and inherits from Connector and Thread.
    """
    
    def __init__(self, gateway, config, connector_type):
        """
        初始化方法,设置连接器的配置、网关和类型。
        Initializes the connector with the given configuration, gateway, and connector type.
        
        :param gateway: 网关对象 (ThingsBoard gateway object)
        :param config: 连接器配置 (Connector configuration)
        :param connector_type: 连接器类型 (Connector type)
        """
        super().__init__()
        self.daemon = True
        self._log = init_logger(gateway, config.get('name', connector_type), config.get('logLevel', 'INFO'))
        
        self.__config = config
        self.__gateway = gateway
        self.__connector_type = connector_type
        self.__stopped = False
        self.__devices = self.__config["devices"]
        self.__id = self.__config.get("id", "dht11") # 初始化连接器ID (Initialize connector ID)
        
        self.statistics = {'MessagesReceived': 0, 'MessagesSent': 0}
        self.name = config.get('name', 'DHT11 Connector')

        # 加载上行数据转换器 (Load uplink data converter)
        self.__converter = Dht11UplinkConverter() if not self.__config.get("converter", "") else \
            TBModuleLoader.import_module(self.__connector_type, self.__config["converter"])
        
        self._log.info("[%s] Initialization success.", self.get_name())
        
    def open(self):
        """
        开启连接器。
        Opens the connector.
        """
        self._log.info("[%s] Starting...", self.get_name())
        self.__stopped = False
        self.start()

    def close(self):
        """
        关闭连接器。
        Closes the connector.
        """
        if not self.__stopped:
            self.__stopped = True  
            self._log.info("[%s] Stopping", self.get_name())
            self._log.reset()
        
    def get_name(self):
        """
        获取连接器名称。
        Returns the name of the connector.
        
        :return: 连接器名称 (Connector name)
        """
        return self.name
    
    def get_id(self):
        """
        获取连接器的ID。
        Returns the ID of the connector.
        
        :return: 连接器的ID (Connector ID)
        """
        return self.__id
    
    def is_connected(self):
        """
        检查连接器是否已连接。
        Checks if the connector is connected.
        
        :return: 如果连接器已连接,返回True;否则,返回False (True if the connector is connected, False otherwise)
        """
        return not self.__stopped
    
    def on_attributes_update(self, content):
        """
        处理属性更新。在这个连接器中,这个方法为空。
        Handles attributes update. In this connector, this method is empty.
        
        :param content: 属性更新的内容 (Content of the attributes update)
        """
        pass
    
    def server_side_rpc_handler(self, content):
        """
        处理服务端RPC请求。在这个连接器中,这个方法为空。
        Handles server-side RPC requests. In this connector, this method is empty.
        
        :param content: RPC请求的内容 (Content of the RPC request)
        """
        pass

    def get_config(self):
        """
        获取连接器的配置。
        Returns the configuration of the connector.
        
        :return: 连接器的配置 (Connector configuration)
        """
        return self.__config

    def get_type(self):
        """
        获取连接器的类型。
        Returns the type of the connector.
        
        :return: 连接器的类型 (Connector type)
        """
        return self.__connector_type

    def is_stopped(self):
        """
        检查连接器是否已停止。
        Checks if the connector is stopped.
        
        :return: 如果连接器已停止,返回True;否则,返回False (True if the connector is stopped, False otherwise)
        """
        return self.__stopped

    def run(self):
        """
        连接器的主要运行逻辑。循环读取配置的设备,获取传感器数据,并将其发送到ThingsBoard。
        The main running logic of the connector. It loops through the configured devices, retrieves sensor data, and sends it to ThingsBoard.
        """
        while not self.__stopped:
            for device in self.__devices:
                try:
                    # 读取DHT11传感器数据 (Read data from the DHT11 sensor)
                    humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, device['pin'])
                    
                    if humidity and temperature:
                        data = {'name': device['name'], 'temperature': temperature, 'humidity': humidity, 'ts': int(time.time() * 1000)}
                        # 转换数据格式 (Convert data format)
                        
                        converted_data = self.__converter.convert(device, data)
    
                        # 发送数据到ThingsBoard (Send data to ThingsBoard)
                        self.__gateway.send_to_storage(self.name, self.get_id(), converted_data)
                        #self.__gateway.send_to_storage(self.name, device['name'], converted_data)
                        self.statistics['MessagesSent'] += 1
                        self._log.debug("[%s] Data to ThingsBoard: %s", self.get_name(), converted_data)
                    else:
                        self._log.warning('[%s] Could not read data from DHT11 sensor.', self.get_name())
                        
                except Exception as e:
                    self._log.exception(e)
                    
                # 等待指定的轮询周期 (Wait for the specified polling period)
                time.sleep(device.get('pollPeriod', 1))

        self.__stopped = False
        self._log.info("[%s] Stopped.", self.get_name())