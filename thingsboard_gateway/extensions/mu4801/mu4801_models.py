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
    ALARM = 1    # 告警

class SwitchStatus(Enum):
    ON = 0       # 开
    OFF = 1      # 关

class EnableStatus(Enum):  
    DISABLE = 0  # 禁止
    ENABLE = 1   # 使能

class LoadOffMode(Enum):
    VOLTAGE = 0  # 负载下电模式 - 电压模式
    TIME = 1     # 负载下电模式 - 时间模式

class RectModuleControlType(Enum):   
    ON = 0x20    # 开机
    OFF = 0x2F   # 关机

class SystemControlState(Enum):
    AUTO = 0xE0   # 自动控制状态  
    MANUAL = 0xE1 # 手动控制状态

class SystemControlType(Enum):
    RESET = 0xE1         # 系统复位
    LOAD1_OFF = 0xE5     # 负载1下电  
    LOAD1_ON = 0xE6      # 负载1上电
    LOAD2_OFF = 0xE7     # 负载2下电
    LOAD2_ON = 0xE8      # 负载2上电
    LOAD3_OFF = 0xE9     # 负载3下电
    LOAD3_ON = 0xEA      # 负载3上电   i
    LOAD4_OFF = 0xEB     # 负载4下电
    LOAD4_ON = 0xEC      # 负载4上电
    BATTERY_OFF = 0xED   # 电池下电
    BATTERY_ON = 0xEE    # 电池上电
    
class VoltageStatus(Enum):
    NORMAL = 0   # 正常  
    UNDER = 1    # 欠压
    OVER = 2     # 过压

class FrequencyStatus(Enum):  
    NORMAL = 0   # 正常
    UNDER = 1    # 过低
    OVER = 2     # 过高

class ChargeStatus(Enum):
    FLOAT = 0    # 浮充  
    EQUALIZE = 1 # 均充
    TEST = 2     # 测试

class TempStatus(Enum):
    NORMAL = 0   # 正常
    OVER = 1     # 过温   
    UNDER = 2    # 欠温

class SensorStatus(Enum):
    NORMAL = 0   # 正常
    BREAK = 1    # 未接
    FAULT = 2    # 故障

class LVDStatus(Enum):  
    NORMAL = 0      # 正常
    IMPENDING = 1   # 即将下电
    OFF = 2         # 已下电

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

@dataclass    
class DeviceAddress:
    def __init__(self, address: int):
        self.address = address  # 设备地址,1字节

    def to_bytes(self):
        return struct.pack('B', self.address)

    @classmethod
    def from_bytes(cls, data):
        address, = struct.unpack('B', data)
        return cls(address)

    def to_dict(self):
        return {"address": self.address}

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
    def __init__(self, collector_name: str, software_version: SoftwareVersion, manufacturer: str):
        self.collector_name = collector_name    # 采集器名称,10字节
        self.software_version = software_version  # 厂商软件版本,2字节
        self.manufacturer = manufacturer    # 厂商名称,20字节

    def to_bytes(self):
        data = bytearray()
        data.extend((self.collector_name.encode('ascii')[:10]).ljust(10, b'\x00'))
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
            "collector_name": self.collector_name,
            "software_version": self.software_version.to_dict(),
            "manufacturer": self.manufacturer
        }

@dataclass
class AcAnalogData:
    def __init__(self, data_flag: DataFlag, number_of_inputs: int, voltage_a: float, voltage_b: float, voltage_c: float,
                 frequency: float, user_defined_params_count: int):
        self.data_flag = data_flag   # 数据标志,固定为0,1字节
        self.number_of_inputs = number_of_inputs   # 交流输入路数,固定为1路,1字节
        self.voltage_a = voltage_a   # 输入线/相电压AB/A,4字节浮点数
        self.voltage_b = voltage_b   # 输入线/相电压BC/B,4字节浮点数
        self.voltage_c = voltage_c   # 输入线/相电压CA/C,4字节浮点数
        self.frequency = frequency   # 输入频率,4字节浮点数
        self.user_defined_params_count = user_defined_params_count  # 用户自定义数量,固定为30,1字节

    def to_bytes(self):
        return struct.pack('<BBBBBBBBBBBBBBBBBBB', self.data_flag.value, self.number_of_inputs,
                        *struct.unpack('4B', struct.pack('<f', self.voltage_a)),
                        *struct.unpack('4B', struct.pack('<f', self.voltage_b)),  
                        *struct.unpack('4B', struct.pack('<f', self.voltage_c)),
                        *struct.unpack('4B', struct.pack('<f', self.frequency)),
                        self.user_defined_params_count)
  
    @classmethod
    def from_bytes(cls, data):
        data_flag, number_of_inputs, *values = struct.unpack('<BBBBBBBBBBBBBBBBBBB', data)
        voltage_a = struct.unpack('<f', bytes(values[:4]))[0]
        voltage_b = struct.unpack('<f', bytes(values[4:8]))[0]  
        voltage_c = struct.unpack('<f', bytes(values[8:12]))[0]
        frequency = struct.unpack('<f', bytes(values[12:16]))[0]  
        user_defined_params_count = values[16] 
        return cls(DataFlag(data_flag), number_of_inputs, voltage_a, voltage_b, voltage_c, 
                   frequency, user_defined_params_count)
        
    def to_dict(self):
        return {
            "data_flag": self.data_flag.name,  
            "number_of_inputs": self.number_of_inputs,
            "voltage_a": self.voltage_a,
            "voltage_b": self.voltage_b,
            "voltage_c": self.voltage_c,
            "frequency": self.frequency,
            "user_defined_params_count": self.user_defined_params_count
        }

