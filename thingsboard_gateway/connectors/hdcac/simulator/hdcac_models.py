from enum import Enum
import struct
from dataclasses import dataclass
import datetime
import logging
from typing import Dict, Any, Set
import json

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class DataFlag(Enum):
    """数据标志枚举类"""
    NORMAL = 0  # 数据标志,0表示正常

class AlarmStatus(Enum):
    """告警状态枚举类"""
    NORMAL = 0x00  # 正常
    ALARM = 0xF0    # 故障
    INVALID = 0x20  # 无此告警

class SwitchStatus(Enum):
    """开关状态枚举类"""
    OFF = 0x00       # 关
    ON = 0x01      # 开
    INVALID = 0x20  # 无此设备
    CUSTOM = 0x80  # 用户自定义起始值

class RemoteCommand(Enum):
    """遥控命令枚举类"""
    ON = 0x10         # 开机
    OFF = 0x1F        # 关机
    COOLING_ON = 0x20  # 制冷开
    COOLING_OFF = 0x2F # 制冷关
    HEATING_ON = 0x30  # 制热开
    HEATING_OFF = 0x3F # 制热关

class ConfigParamType(Enum):
    """配置参数类型枚举类"""
    AC_START_TEMP = 0x80       # 空调开启温度
    AC_TEMP_HYSTERESIS = 0x81  # 空调灵敏点
    HEAT_START_TEMP = 0x82     # 加热开启温度
    HEAT_HYSTERESIS = 0x83     # 加热灵敏度
    HIGH_TEMP_ALARM = 0x84     # 高温告警点
    LOW_TEMP_ALARM = 0x85      # 低温告警点

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


    def to_bytes(self):
        """将对象转换为字节串"""
        raise NotImplementedError("Subclasses must implement to_bytes method")

    @classmethod
    def from_bytes(cls, data):
        """从字节串创建对象"""
        raise NotImplementedError("Subclasses must implement from_bytes method")

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
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON string: {data}")

        if not isinstance(data, dict):
            raise TypeError(f"Expected dict or JSON string, got {type(data)}")

        instance = cls()
        for k, v in data.items():
            if k in cls._supported_fields and k not in cls._fixed_fields:
                field_type = type(getattr(instance, k, None))
                if issubclass(field_type, Enum):
                    # 处理枚举类型
                    instance._set_enum_field(k, v, field_type)
                elif isinstance(getattr(instance, k), list):
                    # 处理列表类型（可能是枚举列表）
                    instance._set_list_field(k, v)
                else:
                    # 对于其他类型，尝试直接赋值
                    setattr(instance, k, v)
        instance._init_unsupported_fields()
        instance._init_fixed_fields()
        return instance

    def _set_enum_field(self, field_name, value, enum_type):
        """设置枚举字段的值"""
        try:
            setattr(self, field_name, self._convert_to_enum(value, enum_type))
        except ValueError as e:
            raise ValueError(f"Error setting field {field_name}: {str(e)}")

    def _set_list_field(self, field_name, value):
        """设置列表字段的值"""
        if not isinstance(value, list):
            raise ValueError(f"Expected list for field {field_name}, got {type(value)}")

        current_value = getattr(self, field_name)
        if not current_value:
            setattr(self, field_name, value)
            return

        # 假设列表中的所有元素类型相同，检查第一个元素
        elem_type = type(current_value[0])
        if issubclass(elem_type, Enum):
            # 处理枚举列表
            try:
                new_value = [self._convert_to_enum(item, elem_type) for item in value]
                setattr(self, field_name, new_value)
            except ValueError as e:
                raise ValueError(f"Error in list field {field_name}: {str(e)}")
        else:
            # 非枚举列表，直接赋值
            setattr(self, field_name, value)

    def _convert_to_enum(self, value, enum_type):
        """将给定的值转换为指定的枚举类型"""
        if isinstance(value, str):
            try:
                return enum_type[value.upper()]
            except KeyError:
                raise ValueError(f"Invalid enum name '{value}' for {enum_type.__name__}")
        else:
            try:
                return enum_type(value)
            except ValueError:
                raise ValueError(f"Invalid enum value {value} for {enum_type.__name__}")

    def __str__(self):
        """返回对象的字符串表示"""
        class_name = self.__class__.__name__
        attributes = []
        for field in self._supported_fields:
            value = getattr(self, field)
            if isinstance(value, Enum):
                value = value.name
            elif isinstance(value, list) and value and isinstance(value[0], Enum):
                value = [item.name for item in value]
            attributes.append(f"{field}={value}")
        return f"{class_name}({', '.join(attributes)})"

