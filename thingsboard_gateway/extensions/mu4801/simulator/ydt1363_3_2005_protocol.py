import struct
import logging
import serial
from serial.serialutil import SerialException
from collections import namedtuple
from dataclasses import dataclass
import datetime
from typing import List, Dict, Union

# 帧结构常量
SOI = 0x7E  # 起始位标志(Start Of Information)
EOI = 0x0D  # 结束码(End Of Information)
PROTOCOL_VERSION = 0x21  # 协议版本号

# 帧结构中各字段的索引
SOI_INDEX = 0  # SOI字段的索引
VER_INDEX = 1  # 版本号字段的索引  
ADR_INDEX = 2  # 设备地址字段的索引
CID1_INDEX = 3  # 设备类型标识字段的索引
CID2_INDEX = 4  # 控制标识字段的索引
LENGTH_INDEX = 5  # 数据长度字段的索引
INFO_INDEX = 7  # 数据信息字段的索引
CHKSUM_INDEX = -3  # 校验和字段的索引
EOI_INDEX = -1  # EOI字段的索引

START_FLAG_LENGTH = 1  # 起始标志(lSTX)的长度
ADDRESS_LENGTH = 2     # 设备地址(lADDR)的长度
CONTROL_CODE_LENGTH = 2  # 控制码(lCTRL1, lCTRL2)的长度
DATA_LENGTH_LENGTH = 2   # 数据长度(lLENL, lLENH)的长度
CHECKSUM_LENGTH = 2      # 校验码(lCHKSUM)的长度
END_FLAG_LENGTH = 1      # 结束标志(lETX)的长度
MIN_FRAME_LENGTH = (     # 最小帧长度
        START_FLAG_LENGTH +
        ADDRESS_LENGTH +
        CONTROL_CODE_LENGTH +
        DATA_LENGTH_LENGTH +
        CHECKSUM_LENGTH +
        END_FLAG_LENGTH
    )

# 帧长度编码常量
LENID_ZERO = 0  # 长度标识为0,表示数据字段为空
LENID_LOW_MASK = 0xFF  # 长度标识低字节掩码
LENID_HIGH_MASK = 0x0F  # 长度标识高字节掩码  
LCHKSUM_MASK = 0xF0  # 长度校验和掩码
LCHKSUM_SHIFT = 4  # 长度校验和在字节中的偏移量

# CID1枚举值
CID1_ENUM = {
    "0x40": "开关电源系统（交流配电）",
    "0x41": "开关电源系统（整流器）",  
    "0x42": "开关电源系统（直流配电）"
}

# CID2枚举值
CID2_ENUM = {
    "0x41": "获取模拟量量化后数据（浮点数）",
    "0x43": "获取开关输入状态",
    "0x44": "获取告警状态",
    "0x45": "遥控",
    "0x46": "获取系统参数（浮点数）",
    "0x48": "设定系统参数（浮点数）",  
    "0x4D": "获取监测模块时间",
    "0x4E": "设置监测模块时间",
    "0x4F": "获取通信协议版本号",
    "0x50": "获取设备地址",
    "0x51": "获取设备（监测模块）厂家信息",
    "0x80": "修改系统控制状态",
    "0x81": "读取系统控制状态",
    "0x84": "后台告警音使能控制",
    "0x90": "读取节能参数",
    "0x91": "设置节能参数",
    "0x92": "系统控制"
}

# 告警枚举值
VOLT_ALARM_STATUS_ENUM = {
    0: "正常",
    1: "欠压", 
    2: "过压"
}

TEMP_ALARM_STATUS_ENUM = {
    0: "正常",
    176: "过温",
    177: "欠温" 
}

HUMIDITY_ALARM_STATUS_ENUM = {
    0: "正常",
    198: "过湿"
}

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')

