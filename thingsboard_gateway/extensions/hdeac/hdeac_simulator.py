import serial
import struct
import time
import binascii

# 模拟空调参数
ac_temp = 25.0         # 空调温度
ac_temp_set = 25.0     # 设置温度
ac_temp_range = 5.0    # 温度范围
ac_humidity = 50.0     # 空调湿度
ac_humidity_set = 50.0 # 设置湿度  
ac_humidity_range = 20.0 # 湿度范围
ac_mode = 0            # 空调模式(0-制冷,1-制热,2-除湿)  
ac_fan_speed = 0       # 风速(0-低速,1-中速,2-高速)
ac_power_state = 1     # 电源状态(0-关机,1-开机)
ac_eco_mode = 0        # 节能模式(0-关闭,1-开启)
ac_lock = 0            # 童锁(0-关闭,1-开启) 
ac_swing = 0           # 摆风(0-关闭,1-开启)
ac_indoor_temp = 26.5  # 室内温度
ac_indoor_humidity = 65.0 # 室内湿度  
ac_fault_code = 0      # 故障代码
ac_cumulative_runtime = 1000 # 累计运行时间(小时)
ac_voltage = 220       # 工作电压
ac_current = 1.5       # 工作电流
ac_indoor_fan_state = 1 # 内风机状态(0-关机,1-开机)
ac_outdoor_fan_state = 1 # 外风机状态(0-关机,1-开机)
ac_heater_state = 0    # 加热状态(0-关机,1-开机)
ac_cooling_fault = 0   # 制冷故障  
ac_high_temp_alarm = 0 # 高温告警
ac_low_temp_alarm = 0  # 低温告警
ac_heater_fault = 0    # 加热故障
ac_sensor_fault = 0    # 传感器故障
ac_voltage_fault = 0   # 电压故障
ac_work_state_fault = 0 # 设备工作状态异常

ac_firmwareVersion = [1, 0] # 厂家软件版本号

ac_cooling_timer = None  # 制冷开启计时器
ac_heating_timer = None  # 制热开启计时器

def calc_checksum(data):
    """计算校验和"""
    checksum = sum([b for b in data]) % 65536
    return (checksum ^ 0xFFFF) + 1

def send_response(ser,ver,adr,cid1,cid2,data):
    """发送响应数据"""
    # 构造响应帧  
    soi = b'\x7E'  # 起始位
    ver = struct.pack('B', ver)
    adr = struct.pack('B', adr)
    cid1 = struct.pack('B', cid1)
    cid2 = struct.pack('B', cid2)
    length = struct.pack('>H', len(data))
    info = data
    frame = ver + adr + cid1 + cid2 + length + info
    checksum = struct.pack('>H', calc_checksum(frame))
    eoi = b'\x0D'  # 结束位

    response = soi + frame + checksum + eoi

    # 发送响应数据
    ser.write(response)
    print('发送响应:', ' '.join([f'{c:02X}' for c in response]))

