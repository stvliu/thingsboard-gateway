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

      
class Mu4801Connector(Thread, Connector):
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
        super().__init__()
        self.statistics = {'MessagesReceived': 0, 'MessagesSent': 0}
        self.__gateway = gateway
        self.__connector_type = connector_type
        self.__config = config
        
        self.name = config.get("name", 'MU4801 ' + ''.join(choice(ascii_lowercase) for _ in range(5)))
        self._log = init_logger(gateway, config.get('name', connector_type), config.get('logLevel', 'INFO'))
        
        self._log.info("Initializing MU4801 connector")
        self.__connected = False
        self.__connecting = False
        self.__stopped = False
        self.daemon = True
        
        self.__parse_config()

        self.__rpc_requests = Queue()
        self.__attribute_updates = Queue()
        
        self.__serial = None
        self.__last_connect_attempt_time = 0
        self.__reconnect_interval = config.get('reconnect_interval', 10)

        self.__convert_frequency = self.__config['pollInterval'] / 1000
        self.__command_timeout = self.__config['commandTimeout'] / 1000
        
        self._log.info("Config: %s", self.__config)
        self.__init_converters()

        self._log.info("[%s] MU4801 connector initialized.", self.get_name())

    def __parse_config(self):
        default_config = {}
        device_config = {}

        for device in self.__config.get('devices', []):
            if 'deviceType' in device and device['deviceType'] == 'default':
                default_config = device
            else:
                device_config[device["deviceName"]] = device

        self.__config['defaultConfig'] = default_config
        self.__config['deviceConfig'] = device_config
        
    def __init_converters(self):
        self.__uplink_converter = Mu4801UplinkConverter(self, self._log)
        self.__downlink_converter = Mu4801DownlinkConverter(self, self._log)

    def open(self):
        self.__stopped = False
        self.start()
        
    def __run(self):
        self._log.debug("Starting MU4801 connector thread")
        self.__connected = True

        while not self.__stopped:
            if not self.__connected:
                self.__connect()
                time.sleep(self.__reconnect_interval)
            else:
                try:
                    for device_name in self.__config['deviceConfig']:
                        device_config = self.__config['deviceConfig'][device_name]
                        
                        for attribute in device_config.get('attributes', []):
                            reply = self.__send_command(attribute['command'], device_config)
                            if reply:
                                result = self.__uplink_converter.parse_attribute(attribute, reply, device_name)
                                if result:
                                    self._log.debug(f'[{self.get_name()}] Attribute reply parsed: {result}')
                                    self.collect_statistic_and_send(self.get_name(), result)
                                    
                        for ts_key, ts_config in device_config.get('timeseries', {}).items():
                            reply = self.__send_command(ts_config['command'], device_config)
                            if reply:
                                result = self.__uplink_converter.parse_telemetry(ts_config, reply, device_name)
                                if result:
                                    self._log.debug(f'[{self.get_name()}] Timeseries reply parsed: {result}')
                                    self.collect_statistic_and_send(self.get_name(), result)
                                    
                        for alarm_key, alarm_config in device_config.get('alarms', {}).items():
                            reply = self.__send_command(alarm_config['command'], device_config)
                            if reply:
                                result = self.__uplink_converter.parse_alarm(alarm_config, reply, device_name)
                                if result:
                                    self._log.debug(f'[{self.get_name()}] Alarm reply parsed: {result}')
                                    self.collect_statistic_and_send(self.get_name(), result)
                                    
                        self.__read_load_status(device_name, device_config)
                        self.__handle_rectifier_commands(device_name, device_config)
                           
                    while not self.__attribute_updates.empty():
                        attribute_update = self.__attribute_updates.get()
                        try:
                            device_name = attribute_update['device']  
                            device_config = self.__config['deviceConfig'][device_name]
                            attribute_updates = deepcopy(device_config['attributeUpdates'])
                            for attribute_config in attribute_updates:
                                if attribute_config['attributeOnThingsBoard'] == attribute_update['attribute']:
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
                            
                    while not self.__rpc_requests.empty():
                        rpc_request = self.__rpc_requests.get()
                        try:
                            device_name = rpc_request['device']
                            rpc_config = rpc_request['config'] 
                            rpc_params = rpc_request['params']
                            
                            method_config = next((m for m in self.__config['serverSideRpc'] if m['method'] == rpc_config['method']), None)
                            if not method_config:
                                self._log.error(f"[{self.get_name()}] RPC method '{rpc_config['method']}' not found in configuration.")
                                continue
                            
                            method_params = self.__downlink_converter.config_from_type(method_config['paramsFormat'])
                            command_config = {
                                **rpc_config,
                                "device": device_name,
                                "value": rpc_params
                            }
                            
                            commands = self.__downlink_converter.convert(command_config, method_params)
                            
                            reply = None
                            if isinstance(commands, list):
                                for command in commands:
                                    reply = self.__send_command(command, device_config)
                            else:
                                reply = self.__send_command(commands, device_config)
                            
                            if reply is not None:
                                self._log.debug(f"[{self.get_name()}] RPC reply received: {reply.hex()}")
                                self.statistics['MessagesSent'] += 1
                                
                                if rpc_config['method'] in self.__downlink_converter.unidirectional_methods:
                                    result = {'success': True}
                                else:
                                    result = self.__uplink_converter.parse_rpc_reply(reply, rpc_config, device_name)
                                
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
                            
                    current_time = time.time()
                    if self.__last_heartbeat_time + self.__config['heartbeatIntervalMs'] / 1000 < current_time:
                        self.__last_heartbeat_time = current_time
                        self.__gateway.send_to_storage(self.name, {
                            'ts': int(current_time * 1000),
                            'values': {
                                'deviceCount': len(self.__config['deviceConfig']),
                                'activeConnections': sum(device.get('connected', 0) for device in self.__config['deviceConfig'].values())
                            }
                        })
                    
                    time.sleep(self.__convert_frequency)
                    
                except Exception as e:
                    self._log.exception("Error in polling loop: %s", e)
                    self.__disconnect()
                    
        self._log.info('[%s] Connector stopped.', self.get_name())
        
    def __read_load_status(self, device_name, device_config):
        try:
            load_switch_config = device_config.get('loadSwitchControl', {})
            if not load_switch_config:
                return
            
            reply = self.__send_command(load_switch_config['read']['command'], device_config)
            if reply:
                load_status = {}
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
        try:
            reply = self.__send_command('0x41', device_config)
            if reply:
                result = self.__uplink_converter.parse_rectifier_telemetry(reply, device_name)
                if result:
                    self._log.debug(f'[{self.get_name()}] Rectifier telemetry parsed: {result}')
                    self.collect_statistic_and_send(self.get_name(), result)
            
            reply = self.__send_command('0x44', device_config)
            if reply:
                result = self.__uplink_converter.parse_rectifier_alarms(reply, device_name)
                if result:
                    self._log.debug(f'[{self.get_name()}] Rectifier alarms parsed: {result}')
                    self.collect_statistic_and_send(self.get_name(), result)
            
            reply = self.__send_command('0x43', device_config)
            if reply:
                result = self.__uplink_converter.parse_rectifier_status(reply, device_name)
                if result:
                    self._log.debug(f'[{self.get_name()}] Rectifier status parsed: {result}')
                    self.collect_statistic_and_send(self.get_name(), result)
                    
        except Exception as e:
            self._log.error(f"Failed to handle rectifier commands for device '{device_name}': {str(e)}")
        
    def close(self):
        self.__stopped = True
        self.__disconnect()

    def get_name(self):
        return self.name

    def is_connected(self):
        return self.__connected
        
    def on_attributes_update(self, content):
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
        try:
            device_name = content['device']
            rpc_method = content['data']['method']
            rpc_params = content['data']['params']
            rpc_id = content['data']['id']
            
            rpc_config = None
            for rpc in self.__config['serverSideRpc']:
                if rpc['method'] == rpc_method:
                    rpc_config = rpc
                    break
                    
            if not rpc_config:
                self._log.error(f"RPC method '{rpc_method}' not found in configuration for device '{device_name}'.")
                self.__gateway.send_rpc_reply(content['device'], content['data']['id'], {'success': False})
                return
            
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
        self.statistics["MessagesReceived"] += 1
        self.__gateway.send_to_storage(connector_name, data)
        self.statistics["MessagesSent"] += 1
    
    def is_stopped(self):
        return self.__stopped
        
    def get_config(self):
        return self.__config

    def get_config_parameter(self, parameter, default=None):
        return self.get_config().get(parameter, default)

    def get_type(self):
        return self.__connector_type

    def get_gateway(self):
        return self.__gateway

    def get_id(self):
        return self.name

    def __connect(self):
        try:
            self._log.info(f"[{self.get_name()}] Connecting to serial port {self.__config['port']}")
            self.__serial = serial.Serial(
                port=self.__config['port'],
                baudrate=self.__config['baudrate'],
                bytesize=self.__config['bytesize'],
                parity=self.__config['parity'][0],
                stopbits=self.__config['stopbits'],
                timeout=self.__config.get('timeout', 1),
            )
            self.__reader = self.__serial
            self.__writer = self.__serial

            reply = self.__send_command("0x50", self.__config)
            if reply is not None:
                self._log.info(f'[{self.get_name()}] Successfully connected to serial port, test command replied: {reply.hex()}')
                self.__connected = True
            else:
                raise serial.SerialException(f"Test command failed on serial port {self.__config['port']}")

        except serial.SerialException as e:
            self.__connected = False
            if e.errno == 2:
                self._log.error(f"[{self.get_name()}] Serial port {self.__config['port']} not found: {str(e)}")
            elif e.errno == 13:
                self._log.error(f"[{self.get_name()}] No permission to access serial port {self.__config['port']}: {str(e)}")
            else:
                self._log.error(f"[{self.get_name()}] Error connecting to serial port: {str(e)}")
            
            self.__last_connect_attempt_time = time.time()

    def __disconnect(self):
        if self.__serial and self.__serial.is_open:
            self.__serial.close()
            self.__connected = False
            self._log.info(f'[{self.get_name()}] Disconnected from serial port.')
                    
    def __send_command(self, command, device_config):
        if not self.__connected:
            return None
        
        if isinstance(command, str):
            command = bytes.fromhex(command.replace('0x', ''))
        
        self._log.debug(f"[{self.get_name()}] Sending command to device '{device_config['deviceName']}': {command.hex()}")
        command_attempt_count = 0
        attempt_period = self.__config['commandTimeout'] / 1000
        max_attempts = self.__config['maxCommandAttempts']
        
        while command_attempt_count < max_attempts:
            try:
                with self.__device_lock:
                    self.__writer.write(command)
                    self.__writer.flush()
                    if not self.__config.get('expectReply', True):
                        return None
                        
                    timeout_start = time.time()
                    reply = b''
                    
                    while time.time() - timeout_start < self.__command_timeout:
                        read_size = self.__reader.in_waiting
                        if read_size > 0:
                            chunk = self.__reader.read(read_size)
                            reply += chunk
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
        
        event = {
            'device': device_config['deviceName'],
            'type': 'commandFailed',
            'command': command.hex()
        }
        self.__gateway.send_to_storage(self.get_name(), event)
        return None

    def run(self):
        self.__run()