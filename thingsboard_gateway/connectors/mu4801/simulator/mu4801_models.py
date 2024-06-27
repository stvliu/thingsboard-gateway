import struct
from enum import Enum
from typing import List, Dict, Any, Set
from dataclasses import dataclass
import logging
logging.basicConfig(level=logging.DEBUG)

# 常量定义
COLLECTOR_NAME_LENGTH = 10
MANUFACTURER_NAME_LENGTH = 20
AC_RESERVED_PARAMS_COUNT = 30
RECT_MODULE_RESERVED_PARAMS_COUNT = 7
DC_USER_DEFINED_PARAMS_COUNT = 55
BATTERY_GROUP_COUNT = 6
LOAD_BRANCH_COUNT = 4
ENV_TEMP_COUNT = 3
ENV_HUMIDITY_COUNT = 3

# 固定值常量
DEFAULT_FLOAT_VALUE = 0.0
DEFAULT_INT_VALUE = 0
DEFAULT_BATTERY_GROUP_COUNT = 1
DEFAULT_LOAD_BRANCH_COUNT = 4

class DataFlag(Enum):
    NORMAL = 0

class AlarmStatus(Enum):
    NORMAL = 0
    ALARM = 0x81

class SwitchStatus(Enum):
    ON = 0
    OFF = 1

class EnableStatus(Enum):
    ENABLE = 0xE0
    DISABLE = 0xE1

class LoadOffMode(Enum):
    VOLTAGE = 0
    TIME = 1

class RectModuleControlType(Enum):
    ON = 0x20
    OFF = 0x2F

class SystemControlStateModel(Enum):
    AUTO = 0xE0
    MANUAL = 0xE1

class SystemControlType(Enum):
    RESET = 0xE1
    LOAD1_OFF = 0xE5
    LOAD1_ON = 0xE6
    LOAD2_OFF = 0xE7
    LOAD2_ON = 0xE8
    LOAD3_OFF = 0xE9
    LOAD3_ON = 0xEA
    LOAD4_OFF = 0xEB
    LOAD4_ON = 0xEC
    BATTERY_OFF = 0xED
    BATTERY_ON = 0xEE

class VoltageStatus(Enum):
    NORMAL = 0
    UNDER = 1
    OVER = 2

class FrequencyStatus(Enum):
    NORMAL = 0
    UNDER = 1
    OVER = 2

class TempStatus(Enum):
    NORMAL = 0
    OVER = 0xB0
    UNDER = 0xB1

class SensorStatus(Enum):
    NORMAL = 0
    BREAK = 0xB2
    FAULT = 0xB3

class LVDStatus(Enum):
    NORMAL = 0
    IMPENDING = 1
    OFF = 2

class ChargeStatus(Enum):
    FLOAT = 0
    EQUALIZE = 1
    TEST = 2

class BaseModel:
    _supported_fields: Set[str] = set()
    _unsupported_fields: Dict[str, Any] = {}
    _fixed_fields: Dict[str, Any] = {}

    def _init_unsupported_fields(self):
        for field, default_value in self._unsupported_fields.items():
            setattr(self, field, default_value)

    def _init_fixed_fields(self):
        for field, default_value in self._fixed_fields.items():
            setattr(self, field, default_value)

    def to_dict(self):
        return {
            k: v.name if isinstance(v, Enum) else
            [item.name for item in v] if isinstance(v, list) and v and isinstance(v[0], Enum) else
            v
            for k, v in self.__dict__.items()
            if k in self._supported_fields and k not in self._fixed_fields
        }

    @classmethod
    def from_dict(cls, data):
        instance = cls()
        for k, v in data.items():
            if k in cls._supported_fields and k not in cls._fixed_fields:
                setattr(instance, k, v)
        instance._init_unsupported_fields()
        instance._init_fixed_fields()
        return instance


    def to_bytes(self):
        raise NotImplementedError("Subclasses must implement to_bytes method")

    @classmethod
    def from_bytes(cls, data):
        raise NotImplementedError("Subclasses must implement from_bytes method")

