import struct
from abc import ABC, abstractmethod

class Codec(ABC):
    @abstractmethod
    def encode(self, data):
        pass

    @abstractmethod
    def decode(self, bytes):
        pass

class IntegerCodec(Codec):
    def encode(self, data):
        return struct.pack('<i', data)

    def decode(self, bytes):
        return struct.unpack('<i', bytes)[0]

class FloatCodec(Codec):
    def encode(self, data):
        return struct.pack('<f', data)

    def decode(self, bytes):
        return struct.unpack('<f', bytes)[0]

class StringCodec(Codec):
    def encode(self, data):
        return data.encode('ascii')

    def decode(self, bytes):
        return bytes.decode('ascii')

class DataCodec:
    def __init__(self):
        self.codecs = {
            int: IntegerCodec(),
            float: FloatCodec(),
            str: StringCodec(),
        }

    def encode(self, data):
        codec = self.codecs.get(type(data))
        if codec:
            return codec.encode(data)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

    def decode(self, bytes, data_type):
        codec = self.codecs.get(data_type)
        if codec:
            return codec.decode(bytes)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")