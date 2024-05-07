"""
文件: ydt1363_connector.py
描述: YD/T 1363.3-2015协议连接器,用于通过Thingsboard IoT Gateway采集和控制支持YD/T 1363.3-2015协议的设备。
"""

import time
import socket
import struct
from threading import Thread
from random import choice
from string import ascii_lowercase

from thingsboard_gateway.connectors.connector import Connector
from thingsboard_gateway.tb_utility.tb_utility import TBUtility
from ydt1363_uplink_converter import YDT1363UplinkConverter
from ydt1363_downlink_converter import YDT1363DownlinkConverter
from thingsboard_gateway.tb_utility.tb_logger import init_logger


class YDT1363Connector(Thread, Connector):
    """
    YDT1363Connector类,继承自Thread和Connector,实现了YD/T 1363.3协议的连接器功能。
    """

    def __init__(self, gateway, config, connector_type):
        """
        初始化YDT1363Connector连接器。
        
        参数:
        - gateway: Gateway对象,连接器所属的Gateway实例。
        - config: dict,连接器配置信息。
        - connector_type: str,连接器类型。
        """
        super().__init__()
        self.daemon = True

        # Gateway对象,连接器所属的Gateway实例
        self.__gateway = gateway
        # 连接器类型
        self._connector_type = connector_type
        # 连接器配置信息
        self.__config = config
        # 连接器名称,默认为"YDT1363 Connector"加上5个随机小写字母
        self.name = config.get("name", 'YDT1363 Connector ' + ''.join(choice(ascii_lowercase) for _ in range(5)))
        # 日志对象,通过init_logger函数初始化
        self._log = init_logger(gateway, self.name, self.__config.get('logLevel', 'INFO'))
        # 需要连接的设备信息列表
        self.__devices = self.__config["devices"]
        # 连接器的统计信息
        self.statistics = {'MessagesReceived': 0, 'MessagesSent': 0}
        # 连接超时时间,默认为30秒
        self.__connect_timeout = self.__config.get("connectTimeout", 30)
        # 重连间隔时间,默认为10秒
        self.__reconnect_interval = self.__config.get("reconnectInterval", 10)
        # 上次重连时间戳
        self.__last_reconnect_time = 0
        # 连接器是否已停止
        self.__stopped = True
        # 连接器是否已连接
        self._connected = False
        
    def open(self):
        """
        启动连接器。
        """
        self.__stopped = False
        self.start()
        self.__last_reconnect_time = time.time()
        self._log.info("Starting YDT1363 connector")  

    def run(self):
        """
        连接器线程的主函数,循环执行以下操作,直到连接器停止:
        1. 如果连接器未连接,且当前时间距离上次重连时间超过了重连间隔,则尝试连接设备。
        2. 如果连接器已连接,则轮询设备数据。
        3. 休眠0.01秒,避免过于频繁地执行循环。
        """
        while not self.__stopped:
            if not self._connected and time.time() - self.__last_reconnect_time >= self.__reconnect_interval:
                self.__connect_to_devices()
            if self._connected:
                self.__poll_data()
            time.sleep(.01)

    def close(self):
        """
        停止连接器。
        """
        self.__stopped = True
        self._connected = False
        self.__disconnect_from_devices()
        self._log.info('YDT1363 connector has been stopped.')

    def get_name(self):
        """
        获取连接器名称。
        
        返回:
        - str,连接器名称。
        """
        return self.name
    
    def get_id(self):
        """
        获取连接器ID。
        
        返回:
        - str,连接器ID。
        """
        return self.__config.get("id", "ydt1363") 
    
    def get_type(self):
        """
        获取连接器类型。
        
        返回:
        - str,连接器类型。
        """
        return self._connector_type

    def get_config(self):
        """
        获取连接器配置信息。
        
        返回:
        - dict,连接器配置信息。
        """
        return self.__config

    def is_connected(self):
        """
        获取连接器的连接状态。
        
        返回:
        - bool,连接器是否已连接。
        """
        return self._connected
    
    def is_stopped(self):
        """
        获取连接器的停止状态。
        
        返回:
        - bool,连接器是否已停止。
        """
        return self.__stopped

    def on_attributes_update(self, content):
        """
        处理Thingsboard下发的属性更新请求。
        
        参数:
        - content: dict,属性更新请求的内容。
        """
        try:
            # 根据设备名称查找设备配置
            device_config = tuple(filter(lambda d: d['deviceName'] == content['device'], self.__devices))[0]
            # 遍历设备的属性更新请求配置
            for attribute_request_config in device_config['attributeUpdateRequests']:
                # 获取属性名称
                attribute_key = content['data'].get(attribute_request_config['attributeFilter']) 
                if attribute_key is not None:
                    # 使用下行数据转换器将属性值转换为YD/T 1363.3协议要求的格式
                    data = YDT1363DownlinkConverter.convert(attribute_request_config, attribute_key)
                    # 构造YD/T 1363.3协议命令  
                    request = self.__form_request(attribute_request_config['cid1'], attribute_request_config['command'], data)
                    # 发送命令给设备
                    self.__send_request(device_config['socket'], request)
        except Exception as e:
            self._log.exception(e)

    def server_side_rpc_handler(self, content):
        """
        处理Thingsboard下发的RPC请求。
        
        参数:
        - content: dict,RPC请求的内容。
        """
        try:
            # 根据设备名称查找设备配置
            device_config = tuple(filter(lambda d: d['deviceName'] == content['device'], self.__devices))[0]
            # 遍历设备的RPC请求配置
            for rpc_request_config in device_config['serverSideRpcRequests']:
                # 检查RPC方法名是否匹配
                if rpc_request_config['requestFilter'] == content['data']['method']:
                    # 获取RPC参数
                    data = content['data'].get('params')
                    if data is not None:
                        # 使用下行数据转换器将RPC参数转换为YD/T 1363.3协议要求的格式
                        data = YDT1363DownlinkConverter.convert(rpc_request_config, data)
                    # 构造YD/T 1363.3协议命令
                    request = self.__form_request(rpc_request_config['cid1'], rpc_request_config['command'], data)
                    # 发送命令给设备
                    self.__send_request(device_config['socket'], request)
                    # 发送RPC响应给Thingsboard,表示RPC请求已成功处理
                    self.__gateway.send_rpc_reply(device=content["device"], req_id=content["data"]["id"], success_sent=True)
        except Exception as e:
            self._log.exception(e)
            # 发送RPC响应给Thingsboard,表示RPC请求处理失败
            self.__gateway.send_rpc_reply(device=content["device"], req_id=content["data"]["id"], success_sent=False)

    def collect_statistic_and_send(self, connector_name, data):
        """
        更新连接器的统计信息,并将采集到的数据发送给Thingsboard。
        
        参数:
        - connector_name: str,连接器名称。
        - data: dict,采集到的数据。
        """
        self.statistics["MessagesReceived"] = self.statistics["MessagesReceived"] + 1
        self.__gateway.send_to_storage(connector_name, data)
        self.statistics["MessagesSent"] = self.statistics["MessagesSent"] + 1

    def __connect_to_devices(self):
        """
        连接所有配置的设备。
        """
        for device in self.__devices:
            try:
                # 连接设备
                self.open_device_connection(device)
            except Exception as e:
                self._log.error("Error on connecting to device: %r", e)
                self._connected = False
        # 更新连接器的连接状态
        self._connected = any([d.get('connected') for d in self.__devices])
        self.__last_reconnect_time = time.time()

    def __disconnect_from_devices(self):
        """
        断开所有设备的连接。
        """
        for device in self.__devices:
            try:
                # 断开设备连接
                self.close_device_connection(device)
            except Exception as e:
                self._log.error("Error on disconnecting from device: %r", e)
        self._connected = False

    def open_device_connection(self, device):
        """
        连接单个设备。
        
        参数:
        - device: dict,设备配置信息。
        """
        try:
            device_config = self.__get_device_config(device)
            # 创建Socket对象
            device_socket = socket.socket()
            # 设置连接超时时间
            device_socket.settimeout(device_config['connectTimeout'])
            # 连接设备
            device_socket.connect((device_config['host'], device_config['port']))
            # 将Socket对象保存到设备配置中
            device_config['socket'] = device_socket
            # 更新设备的连接状态
            device_config['connected'] = True
            self._log.info('Connected to %s', device_config['deviceName'])
        except Exception as e:
            self._log.error('Unable to connect to %s: %s', device_config['deviceName'], str(e))

    def close_device_connection(self, device):
        """
        关闭单个设备的连接。
        
        参数:
        - device: dict,设备配置信息。
        """
        device_config = self.__get_device_config(device)
        if device_config.get('connected'):
            # 关闭Socket连接
            device_config['socket'].close()
            # 更新设备的连接状态
            device_config['connected'] = False
            self._log.info('Disconnected from %s', device_config['deviceName'])

    def __poll_data(self):
        """
        轮询设备数据。
        """
        for device in self.__devices:
            device_config = self.__get_device_config(device)
            if device_config.get('connected'):
                current_time = time.time()
                # 检查是否到了轮询时间
                if current_time - device_config.get('lastActivityTime', 0) >= device_config['pollingInterval']/1000:
                    # 遍历设备的属性配置
                    for attribute in device_config['attributes']:
                        # 构造属性读取命令
                        request = self.__form_request(attribute['cid1'], attribute['cid2'])
                        # 发送命令给设备
                        response = self.__send_request(device_config['socket'], request)
                        # 解析设备响应
                        response_data = self.__parse_response(response, attribute)
                        # 将响应数据转换为Thingsboard接受的格式
                        converted_data = YDT1363UplinkConverter(self._log).convert(device_config, response_data)
                        # 发送数据到Thingsboard
                        self.collect_statistic_and_send(self.get_name(), converted_data)
                    # 遍历设备的遥测配置
                    for telemetry in device_config['telemetry']:
                        # 构造遥测数据读取命令
                        request = self.__form_request(telemetry['cid1'], telemetry['cid2'])
                        # 发送命令给设备
                        response = self.__send_request(device_config['socket'], request)
                        # 解析设备响应
                        response_data = self.__parse_response(response, telemetry)
                        # 将响应数据转换为Thingsboard接受的格式
                        converted_data = YDT1363UplinkConverter(self._log).convert(device_config, response_data)
                        # 发送数据到Thingsboard
                        self.collect_statistic_and_send(self.get_name(), converted_data)
                    # 更新最后一次活动时间
                    device_config['lastActivityTime'] = current_time

    @staticmethod
    def __form_request(cid1, cid2, data=None):
        """
        构造YD/T 1363.3协议命令。
        
        参数:
        - cid1: str,命令标识1。
        - cid2: str,命令标识2。
        - data: bytes,可选,命令数据。
        
        返回:
        - bytes,YD/T 1363.3协议命令。
        """
        request = bytearray([0x68, 0x0D, 0x00, 0x41, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, int(cid1, 16), int(cid2, 16), 0x00, 0x16])
        if data is not None:
            request.extend(data)
        return request

    @staticmethod
    def __send_request(sock, request):
        """
        向设备发送YD/T 1363.3协议命令,并接收设备返回的响应数据。
        
        参数:
        - sock: socket.socket,与设备的Socket连接。
        - request: bytes,YD/T 1363.3协议命令。
        
        返回:
        - bytes,设备返回的响应数据。
        """
        sock.sendall(request)
        response = sock.recv(1024)
        return response
    
    @staticmethod
    def __parse_response(response, config):
        """
        解析设备返回的响应数据。
        
        参数:
        - response: bytes,设备返回的响应数据。
        - config: dict,命令配置。
        
        返回:
        - dict,解析后的数据。
        
        异常:
        - Exception,如果响应数据格式不正确。
        """
        result = {}
        # 检查响应数据的起始标志和结束标志是否正确
        if response[0] != 0x68 or response[14] != 0x16:
            raise Exception("Invalid response format")

        # 提取响应数据的长度
        data_length = struct.unpack('<H', response[1:3])[0]
        # 检查响应数据的长度是否与实际长度匹配
        if data_length + 4 != len(response):
            raise Exception("Data length does not match response length")

        # 如果是多帧数据
        if config.get('command') == 'multipleFrame':
            # 提取数据部分
            total_data = response[15:-1]
            # 提取数据项的数量
            items_count = struct.unpack('<H', total_data[:2])[0]
            data_offset = 2
            # 循环提取每个数据项
            for _ in range(items_count):
                key = config['key']
                data_bytes = total_data[data_offset:data_offset+config.get('length', 4)]
                data_offset += config.get('length', 4)
                # 将原始字节数据转换为Python数据类型
                result[key] = YDT1363Connector.__convert_data(data_bytes, config)
        else:
            # 提取数据部分
            data = response[15:-1]
            # 将原始字节数据转换为Python数据类型
            result[config['key']] = YDT1363Connector.__convert_data(data, config)
        return result

    @staticmethod
    def __convert_data(data_bytes, config):
        """
        将原始字节数据转换为Python数据类型。

        参数:
        - data_bytes: bytes,原始字节数据。
        - config: dict,数据配置。

        返回:
        - 转换后的Python数据类型。
        """
        # 根据数据类型进行转换
        if config.get('dataType') == 'uint8':
            return int.from_bytes(data_bytes, 'big', signed=False)
        elif config.get('dataType') == 'uint16':
            return int.from_bytes(data_bytes, config.get('byteOrder', 'little'), signed=False)
        elif config.get('dataType') == 'int16':
            return int.from_bytes(data_bytes, config.get('byteOrder', 'little'), signed=True)
        elif config.get('dataType') == 'uint32':
            return int.from_bytes(data_bytes, config.get('byteOrder', 'little'), signed=False)
        elif config.get('dataType') == 'int32':
            return int.from_bytes(data_bytes, config.get('byteOrder', 'little'), signed=True)
        elif config.get('dataType') == 'float32':
            return struct.unpack('>f' if config.get('byteOrder') == 'big' else '<f', data_bytes)[0]
        elif config.get('dataType') == 'alarms':
            data = int.from_bytes(data_bytes, 'big', signed=False)
            alarms = []
            # 根据配置的映射关系,解析出告警信息
            for i, key in enumerate(sorted(config['mapping'].keys())):
                if data & (1 << i):
                    alarms.append(config['mapping'][key])
            return alarms
        else:
            return data_bytes

    @staticmethod
    def __get_device_config(device):
        """
        根据设备名称获取设备的配置信息。

        参数:
        - device: dict,设备信息。

        返回:
        - dict,设备配置信息。
        """
        return next(d for d in device['devices'] if d['deviceName'] == device['deviceName'])