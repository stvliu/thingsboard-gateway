from abc import ABC, abstractmethod

class ProtocolBase(ABC):
    def __init__(self, config, device_addr, port, **kwargs):
        self._config = config
        self._device_addr = device_addr
        self._port = port
        for key, value in kwargs.items():
            setattr(self, f'_{key}', value)
    
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def is_connected(self):
        pass
    
    @abstractmethod
    def send_command(self, command_key, data=None):
        pass