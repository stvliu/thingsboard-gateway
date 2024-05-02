# Copyright © 2023 The ThingsBoard Authors
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""DHT11连接器实现模块."""

import json
import time
import Adafruit_DHT
from threading import Thread, Lock
from thingsboard_gateway.connectors.connector import Connector, log    
from thingsboard_gateway.tb_utility.tb_utility import TBUtility

class Dht11Connector(Thread, Connector):
    """DHT11连接器类.
    
    继承自Thread和Connector,实现了连接器的基本功能.
    """
    
    def __init__(self, gateway, config, connector_type):
        """构造函数.
        
        Args:
            gateway: 网关对象
            config: 连接器配置信息
            connector_type: 连接器类型
        """
        super().__init__()
        self.gateway = gateway  # 网关对象
        self.config = config  # 连接器配置
        self.connector_type = connector_type  # 连接器类型
        self.devices = []  # 设备列表
        self.mutex = Lock()  # 互斥锁,用于同步访问设备数据
        self.data = {}  # 设备数据字典

        # 加载设备配置
        devices = self.config.get("devices", [])
        for device in devices:
            try:
                name = device["name"]  # 设备名称
                gpio = device["gpio"]  # GPIO引脚号
                interval = device.get("reportInterval", 5000) / 1000.0  # 数据上报间隔,单位为秒
                self.devices.append({
                    "name": name,
                    "gpio": gpio,
                    "interval": interval  
                })
                log.info("Loaded device %s, gpio: %d, interval: %.1f", name, gpio, interval)
            except Exception as e:
                log.error("Failed to load device '%s', error: %s", device, str(e))
        log.info("Loaded %d devices in total", len(self.devices))

    def run(self):
        """连接器主线程函数.
        
        定期采集所有设备的数据,并上报到Thingsboard.
        """
        while True:
            # 遍历设备列表,采集数据并上报
            for device in self.devices:
                try:
                    name = device["name"]  # 设备名称
                    gpio = device["gpio"]  # GPIO引脚号
                    interval = device["interval"]  # 数据上报间隔

                    # 读取DHT11传感器数据
                    humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, gpio)
                    if humidity is None or temperature is None:
                        log.warning("Failed to read data from device %s", name)
                        continue

                    # 同步更新设备数据  
                    self.mutex.acquire()
                    self.data[name] = {
                        "temperature": temperature,
                        "humidity": humidity
                    }
                    self.mutex.release()

                    # 上报数据到Thingsboard
                    self.__upload(name, self.data[name])
                except Exception as e:
                    log.exception(e)

                # 延时,控制数据上报频率  
                time.sleep(interval)

            log.debug("All devices processed, waiting for next round")
            time.sleep(1)

    def close(self):
        """关闭连接器."""
        log.info("Stopping DHT11 connector")
        self.stopped = True

    def get_name(self):
        """获取连接器名称.
        
        Returns:
            str: 连接器名称
        """
        return "DHT11 Connector"

    def on_attributes_update(self, content):  
        """处理Thingsboard下发的属性更新请求.
        
        Args:
            content (dict): 属性更新请求的内容
        """
        log.debug(content)
        device = content["device"]  # 设备名称
        for key, value in content["data"].items():
            if key == "reportInterval":
                try:
                    interval = int(value) / 1000.0  # 上报间隔,单位为秒
                    updated = False  
                    # 更新设备配置
                    for item in self.devices:
                        if item["name"] == device:
                            item["interval"] = interval
                            updated = True
                            break
                    
                    if updated:
                        log.info("Device %s report interval updated to %.1f", device, interval)
                except Exception as e:
                    log.exception(e)

    def __upload(self, name, data):
        """上报数据到Thingsboard.
        
        Args:
            name (str): 设备名称
            data (dict): 要上报的数据
        """  
        try:
            # 组装数据
            self.gateway.send_to_storage(self.get_name(), {
                "deviceName": name,
                "deviceType": "thermometer",  
                "telemetry": [
                    {
                        "ts": int(time.time() * 1000),
                        "values": data
                    }
                ]
            })
            log.debug("Data for device %s uploaded: %s", name, json.dumps(data))
        except Exception as e:
            log.exception(e)

    def server_side_rpc_handler(self, content):
        """处理Thingsboard下发的RPC请求.
        
        Args:
            content (dict): RPC请求的内容
        """
        try:
            device = content["device"]  # 设备名称
            # 修改数据上报间隔
            if content["data"]["method"] == "setInterval":
                interval = content["data"]["params"]["interval"]
                self.on_attributes_update({
                    "device": device,
                    "data": {"reportInterval": interval}
                })
                log.info("RPC request for device %s processed, set interval to %d", device, interval)
                self.gateway.send_rpc_reply(device, content["data"]["id"], {"success": True})
        except Exception as e:
            log.exception(e)