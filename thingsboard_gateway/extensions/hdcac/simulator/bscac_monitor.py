from bscac_protocol import BscAcProtocol
import logging
import datetime

# 导入相关的数据类  
from models import *

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class BscAcMonitor:
    def __init__(self, device_addr, port):
        self._log = logging.getLogger(self.__class__.__name__) 
        self._protocol = BscAcProtocol(device_addr, port)
        self._protocol.connect()

    def show_menu(self):
        print("请选择要执行的操作:")
        print("1. 读取空调模拟量")
        print("2. 读取空调运行状态") 
        print("3. 读取空调告警状态")
        print("4. 遥控空调")
        print("5. 读取空调配置参数")
        print("6. 设置空调配置参数")
        print("7. 读取空调时间")
        print("8. 设置空调时间")
        print("9. 设置设备地址")
        print("10. 读取厂家信息")
        print("0. 退出程序")

    def run(self):
        while True:
            self.show_menu()
            choice = input("请输入选项编号: ")
            print()

            if choice == '0':
                print("程序退出") 
                break
            elif choice == '1':  # 读取空调模拟量
                print("读取空调模拟量:")
                analog_data = self._protocol.send_command('getAcAnalogData')
                print(f"机柜温度: {analog_data.cabinet_temp:.1f}°C")
                print(f"送风温度: {analog_data.supply_temp:.1f}°C") 
                print(f"交流电压: {analog_data.voltage}V")
                print(f"工作电流: {analog_data.current}A")
            elif choice == '2':  # 读取空调运行状态
                print("读取空调运行状态:")
                run_status = self._protocol.send_command('getAcRunStatus')
                print(f"空调状态: {'开机' if run_status.air_conditioner == SwitchStatus.ON else '关机'}")
                print(f"内风机状态: {'开启' if run_status.indoor_fan == SwitchStatus.ON else '关闭'}")
                print(f"外风机状态: {'开启' if run_status.outdoor_fan == SwitchStatus.ON else '关闭'}")
                print(f"加热状态: {'开启' if run_status.heater == SwitchStatus.ON else '关闭'}")
            elif choice == '3':  # 读取空调告警状态
                print("读取空调告警状态:")  
                alarm_status = self._protocol.send_command('getAcAlarmStatus')
                print(f"制冷故障: {alarm_status.compressor_alarm.name}")
                print(f"高温告警: {alarm_status.high_temp.name}") 
                print(f"低温告警: {alarm_status.low_temp.name}")
                print(f"加热故障: {alarm_status.heater_alarm.name}")
                print(f"传感器故障: {alarm_status.sensor_fault.name}")
                print(f"过压告警: {alarm_status.over_voltage.name}")
                print(f"欠压告警: {alarm_status.under_voltage.name}")
            elif choice == '4':  # 遥控空调
                print("遥控空调:")
                print("1. 开机")
                print("2. 关机")
                print("3. 制冷开启")  
                print("4. 制冷关闭")
                print("5. 制热开启")
                print("6. 制热关闭") 
                cmd = input("请选择遥控命令编号: ")
                if cmd == '1':
                    self._protocol.send_command('remoteControl', RemoteControl(RemoteCommand.ON))
                elif cmd == '2':
                    self._protocol.send_command('remoteControl', RemoteControl(RemoteCommand.OFF))  
                elif cmd == '3':
                    self._protocol.send_command('remoteControl', RemoteControl(RemoteCommand.COOLING_ON))
                elif cmd == '4':
                    self._protocol.send_command('remoteControl', RemoteControl(RemoteCommand.COOLING_OFF))
                elif cmd == '5':
                    self._protocol.send_command('remoteControl', RemoteControl(RemoteCommand.HEATING_ON))
                elif cmd == '6':  
                    self._protocol.send_command('remoteControl', RemoteControl(RemoteCommand.HEATING_OFF))
                else:
                    print("无效的遥控命令")
            elif choice == '5':  # 读取空调配置参数  
                print("读取空调配置参数:")
                config_params = self._protocol.send_command('getAcConfigParams')
                print(f"空调开启温度: {config_params.start_temp/10:.1f}°C")
                print(f"空调停止回差: {config_params.temp_hysteresis/10:.1f}°C") 
                print(f"加热开启温度: {config_params.heater_start_temp/10:.1f}°C")
                print(f"加热停止回差: {config_params.heater_hysteresis/10:.1f}°C") 
                print(f"高温告警点: {config_params.high_temp_alarm/10:.1f}°C")
                print(f"低温告警点: {config_params.low_temp_alarm/10:.1f}°C")
            elif choice == '6':  # 设置空调配置参数
                print("设置空调配置参数:")
                print("1. 空调开启温度")
                print("2. 空调停止回差")
                print("3. 加热开启温度")
                print("4. 加热停止回差")   
                print("5. 高温告警点")
                print("6. 低温告警点")
                param_type = input("请选择要设置的参数编号: ")
                param_value = int(float(input("请输入参数值(°C,保留一位小数): ")) * 10)
                if param_type == '1':
                    self._protocol.send_command('setAcConfigParams', ConfigParam(ConfigParamType.AC_START_TEMP, param_value))
                elif param_type == '2':
                    self._protocol.send_command('setAcConfigParams', ConfigParam(ConfigParamType.AC_TEMP_HYSTERESIS, param_value))
                elif param_type == '3':
                    self._protocol.send_command('setAcConfigParams', ConfigParam(ConfigParamType.HEAT_START_TEMP, param_value))
                elif param_type == '4':
                    self._protocol.send_command('setAcConfigParams', ConfigParam(ConfigParamType.HEAT_HYSTERESIS, param_value))
                elif param_type == '5':  
                    self._protocol.send_command('setAcConfigParams', ConfigParam(ConfigParamType.HIGH_TEMP_ALARM, param_value))
                elif param_type == '6':
                    self._protocol.send_command('setAcConfigParams', ConfigParam(ConfigParamType.LOW_TEMP_ALARM, param_value))  
                else:
                    print("无效的参数选择")
            elif choice == '7':  # 读取空调时间
                print("读取空调时间:")
                date_time = self._protocol.send_command('getDateTime')  
                print(f"空调时间: {date_time.datetime}")
            elif choice == '8':  # 设置空调时间
                print("设置空调时间:")
                try:
                    dt_str = input("请输入日期时间(格式: YYYY-MM-DD hh:mm:ss): ")
                    dt = datetime.datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                    self._protocol.send_command('setDateTime', DateTime(
                        year=dt.year,
                        month=dt.month,
                        day=dt.day, 
                        hour=dt.hour,
                        minute=dt.minute,
                        second=dt.second
                    ))
                    print("空调时间设置成功")
                except ValueError:
                    print("无效的日期时间格式")
            elif choice == '9':  # 设置设备地址  
                print("设置设备地址:")
                try:
                    address = int(input("请输入新的设备地址(1-254): "))
                    if address < 1 or address > 254:
                        raise ValueError
                    self._protocol.send_command('setDeviceAddress', DeviceAddress(address))
                    print(f"设备地址已设置为: {address}")   
                except ValueError:
                    print("无效的设备地址")
            elif choice == '10':  # 读取厂家信息 
                print("读取厂家信息:")
                info = self._protocol.send_command('getManufacturerInfo')
                print(f"设备名称: {info.device_name}")
                print(f"软件版本: {info.software_version}")
                print(f"制造商: {info.manufacturer}")
            else:
                print("无效的选项")

            print()
                
if __name__ == '__main__':
    device_addr = 1
    default_port = '/dev/ttyS4'  
    port = input(f'请输入串口号(默认为{default_port}): ')
    if not port:
        port = default_port
    logging.info(f"Using serial port: {port}") 
    monitor = BscAcMonitor(device_addr, port)
    monitor.run()