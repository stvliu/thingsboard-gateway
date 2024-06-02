import struct
import datetime
import logging
from dataclasses import dataclass
from typing import List, Dict, Union, Optional
import serial

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constant Definitions
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

# Exception Classes
class ProtocolError(Exception):
    pass

class RTNError(ProtocolError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)

class RTNVerError(RTNError):
    def __init__(self):
        super().__init__('0x01', "Version mismatch")

class RTNChksumError(RTNError):
    def __init__(self):
        super().__init__('0x02', "Checksum error")

class RTNLchksumError(RTNError):
    def __init__(self):
        super().__init__('0x03', "Length checksum error")

class RTNCidError(RTNError):
    def __init__(self):
        super().__init__('0x04', "Invalid CID")

class RTNFormatError(RTNError):
    def __init__(self):
        super().__init__('0x05', "Format error")

class RTNDataError(RTNError):
    def __init__(self):
        super().__init__('0x06', "Invalid data")


# Data Classes
@dataclass
class CommandData:
    key: str
    name: str
    data_type: str
    start_pos: int
    length: int
    enum: Union[Dict[str, int], None] = None

    def __post_init__(self):
        if self.data_type not in ['uint8', 'uint16', 'float', 'enum', 'datetime', 'string']:
            raise ValueError(f"Unsupported data type: {self.data_type}")

@dataclass
class CommandParam(CommandData):
    param_type: Union[str, None] = None

@dataclass
class CommandValue(CommandData):
    quantity: Union[int, str, None] = None

# Command Module
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
        logger.debug(f"Initializing Commands with config: {config}")
        self._command_dict = {}

        self._attributes = self._parse_commands(config['attributes'])
        self._timeseries = self._parse_commands(config['timeseries'])
        self._alarms = self._parse_commands(config['alarms'])
        self._server_side_rpc = self._parse_commands(config['serverSideRpc'])

        for command in self._attributes + self._timeseries + self._alarms + self._server_side_rpc:
            self._command_dict[(command.cid1, command.cid2)] = command
        logger.debug(f"Built command dictionary: {self._command_dict}")

    def _parse_commands(self, commands_configs):
        logger.debug(f"Parsing commands from config: {commands_configs}")
        commands = []
        for cmd_config in commands_configs:
            params = [CommandParam(**param) for param in cmd_config.get('params', [])]
            values = [CommandValue(**value) for value in cmd_config.get('values', [])]
            command = Command(cmd_config['cid1'], cmd_config['cid2'], cmd_config['key'], cmd_config['name'], params, values)
            commands.append(command)
        logger.debug(f"Parsed commands: {commands}")
        return commands

    def get_command_by_cid(self, cid1, cid2):
        logger.debug(f"Looking up command with cid1={cid1}, cid2={cid2}")
        command = self._command_dict.get((cid1, cid2))
        logger.debug(f"Found command: {command}")
        return command

    def get_command_by_key(self, command_key):
        logger.debug(f"Looking up command by key: {command_key}")
        for command in self._attributes + self._timeseries + self._alarms + self._server_side_rpc:
            if command.key == command_key:
                logger.debug(f"Found command: {command}")
                return command
        logger.debug(f"Command not found")
        return None

# Codec Module
class FieldCodec:
    """
    字段编解码器基类
    """

    def encode(self, value):
        """
        对一个包含多个值的字段进行编码
        :param values: 字段值的字典,键为值的key,值为具体的值
        :return: 编码后的字节流
        """
        raise NotImplementedError

    def decode(self, data):
        """
        从字节流中解码出多个值
        :param data: 字节流数据
        :return: 字段值的字典,键为值的key,值为解码后的具体值
        """
        raise NotImplementedError

class Type:
    def __init__(self):
        pass
    
    def fromBytes(self, bytes):
        pass
    def toBytes(self, data):
        pass
class UInt8(Type):
    def fromBytes(self, bytes):
        return struct.unpack('B', bytes)[0]
    def toBytes(self, data):
        return struct.pack('B', data)
    

class UInt16(Type):
    def fromBytes(self, bytes):
        return struct.unpack('>H', bytes)[0]
    def toBytes(self, data):
        return struct.pack('>H', data)
    

class Float(Type):
    def fromBytes(self, bytes):
        return struct.unpack('>f', bytes)[0]
    def toBytes(self, data):
        return struct.pack('>f', data)    


