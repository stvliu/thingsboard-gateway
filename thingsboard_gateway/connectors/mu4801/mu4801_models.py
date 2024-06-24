"""
mu4801_models.py

此模块包含 MU4801 协议的数据模型。它定义了各种类，这些类代表协议中使用的不同类型的数据结构，包括
配置参数、模拟数据、警报状态和控制命令。

每个类都提供序列化（to_bytes）和反序列化（from_bytes）的方法以及与字典格式（to_dict 和 from_dict）之间的转换。

这些模型用于在与 MU4801 设备通信时对数据进行编码和解码。
"""

from enum import Enum
from typing import List, Dict, Any
import struct

class DataFlag(Enum):
    """数据标志"""
    NORMAL = 0

class AlarmStatus(Enum):
    """告警状态"""
    NORMAL = 0
    ALARM = 0x81

class SwitchStatus(Enum):
    """开关状态"""
    ON = 0
    OFF = 1

class EnableStatus(Enum):
    """使能状态"""
    ENABLE = 0xE0
    DISABLE = 0xE1

class LoadOffMode(Enum):
    """负载断开模式"""
    VOLTAGE = 0
    TIME = 1

class RectModuleControlType(Enum):
    """整流模块控制类型"""
    ON = 0x20
    OFF = 0x2F

class SystemControlStateModel(Enum):
    """系统控制状态模型"""
    AUTO = 0xE0
    MANUAL = 0xE1

class SystemControlType(Enum):
    """系统控制类型"""
    RESET = 0xE1      # 系统复位
    LOAD1_OFF = 0xE5  # 负载1下电
    LOAD1_ON = 0xE6   # 负载1上电
    LOAD2_OFF = 0xE7  # 负载2下电
    LOAD2_ON = 0xE8   # 负载2上电
    LOAD3_OFF = 0xE9  # 负载3下电
    LOAD3_ON = 0xEA   # 负载3上电
    LOAD4_OFF = 0xEB  # 负载4下电
    LOAD4_ON = 0xEC   # 负载4上电
    BATTERY_OFF = 0xED  # 电池下电
    BATTERY_ON = 0xEE   # 电池上电

class VoltageStatus(Enum):
    """电压状态"""
    NORMAL = 0
    UNDER = 1
    OVER = 2

class FrequencyStatus(Enum):
    """频率状态"""
    NORMAL = 0
    UNDER = 1
    OVER = 2

class TempStatus(Enum):
    """温度状态"""
    NORMAL = 0
    OVER = 0xB0
    UNDER = 0xB1

class SensorStatus(Enum):
    """传感器状态"""
    NORMAL = 0
    BREAK = 0xB2
    FAULT = 0xB3

class LVDStatus(Enum):
    """LVD状态"""
    NORMAL = 0
    IMPENDING = 1
    OFF = 2

class ChargeStatus(Enum):
    """充电状态"""
    FLOAT = 0
    EQUALIZE = 1
    TEST = 2

class DateTime:
    """日期时间类"""
    def __init__(self, year: int, month: int, day: int, hour: int, minute: int, second: int):
        self.year = year    # 年
        self.month = month  # 月
        self.day = day      # 日
        self.hour = hour    # 时
        self.minute = minute  # 分
        self.second = second  # 秒

    def to_bytes(self):
        return struct.pack('>HBBBBB', self.year, self.month, self.day, self.hour, self.minute, self.second)

    @classmethod
    def from_bytes(cls, data):
        return cls(*struct.unpack('>HBBBBB', data))

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class ProtocolVersion:
    """协议版本类"""
    def __init__(self, version: str):
        self.version = version  # 版本号

    def to_bytes(self):
        return self.version.encode('ascii')

    @classmethod
    def from_bytes(cls, data):
        return cls(data.decode('ascii'))

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class DeviceAddress:
    """设备地址类"""
    def __init__(self, address: int):
        self.address = address  # 设备地址

    def to_bytes(self):
        return struct.pack('B', self.address)

    @classmethod
    def from_bytes(cls, data):
        return cls(struct.unpack('B', data)[0])

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class SoftwareVersion:
    """软件版本类"""
    def __init__(self, major: int, minor: int):
        self.major = major  # 主版本号
        self.minor = minor  # 次版本号

    def to_bytes(self):
        return struct.pack('BB', self.major, self.minor)

    @classmethod
    def from_bytes(cls, data):
        return cls(*struct.unpack('BB', data))

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class ManufacturerInfo:
    """厂商信息类"""
    def __init__(self, collector_name: str, software_version: SoftwareVersion, manufacturer: str):
        self.collector_name = collector_name        # 采集器名称
        self.software_version = software_version    # 软件版本
        self.manufacturer = manufacturer            # 厂商名称

    def to_bytes(self):
        data = bytearray()
        data.extend(self.collector_name.encode('ascii').ljust(10, b'\x00'))
        data.extend(self.software_version.to_bytes())
        data.extend(self.manufacturer.encode('ascii').ljust(20, b'\x00'))
        return bytes(data)

    @classmethod
    def from_bytes(cls, data):
        collector_name = data[:10].decode('ascii').rstrip('\x00')
        software_version = SoftwareVersion.from_bytes(data[10:12])
        manufacturer = data[12:32].decode('ascii').rstrip('\x00')
        return cls(collector_name, software_version, manufacturer)

    def to_dict(self):
        return {
            "collector_name": self.collector_name,
            "software_version": self.software_version.to_dict(),
            "manufacturer": self.manufacturer
        }

    @classmethod
    def from_dict(cls, data):
        data['software_version'] = SoftwareVersion.from_dict(data['software_version'])
        return cls(**data)

