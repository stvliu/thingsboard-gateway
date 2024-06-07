import serial
import time
import logging
from thingsboard_gateway.connectors.ydt1363.exceptions import *
from thingsboard_gateway.connectors.ydt1363.constants import *
from thingsboard_gateway.connectors.ydt1363.frame_codec import *

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class SerialLink:
    def __init__(self, port, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None, max_reconnect_attempts=5, reconnect_interval=1):
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_interval = reconnect_interval
        self._serial = None

    def connect(self):
        attempt_count = 0
        while attempt_count < self.max_reconnect_attempts:
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
                attempt_count += 1
                logger.error(f"Failed to connect to serial port (attempt {attempt_count}/{self.max_reconnect_attempts}): {e}")
                time.sleep(self.reconnect_interval)
        
        raise ConnectionError(f"Could not connect to serial port {self.port} after {self.max_reconnect_attempts} attempts")

    def is_connected(self):
        return self._serial and self._serial.is_open
    
    def disconnect(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
            logger.info(f"Disconnected from serial port {self.port}")

    def send_frame(self, frame):
        try: 
            self._serial.write(frame)
        except serial.SerialException as e:
            logger.error(f"Failed to send frame: {e}")
            self.disconnect()
            self.connect()
            self._serial.write(frame)

    # def receive_frame(self):
    #     logger.debug(f"Receiving frame")
    #     try:
    #         # Read SOI
    #         soi = self._serial.read(START_FLAG_LENGTH)
    #         if len(soi) == 0 or soi[0] != SOI:
    #             raise ProtocolError(f"Invalid SOI: {soi.hex()}")

    #         # Read VER, ADR, CID1, CID2
    #         header = self._serial.read(ADDRESS_LENGTH + CONTROL_CODE_LENGTH)
    #         if len(header) < ADDRESS_LENGTH + CONTROL_CODE_LENGTH:
    #             raise ProtocolError(f"Incomplete header: {header.hex()}")

    #         # Read LENGTH
    #         length = self._serial.read(DATA_LENGTH_LENGTH)
    #         if len(length) < DATA_LENGTH_LENGTH:
    #             raise ProtocolError(f"Incomplete LENGTH: {length.hex()}")
    #         info_length = FrameCodec._decode_length(length)

    #         # Read INFO
    #         info = self._serial.read(info_length)
    #         if len(info) < info_length:
    #             raise ProtocolError(f"Incomplete INFO: {info.hex()}")

    #         # Read CHKSUM
    #         chksum = self._serial.read(CHECKSUM_LENGTH)
    #         if len(chksum) < CHECKSUM_LENGTH:
    #             raise ProtocolError(f"Incomplete CHKSUM: {chksum.hex()}")

    #         # Read EOI
    #         eoi = self._serial.read(END_FLAG_LENGTH)
    #         if len(eoi) == 0 or eoi[0] != EOI:
    #             raise ProtocolError(f"Invalid EOI: {eoi.hex()}")

    #         # Assemble the frame
    #         frame = soi + header + length + info + chksum + eoi
    #         logger.debug(f"Received frame: {frame.hex()}")
    #         return frame

    #     except serial.SerialTimeoutException:
    #         raise ProtocolError("Timeout waiting for response")

    def receive_frame(self, timeout:float =1):
        logger.debug(f"Receiving frame")
        
        # 设置串口读取超时时间
        self._serial.timeout = timeout
        
        while True:
            try:
                # Read SOI
                soi = self._serial.read(START_FLAG_LENGTH)
                if len(soi) == 0:  # 超时,没有读取到数据
                    continue
                if soi[0] != SOI:
                    logger.warning(f"Invalid SOI: {soi.hex()}, discarding frame")
                    continue
                
                # Read VER, ADR, CID1, CID2
                header = self._serial.read(ADDRESS_LENGTH + CONTROL_CODE_LENGTH)
                if len(header) < ADDRESS_LENGTH + CONTROL_CODE_LENGTH:
                    logger.warning(f"Incomplete header: {header.hex()}, discarding frame")
                    continue
                
                # Read LENGTH
                length = self._serial.read(DATA_LENGTH_LENGTH)
                if len(length) < DATA_LENGTH_LENGTH:
                    logger.warning(f"Incomplete LENGTH: {length.hex()}, discarding frame")
                    continue
                info_length = FrameCodec._decode_length(length)
                
                # Read INFO
                info = self._serial.read(info_length)
                if len(info) < info_length:
                    logger.warning(f"Incomplete INFO: {info.hex()}, discarding frame")
                    continue
                
                # Read CHKSUM
                chksum = self._serial.read(CHECKSUM_LENGTH)
                if len(chksum) < CHECKSUM_LENGTH:
                    logger.warning(f"Incomplete CHKSUM: {chksum.hex()}, discarding frame")
                    continue
                
                # Read EOI
                eoi = self._serial.read(END_FLAG_LENGTH)
                if len(eoi) == 0:
                    logger.warning("No EOI, discarding frame")
                    continue
                if eoi[0] != EOI:
                    logger.warning(f"Invalid EOI: {eoi.hex()}, discarding frame")
                    continue
                
                # Assemble the frame
                frame = soi + header + length + info + chksum + eoi
                
                # Verify frame integrity
                # if not FrameCodec.verify_frame(frame):
                #     logger.warning(f"Invalid frame: {frame.hex()}, discarding")
                #     continue
                
                logger.debug(f"Received frame: {frame.hex()}")
                return frame
            
            except serial.SerialException as e:
                logger.error(f"Serial communication error: {e}")
                raise ConnectionError(f"Serial communication failed: {e}") from e
            
            except Exception as e:
                logger.error(f"Unexpected error while receiving frame: {e}", exc_info=True)
                raise

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()