from mu4801_protocol import MU4801Protocol
import logging
import datetime

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')

class MU4801Monitor:
    def __init__(self, device_addr, port):
        self._log = logging.getLogger(self.__class__.__name__)
        self.protocol = MU4801Protocol(device_addr, port)
        self.protocol.connect()
        self.serial = self.protocol._serial
        
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
        
    def run(self):
        while True:
            self.show_menu()
            choice = input("请输入选项编号: ")
            print()

            if choice == '0':
                print("程序退出")
                break
            elif choice == '1':  # 读取当前时间
                print("读取当前时间:")
                dt = self.protocol.send_command('getDateTime')
                print(f"当前时间: {dt}")
            elif choice == '2':  # 设置当前时间
                print("设置当前时间:")
                try:
                    dt_str = input("请输入日期时间(格式: YYYY-MM-DD hh:mm:ss): ")
                    dt = datetime.datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                    self.protocol.send_command('setDateTime', {
                        'year': dt.year,
                        'month': dt.month,
                        'day': dt.day,
                        'hour': dt.hour,
                        'minute': dt.minute,
                        'second': dt.second
                    })
                    print("时间设置成功")
                except ValueError:
                    print("无效的日期时间格式")
            elif choice == '3':  # 读取协议版本号
                print("读取协议版本号:")
                version = self.protocol.send_command('getProtocolVersion')
                print(f"协议版本号: {version['version']}")
            elif choice == '4':  # 读取设备地址
                print("读取设备地址:")
                addr = self.protocol.send_command('getDeviceAddress')
                print(f"设备地址: {addr['address']}")
            elif choice == '5':  # 读取厂家信息
                print("读取厂家信息:")
                info = self.protocol.send_command('getManufacturerInfo')
                print(f"设备名称: {info['collectorName']}")
                print(f"软件版本: {info['softwareVersion']}")
                print(f"制造商: {info['manufacturer']}")
            elif choice == '6':  # 读取交流数据
                print("读取交流数据:")
                ac_data = self.protocol.send_command('getAcAnalogData')
                print(f"A相电压: {ac_data['voltageA']:.2f} V")
                print(f"B相电压: {ac_data['voltageB']:.2f} V")
                print(f"C相电压: {ac_data['voltageC']:.2f} V")
                print(f"频率: {ac_data['frequency']:.2f} Hz")
            elif choice == '7':  # 读取交流告警状态
                print("读取交流告警状态:")
                ac_alarm = self.protocol.send_command('getAcAlarmStatus')
                print(f"A相电压状态: {ac_alarm['voltageAStatus']}")
                print(f"B相电压状态: {ac_alarm['voltageBStatus']}")
                print(f"C相电压状态: {ac_alarm['voltageCStatus']}")
                print(f"频率状态: {ac_alarm['frequencyStatus']}")
                print(f"交流防雷器状态: {ac_alarm['acArresterStatus']}")
                print(f"交流输入空开状态: {ac_alarm['acInputSwitchStatus']}")
                print(f"交流输出空开状态: {ac_alarm['acOutputSwitchStatus']}")
                print(f"交流第一路输入状态: {ac_alarm['acPowerStatus']}")
            elif choice == '8':  # 读取交流配置参数
                print("读取交流配置参数:")
                ac_config = self.protocol.send_command('getAcConfigParams')
                print(f"交流过压值: {ac_config['acOverVoltage']:.2f} V")
                print(f"交流欠压值: {ac_config['acUnderVoltage']:.2f} V")
            elif choice == '9':  # 设置交流配置参数
                print("设置交流配置参数:")
                try:
                    over_volt = float(input("请输入交流过压值(V): "))
                    under_volt = float(input("请输入交流欠压值(V): "))
                    self.protocol.send_command('setAcConfigParams', {
                        'acOverVoltage': over_volt,
                        'acUnderVoltage': under_volt
                    })
                    print("交流配置参数设置成功")
                except ValueError:
                    print("无效的参数值")
            elif choice == '10':  # 读取整流模块数据
                print("读取整流模块数据:")
                rect_data = self.protocol.send_command('getRectAnalogData', {'moduleCount': 3})
                print(f"输出电压: {rect_data['outputVoltage']:.2f} V")
                for i, current in enumerate(rect_data['moduleCurrent'], 1):
                    print(f"模块{i}电流: {current:.2f} A")
            elif choice == '11':  # 读取整流模块状态
                print("读取整流模块状态:")
                rect_status = self.protocol.send_command('getRectSwitchStatus', {'moduleCount': 3})
                for i, status in enumerate(rect_status['moduleRunStatus'], 1):
                    print(f"模块{i}运行状态: {'开机' if status == 0 else '关机'}")
            elif choice == '12':  # 读取整流模块告警
                print("读取整流模块告警:")
                rect_alarm = self.protocol.send_command('getRectAlarmStatus', {'moduleCount': 3})
                for i, alarm in enumerate(rect_alarm['moduleFailureStatus'], 1):
                    print(f"模块{i}故障状态: {'正常' if alarm == 0 else '故障'}")
                for i, alarm in enumerate(rect_alarm['moduleCommFailureStatus'], 1):
                    print(f"模块{i}通讯故障状态: {'正常' if alarm == 0 else '通讯故障'}")
                for i, alarm in enumerate(rect_alarm['moduleProtectionStatus'], 1):
                    print(f"模块{i}保护状态: {'正常' if alarm == 0 else '保护'}")
                for i, alarm in enumerate(rect_alarm['moduleFanStatus'], 1):
                    print(f"模块{i}风扇状态: {'正常' if alarm == 0 else '故障'}")
            elif choice == '13':  # 整流模块远程开关机
                module_id = int(input("请输入要控制的模块ID(1~n): "))
                ctrl_type = input("请输入控制类型(0-开机, 1-关机): ")
                if ctrl_type == '0':
                    ctrl_code = 0x20
                elif ctrl_type == '1':
                    ctrl_code = 0x2F
                else:
                    print("无效的控制类型")
                    continue

                self.protocol.send_command('controlRectModule', {
                    'moduleId': module_id,
                    'controlType': ctrl_code,
                    'controlValue': 0
                })
                print(f"整流模块{module_id}{'开机' if ctrl_code == 0x20 else '关机'}成功")
            elif choice == '14':  # 读取直流数据
                print("读取直流数据:")
                dc_data = self.protocol.send_command('getDcAnalogData')
                print(f"电池电压: {dc_data['dcVoltage']:.2f} V")
                print(f"负载总电流: {dc_data['totalLoadCurrent']:.2f} A")
                print(f"电池组1电流: {dc_data['batteryGroup1Current']:.2f} A")
                print(f"直流分路1电流: {dc_data['loadBranch1Current']:.2f} A")
                print(f"直流分路2电流: {dc_data['loadBranch2Current']:.2f} A")
                print(f"直流分路3电流: {dc_data['loadBranch3Current']:.2f} A")
                print(f"直流分路4电流: {dc_data['loadBranch4Current']:.2f} A")
                print(f"电池总电流: {dc_data['batteryTotalCurrent']:.2f} A")
                print(f"电池组1容量: {dc_data['batteryGroup1Capacity']:.2f} Ah")
                print(f"电池组1电压: {dc_data['batteryGroup1Voltage']:.2f} V")
                print(f"电池组1中点电压: {dc_data['batteryGroup1MidVoltage']:.2f} V")
                print(f"电池组2中点电压: {dc_data['batteryGroup2MidVoltage']:.2f} V")
                print(f"电池组3中点电压: {dc_data['batteryGroup3MidVoltage']:.2f} V")
                print(f"电池组4中点电压: {dc_data['batteryGroup4MidVoltage']:.2f} V")
                print(f"电池组1温度: {dc_data['batteryGroup1Temperature']:.2f} °C")
                print(f"环境温度1: {dc_data['envTemp1']:.2f} °C")
                print(f"环境温度2: {dc_data['envTemp2']:.2f} °C")
                print(f"环境湿度1: {dc_data['envHumidity1']:.2f} %RH")
                print(f"总负载功率: {dc_data['totalLoadPower']:.2f} W")
                print(f"负载1功率: {dc_data['loadPower1']:.2f} W")
                print(f"负载2功率: {dc_data['loadPower2']:.2f} W")
                print(f"负载3功率: {dc_data['loadPower3']:.2f} W")
                print(f"负载4功率: {dc_data['loadPower4']:.2f} W")
                print(f"总负载电量: {dc_data['totalLoadEnergy']:.2f} kWh")
                print(f"负载1电量: {dc_data['loadEnergy1']:.2f} kWh")
                print(f"负载2电量: {dc_data['loadEnergy2']:.2f} kWh")
                print(f"负载3电量: {dc_data['loadEnergy3']:.2f} kWh")
                print(f"负载4电量: {dc_data['loadEnergy4']:.2f} kWh")
            elif choice == '15':  # 读取直流告警状态
                print("读取直流告警状态:")
                dc_alarm = self.protocol.send_command('getDcAlarmStatus')
                print(f"直流电压状态: {dc_alarm['dcVoltageStatus']}")
                print(f"直流防雷器状态: {dc_alarm['dcArresterStatus']}")
                print(f"负载熔丝状态: {dc_alarm['loadFuseStatus']}")
                print(f"电池组1熔丝状态: {dc_alarm['batteryGroup1FuseStatus']}")
                print(f"电池组2熔丝状态: {dc_alarm['batteryGroup2FuseStatus']}")
                print(f"电池组3熔丝状态: {dc_alarm['batteryGroup3FuseStatus']}")
                print(f"电池组4熔丝状态: {dc_alarm['batteryGroup4FuseStatus']}")
                print(f"BLVD即将下电状态: {dc_alarm['blvdImpendingStatus']}")
                print(f"BLVD下电状态: {dc_alarm['blvdStatus']}")
                print(f"负载即将下电LLVD1状态: {dc_alarm['llvd1ImpendingStatus']}")
                print(f"负载下电LLVD1状态: {dc_alarm['llvd1Status']}")
                print(f"负载即将下电LLVD2状态: {dc_alarm['llvd2ImpendingStatus']}")
                print(f"负载下电LLVD2状态: {dc_alarm['llvd2Status']}")
                print(f"负载即将下电LLVD3状态: {dc_alarm['llvd3ImpendingStatus']}")
                print(f"负载下电LLVD3状态: {dc_alarm['llvd3Status']}")
                print(f"负载即将下电LLVD4状态: {dc_alarm['llvd4ImpendingStatus']}")
                print(f"负载下电LLVD4状态: {dc_alarm['llvd4Status']}")
                print(f"电池温度状态: {dc_alarm['batteryTempStatus']}")
                print(f"电池温度传感器1状态: {dc_alarm['batteryTempSensor1Status']}")
                print(f"环境温度状态: {dc_alarm['envTempStatus']}")
                print(f"环境温度传感器1状态: {dc_alarm['envTempSensor1Status']}")
                print(f"环境温度传感器2状态: {dc_alarm['envTempSensor2Status']}")
                print(f"环境湿度状态: {dc_alarm['envHumidityStatus']}")
                print(f"环境湿度传感器1状态: {dc_alarm['envHumiditySensor1Status']}")
                print(f"门磁状态: {dc_alarm['doorStatus']}")
                print(f"水浸状态: {dc_alarm['waterStatus']}")
                print(f"烟雾状态: {dc_alarm['smokeStatus']}")
                print(f"数字输入1状态: {dc_alarm['digitalInputStatus1']}")
                print(f"数字输入2状态: {dc_alarm['digitalInputStatus2']}")
                print(f"数字输入3状态: {dc_alarm['digitalInputStatus3']}")
                print(f"数字输入4状态: {dc_alarm['digitalInputStatus4']}")
                print(f"数字输入5状态: {dc_alarm['digitalInputStatus5']}")
                print(f"数字输入6状态: {dc_alarm['digitalInputStatus6']}")
            elif choice == '16':  # 读取直流配置参数
                print("读取直流配置参数:")
                dc_config = self.protocol.send_command('getDcConfigParams')
                print(f"直流过压值: {dc_config['dcOverVoltage']:.2f} V")
                print(f"直流欠压值: {dc_config['dcUnderVoltage']:.2f} V")
                print(f"定时均充使能: {'使能' if dc_config['timeEqualizeChargeEnable'] == 1 else '禁止'}")
                print(f"定时均充时间: {dc_config['timeEqualizeDuration']} 小时")
                print(f"定时均充间隔: {dc_config['timeEqualizeInterval']}天")
                print(f"电池组数: {dc_config['batteryGroupNumber']}")
                print(f"电池过温告警点: {dc_config['batteryOverTemp']:.2f} °C")
                print(f"电池欠温告警点: {dc_config['batteryUnderTemp']:.2f} °C")
                print(f"环境过温告警点: {dc_config['envOverTemp']:.2f} °C")
                print(f"环境欠温告警点: {dc_config['envUnderTemp']:.2f} °C")
                print(f"环境过湿告警点: {dc_config['envOverHumidity']:.2f} %RH")
                print(f"电池充电限流点: {dc_config['batteryChargeCurrentLimit']:.2f} C10")
                print(f"浮充电压: {dc_config['floatVoltage']:.2f} V")
                print(f"均充电压: {dc_config['equalizeVoltage']:.2f} V")
                print(f"电池下电电压: {dc_config['batteryOffVoltage']:.2f} V")
                print(f"电池上电电压: {dc_config['batteryOnVoltage']:.2f} V")
                print(f"LLVD1下电电压: {dc_config['llvd1OffVoltage']:.2f} V")
                print(f"LLVD1上电电压: {dc_config['llvd1OnVoltage']:.2f} V")
                print(f"LLVD2下电电压: {dc_config['llvd2OffVoltage']:.2f} V")
                print(f"LLVD2上电电压: {dc_config['llvd2OnVoltage']:.2f} V")
                print(f"LLVD3下电电压: {dc_config['llvd3OffVoltage']:.2f} V")
                print(f"LLVD3上电电压: {dc_config['llvd3OnVoltage']:.2f} V")
                print(f"LLVD4下电电压: {dc_config['llvd4OffVoltage']:.2f} V")
                print(f"LLVD4上电电压: {dc_config['llvd4OnVoltage']:.2f} V")
                print(f"每组电池额定容量: {dc_config['batteryCapacity']:.2f} Ah")
                print(f"电池测试终止电压: {dc_config['batteryTestStopVoltage']:.2f} V")
                print(f"电池组温补系数: {dc_config['batteryTempCoeff']:.2f} mV/°C")
                print(f"电池温补中心点: {dc_config['batteryTempCenter']:.2f} °C")
                print(f"浮充转均充系数: {dc_config['floatToEqualizeCoeff']:.2f} C10")
                print(f"均充转浮充系数: {dc_config['equalizeToFloatCoeff']:.2f} C10")
                print(f"LLVD1下电时间: {dc_config['llvd1OffTime']:.2f} min")
                print(f"LLVD2下电时间: {dc_config['llvd2OffTime']:.2f} min")
                print(f"LLVD3下电时间: {dc_config['llvd3OffTime']:.2f} min")
                print(f"LLVD4下电时间: {dc_config['llvd4OffTime']:.2f} min")
                print(f"负载下电模式: {'电压模式' if dc_config['loadOffMode'] == 0 else '时间模式'}")
            elif choice == '17':  # 设置直流配置参数
                print("设置直流配置参数:")
                try:
                    over_volt = float(input("请输入直流过压值(V): "))
                    under_volt = float(input("请输入直流欠压值(V): "))
                    time_equalize_enable = int(input("请输入定时均充使能(0-禁止, 1-使能): "))
                    time_equalize_duration = int(input("请输入定时均充时间(小时): "))
                    time_equalize_interval = int(input("请输入定时均充间隔(天): "))
                    battery_group_number = int(input("请输入电池组数: "))
                    battery_over_temp = float(input("请输入电池过温告警点(°C): "))
                    battery_under_temp = float(input("请输入电池欠温告警点(°C): "))
                    env_over_temp = float(input("请输入环境过温告警点(°C): "))
                    env_under_temp = float(input("请输入环境欠温告警点(°C): "))
                    env_over_humidity = float(input("请输入环境过湿告警点(%%RH): "))
                    battery_charge_current_limit = float(input("请输入电池充电限流点(C10): "))
                    float_voltage = float(input("请输入浮充电压(V): "))
                    equalize_voltage = float(input("请输入均充电压(V): "))
                    battery_off_voltage = float(input("请输入电池下电电压(V): "))
                    battery_on_voltage = float(input("请输入电池上电电压(V): "))
                    llvd1_off_voltage = float(input("请输入LLVD1下电电压(V): "))
                    llvd1_on_voltage = float(input("请输入LLVD1上电电压(V): "))
                    llvd2_off_voltage = float(input("请输入LLVD2下电电压(V): "))
                    llvd2_on_voltage = float(input("请输入LLVD2上电电压(V): "))
                    llvd3_off_voltage = float(input("请输入LLVD3下电电压(V): "))
                    llvd3_on_voltage = float(input("请输入LLVD3上电电压(V): "))
                    llvd4_off_voltage = float(input("请输入LLVD4下电电压(V): "))
                    llvd4_on_voltage = float(input("请输入LLVD4上电电压(V): "))
                    battery_capacity = float(input("请输入每组电池额定容量(Ah): "))
                    battery_test_stop_voltage = float(input("请输入电池测试终止电压(V): "))
                    battery_temp_coeff = float(input("请输入电池组温补系数(mV/°C): "))
                    battery_temp_center = float(input("请输入电池温补中心点(°C): "))
                    float_to_equalize_coeff = float(input("请输入浮充转均充系数(C10): "))
                    equalize_to_float_coeff = float(input("请输入均充转浮充系数(C10): "))
                    llvd1_off_time = float(input("请输入LLVD1下电时间(min): "))
                    llvd2_off_time = float(input("请输入LLVD2下电时间(min): "))
                    llvd3_off_time = float(input("请输入LLVD3下电时间(min): "))
                    llvd4_off_time = float(input("请输入LLVD4下电时间(min): "))
                    load_off_mode = int(input("请输入负载下电模式(0-电压模式, 1-时间模式): "))
                    self.protocol.send_command('setDcConfigParams', {
                            'dcOverVoltage': over_volt,
                            'dcUnderVoltage': under_volt,
                            'timeEqualizeChargeEnable': time_equalize_enable,
                            'timeEqualizeDuration': time_equalize_duration,
                            'timeEqualizeInterval': time_equalize_interval,
                            'batteryGroupNumber': battery_group_number,
                            'batteryOverTemp': battery_over_temp,
                            'batteryUnderTemp': battery_under_temp,
                            'envOverTemp': env_over_temp,
                            'envUnderTemp': env_under_temp,
                            'envOverHumidity': env_over_humidity,
                            'batteryChargeCurrentLimit': battery_charge_current_limit,
                            'floatVoltage': float_voltage,
                            'equalizeVoltage': equalize_voltage,
                            'batteryOffVoltage': battery_off_voltage,
                            'batteryOnVoltage': battery_on_voltage,
                            'llvd1OffVoltage': llvd1_off_voltage,
                            'llvd1OnVoltage': llvd1_on_voltage,
                            'llvd2OffVoltage': llvd2_off_voltage,
                            'llvd2OnVoltage': llvd2_on_voltage,
                            'llvd3OffVoltage': llvd3_off_voltage,
                            'llvd3OnVoltage': llvd3_on_voltage,
                            'llvd4OffVoltage': llvd4_off_voltage,
                            'llvd4OnVoltage': llvd4_on_voltage,
                            'batteryCapacity': battery_capacity,
                            'batteryTestStopVoltage': battery_test_stop_voltage,
                            'batteryTempCoeff': battery_temp_coeff,
                            'batteryTempCenter': battery_temp_center,
                            'floatToEqualizeCoeff': float_to_equalize_coeff,
                            'equalizeToFloatCoeff': equalize_to_float_coeff,
                            'llvd1OffTime': llvd1_off_time,
                            'llvd2OffTime': llvd2_off_time,
                            'llvd3OffTime': llvd3_off_time,
                            'llvd4OffTime': llvd4_off_time,
                            'loadOffMode': load_off_mode
                        }
                    )
                    print("直流配置参数设置成功")
                except ValueError:
                    print("无效的参数值")
            elif choice == '18':  # 系统控制命令
                print("系统控制命令:")
                print("1. 系统复位")
                print("2. LLVD复位")
                print("3. 负载开关合闸")
                print("4. 负载开关分闸")
                print("5. 电池开关合闸")
                print("6. 电池开关分闸")
                try:
                    cmd = int(input("请选择控制命令编号: "))
                    if cmd == 1:
                        self.protocol.send_command('systemControl', {'controlType': 0xE1})
                    elif cmd == 2:
                        self.protocol.send_command('systemControl', {'controlType': 0xE2})
                    elif cmd == 3:
                        self.protocol.send_command('systemControl', {'controlType': 0xE6})
                    elif cmd == 4:
                        self.protocol.send_command('systemControl', {'controlType': 0xE5})
                    elif cmd == 5:
                        self.protocol.send_command('systemControl', {'controlType': 0xEE})
                    elif cmd == 6:
                        self.protocol.send_command('systemControl', {'controlType': 0xED})
                    else:
                        print("无效的命令编号")
                except ValueError:
                    print("无效的命令编号")
            else:
                print("无效的选项")

            print()
                
if __name__ == '__main__':
    device_addr = 1
    default_port = '/dev/ttyS2'
    port = input(f'请输入串口号(默认为{default_port}): ')
    if not port:
        port = default_port
    logging.info(f"Using serial port: {port}")
    monitor = MU4801Monitor(1, '/dev/ttyS2')
    monitor.run()