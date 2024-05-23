import struct
import logging
import serial
from serial.serialutil import SerialException
from collections import namedtuple
import datetime

# 常量定义
PROTOCOL_VERSION = 0x21
SOI = 0x7E  # 起始位标志
EOI = 0x0D  # 结束码

# 帧结构常量
SOI_INDEX = 0
VER_INDEX = 1
ADR_INDEX = 2
CID1_INDEX = 3
CID2_INDEX = 4
LENGTH_INDEX = 5
INFO_INDEX = 7
CHKSUM_INDEX = -3
EOI_INDEX = -1

# 帧长度编码常量
LENID_ZERO = 0
LENID_LOW_MASK = 0xFF
LENID_HIGH_MASK = 0x0F
LCHKSUM_MASK = 0xF0
LCHKSUM_SHIFT = 4

FrameStruct = namedtuple('FrameStruct', [
    'soi', 'ver', 'adr', 'cid1', 'cid2', 'length', 'info', 'chksum', 'eoi'
])

class FrameUtils:
    
    @staticmethod
    def calc_checksum(data_for_checksum):
        logging.debug(f"Calculating checksum: data={data_for_checksum.hex()}")
        ascii_str = ''.join(f'{byte:02X}' for byte in data_for_checksum)
        logging.debug(f"ASCII string for checksum: {ascii_str}")
        ascii_sum = sum(ord(c) for c in ascii_str)
        logging.debug(f"ASCII sum: {ascii_sum}")
        chksum = ascii_sum % 65536
        logging.debug(f"Checksum (modulo 65536): {chksum}")
        chksum = (~chksum + 1) & 0xFFFF
        logging.debug(f"Checksum (inverted): {chksum}")
        chksum_bytes = struct.pack('>H', chksum)
        logging.debug(f"Checksum bytes: {chksum_bytes.hex()}")
        return chksum_bytes

    @staticmethod
    def extract_data_for_checksum(frame: FrameStruct) -> bytes:
        return struct.pack('>BBB', frame.ver, frame.adr, frame.cid1) + struct.pack('>B', frame.cid2) + frame.length.to_bytes(2, 'big') + frame.info

class FrameEncoder:
    @staticmethod
    def encode_frame(ver, adr, cid1, cid2, info):
        logging.debug(f"Encoding frame: ver={ver:02X}, adr={adr:02X}, cid1={cid1:02X}, cid2={cid2:02X}, info={info.hex()}")
        frame_bytes = bytearray()
        logging.debug(f"Adding SOI to frame: {SOI:02X}")
        frame_bytes.extend(struct.pack('>B', SOI))
        logging.debug(f"Adding ver, adr, cid1 to frame: {struct.pack('>BBB', ver, adr, cid1).hex()}")
        frame_bytes.extend(struct.pack('>BBB', ver, adr, cid1))
        logging.debug(f"Adding cid2 to frame: {struct.pack('>B', cid2).hex()}")
        frame_bytes.extend(struct.pack('>B', cid2))
        length_bytes = FrameEncoder.encode_length(info)
        logging.debug(f"Adding length to frame: {length_bytes.hex()}")
        frame_bytes.extend(length_bytes)
        logging.debug(f"Adding info to frame: {info.hex()}")
        frame_bytes.extend(info)

        data_for_checksum = FrameUtils.extract_data_for_checksum(FrameStruct(
            soi=SOI,
            ver=ver,
            adr=adr,
            cid1=cid1,
            cid2=cid2,
            length=len(info),
            info=info,
            chksum=b'',
            eoi=EOI
        ))
        chksum = FrameUtils.calc_checksum(data_for_checksum)
        logging.debug(f"Adding checksum to frame: {chksum.hex()}")
        frame_bytes.extend(chksum)

        logging.debug(f"Adding EOI to frame: {EOI:02X}")
        frame_bytes.extend(struct.pack('>B', EOI))

        logging.debug(f"Encoded frame: {bytes(frame_bytes).hex()}")
        return bytes(frame_bytes)

    @staticmethod
    def encode_length(data):
        logging.debug(f"Encoding length: data_len={len(data)}")
        data_len = len(data)
        
        if data_len == LENID_ZERO:
            lenid = LENID_ZERO
        else:
            lenid = data_len
        
        lenid_low = lenid & LENID_LOW_MASK
        lenid_high = (lenid >> 8) & LENID_HIGH_MASK
        
        lchksum = (lenid_low + lenid_high + lenid) % 16
        lchksum = (~lchksum + 1) & 0x0F
        
        length = struct.pack('>BB', (lchksum << LCHKSUM_SHIFT) | lenid_high, lenid_low)
        
        logging.debug(f"Encoded length: {length.hex()}")
        return length

