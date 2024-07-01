"""
mu4801_models.py

此模块包含 MU4801 协议的数据模型。它定义了各种类，这些类代表协议中使用的不同类型的数据结构，包括
配置参数、模拟数据、警报状态和控制命令。

每个类都提供序列化（to_bytes）和反序列化（from_bytes）的方法以及与字典格式（to_dict 和 from_dict）之间的转换。

这些模型用于在与 MU4801 设备通信时对数据进行编码和解码。
"""
import struct
from enum import Enum
from typing import List, Dict, Any, Set
from dataclasses import dataclass
import logging
logging.basicConfig(level=logging.DEBUG)

# 常量定义
COLLECTOR_NAME_LENGTH = 10  # 采集器名称长度
MANUFACTURER_NAME_LENGTH = 20  # 制造商名称长度
AC_RESERVED_PARAMS_COUNT = 30  # 交流预留参数数量
RECT_MODULE_RESERVED_PARAMS_COUNT = 7  # 整流模块预留参数数量
DC_USER_DEFINED_PARAMS_COUNT = 55  # 直流用户自定义参数数量
BATTERY_GROUP_COUNT = 6  # 电池组数量
LOAD_BRANCH_COUNT = 4  # 负载分支数量
ENV_TEMP_COUNT = 3  # 环境温度传感器数量
ENV_HUMIDITY_COUNT = 3  # 环境湿度传感器数量

# 固定值常量
DEFAULT_FLOAT_VALUE = 0.0  # 默认浮点值
DEFAULT_INT_VALUE = 0  # 默认整数值
DEFAULT_BATTERY_GROUP_COUNT = 1  # 默认电池组数量
DEFAULT_LOAD_BRANCH_COUNT = 4  # 默认负载分支数量

class DataFlag(Enum):
    """数据标志枚举"""
    NORMAL = 0  # 正常

class AlarmStatus(Enum):
    """告警状态枚举"""
    NORMAL = 0x00  # 正常
    ALARM = 0x81  # 告警

class SwitchStatus(Enum):
    """开关状态枚举"""
    ON = 0  # 开
    OFF = 1  # 关

class EnableStatus(Enum):
    """使能状态枚举"""
    ENABLE = 0x00 # 使能
    DISABLE = 0x01 # 禁止

class LoadOffMode(Enum):
    """负载下电模式枚举"""
    VOLTAGE = 0  # 电压模式
    TIME = 1  # 时间模式

class RectModuleControlType(Enum):
    """整流模块控制类型枚举"""
    ON = 0x20  # 开机
    OFF = 0x2F  # 关机

class SystemControlStateModel(Enum):
    """系统控制状态模型枚举"""
    AUTO = 0xE0  # 自动控制状态
    MANUAL = 0xE1  # 手动控制状态

class SystemControlType(Enum):
    """系统控制类型枚举"""
    RESET = 0xE1  # 系统复位
    LOAD1_OFF = 0xE5  # 负载1下电
    LOAD1_ON = 0xE6  # 负载1上电
    LOAD2_OFF = 0xE7  # 负载2下电
    LOAD2_ON = 0xE8  # 负载2上电
    LOAD3_OFF = 0xE9  # 负载3下电
    LOAD3_ON = 0xEA  # 负载3上电
    LOAD4_OFF = 0xEB  # 负载4下电
    LOAD4_ON = 0xEC  # 负载4上电
    BATTERY_OFF = 0xED  # 电池下电
    BATTERY_ON = 0xEE  # 电池上电

class VoltageStatus(Enum):
    """电压状态枚举"""
    NORMAL = 0x00  # 正常
    UNDER = 0x01   # 欠压
    OVER = 0x02    # 过压

class FrequencyStatus(Enum):
    """频率状态枚举"""
    NORMAL = 0x00  # 正常
    UNDER = 0x01   # 频率过低
    OVER = 0x02    # 频率过高

class FuseStatus(Enum):
    """熔丝状态枚举"""
    NORMAL = 0x00     # 正常
    FUSE_BROKEN = 0x04  # 熔丝断开
    SWITCH_OFF = 0x05   # 开关断开

class AcCommStatus(Enum):
    """交流通信状态枚举"""
    NORMAL = 0x00   # 正常
    ALARM = 0x80  # 告警

class AcArresterStatus(Enum):
    """交流防雷器状态枚举"""
    NORMAL = 0x00  # 正常
    ALARM = 0x81   # 告警

class AcInputSwitchStatus(Enum):
    """交流开关状态枚举"""
    NORMAL = 0x00  # 正常
    ALARM = 0x82  # 告警

class AcOutputSwitchStatus(Enum):
    """交流开关状态枚举"""
    NORMAL = 0x00  # 正常
    ALARM = 0x83  # 告警

class AcPowerStatus(Enum):
    """交流电源状态/交流第一路输入停电枚举"""
    NORMAL = 0x00        # 正常
    ALARM = 0x84  # 告警

class AcAlarmReservedStatus(Enum):
    """交流告警状态枚举"""
    NORMAL = 0x00  # 正常
    ALARM = 0x85   # 告警

class AcCurrentStatus(Enum):
    """交流电流状态枚举"""
    NORMAL = 0x00  # 正常
    OVER = 0x02    # 过高

class TempStatus(Enum):
    """温度状态枚举"""
    NORMAL = 0x00  # 正常
    OVER = 0xB0  # 过温
    UNDER = 0xB1  # 欠温

class SensorStatus(Enum):
    """传感器状态枚举"""
    NORMAL = 0x00  # 正常
    BREAK = 0xB2  # 未接
    FAULT = 0xB3  # 故障

class LVDStatus(Enum):
    """LVD状态枚举"""
    NORMAL = 0  # 正常
    IMPENDING = 1  # 即将下电
    OFF = 2  # 下电

class ChargeStatus(Enum):
    """充电状态枚举"""
    FLOAT = 0  # 浮充
    EQUALIZE = 1  # 均充
    TEST = 2  # 测试

class BaseModel:
    """基础模型类"""
    _supported_fields: Set[str] = set()  # 支持的字段集合
    _unsupported_fields: Dict[str, Any] = {}  # 不支持的字段字典
    _fixed_fields: Dict[str, Any] = {}  # 固定字段字典

    def __init__(self):
        self._init_unsupported_fields()
        self._init_fixed_fields()

    def _init_unsupported_fields(self):
        """初始化不支持的字段"""
        for field, default_value in self._unsupported_fields.items():
            setattr(self, field, default_value)

    def _init_fixed_fields(self):
        """初始化固定字段"""
        for field, default_value in self._fixed_fields.items():
            setattr(self, field, default_value)

    def to_dict(self):
        """将对象转换为字典"""
        return {
            k: v.name if isinstance(v, Enum) else
            [item.name for item in v] if isinstance(v, list) and v and isinstance(v[0], Enum) else
            v
            for k, v in self.__dict__.items()
            if k in self._supported_fields or k in self._fixed_fields
        }

    @classmethod
    def from_dict(cls, data):
        """从字典创建对象"""
        instance = cls()
        for k, v in data.items():
            if k in cls._supported_fields and k not in cls._fixed_fields:
                setattr(instance, k, v)
        instance._init_unsupported_fields()
        instance._init_fixed_fields()
        return instance

    def to_bytes(self):
        """将对象转换为字节串"""
        raise NotImplementedError("Subclasses must implement to_bytes method")

    @classmethod
    def from_bytes(cls, data):
        """从字节串创建对象"""
        raise NotImplementedError("Subclasses must implement from_bytes method")

@dataclass
class DateTime(BaseModel):
    """日期时间类"""
    _supported_fields = {'year', 'month', 'day', 'hour', 'minute', 'second'}

    def __init__(self, year: int = DEFAULT_INT_VALUE, month: int = 1, day: int = 1,
                 hour: int = DEFAULT_INT_VALUE, minute: int = DEFAULT_INT_VALUE, second: int = DEFAULT_INT_VALUE):
        self.year = year  # 年
        self.month = month  # 月
        self.day = day  # 日
        self.hour = hour  # 时
        self.minute = minute  # 分
        self.second = second  # 秒
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段


    def to_bytes(self):
        return struct.pack('>HBBBBB', self.year, self.month, self.day, self.hour, self.minute, self.second)

    @classmethod
    def from_bytes(cls, data):
        return cls(*struct.unpack('>HBBBBB', data))

    def __str__(self):
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d} {self.hour:02d}:{self.minute:02d}:{self.second:02d}"

@dataclass
class ProtocolVersion(BaseModel):
    """协议版本类"""
    _supported_fields = {'version'}

    def __init__(self, version: str = 'V2.1'):
        self.version = version  # 协议版本
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        return self.version.encode('ascii')

    @classmethod
    def from_bytes(cls, data):
        return cls(data.decode('ascii'))

@dataclass
class DeviceAddress(BaseModel):
    """设备地址类"""
    _supported_fields = {'address'}

    def __init__(self, address: int = DEFAULT_INT_VALUE):
        self.address = address  # 设备地址
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        return struct.pack('B', self.address)

    @classmethod
    def from_bytes(cls, data):
        return cls(struct.unpack('B', data)[0])