@dataclass
class AcAnalogData(BaseModel):
    """空调模拟量数据类"""
    _supported_fields = {'cabinet_temp', 'supply_temp', 'voltage', 'current'}
    _fixed_fields = {'data_flag': DataFlag.NORMAL}

    def __init__(self, cabinet_temp: int = 0, supply_temp: int = 0,
                 voltage: int = 0, current: int = 0):
        super().__init__()
        self.cabinet_temp = cabinet_temp   # 机柜温度（回风温度）,2字节有符号整数
        self.supply_temp = supply_temp   # 空调送风温度,2字节有符号整数
        self.voltage = voltage   # 交流电压,2字节无符号整数
        self.current = current   # （当前实时压缩机工作电流或上一次压缩机工作电流）,2字节无符号整数

    def to_bytes(self) -> bytes:
        return struct.pack('<BhhHH', self.data_flag.value, int(self.cabinet_temp),
                           int(self.supply_temp), int(self.voltage), int(self.current))

    @classmethod
    def from_bytes(cls, data: bytes):
        _, cabinet_temp, supply_temp, voltage, current = struct.unpack('<BhhHH', data)
        return cls(cabinet_temp, supply_temp, voltage, current)

    def to_dict(self):
        return {
            'cabinet_temp': self.cabinet_temp / 10,
            'supply_temp': self.supply_temp / 10,
            'voltage': self.voltage,
            'current': self.current
        }
@dataclass
class AcAlarmStatus(BaseModel):
    """空调告警状态类"""
    _supported_fields = {'compressor_alarm', 'high_temp', 'low_temp',
                         'heater_alarm', 'sensor_fault', 'over_voltage', 'under_voltage'}
    _fixed_fields = {'data_flag': DataFlag.NORMAL}
    _unsupported_fields = {'reserved': AlarmStatus.NORMAL}

    def __init__(self, compressor_alarm: AlarmStatus = AlarmStatus.NORMAL,
                 high_temp: AlarmStatus = AlarmStatus.NORMAL,
                 low_temp: AlarmStatus = AlarmStatus.NORMAL,
                 heater_alarm: AlarmStatus = AlarmStatus.NORMAL,
                 sensor_fault: AlarmStatus = AlarmStatus.NORMAL,
                 over_voltage: AlarmStatus = AlarmStatus.NORMAL,
                 under_voltage: AlarmStatus = AlarmStatus.NORMAL):
        super().__init__()
        self.compressor_alarm = compressor_alarm  # 制冷告警,1字节
        self.high_temp = high_temp   # 高温告警,1字节
        self.low_temp = low_temp   # 低温告警,1字节
        self.heater_alarm = heater_alarm   # 加热器告警,1字节
        self.sensor_fault = sensor_fault   # 温度传感器故障告警,1字节
        self.over_voltage = over_voltage    # 过电压告警,1字节
        self.under_voltage = under_voltage  # 欠电压告警,1字节

    def to_bytes(self) -> bytes:
        return struct.pack('<BBBBBBBBBB', self.data_flag.value,
                           self.compressor_alarm.value,
                           self.high_temp.value,
                           self.low_temp.value,
                           self.heater_alarm.value,
                           self.sensor_fault.value,
                           self.over_voltage.value,
                           self.under_voltage.value,
                           self.reserved.value,
                           self.reserved.value)  # 预留两个字节

    @classmethod
    def from_bytes(cls, data: bytes):
        (_, compressor_alarm, high_temp, low_temp, heater_alarm,
         sensor_fault, over_voltage, under_voltage, _, _) = struct.unpack('<BBBBBBBBBB', data)
        return cls(AlarmStatus(compressor_alarm), AlarmStatus(high_temp),
                   AlarmStatus(low_temp), AlarmStatus(heater_alarm), AlarmStatus(sensor_fault),
                   AlarmStatus(over_voltage), AlarmStatus(under_voltage))

