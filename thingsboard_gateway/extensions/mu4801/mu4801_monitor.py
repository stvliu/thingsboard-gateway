import serial
import struct
import time
import logging

# 设置日志级别和格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 定义帧格式常量
FRAME_HEADER = 0x7E
FRAME_VERSION = 0x20
FRAME_FOOTER = 0x0D

# 定义命令类型常量
CMD_READ_TIME = 0x4D
CMD_SET_TIME = 0x4E
CMD_READ_VERSION = 0x4F
CMD_READ_ADDR = 0x50
CMD_READ_MANUFACTURER = 0x51
CMD_READ_AC_ANALOG = 0x41
CMD_READ_AC_ALARM = 0x44
CMD_READ_AC_PARAM = 0x46
CMD_SET_AC_PARAM = 0x48
CMD_READ_RECT_ANALOG = 0x41
CMD_READ_RECT_SWITCH = 0x43
CMD_READ_RECT_ALARM = 0x44
CMD_CTRL_RECT = 0x45
CMD_READ_DC_ANALOG = 0x41
CMD_READ_DC_ALARM = 0x44
CMD_READ_DC_PARAM = 0x46
CMD_SET_DC_PARAM = 0x48
CMD_SET_SYS_MODE = 0x80
CMD_READ_SYS_MODE = 0x81
CMD_CTRL_BUZZER = 0x84
CMD_READ_ENERGY_PARAM = 0x90
CMD_SET_ENERGY_PARAM = 0x91
CMD_SYS_CTRL = 0x92

# 定义错误码常量
ERR_GENERAL = 0xAA
ERR_UNSUPPORTED_CMD = 0x80

def send_command(ser, addr, cmd_type, data=b''):
    """发送命令并获取响应数据"""
    # 构造命令帧
    #length = len(data) + 1  # 信息内容长度需要包括命令类型字节
    #frame = struct.pack('>BBBBBB', FRAME_HEADER, FRAME_VERSION, addr, cmd_type, length&0xFF, length>>8) + struct.pack('B', cmd_type) + data + struct.pack('B', FRAME_FOOTER)
    data = struct.pack('B', cmd_type) + data  # 将命令类型作为data的一部分
    length = len(data)  # 数据长度
    frame = struct.pack('>BBBBH', FRAME_HEADER, FRAME_VERSION, addr, cmd_type, length) + data + struct.pack('B', FRAME_FOOTER)
    # 发送命令
    ser.write(frame)
    logging.info('发送命令: %s', ' '.join([f'{c:02X}' for c in frame]))
    
    # 接收响应
    response = ser.read_until(struct.pack('B', FRAME_FOOTER))
    if len(response) > 0:
        if response[0] == FRAME_HEADER and response[-1] == FRAME_FOOTER:
            logging.info('接收响应: %s', ' '.join([f'{c:02X}' for c in response]))
            # 校验帧长度
            resp_len = struct.unpack('>H', response[4:6])[0]
            if resp_len + 6 == len(response):
                return response[1:-1] # 去掉帧头和帧尾
            else:
                logging.error('响应帧长度错误')
        else:
            logging.error('响应帧格式错误')
    else:
        logging.warning('未收到响应')
    
    return None