class AcAnalogData:
    """交流模拟量数据类"""
    def __init__(self, data_flag: DataFlag, number_of_inputs: int, input_voltage_ab_a: float,
                 input_voltage_bc_b: float, input_voltage_ca_c: float, input_frequency: float,
                 user_defined_params_count: int):
        self.data_flag = data_flag    # 数据标志
        self.number_of_inputs = number_of_inputs    # 交流输入路数
        self.input_voltage_ab_a = input_voltage_ab_a    # 输入线电压AB/相电压A
        self.input_voltage_bc_b = input_voltage_bc_b    # 输入线电压BC/相电压B
        self.input_voltage_ca_c = input_voltage_ca_c    # 输入线电压CA/相电压C
        self.input_frequency = input_frequency    # 输入频率
        self.user_defined_params_count = user_defined_params_count    # 用户自定义参数数量

    def to_bytes(self):
        return struct.pack('<BBfffffB', self.data_flag.value, self.number_of_inputs,
                           self.input_voltage_ab_a, self.input_voltage_bc_b,
                           self.input_voltage_ca_c, self.input_frequency,
                           self.user_defined_params_count)

    @classmethod
    def from_bytes(cls, data):
        unpacked = struct.unpack('<BBfffffB', data)
        return cls(DataFlag(unpacked[0]), *unpacked[1:])

    def to_dict(self):
        return {k: v.name if isinstance(v, Enum) else v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data):
        data['data_flag'] = DataFlag[data['data_flag']]
        return cls(**data)

class AcAlarmStatus:
    """交流告警状态类"""
    def __init__(self, data_flag: DataFlag, number_of_inputs: int, input_voltage_ab_a_status: VoltageStatus,
                 input_voltage_bc_b_status: VoltageStatus, input_voltage_ca_c_status: VoltageStatus,
                 fuse_count: int, user_defined_params_count: int, ac_arrester_status: AlarmStatus,
                 ac_input_power_off_first: AlarmStatus):
        self.data_flag = data_flag    # 数据标志
        self.number_of_inputs = number_of_inputs    # 交流输入路数
        self.input_voltage_ab_a_status = input_voltage_ab_a_status    # 输入线电压AB/相电压A状态
        self.input_voltage_bc_b_status = input_voltage_bc_b_status    # 输入线电压BC/相电压B状态
        self.input_voltage_ca_c_status = input_voltage_ca_c_status    # 输入线电压CA/相电压C状态
        self.fuse_count = fuse_count    # 熔丝数量
        self.user_defined_params_count = user_defined_params_count    # 用户自定义参数数量
        self.ac_arrester_status = ac_arrester_status    # 交流防雷器状态
        self.ac_input_power_off_first = ac_input_power_off_first    # 交流输入首次掉电状态

    def to_bytes(self):
        return struct.pack('<BBBBBBBBB', self.data_flag.value, self.number_of_inputs,
                           self.input_voltage_ab_a_status.value, self.input_voltage_bc_b_status.value,
                           self.input_voltage_ca_c_status.value, self.fuse_count,
                           self.user_defined_params_count, self.ac_arrester_status.value,
                           self.ac_input_power_off_first.value)

    @classmethod
    def from_bytes(cls, data):
        unpacked = struct.unpack('<BBBBBBBBB', data)
        return cls(
            DataFlag(unpacked[0]),
            unpacked[1],
            VoltageStatus(unpacked[2]),
            VoltageStatus(unpacked[3]),
            VoltageStatus(unpacked[4]),
            unpacked[5],
            unpacked[6],
            AlarmStatus(unpacked[7]),
            AlarmStatus(unpacked[8])
        )

    def to_dict(self):
        return {k: v.name if isinstance(v, Enum) else v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data):
        for key, enum_class in [('data_flag', DataFlag), ('input_voltage_ab_a_status', VoltageStatus),
                                ('input_voltage_bc_b_status', VoltageStatus), ('input_voltage_ca_c_status', VoltageStatus),
                                ('ac_arrester_status', AlarmStatus), ('ac_input_power_off_first', AlarmStatus)]:
            data[key] = enum_class[data[key]]
        return cls(**data)

