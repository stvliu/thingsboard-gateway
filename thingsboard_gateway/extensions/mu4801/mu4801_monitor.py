from ydt1363_3_2005_protocol import MU4801Protocol
from mu4801_constants import *
from mu4801_data_structs import *
import logging
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class MU4801Monitor:
    def __init__(self, device_addr, port):
        self.protocol = MU4801Protocol(device_addr, port)
        logging.debug(f"Initialized MU4801Monitor with device_addr={device_addr}, port={port}")

    def show_menu(self):
        print("请选择要执行的操作:")
        print("1. 读取当前时间")
        print("2. 设置当前时间")  
        print("3. 读取协议版本号")
        print("4. 读取设备地址")
        print("5. 读取厂家信息")
        print("6. 读取交流数据")  
        print("7. 读取交流告警状态")
        print("8. 读取交流配置参数")
        print("9. 设置交流配置参数")
        print("10. 读取整流模块数据")
        print("11. 读取整流模块状态")
        print("12. 读取整流模块告警")
        print("13. 整流模块远程开关机")
        print("14. 读取直流数据")
        print("15. 读取直流告警状态")  
        print("16. 读取直流配置参数")
        print("17. 设置直流配置参数")
        print("18. 系统控制命令")  
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
                    response = self.protocol.send_command(CID1_SYS_CONTROL, CID2_GET_TIME, None)
                    if response is not None:
                        current_time = DateTimeStruct.from_bytes(response).to_datetime().strftime("%Y-%m-%d %H:%M:%S")
                        logging.info(f"Current time: {current_time}")
                    else:
                        logging.warning("Failed to read current time")
                        
                elif choice == '2':  # 设置当前时间
                    logging.info("Setting current time")
                    time_str = input("请输入设置的时间(格式:YYYY-MM-DD hh:mm:ss): ")
                    logging.debug(f"User input: {time_str}")
                    try:
                        time_struct = DateTimeStruct.from_str(time_str)
                        response = self.protocol.send_command(CID1_SYS_CONTROL, CID2_SET_TIME, time_struct.to_bytes())
                        if response is None:
                            logging.info("Time set successfully")
                        else:
                            logging.warning("Failed to set time")
                    except ValueError as e:
                        logging.error(f"Invalid time format: {e}")

                elif choice == '3':  # 读取协议版本号  
                    logging.info("Reading protocol version")
                    response = self.protocol.send_command(CID1_SYS_CONTROL, CID2_GET_VERSION, None)
                    if response is not None:
                        version = response[0]  
                        logging.info(f"Protocol version: {version>>4}.{version&0x0F}")
                    else:
                        logging.warning("Failed to read protocol version")

                elif choice == '4':  # 读取设备地址
                    logging.info("Reading device address") 
                    response = self.protocol.send_command(CID1_SYS_CONTROL, CID2_GET_ADDR, None)
                    if response is not None:
                        addr = response[0]
                        logging.info(f"Device address: {addr}")
                    else:
                        logging.warning("Failed to read device address")

                elif choice == '5':  # 读取厂家信息
                    logging.info("Reading manufacturer info")
                    response = self.protocol.send_command(CID1_SYS_CONTROL, CID2_GET_MFR_INFO, None) 
                    if response is not None:
                        info = InfoStruct.from_bytes(response)
                        logging.info(f"Device name: {info.device_name}")
                        logging.info(f"Software version: {info.software_version}")
                        logging.info(f"Manufacturer: {info.manufacturer}")
                    else:
                        logging.warning("Failed to read manufacturer info")

                elif choice == '6':  # 读取交流数据  
                    logging.info("Reading AC analog data")
                    response = self.protocol.send_command(CID1_DC_POWER, CID2_GET_ANALOG_FLOAT, None)
                    if response is not None: 
                        analog = AcAnalogStruct.from_bytes(response)
                        logging.info(f"AC voltage (ph_a): {analog.voltage_ph_a:.1f} V") 
                        logging.info(f"AC voltage (ph_b): {analog.voltage_ph_b:.1f} V")
                        logging.info(f"AC voltage (ph_c): {analog.voltage_ph_c:.1f} V")
                        logging.info(f"AC frequency: {analog.ac_freq:.1f} Hz")  
                    else:
                        logging.warning("Failed to read AC analog data")
                        
                elif choice == '7':  # 读取交流告警状态
                    logging.info("Reading AC alarm status")
                    response = self.protocol.send_command(CID1_DC_POWER, CID2_GET_ALARM, None)
                    if response is not None:
                        alarm = AcAlarmStruct.from_bytes(response)
                        logging.info(f"AC SPD alarm: {alarm.spd_alarm}")
                        logging.info(f"AC over voltage (ph_a): {alarm.over_voltage_ph_a}")
                        logging.info(f"AC over voltage (ph_b): {alarm.over_voltage_ph_b}")
                        logging.info(f"AC over voltage (ph_c): {alarm.over_voltage_ph_c}")
                        logging.info(f"AC under voltage (ph_a): {alarm.under_voltage_ph_a}")
                        logging.info(f"AC under voltage (ph_b): {alarm.under_voltage_ph_b}") 
                        logging.info(f"AC under voltage (ph_c): {alarm.under_voltage_ph_c}")
                    else:
                        logging.warning("Failed to read AC alarm status")
                        
                elif choice == '8':  # 读取交流配置参数
                    logging.info("Reading AC config parameters")
                    response = self.protocol.send_command(CID1_DC_POWER, CID2_GET_CONFIG_FLOAT, None)
                    if response is not None:
                        config = AcConfigStruct.from_bytes(response)
                        logging.info(f"AC over voltage setting: {config.ac_over_voltage:.1f} V")
                        logging.info(f"AC under voltage setting: {config.ac_under_voltage:.1f} V")
                    else:
                        logging.warning("Failed to read AC config parameters")

                elif choice == '9':  # 设置交流配置参数
                    logging.info("Setting AC config parameters")
                    over_volt = float(input("请输入交流过压值(V): "))
                    under_volt = float(input("请输入交流欠压值(V): "))
                    config = AcConfigStruct(ac_over_voltage=over_volt, ac_under_voltage=under_volt)
                    response = self.protocol.send_command(CID1_DC_POWER, CID2_SET_CONFIG_FLOAT, config.to_bytes())
                    if response is None:
                        logging.info("AC config updated successfully")
                    else:
                        logging.warning("Failed to update AC config")

                elif choice == '10':  # 读取整流模块数据 
                    logging.info("Reading rectifier analog data") 
                    module_count = int(input("请输入要读取的模块数量: "))
                    response = self.protocol.send_command(CID1_RECT, CID2_GET_ANALOG_FLOAT, struct.pack('B', module_count))
                    if response is not None:
                        analog = RectAnalogStruct.from_bytes(response) 
                        logging.info(f"Output voltage: {analog.output_voltage:.2f} V")
                        for i, current in enumerate(analog.module_currents, 1):
                            logging.info(f"Module {i} current: {current:.2f} A") 
                    else:
                        logging.warning("Failed to read rectifier analog data")

                elif choice == '11':  # 读取整流模块状态
                    logging.info("Reading rectifier status")
                    module_count = int(input("请输入要读取的模块数量: "))
                    response = self.protocol.send_command(CID1_RECT, CID2_GET_STATUS, struct.pack('B', module_count))
                    if response is not None:
                        status = RectStatusStruct.from_bytes(response)
                        for i, state in enumerate(status.status_list, 1):
                            logging.info(f"Module {i} status: {'On' if state == 0 else 'Off'}")
                    else:
                        logging.warning("Failed to read rectifier status")

                elif choice == '12':  # 读取整流模块告警 
                    logging.info("Reading rectifier alarms")
                    module_count = int(input("请输入要读取的模块数量: "))
                    response = self.protocol.send_command(CID1_RECT, CID2_GET_ALARM, struct.pack('B', module_count))
                    if response is not None:
                        alarms = RectAlarmStruct.from_bytes(response)
                        for i, alarm in enumerate(alarms.alarm_list, 1):
                            logging.info(f"Module {i} alarm: {alarm:02X}")
                    else: 
                        logging.warning("Failed to read rectifier alarms")

                elif choice == '13':  # 整流模块远程开关机
                    module_id = int(input("请输入要控制的模块ID(1~n): "))
                    ctrl_type = input("请输入控制类型(0-开机, 1-关机): ")
                    if ctrl_type == '0':
                        ctrl_code = 0x20  # 开机
                    elif ctrl_type == '1':
                        ctrl_code = 0x2F  # 关机
                    else:
                        logging.error("无效的控制类型")
                        continue
                        
                    data = struct.pack('BB', module_id, ctrl_code)   
                    response = self.protocol.send_command(CID1_RECT, CID2_CONTROL, data)
                    if response is None:
                        logging.info(f"Rectifier module {module_id} {'enabled' if ctrl_code == 0x20 else 'disabled'}")  
                    else:
                        logging.warning(f"Failed to control rectifier module {module_id}")
                            
                elif choice == '14':  # 读取直流数据
                    logging.info("Reading DC analog data")
                    response = self.protocol.send_command(CID1_DC_DIST, CID2_GET_ANALOG_FLOAT, None)
                    if response is not None:
                        analog = DcAnalogStruct.from_bytes(response)
                        logging.info(f"Battery voltage: {analog.voltage:.2f} V")
                        logging.info(f"Total load current: {analog.total_current:.2f} A")
                        logging.info(f"Battery current: {analog.battery_current:.2f} A") 
                        logging.info("Load branch currents:")
                        for i, current in enumerate(analog.load_branch_currents, 1): 
                            logging.info(f"Branch {i}: {current:.2f} A")
                    else:
                        logging.warning("Failed to read DC analog data")
                        
                elif choice == '15':  # 读取直流告警状态
                    logging.info("Reading DC alarm status")  
                    response = self.protocol.send_command(CID1_DC_DIST, CID2_GET_ALARM, None)
                    if response is not None:
                        alarm = DcAlarmStruct.from_bytes(response)
                        logging.info(f"DC over voltage: {alarm.over_voltage}")  
                        logging.info(f"DC under voltage: {alarm.under_voltage}")
                        logging.info(f"DC SPD alarm: {alarm.spd_alarm}")
                        logging.info(f"Fuse 1 alarm: {alarm.fuse1_alarm}")  
                        logging.info(f"Fuse 2 alarm: {alarm.fuse2_alarm}")
                        logging.info(f"Fuse 3 alarm: {alarm.fuse3_alarm}")
                        logging.info(f"Fuse 4 alarm: {alarm.fuse4_alarm}")  
                    else:
                        logging.warning("Failed to read DC alarm status")
                        
                elif choice == '16':  # 读取直流配置参数
                    logging.info("Reading DC config parameters") 
                    response = self.protocol.send_command(CID1_DC_DIST, CID2_GET_CONFIG_FLOAT, None)
                    if response is not None:
                        config = DcConfigStruct.from_bytes(response)
                        logging.info(f"DC over voltage setting: {config.voltage_upper_limit:.2f} V") 
                        logging.info(f"DC under voltage setting: {config.voltage_lower_limit:.2f} V")
                        logging.info(f"DC limited current: {config.current_limit:.2f} A")   
                    else:
                        logging.warning("Failed to read DC config parameters")

                elif choice == '17':  # 设置直流配置参数  
                    logging.info("Setting DC config parameters")
                    over_volt = float(input("请输入直流过压值(V): "))
                    under_volt = float(input("请输入直流欠压值(V): "))
                    current_limit = float(input("请输入直流限流值(A): "))
                    config = DcConfigStruct(
                        voltage_upper_limit=over_volt,
                        voltage_lower_limit=under_volt,
                        current_limit=current_limit
                    )        
                    response = self.protocol.send_command(CID1_DC_DIST, CID2_SET_CONFIG_FLOAT, config.to_bytes())
                    if response is None:
                        logging.info("DC config updated successfully")  
                    else:
                        logging.warning("Failed to update DC config")
                        
                elif choice == '18':  # 系统控制命令
                    logging.info("System control commands")   
                    print("a - 系统复位") 
                    print("b - 负载1下电")
                    print("c - 负载1上电")
                    print("d - 电池下电")  
                    print("e - 电池上电")
                    ctrl_choice = input("请选择控制命令: ")
                    if ctrl_choice == 'a':
                        ctrl_type = 0xE1
                    elif ctrl_choice == 'b':
                        ctrl_type = 0xE5   
                    elif ctrl_choice == 'c':
                        ctrl_type = 0xE6
                    elif ctrl_choice == 'd': 
                        ctrl_type = 0xED
                    elif ctrl_choice == 'e':
                        ctrl_type = 0xEE
                    else:
                        logging.error("无效的控制命令")
                        continue
                    response = self.protocol.send_command(CID1_SYS_CONTROL, CID2_CONTROL_SYSTEM, struct.pack('B', ctrl_type))
                    if response is None:
                        logging.info("System control command sent successfully")
                    else:
                        logging.warning("Failed to send system control command")
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