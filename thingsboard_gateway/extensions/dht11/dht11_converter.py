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
DHT11数据转换器实现文件
"""

from thingsboard_gateway.connectors.converter import Converter

# 定义DHT11上行数据转换器类，继承自Converter
class Dht11Converter(Converter):
    def __init__(self, config, log):
        """
        DHT11上行数据转换器初始化方法
        
        :param config: 转换器配置
        :param log: 日志对象
        """
        self._log.info("=========Dht11Converter start initializing.===========")
        self.__config = config
        self._log = log
        self._log.info("=========Dht11Converter initialized.=========")

    def convert(self, device, data):
        """
        转换数据
        
        :param device: 设备配置
        :param data: 原始数据
        :return: 转换后的数据
        """
        result = {
            "deviceName": device["name"],
            "deviceType": "thermometer",
            "telemetry": []
        }
        for telemetry in device["telemetry"]:
            key = telemetry["key"]
            if key in data:
                value = data[key]
                result["telemetry"].append({key: value})
                self._log.debug("Converted telemetry '%s': %s", key, value)
            else:
                self._log.error("Telemetry '%s' not found in data: %s", key, data)
        self._log.info("=========Dht11Converter convert done=======")
        return result
