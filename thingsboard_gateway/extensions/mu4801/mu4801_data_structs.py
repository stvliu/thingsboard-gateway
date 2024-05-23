import struct
from dataclasses import dataclass
from typing import List
from datetime import datetime

@dataclass
class InfoStruct:
    device_name: str
    software_version: str
    manufacturer: str

    def to_bytes(self):
        return (
            self.device_name.ljust(10).encode('ascii')[:10] + 
            self.software_version.ljust(2).encode('ascii')[:2] +
            self.manufacturer.ljust(20).encode('ascii')[:20]
        )
    
    @classmethod
    def from_bytes(cls, data):
        return cls(
            device_name=data[:10].decode('ascii').rstrip(),
            software_version=data[10:12].decode('ascii'),
            manufacturer=data[12:].decode('ascii').rstrip()
        )
        
    def __str__(self):
        return f"InfoStruct(device_name='{self.device_name}', software_version='{self.software_version}', manufacturer='{self.manufacturer}')"

@dataclass  
class AcAnalogStruct:
    voltage_ph_a: float = 0
    voltage_ph_b: float = 0 
    voltage_ph_c: float = 0
    ac_freq: float = 0
    ac_current: float = 0

    def to_bytes(self):
        return struct.pack('<fffff', self.voltage_ph_a, self.voltage_ph_b, self.voltage_ph_c, 
                           self.ac_freq, self.ac_current)

    @classmethod
    def from_bytes(cls, data):
        return cls(*struct.unpack('<fffff', data))
        
    def __str__(self):
        return f"AcAnalogStruct(voltage_ph_a={self.voltage_ph_a}, voltage_ph_b={self.voltage_ph_b}, voltage_ph_c={self.voltage_ph_c}, ac_freq={self.ac_freq}, ac_current={self.ac_current})"

@dataclass
class AcAlarmStruct:
    spd_alarm: int = 0
    over_voltage_ph_a: int = 0
    over_voltage_ph_b: int = 0
    over_voltage_ph_c: int = 0  
    under_voltage_ph_a: int = 0
    under_voltage_ph_b: int = 0
    under_voltage_ph_c: int = 0

    def to_bytes(self):
        return struct.pack('<BBBBBBB', self.spd_alarm, self.over_voltage_ph_a, self.over_voltage_ph_b,
                           self.over_voltage_ph_c, self.under_voltage_ph_a, self.under_voltage_ph_b,
                           self.under_voltage_ph_c)
    
    @classmethod 
    def from_bytes(cls, data):
        return cls(*struct.unpack('<BBBBBBB', data))
        
    def __str__(self):
        return f"AcAlarmStruct(spd_alarm={self.spd_alarm}, over_voltage_ph_a={self.over_voltage_ph_a}, over_voltage_ph_b={self.over_voltage_ph_b}, over_voltage_ph_c={self.over_voltage_ph_c}, under_voltage_ph_a={self.under_voltage_ph_a}, under_voltage_ph_b={self.under_voltage_ph_b}, under_voltage_ph_c={self.under_voltage_ph_c})"

@dataclass
class AcConfigStruct:
    ac_over_voltage: float = 0
    ac_under_voltage: float = 0

    def to_bytes(self):
        return struct.pack('<ff', self.ac_over_voltage, self.ac_under_voltage)

    @classmethod
    def from_bytes(cls, data):
        return cls(*struct.unpack('<ff', data))   

    def __str__(self):
        return f"AcConfigStruct(ac_over_voltage={self.ac_over_voltage}, ac_under_voltage={self.ac_under_voltage})"

@dataclass
class RectAnalogStruct:
    output_voltage: float
    module_count: int 
    module_currents: List[float]  

    def to_bytes(self):  
        return struct.pack(f'<fB{len(self.module_currents)}f', self.output_voltage, self.module_count, *self.module_currents)

    @classmethod
    def from_bytes(cls, data):
        module_count = data[4]  # 模块数量在第5个字节
        unpack_fmt = f'<fB{module_count}f'
        return cls(*struct.unpack_from(unpack_fmt, data))
        
    def __str__(self):
        return f"RectAnalogStruct(output_voltage={self.output_voltage}, module_count={self.module_count}, module_currents={self.module_currents})"

