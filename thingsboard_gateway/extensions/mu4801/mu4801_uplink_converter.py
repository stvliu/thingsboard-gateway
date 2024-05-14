import struct
from io import BytesIO
from thingsboard_gateway.connectors.converter import Converter


class Mu4801UplinkConverter(Converter):
    
    def __init__(self, connector, log):
        self.__connector = connector
        self._log = log
        self.__datatypes = {
            'int16': {'size': 2, 'struct': 'h', 'byteorder': 'big'},
            'uint16': {'size': 2, 'struct': 'H', 'byteorder': 'big'},
            'int32': {'size': 4, 'struct': 'i', 'byteorder': 'big'},  
            'uint32': {'size': 4, 'struct': 'I', 'byteorder': 'big'},
            'uint8': {'size': 1, 'struct': 'B', 'byteorder': 'big'},  
            'float': {'size': 4, 'struct': 'f', 'byteorder': 'big'}, 
            'boolean': {'size': 1, 'struct': '?', 'byteorder': 'big'}, 
            'string': {'size': None, 'struct': None, 'byteorder': None}
        }
        
    def parse_attribute(self, config, data, device_name):
        try:
            value = self.__parse_value(config, data)
            return {
                'device': device_name,
                config['key']: value
            }
        except Exception as e:
            self._log.error(f"Failed to parse attribute data for device '{device_name}': {str(e)}")
        return None
    
    def parse_telemetry(self, config, data, device_name):
        result = {}
        try:
            for name, value_config in config['values'].items():
                value = self.__parse_value(value_config, data)
                if value is not None:
                    result[name] = value
        except Exception as e:
            self._log.error(f"Failed to parse telemetry data for device '{device_name}': {str(e)}")
        return {
            'device': device_name,
            'ts': int(time.time() * 1000),
            'values': result
        } if result else None
        
    def parse_rpc_reply(self, data, config, device_name):
        try:
            result = {}
            for param in config['paramsFormat']:
                value = self.__parse_value(param, data)
                if value is not None:
                    result[param['name']] = value
            
            return {'success': True, 'params': result}
        except Exception as e:
            self._log.error(f"Failed to parse RPC reply data for device '{device_name}': {str(e)}")
            return {'success': False}
        
    def __parse_value(self, config, data):
        value_type = config['dataType']
        start_index = config['startPos']
        
        datatype_config = self.__datatypes.get(value_type)
        if not datatype_config:
            self._log.error(f"Unsupported data type: {value_type}")
            return None
        
        byteorder = datatype_config['byteorder']
        if datatype_config['size'] is None:
            # String type
            value = data[start_index:].decode('ascii').strip('\x00')
        elif value_type == 'boolean':
            # Boolean type
            value = struct.unpack_from(datatype_config['struct'], data, start_index)[0]
            bool_map = config.get('booleanMap')
            if bool_map:
                value = bool_map.get(str(value), value)
        else:
            # Numeric types  
            value = struct.unpack_from(byteorder + datatype_config['struct'], data, start_index)[0] 
            
        if config.get('factor'):
            value *= config['factor']
            
        return value