class AcConfigParams:
    """交流配置参数类"""
    def __init__(self, ac_over_voltage: float, ac_under_voltage: float):
        self.ac_over_voltage = ac_over_voltage    # 交流过压值
        self.ac_under_voltage = ac_under_voltage    # 交流欠压值

    def to_bytes(self):
        return struct.pack('<ff', self.ac_over_voltage, self.ac_under_voltage)

    @classmethod
    def from_bytes(cls, data):
        return cls(*struct.unpack('<ff', data))

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class RectAnalogData:
    """整流模块模拟量数据类"""
    def __init__(self, data_flag: DataFlag, output_voltage: float, module_count: int,
                 module_currents: List[float], user_defined_params_count: List[int],
                 module_current_limit: List[float], module_voltage: List[float],
                 module_temperature: List[float], input_voltage_ab_a: List[float]):
        self.data_flag = data_flag    # 数据标志
        self.output_voltage = output_voltage    # 输出电压
        self.module_count = module_count    # 模块数量
        self.module_currents = module_currents    # 模块电流列表
        self.user_defined_params_count = user_defined_params_count    # 用户自定义参数数量列表
        self.module_current_limit = module_current_limit    # 模块电流限制列表
        self.module_voltage = module_voltage    # 模块电压列表
        self.module_temperature = module_temperature    # 模块温度列表
        self.input_voltage_ab_a = input_voltage_ab_a    # 交流输入三相电压AB/A列表

    def to_bytes(self):
        data = struct.pack('<BBf', self.data_flag.value, self.module_count, self.output_voltage)
        for i in range(self.module_count):
            data += struct.pack('<fBfffff', self.module_currents[i], self.user_defined_params_count[i],
                                 self.module_current_limit[i], self.module_voltage[i], self.module_temperature[i],
                                 self.input_voltage_ab_a[i])
        return data

    @classmethod
    def from_bytes(cls, data):
        data_flag, module_count, output_voltage = struct.unpack('<BBf', data[:6])
        module_currents = []
        user_defined_params_count = []
        module_current_limit = []
        module_voltage = []
        module_temperature = []
        input_voltage_ab_a = []
        offset = 6
        for _ in range(module_count):
            current, user_defined, current_limit, voltage, temperature, voltage_ab_a = struct.unpack('<fBffff', data[offset:offset+21])
            module_currents.append(current)
            user_defined_params_count.append(user_defined)
            module_current_limit.append(current_limit)
            module_voltage.append(voltage)
            module_temperature.append(temperature)
            input_voltage_ab_a.append(voltage_ab_a)
            offset += 21
        return cls(DataFlag(data_flag), output_voltage, module_count, module_currents,
                   user_defined_params_count, module_current_limit, module_voltage, module_temperature,
                   input_voltage_ab_a)

    def to_dict(self):
        return {k: [v.name for v in vlist] if isinstance(vlist, list) and vlist and isinstance(vlist[0], Enum) 
                else v.name if isinstance(v, Enum) else v 
                for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data):
        data['data_flag'] = DataFlag[data['data_flag']]
        return cls(**data)

class RectSwitchStatus:
    """整流模块开关状态类"""
    def __init__(self, data_flag: DataFlag, module_count: int, module_run_status: List[int],
                 user_defined_params_count: List[int]):
        self.data_flag = data_flag    # 数据标志
        self.module_count = module_count    # 模块数量
        self.module_run_status = module_run_status    # 模块运行状态列表
        self.user_defined_params_count = user_defined_params_count    # 用户自定义参数数量列表

    def to_bytes(self):
        data = struct.pack('<BB', self.data_flag.value, self.module_count)
        for i in range(self.module_count):
            data += struct.pack('<BB', self.module_run_status[i], self.user_defined_params_count[i])
        return data

    @classmethod
    def from_bytes(cls, data):
        data_flag, module_count = struct.unpack('<BB', data[:2])
        module_run_status = []
        user_defined_params_count = []
        for i in range(2, 2 + module_count * 2, 2):
            run_status, user_defined = struct.unpack('<BB', data[i:i+2])
            module_run_status.append(run_status)
            user_defined_params_count.append(user_defined)
        return cls(DataFlag(data_flag), module_count, module_run_status, user_defined_params_count)

    def to_dict(self):
        return {k: v.name if isinstance(v, Enum) else v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data):
        data['data_flag'] = DataFlag[data['data_flag']]
        return cls(**data)

