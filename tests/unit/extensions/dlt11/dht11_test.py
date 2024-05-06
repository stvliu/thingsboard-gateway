import Adafruit_DHT
import time

# DHT11传感器类型
sensor = Adafruit_DHT.DHT11

# GPIO引脚号
pin = 4

while True:
    # 读取温湿度数据
    humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

    if humidity is not None and temperature is not None:
        print(f'Temperature: {temperature:.1f}°C, Humidity: {humidity:.1f}%')
    else:
        print('Failed to retrieve data from DHT11 sensor.')

    # 等待2秒后再次读取数据
    time.sleep(2)