@dataclass
class AcRunStatus(BaseModel):
    """获取开关输入状态/空调运行状态类"""
    _supported_fields = {'air_conditioner', 'indoor_fan', 'outdoor_fan', 'heater'}
    _fixed_fields = {'data_flag': DataFlag.NORMAL}

    def __init__(self, air_conditioner: SwitchStatus = SwitchStatus.OFF,
                 indoor_fan: SwitchStatus = SwitchStatus.OFF,
                 outdoor_fan: SwitchStatus = SwitchStatus.OFF,
                 heater: SwitchStatus = SwitchStatus.OFF):
        super().__init__()
        self.air_conditioner = air_conditioner  # 机柜空调设备状态,1字节
        self.indoor_fan = indoor_fan   # 内风机状态,1字节
        self.outdoor_fan = outdoor_fan   # 外风机状态,1字节
        self.heater = heater   # 加热状态,1字节

    def to_bytes(self) -> bytes:
        return struct.pack('<BBBBB', self.data_flag.value,
                           self.air_conditioner.value, self.indoor_fan.value,
                           self.outdoor_fan.value, self.heater.value)

    @classmethod
    def from_bytes(cls, data: bytes):
        _, air_conditioner, indoor_fan, outdoor_fan, heater = struct.unpack('<BBBBB', data)
        return cls(SwitchStatus(air_conditioner), SwitchStatus(indoor_fan),
                   SwitchStatus(outdoor_fan), SwitchStatus(heater))

    def to_dict(self):
        return {
            'air_conditioner': self.air_conditioner.name,
            'indoor_fan': self.indoor_fan.name,
            'outdoor_fan': self.outdoor_fan.name,
            'heater': self.heater.name,
            'cooling': SwitchStatusself.air_conditioner== SwitchStatus.ON and self.heater == SwitchStatus.OFF
        }
    def to_dict(self):
        base_dict = super().to_dict()
        base_dict['cooling'] = self._determine_cooling_status().name
        return base_dict

    @property
    def cooling(self):
        return (self.air_conditioner == SwitchStatus.ON
                and self.outdoor_fan == SwitchStatus.ON
                and self.heater == SwitchStatus.OFF)

    def _determine_cooling_status(self) -> SwitchStatus:
        if self.cooling:
            return SwitchStatus.ON
        return SwitchStatus.OFF

@dataclass
class AcConfigParams(BaseModel):
    """空调配置参数类"""
    _supported_fields = {'start_temp', 'temp_hysteresis', 'heater_start_temp',
                         'heater_hysteresis', 'high_temp_alarm', 'low_temp_alarm'}

    def __init__(self, start_temp: int = 0, temp_hysteresis: int = 0,
                 heater_start_temp: int = 0, heater_hysteresis: int = 0,
                 high_temp_alarm: int = 0, low_temp_alarm: int = 0):
        super().__init__()
        self.start_temp = start_temp   # 空调开启温度,2字节有符号整数
        self.temp_hysteresis = temp_hysteresis   # 空调灵敏点,2字节有符号整数
        self.heater_start_temp = heater_start_temp # 加热开启温度,2字节有符号整数
        self.heater_hysteresis = heater_hysteresis   # 加热灵敏度,2字节有符号整数
        self.high_temp_alarm = high_temp_alarm   # 高温告警点,2字节有符号整数
        self.low_temp_alarm = low_temp_alarm     # 低温告警点,2字节有符号整数

    def to_bytes(self) -> bytes:
        return struct.pack('<hhhhhh', int(self.start_temp), int(self.temp_hysteresis),
                           int(self.heater_start_temp), int(self.heater_hysteresis),
                           int(self.high_temp_alarm), int(self.low_temp_alarm))

    @classmethod
    def from_bytes(cls, data: bytes):
        start_temp, temp_hysteresis, heater_start_temp, heater_hysteresis, high_temp_alarm, low_temp_alarm = struct.unpack('<hhhhhh', data)
        return cls(start_temp, temp_hysteresis, heater_start_temp,
                   heater_hysteresis, high_temp_alarm, low_temp_alarm)

    def to_dict(self):
        return {
            'start_temp': self.start_temp / 10,
            'temp_hysteresis': self.temp_hysteresis / 10,
            'heater_start_temp': self.heater_start_temp  / 10,
            'heater_hysteresis': self.heater_hysteresis / 10,
            'high_temp_alarm': self.high_temp_alarm / 10,
            'low_temp_alarm': self.low_temp_alarm / 10
        }
