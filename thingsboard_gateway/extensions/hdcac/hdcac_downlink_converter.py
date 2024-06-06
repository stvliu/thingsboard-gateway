from thingsboard_gateway.connectors.converter import Converter
from thingsboard_gateway.gateway.statistics_service import StatisticsService
from thingsboard_gateway.extensions.hdcac.hdcac_models import *
import datetime

class HdcAcDownlinkConverter(Converter):
    def __init__(self, config, log):
        self._config = config
        self._log = log

    @StatisticsService.CollectStatistics(start_stat_type='allReceivedBytesFromTB',
                                         end_stat_type='allBytesSentToDevices')
    def convert(self, config, data):
        pass