class RectAlarmStatus:
    """整流模块告警状态类"""
    def __init__(self, data_flag: DataFlag, module_count: int, module_failure_status: List[AlarmStatus],
                 user_defined_params_count: List[int], module_comm_failure_status: List[AlarmStatus],
                 module_protection_status: List[AlarmStatus], module_fan_status: List[AlarmStatus]):
        self.data_flag = data_flag    # 数据标志
        self.module_count = module_count    # 模块数量
        self.module_failure_status = module_failure_status    # 模块故障状态列表
        self.user_defined_params_count = user_defined_params_count    # 用户自定义参数数量列表
        self.module_comm_failure_status = module_comm_failure_status    # 模块通信故障状态列表
        self.module_protection_status = module_protection_status    # 模块保护状态列表
        self.module_fan_status = module_fan_status    # 模块风扇状态列表

    def to_bytes(self):
        data = struct.pack('<BB', self.data_flag.value, self.module_count)
        for i in range(self.module_count):
            data += struct.pack('<BBBBB', self.module_failure_status[i].value,
                                 self.user_defined_params_count[i],
                                 self.module_comm_failure_status[i].value,
                                 self.module_protection_status[i].value,
                                 self.module_fan_status[i].value)
        return data

    @classmethod
    def from_bytes(cls, data):
        data_flag, module_count = struct.unpack('<BB', data[:2])
        module_failure_status = []
        user_defined_params_count = []
        module_comm_failure_status = []
        module_protection_status = []
        module_fan_status = []
        for i in range(2, 2 + module_count * 5, 5):
            failure, user_defined, comm_failure, protection, fan = struct.unpack('<BBBBB', data[i:i+5])
            module_failure_status.append(AlarmStatus(failure))
            user_defined_params_count.append(user_defined)
            module_comm_failure_status.append(AlarmStatus(comm_failure))
            module_protection_status.append(AlarmStatus(protection))
            module_fan_status.append(AlarmStatus(fan))
        return cls(DataFlag(data_flag), module_count, module_failure_status, user_defined_params_count,
                   module_comm_failure_status, module_protection_status, module_fan_status)

    def to_dict(self):
        return {k: [v.name for v in vlist] if isinstance(vlist, list) and vlist and isinstance(vlist[0], Enum) else v.name if isinstance(v, Enum) else v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data):
        data['data_flag'] = DataFlag[data['data_flag']]
        data['module_failure_status'] = [AlarmStatus[status] for status in data['module_failure_status']]
        data['module_comm_failure_status'] = [AlarmStatus[status] for status in data['module_comm_failure_status']]
        data['module_protection_status'] = [AlarmStatus[status] for status in data['module_protection_status']]
        data['module_fan_status'] = [AlarmStatus[status] for status in data['module_fan_status']]
        return cls(**data)

class ControlRectModule:
    """控制整流模块类"""
    def __init__(self, module_id: int, control_type: RectModuleControlType):
        self.module_id = module_id    # 模块ID
        self.control_type = control_type    # 控制类型

    def to_bytes(self):
        return struct.pack('<BB', self.module_id, self.control_type.value)

    @classmethod
    def from_bytes(cls, data):
        module_id, control_type = struct.unpack('<BB', data)
        return cls(module_id, RectModuleControlType(control_type))

    def to_dict(self):
        return {"module_id": self.module_id, "control_type": self.control_type.name}

    @classmethod
    def from_dict(cls, data):
        data['control_type'] = RectModuleControlType[data['control_type']]
        return cls(**data)

class DcAnalogData:
    """直流模拟量数据类"""
    def __init__(self, data_flag: DataFlag, dc_voltage: float, total_load_current: float,
                 battery_group_count: int, battery_group_1_current: float, load_branch_count: int,
                 load_branch_1_current: float, load_branch_2_current: float, load_branch_3_current: float,
                 load_branch_4_current: float, user_defined_params_count: int, battery_total_current: float,
                 battery_group_1_capacity: float, battery_group_1_voltage: float, battery_group_1_mid_voltage: float,
                 battery_group_2_mid_voltage: float, battery_group_3_mid_voltage: float, battery_group_4_mid_voltage: float,
                 battery_group_1_temperature: float, env_temp_1: float, env_temp_2: float, env_humidity_1: float,
                 total_load_power: float, load_power_1: float, load_power_2: float, load_power_3: float,
                 load_power_4: float, total_load_energy: float, load_energy_1: float, load_energy_2: float,
                 load_energy_3: float, load_energy_4: float):
        self.data_flag = data_flag    # 数据标志
        self.dc_voltage = dc_voltage    # 直流电压
        self.total_load_current = total_load_current    # 总负载电流
        self.battery_group_count = battery_group_count    # 电池组数量
        self.battery_group_1_current = battery_group_1_current    # 电池组1电流
        self.load_branch_count = load_branch_count    # 负载分支数量
        self.load_branch_1_current = load_branch_1_current    # 负载分支1电流
        self.load_branch_2_current = load_branch_2_current    # 负载分支2电流
        self.load_branch_3_current = load_branch_3_current    # 负载分支3电流
        self.load_branch_4_current = load_branch_4_current    # 负载分支4电流
        self.user_defined_params_count = user_defined_params_count    # 用户自定义参数数量
        self.battery_total_current = battery_total_current    # 电池总电流
        self.battery_group_1_capacity = battery_group_1_capacity    # 电池组1容量
        self.battery_group_1_voltage = battery_group_1_voltage    # 电池组1电压
        self.battery_group_1_mid_voltage = battery_group_1_mid_voltage    # 电池组1中点电压
        self.battery_group_2_mid_voltage = battery_group_2_mid_voltage    # 电池组2中点电压
        self.battery_group_3_mid_voltage = battery_group_3_mid_voltage    # 电池组3中点电压
        self.battery_group_4_mid_voltage = battery_group_4_mid_voltage    # 电池组4中点电压
        self.battery_group_1_temperature = battery_group_1_temperature    # 电池组1温度
        self.env_temp_1 = env_temp_1    # 环境温度1
        self.env_temp_2 = env_temp_2    # 环境温度2
        self.env_humidity_1 = env_humidity_1    # 环境湿度1
        self.total_load_power = total_load_power    # 总负载功率
        self.load_power_1 = load_power_1    # 负载功率1
        self.load_power_2 = load_power_2    # 负载功率2
        self.load_power_3 = load_power_3    # 负载功率3
        self.load_power_4 = load_power_4    # 负载功率4
        self.total_load_energy = total_load_energy    # 总负载能量
        self.load_energy_1 = load_energy_1    # 负载能量1
        self.load_energy_2 = load_energy_2    # 负载能量2
        self.load_energy_3 = load_energy_3    # 负载能量3
        self.load_energy_4 = load_energy_4    # 负载能量4

    def to_bytes(self):
        return struct.pack('<BBffBfBffffBffffffffffffffffffffff', 
                           self.data_flag.value, self.battery_group_count, self.dc_voltage, 
                           self.total_load_current, self.battery_group_count, self.battery_group_1_current,
                           self.load_branch_count, self.load_branch_1_current, self.load_branch_2_current,
                           self.load_branch_3_current, self.load_branch_4_current, self.user_defined_params_count,
                           self.battery_total_current, self.battery_group_1_capacity, self.battery_group_1_voltage,
                           self.battery_group_1_mid_voltage, self.battery_group_2_mid_voltage,
                           self.battery_group_3_mid_voltage, self.battery_group_4_mid_voltage,
                           self.battery_group_1_temperature, self.env_temp_1, self.env_temp_2,
                           self.env_humidity_1, self.total_load_power, self.load_power_1, self.load_power_2,
                           self.load_power_3, self.load_power_4, self.total_load_energy, self.load_energy_1,
                           self.load_energy_2, self.load_energy_3, self.load_energy_4)

    @classmethod
    def from_bytes(cls, data):
        unpacked = struct.unpack('<BBffBfBffffBffffffffffffffffffffff', data)
        return cls(DataFlag(unpacked[0]), *unpacked[1:])

    def to_dict(self):
        return {k: v.name if isinstance(v, Enum) else v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data):
        data['data_flag'] = DataFlag[data['data_flag']]
        return cls(**data)

