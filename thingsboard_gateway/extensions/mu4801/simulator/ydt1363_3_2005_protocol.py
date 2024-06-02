import struct
import datetime
import logging
from dataclasses import dataclass
from typing import List, Dict, Union, Optional
import serial
from enum import Enum
from commands import *

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 常量定义
SOI = 0x7E
EOI = 0x0D
PROTOCOL_VERSION = 0x21
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

# 返回码(RTN)常量
RTN_OK = 0x00  # 正常
RTN_VER_ERROR = 0x01  # VER错
RTN_CHKSUM_ERROR = 0x02  # CHKSUM错
RTN_LCHKSUM_ERROR = 0x03  # LCHKSUM错
RTN_CID2_INVALID = 0x04  # CID2无效
RTN_COMMAND_FORMAT_ERROR = 0x05  # 命令格式错
RTN_INVALID_DATA = 0x06  # 无效数据
RTN_USER_DEFINED_ERROR_START = 0x80  # 用户自定义错误码起始值
RTN_USER_DEFINED_ERROR_END = 0xEF  # 用户自定义错误码结束值

# 异常类
class ProtocolError(Exception):
    pass

class RTNError(ProtocolError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)

class RTNVerError(RTNError):
    def __init__(self):
        super().__init__(RTN_VER_ERROR, "Version mismatch")

class RTNChksumError(RTNError):
    def __init__(self):
        super().__init__(RTN_CHKSUM_ERROR, "Checksum error")

class RTNLchksumError(RTNError):
    def __init__(self):
        super().__init__(RTN_LCHKSUM_ERROR, "Length checksum error")

class RTNCidError(RTNError):
    def __init__(self):
        super().__init__(RTN_CID2_INVALID, "Invalid CID")

class RTNFormatError(RTNError):
    def __init__(self):
        super().__init__(RTN_COMMAND_FORMAT_ERROR, "Format error")

class RTNDataError(RTNError):
    def __init__(self):
        super().__init__(RTN_INVALID_DATA, "Invalid data")

# 数据类编解码器
class DataCodec:
    def __init__(self):
        self._types = {
                'uint8': self._uint8_codec,
                'uint16': self._uint16_codec,
                'float': self._float_codec,
                'enum': self._enum_codec,
                'datetime': self._datetime_codec,
                'string': self._string_codec
        }
 
    def to_bytes(self, value, data_type: str):
        if data_type in self._types:
            codec = self._types[data_type]
            bytes = codec().encode(value)
            logger.debug(f"Encoded value: {bytes.hex()}")
            return bytes
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
        
    def from_bytes(self, bytes, data_type: str):
        if data_type in self._types:
            codec = self._types[data_type]
            data = codec().decode(bytes)
            logger.debug(f"Decoded value: {data}")
            return data
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
        
    def _uint8_codec(self):
        return UInt8Codec()
    
    def _uint16_codec(self):
        return UInt16Codec()
        
    def _float_codec(self):
        return FloatCodec()
        
    def _enum_codec(self):
        return Enum(self._commands.get_enums())
        
    def _datetime_codec(self):
        return DateTimeCodec()
        
    def _string_codec(self):
        return StringCodec()
        
class Codec:
    def encode(self, value):
        raise NotImplementedError
        
    def decode(self, data):
        raise NotImplementedError
        
class UInt8Codec(Codec):
    def encode(self, value):
        return struct.pack('B', value)
        
    def decode(self, data):
        return struct.unpack('B', data)[0]
        
class UInt16Codec(Codec):
    def encode(self, value):
        return struct.pack('>H', value)
        
    def decode(self, data):
        return struct.unpack('>H', data)[0]
        
class FloatCodec(Codec):
    def encode(self, value):
        return struct.pack('>f', value)
        
    def decode(self, data):
        return struct.unpack('>f', data)[0]
        
