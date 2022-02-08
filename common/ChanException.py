from enum import IntEnum


class ErrCode(IntEnum):
    # chan err
    _CHAN_ERR_BEGIN = 0
    COMMON_ERROR = 1
    NO_DATA = 2
    SRC_DATA_NOT_FOUND = 3
    SRC_DATA_TYPE_ERR = 4
    PARA_ERROR = 5
    EXTRA_KLU_ERR = 6
    SEG_END_VALUE_ERR = 7
    _CHAN_ERR_END = 99

    # Trade Error
    _TRADE_ERR_BEGIN = 100
    RECORD_EXISTED = 101
    RECORD_NOT_EXIST = 102
    RECORD_ALREADY_OPENED = 103
    QUOTA_NOT_ENOUGH = 104
    RECORD_NOT_OPENED = 105
    TRADE_UNLOCK_FAIL = 105
    PLACE_ORDER_FAIL = 107
    LIST_ORDER_FAIL = 108
    CANDEL_ORDER_FAIL = 109
    GET_FUTU_PRICE_FAIL = 110
    GET_FUTU_LOT_SIZE_FAIL = 111
    _TRADE_ERR_END = 199

    # KL data Error
    _KL_ERR_BEGIN = 200
    PRICE_BELOW_ZERO = 201
    KL_DATA_NOT_ALIGN = 202
    KL_DATA_INVALID = 203
    KL_TIME_INCONSISTENT = 204
    TRADEINFO_TOO_MUCH_ZERO = 205
    KL_NOT_MONOTONOUS = 206
    _KL_ERR_END = 299


class CChanException(Exception):
    def __init__(self, message, code=ErrCode.COMMON_ERROR):
        self.errcode = int(code)
        self.s_errcode = code
        Exception.__init__(self, message)

    def is_kldata_err(self):
        return ErrCode._KL_ERR_BEGIN < self.errcode < ErrCode._KL_ERR_END