@dataclass  
class AcAlarmStatus:
    def __init__(self, data_flag: DataFlag, number_of_inputs: int, voltage_a_status: VoltageStatus,
                 voltage_b_status: VoltageStatus, voltage_c_status: VoltageStatus,  
                 frequency_status: FrequencyStatus, fuse_count: int, user_defined_params_count: int,  
                 ac_arrester_status: AlarmStatus, ac_comm_failure_status: AlarmStatus,
                 ac_input_switch_status: AlarmStatus, ac_output_switch_status: AlarmStatus,
                 ac_power_status: AlarmStatus):  
        self.data_flag = data_flag   # 数据标志,固定为0,1字节
        self.number_of_inputs = number_of_inputs   # 交流输入路数,固定为1路,1字节
        self.voltage_a_status = voltage_a_status   # 输入线/相电压AB/A状态,1字节
        self.voltage_b_status = voltage_b_status   # 输入线/相电压BC/B状态,1字节  
        self.voltage_c_status = voltage_c_status   # 输入线/相电压CA/C状态,1字节
        self.frequency_status = frequency_status   # 频率状态,1字节
        self.fuse_count = fuse_count   # 熔丝数量,固定为0,1字节
        self.user_defined_params_count = user_defined_params_count   # 用户自定义数量,固定为18,1字节  
        self.ac_arrester_status = ac_arrester_status    # 交流防雷器状态,1字节
        self.ac_comm_failure_status = ac_comm_failure_status   # 交流屏通讯中断状态,1字节
        self.ac_input_switch_status = ac_input_switch_status    # 交流输入空开跳闸状态,1字节
        self.ac_output_switch_status = ac_output_switch_status   # 交流输出空开跳闸状态,1字节  
        self.ac_power_status = ac_power_status    # 交流第一路输入停电状态,1字节
  
    def to_bytes(self):
        return struct.pack('<BBBBBBBBBBBBB', self.data_flag.value, self.number_of_inputs,
                           self.voltage_a_status.value, self.voltage_b_status.value, self.voltage_c_status.value,  
                           self.frequency_status.value, self.fuse_count, self.user_defined_params_count,
                           self.ac_arrester_status.value, self.ac_comm_failure_status.value,
                           self.ac_input_switch_status.value, self.ac_output_switch_status.value,  
                           self.ac_power_status.value)
  
    @classmethod
    def from_bytes(cls, data):
        (data_flag, number_of_inputs, voltage_a_status, voltage_b_status, voltage_c_status,  
         frequency_status, fuse_count, user_defined_params_count, ac_arrester_status,  
         ac_comm_failure_status, ac_input_switch_status, ac_output_switch_status,
         ac_power_status) = struct.unpack('<BBBBBBBBBBBBB', data)
        return cls(DataFlag(data_flag), number_of_inputs, VoltageStatus(voltage_a_status), VoltageStatus(voltage_b_status),  
                   VoltageStatus(voltage_c_status), FrequencyStatus(frequency_status), fuse_count, user_defined_params_count,
                   AlarmStatus(ac_arrester_status), AlarmStatus(ac_comm_failure_status), 
                   AlarmStatus(ac_input_switch_status), AlarmStatus(ac_output_switch_status),
                   AlarmStatus(ac_power_status))

    def to_dict(self):
        return {
            "data_flag": self.data_flag.name,
            "number_of_inputs": self.number_of_inputs,
            "voltage_a_status": self.voltage_a_status.name,
            "voltage_b_status": self.voltage_b_status.name,  
            "voltage_c_status": self.voltage_c_status.name,
            "frequency_status": self.frequency_status.name,
            "fuse_count": self.fuse_count,
            "user_defined_params_count": self.user_defined_params_count,
            "ac_arrester_status": self.ac_arrester_status.name,  
            "ac_comm_failure_status": self.ac_comm_failure_status.name,
            "ac_input_switch_status": self.ac_input_switch_status.name,
            "ac_output_switch_status": self.ac_output_switch_status.name,
            "ac_power_status": self.ac_power_status.name
        }

@dataclass
class AcConfigParams:  
    def __init__(self, ac_over_voltage: float, ac_under_voltage: float):
        self.ac_over_voltage = ac_over_voltage   # 交流输入线/相电压上限,4字节浮点数
        self.ac_under_voltage = ac_under_voltage  # 交流输入线/相电压下限,4字节浮点数
  
    def to_bytes(self):
        return struct.pack('<ff', self.ac_over_voltage, self.ac_under_voltage)

    @classmethod
    def from_bytes(cls, data):  
        ac_over_voltage, ac_under_voltage = struct.unpack('<ff', data)
        return cls(ac_over_voltage, ac_under_voltage)
        
    def to_dict(self):
        return {
            "ac_over_voltage": self.ac_over_voltage,
            "ac_under_voltage": self.ac_under_voltage  
        }
    
@dataclass  
class RectAnalogData:
    def __init__(self, data_flag: DataFlag, output_voltage: float, module_count: int, module_currents: List[float],
                 user_defined_params_count: List[int], module_current_limit: List[float], module_voltage: List[float], 
                 module_temperature: List[float], module_input_voltage_ab: List[float]):
        self.data_flag = data_flag   # 数据标志,固定为0,1字节  
        self.output_voltage = output_voltage   # 整流模块输出电压,4字节浮点数
        self.module_count = module_count    # 监控模块数量,1字节
        self.module_currents = module_currents  # 整流模块输出电流,4字节浮点数,个数为监控模块数量  
        self.user_defined_params_count = user_defined_params_count   # 用户自定义数量,固定为13,个数为监控模块数量,1字节
        self.module_current_limit = module_current_limit   # 模块限流点,4字节浮点数,个数为监控模块数量
        self.module_voltage = module_voltage   # 模块输出电压,4字节浮点数,个数为监控模块数量  
        self.module_temperature = module_temperature  # 模块温度,4字节浮点数,个数为监控模块数量
        self.module_input_voltage_ab = module_input_voltage_ab  # 交流输入AB线电压,4字节浮点数,个数为监控模块数量
  
    def to_bytes(self):
        data = bytearray(struct.pack('<BBf', self.data_flag.value, self.module_count, self.output_voltage))
        for i in range(self.module_count):
            data.extend(struct.pack('<fB', self.module_currents[i], self.user_defined_params_count[i]))
            data.extend(struct.pack('<fff', self.module_current_limit[i], self.module_voltage[i], self.module_temperature[i]))  
            data.extend(struct.pack('<f', self.module_input_voltage_ab[i]))
        return bytes(data)
        
    @classmethod
    def from_bytes(cls, data):  
        data_flag, module_count, output_voltage = struct.unpack('<BBf', data[:6])
        offset = 6
        module_currents = []
        user_defined_params_count = []  
        module_current_limit = []
        module_voltage = []
        module_temperature = []
        module_input_voltage_ab = []
        for _ in range(module_count):
            module_current, user_defined_param_count = struct.unpack('<fB', data[offset:offset+5]) 
            offset += 5
            module_currents.append(module_current)
            user_defined_params_count.append(user_defined_param_count)
            module_current_limit_val, module_voltage_val, module_temperature_val = struct.unpack('<fff', data[offset:offset+12])
            offset += 12  
            module_current_limit.append(module_current_limit_val)
            module_voltage.append(module_voltage_val)
            module_temperature.append(module_temperature_val)
            module_input_voltage_ab_val, = struct.unpack('<f', data[offset:offset+4])  
            offset += 4
            module_input_voltage_ab.append(module_input_voltage_ab_val)
        return cls(DataFlag(data_flag), output_voltage, module_count, module_currents,   
                   user_defined_params_count, module_current_limit, module_voltage, 
                   module_temperature, module_input_voltage_ab)

    def to_dict(self):
        return {
            "data_flag": self.data_flag.name,
            "output_voltage": self.output_voltage,
            "module_count": self.module_count,  
            "module_currents": self.module_currents,
            "user_defined_params_count": self.user_defined_params_count,
            "module_current_limit": self.module_current_limit,
            "module_voltage": self.module_voltage,
            "module_temperature": self.module_temperature,  
            "module_input_voltage_ab": self.module_input_voltage_ab
        }

