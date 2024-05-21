import serial
import struct
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class MU4801Simulator:
    def __init__(self):
        self.FRAME_HEADER = b'~'
        self.FRAME_FOOTER = b'\r'

        # MU4801模拟器参数
        self.device_addr = 0x01
        self.protocol_version = 0x21
        self.device_name = 'MU4801    '
        self.software_version = '10'
        self.manufacturer = '哈尔滨森谷电气技术有限公司  '

        self.current_time = self.str2bcd('2023-05-24 14:25:00')

    def str2bcd(self, time_str):
        """字符串转BCD码"""
        bcd_data = b''
        for char in time_str:
            if char.isdigit():
                bcd_data += struct.pack('B', int(char))
        return bcd_data

    def bcd2str(self, bcd_data):
        """BCD码转字符串"""
        year = str((bcd_data[0] >> 4) * 10 + (bcd_data[0] & 0x0F))
        month = str((bcd_data[1] >> 4) * 10 + (bcd_data[1] & 0x0F))
        day = str((bcd_data[2] >> 4) * 10 + (bcd_data[2] & 0x0F))
        hour = str((bcd_data[3] >> 4) * 10 + (bcd_data[3] & 0x0F))
        minute = str((bcd_data[4] >> 4) * 10 + (bcd_data[4] & 0x0F))
        second = str((bcd_data[5] >> 4) * 10 + (bcd_data[5] & 0x0F))
        return f"20{year}-{month}-{day} {hour}:{minute}:{second}"

    def ascii_to_bytes(self, ascii_str):
        """ASCII码字符串转字节数组"""
        return bytes.fromhex(ascii_str)

    def bytes_to_ascii(self, byte_data):
        """字节数组转ASCII码字符串"""
        return byte_data.hex().upper()

    def get_length(self, data):
        """计算LENGTH字段的值"""
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

    def calc_chksum(self, frame):
        """计算校验和"""
        data = frame[1:-4]  # 提取需要计算校验和的字段,排除SOI、EOI和CHKSUM
        logging.debug(f"Data for checksum calculation: {data.hex()}")

        ascii_str = ''.join(f'{byte:02X}' for byte in data)  # 将字节数组转换为ASCII码字符串
        logging.debug(f"ASCII string: {ascii_str}")

        ascii_sum = sum(ord(c) for c in ascii_str)  # 求ASCII码之和
        logging.debug(f"ASCII sum: {ascii_sum}")

        chksum = ascii_sum % 65536  # 求和结果模65536
        logging.debug(f"Checksum modulo 65536: {chksum:04X}")

        chksum = (~chksum + 1) & 0xFFFF  # 取反加1,确保结果为16位无符号整数
        logging.debug(f"Checksum after inversion and increment: {chksum:04X}")

        chksum_bytes = struct.pack('>H', chksum)  # 打包为两个字节,大端序
        logging.debug(f"Checksum bytes: {chksum_bytes.hex()}")

        return chksum_bytes

    def send_response(self, ser, data):
        frame_data = struct.pack('>BBB', self.protocol_version, self.device_addr, 0x00) + data
        length = self.get_length(frame_data)
        chksum = self.calc_chksum(length + frame_data)      
        frame = self.FRAME_HEADER + length + frame_data + chksum + self.FRAME_FOOTER
        ser.write(frame)

    def handle_command(self, addr, cid1, cid2, data):
        """处理监控单元发送的命令"""
        logging.debug(f"Received command: addr={addr:02X}, cid1={cid1:02X}, cid2={cid2:02X}, data={data.hex()}")
        
        if cid1 == 0x40:
            if cid2 == 0x4D:  # 获取当前时间
                return self.current_time
            
            elif cid2 == 0x4E:  # 设置当前时间
                try:
                    self.current_time = data[:6]
                    return b''
                except Exception as e:
                    logging.error(f"Error in setting time: {e}")
                    return None

            elif cid2 == 0x4F:  # 获取通信协议版本号
                return struct.pack('B', self.protocol_version)

            elif cid2 == 0x50:  # 获取本机地址  
                return struct.pack('B', self.device_addr)

            elif cid2 == 0x51:  # 获取厂家信息
                response = self.device_name.encode() + self.software_version.encode() + self.manufacturer.encode()  
                return response

        logging.warning(f"Unsupported command: CID2={cid2:02X}")
        return None

    def check_frame(self, frame):
        """校验帧数据的合法性"""
        logging.debug(f"Checking frame: {frame.hex()}")

        # 验证帧同步字符
        if frame[0] != ord(self.FRAME_HEADER) or frame[-1] != ord(self.FRAME_FOOTER):
            logging.error(f"Invalid frame synchronization characters: SOI={frame[0]:02X}, EOI={frame[-1]:02X}")
            return False
        logging.debug(f"Frame synchronization characters check passed: SOI={frame[0]:02X}, EOI={frame[-1]:02X}")

        # 验证校验和
        received_chksum = frame[-3:-1]
        #received_chksum = frame[-4:-2]
        calculated_chksum = self.calc_chksum(frame)
        if calculated_chksum != received_chksum:
            logging.error(f"Checksum verification failed: received={received_chksum.hex()}, calculated={calculated_chksum.hex()}")
            return False
        logging.debug(f"Checksum verification passed: {received_chksum.hex()}")
        
        # 验证数据长度
        lenid_low = frame[6]
        lenid_high = frame[5] & 0x0F
        frame_length = (lenid_high << 8) | lenid_low
        if frame_length + 2 != len(frame) - 9:
            logging.error(f"Data length verification failed: LENID={frame_length}, actual={len(frame)-11}")
            return False
        logging.debug(f"Data length verification passed: LENID={frame_length}, actual={len(frame)-11}")

        logging.debug("Frame check passed")
        return True

    def handle_frame(self, frame, ser):
        """处理合法的帧数据"""
        logging.debug(f"Handling frame: {frame.hex()}")
        
        # 解析帧字段
        frame_ver = frame[1]
        frame_adr = frame[2]
        frame_cid1 = frame[3]
        frame_cid2 = frame[4]
        frame_info = frame[9:-3]

        # 根据CID1和CID2进行命令处理
        response = self.handle_command(frame_adr, frame_cid1, frame_cid2, frame_info)
        
        if response is not None:
            # 构造响应帧
            response_frame = struct.pack('>BBB', frame_ver, frame_adr, 0x00) + response
            response_length = self.get_length(response_frame)
            response_chksum = self.calc_chksum(response_length + response_frame)
            response_full = self.FRAME_HEADER + response_length + response_frame + response_chksum + self.FRAME_FOOTER
            
            # 发送响应帧
            ser.write(response_full)
            logging.debug(f"Sent response: {response_full.hex()}")
        else:
            # 构造错误响应帧
            err_response_frame = struct.pack('>BBB', frame_ver, frame_adr, 0x04)
            err_response_length = self.get_length(err_response_frame)
            err_response_chksum = self.calc_chksum(err_response_length + err_response_frame) 
            err_response_full = self.FRAME_HEADER + err_response_length + err_response_frame + err_response_chksum + self.FRAME_FOOTER
            
            # 发送错误响应帧
            ser.write(err_response_full)
            logging.warning(f"Sent error response: {err_response_full.hex()}")

    def main(self):
        default_port = '/dev/ttyS3'
        port = input(f'请输入串口号(默认为{default_port}): ')
        if not port:
            port = default_port
        baudrate = 9600
        bytesize = serial.EIGHTBITS
        parity = serial.PARITY_NONE
        stopbits = serial.STOPBITS_ONE
        
        try:
            ser = serial.Serial(port, baudrate, bytesize=bytesize, parity=parity, stopbits=stopbits, timeout=1)
            logging.info(f"MU4801 simulator started, using port {port}, baudrate {baudrate}, bytesize {bytesize}, parity {parity}, stopbits {stopbits}")

            while True:
                try:
                    # 读取并验证SOI
                    soi = ser.read(1)
                    if len(soi) == 0:
                        logging.debug("No data received, waiting...")
                        continue
                    if soi[0] != ord(self.FRAME_HEADER):
                        logging.warning(f"Invalid SOI: {soi.hex()}, discarding data...")
                        continue
                    logging.debug(f"Received SOI: {soi.hex()}")

                    # 读取固定长度字段(6字节)
                    fixed_fields = ser.read(6)
                    if len(fixed_fields) < 6:
                        logging.warning(f"Incomplete fixed fields: {fixed_fields.hex()}, discarding data...")
                        continue
                    logging.debug(f"Received fixed fields: {fixed_fields.hex()}")

                    # 解析固定字段
                    frame_ver = fixed_fields[0]
                    frame_adr = fixed_fields[1]
                    frame_cid1 = fixed_fields[2]
                    frame_cid2 = fixed_fields[3]
                    frame_length = fixed_fields[4:6]

                    logging.debug(f"Parsed fixed fields: VER={frame_ver:02X}, ADR={frame_adr:02X}, CID1={frame_cid1:02X}, CID2={frame_cid2:02X}, LENGTH={frame_length.hex()}")


                    # 解析LENGTH字段
                    lenid_low = fixed_fields[5]  
                    lenid_high = fixed_fields[4] & 0x0F
                    lenid = (lenid_high << 8) | lenid_low

                    lchksum = (fixed_fields[4] >> 4) & 0x0F
                    calc_lchksum = (lenid_low + lenid_high + lenid) % 16  
                    calc_lchksum = (~calc_lchksum + 1) & 0x0F

                    if lchksum != calc_lchksum:
                        logging.warning(f"LCHKSUM check failed, received: {lchksum:X}, calculated: {calc_lchksum:X}")
                        continue
                    logging.debug(f"LENGTH field parsed, LENID={lenid}, LCHKSUM={lchksum}")
                    
                    if lenid > 0:
                        # 读取INFO字段
                        info_fields = ser.read(lenid)
                        if len(info_fields) < lenid:
                            logging.warning(f"Incomplete INFO fields: {info_fields.hex()}, discarding data...")
                            continue
                        logging.debug(f"Received INFO fields: {info_fields.hex()}")
                    else:
                        info_fields = b''
                        logging.debug("No INFO fields, LENID is 0") 

                    # 读取CHKSUM字段
                    chksum = ser.read(2) 
                    if len(chksum) < 2:
                        logging.warning(f"Incomplete CHKSUM: {chksum.hex()}, discarding data...")
                        continue 
                    logging.debug(f"Received CHKSUM: {chksum.hex()}")

                    # 读取EOI
                    eoi = ser.read(1)
                    if len(eoi) == 0 or eoi[0] != ord(self.FRAME_FOOTER):
                        logging.warning(f"Invalid EOI: {eoi.hex()}, discarding data...")  
                        continue
                    logging.debug(f"Received EOI: {eoi.hex()}")

                    # 拼接完整帧
                    frame = soi + fixed_fields + info_fields + chksum + eoi
                    logging.debug(f"Received complete frame: {frame.hex()}")

                    # 进行校验和处理
                    if self.check_frame(frame):
                        logging.debug("Frame check passed, handling frame...")
                        self.handle_frame(frame, ser)
                    else:
                        logging.warning(f"Frame check failed, discarding frame: {frame.hex()}")

                except Exception as e:
                    logging.exception(f"Unexpected error: {e}")

        except serial.SerialException:
            logging.error(f"Failed to open serial port {port}. Please check the port name and permissions.")
            sys.exit(1)

if __name__ == '__main__':
    simulator = MU4801Simulator()
    simulator.main()