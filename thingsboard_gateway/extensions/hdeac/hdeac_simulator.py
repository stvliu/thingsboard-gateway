import struct
import time
import serial

# 空调模拟器配置
PORT = '/dev/ttyS3'  # 串口端口
BAUDRATE = 9600  # 波特率
BYTESIZE = serial.EIGHTBITS  # 数据位
PARITY = serial.PARITY_NONE  # 校验位
STOPBITS = serial.STOPBITS_ONE  # 停止位
TIMEOUT = 2  # 超时时间
SLAVE_ADDRESS = 1  # 空调从机地址
PROTOCOL_VERSION = 0x0102  # 通信协议版本号
AC_START_TEMP = 20.0  # 空调启动温度
AC_SENSITIVITY = 2.0  # 空调灵敏度
HEATING_START_TEMP = 15.0  # 加热启动温度
HEATING_SENSITIVITY = 1.5  # 加热灵敏度  
HIGH_TEMP_ALARM = 50.0  # 高温告警阈值
LOW_TEMP_ALARM = -10.0  # 低温告警阈值

# 串口设置  
ser = serial.Serial(PORT, BAUDRATE, BYTESIZE, PARITY, STOPBITS, timeout=TIMEOUT)

print(f'HDE-AC simulator started, listening on port {PORT}')
print('HDE-AC simulator started, listening on port', PORT)

# 状态寄存器
power_state = 0b00000000  # 电源状态
alarms = 0b00000000  # 告警状态

# 配置参数
parameters = {
    0x46: struct.pack('>ff', AC_START_TEMP, AC_SENSITIVITY),  # 空调启动温度和灵敏度
    0x47: struct.pack('>hhhh', int(HEATING_START_TEMP*10), int(HEATING_SENSITIVITY*10), 
                      int(HIGH_TEMP_ALARM*10), int(LOW_TEMP_ALARM*10))  # 加热启动温度、灵敏度、高低温告警阈值
}

# 设备信息
device_info = {
    'device_name': 'HDE-AC1'.encode('ascii').ljust(10, b'\x00'),  # 设备名称  
    'sw_version': PROTOCOL_VERSION.to_bytes(2, 'big'),  # 软件版本号
    'manufacturer': 'Heifeng'.encode('ascii').ljust(20, b'\x00')  # 制造商
}

def make_response(command, data):
    """生成响应报文""" 
    response = bytearray([0xEE, 0xEE, SLAVE_ADDRESS, command])  # 帧头、从机地址、命令字
    response.extend(data)  # 数据域
    crc = sum(response).to_bytes(2, 'little')  # CRC校验
    response.extend(crc)
    return response

while True:
    # 读取请求报文
    request = ser.read(8)  
    if len(request) == 8 and request[0] == 0xEE and request[1] == 0xEE:
        print(f'Received command: {request.hex()}')
        print('Received command:', request.hex())
        command = request[3]
        data = request[4:-2]

        response = None
        
        if command == 0x43:  # 读取电源状态
            response = make_response(command, power_state.to_bytes(1, 'big'))
        elif command == 0x44:  # 读取告警状态
            response = make_response(command, alarms.to_bytes(1, 'big'))  
        elif command == 0x45:  # 遥控命令
            if data[0] == 0x10:  # 开机
                power_state |= 0b00000001  
            elif data[0] == 0x1f:  # 关机
                power_state = 0b00000000
            elif data[0] == 0x20:  # 制冷
                power_state |= 0b00000010
            elif data[0] == 0x2f:  # 停止制冷
                power_state &= ~0b00000010
            elif data[0] == 0x30:  # 加热 
                power_state |= 0b00001000
            elif data[0] == 0x3f:  # 停止加热
                power_state &= ~0b00001000
            elif data[0] == 0x40:  # 内风机启动
                power_state |= 0b00000100
            elif data[0] == 0x4f:  # 内风机关闭
                power_state &= ~0b00000100
            response = make_response(command, b'')
        elif command in [0x46, 0x47]:  # 读取参数
            response = make_response(command, parameters[command])
        elif command == 0x48:  # 设置空调启动温度和灵敏度
            AC_START_TEMP, AC_SENSITIVITY = struct.unpack('>ff', data)
            parameters[0x46] = data
            response = make_response(command, b'')
        elif command == 0x49:  # 设置加热启动温度等参数  
            HEATING_START_TEMP, HEATING_SENSITIVITY, HIGH_TEMP_ALARM, LOW_TEMP_ALARM = struct.unpack('>hhhh', data)
            HEATING_START_TEMP /= 10
            HEATING_SENSITIVITY /= 10
            HIGH_TEMP_ALARM /= 10
            LOW_TEMP_ALARM /= 10
            parameters[0x47] = data
            response = make_response(command, b'')
        elif command == 0x4A:  # 读取历史数据(浮点数)
            history_data = struct.pack('>ii', int(time.time()), 12345) * 20  # 假数据
            response = make_response(command, history_data)
        elif command == 0x4B:  # 读取历史数据(定点数)
            history_data = struct.pack('>ihh', int(time.time()), 1234, 5678) * 20  # 假数据  
            response = make_response(command, history_data)
        elif command == 0x4C:  # 读取历史告警
            history_alarms = struct.pack('>iB', int(time.time()), alarms) * 20  # 假数据
            response = make_response(command, history_alarms)
        elif command == 0x4D:  # 读设备时间 
            timestamp = int(time.time())
            device_time = time.localtime(timestamp)
            device_time_data = struct.pack('>HBBBBB', device_time.tm_year, device_time.tm_mon,
                                            device_time.tm_mday, device_time.tm_hour,  
                                            device_time.tm_min, device_time.tm_sec)
            response = make_response(command, device_time_data)
        elif command == 0x4E:  # 写设备时间
            pass  
        elif command == 0x4F:  # 读通信协议版本号
            response = make_response(command, PROTOCOL_VERSION.to_bytes(2, 'big'))
        elif command == 0x50:  # 读从机地址
            response = make_response(command, SLAVE_ADDRESS.to_bytes(1, 'big')) 
        elif command == 0x51:  # 读设备信息 
            device_info_data = device_info['device_name'] + device_info['sw_version'] + device_info['manufacturer']
            response = make_response(command, device_info_data)
        elif command == 0x80:  # 设置从机地址
            SLAVE_ADDRESS = data[0]  
            response = make_response(command, b'') 
        
        if response:
            ser.write(response)
            print(f'Sent response: {response.hex()}')
            print('Sent response:', response.hex())
        else:
            print(f'Unknown command: 0x{command:02X}')
            print('Unknown command: 0x{:02X}'.format(command))