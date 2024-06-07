import serial
import logging
from exceptions import *
from constants import *
from frame_codec import *

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class SerialLink:
    def __init__(self, device_addr, port, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None):
        self.device_addr = device_addr
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self._serial = None

    def connect(self):
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout
            )
            self._serial.flushInput()
            self._serial.flushOutput()
            logger.info(f"Connected to serial port {self.port}")
        except serial.SerialException as e:
            logger.error(f"Failed to connect to serial port: {e}")
            raise ProtocolError(f"Serial connection failed: {e}")

    def is_connected(self):
        return self._serial and self._serial.is_open
    
    def disconnect(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
            logger.info(f"Disconnected from serial port {self.port}")

    def send_frame(self, frame):
        self._serial.write(frame)

    def receive_frame(self):
        logger.debug(f"Receiving frame")
        try:
            # Read SOI
            soi = self._serial.read(START_FLAG_LENGTH)
            if len(soi) == 0 or soi[0] != SOI:
                raise ProtocolError(f"Invalid SOI: {soi.hex()}")

            # Read VER, ADR, CID1, CID2
            header = self._serial.read(ADDRESS_LENGTH + CONTROL_CODE_LENGTH)
            if len(header) < ADDRESS_LENGTH + CONTROL_CODE_LENGTH:
                raise ProtocolError(f"Incomplete header: {header.hex()}")

            # Read LENGTH
            length = self._serial.read(DATA_LENGTH_LENGTH)
            if len(length) < DATA_LENGTH_LENGTH:
                raise ProtocolError(f"Incomplete LENGTH: {length.hex()}")
            info_length = FrameCodec._decode_length(length)

            # Read INFO
            info = self._serial.read(info_length)
            if len(info) < info_length:
                raise ProtocolError(f"Incomplete INFO: {info.hex()}")

            # Read CHKSUM
            chksum = self._serial.read(CHECKSUM_LENGTH)
            if len(chksum) < CHECKSUM_LENGTH:
                raise ProtocolError(f"Incomplete CHKSUM: {chksum.hex()}")

            # Read EOI
            eoi = self._serial.read(END_FLAG_LENGTH)
            if len(eoi) == 0 or eoi[0] != EOI:
                raise ProtocolError(f"Invalid EOI: {eoi.hex()}")

            # Assemble the frame
            frame = soi + header + length + info + chksum + eoi
            logger.debug(f"Received frame: {frame.hex()}")
            return frame

        except serial.SerialTimeoutException:
            raise ProtocolError("Timeout waiting for response")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()