@dataclass
class SoftwareVersion(BaseModel):
    """软件版本类"""
    _supported_fields = {'major', 'minor'}

    def __init__(self, major: int = 1, minor: int = DEFAULT_INT_VALUE):
        self.major = major  # 主版本号
        self.minor = minor  # 次版本号
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        return struct.pack('BB', self.major, self.minor)

    @classmethod
    def from_bytes(cls, data):
        return cls(*struct.unpack('BB', data))

    def __str__(self):
        return f"{self.major}.{self.minor}"

@dataclass
class ManufacturerInfo(BaseModel):
    """制造商信息类"""
    _supported_fields = {'collector_name', 'software_version', 'manufacturer'}

    def __init__(self, collector_name: str = '', software_version: SoftwareVersion = None, manufacturer: str = ''):
        self.collector_name = collector_name  # 采集器名称
        self.software_version = software_version or SoftwareVersion()  # 软件版本
        self.manufacturer = manufacturer  # 制造商
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        data = bytearray()
        data.extend(self.collector_name.encode('ascii').ljust(COLLECTOR_NAME_LENGTH, b'\x00'))
        data.extend(self.software_version.to_bytes())
        data.extend(self.manufacturer.encode('ascii').ljust(MANUFACTURER_NAME_LENGTH, b'\x00'))
        return bytes(data)

    @classmethod
    def from_bytes(cls, data):
        collector_name = data[:COLLECTOR_NAME_LENGTH].decode('ascii').rstrip('\x00')
        software_version = SoftwareVersion.from_bytes(data[COLLECTOR_NAME_LENGTH:COLLECTOR_NAME_LENGTH+2])
        manufacturer = data[COLLECTOR_NAME_LENGTH+2:COLLECTOR_NAME_LENGTH+2+MANUFACTURER_NAME_LENGTH].decode('ascii').rstrip('\x00')
        return cls(collector_name, software_version, manufacturer)

    def to_dict(self):
        return {
            'collector_name': self.collector_name,
            'software_version': self.software_version.to_dict(),
            'manufacturer': self.manufacturer
        }

@dataclass
class AcAnalogData(BaseModel):
    """交流模拟量数据类"""
    _supported_fields = {'input_voltage_ab_a', 'input_voltage_bc_b', 'input_voltage_ca_c', 'input_frequency'}
    _unsupported_fields = {
        '_output_current_a': DEFAULT_FLOAT_VALUE,  # 交流屏输出电流A (A)
        '_output_current_b': DEFAULT_FLOAT_VALUE,  # 交流屏输出电流B (A)
        '_output_current_c': DEFAULT_FLOAT_VALUE,  # 交流屏输出电流C (A)
        '_reserved': [DEFAULT_FLOAT_VALUE] * AC_RESERVED_PARAMS_COUNT  # 预留参数
    }
    _fixed_fields = {
        'data_flag': DataFlag.NORMAL,  # 数据标志，固定为正常
        'number_of_ac_inputs': 1,  # 交流输入路数，固定为1
        'user_defined_params_count': AC_RESERVED_PARAMS_COUNT  # 用户自定义参数数量，固定为AC_RESERVED_PARAMS_COUNT
    }

    def __init__(self, input_voltage_ab_a: float = DEFAULT_FLOAT_VALUE,
                 input_voltage_bc_b: float = DEFAULT_FLOAT_VALUE,
                 input_voltage_ca_c: float = DEFAULT_FLOAT_VALUE,
                 input_frequency: float = DEFAULT_FLOAT_VALUE):
        self.input_voltage_ab_a = input_voltage_ab_a  # 输入线/相电压 AB/A (V)
        self.input_voltage_bc_b = input_voltage_bc_b  # 输入线/相电压 BC/B (V)
        self.input_voltage_ca_c = input_voltage_ca_c  # 输入线/相电压 CA/C (V)
        self.input_frequency = input_frequency  # 输入频率 (Hz)
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        return struct.pack('<BBffffB30ffff',
                           self.data_flag.value,
                           self.number_of_ac_inputs,
                           self.input_voltage_ab_a,
                           self.input_voltage_bc_b,
                           self.input_voltage_ca_c,
                           self.input_frequency,
                           self.user_defined_params_count,
                           *self._reserved,
                           self._output_current_a,
                           self._output_current_b,
                           self._output_current_c,
                           )

    @classmethod
    def from_bytes(cls, data):
        unpacked = struct.unpack('<BBffffB30ffff', data)
        instance = cls(
            input_voltage_ab_a=unpacked[2],
            input_voltage_bc_b=unpacked[3],
            input_voltage_ca_c=unpacked[4],
            input_frequency=unpacked[5]
        )
        instance._reserved = list(unpacked[7:37])
        instance._output_current_a = unpacked[37]
        instance._output_current_b = unpacked[38]
        instance._output_current_c = unpacked[39]
        return instance

@dataclass
class AcAlarmStatus(BaseModel):
    """交流告警状态类"""
    _supported_fields = {'input_voltage_ab_a_status', 'input_voltage_bc_b_status', 'input_voltage_ca_c_status',
                         'ac_arrester_status', 'ac_power_status'}
    _unsupported_fields = {
        '_frequency_status': FrequencyStatus.NORMAL,        # 频率状态（不支持）
        '_ac_comm_failure_status': AcCommStatus.NORMAL,     # 交流通信故障状态（不支持）
        '_ac_input_switch_status': AcInputSwitchStatus.NORMAL,  # 交流输入空开跳（不支持）
        '_ac_output_switch_status': AcOutputSwitchStatus.NORMAL,  # 交流输出开关状态（不支持）
        '_reserved': [AcAlarmReservedStatus.NORMAL] * 13,           # 预留告警状态（不支持）
        '_input_current_a_status': AcCurrentStatus.NORMAL,  # A相输入电流状态（不支持）
        '_input_current_b_status': AcCurrentStatus.NORMAL,  # B相输入电流状态（不支持）
        '_input_current_c_status': AcCurrentStatus.NORMAL   # C相输入电流状态（不支持）
    }
    _fixed_fields = {
        'data_flag': DataFlag.NORMAL,  # 数据标志，固定为正常
        'number_of_inputs': 1,  # 交流输入路数，固定为1
        'fuse_count': 0,  # 熔丝数量，固定为0
        'user_defined_params_count': 18  # 用户自定义参数数量，固定为18
    }

    def __init__(self,
                 input_voltage_ab_a_status: VoltageStatus = VoltageStatus.NORMAL,  # AB/A相电压状态
                 input_voltage_bc_b_status: VoltageStatus = VoltageStatus.NORMAL,  # BC/B相电压状态
                 input_voltage_ca_c_status: VoltageStatus = VoltageStatus.NORMAL,  # CA/C相电压状态
                 ac_arrester_status: AcArresterStatus = AcArresterStatus.NORMAL,   # 交流防雷器状态
                 ac_power_status: AcPowerStatus = AcPowerStatus.NORMAL):           #交流第一路输入停电枚举
        self.input_voltage_ab_a_status = input_voltage_ab_a_status  # 输入线/相电压AB/A状态
        self.input_voltage_bc_b_status = input_voltage_bc_b_status  # 输入线/相电压BC/B状态
        self.input_voltage_ca_c_status = input_voltage_ca_c_status  # 输入线/相电压CA/C状态
        self.ac_arrester_status = ac_arrester_status  # 交流防雷器断状态
        self.ac_power_status = ac_power_status  # 交流第一路输入停电状态
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        return struct.pack('<BBBBBBBBBBBBBBBBBBBBBBBBBBBBB',
                           self.data_flag.value,
                           self.number_of_inputs,
                           self.input_voltage_ab_a_status.value,
                           self.input_voltage_bc_b_status.value,
                           self.input_voltage_ca_c_status.value,
                           self._frequency_status.value,
                           self.fuse_count,
                           self.user_defined_params_count,
                           self.ac_arrester_status.value,
                           self._ac_comm_failure_status.value,
                           self._ac_input_switch_status.value,
                           self._ac_output_switch_status.value,
                           self.ac_power_status.value,
                           *[status.value for status in self._reserved],
                           self._input_current_a_status.value,
                           self._input_current_b_status.value,
                           self._input_current_c_status.value
                           )

    @classmethod
    def from_bytes(cls, data):
        unpacked = struct.unpack('<BBBBBBBBBBBBBBBBBBBBBBBBBBBBB', data)
        instance = cls(
            input_voltage_ab_a_status=VoltageStatus(unpacked[2]),
            input_voltage_bc_b_status=VoltageStatus(unpacked[3]),
            input_voltage_ca_c_status=VoltageStatus(unpacked[4]),
            ac_arrester_status=AcArresterStatus(unpacked[8]),
            ac_power_status=AcPowerStatus(unpacked[12])
        )
        instance._frequency_status = FrequencyStatus(unpacked[5])
        instance._ac_comm_failure_status = AcCommStatus(unpacked[9])
        instance._ac_input_switch_status=AcInputSwitchStatus(unpacked[10]),
        instance._ac_output_switch_status = AcOutputSwitchStatus(unpacked[11])
        instance._reserved = [AcAlarmReservedStatus(status) for status in unpacked[13:26]]
        instance._input_current_a_status = AcCurrentStatus(unpacked[26])
        instance._input_current_b_status = AcCurrentStatus(unpacked[27])
        instance._input_current_c_status = AcCurrentStatus(unpacked[28])
        return instance

