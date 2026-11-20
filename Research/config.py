"""研究参数。买卖点候选故意放宽，严格一类只作为对照，不作为唯一训练集。"""

from __future__ import annotations

# 三屏障。主标签用固定幅度；中枢高度的 2 倍另做稳健性标签。
UPPER_RETURN = 0.08
LOWER_RETURN = 0.04
ZS_UPPER_MULT = 2.0
HORIZON_PRIMARY = 10
HORIZON_SENSITIVITY = 20
# 单边成本（佣金 + 滑点的保守合计）。往返扣两次。
SIDE_COST = 0.001

# demo1 的严格一类门槛，用决策当时的背驰比和多笔中枢个数重建，不再跑第二遍引擎。
STRICT_DIVERGENCE = 0.8
STRICT_MIN_ZS = 1

EMBARGO_DAYS = HORIZON_SENSITIVITY
MAX_POSITIONS = 10
VOLUME_WINDOW = 20

# 验证段上按扣费后平均收益选阈值，不按 AUC。
THRESHOLDS = [round(0.30 + 0.05 * i, 2) for i in range(11)]
MIN_THRESHOLD_EVENTS = 20

XGB_ROUNDS = 80
XGB_MAX_DEPTH = 3
XGB_ETA = 0.1

# 冒烟用的少量流动性个股，不是沪深 300。正式跑请传入股票池文件。
DEFAULT_CODES = (
    "000001.XSHE",
    "600000.XSHG",
    "600519.XSHG",
)

TYPE_COLUMNS = ("type_1", "type_1p", "type_2", "type_2s", "type_3a", "type_3b")
TYPE_VALUE_TO_COLUMN = {
    "1": "type_1",
    "1p": "type_1p",
    "2": "type_2",
    "2s": "type_2s",
    "3a": "type_3a",
    "3b": "type_3b",
}

# 引擎按买卖点类型写入，缺失时用 0，并单独给 _missing。
ENGINE_OPTIONAL = (
    "divergence_rate",
    "zs_cnt",
    "bsp1_bi_amp",
    "bsp2_retrace_rate",
    "bsp2_break_bi_amp",
    "bsp2_bi_amp",
    "bsp2s_retrace_rate",
    "bsp2s_break_bi_amp",
    "bsp2s_bi_amp",
    "bsp2s_lv",
    "bsp3_zs_height",
    "bsp3_bi_amp",
)

STRUCTURE_OPTIONAL = (
    "seg_bi_cnt",
    "seg_amp",
    "seg_is_down",
    "zs_width",
    "price_vs_zs",
    "bi_amp_ratio",
)

CONFIRM_OPTIONAL = (
    "open_klu_rate",
    "body_ratio",
    "macd_hist",
    "rsi",
    "boll_pos",
    "vol_ratio",
)

OPTIONAL_FEATURES = ENGINE_OPTIONAL + STRUCTURE_OPTIONAL + CONFIRM_OPTIONAL


def model_feature_columns() -> list[str]:
    """固定特征顺序。feature.meta 与训练、推理共用这一份。"""
    columns = ["is_buy", *TYPE_COLUMNS, "bsp_bi_amp", "bi_is_sure"]
    for name in OPTIONAL_FEATURES:
        columns.append(name)
        columns.append(f"{name}_missing")
    return columns


FEATURE_COLUMNS = model_feature_columns()


def make_chan_config():
    """放宽后的候选买卖点配置。调用方传入 CChan，不改引擎默认算法实现。"""
    from ChanConfig import CChanConfig

    return CChanConfig({
        "trigger_step": True,
        "bi_strict": True,
        "skip_step": 0,
        "divergence_rate": float("inf"),
        "bsp2_follow_1": False,
        "bsp3_follow_1": False,
        "min_zs_cnt": 0,
        "macd_algo": "peak",
        "bs_type": "1,1p,2,2s,3a,3b",
        "print_warning": False,
        "print_err_time": False,
        "cal_rsi": True,
        "zs_algo": "normal",
    })


# 时间滚动。训练段还会再用标签窗口截断，见 Research.split。
FOLDS = (
    {
        "name": "train2018_2021_val2022_test2023",
        "train_start": "2018-01-01",
        "train_end": "2021-12-31",
        "val_start": "2022-01-01",
        "val_end": "2022-12-31",
        "test_start": "2023-01-01",
        "test_end": "2023-12-31",
    },
    {
        "name": "train2018_2022_val2023_test2024",
        "train_start": "2018-01-01",
        "train_end": "2022-12-31",
        "val_start": "2023-01-01",
        "val_end": "2023-12-31",
        "test_start": "2024-01-01",
        "test_end": "2024-12-31",
    },
)