@dataclass
class DateTime(BaseModel):
    _supported_fields = {'year', 'month', 'day', 'hour', 'minute', 'second'}

    def __init__(self, year: int = DEFAULT_INT_VALUE, month: int = 1, day: int = 1,
                 hour: int = DEFAULT_INT_VALUE, minute: int = DEFAULT_INT_VALUE, second: int = DEFAULT_INT_VALUE):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second

    def to_bytes(self):
        return struct.pack('>HBBBBB', self.year, self.month, self.day, self.hour, self.minute, self.second)

    @classmethod
    def from_bytes(cls, data):
        return cls(*struct.unpack('>HBBBBB', data))

    def __str__(self):
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d} {self.hour:02d}:{self.minute:02d}:{self.second:02d}"

@dataclass
class ProtocolVersion(BaseModel):
    _supported_fields = {'version'}

    def __init__(self, version: str = 'V2.1'):
        self.version = version

    def to_bytes(self):
        return self.version.encode('ascii')

    @classmethod
    def from_bytes(cls, data):
        return cls(data.decode('ascii'))

@dataclass
class DeviceAddress(BaseModel):
    _supported_fields = {'address'}

    def __init__(self, address: int = DEFAULT_INT_VALUE):
        self.address = address

    def to_bytes(self):
        return struct.pack('B', self.address)

    @classmethod
    def from_bytes(cls, data):
        return cls(struct.unpack('B', data)[0])

@dataclass
class SoftwareVersion(BaseModel):
    _supported_fields = {'major', 'minor'}

    def __init__(self, major: int = 1, minor: int = DEFAULT_INT_VALUE):
        self.major = major
        self.minor = minor

    def to_bytes(self):
        return struct.pack('BB', self.major, self.minor)

    @classmethod
    def from_bytes(cls, data):
        return cls(*struct.unpack('BB', data))

    def __str__(self):
        return f"{self.major}.{self.minor}"

@dataclass
class ManufacturerInfo(BaseModel):
    _supported_fields = {'collector_name', 'software_version', 'manufacturer'}

    def __init__(self, collector_name: str = '', software_version: SoftwareVersion = None, manufacturer: str = ''):
        self.collector_name = collector_name
        self.software_version = software_version or SoftwareVersion()
        self.manufacturer = manufacturer

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
    _supported_fields = {'input_voltage_ab_a', 'input_voltage_bc_b', 'input_voltage_ca_c', 'input_frequency'}
    _unsupported_fields = {
        '_output_current_a': DEFAULT_FLOAT_VALUE,
        '_output_current_b': DEFAULT_FLOAT_VALUE,
        '_output_current_c': DEFAULT_FLOAT_VALUE,
        '_reserved': [DEFAULT_FLOAT_VALUE] * AC_RESERVED_PARAMS_COUNT
    }
    _fixed_fields = {'data_flag': DataFlag.NORMAL, 'number_of_ac_inputs': 1, 'user_defined_params_count': AC_RESERVED_PARAMS_COUNT}

    def __init__(self, input_voltage_ab_a: float = DEFAULT_FLOAT_VALUE,
                 input_voltage_bc_b: float = DEFAULT_FLOAT_VALUE,
                 input_voltage_ca_c: float = DEFAULT_FLOAT_VALUE,
                 input_frequency: float = DEFAULT_FLOAT_VALUE):
        self.data_flag = DataFlag.NORMAL
        self.number_of_ac_inputs = 1
        self.input_voltage_ab_a = input_voltage_ab_a
        self.input_voltage_bc_b = input_voltage_bc_b
        self.input_voltage_ca_c = input_voltage_ca_c
        self.input_frequency = input_frequency
        self.user_defined_params_count = AC_RESERVED_PARAMS_COUNT
        self._init_unsupported_fields()

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
    _supported_fields = {'input_voltage_ab_a_status', 'input_voltage_bc_b_status', 'input_voltage_ca_c_status',
                         'ac_arrester_status', 'ac_input_switch_status', 'ac_power_status'}
    _unsupported_fields = {
        '_frequency_status': FrequencyStatus.NORMAL,
        '_ac_comm_failure_status': AlarmStatus.NORMAL,
        '_ac_output_switch_status': AlarmStatus.NORMAL,
        '_reserved': [AlarmStatus.NORMAL] * 13,
        '_input_current_a_status': AlarmStatus.NORMAL,
        '_input_current_b_status': AlarmStatus.NORMAL,
        '_input_current_c_status': AlarmStatus.NORMAL
    }
    _fixed_fields = {'data_flag': DataFlag.NORMAL, 'number_of_inputs': 1, 'fuse_count': 0, 'user_defined_params_count': 18}

    def __init__(self, input_voltage_ab_a_status: VoltageStatus = VoltageStatus.NORMAL,
                 input_voltage_bc_b_status: VoltageStatus = VoltageStatus.NORMAL,
                 input_voltage_ca_c_status: VoltageStatus = VoltageStatus.NORMAL,
                 ac_arrester_status: AlarmStatus = AlarmStatus.NORMAL,
                 ac_input_switch_status: AlarmStatus = AlarmStatus.NORMAL,
                 ac_power_status: AlarmStatus = AlarmStatus.NORMAL):
        self.data_flag = DataFlag.NORMAL
        self.number_of_inputs = 1
        self.input_voltage_ab_a_status = input_voltage_ab_a_status
        self.input_voltage_bc_b_status = input_voltage_bc_b_status
        self.input_voltage_ca_c_status = input_voltage_ca_c_status
        self.fuse_count = 0
        self.user_defined_params_count = 18
        self.ac_arrester_status = ac_arrester_status
        self.ac_input_switch_status = ac_input_switch_status
        self.ac_power_status = ac_power_status
        self._init_unsupported_fields()

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
                           self.ac_input_switch_status.value,
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
            ac_arrester_status=AlarmStatus(unpacked[8]),
            ac_input_switch_status=AlarmStatus(unpacked[10]),
            ac_power_status=AlarmStatus(unpacked[12])
        )
        instance._frequency_status = FrequencyStatus(unpacked[5])
        instance._ac_comm_failure_status = AlarmStatus(unpacked[9])
        instance._ac_output_switch_status = AlarmStatus(unpacked[11])
        instance._reserved = [AlarmStatus(status) for status in unpacked[13:26]]
        instance._input_current_a_status = AlarmStatus(unpacked[26])
        instance._input_current_b_status = AlarmStatus(unpacked[27])
        instance._input_current_c_status = AlarmStatus(unpacked[28])
        return instance