class Enum(Type):
    def __init__(self, enum_dict):
        self._enum_dict = enum_dict 

    def fromBytes(self, bytes):
        value = struct.unpack('B', bytes)[0]
        return next(key for key, val in self._enum_dict.items() if val == value)  
    def toBytes(self, data):
        value = self._enum_dict[data]
        return struct.pack('B', value)    

class String(Type): 
    def fromBytes(self, bytes):
        return bytes.decode('ascii')
    def toBytes(self, data):
        return data.encode('ascii')
class DateTime(Type):
    def fromBytes(self, bytes):
        year, month, day, hour, minute, second = struct.unpack('>HBBBBB', bytes)
        return datetime.datetime(year, month, day, hour, minute, second)
    def toBytes(self, data):
        return struct.pack('>HBBBBB', data.year, data.month, data.day, data.hour, data.minute, data.second)
class SoftwareVersion(Type):
    def fromBytes(self, bytes):
        major, minor = struct.unpack('BB', bytes)
        return f"{major}.{minor}"
    def toBytes(self, data):
        major, minor = map(int, data.split('.'))
        return struct.pack('BB', major, minor)    

class DataCodec:
    def __init__(self):
        self._types = {
                'uint8': UInt8(),
                'uint16': UInt16(),
                'float': Float(),
                'enum': Enum({}),
                'datetime': DateTime(),
                'string': String(),
                'software_version': SoftwareVersion()
        }

    def encode_value(self, value, value_type: str):
        logger.debug(f"Encoding value: {value}, value_type: {value_type}")
        value_type=self._coders[value_type]
        if value_type:
            encoded_value = value_type.toBytes(value)
            logger.debug(f"Encoded value: {encoded_value.hex()}")
            return encoded_value
        else:
            raise ValueError(f"Unsupported data type: {value_type}")
        
    def decode_value(self, bytes_value: bytes, value_type: str):
        logger.debug(f"Decoding value: {bytes_value.hex()}, value_type: {value_type}")
        value_type=self._coders[value_type.data_type]
        if value_type:
            decoded_value = value_type.fromBytes(bytes_value)
            logger.debug(f"Decoded value: {decoded_value.hex()}")
            return decoded_value
        else:
            raise ValueError(f"Unsupported data type: {value_type}")

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
        # frame.extend(FrameCodec._calculate_checksum(frame))
        frame.extend(FrameCodec._calculate_checksum(frame[VER_INDEX:]))
        frame.extend(struct.pack('B', EOI))
        logger.debug(f"Built frame: {frame.hex()}")
        return bytes(frame)

    @staticmethod
    def decode_frame(frame):
        logger.debug(f"Parsing frame: {frame.hex()}")
        # FrameCodec.validate_frame(frame)
        cid1 = f'0x{frame[CID1_INDEX]:02X}'
        logger.debug(f"cid1: {cid1}")
        cid2 = f'0x{frame[CID2_INDEX]:02X}'
        logger.debug(f"cid2: {cid2}")
        data = frame[INFO_INDEX:CHKSUM_INDEX]
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
        info_length = FrameCodec._decode_length(frame[LENGTH_INDEX:LENGTH_INDEX+2])
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
            logger.warn(f"Frame length mismatch: expected {expected_length}, got {len(frame)}")
            raise RTNLchksumError()
    
        #校验和校验
        received_checksum = frame[CHKSUM_INDEX:CHKSUM_INDEX + CHECKSUM_LENGTH]
        calculated_checksum =FrameCodec._calculate_checksum(frame[VER_INDEX:CHKSUM_INDEX])
        if received_checksum != calculated_checksum:
            logger.warn(f"calculated_checksum {calculated_checksum.hex()}, received_checksum {received_checksum.hex()}")
            raise RTNChksumError()
        
        # if len(frame) < MIN_FRAME_LENGTH:
        #     raise RTNFormatError()
        # if frame[0] != SOI:
        #     raise RTNFormatError()
        # if frame[-1] != EOI:
        #     raise RTNFormatError()
        # if frame[1] != PROTOCOL_VERSION:
        #     raise RTNVerError()

        # #长度校验
        # info_length = FrameCodec._decode_length(frame[LENGTH_INDEX:LENGTH_INDEX+2])
        # expected_length = (
        #     START_FLAG_LENGTH +
        #     ADDRESS_LENGTH +
        #     CONTROL_CODE_LENGTH +
        #     DATA_LENGTH_LENGTH +
        #     info_length +
        #     CHECKSUM_LENGTH +
        #     END_FLAG_LENGTH
        # )
        # expected_length = MIN_FRAME_LENGTH + info_length
        # if len(frame) != expected_length:
        #     raise RTNLchksumError(f"Frame length mismatch: expected {expected_length}, got {len(frame)}")
    
        # #校验和校验
        # received_checksum = frame[CHKSUM_INDEX:CHKSUM_INDEX + CHECKSUM_LENGTH]
        # calculated_checksum =FrameCodec._calculate_checksum(frame[VER_INDEX:CHKSUM_INDEX])
        # logger.debug(f"calculated_checksum {calculated_checksum.hex()}, received_checksum {received_checksum.hex()}")
        # if received_checksum != calculated_checksum:
        #     raise RTNChksumError(f"Checksum mismatch: expected {calculated_checksum.hex()}, got {received_checksum.hex()}")

        # info_length = FrameCodec._decode_length(frame[4:6])
        # expected_length = MIN_FRAME_LENGTH + info_length
        # if len(frame) != expected_length:
        #     raise RTNLchksumError()

        # received_checksum = frame[-3:-1]
        # calculated_checksum = FrameCodec._calculate_checksum(frame[1:-3])
        # logger.debug(f"calculated_checksum {calculated_checksum.hex()}, received_checksum {received_checksum.hex()}")
        # if received_checksum != calculated_checksum:
        #     raise RTNChksumError()

    # @staticmethod
    # def _encode_length(length):
    #     logger.debug(f"Encoding length: {length}")
    #     lenid = length & 0x0FFF
    #     lchksum = ((lenid & 0x0F) + ((lenid >> 4) & 0x0F) + ((lenid >> 8) & 0x0F)) & 0x0F
    #     lchksum = (~lchksum + 1) & 0x0F
    #     encoded_length = struct.pack('>H', (lchksum << 12) | lenid)
    #     logger.debug(f"Encoded length: {encoded_length.hex()}")
    #     return encoded_length

    # @staticmethod
    # def _decode_length(bytes_value):
    #     logger.debug(f"Decoding length: {bytes_value.hex()}")
    #     length = struct.unpack('>H', bytes_value)[0]
    #     lenid = length & 0x0FFF
    #     lchksum = (length >> 12) & 0x0F
    #     calc_lchksum = ((lenid & 0x0F) + ((lenid >> 4) & 0x0F) + ((lenid >> 8) & 0x0F)) & 0x0F
    #     calc_lchksum = (~calc_lchksum + 1) & 0x0F
    #     if lchksum != calc_lchksum:
    #         raise ProtocolError(f"Length checksum mismatch: expected {lchksum}, calculated {calc_lchksum}")
    #     logger.debug(f"Decoded length: {lenid}")
    #     return lenid

    # @staticmethod
    # def _calculate_checksum(data):
    #     logger.debug(f"Calculating checksum for data: {data.hex()}")
    #     checksum = sum(data) & 0xFFFF
    #     checksum = (~checksum + 1) & 0xFFFF
    #     checksum_bytes = struct.pack('>H', checksum)
    #     logger.debug(f"Calculated checksum: {checksum_bytes.hex()}")
    #     return checksum_bytes
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
        # 计算校验和  
        checksum = sum(data_for_checksum[1:]) % 65536
        checksum = (~checksum + 1) & 0xFFFF
        checksum_bytes = struct.pack('>H', checksum)
        logger.debug(f"Calculated checksum: {checksum_bytes.hex()}")
        return checksum_bytes

