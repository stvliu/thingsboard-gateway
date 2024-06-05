from thingsboard_gateway.connectors.converter import Converter
from thingsboard_gateway.gateway.statistics_service import StatisticsService
from thingsboard_gateway.extensions.mu4801.protocol.models import *
import datetime

class Mu4801DownlinkConverter(Converter):
    def __init__(self, connector, log):
        self.__connector = connector
        self._log = log

    @StatisticsService.CollectStatistics(start_stat_type='allReceivedBytesFromTB',
                                         end_stat_type='allBytesSentToDevices')
    def convert(self, config, data):
        converter_map = {
            'setAcConfigParams': self.__convert_ac_config_params,
            'setDateTime': self.__convert_date_time,
            'controlRectModule': self.__convert_control_rect_module,
            'setDcConfigParams': self.__convert_dc_config_params,
            'setSystemControlState': self.__convert_system_control_state,
            'setAlarmSoundEnable': self.__convert_alarm_sound_enable,
            'setEnergyParams': self.__convert_energy_params,
            'systemControl': self.__convert_system_control
        }

        converter_func = converter_map.get(config['key'], None)
        if converter_func:
            return converter_func(data)
        else:
            self._log.error(f"Unknown command key: {config['key']}")
            return None

    def __convert_ac_config_params(self, data):
        return AcConfigParams(
            ac_over_voltage=data.get('ac_over_voltage'),
            ac_under_voltage=data.get('ac_under_voltage')
        )

    def __convert_date_time(self, data):
        dt = datetime.datetime.fromisoformat(data.get('dateTime'))
        return DateTime(
            year=dt.year,
            month=dt.month,
            day=dt.day,
            hour=dt.hour,
            minute=dt.minute,
            second=dt.second
        )

    def __convert_control_rect_module(self, data):
        return ControlRectModule(
            module_id=data.get('module_id'),
            control_type=RectModuleControlType(data.get('control_type')),
            control_value=data.get('control_value', 0)
        )

    def __convert_dc_config_params(self, data):
        return DcConfigParams(
            dc_over_voltage=data.get('dc_over_voltage'),
            dc_under_voltage=data.get('dc_under_voltage'),
            time_equalize_charge_enable=EnableStatus(data.get('time_equalize_charge_enable')),
            time_equalize_duration=data.get('time_equalize_duration'),
            time_equalize_interval=data.get('time_equalize_interval'),
            battery_group_number=data.get('battery_group_number', 1),
            battery_over_temp=data.get('battery_over_temp'),
            battery_under_temp=data.get('battery_under_temp'),
            env_over_temp=data.get('env_over_temp'),
            env_under_temp=data.get('env_under_temp'),
            env_over_humidity=data.get('env_over_humidity'),
            battery_charge_current_limit=data.get('battery_charge_current_limit'),
            float_voltage=data.get('float_voltage'),
            equalize_voltage=data.get('equalize_voltage'),
            battery_off_voltage=data.get('battery_off_voltage'),
            battery_on_voltage=data.get('battery_on_voltage'),
            llvd1_off_voltage=data.get('llvd1_off_voltage'),
            llvd1_on_voltage=data.get('llvd1_on_voltage'),
            llvd2_off_voltage=data.get('llvd2_off_voltage'),
            llvd2_on_voltage=data.get('llvd2_on_voltage'),
            llvd3_off_voltage=data.get('llvd3_off_voltage'),
            llvd3_on_voltage=data.get('llvd3_on_voltage'),
            llvd4_off_voltage=data.get('llvd4_off_voltage'),
            llvd4_on_voltage=data.get('llvd4_on_voltage'),
            battery_capacity=data.get('battery_capacity'),
            battery_test_stop_voltage=data.get('battery_test_stop_voltage'),
            battery_temp_coeff=data.get('battery_temp_coeff'),
            battery_temp_center=data.get('battery_temp_center'),
            float_to_equalize_coeff=data.get('float_to_equalize_coeff'),
            equalize_to_float_coeff=data.get('equalize_to_float_coeff'),
            llvd1_off_time=data.get('llvd1_off_time'),
            llvd2_off_time=data.get('llvd2_off_time'),
            llvd3_off_time=data.get('llvd3_off_time'),
            llvd4_off_time=data.get('llvd4_off_time'),
            load_off_mode=LoadOffMode(data.get('load_off_mode'))
        )
        
    def __convert_system_control_state(self, data):
        return SystemControlState(state=SystemControlState(data.get('state')))
    
    def __convert_alarm_sound_enable(self, data):
        return AlarmSoundEnable(enable=EnableStatus(data.get('enable')))
    
    def __convert_energy_params(self, data):
        return EnergyParams(
            energy_saving=EnableStatus(data.get('energy_saving')),
            min_working_modules=data.get('min_working_modules'),
            module_switch_cycle=data.get('module_switch_cycle'),
            module_best_efficiency_point=data.get('module_best_efficiency_point'),
            module_redundancy_point=data.get('module_redundancy_point')
        )
        
    def __convert_system_control(self, data):
        return SystemControl(control_type=SystemControlType(data.get('control_type')))