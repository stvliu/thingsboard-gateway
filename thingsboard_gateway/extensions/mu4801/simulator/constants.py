# 常量定义
SOI = 0x7E
EOI = 0x0D
PROTOCOL_VERSION = 0x21
# 帧结构中各字段的索引
SOI_INDEX = 0  # SOI字段的索引
VER_INDEX = 1  # 版本号字段的索引 
ADR_INDEX = 2  # 设备地址字段的索引
CID1_INDEX = 3  # 设备类型标识字段的索引
CID2_INDEX = 4  # 控制标识字段的索引
LENGTH_INDEX = 5  # 数据长度字段的索引
INFO_INDEX = 7  # 数据信息字段的索引
CHKSUM_INDEX = -3  # 校验和字段的索引
EOI_INDEX = -1  # EOI字段的索引

START_FLAG_LENGTH = 1  # 起始标志(lSTX)的长度
ADDRESS_LENGTH = 2     # 设备地址(lADDR)的长度
CONTROL_CODE_LENGTH = 2  # 控制码(lCTRL1, lCTRL2)的长度
DATA_LENGTH_LENGTH = 2   # 数据长度(lLENL, lLENH)的长度
CHECKSUM_LENGTH = 2      # 校验码(lCHKSUM)的长度
END_FLAG_LENGTH = 1      # 结束标志(lETX)的长度
MIN_FRAME_LENGTH = (     # 最小帧长度
        START_FLAG_LENGTH +
        ADDRESS_LENGTH +
        CONTROL_CODE_LENGTH +
        DATA_LENGTH_LENGTH +
        CHECKSUM_LENGTH +
        END_FLAG_LENGTH
    )

# 帧长度编码常量
LENID_ZERO = 0  # 长度标识为0,表示数据字段为空
LENID_LOW_MASK = 0xFF  # 长度标识低字节掩码
LENID_HIGH_MASK = 0x0F  # 长度标识高字节掩码  
LCHKSUM_MASK = 0xF0  # 长度校验和掩码
LCHKSUM_SHIFT = 4  # 长度校验和在字节中的偏移量

# 返回码(RTN)常量
RTN_OK = 0x00  # 正常
RTN_VER_ERROR = 0x01  # VER错
RTN_CHKSUM_ERROR = 0x02  # CHKSUM错
RTN_LCHKSUM_ERROR = 0x03  # LCHKSUM错
RTN_CID2_INVALID = 0x04  # CID2无效
RTN_COMMAND_FORMAT_ERROR = 0x05  # 命令格式错
RTN_INVALID_DATA = 0x06  # 无效数据
RTN_USER_DEFINED_ERROR_START = 0x80  # 用户自定义错误码起始值
RTN_USER_DEFINED_ERROR_END = 0xEF  # 用户自定义错误码结束值