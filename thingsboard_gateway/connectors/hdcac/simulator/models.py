from enum import Enum
from typing import List
import struct  
from dataclasses import dataclass
import datetime
import logging

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class DataFlag(Enum):
    NORMAL = 0  # 数据标志,0表示正常

class AlarmStatus(Enum):
    NORMAL = 0   # 正常  
    ALARM = 0xF0    # 告警
    INVALID = 0x20  # 无效值

class SwitchStatus(Enum):
    OFF = 0       # 关
    ON = 1      # 开
    INVALID = 0x20  # 无效值

class EnableStatus(Enum):  
    DISABLE = 0  # 禁止
    ENABLE = 1   # 使能

class VoltageStatus(Enum):
    NORMAL = 0   # 正常  
    OVER = 1    # 过压
    UNDER = 2   # 欠压
    INVALID = 0x20  # 无效值

class SensorStatus(Enum):
    NORMAL = 0   # 正常
    ALARM = 0xF0  # 故障
    INVALID = 0x20  # 无效值

@dataclass
class AcAnalogData:
    def __init__(self, data_flag: DataFlag, cabinet_temp: float, supply_temp: float,
                 voltage: int, current: int):
        self.data_flag = data_flag   # 数据标志,固定为0,1字节
        self.cabinet_temp = cabinet_temp   # 机柜温度,2字节有符号整数
        self.supply_temp = supply_temp   # 送风温度,2字节有符号整数
        self.voltage = voltage   # 交流电压,2字节无符号整数  
        self.current = current   # 工作电流,2字节无符号整数

    def to_bytes(self):
        return struct.pack('<BhhHH', self.data_flag.value, int(self.cabinet_temp*10), 
                           int(self.supply_temp*10), self.voltage, self.current)
  
    @classmethod
    def from_bytes(cls, data):
        data_flag, cabinet_temp, supply_temp, voltage, current = struct.unpack('<BhhHH', data)
        return cls(DataFlag(data_flag), cabinet_temp/10.0, supply_temp/10.0, voltage, current) 
        
    def to_dict(self):
        return {
            "data_flag": self.data_flag.name,  
            "cabinet_temp": self.cabinet_temp,
            "supply_temp": self.supply_temp,
            "voltage": self.voltage,
            "current": self.current
        }
        
@dataclass    
class AcAlarmStatus:
    def __init__(self, data_flag: DataFlag, compressor_alarm: AlarmStatus,
                 high_temp: AlarmStatus, low_temp: AlarmStatus,  
                 heater_alarm: AlarmStatus, sensor_fault: AlarmStatus,
                 over_voltage: AlarmStatus, under_voltage: AlarmStatus,
                 reserved: AlarmStatus):
        self.data_flag = data_flag   # 数据标志,固定为0,1字节
        self.compressor_alarm = compressor_alarm  # 制冷告警,1字节  
        self.high_temp = high_temp   # 高温告警,1字节
        self.low_temp = low_temp   # 低温告警,1字节
        self.heater_alarm = heater_alarm   # 加热器告警,1字节
        self.sensor_fault = sensor_fault   # 温度传感器故障告警,1字节  
        self.over_voltage = over_voltage    # 过电压告警,1字节
        self.under_voltage = under_voltage  # 欠电压告警,1字节
        self.reserved = reserved   # 预留,1字节
        
    def to_bytes(self):
        return struct.pack('<BBBBBBBBB', self.data_flag.value, self.compressor_alarm.value, 
                           self.high_temp.value, self.low_temp.value, self.heater_alarm.value,
                           self.sensor_fault.value, self.over_voltage.value,
                           self.under_voltage.value, self.reserved.value)
 
    @classmethod
    def from_bytes(cls, data):
        (data_flag, compressor_alarm, high_temp, low_temp, heater_alarm,
        sensor_fault, over_voltage, under_voltage, reserved) = struct.unpack('<BBBBBBBBB', data)
        return cls(DataFlag(data_flag), AlarmStatus(compressor_alarm), AlarmStatus(high_temp), 
                   AlarmStatus(low_temp), AlarmStatus(heater_alarm), AlarmStatus(sensor_fault),
                   AlarmStatus(over_voltage), AlarmStatus(under_voltage),
                   AlarmStatus(reserved))

    def to_dict(self):
        return {
            "data_flag": self.data_flag.name,
            "compressor_alarm": self.compressor_alarm.name,  
            "high_temp": self.high_temp.name,
            "low_temp": self.low_temp.name,
            "heater_alarm": self.heater_alarm.name,  
            "sensor_fault": self.sensor_fault.name,
            "over_voltage": self.over_voltage.name,
            "under_voltage": self.under_voltage.name,
            "reserved": self.reserved.name  
        }