@dataclass
class AcConfigParams(BaseModel):
    """交流配置参数类"""
    _supported_fields = {'ac_over_voltage', 'ac_under_voltage'}
    _unsupported_fields = {
        '_ac_output_current_limit': DEFAULT_FLOAT_VALUE,  # 交流输出电流上限 (A)
        '_frequency_upper_limit': DEFAULT_FLOAT_VALUE,  # 频率上限 (Hz)
        '_frequency_lower_limit': DEFAULT_FLOAT_VALUE  # 频率下限 (Hz)
    }

    def __init__(self, ac_over_voltage: float = DEFAULT_FLOAT_VALUE, ac_under_voltage: float = DEFAULT_FLOAT_VALUE):
        self.ac_over_voltage = ac_over_voltage  # 交流输入线/相电压上限 (V)
        self.ac_under_voltage = ac_under_voltage  # 交流输入线/相电压下限 (V)
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        return struct.pack('<fffff',
                           self.ac_over_voltage,
                           self.ac_under_voltage,
                           self._ac_output_current_limit,
                           self._frequency_upper_limit,
                           self._frequency_lower_limit
                           )

    @classmethod
    def from_bytes(cls, data):
        unpacked = struct.unpack('<fffff', data)
        instance = cls(
            ac_over_voltage=unpacked[0],
            ac_under_voltage=unpacked[1]
        )
        instance._ac_output_current_limit = unpacked[2]
        instance._frequency_upper_limit = unpacked[3]
        instance._frequency_lower_limit = unpacked[4]
        return instance

@dataclass
class RectAnalogData(BaseModel):
    """整流模块模拟量数据类"""
    _supported_fields = {'output_voltage', 'module_count', 'module_currents', 'module_current_limit',
                         'module_voltage', 'module_temperature', 'module_input_voltage_ab'}
    _unsupported_fields = {
        '_module_input_voltage_bc': [DEFAULT_FLOAT_VALUE] * BATTERY_GROUP_COUNT,  # 交流输入三相电压BC (V)
        '_module_input_voltage_ca': [DEFAULT_FLOAT_VALUE] * BATTERY_GROUP_COUNT,  # 交流输入三相电压CA (V)
        '_reserved': [DEFAULT_FLOAT_VALUE] * 7  # 预留参数
    }
    _fixed_fields = {'data_flag': DataFlag.NORMAL, 'user_defined_params_count': 13}  # 用户自定义参数数量，固定为13

    def __init__(self, output_voltage: float = DEFAULT_FLOAT_VALUE, module_count: int = DEFAULT_INT_VALUE,
                 module_currents: List[float] = None, module_current_limit: List[float] = None,
                 module_voltage: List[float] = None, module_temperature: List[float] = None,
                 module_input_voltage_ab: List[float] = None):
        self.output_voltage = output_voltage  # 整流模块输出电压 (V)
        self.module_count = module_count  # 监控模块数量
        self.module_currents = module_currents or []  # 整流模块输出电流 (A)
        self.module_current_limit = module_current_limit or []  # 模块限流点 (%)
        self.module_voltage = module_voltage or []  # 模块输出电压 (V)
        self.module_temperature = module_temperature or []  # 模块温度 (℃)
        self.module_input_voltage_ab = module_input_voltage_ab or []  # 交流输入三相电压AB (V)
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        data = struct.pack('<BBf', self.data_flag.value, self.module_count, self.output_voltage)
        for i in range(self.module_count):
            data += struct.pack('<fBffffff7f',
                                self.module_currents[i],
                                self.user_defined_params_count,
                                self.module_current_limit[i],
                                self.module_voltage[i],
                                self.module_temperature[i],
                                self.module_input_voltage_ab[i],
                                self._module_input_voltage_bc[i],
                                self._module_input_voltage_ca[i],
                                *self._reserved)
        return data

    @classmethod
    def from_bytes(cls, data):
        if len(data) < 6:
            raise ValueError("Data too short to contain header information")

        data_flag, module_count, output_voltage = struct.unpack('<BBf', data[:6])
        instance = cls(output_voltage=output_voltage, module_count=module_count)
        instance.data_flag = DataFlag(data_flag)
        offset = 6

        expected_length = 6 + (module_count * 57)  # 6 bytes header + (57 bytes per module)
        if len(data) < expected_length:
            raise ValueError(f"Data length ({len(data)}) is less than expected ({expected_length})")

        for _ in range(module_count):
            if offset + 57 > len(data):
                break  # 防止越界访问

            try:
                module_data = struct.unpack('<fBffffff7f', data[offset:offset+57])
                instance.module_currents.append(module_data[0])
                instance.user_defined_params_count = module_data[1]
                instance.module_current_limit.append(module_data[2])
                instance.module_voltage.append(module_data[3])
                instance.module_temperature.append(module_data[4])
                instance.module_input_voltage_ab.append(module_data[5])
                instance._module_input_voltage_bc.append(module_data[6])
                instance._module_input_voltage_ca.append(module_data[7])
                instance._reserved.extend(module_data[8:])
            except struct.error as e:
                raise ValueError(f"Error unpacking module data at offset {offset}: {e}")

            offset += 57

        return instance

@dataclass
class RectSwitchStatus(BaseModel):
    """整流模块开关输入状态类"""
    _supported_fields = {'module_count', 'module_run_status', 'module_limit_status'}
    _unsupported_fields = {
        '_module_charge_status': [ChargeStatus.FLOAT] * BATTERY_GROUP_COUNT,  # 浮充/均充/测试状态
        '_module_ac_limit_power': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,  # 模块交流限功率
        '_module_temp_limit_power': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,  # 模块温度限功率
        '_module_fan_full_speed': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,  # 风扇全速
        '_module_walk_in_mode': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,  # WALK-IN模式
        '_module_sequential_start': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,  # 顺序起机使能状态
        '_reserved': [AlarmStatus.NORMAL] * 11  # 预留
    }
    _fixed_fields = {'data_flag': DataFlag.NORMAL, 'user_defined_params_count': 16}  # 用户自定义参数数量，固定为16

    def __init__(self, module_count: int = DEFAULT_INT_VALUE,
                 module_run_status: List[SwitchStatus] = None,
                 module_limit_status: List[SwitchStatus] = None):
        self.module_count = module_count  # 整流模块数量
        self.module_run_status = module_run_status or []  # 开机/关机状态
        self.module_limit_status = module_limit_status or []  # 限流/不限流状态
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        data = struct.pack('<BB', self.data_flag.value, self.module_count)
        for i in range(self.module_count):
            module_data = [
                self.module_run_status[i].value,
                self.module_limit_status[i].value,
                self._module_charge_status[i].value,
                self.user_defined_params_count,
                self._module_ac_limit_power[i].value,
                self._module_temp_limit_power[i].value,
                self._module_fan_full_speed[i].value,
                self._module_walk_in_mode[i].value,
                self._module_sequential_start[i].value
            ]
            module_data.extend([status.value for status in self._reserved])
            data += struct.pack('<BBBBB15B', *module_data)
        return data

    @classmethod
    def from_bytes(cls, data):
        data_flag, module_count = struct.unpack('<BB', data[:2])
        instance = cls(module_count=module_count)
        instance.data_flag = DataFlag(data_flag)
        offset = 2
        for _ in range(module_count):
            module_data = struct.unpack('<BBBBB15B', data[offset:offset+20])
            instance.module_run_status.append(SwitchStatus(module_data[0]))
            instance.module_limit_status.append(SwitchStatus(module_data[1]))
            instance._module_charge_status.append(ChargeStatus(module_data[2]))
            instance.user_defined_params_count = module_data[3]
            instance._module_ac_limit_power.append(AlarmStatus(module_data[4]))
            instance._module_temp_limit_power.append(AlarmStatus(module_data[5]))
            instance._module_fan_full_speed.append(AlarmStatus(module_data[6]))
            instance._module_walk_in_mode.append(AlarmStatus(module_data[7]))
            instance._module_sequential_start.append(AlarmStatus(module_data[8]))
            instance._reserved = [AlarmStatus(status) for status in module_data[9:]]
            offset += 20
        return instance

