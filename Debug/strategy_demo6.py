import json
from typing import Dict, TypedDict

import xgboost as xgb
from strategy_demo5 import stragety_feature

from BuySellPoint.BS_Point import CBS_Point
from Chan import CChan
from ChanConfig import CChanConfig
from ChanModel.Features import CFeatures
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Common.CTime import CTime


class T_SAMPLE_INFO(TypedDict):
    feature: CFeatures
    is_buy: bool
    open_time: CTime


def predict_bsp(model: xgb.Booster, last_bsp: CBS_Point, meta: Dict[str, int]):
    missing = -9999999
    feature_arr = [missing] * len(meta)
    for feat_name, feat_value in last_bsp.features.items():
        if feat_name in meta:
            feature_arr[meta[feat_name]] = feat_value
    feature_arr = [feature_arr]
    dtest = xgb.DMatrix(feature_arr, missing=missing)
    return model.predict(dtest)


if __name__ == "__main__":
    """
    本demo主要演示如何在实盘中把策略产出的买卖点，对接到demo5中训练好的离线模型上
    """
    code = "sz.000001"
    begin_time = "2018-01-01"
    end_time = None
    data_src = DATA_SRC.BAO_STOCK
    lv_list = [KL_TYPE.K_DAY]

    config = CChanConfig({
        "trigger_step": True,  # 打开开关！
    })

    chan = CChan(
        code=code,
        begin_time=begin_time,
        end_time=end_time,
        data_src=data_src,
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,
    )

    model = xgb.Booster()
    model.load_model("model.json")
    meta = json.load(open("feature.meta", "r"))

    treated_bsp_idx = set()
    for chan_snapshot in chan.step_load():
        # 策略逻辑要对齐demo5
        last_klu = chan_snapshot[0][-1][-1]
        bsp_list = chan_snapshot.get_bsp()
        if not bsp_list:
            continue
        last_bsp = bsp_list[-1]

        cur_lv_chan = chan_snapshot[0]
        if last_bsp.klu.idx in treated_bsp_idx or cur_lv_chan[-2].idx != last_bsp.klu.klc.idx:
            continue

        last_bsp.features.add_feat(stragety_feature(last_klu))  # 开仓K线特征
        # 买卖点打分，应该和demo5最后的predict结果完全一致才对
        print(last_bsp.klu.time, predict_bsp(model, last_bsp, meta))
        treated_bsp_idx.add(last_bsp.klu.idx)