@dataclass
class RectSwitchStatus:  
    def __init__(self, data_flag: DataFlag, module_count: int, module_run_status: List[SwitchStatus],
                 module_limit_status: List[SwitchStatus], module_charge_status: List[ChargeStatus],
                 user_defined_params_count: List[int]):
        self.data_flag = data_flag   # 数据标志,固定为0,1字节
        self.module_count = module_count    # 整流模块数量,1字节  
        self.module_run_status = module_run_status  # 模块开机/关机状态,1字节,个数为整流模块数量
        self.module_limit_status = module_limit_status  # 模块限流状态,1字节,个数为整流模块数量
        self.module_charge_status = module_charge_status   # 充电状态,1字节,个数为整流模块数量
        self.user_defined_params_count = user_defined_params_count   # 用户自定义数量,固定为16,个数为整流模块数量,1字节

    def to_bytes(self):
        data = bytearray(struct.pack('<BB', self.data_flag.value, self.module_count)) 
        for i in range(self.module_count):
            data.extend(struct.pack('<BBBB', self.module_run_status[i].value, self.module_limit_status[i].value, 
                                    self.module_charge_status[i].value, self.user_defined_params_count[i]))
        return bytes(data)
        
    @classmethod
    def from_bytes(cls, data):  
        data_flag, module_count = struct.unpack('<BB', data[:2])
        offset = 2
        module_run_status = []
        module_limit_status = []
        module_charge_status = []  
        user_defined_params_count = []
        for _ in range(module_count):
            run_status, limit_status, charge_status, user_defined_param_count = struct.unpack('<BBBB', data[offset:offset+4])
            offset += 4
            module_run_status.append(SwitchStatus(run_status))
            module_limit_status.append(SwitchStatus(limit_status))
            module_charge_status.append(ChargeStatus(charge_status))  
            user_defined_params_count.append(user_defined_param_count)
        return cls(DataFlag(data_flag), module_count, module_run_status, module_limit_status,  
                   module_charge_status, user_defined_params_count)

    def to_dict(self):
        return {
            "data_flag": self.data_flag.name,
            "module_count": self.module_count,
            "module_run_status": [status.name for status in self.module_run_status],
            "module_limit_status": [status.name for status in self.module_limit_status],  
            "module_charge_status": [status.name for status in self.module_charge_status],
            "user_defined_params_count": self.user_defined_params_count
        }

@dataclass
class RectAlarmStatus:  
    def __init__(self, data_flag: DataFlag, module_count: int, module_failure_status: List[AlarmStatus],
                 user_defined_params_count: List[int], module_comm_failure_status: List[AlarmStatus], 
                 module_protection_status: List[AlarmStatus], module_fan_status: List[AlarmStatus]):
        self.data_flag = data_flag   # 数据标志,固定为0,1字节
        self.module_count = module_count    # 整流模块数量,1字节
        self.module_failure_status = module_failure_status  # 整流模块故障状态,1字节,个数为整流模块数量
        self.user_defined_params_count = user_defined_params_count   # 用户自定义数量,固定为18,个数为整流模块数量,1字节
        self.module_comm_failure_status = module_comm_failure_status  # 模块通讯故障状态,1字节,个数为整流模块数量
        self.module_protection_status = module_protection_status  # 模块保护状态,1字节,个数为整流模块数量  
        self.module_fan_status = module_fan_status    # 模块风扇状态,1字节,个数为整流模块数量

    def to_bytes(self):
        data = bytearray(struct.pack('<BB', self.data_flag.value, self.module_count))  
        for i in range(self.module_count):
            data.extend(struct.pack('<BBBBB', self.module_failure_status[i].value,
                                    self.user_defined_params_count[i],  
                                    self.module_comm_failure_status[i].value,
                                    self.module_protection_status[i].value,
                                    self.module_fan_status[i].value))
        return bytes(data)
        
    @classmethod
    def from_bytes(cls, data):
        data_flag, module_count = struct.unpack('<BB', data[:2])
        offset = 2
        module_failure_status = []
        user_defined_params_count = []
        module_comm_failure_status = []  
        module_protection_status = []
        module_fan_status = []
        for _ in range(module_count):
            failure_status, user_defined_param_count, comm_failure_status, protection_status, fan_status = struct.unpack('<BBBBB', data[offset:offset+5])  
            offset += 5
            module_failure_status.append(AlarmStatus(failure_status)) 
            user_defined_params_count.append(user_defined_param_count)
            module_comm_failure_status.append(AlarmStatus(comm_failure_status))
            module_protection_status.append(AlarmStatus(protection_status))
            module_fan_status.append(AlarmStatus(fan_status))
        return cls(DataFlag(data_flag), module_count, module_failure_status,
                   user_defined_params_count, module_comm_failure_status,  
                   module_protection_status, module_fan_status)

    def to_dict(self):
        return {
            "data_flag": self.data_flag.name, 
            "module_count": self.module_count,
            "module_failure_status": [status.name for status in self.module_failure_status],
            "user_defined_params_count": self.user_defined_params_count,
            "module_comm_failure_status": [status.name for status in self.module_comm_failure_status],
            "module_protection_status": [status.name for status in self.module_protection_status],  
            "module_fan_status": [status.name for status in self.module_fan_status]
        }

