import serial
import sys

def get_serial_port():
    """获取用户输入的串口号"""
    while True:
        port = input('请输入串口号(如COM3或/dev/ttyUSB0): ')
        if port.strip():
            return port
        else:
            print('串口号不能为空,请重新输入!')

def main():
    # 获取用户输入的串口号
    serial_port1 = get_serial_port()
    serial_port2 = get_serial_port()

    # 打开串口
    try:
        ser1 = serial.Serial(serial_port1, 9600)
        ser2 = serial.Serial(serial_port2, 9600)
    except serial.SerialException as e:
        print(f'打开串口失败: {e}')
        sys.exit(1)

    # 在第一个串口上发送数据
    try:
        ser1.write(b'Hello, world!')
        print(f'串口 {serial_port1} 发送: Hello, world!')
    except serial.SerialException as e:
        print(f'写入串口 {serial_port1} 失败: {e}')
        ser1.close()
        ser2.close()
        sys.exit(1)

    # 从第二个串口读取数据  
    try:
        data = ser2.read(13)
        print(f'串口 {serial_port2} 接收: {data.decode()}')
    except serial.SerialException as e:
        print(f'读取串口 {serial_port2} 失败: {e}')
    finally:  
        ser1.close()
        ser2.close()

if __name__ == '__main__':
    main()