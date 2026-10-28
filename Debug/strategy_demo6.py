# -*- coding: utf-8 -*-
"""
策略演示6 - 实盘预测（对接离线训练模型）

Java 开发者注意：
- Python 的 set() 是集合，类似于 Java 的 new HashSet<>()
- Python 的 in 检查元素是否在集合中，类似于 Java 的 set.contains()
- Python 的 [missing] * len(meta) 创建重复元素的列表
  Java 对比：Collections.nCopies(len(meta), missing) 或手动填充
- Python 的 json.load(open("file", "r")) 从文件读取 JSON
  Java 对比：new ObjectMapper().readValue(new File("file"), Map.class)（Jackson）

策略说明：
    演示如何在实盘中将策略产出的买卖点对接到离线训练好的模型上。
    流程：
    1. 加载训练好的 XGBoost 模型和特征元信息
    2. 步进模式下运行策略
    3. 对每个买卖点，提取特征并用模型预测
    4. 预测结果应与 demo5 完全一致

    注意：预测时需要严格对齐特征顺序（使用 meta 字典映射）。
    缺失的特征用 missing 值填充。
"""

import json
from typing import Dict, TypedDict

import xgboost as xgb
from strategy_demo5 import stragety_feature  # 复用 demo5 的策略特征函数

from BuySellPoint.BS_Point import CBS_Point
from Chan import CChan
from ChanConfig import CChanConfig
from ChanModel.Features import CFeatures
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Common.CTime import CTime


class T_SAMPLE_INFO(TypedDict):
    """
    样本信息类型定义

    Python 特性：TypedDict 定义字典的键值类型
    Java 对比：类似于 Java 的 record 或 POJO 类
    """
    feature: CFeatures
    is_buy: bool
    open_time: CTime


def predict_bsp(model: xgb.Booster, last_bsp: CBS_Point, meta: Dict[str, int]):
    """
    用训练好的模型预测买卖点的准确性

    参数:
        model: 训练好的 XGBoost 模型
        last_bsp: 买卖点对象
        meta: 特征名 → 索引的映射字典

    返回:
        模型预测的分数（0-1之间，越接近1表示越可能正确）

    处理逻辑：
    1. 创建 full_missing 数组（长度 = 特征数量）
    2. 从买卖点特征中提取实际值
    3. 构建 DMatrix 并预测
    """
    missing = -9999999  # 缺失值填充
    feature_arr = [missing] * len(meta)
    for feat_name, feat_value in last_bsp.features.items():
        if feat_name in meta:
            feature_arr[meta[feat_name]] = feat_value
    feature_arr = [feature_arr]
    dtest = xgb.DMatrix(feature_arr, missing=missing)
    return model.predict(dtest)


if __name__ == "__main__":
    code = "sz.000001"
    begin_time = "2018-01-01"
    end_time = None
    data_src = DATA_SRC.BAO_STOCK
    lv_list = [KL_TYPE.K_DAY]

    config = CChanConfig({
        "trigger_step": True,  # 打开步进模式
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

    # 加载训练好的模型和特征元信息
    model = xgb.Booster()
    model.load_model("model.json")
    meta = json.load(open("feature.meta", "r"))

    treated_bsp_idx = set()  # 已处理的买卖点索引，避免重复处理
    for chan_snapshot in chan.step_load():
        # 策略逻辑要对齐 demo5
        last_klu = chan_snapshot[0][-1][-1]
        bsp_list = chan_snapshot.get_latest_bsp()
        if not bsp_list:
            continue
        last_bsp = bsp_list[0]

        cur_lv_chan = chan_snapshot[0]
        # 跳过已处理的买卖点
        if last_bsp.klu.idx in treated_bsp_idx or cur_lv_chan[-2].idx != last_bsp.klu.klc.idx:
            continue

        # 添加策略自定义特征
        last_bsp.features.add_feat(stragety_feature(last_klu))

        # 用模型预测买卖点准确性，结果应与 demo5 最后的 predict 结果完全一致
        print(last_bsp.klu.time, predict_bsp(model, last_bsp, meta))
        treated_bsp_idx.add(last_bsp.klu.idx)