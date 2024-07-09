import logging
import random
import datetime
import time
import threading

from hdcac_protocol import HdcAcProtocol
from hdcac_models import *

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class HdcAcSimulator:
    def __init__(self, device_addr, port):
        self._log = logging.getLogger(self.__class__.__name__)
        self._protocol = HdcAcProtocol(device_addr, port)
        self._protocol.connect()

        self.device_info = {
            'device_name': 'AC',
            'software_version': SoftwareVersion(1, 10),
            'manufacturer': 'HAYDEN SUZHOU'
        }

        self.ac_analog_data = AcAnalogData(
            cabinet_temp=250,  # 25.0°C
            supply_temp=240,  # 24.0°C
            voltage=220,
            current=0
        )

        self.ac_run_status = AcRunStatus(
            air_conditioner=SwitchStatus.ON,
            indoor_fan=SwitchStatus.ON,
            outdoor_fan=SwitchStatus.ON,
            heater=SwitchStatus.OFF
        )

        self.ac_alarm_status = AcAlarmStatus(
            compressor_alarm=AlarmStatus.NORMAL,
            high_temp=AlarmStatus.NORMAL,
            low_temp=AlarmStatus.NORMAL,
            heater_alarm=AlarmStatus.NORMAL,
            sensor_fault=AlarmStatus.NORMAL,
            over_voltage=AlarmStatus.NORMAL,
            under_voltage=AlarmStatus.NORMAL,
        )

        self.ac_config_params = AcConfigParams(
            start_temp=270,  # 27.0°C
            temp_hysteresis=10,  # 1.0°C
            heater_start_temp=180,  # 18.0°C
            heater_hysteresis=10,  # 1.0°C
            high_temp_alarm=350,  # 35.0°C
            low_temp_alarm=50  # 5.0°C
        )

        self.target_temp = 16.0
        self.ambient_temp = random.uniform(30, 36)
        self.cooling_efficiency = 1.0
        self.heating_efficiency = 1.0

        self.simulation_interval = 5  # 每5秒更新一次状态
        self.simulation_timer = None
        self.simulation_running = False
        self.last_update_time = time.time()

        self.mode_change_time = None
        self.mode_start_time = None
        self.auto_mode_timer = None
        self.AUTO_MODE_DELAY = 600  # 10 minutes in seconds

        self.compressor_startup_time = 30  # 压缩机启动时间（秒）
        self.max_efficiency = 1.0
        self.min_efficiency = 0.3
        self.efficiency_ramp_time = 300  # 达到最大效率所需时间（秒）

        self.fault_check_interval = 3600  # 1小时检查一次故障
        self.fault_duration = 1800  # 故障持续时间（30分钟）
        self.fault_probability = 0.1  # 每次检查时发生新故障的概率
        self.faults = {
            'compressor': {'status': False, 'timer': None},
            'fan': {'status': False, 'timer': None},
            'sensor': {'status': False, 'timer': None},
            'refrigerant_leak': {'status': False, 'timer': None},
            'heater': {'status': False, 'timer': None}
        }
        self.fault_check_timer = None

    def start_simulation(self):
        self.simulation_running = True
        self.simulate_ac_state()

    def stop_simulation(self):
        self.simulation_running = False
        if self.simulation_timer:
            self.simulation_timer.cancel()

    def start_fault_check(self):
        self.check_faults()
        self.fault_check_timer = threading.Timer(self.fault_check_interval, self.start_fault_check)
        self.fault_check_timer.start()

    def stop_fault_check(self):
        if self.fault_check_timer:
            self.fault_check_timer.cancel()

    def simulate_ac_state(self):
        if not self.simulation_running:
            return

        current_time = time.time()
        time_delta = current_time - self.last_update_time
        self.last_update_time = current_time

        self.update_ambient_temperature(time_delta)
        # self.check_auto_mode()
        self.simulate_temperature_change(time_delta)
        self.simulate_voltage_current(time_delta)
        self.update_alarm_status()

        self.simulation_timer = threading.Timer(self.simulation_interval, self.simulate_ac_state)
        self.simulation_timer.start()

    def update_ambient_temperature(self, time_delta):
        temp_change = random.uniform(-0.1, 0.1) * time_delta
        self.ambient_temp += temp_change
        self.ambient_temp = max(27, min(self.ambient_temp, 36))

        hour = datetime.datetime.now().hour
        if 6 <= hour < 18:  # 白天
            self.ambient_temp += 0.05 * time_delta
        else:  # 夜晚
            self.ambient_temp -= 0.05 * time_delta

    def check_auto_mode(self):
        cabinet_temp = self.ac_analog_data.cabinet_temp / 10
        if self.ac_run_status.air_conditioner == SwitchStatus.OFF:
            if cabinet_temp >= self.ac_config_params.start_temp / 10:
                self.start_cooling()
            elif cabinet_temp <= self.ac_config_params.heater_start_temp / 10:
                self.start_heating()
        elif self.is_cooling_mode():
            if cabinet_temp <= (self.ac_config_params.start_temp - self.ac_config_params.temp_hysteresis) / 10:
                self.stop_cooling()
            elif cabinet_temp > self.ac_config_params.start_temp / 10:
                self.start_cooling()  # 重新启动制冷
        elif self.is_heating_mode():
            if cabinet_temp >= (self.ac_config_params.heater_start_temp + self.ac_config_params.heater_hysteresis) / 10:
                self.stop_heating()
            elif cabinet_temp < self.ac_config_params.heater_start_temp / 10:
                self.start_heating()  # 重新启动制热

    def is_cooling_mode(self):
        return (self.ac_run_status.air_conditioner == SwitchStatus.ON and
                self.ac_run_status.outdoor_fan == SwitchStatus.ON and
                self.ac_run_status.heater == SwitchStatus.OFF)

    def is_heating_mode(self):
        return (self.ac_run_status.air_conditioner == SwitchStatus.ON and
                self.ac_run_status.heater == SwitchStatus.ON)

    def start_cooling(self):
        self.ac_run_status.air_conditioner = SwitchStatus.ON
        self.ac_run_status.indoor_fan = SwitchStatus.ON
        self.ac_run_status.outdoor_fan = SwitchStatus.ON
        self.ac_run_status.heater = SwitchStatus.OFF
        self.mode_change_time = time.time()
        self.mode_start_time = time.time()
        self._log.info("Cooling mode started")
        # self.set_auto_mode_timer()

    def stop_cooling(self):
        self.ac_run_status.air_conditioner = SwitchStatus.OFF
        self.ac_run_status.indoor_fan = SwitchStatus.OFF
        self.ac_run_status.outdoor_fan = SwitchStatus.OFF
        self.ac_run_status.heater = SwitchStatus.OFF
        self.mode_change_time = None
        self.mode_start_time = None
        # if self.auto_mode_timer:
        #     self.auto_mode_timer.cancel()
        self._log.info("Cooling mode stopped")

    def start_heating(self):
        self.ac_run_status.air_conditioner = SwitchStatus.ON
        self.ac_run_status.indoor_fan = SwitchStatus.ON
        self.ac_run_status.outdoor_fan = SwitchStatus.OFF
        self.ac_run_status.heater = SwitchStatus.ON
        self.mode_change_time = time.time()
        self.mode_start_time = time.time()
        self._log.info("Heating mode started")
        # self.set_auto_mode_timer()

    def stop_heating(self):
        self.ac_run_status.air_conditioner = SwitchStatus.OFF
        self.ac_run_status.indoor_fan = SwitchStatus.OFF
        self.ac_run_status.outdoor_fan = SwitchStatus.OFF
        self.ac_run_status.heater = SwitchStatus.OFF
        self.mode_change_time = None
        self.mode_start_time = None
        # if self.auto_mode_timer:
        #     self.auto_mode_timer.cancel()
        self._log.info("Heating mode stopped")

    def set_auto_mode_timer(self):
        if self.auto_mode_timer:
            self.auto_mode_timer.cancel()
        self.auto_mode_timer = threading.Timer(self.AUTO_MODE_DELAY, self.switch_to_auto_mode)
        self.auto_mode_timer.start()

    def switch_to_auto_mode(self):
        self._log.info("Switching to auto mode after 10 minutes")
        self.check_auto_mode()

    def simulate_temperature_change(self, time_delta):
        if self.ac_run_status.air_conditioner == SwitchStatus.ON:
            if self.is_cooling_mode():
                self.simulate_cooling(time_delta)
            elif self.is_heating_mode():
                self.simulate_heating(time_delta)
        else:
            self.simulate_natural_temperature_change(time_delta)

        self.ac_analog_data.cabinet_temp = max(-500, min(self.ac_analog_data.cabinet_temp, 500))

    def simulate_cooling(self, time_delta):
        if self.mode_change_time is None:
            self.mode_change_time = time.time()

        cooling_duration = time.time() - self.mode_change_time
        current_efficiency = self.calculate_current_efficiency(cooling_duration)

        temp_diff = self.ac_analog_data.cabinet_temp / 10 - self.target_temp
        cooling_rate = 0.2 * current_efficiency * time_delta

        if not self.faults['refrigerant_leak']['status'] and not self.faults['compressor']['status']:
            temp_change = min(abs(temp_diff), cooling_rate) * (-1 if temp_diff > 0 else 1)
            self.ac_analog_data.cabinet_temp += int(temp_change * 10)
        else:
            # 制冷剂泄漏或压缩机故障时，温度变化很小或不变
            self.ac_analog_data.cabinet_temp += int(random.uniform(-0.1, 0.2) * 10)

        # 更新送风温度。如果风扇正常工作，送风温度会比机柜温度低，但不会低于 2°C（因为温度单位是 0.1°C，所以这里用 20）。如果风扇故障，送风温度就等于机柜温度。
        if not self.faults['fan']['status']:
            self.ac_analog_data.supply_temp = max(20, self.ac_analog_data.cabinet_temp - int(20 * current_efficiency))
        else:
            self.ac_analog_data.supply_temp = self.ac_analog_data.cabinet_temp

    def simulate_heating(self, time_delta):
        if self.mode_change_time is None:
            self.mode_change_time = time.time()

        heating_duration = time.time() - self.mode_change_time
        current_efficiency = self.calculate_current_efficiency(heating_duration)

        temp_diff = self.target_temp - self.ac_analog_data.cabinet_temp / 10
        heating_rate = 0.2 * current_efficiency * time_delta

        if not self.faults['heater']['status']:
            temp_change = min(abs(temp_diff), heating_rate) * (1 if temp_diff > 0 else -1)
            self.ac_analog_data.cabinet_temp += int(temp_change * 10)
        else:
            # 加热器故障时，温度变化很小或不变
            self.ac_analog_data.cabinet_temp += int(random.uniform(-0.1, 0.1) * 10)

        # 更新送风温度。如果风扇正常工作，送风温度会比机柜温度低，但不会低于 2°C（因为温度单位是 0.1°C，所以这里用 20）。如果风扇故障，送风温度就等于机柜温度。
        if not self.faults['fan']['status']:
            self.ac_analog_data.supply_temp = max(20, self.ac_analog_data.cabinet_temp - int(20 * current_efficiency))
        else:
            self.ac_analog_data.supply_temp = self.ac_analog_data.cabinet_temp

    def simulate_natural_temperature_change(self, time_delta):
        # 热惯性系数 (0-1之间，越大表示温度变化越慢)
        thermal_inertia = 0.95

        # 隔热性能 (0-1之间，越大表示隔热性能越好)
        insulation_factor = 0.8

        # 计算目标温度（考虑隔热性能）
        target_temp = self.ambient_temp * (1 - insulation_factor) + (
                    self.ac_analog_data.cabinet_temp / 10) * insulation_factor

        # 计算温度差
        temp_diff = target_temp - self.ac_analog_data.cabinet_temp / 10

        # 计算温度变化，考虑热惯性
        temp_change = temp_diff * (1 - thermal_inertia) * time_delta

        # 更新温度
        self.ac_analog_data.cabinet_temp += int(temp_change * 10)
        self.ac_analog_data.supply_temp = self.ac_analog_data.cabinet_temp

    def calculate_current_efficiency(self, duration):
        current_efficiency = min(
            self.max_efficiency,
            self.min_efficiency + (self.max_efficiency - self.min_efficiency) *
            (duration / self.efficiency_ramp_time)
        )

        # 考虑环境温度的影响
        ambient_factor = max(0.5, min(1.5, (self.ambient_temp - 25) / 10 + 1))
        current_efficiency *= ambient_factor

        return current_efficiency

    def simulate_voltage_current(self, time_delta):
        if self.ac_run_status.air_conditioner == SwitchStatus.ON:
            self.ac_analog_data.voltage = 220 + random.randint(-2, 2)

            if self.mode_change_time and (time.time() - self.mode_change_time) < self.compressor_startup_time:
                # 压缩机启动时的高电流
                self.ac_analog_data.current = 40 + random.randint(0, 5)
            elif self.faults['compressor']['status']:
                self.ac_analog_data.current = 35 + random.randint(0, 5)  # 压缩机故障时电流异常高
            elif self.faults['refrigerant_leak']['status']:
                self.ac_analog_data.current = 15 + random.randint(0, 2)  # 制冷剂泄漏时电流较低
            elif self.is_cooling_mode() or self.is_heating_mode():
                self.ac_analog_data.current = 26 + random.randint(0, 4)
            else:
                self.ac_analog_data.current = 5 + random.randint(0, 1)  # 只有风扇运行
        else:
            self.ac_analog_data.voltage = 220 + random.randint(-1, 1)
            self.ac_analog_data.current = random.randint(0, 1)

    def update_alarm_status(self):
        cabinet_temp = self.ac_analog_data.cabinet_temp / 10
        self.ac_alarm_status.high_temp = AlarmStatus.ALARM if cabinet_temp > self.ac_config_params.high_temp_alarm / 10 else AlarmStatus.NORMAL
        self.ac_alarm_status.low_temp = AlarmStatus.ALARM if cabinet_temp < self.ac_config_params.low_temp_alarm / 10 else AlarmStatus.NORMAL

        self.ac_alarm_status.compressor_alarm = AlarmStatus.ALARM if self.faults['compressor'][
            'status'] else AlarmStatus.NORMAL
        self.ac_alarm_status.sensor_fault = AlarmStatus.ALARM if self.faults['sensor'][
            'status'] else AlarmStatus.NORMAL

        self.ac_alarm_status.over_voltage = AlarmStatus.ALARM if self.ac_analog_data.voltage > 240 else AlarmStatus.NORMAL
        self.ac_alarm_status.under_voltage = AlarmStatus.ALARM if self.ac_analog_data.voltage < 200 else AlarmStatus.NORMAL

        # 新增制冷/加热效果不佳的告警
        if (self.is_cooling_mode() and cabinet_temp > (
                self.ac_config_params.start_temp + self.ac_config_params.temp_hysteresis) / 10) or \
                (self.is_heating_mode() and cabinet_temp < (
                        self.ac_config_params.heater_start_temp - self.ac_config_params.heater_hysteresis) / 10):
            self.ac_alarm_status.compressor_alarm = AlarmStatus.ALARM

        self.ac_alarm_status.heater_alarm = AlarmStatus.ALARM if self.faults['heater'][
            'status'] else AlarmStatus.NORMAL

    def check_faults(self):
        self._log.info("Performing scheduled fault check")
        for fault in self.faults:
            if not self.faults[fault]['status']:  # 如果当前没有故障
                if random.random() < self.fault_probability:
                    self.set_fault(fault, True)

    def set_fault(self, fault, status):
        self.faults[fault]['status'] = status
        if status:
            self._log.warning(f"{fault.capitalize()} fault occurred.")
            # 设置故障自动恢复定时器
            self.faults[fault]['timer'] = threading.Timer(self.fault_duration, self.set_fault, args=[fault, False])
            self.faults[fault]['timer'].start()
        else:
            self._log.info(f"{fault.capitalize()} fault resolved.")
            if self.faults[fault]['timer']:
                self.faults[fault]['timer'].cancel()
                self.faults[fault]['timer'] = None
        self.update_fault_effects()

    def update_fault_effects(self):
        if self.faults['compressor']['status']:
            self.cooling_efficiency = 0.1
            self.heating_efficiency = 0.1
        elif self.faults['refrigerant_leak']['status']:
            self.cooling_efficiency = max(0.5, self.cooling_efficiency - 0.1)
            self.heating_efficiency = max(0.5, self.heating_efficiency - 0.1)
        elif self.faults['heater']['status']:
            self.heating_efficiency = 0.1
        else:
            self.cooling_efficiency = 1.0
            self.heating_efficiency = 1.0

        if self.faults['fan']['status']:
            self.ac_run_status.indoor_fan = SwitchStatus.OFF
            self.ac_run_status.outdoor_fan = SwitchStatus.OFF

        # 更新告警状态
        self.update_alarm_status()

    def handle_get_ac_analog_data(self):
        return self.ac_analog_data

    def handle_get_ac_run_status(self):
        return self.ac_run_status

    def handle_get_ac_alarm_status(self):
        return self.ac_alarm_status

    def handle_remote_control(self, request: RemoteControl):
        command = request.command
        if command == RemoteCommand.ON:
            self.ac_run_status.air_conditioner = SwitchStatus.ON
        elif command == RemoteCommand.OFF:
            self.stop_cooling()
            self.stop_heating()
        elif command == RemoteCommand.COOLING_ON:
            self.start_cooling()
        elif command == RemoteCommand.COOLING_OFF:
            self.stop_cooling()
        elif command == RemoteCommand.HEATING_ON:
            self.start_heating()
        elif command == RemoteCommand.HEATING_OFF:
            self.stop_heating()
        self._log.info(f"AC remote controlled: {command.name}")

    def handle_get_ac_config_params(self):
        return self.ac_config_params

    def handle_set_ac_config_params(self, request: ConfigParam):
        param_type = request.param_type
        param_value = request.param_value
        if param_type == ConfigParamType.AC_START_TEMP:
            self.ac_config_params.start_temp = param_value
        elif param_type == ConfigParamType.AC_TEMP_HYSTERESIS:
            self.ac_config_params.temp_hysteresis = param_value
        elif param_type == ConfigParamType.HEAT_START_TEMP:
            self.ac_config_params.heater_start_temp = param_value
        elif param_type == ConfigParamType.HEAT_HYSTERESIS:
            self.ac_config_params.heater_hysteresis = param_value
        elif param_type == ConfigParamType.HIGH_TEMP_ALARM:
            self.ac_config_params.high_temp_alarm = param_value
        elif param_type == ConfigParamType.LOW_TEMP_ALARM:
            self.ac_config_params.low_temp_alarm = param_value
        self._log.info(f"AC config updated: {param_type.name} set to {param_value}")

    def handle_get_date_time(self):
        now = datetime.datetime.now()
        return DateTime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=now.hour,
            minute=now.minute,
            second=now.second
        )

    def handle_set_date_time(self, request: DateTime):
        self._log.info(f"AC datetime set to: {request.datetime}")

    def handle_set_device_address(self, request: DeviceAddress):
        self._log.info(f"AC address set to: {request.address}")

    def handle_get_manufacturer_info(self):
        return ManufacturerInfo(
            device_name=self.device_info['device_name'],
            software_version=self.device_info['software_version'],
            manufacturer=self.device_info['manufacturer']
        )

    def run(self):
        self.start_simulation()
        self.start_fault_check()
        try:
            while True:
                command, command_data = self._protocol.receive_command()
                if not command:
                    continue

                response_data = None

                if command.key == 'getAcAnalogData':
                    response_data = self.handle_get_ac_analog_data()
                elif command.key == 'getAcRunStatus':
                    response_data = self.handle_get_ac_run_status()
                elif command.key == 'getAcAlarmStatus':
                    response_data = self.handle_get_ac_alarm_status()
                elif command.key == 'remoteControl':
                    self.handle_remote_control(command_data)
                elif command.key == 'getAcConfigParams':
                    response_data = self.handle_get_ac_config_params()
                elif command.key == 'setAcConfigParams':
                    self.handle_set_ac_config_params(command_data)
                elif command.key == 'getDateTime':
                    response_data = self.handle_get_date_time()
                elif command.key == 'setDateTime':
                    self.handle_set_date_time(command_data)
                elif command.key == 'setDeviceAddress':
                    self.handle_set_device_address(command_data)
                elif command.key == 'getManufacturerInfo':
                    response_data = self.handle_get_manufacturer_info()

                self._protocol.send_response(command, '0x00', response_data)

        except Exception as e:
            self._log.error(f"An error occurred: {e}", exc_info=True)
        finally:
            self.stop_simulation()
            self.stop_fault_check()

if __name__ == '__main__':
    device_addr = 1
    default_port = '/dev/ttyS5'
    port = default_port
    logging.info(f"Using serial port: {port}")
    simulator = HdcAcSimulator(device_addr, port)
    simulator.run()