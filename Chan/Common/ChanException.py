from enum import IntEnum


class ErrCode(IntEnum):
    # chan err
    _CHAN_ERR_BEGIN = 0
    COMMON_ERROR = 1
    SRC_DATA_NOT_FOUND = 3
    SRC_DATA_TYPE_ERR = 4
    PARA_ERROR = 5
    EXTRA_KLU_ERR = 6
    SEG_END_VALUE_ERR = 7
    SEG_EIGEN_ERR = 8
    BI_ERR = 9
    COMBINER_ERR = 10
    PLOT_ERR = 11
    MODEL_ERROR = 12
    SEG_LEN_ERR = 13
    ENV_CONF_ERR = 14
    UNKNOWN_DB_TYPE = 15
    FEATURE_ERROR = 16
    CONFIG_ERROR = 17
    SRC_DATA_FORMAT_ERROR = 18
    _CHAN_ERR_END = 99

    # Trade Error
    _TRADE_ERR_BEGIN = 100
    SIGNAL_EXISTED = 101
    RECORD_NOT_EXIST = 102
    RECORD_ALREADY_OPENED = 103
    QUOTA_NOT_ENOUGH = 104
    RECORD_NOT_OPENED = 105
    TRADE_UNLOCK_FAIL = 106
    PLACE_ORDER_FAIL = 107
    LIST_ORDER_FAIL = 108
    CANDEL_ORDER_FAIL = 109
    GET_FUTU_PRICE_FAIL = 110
    GET_FUTU_LOT_SIZE_FAIL = 111
    OPEN_RECORD_NOT_WATCHING = 112
    GET_HOLDING_QTY_FAIL = 113
    RECORD_CLOSED = 114
    REQUEST_TRADING_DAYS_FAIL = 115
    COVER_ORDER_ID_NOT_UNIQUE = 116
    SIGNAL_TRADED = 117
    _TRADE_ERR_END = 199

    # KL data Error
    _KL_ERR_BEGIN = 200
    PRICE_BELOW_ZERO = 201
    KL_DATA_NOT_ALIGN = 202
    KL_DATA_INVALID = 203
    KL_TIME_INCONSISTENT = 204
    TRADEINFO_TOO_MUCH_ZERO = 205
    KL_NOT_MONOTONOUS = 206
    SNAPSHOT_ERR = 207
    SUSPENSION = 208  # 疑似停牌
    STOCK_IPO_TOO_LATE = 209
    NO_DATA = 210
    STOCK_NOT_ACTIVE = 211
    STOCK_PRICE_NOT_ACTIVE = 212
    _KL_ERR_END = 299


class CChanException(Exception):
    def __init__(self, message, code=ErrCode.COMMON_ERROR):
        self.errcode = code
        self.msg = message
        Exception.__init__(self, message)

    def is_kldata_err(self):
        return ErrCode._KL_ERR_BEGIN < self.errcode < ErrCode._KL_ERR_END

    def is_chan_err(self):
        return ErrCode._CHAN_ERR_BEGIN < self.errcode < ErrCode._CHAN_ERR_END


if __name__ == "__main__":
    def foo():
        raise CChanException("XXX", ErrCode.CONFIG_ERROR)

    try:
        foo()
    except CChanException as e:
        print(str(e.errcode))
        # python3.8 结果为： ErrCode.CONFIG_ERROR
        # python3.11 结果为：17

        print(e.errcode.name, type(e.errcode.name))