class DcAlarmStatus:
    """直流告警状态类"""
    def __init__(self, data_flag: DataFlag, dc_voltage_status: VoltageStatus, battery_fuse_count: int,
                 user_defined_params_count: int, dc_arrester_status: AlarmStatus, load_fuse_status: AlarmStatus,
                 battery_group_1_fuse_status: AlarmStatus, battery_group_2_fuse_status: AlarmStatus,
                 battery_group_3_fuse_status: AlarmStatus, battery_group_4_fuse_status: AlarmStatus,
                 blvd_status: LVDStatus, llvd1_status: LVDStatus, llvd2_status: LVDStatus,
                 llvd3_status: LVDStatus, llvd4_status: LVDStatus, battery_temp_status: TempStatus,
                 battery_temp_sensor_1_status: SensorStatus, env_temp_status: TempStatus,
                 env_temp_sensor_1_status: SensorStatus, env_temp_sensor_2_status: SensorStatus,
                 env_humidity_status: AlarmStatus, env_humidity_sensor_1_status: SensorStatus,
                 door_status: AlarmStatus, water_status: AlarmStatus, smoke_status: AlarmStatus,
                 digital_input_status_1: AlarmStatus, digital_input_status_2: AlarmStatus,
                 digital_input_status_3: AlarmStatus, digital_input_status_4: AlarmStatus,
                 digital_input_status_5: AlarmStatus, digital_input_status_6: AlarmStatus):
        self.data_flag = data_flag    # 数据标志
        self.dc_voltage_status = dc_voltage_status    # 直流电压状态
        self.battery_fuse_count = battery_fuse_count    # 电池保险丝数量
        self.user_defined_params_count = user_defined_params_count    # 用户自定义参数数量
        self.dc_arrester_status = dc_arrester_status    # 直流防雷器状态
        self.load_fuse_status = load_fuse_status    # 负载保险丝状态
        self.battery_group_1_fuse_status = battery_group_1_fuse_status    # 电池组1保险丝状态
        self.battery_group_2_fuse_status = battery_group_2_fuse_status    # 电池组2保险丝状态
        self.battery_group_3_fuse_status = battery_group_3_fuse_status    # 电池组3保险丝状态
        self.battery_group_4_fuse_status = battery_group_4_fuse_status    # 电池组4保险丝状态
        self.blvd_status = blvd_status    # BLVD状态
        self.llvd1_status = llvd1_status    # LLVD1状态
        self.llvd2_status = llvd2_status    # LLVD2状态
        self.llvd3_status = llvd3_status    # LLVD3状态
        self.llvd4_status = llvd4_status    # LLVD4状态
        self.battery_temp_status = battery_temp_status    # 电池温度状态
        self.battery_temp_sensor_1_status = battery_temp_sensor_1_status    # 电池温度传感器1状态
        self.env_temp_status = env_temp_status    # 环境温度状态
        self.env_temp_sensor_1_status = env_temp_sensor_1_status    # 环境温度传感器1状态
        self.env_temp_sensor_2_status = env_temp_sensor_2_status    # 环境温度传感器2状态
        self.env_humidity_status = env_humidity_status    # 环境湿度状态
        self.env_humidity_sensor_1_status = env_humidity_sensor_1_status    # 环境湿度传感器1状态
        self.door_status = door_status    # 门状态
        self.water_status = water_status    # 水浸状态
        self.smoke_status = smoke_status    # 烟雾状态
        self.digital_input_status_1 = digital_input_status_1    # 数字输入状态1
        self.digital_input_status_2 = digital_input_status_2    # 数字输入状态2
        self.digital_input_status_3 = digital_input_status_3    # 数字输入状态3
        self.digital_input_status_4 = digital_input_status_4    # 数字输入状态4
        self.digital_input_status_5 = digital_input_status_5    # 数字输入状态5
        self.digital_input_status_6 = digital_input_status_6    # 数字输入状态6

    def to_bytes(self):
        return struct.pack('<BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB', 
                           self.data_flag.value, self.dc_voltage_status.value,
                           self.battery_fuse_count, self.user_defined_params_count,
                           self.dc_arrester_status.value, self.load_fuse_status.value,
                           self.battery_group_1_fuse_status.value, self.battery_group_2_fuse_status.value,
                           self.battery_group_3_fuse_status.value, self.battery_group_4_fuse_status.value,
                           self.blvd_status.value, self.llvd1_status.value, self.llvd2_status.value,
                           self.llvd3_status.value, self.llvd4_status.value, self.battery_temp_status.value,
                           self.battery_temp_sensor_1_status.value, self.env_temp_status.value,
                           self.env_temp_sensor_1_status.value, self.env_temp_sensor_2_status.value,
                           self.env_humidity_status.value, self.env_humidity_sensor_1_status.value,
                           self.door_status.value, self.water_status.value, self.smoke_status.value,
                           self.digital_input_status_1.value, self.digital_input_status_2.value,
                           self.digital_input_status_3.value, self.digital_input_status_4.value,
                           self.digital_input_status_5.value, self.digital_input_status_6.value)

    @classmethod
    def from_bytes(cls, data):
        unpacked = struct.unpack('<BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB', data)
        return cls(
            DataFlag(unpacked[0]),
            VoltageStatus(unpacked[1]),
            unpacked[2],
            unpacked[3],
            AlarmStatus(unpacked[4]),
            AlarmStatus(unpacked[5]),
            AlarmStatus(unpacked[6]),
            AlarmStatus(unpacked[7]),
            AlarmStatus(unpacked[8]),
            AlarmStatus(unpacked[9]),
            LVDStatus(unpacked[10]),
            LVDStatus(unpacked[11]),
            LVDStatus(unpacked[12]),
            LVDStatus(unpacked[13]),
            LVDStatus(unpacked[14]),
            TempStatus(unpacked[15]),
            SensorStatus(unpacked[16]),
            TempStatus(unpacked[17]),
            SensorStatus(unpacked[18]),
            SensorStatus(unpacked[19]),
            AlarmStatus(unpacked[20]),
            SensorStatus(unpacked[21]),
            AlarmStatus(unpacked[22]),
            AlarmStatus(unpacked[23]),
            AlarmStatus(unpacked[24]),
            AlarmStatus(unpacked[25]),
            AlarmStatus(unpacked[26]),
            AlarmStatus(unpacked[27]),
            AlarmStatus(unpacked[28]),
            AlarmStatus(unpacked[29]),
            AlarmStatus(unpacked[30])
        )

    def to_dict(self):
        return {k: v.name if isinstance(v, Enum) else v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data):
        for key, enum_class in [
            ('data_flag', DataFlag),
            ('dc_voltage_status', VoltageStatus),
            ('dc_arrester_status', AlarmStatus),
            ('load_fuse_status', AlarmStatus),
            ('battery_group_1_fuse_status', AlarmStatus),
            ('battery_group_2_fuse_status', AlarmStatus),
            ('battery_group_3_fuse_status', AlarmStatus),
            ('battery_group_4_fuse_status', AlarmStatus),
            ('blvd_status', LVDStatus),
            ('llvd1_status', LVDStatus),
            ('llvd2_status', LVDStatus),
            ('llvd3_status', LVDStatus),
            ('llvd4_status', LVDStatus),
            ('battery_temp_status', TempStatus),
            ('battery_temp_sensor_1_status', SensorStatus),
            ('env_temp_status', TempStatus),
            ('env_temp_sensor_1_status', SensorStatus),
            ('env_temp_sensor_2_status', SensorStatus),
            ('env_humidity_status', AlarmStatus),
            ('env_humidity_sensor_1_status', SensorStatus),
            ('door_status', AlarmStatus),
            ('water_status', AlarmStatus),
            ('smoke_status', AlarmStatus),
            ('digital_input_status_1', AlarmStatus),
            ('digital_input_status_2', AlarmStatus),
            ('digital_input_status_3', AlarmStatus),
            ('digital_input_status_4', AlarmStatus),
            ('digital_input_status_5', AlarmStatus),
            ('digital_input_status_6', AlarmStatus),
        ]:
            data[key] = enum_class[data[key]]
        return cls(**data)

