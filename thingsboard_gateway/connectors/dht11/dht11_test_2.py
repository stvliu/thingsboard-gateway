import time
import board
import adafruit_dht

# 将DHT11传感器的data引脚连接到GPIO的17号引脚
dht_device = adafruit_dht.DHT11(board.D17)

while True:
    try:
        # 读取DHT11传感器的温度和湿度数据
        temperature = dht_device.temperature
        humidity = dht_device.humidity
        
        # 打印温度和湿度数据
        print(f"Temperature: {temperature:.1f}°C, Humidity: {humidity:.1f}%")
        
    except RuntimeError as e:
        # 读取数据时发生错误,打印错误信息并重试
        print(f"Reading data from DHT11 failed: {e}, retrying...")
        time.sleep(2)
        continue
        
    except Exception as e:
        # 发生其他错误,打印错误信息并退出程序
        print(f"Error: {e}")
        break
        
    # 等待2秒后再次读取数据
    time.sleep(2)