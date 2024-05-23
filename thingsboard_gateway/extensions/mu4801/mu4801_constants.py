# 帧结构常量
SOI = 0x7E  # 起始位标志(Start Of Information)
EOI = 0x0D  # 结束码(End Of Information)
PROTOCOL_VERSION = 0x21  # 协议版本号

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

# 帧长度编码常量
LENID_ZERO = 0  # 长度标识为0,表示数据字段为空
LENID_LOW_MASK = 0xFF  # 长度标识低字节掩码
LENID_HIGH_MASK = 0x0F  # 长度标识高字节掩码
LCHKSUM_MASK = 0xF0  # 长度校验和掩码
LCHKSUM_SHIFT = 4  # 长度校验和在字节中的偏移量

# 设备类型编码(CID1)
CID1_DC_POWER = 0x40  # 开关电源系统(交流配电)
CID1_RECT = 0x41  # 开关电源系统(整流器)
CID1_DC_DIST = 0x42  # 开关电源系统(直流配电)
CID1_SYS_CONTROL = 0x80  # 系统控制

# 控制标识编码(CID2)
CID2_GET_ANALOG_FLOAT = 0x41  # 获取模拟量(浮点数)
CID2_GET_ALARM = 0x44  # 获取告警状态
CID2_CONTROL = 0x45  # 遥控
CID2_GET_STATUS = 0x43  # 获取开关输入状态
CID2_GET_CONFIG_FLOAT = 0x46  # 获取配置参数(浮点数)
CID2_SET_CONFIG_FLOAT = 0x48  # 设置配置参数(浮点数)
CID2_REMOTE_SET_FLOAT = 0x80  # 遥调设定值(浮点数)
CID2_GET_TIME = 0x4D  # 获取时间
CID2_SET_TIME = 0x4E  # 设置时间
CID2_GET_VERSION = 0x4F  # 获取协议版本号
CID2_GET_ADDR = 0x50  # 获取设备地址
CID2_GET_MFR_INFO = 0x51  # 获取制造商信息
CID2_CONTROL_SYSTEM = 0x92  # 系统控制命令
CID2_GET_SYS_STATUS = 0x81  # 获取系统状态
CID2_SET_SYS_STATUS = 0x80  # 设置系统状态
CID2_BUZZER_CONTROL = 0x84  # 蜂鸣器控制
CID2_GET_POWER_SAVING = 0x90  # 获取节能参数
CID2_SET_POWER_SAVING = 0x91  # 设置节能参数