class Enum(Codec):
    def __init__(self, enum_dict):
        self._enum_dict = enum_dict
        self._value_to_byte = {value: struct.pack('B', value) for value in enum_dict.values()}
        self._byte_to_value = {byte_value: key for key, byte_value in self._value_to_byte.items()}

    def encode(self, value):
        if value in self._enum_dict.keys():
            enum_value = self._enum_dict[value]
            return self._value_to_byte[enum_value]
        else:
            raise ValueError(f"Invalid enum value: {value}")
        
    def decode(self, data):
        value = struct.unpack('B', data)[0]
        return self._byte_to_value.get(value, None)
        
class DateTimeCodec(Codec):
    def encode(self, value):
        return struct.pack('>HBBBBB', value.year, value.month, value.day, value.hour, value.minute, value.second)
        
    def decode(self, data):
        year, month, day, hour, minute, second = struct.unpack('>HBBBBB', data)
        return datetime.datetime(year, month, day, hour, minute, second)
        
class StringCodec(Codec):
    def encode(self, value):
        return value.encode('ascii')
        
    def decode(self, data):
        return data.decode('ascii')

# 帧编解码器        
class FrameCodec:
    @staticmethod
    def encode_frame(cid1, cid2, data, address=0x00):
        logger.debug(f"Building frame: cid1={cid1}, cid2={cid2}, data={data.hex() if data else None}")
        frame = bytearray()
        frame.extend(struct.pack('B', SOI))
        frame.extend(struct.pack('B', PROTOCOL_VERSION))
        frame.extend(struct.pack('B', address))
        frame.extend(bytes.fromhex(cid1[2:]))
        frame.extend(bytes.fromhex(cid2[2:]))
        frame.extend(FrameCodec._encode_length(len(data)))
        frame.extend(data)
        frame.extend(FrameCodec._calculate_checksum(frame[1:]))
        frame.extend(struct.pack('B', EOI))
        logger.debug(f"Built frame: {frame.hex()}")
        return bytes(frame)

    @staticmethod
    def decode_frame(frame):
        logger.debug(f"Parsing frame: {frame.hex()}")
        FrameCodec.validate_frame(frame)
        cid1 = f'0x{frame[CID1_INDEX]:02X}'
        logger.debug(f"cid1: {cid1}")
        cid2 = f'0x{frame[CID2_INDEX]:02X}'
        logger.debug(f"cid2: {cid2}")
        data_start = INFO_INDEX
        data_end = len(frame) + CHKSUM_INDEX
        data = frame[data_start:data_end]
        logger.debug(f"data: {data.hex()}")
        return cid1, cid2, data

    @staticmethod
    def validate_frame(frame):
        logger.debug(f"Validating frame: {frame.hex()} , length: {len(frame)}")
        #最小长度校验
        if len(frame) < MIN_FRAME_LENGTH:
            logger.warn(f"Frame too short: {len(frame)} bytes")
            raise RTNFormatError()
        if frame[SOI_INDEX] != SOI:
            logger.warn(f"Invalid start byte: {int.from_bytes(frame[SOI_INDEX:SOI_INDEX+1], 'big'):02X}")
            raise RTNFormatError()
        if frame[EOI_INDEX] != EOI:
            logger.warn(f"Invalid end byte: {int.from_bytes(frame[EOI_INDEX:EOI_INDEX+1], 'big'):02X}")
            raise RTNFormatError()
        if frame[VER_INDEX] != PROTOCOL_VERSION:  
            logger.warn(f"Version mismatch: expected {PROTOCOL_VERSION}, got {frame[VER_INDEX]}")
            raise RTNFormatError()
        
        #长度校验
        info_length = FrameCodec._decode_length(frame[LENGTH_INDEX:LENGTH_INDEX+DATA_LENGTH_LENGTH])
        expected_length = MIN_FRAME_LENGTH + info_length
        if len(frame) != expected_length:
            logger.warn(f"Frame length mismatch: expected {expected_length}, got {len(frame)}")
            raise RTNLchksumError()
    
        #校验和校验
        received_checksum = frame[CHKSUM_INDEX:CHKSUM_INDEX + CHECKSUM_LENGTH]
        calculated_checksum = FrameCodec._calculate_checksum(frame[VER_INDEX:CHKSUM_INDEX])
        if received_checksum != calculated_checksum:
            logger.warn(f"Checksum mismatch: expected {calculated_checksum.hex()}, got {received_checksum.hex()}")
            raise RTNChksumError()
        
    @staticmethod
    def _encode_length(length):
        logger.debug(f"Encoding length: {length}")
        # 编码数据长度  
        lenid_low = length & LENID_LOW_MASK
        lenid_high = (length >> 8) & LENID_HIGH_MASK
        lchksum = (lenid_low + lenid_high + length) % 16  
        lchksum = (~lchksum + 1) & 0x0F
        encoded_length = struct.pack('BB', (lchksum << LCHKSUM_SHIFT) | lenid_high, lenid_low)
        logger.debug(f"Encoded length: {encoded_length.hex()}")
        return encoded_length
    
    @staticmethod
    def _decode_length(length_bytes):
        logger.debug(f"Decoding length: {length_bytes.hex()}")
        lenid_low = length_bytes[1]  
        lenid_high = length_bytes[0] & LENID_HIGH_MASK
        lchksum = (length_bytes[0] >> LCHKSUM_SHIFT) & 0x0F
        
        lenid = (lenid_high << 8) | lenid_low
        
        calculated_lchksum = (lenid_low + lenid_high + lenid) % 16
        calculated_lchksum = (~calculated_lchksum + 1) & 0x0F
        if lchksum != calculated_lchksum:
            raise ProtocolError(f"Invalid LCHKSUM: received={lchksum:X}, calculated={calculated_lchksum:X}")
        logger.debug(f"Decoded length: {lenid}")
        return lenid
    
    @staticmethod
    def _calculate_checksum(data_for_checksum):
        logger.debug(f"Calculating checksum for data: {data_for_checksum.hex()}")
        checksum = sum(data_for_checksum) % 65536
        checksum = (~checksum + 1) & 0xFFFF
        checksum_bytes = struct.pack('>H', checksum)
        logger.debug(f"Calculated checksum: {checksum_bytes.hex()}")
        return checksum_bytes
        
