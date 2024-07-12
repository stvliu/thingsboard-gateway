import logging
import random
import datetime
import time
import threading

from hdcac_protocol import HdcAcProtocol
from hdcac_models import *

# 配置日志记录
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# 定义常量来替换魔术数字
SIMULATION_INTERVAL = 5  # 模拟间隔时间(秒)
AUTO_MODE_DELAY = 600  # 自动模式延迟时间(秒)
COMPRESSOR_STARTUP_TIME = 30  # 压缩机启动时间(秒)
EFFICIENCY_RAMP_TIME = 300  # 达到最大效率所需时间(秒)
FAULT_CHECK_INTERVAL = 3600  # 故障检查间隔时间(秒)
FAULT_DURATION = 1800  # 故障持续时间(秒)
FAULT_PROBABILITY = 0.1  # 故障发生概率

# 温度相关常量
MIN_AMBIENT_TEMP = 27  # 最低环境温度(°C)
MAX_AMBIENT_TEMP = 36  # 最高环境温度(°C)
DAY_TEMP_CHANGE_RATE = 0.02  # 白天温度变化率(°C/秒)
NIGHT_TEMP_CHANGE_RATE = -0.02  # 夜晚温度变化率(°C/秒)
MIN_CABINET_TEMP = -20  # 最低机柜温度(°C)
MAX_CABINET_TEMP = 40  # 最高机柜温度(°C)
TEMP_SCALE = 10  # 温度缩放因子，用于将浮点温度转换为整数存储

# 电压和电流相关常量
NORMAL_VOLTAGE = 220  # 正常电压(V)
HIGH_VOLTAGE_THRESHOLD = 240  # 高电压阈值(V)
LOW_VOLTAGE_THRESHOLD = 200  # 低电压阈值(V)
MAX_STARTUP_CURRENT = 45  # 最大启动电流(A)
MIN_STARTUP_CURRENT = 40  # 最小启动电流(A)
MAX_NORMAL_CURRENT = 30  # 最大正常工作电流(A)
MIN_NORMAL_CURRENT = 26  # 最小正常工作电流(A)
MAX_FAULT_CURRENT = 40  # 最大故障电流(A)
MIN_FAULT_CURRENT = 35  # 最小故障电流(A)
MAX_LEAK_CURRENT = 17  # 最大泄漏电流(A)
MIN_LEAK_CURRENT = 15  # 最小泄漏电流(A)
MAX_FAN_CURRENT = 6  # 最大风扇电流(A)
MIN_FAN_CURRENT = 5  # 最小风扇电流(A)

# 效率相关常量
MAX_EFFICIENCY = 1.0  # 最大效率
MIN_EFFICIENCY = 0.3  # 最小效率
COOLING_RATE_FACTOR = 0.2  # 制冷速率因子

# 其他常量
RANDOM_TEMP_CHANGE_MIN = -0.1  # 最小随机温度变化(°C)
RANDOM_TEMP_CHANGE_MAX = 0.1  # 最大随机温度变化(°C)
VOLTAGE_FLUCTUATION = 2  # 电压波动范围(V)
DEFAULT_TARGET_TEMP = 18.0  # 默认目标温度(°C)