@dataclass
class RectAlarmStatus(BaseModel):
    """整流模块告警状态类"""
    _supported_fields = {'module_count', 'module_failure_status', 'module_comm_failure_status',
                         'module_protection_status', 'module_fan_status'}
    _unsupported_fields = {
        '_module_unbalanced_current': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,  # 模块不均流状态
        '_module_ac_overvoltage': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,  # 模块交流过压状态
        '_module_ac_undervoltage': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,  # 模块交流欠压状态
        '_module_ac_unbalanced': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,  # 模块交流不平衡状态
        '_module_ac_phase_loss': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,  # 模块交流缺相状态
        '_module_env_temp_abnormal': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,  # 模块环境温度异常状态
        '_reserved': [AlarmStatus.NORMAL] * 9  # 预留告警状态
    }
    _fixed_fields = {'data_flag': DataFlag.NORMAL, 'user_defined_params_count': 18}  # 用户自定义参数数量，固定为18

    def __init__(self, module_count: int = DEFAULT_INT_VALUE, module_failure_status: List[AlarmStatus] = None,
                 module_comm_failure_status: List[AlarmStatus] = None,
                 module_protection_status: List[AlarmStatus] = None, module_fan_status: List[AlarmStatus] = None):
        self.module_count = module_count  # 整流模块数量
        self.module_failure_status = module_failure_status or []  # 整流模块故障状态
        self.module_comm_failure_status = module_comm_failure_status or []  # 模块通讯中断状态
        self.module_protection_status = module_protection_status or []  # 模块保护状态
        self.module_fan_status = module_fan_status or []  # 模块风扇故障状态
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        data = struct.pack('<BB', self.data_flag.value, self.module_count)
        for i in range(self.module_count):
            data += struct.pack('<BBBBBBBBBBB9B',
                                self.module_failure_status[i].value,
                                self.user_defined_params_count,
                                self.module_comm_failure_status[i].value,
                                self.module_protection_status[i].value,
                                self.module_fan_status[i].value,
                                self._module_unbalanced_current[i].value,
                                self._module_ac_overvoltage[i].value,
                                self._module_ac_undervoltage[i].value,
                                self._module_ac_unbalanced[i].value,
                                self._module_ac_phase_loss[i].value,
                                self._module_env_temp_abnormal[i].value,
                                *[status.value for status in self._reserved]
                                )
        return data

    @classmethod
    def from_bytes(cls, data):
        data_flag, module_count = struct.unpack('<BB', data[:2])
        instance = cls(module_count=module_count)
        offset = 2
        for _ in range(module_count):
            module_data = struct.unpack('<BBBBBBBBBBB9B', data[offset:offset+20])
            instance.module_failure_status.append(AlarmStatus(module_data[0]))
            instance.module_comm_failure_status.append(AlarmStatus(module_data[2]))
            instance.module_protection_status.append(AlarmStatus(module_data[3]))
            instance.module_fan_status.append(AlarmStatus(module_data[4]))
            instance._module_unbalanced_current.append(AlarmStatus(module_data[5]))
            instance._module_ac_overvoltage.append(AlarmStatus(module_data[6]))
            instance._module_ac_undervoltage.append(AlarmStatus(module_data[7]))
            instance._module_ac_unbalanced.append(AlarmStatus(module_data[8]))
            instance._module_ac_phase_loss.append(AlarmStatus(module_data[9]))
            instance._module_env_temp_abnormal.append(AlarmStatus(module_data[10]))
            instance._reserved = [AlarmStatus(status) for status in module_data[11:]]
            offset += 20
        return instance

@dataclass
class DcAnalogData(BaseModel):
    """直流配电模拟量数据类"""
    _supported_fields = {'dc_voltage', 'total_load_current', 'battery_group_1_current',
                         'load_branch_1_current', 'load_branch_2_current', 'load_branch_3_current', 'load_branch_4_current',
                         'battery_total_current', 'battery_group_1_capacity', 'battery_group_1_voltage',
                         'battery_group_1_mid_voltage', 'battery_group_2_mid_voltage', 'battery_group_3_mid_voltage',
                         'battery_group_4_mid_voltage', 'battery_group_1_temperature', 'env_temp_1', 'env_temp_2',
                         'env_humidity_1', 'total_load_power', 'load_power_1', 'load_power_2', 'load_power_3',
                         'load_power_4', 'total_load_energy', 'load_energy_1', 'load_energy_2', 'load_energy_3',
                         'load_energy_4'}
    _unsupported_fields = {
        '_battery_group_2_current': DEFAULT_FLOAT_VALUE,  # 电池组2电流
        '_battery_group_3_current': DEFAULT_FLOAT_VALUE,  # 电池组3电流
        '_battery_group_4_current': DEFAULT_FLOAT_VALUE,  # 电池组4电流
        '_battery_group_5_current': DEFAULT_FLOAT_VALUE,  # 电池组5电流
        '_battery_group_6_current': DEFAULT_FLOAT_VALUE,  # 电池组6电流
        '_battery_group_2_voltage': DEFAULT_FLOAT_VALUE,  # 电池组2电压
        '_battery_group_3_voltage': DEFAULT_FLOAT_VALUE,  # 电池组3电压
        '_battery_group_4_voltage': DEFAULT_FLOAT_VALUE,  # 电池组4电压
        '_battery_group_5_voltage': DEFAULT_FLOAT_VALUE,  # 电池组5电压
        '_battery_group_6_voltage': DEFAULT_FLOAT_VALUE,  # 电池组6电压
        '_battery_group_5_mid_voltage': DEFAULT_FLOAT_VALUE,  # 电池组5中点电压
        '_battery_group_6_mid_voltage': DEFAULT_FLOAT_VALUE,  # 电池组6中点电压
        '_battery_group_2_capacity': DEFAULT_FLOAT_VALUE,  # 电池组2容量
        '_battery_group_3_capacity': DEFAULT_FLOAT_VALUE,  # 电池组3容量
        '_battery_group_4_capacity': DEFAULT_FLOAT_VALUE,  # 电池组4容量
        '_battery_group_5_capacity': DEFAULT_FLOAT_VALUE,  # 电池组5容量
        '_battery_group_6_capacity': DEFAULT_FLOAT_VALUE,  # 电池组6容量
        '_battery_group_2_temperature': DEFAULT_FLOAT_VALUE,  # 电池组2温度
        '_battery_group_3_temperature': DEFAULT_FLOAT_VALUE,  # 电池组3温度
        '_battery_group_4_temperature': DEFAULT_FLOAT_VALUE,  # 电池组4温度
        '_battery_group_5_temperature': DEFAULT_FLOAT_VALUE,  # 电池组5温度
        '_battery_group_6_temperature': DEFAULT_FLOAT_VALUE,  # 电池组6温度
        '_env_temp_3': DEFAULT_FLOAT_VALUE,  # 环境温度3
        '_env_humidity_2': DEFAULT_FLOAT_VALUE,  # 环境湿度2
        '_env_humidity_3': DEFAULT_FLOAT_VALUE,  # 环境湿度3
        '_reserved': [DEFAULT_FLOAT_VALUE] * 2  # 预留参数
    }
    _fixed_fields = {'data_flag': DataFlag.NORMAL, 'battery_group_count': DEFAULT_BATTERY_GROUP_COUNT,
                     'load_branch_count': DEFAULT_LOAD_BRANCH_COUNT, 'user_defined_params_count': DC_USER_DEFINED_PARAMS_COUNT}

    def __init__(self, dc_voltage: float = 0, total_load_current: float = 0,
                 battery_group_1_current: float = 0,
                 load_branch_1_current: float = 0, load_branch_2_current: float = 0,
                 load_branch_3_current: float = 0, load_branch_4_current: float = 0,
                 battery_total_current: float = 0, battery_group_1_capacity: float = 0,
                 battery_group_1_voltage: float = 0, battery_group_1_mid_voltage: float = 0,
                 battery_group_2_mid_voltage: float = 0, battery_group_3_mid_voltage: float = 0,
                 battery_group_4_mid_voltage: float = 0, battery_group_1_temperature: float = 0,
                 env_temp_1: float = 0, env_temp_2: float = 0,
                 env_humidity_1: float = 0, total_load_power: float = 0,
                 load_power_1: float = 0, load_power_2: float = 0,
                 load_power_3: float = 0, load_power_4: float = 0,
                 total_load_energy: float = 0, load_energy_1: float = 0,
                 load_energy_2: float = 0, load_energy_3: float = 0,
                 load_energy_4: float = 0):
        self.dc_voltage = dc_voltage  # 直流输出电压 (V)
        self.total_load_current = total_load_current  # 总负载电流 (A)
        self.battery_group_1_current = battery_group_1_current  # 电池组1电流 (A)
        self.load_branch_1_current = load_branch_1_current  # 直流分路1电流 (A)
        self.load_branch_2_current = load_branch_2_current  # 直流分路2电流 (A)
        self.load_branch_3_current = load_branch_3_current  # 直流分路3电流 (A)
        self.load_branch_4_current = load_branch_4_current  # 直流分路4电流 (A)
        self.battery_total_current = battery_total_current  # 电池总电流 (A)
        self.battery_group_1_capacity = battery_group_1_capacity  # 电池组1容量 (%)
        self.battery_group_1_voltage = battery_group_1_voltage  # 电池组1电压 (V)
        self.battery_group_1_mid_voltage = battery_group_1_mid_voltage  # 电池组1中点电压 (V)
        self.battery_group_2_mid_voltage = battery_group_2_mid_voltage  # 电池组2中点电压 (V)
        self.battery_group_3_mid_voltage = battery_group_3_mid_voltage  # 电池组3中点电压 (V)
        self.battery_group_4_mid_voltage = battery_group_4_mid_voltage  # 电池组4中点电压 (V)
        self.battery_group_1_temperature = battery_group_1_temperature  # 电池组1温度 (℃)
        self.env_temp_1 = env_temp_1  # 环境温度1 (℃)
        self.env_temp_2 = env_temp_2  # 环境温度2 (℃)
        self.env_humidity_1 = env_humidity_1  # 环境湿度1 (%)
        self.total_load_power = total_load_power  # 直流总负载功率 (W)
        self.load_power_1 = load_power_1  # 直流负载1-4功率 (W)
        self.load_power_2 = load_power_2
        self.load_power_3 = load_power_3
        self.load_power_4 = load_power_4
        self.total_load_energy = total_load_energy  # 直流总负载电量 (kWh)
        self.load_energy_1 = load_energy_1  # 直流负载1-4电量 (kWh)
        self.load_energy_2 = load_energy_2
        self.load_energy_3 = load_energy_3
        self.load_energy_4 = load_energy_4
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        return struct.pack('<BBffBfBffffB31f2f',
                           int(self.data_flag.value),
                           int(self.battery_group_count),
                           float(self.dc_voltage),
                           float(self.total_load_current),
                           int(self.battery_group_count),
                           float(self.battery_group_1_current),
                           int(self.load_branch_count),
                           float(self.load_branch_1_current),
                           float(self.load_branch_2_current),
                           float(self.load_branch_3_current),
                           float(self.load_branch_4_current),
                           int(self.user_defined_params_count),
                           float(self.battery_total_current),
                           float(self.battery_group_1_capacity),
                           float(self.battery_group_1_voltage),
                           float(self.battery_group_1_mid_voltage),
                           float(self.battery_group_2_mid_voltage),
                           float(self.battery_group_3_mid_voltage),
                           float(self.battery_group_4_mid_voltage),
                           float(self._battery_group_5_mid_voltage),
                           float(self._battery_group_6_mid_voltage),
                           float(self.battery_group_1_temperature),
                           float(self._battery_group_2_temperature),
                           float(self._battery_group_3_temperature),
                           float(self._battery_group_4_temperature),
                           float(self._battery_group_5_temperature),
                           float(self._battery_group_6_temperature),
                           float(self.env_temp_1),
                           float(self.env_temp_2),
                           float(self._env_temp_3),
                           float(self.env_humidity_1),
                           float(self._env_humidity_2),
                           float(self._env_humidity_3),
                           float(self.total_load_power),
                           float(self.load_power_1),
                           float(self.load_power_2),
                           float(self.load_power_3),
                           float(self.load_power_4),
                           float(self.total_load_energy),
                           float(self.load_energy_1),
                           float(self.load_energy_2),
                           float(self.load_energy_3),
                           float(self.load_energy_4),
                           *self._reserved
                           )

    @classmethod
    def from_bytes(cls, data):
        unpacked = struct.unpack('<BBffBfBffffB31f2f', data)
        instance = cls(
            dc_voltage=float(unpacked[2]),
            total_load_current=float(unpacked[3]),
            battery_group_1_current=float(unpacked[5]),
            load_branch_1_current=float(unpacked[7]),
            load_branch_2_current=float(unpacked[8]),
            load_branch_3_current=float(unpacked[9]),
            load_branch_4_current=float(unpacked[10]),
            battery_total_current=float(unpacked[12]),
            battery_group_1_capacity=float(unpacked[13]),
            battery_group_1_voltage=float(unpacked[14]),
            battery_group_1_mid_voltage=float(unpacked[15]),
            battery_group_2_mid_voltage=float(unpacked[16]),
            battery_group_3_mid_voltage=float(unpacked[17]),
            battery_group_4_mid_voltage=float(unpacked[18]),
            battery_group_1_temperature=float(unpacked[21]),
            env_temp_1=float(unpacked[27]),
            env_temp_2=float(unpacked[28]),
            env_humidity_1=float(unpacked[30]),
            total_load_power=float(unpacked[33]),
            load_power_1=float(unpacked[34]),
            load_power_2=float(unpacked[35]),
            load_power_3=float(unpacked[36]),
            load_power_4=float(unpacked[37]),
            total_load_energy=float(unpacked[38]),
            load_energy_1=float(unpacked[39]),
            load_energy_2=float(unpacked[40]),
            load_energy_3=float(unpacked[41]),
            load_energy_4=float(unpacked[42])
        )
        instance.data_flag = DataFlag(int(unpacked[0]))
        instance.battery_group_count = int(unpacked[1])
        instance.load_branch_count = int(unpacked[6])
        instance.user_defined_params_count = int(unpacked[11])
        instance._battery_group_5_mid_voltage = float(unpacked[19])
        instance._battery_group_6_mid_voltage = float(unpacked[20])
        instance._battery_group_2_temperature = float(unpacked[22])
        instance._battery_group_3_temperature = float(unpacked[23])
        instance._battery_group_4_temperature = float(unpacked[24])
        instance._battery_group_5_temperature = float(unpacked[25])
        instance._battery_group_6_temperature = float(unpacked[26])
        instance._env_temp_3 = float(unpacked[29])
        instance._env_humidity_2 = float(unpacked[31])
        instance._env_humidity_3 = float(unpacked[32])
        instance._reserved = list(unpacked[-2:])  # 最后两个字段作为预留字段
        return instance

