"""
MU4801上行数据转换器
该转换器用于将MU4801设备上报的数据转换为Thingsboard平台能识别的格式。
"""

import struct
import time
from io import BytesIO
from thingsboard_gateway.connectors.converter import Converter


class Mu4801UplinkConverter(Converter):
    """
    MU4801上行数据转换器类
    继承自Converter基类
    """
    
    def __init__(self, connector, log):
        """
        初始化上行数据转换器
        
        参数:
        connector: 连接器对象
        log: 日志对象
        """
        self.__connector = connector
        self._log = log
        # 数据类型配置
        self.__datatypes = {
            'int16': {'size': 2, 'struct': 'h'},
            'uint16': {'size': 2, 'struct': 'H'},
            'int32': {'size': 4, 'struct': 'i'},
            'uint32': {'size': 4, 'struct': 'I'},
            'uint8': {'size': 1, 'struct': 'B'},
            'float': {'size': 4, 'struct': 'f'},
            'boolean': {'size': 1, 'struct': '?'},
            'string': {'size': None, 'struct': None}
        }

    def convert(self, config, data):
        # 将Thingsboard下发的控制命令转换为MU4801设备的Modbus命令
        pass

    def parse_attribute(self, config, data, device_name):
        """
        解析属性数据
        
        参数:
        config: 属性配置
        data: 属性数据(字节串)
        device_name: 设备名称
        
        返回:  
        解析后的属性数据(dict)
        """
        result = {}
        try:
            timestamp = int(time.time() * 1000)
            
            if config['key'] == 'currentTime':
                # 解析当前时间
                values_config = config['values']
                for value_config in values_config:
                    name = value_config['key']
                    value = self.__parse_value(value_config, data)
                    if value is not None:
                        result[name] = value
            else:
                # 解析其他属性
                value = self.__parse_value(config, data)
                if value is not None:
                    result[config['key']] = value
                            
        except Exception as e:
            self._log.debug(f"Failed to parse attribute data for device '{device_name}': {str(e)}")
        
        if result:
            return {
                'device': device_name,
                'ts': timestamp,
                'values': result
            }
        else:
            return None
    
    def parse_telemetry(self, config, data, device_name):
        """
        解析遥测数据
        
        参数:
        config: 遥测配置
        data: 遥测数据(字节串)
        device_name: 设备名称
        
        返回:
        解析后的遥测数据(dict)
        """
        result = {}
        try:
            # 遍历配置的遥测值,逐个解析
            for name, value_config in config['values'].items():
                value = self.__parse_value(value_config, data)
                if value is not None:
                    result[name] = value
        except Exception as e:
            self._log.debug(f"Failed to parse telemetry data for device '{device_name}': {str(e)}")
        return {
            'device': device_name,
            'ts': int(time.time() * 1000),
            'values': result
        } if result else None
        
    def parse_alarm(self, config, data, device_name):
        """
        解析告警数据
        
        参数:
        config: 告警配置
        data: 告警数据(字节串)
        device_name: 设备名称
        
        返回:
        解析后的告警数据(dict)
        """
        result = {}
        try:
            # 遍历配置的告警值,逐个解析
            for name, value_config in config['values'].items():
                value = self.__parse_value(value_config, data)
                if value is not None:
                    result[name] = value
        except Exception as e:
            self._log.debug(f"Failed to parse alarm data for device '{device_name}': {str(e)}")
        return {
            'device': device_name,
            **result
        } if result else None
        
    def parse_rectifier_telemetry(self, data, device_name):
        """
        解析整流模块遥测数据
        
        参数:
        data: 遥测数据(字节串)
        device_name: 设备名称
        
        返回:
        解析后的整流模块遥测数据(dict)
        """
        result = {}
        try:
            # 数据标志,应为0
            dataflag = data[0]
            if dataflag != 0:
                self._log.debug(f"Unexpected dataflag value: {dataflag}")
            
            # 整流模块数量
            num_modules = data[2]
            result['moduleCount'] = num_modules
            
            # 直流输出电压
            dc_voltage = struct.unpack_from('>f', data, 3)[0]
            result['dcOutputVoltage'] = dc_voltage

            # 解析各整流模块的输出电流和电压
            for i in range(num_modules):
                idx = 7 + 8*i
                module_current = struct.unpack_from('>f', data, idx)[0]
                result[f'module{i+1}Current'] = module_current
                
                idx += 4
                module_voltage = struct.unpack_from('>f', data, idx)[0]
                result[f'module{i+1}Voltage'] = module_voltage
            
            # 解析自定义参数
            idx = 7 + 8*num_modules + 1
            num_custom = data[idx]
            
            for i in range(num_custom):
                idx += 1
                param_type = data[idx]
                idx += 1
                value = struct.unpack_from('>f', data, idx)[0]
                
                if param_type == 0xE0:
                    result[f'module{i+1}CurrentLimit'] = value
                elif param_type == 0xE1:
                    result[f'module{i+1}Temperature'] = value
                else:
                    self._log.debug(f"Unknown custom param type: {hex(param_type)}")
                                        
                idx += 4
            
        except Exception as e:
            self._log.debug(f"Failed to parse rectifier telemetry data for device '{device_name}': {str(e)}")
        
        return {
            'device': device_name,
            'ts': int(time.time() * 1000),
            'values': result
        } if result else None
        
    def parse_rectifier_alarms(self, data, device_name):
        """
        解析整流模块告警数据
        
        参数:
        data: 告警数据(字节串)
        device_name: 设备名称
        
        返回:
        解析后的整流模块告警数据(dict)
        """
        result = {}
        try:
            # 数据标志,应为0
            dataflag = data[0]
            if dataflag != 0:
                self._log.debug(f"Unexpected dataflag value: {dataflag}")
            
            # 整流模块数量
            num_modules = data[1]
            
            # 解析各整流模块的告警状态
            for i in range(num_modules):
                module_alarms = data[2+i]
                result[f'module{i+1}Fault'] = bool(module_alarms & 0x01)
                result[f'module{i+1}ACFault'] = bool(module_alarms & 0x02)
                result[f'module{i+1}PhaseLoss'] = bool(module_alarms & 0x04)
                result[f'module{i+1}DCFault'] = bool(module_alarms & 0x08)
                result[f'module{i+1}OverTemp'] = bool(module_alarms & 0x10)
                result[f'module{i+1}FanFault'] = bool(module_alarms & 0x20)
                
            # 解析自定义告警
            idx = 2 + num_modules
            num_custom = data[idx]
            
            for i in range(num_custom):
                idx += 1
                alarm_type = data[idx]
                
                if alarm_type == 0x80:
                    result[f'module{i+1}CommFault'] = True
                elif alarm_type == 0x81: 
                    result[f'module{i+1}Protection'] = True
                elif alarm_type == 0x88:
                    result[f'module{i+1}FanFault'] = True
                else:  
                    self._log.debug(f"Unknown custom alarm type: {hex(alarm_type)}")
            
        except Exception as e:
            self._log.debug(f"Failed to parse rectifier alarm data for device '{device_name}': {str(e)}")
        
        return {
            'device': device_name,
            **result
        } if result else None
        
    def parse_rectifier_status(self, data, device_name):
        """
        解析整流模块状态数据
        
        参数:
        data: 状态数据(字节串)
        device_name: 设备名称
        
        返回:
        解析后的整流模块状态数据(dict)
        """ 
        result = {} 
        try:
            # 数据标志,应为0
            dataflag = data[0]
            if dataflag != 0:
                self._log.debug(f"Unexpected dataflag value: {dataflag}")
            
            # 整流模块数量
            num_modules = data[1]
            
            # 解析各整流模块的开关状态和限流状态
            for i in range(num_modules):
                idx = 2 + i*2
                
                onoff_status = data[idx]
                limit_status = data[idx+1]
                
                result[f'module{i+1}OnOff'] = 'off' if onoff_status == 0x01 else 'on'
                result[f'module{i+1}CurrentLimited'] = 'yes' if limit_status == 0x00 else 'no'
            
        except Exception as e:
            self._log.debug(f"Failed to parse rectifier status data for device '{device_name}': {str(e)}")
        
        return {
            'device': device_name,
            **result
        } if result else None
        
    def parse_rpc_reply(self, data, config, device_name):
        """
        解析RPC响应数据
        
        参数:
        data: 响应数据(字节串)
        config: RPC配置
        device_name: 设备名称
        
        返回:
        解析后的RPC响应数据(dict)
        """
        try:
            result = {}
            # 遍历配置的RPC参数,逐个解析
            for param_name, param_config in config['paramsFormat'].items(): 
                value = self.__parse_value(param_config, data)
                if value is not None:
                    result[param_name] = value
            
            return {'success': True, 'params': result}
        except Exception as e:
            self._log.debug(f"Failed to parse RPC reply data for device '{device_name}': {str(e)}")
            return {'success': False}
        
    def __parse_value(self, config, data):
        """
        根据配置解析数据值
        
        参数:
        config: 数据配置
        data: 数据(字节串)
        
        返回:
        解析后的数据值
        """
        # 数据类型
        value_type = config['dataType']
        # 起始位置
        start_index = config['startPos']
        
        # 获取数据类型配置
        datatype_config = self.__datatypes.get(value_type)
        if not datatype_config:
            self._log.error(f"Unsupported data type: {value_type}")
            return None
        
        if datatype_config['size'] is None:
            # 字符串类型
            value = data[start_index:start_index+config['length']].decode('ascii').strip('\x00')
        elif value_type == 'boolean':
            # 布尔类型
            value = struct.unpack_from(datatype_config['struct'], data, start_index)[0]
            bool_map = config.get('booleanMap')
            if bool_map:
                value = bool_map.get(str(value), value)
        else:
            # 数值类型
            value = struct.unpack_from('>' + datatype_config['struct'], data, start_index)[0]
            
        # 应用缩放系数
        if config.get('scale'):
            value = value * config['scale']
            
        return value