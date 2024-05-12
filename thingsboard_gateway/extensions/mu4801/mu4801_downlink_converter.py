"""
文件: mu4801_downlink_converter.py
描述: MU4801协议下行数据转换器,将Thingsboard下发的控制命令转换为设备能识别的原始数据。
"""

import struct
import time


class MU4801DownlinkConverter:
    """
    MU4801DownlinkConverter类,实现了将Thingsboard下发的控制命令转换为设备能识别的原始数据的功能。
    """
    
    @staticmethod
    def convert(config, data):
        """
        转换数据的静态方法。
        
        参数:
        - config: dict,转换器配置信息。
        - data: dict,Thingsboard下发的控制命令数据。
        
        返回:
        - bytes,转换后的原始数据。
        """
        # 根据数据类型进行转换
        if config.get('dataType') == 'uint8':
            return struct.pack('>B', data)
        elif config.get('dataType') == 'uint16':
            return struct.pack('>H', data)
        elif config.get('dataType') == 'int16':
            return struct.pack('>h', data)
        elif config.get('dataType') == 'uint32':
            return struct.pack('>I', data)
        elif config.get('dataType') == 'int32':
            return struct.pack('>i', data)
        elif config.get('dataType') == 'float32':
            return struct.pack('>f', data)
        elif config.get('dataType') == 'enum':
            # 根据映射关系找到对应的枚举值
            for key, value in config['mapping'].items():
                if value == data:
                    return struct.pack('>B', int(key, 16))
            raise ValueError(f"Invalid enum value: {data}")
        elif config.get('dataType') == 'timestamp':
            try:
                # 将时间戳转换为年月日时分秒
                time_tuple = time.localtime(data / 1000)
                year = time_tuple.tm_year
                month = time_tuple.tm_mon
                day = time_tuple.tm_mday
                hour = time_tuple.tm_hour
                minute = time_tuple.tm_min
                second = time_tuple.tm_sec
                return struct.pack('>HBBBBB', year, month, day, hour, minute, second)
            except (ValueError, OverflowError):
                return None
        elif config.get('dataType') == 'parameters':
            result = bytearray()
            for key, value in config['mapping'].items():
                result.extend(MU4801DownlinkConverter.convert(value, data[key]))
            return bytes(result)
        else:
            return data