@dataclass
class DcAlarmStatus(BaseModel):
    """直流告警状态类"""
    _supported_fields = {
        'dc_voltage_status', 'dc_arrester_status', 'load_fuse_status',
        'battery_group_1_fuse_status', 'battery_group_2_fuse_status',
        'battery_group_3_fuse_status', 'battery_group_4_fuse_status',
        'blvd_status', 'llvd1_status', 'llvd2_status', 'llvd3_status', 'llvd4_status',
        'battery_temp_status', 'battery_temp_sensor_1_status',
        'env_temp_status', 'env_temp_sensor_1_status', 'env_temp_sensor_2_status',
        'env_humidity_status', 'env_humidity_sensor_1_status',
        'door_status', 'water_status', 'smoke_status',
        'digital_input_status_1', 'digital_input_status_2', 'digital_input_status_3',
        'digital_input_status_4', 'digital_input_status_5', 'digital_input_status_6'
    }

    _unsupported_fields = {
        '_dc_comm_failure_status': AlarmStatus.NORMAL,  # 直流屏通讯中断状态
        '_battery_group_charge_overcurrent': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,  # 电池组充电过流状态
        '_battery_group_unbalanced': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,  # 电池组不平衡状态
        '_blvd_impending': AlarmStatus.NORMAL,  # BLVD即将下电状态
        '_llvd1_impending': AlarmStatus.NORMAL,  # LLVD1即将下电状态
        '_llvd2_impending': AlarmStatus.NORMAL,  # LLVD2即将下电状态
        '_llvd3_impending': AlarmStatus.NORMAL,  # LLVD3即将下电状态
        '_llvd4_impending': AlarmStatus.NORMAL,  # LLVD4即将下电状态
        '_battery_temp_sensor_2_status': SensorStatus.NORMAL,  # 电池温度传感器2状态
        '_battery_temp_sensor_3_status': SensorStatus.NORMAL,  # 电池温度传感器3状态
        '_battery_temp_sensor_4_status': SensorStatus.NORMAL,  # 电池温度传感器4状态
        '_battery_temp_sensor_5_status': SensorStatus.NORMAL,  # 电池温度传感器5状态
        '_battery_temp_sensor_6_status': SensorStatus.NORMAL,  # 电池温度传感器6状态
        '_env_temp_sensor_3_status': SensorStatus.NORMAL,  # 环境温度传感器3状态
        '_env_humidity_sensor_2_status': SensorStatus.NORMAL,  # 环境湿度传感器2状态
        '_env_humidity_sensor_3_status': SensorStatus.NORMAL,  # 环境湿度传感器3状态
        '_infrared_status': AlarmStatus.NORMAL,  # 红外告警状态
        '_reserved': [AlarmStatus.NORMAL] * 72  # 预留告警状态
    }

    _fixed_fields = {'data_flag': DataFlag.NORMAL, 'battery_fuse_count': 0, 'user_defined_params_count': 151}

    def __init__(self, dc_voltage_status: VoltageStatus = VoltageStatus.NORMAL,
                 dc_arrester_status: AlarmStatus = AlarmStatus.NORMAL,
                 load_fuse_status: AlarmStatus = AlarmStatus.NORMAL,
                 battery_group_1_fuse_status: AlarmStatus = AlarmStatus.NORMAL,
                 battery_group_2_fuse_status: AlarmStatus = AlarmStatus.NORMAL,
                 battery_group_3_fuse_status: AlarmStatus = AlarmStatus.NORMAL,
                 battery_group_4_fuse_status: AlarmStatus = AlarmStatus.NORMAL,
                 blvd_status: LVDStatus = LVDStatus.NORMAL,
                 llvd1_status: LVDStatus = LVDStatus.NORMAL,
                 llvd2_status: LVDStatus = LVDStatus.NORMAL,
                 llvd3_status: LVDStatus = LVDStatus.NORMAL,
                 llvd4_status: LVDStatus = LVDStatus.NORMAL,
                 battery_temp_status: TempStatus = TempStatus.NORMAL,
                 battery_temp_sensor_1_status: SensorStatus = SensorStatus.NORMAL,
                 env_temp_status: TempStatus = TempStatus.NORMAL,
                 env_temp_sensor_1_status: SensorStatus = SensorStatus.NORMAL,
                 env_temp_sensor_2_status: SensorStatus = SensorStatus.NORMAL,
                 env_humidity_status: AlarmStatus = AlarmStatus.NORMAL,
                 env_humidity_sensor_1_status: SensorStatus = SensorStatus.NORMAL,
                 door_status: AlarmStatus = AlarmStatus.NORMAL,
                 water_status: AlarmStatus = AlarmStatus.NORMAL,
                 smoke_status: AlarmStatus = AlarmStatus.NORMAL,
                 digital_input_status_1: AlarmStatus = AlarmStatus.NORMAL,
                 digital_input_status_2: AlarmStatus = AlarmStatus.NORMAL,
                 digital_input_status_3: AlarmStatus = AlarmStatus.NORMAL,
                 digital_input_status_4: AlarmStatus = AlarmStatus.NORMAL,
                 digital_input_status_5: AlarmStatus = AlarmStatus.NORMAL,
                 digital_input_status_6: AlarmStatus = AlarmStatus.NORMAL):
        # 初始化支持的字段
        self.dc_voltage_status = dc_voltage_status
        self.dc_arrester_status = dc_arrester_status
        self.load_fuse_status = load_fuse_status
        self.battery_group_1_fuse_status = battery_group_1_fuse_status
        self.battery_group_2_fuse_status = battery_group_2_fuse_status
        self.battery_group_3_fuse_status = battery_group_3_fuse_status
        self.battery_group_4_fuse_status = battery_group_4_fuse_status
        self.blvd_status = blvd_status
        self.llvd1_status = llvd1_status
        self.llvd2_status = llvd2_status
        self.llvd3_status = llvd3_status
        self.llvd4_status = llvd4_status
        self.battery_temp_status = battery_temp_status
        self.battery_temp_sensor_1_status = battery_temp_sensor_1_status
        self.env_temp_status = env_temp_status
        self.env_temp_sensor_1_status = env_temp_sensor_1_status
        self.env_temp_sensor_2_status = env_temp_sensor_2_status
        self.env_humidity_status = env_humidity_status
        self.env_humidity_sensor_1_status = env_humidity_sensor_1_status
        self.door_status = door_status
        self.water_status = water_status
        self.smoke_status = smoke_status
        self.digital_input_status_1 = digital_input_status_1
        self.digital_input_status_2 = digital_input_status_2
        self.digital_input_status_3 = digital_input_status_3
        self.digital_input_status_4 = digital_input_status_4
        self.digital_input_status_5 = digital_input_status_5
        self.digital_input_status_6 = digital_input_status_6

        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        # 计算实际需要的格式化字符串
        format_string = '<' # 小端字节序
        format_string += 'B'  # data_flag
        format_string += 'B'  # dc_voltage_status
        format_string += 'B'  # battery_fuse_count
        format_string += 'B'  # user_defined_params_count
        format_string += 'B'  # dc_arrester_status
        format_string += 'B'  # _dc_comm_failure_status
        format_string += 'B'  # load_fuse_status
        format_string += 'BBBB'  # battery_group_1_to_4_fuse_status
        format_string += 'BB'  # battery_group_5_to_6_fuse_status (always NORMAL)
        format_string += 'B' * BATTERY_GROUP_COUNT  # _battery_group_charge_overcurrent
        format_string += 'B' * BATTERY_GROUP_COUNT  # _battery_group_unbalanced
        format_string += 'B' * BATTERY_GROUP_COUNT  # battery_group_lost (always NORMAL)
        format_string += 'BB'  # blvd_status and _blvd_impending
        format_string += 'BB' * LOAD_BRANCH_COUNT  # llvd_status and _llvd_impending for each branch
        format_string += 'B'  # battery_temp_status
        format_string += 'B' * BATTERY_GROUP_COUNT  # battery_temp_sensor_status for each group
        format_string += 'BBB'  # env_temp_status and env_temp_sensor_1_2_status
        format_string += 'B'  # _env_temp_sensor_3_status
        format_string += 'B'  # env_humidity_status
        format_string += 'B' * ENV_HUMIDITY_COUNT  # env_humidity_sensor_status for each sensor
        format_string += 'BBB'  # door_status, water_status, smoke_status
        format_string += 'B'  # _infrared_status
        data = struct.pack(format_string,
                           self.data_flag.value,
                           self.dc_voltage_status.value,
                           self.battery_fuse_count,
                           self.user_defined_params_count,
                           self.dc_arrester_status.value,
                           self._dc_comm_failure_status.value,
                           self.load_fuse_status.value,
                           self.battery_group_1_fuse_status.value,
                           self.battery_group_2_fuse_status.value,
                           self.battery_group_3_fuse_status.value,
                           self.battery_group_4_fuse_status.value,
                           AlarmStatus.NORMAL.value,  # battery_group_5_fuse_status
                           AlarmStatus.NORMAL.value,  # battery_group_6_fuse_status
                           *[status.value for status in self._battery_group_charge_overcurrent],
                           *[status.value for status in self._battery_group_unbalanced],
                           *[AlarmStatus.NORMAL.value] * BATTERY_GROUP_COUNT,  # battery_group_lost
                           self.blvd_status.value,
                           self._blvd_impending.value,
                           self.llvd1_status.value,
                           self._llvd1_impending.value,
                           self.llvd2_status.value,
                           self._llvd2_impending.value,
                           self.llvd3_status.value,
                           self._llvd3_impending.value,
                           self.llvd4_status.value,
                           self._llvd4_impending.value,
                           self.battery_temp_status.value,
                           self.battery_temp_sensor_1_status.value,
                           self._battery_temp_sensor_2_status.value,
                           self._battery_temp_sensor_3_status.value,
                           self._battery_temp_sensor_4_status.value,
                           self._battery_temp_sensor_5_status.value,
                           self._battery_temp_sensor_6_status.value,
                           self.env_temp_status.value,
                           self.env_temp_sensor_1_status.value,
                           self.env_temp_sensor_2_status.value,
                           self._env_temp_sensor_3_status.value,
                           self.env_humidity_status.value,
                           self.env_humidity_sensor_1_status.value,
                           self._env_humidity_sensor_2_status.value,
                           self._env_humidity_sensor_3_status.value,
                           self.door_status.value,
                           self.water_status.value,
                           self.smoke_status.value,
                           self._infrared_status.value)

        # 处理开关量输入1~12告警
        digital_inputs = [
            self.digital_input_status_1.value,
            self.digital_input_status_2.value,
            self.digital_input_status_3.value,
            self.digital_input_status_4.value,
            self.digital_input_status_5.value,
            self.digital_input_status_6.value,
        ]
        # 添加6个无效（正常）状态以凑满12个字节
        digital_inputs.extend([AlarmStatus.NORMAL.value] * 6)

        data += struct.pack('12B', *digital_inputs)
        data += struct.pack('72B', *[status.value for status in self._reserved])

        return data

    @classmethod
    def from_bytes(cls, data):
        if len(data) < 135:
            raise ValueError(f"Data length is too short. Expected at least 135 bytes, but got {len(data)} bytes.")

        unpacked = struct.unpack('<BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB', data[:51])
        instance = cls(
            dc_voltage_status=VoltageStatus(unpacked[1]),
            dc_arrester_status=AlarmStatus(unpacked[4]),
            load_fuse_status=AlarmStatus(unpacked[6]),
            battery_group_1_fuse_status=AlarmStatus(unpacked[7]),
            battery_group_2_fuse_status=AlarmStatus(unpacked[8]),
            battery_group_3_fuse_status=AlarmStatus(unpacked[9]),
            battery_group_4_fuse_status=AlarmStatus(unpacked[10]),
            blvd_status=LVDStatus(unpacked[16]),
            llvd1_status=LVDStatus(unpacked[18]),
            llvd2_status=LVDStatus(unpacked[20]),
            llvd3_status=LVDStatus(unpacked[22]),
            llvd4_status=LVDStatus(unpacked[24]),
            battery_temp_status=TempStatus(unpacked[26]),
            battery_temp_sensor_1_status=SensorStatus(unpacked[27]),
            env_temp_status=TempStatus(unpacked[33]),
            env_temp_sensor_1_status=SensorStatus(unpacked[34]),
            env_temp_sensor_2_status=SensorStatus(unpacked[35]),
            env_humidity_status=AlarmStatus(unpacked[37]),
            env_humidity_sensor_1_status=SensorStatus(unpacked[38]),
            door_status=AlarmStatus(unpacked[41]),
            water_status=AlarmStatus(unpacked[42]),
            smoke_status=AlarmStatus(unpacked[43])
        )
        instance._dc_comm_failure_status = AlarmStatus(unpacked[5])
        instance._battery_group_charge_overcurrent = [AlarmStatus(status) for status in unpacked[11:17]]
        instance._battery_group_unbalanced = [AlarmStatus(status) for status in unpacked[17:23]]
        instance._blvd_impending = AlarmStatus(unpacked[17])
        instance._llvd1_impending = AlarmStatus(unpacked[19])
        instance._llvd2_impending = AlarmStatus(unpacked[21])
        instance._llvd3_impending = AlarmStatus(unpacked[23])
        instance._llvd4_impending = AlarmStatus(unpacked[25])
        instance._battery_temp_sensor_2_status = SensorStatus(unpacked[28])
        instance._battery_temp_sensor_3_status = SensorStatus(unpacked[29])
        instance._battery_temp_sensor_4_status = SensorStatus(unpacked[30])
        instance._battery_temp_sensor_5_status = SensorStatus(unpacked[31])
        instance._battery_temp_sensor_6_status = SensorStatus(unpacked[32])
        instance._env_temp_sensor_3_status = SensorStatus(unpacked[36])
        instance._env_humidity_sensor_2_status = SensorStatus(unpacked[39])
        instance._env_humidity_sensor_3_status = SensorStatus(unpacked[40])
        instance._infrared_status = AlarmStatus(unpacked[44])

        digital_inputs = struct.unpack('12B', data[51:63])
        instance.digital_input_status_1 = AlarmStatus(digital_inputs[0])
        instance.digital_input_status_2 = AlarmStatus(digital_inputs[1])
        instance.digital_input_status_3 = AlarmStatus(digital_inputs[2])
        instance.digital_input_status_4 = AlarmStatus(digital_inputs[3])
        instance.digital_input_status_5 = AlarmStatus(digital_inputs[4])
        instance.digital_input_status_6 = AlarmStatus(digital_inputs[5])

        reserved_data = data[63:135]  # 保留字段总是72字节
        instance._reserved = [AlarmStatus(status) for status in struct.unpack('72B', reserved_data)]

        return instance

    def __str__(self):
        return (f"DcAlarmStatus("
                f"dc_voltage_status={self.dc_voltage_status}, "
                f"dc_arrester_status={self.dc_arrester_status}, "
                f"load_fuse_status={self.load_fuse_status}, "
                f"battery_group_1_fuse_status={self.battery_group_1_fuse_status}, "
                f"battery_group_2_fuse_status={self.battery_group_2_fuse_status}, "
                f"battery_group_3_fuse_status={self.battery_group_3_fuse_status}, "
                f"battery_group_4_fuse_status={self.battery_group_4_fuse_status}, "
                f"blvd_status={self.blvd_status}, "
                f"llvd1_status={self.llvd1_status}, "
                f"llvd2_status={self.llvd2_status}, "
                f"llvd3_status={self.llvd3_status}, "
                f"llvd4_status={self.llvd4_status}, "
                f"battery_temp_status={self.battery_temp_status}, "
                f"battery_temp_sensor_1_status={self.battery_temp_sensor_1_status}, "
                f"env_temp_status={self.env_temp_status}, "
                f"env_temp_sensor_1_status={self.env_temp_sensor_1_status}, "
                f"env_temp_sensor_2_status={self.env_temp_sensor_2_status}, "
                f"env_humidity_status={self.env_humidity_status}, "
                f"env_humidity_sensor_1_status={self.env_humidity_sensor_1_status}, "
                f"door_status={self.door_status}, "
                f"water_status={self.water_status}, "
                f"smoke_status={self.smoke_status}, "
                f"digital_input_status_1={self.digital_input_status_1}, "
                f"digital_input_status_2={self.digital_input_status_2}, "
                f"digital_input_status_3={self.digital_input_status_3}, "
                f"digital_input_status_4={self.digital_input_status_4}, "
                f"digital_input_status_5={self.digital_input_status_5}, "
                f"digital_input_status_6={self.digital_input_status_6})")

    def __repr__(self):
        return self.__str__()

