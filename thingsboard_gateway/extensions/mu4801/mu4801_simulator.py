import serial
import struct
import time
import random

# 模拟MU4801设备参数
current_time = time.strftime('%Y%m%d%H%M%S')  # 当前时间
protocol_version = 'V2.1'  # 协议版本号  

address = 1  # 设备地址

# 交流模拟量
ac_voltage_ab = 220.0  # 输入线电压AB  
ac_voltage_bc = 220.0  # 输入线电压BC
ac_voltage_ca = 220.0  # 输入线电压CA
ac_frequency = 50.0  # 输入频率

# 交流告警状态
ac_voltage_ab_state = 0   # 输入线电压AB状态
ac_voltage_bc_state = 0   # 输入线电压BC状态  
ac_voltage_ca_state = 0   # 输入线电压CA状态
ac_spd_alarm = 0  # 交流防雷器断
ac_phase1_state = 0  # 交流第一路输入停电

# 交流配电参数  
ac_voltage_high = 240.0  # 交流输入线电压上限
ac_voltage_low = 200.0   # 交流输入线电压下限

# 整流模块模拟量
rec_voltage = 54.0    # 整流模块输出电压
rec_num = 4  # 监控模块数量
rec_current = [20.0] * rec_num  # 整流模块输出电流
rec_limited_point = [100.0] * rec_num  # 模块限流点
rec_volt = [54.0] * rec_num  # 模块输出电压  
rec_temp = [25.0] * rec_num  # 模块温度
rec_input_volt_ab = [220.0] * rec_num  # 交流输入AB线电压

# 整流模块开关量  
rec_onoff_state = [0] * rec_num  # 开关机状态
rec_limited_state = [0] * rec_num  # 限流状态

# 整流模块告警状态
rec_comm_alarm = [0] * rec_num  # 模块通讯中断
rec_protect_alarm = [0] * rec_num  # 模块保护  
rec_fan_alarm = [0] * rec_num  # 模块风扇故障

# 直流模拟量
dc_voltage = 54.0  # 直流输出电压
dc_load_current = 50.0  # 总负载电流  
bat_group_num = 4  # 电池组数
bat_group_current = [20.0] * bat_group_num  # 电池组电流
dc_branch_num = 4  # 直流分路数
dc_branch_current = [10.0, 12.0, 8.0, 15.0]  # 直流分路电流
bat_total_current = 20.0  # 电池总电流 
bat_group_mid_volt = [25.0] * bat_group_num  # 电池组中点电压
bat_group_cap = [100.0] * bat_group_num  # 电池组剩余容量  
bat_group_temp = [25.0] * bat_group_num  # 电池组温度
env_temp = [26.5, 25.8]  # 机柜内环境温度
env_humidity = [55.0]  # 机柜内环境湿度
dc_load_total_power = 1200.0  # 直流总负载功率
dc_load_total_energy = 12800.0  # 直流总负载电量  
dc_load_power = [200.0, 300.0, 250.0, 450.0]  # 直流负载功率
dc_load_energy = [2100.0, 3200.0, 2500.0, 4000.0]  # 直流负载电量

# 直流告警状态 
dc_volt_state = 0  # 直流电压状态
dc_spd_alarm = 1  # 直流防雷器故障  
ac_in1_state = 0  # 交流第一路输入停电
bat_fuse_alarm = [0] * bat_group_num  # 电池组熔丝断告警 
bat_group_lost_alarm = [0] * bat_group_num  # 电池组丢失告警
blvd_will_alarm = 0  # BLVD即将下电告警
blvd_alarm = 0  # BLVD下电告警
llvd_will_alarm = [0, 0, 0, 0]  # 负载即将下电告警
llvd_alarm = [0, 0, 0, 0]  # 负载下电告警  
bat_temp_alarm = 0  # 电池温度告警
bat_temp_sensor_alarm = [0] * bat_group_num  # 电池温度传感器异常告警
env_temp_alarm = 0  # 环境温度告警
env_temp_sensor_alarm = [0, 0]  # 环境温度传感器异常告警
env_humi_alarm = 0  # 环境湿度告警
env_humi_sensor_alarm = [0]  # 环境湿度传感器异常告警
door_alarm = 0  # 门磁告警
water_alarm = 0  # 水浸告警  
smoke_alarm = 0  # 烟雾告警
switch_in_alarm = 0  # 开关量输入告警