class DcConfigParams:
    """直流配置参数类"""
    def __init__(self, dc_over_voltage: float, dc_under_voltage: float, time_equalize_charge_enable: EnableStatus,
                 time_equalize_duration: int, time_equalize_interval: int, battery_group_number: int,
                 battery_over_temp: float, battery_under_temp: float, env_over_temp: float, env_under_temp: float,
                 env_over_humidity: float, battery_charge_current_limit: float, float_voltage: float,
                 equalize_voltage: float, battery_off_voltage: float, battery_on_voltage: float,
                 llvd1_off_voltage: float, llvd1_on_voltage: float, llvd2_off_voltage: float, llvd2_on_voltage: float,
                 llvd3_off_voltage: float, llvd3_on_voltage: float, llvd4_off_voltage: float, llvd4_on_voltage: float,
                 battery_capacity: float, battery_test_stop_voltage: float, battery_temp_coeff: float,
                 battery_temp_center: float, float_to_equalize_coeff: float, equalize_to_float_coeff: float,
                 llvd1_off_time: float, llvd2_off_time: float, llvd3_off_time: float, llvd4_off_time: float,
                 load_off_mode: LoadOffMode):
        self.dc_over_voltage = dc_over_voltage    # 直流过压值
        self.dc_under_voltage = dc_under_voltage    # 直流欠压值
        self.time_equalize_charge_enable = time_equalize_charge_enable    # 定时均充使能状态
        self.time_equalize_duration = time_equalize_duration    # 定时均充持续时间
        self.time_equalize_interval = time_equalize_interval    # 定时均充间隔
        self.battery_group_number = battery_group_number    # 电池组数量
        self.battery_over_temp = battery_over_temp    # 电池过温值
        self.battery_under_temp = battery_under_temp    # 电池欠温值
        self.env_over_temp = env_over_temp    # 环境过温值
        self.env_under_temp = env_under_temp    # 环境欠温值
        self.env_over_humidity = env_over_humidity    # 环境过湿值
        self.battery_charge_current_limit = battery_charge_current_limit    # 电池充电电流限制
        self.float_voltage = float_voltage    # 浮充电压
        self.equalize_voltage = equalize_voltage    # 均充电压
        self.battery_off_voltage = battery_off_voltage    # 电池断开电压
        self.battery_on_voltage = battery_on_voltage    # 电池接通电压
        self.llvd1_off_voltage = llvd1_off_voltage    # LLVD1断开电压
        self.llvd1_on_voltage = llvd1_on_voltage    # LLVD1接通电压
        self.llvd2_off_voltage = llvd2_off_voltage    # LLVD2断开电压
        self.llvd2_on_voltage = llvd2_on_voltage    # LLVD2接通电压
        self.llvd3_off_voltage = llvd3_off_voltage    # LLVD3断开电压
        self.llvd3_on_voltage = llvd3_on_voltage    # LLVD3接通电压
        self.llvd4_off_voltage = llvd4_off_voltage    # LLVD4断开电压
        self.llvd4_on_voltage = llvd4_on_voltage    # LLVD4接通电压
        self.battery_capacity = battery_capacity    # 电池容量
        self.battery_test_stop_voltage = battery_test_stop_voltage    # 电池测试停止电压
        self.battery_temp_coeff = battery_temp_coeff    # 电池温度系数
        self.battery_temp_center = battery_temp_center    # 电池温度中心点
        self.float_to_equalize_coeff = float_to_equalize_coeff    # 浮充转均充系数
        self.equalize_to_float_coeff = equalize_to_float_coeff    # 均充转浮充系数
        self.llvd1_off_time = llvd1_off_time    # LLVD1断开时间
        self.llvd2_off_time = llvd2_off_time    # LLVD2断开时间
        self.llvd3_off_time = llvd3_off_time    # LLVD3断开时间
        self.llvd4_off_time = llvd4_off_time    # LLVD4断开时间
        self.load_off_mode = load_off_mode    # 负载断开模式

    def to_bytes(self):
        return struct.pack('<ffBHHBffffffffffffffffffffffffffffffffffffB',
                           self.dc_over_voltage, self.dc_under_voltage,
                           self.time_equalize_charge_enable.value, self.time_equalize_duration,
                           self.time_equalize_interval, self.battery_group_number,
                           self.battery_over_temp, self.battery_under_temp,
                           self.env_over_temp, self.env_under_temp,
                           self.env_over_humidity, self.battery_charge_current_limit,
                           self.float_voltage, self.equalize_voltage,
                           self.battery_off_voltage, self.battery_on_voltage,
                           self.llvd1_off_voltage, self.llvd1_on_voltage,
                           self.llvd2_off_voltage, self.llvd2_on_voltage,
                           self.llvd3_off_voltage, self.llvd3_on_voltage,
                           self.llvd4_off_voltage, self.llvd4_on_voltage,
                           self.battery_capacity, self.battery_test_stop_voltage,
                           self.battery_temp_coeff, self.battery_temp_center,
                           self.float_to_equalize_coeff, self.equalize_to_float_coeff,
                           self.llvd1_off_time, self.llvd2_off_time,
                           self.llvd3_off_time, self.llvd4_off_time,
                           self.load_off_mode.value)

    @classmethod
    def from_bytes(cls, data):
        unpacked = struct.unpack('<ffBHHBffffffffffffffffffffffffffffffffffffB', data)
        return cls(
            dc_over_voltage=unpacked[0],
            dc_under_voltage=unpacked[1],
            time_equalize_charge_enable=EnableStatus(unpacked[2]),
            time_equalize_duration=unpacked[3],
            time_equalize_interval=unpacked[4],
            battery_group_number=unpacked[5],
            battery_over_temp=unpacked[6],
            battery_under_temp=unpacked[7],
            env_over_temp=unpacked[8],
            env_under_temp=unpacked[9],
            env_over_humidity=unpacked[10],
            battery_charge_current_limit=unpacked[11],
            float_voltage=unpacked[12],
            equalize_voltage=unpacked[13],
            battery_off_voltage=unpacked[14],
            battery_on_voltage=unpacked[15],
            llvd1_off_voltage=unpacked[16],
            llvd1_on_voltage=unpacked[17],
            llvd2_off_voltage=unpacked[18],
            llvd2_on_voltage=unpacked[19],
            llvd3_off_voltage=unpacked[20],
            llvd3_on_voltage=unpacked[21],
            llvd4_off_voltage=unpacked[22],
            llvd4_on_voltage=unpacked[23],
            battery_capacity=unpacked[24],
            battery_test_stop_voltage=unpacked[25],
            battery_temp_coeff=unpacked[26],
            battery_temp_center=unpacked[27],
            float_to_equalize_coeff=unpacked[28],
            equalize_to_float_coeff=unpacked[29],
            llvd1_off_time=unpacked[30],
            llvd2_off_time=unpacked[31],
            llvd3_off_time=unpacked[32],
            llvd4_off_time=unpacked[33],
            load_off_mode=LoadOffMode(unpacked[34])
        )

    def to_dict(self):
        return {k: v.name if isinstance(v, Enum) else v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, data):
        data['time_equalize_charge_enable'] = EnableStatus[data['time_equalize_charge_enable']]
        data['load_off_mode'] = LoadOffMode[data['load_off_mode']]
        return cls(**data)