# Protocol Class
class Protocol:
    def __init__(self, device_addr = 1,  port=None, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None, config=None):
        logger.debug(f"Initializing Protocol with config={config}, port={port}, baudrate={baudrate}, bytesize={bytesize}, parity={parity}, stopbits={stopbits}, timeout={timeout}")
        self._commands = Commands(config)
        self._frame_codec = FrameCodec()
        self._data_codec = DataCodec()

        self._device_addr = device_addr
        self._port = port
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._timeout = timeout
        self._serial = None

    def get_device_addr(self):
        return self._device_addr
    
    def connect(self):
        import serial
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
            soi = self._serial.read(1)
            if len(soi) == 0 or soi[0] != SOI:
                raise ProtocolError(f"Invalid SOI: {soi.hex()}")

            # Read VER, ADR, CID1, CID2
            header = self._serial.read(4)
            if len(header) < 4:
                raise ProtocolError(f"Incomplete header: {header.hex()}")

            # Read LENGTH
            length = self._serial.read(2)
            if len(length) < 2:
                raise ProtocolError(f"Incomplete LENGTH: {length.hex()}")
            info_length = FrameCodec._decode_length(length)

            # Read INFO
            info = self._serial.read(info_length)
            if len(info) < info_length:
                raise ProtocolError(f"Incomplete INFO: {info.hex()}")

            # Read CHKSUM
            chksum = self._serial.read(2)
            if len(chksum) < 2:
                raise ProtocolError(f"Incomplete CHKSUM: {chksum.hex()}")

            # Read EOI
            eoi = self._serial.read(1)
            if len(eoi) == 0 or eoi[0] != EOI:
                raise ProtocolError(f"Invalid EOI: {eoi.hex()}")

            # Assemble the frame
            frame = soi + header + length + info + chksum + eoi
            logger.debug(f"Received frame: {frame.hex()}")
            FrameCodec.validate_frame(frame)
            return frame

        except serial.SerialTimeoutException:
            raise ProtocolError("Timeout waiting for response")

    def _build_command_frame(self, command, data):
        logger.debug(f"Building command frame: {command}, data: {data}")
        if not data:
            data = {}
        command_data = b''
        for param in command.params:
            value = data.get(param.key)
            if value is None:
                logger.warning(f"Missing parameter: {param.key}")
                return None
            command_data += self._data_codec.encode_value(value, param)
        command_frame = self._frame_codec.encode_frame(command.cid1, command.cid2, command_data, self._device_addr)
        logger.debug(f"Built command frame: {command_frame.hex()}")
        return command_frame

    def _decode_command_data(self, command, data):
        logger.debug(f"Decoding command data for {command}: {data.hex()}")
        if not data:
            return {}
        result = {}
        for param in command.params:
            result[param.key] = self._decode_value(data, param, result)
        logger.debug(f"Decoded command data: {result}")
        return result

    def _encode_response_data(self, command, data):
        logger.debug(f"Encoding response data for {command}: {data}")
        if not data:
            return b''
        response_data = b''
        for value in command.values:
            if value.key in data:
                response_data += self._data_codec.encode_value(data[value.key], value)
        logger.debug(f"Encoded response data: {response_data.hex()}")
        return response_data

    def _decode_response_data(self, command, response_frame):
        logger.debug(f"Decoding response data for {command}: {response_frame.hex()}")
        cid1, cid2, response_data = self._frame_codec.decode_frame(response_frame)
        if not response_data:
            return {}
        result = {}
        for value in command.values:
            result[value.key] = self._decode_value(response_data, value, result)
        logger.debug(f"Decoded response data: {result}")
        return result

    def _decode_value(self, data, data_config, result):
        logger.debug(f"Decoding value for {data_config} from {data.hex()}")
        if data_config.quantity and isinstance(data_config.quantity, str):
            # 变长字段，需要先获取长度
            length_key = data_config.quantity[2:-1]
            length = result[length_key]
            logger.debug(f"Decoding variable length value, length key: {length_key}, length: {length}")
        else:
            length = data_config.quantity or 1
            logger.debug(f"Decoding fixed length value, length: {length}")

        if length == 1:
            bytes_value = data[data_config.start_pos:data_config.start_pos+data_config.length]
            logger.debug(f"Decoding single value: {bytes_value.hex()}")
            return self._data_codec.decode_value(bytes_value, data_config)
        else:
            logger.debug(f"Decoding {length} values")
            values = []
            for i in range(length):
                bytes_value = data[data_config.start_pos+i*data_config.length:
                                   data_config.start_pos+(i+1)*data_config.length]
                logger.debug(f"Decoding value {i+1}/{length}: {bytes_value.hex()}")
                values.append(self._data_codec.decode_value(bytes_value, data_config))
            logger.debug(f"Decoded {length} values: {values}")
            return values

    def _validate_command_data(self, command, data):
        # TODO: Add validation logic based on command definition
        pass

    def _is_unidirectional_command(self, command):
        logger.debug(f"Checking if command is unidirectional: {command}")
        is_unidirectional = len(command.values) == 0
        logger.debug(f"Command is unidirectional: {is_unidirectional}")
        return is_unidirectional