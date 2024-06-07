from constants import *

# 异常类
class ProtocolError(Exception):
    pass

class RTNError(ProtocolError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)

class RTNVerError(RTNError):
    def __init__(self):
        super().__init__(RTN_VER_ERROR, "Version mismatch")

class RTNChksumError(RTNError):
    def __init__(self):
        super().__init__(RTN_CHKSUM_ERROR, "Checksum error")

class RTNLchksumError(RTNError):
    def __init__(self):
        super().__init__(RTN_LCHKSUM_ERROR, "Length checksum error")

class RTNCidError(RTNError):
    def __init__(self, cid1 = None, cid2 = None):
        super().__init__(RTN_CID2_INVALID, f"Invalid cid: cid1 = {cid1},cid2 = {cid2}")

class RTNFormatError(RTNError):
    def __init__(self):
        super().__init__(RTN_COMMAND_FORMAT_ERROR, "Format error")

class RTNDataError(RTNError):
    def __init__(self):
        super().__init__(RTN_INVALID_DATA, "Invalid data")