"""
HDE-AIR系列机柜空调连接器,用于通过ThingsBoard IoT Gateway采集和控制黑盾机柜空调。
"""

import time
from threading import Thread
import serial
from thingsboard_gateway.connectors.connector import Connector
from thingsboard_gateway.tb_utility.tb_utility import TBUtility
from thingsboard_gateway.extensions.hdeac.hdeac_uplink_converter import HdeAcUplinkConverter
from thingsboard_gateway.extensions.hdeac.hdeac_downlink_converter import HdeAcDownlinkConverter
from thingsboard_gateway.tb_utility.tb_logger import init_logger


class HdeAcConnector(Thread, Connector):
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
        
        # 读取设备地址范围，如果没有指定，则默认为1到254       
        self.__address_range = config.get('address_range', {'start': 1, 'end': 254})

        # 读取协议类型，如rtu、ascii        
        self.__protocol = config.get('protocol', 'rtu')

        # 读取数据采集间隔,默认为5秒        
        self.__interval = config.get('interval', 5)

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
            
    def collect_statistic_and_send(self, connector_name, connector_id, data):  
        """
        发送统计数据。
        
        参数:
        - connector_name: 连接器名称,字符串
        - data: 要发送的数据,字典
        """
        self.__reads += 1  
        self.gateway.send_to_storage(connector_name, connector_id, data)
        self.__writes += 1
        
        self.gateway.add_message_statistics(self.get_name(), 'MessagesReceived', 1)
        self.gateway.add_message_statistics(self.get_name(), 'MessagesSent', 1)
    
    def __run(self):
        """  
        连接器线程主函数,循环执行数据采集和发送。
        """
        while not self.__stopped:
            if not self.__connected:
                self.__connect()
                time.sleep(self.__reconnect_interval)
            else:          
                try:
                    for address in range(self.__address_range['start'], self.__address_range['end']+1):
                        device = self.__find_device_by_address(address)
                        if device:
                            self.__get_data(device)
                        else:
                            self.log.warning('Device with address %d not found in configuration', address)
                            
                    self.__check_status()
                except Exception as e:
                    self.log.exception(e)
                    self.__disconnect()
                    
            time.sleep(self.__interval)
                        
    def __find_device_by_address(self, address):
        """
        从配置的设备列表中查找指定地址的设备。

        参数:  
        - address: 设备地址,整数

        返回:
        - 设备信息字典,如果找到;否则返回None  
        """
        for device in self.devices:
            if device.get('address', {}).get('command') == address:
                return device
        
        return None
                
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
            # 获取通信协议版本号
            if 'version' in device:
                command = self.downlink_converter.convert_version_command(device['version'])
                data = self.__write_command(device, command)
                version = self.uplink_converter.parse_version(data)
                if version:
                    self.log.debug('Protocol version for %s: %s', device['deviceName'], version)

            # 获取设备地址
            if 'address' in device:  
                command = self.downlink_converter.convert_object(self.log, device['address'], 'command')
                data = self.__write_command(device, command)
                addr = self.uplink_converter.parse_address(data)
                if addr:
                    self.log.debug('Device address for %s: %s', device['deviceName'], addr)

            # 采集时间序列数据  
            for request in device.get('timeseries', []):
                if 'command' in request:
                    command = self.downlink_converter.convert_object(self.log, request, 'command')
                    
                    retry_times = 3
                    data = None
                    while retry_times > 0:
                        try:
                            data = self.__write_command(device, command)
                            break
                        except Exception as e:
                            retry_times -= 1
                            self.log.warning('Failed to read data from device %s, remaining retry times: %d', device['deviceName'], retry_times, exc_info=e)
                            if retry_times == 0:
                                raise e
                                
                    if data is not None:                
                        converted_data = self.uplink_converter.convert(request, data)
                        self.collect_statistic_and_send(self.get_name(), self.get_id(), converted_data)
            
            # 采集属性数据
            for request in device.get('attributes', []):  
                command = self.downlink_converter.convert_object(self.log, request, 'command')
                data = self.__write_command(device, command)
                converted_data = self.uplink_converter.convert(request, data)   
                self.collect_statistic_and_send(self.get_name(), self.get_id(), converted_data)

            # 采集配置参数数据
            for request in device.get('parameters', []):
                get_command = self.downlink_converter.convert_object(self.log, request, 'get_command')
                data = self.__write_command(device, get_command)
                converted_data = self.uplink_converter.convert(request, data)
                self.collect_statistic_and_send(self.get_name(), self.get_id(), converted_data)
            
            # 获取设备历史数据（浮点数）  
            for request in device.get('history', []):
                if 'command' in request and request['command'] == '0x4A':
                    get_command = self.downlink_converter.convert_object(self.log, request, 'command')
                    data = self.__write_command(device, get_command)
                    converted_data = self.uplink_converter.convert(request, data)
                    self.collect_statistic_and_send(self.get_name(), self.get_id(), converted_data)
            
            # 获取设备历史数据（定点数）
            for request in device.get('history', []):
                if 'command' in request and request['command'] == '0x4B':
                    get_command = self.downlink_converter.convert_object(self.log, request, 'command')
                    data = self.__write_command(device, get_command)
                    converted_data = self.uplink_converter.convert(request, data)
                    self.collect_statistic_and_send(self.get_name(), self.get_id(), converted_data)

            # 获取历史告警数据
            for request in device.get('history_alarms', []):  
                if 'command' in request:
                    get_command = self.downlink_converter.convert_object(self.log, request, 'command')
                    data = self.__write_command(device, get_command)
                    converted_data = self.uplink_converter.convert_history_alarms(request, data)
                    self.collect_statistic_and_send(self.get_name(), self.get_id(), converted_data)

            # 获取设备系统时间
            for request in device.get('time', []):
                if 'command' in request and request['command'] == '0x4D':
                    get_command = self.downlink_converter.convert_object(self.log, request['get_time'], 'command')
                    data = self.__write_command(device, get_command)
                    converted_data = self.uplink_converter.convert(request['get_time'], data)
                    self.collect_statistic_and_send(self.get_name(), self.get_id(), converted_data)

            # 获取设备厂家信息
            if 'device_info' in device:
                command = self.downlink_converter.convert_object(self.log, device['device_info'], 'command')
                data = self.__write_command(device, command)
                converted_data = self.uplink_converter.convert(device['device_info'], data)
                self.collect_statistic_and_send(self.get_name(), self.get_id(), converted_data)
            
            device['online'] = True
        except Exception as e:
            self.log.exception('Error while getting data from device %s', device['deviceName'], exc_info=e)
            device['online'] = False

    def __write_command(self, device, command):
        """
        向机柜空调发送控制命令并接收响应。

        参数:
        - device: 设备配置,字典
        - command: 要发送的控制命令,字节数组

        返回:  
        - 机柜空调返回的数据,字节数组
        """ 
        self.log.debug('Writing command to device %s: %s', device['address']['command'], command.hex())

        # 根据设备地址将命令发送给指定设备
        command[2] = device['address']['command']  

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
                    
        self.log.debug('Read %d bytes from device %s: %s', len(data), device['address']['command'], data.hex())
        return data
    
    def __set_address(self):
        """
        设置机柜空调的地址。
        """
        for device in self.devices:
            if 'set_address' in device:
                command = self.downlink_converter.convert_object(self.log, device['set_address'], 'command')
                addr_cmd = self.downlink_converter.convert_object(self.log, device['address'], 'command')
                command.extend(addr_cmd)
                try:
                    self.__serial.write(command)
                    time.sleep(0.2)
                    # 读取响应数据
                    data = self.__serial.read(self.__serial.inWaiting())
                    self.log.debug('Set address %s for device %s: %s', addr_cmd.hex(), device['deviceName'], data.hex())
                except Exception as e:
                    self.log.exception(e)

    def __check_status(self):
        """
        检查所有设备的在线状态,并发送告警或恢复通知。
        """
        offline_devices = []
        online_devices = []

        for device in self.devices:
            if not device.get('online', True):
                offline_devices.append(device)
            else:
                online_devices.append(device)
                
        if offline_devices:
            self.log.warning('Devices offline: %s', ', '.join(d['deviceName'] for d in offline_devices))
            
            data = {'devices': [{'name': d['deviceName'], 'type': d.get('deviceType', 'default')} for d in offline_devices]}
            self.gateway.send_to_storage(self.get_name(), self.get_id(), data)
            
        if online_devices:
            self.log.info('Devices online: %s', ', '.join(d['deviceName'] for d in online_devices))
            
            data = {'devices': [{'name': d['deviceName'], 'type': d.get('deviceType', 'default')} for d in online_devices]}  
            self.gateway.send_to_storage(self.get_name(), self.get_id(), data)

    def run(self):
        """
        连接器线程入口函数。  
        """
        self.__run()