# 直流配电参数
dc_vol_high = 57.6  # 直流电压上限
dc_vol_low = 42.0  # 直流电压下限 
timed_boost_enable = 1  # 定时均充使能
timed_boost_hour = 12  # 定时均充时间  
timed_boost_interval_day = 60  # 定时均充间隔天数
bat_group1_num = 3  # 第1屏电池组数
bat_high_temp = 50.0  # 电池过温告警点
bat_low_temp = -5.0  # 电池欠温告警点
env_high_temp = 45.0  # 环境过温告警点
env_low_temp = 5.0  # 环境欠温告警点  
env_high_humi = 90.0  # 环境过湿告警点
env_low_humi = 20.0  # 环境欠湿告警点
bat_charge_limited = 0.1  # 电池充电限流点
bat_float_volt = 54.0  # 浮充电压
bat_boost_volt = 56.0  # 均充电压  
bat_dropout_volt = 42.0  # 电池下电电压
bat_up_volt = 50.0  # 电池上电电压
llvd_dropout_volt = [43.0, 43.0, 43.0, 43.0]  # 负载下电电压
llvd_up_volt = [50.0, 50.0, 50.0, 50.0]  # 负载上电电压 
bat_size = 100.0  # 每组电池额定容量
bat_test_volt = 46.0  # 电池测试终止电压  
bat_temp_compensate = 72.0  # 电池组温补系数
bat_temp_compensate_base = 25.0  # 电池温补中心点
bat_float_volt_factor = 2.15  # 浮充转均充系数
bat_boost_volt_factor = 2.07  # 均充转浮充系数
llvd_dropout_time = [0, 0, 0, 0]  # 负载下电延时
loadoff_mode = 1  # 负载下电模式 

# 系统状态
system_mode = 0  # 系统模式,0-自动,1-手动

# 告警音使能
buzzer_enable = 0  # 0-使能,1-禁止  

# 节能参数
energy_saving_enable = 1  # 节能使能
energy_saving_min_rect = 1  # 最小工作模块数  
energy_saving_rect_rotate_period = 2  # 模块循环周期(天)
energy_saving_rect_optimal_curr = 25  # 模块最佳效率点(%)
energy_saving_rect_redundant_curr = 40  # 模块冗余电流点(%)  