def parse_response(data):
    """解析响应数据"""
    if len(data) >= 5:
        addr, cid1, cid2 = struct.unpack('>BBB', data[:3])
        
        if cid1 == 0x41 and cid2 == ERR_GENERAL:  # 通用错误码
            logging.error('设备返回错误')
        elif cid1 == 0x41 and cid2 == ERR_UNSUPPORTED_CMD:  # 不支持的命令
            logging.error('设备不支持该命令')
        else:
            length = struct.unpack('>H', data[3:5])[0]
            info = data[5:5+length]
            
            if cid1 == 0x40 and cid2 == 0x00:  # 通用应答
                if length == 0:
                    logging.info('操作成功')    
                else:
                    logging.info('操作失败')
            
            elif cid1 == 0x40 and cid2 == CMD_READ_TIME:  # 获取当前时间
                current_time = info.decode()
                logging.info('当前时间: %s', current_time)
            
            elif cid1 == 0x40 and cid2 == CMD_READ_VERSION:  # 获取协议版本号
                protocol_ver = info.decode()
                logging.info('协议版本号: %s', protocol_ver)
            
            elif cid1 == 0x40 and cid2 == CMD_READ_ADDR:  # 获取本机地址
                device_addr = struct.unpack('B', info)[0]
                logging.info('设备地址: %d', device_addr)
            
            elif cid1 == 0x40 and cid2 == CMD_READ_MANUFACTURER:  # 获取厂家信息
                device_name = info[:10].decode().strip()
                software_ver = info[10:12].decode()
                manufacturer = info[12:].decode().strip()
                logging.info('设备名称: %s', device_name)
                logging.info('软件版本: %s', software_ver)
                logging.info('厂商名称: %s', manufacturer)
            
            elif cid1 == 0x41 and cid2 == CMD_READ_AC_ANALOG: # 获取交流模拟量
                if info[0] == 0x00:  # 交流模拟量
                    ac_volt_ab, ac_volt_bc, ac_volt_ca, ac_freq = struct.unpack('>ffff', info[3:19])
                    logging.info('交流输入线电压 AB: %.1f V', ac_volt_ab) 
                    logging.info('交流输入线电压 BC: %.1f V', ac_volt_bc)
                    logging.info('交流输入线电压 CA: %.1f V', ac_volt_ca)
                    logging.info('交流输入频率: %.2f Hz', ac_freq)
                    
            elif cid1 == 0x41 and cid2 == CMD_READ_AC_ALARM:  # 获取交流告警状态
                ac_volt_state = ['正常', '欠压', '过压']
                logging.info('交流告警状态:')
                logging.info('  交流输入线电压AB状态: %s', ac_volt_state[info[2]])
                logging.info('  交流输入线电压BC状态: %s', ac_volt_state[info[3]])
                logging.info('  交流输入线电压CA状态: %s', ac_volt_state[info[4]])
                logging.info('  交流防雷器状态: %s', '正常' if info[6] == 0 else '断开')  
                logging.info('  交流第一路输入状态: %s', '正常' if info[11] == 0 else '停电')
                
            elif cid1 == 0x40 and cid2 == CMD_READ_AC_PARAM:  # 获取交流配电参数
                ac_volt_high, ac_volt_low = struct.unpack('>ff', info[:8])
                logging.info('交流输入线电压上限: %.1f V', ac_volt_high)
                logging.info('交流输入线电压下限: %.1f V', ac_volt_low)
                
            elif cid1 == 0x41 and cid2 == CMD_READ_RECT_ANALOG:  # 获取整流模块模拟量
                if info[1] == rec_num:  # 整流模块模拟量
                    rec_volt = struct.unpack('>f', info[0:4])[0]
                    rec_num = info[4]
                    logging.info('整流模块输出电压: %.1f V', rec_volt)  
                    logging.info('整流模块数量: %d', rec_num)
                    offset = 5  
                    for i in range(rec_num):
                        rec_curr = struct.unpack('>f', info[offset:offset+4])[0]
                        offset += 4
                        rec_param_num = info[offset]
                        offset += 1
                        rec_limit_point = struct.unpack('>f', info[offset:offset+4])[0]
                        offset += 4
                        rec_out_volt = struct.unpack('>f', info[offset:offset+4])[0] 
                        offset += 4
                        rec_temp = struct.unpack('>f', info[offset:offset+4])[0]
                        offset += 4 
                        rec_ac_volt = struct.unpack('>f', info[offset:offset+4])[0]
                        offset += 4
                        logging.info('模块%d:', i+1)
                        logging.info('  输出电流: %.1f A', rec_curr) 
                        logging.info('  限流点: %.0f%%', rec_limit_point) 
                        logging.info('  输出电压: %.1f V', rec_out_volt)
                        logging.info('  温度: %.1f ℃', rec_temp)
                        logging.info('  交流输入电压: %.1f V', rec_ac_volt)
                        
            elif cid1 == 0x41 and cid2 == CMD_READ_RECT_SWITCH:  # 获取整流模块开关状态
                rec_num = info[1]  
                logging.info('整流模块开关输入状态(共%d个模块):', rec_num)
                offset = 2
                for i in range(rec_num):
                    onoff_state = '开机' if info[offset] == 0 else '关机'
                    limit_state = '限流' if info[offset+1] == 0 else '不限流'
                    offset += 2
                    logging.info('模块%d: %s, %s', i+1, onoff_state, limit_state)
                    
            elif cid1 == 0x41 and cid2 == CMD_READ_RECT_ALARM:  # 获取整流模块告警状态
                if info[1] == rec_num:  # 整流模块告警状态  
                    logging.info('整流模块告警状态(共%d个模块):', rec_num)
                    offset = 2
                    for i in range(rec_num):
                        module_fault = '故障' if info[offset] == 1 else '正常'
                        offset += 1
                        param_num = info[offset]  
                        offset += 1
                        comm_alarm = '通讯中断' if info[offset] == 0x80 else '正常'
                        offset += 1
                        protect_alarm = '保护告警' if info[offset] == 0x81 else '正常'
                        offset += 1
                        fan_alarm = '风扇故障' if info[offset] == 0x88 else '正常'
                        offset += 1
                        logging.info('模块%d: %s, %s, %s, %s', i+1, module_fault, comm_alarm, protect_alarm, fan_alarm)
                        
            elif cid1 == 0x41 and cid2 == CMD_READ_DC_ANALOG:  # 获取直流模拟量
                dc_volt = struct.unpack('>f', info[0:4])[0]
                dc_curr = struct.unpack('>f', info[4:8])[0]
                bat_group_num = info[8]
                logging.info('直流输出电压: %.1f V', dc_volt) 
                logging.info('总负载电流: %.1f A', dc_curr)
                logging.info('电池组数量: %d', bat_group_num)
                offset = 9
                for i in range(bat_group_num):
                    bat_curr = struct.unpack('>f', info[offset:offset+4])[0]
                    offset += 4
                    logging.info('电池组%d电流: %.1f A', i+1, bat_curr)
                dc_branch_num = info[offset] 
                offset += 1
                logging.info('直流分路数量: %d', dc_branch_num)
                for i in range(dc_branch_num):
                    dc_branch_curr = struct.unpack('>f', info[offset:offset+4])[0]
                    offset += 4
                    logging.info('直流分路%d电流: %.1f A', i+1, dc_branch_curr) 
                bat_total_curr = struct.unpack('>f', info[offset+1:offset+5])[0]
                offset += 5
                logging.info('电池总电流: %.1f A', bat_total_curr)
                for i in range(4):
                    bat_mid_volt = struct.unpack('>f', info[offset:offset+4])[0]
                    offset += 4
                    logging.info('电池组%d中点电压: %.1f V', i+1, bat_mid_volt)
                for i in range(1):
                    bat_cap = struct.unpack('>f', info[offset:offset+4])[0] 
                    offset += 4
                    logging.info('电池组%d剩余容量: %.1f%%', i+1, bat_cap)  
                for i in range(1):
                    bat_temp = struct.unpack('>f', info[offset:offset+4])[0]
                    offset += 4
                    logging.info('电池组%d温度: %.1f℃', i+1, bat_temp)
                for i in range(2):
                    env_temp = struct.unpack('>f', info[offset:offset+4])[0]
                    offset += 4
                    logging.info('环境温度%d: %.1f℃', i+1, env_temp) 
                for i in range(1):
                    env_humi = struct.unpack('>f', info[offset:offset+4])[0]  
                    offset += 4
                    logging.info('环境湿度%d: %.1f%%', i+1, env_humi) 
                dc_load_total_power = struct.unpack('>f', info[offset+48:offset+52])[0]
                dc_load_total_energy = struct.unpack('>f', info[offset+52:offset+56])[0]
                logging.info('直流总负载功率: %.0f W', dc_load_total_power)
                logging.info('直流总负载电量: %.1f kWh', dc_load_total_energy)
                for i in range(4):
                    dc_load_power = struct.unpack('>f', info[offset+56+i*4:offset+60+i*4])[0] 
                    logging.info('直流负载%d功率: %.0f W', i+1, dc_load_power)
                for i in range(4):
                    dc_load_energy = struct.unpack('>f', info[offset+72+i*4:offset+76+i*4])[0]
                    logging.info('直流负载%d电量: %.1f kWh', i+1, dc_load_energy)
                                                
            elif cid1 == 0x41 and cid2 == CMD_READ_DC_ALARM:  # 获取直流告警状态
                logging.info('直流告警状态:')  
                dc_volt_state = '正常' if info[2] == 0 else '欠压' if info[2] == 1 else '过压'
                logging.info('  直流电压状态: %s', dc_volt_state)
                logging.info('  直流防雷器状态: %s', '故障' if info[6] == 0x81 else '正常')
                logging.info('  交流第一路输入状态: %s', '停电' if info[8] == 0x84 else '正常')
                for i in range(4):
                    logging.info('  电池组%d熔丝状态: %s', i+1, '熔断' if info[9+i] == 0x83 else '正常')  
                for i in range(4):
                    logging.info('  电池组%d状态: %s', i+1, '丢失' if info[19+i] == 0x95 else '正常')
                logging.info('  BLVD状态: %s', '即将下电' if info[23] == 0x9B else '正常') 
                logging.info('  BLVD状态: %s', '已下电' if info[24] == 0x9C else '正常')
                for i in range(4):
                    logging.info('  负载%d即将下电状态: %s', i+1, '即将下电' if info[25+i*2] == 0x9D else '正常')
                    logging.info('  负载%d已下电状态: %s', i+1, '已下电' if info[26+i*2] == 0x9E else '正常')
                bat_temp_alarm = '正常' if info[44] == 0 else '过温' if info[44] == 0xB0 else '欠温' 
                logging.info('  电池温度状态: %s', bat_temp_alarm)
                logging.info('  电池温度传感器状态: %s', '正常' if info[45] == 0 else '未接入' if info[45] == 0xB2 else '故障')
                env_temp_alarm = '正常' if info[47] == 0 else '过温' if info[47] == 0xBE else '欠温'
                logging.info('  环境温度状态: %s', env_temp_alarm)
                for i in range(2):
                    sensor_state = '正常' if info[48+i] == 0 else '未接入' if info[48+i] == 0xC0 else '故障'
                    logging.info('  环境温度传感器%d状态: %s', i+1, sensor_state)
                env_humi_alarm = '正常' if info[50] == 0 else '过湿' if info[50] == 0xC6 else '欠湿'
                logging.info('  环境湿度状态: %s', env_humi_alarm)
                sensor_state = '正常' if info[51] == 0 else '未接入' if info[51] == 0xC8 else '故障'
                logging.info('  环境湿度传感器状态: %s', sensor_state)
                logging.info('  门磁状态: %s', '告警' if info[52] == 0xCE else '正常')
                logging.info('  水浸状态: %s', '告警' if info[53] == 0xCF else '正常')
                logging.info('  烟雾状态: %s', '告警' if info[54] == 0xD0 else '正常')
                for i in range(6):
                    logging.info('  开关量输入%d状态: %s', i+1, '告警' if info[56+i] == 0xD2 else '正常')
                    
            elif cid1 == 0x40 and cid2 == CMD_READ_DC_PARAM:  # 获取直流配电参数
                dc_volt_high, dc_volt_low = struct.unpack('>ff', info[:8])
                logging.info('直流电压上限: %.1f V', dc_volt_high)
                logging.info('直流电压下限: %.1f V', dc_volt_low)
                timed_boost_enable = '使能' if info[10] == 1 else '禁止'
                logging.info('定时均充功能: %s', timed_boost_enable)
                logging.info('定时均充时间: %d 小时', info[16])
                logging.info('定时均充间隔: %d 天', struct.unpack(">H", info[17:19])[0])
                logging.info('第1屏电池组数: %d', info[19])
                bat_high_temp, bat_low_temp = struct.unpack('>ff', info[29:37])
                logging.info('电池过温告警点: %.1f ℃', bat_high_temp)
                logging.info('电池欠温告警点: %.1f ℃', bat_low_temp)
                env_high_temp, env_low_temp = struct.unpack('>ff', info[37:45])
                logging.info('环境过温告警点: %.1f ℃', env_high_temp)
                logging.info('环境欠温告警点: %.1f ℃', env_low_temp)
                env_high_humi, env_low_humi = struct.unpack('>ff', info[45:53]) 
                logging.info('环境过湿告警点: %.1f %%', env_high_humi)
                logging.info('环境欠湿告警点: %.1f %%', env_low_humi)
                bat_charge_limited = struct.unpack('>f', info[53:57])[0]
                logging.info('电池充电限流点: %.2f C10', bat_charge_limited) 
                bat_float_volt, bat_boost_volt = struct.unpack('>ff', info[57:65])
                logging.info('浮充电压: %.1f V', bat_float_volt)
                logging.info('均充电压: %.1f V', bat_boost_volt)
                bat_dropout_volt, bat_up_volt = struct.unpack('>ff', info[65:73])
                logging.info('电池下电电压: %.1f V', bat_dropout_volt)
                logging.info('电池上电电压: %.1f V', bat_up_volt)
                for i in range(4):
                    logging.info('LLVD%d下电电压: %.1f V', i+1, struct.unpack(">f", info[73+i*4:77+i*4])[0])
                for i in range(4):
                    logging.info('LLVD%d上电电压: %.1f V', i+1, struct.unpack(">f", info[89+i*4:93+i*4])[0])
                logging.info('每组电池额定容量: %.0f Ah', struct.unpack(">f", info[105:109])[0])
                logging.info('电池测试终止电压: %.1f V', struct.unpack(">f", info[109:113])[0])
                logging.info('电池组温补系数: %.1f mV/℃', struct.unpack(">f", info[117:121])[0])
                logging.info('电池温补中心点: %.1f ℃', struct.unpack(">f", info[121:125])[0])
                float_volt_factor, boost_volt_factor = struct.unpack('>ff', info[125:133])
                logging.info('浮充转均充系数: %.2f C10', float_volt_factor)
                logging.info('均充转浮充系数: %.2f C10', boost_volt_factor)
                for i in range(4):
                    logging.info('LLVD%d下电延时: %.0f 分钟', i+1, struct.unpack(">f", info[133+i*4:137+i*4])[0])  
                logging.info('负载下电模式: %s', '时间' if info[149] == 1 else '电压')
                
            elif cid1 == 0x41 and cid2 == CMD_CTRL_RECT:  # 遥控整流模块
                logging.info('遥控整流模块 %s', '开机' if info[0] == 0x20 else '关机')
                
            elif cid1 == 0x41 and cid2 == CMD_SET_SYS_MODE:  # 修改系统控制状态
                logging.info('设置系统控制状态为 %s', '自动' if info[0] == 0xE0 else '手动')
                
            elif cid1 == 0x41 and cid2 == CMD_READ_SYS_MODE:  # 读取系统控制状态
                logging.info('系统当前处于 %s 状态', '自动控制' if info[0] == 0xE0 else '手动控制')
                
            elif cid1 == 0x41 and cid2 == CMD_CTRL_BUZZER:  # 后台告警音控制
                logging.info('告警音 %s', '使能' if info[0] == 0xE0 else '禁止')
                
            elif cid1 == 0x41 and cid2 == CMD_READ_ENERGY_PARAM:  # 读取节能参数
                energy_saving_enable = info[0]  
                energy_saving_min_rect = info[1]
                energy_saving_rotate_period = struct.unpack('>H', info[2:4])[0]
                energy_saving_optimal = info[4]
                energy_saving_redundant = info[5]
                logging.info('节能 %s', '使能' if energy_saving_enable == 0 else '禁止')  
                logging.info('最小工作模块数: %d', energy_saving_min_rect)
                logging.info('模块循环周期: %d 天', energy_saving_rotate_period) 
                logging.info('模块最佳效率点: %d %%', energy_saving_optimal)
                logging.info('模块冗余点: %d %%', energy_saving_redundant)
                
            elif cid1 == 0x41 and cid2 == CMD_SYS_CTRL:  # 系统控制
                if info[0] == 0xE1:
                    logging.info('系统复位')
                elif info[0] == 0xE5:
                    logging.info('负载1下电')
                elif info[0] == 0xE6:
                    logging.info('负载1上电')
                elif info[0] == 0xE7:
                    logging.info('负载2下电')
                elif info[0] == 0xE8:
                    logging.info('负载2上电')
                elif info[0] == 0xE9:
                    logging.info('负载3下电')
                elif info[0] == 0xEA:
                    logging.info('负载3上电') 
                elif info[0] == 0xEB:
                    logging.info('负载4下电')
                elif info[0] == 0xEC:
                    logging.info('负载4上电')  
                elif info[0] == 0xED:
                    logging.info('电池下电')
                elif info[0] == 0xEE:
                    logging.info('电池上电')
                                        
    else:
        logging.error('响应数据长度错误')

