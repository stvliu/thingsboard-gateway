import pigpio
import pigpio_dht
import time

# 初始化pigpio
pi = pigpio.pi()

# 设置DHT11传感器连接的GPIO引脚
dht11_pin = 4  # 确保这里是一个整数值

# 创建DHT11传感器对象
dht11 = pigpio_dht.DHT11(pi, dht11_pin)

try:
    while True:
        # 读取DHT11传感器数据
        result = dht11.read()
        
        # 检查读取是否成功
        if result.is_valid():
            temperature = result.temperature
            humidity = result.humidity
            print(f"Temperature: {temperature:.1f}°C, Humidity: {humidity:.1f}%")
        else:
            print("读取DHT11传感器数据失败")
        
        # 延迟2秒后再次读取
        time.sleep(2)

except KeyboardInterrupt:
    # 清理资源
    dht11.cancel()
    pi.stop()