@dataclass
class DcConfigParams(BaseModel):
    """直流配置参数类"""
    _supported_fields = {
        'dc_over_voltage', 'dc_under_voltage', 'time_equalize_charge_enable',
        'time_equalize_duration', 'time_equalize_interval', 'battery_group_number',
        'battery_over_temp', 'battery_under_temp', 'env_over_temp', 'env_under_temp',
        'env_over_humidity', 'env_under_humidity', 'battery_charge_current_limit',
        'float_voltage', 'equalize_voltage', 'battery_off_voltage', 'battery_on_voltage',
        'llvd1_off_voltage', 'llvd1_on_voltage', 'llvd2_off_voltage', 'llvd2_on_voltage',
        'llvd3_off_voltage', 'llvd3_on_voltage', 'llvd4_off_voltage', 'llvd4_on_voltage',
        'battery_capacity', 'battery_test_stop_voltage', 'battery_temp_coeff',
        'battery_temp_center', 'float_to_equalize_coeff', 'equalize_to_float_coeff',
        'llvd1_off_time', 'llvd2_off_time', 'llvd3_off_time', 'llvd4_off_time',
        'load_off_mode'
    }
    _unsupported_fields = {
        '_auto_equalize_charge_enable': EnableStatus.DISABLE,
        '_time_test_enable': EnableStatus.DISABLE,
        '_time_test_interval_high': DEFAULT_INT_VALUE,
        '_time_test_interval_low': DEFAULT_INT_VALUE,
        '_battery_test_stop_time_high': DEFAULT_INT_VALUE,
        '_battery_test_stop_time_low': DEFAULT_INT_VALUE,
        '_battery_group_over_voltage': DEFAULT_FLOAT_VALUE,
        '_battery_group_under_voltage': DEFAULT_FLOAT_VALUE,
        '_battery_group_charge_over_current': DEFAULT_FLOAT_VALUE,
        '_battery_test_stop_capacity': DEFAULT_FLOAT_VALUE,
        '_reserved': [DEFAULT_INT_VALUE] * 55
    }
    _fixed_fields = {
        'battery_group_number_len': 10,  # "第1屏-第10屏电池组数"字段总长度为10字节
        'user_defined_params_count': 67  # "用户自定义数量P"固定为67
    }

    def __init__(self, dc_over_voltage: float = DEFAULT_FLOAT_VALUE, dc_under_voltage: float = DEFAULT_FLOAT_VALUE,
                 time_equalize_charge_enable: EnableStatus = EnableStatus.DISABLE,
                 time_equalize_duration: int = DEFAULT_INT_VALUE, time_equalize_interval: int = DEFAULT_INT_VALUE,
                 battery_group_number: int = DEFAULT_INT_VALUE, battery_over_temp: float = DEFAULT_FLOAT_VALUE,
                 battery_under_temp: float = DEFAULT_FLOAT_VALUE, env_over_temp: float = DEFAULT_FLOAT_VALUE,
                 env_under_temp: float = DEFAULT_FLOAT_VALUE, env_over_humidity: float = DEFAULT_FLOAT_VALUE,
                 env_under_humidity: float = DEFAULT_FLOAT_VALUE,
                 battery_charge_current_limit: float = DEFAULT_FLOAT_VALUE, float_voltage: float = DEFAULT_FLOAT_VALUE,
                 equalize_voltage: float = DEFAULT_FLOAT_VALUE, battery_off_voltage: float = DEFAULT_FLOAT_VALUE,
                 battery_on_voltage: float = DEFAULT_FLOAT_VALUE, llvd1_off_voltage: float = DEFAULT_FLOAT_VALUE,
                 llvd1_on_voltage: float = DEFAULT_FLOAT_VALUE, llvd2_off_voltage: float = DEFAULT_FLOAT_VALUE,
                 llvd2_on_voltage: float = DEFAULT_FLOAT_VALUE, llvd3_off_voltage: float = DEFAULT_FLOAT_VALUE,
                 llvd3_on_voltage: float = DEFAULT_FLOAT_VALUE, llvd4_off_voltage: float = DEFAULT_FLOAT_VALUE,
                 llvd4_on_voltage: float = DEFAULT_FLOAT_VALUE, battery_capacity: float = DEFAULT_FLOAT_VALUE,
                 battery_test_stop_voltage: float = DEFAULT_FLOAT_VALUE, battery_temp_coeff: float = DEFAULT_FLOAT_VALUE,
                 battery_temp_center: float = DEFAULT_FLOAT_VALUE, float_to_equalize_coeff: float = DEFAULT_FLOAT_VALUE,
                 equalize_to_float_coeff: float = DEFAULT_FLOAT_VALUE, llvd1_off_time: float = DEFAULT_FLOAT_VALUE,
                 llvd2_off_time: float = DEFAULT_FLOAT_VALUE, llvd3_off_time: float = DEFAULT_FLOAT_VALUE,
                 llvd4_off_time: float = DEFAULT_FLOAT_VALUE, load_off_mode: LoadOffMode = LoadOffMode.VOLTAGE):
        self.dc_over_voltage = dc_over_voltage  # 直流过压值
        self.dc_under_voltage = dc_under_voltage  # 直流欠压值
        self.time_equalize_charge_enable = time_equalize_charge_enable  # 定时均充使能
        self.time_equalize_duration = time_equalize_duration  # 定时均充时间
        self.time_equalize_interval = time_equalize_interval  # 定时均充间隔
        self.battery_group_number = battery_group_number  # 电池组数
        self.battery_over_temp = battery_over_temp  # 电池过温告警点
        self.battery_under_temp = battery_under_temp  # 电池欠温告警点
        self.env_over_temp = env_over_temp  # 环境过温告警点
        self.env_under_temp = env_under_temp  # 环境欠温告警点
        self.env_over_humidity = env_over_humidity  # 环境过湿告警点
        self.env_under_humidity = env_under_humidity  # 环境欠湿告警点
        self.battery_charge_current_limit = battery_charge_current_limit  # 电池充电限流点
        self.float_voltage = float_voltage  # 浮充电压
        self.equalize_voltage = equalize_voltage  # 均充电压
        self.battery_off_voltage = battery_off_voltage  # 电池下电电压
        self.battery_on_voltage = battery_on_voltage  # 电池上电电压
        self.llvd1_off_voltage = llvd1_off_voltage  # LLVD1下电电压
        self.llvd1_on_voltage = llvd1_on_voltage  # LLVD1上电电压
        self.llvd2_off_voltage = llvd2_off_voltage  # LLVD2下电电压
        self.llvd2_on_voltage = llvd2_on_voltage  # LLVD2上电电压
        self.llvd3_off_voltage = llvd3_off_voltage  # LLVD3下电电压
        self.llvd3_on_voltage = llvd3_on_voltage  # LLVD3上电电压
        self.llvd4_off_voltage = llvd4_off_voltage  # LLVD4下电电压
        self.llvd4_on_voltage = llvd4_on_voltage  # LLVD4上电电压
        self.battery_capacity = battery_capacity  # 每组电池额定容量
        self.battery_test_stop_voltage = battery_test_stop_voltage  # 电池测试终止电压
        self.battery_temp_coeff = battery_temp_coeff  # 电池组温补系数
        self.battery_temp_center = battery_temp_center  # 电池温补中心点
        self.float_to_equalize_coeff = float_to_equalize_coeff  # 浮充转均充系数
        self.equalize_to_float_coeff = equalize_to_float_coeff  # 均充转浮充系数
        self.llvd1_off_time = llvd1_off_time  # LLVD1下电时间
        self.llvd2_off_time = llvd2_off_time  # LLVD2下电时间
        self.llvd3_off_time = llvd3_off_time  # LLVD3下电时间
        self.llvd4_off_time = llvd4_off_time  # LLVD4下电时间
        self.load_off_mode = load_off_mode  # 负载下电模式

        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self) -> bytes:
        return struct.pack(
            '<ffBBBBBBBBBBB10BfffffffffffffffffffffffffffffffffB55B',
            self.dc_over_voltage,
            self.dc_under_voltage,
            self.user_defined_params_count,
            self.time_equalize_charge_enable.value,
            self._auto_equalize_charge_enable.value,
            self._time_test_enable.value,
            self._time_test_interval_high,
            self._time_test_interval_low,
            self._battery_test_stop_time_high,
            self._battery_test_stop_time_low,
            self.time_equalize_duration,
            self.time_equalize_interval >> 8,
            self.time_equalize_interval & 0xFF,
            self.battery_group_number,
            *([0] * 9),  # 填充剩余的9个电池组数
            self._battery_group_over_voltage,
            self._battery_group_under_voltage,
            self._battery_group_charge_over_current,
            self.battery_over_temp,
            self.battery_under_temp,
            self.env_over_temp,
            self.env_under_temp,
            self.env_over_humidity,
            self.env_under_humidity,
            self.battery_charge_current_limit,
            self.float_voltage,
            self.equalize_voltage,
            self.battery_off_voltage,
            self.battery_on_voltage,
            self.llvd1_off_voltage,
            self.llvd1_on_voltage,
            self.llvd2_off_voltage,
            self.llvd2_on_voltage,
            self.llvd3_off_voltage,
            self.llvd3_on_voltage,
            self.llvd4_off_voltage,
            self.llvd4_on_voltage,
            self.battery_capacity,
            self.battery_test_stop_voltage,
            self._battery_test_stop_capacity,
            self.battery_temp_coeff,
            self.battery_temp_center,
            self.float_to_equalize_coeff,
            self.equalize_to_float_coeff,
            self.llvd1_off_time,
            self.llvd2_off_time,
            self.llvd3_off_time,
            self.llvd4_off_time,
            self.load_off_mode.value,
            *self._reserved
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> 'DcConfigParams':

        if len(data) != 217:
            print(f"Invalid data length: {len(data)}, expected 217")
            raise ValueError("Invalid data length")

        values = struct.unpack('<ffBBBBBBBBBBB10BfffffffffffffffffffffffffffffffffB55B', data)

        instance = cls(
            dc_over_voltage=values[0],
            dc_under_voltage=values[1],
            time_equalize_charge_enable=EnableStatus(values[3]),
            time_equalize_duration=values[10],
            time_equalize_interval=(values[11] << 8) | values[12],
            battery_group_number=values[13],
            battery_over_temp=values[17],
            battery_under_temp=values[18],
            env_over_temp=values[19],
            env_under_temp=values[20],
            env_over_humidity=values[21],
            env_under_humidity=values[22],
            battery_charge_current_limit=values[23],
            float_voltage=values[24],
            equalize_voltage=values[25],
            battery_off_voltage=values[26],
            battery_on_voltage=values[27],
            llvd1_off_voltage=values[28],
            llvd1_on_voltage=values[29],
            llvd2_off_voltage=values[30],
            llvd2_on_voltage=values[31],
            llvd3_off_voltage=values[32],
            llvd3_on_voltage=values[33],
            llvd4_off_voltage=values[34],
            llvd4_on_voltage=values[35],
            battery_capacity=values[36],
            battery_test_stop_voltage=values[37],
            battery_temp_coeff=values[39],
            battery_temp_center=values[40],
            float_to_equalize_coeff=values[41],
            equalize_to_float_coeff=values[42],
            llvd1_off_time=values[43],
            llvd2_off_time=values[44],
            llvd3_off_time=values[45],
            llvd4_off_time=values[46],
            load_off_mode=LoadOffMode(values[47])
        )

        # Set unsupported fields
        instance.user_defined_params_count = values[2]
        instance._auto_equalize_charge_enable = EnableStatus(values[4])
        instance._time_test_enable = EnableStatus(values[5])
        instance._time_test_interval_high = values[6]
        instance._time_test_interval_low = values[7]
        instance._battery_test_stop_time_high = values[8]
        instance._battery_test_stop_time_low = values[9]
        instance._battery_group_over_voltage = values[14]
        instance._battery_group_under_voltage = values[15]
        instance._battery_group_charge_over_current = values[16]
        instance._battery_test_stop_capacity = values[38]
        instance._reserved = list(values[48:])

        return instance

@dataclass
class ControlRectModule(BaseModel):
    """整流模块控制类"""
    _supported_fields = {'module_id', 'control_type'}

    def __init__(self, module_id: int = DEFAULT_INT_VALUE, control_type: RectModuleControlType = RectModuleControlType.ON):
        self.module_id = module_id  # 模块ID
        self.control_type = control_type  # 控制类型
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        return struct.pack('<BB', self.module_id, self.control_type.value)

    @classmethod
    def from_bytes(cls, data):
        module_id, control_type = struct.unpack('<BB', data)
        return cls(module_id, RectModuleControlType(control_type))

@dataclass
class SystemControlState(BaseModel):
    """系统控制状态类"""
    _supported_fields = {'state'}

    def __init__(self, state: SystemControlStateModel = SystemControlStateModel.AUTO):
        self.state = state  # 系统控制状态
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        return struct.pack('<B', self.state.value)

    @classmethod
    def from_bytes(cls, data):
        state, = struct.unpack('<B', data)
        return cls(SystemControlStateModel(state))

@dataclass
class AlarmSoundEnable(BaseModel):
    """告警音使能控制类"""
    _supported_fields = {'enable'}

    def __init__(self, enable: EnableStatus = EnableStatus.ENABLE):
        self.enable = enable  # 使能状态
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        return struct.pack('<B', self.enable.value)

    @classmethod
    def from_bytes(cls, data):
        enable, = struct.unpack('<B', data)
        return cls(EnableStatus(enable))

@dataclass
class EnergyParams(BaseModel):
    """节能参数类"""
    _supported_fields = {'energy_saving', 'min_working_modules', 'module_switch_cycle',
                         'module_best_efficiency_point', 'module_redundancy_point'}
    _unsupported_fields = {'_reserved': [DEFAULT_INT_VALUE] * 18}

    def __init__(self, energy_saving: EnableStatus = EnableStatus.ENABLE,
                 min_working_modules: int = DEFAULT_INT_VALUE,
                 module_switch_cycle: int = DEFAULT_INT_VALUE,
                 module_best_efficiency_point: int = DEFAULT_INT_VALUE,
                 module_redundancy_point: int = DEFAULT_INT_VALUE):
        self.energy_saving = energy_saving  # 节能允许
        self.min_working_modules = min_working_modules  # 最小工作模块数
        self.module_switch_cycle = module_switch_cycle  # 模块循环开关周期
        self.module_best_efficiency_point = module_best_efficiency_point  # 模块最佳效率点
        self.module_redundancy_point = module_redundancy_point  # 模块冗余点
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        return struct.pack('<BBHBB18B',
                           self.energy_saving.value,
                           self.min_working_modules,
                           self.module_switch_cycle,
                           self.module_best_efficiency_point,
                           self.module_redundancy_point,
                           *self._reserved
                           )

    @classmethod
    def from_bytes(cls, data):
        unpacked = struct.unpack('<BBHBB18B', data)
        instance = cls(
            energy_saving=EnableStatus(unpacked[0]),
            min_working_modules=unpacked[1],
            module_switch_cycle=unpacked[2],
            module_best_efficiency_point=unpacked[3],
            module_redundancy_point=unpacked[4]
        )
        instance._reserved = list(unpacked[5:])
        return instance

@dataclass
class SystemControl(BaseModel):
    """系统控制类"""
    _supported_fields = {'control_type'}

    def __init__(self, control_type: SystemControlType = SystemControlType.RESET):
        self.control_type = control_type  # 控制类型
        super().__init__()  # 调用父类的__init__方法来初始化unsupported和fixed字段

    def to_bytes(self):
        return struct.pack('<B', self.control_type.value)

    @classmethod
    def from_bytes(cls, data):
        control_type, = struct.unpack('<B', data)
        return cls(SystemControlType(control_type))

# 文件结束