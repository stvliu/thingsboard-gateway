from mu4801_protocol import MU4801Protocol
import logging
import random
import time
import datetime

# 导入相关的数据类
from mu4801_models import *

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class MU4801Simulator:
    def __init__(self, device_addr, port):
        self._log = logging.getLogger(self.__class__.__name__)
        self._protocol = MU4801Protocol(device_addr, port)
        self._protocol.connect()

        self.device_info = {
            'collector_name': 'MU4801A',
            'software_version': SoftwareVersion(1,11),
            'manufacturer': 'Virtual Inc.'
        }

        # 使用对应的数据类初始化模拟数据
        self.ac_data = AcAnalogData(
            input_voltage_ab_a=220.0,
            input_voltage_bc_b=220.0,
            input_voltage_ca_c=220.0,
            input_frequency=50.0
        )

        self.ac_alarm_status = AcAlarmStatus(
            input_voltage_ab_a_status=VoltageStatus.NORMAL,
            input_voltage_bc_b_status=VoltageStatus.NORMAL,
            input_voltage_ca_c_status=VoltageStatus.NORMAL,
            ac_arrester_status=AcArresterStatus.NORMAL,
            ac_power_status=AcPowerStatus.NORMAL
        )

        self.ac_config_params = AcConfigParams(
            ac_over_voltage=260.0,
            ac_under_voltage=180.0
        )

        self.rect_data = RectAnalogData(
            output_voltage=53.5,
            module_count=3,
            module_currents=[30.0, 30.0, 30.0],
            module_current_limit=[105.0, 105.0, 105.0],
            module_voltage=[53.5, 53.5, 53.5],
            module_temperature=[25.0, 25.0, 25.0],
            module_input_voltage_ab=[380.0, 380.0, 380.0]
        )

        self.rect_status = RectSwitchStatus(
            module_count=3,
            module_run_status=[SwitchStatus.ON, SwitchStatus.ON, SwitchStatus.ON],
            module_limit_status=[SwitchStatus.OFF, SwitchStatus.OFF, SwitchStatus.OFF]
        )


        self.rect_alarm_status = RectAlarmStatus(
            module_count=3,
            module_failure_status=[AlarmStatus.NORMAL, AlarmStatus.NORMAL, AlarmStatus.NORMAL],
            module_comm_failure_status=[AlarmStatus.NORMAL, AlarmStatus.NORMAL, AlarmStatus.NORMAL],
            module_protection_status=[AlarmStatus.NORMAL, AlarmStatus.NORMAL, AlarmStatus.NORMAL],
            module_fan_status=[AlarmStatus.NORMAL, AlarmStatus.NORMAL, AlarmStatus.NORMAL]
        )

        self.dc_data = DcAnalogData(
            dc_voltage=53.5,
            total_load_current=120.0,
            battery_group_1_current=40.0,
            load_branch_1_current=30.0,
            load_branch_2_current=30.0,
            load_branch_3_current=30.0,
            load_branch_4_current=30.0,
            battery_total_current=40.0,
            battery_group_1_capacity=100.0,
            battery_group_1_voltage=53.5,
            battery_group_1_mid_voltage=26.7,
            battery_group_2_mid_voltage=26.7,
            battery_group_3_mid_voltage=26.7,
            battery_group_4_mid_voltage=26.7,
            battery_group_1_temperature=25.0,
            env_temp_1=25.0,
            env_temp_2=25.0,
            env_humidity_1=50.0,
            total_load_power=6000.0,
            load_power_1=1500.0,
            load_power_2=1500.0,
            load_power_3=1500.0,
            load_power_4=1500.0,
            total_load_energy=100.0,
            load_energy_1=25.0,
            load_energy_2=25.0,
            load_energy_3=25.0,
            load_energy_4=25.0
        )

        self.dc_alarm_status = DcAlarmStatus(
            dc_voltage_status=VoltageStatus.NORMAL,
            dc_arrester_status=AlarmStatus.NORMAL,
            load_fuse_status=AlarmStatus.NORMAL,
            battery_group_1_fuse_status=AlarmStatus.NORMAL,
            battery_group_2_fuse_status=AlarmStatus.NORMAL,
            battery_group_3_fuse_status=AlarmStatus.NORMAL,
            battery_group_4_fuse_status=AlarmStatus.NORMAL,
            blvd_status=LVDStatus.NORMAL,
            llvd1_status=LVDStatus.NORMAL,
            llvd2_status=LVDStatus.NORMAL,
            llvd3_status=LVDStatus.NORMAL,
            llvd4_status=LVDStatus.NORMAL,
            battery_temp_status=TempStatus.NORMAL,
            battery_temp_sensor_1_status=SensorStatus.NORMAL,
            env_temp_status=TempStatus.NORMAL,
            env_temp_sensor_1_status=SensorStatus.NORMAL,
            env_temp_sensor_2_status=SensorStatus.NORMAL,
            env_humidity_status=AlarmStatus.NORMAL,
            env_humidity_sensor_1_status=SensorStatus.NORMAL,
            door_status=AlarmStatus.NORMAL,
            water_status=AlarmStatus.NORMAL,
            smoke_status=AlarmStatus.NORMAL,
            digital_input_status_1=AlarmStatus.NORMAL,
            digital_input_status_2=AlarmStatus.NORMAL,
            digital_input_status_3=AlarmStatus.NORMAL,
            digital_input_status_4=AlarmStatus.NORMAL,
            digital_input_status_5=AlarmStatus.NORMAL,
            digital_input_status_6=AlarmStatus.NORMAL,
        )

        self.dc_config_params = DcConfigParams(
            dc_over_voltage=57.6,
            dc_under_voltage=43.2,
            time_equalize_charge_enable=EnableStatus.DISABLE,
            time_equalize_duration=8,
            time_equalize_interval=180,
            battery_group_number=1,
            battery_over_temp=50.0,
            battery_under_temp=0.0,
            env_over_temp=45.0,
            env_under_temp=5.0,
            env_over_humidity=90.0,
            battery_charge_current_limit=0.5,
            float_voltage=53.5,
            equalize_voltage=56.5,
            battery_off_voltage=43.2,
            battery_on_voltage=48.0,
            llvd1_off_voltage=47.5,
            llvd1_on_voltage=48.5,
            llvd2_off_voltage=47.5,
            llvd2_on_voltage=48.5,
            llvd3_off_voltage=47.5,
            llvd3_on_voltage=48.5,
            llvd4_off_voltage=47.5,
            llvd4_on_voltage=48.5,
            battery_capacity=200,
            battery_test_stop_voltage=44.8,
            battery_temp_coeff=72.0,
            battery_temp_center=25.0,
            float_to_equalize_coeff=0.5,
            equalize_to_float_coeff=1.0,
            llvd1_off_time=5.0,
            llvd2_off_time=5.0,
            llvd3_off_time=5.0,
            llvd4_off_time=5.0,
            load_off_mode=LoadOffMode.VOLTAGE
        )

        self.energy_params = EnergyParams(
            energy_saving=EnableStatus.ENABLE,
            min_working_modules=2,
            module_switch_cycle=180,
            module_best_efficiency_point=90,
            module_redundancy_point=100
        )

        self.system_control_state_model = SystemControlStateModel.AUTO
        self.alarm_sound_enable = EnableStatus.ENABLE

    def handle_get_time(self):
        now = datetime.datetime.now()
        return DateTime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=now.hour,
            minute=now.minute,
            second=now.second
        )

    def handle_set_time(self, request: DateTime):
        self._log.info(f"Time set to: {request.year}-{request.month:02d}-{request.day:02d} {request.hour:02d}:{request.minute:02d}:{request.second:02d}")

    def handle_get_protocol_version(self):
        return ProtocolVersion(version='V2.1')

    def handle_get_device_address(self):
        return DeviceAddress(address=self._protocol.device_addr)

    def handle_get_manufacturer_info(self):
        return ManufacturerInfo(**self.device_info)

    def handle_get_ac_analog_data(self):
        # 模拟一些随机波动
        self.ac_data.input_voltage_ab_a = 220.0 + random.uniform(-5.0, 5.0)
        self.ac_data.input_voltage_bc_b = 220.0 + random.uniform(-5.0, 5.0)
        self.ac_data.input_voltage_ca_c = 220.0 + random.uniform(-5.0, 5.0)
        self.ac_data.input_frequency = 50.0 + random.uniform(-0.5, 0.5)
        return self.ac_data

    def handle_get_ac_alarm_status(self):
        return self.ac_alarm_status

    def handle_get_ac_config_params(self):
        return self.ac_config_params

    def handle_set_ac_config_params(self, request: AcConfigParams):
        self.ac_config_params = request
        self._log.info(f"AC config updated: {request.to_dict()}")

    def handle_get_rect_analog_data(self):
        # 模拟一些随机波动
        self.rect_data.output_voltage = 53.5 + random.uniform(-0.5, 0.5)
        for i in range(self.rect_data.module_count):
            self.rect_data.module_currents[i] = 30.0 + random.uniform(-2.0, 2.0)
            self.rect_data.module_voltage[i] = 53.5 + random.uniform(-0.5, 0.5)
            self.rect_data.module_temperature[i] = 25.0 + random.uniform(-2.0, 2.0)
        return self.rect_data

    def handle_get_rect_status(self):
        return self.rect_status

    def handle_get_rect_alarm_status(self):
        return self.rect_alarm_status

    def handle_control_rect_module(self, request: ControlRectModule):
        module_id = request.module_id
        control_type = request.control_type
        if 0 <= module_id < self.rect_status.module_count:
            if control_type == RectModuleControlType.ON:
                self.rect_status.module_run_status[module_id] = SwitchStatus.ON
            elif control_type == RectModuleControlType.OFF:
                self.rect_status.module_run_status[module_id] = SwitchStatus.OFF
            self._log.info(f"Rectifier module {module_id} turned {'on' if control_type == RectModuleControlType.ON else 'off'}")
        else:
            self._log.warning(f"Invalid module ID: {module_id}")

    def handle_get_dc_analog_data(self):
        # 模拟一些随机波动
        self.dc_data.dc_voltage = 53.5 + random.uniform(-0.5, 0.5)
        self.dc_data.total_load_current = 120.0 + random.uniform(-5.0, 5.0)
        self.dc_data.battery_group_1_current = 40.0 + random.uniform(-2.0, 2.0)
        self.dc_data.load_branch_1_current = 30.0 + random.uniform(-1.0, 1.0)
        self.dc_data.load_branch_2_current = 30.0 + random.uniform(-1.0, 1.0)
        self.dc_data.load_branch_3_current = 30.0 + random.uniform(-1.0, 1.0)
        self.dc_data.load_branch_4_current = 30.0 + random.uniform(-1.0, 1.0)
        return self.dc_data

    def handle_get_dc_alarm_status(self):
        return self.dc_alarm_status

    def handle_get_dc_config_params(self):
        return self.dc_config_params

    def handle_set_dc_config_params(self, request: DcConfigParams):
        self.dc_config_params = request
        self._log.info(f"DC config updated: {request.to_dict()}")

    def handle_set_system_control_state(self, request: SystemControlState):
        self.system_control_state_model = request.state
        self._log.info(f"System control state set to: {self.system_control_state_model.name}")

    def handle_get_system_control_state(self):
        return SystemControlState(state=self.system_control_state_model)

    def handle_set_alarm_sound_enable(self, request: AlarmSoundEnable):
        self.alarm_sound_enable = request.enable
        self._log.info(f"Alarm sound {'enabled' if request.enable == EnableStatus.ENABLE else 'disabled'}")

    def handle_get_energy_params(self):
        return self.energy_params

    def handle_set_energy_params(self, request: EnergyParams):
        self.energy_params = request
        self._log.info(f"Energy params updated: {request.to_dict()}")

    def handle_system_control(self, request: SystemControl):
        control_type = request.control_type
        if control_type == SystemControlType.RESET:
            self._log.info("System reset")
        elif control_type == SystemControlType.LOAD1_OFF:
            self._log.info("Load 1 off")
        elif control_type == SystemControlType.LOAD1_ON:
            self._log.info("Load 1 on")
        elif control_type == SystemControlType.LOAD2_OFF:
            self._log.info("Load 2 off")
        elif control_type == SystemControlType.LOAD2_ON:
            self._log.info("Load 2 on")
        elif control_type == SystemControlType.LOAD3_OFF:
            self._log.info("Load 3 off")
        elif control_type == SystemControlType.LOAD3_ON:
            self._log.info("Load 3 on")
        elif control_type == SystemControlType.LOAD4_OFF:
            self._log.info("Load 4 off")
        elif control_type == SystemControlType.LOAD4_ON:
            self._log.info("Load 4 on")
        elif control_type == SystemControlType.BATTERY_OFF:
            self._log.info("Battery off")
        elif control_type == SystemControlType.BATTERY_ON:
            self._log.info("Battery on")

    def run(self):
        while True:
            try:
                command, command_data = self._protocol.receive_command()
                if not command:
                    continue

                response_data = None

                if command.cid1 == '0x40':
                    if command.cid2 == '0x4D':  # 获取当前时间
                        response_data = self.handle_get_time()
                    elif command.cid2 == '0x4E':  # 设置当前时间
                        self.handle_set_time(command_data)
                    elif command.cid2 == '0x4F':  # 获取协议版本号
                        response_data = self.handle_get_protocol_version()
                    elif command.cid2 == '0x50':  # 获取本机地址
                        response_data = self.handle_get_device_address()
                    elif command.cid2 == '0x51':  # 获取厂家信息
                        response_data = self.handle_get_manufacturer_info()
                    elif command.cid2 == '0x41':  # 获取交流模拟量
                        response_data = self.handle_get_ac_analog_data()
                    elif command.cid2 == '0x44':  # 获取交流告警状态
                        response_data = self.handle_get_ac_alarm_status()
                    elif command.cid2 == '0x46':  # 获取交流配电参数
                        response_data = self.handle_get_ac_config_params()
                    elif command.cid2 == '0x48':  # 设置交流配电参数
                        self.handle_set_ac_config_params(command_data)
                    elif command.cid2 == '0x84':  # 后台告警音使能控制
                        self.handle_set_alarm_sound_enable(command_data)

                elif command.cid1 == '0x41':
                    if command.cid2 == '0x41':  # 获取整流模块模拟量
                        response_data = self.handle_get_rect_analog_data()
                    elif command.cid2 == '0x43':  # 获取整流模块开关输入状态
                        response_data = self.handle_get_rect_status()
                    elif command.cid2 == '0x44':  # 获取整流模块告警状态
                        response_data = self.handle_get_rect_alarm_status()
                    elif command.cid2 == '0x45':  # 遥控整流模块
                        self.handle_control_rect_module(command_data)

                elif command.cid1 == '0x42':
                    if command.cid2 == '0x41':  # 获取直流配电模拟量
                        response_data = self.handle_get_dc_analog_data()
                    elif command.cid2 == '0x44':  # 获取直流告警状态
                        response_data = self.handle_get_dc_alarm_status()
                    elif command.cid2 == '0x46':  # 获取直流配电参数
                        response_data = self.handle_get_dc_config_params()
                    elif command.cid2 == '0x48':  # 设置直流配电参数
                        self.handle_set_dc_config_params(command_data)
                    elif command.cid2 == '0x80':  # 修改系统控制状态
                        self.handle_set_system_control_state(command_data)
                    elif command.cid2 == '0x81':  # 读取系统控制状态
                        response_data = self.handle_get_system_control_state()
                    elif command.cid2 == '0x90':  # 读取节能参数
                        response_data = self.handle_get_energy_params()
                    elif command.cid2 == '0x91':  # 设置节能参数
                        self.handle_set_energy_params(command_data)
                    elif command.cid2 == '0x92':  # 系统控制
                        self.handle_system_control(command_data)

                self._protocol.send_response(command, '0x00', response_data)

            except Exception as e:
                self._log.error(f"An error occurred: {e}", exc_info=True)

if __name__ == '__main__':
    device_addr = 1
    default_port = '/dev/ttyS3'
    port = input(f'请输入串口号(默认为{default_port}): ')
    if not port:
        port = default_port
    logging.info(f"Using serial port: {port}")
    simulator = MU4801Simulator(device_addr, port)
    simulator.run()