from .CEnum import BI_DIR, KL_TYPE


def kltype_lt_day(_type: KL_TYPE):
    return _type.value < KL_TYPE.K_DAY.value


def kltype_lte_day(_type: KL_TYPE):
    return _type.value <= KL_TYPE.K_DAY.value


def check_kltype_order(type_list):
    last_lv = type_list[0].value
    for kl_type in type_list[1:]:
        assert kl_type.value < last_lv, "lv_list的顺序必须从大级别到小级别"
        last_lv = kl_type.value


def revert_bi_dir(dir):
    return BI_DIR.DOWN if dir == BI_DIR.UP else BI_DIR.UP


def has_overlap(l1, h1, l2, h2, equal=False):
    return h2 >= l1 and h1 >= l2 if equal else h2 > l1 and h1 > l2


def str2float(s):
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_inf(v):
    if isinstance(v, float):
        if v == float("inf"):
            v = 'float("inf")'
        if v == float("-inf"):
            v = 'float("-inf")'
    return v