class FrameDecoder:
    @staticmethod
    def decode_length(length_bytes):
        lenid_low = length_bytes[1]
        lenid_high = length_bytes[0] & LENID_HIGH_MASK
        lchksum = (length_bytes[0] >> LCHKSUM_SHIFT) & 0x0F

        lenid = (lenid_high << 8) | lenid_low

        if lenid == LENID_ZERO:
            info_length = LENID_ZERO
        else:
            calculated_lchksum = (lenid_low + lenid_high + lenid) % 16
            calculated_lchksum = (~calculated_lchksum + 1) & 0x0F
            if lchksum != calculated_lchksum:
                raise ValueError(f"Invalid LCHKSUM: received={lchksum:X}, calculated={calculated_lchksum:X}")
            info_length = lenid
        return info_length

    @staticmethod
    def validate_frame(frame):
        logging.debug(f"Validating frame: {frame}")
        
        # 检查帧的实际长度是否与长度字段匹配
        if frame.length != len(frame.info):
            logging.warning(f"Invalid frame: length mismatch (expected: {frame.length}, received: {len(frame.info)})")
            return False
        
        data_for_checksum = FrameUtils.extract_data_for_checksum(frame)
        logging.debug(f"Data for checksum calculation: {data_for_checksum.hex()}")
        expected_checksum = FrameUtils.calc_checksum(data_for_checksum)
        logging.debug(f"Expected checksum: {expected_checksum.hex()}, received checksum: {frame.chksum.hex()}")
        
        if expected_checksum != frame.chksum:
            logging.warning("Invalid frame: checksum mismatch")
            return False
    
        return True

    @staticmethod
    def recv_frame(serial, timeout=None):
        logging.debug(f"Receiving frame with timeout={timeout}")

        if timeout is not None:
            serial.timeout = timeout

        try:
            # 等待数据可读
            while True:
                if serial.in_waiting > 0:
                    logging.debug(f"Data available, bytes in buffer: {serial.in_waiting}")
                    break
                #logging.debug("No data available, waiting...")

            soi = serial.read(1)
            logging.debug(f"Received SOI: {soi.hex()}")
            if len(soi) == 0:
                logging.warning("No data received, timeout occurred")
                return None

            if soi[0] != SOI:
                logging.warning(f"Invalid frame: SOI not found (received: {soi[0]:02X})")
                return None

            ver = serial.read(1)[0]
            logging.debug(f"Received VER: {ver:02X}")
            adr = serial.read(1)[0]
            logging.debug(f"Received ADR: {adr:02X}")
            cid1 = serial.read(1)[0]
            logging.debug(f"Received CID1: {cid1:02X}")
            cid2 = serial.read(1)[0]
            logging.debug(f"Received CID2: {cid2:02X}")
            length_bytes = serial.read(2)
            logging.debug(f"Received LENGTH bytes: {length_bytes.hex()}")

            length = FrameDecoder.decode_length(length_bytes)
            logging.debug(f"Decoded LENGTH: {length}")
            info = serial.read(length)
            logging.debug(f"Received INFO: {info.hex()}")

            chksum_bytes = serial.read(2)
            logging.debug(f"Received CHKSUM bytes: {chksum_bytes.hex()}")
            eoi = serial.read(1)
            logging.debug(f"Received EOI: {eoi.hex()}")
            if len(eoi) == 0:
                logging.warning("Incomplete frame received, EOI not found")
                return None

            if eoi[0] != EOI:
                logging.warning(f"Invalid frame: EOI not found (received: {eoi[0]:02X})")
                return None

            frame = FrameStruct(
                soi=soi[0],
                ver=ver,
                adr=adr,
                cid1=cid1,
                cid2=cid2,
                length=length,
                info=info,
                chksum=chksum_bytes,
                eoi=eoi[0]
            )
            logging.debug(f"Received frame: {frame}")

            if not FrameDecoder.validate_frame(frame):
                logging.warning("Invalid frame: checksum mismatch")
                return None

            return frame
        except Exception as e:
            logging.exception(f"Error receiving frame: {e}")
            return None