class SystemControlState:
    """系统控制状态类"""
    def __init__(self, state: SystemControlStateModel):
        self.state = state    # 系统控制状态

    def to_bytes(self):
        return struct.pack('<B', self.state.value)

    @classmethod
    def from_bytes(cls, data):
        state, = struct.unpack('<B', data)
        return cls(SystemControlStateModel(state))

    def to_dict(self):
        return {"state": self.state.name}

    @classmethod
    def from_dict(cls, data):
        return cls(SystemControlStateModel[data['state']])

class AlarmSoundEnable:
    """告警声音使能类"""
    def __init__(self, enable: EnableStatus):
        self.enable = enable    # 使能状态

    def to_bytes(self):
        return struct.pack('<B', self.enable.value)

    @classmethod
    def from_bytes(cls, data):
        enable, = struct.unpack('<B', data)
        return cls(EnableStatus(enable))

    def to_dict(self):
        return {"enable": self.enable.name}

    @classmethod
    def from_dict(cls, data):
        return cls(EnableStatus[data['enable']])

class EnergyParams:
    """节能参数类"""
    def __init__(self, energy_saving: int, min_working_modules: int, module_switch_cycle: int,
                 module_best_efficiency_point: int, module_redundancy_point: int):
        self.energy_saving = energy_saving    # 节能状态
        self.min_working_modules = min_working_modules    # 最小工作模块数
        self.module_switch_cycle = module_switch_cycle    # 模块切换周期
        self.module_best_efficiency_point = module_best_efficiency_point    # 模块最佳效率点
        self.module_redundancy_point = module_redundancy_point    # 模块冗余点

    def to_bytes(self):
        return struct.pack('<BBHBB', self.energy_saving, self.min_working_modules, self.module_switch_cycle,
                           self.module_best_efficiency_point, self.module_redundancy_point)

    @classmethod
    def from_bytes(cls, data):
        return cls(*struct.unpack('<BBHBB', data))

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class SystemControl:
    """系统控制类"""
    def __init__(self, control_type: SystemControlType):
        self.control_type = control_type    # 控制类型

    def to_bytes(self):
        return struct.pack('<B', self.control_type.value)

    @classmethod
    def from_bytes(cls, data):
        control_type, = struct.unpack('<B', data)
        return cls(SystemControlType(control_type))

    def to_dict(self):
        return {"control_type": self.control_type.name}

    @classmethod
    def from_dict(cls, data):
        return cls(SystemControlType[data['control_type']])