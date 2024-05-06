"""
文件: ydt1363_downlink_converter.py
描述: YD/T 1363.3协议下行数据转换器,将Thingsboard下发的控制命令转换为设备能识别的原始数据。
"""

import struct


class YDT1363DownlinkConverter:
    """
    YDT1363DownlinkConverter类,实现了将Thingsboard下发的控制命令转换为设备能识别的原始数据的功能。
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
        elif config.get('dataType') in ('enum', 'timestamp', 'parameters'):
            return str(data).encode('ascii')
        else:
            return data