@dataclass
class RemoteControl(BaseModel):
    """遥控控制类"""
    _supported_fields = {'command'}

    def __init__(self, command: RemoteCommand = RemoteCommand.OFF):
        super().__init__()
        self.command = command   # 遥控命令,1字节

    def to_bytes(self) -> bytes:
        return struct.pack('<B', self.command.value)

    @classmethod
    def from_bytes(cls, data: bytes):
        command, = struct.unpack('<B', data)
        return cls(RemoteCommand(command))

@dataclass
class DateTime(BaseModel):
    """日期时间类"""
    _supported_fields = {'year', 'month', 'day', 'hour', 'minute', 'second'}

    def __init__(self, year: int = 1970, month: int = 1, day: int = 1,
                 hour: int = 0, minute: int = 0, second: int = 0):
        super().__init__()
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second

    def to_bytes(self) -> bytes:
        return struct.pack('>HBBBBB', self.year, self.month, self.day, self.hour, self.minute, self.second)

    @property
    def datetime(self) -> datetime.datetime:
        return datetime.datetime(self.year, self.month, self.day, self.hour, self.minute, self.second)

    @classmethod
    def from_bytes(cls, data: bytes):
        year, month, day, hour, minute, second = struct.unpack('>HBBBBB', data)
        return cls(year, month, day, hour, minute, second)

@dataclass
class ConfigParam(BaseModel):
    """配置参数类"""
    _supported_fields = {'param_type', 'param_value'}

    def __init__(self, param_type: ConfigParamType, param_value: int):
        super().__init__()
        self.param_type = param_type    # 参数类型,1字节
        self.param_value = param_value  # 参数值,2字节有符号整数

    def to_bytes(self):
        return struct.pack('<Bh', self.param_type.value, self.param_value)

    @classmethod
    def from_bytes(cls, data):
        param_type, param_value = struct.unpack('<Bh', data)
        return cls(ConfigParamType(param_type), param_value)

@dataclass
class DeviceAddress(BaseModel):
    """设备地址类"""
    _supported_fields = {'address'}

    def __init__(self, address: int):
        super().__init__()
        self.address = address  # 新设备地址,1字节

    def to_bytes(self):
        return struct.pack('<B', self.address)

    @classmethod
    def from_bytes(cls, data):
        address, = struct.unpack('<B', data)
        return cls(address)

@dataclass
class SoftwareVersion(BaseModel):
    """软件版本信息类"""
    _supported_fields = {'major', 'minor'}

    def __init__(self, major: int, minor: int):
        super().__init__()
        self.major = major  # 主版本号,1字节
        self.minor = minor  # 次版本号,1字节

    def to_bytes(self):
        return struct.pack('BB', self.major, self.minor)

    @classmethod
    def from_bytes(cls, data):
        major, minor = struct.unpack('BB', data)
        return cls(major, minor)

    def __str__(self):
        return f"{self.major}.{self.minor}"

@dataclass
class ManufacturerInfo(BaseModel):
    """设备厂商信息类"""
    _supported_fields = {'device_name', 'software_version', 'manufacturer'}

    def __init__(self, device_name: str, software_version: SoftwareVersion, manufacturer: str):
        super().__init__()
        self.device_name = device_name    # 设备名称,10字节
        self.software_version = software_version  # 厂商软件版本,2字节
        self.manufacturer = manufacturer    # 厂商名称,20字节

    def to_bytes(self):
        data = bytearray()
        data.extend((self.device_name.encode('ascii')[:10]).ljust(10, b'\x00'))
        data.extend(self.software_version.to_bytes())
        data.extend((self.manufacturer.encode('ascii')[:20]).ljust(20, b'\x00'))
        return bytes(data)

    @classmethod
    def from_bytes(cls, data):
        device_name = data[:10].decode('ascii').rstrip('\x00')
        software_version = SoftwareVersion.from_bytes(data[10:12])
        manufacturer = data[12:32].decode('ascii').rstrip('\x00')
        return cls(device_name, software_version, manufacturer)

    def to_dict(self):
        return {
            'device_name': self.device_name,
            'software_version': self.software_version.to_dict(),
            'manufacturer': self.manufacturer
        }