@dataclass
class AcRunStatus:
    def __init__(self, air_conditioner: SwitchStatus, indoor_fan: SwitchStatus, 
                 outdoor_fan: SwitchStatus, heater: SwitchStatus):
        self.air_conditioner = air_conditioner  # 空调开关机状态,1字节
        self.indoor_fan = indoor_fan   # 内风机状态,1字节
        self.outdoor_fan = outdoor_fan   # 外风机状态,1字节
        self.heater = heater   # 加热状态,1字节

    def to_bytes(self):
        return struct.pack('<BBBB', self.air_conditioner.value, self.indoor_fan.value, 
                           self.outdoor_fan.value, self.heater.value)

    @classmethod
    def from_bytes(cls, data):
        air_conditioner, indoor_fan, outdoor_fan, heater = struct.unpack('<BBBB', data)
        return cls(SwitchStatus(air_conditioner), SwitchStatus(indoor_fan),
                   SwitchStatus(outdoor_fan), SwitchStatus(heater)) 

    def to_dict(self):
        return {
            "air_conditioner": self.air_conditioner.name, 
            "indoor_fan": self.indoor_fan.name,
            "outdoor_fan": self.outdoor_fan.name,
            "heater": self.heater.name
        }
        
@dataclass
class AcConfigParams:
   def __init__(self, start_temp: int, temp_hysteresis: int, heater_start_temp: int,
                heater_hysteresis: int, high_temp_alarm: int, low_temp_alarm: int):
       self.start_temp = start_temp   # 空调开启温度,2字节有符号整数,0.1度
       self.temp_hysteresis = temp_hysteresis   # 空调停止回差,2字节有符号整数,0.1度  
       self.heater_start_temp = heater_start_temp # 加热开启温度,2字节有符号整数,0.1度
       self.heater_hysteresis = heater_hysteresis   # 加热停止回差,2字节有符号整数,0.1度
       self.high_temp_alarm = high_temp_alarm   # 高温告警点,2字节有符号整数,0.1度 
       self.low_temp_alarm = low_temp_alarm     # 低温告警点,2字节有符号整数,0.1度
       
   def to_bytes(self): 
       return struct.pack('<hhhhhh', self.start_temp, self.temp_hysteresis, 
                          self.heater_start_temp, self.heater_hysteresis,
                          self.high_temp_alarm, self.low_temp_alarm)

   @classmethod
   def from_bytes(cls, data):
       start_temp, temp_hysteresis, heater_start_temp, heater_hysteresis, high_temp_alarm, low_temp_alarm = struct.unpack('<hhhhhh', data)
       return cls(start_temp, temp_hysteresis, heater_start_temp,
                  heater_hysteresis, high_temp_alarm, low_temp_alarm)

   def to_dict(self):
       return {
           "start_temp": self.start_temp / 10.0,
           "temp_hysteresis": self.temp_hysteresis / 10.0, 
           "heater_start_temp": self.heater_start_temp / 10.0,
           "heater_hysteresis": self.heater_hysteresis / 10.0,
           "high_temp_alarm": self.high_temp_alarm / 10.0,
           "low_temp_alarm": self.low_temp_alarm / 10.0
       }

class RemoteCommand(Enum):
    ON = 0x10         # 开机 
    OFF = 0x1F        # 关机
    COOLING_ON = 0x20  # 制冷开  
    COOLING_OFF = 0x2F # 制冷关
    HEATING_ON = 0x30  # 制热开
    HEATING_OFF = 0x3F # 制热关

@dataclass
class RemoteControl:
   def __init__(self, command: RemoteCommand):
       self.command = command   # 遥控命令,1字节
   
   def to_bytes(self):
       return struct.pack('<B', self.command.value)
       
   @classmethod
   def from_bytes(cls, data):
       command, = struct.unpack('<B', data)
       return cls(RemoteCommand(command))

   def to_dict(self):
       return {"command": self.command.name}

