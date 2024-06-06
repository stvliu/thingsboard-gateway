# mu4801_connector.py
import asyncio
import time
import serial
from random import choice
from string import ascii_lowercase
from threading import Thread
from thingsboard_gateway.connectors.connector import Connector
from thingsboard_gateway.tb_utility.tb_utility import TBUtility
from thingsboard_gateway.gateway.statistics_service import StatisticsService
from thingsboard_gateway.tb_utility.tb_logger import init_logger

from thingsboard_gateway.extensions.mu4801.mu4801_uplink_converter import Mu4801UplinkConverter
from thingsboard_gateway.extensions.mu4801.mu4801_downlink_converter import Mu4801DownlinkConverter
from thingsboard_gateway.extensions.mu4801.mu4801_protocol import MU4801Protocol

DEFAULT_PORT: str = '/dev/ttyUSB0'
DEFAULT_BAUDRATE = 9600
DEFAULT_BYTESIZE = serial.EIGHTBITS
DEFAULT_PARITY = serial.PARITY_NONE
DEFAULT_STOPBITS = serial.STOPBITS_ONE
DEFAULT_TIMEOUT = 1
DEFAULT_DEVICE_ADDRESS = 1
DEFAULT_POLL_INTERVAL = 5
RECONNECT_DELAY = 5.0  # 重连延迟
class Mu4801Connector(Thread, Connector):


    def __init__(self, gateway, config, connector_type):
        super().__init__()
        self.statistics = {'MessagesReceived': 0, 'MessagesSent': 0}
        self.__gateway = gateway
        self.__connector_type = connector_type
        self.__config = config
        self.__id = self.__config.get('id')
        self.name = config.get("name", 'MU4801 ' + ''.join(choice(ascii_lowercase) for _ in range(5)))
        self._log = init_logger(gateway, self.name, config.get('logLevel', 'INFO'))
        self._log.info("Initializing MU4801 connector")
        self.__devices = self.__config["devices"]
        self.__connected = False
        self.__stopped = False
        self.daemon = True

        self.__serial_config = None
        self.__parse_config()
        self.__init_serial_config()
        self.__init_converters()

        self.__loop = asyncio.new_event_loop()

        self._log.info("[%s] MU4801 connector initialized.", self.get_name())

    def open(self):
        self.__loop.run_until_complete(self.__run())

    def close(self):
        self.__stopped = True
        self.__disconnect()

    def get_id(self):
        return self.__id
    
    def get_name(self):
        return self.name

    def get_type(self):
        return self.__connector_type

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
        pass

    @StatisticsService.CollectAllReceivedBytesStatistics(start_stat_type='allReceivedBytesFromTB')
    def server_side_rpc_handler(self, device, data):
        self._log.debug(f"Received RPC for device {device}")
        for rpc_request in data:
            rpc_config = next((c for c in device.get('serverSideRpc', []) if c['method'] == rpc_request['method']), None)
            if rpc_config:
                command_data = self.__downlink_converter.convert(rpc_config, rpc_request['params'])
                reply = self.__protocol.send_command(rpc_config['key'], command_data)
                self.__gateway.send_rpc_reply(device, rpc_request['requestId'], self.__uplink_converter.convert(rpc_config, reply))
            else:
                self._log.error(f"RPC method {rpc_request['method']} not found for device {device}")

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


    async def __run(self):
        while True:
            try:
                if not self.__connected:
                    self.__connect()

                if self.__connected:
                    await self.__poll_devices()

                await asyncio.sleep(self.__config.get('pollInterval', DEFAULT_POLL_INTERVAL))
            except Exception as e:
                self._log.exception(f"Error in Mu4801 connector: {e}")
                await asyncio.sleep(RECONNECT_DELAY)  

    async def __poll_devices(self):
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


    # def _collect_statistic_and_send(self, connector_name, connector_id, data):
    #     self.statistics["MessagesReceived"] = self.statistics["MessagesReceived"] + 1
    #     self.__gateway.send_to_storage(connector_name, connector_id, data)
    #     self.statistics["MessagesSent"] = self.statistics["MessagesSent"] + 1
    
    # def _collect_statistic_and_send(self, connector_name, connector_id, data):
    #     self.statistics["MessagesReceived"] = self.statistics["MessagesReceived"] + 1
    #     attributes_data = [{
    #         'key': k,
    #         'value': v
    #     } for k, v in data['attributes'].items()]
    #     data_dict = {
    #         'deviceName': data['deviceName'], 
    #         'deviceType': data['deviceType'],
    #         'attributes': attributes_data,  
    #         'telemetry': [{
    #             'ts': int(time.time() * 1000),  # 当前时间戳
    #             'values': data['telemetry'] 
    #         }]
    #     }
    #     self.__gateway.send_to_storage(connector_name, connector_id, data_dict)
    #     self.statistics["MessagesSent"] = self.statistics["MessagesSent"] + 1
    
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