class HdcAcSimulator:
    def __init__(self, device_addr, port):
        """
        初始化空调模拟器

        :param device_addr: 设备地址
        :param port: 串口端口
        """
        self._log = logging.getLogger(self.__class__.__name__)
        self._protocol = HdcAcProtocol(device_addr, port)
        self._protocol.connect()

        # 初始化设备信息
        self.device_info = {
            'device_name': 'AC',
            'software_version': SoftwareVersion(1, 10),
            'manufacturer': 'HAYDEN SUZHOU'
        }

        # 初始化空调模拟量数据
        self.ac_analog_data = AcAnalogData(
            cabinet_temp=25 * TEMP_SCALE,  # 25.0°C
            supply_temp=24 * TEMP_SCALE,  # 24.0°C
            voltage=NORMAL_VOLTAGE,
            current=0
        )

        # 初始化空调运行状态
        self.ac_run_status = AcRunStatus(
            air_conditioner=SwitchStatus.ON,
            indoor_fan=SwitchStatus.ON,
            outdoor_fan=SwitchStatus.ON,
            heater=SwitchStatus.OFF
        )

        # 初始化空调告警状态
        self.ac_alarm_status = AcAlarmStatus(
            compressor_alarm=AlarmStatus.NORMAL,
            high_temp=AlarmStatus.NORMAL,
            low_temp=AlarmStatus.NORMAL,
            heater_alarm=AlarmStatus.NORMAL,
            sensor_fault=AlarmStatus.NORMAL,
            over_voltage=AlarmStatus.NORMAL,
            under_voltage=AlarmStatus.NORMAL,
        )

        # 初始化空调配置参数
        self.ac_config_params = AcConfigParams(
            start_temp=27 * TEMP_SCALE,  # 27.0°C
            temp_hysteresis=1 * TEMP_SCALE,  # 1.0°C
            heater_start_temp=18 * TEMP_SCALE,  # 18.0°C
            heater_hysteresis=1 * TEMP_SCALE,  # 1.0°C
            high_temp_alarm=35 * TEMP_SCALE,  # 35.0°C
            low_temp_alarm=5 * TEMP_SCALE  # 5.0°C
        )

        self.target_temp = DEFAULT_TARGET_TEMP
        self.ambient_temp = random.uniform(MIN_AMBIENT_TEMP, MAX_AMBIENT_TEMP)
        self.cooling_efficiency = MAX_EFFICIENCY
        self.heating_efficiency = MAX_EFFICIENCY

        self.simulation_interval = SIMULATION_INTERVAL
        self.simulation_timer = None
        self.simulation_running = False
        self.last_update_time = time.time()

        self.mode_change_time = None
        self.mode_start_time = None
        self.auto_mode_timer = None
        self.AUTO_MODE_DELAY = AUTO_MODE_DELAY

        self.compressor_startup_time = COMPRESSOR_STARTUP_TIME
        self.max_efficiency = MAX_EFFICIENCY
        self.min_efficiency = MIN_EFFICIENCY
        self.efficiency_ramp_time = EFFICIENCY_RAMP_TIME

        self.fault_check_interval = FAULT_CHECK_INTERVAL
        self.fault_duration = FAULT_DURATION
        self.fault_probability = FAULT_PROBABILITY
        self.faults = {
            'compressor': {'status': False, 'timer': None},
            'fan': {'status': False, 'timer': None},
            'sensor': {'status': False, 'timer': None},
            'refrigerant_leak': {'status': False, 'timer': None},
            'heater': {'status': False, 'timer': None}
        }
        self.fault_check_timer = None

    def start_simulation(self):
        """
        启动模拟器
        """
        self.simulation_running = True
        self.simulate_ac_state()

    def stop_simulation(self):
        """
        停止模拟器
        """
        self.simulation_running = False
        if self.simulation_timer:
            self.simulation_timer.cancel()

    def start_fault_check(self):
        """
        开始故障检查
        """
        self.check_faults()
        self.fault_check_timer = threading.Timer(self.fault_check_interval, self.start_fault_check)
        self.fault_check_timer.start()

    def stop_fault_check(self):
        """
        停止故障检查
        """
        if self.fault_check_timer:
            self.fault_check_timer.cancel()

    def simulate_ac_state(self):
        """
        模拟空调状态
        """
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
        """
        更新环境温度

        :param time_delta: 时间间隔
        """
        temp_change = random.uniform(RANDOM_TEMP_CHANGE_MIN, RANDOM_TEMP_CHANGE_MAX) * time_delta
        self.ambient_temp += temp_change
        self.ambient_temp = max(MIN_AMBIENT_TEMP, min(self.ambient_temp, MAX_AMBIENT_TEMP))

        hour = datetime.datetime.now().hour
        if 6 <= hour < 18:  # 白天
            self.ambient_temp += DAY_TEMP_CHANGE_RATE * time_delta
        else:  # 夜晚
            self.ambient_temp += NIGHT_TEMP_CHANGE_RATE * time_delta

    def check_auto_mode(self):
        """
        检查并执行自动模式
        """
        cabinet_temp = self.ac_analog_data.cabinet_temp / TEMP_SCALE
        if self.ac_run_status.air_conditioner == SwitchStatus.OFF:
            if cabinet_temp >= self.ac_config_params.start_temp / TEMP_SCALE:
                self.start_cooling()
            elif cabinet_temp <= self.ac_config_params.heater_start_temp / TEMP_SCALE:
                self.start_heating()
        elif self.is_cooling_mode():
            if cabinet_temp <= (self.ac_config_params.start_temp - self.ac_config_params.temp_hysteresis) / TEMP_SCALE:
                self.stop_cooling()
            elif cabinet_temp > self.ac_config_params.start_temp / TEMP_SCALE:
                self.start_cooling()  # 重新启动制冷
        elif self.is_heating_mode():
            if cabinet_temp >= (
                    self.ac_config_params.heater_start_temp + self.ac_config_params.heater_hysteresis) / TEMP_SCALE:
                self.stop_heating()
            elif cabinet_temp < self.ac_config_params.heater_start_temp / TEMP_SCALE:
                self.start_heating()  # 重新启动制热

    def is_cooling_mode(self):
        """
        判断是否为制冷模式
        """
        return (self.ac_run_status.air_conditioner == SwitchStatus.ON and
                self.ac_run_status.outdoor_fan == SwitchStatus.ON and
                self.ac_run_status.heater == SwitchStatus.OFF)

    def is_heating_mode(self):
        """
        判断是否为制热模式
        """
        return (self.ac_run_status.air_conditioner == SwitchStatus.ON and
                self.ac_run_status.heater == SwitchStatus.ON)

    def start_cooling(self):
        """
        启动制冷模式
        """
        self.ac_run_status.air_conditioner = SwitchStatus.ON
        self.ac_run_status.indoor_fan = SwitchStatus.ON
        self.ac_run_status.outdoor_fan = SwitchStatus.ON
        self.ac_run_status.heater = SwitchStatus.OFF
        self.mode_change_time = time.time()
        self.mode_start_time = time.time()
        # self.set_auto_mode_timer()
        self._log.info("制冷模式启动")

    def stop_cooling(self):
        """
        停止制冷模式
        """
        self.ac_run_status.air_conditioner = SwitchStatus.OFF
        self.ac_run_status.indoor_fan = SwitchStatus.OFF
        self.ac_run_status.outdoor_fan = SwitchStatus.OFF
        self.ac_run_status.heater = SwitchStatus.OFF
        self.mode_change_time = None
        self.mode_start_time = None
        # if self.auto_mode_timer:
        #     self.auto_mode_timer.cancel()
        self._log.info("制冷模式停止")

    def start_heating(self):
        """
        启动制热模式
        """
        self.ac_run_status.air_conditioner = SwitchStatus.ON
        self.ac_run_status.indoor_fan = SwitchStatus.ON
        self.ac_run_status.outdoor_fan = SwitchStatus.OFF
        self.ac_run_status.heater = SwitchStatus.ON
        self.mode_change_time = time.time()
        self.mode_start_time = time.time()
        # self.set_auto_mode_timer()
        self._log.info("制热模式启动")

    def stop_heating(self):
        """
        停止制热模式
        """
        self.ac_run_status.air_conditioner = SwitchStatus.OFF
        self.ac_run_status.indoor_fan = SwitchStatus.OFF
        self.ac_run_status.outdoor_fan = SwitchStatus.OFF
        self.ac_run_status.heater = SwitchStatus.OFF
        self.mode_change_time = None
        self.mode_start_time = None
        # if self.auto_mode_timer:
        #     self.auto_mode_timer.cancel()
        self._log.info("制热模式停止")

    def set_auto_mode_timer(self):
        """
        设置自动模式定时器
        """
        if self.auto_mode_timer:
            self.auto_mode_timer.cancel()
        self.auto_mode_timer = threading.Timer(self.AUTO_MODE_DELAY, self.switch_to_auto_mode)
        self.auto_mode_timer.start()

    def switch_to_auto_mode(self):
        """
        切换到自动模式
        """
        self._log.info("10分钟后切换到自动模式")
        # self.check_auto_mode()

    def simulate_temperature_change(self, time_delta):
        """
        模拟温度变化

        :param time_delta: 时间间隔
        """
        if self.ac_run_status.air_conditioner == SwitchStatus.ON:
            if self.is_cooling_mode():
                self.simulate_cooling(time_delta)
            elif self.is_heating_mode():
                self.simulate_heating(time_delta)
        else:
            self.simulate_natural_temperature_change(time_delta)

        self.ac_analog_data.cabinet_temp = max(MIN_CABINET_TEMP * TEMP_SCALE,
                                               min(self.ac_analog_data.cabinet_temp, MAX_CABINET_TEMP * TEMP_SCALE))

    def simulate_cooling(self, time_delta):
        """
        模拟制冷过程

        :param time_delta: 时间间隔
        """
        if self.mode_change_time is None:
            self.mode_change_time = time.time()

        cooling_duration = time.time() - self.mode_change_time
        current_efficiency = self.calculate_current_efficiency(cooling_duration)

        temp_diff = self.ac_analog_data.cabinet_temp / TEMP_SCALE - self.target_temp
        cooling_rate = COOLING_RATE_FACTOR * current_efficiency * time_delta

        if not self.faults['refrigerant_leak']['status'] and not self.faults['compressor']['status']:
            temp_change = min(abs(temp_diff), cooling_rate) * (-1 if temp_diff > 0 else 1)
            self.ac_analog_data.cabinet_temp += int(temp_change * TEMP_SCALE)
        else:
            # 制冷剂泄漏或压缩机故障时，温度变化很小或不变
            self.ac_analog_data.cabinet_temp += int(
                random.uniform(RANDOM_TEMP_CHANGE_MIN, RANDOM_TEMP_CHANGE_MAX) * TEMP_SCALE)

        # 更新送风温度。如果风扇正常工作，送风温度会比机柜温度低，但不会低于 2°C。如果风扇故障，送风温度就等于机柜温度。
        if not self.faults['fan']['status']:
            self.ac_analog_data.supply_temp = max(2 * TEMP_SCALE, self.ac_analog_data.cabinet_temp - int(
                2 * TEMP_SCALE * current_efficiency))
        else:
            self.ac_analog_data.supply_temp = self.ac_analog_data.cabinet_temp

    def simulate_heating(self, time_delta):
        """
        模拟制热过程

        :param time_delta: 时间间隔
        """
        if self.mode_change_time is None:
            self.mode_change_time = time.time()

        heating_duration = time.time() - self.mode_change_time
        current_efficiency = self.calculate_current_efficiency(heating_duration)

        temp_diff = self.target_temp - self.ac_analog_data.cabinet_temp / TEMP_SCALE
        heating_rate = COOLING_RATE_FACTOR * current_efficiency * time_delta

        if not self.faults['heater']['status']:
            temp_change = min(abs(temp_diff), heating_rate) * (1 if temp_diff > 0 else -1)
            self.ac_analog_data.cabinet_temp += int(temp_change * TEMP_SCALE)
        else:
            # 加热器故障时，温度变化很小或不变
            self.ac_analog_data.cabinet_temp += int(
                random.uniform(RANDOM_TEMP_CHANGE_MIN, RANDOM_TEMP_CHANGE_MAX) * TEMP_SCALE)

        # 更新送风温度。如果风扇正常工作，送风温度会比机柜温度高。如果风扇故障，送风温度就等于机柜温度。
        if not self.faults['fan']['status']:
            self.ac_analog_data.supply_temp = self.ac_analog_data.cabinet_temp + int(
                2 * TEMP_SCALE * current_efficiency)
        else:
            self.ac_analog_data.supply_temp = self.ac_analog_data.cabinet_temp

    def simulate_natural_temperature_change(self, time_delta):
        """
        模拟自然温度变化

        :param time_delta: 时间间隔
        """
        # 热惯性系数 (0-1之间，越大表示温度变化越慢)
        thermal_inertia = 0.95

        # 隔热性能 (0-1之间，越大表示隔热性能越好)
        insulation_factor = 0.8

        # 计算目标温度（考虑隔热性能）
        target_temp = self.ambient_temp * (1 - insulation_factor) + (
                    self.ac_analog_data.cabinet_temp / TEMP_SCALE) * insulation_factor

        # 计算温度差
        temp_diff = target_temp - self.ac_analog_data.cabinet_temp / TEMP_SCALE

        # 计算温度变化，考虑热惯性
        temp_change = temp_diff * (1 - thermal_inertia) * time_delta

        # 更新温度
        self.ac_analog_data.cabinet_temp += int(temp_change * TEMP_SCALE)
        self.ac_analog_data.supply_temp = self.ac_analog_data.cabinet_temp

    def calculate_current_efficiency(self, duration):
        """
        计算当前效率

        :param duration: 运行持续时间
        :return: 当前效率
        """
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
        """
        模拟电压和电流变化

        :param time_delta: 时间间隔
        """
        if self.ac_run_status.air_conditioner == SwitchStatus.ON:
            self.ac_analog_data.voltage = NORMAL_VOLTAGE + random.randint(-VOLTAGE_FLUCTUATION, VOLTAGE_FLUCTUATION)

            if self.mode_change_time and (time.time() - self.mode_change_time) < self.compressor_startup_time:
                # 压缩机启动时的高电流
                self.ac_analog_data.current = random.randint(MIN_STARTUP_CURRENT, MAX_STARTUP_CURRENT)
            elif self.faults['compressor']['status']:
                self.ac_analog_data.current = random.randint(MIN_FAULT_CURRENT, MAX_FAULT_CURRENT)  # 压缩机故障时电流异常高
            elif self.faults['refrigerant_leak']['status']:
                self.ac_analog_data.current = random.randint(MIN_LEAK_CURRENT, MAX_LEAK_CURRENT)  # 制冷剂泄漏时电流较低
            elif self.is_cooling_mode() or self.is_heating_mode():
                self.ac_analog_data.current = random.randint(MIN_NORMAL_CURRENT, MAX_NORMAL_CURRENT)
            else:
                self.ac_analog_data.current = random.randint(MIN_FAN_CURRENT, MAX_FAN_CURRENT)  # 只有风扇运行
        else:
            self.ac_analog_data.voltage = NORMAL_VOLTAGE + random.randint(-1, 1)
            self.ac_analog_data.current = random.randint(0, 1)

    def update_alarm_status(self):
        """
        更新告警状态
        """
        cabinet_temp = self.ac_analog_data.cabinet_temp / TEMP_SCALE
        self.ac_alarm_status.high_temp = AlarmStatus.ALARM if cabinet_temp > self.ac_config_params.high_temp_alarm / TEMP_SCALE else AlarmStatus.NORMAL
        self.ac_alarm_status.low_temp = AlarmStatus.ALARM if cabinet_temp < self.ac_config_params.low_temp_alarm / TEMP_SCALE else AlarmStatus.NORMAL

        self.ac_alarm_status.compressor_alarm = AlarmStatus.ALARM if self.faults['compressor'][
            'status'] else AlarmStatus.NORMAL
        self.ac_alarm_status.sensor_fault = AlarmStatus.ALARM if self.faults['sensor']['status'] else AlarmStatus.NORMAL

        self.ac_alarm_status.over_voltage = AlarmStatus.ALARM if self.ac_analog_data.voltage > HIGH_VOLTAGE_THRESHOLD else AlarmStatus.NORMAL
        self.ac_alarm_status.under_voltage = AlarmStatus.ALARM if self.ac_analog_data.voltage < LOW_VOLTAGE_THRESHOLD else AlarmStatus.NORMAL

        # 新增制冷/加热效果不佳的告警
        if (self.is_cooling_mode() and cabinet_temp > (
                self.ac_config_params.start_temp + self.ac_config_params.temp_hysteresis) / TEMP_SCALE) or \
                (self.is_heating_mode() and cabinet_temp < (
                        self.ac_config_params.heater_start_temp - self.ac_config_params.heater_hysteresis) / TEMP_SCALE):
            self.ac_alarm_status.compressor_alarm = AlarmStatus.ALARM

        self.ac_alarm_status.heater_alarm = AlarmStatus.ALARM if self.faults['heater']['status'] else AlarmStatus.NORMAL

    def check_faults(self):
        """
        检查故障
        """
        self._log.info("执行定期故障检查")
        for fault in self.faults:
            if not self.faults[fault]['status']:  # 如果当前没有故障
                if random.random() < self.fault_probability:
                    self.set_fault(fault, True)

    def set_fault(self, fault, status):
        """
        设置故障状态

        :param fault: 故障类型
        :param status: 故障状态
        """
        self.faults[fault]['status'] = status
        if status:
            self._log.warning(f"{fault.capitalize()} 故障发生.")
            # 设置故障自动恢复定时器
            self.faults[fault]['timer'] = threading.Timer(self.fault_duration, self.set_fault, args=[fault, False])
            self.faults[fault]['timer'].start()
        else:
            self._log.info(f"{fault.capitalize()} 故障已解决.")
            if self.faults[fault]['timer']:
                self.faults[fault]['timer'].cancel()
                self.faults[fault]['timer'] = None
        self.update_fault_effects()

    def update_fault_effects(self):
        """
        更新故障影响
        """
        if self.faults['compressor']['status']:
            self.cooling_efficiency = 0.1
            self.heating_efficiency = 0.1
        elif self.faults['refrigerant_leak']['status']:
            self.cooling_efficiency = max(0.5, self.cooling_efficiency - 0.1)
            self.heating_efficiency = max(0.5, self.heating_efficiency - 0.1)
        elif self.faults['heater']['status']:
            self.heating_efficiency = 0.1
        else:
            self.cooling_efficiency = MAX_EFFICIENCY
            self.heating_efficiency = MAX_EFFICIENCY

        # if self.faults['fan']['status']:
        #     self.ac_run_status.indoor_fan = SwitchStatus.OFF
        #     self.ac_run_status.outdoor_fan = SwitchStatus.OFF

        # 更新告警状态
        self.update_alarm_status()

    def handle_get_ac_analog_data(self):
        """
        处理获取空调模拟量数据请求

        :return: 空调模拟量数据
        """
        return self.ac_analog_data

    def handle_get_ac_run_status(self):
        """
        处理获取空调运行状态请求

        :return: 空调运行状态
        """
        return self.ac_run_status

    def handle_get_ac_alarm_status(self):
        """
        处理获取空调告警状态请求

        :return: 空调告警状态
        """
        return self.ac_alarm_status

    def handle_remote_control(self, request: RemoteControl):
        """
        处理远程控制请求

        :param request: 远程控制请求
        """
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
        self._log.info(f"空调远程控制: {command.name}")

    def handle_get_ac_config_params(self):
        """
        处理获取空调配置参数请求

        :return: 空调配置参数
        """
        return self.ac_config_params

    def handle_set_ac_config_params(self, request: ConfigParam):
        """
        处理设置空调配置参数请求

        :param request: 配置参数请求
        """
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
        self._log.info(f"空调配置已更新: {param_type.name} 设置为 {param_value}")

    def handle_get_date_time(self):
        """
        处理获取日期时间请求

        :return: 当前日期时间
        """
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
        """
        处理设置日期时间请求

        :param request: 日期时间请求
        """
        self._log.info(f"空调日期时间设置为: {request.datetime}")

    def handle_set_device_address(self, request: DeviceAddress):
        """
        处理设置设备地址请求

        :param request: 设备地址请求
        """
        self._log.info(f"空调地址设置为: {request.address}")

    def handle_get_manufacturer_info(self):
        """
        处理获取制造商信息请求

        :return: 制造商信息
        """
        return ManufacturerInfo(
            device_name=self.device_info['device_name'],
            software_version=self.device_info['software_version'],
            manufacturer=self.device_info['manufacturer']
        )

    def run(self):
        """
        运行空调模拟器
        """
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
            self._log.error(f"发生错误: {e}", exc_info=True)
        finally:
            self.stop_simulation()
            self.stop_fault_check()

if __name__ == '__main__':
    device_addr = 1
    default_port = '/dev/ttyS5'
    port = default_port
    logging.info(f"使用串口: {port}")
    simulator = HdcAcSimulator(device_addr, port)
    simulator.run()