@dataclass
class ControlRectModule:
    def __init__(self, module_id: int, control_type: RectModuleControlType, control_value: int):  
        self.module_id = module_id   # 模块ID,1字节
        self.control_type = control_type  # 控制类型,1字节,开机20H,关机2FH
        self.control_value = control_value  # 控制值,1字节
        
    def to_bytes(self):
        return struct.pack('<BBB', self.module_id, self.control_type.value, self.control_value)
        
    @classmethod
    def from_bytes(cls, data):
        module_id, control_type, control_value = struct.unpack('<BBB', data)
        return cls(module_id, RectModuleControlType(control_type), control_value)

    def to_dict(self):
        return {
            "module_id": self.module_id,
            "control_type": self.control_type.name,  
            "control_value": self.control_value
        }

@dataclass  
class DcAnalogData:
    def __init__(self, data_flag: DataFlag, dc_voltage: float, total_load_current: float, battery_group_count: int,
                 battery_group_1_number: int, battery_group_1_current: float, load_branch_count: int,
                 load_branch_1_current: float, load_branch_2_current: float, load_branch_3_current: float,
                 load_branch_4_current: float, user_defined_params_count: int, battery_total_current: float,
                 battery_group_1_capacity: float, battery_group_1_voltage: float, battery_group_1_mid_voltage: float,
                 battery_group_2_mid_voltage: float, battery_group_3_mid_voltage: float, battery_group_4_mid_voltage: float,
                 battery_group_1_temperature: float, env_temp_1: float, env_temp_2: float, env_humidity_1: float,
                 total_load_power: float, load_power_1: float, load_power_2: float, load_power_3: float,
                 load_power_4: float, total_load_energy: float, load_energy_1: float, load_energy_2: float,
                 load_energy_3: float, load_energy_4: float):
        self.data_flag = data_flag   # 数据标志,固定为0,1字节
        self.dc_voltage = dc_voltage   # 直流输出电压,4字节浮点数
        self.total_load_current = total_load_current   # 总负载电流,4字节浮点数
        self.battery_group_count = battery_group_count   # 蓄电池组数,固定为1,1字节
        self.battery_group_1_number = battery_group_1_number  # 第1组蓄电池编号,1字节  
        self.battery_group_1_current = battery_group_1_current  # 第1组蓄电池电流,4字节浮点数
        self.load_branch_count = load_branch_count   # 监测直流分路电流数,固定为4,1字节
        self.load_branch_1_current = load_branch_1_current  # 直流分路1电流,4字节浮点数  
        self.load_branch_2_current = load_branch_2_current  # 直流分路2电流,4字节浮点数
        self.load_branch_3_current = load_branch_3_current  # 直流分路3电流,4字节浮点数
        self.load_branch_4_current = load_branch_4_current  # 直流分路4电流,4字节浮点数
        self.user_defined_params_count = user_defined_params_count  # 用户自定义数量,固定为55,1字节
        self.battery_total_current = battery_total_current  # 电池总电流,4字节浮点数  
        self.battery_group_1_capacity = battery_group_1_capacity  # 电池组1剩余容量,4字节浮点数
        self.battery_group_1_voltage = battery_group_1_voltage   # 电池组1电压,4字节浮点数
        self.battery_group_1_mid_voltage = battery_group_1_mid_voltage  # 电池组1中点电压,4字节浮点数
        self.battery_group_2_mid_voltage = battery_group_2_mid_voltage  # 电池组2中点电压,4字节浮点数  
        self.battery_group_3_mid_voltage = battery_group_3_mid_voltage  # 电池组3中点电压,4字节浮点数
        self.battery_group_4_mid_voltage = battery_group_4_mid_voltage  # 电池组4中点电压,4字节浮点数
        self.battery_group_1_temperature = battery_group_1_temperature  # 电池组1温度,4字节浮点数
        self.env_temp_1 = env_temp_1  # 机柜内环境温度1,4字节浮点数
        self.env_temp_2 = env_temp_2  # 机柜内环境温度2,4字节浮点数
        self.env_humidity_1 = env_humidity_1   # 机柜内环境湿度1,4字节浮点数 
        self.total_load_power = total_load_power  # 总负载功率,4字节浮点数
        self.load_power_1 = load_power_1   # 直流负载1功率,4字节浮点数
        self.load_power_2 = load_power_2   # 直流负载2功率,4字节浮点数
        self.load_power_3 = load_power_3   # 直流负载3功率,4字节浮点数
        self.load_power_4 = load_power_4   # 直流负载4功率,4字节浮点数  
        self.total_load_energy = total_load_energy   # 总负载电量,4字节浮点数
        self.load_energy_1 = load_energy_1  # 直流负载1电量,4字节浮点数
        self.load_energy_2 = load_energy_2  # 直流负载2电量,4字节浮点数
        self.load_energy_3 = load_energy_3  # 直流负载3电量,4字节浮点数
        self.load_energy_4 = load_energy_4  # 直流负载4电量,4字节浮点数

    def to_bytes(self):
        data = bytearray(struct.pack('<BBff', self.data_flag.value, self.battery_group_count, 
                                    self.dc_voltage, self.total_load_current))
        data.extend(struct.pack('<BB', self.battery_group_1_number, self.load_branch_count))
        data.extend(struct.pack('<f', self.battery_group_1_current))
        data.extend(struct.pack('<B', self.user_defined_params_count))  
        data.extend(struct.pack('<ffff', self.load_branch_1_current, self.load_branch_2_current, 
                                self.load_branch_3_current, self.load_branch_4_current))
        data.extend(struct.pack('<H', 0))  # 添加用户自定义数量P的占位符
        data.extend(struct.pack('<ffffff', self.battery_total_current, self.battery_group_1_capacity,
                                self.battery_group_1_voltage, self.battery_group_1_mid_voltage,
                                self.battery_group_2_mid_voltage, self.battery_group_3_mid_voltage))
        data.extend(struct.pack('<fff', self.battery_group_4_mid_voltage, self.battery_group_1_temperature,
                                self.env_temp_1))
        data.extend(struct.pack('<fffff', self.env_temp_2, self.env_humidity_1, self.total_load_power,
                                self.load_power_1, self.load_power_2))
        data.extend(struct.pack('<fffff', self.load_power_3, self.load_power_4, self.total_load_energy,
                                self.load_energy_1, self.load_energy_2))
        data.extend(struct.pack('<fff', self.load_energy_3, self.load_energy_4, 0.0))  # 添加占位符
        return bytes(data) 

    @classmethod
    def from_bytes(cls, data):
        (data_flag, battery_group_count, dc_voltage, total_load_current,
        battery_group_1_number, load_branch_count, battery_group_1_current,
        user_defined_params_count) = struct.unpack('<BBffBBfB', data[:17])
        offset = 17
        (load_branch_1_current, load_branch_2_current, load_branch_3_current,  
        load_branch_4_current) = struct.unpack('<ffff', data[offset:offset+16])
        offset += 18  # 跳过用户自定义数量P的2字节
        (battery_total_current, battery_group_1_capacity, battery_group_1_voltage,
        battery_group_1_mid_voltage, battery_group_2_mid_voltage, battery_group_3_mid_voltage) = struct.unpack('<ffffff', data[offset:offset+24])
        offset += 24  
        (battery_group_4_mid_voltage, battery_group_1_temperature, env_temp_1) = struct.unpack('<fff', data[offset:offset+12])  
        offset += 12
        (env_temp_2, env_humidity_1, total_load_power, load_power_1, load_power_2) = struct.unpack('<fffff', data[offset:offset+20])
        offset += 20
        (load_power_3, load_power_4, total_load_energy, load_energy_1, load_energy_2) = struct.unpack('<fffff', data[offset:offset+20])
        offset += 20
        (load_energy_3, load_energy_4) = struct.unpack('<ff', data[offset:offset+8])
        return cls(DataFlag(data_flag), dc_voltage, total_load_current, battery_group_count,
                battery_group_1_number, battery_group_1_current, load_branch_count,
                load_branch_1_current, load_branch_2_current, load_branch_3_current,  
                load_branch_4_current, user_defined_params_count, battery_total_current,
                battery_group_1_capacity, battery_group_1_voltage, battery_group_1_mid_voltage, 
                battery_group_2_mid_voltage, battery_group_3_mid_voltage, battery_group_4_mid_voltage,
                battery_group_1_temperature, env_temp_1, env_temp_2, env_humidity_1,
                total_load_power, load_power_1, load_power_2, load_power_3,  
                load_power_4, total_load_energy, load_energy_1, load_energy_2,
                load_energy_3, load_energy_4)

    def to_dict(self):
        return {
            "data_flag": self.data_flag.name,  
            "dc_voltage": self.dc_voltage,
            "total_load_current": self.total_load_current,
            "battery_group_count": self.battery_group_count,
            "battery_group_1_number": self.battery_group_1_number,
            "battery_group_1_current": self.battery_group_1_current,  
            "load_branch_count": self.load_branch_count,
            "load_branch_1_current": self.load_branch_1_current,
            "load_branch_2_current": self.load_branch_2_current,
            "load_branch_3_current": self.load_branch_3_current,  
            "load_branch_4_current": self.load_branch_4_current,
            "user_defined_params_count": self.user_defined_params_count,
            "battery_total_current": self.battery_total_current,
            "battery_group_1_capacity": self.battery_group_1_capacity,
            "battery_group_1_voltage": self.battery_group_1_voltage,
            "battery_group_1_mid_voltage": self.battery_group_1_mid_voltage,
            "battery_group_2_mid_voltage": self.battery_group_2_mid_voltage,
            "battery_group_3_mid_voltage": self.battery_group_3_mid_voltage,  
            "battery_group_4_mid_voltage": self.battery_group_4_mid_voltage,
            "battery_group_1_temperature": self.battery_group_1_temperature,
            "env_temp_1": self.env_temp_1,
            "env_temp_2": self.env_temp_2,
            "env_humidity_1": self.env_humidity_1,  
            "total_load_power": self.total_load_power,
            "load_power_1": self.load_power_1,
            "load_power_2": self.load_power_2,
            "load_power_3": self.load_power_3,
            "load_power_4": self.load_power_4,
            "total_load_energy": self.total_load_energy,
            "load_energy_1": self.load_energy_1,  
            "load_energy_2": self.load_energy_2,
            "load_energy_3": self.load_energy_3,  
            "load_energy_4": self.load_energy_4
        }
        
