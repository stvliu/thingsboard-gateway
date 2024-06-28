from mu4801_protocol import MU4801Protocol
import logging
import datetime

# 导入相关的数据类
from mu4801_models import *

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class MU4801Monitor:
    def __init__(self, device_addr, port):
        self._log = logging.getLogger(self.__class__.__name__)
        self._protocol = MU4801Protocol(device_addr, port)
        self._protocol.connect()


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
        print("11. 读取整流模块开关输入状态")
        print("12. 读取整流模块告警")
        print("13. 整流模块远程开关机")
        print("14. 读取直流数据")
        print("15. 读取直流告警状态")
        print("16. 读取直流配置参数")
        print("17. 设置直流配置参数")
        print("18. 修改系统控制状态")
        print("19. 读取系统控制状态")
        print("20. 后台告警音使能控制")
        print("21. 读取节能参数")
        print("22. 设置节能参数")
        print("23. 系统控制命令")
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
                dt = self._protocol.send_command('getDateTime')
                print(f"当前时间: {dt}")
            elif choice == '2':  # 设置当前时间
                print("设置当前时间:")
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
                    print("时间设置成功")
                except ValueError:
                    print("无效的日期时间格式")
            elif choice == '3':  # 读取协议版本号
                print("读取协议版本号:")
                version = self._protocol.send_command('getProtocolVersion')
                print(f"协议版本号: {version.version}")
            elif choice == '4':  # 读取设备地址
                print("读取设备地址:")
                addr = self._protocol.send_command('getDeviceAddress')
                print(f"设备地址: {addr.address}")
            elif choice == '5':  # 读取厂家信息
                print("读取厂家信息:")
                info = self._protocol.send_command('getManufacturerInfo')
                print(f"设备名称: {info.collector_name}")
                print(f"软件版本: {info.software_version}")
                print(f"制造商: {info.manufacturer}")
            elif choice == '6':  # 读取交流数据
                print("读取交流数据:")
                ac_data = self._protocol.send_command('getAcAnalogData')
                print(f"A相电压: {ac_data.input_voltage_ab_a:.2f} V")
                print(f"B相电压: {ac_data.input_voltage_bc_b:.2f} V")
                print(f"C相电压: {ac_data.input_voltage_ca_c:.2f} V")
                print(f"频率: {ac_data.input_frequency:.2f} Hz")
            elif choice == '7':  # 读取交流告警状态
                print("读取交流告警状态:")
                ac_alarm = self._protocol.send_command('getAcAlarmStatus')
                print(f"A相电压状态: {ac_alarm.input_voltage_ab_a_status.name}")
                print(f"B相电压状态: {ac_alarm.input_voltage_bc_b_status.name}")
                print(f"C相电压状态: {ac_alarm.input_voltage_ca_c_status.name}")
                print(f"交流防雷器状态: {ac_alarm.ac_arrester_status.name}")
                print(f"交流第一路输入状态: {ac_alarm.ac_power_status.name}")
            elif choice == '8':  # 读取交流配置参数
                print("读取交流配置参数:")
                ac_config = self._protocol.send_command('getAcConfigParams')
                print(f"交流过压值: {ac_config.ac_over_voltage:.2f} V")
                print(f"交流欠压值: {ac_config.ac_under_voltage:.2f} V")
            elif choice == '9':  # 设置交流配置参数
                print("设置交流配置参数:")
                try:
                    over_volt = float(input("请输入交流过压值(V): "))
                    under_volt = float(input("请输入交流欠压值(V): "))
                    self._protocol.send_command('setAcConfigParams', AcConfigParams(
                        ac_over_voltage=over_volt,
                        ac_under_voltage=under_volt
                    ))
                    print("交流配置参数设置成功")
                except ValueError:
                    print("无效的参数值")
            elif choice == '10':  # 读取整流模块数据
                print("读取整流模块数据:")
                rect_data = self._protocol.send_command('getRectAnalogData')
                print(f"输出电压: {rect_data.output_voltage:.2f} V")
                for i, current in enumerate(rect_data.module_currents, 1):
                    print(f"模块{i}电流: {current:.2f} A")
            elif choice == '11':  # 读取整流模块开关输入状态
                print("读取整流模块开关输入状态:")
                rect_status = self._protocol.send_command('getRectSwitchStatus')
                for i, run_status in enumerate(rect_status.module_run_status, 1):
                    print(f"模块{i}运行状态: {'开机' if run_status == SwitchStatus.ON else '关机'}")
                for i, limit_status in enumerate(rect_status.module_limit_status, 1):
                    print(f"模块{i}限流状态: {'限流' if limit_status == SwitchStatus.ON else '不限流'}")
            elif choice == '12':  # 读取整流模块告警
                print("读取整流模块告警:")
                rect_alarm = self._protocol.send_command('getRectAlarmStatus')
                for i, failure_status in enumerate(rect_alarm.module_failure_status, 1):
                    print(f"模块{i}故障状态: {'故障' if failure_status == AlarmStatus.ALARM else '正常'}")
                for i, comm_status in enumerate(rect_alarm.module_comm_failure_status, 1):
                    print(f"模块{i}通讯状态: {'通讯故障' if comm_status == AlarmStatus.ALARM else '正常'}")
                for i, protection_status in enumerate(rect_alarm.module_protection_status, 1):
                    print(f"模块{i}保护状态: {'保护' if protection_status == AlarmStatus.ALARM else '正常'}")
                for i, fan_status in enumerate(rect_alarm.module_fan_status, 1):
                    print(f"模块{i}风扇状态: {'故障' if fan_status == AlarmStatus.ALARM else '正常'}")
            elif choice == '13':  # 整流模块远程开关机
                module_id = int(input("请输入要控制的模块ID(1~n): "))
                ctrl_type = input("请输入控制类型(0-开机, 1-关机): ")
                if ctrl_type == '0':
                    ctrl_code = RectModuleControlType.ON
                elif ctrl_type == '1':
                    ctrl_code = RectModuleControlType.OFF
                else:
                    print("无效的控制类型")
                    continue

                self._protocol.send_command('controlRectModule', ControlRectModule(
                    module_id=module_id,
                    control_type=ctrl_code
                ))
                print(f"整流模块{module_id}{'开机' if ctrl_code == RectModuleControlType.ON else '关机'}成功")
            elif choice == '14':  # 获取直流配电模拟量(浮点数)
                print("获取直流配电模拟量(浮点数):")
                dc_data = self._protocol.send_command('getDcAnalogData')
                print(f"电池电压: {dc_data.dc_voltage:.2f} V")
                print(f"负载总电流: {dc_data.total_load_current:.2f} A")
                print(f"电池组1电流: {dc_data.battery_group_1_current:.2f} A")
                print(f"负载分路1电流: {dc_data.load_branch_1_current:.2f} A")
                print(f"负载分路2电流: {dc_data.load_branch_2_current:.2f} A")
                print(f"负载分路3电流: {dc_data.load_branch_3_current:.2f} A")
                print(f"负载分路4电流: {dc_data.load_branch_4_current:.2f} A")
                print(f"电池总电流: {dc_data.battery_total_current:.2f} A")
                print(f"电池组1容量: {dc_data.battery_group_1_capacity:.2f} %")
                print(f"电池组1电压: {dc_data.battery_group_1_voltage:.2f} V")
                print(f"电池组1中点电压: {dc_data.battery_group_1_mid_voltage:.2f} V")
                print(f"电池组2中点电压: {dc_data.battery_group_2_mid_voltage:.2f} V")
                print(f"电池组3中点电压: {dc_data.battery_group_3_mid_voltage:.2f} V")
                print(f"电池组4中点电压: {dc_data.battery_group_4_mid_voltage:.2f} V")
                print(f"电池组1温度: {dc_data.battery_group_1_temperature:.2f} °C")
                print(f"环境温度1: {dc_data.env_temp_1:.2f} °C")
                print(f"环境温度2: {dc_data.env_temp_2:.2f} °C")
                print(f"环境湿度1: {dc_data.env_humidity_1:.2f} %RH")
                print(f"总负载功率: {dc_data.total_load_power:.2f} W")
                print(f"负载功率1: {dc_data.load_power_1:.2f} W")
                print(f"负载功率2: {dc_data.load_power_2:.2f} W")
                print(f"负载功率3: {dc_data.load_power_3:.2f} W")
                print(f"负载功率4: {dc_data.load_power_4:.2f} W")
                print(f"总负载电量: {dc_data.total_load_energy:.2f} kWh")
                print(f"负载电量1: {dc_data.load_energy_1:.2f} kWh")
                print(f"负载电量2: {dc_data.load_energy_2:.2f} kWh")
                print(f"负载电量3: {dc_data.load_energy_3:.2f} kWh")
                print(f"负载电量4: {dc_data.load_energy_4:.2f} kWh")
            elif choice == '15':  # 读取直流告警状态
                print("读取直流告警状态:")
                dc_alarm = self._protocol.send_command('getDcAlarmStatus')
                print(f"直流电压状态: {dc_alarm.dc_voltage_status.name}")
                print(f"直流防雷器状态: {dc_alarm.dc_arrester_status.name}")
                print(f"负载熔丝状态: {dc_alarm.load_fuse_status.name}")
                print(f"电池组1熔丝状态: {dc_alarm.battery_group_1_fuse_status.name}")
                print(f"电池组2熔丝状态: {dc_alarm.battery_group_2_fuse_status.name}")
                print(f"电池组3熔丝状态: {dc_alarm.battery_group_3_fuse_status.name}")
                print(f"电池组4熔丝状态: {dc_alarm.battery_group_4_fuse_status.name}")
                print(f"BLVD下电状态: {dc_alarm.blvd_status.name}")
                print(f"LLVD1下电状态: {dc_alarm.llvd1_status.name}")
                print(f"LLVD2下电状态: {dc_alarm.llvd2_status.name}")
                print(f"LLVD3下电状态: {dc_alarm.llvd3_status.name}")
                print(f"LLVD4下电状态: {dc_alarm.llvd4_status.name}")
                print(f"电池温度状态: {dc_alarm.battery_temp_status.name}")
                print(f"电池温度传感器1状态: {dc_alarm.battery_temp_sensor_1_status.name}")
                print(f"环境温度状态: {dc_alarm.env_temp_status.name}")
                print(f"环境温度传感器1状态: {dc_alarm.env_temp_sensor_1_status.name}")
                print(f"环境温度传感器2状态: {dc_alarm.env_temp_sensor_2_status.name}")
                print(f"环境湿度状态: {dc_alarm.env_humidity_status.name}")
                print(f"环境湿度传感器1状态: {dc_alarm.env_humidity_sensor_1_status.name}")
                print(f"门磁状态: {dc_alarm.door_status.name}")
                print(f"水浸状态: {dc_alarm.water_status.name}")
                print(f"烟雾状态: {dc_alarm.smoke_status.name}")
                print(f"数字输入1状态: {dc_alarm.digital_input_status_1.name}")
                print(f"数字输入2状态: {dc_alarm.digital_input_status_2.name}")
                print(f"数字输入3状态: {dc_alarm.digital_input_status_3.name}")
                print(f"数字输入4状态: {dc_alarm.digital_input_status_4.name}")
                print(f"数字输入5状态: {dc_alarm.digital_input_status_5.name}")
                print(f"数字输入6状态: {dc_alarm.digital_input_status_6.name}")
            elif choice == '16':  # 读取直流配置参数
                print("读取直流配置参数:")
                dc_config = self._protocol.send_command('getDcConfigParams')
                print(f"直流过压值: {dc_config.dc_over_voltage:.2f} V")
                print(f"直流欠压值: {dc_config.dc_under_voltage:.2f} V")
                print(f"定时均充使能: {'使能' if dc_config.time_equalize_charge_enable == EnableStatus.ENABLE else '禁止'}")
                print(f"定时均充时间: {dc_config.time_equalize_duration} 小时")
                print(f"定时均充间隔: {dc_config.time_equalize_interval} 天")
                print(f"电池组数: {dc_config.battery_group_number}")
                print(f"电池过温告警点: {dc_config.battery_over_temp:.2f} °C")
                print(f"电池欠温告警点: {dc_config.battery_under_temp:.2f} °C")
                print(f"环境过温告警点: {dc_config.env_over_temp:.2f} °C")
                print(f"环境欠温告警点: {dc_config.env_under_temp:.2f} °C")
                print(f"环境过湿告警点: {dc_config.env_over_humidity:.2f} %RH")
                print(f"电池充电限流点: {dc_config.battery_charge_current_limit:.2f} C10")
                print(f"浮充电压: {dc_config.float_voltage:.2f} V")
                print(f"均充电压: {dc_config.equalize_voltage:.2f} V")
                print(f"电池下电电压: {dc_config.battery_off_voltage:.2f} V")
                print(f"电池上电电压: {dc_config.battery_on_voltage:.2f} V")
                print(f"LLVD1下电电压: {dc_config.llvd1_off_voltage:.2f} V")
                print(f"LLVD1上电电压: {dc_config.llvd1_on_voltage:.2f} V")
                print(f"LLVD2下电电压: {dc_config.llvd2_off_voltage:.2f} V")
                print(f"LLVD2上电电压: {dc_config.llvd2_on_voltage:.2f} V")
                print(f"LLVD3下电电压: {dc_config.llvd3_off_voltage:.2f} V")
                print(f"LLVD3上电电压: {dc_config.llvd3_on_voltage:.2f} V")
                print(f"LLVD4下电电压: {dc_config.llvd4_off_voltage:.2f} V")
                print(f"LLVD4上电电压: {dc_config.llvd4_on_voltage:.2f} V")
                print(f"每组电池额定容量: {dc_config.battery_capacity:.2f} Ah")
                print(f"电池测试终止电压: {dc_config.battery_test_stop_voltage:.2f} V")
                print(f"电池组温补系数: {dc_config.battery_temp_coeff:.2f} mV/°C")
                print(f"电池温补中心点: {dc_config.battery_temp_center:.2f} °C")
                print(f"浮充转均充系数: {dc_config.float_to_equalize_coeff:.2f}")
                print(f"均充转浮充系数: {dc_config.equalize_to_float_coeff:.2f}")
                print(f"LLVD1下电时间: {dc_config.llvd1_off_time:.2f} min")
                print(f"LLVD2下电时间: {dc_config.llvd2_off_time:.2f} min")
                print(f"LLVD3下电时间: {dc_config.llvd3_off_time:.2f} min")
                print(f"LLVD4下电时间: {dc_config.llvd4_off_time:.2f} min")
                print(f"负载下电模式: {'电压模式' if dc_config.load_off_mode == LoadOffMode.VOLTAGE else '时间模式'}")
            elif choice == '17':  # 设置直流配置参数
                print("设置直流配置参数:")
                try:
                    over_volt = float(input("请输入直流过压值(V): "))
                    under_volt = float(input("请输入直流欠压值(V): "))
                    time_equalize_enable = EnableStatus(int(input("请输入定时均充使能(0-禁止, 1-使能): ")))
                    time_equalize_duration = int(input("请输入定时均充时间(小时): "))
                    time_equalize_interval = int(input("请输入定时均充间隔(天): "))
                    battery_group_number = int(input("请输入电池组数: "))
                    battery_over_temp = float(input("请输入电池过温告警点(°C): "))
                    battery_under_temp = float(input("请输入电池欠温告警点(°C): "))
                    env_over_temp = float(input("请输入环境过温告警点(°C): "))
                    env_under_temp = float(input("请输入环境欠温告警点(°C): "))
                    env_over_humidity = float(input("请输入环境过湿告警点(%RH): "))
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
                    float_to_equalize_coeff = float(input("请输入浮充转均充系数: "))
                    equalize_to_float_coeff = float(input("请输入均充转浮充系数: "))
                    llvd1_off_time = float(input("请输入LLVD1下电时间(min): "))
                    llvd2_off_time = float(input("请输入LLVD2下电时间(min): "))
                    llvd3_off_time = float(input("请输入LLVD3下电时间(min): "))
                    llvd4_off_time = float(input("请输入LLVD4下电时间(min): "))
                    load_off_mode = LoadOffMode(int(input("请输入负载下电模式(0-电压模式, 1-时间模式): ")))
                    self._protocol.send_command('setDcConfigParams', DcConfigParams(
                        dc_over_voltage=over_volt,
                        dc_under_voltage=under_volt,
                        time_equalize_charge_enable=time_equalize_enable,
                        time_equalize_duration=time_equalize_duration,
                        time_equalize_interval=time_equalize_interval,
                        battery_group_number=battery_group_number,
                        battery_over_temp=battery_over_temp,
                        battery_under_temp=battery_under_temp,
                        env_over_temp=env_over_temp,
                        env_under_temp=env_under_temp,
                        env_over_humidity=env_over_humidity,
                        battery_charge_current_limit=battery_charge_current_limit,
                        float_voltage=float_voltage,
                        equalize_voltage=equalize_voltage,
                        battery_off_voltage=battery_off_voltage,
                        battery_on_voltage=battery_on_voltage,
                        llvd1_off_voltage=llvd1_off_voltage,
                        llvd1_on_voltage=llvd1_on_voltage,
                        llvd2_off_voltage=llvd2_off_voltage,
                        llvd2_on_voltage=llvd2_on_voltage,
                        llvd3_off_voltage=llvd3_off_voltage,
                        llvd3_on_voltage=llvd3_on_voltage,
                        llvd4_off_voltage=llvd4_off_voltage,
                        llvd4_on_voltage=llvd4_on_voltage,
                        battery_capacity=battery_capacity,
                        battery_test_stop_voltage=battery_test_stop_voltage,
                        battery_temp_coeff=battery_temp_coeff,
                        battery_temp_center=battery_temp_center,
                        float_to_equalize_coeff=float_to_equalize_coeff,
                        equalize_to_float_coeff=equalize_to_float_coeff,
                        llvd1_off_time=llvd1_off_time,
                        llvd2_off_time=llvd2_off_time,
                        llvd3_off_time=llvd3_off_time,
                        llvd4_off_time=llvd4_off_time,
                        load_off_mode=load_off_mode
                    ))
                    print("直流配置参数设置成功")
                except ValueError:
                    print("无效的参数值")
            elif choice == '18':  # 修改系统控制状态
                print("修改系统控制状态:")
                print("1. 自动控制状态")
                print("2. 手动控制状态")
                try:
                    state = int(input("请选择新的控制状态编号: "))
                    if state == 1:
                        self._protocol.send_command('setSystemControlState', SystemControlState(
                            state=SystemControlStateModel.AUTO
                        ))
                    elif state == 2:
                        self._protocol.send_command('setSystemControlState', SystemControlState(
                            state=SystemControlStateModel.MANUAL
                        ))
                    else:
                        print("无效的状态编号")
                except ValueError:
                    print("无效的状态编号")
            elif choice == '19':  # 读取系统控制状态
                print("读取系统控制状态:")
                state = self._protocol.send_command('getSystemControlState')
                print(f"当前系统控制状态: {state.state.name}")
            elif choice == '20':  # 后台告警音使能控制
                print("后台告警音使能控制:")
                print("1. 禁止告警音")
                print("2. 使能告警音")
                try:
                    enable = int(input("请选择告警音使能状态编号: "))
                    if enable == 1:
                        self._protocol.send_command('systemControl', AlarmSoundEnable(
                            enable=EnableStatus.DISABLE
                        ))
                    elif enable == 2:
                        self._protocol.send_command('systemControl', AlarmSoundEnable(
                            enable=EnableStatus.ENABLE
                        ))
                    else:
                        print("无效的使能状态编号")
                except ValueError:
                    print("无效的使能状态编号")
            elif choice == '21':  # 读取节能参数
                print("读取节能参数:")
                energy_params = self._protocol.send_command('getEnergyParams')
                print(f"节能允许: {'使能' if energy_params.energy_saving == EnableStatus.ENABLE else '禁止'}")
                print(f"最小工作模块数: {energy_params.min_working_modules}")
                print(f"模块循环开关周期: {energy_params.module_switch_cycle} 天")
                print(f"模块最佳效率点: {energy_params.module_best_efficiency_point} %")
                print(f"模块冗余点: {energy_params.module_redundancy_point} %")
            elif choice == '22':  # 设置节能参数
                print("设置节能参数:")
                try:
                    energy_saving = EnableStatus(int(input("请输入节能允许(0-禁止, 1-使能): ")))
                    min_working_modules = int(input("请输入最小工作模块数: "))
                    module_switch_cycle = int(input("请输入模块循环开关周期(天): "))
                    module_best_efficiency_point = int(input("请输入模块最佳效率点(%): "))
                    module_redundancy_point = int(input("请输入模块冗余点(%): "))
                    self._protocol.send_command('setEnergyParams', EnergyParams(
                        energy_saving=energy_saving,
                        min_working_modules=min_working_modules,
                        module_switch_cycle=module_switch_cycle,
                        module_best_efficiency_point=module_best_efficiency_point,
                        module_redundancy_point=module_redundancy_point
                    ))
                    print("节能参数设置成功")
                except ValueError:
                    print("无效的参数值")
            elif choice == '23':  # 系统控制命令
                print("系统控制命令:")
                print("1. 系统复位")
                print("2. 负载1下电")
                print("3. 负载1上电")
                print("4. 负载2下电")
                print("5. 负载2上电")
                print("6. 负载3下电")
                print("7. 负载3上电")
                print("8. 负载4下电")
                print("9. 负载4上电")
                print("10. 电池下电")
                print("11. 电池上电")
                try:
                    cmd = int(input("请选择控制命令编号: "))
                    if cmd == 1:
                        self._protocol.send_command('systemControl', SystemControl(
                            control_type=SystemControlType.RESET
                        ))
                    elif cmd == 2:
                        self._protocol.send_command('systemControl', SystemControl(
                            control_type=SystemControlType.LOAD1_OFF
                        ))
                    elif cmd == 3:
                        self._protocol.send_command('systemControl', SystemControl(
                            control_type=SystemControlType.LOAD1_ON
                        ))
                    elif cmd == 4:
                        self._protocol.send_command('systemControl', SystemControl(
                            control_type=SystemControlType.LOAD2_OFF
                        ))
                    elif cmd == 5:
                        self._protocol.send_command('systemControl', SystemControl(
                            control_type=SystemControlType.LOAD2_ON
                        ))
                    elif cmd == 6:
                        self._protocol.send_command('systemControl', SystemControl(
                            control_type=SystemControlType.LOAD3_OFF
                        ))
                    elif cmd == 7:
                        self._protocol.send_command('systemControl', SystemControl(
                            control_type=SystemControlType.LOAD3_ON
                        ))
                    elif cmd == 8:
                        self._protocol.send_command('systemControl', SystemControl(
                            control_type=SystemControlType.LOAD4_OFF
                        ))
                    elif cmd == 9:
                        self._protocol.send_command('systemControl', SystemControl(
                            control_type=SystemControlType.LOAD4_ON
                        ))
                    elif cmd == 10:
                        self._protocol.send_command('systemControl', SystemControl(
                            control_type=SystemControlType.BATTERY_OFF
                        ))
                    elif cmd == 11:
                        self._protocol.send_command('systemControl', SystemControl(
                            control_type=SystemControlType.BATTERY_ON
                        ))
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
    monitor = MU4801Monitor(device_addr, port)
    monitor.run()