@dataclass  
class DateTime:  
    def __init__(self, year: int, month: int, day: int, hour: int, minute: int, second: int):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour  
        self.minute = minute
        self.second = second

    def to_bytes(self):
        return struct.pack('>HBBBBB', self.year, self.month, self.day, self.hour, self.minute, self.second)

    @property  
    def datetime(self):
        return datetime.datetime(self.year, self.month, self.day, self.hour, self.minute, self.second)  
    
    @classmethod
    def from_bytes(cls, data): 
        year, month, day, hour, minute, second = struct.unpack('>HBBBBB', data)
        return cls(year, month, day, hour, minute, second)
        
    def to_dict(self):  
        return {
            "year": self.year,
            "month": self.month, 
            "day": self.day,
            "hour": self.hour,
            "minute": self.minute,
            "second": self.second
        }

class ConfigParamType(Enum):
    AC_START_TEMP = 0x80       # 空调开启温度
    AC_TEMP_HYSTERESIS = 0x81  # 空调停止回差  
    HEAT_START_TEMP = 0x82     # 加热开启温度
    HEAT_HYSTERESIS = 0x83     # 加热停止回差
    HIGH_TEMP_ALARM = 0x84     # 高温告警点    
    LOW_TEMP_ALARM = 0x85      # 低温告警点

@dataclass
class ConfigParam:
    def __init__(self, param_type: ConfigParamType, param_value: int):
        self.param_type = param_type    # 参数类型,1字节
        self.param_value = param_value  # 参数值,2字节有符号整数,0.1度
        
    def to_bytes(self):
        return struct.pack('<Bh', self.param_type.value, self.param_value)

    @classmethod    
    def from_bytes(cls, data):
        param_type, param_value = struct.unpack('<Bh', data)
        return cls(ConfigParamType(param_type), param_value)

    def to_dict(self):
        return {
            "param_type": self.param_type.name,
            "param_value": self.param_value / 10.0
        }
        
@dataclass
class DeviceAddress:
    def __init__(self, address: int):
        self.address = address  # 新设备地址,1字节

    def to_bytes(self):
        return struct.pack('<B', self.address)

    @classmethod
    def from_bytes(cls, data):
        address, = struct.unpack('<B', data) 
        return cls(address)

    def to_dict(self):
        return {"address": self.address}

@dataclass
class ProtocolVersion:
    def __init__(self, version: str):
        self.version = version

    def to_bytes(self):
        return self.version.encode('ascii')

    @classmethod
    def from_bytes(cls, data):
        version = data.decode('ascii')
        return cls(version)

    def to_dict(self):
        return {"version": self.version} 

@dataclass
class SoftwareVersion():
    def __init__(self, major: int, minor: int):
        self.major = major
        self.minor = minor

    def to_bytes(self):
        return struct.pack('BB', self.major, self.minor)

    @classmethod
    def from_bytes(cls, data):
        major, minor = struct.unpack('BB', data)
        return cls(major, minor)

    def to_dict(self):
        return {"major": self.major, "minor": self.minor}
    
    def __str__(self):
        return f"{self.major}.{self.minor}"
    
@dataclass
class ManufacturerInfo:
    def __init__(self, device_name: str, software_version: SoftwareVersion, manufacturer: str):
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
        collector_name = data[:10].decode('ascii').rstrip('\x00') 
        software_version =SoftwareVersion.from_bytes(data[10:12])
        manufacturer = data[12:32].decode('ascii').rstrip('\x00')
        return cls(collector_name, software_version, manufacturer)

    def to_dict(self):
        return {
            "collector_name": self.device_name,
            "software_version": self.software_version.to_dict(),
            "manufacturer": self.manufacturer
        }

@dataclass
class ProtocolVersion:
    def __init__(self, version: str):
        self.version = version

    def to_bytes(self):
        return self.version.encode('ascii')

    @classmethod
    def from_bytes(cls, data):
        version = data.decode('ascii')
        return cls(version)

    def to_dict(self):
        return {"protocol_version": self.version} 