@dataclass    
class RectStatusStruct:
    module_count: int
    status_list: List[int]  

    def to_bytes(self):
        return struct.pack(f'<B{len(self.status_list)}B', self.module_count, *self.status_list)

    @classmethod  
    def from_bytes(cls, data):
        module_count = data[0] 
        return cls(module_count=module_count, status_list=list(data[1:module_count+1]))
        
    def __str__(self):
        return f"RectStatusStruct(module_count={self.module_count}, status_list={self.status_list})"

@dataclass
class RectAlarmStruct:
    module_count: int  
    alarm_list: List[int]

    def to_bytes(self):
        return struct.pack(f'<B{len(self.alarm_list)}B', self.module_count, *self.alarm_list) 

    @classmethod
    def from_bytes(cls, data):
        module_count = data[0]
        return cls(module_count=module_count, alarm_list=list(data[1:module_count+1]))
        
    def __str__(self):
        return f"RectAlarmStruct(module_count={self.module_count}, alarm_list={self.alarm_list})"

@dataclass 
class DcAnalogStruct:
    voltage: float
    total_current: float  
    battery_current: float
    load_branch_currents: List[float] 

    def to_bytes(self):
        return struct.pack(f'<fffBf', self.voltage, self.total_current, self.battery_current,
                           len(self.load_branch_currents), *self.load_branch_currents)

    @classmethod
    def from_bytes(cls, data):
        voltage, total_current, battery_current = struct.unpack_from('<fff', data)
        branch_count = data[12]  # 分路数量在第13个字节  
        branch_currents = list(struct.unpack_from(f'<{branch_count}f', data, 13))
        return cls(voltage, total_current, battery_current, branch_currents)
        
    def __str__(self):
        return f"DcAnalogStruct(voltage={self.voltage}, total_current={self.total_current}, battery_current={self.battery_current}, load_branch_currents={self.load_branch_currents})"

@dataclass
class DcAlarmStruct:   
    over_voltage: int = 0
    under_voltage: int = 0  
    spd_alarm: int = 0
    fuse1_alarm: int = 0
    fuse2_alarm: int = 0
    fuse3_alarm: int = 0  
    fuse4_alarm: int = 0

    def to_bytes(self):
        return struct.pack('<BBBBBBB', self.over_voltage, self.under_voltage, self.spd_alarm,
                           self.fuse1_alarm, self.fuse2_alarm, self.fuse3_alarm, self.fuse4_alarm)  

    @classmethod  
    def from_bytes(cls, data):
        return cls(*struct.unpack('<BBBBBBB', data))

    def __str__(self):
        return f"DcAlarmStruct(over_voltage={self.over_voltage}, under_voltage={self.under_voltage}, spd_alarm={self.spd_alarm}, fuse1_alarm={self.fuse1_alarm}, fuse2_alarm={self.fuse2_alarm}, fuse3_alarm={self.fuse3_alarm}, fuse4_alarm={self.fuse4_alarm})"

@dataclass
class DcConfigStruct:
    voltage_upper_limit: float
    voltage_lower_limit: float 
    current_limit: float

    def to_bytes(self):
        return struct.pack('<fff', self.voltage_upper_limit, self.voltage_lower_limit, self.current_limit)

    @classmethod
    def from_bytes(cls, data):  
        return cls(*struct.unpack('<fff', data))

    def __str__(self):
        return f"DcConfigStruct(voltage_upper_limit={self.voltage_upper_limit}, voltage_lower_limit={self.voltage_lower_limit}, current_limit={self.current_limit})"

@dataclass 
class DateTimeStruct:
    year: int
    month: int 
    day: int
    hour: int
    minute: int  
    second: int

    def to_bytes(self): 
        return struct.pack('<HBBBBB', self.year, self.month, self.day, self.hour, self.minute, self.second)

    @classmethod
    def from_bytes(cls, data):
        return cls(*struct.unpack('<HBBBBB', data))

    @classmethod
    def from_datetime(cls, dt):
        return cls(
            year=dt.year,
            month=dt.month,
            day=dt.day,
            hour=dt.hour,
            minute=dt.minute,
            second=dt.second
        )

    def to_datetime(self):
        return datetime(self.year, self.month, self.day, self.hour, self.minute, self.second)

    @classmethod  
    def from_str(cls, dt_str): 
        return cls(*map(int, datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").timetuple()[:6]))

    def __str__(self):
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d} {self.hour:02d}:{self.minute:02d}:{self.second:02d}"