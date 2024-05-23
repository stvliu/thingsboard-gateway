from mu4801_constants import *
from mu4801_data_structs import *
from ydt1363_3_2005_protocol import MU4801Protocol 
from datetime import datetime
import logging
import random
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

class MU4801Simulator:
    def __init__(self, device_addr, port):
        self.protocol = MU4801Protocol(device_addr, port)
        logging.debug(f"Initialized MU4801Protocol with device_addr={device_addr}, port={port}")
        self.device_name = 'MU4801 SIMULATOR'
        self.software_version = '01'
        self.manufacturer = 'ABC Technologies Ltd.'
        
        self.ac_voltage = 220.0
        self.ac_over_voltage = 260.0
        self.ac_under_voltage = 160.0

        self.rect_module_count = 3
        self.rect_output_voltage = 53.5
        self.rect_module_currents = [30.2, 28.5, 29.7]
        self.rect_module_status = [0x00] * 3
        self.rect_module_alarm = [0x00] * 3  
        self.load_current = 65.8
        self.battery_current = 11.2
        self.battery_voltage = 55.1

    # CID2=0x4D/0x4E
    def handle_get_time(self):
        return datetime.now()
    
    def handle_set_time(self, data):        
        # log info, but make no actual change
        logging.info(f"Time set to: {DateTimeStruct.from_bytes(data)}")

    # CID2=0x4F  
    def handle_get_version(self):
        return self.protocol.protocol_version

    # CID2=0x50
    def handle_get_address(self):
        return self.protocol.device_addr

    # CID2=0x51
    def handle_get_info(self):
        return InfoStruct(self.device_name, self.software_version, self.manufacturer)

    # CID1=0x40, CID2=0x41
    def handle_get_ac_analog(self):
        # 模拟交流数据
        ac_freq = 50.2
        ac_current = 10.5
        return AcAnalogStruct(ac_voltage=self.ac_voltage, ac_freq=ac_freq, 
                              ac_current=ac_current)
    
    # CID1=0x40, CID2=0x44
    def handle_get_ac_alarm(self):  
        alarm = AcAlarmStruct()
        if self.ac_voltage > self.ac_over_voltage:
            alarm.over_voltage = 0x02
        elif self.ac_voltage < self.ac_under_voltage:  
            alarm.under_voltage = 0x01
        
        # 随机模拟其他告警
        alarm.spd_alarm = random.randint(0, 1)
        alarm.ph1_under_voltage = random.choice([0x00, 0x01])
        return alarm

    # CID1=0x40, CID2=0x46 
    def handle_get_ac_config(self):
        return AcConfigStruct(
            ac_over_voltage=self.ac_over_voltage, 
            ac_under_voltage=self.ac_under_voltage
        )
    
    # CID1=0x40, CID2=0x48
    def handle_set_ac_config(self, data): 
        config = AcConfigStruct.from_bytes(data)
        self.ac_over_voltage = config.ac_over_voltage
        self.ac_under_voltage = config.ac_under_voltage
        logging.info(f"AC config updated: over_volt={self.ac_over_voltage}, under_volt={self.ac_under_voltage}")

    # CID1=0x41, CID2=0x41 
    def handle_get_rect_analog(self, module_count):
        return RectAnalogStruct(
            output_voltage=self.rect_output_voltage,
            module_count=module_count,
            module_currents=self.rect_module_currents[:module_count]
        )
    
    # CID1=0x41, CID2=0x43
    def handle_get_rect_status(self, module_count): 
        # 模拟整流模块状态,偶尔切换状态
        for i in range(module_count):
            self.rect_module_status[i] = random.choice([0x00, 0x01]) 
        
        return RectStatusStruct(
            module_count=module_count,
            status_list=self.rect_module_status[:module_count]  
        )

    # CID1=0x41, CID2=0x44
    def handle_get_rect_alarm(self, module_count):
        # 模拟整流模块告警
        for i in range(module_count):
            self.rect_module_alarm[i] = random.choice([0x00, 0x01, 0x80, 0x88])

        return RectAlarmStruct(
            module_count=module_count, 
            alarm_list=self.rect_module_alarm[:module_count]
        ) 

    # CID1=0x41, CID2=0x45/0x80   
    def handle_control_rect(self, module_id, control_type):  
        if control_type == 0x20:
            logging.info(f"Rectifier module {module_id} turned on")
        elif control_type == 0x2F:  
            logging.info(f"Rectifier module {module_id} turned off")
        else:
            logging.warning(f"Unsupported control type: {control_type:02X}")

    # CID1=0x42, CID2=0x41
    def handle_get_dc_analog(self): 
        # 模拟负载分路电流
        load_branch_currents = [random.uniform(1, 10) for _ in range(4)]
        return DcAnalogStruct(
            voltage=self.battery_voltage,
            total_current=self.load_current,
            battery_current=self.battery_current, 
            load_branch_currents=load_branch_currents
        ) 
    
    # CID1=0x42, CID2=0x44
    def handle_get_dc_alarm(self):
        dc_alarm = DcAlarmStruct()

        if self.battery_voltage > 57.6:  # 假设57.6为过压告警点
            dc_alarm.over_voltage = 1
        elif self.battery_voltage < 43.2:  # 假设43.2为欠压告警点  
            dc_alarm.under_voltage = 1
        
        # 其他告警随机模拟
        dc_alarm.fuse1_alarm = random.randint(0, 1) 
        dc_alarm.spd_alarm = random.randint(0, 1)
        return dc_alarm

    # CID1=0x42, CID2=0x46
    def handle_get_dc_config(self):
        return DcConfigStruct(
            voltage_upper_limit=57.6,
            voltage_lower_limit=43.2   
        )

    # CID1=0x42, CID2=0x48
    def handle_set_dc_config(self, data):
        dc_config = DcConfigStruct.from_bytes(data) 
        # 实际应用中需要更新配置,此处仅示例
        logging.info(f"DC configuration updated: upper={dc_config.voltage_upper_limit}, lower={dc_config.voltage_lower_limit}")

    # CID1=0x42, CID2=0x92  
    def handle_control_system(self, control_type):
        # 模拟系统控制
        if control_type == 0xE1:
            logging.info("System reset")
        elif control_type == 0xE5:  
            logging.info("Load 1 off")
        elif control_type == 0xE6:
            logging.info("Load 1 on")
        elif control_type == 0xED:  
            logging.info("Battery off")
        elif control_type == 0xEE:
            logging.info("Battery on")  
        else:
            logging.warning(f"Unsupported control type: {control_type:02X}")

    def run(self):
        while True:
            try:
                if not self.protocol.is_connected():
                    logging.info("Connecting to serial port...")
                    if not self.protocol.open():
                        time.sleep(1)
                        continue

                frame = self.protocol.recv_command()
                if frame is None:
                    continue

                logging.info(f"Received command frame: cid1={frame.cid1:02X}, cid2={frame.cid2:02X}, info={frame.info.hex()}")
                response = self.protocol.handle_command(frame.cid1, frame.cid2, frame.info)
                if response is not None:
                    logging.debug(f"Sending response frame: cid1={frame.cid1:02X}, cid2=00, info={response}")
                    self.protocol.send_response(frame.cid1, 0x00, response)
                    logging.debug(f"====================================================")
                else:
                    logging.warning(f"Unsupported command, sending error response: cid1={frame.cid1:02X}, cid2=04")
                    self.protocol.send_response(frame.cid1, 0x04, b'')

            except Exception as e:
                logging.exception(f"Unexpected error occurred: {e}")
                self.protocol.close()
                time.sleep(1)  # wait before attempting to reconnect

if __name__ == '__main__':
    device_addr = 1
    default_port = '/dev/ttyS3'
    port = input(f'请输入串口号(默认为{default_port}): ')
    if not port:
        port = default_port
    logging.info(f"Using serial port: {port}") 
    simulator = MU4801Simulator(device_addr, port)
    simulator.run()