# 命令类        
class Command:
    def __init__(self, cid1, cid2, key, name, request_class, response_class):
        self.cid1 = cid1
        self.cid2 = cid2
        self.key = key
        self.name = name
        self.request_class = request_class
        self.response_class = response_class
        
# 命令管理器
class Commands:
    def __init__(self, config):
        logger.debug(f"Initializing Commands with config: {config}")
        self._enums = {}
        self._commands_by_cid = {}
        self._commands_by_key = {}
        self._attributes = self._parse_commands(config['attributes'])
        self._timeseries = self._parse_commands(config['timeseries'])
        self._alarms = self._parse_commands(config['alarms'])
        self._server_side_rpc = self._parse_commands(config['serverSideRpc'])
        for command in self._attributes + self._timeseries + self._alarms + self._server_side_rpc:
            self._commands_by_cid[(command.cid1, command.cid2)] = command
            self._commands_by_key[command.key] = command

    def _parse_commands(self, cmd_configs):
        commands = []
        for cmd_config in cmd_configs:
            cid1 = cmd_config['cid1']
            cid2 = cmd_config['cid2']
            key = cmd_config['key']
            name = cmd_config['name']
            request_class_name = cmd_config.get('request')
            response_class_name = cmd_config.get('response')
            
            request_class = None
            if request_class_name:
                request_module = __import__('commands', fromlist=[request_class_name])
                request_class = getattr(request_module, request_class_name)
                self._collect_enums(request_class, self._enums)
                
            response_class = None  
            if response_class_name:
                response_module = __import__('commands', fromlist=[response_class_name])
                response_class = getattr(response_module, response_class_name)
                self._collect_enums(response_class, self._enums)
                
            cmd = Command(cid1, cid2, key, name, request_class, response_class)
            commands.append(cmd)

        return commands

    def get_command_by_cid(self, cid1, cid2):
        logger.debug(f"Looking up command with cid1={cid1}, cid2={cid2}")
        command = self._commands_by_cid.get((cid1, cid2))
        logger.debug(f"Found command: {command}")
        return command

    def get_command_by_key(self, command_key):
        logger.debug(f"Looking up command by key: {command_key}")
        command = self._commands_by_key.get(command_key)
        logger.debug(f"Found command: {command}")
        return command

    def get_enums(self):
        return self._enums
    
    def _collect_enums(self, data_class, enums):
        from dataclasses import fields
        for field in fields(data_class):
            if field.type is Enum:
                enums.update(field.type.enum_dict)
        from dataclasses import fields
        for field in fields(data_class):
            if field.type is Enum:
                enums.update(field.type.enum_dict)
        