@dataclass    
class DcAlarmStatus:
    def __init__(self, data_flag: DataFlag, dc_voltage_status: VoltageStatus, 
                 battery_fuse_count: int, user_defined_params_count: int,
                 dc_arrester_status: AlarmStatus, load_fuse_status: AlarmStatus,
                 battery_group_1_fuse_status: AlarmStatus, battery_group_2_fuse_status: AlarmStatus,
                 battery_group_3_fuse_status: AlarmStatus, battery_group_4_fuse_status: AlarmStatus,
                 blvd_status: LVDStatus, llvd1_status: LVDStatus, llvd2_status: LVDStatus,
                 llvd3_status: LVDStatus, llvd4_status: LVDStatus,
                 battery_temp_status: TempStatus, battery_temp_sensor_1_status: SensorStatus,
                 env_temp_status: TempStatus, env_temp_sensor_1_status: SensorStatus,
                 env_temp_sensor_2_status: SensorStatus, env_humidity_status: AlarmStatus,
                 env_humidity_sensor_1_status: SensorStatus, door_status: AlarmStatus,
                 water_status: AlarmStatus, smoke_status: AlarmStatus,
                 digital_input_status_1: AlarmStatus, digital_input_status_2: AlarmStatus,
                 digital_input_status_3: AlarmStatus, digital_input_status_4: AlarmStatus,
                 digital_input_status_5: AlarmStatus, digital_input_status_6: AlarmStatus):
        self.data_flag = data_flag   # 数据标志,固定为0,1字节  
        self.dc_voltage_status = dc_voltage_status  # 直流电压状态,1字节
        self.battery_fuse_count = battery_fuse_count   # 监测直流熔丝(或开关)数量,固定为0,1字节
        self.user_defined_params_count = user_defined_params_count # 用户自定义数量,固定为151,1字节 
        self.dc_arrester_status = dc_arrester_status  # 直流防雷器状态,1字节
        self.load_fuse_status = load_fuse_status  # 负载熔丝状态,1字节
        self.battery_group_1_fuse_status = battery_group_1_fuse_status  # 电池组1熔丝状态,1字节  
        self.battery_group_2_fuse_status = battery_group_2_fuse_status  # 电池组2熔丝状态,1字节
        self.battery_group_3_fuse_status = battery_group_3_fuse_status  # 电池组3熔丝状态,1字节
        self.battery_group_4_fuse_status = battery_group_4_fuse_status  # 电池组4熔丝状态,1字节
        self.blvd_status = blvd_status    # BLVD状态,1字节
        self.llvd1_status = llvd1_status  # 负载LLVD1状态,1字节
        self.llvd2_status = llvd2_status  # 负载LLVD2状态,1字节
        self.llvd3_status = llvd3_status  # 负载LLVD3状态,1字节  
        self.llvd4_status = llvd4_status  # 负载LLVD4状态,1字节
        self.battery_temp_status = battery_temp_status   # 电池温度状态,1字节
        self.battery_temp_sensor_1_status = battery_temp_sensor_1_status  # 电池温度传感器1状态,1字节
        self.env_temp_status = env_temp_status    # 环境温度状态,1字节
        self.env_temp_sensor_1_status = env_temp_sensor_1_status  # 环境温度传感器1状态,1字节  
        self.env_temp_sensor_2_status = env_temp_sensor_2_status  # 环境温度传感器2状态,1字节
        self.env_humidity_status = env_humidity_status  # 环境湿度状态,1字节
        self.env_humidity_sensor_1_status = env_humidity_sensor_1_status  # 环境湿度传感器1状态,1字节
        self.door_status = door_status    # 门磁状态,1字节
        self.water_status = water_status  # 水浸状态,1字节
        self.smoke_status = smoke_status  # 烟雾状态,1字节
        self.digital_input_status_1 = digital_input_status_1  # 数字输入1状态,1字节
        self.digital_input_status_2 = digital_input_status_2  # 数字输入2状态,1字节  
        self.digital_input_status_3 = digital_input_status_3  # 数字输入3状态,1字节
        self.digital_input_status_4 = digital_input_status_4  # 数字输入4状态,1字节
        self.digital_input_status_5 = digital_input_status_5  # 数字输入5状态,1字节
        self.digital_input_status_6 = digital_input_status_6  # 数字输入6状态,1字节

    def to_bytes(self):
        data = bytearray(struct.pack('<BBBB', self.data_flag.value, self.dc_voltage_status.value,
                            self.battery_fuse_count, self.user_defined_params_count))
        data.extend(struct.pack('<BBBBBBBBBBBBBBBBBBBBBBBBBBB',
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
                                self.digital_input_status_5.value, self.digital_input_status_6.value))
        return bytes(data)
 
    @classmethod
    def from_bytes(cls, data):
        (data_flag, dc_voltage_status, battery_fuse_count, user_defined_params_count,
        dc_arrester_status, load_fuse_status, battery_group_1_fuse_status, battery_group_2_fuse_status,
        battery_group_3_fuse_status, battery_group_4_fuse_status, blvd_status, llvd1_status,
        llvd2_status, llvd3_status, llvd4_status, battery_temp_status, battery_temp_sensor_1_status,
        env_temp_status, env_temp_sensor_1_status, env_temp_sensor_2_status, env_humidity_status,
        env_humidity_sensor_1_status, door_status, water_status, smoke_status, digital_input_status_1,
        digital_input_status_2, digital_input_status_3, digital_input_status_4, digital_input_status_5,
        digital_input_status_6) = struct.unpack('<BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB', data)
        return cls(DataFlag(data_flag), VoltageStatus(dc_voltage_status), battery_fuse_count,
                user_defined_params_count, AlarmStatus(dc_arrester_status), AlarmStatus(load_fuse_status), 
                AlarmStatus(battery_group_1_fuse_status), AlarmStatus(battery_group_2_fuse_status),
                AlarmStatus(battery_group_3_fuse_status), AlarmStatus(battery_group_4_fuse_status),
                LVDStatus(blvd_status), LVDStatus(llvd1_status), LVDStatus(llvd2_status),
                LVDStatus(llvd3_status), LVDStatus(llvd4_status), TempStatus(battery_temp_status),
                SensorStatus(battery_temp_sensor_1_status), TempStatus(env_temp_status),
                SensorStatus(env_temp_sensor_1_status), SensorStatus(env_temp_sensor_2_status),
                AlarmStatus(env_humidity_status), SensorStatus(env_humidity_sensor_1_status),
                AlarmStatus(door_status), AlarmStatus(water_status), AlarmStatus(smoke_status),
                AlarmStatus(digital_input_status_1), AlarmStatus(digital_input_status_2),
                AlarmStatus(digital_input_status_3), AlarmStatus(digital_input_status_4),
                AlarmStatus(digital_input_status_5), AlarmStatus(digital_input_status_6))

    def to_dict(self):
        return {
            "data_flag": self.data_flag.name,
            "dc_voltage_status": self.dc_voltage_status.name,
            "battery_fuse_count": self.battery_fuse_count,  
            "user_defined_params_count": self.user_defined_params_count,
            "dc_arrester_status": self.dc_arrester_status.name,
            "load_fuse_status": self.load_fuse_status.name,
            "battery_group_1_fuse_status": self.battery_group_1_fuse_status.name,
            "battery_group_2_fuse_status": self.battery_group_2_fuse_status.name,
            "battery_group_3_fuse_status": self.battery_group_3_fuse_status.name,  
            "battery_group_4_fuse_status": self.battery_group_4_fuse_status.name,
            "blvd_status": self.blvd_status.name,
            "llvd1_status": self.llvd1_status.name,
            "llvd2_status": self.llvd2_status.name,
            "llvd3_status": self.llvd3_status.name,
            "llvd4_status": self.llvd4_status.name,  
            "battery_temp_status": self.battery_temp_status.name,
            "battery_temp_sensor_1_status": self.battery_temp_sensor_1_status.name,  
            "env_temp_status": self.env_temp_status.name,
            "env_temp_sensor_1_status": self.env_temp_sensor_1_status.name,
            "env_temp_sensor_2_status": self.env_temp_sensor_2_status.name,
            "env_humidity_status": self.env_humidity_status.name,
            "env_humidity_sensor_1_status": self.env_humidity_sensor_1_status.name,
            "door_status": self.door_status.name,  
            "water_status": self.water_status.name,
            "smoke_status": self.smoke_status.name,
            "digital_input_status_1": self.digital_input_status_1.name,
            "digital_input_status_2": self.digital_input_status_2.name,  
            "digital_input_status_3": self.digital_input_status_3.name,
            "digital_input_status_4": self.digital_input_status_4.name,
            "digital_input_status_5": self.digital_input_status_5.name,
            "digital_input_status_6": self.digital_input_status_6.name
        }

