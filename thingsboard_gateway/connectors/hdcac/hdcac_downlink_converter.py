from thingsboard_gateway.connectors.converter import Converter
from thingsboard_gateway.gateway.statistics_service import StatisticsService
from thingsboard_gateway.connectors.hdcac.hdcac_models import *
import datetime

class HdcAcDownlinkConverter(Converter):
    def __init__(self, config, log):
        self._config = config
        self._log = log

    @property
    def model_mapping(self):
        return {
            'remoteControl': RemoteControl,
            'getAcRunStatus': None,
            'getAcConfigParams': None,
            'setAcConfigParams': ConfigParam,
            'getDateTime': None,
            'setDateTime': DateTime,
            'setDeviceAddress': DeviceAddress
        }

    @StatisticsService.CollectStatistics(start_stat_type='allReceivedBytesFromTB',
                                         end_stat_type='allBytesSentToDevices')
    def convert(self, config, data):
        if config['key'] in self.model_mapping:
            model_class = self.model_mapping.get(config['key'])
            if model_class is None:
                return None
            if model_class:
                if data is None:
                    if config['key'].startswith('get'):
                        return None
                    else:
                        raise ValueError(f"Command {config['key']} requires parameters but got None")
                else:
                    return model_class.from_dict(data)
        else:
            self._log.error(f"Unknown command key: {config['key']}")
            raise Exception(f"Unknown command key: {config['key']}")