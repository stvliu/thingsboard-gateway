import serial
import struct
import time
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class MU4801Monitor:
    def __init__(self, device_addr=1):
        self.FRAME_HEADER = b'~'  # 帧起始标志为0x7E
        self.FRAME_FOOTER = b'\r'  # 帧结束标志为0x0D
        self.FRAME_VERSION = 0x21  # 协议版本号为0x21
        self.device_addr = device_addr  # 设备地址,默认为1
        
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
        
    def send_command(self, ser, cid1, cid2, data=b''):
        """发送命令并获取响应数据"""
        # # 构造发送帧  
        # frame_data = struct.pack('>BBBB', self.FRAME_VERSION, self.device_addr, cid1, cid2)
        # frame_data += self.get_length(data)
        # frame_data += data  
        
        # frame = self.FRAME_HEADER + frame_data + self.FRAME_FOOTER
        # chksum = self.calc_chksum(frame)
        # frame = frame[:-1] + chksum + self.FRAME_FOOTER
        # 构造发送帧  
        frame_data = struct.pack('>BBBB', self.FRAME_VERSION, self.device_addr, cid1, cid2)
        frame_data += self.get_length(data)

        frame = self.FRAME_HEADER + frame_data + data + self.FRAME_FOOTER
        chksum = self.calc_chksum(frame)
        frame = frame[:-1] + chksum + self.FRAME_FOOTER
        
        ser.write(frame)  # 发送命令帧
        logging.debug(f"Sent command: {frame.hex()}")  
        
        # 读取响应帧  
        while True:
            soi = ser.read(1)
            if len(soi) == 0:
                return None
            if soi[0] == ord(self.FRAME_HEADER):
                break
        
        fixed_fields = ser.read(9)
        if len(fixed_fields) < 9:  
            return None
        
        lenid_low = fixed_fields[5]
        lenid_high = fixed_fields[4] & 0x0F
        frame_length = (lenid_high << 8) | lenid_low
        
        frame_lchksum = (fixed_fields[4] >> 4) & 0x0F
        
        calc_lchksum = (fixed_fields[4] + fixed_fields[5] + frame_length) % 16
        if frame_lchksum != ((~calc_lchksum) + 1) & 0x0F:
            logging.warning(f"LCHKSUM check failed, received: {frame_lchksum:X}, calculated: {((~calc_lchksum) + 1) & 0x0F:X}")
        
        frame_info = ser.read(frame_length)
        if len(frame_info) < frame_length:
            return None
        
        frame_chksum = ser.read(2) 
        if len(frame_chksum) < 2:
            return None
        
        eoi = ser.read(1)
        if len(eoi) == 0 or eoi[0] != ord(self.FRAME_FOOTER):
            return None
            
        frame_data = soi + fixed_fields + frame_info + frame_chksum + eoi
        
        # 校验响应帧
        if not self.check_frame(frame_data):
            logging.warning(f"Invalid response frame: {frame_data.hex()}")
            return None
        
        # 解析响应数据
        frame_rtn = fixed_fields[3]
        frame_info = frame_info
        
        if frame_rtn == 0x00:
            return frame_info  # 返回INFO字段的数据
        else:
            logging.warning(f"Error response: RTN={frame_rtn:02X}")
            return None
        
    def bcd2str(self, bcd_data):
        """BCD码转字符串"""
        year = str((bcd_data[0] >> 4) * 10 + (bcd_data[0] & 0x0F))
        month = str((bcd_data[1] >> 4) * 10 + (bcd_data[1] & 0x0F))
        day = str((bcd_data[2] >> 4) * 10 + (bcd_data[2] & 0x0F))
        hour = str((bcd_data[3] >> 4) * 10 + (bcd_data[3] & 0x0F))
        minute = str((bcd_data[4] >> 4) * 10 + (bcd_data[4] & 0x0F))
        second = str((bcd_data[5] >> 4) * 10 + (bcd_data[5] & 0x0F))
        return f"20{year}-{month}-{day} {hour}:{minute}:{second}"
        
    def str2bcd(self, time_str):
        """字符串转BCD码""" 
        bcd_data = b''
        for char in time_str:
            if char.isdigit():
                bcd_data += struct.pack('B', int(char))
        return bcd_data
        
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
        
    def show_menu(self):
        print("请选择要执行的操作:")
        print("1. 读取当前时间")
        print("2. 设置当前时间")  
        print("3. 读取协议版本号")
        print("4. 读取设备地址")
        print("5. 读取厂家信息")
        print("6. 读取交流电压")
        print("7. 读取直流电压电流")
        print("0. 退出程序")
        
    def main(self):
        default_port = '/dev/ttyS2'
        port = input(f'请输入串口号(默认为{default_port}): ')
        if not port:
            port = default_port
        baudrate = 9600
        bytesize = serial.EIGHTBITS
        parity = serial.PARITY_NONE
        stopbits = serial.STOPBITS_ONE
        
        try:
            ser = serial.Serial(port, baudrate, bytesize=bytesize, parity=parity, stopbits=stopbits)
            logging.info(f"Serial port {port} opened, baudrate {baudrate}, bytesize {bytesize}, parity {parity}, stopbits {stopbits}")
            
            while True:
                self.show_menu()
                choice = input("请输入选项编号: ")
                
                if choice == '0':
                    logging.info("Exit monitor")
                    break
                elif choice == '1':  # 读取当前时间
                    response = self.send_command(ser, 0x40, 0x4D)
                    if response:
                        current_time = self.bcd2str(response[:6])
                        logging.info(f"Current time: {current_time}")
                elif choice == '2':  # 设置当前时间
                    time_str = input("请输入设置的时间(格式:YY-MM-DD hh:mm:ss): ")
                    time_bcd = self.str2bcd(time_str)
                    response = self.send_command(ser, 0x40, 0x4E, time_bcd)
                    if response is not None:  
                        logging.info("Time set successfully")
                elif choice == '3':  # 读取协议版本号
                    response = self.send_command(ser, 0x40, 0x4F)
                    if response:
                        ver = struct.unpack('B', response)[0]
                        logging.info(f"Protocol version: {ver>>4}.{ver&0x0F}")  
                elif choice == '4':  # 读取设备地址
                    response = self.send_command(ser, 0x40, 0x50)
                    if response:
                        device_addr = struct.unpack('B', response)[0]
                        logging.info(f"Device address: {device_addr}")
                elif choice == '5':  # 读取厂家信息
                    response = self.send_command(ser, 0x40, 0x51)
                    if response:
                        device_name = response[:10].decode('utf-8').rstrip('\x00') 
                        software_ver = response[10:12].decode('utf-8')
                        manufacturer = response[12:].decode('utf-8').rstrip('\x00')
                        logging.info(f"Device name: {device_name}")
                        logging.info(f"Software version: {software_ver}")
                        logging.info(f"Manufacturer: {manufacturer}")
                elif choice == '6':  # 读取交流电压
                    response = self.send_command(ser, 0x40, 0x41)
                    if response:
                        # TODO: 解析交流电压数据
                        pass  
                elif choice == '7':  # 读取直流电压电流
                    response = self.send_command(ser, 0x41, 0x41)
                    if response:
                        # TODO: 解析直流电压电流数据
                        pass
                else:
                    logging.error(f"Invalid choice {choice}")
                
        except serial.SerialException:
            logging.error(f"Failed to open serial port {port}. Please check the port name and permissions.")
            sys.exit(1)
        except KeyboardInterrupt:
            logging.info("MU4801 monitor terminated")
        finally:
            ser.close()
            logging.info("Serial port closed")

if __name__ == '__main__':
    monitor = MU4801Monitor()
    monitor.main()