class InfoEncoder:
    # 定义编码函数字典
    ENCODE_FUNCS = {
        float: lambda x: struct.pack('>f', x),
        int: lambda x: struct.pack('>h', x),
        datetime.datetime: lambda x: InfoEncoder.encode_datetime(x),
        bytes: lambda x: x,
        type(None): lambda x: b'',  # 添加None类型的处理
    }

    @staticmethod
    def encode_info(info_data):
        info_bytes = InfoEncoder.encode_data(info_data)
        return info_bytes

    @staticmethod
    def encode_data(data):
        # 检查data是否为整数且在0到255之间
        if isinstance(data, int) and 0 <= data <= 255:
            return struct.pack('>B', data)
        
        # 使用字典映射数据类型到编码函数
        encode_func = InfoEncoder.ENCODE_FUNCS.get(type(data))
        if encode_func:
            return encode_func(data)
        else:
            raise ValueError(f"Invalid data type: {type(data)}")

    @staticmethod
    def encode_datetime(dt):
        # datetime编码逻辑保持不变
        year = struct.pack('>H', dt.year)
        month = struct.pack('>B', dt.month)
        day = struct.pack('>B', dt.day)
        hour = struct.pack('>B', dt.hour)
        minute = struct.pack('>B', dt.minute)
        second = struct.pack('>B', dt.second)
        return year + month + day + hour + minute + second

class InfoDecoder:
    @staticmethod
    def decode_info(info_bytes):
        info_type = None
        info_value = None
        if len(info_bytes) == 4:
            info_type = float
            info_value = struct.unpack('>f', info_bytes)[0]
        elif len(info_bytes) == 2:
            info_type = int
            info_value = struct.unpack('>h', info_bytes)[0]
        elif len(info_bytes) == 7:
            info_type = datetime.datetime
            info_value = InfoDecoder.decode_datetime(info_bytes)
        elif len(info_bytes) == 1:
            info_type = int
            info_value = struct.unpack('>B', info_bytes)[0]
        elif len(info_bytes) > 0:
            info_type = bytes
            info_value = info_bytes
        return info_type, info_value

    @staticmethod
    def decode_datetime(bytes_data):
        year = struct.unpack('>H', bytes_data[:2])[0]
        month = struct.unpack('>B', bytes_data[2:3])[0]
        day = struct.unpack('>B', bytes_data[3:4])[0]
        hour = struct.unpack('>B', bytes_data[4:5])[0]
        minute = struct.unpack('>B', bytes_data[5:6])[0]
        second = struct.unpack('>B', bytes_data[6:7])[0]
        return datetime.datetime(year, month, day, hour, minute, second)

class Protocol:
    def __init__(self, device_addr, port=None, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=0.5):
        self.device_addr = device_addr
        self.serial = None
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.protocol_version = PROTOCOL_VERSION

    def open(self):
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout
            )
            return True
        except SerialException as e:
            print(f"Error opening serial port: {e}")
            return False

    def close(self):
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
            except SerialException as e:
                print(f"Error closing serial port: {e}")

    def is_connected(self):
        return self.serial and self.serial.is_open

    def send_command(self, cid1, cid2, info_data, response_timeout=0.5):
        if not self.is_connected():
            logging.warning("Serial port is not connected")
            return None

        try:
            info = InfoEncoder.encode_info(info_data)
            logging.debug(f"Encoded info: {info.hex()}")
            frame = FrameEncoder.encode_frame(self.protocol_version, self.device_addr, cid1, cid2, info)
            logging.debug(f"Encoded frame: {frame.hex()}")
            if frame is not None:
                logging.debug(f"Sending command: cid1={cid1:02X}, cid2={cid2:02X}, info={info.hex()}")
                self.serial.write(frame)
                response_frame = self.recv_response(response_timeout)
                if response_frame is not None:
                    logging.debug(f"Received response frame: {response_frame}")
                    return InfoDecoder.decode_info(response_frame.info)
        except Exception as e:
            logging.exception(f"Error sending command or receiving response: {e}")
            return None
    
    def send_response(self, cid1, cid2, info):
        if not self.is_connected():
            logging.warning("Serial port is not connected")
            return False

        try:
            response_frame = FrameEncoder.encode_frame(self.protocol_version, self.device_addr, cid1, cid2, info)
            logging.debug(f"Sending response frame: {response_frame.hex()}")
            self.serial.write(response_frame)
            return True
        except Exception as e:
            logging.exception(f"Error sending response frame: {e}")
            return False

    def recv_command(self, timeout=0.5):
        if not self.is_connected():
            logging.warning("Serial port is not connected")
            return None

        command_frame = FrameDecoder.recv_frame(self.serial, timeout)
        if command_frame is None:
            logging.warning("Received invalid command frame")
            return None

        logging.debug(f"Received command frame: {command_frame}")
        return command_frame

    def recv_response(self, response_timeout=0.5):
        if not self.is_connected():
            logging.warning("Serial port is not connected")
            return None

        response_frame = FrameDecoder.recv_frame(self.serial, response_timeout)
        if response_frame is None:
            logging.warning("Received invalid response frame")
            return None

        logging.debug(f"Received response frame: {response_frame}")
        return response_frame
