import serial
import time
import logging
import threading

from exceptions import *
from constants import *
from frame_codec import *

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class SerialLink:
    def __init__(self, port, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None, reconnect_interval=1):
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.reconnect_interval = reconnect_interval
        self._serial = None
        self._send_lock = threading.Lock()  # 初始化发送锁
        self._receive_lock = threading.Lock()  # 初始化锁


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
            return
        except serial.SerialException as e:
            raise ConnectionError(f"Could not connect to serial port {self.port}")

    def is_connected(self):
        return self._serial and self._serial.is_open

    def disconnect(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
            logger.info(f"Disconnected from serial port {self.port}")

    def send_frame(self, frame):
        with self._send_lock:
            if not self.is_connected():
                self._reconnect()
            self._serial.write(frame)

    def receive_frame(self, timeout:float =1):
        with self._receive_lock:
            logger.debug(f"Receiving frame")
            self._serial.timeout = timeout
            retries = 0
            max_retries = 3
            while True:
                try:
                    soi = self._read_bytes(START_FLAG_LENGTH)
                    if len(soi) == 0:  # 超时,没有读取到数据
                        retries += 1
                        if retries >= max_retries:
                            raise FrameReceiveTimeoutError(timeout = timeout, attempts = retries)
                        else:
                            time.sleep(0.1)  # 等待一段时间再重试
                            continue

                    if soi[0] != SOI:
                        logger.warning(f"Invalid SOI: {soi.hex()}, discarding frame")
                        continue

                    header = self._read_bytes(ADDRESS_LENGTH + CONTROL_CODE_LENGTH)
                    if len(header) < ADDRESS_LENGTH + CONTROL_CODE_LENGTH:
                        logger.warning(f"Incomplete header: {header.hex()}, discarding frame")
                        continue

                    length = self._read_bytes(DATA_LENGTH_LENGTH)
                    if len(length) < DATA_LENGTH_LENGTH:
                        logger.warning(f"Incomplete LENGTH: {length.hex()}, discarding frame")
                        continue
                    try:
                        info_length = FrameCodec._decode_length(length)
                    except ProtocolError as e:
                        logger.warning(f"Error decoding frame length: {e}, discarding frame")
                        continue

                    info = self._read_bytes(info_length)
                    if len(info) < info_length:
                        logger.warning(f"Incomplete INFO: {info.hex()}, discarding frame")
                        continue

                    chksum = self._read_bytes(CHECKSUM_LENGTH)
                    if len(chksum) < CHECKSUM_LENGTH:
                        logger.warning(f"Incomplete CHKSUM: {chksum.hex()}, discarding frame")
                        continue

                    eoi = self._read_bytes(END_FLAG_LENGTH)
                    if len(eoi) == 0:
                        logger.warning("No EOI, discarding frame")
                        continue
                    if eoi[0] != EOI:
                        logger.warning(f"Invalid EOI: {eoi.hex()}, discarding frame")
                        continue

                    frame = soi + header + length + info + chksum + eoi

                    try:
                        FrameCodec.validate_frame(frame)
                    except ProtocolError as e:
                        logger.warning(f"Invalid frame: {e}, discarding frame")
                        continue

                    logger.debug(f"Received frame: {frame.hex()}")
                    return frame

                except serial.SerialException as e:
                    logger.error(f"Serial communication error: {e}")
                    self._reconnect()
                except FrameReceiveTimeoutError as e:
                    retries = 0
                    logger.debug(f"Frame receive timeout: {e}")
                except ProtocolError as e:
                    logger.warning(f"Protocol error: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error while receiving frame: {e}", exc_info=True)
                time.sleep(0.1)

    def _write_bytes(self, bytes):
        self._serial.write(bytes)

    def _read_bytes(self, size: int = 1):
        return self._serial.read(size)

    def _reconnect(self):
        logger.debug(f"Reconnecting to serial port {self.port}")
        self.disconnect()
        self.connect()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def _reconnect(self):
        logger.debug(f"Reconnecting to serial port {self.port}")
        self.disconnect()
        self.connect()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()