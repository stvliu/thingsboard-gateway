import serial
import struct
import time
import select

def calc_checksum(data):
    """计算校验和"""
    checksum = sum([b for b in data]) % 65536
    return (checksum ^ 0xFFFF) + 1

def send_command(ser, ver, adr, cid1, cid2, info):
    """发送命令"""
    # 构造命令帧
    soi = b'\x7E'  # 起始位
    ver = struct.pack('B', ver)
    adr = struct.pack('B', adr)
    cid1 = struct.pack('B', cid1)
    cid2 = struct.pack('B', cid2)
    length = struct.pack('>H', len(info) + 5)
    data = ver + adr + cid1 + cid2 + length + info
    checksum = struct.pack('>H', calc_checksum(data))
    eoi = b'\x0D'  # 结束位

    command = soi + data + checksum + eoi

    # 发送命令
    try:
        ser.write(command)
        print('发送命令:', ' '.join([f'{c:02X}' for c in command]))
    except serial.SerialException as e:
        print(f'发送命令失败: {e}')
        return False
    
    return True

def receive_response(ser, timeout=5):  # 增加接收超时时间
    """接收响应"""
    response = b''
    start_time = time.time()
    
    while True:
        ready, _, _ = select.select([ser], [], [], 0.1)
        if ready:
            c = ser.read(1)
            if c == b'\x7E':  # 起始位
                response = c
                start_time = time.time()  # 重置起始时间
            elif c == b'\x0D':  # 结束位
                response += c
                break
            else:
                response += c

        if time.time() - start_time > timeout:  # 超时
            print('接收响应超时')
            return None

    print('接收响应:', ' '.join([f'{c:02X}' for c in response]))

    if len(response) > 9:
        data = response[1:-3]
        checksum = struct.unpack('>H', response[-3:-1])[0]

        # 验证校验和
        calc_cs = calc_checksum(data)
        if calc_cs == checksum:
            print('校验和正确')
            ver, adr, cid1, cid2, length = struct.unpack('>BBBBB', data[:5])
            info = data[5:]
            return ver, adr, cid1, cid2, info
        else:
            print('校验和错误')
            return None
    else:
        print('响应格式错误')
        return None

def main():
    # 获取串口配置
    serial_port = input('请输入串口号(如COM3或/dev/ttyUSB0): ')
    baud_rate = 9600
    bytesize = serial.EIGHTBITS
    parity = serial.PARITY_NONE
    stopbits = serial.STOPBITS_ONE

    # 打开串口
    try:
        ser = serial.Serial(serial_port, baud_rate, bytesize, parity, stopbits, timeout=0.5)
        print(f'连接到黑盾空调模拟器: {serial_port}')
    except serial.SerialException as e:
        print(f'打开串口失败: {e}')
        return

    while True:
        # 发送获取参数命令
        if send_command(ser, 0x20, 0x01, 0x61, 0x47, b''):
            # 接收响应
            response = receive_response(ser)
            if response:
                ver, adr, cid1, cid2, info = response
                if cid1 == 0x61 and cid2 == 0x00:
                    ac_temp_set, ac_temp_range, ac_heater_start, ac_heater_span, ac_exchanger_start, ac_exchanger_span = struct.unpack('>hhhhhh', info)
                    print(f'空调设置温度: {ac_temp_set/10}℃')
                    print(f'空调温度范围: {ac_temp_range/10}℃')
                    print(f'加热开启点: {ac_heater_start/10}℃')
                    print(f'加热灵敏度: {ac_heater_span/10}℃')
                    print(f'热交换开启点: {ac_exchanger_start/10}℃')
                    print(f'热交换灵敏点: {ac_exchanger_span/10}℃')
                else:
                    print('响应命令类型错误')

        time.sleep(1)  # 增加发送命令的时间间隔

        # 发送获取系统模拟量命令  
        if send_command(ser, 0x20, 0x01, 0x61, 0x42, b''):
            # 接收响应
            response = receive_response(ser)
            if response:
                ver, adr, cid1, cid2, info = response
                if cid1 == 0x61 and cid2 == 0x00:
                    ac_temp, ac_indoor_temp, ac_voltage, ac_current = struct.unpack('>hhhh', info)
                    print(f'空调温度: {ac_temp/10}℃')
                    print(f'室内温度: {ac_indoor_temp/10}℃')
                    print(f'工作电压: {ac_voltage}V')
                    print(f'工作电流: {ac_current/10}A')
                else:
                    print('响应命令类型错误')

        time.sleep(1)  # 增加发送命令的时间间隔

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('程序已终止')
    except Exception as e:
        print(f'发生异常: {e}')