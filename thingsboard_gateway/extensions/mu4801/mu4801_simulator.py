import serial
import struct
import random
import time
import logging

# 设置日志级别和格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 定义帧格式常量
FRAME_HEADER = 0x7E
FRAME_VERSION = 0x20
FRAME_FOOTER = 0x0D

# 定义错误码常量
ERR_GENERAL = 0xAA
ERR_UNSUPPORTED_CMD = 0x80

# MU4801模拟器参数
device_addr = 0x01
current_time = '20230418092503'
protocol_version = 'V2.1'
device_name = 'MU4801'
software_version = 'V100'  
manufacturer = 'XXX'

# 交流参数 
ac_volt = [220.0, 220.0, 220.0]  
ac_freq = 50.0
ac_spd_alarm = 0
ac_switch_alarm = 0

# 交流告警参数
ac_volt_high = 240.0  
ac_volt_low = 200.0

# 整流模块参数
rec_volt = 54.0
rec_num = 1
rec_curr = [50]  
rec_limit_point = [105]
rec_temperature = [25]  
rec_comm_alarm = [0] * rec_num
rec_protect_alarm = [0] * rec_num
rec_fan_alarm = [0] * rec_num  

# 直流参数
dc_volt = 54.0
dc_load_current = 100.0
bat_group_num = 4
bat_current = [20] * bat_group_num  
dc_branch_num = 4  
dc_branch_current = [10, 15, 12, 8]
bat_total_current = 20
bat_mid_volt = [28] * bat_group_num
bat_cap = [100]
bat_temp = [25]  
env_temp = [25, 25]
env_humi = [50]  
dc_load_power = [120, 150, 80, 100]
dc_load_energy = [1.2, 1.5, 0.8, 1.0]

# 直流告警参数
dc_volt_high = 57.6
dc_volt_low = 45.0  
dc_spd_alarm =0
ac_in1_alarm = 0
bat_fuse_alarm = [0] * bat_group_num
bat_group_lost_alarm = [0] * bat_group_num
blvd_will_alarm = 0
blvd_alarm = 0
llvd_will_alarm = [0] * 4
llvd_alarm = [0] * 4
bat_high_temp = 50.0  
bat_low_temp = -5.0
env_high_temp = 45.0
env_low_temp = 5.0
env_high_humi = 90.0  
env_low_humi = 20.0

# 直流配电参数
timed_boost_enable = 1
timed_boost_hour = 12
timed_boost_interval_day = 60  
bat_group1_num = 4
bat_charge_limited = 0.1
bat_float_volt = 54.0
bat_boost_volt = 56.0
bat_dropout_volt = 42.0
bat_up_volt = 50.0
llvd_dropout_volt = [43.0, 43.0, 43.0, 43.0]
llvd_up_volt = [50.0, 50.0, 50.0, 50.0]
bat_size = 100
bat_test_volt = 46.0
bat_temp_compensate = 72.0
bat_temp_compensate_base = 25.0
bat_float_volt_factor = 2.15  
bat_boost_volt_factor = 2.07
llvd_dropout_time = [0, 0, 0, 0]
loadoff_mode = 1

# 系统状态
system_mode = 0  # 0-自动, 1-手动

# 告警音使能 
buzzer_enable = 0  # 0-使能, 1-禁止

# 节能参数  
energy_saving_enable = 1
energy_saving_min_rect = 1
energy_saving_rotate_period = 2
energy_saving_optimal_curr = 25  
energy_saving_redundant_curr = 40

def send_response(ser, addr, resp_type, data):
    """发送响应数据"""
    # 构造响应帧
    length = len(data) + 1  # 信息内容长度需要包括响应类型字节
    frame = struct.pack('>BBBBHB', FRAME_HEADER, FRAME_VERSION, addr, resp_type, length, resp_type) + data + struct.pack('B', FRAME_FOOTER)
    
    # 发送响应
    ser.write(frame)
    logging.info('发送响应: %s', ' '.join([f'{c:02X}' for c in frame]))
   