@dataclass
class DcConfigParams:
    def __init__(self, dc_over_voltage: float, dc_under_voltage: float, time_equalize_charge_enable: EnableStatus,
                 time_equalize_duration: int, time_equalize_interval: int, battery_group_number: int, 
                 battery_over_temp: float, battery_under_temp: float, env_over_temp: float, env_under_temp: float,
                 env_over_humidity: float, battery_charge_current_limit: float, float_voltage: float,
                 equalize_voltage: float, battery_off_voltage: float, battery_on_voltage: float, llvd1_off_voltage: float,
                 llvd1_on_voltage: float, llvd2_off_voltage: float, llvd2_on_voltage: float, llvd3_off_voltage: float,
                 llvd3_on_voltage: float, llvd4_off_voltage: float, llvd4_on_voltage: float, battery_capacity: float,
                 battery_test_stop_voltage: float, battery_temp_coeff: float, battery_temp_center: float,
                 float_to_equalize_coeff: float, equalize_to_float_coeff: float, llvd1_off_time: float,
                 llvd2_off_time: float, llvd3_off_time: float, llvd4_off_time: float, load_off_mode: LoadOffMode):
       self.dc_over_voltage = dc_over_voltage  # 直流过压值,4字节浮点数  
       self.dc_under_voltage = dc_under_voltage  # 直流欠压值,4字节浮点数
       self.time_equalize_charge_enable = time_equalize_charge_enable  # 定时均充使能,1字节
       self.time_equalize_duration = time_equalize_duration   # 定时均充时间,1字节
       self.time_equalize_interval = time_equalize_interval   # 定时均充间隔,2字节  
       self.battery_group_number = battery_group_number  # 电池组数,1字节
       self.battery_over_temp = battery_over_temp   # 电池过温告警点,4字节浮点数
       self.battery_under_temp = battery_under_temp   # 电池欠温告警点,4字节浮点数
       self.env_over_temp = env_over_temp  # 环境过温告警点,4字节浮点数
       self.env_under_temp = env_under_temp  # 环境欠温告警点,4字节浮点数
       self.env_over_humidity = env_over_humidity   # 环境过湿告警点,4字节浮点数  
       self.battery_charge_current_limit = battery_charge_current_limit  # 电池充电限流点,4字节浮点数
       self.float_voltage = float_voltage   # 浮充电压,4字节浮点数
       self.equalize_voltage = equalize_voltage  # 均充电压,4字节浮点数
       self.battery_off_voltage = battery_off_voltage  # 电池下电电压,4字节浮点数
       self.battery_on_voltage = battery_on_voltage   # 电池上电电压,4字节浮点数
       self.llvd1_off_voltage = llvd1_off_voltage  # LLVD1下电电压,4字节浮点数
       self.llvd1_on_voltage = llvd1_on_voltage   # LLVD1上电电压,4字节浮点数
       self.llvd2_off_voltage = llvd2_off_voltage  # LLVD2下电电压,4字节浮点数
       self.llvd2_on_voltage = llvd2_on_voltage   # LLVD2上电电压,4字节浮点数
       self.llvd3_off_voltage = llvd3_off_voltage  # LLVD3下电电压,4字节浮点数
       self.llvd3_on_voltage = llvd3_on_voltage   # LLVD3上电电压,4字节浮点数
       self.llvd4_off_voltage = llvd4_off_voltage  # LLVD4下电电压,4字节浮点数  
       self.llvd4_on_voltage = llvd4_on_voltage   # LLVD4上电电压,4字节浮点数
       self.battery_capacity = battery_capacity  # 每组电池额定容量,4字节浮点数
       self.battery_test_stop_voltage = battery_test_stop_voltage  # 电池测试终止电压,4字节浮点数
       self.battery_temp_coeff = battery_temp_coeff  # 电池组温补系数,4字节浮点数
       self.battery_temp_center = battery_temp_center  # 电池温补中心点,4字节浮点数
       self.float_to_equalize_coeff = float_to_equalize_coeff  # 浮充转均充系数,4字节浮点数  
       self.equalize_to_float_coeff = equalize_to_float_coeff  # 均充转浮充系数,4字节浮点数
       self.llvd1_off_time = llvd1_off_time   # LLVD1下电时间,4字节浮点数
       self.llvd2_off_time = llvd2_off_time   # LLVD2下电时间,4字节浮点数
       self.llvd3_off_time = llvd3_off_time   # LLVD3下电时间,4字节浮点数
       self.llvd4_off_time = llvd4_off_time   # LLVD4下电时间,4字节浮点数
       self.load_off_mode = load_off_mode    # 负载下电模式,1字节

    def to_bytes(self):
        data = bytearray(struct.pack('<ff', self.dc_over_voltage, self.dc_under_voltage))
        data.extend(struct.pack('<BHHBffff', self.time_equalize_charge_enable.value, self.time_equalize_duration,
                                self.time_equalize_interval, self.battery_group_number, self.battery_over_temp,
                                self.battery_under_temp, self.env_over_temp, self.env_under_temp))  
        data.extend(struct.pack('<ffffffffffffffffffffffff', self.env_over_humidity, self.battery_charge_current_limit,
                                self.float_voltage, self.equalize_voltage, self.battery_off_voltage, self.battery_on_voltage,
                                self.llvd1_off_voltage, self.llvd1_on_voltage, self.llvd2_off_voltage, self.llvd2_on_voltage,
                                self.llvd3_off_voltage, self.llvd3_on_voltage, self.llvd4_off_voltage, self.llvd4_on_voltage,  
                                self.battery_capacity, self.battery_test_stop_voltage, self.battery_temp_coeff,
                                self.battery_temp_center, self.float_to_equalize_coeff, self.equalize_to_float_coeff,
                                self.llvd1_off_time, self.llvd2_off_time, self.llvd3_off_time, self.llvd4_off_time))  
        data.extend(struct.pack('<B', self.load_off_mode.value))
        return bytes(data)

    @classmethod  
    def from_bytes(cls, data):
        (dc_over_voltage, dc_under_voltage, time_equalize_charge_enable, time_equalize_duration,
            time_equalize_interval, battery_group_number, battery_over_temp, battery_under_temp,
            env_over_temp, env_under_temp, env_over_humidity, battery_charge_current_limit,
            float_voltage, equalize_voltage, battery_off_voltage, battery_on_voltage, llvd1_off_voltage,
            llvd1_on_voltage, llvd2_off_voltage, llvd2_on_voltage, llvd3_off_voltage, llvd3_on_voltage,
            llvd4_off_voltage, llvd4_on_voltage, battery_capacity, battery_test_stop_voltage,
            battery_temp_coeff, battery_temp_center, float_to_equalize_coeff, equalize_to_float_coeff,
            llvd1_off_time, llvd2_off_time, llvd3_off_time, llvd4_off_time, load_off_mode) = struct.unpack('<ffBHHBffffffffffffffffffffffffffffB', data)
        return cls(dc_over_voltage, dc_under_voltage, EnableStatus(time_equalize_charge_enable),
                    time_equalize_duration, time_equalize_interval, battery_group_number,
                    battery_over_temp, battery_under_temp, env_over_temp, env_under_temp,
                    env_over_humidity, battery_charge_current_limit, float_voltage, equalize_voltage,
                    battery_off_voltage, battery_on_voltage, llvd1_off_voltage, llvd1_on_voltage,
                    llvd2_off_voltage, llvd2_on_voltage, llvd3_off_voltage, llvd3_on_voltage,
                    llvd4_off_voltage, llvd4_on_voltage, battery_capacity, battery_test_stop_voltage,
                    battery_temp_coeff, battery_temp_center, float_to_equalize_coeff, equalize_to_float_coeff,
                    llvd1_off_time, llvd2_off_time, llvd3_off_time, llvd4_off_time, LoadOffMode(load_off_mode))

    def to_dict(self):
        return {
            "dc_over_voltage": self.dc_over_voltage,
            "dc_under_voltage": self.dc_under_voltage,
            "time_equalize_charge_enable": self.time_equalize_charge_enable.name,
            "time_equalize_duration": self.time_equalize_duration,
            "time_equalize_interval": self.time_equalize_interval,
            "battery_group_number": self.battery_group_number,
            "battery_over_temp": self.battery_over_temp,  
            "battery_under_temp": self.battery_under_temp,
            "env_over_temp": self.env_over_temp,
            "env_under_temp": self.env_under_temp,
            "env_over_humidity": self.env_over_humidity,
            "battery_charge_current_limit": self.battery_charge_current_limit,
            "float_voltage": self.float_voltage,
            "equalize_voltage": self.equalize_voltage,
            "battery_off_voltage": self.battery_off_voltage,
            "battery_on_voltage": self.battery_on_voltage,  
            "llvd1_off_voltage": self.llvd1_off_voltage,
            "llvd1_on_voltage": self.llvd1_on_voltage,
            "llvd2_off_voltage": self.llvd2_off_voltage,  
            "llvd2_on_voltage": self.llvd2_on_voltage,
            "llvd3_off_voltage": self.llvd3_off_voltage,
            "llvd3_on_voltage": self.llvd3_on_voltage,
            "llvd4_off_voltage": self.llvd4_off_voltage,
            "llvd4_on_voltage": self.llvd4_on_voltage,
            "battery_capacity": self.battery_capacity,
            "battery_test_stop_voltage": self.battery_test_stop_voltage,
            "battery_temp_coeff": self.battery_temp_coeff,
            "battery_temp_center": self.battery_temp_center,
            "float_to_equalize_coeff": self.float_to_equalize_coeff,  
            "equalize_to_float_coeff": self.equalize_to_float_coeff,
            "llvd1_off_time": self.llvd1_off_time,
            "llvd2_off_time": self.llvd2_off_time,
            "llvd3_off_time": self.llvd3_off_time,
            "llvd4_off_time": self.llvd4_off_time,
            "load_off_mode": self.load_off_mode.name
        }