@dataclass
class CommandData:
    key: str
    name: str
    data_type: str  
    start_pos: int
    length: int
    enum: Union[Dict[str, int], None] = None

    def __init__(self, **kwargs):
        self.key= kwargs['key']
        self.name = kwargs['name']
        self.data_type = kwargs['dataType']
        self.start_pos = kwargs['startPos']
        self.length = kwargs['length']
        self.enum = kwargs.get('enum')

    def __post_init__(self):
        if self.data_type not in ['uint8', 'uint16', 'float', 'enum', 'datetime', 'string']:
            raise ValueError(f"Unsupported data type: {self.data_type}")

@dataclass
class CommandParam(CommandData):
    param_type: Union[str, None] = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.param_type = kwargs.get('param_type')

@dataclass  
class CommandValue(CommandData):
    quantity: Union[int, str, None] = None
   
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.quantity = kwargs.get('quantity')

@dataclass
class Command:
    cid1: str
    cid2: str
    key: str
    name: str
    params: List[CommandParam]
    values: List[CommandValue]

class Commands:
    def __init__(self, config):
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.debug(f"Initializing Commands with config: {config}")
        self._attributes = self._parse_commands(config['attributes'])
        self._timeseries = self._parse_commands(config['timeseries'])
        self._alarms = self._parse_commands(config['alarms'])
        self._server_side_rpc = self._parse_commands(config['serverSideRpc'])

        self._command_dict = {}
        for command in self._attributes + self._timeseries + self._alarms + self._server_side_rpc:
            self._command_dict[(command.cid1, command.cid2)] = command
        self._log.debug(f"Built command dictionary: {self._command_dict}")
        
    def _parse_commands(self, commands_config):
        self._log.debug(f"Parsing commands from config: {commands_config}")
        commands = []
        for cmd_config in commands_config:
            params = [CommandParam(**param) for param in cmd_config.get('params', [])]
            values = [CommandValue(**value) for value in cmd_config.get('values', [])]
            command = Command(cmd_config['cid1'], cmd_config['cid2'], cmd_config['key'], cmd_config['name'], params, values)
            commands.append(command)
        self._log.debug(f"Parsed commands: {commands}")
        return commands

    def get_command(self, cid1, cid2):
        self._log.debug(f"Looking up command with cid1={cid1}, cid2={cid2}")
        command = self._command_dict.get((cid1, cid2))
        self._log.debug(f"Found command: {command}")
        return command
    
    def get_command(self, command_key):
        self._log.debug(f"Looking up command by key: {command_key}")
        for command in self._attributes + self._timeseries + self._alarms + self._server_side_rpc:
            if command.key == command_key:
                self._log.debug(f"Found command: {command}")
                return command
        self._log.debug(f"Command not found")
        return None
        
class ProtocolError(Exception):
    pass

