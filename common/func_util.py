from .CEnum import KL_TYPE, BI_DIR
from common.ChanException import CChanException, ErrCode
from KLine.CKline_Unit import KLine_Unit


def kltype_lt_day(_type):
    return _type in [KL_TYPE.K_1M, KL_TYPE.K_5M, KL_TYPE.K_15M, KL_TYPE.K_30M, KL_TYPE.K_60M]


def kltype_lte_day(_type):
    return _type in [KL_TYPE.K_1M, KL_TYPE.K_5M, KL_TYPE.K_15M, KL_TYPE.K_30M, KL_TYPE.K_60M, KL_TYPE.K_DAY]


def check_kltype_order(type_list: list):
    _dict = {
        KL_TYPE.K_1M: 1,
        KL_TYPE.K_3M: 2,
        KL_TYPE.K_5M: 3,
        KL_TYPE.K_15M: 4,
        KL_TYPE.K_30M: 5,
        KL_TYPE.K_60M: 6,
        KL_TYPE.K_DAY: 7,
        KL_TYPE.K_WEEK: 8,
        KL_TYPE.K_MON: 9,
        KL_TYPE.K_QUARTER: 10,
        KL_TYPE.K_YEAR: 11,
    }
    last_lv = float("inf")
    for kl_type in type_list:
        cur_lv = _dict[kl_type]
        assert cur_lv < last_lv, "lv_list的顺序必须从大级别到小级别"
        last_lv = cur_lv


def revert_bi_dir(dir):
    if dir == BI_DIR.UP:
        return BI_DIR.DOWN
    else:
        return BI_DIR.UP


def has_overlap(l1, h1, l2, h2, equal=False):
    if equal:
        return h2 >= l1 and h1 >= l2
    else:
        return h2 > l1 and h1 > l2


def str2float(s):
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_extrainfo_kl(extrainfo_kl, lv_list):
    if extrainfo_kl is None:
        return None
    if type(extrainfo_kl) == list:
        if len(lv_list) != 1:
            raise CChanException("extrainfo_kl can't be a list in multi levels", ErrCode.EXTRA_KLU_ERR)
        return {lv_list[0]: extrainfo_kl}
    for kl_type, data in extrainfo_kl.items():
        if kl_type not in lv_list:
            raise CChanException(f"extrainfo_kl keys {kl_type} is not in lv_list={lv_list}", ErrCode.EXTRA_KLU_ERR)
        if type(data) != list:
            raise CChanException(f"extrainfo_kl values must be as list but not {type(data)}", ErrCode.EXTRA_KLU_ERR)
        for idx, klu in enumerate(data):
            if type(klu) != KLine_Unit:
                raise CChanException(f"extrainfo_kl[{kl_type}][{idx}]'s type must be KLine_Unit, but not {type(klu)}", ErrCode.EXTRA_KLU_ERR)
    return extrainfo_kl
