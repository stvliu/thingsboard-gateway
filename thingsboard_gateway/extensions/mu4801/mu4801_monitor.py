import logging
from datetime import datetime
from ydt1363_3_2005_protocol import Protocol, InfoEncoder, InfoDecoder

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class MU4801Monitor:
    def __init__(self, device_addr, port):
        self.protocol = Protocol(device_addr, port)
        logging.debug(f"Initialized MU4801Monitor with device_addr={device_addr}, port={port}")

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
        if not self.protocol.open():
            logging.error("Failed to open serial port")
            return

        try:
            while True:
                self.show_menu()
                choice = input("请输入选项编号: ")
                logging.debug(f"User input: {choice}")

                if choice == '0':
                    logging.info("Exiting monitor")
                    break
                elif choice == '1':  # 读取当前时间
                    logging.info("Reading current time")
                    response = self.protocol.send_command(0x40, 0x4D, None)
                    if response is not None:
                        info_type, info_value = response
                        if info_type == datetime:
                            current_time = info_value.strftime("%Y-%m-%d %H:%M:%S")
                            logging.info(f"Current time: {current_time}")
                        else:
                            logging.warning(f"Unexpected response type: {info_type}")
                    else:
                        logging.warning("Failed to read current time")
                elif choice == '2':  # 设置当前时间
                    logging.info("Setting current time")
                    time_str = input("请输入设置的时间(格式:YY-MM-DD hh:mm:ss): ")
                    logging.debug(f"User input: {time_str}")
                    time_data = InfoEncoder.encode_datetime(datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S"))
                    logging.debug(f"Encoded time data: {time_data.hex()}")
                    response = self.protocol.send_command(0x40, 0x4E, time_data)
                    if response is None:
                        logging.info("Time set successfully")
                    else:
                        logging.warning("Failed to set time")
                elif choice == '3':  # 读取协议版本号
                    logging.info("Reading protocol version")
                    response = self.protocol.send_command(0x40, 0x4F, None)
                    if response is not None:
                        info_type, info_value = response
                        if info_type == int:
                            ver = info_value
                            logging.info(f"Protocol version: {ver>>4}.{ver&0x0F}")
                        else:
                            logging.warning(f"Unexpected response type: {info_type}")
                    else:
                        logging.warning("Failed to read protocol version")
                elif choice == '4':  # 读取设备地址
                    logging.info("Reading device address")
                    response = self.protocol.send_command(0x40, 0x50, None)
                    if response is not None:
                        info_type, info_value = response
                        if info_type == int:
                            device_addr = info_value
                            logging.info(f"Device address: {device_addr}")
                        else:
                            logging.warning(f"Unexpected response type: {info_type}")
                    else:
                        logging.warning("Failed to read device address")
                elif choice == '5':  # 读取厂家信息
                    logging.info("Reading manufacturer info")
                    response = self.protocol.send_command(0x40, 0x51, None)
                    if response is not None:
                        info_type, info_value = response
                        if info_type == bytes:
                            device_name = info_value[:10].decode('ascii').rstrip()
                            software_ver = info_value[10:12].decode('ascii')
                            manufacturer = info_value[12:].decode('ascii').rstrip()
                            logging.info(f"Device name: {device_name}")
                            logging.info(f"Software version: {software_ver}")
                            logging.info(f"Manufacturer: {manufacturer}")
                        else:
                            logging.warning(f"Unexpected response type: {info_type}")
                    else:
                        logging.warning("Failed to read manufacturer info")
                elif choice == '6':  # 读取交流电压
                    logging.info("Reading AC voltage")
                    response = self.protocol.send_command(0x40, 0x41, None)
                    if response is not None:
                        info_type, info_value = response
                        if info_type == bytes:
                            # TODO: 解析交流电压数据
                            pass
                        else:
                            logging.warning(f"Unexpected response type: {info_type}")
                    else:
                        logging.warning("Failed to read AC voltage")
                elif choice == '7':  # 读取直流电压电流
                    logging.info("Reading DC voltage and current")
                    response = self.protocol.send_command(0x41, 0x41, None)
                    if response is not None:
                        info_type, info_value = response
                        if info_type == bytes:
                            # TODO: 解析直流电压电流数据
                            pass
                        else:
                            logging.warning(f"Unexpected response type: {info_type}")
                    else:
                        logging.warning("Failed to read DC voltage and current")
                else:
                    logging.warning(f"Invalid choice: {choice}")

        except KeyboardInterrupt:
            logging.info("MU4801 monitor terminated by user")
        finally:
            self.protocol.close()
            logging.info("Serial port closed")

if __name__ == '__main__':
    device_addr = 1
    
    default_port = '/dev/ttyS2'
    port = input(f'请输入串口号(默认为{default_port}): ')
    if not port:
        port = default_port
    logging.info(f"Using serial port: {port}")
    
    monitor = MU4801Monitor(device_addr, port)
    monitor.main()