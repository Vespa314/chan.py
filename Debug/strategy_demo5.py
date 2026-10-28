# -*- coding: utf-8 -*-
"""
策略演示5 - 机器学习样本生成（XGBoost 训练）

Java 开发者注意：
- Python 的 TypedDict 是类型化字典，定义字典的键和值类型
  Java 对比：类似于有固定字段的 POJO/DTO 类
- Python 的 json.dumps(obj) 序列化为 JSON 字符串
  Java 对比：类似于 new ObjectMapper().writeValueAsString(obj)（Jackson）
- Python 的 lambda x: x[0] 是匿名函数，类似于 Java 的 x -> x[0]（Lambda）
- Python 的 open("file", "w") 打开文件，建议用 with 语句管理
  Java 对比：类似于 new FileWriter("file")，但 Java 的 try-with-resources 更安全
- Python 的 set 是集合类型，类似于 Java 的 HashSet
- Python 的 in 操作符检查元素是否在集合中
  Java 对比：set.contains(element)

策略说明：
    演示如何记录策略产出的买卖点特征，并将这些特征作为样本训练模型。
    流程：
    1. 跑策略，收集买卖点及其特征
    2. 以缠论识别的准确买卖点为 label（正确=1，错误=0）
    3. 生成 libsvm 格式的特征文件
    4. 训练 XGBoost 模型
    5. 保存模型和特征元信息

    注意：demo 中训练和预测使用同一份数据（不合理），仅用于演示。
"""

import json
from typing import Dict, TypedDict

import xgboost as xgb

from Chan import CChan
from ChanConfig import CChanConfig
from ChanModel.Features import CFeatures
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Common.CTime import CTime
from Plot.PlotDriver import CPlotDriver


class T_SAMPLE_INFO(TypedDict):
    """
    样本信息类型定义

    Python 特性：TypedDict 定义字典的键和值类型
    Java 对比：类似于 Java 的 record 或 POJO 类
    """
    feature: CFeatures
    is_buy: bool
    open_time: CTime


def plot(chan, plot_marker):
    """
    绘制带标记的图表，用于检查 label 是否正确

    参数:
        chan: CChan 对象
        plot_marker: 标记字典，格式 {'date': ('text', 'position', 'color')}
    """
    plot_config = {
        "plot_kline": True,
        "plot_bi": True,
        "plot_seg": True,
        "plot_zs": True,
        "plot_bsp": True,
        "plot_marker": True,
    }
    plot_para = {
        "figure": {
            "x_range": 400,
        },
        "marker": {
            "markers": plot_marker
        }
    }
    plot_driver = CPlotDriver(
        chan,
        plot_config=plot_config,
        plot_para=plot_para,
    )
    plot_driver.save2img("label.png")


def stragety_feature(last_klu):
    """
    策略自定义特征函数

    参数:
        last_klu: 开仓时的最后一根K线

    返回:
        自定义特征字典

    这里仅演示最简单的特征：开仓K线的涨跌幅。
    实际应用中可添加更多特征（如 MACD、RSI、成交量等）。
    """
    return {
        "open_klu_rate": (last_klu.close - last_klu.open) / last_klu.open,
    }


if __name__ == "__main__":
    code = "sz.000001"
    begin_time = "2018-01-01"
    end_time = None
    data_src = DATA_SRC.BAO_STOCK
    lv_list = [KL_TYPE.K_DAY]

    config = CChanConfig({
        "trigger_step": True,  # 打开步进模式
        "bi_strict": True,
        "skip_step": 0,
        "divergence_rate": float("inf"),
        "bsp2_follow_1": False,
        "bsp3_follow_1": False,
        "min_zs_cnt": 0,
        "bs1_peak": False,
        "macd_algo": "peak",
        "bs_type": '1,2,3a,1p,2s,3b',
        "print_warning": True,
        "zs_algo": "normal",
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

    bsp_dict: Dict[int, T_SAMPLE_INFO] = {}  # 存储策略产出的买卖点特征

    # ===== 阶段1：跑策略，收集买卖点特征 =====
    for chan_snapshot in chan.step_load():
        last_klu = chan_snapshot[0][-1][-1]
        bsp_list = chan_snapshot.get_latest_bsp()
        if not bsp_list:
            continue
        last_bsp = bsp_list[0]

        cur_lv_chan = chan_snapshot[0]
        # 策略：买卖点分形第三元素出现时交易
        if last_bsp.klu.idx not in bsp_dict and cur_lv_chan[-2].idx == last_bsp.klu.klc.idx:
            bsp_dict[last_bsp.klu.idx] = {
                "feature": last_bsp.features,
                "is_buy": last_bsp.is_buy,
                "open_time": last_klu.time,
            }
            # 添加策略自定义特征
            bsp_dict[last_bsp.klu.idx]['feature'].add_feat(stragety_feature(last_klu))
            print(last_bsp.klu.time, last_bsp.is_buy)

    # ===== 阶段2：生成 libsvm 格式特征文件 =====
    # 以缠论识别的准确买卖点为 label
    bsp_academy = [bsp.klu.idx for bsp in chan.get_latest_bsp(number=0)]
    feature_meta = {}  # 特征名 → 索引映射
    cur_feature_idx = 0
    plot_marker = {}  # 用于绘图验证的标记

    fid = open("feature.libsvm", "w")
    for bsp_klu_idx, feature_info in bsp_dict.items():
        # label = 1 表示该买卖点被缠论确认为正确的买卖点
        label = int(bsp_klu_idx in bsp_academy)
        features = []  # List[(idx, value)]

        for feature_name, value in feature_info['feature'].items():
            if feature_name not in feature_meta:
                feature_meta[feature_name] = cur_feature_idx
                cur_feature_idx += 1
            features.append((feature_meta[feature_name], value))

        # 按特征索引排序
        features.sort(key=lambda x: x[0])
        feature_str = " ".join([f"{idx}:{value}" for idx, value in features])
        fid.write(f"{label} {feature_str}\n")

        # 标记用于绘图验证：√ 正确，× 错误
        plot_marker[feature_info["open_time"].to_str()] = (
            "√" if label else "×",
            "down" if feature_info["is_buy"] else "up"
        )
    fid.close()

    # 保存特征元信息，实盘预测时用于特征对齐
    with open("feature.meta", "w") as fid:
        fid.write(json.dumps(feature_meta))

    # ===== 阶段3：绘图验证 label 是否正确 =====
    plot(chan, plot_marker)

    # ===== 阶段4：训练 XGBoost 模型 =====
    dtrain = xgb.DMatrix("feature.libsvm?format=libsvm")  # 加载 libsvm 格式数据
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

    # ===== 阶段5：加载模型并预测（验证用） =====
    model = xgb.Booster()
    model.load_model("model.json")
    print(model.predict(dtrain))