# 协议类
class Protocol:
    def __init__(self, device_addr = 1,  port=None, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None, config=None):
        logger.debug(f"Initializing Protocol with config={config}, port={port}, baudrate={baudrate}, bytesize={bytesize}, parity={parity}, stopbits={stopbits}, timeout={timeout}")
        self._commands = Commands(config)
        self._frame_codec = FrameCodec()
        self._data_codec = DataCodec()
        self._data_codec._commands = self._commands

        self._device_addr = device_addr
        self._port = port
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._timeout = timeout
        self._serial = None

    @property
    def device_addr(self):
        return self._device_addr
    
    def connect(self):
        try:
            logger.debug(f"Connecting to serial port {self._port}")
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
            logger.info(f"Connected to serial port {self._port}")
        except serial.SerialException as e:
            logger.error(f"Failed to connect to serial port: {e}")
            raise ProtocolError(f"Serial connection failed: {e}")

    def disconnect(self):
        if self._serial and self._serial.is_open:
            logger.debug(f"Disconnecting from serial port {self._port}")
            self._serial.close()
            logger.info(f"Disconnected from serial port {self._port}")

    def send_command(self, command_key, data=None):
        logger.debug(f"Sending command: {command_key}, data: {data}")
        command = self._commands.get_command_by_key(command_key)
        if not command:
            logger.warning(f"Command '{command_key}' not found in configuration.")
            return None
        command_frame = self._build_command_frame(command, data)
        if command_frame is None:
            logger.warning(f"Failed to build command frame for {command}")
            return None
        self._send_frame(command_frame)
        if not self._is_unidirectional_command(command):
            # 接收响应帧
            response_frame = self._receive_frame() 
            if response_frame is None:
                logger.warning(f"No response received for command: {command}")
                return None
            response_data = self._decode_response_data(command, response_frame)
            logger.debug(f"Decoded response data: {response_data}")
            return response_data

    def receive_command(self):
        frame = self._receive_frame()
        try:
            cid1, cid2, data = self._frame_codec.decode_frame(frame)
        except ProtocolError:
            raise RTNFormatError()

        command = self._commands.get_command_by_cid(cid1, cid2)
        if not command:
            raise RTNCidError()

        try:
            command_data = self._decode_command_data(command, data)
        except ProtocolError:
            raise RTNDataError()

        logger.debug(f"Received command: {command}, data: {command_data}")
        return command, command_data

    def send_response(self, ref_command, rtn_code, response_data=None):
        logger.debug(f"Sending response for request: {ref_command}, rtn_code: {rtn_code}, data: {response_data}")
        try:
            response_frame = self._frame_codec.encode_frame(
                ref_command.cid1,
                rtn_code,
                self._encode_response_data(ref_command, response_data),
                self._device_addr
            )
            self._send_frame(response_frame)
            logger.debug(f"Response sent")
        except ProtocolError as e:
            logger.error(f"Failed to send response: {e}")
            raise RTNFormatError() from e

    def _send_frame(self, frame):
        logger.debug(f"Sending frame: {frame.hex()}")
        if not self._serial or not self._serial.is_open:
            raise ProtocolError("Serial port is not connected")

        try:
            logger.debug(f"Writing frame to serial port")
            self._serial.write(frame)
            self._serial.flush()
            logger.debug(f"Frame sent")
        except serial.SerialTimeoutException as e:
            logger.error(f"Timeout sending frame: {e}")
            raise ProtocolError(f"Timeout sending frame: {e}")
    
    def _receive_frame(self):
        logger.debug(f"Receiving frame")
        try:
            # Read SOI
            soi = self._serial.read(START_FLAG_LENGTH)
            if len(soi) == 0 or soi[0] != SOI:
                raise ProtocolError(f"Invalid SOI: {soi.hex()}")

            # Read VER, ADR, CID1, CID2
            header = self._serial.read(ADDRESS_LENGTH + CONTROL_CODE_LENGTH)
            if len(header) < ADDRESS_LENGTH + CONTROL_CODE_LENGTH:
                raise ProtocolError(f"Incomplete header: {header.hex()}")

            # Read LENGTH
            length = self._serial.read(DATA_LENGTH_LENGTH)
            if len(length) < DATA_LENGTH_LENGTH:
                raise ProtocolError(f"Incomplete LENGTH: {length.hex()}")
            info_length = FrameCodec._decode_length(length)

            # Read INFO
            info = self._serial.read(info_length)
            if len(info) < info_length:
                raise ProtocolError(f"Incomplete INFO: {info.hex()}")

            # Read CHKSUM
            chksum = self._serial.read(CHECKSUM_LENGTH)
            if len(chksum) < CHECKSUM_LENGTH:
                raise ProtocolError(f"Incomplete CHKSUM: {chksum.hex()}")

            # Read EOI
            eoi = self._serial.read(END_FLAG_LENGTH)
            if len(eoi) == 0 or eoi[0] != EOI:
                raise ProtocolError(f"Invalid EOI: {eoi.hex()}")

            # Assemble the frame
            frame = soi + header + length + info + chksum + eoi
            logger.debug(f"Received frame: {frame.hex()}")
            return frame

        except serial.SerialTimeoutException:
            raise ProtocolError("Timeout waiting for response")

    def _build_command_frame(self, command, data):
        logger.debug(f"Building command frame: {command}, data: {data}")
        if not data:
            data = {}
        if command.request_class:
            try:
                request_obj = command.request_class(**data)
                command_data = request_obj.to_bytes()
            except Exception as e:
                logger.error(f"Error building request object: {e}")
                return None
        else:
            command_data = b''
        command_frame = self._frame_codec.encode_frame(command.cid1, command.cid2, command_data, self._device_addr)
        logger.debug(f"Built command frame: {command_frame.hex()}")
        return command_frame

    def _decode_command_data(self, command, data):
        logger.debug(f"Decoding command data for {command}: {data.hex()}")
        if not data:
            return {}
        if command.request_class:
            try:
                command_data = command.request_class.from_bytes(data)
            except Exception as e:
                logger.error(f"Error decoding request data: {e}")
                raise ProtocolError(f"Error decoding request data: {e}")
        else:
            command_data = {}
        logger.debug(f"Decoded command data: {command_data}")
        return command_data

    def _encode_response_data(self, command, data):
        logger.debug(f"Encoding response data for {command}: {data}")
        if command.response_class:
            try:
                if isinstance(data, command.response_class):
                    response_data = data.to_bytes()
                else:
                    response_data = self._data_codec.to_bytes(data)
            except Exception as e:
                logger.error(f"Error encoding response data: {e}")
                raise ProtocolError(f"Error encoding response data: {e}")
        else:
            response_data = b''
        logger.debug(f"Encoded response data: {response_data.hex()}")
        return response_data

    def _decode_response_data(self, command, response_frame):
        logger.debug(f"Decoding response data for {command}: {response_frame.hex()}")
        if command.response_class:
            try:
                cid1, cid2, response_data = self._frame_codec.decode_frame(response_frame)
                response_data = command.response_class.from_bytes(response_data)
            except Exception as e:
                logger.error(f"Error decoding response data: {e}")
                raise ProtocolError(f"Error decoding response data: {e}")
        else:
            response_data = {}
        logger.debug(f"Decoded response data: {response_data}")
        return response_data

    def _validate_command_data(self, command, data):
        # TODO: Add validation logic based on command definition
        pass

    def _is_unidirectional_command(self, command):
        logger.debug(f"Checking if command is unidirectional: {command}")
        is_unidirectional = command.response_class is None
        logger.debug(f"Command is unidirectional: {is_unidirectional}")
        return is_unidirectional 