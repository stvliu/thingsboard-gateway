import struct
import logging
import serial
from serial.serialutil import SerialException
from collections import namedtuple
import datetime
from typing import Union

from mu4801_constants import *
from mu4801_data_structs import *

# 定义帧结构
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
        logging.debug(f"Encoding frame: ver={ver:02X}, adr={adr:02X}, cid1={cid1:02X}, cid2={cid2:02X}, info={info}")
        frame_bytes = bytearray()
        logging.debug(f"Adding SOI to frame: {SOI:02X}")
        frame_bytes.extend(struct.pack('>B', SOI))
        logging.debug(f"Adding ver, adr, cid1 to frame: {struct.pack('>BBB', ver, adr, cid1).hex()}")
        frame_bytes.extend(struct.pack('>BBB', ver, adr, cid1))
        logging.debug(f"Adding cid2 to frame: {struct.pack('>B', cid2).hex()}")
        frame_bytes.extend(struct.pack('>B', cid2))

        logging.debug(f"Before encoding data: info={info}, type={type(info)}")
        info = DataEncoder.encode_data(info)
        logging.debug(f"After encoding data: info={info}, type={type(info)}")

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
        info_length = lenid

        calculated_lchksum = (lenid_low + lenid_high + lenid) % 16
        calculated_lchksum = (~calculated_lchksum + 1) & 0x0F
        if lchksum != calculated_lchksum:
            raise ValueError(f"Invalid LCHKSUM: received={lchksum:X}, calculated={calculated_lchksum:X}")

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

class DataEncoder:
    @staticmethod
    def encode_data(data):
        if data is None:
            return b''
        elif isinstance(data, bytes):
            return data
        elif isinstance(data, int):
            return struct.pack('<B', data)
        elif isinstance(data, float):
            return struct.pack('<f', data)
        elif isinstance(data, str):
            return data.encode('ascii')
        elif isinstance(data, (InfoStruct, AcAnalogStruct, AcAlarmStruct, AcConfigStruct,
                            RectAnalogStruct, RectStatusStruct, RectAlarmStruct,
                            DcAnalogStruct, DcAlarmStruct, DcConfigStruct, DateTimeStruct)):
            return data.to_bytes()
        elif isinstance(data, (list, tuple)):
            return b''.join(FrameEncoder.encode_length(item) for item in data)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

class DataDecoder:
    @staticmethod
    def decode_data(cid1, cid2, data):
        if cid1 == CID1_DC_POWER:
            if cid2 == CID2_GET_ANALOG_FLOAT:
                return AcAnalogStruct.from_bytes(data)
            elif cid2 == CID2_GET_ALARM:
                return AcAlarmStruct.from_bytes(data)
            elif cid2 == CID2_GET_CONFIG_FLOAT:
                return AcConfigStruct.from_bytes(data)
        elif cid1 == CID1_RECT:
            if cid2 == CID2_GET_ANALOG_FLOAT:
                return RectAnalogStruct.from_bytes(data)
            elif cid2 == CID2_GET_STATUS:
                return RectStatusStruct.from_bytes(data)
            elif cid2 == CID2_GET_ALARM:
                return RectAlarmStruct.from_bytes(data)
        elif cid1 == CID1_DC_DIST:
            if cid2 == CID2_GET_ANALOG_FLOAT:
                return DcAnalogStruct.from_bytes(data)
            elif cid2 == CID2_GET_ALARM:
                return DcAlarmStruct.from_bytes(data)
            elif cid2 == CID2_GET_CONFIG_FLOAT:
                return DcConfigStruct.from_bytes(data)
        elif cid1 == CID1_SYS_CONTROL:
            if cid2 == CID2_GET_TIME:
                return DateTimeStruct.from_bytes(data)
            elif cid2 == CID2_GET_VERSION:
                return data[0]  # 版本号是单字节整数
            elif cid2 == CID2_GET_ADDR:
                return data[0]  # 地址是单字节整数
            elif cid2 == CID2_GET_MFR_INFO:
                return InfoStruct.from_bytes(data)
            elif cid2 == CID2_GET_SYS_STATUS:
                return data[0]  # 系统状态是单字节整数
        return data  # 如果不能解码,就原样返回数据
    
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
            info = DataEncoder.encode_data(info_data)
            logging.debug(f"Encoded info: {info.hex()}")
            frame = FrameEncoder.encode_frame(self.protocol_version, self.device_addr, cid1, cid2, info)
            logging.debug(f"Encoded frame: {frame.hex()}")
            if frame is not None:
                logging.debug(f"Sending command: cid1={cid1:02X}, cid2={cid2:02X}, info={info.hex()}")
                self.serial.write(frame)
                response_frame = self.recv_response(response_timeout)
                if response_frame is not None:
                    logging.debug(f"Received response frame: {response_frame}")
                    return DataDecoder.decode_data(cid1, response_frame.cid2, response_frame.info)
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

