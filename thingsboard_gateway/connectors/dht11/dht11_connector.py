#     Copyright 2024. ThingsBoard
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

"""
DHT11连接器实现文件
"""

import time
import Adafruit_DHT
from threading import Thread
from thingsboard_gateway.connectors.connector import Connector
from thingsboard_gateway.tb_utility.tb_loader import TBModuleLoader
from thingsboard_gateway.tb_utility.tb_utility import TBUtility
from thingsboard_gateway.gateway.statistics_service import StatisticsService
from thingsboard_gateway.tb_utility.tb_logger import init_logger

# 定义DHT11连接器类，继承自Connector
class Dht11Connector(Thread, Connector):
    def __init__(self, gateway, config, connector_type):
        """
        DHT11连接器初始化方法
        
        :param gateway: 网关对象
        :param config: 连接器配置
        :param connector_type: 连接器类型
        """
        super().__init__()
        self.__config = config
        self.__gateway = gateway
        self.__connector_type = connector_type

        self.statistics = {'MessagesReceived': 0,'MessagesSent': 0} # 初始化统计信息
        
        self.name = config.get('name', 'DHT11 Connector')
        self._log = init_logger(gateway, self.name, config.get('logLevel', 'INFO')) # 初始化日志对象
        
        # 加载数据转换器
        self.devices = self.__config["devices"]
        self.load_converters()
        
        self.stopped = False 
        self.daemon = True

        self._log.info("Dht11Connector initialized.")
        
    def open(self):
        """
        连接器开启方法
        """
        self._log.info("Starting Dht11Connector...")
        self.start()
        self._log.info("Dht11Connector started.")
                    
    def run(self):
        """
        连接器运行方法
        """
        sensor = Adafruit_DHT.DHT11
        while not self.stopped:
            for device in self.devices:
                try:
                    # 读取DHT11传感器数据
                    # self._log.info("pin: %s", device["pin"])
                    humidity, temperature = Adafruit_DHT.read_retry(sensor, device["pin"])
                    
                    # 转换数据格式
                    data = {
                        "temperature": temperature,
                        "humidity": humidity
                    }
                    converted_data = device["converter"].convert(device, data)
                    
                    # 发送数据到ThingsBoard
                    self.__gateway.send_to_storage(self.name, self.get_id(), converted_data)
                    self.statistics['MessagesSent'] += 1
                    self._log.debug("Data to ThingsBoard: %s", converted_data)
                    time.sleep(device["pollPeriod"])
                except Exception as e:
                    self._log.exception(e)

    def close(self):
        """
        连接器关闭方法
        """
        self._log.info("Stopping Dht11Connector...")
        self.stopped = True
    
    def get_name(self):
        """
        获取连接器名称
        """
        return self.name
    
    def get_id(self):
        """
        获取连接器ID
        """
        return self.__config.get("id", "dht11")
    
    def is_connected(self):
        """
        连接器是否已连接
        """
        return not self.stopped
    
    def get_config(self):
        """
        获取连接器配置
        """
        return self.__config
    
    def get_type(self):
        """
        获取连接器类型
        """
        return self.__connector_type
    
    def is_stopped(self):
        """
        连接器是否已停止
        """
        return self.stopped
    
    @StatisticsService.CollectAllReceivedBytesStatistics(start_stat_type='allReceivedBytesFromTB')
    def on_attributes_update(self, content):
        """
        处理属性更新
        """
        self._log.debug("Received attributes update request: %s", content)

    @StatisticsService.CollectAllReceivedBytesStatistics(start_stat_type='allReceivedBytesFromTB')
    def server_side_rpc_handler(self, content):
        """
        处理服务端RPC请求
        """
        self._log.debug("Received RPC request: %s", content)
        
    def load_converters(self):
        """
        加载数据转换器
        """
        self._log.debug("Loading converters...")
        for device in self.devices:
            try:
                converter_class = device["converter"]
                device["converter"] = TBModuleLoader.import_module(self.__connector_type,
                                                                   converter_class)(device, log=self._log)
                self._log.debug("Converter %s loaded.", converter_class)
            except Exception as e:
                self._log.error("Failed to load converter %s", converter_class)
                self._log.exception(e)
        self._log.debug("Converters loading done.")
