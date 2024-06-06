from bscac_protocol import BscAcProtocol
import logging
import random
import time
import datetime

# 导入相关的数据类
from models import *

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class BscAcSimulator:
    def __init__(self, device_addr, port):
        self._log = logging.getLogger(self.__class__.__name__)
        self._protocol = BscAcProtocol(device_addr, port)
        self._protocol.connect()
        
        self.device_info = {
            'device_name': 'AC',
            'software_version': '1.00',
            'manufacturer': 'HAYDEN SUZHOU'
        }
        
        # 使用对应的数据类初始化模拟数据
        self.ac_analog_data = AcAnalogData(
            data_flag=DataFlag.NORMAL,
            cabinet_temp=25.0,
            supply_temp=20.0,
            voltage=220,
            current=10  
        )
        
        self.ac_run_status = AcRunStatus(
            air_conditioner=SwitchStatus.ON,
            indoor_fan=SwitchStatus.ON,
            outdoor_fan=SwitchStatus.ON,
            heater=SwitchStatus.OFF
        )
        
        self.ac_alarm_status = AcAlarmStatus(
            data_flag=DataFlag.NORMAL,
            compressor_alarm=AlarmStatus.NORMAL,
            high_temp=AlarmStatus.NORMAL,  
            low_temp=AlarmStatus.NORMAL,
            heater_alarm=AlarmStatus.NORMAL,
            sensor_fault=AlarmStatus.NORMAL,
            over_voltage=AlarmStatus.NORMAL,  
            under_voltage=AlarmStatus.NORMAL,
            reserved=AlarmStatus.INVALID
        )  
        
        self.ac_config_params = AcConfigParams(
            start_temp=270,  
            temp_hysteresis=10,
            heater_start_temp=180,
            heater_hysteresis=20,
            high_temp_alarm=320,
            low_temp_alarm=160
        )
        
    def handle_get_ac_analog_data(self):
        # 模拟一些随机波动
        self.ac_analog_data.cabinet_temp += random.uniform(-1.0, 1.0)
        self.ac_analog_data.supply_temp += random.uniform(-0.5, 0.5)
        self.ac_analog_data.voltage += random.randint(-5, 5)  
        self.ac_analog_data.current += random.randint(-1, 1)
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
            self.ac_run_status.air_conditioner = SwitchStatus.OFF
        elif command == RemoteCommand.COOLING_ON:
            self.ac_run_status.air_conditioner = SwitchStatus.ON
            self.ac_run_status.heater = SwitchStatus.OFF 
        elif command == RemoteCommand.COOLING_OFF:
            self.ac_run_status.air_conditioner = SwitchStatus.OFF
            self.ac_run_status.heater = SwitchStatus.OFF
        elif command == RemoteCommand.HEATING_ON:  
            self.ac_run_status.air_conditioner = SwitchStatus.ON
            self.ac_run_status.heater = SwitchStatus.ON
        elif command == RemoteCommand.HEATING_OFF:
            self.ac_run_status.air_conditioner = SwitchStatus.OFF   
            self.ac_run_status.heater = SwitchStatus.OFF
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
        while True:
            try:
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
                
if __name__ == '__main__':  
    device_addr = 1
    default_port = '/dev/ttyS5'
    port = input(f'请输入串口号(默认为{default_port}): ')
    if not port:
        port = default_port
    logging.info(f"Using serial port: {port}") 
    simulator = BscAcSimulator(device_addr, port)  
    simulator.run()