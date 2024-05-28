from thingsboard_gateway.connectors.converter import Converter
import struct
from io import BytesIO

class Mu4801DownlinkConverter(Converter):
   def __init__(self, connector, log):
       self.__connector = connector
       self._log = log
       self.unidirectional_methods = ['setLoadSwitch', 'setRectifierModule', 'setBatterySwitch', 'resetSystem', 'setDateTime']
       self.__datatypes = {
           'int16': {'size': 2, 'struct': 'h', 'byteorder': 'big', 'signed': True},
           'uint16': {'size': 2, 'struct': 'H', 'byteorder': 'big', 'signed': False},
           'int32': {'size': 4, 'struct': 'i', 'byteorder': 'big', 'signed': True},
           'uint32': {'size': 4, 'struct': 'I', 'byteorder': 'big', 'signed': False},
           'uint8': {'size': 1, 'struct': 'B', 'byteorder': 'big', 'signed': False},
           'float': {'size': 4, 'struct': 'f', 'byteorder': 'big', 'signed': True},
           'boolean': {'size': 1, 'struct': 'B', 'byteorder': 'big', 'signed': False},
           'string': {'size': None, 'struct': None, 'byteorder': None, 'signed': False}
       }

   def convert(self, config, data):
       command_hex = config['command']
       frame_template = config['frame_template']

       buffer = BytesIO()

       for param_config in frame_template:
           name = param_config['name']
           value_type = param_config['dataType']

           if name in data['value']:
               value = data['value'][name]
           elif name in data:
               value = data[name]
           else:
               self._log.warning(f"Parameter '{name}' not found in data: {data}")
               continue

           datatype_config = self.__datatypes.get(value_type)
           if not datatype_config:
               self._log.error(f"Unsupported data type: {value_type}")
               continue

           if value_type == 'boolean':
               bool_map = param_config.get('booleanMap', {'true': 1, 'false': 0})
               value = bool_map.get(str(value).lower(), value)

           if datatype_config['size'] is None:
               buffer.write(value.encode('ascii'))
           else:
               byteorder = datatype_config['byteorder']
               signed = datatype_config['signed']
               struct.pack_into(byteorder + datatype_config['struct'], buffer.getbuffer(), buffer.tell(), value)
               buffer.seek(datatype_config['size'], 1)

       data_hex = buffer.getvalue().hex()
       command = bytes.fromhex(command_hex.format(data=data_hex))

       self._log.debug(f"Converted RPC command: {command.hex()}")
       return command

   def convert_rectifier_settings(self, config, data):
       command_hex = config['command']
       frame_template = config['frame_template']

       buffer = BytesIO()

       for param_config in frame_template:
           name = param_config['name']
           value_type = param_config['dataType']

           if name in data['value']:
               value = data['value'][name]
           elif name in data:
               value = data[name]
           else:
               self._log.warning(f"Parameter '{name}' not found in data: {data}")
               continue

           datatype_config = self.__datatypes.get(value_type)
           if not datatype_config:
               self._log.error(f"Unsupported data type: {value_type}")
               continue

           if value_type == 'boolean':
               bool_map = param_config.get('booleanMap', {'true': 1, 'false': 0})
               value = bool_map.get(str(value).lower(), value)

           if datatype_config['size'] is None:
               buffer.write(value.encode('ascii'))
           else:
               byteorder = datatype_config['byteorder']
               signed = datatype_config['signed']
               struct.pack_into(byteorder + datatype_config['struct'], buffer.getbuffer(), buffer.tell(), value)
               buffer.seek(datatype_config['size'], 1)

       data_hex = buffer.getvalue().hex()
       command = bytes.fromhex(command_hex.format(data=data_hex))

       self._log.debug(f"Converted rectifier settings command: {command.hex()}")
       return command

   @staticmethod
   def config_from_type(config):
       for key, value in config.items():
           if isinstance(value, str):
               if value.startswith("${") and value.endswith("}"):
                   value = eval(value[2:-1])
               config[key] = value
       return config