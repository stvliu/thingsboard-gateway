from thingsboard_gateway.gateway.statistics_service import StatisticsService

class Mu4801UplinkConverter:
    def __init__(self, connector, log):
       self.__connector = connector
       self._log = log

    @StatisticsService.CollectStatistics(start_stat_type='receivedBytesFromDevices',
                                         end_stat_type='convertedBytesFromDevice')
    def convert(self, config, data):
        if data:
            return data.to_dict()
        return {} 