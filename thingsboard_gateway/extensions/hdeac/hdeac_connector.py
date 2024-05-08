"""
HDE-AIR系列机柜空调连接器,用于通过ThingsBoard IoT Gateway采集和控制黑盾机柜空调。
"""

import time
import threading
import serial  
from thingsboard_gateway.connectors.connector import Connector
from thingsboard_gateway.tb_utility.tb_utility import TBUtility
from hdeac_uplink_converter import HdeAcUplinkConverter
from hdeac_downlink_converter import HdeAcDownlinkConverter   
from thingsboard_gateway.tb_utility.tb_logger import init_logger


class HdeAcConnector(Connector):
    """
    HDE-AIR系列机柜空调连接器类,继承自Connector基类,实现了黑盾机柜空调的数据采集和控制逻辑。
    """

    def __init__(self, gateway, config, connector_type):
        """
        HdeAcConnector类初始化方法。
        
        参数:
        - gateway: ThingsBoard IoT Gateway实例
        - config: 连接器配置信息,从tb_gateway.yaml中读取
        - connector_type: 连接器类型,用于在日志中区分不同的连接器
        """
        super().__init__()  
        self.gateway = gateway
        self.config = config
        self.connector_type = connector_type
        # 使用从配置中读取的连接器名称,如果没有指定,则默认为HdeAcConnector
        self.name = config.get("name", "HdeAcConnector") 
        self.devices = config.get('devices')
        
        # 从config中读取RS485串口配置参数      
        self.__port = config.get('port', '/dev/ttyUSB0')
        self.__baudrate = config.get('baudrate', 9600)  
        self.__timeout = config.get('timeout', 35)
        self.__stopbits = config.get('stopbits', serial.STOPBITS_ONE)
        self.__bytesize = config.get('bytesize', serial.EIGHTBITS)
        self.__parity = config.get('parity', serial.PARITY_NONE)
        
        # 读取协议类型，如rtu、ascii
        self.__protocol = config.get('protocol', 'rtu')

        # 读取数据采集间隔        
        self.__interval = config.get('interval', 10)
        
        # 使用init_logger初始化日志对象
        self.log = init_logger(gateway, self.name, self.config.get('log_level', 'INFO'))
        
        # 增加统计属性      
        self.__reads = 0  
        self.__writes = 0
        
        self.__connected = False
        self.__stopped = False  
        self.__serial = None
        
        # 增加连接重试机制相关的属性
        self.__connecting = False
        self.__last_connect_attempt_time = 0
        self.__reconnect_interval = config.get('reconnect_interval', 10)
        
        # 初始化UpLink和DownLink Converter
        self.uplink_converter = HdeAcUplinkConverter(self.log)
        self.downlink_converter = HdeAcDownlinkConverter(self.log)
        
    def open(self):
        """
        启动连接器。
        
        将连接器设置为启动状态,并启动连接器线程。
        """
        self.__stopped = False
        self.start()
        
    def close(self):
        """  
        关闭连接器。
        
        将连接器设置为停止状态,关闭RS485串口连接。
        """
        self.__stopped = True
        self.__disconnect()
        
    def get_name(self):  
        """
        获取连接器名称。
        
        返回:
        - 连接器名称,字符串  
        """
        return self.name
    
    def get_id(self):
        """  
        获取连接器ID。
        
        返回:  
        - 连接器ID,字符串
        """  
        return self.config.get('id', self.name)
    
    def get_type(self):
        """
        获取连接器类型。
        
        返回:  
        - 连接器类型,字符串
        """
        return self.connector_type
    
    def get_config(self):
        """ 
        获取连接器配置信息。
        
        返回:
        - 连接器配置信息,字典
        """
        return self.config
    
    def is_connected(self):
        """
        获取连接器连接状态。
        
        返回:
        - 连接器是否已连接,布尔值
        """
        return self.__connected
    
    def is_stopped(self):  
        """
        获取连接器停止状态。
        
        返回:
        - 连接器是否已停止,布尔值  
        """
        return self.__stopped
            
    def on_attributes_update(self, content):
        """
        处理属性更新请求。
        
        参数:
        - content: 属性更新请求的内容,字典
        """
        try:
            device = tuple(filter(lambda d: d['deviceName'] == content['device'], self.devices))[0]
            for attr_request in device.get('attribute_updates', []):
                if attr_request['attribute'] == content['data']['attribute']:
                    command = self.downlink_converter.convert(attr_request, content['data'])
                    self.__write_command(device, command)
        except Exception as e:
            self.log.exception(e)
            
    def server_side_rpc_handler(self, content):
        """
        处理RPC请求。
        
        参数:  
        - content: RPC请求的内容,字典
        """
        try:
            device = tuple(filter(lambda d: d['deviceName'] == content['device'], self.devices))[0]
            for rpc_request in device.get('server_side_rpc', []):
                if rpc_request['method'] == content['data']['method']:
                    command = self.downlink_converter.convert(rpc_request, content['data'])
                    self.__write_command(device, command)
                    
                    self.gateway.send_rpc_reply(device=content["device"], req_id=content["data"]["id"], success_sent=True) 
        except Exception as e:
            self.log.exception(e)  
            self.gateway.send_rpc_reply(device=content["device"], req_id=content["data"]["id"], success_sent=False)
            
    def collect_statistic_and_send(self, connector_name, data):
        """
        发送统计数据。
        
        参数:
        - connector_name: 连接器名称,字符串
        - data: 要发送的数据,字典  
        """
        self.__reads += 1
        self.gateway.send_to_storage(connector_name, data)
        self.__writes += 1
        
        self.gateway.add_message_statistics(self.get_name(), 'MessagesReceived', 1)
        self.gateway.add_message_statistics(self.get_name(), 'MessagesSent', 1)
    
    def __run(self):
        """
        连接器线程主函数,循环执行数据采集和发送。
        """
        while not self.__stopped:
            if not self.__connected:
                if not self.__connecting and time.time() - self.__last_connect_attempt_time >= self.__reconnect_interval:
                    self.__connecting = True
                    self.__connect()
                else:
                    time.sleep(1)
                    continue
            else:
                for device in self.devices:
                    self.__get_data(device)
                
            time.sleep(self.__interval)
            
            
    def __connect(self):
        """
        与机柜空调建立RS485连接。
        """
        try:
            self.__serial = serial.Serial(port=self.__port, baudrate=self.__baudrate, timeout=self.__timeout, 
                                          stopbits=self.__stopbits, bytesize=self.__bytesize, 
                                          parity=self.__parity)
            self.__connected = True
            self.__connecting = False
            self.log.info('Successfully connected to serial port %s', self.__port)
        except Exception as e:
            self.log.error('Failed to connect to serial port %s: %s', self.__port, str(e))
            self.__connected = False
            self.__connecting = False
            self.__last_connect_attempt_time = time.time()
            self.__disconnect()
            
    def __disconnect(self):
        """
        关闭与机柜空调的RS485连接。  
        """
        if self.__serial:
            try:
                self.__serial.close()
            except Exception as e:
                self.log.exception(e)
                
        self.__connected = False
        self.log.info('Disconnected from serial port %s', self.__port)
            
    def __get_data(self, device):
        """
        从机柜空调中读取数据并发送。
        
        参数:
        - device: 要采集的设备配置,字典
        """
        try:
            # 采集时间序列数据
            for request in device.get('timeseries', []):
                command = self.downlink_converter.convert_object(self.log, request, 'command')
                data = self.__write_command(device, command)
                converted_data = self.uplink_converter.convert(request, data)
                self.collect_statistic_and_send(self.get_name(), converted_data)
            
            # 采集属性数据
            for request in device.get('attributes', []):
                command = self.downlink_converter.convert_object(self.log, request, 'command')
                data = self.__write_command(device, command)
                converted_data = self.uplink_converter.convert(request, data)
                self.collect_statistic_and_send(self.get_name(), converted_data)
                
            # 采集配置参数数据
            for request in device.get('parameters', []):
                get_command = self.downlink_converter.convert_object(self.log, request, 'get_command')
                data = self.__write_command(device, get_command)
                converted_data = self.uplink_converter.convert(request, data)
                self.collect_statistic_and_send(self.get_name(), converted_data)
                
            # 获取设备系统时间    
            for request in device.get('time', []):
                get_command = self.downlink_converter.convert_object(self.log, request, 'command')  
                data = self.__write_command(device, get_command)
                converted_data = self.uplink_converter.convert(request, data)  
                self.collect_statistic_and_send(self.get_name(), converted_data)
                
            # 设置设备系统时间
            if 'set_time' in device and device['set_time'].get('sync', True):
                set_command = self.downlink_converter.convert_object(self.log, device['set_time'], 'command')
                self.__write_command(device, set_command)
                
            # 获取设备版本信息
            if 'version' in device:
                command = self.downlink_converter.convert_object(self.log, device['version'], 'command') 
                data = self.__write_command(device, command)
                converted_data = self.uplink_converter.convert(device['version'], data)
                self.collect_statistic_and_send(self.get_name(), converted_data)  
                    
        except Exception as e:
            self.log.exception(e)
            
    def __write_command(self, device, command):
        """
        向机柜空调发送控制命令并接收响应。
        
        参数:
        - device: 设备配置,字典
        - command: 要发送的控制命令,字节数组
        
        返回:  
        - 机柜空调返回的数据,字节数组
        """
        self.log.debug('Writing command to device %s: %s', device['address'], command.hex())
        
        # 根据设备地址将命令发送给指定设备
        command[2] = device['address']
        
        # 发送命令并等待响应  
        self.__serial.write(command)  
        time.sleep(0.2)
        
        data = b''
        start_time = time.time()
        while True:  
            # 多次读取,直到读完所有响应数据或超时
            if self.__serial.inWaiting() > 0:  
                data += self.__serial.read(self.__serial.inWaiting())
                start_time = time.time()
            else:
                time.sleep(0.1)
                if time.time() - start_time > device.get('response_timeout', 2):
                    break
            
        self.log.debug('Read %d bytes from device %s: %s', len(data), device['address'], data.hex())
        return data
    
    def __start_thread(self):
        """
        启动连接器线程。
        """
        # 设置连接器线程为守护线程  
        self.daemon = True
        # 启动连接器线程
        self.start()
        
    def run(self):
        """
        连接器线程入口函数。
        """    
        self.__run()