"""
文件: mu4801_uplink_converter.py
描述: MU4801协议上行数据转换器,将设备上报的原始数据转换为Thingsboard接受的数据格式。
"""


class MU4801UplinkConverter:
    """
    MU4801UplinkConverter类,实现了将设备上报的原始数据转换为Thingsboard接受的数据格式的功能。
    """

    def __init__(self, logger):
        """
        初始化MU4801UplinkConverter对象。

        参数:
        - logger: logging.Logger,日志对象。
        """
        # 日志对象
        self.__logger = logger

    def convert(self, config, data):
        """
        转换数据的方法。

        参数:
        - config: dict,转换器配置信息。
        - data: dict,设备上报的原始数据。

        返回:
        - dict,转换后的Thingsboard接受的数据格式。
        """
        result = {
            # 设备名称
            'deviceName': config['deviceName'],
            # 设备类型  
            'deviceType': config['deviceType'],
            # 属性数据
            'attributes': [],
            # 遥测数据
            'telemetry': []
        }
        try:
            # 遍历原始数据中的每一项
            for item in data:
                # 判断数据类型是属性数据还是遥测数据
                data_type = 'attributes' if item in config['attributes'] else 'telemetry'
                # 将转换后的数据添加到对应的数组中
                result[data_type].append({item: data[item]})
        except Exception as e:
            # 记录转换数据时发生的异常
            self.__logger.error('Failed to convert data: %s', str(e))
        return result