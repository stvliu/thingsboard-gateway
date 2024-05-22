import logging
from datetime import datetime
from ydt1363_protocol import Protocol, InfoEncoder

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class MU4801Simulator:
    def __init__(self, device_addr, port):
        self.protocol = Protocol(device_addr, port)
        logging.debug(f"Initialized MU4801Protocol with device_addr={device_addr}, port={port}")
        self.device_name = 'MU4801    '
        self.software_version = '10'
        self.manufacturer = 'Harbin Segu Electric Technology Co., Ltd.'
        self.current_time = InfoEncoder.encode_datetime(datetime.strptime("2023-05-24 14:25:00", "%Y-%m-%d %H:%M:%S"))
        logging.debug(f"Initialized MU4801Simulator with device_name={self.device_name}, software_version={self.software_version}, manufacturer={self.manufacturer}, current_time={self.current_time.hex()}")

    def handle_get_time(self):
        logging.debug("Handling get time command")
        return self.current_time

    def handle_set_time(self, data):
        logging.debug(f"Handling set time command with data={data.hex()}")
        self.current_time = data
        return None

    def handle_get_version(self):
        logging.debug("Handling get version command")
        return InfoEncoder.encode_data(self.protocol.protocol_version)

    def handle_get_address(self):
        logging.debug("Handling get address command")
        return InfoEncoder.encode_data(self.protocol.device_addr)

    def handle_get_info(self):
        logging.debug("Handling get info command")
        
        # 设备名称:10字节,不足部分以空格填充
        device_name = self.device_name.ljust(10)[:10].encode('ascii')
        
        # 软件版本:2字节,不足部分以空格填充
        software_version = self.software_version.ljust(2)[:2].encode('ascii')
        
        # 厂商名称:20字节,超出部分截断
        manufacturer = self.manufacturer[:20].ljust(20)[:20].encode('ascii')
        
        response = device_name + software_version + manufacturer
        logging.debug(f"Responding with device info: {response.decode('ascii')}")
        return response

    def handle_command(self, cid1, cid2, data):
        logging.debug(f"Received command: cid1={cid1:02X}, cid2={cid2:02X}, data={data.hex()}")

        if cid1 == 0x40:
            if cid2 == 0x4D:  # 获取当前时间
                return self.handle_get_time()
            elif cid2 == 0x4E:  # 设置当前时间
                return self.handle_set_time(data)
            elif cid2 == 0x4F:  # 获取通信协议版本号
                return self.handle_get_version()
            elif cid2 == 0x50:  # 获取本机地址
                return self.handle_get_address()
            elif cid2 == 0x51:  # 获取厂家信息
                return self.handle_get_info()

        logging.warning(f"Unsupported command: CID2={cid2:02X}")
        return None

    def main(self):
        if not self.protocol.open():
            logging.error("Failed to open serial port")
            return

        logging.info("MU4801 simulator started")
        try:
            while True:
                #logging.debug("Waiting for command frame...")
                frame = self.protocol.recv_command()
                if frame is None:
                    logging.warning("Received invalid frame, skipping")
                    continue

                logging.info(f"Received command frame: cid1={frame.cid1:02X}, cid2={frame.cid2:02X}, info={frame.info.hex()}")
                response = self.handle_command(frame.cid1, frame.cid2, frame.info)
                if response is not None:
                    logging.debug(f"Sending response frame: cid1={frame.cid1:02X}, cid2=00, info={response.hex()}")
                    logging.debug(f"=======================")
                    self.protocol.send_response(frame.cid1, 0x00, response)

                else:
                    logging.warning(f"Unsupported command, sending error response: cid1={frame.cid1:02X}, cid2=04")
                    self.protocol.send_response(frame.cid1, 0x04, b'')

        except KeyboardInterrupt:
            logging.info("MU4801 simulator terminated by user")
        finally:
            self.protocol.close()
            logging.info("Serial port closed")

if __name__ == '__main__':
    device_addr = 1
    
    default_port = '/dev/ttyS3'
    port = input(f'请输入串口号(默认为{default_port}): ')
    if not port:
        port = default_port
    logging.info(f"Using serial port: {port}")

    simulator = MU4801Simulator(device_addr, port)
    simulator.main()