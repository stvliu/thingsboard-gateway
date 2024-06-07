import time
from thingsboard_gateway.gateway.statistics_service import StatisticsService

class Mu4801UplinkConverter:
    def __init__(self, config, log):
       self._config = config
       self._log = log

    @StatisticsService.CollectStatistics(start_stat_type='receivedBytesFromDevices',
                                         end_stat_type='convertedBytesFromDevice')
    def convert(self, config, data):
        result = {
            'deviceName': data['deviceName'], 
            'deviceType': data['deviceType'],
            'attributes': [{
                str(k): v
            } for k, v in data['attributes'].items()],
            'telemetry': [{
                'ts': int(time.time() * 1000),
                'values': data['telemetry']
            }]
        }
        return result