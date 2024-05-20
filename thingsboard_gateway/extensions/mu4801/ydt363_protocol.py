import struct
import serial
from serial.serialutil import SerialException

class FrameEncoder:
    SOI = 0x7E  # 起始位标志
    VER = 0x21  # 协议版本号
    EOI = 0x0D  # 结束码

    @staticmethod
    def encode_frame(device_addr, cid1, cid2, length, info):
        frame_bytes = bytearray()
        frame_bytes.append(FrameEncoder.SOI)
        frame_bytes.append(FrameEncoder.VER)
        frame_bytes.append(device_addr)
        frame_bytes.append(cid1)
        frame_bytes.append(cid2)
        frame_bytes.extend(length)
        frame_bytes.extend(info)

        chksum = FrameEncoder.calc_checksum(frame_bytes)
        chksum_bytes = struct.pack('>H', chksum)
        frame_bytes.extend(chksum_bytes)

        frame_bytes.append(FrameEncoder.EOI)

        return bytes(frame_bytes)

    @staticmethod
    def calc_checksum(frame_bytes):
        checksum = sum(frame_bytes[1:-3]) % 65536  # 不包括SOI、EOI和CHKSUM
        checksum = (~checksum + 1) & 0xFFFF
        return checksum

class InfoEncoder:
    @staticmethod
    def encode_info(cid1, cid2, info_data):
        info_bytes = InfoEncoder.encode_data(info_data)

        length = len(info_bytes)
        length_bytes = struct.pack('>H', length)

        length_checksum = InfoEncoder.calc_length_checksum(length_bytes, info_bytes)
        length_bytes = bytes([length_checksum]) + length_bytes

        return cid1, cid2, length_bytes, info_bytes

    @staticmethod
    def encode_data(data):
        if isinstance(data, float):
            return struct.pack('>f', data)
        elif isinstance(data, int):
            return struct.pack('>h', data)
        else:
            raise ValueError("Invalid data type")

    @staticmethod
    def calc_length_checksum(length_bytes, info_bytes):
        checksum_bytes = bytearray(length_bytes)
        checksum_bytes.extend(info_bytes)
        checksum = sum(checksum_bytes) % 16
        checksum = (~checksum + 1) & 0xFF
        return checksum

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
        return info_type, info_value

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
            cid1, cid2, length, info = InfoEncoder.encode_info(cid1, cid2, info_data)
            frame = FrameEncoder.encode_frame(self.device_addr, cid1, cid2, length, info)
            if frame is not None:
                self.serial.write(frame)
                response_struct = self.recv_response(response_timeout)
                if response_struct is not None:
                    if self.validate_response(response_struct):
                        return InfoDecoder.decode_info(response_struct.info)
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
            if soi != bytes([FrameEncoder.SOI]):
                print("Invalid response: SOI not found")
                return None

            ver = self.read_bytes(1)
            adr = self.read_bytes(1)
            cid1 = self.read_bytes(1)
            cid2 = self.read_bytes(1)
            length_bytes = self.read_bytes(3)
            length_checksum = length_bytes[0]
            length = struct.unpack('>H', length_bytes[1:])[0]
            info = self.read_bytes(length)

            chksum_bytes = self.read_bytes(2)
            eoi = self.read_bytes(1)
            if eoi != bytes([FrameEncoder.EOI]):
                print("Invalid response: EOI not found")
                return None

            # 校验LENGTH字段校验和
            expected_length_checksum = InfoEncoder.calc_length_checksum(length_bytes[1:], info)
            if length_checksum != expected_length_checksum:
                print("Invalid response: length checksum mismatch")
                return None

            # 校验和比对
            expected_checksum = FrameEncoder.calc_checksum(
                ver +
                adr +
                cid1 +
                cid2 +
                length_bytes[1:] +
                info
            )
            received_checksum = struct.unpack('>H', chksum_bytes)[0]
            if expected_checksum != received_checksum:
                print("Invalid response: checksum mismatch")
                return None

            return InfoStruct(
                soi=soi[0],
                ver=ver[0],
                adr=adr[0],
                cid1=cid1[0],
                cid2=cid2[0],
                length=length_bytes[1:],
                info=info,
                chksum=chksum_bytes,
                eoi=eoi[0]
            )
        except Exception as e:
            print(f"Error receiving response: {e}")
            return None

    def read_bytes(self, num_bytes=1):
        bytes_data = self.serial.read(num_bytes)
        if len(bytes_data) != num_bytes:
            raise Exception("Read timeout")
        return bytes_data

    def validate_response(self, response_struct):
        frame_bytes = bytearray()
        frame_bytes.extend(bytes([response_struct.ver]))
        frame_bytes.extend(bytes([response_struct.adr]))
        frame_bytes.extend(bytes([response_struct.cid1]))
        frame_bytes.extend(bytes([response_struct.cid2]))
        frame_bytes.extend(response_struct.length)
        frame_bytes.extend(response_struct.info)

        expected_checksum = FrameEncoder.calc_checksum(frame_bytes)
        received_checksum = struct.unpack('>H', response_struct.chksum)[0]
        return expected_checksum == received_checksum

InfoStruct = namedtuple('InfoStruct', [
    'soi', 'ver', 'adr', 'cid1', 'cid2', 'length', 'info', 'chksum', 'eoi'
])