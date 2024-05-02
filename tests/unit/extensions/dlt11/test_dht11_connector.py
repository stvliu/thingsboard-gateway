import unittest
from unittest.mock import Mock, patch
from thingsboard_gateway.extensions.dht11.dht11_connector import Dht11Connector

class TestDht11Connector(unittest.TestCase):
    
    def setUp(self):
        # 创建模拟对象
        self.gateway = Mock()
        self.config = {
            'devices': [
                {'name': 'device1', 'gpio': 1, 'reportInterval': 5000},
                {'name': 'device2', 'gpio': 2, 'reportInterval': 3000}
            ]
        }
        self.connector = Dht11Connector(self.gateway, self.config, 'dht11')
        
    def tearDown(self):
        # 清理工作
        pass

    def test_get_name(self):
        self.assertEqual(self.connector.get_name(), 'DHT11 Connector')

    def test_load_devices(self):
        self.assertEqual(len(self.connector.devices), 2)
        self.assertEqual(self.connector.devices[0]['name'], 'device1')
        self.assertEqual(self.connector.devices[0]['gpio'], 1)
        self.assertEqual(self.connector.devices[0]['interval'], 5)
        self.assertEqual(self.connector.devices[1]['name'], 'device2')
        self.assertEqual(self.connector.devices[1]['gpio'], 2)
        self.assertEqual(self.connector.devices[1]['interval'], 3)

    @patch('Adafruit_DHT.read_retry')
    def test_upload_data(self, mock_read_retry):
        mock_read_retry.return_value = (60, 25.5)
        self.connector._Dht11Connector__upload('device1', {'humidity': 60, 'temperature': 25.5})
        self.gateway.send_to_storage.assert_called_once_with(
            'DHT11 Connector',
            {
                'deviceName': 'device1', 
                'deviceType': 'thermometer',
                'telemetry': [
                    {'ts': unittest.mock.ANY, 'values': {'humidity': 60, 'temperature': 25.5}}
                ]
            }
        )

    def test_on_attributes_update(self):
        content = {'device': 'device1', 'data': {'reportInterval': 8000}}
        self.connector.on_attributes_update(content)
        self.assertEqual(self.connector.devices[0]['interval'], 8)

    def test_server_side_rpc(self):
        content = {'device': 'device1', 'data': {'id': 1, 'method': 'setInterval', 'params': {'interval': 7000}}}
        self.connector.server_side_rpc_handler(content)
        self.gateway.send_rpc_reply.assert_called_once_with('device1', 1, {'success': True})
        self.assertEqual(self.connector.devices[0]['interval'], 7)

if __name__ == '__main__':
    unittest.main()