def handle_command(ser, addr, cid1, cid2, data):
    """处理监控单元发送的命令"""
    success = True
    
    if cid1 == 0x40 and cid2 == 0x4D:  # 获取当前时间
        response = current_time.encode()
        send_response(ser, addr, 0x40, response)
        
    elif cid1 == 0x40 and cid2 == 0x4E:  # 设置当前时间
        set_time = data.decode()
        try:
            time.strptime(set_time, '%Y%m%d%H%M%S')
            current_time = set_time
            send_response(ser, addr, 0x40, b'')
        except:
            success = False  
            
    elif cid1 == 0x40 and cid2 == 0x4F:  # 获取协议版本号
        response = protocol_version.encode()
        send_response(ser, addr, 0x40, response)
        
    elif cid1 == 0x40 and cid2 == 0x50:  # 获取本机地址
        response = struct.pack('B', device_addr)
        send_response(ser, addr, 0x40, response)
        
    elif cid1 == 0x40 and cid2 == 0x51:  # 获取厂家信息
        response = device_name.encode().ljust(10) + software_version.encode() + manufacturer.encode().ljust(20)
        send_response(ser, addr, 0x40, response)
        
    elif cid1 == 0x41 and cid2 == 0x41:  # 获取交流/整流/直流模拟量(浮点数)
        if data[0] == 0x00:  # 交流模拟量
            for i in range(3):
                ac_volt[i] += random.uniform(-2, 2)  # 模拟电压微小波动
            ac_freq += random.uniform(-0.5, 0.5)  # 模拟频率微小波动
            
            response = b'\x00\x01' + struct.pack('>ffff', ac_volt[0], ac_volt[1], ac_volt[2], ac_freq)
            response += b'\x1E' + b'\x00\x00\x00\x00' * 30
            send_response(ser, addr, 0x41, response)
            
        elif data[1] == rec_num:  # 整流模块模拟量  
            rec_volt += random.uniform(-0.1, 0.1)  # 模拟整流电压微小波动
            response = b'\x00' + struct.pack('>fB', rec_volt, rec_num)
            for i in range(rec_num):
                rec_curr[i] += random.uniform(-0.5, 0.5)  # 模拟电流微小波动
                response += struct.pack('>f', rec_curr[i]) 
                response += struct.pack('>B', 13)  # 每个模块有13个自定义参数
                response += struct.pack('>f', rec_limit_point[i])
                response += struct.pack('>f', rec_volt)
                rec_temperature[i] += random.uniform(-1, 1)  # 模拟温度微小波动  
                response += struct.pack('>f', rec_temperature[i])
                response += struct.pack('>f', ac_volt[0]) 
                response += struct.pack('>f', 0) * 9  # 9个预留位
            send_response(ser, addr, 0x41, response)
            
        else:  # 直流模拟量
            dc_volt += random.uniform(-0.1, 0.1)  # 模拟直流电压微小波动
            dc_load_current += random.uniform(-1, 1)  # 模拟负载电流微小波动
            bat_total_current += random.uniform(-1, 1)  # 模拟电池总电流微小波动  
            for i in range(bat_group_num):
                bat_current[i] += random.uniform(-0.5, 0.5)  # 模拟电池组电流微小波动
                bat_mid_volt[i] += random.uniform(-0.1, 0.1)  # 模拟电池组中点电压微小波动
            bat_cap[0] += random.uniform(-1, 1)  # 模拟电池组容量微小波动  
            bat_temp[0] += random.uniform(-1, 1)  # 模拟电池组温度微小波动
            for i in range(2):  
                env_temp[i] += random.uniform(-1, 1)  # 模拟环境温度微小波动
            env_humi[0] += random.uniform(-2, 2)  # 模拟环境湿度微小波动
            dc_load_total_power = sum(dc_load_power)  
            dc_load_total_power += random.uniform(-10, 10)  # 模拟直流总负载功率微小波动
            dc_load_total_energy = sum(dc_load_energy)
            dc_load_total_energy += dc_load_total_power/3600  # 模拟直流总电能微小增加
            for i in range(dc_branch_num):
                dc_branch_current[i] += random.uniform(-0.5, 0.5)  # 模拟直流分路电流微小波动
                dc_load_power[i] += random.uniform(-5, 5)  # 模拟直流负载功率微小波动
                dc_load_energy[i] += dc_load_power[i]/3600  # 模拟直流负载电能微小增加
            
            response = struct.pack('>ff', dc_volt, dc_load_current) 
            response += struct.pack('>B', bat_group_num)
            for i in range(bat_group_num):
                response += struct.pack('>f', bat_current[i])  
            response += struct.pack('>B', dc_branch_num)
            for i in range(dc_branch_num):
                response += struct.pack('>f', dc_branch_current[i])
            response += struct.pack('>B', 55)  # 55个用户自定义参数
            response += struct.pack('>f', bat_total_current)
            for i in range(4):
                response += struct.pack('>f', bat_mid_volt[i])
            response += struct.pack('>f', bat_cap[0])
            response += struct.pack('>f', bat_temp[0])
            for i in range(2):
                response += struct.pack('>f', env_temp[i])
            response += struct.pack('>f', env_humi[0])
            response += struct.pack('>f', 0) * 12  # 12个预留位
            response += struct.pack('>ff', dc_load_total_power, dc_load_total_energy)
            for i in range(dc_branch_num):
                response += struct.pack('>f', dc_load_power[i])
            for i in range(dc_branch_num):
                response += struct.pack('>f', dc_load_energy[i])
            response += struct.pack('>f', 0) * 2  # 2个预留位
            send_response(ser, addr, 0x41, response)
        
    elif cid1 == 0x41 and cid2 == 0x43:  # 获取整流模块开关输入状态
        response = b'\x00' + struct.pack('>B', rec_num)
        for i in range(rec_num):
            onoff_state = 0 if random.random() < 0.95 else 1  # 模拟开关机状态
            limit_state = 0 if random.random() < 0.9 else 1  # 模拟限流状态

            response += struct.pack('BB', onoff_state, limit_state)
            response += b'\x00' * (1 + 16)  # 1个充电状态位和16个预留位  
        send_response(ser, addr, 0x41, response)
        
    elif cid1 == 0x41 and cid2 == 0x44:  # 获取交流/整流/直流告警状态
        if len(data) == 1:  # 交流告警状态
            ac_volt_state = [0] * 3
            for i in range(3):
                if ac_volt[i] < ac_volt_low:
                    ac_volt_state[i] = 1  # 欠压
                elif ac_volt[i] > ac_volt_high:
                    ac_volt_state[i] = 2  # 过压
                    
            response = struct.pack('BBBBBBBBBBBBBBBBBBB', 0, 1, ac_volt_state[0], ac_volt_state[1], ac_volt_state[2], 0, ac_spd_alarm, 0, 0, 0, 0, ac_switch_alarm, 0, 0, 0, 0, 0, 0, 0)
            send_response(ser, addr, 0x41, response)
            
        elif data[1] == rec_num:  # 整流模块告警状态  
            response = b'\x00' + struct.pack('B', rec_num)
            for i in range(rec_num):
                module_fault = 0 if random.random() < 0.99 else 1  # 模拟模块故障  
                response += struct.pack('B', module_fault)
                response += struct.pack('>B', 18)  # 18个自定义参数
                response += struct.pack('B', rec_comm_alarm[i])
                response += struct.pack('B', rec_protect_alarm[i]) 
                response += struct.pack('B', rec_fan_alarm[i])
                response += b'\x00' * 15 
            send_response(ser, addr, 0x41, response)
            
        else:  # 直流告警状态
            dc_volt_state = 0
            if dc_volt < dc_volt_low:
                dc_volt_state = 1  # 欠压
            elif dc_volt > dc_volt_high:
                dc_volt_state = 2  # 过压
                
            response = struct.pack('B', 0)
            response += struct.pack('B', 1) 
            response += struct.pack('B', dc_volt_state)
            response += struct.pack('B', 0)  # 电池熔丝/开关状态,无
            response += struct.pack('B', 151)
            response += struct.pack('B', dc_spd_alarm)
            response += struct.pack('B', 0)  # 直流屏通讯中断,不支持
            response += struct.pack('B', 1)  # 负载熔丝断(合路)  
            response += struct.pack('B', ac_in1_alarm)
            for alarm in bat_fuse_alarm:
                response += struct.pack('B', alarm) 
            response += struct.pack('B', 0) * 6  # 电池组充电过流告警,不支持
            for alarm in bat_group_lost_alarm:
                response += struct.pack('B', alarm)
            response += struct.pack('B', blvd_will_alarm)
            response += struct.pack('B', blvd_alarm)  
            for alarm in llvd_will_alarm:
                response += struct.pack('B', alarm)
            for alarm in llvd_alarm:  
                response += struct.pack('B', alarm)
            response += struct.pack('B', 0) * 11  # 预留告警11个
            bat_temp_state = 0
            if bat_temp[0] > bat_high_temp:
                bat_temp_state = 1  # 过温  
            elif bat_temp[0] < bat_low_temp:
                bat_temp_state = 2  # 欠温
            response += struct.pack('B', bat_temp_state)
            bat_temp_sensor_state = 0 if random.random() < 0.99 else 1 if random.random() < 0.5 else 2  # 模拟电池温度传感器状态
            response += struct.pack('B', bat_temp_sensor_state)
            env_temp_state = 0
            if env_temp[0] > env_high_temp:
                env_temp_state = 1  # 过温
            elif env_temp[0] < env_low_temp:
                env_temp_state = 2  # 欠温
            response += struct.pack('B', env_temp_state)
            for i in range(2):
                env_temp_sensor_state = 0 if random.random() < 0.99 else 1 if random.random() < 0.5 else 2  # 模拟环境温度传感器状态
                response += struct.pack('B', env_temp_sensor_state)
            env_humi_state = 0
            if env_humi[0] > env_high_humi:
                env_humi_state = 1  # 过湿
            elif env_humi[0] < env_low_humi:
                env_humi_state = 2  # 欠湿
            response += struct.pack('B', env_humi_state)
            env_humi_sensor_state = 0 if random.random() < 0.99 else 1 if random.random() < 0.5 else 2  # 模拟环境湿度传感器状态
            response += struct.pack('B', env_humi_sensor_state)
            door_alarm = 0 if random.random() < 0.95 else 1  # 模拟门磁告警
            response += struct.pack('B', door_alarm)
            water_alarm = 0 if random.random() < 0.95 else 1  # 模拟水浸告警
            response += struct.pack('B', water_alarm)
            smoke_alarm = 0 if random.random() < 0.95 else 1  # 模拟烟雾告警
            response += struct.pack('B', smoke_alarm)
            for i in range(6):
                switch_in_alarm = 0 if random.random() < 0.95 else 1  # 模拟开关量输入告警
                response += struct.pack('B', switch_in_alarm)
            response += struct.pack('B', 0) * 72  # 预留告警72个,不支持
            send_response(ser, addr, 0x41, response)
        
    elif cid1 == 0x40 and cid2 == 0x46:  # 获取交流/直流配电参数(浮点数)
        if len(data) == 1:  # 交流配电参数
            response = struct.pack('>ff', ac_volt_high, ac_volt_low)
            response += struct.pack('>ff', 0, 0)  # 交流输出电流上限和频率上下限,不支持
            response += b'\x00'  # 用户自定义数量,固定为0
            send_response(ser, addr, 0x40, response)
        else:  # 直流配电参数
            response = struct.pack('>ff', dc_volt_high, dc_volt_low)
            response += struct.pack('B', 67)  # 67个用户自定义参数
            response += struct.pack('B', timed_boost_enable)
            response += struct.pack('B', 0)  # 自动均充使能,不支持
            response += struct.pack('B', 0)  # 定时测试使能,不支持
            response += struct.pack('BB', 0, 0)  # 定时测试间隔,不支持
            response += struct.pack('BB', 0, 0)  # 电池测试时间,不支持
            response += struct.pack('B', timed_boost_hour)
            response += struct.pack('>H', timed_boost_interval_day)
            response += struct.pack('B', bat_group1_num) + b'\x00' * 9  # 10组电池,只支持第1组
            response += struct.pack('>f', 0) * 4  # 电池组过/欠压告警点,不支持
            response += struct.pack('>ffff', bat_high_temp, bat_low_temp, env_high_temp, env_low_temp)
            response += struct.pack('>ff', env_high_humi, env_low_humi)
            response += struct.pack('>f', bat_charge_limited)
            response += struct.pack('>fff', bat_float_volt, bat_boost_volt, bat_dropout_volt)
            response += struct.pack('>f', bat_up_volt)
            for volt in llvd_dropout_volt:
                response += struct.pack('>f', volt)
            for volt in llvd_up_volt:
                response += struct.pack('>f', volt)
            response += struct.pack('>f', bat_size)
            response += struct.pack('>f', bat_test_volt)
            response += struct.pack('>f', 0)  # 电池测试终止容量,不支持
            response += struct.pack('>ff', bat_temp_compensate, bat_temp_compensate_base)
            response += struct.pack('>ff', bat_float_volt_factor, bat_boost_volt_factor)
            for t in llvd_dropout_time:
                response += struct.pack('>f', t)
            response += struct.pack('B', loadoff_mode)
            response += b'\x00' * 55  # 55个预留位,不支持
            send_response(ser, addr, 0x40, response)
    
    elif cid1 == 0x40 and cid2 == 0x48:  # 设置交流/直流配电参数(浮点数)
        if len(data) == 9:
            cmd = data[0]
            value = struct.unpack('>f', data[1:])[0]
            if cmd == 0x80:
                ac_volt_high = value
            elif cmd == 0x81:
                ac_volt_low = value
            else:
                success = False
            send_response(ser, addr, 0x40, b'')
        else:  # 直流配电参数
            if len(data) == 5:
                cmd = data[0]
                value = data[1]
                if cmd == 0xC0:
                    timed_boost_enable = value
                elif cmd == 0xC5:
                    timed_boost_hour = value
                elif cmd == 0xC7:
                    bat_group1_num = value
                elif cmd == 0xF2:
                    loadoff_mode = value
                else:
                    success = False
            elif len(data) == 6:
                cmd = data[0]
                value = struct.unpack('>H', data[1:3])[0]
                if cmd == 0xC6:
                    timed_boost_interval_day = value
                else:
                    success = False
            elif len(data) == 9:
                cmd = data[0]
                value = struct.unpack('>f', data[1:])[0]
                if cmd == 0x80:
                    dc_volt_high = value
                elif cmd == 0x81:
                    dc_volt_low = value
                elif cmd == 0xD4:
                    bat_high_temp = value
                elif cmd == 0xD5:
                    bat_low_temp = value
                elif cmd == 0xD6:
                    env_high_temp = value
                elif cmd == 0xD7:
                    env_low_temp = value
                elif cmd == 0xD8:
                    env_high_humi = value
                elif cmd == 0xD9:
                    env_low_humi = value
                elif cmd == 0xDA:
                    bat_charge_limited = value
                elif cmd == 0xDB:
                    bat_float_volt = value
                elif cmd == 0xDC:
                    bat_boost_volt = value
                elif cmd == 0xDD:
                    bat_dropout_volt = value
                elif cmd == 0xDE:
                    bat_up_volt = value
                elif cmd >= 0xDF and cmd <= 0xE6:
                    idx = cmd - 0xDF
                    if idx % 2 == 0:
                        llvd_dropout_volt[idx // 2] = value
                    else:
                        llvd_up_volt[idx // 2] = value
                elif cmd == 0xE7:
                    bat_size = value
                elif cmd == 0xE8:
                    bat_test_volt = value
                elif cmd == 0xEA:
                    bat_temp_compensate = value
                elif cmd == 0xEB:
                    bat_temp_compensate_base = value
                elif cmd == 0xEC:
                    bat_float_volt_factor = value
                elif cmd == 0xED:
                    bat_boost_volt_factor = value
                elif cmd >= 0xEE and cmd <= 0xF1:
                    idx = cmd - 0xEE
                    llvd_dropout_time[idx] = value
                else:
                    success = False
            else:
                success = False
            send_response(ser, addr, 0x40, b'')
                
    elif cid1 == 0x41 and cid2 == 0x45:  # 遥控整流模块
        if len(data) == 1:
            cmd = data[0]
            if cmd == 0x20:  # 开机
                rec_onoff_state = [0] * rec_num
            elif cmd == 0x2F:  # 关机
                rec_onoff_state = [1] * rec_num
            else:
                success = False
        else:
            success = False
        send_response(ser, addr, 0x41, b'')
        
    elif cid1 == 0x41 and cid2 == 0x80:  # 修改系统控制状态
        if len(data) == 1:
            cmd = data[0]
            if cmd == 0xE0:
                system_mode = 0  # 自动
            elif cmd == 0xE1:
                system_mode = 1  # 手动
            else:
                success = False
        else:
            success = False
        send_response(ser, addr, 0x41, b'')
        
    elif cid1 == 0x41 and cid2 == 0x81:  # 读取系统控制状态
        response = struct.pack('B', 0xE0 if system_mode == 0 else 0xE1)
        send_response(ser, addr, 0x41, response)
        
    elif cid1 == 0x41 and cid2 == 0x84:  # 后台告警音使能控制
        if len(data) == 1:
            cmd = data[0]
            if cmd == 0xE1:
                buzzer_enable = 1  # 禁止
            elif cmd == 0xE0:
                buzzer_enable = 0  # 使能
            else:
                success = False
        else:
            success = False
        send_response(ser, addr, 0x41, b'')
        
    elif cid1 == 0x41 and cid2 == 0x90:  # 读取节能参数
        response = struct.pack('B', energy_saving_enable)
        response += struct.pack('B', energy_saving_min_rect)
        response += struct.pack('>H', energy_saving_rotate_period)
        response += struct.pack('B', energy_saving_optimal_curr)
        response += struct.pack('B', energy_saving_redundant_curr)
        response += b'\x00' * 18  # 18个预留位
        send_response(ser, addr, 0x41, response)
        
    elif cid1 == 0x41 and cid2 == 0x91:  # 设置节能参数
        if len(data) == 6:
            cmd = data[0]
            value = data[1]
            if cmd == 0xE1:
                energy_saving_enable = value
            elif cmd == 0xE2:
                energy_saving_min_rect = value
            elif cmd == 0xE4:
                energy_saving_optimal_curr = value
            elif cmd == 0xE5:
                energy_saving_redundant_curr = value
            else:
                success = False
        elif len(data) == 7:
            cmd = data[0]
            value = struct.unpack('>H', data[1:3])[0]
            if cmd == 0xE3:
                energy_saving_rotate_period = value
            else:
                success = False
        else:
            success = False
        send_response(ser, addr, 0x41, b'')
        
    elif cid1 == 0x41 and cid2 == 0x92:  # 系统控制
        if len(data) == 2:
            cmd = data[0]
            value = data[1]
            if cmd == 0xE1:  # 系统复位
                print('系统复位')
            elif cmd == 0xE5:  # 负载1下电
                llvd_alarm[0] = 1
            elif cmd == 0xE6:  # 负载1上电
                llvd_alarm[0] = 0
            elif cmd == 0xE7:  # 负载2下电
                llvd_alarm[1] = 1
            elif cmd == 0xE8:  # 负载2上电
                llvd_alarm[1] = 0
            elif cmd == 0xE9:  # 负载3下电
                llvd_alarm[2] = 1
            elif cmd == 0xEA:  # 负载3上电
                llvd_alarm[2] = 0
            elif cmd == 0xEB:  # 负载4下电
                llvd_alarm[3] = 1
            elif cmd == 0xEC:  # 负载4上电
                llvd_alarm[3] = 0
            elif cmd == 0xED:  # 电池下电
                blvd_alarm = 1
            elif cmd == 0xEE:  # 电池上电
                blvd_alarm = 0
            else:
                success = False
        else:
            success = False
        send_response(ser, addr, 0x41, b'')

    else:
        success = False
        logging.warning('不支持的命令: CID1=%02XH, CID2=%02XH', cid1, cid2)
        send_response(ser, addr, 0x41, struct.pack('B', ERR_UNSUPPORTED_CMD))
    
    if not success:  # 如果处理失败,返回通用错误码
        send_response(ser, addr, cid1, struct.pack('B', ERR_GENERAL))
        
def main():
    # 获取串口配置
    port = input('请输入串口号(如COM3): ')
    baudrate = 9600
    bytesize = 8
    parity = 'N'
    stopbits = 1

    # 打开串口
    ser = serial.Serial(port, baudrate, bytesize, parity, stopbits)
    logging.info('MU4801模拟器已启动,使用串口: %s', port)

    while True:
        # 接收数据
        header = ser.read(5)  # 读取帧头部分(帧头1字节 + 帧版本1字节 + 设备地址1字节 + 命令类型1字节 + 数据长度2字节)

        if len(header) == 5:
            frame_len = struct.unpack('>H', header[3:5])[0]  # 解析数据长度
            data = ser.read(frame_len + 1)  # 读取数据部分和帧尾

            if len(data) == frame_len + 1 and data[-1] == FRAME_FOOTER:
                try:
                    frame_adr = header[2]
                    frame_cid1 = header[0]
                    frame_cid2 = header[1]
                    frame_info = data[:-1]
                    logging.info('接收到报文: %s', ' '.join([f'{c:02X}' for c in header+data]))

                    # 处理报文
                    handle_command(ser, frame_adr, frame_cid1, frame_cid2, frame_info)
                except Exception as e:
                    logging.exception('解析报文时出错: %s', e)
            else:
                logging.error('报文格式错误')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info('程序已终止')