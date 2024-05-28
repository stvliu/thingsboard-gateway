import struct
import logging
from dataclasses import dataclass
from typing import List, Dict, Union

from thingsboard_gateway.connectors.connector import log

@dataclass
class CommandData:
    name: str
    name_cn: str
    data_type: str
    start_pos: int
    length: int
    enum: Union[Dict[str, int], None] = None

@dataclass
class CommandParam(CommandData):
    param_type: Union[str, None] = None

@dataclass
class CommandValue(CommandData):
    quantity: Union[int, str, None] = None

@dataclass
class Command:
    cid1: str
    cid2: str
    name: str
    name_cn: str
    params: List[CommandParam]
    values: List[CommandValue]

class Protocol:
    START_CHAR = b'\x7E'  # 起始符
    END_CHAR = b'\x0D'    # 结束符
    PROTOCOL_VERSION = 33  # 协议版本号
    unidirectional_methods = []  # 无需设备响应的方法列表

    def __init__(self, device_addr, port='/dev/ttyS0', baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=1, config=None):
        self._device_addr = device_addr
        self._port = port
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._timeout = timeout
        self._config = config
        self._serial = None

    def connect(self):
        import serial
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
        log.debug(f"Connected to serial port {self._port}")

    def disconnect(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
            log.debug(f"Disconnected from serial port {self._port}")

    def is_connected(self):
        return self._serial and self._serial.is_open

    def send_command(self, command, data=None):
        if isinstance(command, str):
            command_obj = self._config.get_command(command)
            if not command_obj:
                raise ValueError(f"Command '{command}' not found in configuration.")
        else:
            command_obj = command
        
        if data is None:
            data = {}
        command_frame = self.build_command(command_obj, data)
        response = self._send_frame(command_frame)
        
        if not self.is_unidirectional_command(command_obj):
            result = self.parse_response(response, command_obj)
        else:
            result = None
            
        return result

    def _send_frame(self, frame):
        if not self.is_connected():
            raise Exception("Serial port is not connected")
        
        # 发送命令帧
        log.debug(f"Sending frame: {frame.hex()}")
        self._serial.write(frame)
        self._serial.flush()

        # 接收响应帧
        response = self._receive_frame()
        log.debug(f"Received response: {response.hex()}")

        return response

    def build_frame(self, cid1, cid2, data):
        # 构建命令帧
        frame = bytearray()
        frame.extend(self.START_CHAR)
        frame.extend(struct.pack('>B', self.PROTOCOL_VERSION))
        frame.extend(struct.pack('>B', self._device_addr))
        frame.extend(bytes.fromhex(cid1[2:]))
        frame.extend(bytes.fromhex(cid2[2:]))
        frame.extend(self._encode_length(len(data)))
        frame.extend(data)
        frame.extend(self._calculate_checksum(frame))
        frame.extend(self.END_CHAR)
        return bytes(frame)

    def _receive_frame(self):
        # 接收响应帧
        frame = bytearray()
        while True:
            byte = self._serial.read(1)
            if len(byte) == 0:
                raise Exception("Timeout waiting for response")
            if byte == self.START_CHAR:
                frame = bytearray(byte)
            elif byte == self.END_CHAR:
                frame.extend(byte)
                break
            else:
                frame.extend(byte)
        return bytes(frame)

    def _encode_length(self, length):
        # 编码数据长度
        lenid_low = length & 0xFF
        lenid_high = (length >> 8) & 0x0F
        lchksum = (lenid_low + lenid_high + length) % 16
        lchksum = (~lchksum + 1) & 0x0F
        return struct.pack('>BB', (lchksum << 4) | lenid_high, lenid_low)

    def _calculate_checksum(self, data):
        # 计算校验和
        checksum = sum(data[1:]) % 65536
        checksum = (~checksum + 1) & 0xFFFF
        return struct.pack('>H', checksum)

    def build_command(self, command: Command, data: dict):
        # 根据Command对象和参数字典组装命令帧
        command_data = b''
        for param in command.params:
            value = data[param.name]
            bytes_value = self.encode_value(value, param)
            command_data += bytes_value
        command_frame = self.build_frame(command.cid1, command.cid2, command_data)
        return command_frame

    def encode_value(self, value, data_config: CommandData):
        if data_config.data_type == 'uint8':
            return struct.pack('B', value)
        elif data_config.data_type == 'uint16':
            return struct.pack('>H', value)
        elif data_config.data_type == 'float':
            return struct.pack('>f', value)
        elif data_config.data_type == 'enum':
            return struct.pack('B', data_config.enum[value])
        
    def decode_value(self, bytes_value, data_config: CommandData):
        if data_config.data_type == 'uint8':
            return bytes_value[0]
        elif data_config.data_type == 'uint16':
            return struct.unpack('>H', bytes_value)[0]
        elif data_config.data_type == 'float':
            return struct.unpack('>f', bytes_value)[0]
        elif data_config.data_type == 'enum':
            value = bytes_value[0]
            return next(key for key, val in data_config.enum.items() if val == value)
        
    def parse_response(self, response, command: Command):
        # 根据Command对象解析响应帧
        result = {}
        for value_config in command.values:
            start_pos = value_config.start_pos
            length = value_config.length
            bytes_value = response[start_pos: start_pos+length]
            value = self.decode_value(bytes_value, value_config)
            result[value_config.name] = value
        return result
    
    def is_unidirectional_command(self, command):
        return command.name in self.unidirectional_methods