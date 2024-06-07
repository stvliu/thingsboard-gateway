import logging
import struct
from thingsboard_gateway.connectors.ydt1363.exceptions import *
from thingsboard_gateway.connectors.ydt1363.constants import *

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# 帧编解码器        
class FrameCodec:
    @staticmethod
    def encode_frame(cid1, cid2, data, address=0x00):
        logger.debug(f"Building frame: cid1={cid1}, cid2={cid2}, data={data.hex() if data else None}")
        frame = bytearray()
        frame.extend(struct.pack('B', SOI))
        frame.extend(struct.pack('B', PROTOCOL_VERSION))
        frame.extend(struct.pack('B', address))
        frame.extend(bytes.fromhex(cid1[2:]))
        frame.extend(bytes.fromhex(cid2[2:]))
        frame.extend(FrameCodec._encode_length(len(data)))
        frame.extend(data)
        frame.extend(FrameCodec._calculate_checksum(frame[1:]))
        frame.extend(struct.pack('B', EOI))
        logger.debug(f"Built frame: {frame.hex()}")
        return bytes(frame)

    @staticmethod
    def decode_frame(frame):
        logger.debug(f"Parsing frame: {frame.hex()}")
        FrameCodec.validate_frame(frame)
        cid1 = f'0x{frame[CID1_INDEX]:02X}'
        logger.debug(f"cid1: {cid1}")
        cid2 = f'0x{frame[CID2_INDEX]:02X}'
        logger.debug(f"cid2: {cid2}")
        data_start = INFO_INDEX
        data_end = len(frame) + CHKSUM_INDEX
        data = frame[data_start:data_end]
        logger.debug(f"data: {data.hex()}")
        return cid1, cid2, data

    @staticmethod
    def validate_frame(frame):
        logger.debug(f"Validating frame: {frame.hex()} , length: {len(frame)}")
        #最小长度校验
        if len(frame) < MIN_FRAME_LENGTH:
            logger.warn(f"Frame too short: {len(frame)} bytes")
            raise RTNFormatError()
        if frame[SOI_INDEX] != SOI:
            logger.warn(f"Invalid start byte: {int.from_bytes(frame[SOI_INDEX:SOI_INDEX+1], 'big'):02X}")
            raise RTNFormatError()
        if frame[EOI_INDEX] != EOI:
            logger.warn(f"Invalid end byte: {int.from_bytes(frame[EOI_INDEX:EOI_INDEX+1], 'big'):02X}")
            raise RTNFormatError()
        if frame[VER_INDEX] != PROTOCOL_VERSION:  
            logger.warn(f"Version mismatch: expected {PROTOCOL_VERSION}, got {frame[VER_INDEX]}")
            raise RTNFormatError()
        
        #长度校验
        info_length = FrameCodec._decode_length(frame[LENGTH_INDEX:LENGTH_INDEX+DATA_LENGTH_LENGTH])
        expected_length = MIN_FRAME_LENGTH + info_length
        if len(frame) != expected_length:
            logger.warn(f"Frame length mismatch: expected {expected_length}, got {len(frame)}")
            raise RTNLchksumError()
    
        #校验和校验
        received_checksum = frame[CHKSUM_INDEX:CHKSUM_INDEX + CHECKSUM_LENGTH]
        calculated_checksum = FrameCodec._calculate_checksum(frame[VER_INDEX:CHKSUM_INDEX])
        if received_checksum != calculated_checksum:
            logger.warn(f"Checksum mismatch: expected {calculated_checksum.hex()}, got {received_checksum.hex()}")
            raise RTNChksumError()
        
    @staticmethod
    def _encode_length(length):
        logger.debug(f"Encoding length: {length}")
        # 编码数据长度  
        lenid_low = length & LENID_LOW_MASK
        lenid_high = (length >> 8) & LENID_HIGH_MASK
        lchksum = (lenid_low + lenid_high + length) % 16  
        lchksum = (~lchksum + 1) & 0x0F
        encoded_length = struct.pack('BB', (lchksum << LCHKSUM_SHIFT) | lenid_high, lenid_low)
        logger.debug(f"Encoded length: {encoded_length.hex()}")
        return encoded_length
    
    @staticmethod
    def _decode_length(length_bytes):
        logger.debug(f"Decoding length: {length_bytes.hex()}")
        lenid_low = length_bytes[1]  
        lenid_high = length_bytes[0] & LENID_HIGH_MASK
        lchksum = (length_bytes[0] >> LCHKSUM_SHIFT) & 0x0F
        
        lenid = (lenid_high << 8) | lenid_low
        
        calculated_lchksum = (lenid_low + lenid_high + lenid) % 16
        calculated_lchksum = (~calculated_lchksum + 1) & 0x0F
        if lchksum != calculated_lchksum:
            raise ProtocolError(f"Invalid LCHKSUM: received={lchksum:X}, calculated={calculated_lchksum:X}")
        logger.debug(f"Decoded length: {lenid}")
        return lenid
    
    @staticmethod
    def _calculate_checksum(data_for_checksum):
        logger.debug(f"Calculating checksum for data: {data_for_checksum.hex()}")
        checksum = sum(data_for_checksum) % 65536
        checksum = (~checksum + 1) & 0xFFFF
        checksum_bytes = struct.pack('>H', checksum)
        logger.debug(f"Calculated checksum: {checksum_bytes.hex()}")
        return checksum_bytes