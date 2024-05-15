"""
MU4801系列电池管理单元的Thingsboard网关连接器。
该连接器通过串口与MU4801通信,周期性读取设备属性、时间序列数据和告警状态,
并将其上报到Thingsboard服务器。同时支持通过Thingsboard下发控制命令。
"""

import time
import threading  
from threading import Thread
from random import choice
from string import ascii_lowercase
from queue import Queue
from copy import deepcopy

import serial
from thingsboard_gateway.connectors.connector import Connector
from thingsboard_gateway.tb_utility.tb_utility import TBUtility
from thingsboard_gateway.gateway.statistics_service import StatisticsService
from thingsboard_gateway.tb_utility.tb_logger import init_logger

from thingsboard_gateway.extensions.mu4801.mu4801_uplink_converter import Mu4801UplinkConverter
from thingsboard_gateway.extensions.mu4801.mu4801_downlink_converter import Mu4801DownlinkConverter

class Mu4801Connector(Connector, Thread):
    """
    MU4801系列电池管理单元的Thingsboard网关连接器。  
    通过串口与设备通信,并将数据转换上报到Thingsboard服务器。
    """
    
    def __init__(self, gateway, config, connector_type):
        """
        MU4801连接器的初始化方法。
        
        参数:
        gateway: 网关对象
        config: 连接器配置信息(dict类型)
        connector_type: 连接器类型(字符串) 
        """
        # 初始化连接统计信息
        self.statistics = {'MessagesReceived': 0, 'MessagesSent': 0}
        super().__init__()  
        self.__gateway = gateway
        self.__connector_type = connector_type
        self.__config = config
        
        # 生成连接器名称 
        self.name = config.get("name", 'MU4801 ' + ''.join(choice(ascii_lowercase) for _ in range(5)))

        # 初始化日志
        self._log = init_logger(gateway, config.get('name', connector_type), config.get('logLevel', 'INFO'))
        self._log.info("Initializing MU4801 connector")

        # 连接状态标志位
        self.__connected = False  
        # 停止标志位
        self.__stopped = False
        self.daemon = True
        
        # 解析配置
        self.__parse_config()

        # 初始化RPC请求队列
        self.__rpc_requests = Queue()   
        # 初始化属性更新队列
        self.__attribute_updates = Queue()
        
        # 初始化串口相关变量
        self.__serial = None
        self.__reader = None 
        self.__writer = None
        # 初始化设备访问锁 
        self.__device_lock = threading.Lock()

        # 初始化上次轮询和心跳时间戳
        self.__last_poll_time = 0 
        self.__last_heartbeat_time = 0  

        # 从配置计算轮询间隔和命令超时时间
        self.__convert_frequency = self.__config['pollInterval'] / 1000  
        self.__command_timeout = self.__config['commandTimeout'] / 1000
        
        self._log.info("Config: %s", self.__config)
        # 初始化数据转换器
        self.__init_converters()

        self._log.info("[%s] MU4801 connector initialized.", self.get_name())

    def __parse_config(self):
        """
        解析连接器配置,提取默认配置和具体设备配置
        """
        default_config = {} 
        device_config = {}

        # 遍历配置的设备列表,提取默认配置和具体设备配置
        for device in self.__config.get('devices', []):
            if 'deviceType' in device and device['deviceType'] == 'default':
                default_config = device  
            else:
                device_config[device["deviceName"]] = device

        self.__config['defaultConfig'] = default_config
        self.__config['deviceConfig'] = device_config
        
    def __init_converters(self):
        """
        初始化上行和下行数据转换器
        """
        self.__uplink_converter = Mu4801UplinkConverter(self, self._log)
        self.__downlink_converter = Mu4801DownlinkConverter(self, self._log)

    def open(self):
        """
        连接器开启方法,置位停止标志位并启动连接器线程
        """    
        self.__stopped = False
        self.start()
        
    def run(self):
        """
        连接器主线程方法
        """  
        self._log.debug("Starting MU4801 connector thread")
        self.__connected = True

        # 循环执行,直到停止标志位被置位
        while not self.__stopped:
            # 如果未连接,则尝试连接串口
            if not self.__connected:
                self.__connect_serial()
                
            try:
                # 遍历配置的设备列表,处理每个设备
                for device_name in self.__config['deviceConfig']: 
                    device_config = self.__config['deviceConfig'][device_name]
                    
                    # 读取并上报设备属性
                    for attribute in device_config.get('attributes', []):
                        reply = self.__send_command(attribute['command'], device_config)
                        if reply:
                            result = self.__uplink_converter.parse_attribute(attribute, reply, device_name)
                            if result:
                                self._log.debug(f'[{self.get_name()}] Attribute reply parsed: {result}')
                                self.collect_statistic_and_send(self.get_name(), result)
                                
                    # 读取并上报设备时序数据
                    for ts_key, ts_config in device_config.get('timeseries', {}).items():
                        reply = self.__send_command(ts_config['command'], device_config) 
                        if reply:
                            result = self.__uplink_converter.parse_telemetry(ts_config, reply, device_name)
                            if result:
                                self._log.debug(f'[{self.get_name()}] Timeseries reply parsed: {result}')
                                self.collect_statistic_and_send(self.get_name(), result)
                                
                    # 读取并上报设备告警状态
                    for alarm_key, alarm_config in device_config.get('alarms', {}).items():
                        reply = self.__send_command(alarm_config['command'], device_config)
                        if reply:  
                            result = self.__uplink_converter.parse_alarm(alarm_config, reply, device_name)
                            if result:
                                self._log.debug(f'[{self.get_name()}] Alarm reply parsed: {result}') 
                                self.collect_statistic_and_send(self.get_name(), result)
                                
                    # 读取负载开关状态
                    self.__read_load_status(device_name, device_config)
                    
                    # 处理整流模块相关命令  
                    self.__handle_rectifier_commands(device_name, device_config)
                       
                # 处理Thingsboard下发的属性更新请求    
                while not self.__attribute_updates.empty():
                    attribute_update = self.__attribute_updates.get()
                    try:
                        device_name = attribute_update['device']
                        device_config = self.__config['deviceConfig'][device_name]
                        attribute_updates = deepcopy(device_config['attributeUpdates'])
                        for attribute_config in attribute_updates:
                            if attribute_config['attributeOnThingsBoard'] == attribute_update['attribute']:
                                # 使用下行转换器将属性更新转换为设备命令
                                value = attribute_update['value']  
                                command = self.__downlink_converter.convert({
                                    **attribute_config, 
                                    "device": device_name,
                                    "value": value
                                })
                                reply = self.__send_command(command, device_config)
                                if reply:
                                    self._log.debug(f"[{self.get_name()}] Attribute update reply received: {reply.hex()}")
                                    self.statistics['MessagesSent'] += 1
                    except Exception as e:
                        self._log.exception("Failed to update attribute: %s", e)
                        
                # 处理Thingsboard下发的RPC请求        
                while not self.__rpc_requests.empty(): 
                    rpc_request = self.__rpc_requests.get()
                    try:
                        device_name = rpc_request['device']
                        rpc_config = rpc_request['config']  
                        rpc_params = rpc_request['params']
                        
                        # 查找RPC方法对应的配置
                        method_config = next((m for m in self.__config['serverSideRpc'] if m['method'] == rpc_config['method']), None)
                        if not method_config:
                            self._log.error(f"[{self.get_name()}] RPC method '{rpc_config['method']}' not found in configuration.")
                            continue
                        
                        # 使用下行转换器将RPC请求转换为设备命令
                        method_params = self.__downlink_converter.config_from_type(method_config['paramsFormat'])
                        command_config = {
                            **rpc_config,
                            "device": device_name,
                            "value": rpc_params
                        }
                        
                        commands = self.__downlink_converter.convert(command_config, method_params)
                        
                        # 发送命令并接收设备响应
                        reply = None
                        if isinstance(commands, list):
                            for command in commands:
                                reply = self.__send_command(command, device_config)
                        else:
                            reply = self.__send_command(commands, device_config)
                        
                        if reply is not None:
                            self._log.debug(f"[{self.get_name()}] RPC reply received: {reply.hex()}")
                            self.statistics['MessagesSent'] += 1
                            
                            # 对于无需响应的RPC,直接返回成功
                            if rpc_config['method'] in self.__downlink_converter.unidirectional_methods:
                                result = {'success': True}
                            else:
                                # 使用上行转换器解析RPC响应  
                                result = self.__uplink_converter.parse_rpc_reply(reply, rpc_config, device_name)
                            
                            # 将RPC响应发送给Thingsboard
                            self.__gateway.send_rpc_reply(device_name, rpc_request['id'], result)
                        else:
                            self._log.warning(f"[{self.get_name()}] RPC call '{rpc_config['method']}' failed: no reply from device.")
                            self.__gateway.send_rpc_reply(device_name, rpc_request['id'], {'success': False})
                
                    except Exception as e:
                        self._log.exception("Failed to process RPC request: %s", e)
                        self.__gateway.send_rpc_reply(rpc_request['device'], rpc_request['id'], {
                            'success': False,
                            'error': str(e) 
                        })
                        
                # 定时发送心跳数据到Thingsboard       
                current_time = time.time()
                if self.__last_heartbeat_time + self.__config['heartbeatIntervalMs'] / 1000 < current_time:
                    self.__last_heartbeat_time = current_time
                    self.__gateway.send_to_storage(self.name, {
                        'ts': int(current_time * 1000),
                        'values': {
                            # 心跳数据中包含配置的设备数和当前连接的设备数
                            'deviceCount': len(self.__config['deviceConfig']),  
                            'activeConnections': sum(device.get('connected', 0) for device in self.__config['deviceConfig'].values())
                        }  
                    })
                
                # 延时等待下一次轮询
                time.sleep(self.__convert_frequency)
                
            except Exception as e:
                self._log.exception("Error in polling loop: %s", e)

                # 发生异常时关闭串口连接
                try:
                    self.__serial.close()
                except:
                    pass
                self.__connected = False

        self._log.info('[%s] Connector stopped.', self.get_name())
        
    def __read_load_status(self, device_name, device_config):
        """
        读取负载开关状态并上报
        
        参数:
        device_name: 设备名称
        device_config: 设备配置(dict)
        """
        try:
            load_switch_config = device_config.get('loadSwitchControl', {})
            # 如果未配置负载开关,则跳过
            if not load_switch_config:  
                return
            
            # 发送读取命令
            reply = self.__send_command(load_switch_config['read']['command'], device_config)
            if reply:
                load_status = {}
                # 遍历配置的负载开关,解析各开关的状态
                for load_no in load_switch_config['loadNO']:
                    status_byte = reply[load_switch_config['read']['startPos'] + load_no - 1] 
                    status = load_switch_config['read']['booleanMap'].get(str(status_byte), 'unknown')
                    load_status[f'load{load_no}'] = status
                
                result = {'device': device_name, **load_status}
                self._log.debug(f'[{self.get_name()}] Load status parsed: {result}') 
                self.collect_statistic_and_send(self.get_name(), result)

        except Exception as e:
            self._log.exception(f"Failed to read load status for device '{device_name}': {str(e)}")
            
    def __handle_rectifier_commands(self, device_name, device_config):
        """
        处理整流模块相关命令
        
        参数:
        device_name: 设备名称  
        device_config: 设备配置(dict)
        """  
        try:
            # 读取整流模块的遥测数据
            reply = self.__send_command('0x41', device_config)  
            if reply:
                result = self.__uplink_converter.parse_rectifier_telemetry(reply, device_name)
                if result:
                    self._log.debug(f'[{self.get_name()}] Rectifier telemetry parsed: {result}')
                    self.collect_statistic_and_send(self.get_name(), result)
            
            # 读取整流模块的告警状态        
            reply = self.__send_command('0x44', device_config)
            if reply:
                result = self.__uplink_converter.parse_rectifier_alarms(reply, device_name)
                if result:
                    self._log.debug(f'[{self.get_name()}] Rectifier alarms parsed: {result}')  
                    self.collect_statistic_and_send(self.get_name(), result)
            
            # 读取整流模块的开关状态
            reply = self.__send_command('0x43', device_config)
            if reply:  
                result = self.__uplink_converter.parse_rectifier_status(reply, device_name)
                if result:
                    self._log.debug(f'[{self.get_name()}] Rectifier status parsed: {result}')
                    self.collect_statistic_and_send(self.get_name(), result)
                    
        except Exception as e:
            self._log.error(f"Failed to handle rectifier commands for device '{device_name}': {str(e)}")
        
    def close(self):
        """
        关闭连接器,置位停止标志
        """
        self.__stopped = True
        self.__disconnect_serial()

    def get_name(self):
        """
        获取连接器名称
        
        返回值:
        连接器名称(字符串)
        """
        return self.name

    def is_connected(self):
        """
        获取连接状态
        
        返回值:
        连接状态(布尔值)
        """
        return self.__connected
        
    def on_attributes_update(self, content):
        """
        处理Thingsboard下发的属性更新请求
        
        参数:  
        content: 属性更新请求内容(dict)
        """  
        try:
            device_name = content['device']
            for attribute_update in self.__config['deviceConfig'][device_name].get('attributeUpdates', []):
                if attribute_update['attributeOnThingsBoard'] in content:
                    self.__attribute_updates.put({
                        'device': device_name,
                        'attribute': attribute_update['attributeOnThingsBoard'],
                        'value': content[attribute_update['attributeOnThingsBoard']]  
                    })
        except Exception as e:
            self._log.exception("Failed to process attribute update: %s", e)
            
    def server_side_rpc_handler(self, content):
        """
        处理Thingsboard下发的RPC请求
        
        参数:
        content: RPC请求内容(dict)
        """
        try:
            device_name = content['device']
            rpc_method = content['data']['method']
            rpc_params = content['data']['params']
            rpc_id = content['data']['id']
            
            # 在配置中查找RPC方法对应的配置
            rpc_config = None  
            for rpc in self.__config['serverSideRpc']: 
                if rpc['method'] == rpc_method:
                    rpc_config = rpc
                    break
                    
            if not rpc_config:
                self._log.error(f"RPC method '{rpc_method}' not found in configuration for device '{device_name}'.")
                self.__gateway.send_rpc_reply(content['device'], content['data']['id'], {'success': False})
                return
            
            # 将RPC请求放入队列,待处理
            self.__rpc_requests.put({
                'id': rpc_id, 
                'device': device_name,
                'params': rpc_params, 
                'config': rpc_config  
            })
        except Exception as e:
            self._log.exception("Failed to process RPC request: %s", e)
            self.__gateway.send_rpc_reply(content['device'], content['data']['id'], {'success': False, 'error': str(e)})
            
    @StatisticsService.CollectStatistics(start_stat_type='receivedBytesFromDevices', 
                                         end_stat_type='convertedBytesFromDevice')
    def collect_statistic_and_send(self, connector_name, data):
        """
        统计接收和发送消息数量并将数据发送到Thingsboard
        
        参数:
        connector_name: 连接器名称
        data: 要发送的数据(dict)
        """
        self.statistics["MessagesReceived"] += 1
        self.__gateway.send_to_storage(connector_name, data)
        self.statistics["MessagesSent"] += 1

    def is_stopped(self):
        """
        获取停止标志状态
        
        返回值:
        停止标志状态(布尔值)
        """
        return self.__stopped
        
    def get_config(self):
        """
        获取连接器配置
        
        返回值:
        连接器配置(dict)
        """
        return self.__config

    def get_config_parameter(self, parameter, default=None):
        """
        获取指定的连接器配置参数
        
        参数:
        parameter: 参数名(字符串)
        default: 默认值(可选)
        
        返回值:
        参数值
        """
        return self.get_config().get(parameter, default)

    def get_type(self):
        """
        获取连接器类型
        
        返回值:  
        连接器类型(字符串)
        """
        return self.__connector_type

    def get_gateway(self):
        """
        获取网关对象
        
        返回值:
        网关对象  
        """
        return self.__gateway

    def get_id(self):
        """
        获取连接器ID(与连接器名称相同)
        
        返回值:
        连接器ID(字符串)
        """
        return self.name

    def __connect_serial(self):
        """
        连接串口
        """
        connect_attempt_count = 0
        max_attempts = self.__config['reconnectInterval']['maxAttempts']
        attempt_period = self.__config['reconnectInterval']['period'] / 1000
        
        # 尝试建立串口连接,直到达到最大尝试次数或连接成功
        while connect_attempt_count < max_attempts and not self.__stopped:
            try:
                self._log.info(f"[{self.get_name()}] Connecting to serial port {self.__config['port']} "
                               f"(attempt {connect_attempt_count + 1}/{max_attempts})")
                # 根据配置参数创建串口对象              
                self.__serial = serial.Serial(
                    port=self.__config['port'],
                    baudrate=self.__config['baudrate'],
                    bytesize=self.__config['bytesize'],
                    parity=self.__config['parity'][0],
                    stopbits=self.__config['stopbits'],
                    timeout=self.__config['timeout'] / 1000,
                )
                # 设置读写句柄
                self.__reader = self.__serial
                self.__writer = self.__serial
                self.__connected = True
                self._log.info(f'[{self.get_name()}] Successfully connected to serial port.')
                return
            except serial.SerialException as e:
                self._log.error(f"[{self.get_name()}] Error connecting to serial port: {str(e)}")
                
            connect_attempt_count += 1
            time.sleep(attempt_period)

        self.__connected = False

    def __disconnect_serial(self):
        """
        断开串口连接  
        """
        if self.__serial and self.__serial.is_open:
            self.__serial.close() 
            self.__connected = False
            self._log.info(f'[{self.get_name()}] Disconnected from serial port.')
                    
    def __send_command(self, command, device_config):
        """
        发送命令到设备并接收响应
        
        参数:
        command: 命令(字符串或字节串)
        device_config: 设备配置(dict)
        
        返回值:
        设备响应(字节串),如果发送失败则返回None
        """
        if not self.__connected:
            return None
        
        # 如果命令是字符串,则将其转换为字节串
        if isinstance(command, str):
            command = bytes.fromhex(command.replace('0x', ''))
        
        self._log.debug(f"[{self.get_name()}] Sending command to device '{device_config['deviceName']}': {command.hex()}")
        command_attempt_count = 0   
        attempt_period = self.__config['commandTimeout'] / 1000
        max_attempts = self.__config['maxCommandAttempts'] 
        
        # 尝试发送命令,直到达到最大尝试次数或发送成功
        while command_attempt_count < max_attempts:
            try:
                with self.__device_lock:
                    # 发送命令
                    self.__writer.write(command)  
                    self.__writer.flush()
                    # 如果配置中指定不需要响应,则直接返回
                    if not self.__config.get('expectReply', True):
                        return None
                        
                    timeout_start = time.time()
                    reply = b'' 
                    
                    # 循环读取响应,直到读取完整的响应或超时
                    while time.time() - timeout_start < self.__command_timeout:
                        # 获取可读取的字节数
                        read_size = self.__reader.in_waiting
                        if read_size > 0:
                            # 读取数据并追加到响应中
                            chunk = self.__reader.read(read_size)
                            reply += chunk
                            # 如果响应以回车结尾,则表示读取完整
                            if reply.endswith(b'\r'):
                                self._log.debug(f"[{self.get_name()}] Reply received from device: {reply.hex()}")
                                return reply
                            
                        time.sleep(0.01)
                        
                raise TimeoutError(f"[{self.get_name()}] Command timed out after {self.__command_timeout}s")

            except Exception as e:
                self._log.error(f"[{self.get_name()}] Error sending command: {str(e)}")
            
            command_attempt_count += 1
            time.sleep(attempt_period)
            
        self._log.warning(f"[{self.get_name()}] Command failed after {max_attempts} attempts.")
        
        # 命令发送失败时生成一个事件上报
        event = {
            'device': device_config['deviceName'],
            'type': 'commandFailed',
            'command': command.hex()
        }
        self.__gateway.send_to_storage(self.get_name(), event)
        return None