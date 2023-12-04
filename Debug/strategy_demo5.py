from typing import Dict

import xgboost as xgb

from Chan import CChan
from ChanConfig import CChanConfig
from ChanModel.Features import CFeatures
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE

if __name__ == "__main__":
    """
    本demo主要演示如何记录策略产出的买卖点的特征
    然后将这些特征作为样本，训练一个模型(以XGB为demo)
    用于预测买卖点的准确性

    请注意，demo训练预测都用的是同一份数据，这是不合理的，仅仅是为了演示
    """
    code = "sz.000001"
    begin_time = "2000-01-01"
    end_time = None
    data_src = DATA_SRC.BAO_STOCK
    lv_list = [KL_TYPE.K_DAY]

    config = CChanConfig({
        "triger_step": True,  # 打开开关！
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

    bsp_dict: Dict[int, CFeatures] = {}  # 存储策略产出的bsp的特征

    # 跑策略，保存买卖点的特征
    for chan_snapshot in chan.step_load():
        bsp_list = chan_snapshot.get_bsp()
        if not bsp_list:
            continue
        last_bsp = bsp_list[-1]

        cur_lv_chan = chan_snapshot[0]
        if last_bsp.klu.idx not in bsp_dict and cur_lv_chan[-2].idx == last_bsp.klu.klc.idx:
            # 假如策略是：买卖点分形第三元素出现时交易
            bsp_dict[last_bsp.klu.idx] = last_bsp.features
            print(last_bsp.klu.time, last_bsp.is_buy)

    # 生成libsvm样本特征
    bsp_academy = [bsp.klu.idx for bsp in chan.get_bsp()]
    feature_meta = {}  # 特征meta
    cur_feature_idx = 0
    fid = open("feature.libsvm", "w")
    for bsp_klu_idx, feature in bsp_dict.items():
        label = int(bsp_klu_idx in bsp_academy)  # 以买卖点识别是否准确为label
        features = []  # List[(idx, value)]
        for feature_name, value in feature.items():
            if feature_name not in feature_meta:
                feature_meta[feature_name] = cur_feature_idx
                cur_feature_idx += 1
            features.append((feature_meta[feature_name], value))
        features.sort(key=lambda x: x[0])
        feature_str = " ".join([f"{idx}:{value}" for idx, value in features])
        fid.write(f"{label} {feature_str}\n")

    # load sample file & train model
    dtrain = xgb.DMatrix("feature.libsvm?format=libsvm")  # load sample
    param = {'max_depth': 2, 'eta': 0.3, 'objective': 'binary:logistic', 'eval_metric': 'auc'}
    evals_result = {}
    bst = xgb.train(
        param,
        dtrain=dtrain,
        num_boost_round=10,
        evals=[(dtrain, "train")],
        evals_result=evals_result,
        verbose_eval=True,
    )
    bst.save_model("model.json")

    # load model
    model = xgb.Booster()
    model.load_model("model.json")
    # predict
    print(model.predict(dtrain))