def handle_command(ser,ver,adr,cid1,cid2,info):
    """处理接收到的命令"""
    global ac_temp, ac_temp_set, ac_temp_range, ac_humidity, ac_humidity_set, ac_humidity_range, ac_mode, ac_fan_speed, ac_power_state, ac_eco_mode, ac_lock, ac_swing, ac_indoor_temp, ac_indoor_humidity, ac_fault_code, ac_cumulative_runtime, ac_voltage, ac_current, ac_indoor_fan_state, ac_outdoor_fan_state, ac_heater_state, ac_cooling_fault, ac_high_temp_alarm, ac_low_temp_alarm, ac_heater_fault, ac_sensor_fault, ac_voltage_fault, ac_work_state_fault, ac_firmwareVersion, ac_cooling_timer, ac_heating_timer

    rtn = 0  # 正常返回

    if cid1 == 0x61 and cid2 == 0x42:  # 获取系统模拟量量化数据(定点数)
        response_data = struct.pack('>hhhh', int(ac_temp*10), int(ac_indoor_temp*10), int(ac_voltage), int(ac_current*10)) 
        send_response(ser,ver,adr,0x61,0,response_data)

    elif cid1 == 0x61 and cid2 == 0x43:  # 获取开关输入状态
        response_data = struct.pack('BBBB', ac_power_state, ac_indoor_fan_state, ac_outdoor_fan_state, ac_heater_state) 
        send_response(ser,ver,adr,0x61,0,response_data)

    elif cid1 == 0x61 and cid2 == 0x44:  # 获取告警状态  
        response_data = struct.pack('BBBBBBBB', ac_cooling_fault, ac_high_temp_alarm, ac_low_temp_alarm, ac_heater_fault, ac_sensor_fault, ac_voltage_fault, ac_work_state_fault, 0x20)
        send_response(ser,ver,adr,0x61,0,response_data)

    elif cid1 == 0x61 and cid2 == 0x45:  # 遥控
        if len(info) == 1:
            cmd = info[0]
            if cmd == 0x10:  # 开机
                ac_power_state = 1
            elif cmd == 0x1F:  # 关机  
                ac_power_state = 0
            elif cmd == 0x20:  # 制冷开启
                ac_mode = 0
                if ac_cooling_timer is None:
                    ac_cooling_timer = time.time()  
            elif cmd == 0x2F:  # 制冷关闭
                ac_mode = 1
                ac_cooling_timer = None
            elif cmd == 0x30:  # 制热开启
                ac_mode = 1
                if ac_heating_timer is None:
                    ac_heating_timer = time.time()
            elif cmd == 0x3F:  # 制热关闭  
                ac_mode = 0
                ac_heating_timer = None
            else:
                rtn = 6  # 无效数据
        else:
            rtn = 5  # 命令格式错  
        send_response(ser,ver,adr,0x61,rtn,b'')

    elif cid1 == 0x61 and cid2 == 0x47:  # 获取参数(定点数)
        response_data = struct.pack('>hhhhhh', int(ac_temp_set*10), int(ac_temp_range*10), int(ac_heater_start*10), int(ac_heater_span*10), int(ac_exchanger_start*10), int(ac_exchanger_span*10))
        send_response(ser,ver,adr,0x61,0,response_data)  

    elif cid1 == 0x61 and cid2 == 0x49:  # 设置参数(定点数)
        if len(info) == 3:
            cmd = info[0]
            data = struct.unpack('>h', info[1:])[0] / 10.0
            if cmd == 0x80:  # 空调开启点  
                ac_temp_set = data
            elif cmd == 0x81:  # 空调灵敏点
                ac_temp_range = data
            elif cmd == 0x82:  # 加热开启点
                ac_heater_start = data
            elif cmd == 0x83:  # 加热灵敏度
                ac_heater_span = data
            elif cmd == 0x84:  # 热交换开启点
                ac_exchanger_start = data
            elif cmd == 0x85:  # 热交换灵敏点
                ac_exchanger_span = data
            else:
                rtn = 6  # 无效数据
        else:  
            rtn = 5  # 命令格式错
        send_response(ser,ver,adr,0x61,rtn,b'')

    elif cid1 == 0x61 and cid2 == 0x4D:  # 获取监测模块时间
        response_data = time.strftime('%Y%m%d%H%M%S').encode()  
        send_response(ser,ver,adr,0x61,0,response_data)
    
    elif cid1 == 0x61 and cid2 == 0x4E:  # 设置监测模块时间  
        if len(info) == 14:
            try:
                dt = time.strptime(info.decode(), '%Y%m%d%H%M%S')
                # 设置系统时间  
                time.clock_settime(dt)  
            except:
                rtn = 6  # 无效数据
        else:
            rtn = 5  # 命令格式错
        send_response(ser,ver,adr,0x61,rtn,b'')  

    elif cid1 == 0x61 and cid2 == 0x51:  # 获取设备厂家信息
        version_hex = f'{ac_firmwareVersion[0]:02X}{ac_firmwareVersion[1]:02X}'
        response_data = f'AC\x00\x00{version_hex}HAYDEN SUZHOU'.encode()
        send_response(ser,ver,adr,0x61,0,response_data)

    elif cid1 == 0x61 and cid2 == 0x80:  # 设置设备地址
        if len(info) == 1:
            adr = info[0]  
            send_response(ser,ver,adr,0x61,0,b'') 
        else:
            send_response(ser,ver,adr,0x61,5,b'')  # 命令格式错
    else:
        send_response(ser,ver,adr,0x61,0x80,b'')  # CID1错误
        
    # 检查制冷、制热开启是否超时
    if ac_cooling_timer is not None and time.time() - ac_cooling_timer > 600:
        ac_cooling_timer = None
        ac_mode = 1 if ac_temp < ac_temp_set else 0
        
    if ac_heating_timer is not None and time.time() - ac_heating_timer > 600:
        ac_heating_timer = None
        ac_mode = 0 if ac_temp > ac_temp_set else 1
        
    time.sleep(0.1)  # 控制命令处理的速度
        
def main():
    # 获取串口配置
    serial_port = input('请输入串口号(如COM3或/dev/ttyUSB0): ')
    baud_rate = 9600
    bytesize = serial.EIGHTBITS
    parity = serial.PARITY_NONE
    stopbits = serial.STOPBITS_ONE

    # 打开串口
    ser = serial.Serial(serial_port, baud_rate, bytesize, parity, stopbits)

    print(f'黑盾空调模拟器已启动，使用串口: {serial_port}')

    receiving = False
    received_data = b''

    while True:
        if not receiving:
            # 找到数据帧的起始标志
            while True:
                data = ser.read(1)
                if data == b'\x7E':
                    receiving = True
                    received_data = data
                    break
        else:
            data = ser.read(1)
            received_data += data
            if data == b'\x0D':  # 找到数据帧的结束标志
                receiving = False

                try:
                    header = received_data[1:9]
                    ver,adr,cid1,cid2,length = struct.unpack('>BBBBB', header[0:5]) 
                    info = received_data[9:-3]
                    checksum = received_data[-3:-1]

                    eoi = received_data[-1:]
                    print('接收命令:', f'7E {" ".join([f"{c:02X}" for c in header])} {" ".join([f"{c:02X}" for c in info])} {" ".join([f"{c:02X}" for c in checksum])} {eoi[0]:02X}')
                    
                    # 验证校验和
                    calc_cs = calc_checksum([ver,adr,cid1,cid2,length]+list(info))
                    received_cs = struct.unpack('>H', checksum)[0]
                    if calc_cs == received_cs:
                        handle_command(ser,ver,adr,cid1,cid2,info)  # 处理命令
                    else:
                        print('校验和错误')

                except Exception as e:
                    print(f'解析命令时出错: {e}')
                        
                received_data = b''  # 清空接收缓冲区
                    
        time.sleep(0.01)  # 控制接收数据的速度
        
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('程序已终止')