def main():
    # 获取串口配置
    port = input('请输入串口号(如COM3): ')
    baudrate = 9600  
    bytesize = 8
    parity = 'N'
    stopbits = 1

    # 打开串口
    ser = serial.Serial(port, baudrate, bytesize, parity, stopbits)
    logging.info('MU4801监控程序已启动,使用串口: %s', port) 

    while True:
        # 发送获取设备地址命令
        response = send_command(ser, 0x01, CMD_READ_ADDR)
        if response:
            parse_response(response)
            device_addr = struct.unpack('B', response[-1:])[0]
        else:
            device_addr = 0x01  # 默认设备地址
        
        # 发送获取当前时间命令
        response = send_command(ser, device_addr, CMD_READ_TIME)  
        if response:  
            parse_response(response)
        
        # 发送获取协议版本号命令
        response = send_command(ser, device_addr, CMD_READ_VERSION)
        if response:
            parse_response(response)
        
        # 发送获取厂家信息命令
        response = send_command(ser, device_addr, CMD_READ_MANUFACTURER)
        if response:
            parse_response(response)
        
        # 发送获取交流模拟量命令  
        response = send_command(ser, device_addr, CMD_READ_AC_ANALOG)
        if response: 
            parse_response(response)
        
        # 发送获取交流告警状态命令
        response = send_command(ser, device_addr, CMD_READ_AC_ALARM)
        if response:
            parse_response(response)
        
        # 发送获取交流配电参数命令
        response = send_command(ser, device_addr, CMD_READ_AC_PARAM)
        if response:  
            parse_response(response)
        
        # 发送获取整流模块模拟量命令
        response = send_command(ser, device_addr, CMD_READ_RECT_ANALOG)
        if response:
            parse_response(response)
        
        # 发送获取整流模块开关状态命令  
        response = send_command(ser, device_addr, CMD_READ_RECT_SWITCH)
        if response:
            parse_response(response)
        
        # 发送获取整流模块告警状态命令
        response = send_command(ser, device_addr, CMD_READ_RECT_ALARM)
        if response:
            parse_response(response)
        
        # 发送获取直流模拟量命令
        response = send_command(ser, device_addr, CMD_READ_DC_ANALOG)
        if response:
            parse_response(response)
        
        # 发送获取直流告警状态命令
        response = send_command(ser, device_addr, CMD_READ_DC_ALARM)
        if response:  
            parse_response(response)
        
        # 发送获取直流配电参数命令  
        response = send_command(ser, device_addr, CMD_READ_DC_PARAM)
        if response:
            parse_response(response)
        
        # 发送遥控整流模块开机命令
        response = send_command(ser, device_addr, CMD_CTRL_RECT, b'\x20')
        if response:
            parse_response(response)

        time.sleep(5)  # 每隔5秒采集一次数据

if __name__ == '__main__':
    main()