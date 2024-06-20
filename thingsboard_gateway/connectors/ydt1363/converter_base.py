from thingsboard_gateway.gateway.statistics_service import StatisticsService

class ConverterBase:
    @StatisticsService.CollectStatistics(start_stat_type='allReceivedBytesFromTB',
                                         end_stat_type='allBytesSentToDevices')
    def convert(self, config, data):
        raise NotImplementedError