@dataclass
class AcConfigParams(BaseModel):
    _supported_fields = {'ac_over_voltage', 'ac_under_voltage'}
    _unsupported_fields = {
        '_ac_output_current_limit': DEFAULT_FLOAT_VALUE,
        '_frequency_upper_limit': DEFAULT_FLOAT_VALUE,
        '_frequency_lower_limit': DEFAULT_FLOAT_VALUE
    }

    def __init__(self, ac_over_voltage: float = DEFAULT_FLOAT_VALUE, ac_under_voltage: float = DEFAULT_FLOAT_VALUE):
        self.ac_over_voltage = ac_over_voltage
        self.ac_under_voltage = ac_under_voltage
        self._init_unsupported_fields()

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
    _supported_fields = {'output_voltage', 'module_count', 'module_currents', 'module_current_limit',
                         'module_voltage', 'module_temperature', 'module_input_voltage_ab'}
    _unsupported_fields = {
        '_module_input_voltage_bc': [DEFAULT_FLOAT_VALUE] * BATTERY_GROUP_COUNT,
        '_module_input_voltage_ca': [DEFAULT_FLOAT_VALUE] * BATTERY_GROUP_COUNT,
        '_reserved': [DEFAULT_FLOAT_VALUE] * 7
    }
    _fixed_fields = {'data_flag': DataFlag.NORMAL, 'user_defined_params_count': 13}

    def __init__(self, output_voltage: float = DEFAULT_FLOAT_VALUE, module_count: int = DEFAULT_INT_VALUE,
                 module_currents: List[float] = None, module_current_limit: List[float] = None,
                 module_voltage: List[float] = None, module_temperature: List[float] = None,
                 module_input_voltage_ab: List[float] = None):
        self.data_flag = DataFlag.NORMAL
        self.output_voltage = output_voltage
        self.module_count = module_count
        self.module_currents = module_currents or []
        self.module_current_limit = module_current_limit or []
        self.module_voltage = module_voltage or []
        self.module_temperature = module_temperature or []
        self.module_input_voltage_ab = module_input_voltage_ab or []
        self.user_defined_params_count = 13  # 固定值
        self._init_unsupported_fields()

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
    _supported_fields = {'module_count', 'module_run_status', 'module_limit_status'}
    _unsupported_fields = {
        '_module_charge_status': [ChargeStatus.FLOAT] * BATTERY_GROUP_COUNT,
        '_module_ac_limit_power': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,
        '_module_temp_limit_power': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,
        '_module_fan_full_speed': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,
        '_module_walk_in_mode': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,
        '_module_sequential_start': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,
        '_reserved': [AlarmStatus.NORMAL] * 11
    }
    _fixed_fields = {'data_flag': DataFlag.NORMAL, 'user_defined_params_count': 16}

    def __init__(self, module_count: int = DEFAULT_INT_VALUE,
                 module_run_status: List[SwitchStatus] = None,
                 module_limit_status: List[SwitchStatus] = None):
        self.data_flag = DataFlag.NORMAL
        self.module_count = module_count
        self.module_run_status = module_run_status or []
        self.module_limit_status = module_limit_status or []
        self.user_defined_params_count = 16  # 固定为16
        self._init_unsupported_fields()

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
    _supported_fields = {'module_count', 'module_failure_status', 'module_comm_failure_status',
                         'module_protection_status', 'module_fan_status'}
    _unsupported_fields = {
        '_module_unbalanced_current': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,
        '_module_ac_overvoltage': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,
        '_module_ac_undervoltage': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,
        '_module_ac_unbalanced': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,
        '_module_ac_phase_loss': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,
        '_module_env_temp_abnormal': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,
        '_reserved': [AlarmStatus.NORMAL] * 9
    }
    _fixed_fields = {'data_flag': DataFlag.NORMAL, 'user_defined_params_count': 18}

    def __init__(self, module_count: int = DEFAULT_INT_VALUE, module_failure_status: List[AlarmStatus] = None,
                 module_comm_failure_status: List[AlarmStatus] = None,
                 module_protection_status: List[AlarmStatus] = None, module_fan_status: List[AlarmStatus] = None):
        self.data_flag = DataFlag.NORMAL
        self.module_count = module_count
        self.module_failure_status = module_failure_status or []
        self.module_comm_failure_status = module_comm_failure_status or []
        self.module_protection_status = module_protection_status or []
        self.module_fan_status = module_fan_status or []
        self.user_defined_params_count = 18
        self._init_unsupported_fields()

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
    _supported_fields = {'dc_voltage', 'total_load_current', 'battery_group_1_current',
                         'load_branch_1_current', 'load_branch_2_current', 'load_branch_3_current', 'load_branch_4_current',
                         'battery_total_current', 'battery_group_1_capacity', 'battery_group_1_voltage',
                         'battery_group_1_mid_voltage', 'battery_group_2_mid_voltage', 'battery_group_3_mid_voltage',
                         'battery_group_4_mid_voltage', 'battery_group_1_temperature', 'env_temp_1', 'env_temp_2',
                         'env_humidity_1', 'total_load_power', 'load_power_1', 'load_power_2', 'load_power_3',
                         'load_power_4', 'total_load_energy', 'load_energy_1', 'load_energy_2', 'load_energy_3',
                         'load_energy_4'}
    _unsupported_fields = {
        '_battery_group_2_current': DEFAULT_FLOAT_VALUE,
        '_battery_group_3_current': DEFAULT_FLOAT_VALUE,
        '_battery_group_4_current': DEFAULT_FLOAT_VALUE,
        '_battery_group_5_current': DEFAULT_FLOAT_VALUE,
        '_battery_group_6_current': DEFAULT_FLOAT_VALUE,
        '_battery_group_2_voltage': DEFAULT_FLOAT_VALUE,
        '_battery_group_3_voltage': DEFAULT_FLOAT_VALUE,
        '_battery_group_4_voltage': DEFAULT_FLOAT_VALUE,
        '_battery_group_5_voltage': DEFAULT_FLOAT_VALUE,
        '_battery_group_6_voltage': DEFAULT_FLOAT_VALUE,
        '_battery_group_5_mid_voltage': DEFAULT_FLOAT_VALUE,
        '_battery_group_6_mid_voltage': DEFAULT_FLOAT_VALUE,
        '_battery_group_2_capacity': DEFAULT_FLOAT_VALUE,
        '_battery_group_3_capacity': DEFAULT_FLOAT_VALUE,
        '_battery_group_4_capacity': DEFAULT_FLOAT_VALUE,
        '_battery_group_5_capacity': DEFAULT_FLOAT_VALUE,
        '_battery_group_6_capacity': DEFAULT_FLOAT_VALUE,
        '_battery_group_2_temperature': DEFAULT_FLOAT_VALUE,
        '_battery_group_3_temperature': DEFAULT_FLOAT_VALUE,
        '_battery_group_4_temperature': DEFAULT_FLOAT_VALUE,
        '_battery_group_5_temperature': DEFAULT_FLOAT_VALUE,
        '_battery_group_6_temperature': DEFAULT_FLOAT_VALUE,
        '_env_temp_3': DEFAULT_FLOAT_VALUE,
        '_env_humidity_2': DEFAULT_FLOAT_VALUE,
        '_env_humidity_3': DEFAULT_FLOAT_VALUE,
        '_reserved': [DEFAULT_FLOAT_VALUE] * 2
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
        self.dc_voltage = dc_voltage
        self.total_load_current = total_load_current
        self.battery_group_1_current = battery_group_1_current
        self.load_branch_1_current = load_branch_1_current
        self.load_branch_2_current = load_branch_2_current
        self.load_branch_3_current = load_branch_3_current
        self.load_branch_4_current = load_branch_4_current
        self.battery_total_current = battery_total_current
        self.battery_group_1_capacity = battery_group_1_capacity
        self.battery_group_1_voltage = battery_group_1_voltage
        self.battery_group_1_mid_voltage = battery_group_1_mid_voltage
        self.battery_group_2_mid_voltage = battery_group_2_mid_voltage
        self.battery_group_3_mid_voltage = battery_group_3_mid_voltage
        self.battery_group_4_mid_voltage = battery_group_4_mid_voltage
        self.battery_group_1_temperature = battery_group_1_temperature
        self.env_temp_1 = env_temp_1
        self.env_temp_2 = env_temp_2
        self.env_humidity_1 = env_humidity_1
        self.total_load_power = total_load_power
        self.load_power_1 = load_power_1
        self.load_power_2 = load_power_2
        self.load_power_3 = load_power_3
        self.load_power_4 = load_power_4
        self.total_load_energy = total_load_energy
        self.load_energy_1 = load_energy_1
        self.load_energy_2 = load_energy_2
        self.load_energy_3 = load_energy_3
        self.load_energy_4 = load_energy_4
        self._init_unsupported_fields()
        self._init_fixed_fields()

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
        '_dc_comm_failure_status': AlarmStatus.NORMAL,
        '_battery_group_charge_overcurrent': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,
        '_battery_group_unbalanced': [AlarmStatus.NORMAL] * BATTERY_GROUP_COUNT,
        '_blvd_impending': AlarmStatus.NORMAL,
        '_llvd1_impending': AlarmStatus.NORMAL,
        '_llvd2_impending': AlarmStatus.NORMAL,
        '_llvd3_impending': AlarmStatus.NORMAL,
        '_llvd4_impending': AlarmStatus.NORMAL,
        '_battery_temp_sensor_2_status': SensorStatus.NORMAL,
        '_battery_temp_sensor_3_status': SensorStatus.NORMAL,
        '_battery_temp_sensor_4_status': SensorStatus.NORMAL,
        '_battery_temp_sensor_5_status': SensorStatus.NORMAL,
        '_battery_temp_sensor_6_status': SensorStatus.NORMAL,
        '_env_temp_sensor_3_status': SensorStatus.NORMAL,
        '_env_humidity_sensor_2_status': SensorStatus.NORMAL,
        '_env_humidity_sensor_3_status': SensorStatus.NORMAL,
        '_infrared_status': AlarmStatus.NORMAL,
        '_reserved': [AlarmStatus.NORMAL] * 72
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

        # 初始化固定字段
        for field, value in self._fixed_fields.items():
            setattr(self, field, value)

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

        # 初始化不支持的字段
        for field, value in self._unsupported_fields.items():
            setattr(self, field, value)

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
        format_string += 'B'  # _i
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
        self.dc_over_voltage = dc_over_voltage
        self.dc_under_voltage = dc_under_voltage
        self.time_equalize_charge_enable = time_equalize_charge_enable
        self.time_equalize_duration = time_equalize_duration
        self.time_equalize_interval = time_equalize_interval
        self.battery_group_number = battery_group_number
        self.battery_over_temp = battery_over_temp
        self.battery_under_temp = battery_under_temp
        self.env_over_temp = env_over_temp
        self.env_under_temp = env_under_temp
        self.env_over_humidity = env_over_humidity
        self.env_under_humidity = env_under_humidity
        self.battery_charge_current_limit = battery_charge_current_limit
        self.float_voltage = float_voltage
        self.equalize_voltage = equalize_voltage
        self.battery_off_voltage = battery_off_voltage
        self.battery_on_voltage = battery_on_voltage
        self.llvd1_off_voltage = llvd1_off_voltage
        self.llvd1_on_voltage = llvd1_on_voltage
        self.llvd2_off_voltage = llvd2_off_voltage
        self.llvd2_on_voltage = llvd2_on_voltage
        self.llvd3_off_voltage = llvd3_off_voltage
        self.llvd3_on_voltage = llvd3_on_voltage
        self.llvd4_off_voltage = llvd4_off_voltage
        self.llvd4_on_voltage = llvd4_on_voltage
        self.battery_capacity = battery_capacity
        self.battery_test_stop_voltage = battery_test_stop_voltage
        self.battery_temp_coeff = battery_temp_coeff
        self.battery_temp_center = battery_temp_center
        self.float_to_equalize_coeff = float_to_equalize_coeff
        self.equalize_to_float_coeff = equalize_to_float_coeff
        self.llvd1_off_time = llvd1_off_time
        self.llvd2_off_time = llvd2_off_time
        self.llvd3_off_time = llvd3_off_time
        self.llvd4_off_time = llvd4_off_time
        self.load_off_mode = load_off_mode

        # 初始化"不支持"字段、"固定"字段为默认值
        self._init_unsupported_fields()
        self._init_fixed_fields()

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
    _supported_fields = {'module_id', 'control_type'}

    def __init__(self, module_id: int = DEFAULT_INT_VALUE, control_type: RectModuleControlType = RectModuleControlType.ON):
        self.module_id = module_id
        self.control_type = control_type

    def to_bytes(self):
        return struct.pack('<BB', self.module_id, self.control_type.value)

    @classmethod
    def from_bytes(cls, data):
        module_id, control_type = struct.unpack('<BB', data)
        return cls(module_id, RectModuleControlType(control_type))

@dataclass
class SystemControlState(BaseModel):
    _supported_fields = {'state'}

    def __init__(self, state: SystemControlStateModel = SystemControlStateModel.AUTO):
        self.state = state

    def to_bytes(self):
        return struct.pack('<B', self.state.value)

    @classmethod
    def from_bytes(cls, data):
        state, = struct.unpack('<B', data)
        return cls(SystemControlStateModel(state))

@dataclass
class AlarmSoundEnable(BaseModel):
    _supported_fields = {'enable'}

    def __init__(self, enable: EnableStatus = EnableStatus.ENABLE):
        self.enable = enable

    def to_bytes(self):
        return struct.pack('<B', self.enable.value)

    @classmethod
    def from_bytes(cls, data):
        enable, = struct.unpack('<B', data)
        return cls(EnableStatus(enable))

@dataclass
class EnergyParams(BaseModel):
    _supported_fields = {'energy_saving', 'min_working_modules', 'module_switch_cycle',
                         'module_best_efficiency_point', 'module_redundancy_point'}
    _unsupported_fields = {'_reserved': [DEFAULT_INT_VALUE] * 18}

    def __init__(self, energy_saving: EnableStatus = EnableStatus.ENABLE,
                 min_working_modules: int = DEFAULT_INT_VALUE,
                 module_switch_cycle: int = DEFAULT_INT_VALUE,
                 module_best_efficiency_point: int = DEFAULT_INT_VALUE,
                 module_redundancy_point: int = DEFAULT_INT_VALUE):
        self.energy_saving = energy_saving
        self.min_working_modules = min_working_modules
        self.module_switch_cycle = module_switch_cycle
        self.module_best_efficiency_point = module_best_efficiency_point
        self.module_redundancy_point = module_redundancy_point
        self._init_unsupported_fields()

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
    _supported_fields = {'control_type'}

    def __init__(self, control_type: SystemControlType = SystemControlType.RESET):
        self.control_type = control_type

    def to_bytes(self):
        return struct.pack('<B', self.control_type.value)

    @classmethod
    def from_bytes(cls, data):
        control_type, = struct.unpack('<B', data)
        return cls(SystemControlType(control_type))

# 这里是 mu4801_models.py 文件的结束