from thingsboard_gateway.connectors.converter import Converter
from thingsboard_gateway.gateway.statistics_service import StatisticsService
from thingsboard_gateway.connectors.mu4801.mu4801_models import *
import datetime

class Mu4801DownlinkConverter(Converter):
    def __init__(self, config, log):
        self._config = config
        self._log = log

    @property
    def model_mapping(self):
        return {
            'setAcConfigParams': AcConfigParams,
            'setDateTime': DateTime,
            'controlRectModule': ControlRectModule,
            'setDcConfigParams': DcConfigParams,
            'setSystemControlState': SystemControlState,
            'setAlarmSoundEnable': AlarmSoundEnable,
            'setEnergyParams': EnergyParams,
            'getEnergyParams': None,
            'systemControl': SystemControl
        }

    @StatisticsService.CollectStatistics(start_stat_type='allReceivedBytesFromTB',
                                         end_stat_type='allBytesSentToDevices')
    def convert(self, config, data):
        if self.model_mapping.has_key(config['key']):
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