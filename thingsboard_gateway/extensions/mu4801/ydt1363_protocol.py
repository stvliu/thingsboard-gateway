import struct
import serial
from serial.serialutil import SerialException
from collections import namedtuple
import datetime

class FrameEncoder:
    SOI = 0x7E  # 起始位标志
    VER = 0x21  # 协议版本号
    EOI = 0x0D  # 结束码

    @staticmethod
    def encode_frame(device_addr, cid1, cid2, info):
        frame_bytes = bytearray()
        frame_bytes.append(FrameEncoder.SOI)
        frame_bytes.extend(FrameEncoder.encode_byte(FrameEncoder.VER))
        frame_bytes.extend(FrameEncoder.encode_byte(device_addr))
        frame_bytes.extend(FrameEncoder.encode_byte(cid1))
        frame_bytes.extend(FrameEncoder.encode_byte(cid2))
        
        length_bytes = FrameEncoder.encode_word(len(info))
        length_checksum = FrameEncoder.calc_length_checksum(length_bytes)
        frame_bytes.extend(FrameEncoder.encode_byte(length_checksum))
        frame_bytes.extend(length_bytes)
        
        frame_bytes.extend(info)

        chksum = FrameEncoder.calc_checksum(frame_bytes[1:])
        frame_bytes.extend(FrameEncoder.encode_word(chksum))

        frame_bytes.append(FrameEncoder.EOI)

        return bytes(frame_bytes)

    @staticmethod
    def encode_byte(value):
        return [value // 16, value % 16]

    @staticmethod
    def encode_word(value):
        return [value // 256 // 16, value // 256 % 16, value % 256 // 16, value % 256 % 16]

    @staticmethod
    def calc_length_checksum(length_bytes):
        checksum = sum(length_bytes) % 16
        checksum = (~checksum + 1) & 0xF
        return checksum

    @staticmethod
    def calc_checksum(frame_bytes):
        checksum = sum(frame_bytes) % 65536
        checksum = (~checksum + 1) & 0xFFFF
        return checksum

class InfoEncoder:
    @staticmethod
    def encode_info(cid1, cid2, info_data):
        info_bytes = InfoEncoder.encode_data(info_data)
        return cid1, cid2, info_bytes

    @staticmethod
    def encode_data(data):
        if isinstance(data, float):
            return struct.pack('>f', data)
        elif isinstance(data, int):
            return struct.pack('>h', data)
        elif isinstance(data, datetime.datetime):
            return InfoEncoder.encode_datetime(data)
        elif isinstance(data, int) and 0 <= data <= 255:
            return struct.pack('>B', data)
        else:
            raise ValueError("Invalid data type")

    @staticmethod
    def encode_datetime(dt):
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

class YDT1363Protocol:
    def __init__(self, device_addr, port=None, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=0.5):
        self.device_addr = device_addr
        self.serial = None
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout

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
            print("Serial port is not connected")
            return None, None

        try:
            cid1, cid2, info = InfoEncoder.encode_info(cid1, cid2, info_data)
            frame = FrameEncoder.encode_frame(self.device_addr, cid1, cid2, info)
            if frame is not None:
                self.serial.write(frame)
                response_frame = self.recv_response(response_timeout)
                if response_frame is not None:
                    if self.validate_response(response_frame):
                        return InfoDecoder.decode_info(response_frame.info)
                    else:
                        print("Invalid response: checksum mismatch")
        except Exception as e:
            print(f"Error sending command or receiving response: {e}")
        return None, None

    def recv_response(self, response_timeout=0.5):
        if not self.is_connected():
            print("Serial port is not connected")
            return None

        try:
            self.serial.timeout = response_timeout
            soi = self.read_byte()
            if soi != FrameEncoder.SOI:
                print("Invalid response: SOI not found")
                return None

            ver = self.decode_byte(self.read_bytes(2))
            adr = self.decode_byte(self.read_bytes(2))
            cid1 = self.decode_byte(self.read_bytes(2))
            cid2 = self.decode_byte(self.read_bytes(2))
            length_checksum = self.decode_byte(self.read_bytes(2))
            length_bytes = self.read_bytes(4)
            length = self.decode_word(length_bytes)
            info = self.read_bytes(length * 2)

            chksum_bytes = self.read_bytes(4)
            eoi = self.read_byte()
            if eoi != FrameEncoder.EOI:
                print("Invalid response: EOI not found")
                return None

            # 校验LENGTH字段校验和
            expected_length_checksum = FrameEncoder.calc_length_checksum(length_bytes)
            if length_checksum != expected_length_checksum:
                print("Invalid response: length checksum mismatch")
                return None

            # 校验和比对
            expected_checksum = FrameEncoder.calc_checksum(
                FrameEncoder.encode_byte(ver) +
                FrameEncoder.encode_byte(adr) +
                FrameEncoder.encode_byte(cid1) +
                FrameEncoder.encode_byte(cid2) +
                FrameEncoder.encode_byte(length_checksum) +
                length_bytes +
                info
            )
            received_checksum = self.decode_word(chksum_bytes)
            if expected_checksum != received_checksum:
                print("Invalid response: checksum mismatch")
                return None

            return FrameStruct(
                soi=soi,
                ver=ver,
                adr=adr,
                cid1=cid1,
                cid2=cid2,
                length=length,
                info=info,
                chksum=received_checksum,
                eoi=eoi
            )
        except Exception as e:
            print(f"Error receiving response: {e}")
            return None

    def read_byte(self):
        byte_data = self.serial.read(1)
        if len(byte_data) != 1:
            raise Exception("Read timeout")
        return byte_data[0]

    def read_bytes(self, num_bytes):
        bytes_data = self.serial.read(num_bytes)
        if len(bytes_data) != num_bytes:
            raise Exception("Read timeout")
        return bytes_data

    def decode_byte(self, bytes_data):
        return bytes_data[0] * 16 + bytes_data[1]

    def decode_word(self, bytes_data):
        return (bytes_data[0] * 16 + bytes_data[1]) * 256 + (bytes_data[2] * 16 + bytes_data[3])

    def validate_response(self, response_frame):
        frame_bytes = bytearray()
        frame_bytes.extend(FrameEncoder.encode_byte(response_frame.ver))
        frame_bytes.extend(FrameEncoder.encode_byte(response_frame.adr))
        frame_bytes.extend(FrameEncoder.encode_byte(response_frame.cid1))
        frame_bytes.extend(FrameEncoder.encode_byte(response_frame.cid2))
        frame_bytes.extend(FrameEncoder.encode_byte(FrameEncoder.calc_length_checksum(FrameEncoder.encode_word(response_frame.length))))
        frame_bytes.extend(FrameEncoder.encode_word(response_frame.length))
        frame_bytes.extend(response_frame.info)

        expected_checksum = FrameEncoder.calc_checksum(frame_bytes)
        return expected_checksum == response_frame.chksum

FrameStruct = namedtuple('FrameStruct', [
    'soi', 'ver', 'adr', 'cid1', 'cid2', 'length', 'info', 'chksum', 'eoi'
])