# mu4801_connector.py
import time
import json

from random import choice
from string import ascii_lowercase
from threading import Thread
from thingsboard_gateway.connectors.connector import Connector
from thingsboard_gateway.tb_utility.tb_utility import TBUtility
from thingsboard_gateway.gateway.statistics_service import StatisticsService
from thingsboard_gateway.tb_utility.tb_logger import init_logger

from thingsboard_gateway.connectors.mu4801.mu4801_constants import *
from thingsboard_gateway.connectors.mu4801.mu4801_uplink_converter import Mu4801UplinkConverter
from thingsboard_gateway.connectors.mu4801.mu4801_downlink_converter import Mu4801DownlinkConverter
from thingsboard_gateway.connectors.mu4801.mu4801_protocol import MU4801Protocol

class Mu4801Connector(Thread, Connector):

    def __init__(self, gateway, config, connector_type):
        super().__init__()
        self.statistics = {'MessagesReceived': 0, 'MessagesSent': 0}
        self.__gateway = gateway
        self._connector_type = connector_type
        self.__config = config
        self.__id = self.__config.get('id')
        self.name = config.get("name", 'MU4801 ' + ''.join(choice(ascii_lowercase) for _ in range(5)))
        self._log = init_logger(gateway, self.name, config.get('logLevel', 'INFO'))
        self._log.info("Initializing MU4801 connector")
        self.__devices = self.__config[DEVICES_PARAMETER]
        self.__connected = False
        self.__stopped = False
        self.daemon = True

        self.__serial_config = None
        self.__parse_config()
        self.__init_serial_config()
        self.__init_converters()

        # self.__loop = asyncio.new_event_loop()

        self._log.info("[%s] MU4801 connector initialized.", self.get_name())

    def open(self):
        # self.__loop.run_until_complete(self.__run())
        self._log.info("[%s] Starting...", self.get_name())
        self.__stopped = False
        self.start()

    def run(self):
        self._log.info(f"[{self.name}] Starting MU4801 connector")
        self.__run()

    def close(self):
        self.__stopped = True
        self.__disconnect()

    def get_id(self):
        return self.__id
    
    def get_name(self):
        return self.name

    def get_type(self):
        return self._connector_type

    def get_config(self):
        return self.__config

    def get_gateway(self):
        return self.__gateway
        
    def is_connected(self):
        return self.__protocol and self.__protocol.is_connected()

    def is_stopped(self):
        return self.__stopped
    
    @StatisticsService.CollectAllReceivedBytesStatistics(start_stat_type='allReceivedBytesFromTB')  
    def on_attributes_update(self, content):
        for device in content:
            device_name = device[DEVICE_SECTION_PARAMETER]
            data = device.get("data", {})
            if data:
                for config in self.__config[DEVICES_PARAMETER]:
                    if config[DEVICE_NAME_PARAMETER] == device_name:
                        for attribute_updates_config in config.get("attributeUpdates", []):
                            attribute_key = attribute_updates_config["key"]
                            if attribute_key in data:
                                attribute_data = {attribute_key: data[attribute_key]}
                                converted_data = self.__downlink_converter.convert(attribute_updates_config, attribute_data)
                                self.__update_device_attribute(attribute_updates_config, converted_data)

    @StatisticsService.CollectAllReceivedBytesStatistics(start_stat_type='allReceivedBytesFromTB')
    def server_side_rpc_handler(self, server_rpc_request):
        content_type = type(server_rpc_request).__name__
        self._log.debug(f"[RPC Request] Received ({content_type}): {server_rpc_request}")

        # 检查RPC是否是一个连接器RPC
        if self._is_connector_rpc(server_rpc_request):
            # 处理连接器RPC
            self._log.debug("Received RPC to connector: %r", server_rpc_request)
            return
        elif self.__is_device_rpc(server_rpc_request): 
            # 处理设备RPC
            device_name = server_rpc_request['device']
            rpc_data = server_rpc_request['data']

            # 检查'data'字段是否是一个包含'method'和'id'的字典
            if not isinstance(rpc_data, dict) or 'method' not in rpc_data or 'id' not in rpc_data:
                self._handle_invalid_rpc_data(device_name, rpc_data)
                return

            rpc_method = rpc_data['method']
            rpc_id = rpc_data['id']

            # 根据设备名查找设备配置
            device = self.__get_device_by_name(device_name)
            if not device:
                self._handle_unknown_device(device_name, rpc_id)
                return

            # 根据RPC方法查找RPC配置
            server_side_rpc_config = self.__get_device_rpc_config(device, rpc_method)
            if not server_side_rpc_config:
                self._handle_unknown_rpc_method(device_name, rpc_method, rpc_id)
                return

            # 转换RPC数据
            converted_data = self._convert_rpc_data(server_side_rpc_config, rpc_data, device_name, rpc_method, rpc_id)

            # 发送RPC命令
            self._send_rpc_command(server_side_rpc_config, converted_data, device_name, rpc_method, rpc_data, rpc_id)
        else:
            self._handle_invalid_rpc_request(server_rpc_request)
            return

    def is_filtering_enable(self):
        return DEFAULT_SEND_ON_CHANGE_VALUE

    def get_ttl_for_duplicates(self):
        return DEFAULT_SEND_ON_CHANGE_INFINITE_TTL_VALUE

    def _is_connector_rpc(self, server_rpc_request):
        # 检查RPC方法是否是一个连接器RPC
        try:
            return 'method' in server_rpc_request
        except (ValueError, AttributeError):
            return False

    def _extract_connector_rpc_method(self, rpc_method):
        # 提取连接器RPC的方法名
        return rpc_method.split('_', 1)[1]

    def _extract_device_name(self, rpc_data):
        # 提取设备名
        return rpc_data['params'].split(' ')[0].split('=')[-1]

    def _handle_invalid_rpc_request(self, server_rpc_request):
        # 处理无效的RPC请求
        error_msg = f"Invalid RPC request format: {server_rpc_request}"
        self._log.error(error_msg)

    def _handle_invalid_rpc_data(self, device_name, rpc_data):
        # 处理无效的RPC数据
        error_msg = f"Invalid 'data' field in RPC request: {rpc_data}"
        self._log.error(error_msg)
        self.__gateway.send_rpc_reply(device=device_name, req_id=rpc_data.get('id'), content={"error": error_msg}, success_sent=False)

    def _handle_unknown_device(self, device_name, rpc_id):
        # 处理未知设备
        error_msg = f"Device {device_name} not found in config"
        self._log.error(error_msg)
        self.__gateway.send_rpc_reply(device=device_name, req_id=rpc_id, content={"error": error_msg}, success_sent=False)

    def _handle_unknown_rpc_method(self, device_name, rpc_method, rpc_id):
        # 处理未知的RPC方法
        error_msg = f"RPC method {rpc_method} not found in config for device {device_name}"
        self._log.error(error_msg)
        self.__gateway.send_rpc_reply(device=device_name, req_id=rpc_id, content={"error": error_msg}, success_sent=False)

    def _convert_rpc_data(self, server_side_rpc_config, rpc_data, device_name, rpc_method, rpc_id):
        # 转换RPC数据
        try:
            return self.__downlink_converter.convert(server_side_rpc_config, rpc_data.get('params'))
        except Exception as e:
            error_msg = f"Failed to convert RPC data for method {rpc_method} of device {device_name}: {e}"
            self._log.error(error_msg)
            self.__gateway.send_rpc_reply(device=device_name, req_id=rpc_id, content={"error": error_msg}, success_sent=False)
            return None

    def _send_rpc_command(self, server_side_rpc_config, converted_data, device_name, rpc_method, rpc_data, rpc_id):
        # 发送RPC命令
        try:
            response = self.__send_rpc_command(server_side_rpc_config, converted_data)
            responseJson = json.dumps(response);
            self.__gateway.send_rpc_reply(device=device_name, req_id=rpc_id, content=responseJson, success_sent=True)
            self._log.debug(f"RPC {rpc_method} executed with data {rpc_data}, response: {responseJson}")
        except Exception as e:
            error_msg = f"Failed to send RPC command for method {rpc_method} of device {device_name}: {e}"
            self._log.error(error_msg)
            self.__gateway.send_rpc_reply(device=device_name, req_id=rpc_id, content={"error": error_msg}, success_sent=False)
    def __parse_config(self):
        pass

    def __init_serial_config(self):
        self.__serial_config = {
            'port': self.__config.get('port', DEFAULT_PORT),
            'baudrate': self.__config.get('baudrate', DEFAULT_BAUDRATE),
            'bytesize': self.__config.get('bytesize', DEFAULT_BYTESIZE),
            'parity': self.__config.get('parity', DEFAULT_PARITY),
            'stopbits': self.__config.get('stopbits', DEFAULT_STOPBITS),
            'timeout': self.__config.get('timeout', DEFAULT_TIMEOUT),
            'deviceAddress': self.__config.get('deviceAddress', DEFAULT_DEVICE_ADDRESS)
        }
    
    def __init_converters(self):
        self.__uplink_converter = Mu4801UplinkConverter(self.__config, self._log)
        self.__downlink_converter = Mu4801DownlinkConverter(self.__config, self._log)

    def __connect(self):
        try:
            self._log.info(f"[{self.name}] Connecting to serial port {self.__serial_config['port']}")
            self.__protocol = MU4801Protocol(
                config=self.__devices[0],
                device_addr=self.__serial_config['deviceAddress'],
                port=self.__serial_config['port'],
                baudrate=self.__serial_config['baudrate'],
                bytesize=self.__serial_config['bytesize'],
                parity=self.__serial_config['parity'],
                stopbits=self.__serial_config['stopbits'],
                timeout=self.__serial_config['timeout']
            )
            self.__protocol.connect()
            self.__connected = True
        except Exception as e:
            self._log.error(f"[{self.name}] Error connecting to serial port: {str(e)}")
            self.__connected = False


    def __run(self):
        while True:
            try:
                if not self.__connected:
                    self.__connect()

                if self.__connected:
                    self.__poll_devices()

                time.sleep(self.__config.get('pollInterval', DEFAULT_POLL_INTERVAL))
            except Exception as e:
                self._log.exception(f"Error in Mu4801 connector: {e}")
                time.sleep(RECONNECT_DELAY)  

    def __poll_devices(self):
        for device in self.__config['devices']:
            self.__process_device(device)

    def __process_device(self, device):
        device_name = device['deviceName']
        device_type = device.get('deviceType', 'default')
        self._log.debug(f"Processing device {device_name}")
        device_data = {'deviceName': device_name, 'deviceType': device_type, 'attributes': {}, 'telemetry': {}}

        for attribute_config in device.get('attributes', []):
            attribute_data = self.__read_device_data(attribute_config)
            if attribute_data:
                device_data['attributes'].update(attribute_data)

        for telemetry_config in device.get('timeseries', []):
            telemetry_data = self.__read_device_data(telemetry_config)
            if telemetry_data:
                device_data['telemetry'].update(telemetry_data)
        self._collect_statistic_and_send(self.get_name(), self.get_id(), device_data)

    def __disconnect(self):
        if self.__protocol:
            self.__protocol.disconnect()
            self.__connected = False
            self._log.info(f"[{self.name}] Disconnected from serial port")

    def __read_device_data(self, command_config):
        command_key = command_config['key']
        value = self.__protocol.send_command(command_key)
        if value:
            return value.to_dict()
        else:
            return {} 
    
    def _collect_statistic_and_send(self, connector_name, connector_id, data):
        self.statistics["MessagesReceived"] = self.statistics["MessagesReceived"] + 1
        
        # 调试日志:打印接收到的原始数据
        # self._log.debug(f"[{connector_name}] Received data from device: {data}")
        
        data=self.__uplink_converter.convert(config = self.__config, data = data)
        
        # 调试日志:打印转换后的数据
        # self._log.debug(f"[{connector_name}] Converted data: {data}")
        
        self.__gateway.send_to_storage(connector_name, connector_id, data)
        self.statistics["MessagesSent"] = self.statistics["MessagesSent"] + 1
        
        # 调试日志:确认数据已发送
        self._log.debug(f"[{connector_name}] Data sent to Thingsboard")
    
    def __update_device_attribute(self, attribute_updates_config, attribute_data):
        command_key = attribute_updates_config['key']
        try:
            self.__protocol.send_command(command_key, attribute_data)
            self._log.debug(f"Attribute {command_key} updated with value {attribute_data}")
        except Exception as e:
            self._log.exception(f"Error updating attribute {command_key}: {e}")
        
    def __get_device_by_name(self, device_name):
        for device in self.__devices:
            if device['deviceName'] == device_name:
                return device
        return None
    
    def __is_device_rpc(self, server_rpc_request):
        return 'device' in server_rpc_request and 'data' in server_rpc_request
    
    def __get_device_rpc_config(self, device, rpc_method_name):
        for rpc_config in device.get(SERVER_SIDE_RPC_PARAMETER, []):
            if rpc_config['key'] == rpc_method_name:
                return rpc_config
        return None
    
    def __send_rpc_command(self, server_side_rpc_config, rpc_data):  
        command_key = server_side_rpc_config['key']
        self._log.debug(f"Sending RPC command {command_key} with data: {rpc_data}")
        try:
            response = self.__protocol.send_command(command_key, rpc_data)
            self._log.debug(f"RPC {command_key} executed with data {rpc_data}, response: {response}")  
            if response :
                response_dict = response.to_dict()
            else:
                response_dict = {}
            self._log.debug(f"Converted response to dict: {response_dict}")
            return response_dict
        except Exception as e:
            self._log.exception(f"Error executing RPC {command_key}: {e}")
            return {"success": False, "error": str(e)}