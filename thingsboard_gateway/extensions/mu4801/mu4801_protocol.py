import struct
import serial
from serial.serialutil import SerialException
from collections import namedtuple
import datetime

class FrameEncoder:
    SOI = b'~'  # 起始位标志
    EOI = b'\r'  # 结束码

    @staticmethod
    def encode_frame(ver, adr, cid1, cid2, info):
        frame_bytes = bytearray()
        frame_bytes.extend(FrameEncoder.SOI)
        frame_bytes.extend(struct.pack('>BBB', ver, adr, cid1))
        frame_bytes.extend(struct.pack('>B', cid2))
        length_bytes = FrameEncoder.encode_length(info)
        frame_bytes.extend(length_bytes)
        frame_bytes.extend(info)

        data_for_checksum = struct.pack('>BBB', ver, adr, cid1) + struct.pack('>B', cid2) + length_bytes + info
        chksum = FrameEncoder.calc_checksum(data_for_checksum)
        frame_bytes.extend(chksum)

        frame_bytes.extend(FrameEncoder.EOI)

        return bytes(frame_bytes)

    @staticmethod
    def encode_length(data):
        data_len = len(data)
        lenid = data_len // 2
        
        lenid_low = lenid & 0xFF
        lenid_high = (lenid >> 8) & 0x0F
        
        lchksum = (lenid_low + lenid_high + lenid) % 16
        lchksum = (~lchksum + 1) & 0x0F
        
        length = struct.pack('>BB', (lchksum << 4) | lenid_high, lenid_low)
        
        if data_len == 0:
            length = b'\x00\x00'  # 当data为空时,LENGTH字段填充0000
            
        return length

    @staticmethod
    def calc_checksum(data_for_checksum):
        ascii_str = ''.join(f'{byte:02X}' for byte in data_for_checksum)
        ascii_sum = sum(ord(c) for c in ascii_str)
        chksum = ascii_sum % 65536
        chksum = (~chksum + 1) & 0xFFFF
        chksum_bytes = struct.pack('>H', chksum)
        return chksum_bytes

class InfoEncoder:
    @staticmethod
    def encode_info(info_data):
        info_bytes = InfoEncoder.encode_data(info_data)
        return info_bytes

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
        elif isinstance(data, bytes):
            return data
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

class MU4801Protocol:
    def __init__(self, device_addr, port=None, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=0.5):
        self.device_addr = device_addr
        self.serial = None
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.protocol_version = 0x21

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
            info = InfoEncoder.encode_info(info_data)
            frame = FrameEncoder.encode_frame(self.protocol_version, self.device_addr, cid1, cid2, info)
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
            soi = self.read_bytes(1)
            if soi != FrameEncoder.SOI:
                print("Invalid response: SOI not found")
                return None

            ver = self.read_byte()
            adr = self.read_byte()
            cid1 = self.read_byte()
            cid2 = self.read_byte()
            length_bytes = self.read_bytes(2)
            
            length = self.decode_length(length_bytes)
            info = self.read_bytes(length)

            chksum_bytes = self.read_bytes(2)
            eoi = self.read_bytes(1)
            if eoi != FrameEncoder.EOI:
                print("Invalid response: EOI not found")
                return None

            return FrameStruct(
                soi=soi,
                ver=ver,
                adr=adr,
                cid1=cid1,
                cid2=cid2,
                length=length,
                info=info,
                chksum=chksum_bytes,
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

    def decode_length(self, length_bytes):
        lenid_low = length_bytes[1]
        lenid_high = length_bytes[0] & 0x0F
        frame_length = (lenid_high << 8) | lenid_low
        return frame_length

    def validate_response(self, response_frame):
        data_for_checksum = struct.pack('>BBB', response_frame.ver, response_frame.adr, response_frame.cid1) + struct.pack('>B', response_frame.cid2) + response_frame.length.to_bytes(2, 'big') + response_frame.info
        expected_checksum = FrameEncoder.calc_checksum(data_for_checksum)
        return expected_checksum == response_frame.chksum

FrameStruct = namedtuple('FrameStruct', [
    'soi', 'ver', 'adr', 'cid1', 'cid2', 'length', 'info', 'chksum', 'eoi'
])