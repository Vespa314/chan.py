from enum import IntEnum


class ErrCode(IntEnum):
    COMMON_ERROR = 1
    KL_DATA_NOT_ALIGN = 2
    RECORD_EXISTED = 3
    RECORD_NOT_EXIST = 4
    RECORD_ALREADY_OPENED = 5
    QUOTA_NOT_ENOUGH = 6
    RECORD_NOT_OPENED = 7
    TRADE_UNLOCK_FAIL = 8
    PLACE_ORDER_FAIL = 9
    LIST_ORDER_FAIL = 10
    CANDEL_ORDER_FAIL = 11
    PARA_ERROR = 10000


class CChanException(Exception):
    def __init__(self, message, code=ErrCode.COMMON_ERROR):
        self.errcode = int(code)
        Exception.__init__(self, message)