class Protocol:
    def __init__(self, device_addr = 1,  port=None, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None, config=None):
        self._log = logging.getLogger(self.__class__.__name__)
        self._device_addr = device_addr
        self._port = port
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._timeout = timeout
        
        if config:
            self._commands = Commands(config)
        else:
            self._commands = None
        
        self._serial = None
        self._log.debug(f"Initialized Protocol with device_addr={device_addr}, port={port}, baudrate={baudrate}, bytesize={bytesize}, parity={parity}, stopbits={stopbits}, timeout={timeout}, config={config}")

    def connect(self):
        try: 
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=self._bytesize,
                parity=self._parity,
                stopbits=self._stopbits,
                timeout=self._timeout
            )
            self._serial.flushInput()
            self._serial.flushOutput()
            self._log.info(f"Connected to serial port {self._port}")
        except serial.SerialException as e:
            self._log.error(f"Failed to connect to serial port: {e}")
            raise ProtocolError(f"Serial connection failed: {e}")
        
    def disconnect(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
            self._log.info(f"Disconnected from serial port {self._port}")

    def is_connected(self):
        return self._serial and self._serial.is_open

    def send_command(self, command_key, data=None):
        self._log.debug(f"Sending command: {command_key}, data: {data}")
        if isinstance(command_key, str):
            command_obj = self._find_command_by_key(command_key)
            if not command_obj:
                self._log.warning(f"Command '{command_key}' not found in configuration.")
                return None
        else:
            command_obj = command_key

        command_frame = self.build_command(command_obj, data)
        if command_frame is None:
            self._log.warning(f"Failed to build command frame for {command_obj}")
            return None

        response = self._send_frame(command_frame)

        if not self.is_unidirectional_command(command_obj):
            response_command_obj = self._find_command_by_cid(response[CID1_INDEX], response[CID2_INDEX])
            if response_command_obj:
                result = self.parse_response(response, response_command_obj)
            else:
                self._log.warning(f"Unknown response command: cid1={response[CID1_INDEX]:02X}, cid2={response[CID2_INDEX]:02X}")
                result = None
        else:
            result = None

        self._log.debug(f"Command result: {result}")
        return result

    def _find_command_by_key(self, command_key):
        if not isinstance(command_key, str):
            self._log.error(f"command_key must be a string, but got {type(command_key)}")
            raise TypeError(f"command_key must be a string, but got {type(command_key)}")
        self._log.debug(f"Looking up command by key: {command_key}")
        command = self._commands.get_command(command_key)
        self._log.debug(f"Found command: {command}")
        return command
        
    def _find_command_by_cid(self, cid1, cid2):
        cid1_hex = f'0x{cid1:02X}'
        cid2_hex = f'0x{cid2:02X}'
        self._log.debug(f"Looking up command by cid: cid1={cid1_hex}, cid2={cid2_hex}")  
        command = self._commands.get_command(cid1_hex, cid2_hex)
        self._log.debug(f"Found command: {command}")
        return command
    
    def _send_frame(self, frame):
        self._log.debug(f"Sending frame: {frame.hex()}")
        if not self.is_connected():
            raise ProtocolError("Serial port is not connected")
        
        try:
            self._log.debug(f"Writing frame to serial port")
            self._serial.write(frame)
            self._serial.flush()
            self._log.debug(f"Frame sent")
        except serial.SerialTimeoutException as e:
            self._log.error(f"Timeout sending frame: {e}")
            raise ProtocolError(f"Timeout sending frame: {e}")
            
        try:  
            response = self._receive_command()
            self._log.debug(f"Received response: {response.hex()}")
        except ProtocolError as e:
            self._log.error(f"Error receiving response: {e}")
            raise e
        
        return response

    def build_frame(self, cid1, cid2, data):
        self._log.debug(f"Building frame: cid1={cid1}, cid2={cid2}, data={data.hex()}")
        # 构建命令帧
        frame = bytearray()
        frame.extend(struct.pack('B', SOI))
        frame.extend(struct.pack('B', PROTOCOL_VERSION))  
        frame.extend(struct.pack('B', self._device_addr))
        frame.extend(bytes.fromhex(cid1[2:]))
        frame.extend(bytes.fromhex(cid2[2:]))
        frame.extend(self._encode_length(len(data)))
        frame.extend(data)
        frame.extend(self._calculate_checksum(frame[VER_INDEX:]))
        frame.extend(struct.pack('B', EOI))
        self._log.debug(f"Built frame: {frame.hex()}")
        return bytes(frame)
    
    def _parse_frame(self, frame):
        self._log.debug(f"Parsing frame: {frame.hex()}")
        try:
            self._validate_frame(frame)
            cid1 = f'0x{frame[CID1_INDEX]:02X}'
            cid2 = f'0x{frame[CID2_INDEX]:02X}'
            data = frame[INFO_INDEX:CHKSUM_INDEX]
            command = self._find_command_by_cid(cid1, cid2)
            if command:
                values = self.parse_response(command, data)
                command.values = values
                self._log.debug(f"Parsed command: {command}")
                return command
            else:
                self._log.warning(f"Unknown command: cid1={cid1}, cid2={cid2}")
                return None
        except ProtocolError as e:
            self._log.error(f"Error parsing frame: {e}")
            raise e

    def _receive_command(self):
        self._log.debug(f"Receiving command")
        try:
            frame = bytearray()
            while True:
                byte = self._serial.read(1)
                if len(byte) == 0:
                    raise ProtocolError("Timeout waiting for response")
                if byte[0] == SOI:
                    frame = bytearray(byte)
                elif byte[0] == EOI:
                    frame.extend(byte)
                    break  
                else:
                    frame.extend(byte)
            self._log.debug(f"Received frame: {frame.hex()}")
            command = self._parse_frame(frame)
            return command
        except serial.SerialTimeoutException:
            raise ProtocolError("Timeout waiting for response")

    def parse_response(self, command: Command, data: bytes):
        self._log.debug(f"Parsing response for command: {command}")
        # 根据Command对象解析响应帧
        result = {}
        for value_config in command.values:
            start_pos = value_config.start_pos
            length = value_config.length

            # 处理带有quantity的情况
            quantity = value_config.quantity
            if isinstance(quantity, str):
                # 如果quantity是变量名，从result中取值  
                quantity = result[quantity[2:-1]]  # 去掉${}

            if quantity is None or quantity == 1:
                bytes_value = data[start_pos: start_pos+length]
                value = self.decode_value(bytes_value, value_config)
                result[value_config.key] = value
            else:
                # 多个重复值的情况
                values = []
                for i in range(quantity):
                    bytes_value = data[start_pos + i*length: start_pos + (i+1)*length]
                    value = self.decode_value(bytes_value, value_config)
                    values.append(value)
                result[value_config.key] = values

        self._log.debug(f"Parsed response: {result}")
        return result
    
    def _validate_frame(self, frame):
        #最小长度校验
        self._log.debug(f"Validating frame: {frame.hex()}")
        if len(frame) < MIN_FRAME_LENGTH:
            raise ProtocolError(f"Frame too short: {len(frame)} bytes")
        if frame[SOI_INDEX] != SOI:
            raise ProtocolError(f"Invalid start byte: {frame[SOI_INDEX]:02X}")
        if frame[EOI_INDEX] != EOI:
            raise ProtocolError(f"Invalid end byte: {frame[EOI_INDEX]:02X}")
        if frame[VER_INDEX] != PROTOCOL_VERSION:  
            raise ProtocolError(f"Unsupported protocol version: {frame[VER_INDEX]:02X}")
        
        #长度校验
        info_length = self._decode_length(frame[LENGTH_INDEX:LENGTH_INDEX+2])
        expected_length = (
            START_FLAG_LENGTH +
            ADDRESS_LENGTH +
            CONTROL_CODE_LENGTH +
            DATA_LENGTH_LENGTH +
            info_length +
            CHECKSUM_LENGTH +
            END_FLAG_LENGTH
        )
        expected_length = MIN_FRAME_LENGTH + info_length
        if len(frame) != expected_length:
            raise ValueError(f"Frame length mismatch: expected {expected_length}, got {len(frame)}")
    
        #校验和校验
        received_checksum = frame[CHKSUM_INDEX:CHKSUM_INDEX + CHECKSUM_LENGTH]
        calculated_checksum =self._calculate_checksum(frame[VER_INDEX:CHKSUM_INDEX])
        if received_checksum != calculated_checksum:
            raise ValueError(f"Checksum mismatch: expected {calculated_checksum.hex()}, got {received_checksum.hex()}")
      
    def _encode_length(self, length):
        self._log.debug(f"Encoding length: {length}")
        # 编码数据长度  
        lenid_low = length & LENID_LOW_MASK
        lenid_high = (length >> 8) & LENID_HIGH_MASK
        lchksum = (lenid_low + lenid_high + length) % 16  
        lchksum = (~lchksum + 1) & 0x0F
        encoded_length = struct.pack('BB', (lchksum << LCHKSUM_SHIFT) | lenid_high, lenid_low)
        self._log.debug(f"Encoded length: {encoded_length.hex()}")
        return encoded_length
    
    def _decode_length(self, length_bytes):
        self._log.debug(f"Decoding length: {length_bytes.hex()}")
        lenid_low = length_bytes[1]  
        lenid_high = length_bytes[0] & LENID_HIGH_MASK
        lchksum = (length_bytes[0] >> LCHKSUM_SHIFT) & 0x0F
        
        lenid = (lenid_high << 8) | lenid_low
        
        calculated_lchksum = (lenid_low + lenid_high + lenid) % 16
        calculated_lchksum = (~calculated_lchksum + 1) & 0x0F
        if lchksum != calculated_lchksum:
            raise ProtocolError(f"Invalid LCHKSUM: received={lchksum:X}, calculated={calculated_lchksum:X}")
        self._log.debug(f"Decoded length: {lenid}")
        return lenid

    def _calculate_checksum(self, data_for_checksum):
        self._log.debug(f"Calculating checksum for data: {data_for_checksum.hex()}")
        # 计算校验和  
        checksum = sum(data_for_checksum[1:]) % 65536
        checksum = (~checksum + 1) & 0xFFFF
        checksum_bytes = struct.pack('>H', checksum)
        self._log.debug(f"Calculated checksum: {checksum_bytes.hex()}")
        return checksum_bytes

    def build_command(self, command: Command, data: dict):  
        self._log.debug(f"Building command: {command}, data: {data}")
        # 根据Command对象和参数字典组装命令帧
        command_data = b''
        for param in command.params:
            value = data[param.key]
            bytes_value = self.encode_value(value, param)
            command_data += bytes_value
        command_frame = self.build_frame(command.cid1, command.cid2, command_data)
        self._log.debug(f"Built command frame: {command_frame.hex()}")
        return command_frame

    def encode_value(self, value, data_config: CommandData):
        self._log.debug(f"Encoding value: {value}, data_config: {data_config}")
        if data_config.data_type == 'uint8':
            encoded_value = struct.pack('B', value)
        elif data_config.data_type == 'uint16':
            encoded_value = struct.pack('>H', value)  
        elif data_config.data_type == 'float':
            encoded_value = struct.pack('>f', value)
        elif data_config.data_type == 'enum':  
            encoded_value = struct.pack('B', data_config.enum[value])
        elif data_config.data_type == 'datetime':
            encoded_value = self.encode_datetime(value)
        elif data_config.data_type == 'string':
            encoded_value = value.encode('ascii')
        else:
            raise ValueError(f"Unsupported data type: {data_config.data_type}")
        self._log.debug(f"Encoded value: {encoded_value.hex()}")
        return encoded_value

    def encode_datetime(self, dt: datetime):
        self._log.debug(f"Encoding datetime: {dt}")
        encoded_value = struct.pack('>HBBBBB', dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        self._log.debug(f"Encoded datetime: {encoded_value.hex()}")
        return encoded_value
        
    def decode_value(self, bytes_value, data_config: CommandData):
        self._log.debug(f"Decoding value: {bytes_value.hex()}, data_config: {data_config}")
        if data_config.data_type == 'uint8':
            decoded_value = bytes_value[0]  
        elif data_config.data_type == 'uint16':
            decoded_value = struct.unpack('>H', bytes_value)[0]
        elif data_config.data_type == 'float': 
            decoded_value = struct.unpack('>f', bytes_value)[0]
        elif data_config.data_type == 'enum':
            value = bytes_value[0] 
            decoded_value = next(key for key, val in data_config.enum.items() if val == value)
        elif data_config.data_type == 'datetime':
            decoded_value = self.decode_datetime(bytes_value)
        elif data_config.data_type == 'string':
            decoded_value = bytes_value.decode('ascii')   
        else:
            raise ValueError(f"Unsupported data type: {data_config.data_type}")
        self._log.debug(f"Decoded value: {decoded_value}")
        return decoded_value

    def decode_datetime(self, bytes_value):
        self._log.debug(f"Decoding datetime: {bytes_value.hex()}")
        year, month, day, hour, minute, second = struct.unpack('>HBBBBB', bytes_value)
        dt = datetime(year, month, day, hour, minute, second)
        self._log.debug(f"Decoded datetime: {dt}")
        return dt

    def is_unidirectional_command(self, command):
        self._log.debug(f"Checking if command is unidirectional: {command}")
        is_unidirectional = not command.values
        self._log.debug(f"Command is unidirectional: {is_unidirectional}")  
        return is_unidirectional