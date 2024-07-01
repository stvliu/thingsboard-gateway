import serial
import time
import logging
import threading

from thingsboard_gateway.connectors.ydt1363.exceptions import *
from thingsboard_gateway.connectors.ydt1363.constants import *
from thingsboard_gateway.connectors.ydt1363.frame_codec import *

# 配置日志记录
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class SerialLink:
    """
    SerialLink类用于管理与串行端口的连接和通信。
    它提供了连接、断开连接、发送和接收数据帧的方法。
    """

    def __init__(self, port, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE, timeout=None, reconnect_interval=1):
        """
        初始化SerialLink对象。

        :param port: 串行端口名称
        :param baudrate: 波特率
        :param bytesize: 数据位
        :param parity: 校验位
        :param stopbits: 停止位
        :param timeout: 超时时间
        :param reconnect_interval: 重连间隔时间
        """
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.reconnect_interval = reconnect_interval
        self._serial = None
        self._send_lock = threading.Lock()  # 初始化发送锁
        self._receive_lock = threading.Lock()  # 初始化接收锁
        self._max_retries = 3  # 最大重连次数

    def connect(self):
        """
        建立与串行端口的连接。
        如果连接失败,会抛出ConnectionError异常。
        """
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout
            )
            self._serial.flushInput()  # 清空输入缓冲区
            self._serial.flushOutput()  # 清空输出缓冲区
            logger.info(f"Connected to serial port {self.port}")
            return
        except serial.SerialException as e:
            raise ConnectionError(f"Could not connect to serial port {self.port}")

    def is_connected(self):
        """
        检查是否已连接到串行端口。

        :return: 如果已连接则返回True,否则返回False
        """
        return self._serial and self._serial.is_open

    def disconnect(self):
        """
        断开与串行端口的连接。
        """
        if self._serial and self._serial.is_open:
            self._serial.close()
            logger.info(f"Disconnected from serial port {self.port}")

    def send_frame(self, frame):
        """
        发送数据帧。

        :param frame: 要发送的数据帧
        """
        with self._send_lock:  # 使用锁确保线程安全
            for attempt in range(self._max_retries):
                try:
                    if not self.is_connected():
                        self.connect()
                    self._serial.write(frame)
                    return
                except (serial.SerialException, OSError) as e:
                    logger.error(f"Send attempt {attempt + 1} failed: {e}")
                    self.disconnect()
                    if attempt < self._max_retries - 1:
                        time.sleep(self.reconnect_interval)
                    else:
                        raise CommunicationError(f"Failed to send frame after {self._max_retries} attempts")

    def receive_frame(self, timeout:float =1):
        """
        接收数据帧。

        :param timeout: 接收超时时间
        :return: 接收到的数据帧
        """
        with self._receive_lock:  # 使用锁确保线程安全
            logger.debug(f"Receiving frame")
            self._serial.timeout = timeout
            retries = 0
            while True:
                try:
                    # 读取起始标志(SOI)
                    soi = self._read_bytes(START_FLAG_LENGTH)
                    if len(soi) == 0:  # 超时,没有读取到数据
                        retries += 1
                        if retries >= self._max_retries:
                            raise CommunicationError(f"Failed to receive frame after {self._max_retries} attempts")
                        else:
                            time.sleep(0.1)  # 等待一段时间再重试
                            continue

                    if soi[0] != SOI:
                        logger.warning(f"Invalid SOI: {soi.hex()}, discarding frame")
                        continue

                    # 读取帧头
                    header = self._read_bytes(ADDRESS_LENGTH + CONTROL_CODE_LENGTH)
                    if len(header) < ADDRESS_LENGTH + CONTROL_CODE_LENGTH:
                        logger.warning(f"Incomplete header: {header.hex()}, discarding frame")
                        continue

                    # 读取长度字段
                    length = self._read_bytes(DATA_LENGTH_LENGTH)
                    if len(length) < DATA_LENGTH_LENGTH:
                        logger.warning(f"Incomplete LENGTH: {length.hex()}, discarding frame")
                        continue
                    try:
                        info_length = FrameCodec._decode_length(length)
                    except ProtocolError as e:
                        logger.warning(f"Error decoding frame length: {e}, discarding frame")
                        continue

                    # 读取信息字段
                    info = self._read_bytes(info_length)
                    if len(info) < info_length:
                        logger.warning(f"Incomplete INFO: {info.hex()}, discarding frame")
                        continue

                    # 读取校验和
                    chksum = self._read_bytes(CHECKSUM_LENGTH)
                    if len(chksum) < CHECKSUM_LENGTH:
                        logger.warning(f"Incomplete CHKSUM: {chksum.hex()}, discarding frame")
                        continue

                    # 读取结束标志(EOI)
                    eoi = self._read_bytes(END_FLAG_LENGTH)
                    if len(eoi) == 0:
                        logger.warning("No EOI, discarding frame")
                        continue
                    if eoi[0] != EOI:
                        logger.warning(f"Invalid EOI: {eoi.hex()}, discarding frame")
                        continue

                    # 组装完整的帧
                    frame = soi + header + length + info + chksum + eoi

                    # 验证帧的有效性
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
                except CommunicationError as e:
                    retries = 0
                    logger.debug(f"Frame receive timeout: {e}")
                except ProtocolError as e:
                    logger.warning(f"Protocol error: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error while receiving frame: {e}", exc_info=True)
                time.sleep(0.1)

    def _write_bytes(self, bytes):
        """
        向串行端口写入字节数据。

        :param bytes: 要写入的字节数据
        """
        self._serial.write(bytes)

    def _read_bytes(self, size: int = 1):
        """
        从串行端口读取指定数量的字节。

        :param size: 要读取的字节数. 默认为1
        :return: 读取到的字节数据
        """
        return self._serial.read(size)

    def _reconnect(self):
        """
        重新连接串行端口。
        """
        logger.debug(f"Reconnecting to serial port {self.port}")
        self.disconnect()
        self.connect()

    def __enter__(self):
        """
        上下文管理器的进入方法。
        在进入 with 语句块时调用,建立连接。

        :return: SerialLink对象自身
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器的退出方法。
        在离开 with 语句块时调用,断开连接。

        :param exc_type: 异常类型
        :param exc_val: 异常值
        :param exc_tb: 异常追踪信息
        """
        self.disconnect()