@dataclass
class SystemControlState:
   def __init__(self, state: SystemControlState):  
       self.state = state   # 系统控制状态,1字节
   
   def to_bytes(self):
       return struct.pack('<B', self.state.value)
       
   @classmethod
   def from_bytes(cls, data):
       state, = struct.unpack('<B', data)  
       return cls(SystemControlState(state))

   def to_dict(self):
       return {
           "state": self.state.name
       }

@dataclass
class AlarmSoundEnable:
   def __init__(self, enable: EnableStatus):
       self.enable = enable   # 告警音使能,1字节  
   
   def to_bytes(self):
       return struct.pack('<B', self.enable.value)
       
   @classmethod  
   def from_bytes(cls, data):
       enable, = struct.unpack('<B', data)
       return cls(EnableStatus(enable))

   def to_dict(self):
       return {
           "enable": self.enable.name
       }

@dataclass
class EnergyParams:
   def __init__(self, energy_saving: EnableStatus, min_working_modules: int, module_switch_cycle: int,
                module_best_efficiency_point: int, module_redundancy_point: int):
       self.energy_saving = energy_saving   # 节能允许,1字节,0:使能,1:禁止  
       self.min_working_modules = min_working_modules   # 最小工作模块数,1字节
       self.module_switch_cycle = module_switch_cycle   # 模块循环开关周期,2字节
       self.module_best_efficiency_point = module_best_efficiency_point   # 模块最佳效率点,1字节
       self.module_redundancy_point = module_redundancy_point   # 模块冗余点,1字节
   
   def to_bytes(self):
       return struct.pack('<BBHBB', self.energy_saving.value, self.min_working_modules, self.module_switch_cycle,
                          self.module_best_efficiency_point, self.module_redundancy_point)
       
   @classmethod
   def from_bytes(cls, data):
       (energy_saving, min_working_modules, module_switch_cycle,   
        module_best_efficiency_point, module_redundancy_point) = struct.unpack('<BBHBB', data)
       return cls(EnableStatus(energy_saving), min_working_modules, module_switch_cycle,
                  module_best_efficiency_point, module_redundancy_point)

   def to_dict(self):
       return {
           "energy_saving": self.energy_saving.name,
           "min_working_modules": self.min_working_modules,
           "module_switch_cycle": self.module_switch_cycle,
           "module_best_efficiency_point": self.module_best_efficiency_point,
           "module_redundancy_point": self.module_redundancy_point
       }
   
@dataclass
class SystemControl:
   def __init__(self, control_type: SystemControlType):
       self.control_type = control_type   # 控制类型,1字节
   
   def to_bytes(self):
       return struct.pack('<B', self.control_type.value)
       
   @classmethod
   def from_bytes(cls, data):
       control_type, = struct.unpack('<B', data)
       return cls(SystemControlType(control_type))

   def to_dict(self):
       return {
           "control_type": self.control_type.name  
       }

        
# 命令类        
class Command:
    def __init__(self, cid1, cid2, key, name, request_class, response_class):
        self.cid1 = cid1
        self.cid2 = cid2
        self.key = key
        self.name = name
        self.request_class = request_class
        self.response_class = response_class
        