def calc_crc(data):
    """计算CRC"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc = crc >> 1
    return ((crc & 0x00FF) << 8) | ((crc & 0xFF00) >> 8)

def send_response(ser, address, cid1, cid2, data):
    """发送响应数据"""
    # 构造响应帧
    sof = 0x7E  # 帧起始符  
    length = len(data)  
    frame = struct.pack(f'>BBBH{length}s', address, cid1, cid2, length, data)
    crc = calc_crc(frame)
    frame += struct.pack('>H', crc)  
    frame = struct.pack('>B', sof) + frame + b'\r'
    
    # 发送响应  
    ser.write(frame) 
    print('发送响应:', ' '.join([f'{c:02X}' for c in frame]))
    
def handle_command(ser, address, cid1, cid2, data):  
    """处理监控单元发送的命令"""
    success = True
    
    if cid1 == 0x40 and cid2 == 0x4D:  # 获取当前时间
        response = current_time.encode()
        send_response(ser, address, 0x40, 0x00, response)
        
    elif cid1 == 0x40 and cid2 == 0x4E:  # 设置当前时间
        set_time = data.decode()  
        try:
            time.strptime(set_time, '%Y%m%d%H%M%S')  
            current_time = set_time
            send_response(ser, address, 0x40, 0x00, b'')  
        except:
            success = False
            
    elif cid1 == 0x40 and cid2 == 0x4F:  # 获取协议版本号
        response = protocol_version.encode()
        send_response(ser, address, 0x40, 0x00, response)
        
    elif cid1 == 0x40 and cid2 == 0x50:  # 获取本机地址
        response = struct.pack('B', address) 
        send_response(ser, address, 0x40, 0x00, response)
        
    elif cid1 == 0x40 and cid2 == 0x51:  # 获取厂家信息
        device_name = 'MU4801'  
        software_version = 'V100'
        manufacturer = 'HAYDEN'  
        response = device_name.encode().ljust(10) + software_version.encode() + manufacturer.encode().ljust(20)
        send_response(ser, address, 0x40, 0x00, response)
        
    elif cid1 == 0x41 and cid2 == 0x41:  # 获取交流模拟量(浮点数)  
        ac_voltage_ab += random.uniform(-2, 2)  # 模拟电压微小波动
        ac_voltage_bc += random.uniform(-2, 2)
        ac_voltage_ca += random.uniform(-2, 2)
        ac_frequency += random.uniform(-0.5, 0.5)  # 模拟频率微小波动
        
        response = b'\x00\x01' + struct.pack('>ffff', ac_voltage_ab, ac_voltage_bc, ac_voltage_ca, ac_frequency) 
        response += b'\x1E' + b'\x00\x00\x00\x00' * 30
        send_response(ser, address, 0x41, 0x00, response)

    elif cid1 == 0x41 and cid2 == 0x44:  # 获取交流告警状态
        response = struct.pack('BBBBBBBBBBBBBBBBBBB', 0, 1, ac_voltage_ab_state, ac_voltage_bc_state, ac_voltage_ca_state, 0, ac_spd_alarm, 0, 0, 0, 0, ac_phase1_state, 0, 0, 0, 0, 0, 0, 0)  
        send_response(ser, address, 0x41, 0x00, response)
        
    elif cid1 == 0x40 and cid2 == 0x46:  # 获取交流配电参数(浮点数)      
        response = struct.pack('>ffff', ac_voltage_high, ac_voltage_low, 0, 0) + b'\x00'    
        send_response(ser, address, 0x40, 0x00, response)
        
    elif cid1 == 0x40 and cid2 == 0x48:  # 设置交流配电参数(浮点数)  
        if len(data) == 9:
            cmd = data[0]
            value = struct.unpack('>f', data[1:])[0]
            if cmd == 0x80:
                ac_voltage_high = value
            elif cmd == 0x81:
                ac_voltage_low = value
            else:
                success = False
        else:
            success = False
        send_response(ser, address, 0x40, 0x00, b'')
            
    elif cid1 == 0x41 and cid2 == 0x41:  # 获取整流模块模拟量(浮点数)  
        rec_voltage += random.uniform(-0.1, 0.1)  # 模拟整流电压微小波动
        response = b'\x00' + struct.pack('>fB', rec_voltage, rec_num)
        for i in range(rec_num):
            rec_current[i] += random.uniform(-0.5, 0.5)  # 模拟电流微小波动  
            response += struct.pack('>f', rec_current[i])   
            response += struct.pack('>B', 13)  # 每个模块有13个自定义参数
            response += struct.pack('>f', rec_limited_point[i])
            response += struct.pack('>f', rec_volt[i]) 
            rec_temp[i] += random.uniform(-1, 1)  # 模拟温度微小波动
            response += struct.pack('>f', rec_temp[i])
            response += struct.pack('>f', rec_input_volt_ab[i])
            response += struct.pack('>f', 0) * 9  # 9个预留位
        send_response(ser, address, 0x41, 0x00, response)
        
    elif cid1 == 0x41 and cid2 == 0x43:  # 获取整流模块开关输入状态
        response = b'\x00' + struct.pack('>B', rec_num)
        for i in range(rec_num):
            response += struct.pack('BB', rec_onoff_state[i], rec_limited_state[i]) 
            response += b'\x10' * (1 + 16)  # 每个模块有1个充电状态位和16个预留位
        send_response(ser, address, 0x41, 0x00, response)
        
    elif cid1 == 0x41 and cid2 == 0x44:  # 获取整流模块告警状态
        response = b'\x00' + struct.pack('B', rec_num)
        for i in range(rec_num):
            response += struct.pack('B', 0)  # 模块故障位
            response += struct.pack('>B', 18)  # 18个自定义参数
            response += struct.pack('B', rec_comm_alarm[i]) 
            response += struct.pack('B', rec_protect_alarm[i])
            response += struct.pack('B', rec_fan_alarm[i])
            response += b'\x00' * 15
        send_response(ser, address, 0x41, 0x00, response)
        
    elif cid1 == 0x41 and cid2 == 0x45:  # 遥控整流模块
        if len(data) == 1:
            cmd = data[0]
            if cmd == 0x20:  # 开机
                for i in range(rec_num):
                    rec_onoff_state[i] = 0  
            elif cmd == 0x2F:  # 关机  
                for i in range(rec_num):
                    rec_onoff_state[i] = 1
            else:
                success = False
        else:
            success = False
        send_response(ser, address, 0x41, 0x00, b'')
        
    elif cid1 == 0x41 and cid2 == 0x41:  # 获取直流配电模拟量(浮点数)
        dc_voltage += random.uniform(-0.1, 0.1)  # 模拟直流电压微小波动
        dc_load_current += random.uniform(-1, 1)  # 模拟负载电流微小波动
        bat_total_current += random.uniform(-1, 1)  # 模拟电池总电流微小波动
        for i in range(bat_group_num):
            bat_group_current[i] += random.uniform(-0.5, 0.5)  # 模拟电池组电流微小波动
            bat_group_mid_volt[i] += random.uniform(-0.1, 0.1)  # 模拟电池组中点电压微小波动
            bat_group_cap[i] += random.uniform(-1, 1)  # 模拟电池组容量微小波动
            bat_group_temp[i] += random.uniform(-1, 1)  # 模拟电池组温度微小波动
        for i in range(len(env_temp)):
            env_temp[i] += random.uniform(-1, 1)  # 模拟环境温度微小波动
        for i in range(len(env_humidity)):  
            env_humidity[i] += random.uniform(-2, 2)  # 模拟环境湿度微小波动
        dc_load_total_power += random.uniform(-10, 10)  # 模拟直流总负载功率微小波动
        dc_load_total_energy += dc_load_total_power/3600  # 模拟直流总电能微小增加
        for i in range(dc_branch_num):
            dc_branch_current[i] += random.uniform(-0.5, 0.5)  # 模拟直流分路电流微小波动
            dc_load_power[i] += random.uniform(-5, 5)  # 模拟直流负载功率微小波动 
            dc_load_energy[i] += dc_load_power[i]/3600  # 模拟直流负载电能微小增加
        
        response = struct.pack('>ff', dc_voltage, dc_load_current)
        response += struct.pack('>B', bat_group_num)
        for i in range(bat_group_num):  
            response += struct.pack('>f', bat_group_current[i])
        response += struct.pack('>B', dc_branch_num)
        for i in range(dc_branch_num):
            response += struct.pack('>f', dc_branch_current[i])
        response += struct.pack('>B', 55)  # 55个用户自定义参数
        response += struct.pack('>f', bat_total_current)
        for i in range(bat_group_num):
            response += struct.pack('>f', bat_group_mid_volt[i])
        for i in range(bat_group_num):   
            response += struct.pack('>f', bat_group_cap[i]) 
        for i in range(bat_group_num):
            response += struct.pack('>f', bat_group_temp[i])
        for temp in env_temp:  
            response += struct.pack('>f', temp)
        for humi in env_humidity:
            response += struct.pack('>f', humi)
        response += struct.pack('>f', 0) * 12  # 12个预留位
        response += struct.pack('>ff', dc_load_total_power, dc_load_total_energy)
        for i in range(dc_branch_num):
            response += struct.pack('>f', dc_load_power[i]) 
        for i in range(dc_branch_num):
            response += struct.pack('>f', dc_load_energy[i])
        response += struct.pack('>f', 0) * 2  # 2个预留位
        send_response(ser, address, 0x41, 0x00, response)
        
    elif cid1 == 0x41 and cid2 == 0x44:  # 获取直流告警状态
        response = struct.pack('B', 0) 
        response += struct.pack('B', 1)
        response += struct.pack('B', dc_volt_state)
        response += struct.pack('B', 0)  # 电池熔丝/开关状态,无
        response += struct.pack('B', 151)
        response += struct.pack('B', dc_spd_alarm)
        response += struct.pack('B', 0)  # 直流屏通讯中断,不支持 
        response += struct.pack('B', 1)  # 负载熔丝断(合路)
        response += struct.pack('B', ac_in1_state)
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
        response += struct.pack('B', bat_temp_alarm)
        for alarm in bat_temp_sensor_alarm:
            response += struct.pack('B', alarm)
        response += struct.pack('B', env_temp_alarm)
        for alarm in env_temp_sensor_alarm:  
            response += struct.pack('B', alarm)
        response += struct.pack('B', env_humi_alarm)
        for alarm in env_humi_sensor_alarm:
            response += struct.pack('B', alarm)
        response += struct.pack('B', door_alarm)  
        response += struct.pack('B', water_alarm)
        response += struct.pack('B', smoke_alarm)
        response += struct.pack('B', 0)  # 红外告警,不支持
        for _ in range(6):  # 开关量告警1-6
            response += struct.pack('B', switch_in_alarm)
        response += struct.pack('B', 0) * 72  # 预留告警72个,不支持  
        send_response(ser, address, 0x41, 0x00, response)
        
    elif cid1 == 0x40 and cid2 == 0x46:  # 获取直流配电参数(浮点数)
        response = struct.pack('>ff', dc_vol_high, dc_vol_low)  
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
        send_response(ser, address, 0x40, 0x00, response)
        
    elif cid1 == 0x40 and cid2 == 0x48:  # 设置直流配电参数(浮点数)
        if len(data) == 9:
            cmd = data[0]
            value = struct.unpack('>f', data[1:])[0]
            if cmd == 0x80:
                dc_vol_high = value
            elif cmd == 0x81:
                dc_vol_low = value
            elif cmd == 0xC0:
                timed_boost_enable = int(value)
            elif cmd == 0xC5:
                timed_boost_hour = int(value)
            elif cmd == 0xC6:
                timed_boost_interval_day = int(value)  
            elif cmd == 0xC7:
                bat_group1_num = int(value)
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
            elif cmd == 0xDF:
                llvd_dropout_volt[0] = value  
            elif cmd == 0xE0:
                llvd_up_volt[0] = value
            elif cmd == 0xE1:
                llvd_dropout_volt[1] = value
            elif cmd == 0xE2:
                llvd_up_volt[1] = value
            elif cmd == 0xE3:
                llvd_dropout_volt[2] = value
            elif cmd == 0xE4:  
                llvd_up_volt[2] = value
            elif cmd == 0xE5:
                llvd_dropout_volt[3] = value
            elif cmd == 0xE6:
                llvd_up_volt[3] = value
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
            elif cmd == 0xEE:
                llvd_dropout_time[0] = value
            elif cmd == 0xEF:
                llvd_dropout_time[1] = value
            elif cmd == 0xF0:
                llvd_dropout_time[2] = value
            elif cmd == 0xF1:  
                llvd_dropout_time[3] = value
            elif cmd == 0xF2:
                loadoff_mode = int(value)
            else:
                success = False  
        else:
            success = False
        send_response(ser, address, 0x40, 0x00, b'')
        
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
        send_response(ser, address, 0x41, 0x00, b'')
        
    elif cid1 == 0x41 and cid2 == 0x81:  # 读取系统控制状态
        response = struct.pack('B', 0xE0 if system_mode == 0 else 0xE1)
        send_response(ser, address, 0x41, 0x00, response)
        
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
        send_response(ser, address, 0x41, 0x00, b'')
        
    elif cid1 == 0x41 and cid2 == 0x90:  # 读取节能参数  
        response = struct.pack('B', energy_saving_enable)
        response += struct.pack('B', energy_saving_min_rect)
        response += struct.pack('>H', energy_saving_rect_rotate_period)
        response += struct.pack('B', energy_saving_rect_optimal_curr)
        response += struct.pack('B', energy_saving_rect_redundant_curr)
        response += b'\x00' * 18  # 18个预留位
        send_response(ser, address, 0x41, 0x00, response)
        
    elif cid1 == 0x41 and cid2 == 0x91:  # 设置节能参数
        if len(data) == 6:
            cmd = data[0]
            value = data[1]
            if cmd == 0xE1:
                energy_saving_enable = value
            elif cmd == 0xE2:
                energy_saving_min_rect = value
            elif cmd == 0xE3:
                energy_saving_rect_rotate_period = struct.unpack('>H', data[1:3])[0]
            elif cmd == 0xE4:
                energy_saving_rect_optimal_curr = value
            elif cmd == 0xE5:  
                energy_saving_rect_redundant_curr = value
            else:
                success = False
        else:
            success = False
        send_response(ser, address, 0x41, 0x00, b'')
        
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
        send_response(ser, address, 0x41, 0x00, b'')

    else:
        success = False
        send_response(ser, address, 0x41, 0x80, b'')  # 不支持的命令
    
    if not success:  # 如果处理失败,返回通用错误码
        send_response(ser, address, cid1, 0xAA, b'')
        
def main():
    # 获取串口配置
    port = input('请输入串口号(如COM3): ')
    baudrate = 9600
    bytesize = 8
    parity = 'N'
    stopbits = 1

    # 打开串口
    ser = serial.Serial(port, baudrate, bytesize, parity, stopbits)
    print(f'MU4801模拟器已启动,使用串口: {port}')

    while True:
        # 接收数据
        data = ser.read_until(b'\r')
        
        if len(data) > 0:
            # 解析报文
            if data[0] == 0x7E and data[-1] == 0x0D:
                try:
                    frame_data = data[1:-3]
                    frame_crc = struct.unpack('>H', data[-3:-1])[0]
                    calc_crc_value = calc_crc(frame_data)
                    
                    if frame_crc == calc_crc_value:
                        frame_adr = frame_data[0]
                        frame_cid1 = frame_data[1]
                        frame_cid2 = frame_data[2]
                        frame_len = struct.unpack('>H', frame_data[3:5])[0]
                        frame_info = frame_data[5:5+frame_len]
                        print('接收到报文: ', ' '.join([f'{c:02X}' for c in data]))
                        
                        # 处理报文
                        handle_command(ser, frame_adr, frame_cid1, frame_cid2, frame_info)
                    else:
                        print('CRC校验失败')
                except Exception as e:
                    print(f'解析报文时出错: {e}')
            else:
                print('报文格式错误')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('程序已终止')