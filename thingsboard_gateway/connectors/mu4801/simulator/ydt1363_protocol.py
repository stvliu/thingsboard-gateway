import struct
import datetime
import logging
from dataclasses import dataclass
from typing import List, Dict, Union, Optional
import serial
from enum import Enum
from constants import *
from exceptions import *
from models import *
from frame_codec import FrameCodec
from data_codec import DataCodec
from commands import Commands
from serial_link import SerialLink

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)
     
# 协议类
class Ydt1363Protocol:
    def __init__(self, device_addr = 1,  port=None, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None, config=None):
        logger.debug(f"Initializing Protocol with port={port}, baudrate={baudrate}, bytesize={bytesize}, parity={parity}, stopbits={stopbits}, timeout={timeout}")
        self._device_addr = device_addr
        self._port = port
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._timeout = timeout
        self._config = config

        self._commands = Commands(config)
        self._frame_codec = FrameCodec()
        self._data_codec = DataCodec()
        self._serial_link = SerialLink(device_addr, port)

    @property
    def device_addr(self):
        return self._device_addr
    
    def connect(self):
        self._serial_link.connect()
    
    def disconnect(self):
        self._serial_link.disconnect()

    def is_connected(self):
        return self._serial_link.is_connected()
    
    def send_command(self, command_key, data=None):
        logger.debug(f"Sending command: {command_key}, data: {data}")
        command = self._commands.get_command_by_key(command_key)
        if command is None:
            raise ValueError(f"Unknown command: {command_key}")
        # 构建请求帧
        request_frame = self._build_command_frame(command, data)
        # 发送请求帧
        self._send_frame(request_frame)
        
        # 接收响应帧
        response_frame = self._receive_frame()
        if response_frame is None:
            raise ProtocolError(f"No response received for command: {command}")
        
        # 解析响应数据
        response_data = self._decode_response_data(command, response_frame)
        
        # 检查返回码
        rtn_code = response_frame[CID2_INDEX]
        if rtn_code == RTN_OK:
            logger.debug(f"Received normal response: {response_data}")
            return response_data
        else:
            logger.debug(f"Received error response: RTN={rtn_code}")
            self._handle_error_response(rtn_code)

    def receive_command(self):
        request_frame = self._receive_frame()
        try:
            cid1, cid2, request_bytes = self._frame_codec.decode_frame(request_frame)
        except ProtocolError as e:
            # 根据不同的错误类型,发送相应的错误响应
            if isinstance(e, RTNVerError):
                self._send_error_response(RTN_VER_ERROR)
            elif isinstance(e, RTNChksumError):
                self._send_error_response(RTN_CHKSUM_ERROR)
            elif isinstance(e, RTNLchksumError):
                self._send_error_response(RTN_LCHKSUM_ERROR)
            else:
                self._send_error_response(RTN_COMMAND_FORMAT_ERROR)
            raise e

        request_command = self._commands.get_command_by_cid(cid1, cid2)
        if not request_command:
            logger.warning(f"Command with cid1={cid1}, cid2={cid2} not found in configuration.",exc_info=True)
            # 如果找不到对应的命令,发送一个CID2无效的错误响应
            self._send_error_response(RTN_CID2_INVALID)
            raise RTNCidError(cid1=cid1, cid2=cid2)
        try:
            request_data = self._decode_request_data(request_command, request_bytes)
        except ProtocolError:
            logger.warning(f"Error decoding command data: {request_bytes.hex()}",exc_info=True)
            # 如果解析命令数据失败,发送一个无效数据的错误响应
            self._send_error_response(RTN_INVALID_DATA)
            raise RTNDataError()
        logger.debug(f"Received command: {request_command}, data: {request_data}")
        return request_command, request_data

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
            logger.error(f"Failed to send response: {e}", exc_info=True)
            raise RTNFormatError() from e
    
    def _send_frame(self, frame):
        self._serial_link.send_frame(frame)
    
    def _receive_frame(self):
        return self._serial_link.receive_frame()

    def _build_command_frame(self, command, data):
        """
        构建命令帧。

        :param command: 命令对象,包含命令类型信息。
        :param data: 请求数据,可以是一个字典或者一个请求类的对象。
        :return: 构建好的命令帧(字节串),如果构建失败则返回None。
        """
        logger.debug(f"Building command frame: {command}, data: {data}")

        if command.request_class:
            # 如果命令有关联的请求类
            if not isinstance(data, command.request_class):
                # 如果提供的数据不是一个请求类的对象,尝试用数据字典创建一个
                try:
                    request_obj = command.request_class(**data)
                except Exception as e:
                    raise ProtocolError(f"Failed to create request object: {e} for command: {command.key}")
            else:
                # 如果提供的数据已经是一个请求类的对象,直接使用它
                request_obj = data
            try:
                # 尝试将请求对象序列化为字节串
                command_data = request_obj.to_bytes()
            except Exception as e:
                # 如果序列化失败,记录错误并返回None
                raise ProtocolError(f"Failed to serialize request object: {e} for command: {command.key}")
        else:
            # 如果命令没有关联的请求类,将命令数据设为空字节串
            command_data = b''

        # 使用帧编码器将命令类型、命令数据和设备地址编码为命令帧
        command_frame = self._frame_codec.encode_frame(command.cid1, command.cid2, command_data, self._device_addr)
        logger.debug(f"Built command frame: {command_frame.hex()}")

        # 返回构建好的命令帧
        return command_frame
    
    def _encode_response_data(self, command, data):
        logger.debug(f"Encoding response data for {command}: {data}")
        logger.debug(f"Checking if command {command} has response_class")
        if command.response_class:
            logger.debug(f"Command {command} has response_class: {command.response_class}")
            try:
                logger.debug(f"Checking if data {data} is instance of {command.response_class}")
                if isinstance(data, command.response_class):
                    logger.debug(f"Data {data} is instance of {command.response_class}, encoding to bytes")
                    response_data = data.to_bytes()
                else:
                    logger.debug(f"Data {data} is not instance of {command.response_class}, encoding with data codec")
                    response_data = self._data_codec.to_bytes(data)
                
                logger.debug(f"Checking if encoded response data is None")
                if response_data is None:  # 添加检查
                    logger.error(f"Failed to encode response data: {data}", exc_info=True)
                    raise ProtocolError(f"Failed to encode response data: {data}")
                
            except Exception as e:
                logger.error(f"Error encoding response data: {e}", exc_info=True)
                raise ProtocolError(f"Error encoding response data: {e}")
        else:
            logger.debug(f"Command {command} does not have response_class, setting response_data to empty bytes")
            response_data = b''
            
        logger.debug(f"Encoded response data: {response_data.hex()}")
        return response_data

    def _decode_request_data(self, command, request_bytes):
        logger.debug(f"Decoding command data for {command}: {request_bytes.hex()}")
        if not request_bytes:
            return {}
        if command.request_class:
            try:
                request_data = command.request_class.from_bytes(request_bytes)
            except Exception as e:
                logger.error(f"Error decoding request data: {e}")
                raise ProtocolError(f"Error decoding request data: {e}")
        else:
            request_data = {}
        logger.debug(f"Decoded command data: {request_data}")
        return request_data
    
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
    
    def _send_error_response(self, rtn_code):
        """
        发送错误响应。

        :param rtn_code: 错误码。
        """
        response_frame = self._frame_codec.encode_frame(
            '0x00',  # 使用一个虚拟的CID1
            rtn_code,  # 错误码作为RTN
            b'',  # 错误响应没有数据
            self._device_addr
        )
        self._send_frame(response_frame)

    def _handle_error_response(self, rtn_code):
        """
        处理错误响应。

        :param rtn_code: 返回码。
        :raises ProtocolError: 如果返回码表示一个错误。
        """
        if rtn_code == RTN_VER_ERROR:
            raise RTNVerError()
        elif rtn_code == RTN_CHKSUM_ERROR:
            raise RTNChksumError()
        elif rtn_code == RTN_LCHKSUM_ERROR:
            raise RTNLchksumError()
        elif rtn_code == RTN_CID2_INVALID:
            raise RTNCidError()
        elif rtn_code == RTN_COMMAND_FORMAT_ERROR:
            raise RTNFormatError()
        elif rtn_code == RTN_INVALID_DATA:
            raise RTNDataError()
        elif RTN_USER_DEFINED_ERROR_START <= rtn_code <= RTN_USER_DEFINED_ERROR_END:
            raise RTNError(rtn_code, f"User-defined error: {rtn_code}")
        else:
            raise RTNError(rtn_code, f"Unknown error: {rtn_code}")

    def _is_unidirectional_command(self, command):
        return command.response_type is None