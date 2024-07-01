from constants import *

# 异常类
class ProtocolError(Exception):
    """协议错误的基类"""
    pass

class RTNError(ProtocolError):
    """返回码错误的基类"""
    def __init__(self, code, message):
        self.code = code  # 错误码
        super().__init__(message)  # 错误信息

class RTNVerError(RTNError):
    """版本不匹配错误"""
    def __init__(self):
        super().__init__(RTN_VER_ERROR, "Version mismatch")

class RTNChksumError(RTNError):
    """校验和错误"""
    def __init__(self):
        super().__init__(RTN_CHKSUM_ERROR, "Checksum error")

class RTNLchksumError(RTNError):
    """长度校验和错误"""
    def __init__(self):
        super().__init__(RTN_LCHKSUM_ERROR, "Length checksum error")

class RTNCidError(RTNError):
    """无效的CID错误"""
    def __init__(self, cid1 = None, cid2 = None):
        super().__init__(RTN_CID2_INVALID, f"Invalid cid: cid1 = {cid1}, cid2 = {cid2}")

class RTNFormatError(RTNError):
    """命令格式错误"""
    def __init__(self):
        super().__init__(RTN_COMMAND_FORMAT_ERROR, "Format error")

class RTNDataError(RTNError):
    """无效数据错误"""
    def __init__(self):
        super().__init__(RTN_INVALID_DATA, "Invalid data")

class FrameReceiveTimeoutError(ProtocolError):
    """
    帧接收超时错误

    当在指定的超时时间内未能完全接收到一个有效的数据帧时抛出此异常。
    这可能是由于通信延迟、设备未响应或数据传输中断等原因导致的。
    """
    def __init__(self, timeout: float, attempts: int):
        self.timeout = timeout  # 总的超时时间
        self.attempts = attempts  # 尝试接收的次数
        message = f"Failed to receive complete frame after {attempts} attempts over {timeout} seconds"
        super().__init__(message)