class MU4801Protocol(Protocol):
    
    def handle_get_time(self):
        return DateTimeStruct.from_datetime(datetime.now())
        
    def handle_set_time(self, data):
        time_struct = DateTimeStruct.from_bytes(data)
        logging.info(f"Time set to: {time_struct}")
        # TODO: 实际设置时间的逻辑
        
    def handle_get_version(self):
        return self.protocol_version
        
    def handle_get_address(self):
        return self.device_addr
        
    def handle_get_info(self):
        return InfoStruct(
            device_name='MU4801',
            software_version='01', 
            manufacturer='ABC Technologies Ltd.'
        )
        
    def handle_get_ac_analog(self):
        # TODO: 实际获取交流模拟量的逻辑
        return AcAnalogStruct(
            voltage_ph_a=220.1,
            voltage_ph_b=220.5,
            voltage_ph_c=221.0, 
            ac_freq=50.0,
            ac_current=10.0
        )
        
    def handle_get_ac_alarm(self):
        # TODO: 实际获取交流告警状态的逻辑  
        return AcAlarmStruct(
            spd_alarm=0,
            over_voltage_ph_a=0,
            over_voltage_ph_b=0,
            over_voltage_ph_c=0,
            under_voltage_ph_a=0, 
            under_voltage_ph_b=0,
            under_voltage_ph_c=0 
        )
        
    def handle_get_ac_config(self):
        # TODO: 实际获取交流配置参数的逻辑
        return AcConfigStruct(
            ac_over_voltage=260.0, 
            ac_under_voltage=160.0
        )
        
    def handle_set_ac_config(self, config_data):
        config = AcConfigStruct.from_bytes(config_data)
        logging.info(f"AC config updated: over_volt={config.ac_over_voltage}, under_volt={config.ac_under_voltage}")
        # TODO: 实际设置交流配置参数的逻辑

    def handle_get_rect_analog(self, module_count):
        # TODO: 实际获取整流模块模拟量的逻辑
        return RectAnalogStruct(
            output_voltage=53.5,
            module_count=module_count,
            module_currents=[30.0, 29.5, 28.8][:module_count] 
        )
    
    def handle_get_rect_status(self, module_count):
        # TODO: 实际获取整流模块状态的逻辑
        return RectStatusStruct(
            module_count=module_count,
            status_list=[0x00, 0x01, 0x00][:module_count]
        )

    def handle_get_rect_alarm(self, module_count):
        # TODO: 实际获取整流模块告警状态的逻辑 
        return RectAlarmStruct(
            module_count=module_count,
            alarm_list=[0x00, 0x00, 0x01][:module_count] 
        )

    def handle_control_rect(self, module_id, control_type):
        logging.info(f"Rectifier module {module_id} control: {'enable' if control_type == 0x20 else 'disable'}")
        # TODO: 实际控制整流模块的逻辑

    def handle_set_rect_param(self, param_data):  
        # TODO: 实际设置整流模块参数的逻辑
        logging.info(f"Rectifier module parameter set: {param_data.hex()}")

    def handle_get_dc_analog(self):
        # TODO: 实际获取直流模拟量的逻辑
        return DcAnalogStruct(
            voltage=53.5,  
            total_current=88.2,
            battery_current=10.5, 
            load_branch_currents=[20.1, 22.3, 19.8, 21.5]  
        )

    def handle_get_dc_alarm(self):  
        # TODO: 实际获取直流告警状态的逻辑
        return DcAlarmStruct(
            over_voltage=0,  
            under_voltage=0,
            spd_alarm=0,
            fuse1_alarm=0,
            fuse2_alarm=0, 
            fuse3_alarm=0,
            fuse4_alarm=0
        )

    def handle_get_dc_config(self):
        # TODO: 实际获取直流配置参数的逻辑 
        return DcConfigStruct(
            voltage_upper_limit=57.6,  
            voltage_lower_limit=43.2,
            current_limit=100.0 
        )

    def handle_set_dc_config(self, config_data): 
        config = DcConfigStruct.from_bytes(config_data)
        logging.info(f"DC config updated: upper={config.voltage_upper_limit}, lower={config.voltage_lower_limit}")
        # TODO: 实际设置直流配置参数的逻辑

    def handle_control_system(self, control_type):
        # TODO: 实际系统控制命令的逻辑
        if control_type == 0xE1:  
            logging.info("System reset")
        elif control_type in [0xE5, 0xE6, 0xED, 0xEE]:
            load_id = (control_type - 0xE5) // 2 + 1 
            action = 'off' if control_type % 2 else 'on'
            logging.info(f"Load {load_id} turned {action}")
        else:
            logging.warning(f"Unsupported control type: {control_type:02X}")

    def handle_get_system_status(self):
        # TODO: 实际获取系统状态的逻辑
        return 0x00  # 占位,返回状态码

    def handle_set_system_status(self, control_value):
        logging.info(f"System status set to: {control_value}")
        # TODO: 实际设置系统状态的逻辑

    def handle_set_buzzer(self, enable):
        logging.info(f"Buzzer {'enabled' if enable else 'disabled'}") 
        # TODO: 实际设置蜂鸣器的逻辑

    def handle_get_power_saving_params(self):
        # TODO: 实际获取节能参数的逻辑
        return struct.pack('<BBBBB', 0x00, 1, 0x00, 30, 95, 75)

    def handle_set_power_saving_params(self, param_data):
        logging.info(f"Power saving parameters set: {param_data.hex()}")
        # TODO: 实际设置节能参数的逻辑

    def handle_command(self, cid1, cid2, data):
        logging.debug(f"Received command: cid1={cid1:02X}, cid2={cid2:02X}, data={data.hex()}")
        
        if cid1 == CID1_DC_POWER:
            if cid2 == CID2_GET_ANALOG_FLOAT:
                return self.handle_get_ac_analog()
            elif cid2 == CID2_GET_ALARM:
                return self.handle_get_ac_alarm()
            elif cid2 == CID2_GET_CONFIG_FLOAT:
                return self.handle_get_ac_config()
            elif cid2 == CID2_SET_CONFIG_FLOAT:
                return self.handle_set_ac_config(data)
        
        elif cid1 == CID1_RECT:
            if cid2 == CID2_GET_ANALOG_FLOAT:
                return self.handle_get_rect_analog(data[0])  # 第一个字节表示整流模块数量
            elif cid2 == CID2_GET_STATUS:
                return self.handle_get_rect_status(data[0]) 
            elif cid2 == CID2_GET_ALARM:
                return self.handle_get_rect_alarm(data[0])
            elif cid2 == CID2_CONTROL:  
                return self.handle_control_rect(data[0], data[1])  # 第一个字节表示模块ID,第二个字节表示控制类型
            elif cid2 == CID2_REMOTE_SET_FLOAT:
                return self.handle_set_rect_param(data)

        elif cid1 == CID1_DC_DIST:
            if cid2 == CID2_GET_ANALOG_FLOAT:
                return self.handle_get_dc_analog() 
            elif cid2 == CID2_GET_ALARM:
                return self.handle_get_dc_alarm()
            elif cid2 == CID2_GET_CONFIG_FLOAT:
                return self.handle_get_dc_config()
            elif cid2 == CID2_SET_CONFIG_FLOAT:
                return self.handle_set_dc_config(data)

        elif cid1 == CID1_SYS_CONTROL:
            if cid2 == CID2_CONTROL_SYSTEM:
                return self.handle_control_system(data[0])  # data[0]表示控制类型
            elif cid2 == CID2_GET_SYS_STATUS:
                return self.handle_get_system_status()
            elif cid2 == CID2_SET_SYS_STATUS:
                return self.handle_set_system_status(data[0])  # data[0]为控制值
            elif cid2 == CID2_BUZZER_CONTROL:
                return self.handle_set_buzzer(data[0]) 
            elif cid2 == CID2_GET_POWER_SAVING:
                return self.handle_get_power_saving_params()
            elif cid2 == CID2_SET_POWER_SAVING:
                return self.handle_set_power_saving_params(data)

        # 通用命令处理
        if cid2 == CID2_GET_TIME:
            return self.handle_get_time()
        elif cid2 == CID2_SET_TIME:
            return self.handle_set_time(data) 
        elif cid2 == CID2_GET_VERSION:
            return self.handle_get_version()
        elif cid2 == CID2_GET_ADDR:
            return self.handle_get_address()
        elif cid2 == CID2_GET_MFR_INFO:
            return self.handle_get_info()

        logging.warning(f"Unsupported command: CID2={cid2:02X}")
        return None