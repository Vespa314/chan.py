# -*- coding: utf-8 -*-
"""
程序入口模块 - 演示如何使用 chan.py 进行缠论分析

Java 开发者注意：
- if __name__ == "__main__": 是 Python 的入口点检测，类似于 Java 的 public static void main(String[] args)
  Python 对比：当脚本直接运行时 __name__ 为 "__main__"，被导入时则为模块名
- Python 字典定义 {key: value} 类似于 Java 的 Map.of() 或 HashMap
- Python 的文件路径用 ./ 相对于当前工作目录，不同于 Java 的 classpath 概念
- Python 的 float("inf") 表示正无穷，类似于 Java 的 Double.POSITIVE_INFINITY

使用说明：
    直接运行此脚本即可进行缠论分析并生成图表：
    python main.py
"""

from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Plot.AnimatePlotDriver import CAnimateDriver
from Plot.PlotDriver import CPlotDriver

if __name__ == "__main__":
    """
    缠论分析主流程演示

    流程：
    1. 配置参数（股票代码、时间范围、数据源、级别等）
    2. 创建 CChan 实例并加载数据
    3. 根据 trigger_step 模式选择绘图方式
       - trigger_step=False: 一次性加载所有数据，使用 CPlotDriver 绘制静态图
       - trigger_step=True: 逐步加载，使用 CAnimateDriver 生成动画
    """

    # ========== 基本配置 ==========
    code = "sz.000001"          # 平安银行（深圳）
    begin_time = "2018-01-01"   # 数据起始时间
    end_time = None             # 数据结束时间（None=最新）
    data_src = DATA_SRC.BAO_STOCK  # 数据源：BaoStock
    lv_list = [KL_TYPE.K_DAY]   # 分析级别：日线

    # ========== 缠论配置 ==========
    config = CChanConfig({
        "bi_strict": True,              # 笔严格模式（严格按缠论定义）
        "trigger_step": False,          # 是否步进模式（False=一次性加载）
        "skip_step": 0,                 # 跳过前N步
        "divergence_rate": float("inf"),  # 背驰率（inf=不限制）
        "bsp2_follow_1": False,         # 二类买卖点不跟随一类
        "bsp3_follow_1": False,         # 三类买卖点不跟随一类
        "min_zs_cnt": 0,                # 最小中枢数量
        "bs1_peak": False,             # 一买是否取峰值
        "macd_algo": "peak",           # MACD 算法（peak=峰值法）
        "bs_type": '1,2,3a,1p,2s,3b',  # 启用的买卖点类型
        "print_warning": True,          # 是否打印警告
        "zs_algo": "normal",            # 中枢算法（normal=标准）
    })

    # ========== 绘图配置 ==========
    plot_config = {
        "plot_kline": True,          # 显示K线（阴阳烛）
        "plot_kline_combine": True,  # 显示合并K线
        "plot_bi": True,             # 显示笔
        "plot_seg": True,            # 显示线段
        "plot_eigen": False,         # 不显示特征序列
        "plot_zs": True,             # 显示中枢
        "plot_macd": False,          # 不显示MACD
        "plot_mean": False,          # 不显示均线
        "plot_channel": False,       # 不显示趋势通道
        "plot_bsp": True,            # 显示买卖点
        "plot_extrainfo": False,     # 不显示额外信息
        "plot_demark": False,        # 不显示Demark序列
        "plot_marker": False,        # 不显示自定义标记
        "plot_rsi": False,           # 不显示RSI
        "plot_kdj": False,           # 不显示KDJ
    }

    # ========== 绘图参数（样式调整） ==========
    plot_para = {
        "seg": {
            # "plot_trendline": True,  # 取消注释以显示线段趋势线
        },
        "bi": {
            # "show_num": True,        # 取消注释以显示笔编号
            # "disp_end": True,        # 取消注释以显示端点价格
        },
        "figure": {
            "x_range": 200,            # 显示最后200根K线
        },
        "marker": {
            # 自定义标记示例
            # "markers": {  # text, position, color
            #     '2023/06/01': ('marker here', 'up', 'red'),
            #     '2023/06/08': ('marker here', 'down')
            # },
        }
    }

    # ========== 创建缠论分析实例 ==========
    chan = CChan(
        code=code,
        begin_time=begin_time,
        end_time=end_time,
        data_src=data_src,
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,  # 前复权
    )

    # ========== 绘图 ==========
    if not config.trigger_step:
        # 静态模式：一次性绘制所有分析结果
        plot_driver = CPlotDriver(
            chan,
            plot_config=plot_config,
            plot_para=plot_para,
        )
        plot_driver.figure.show()        # 显示图表
        plot_driver.save2img("./test.png")  # 保存为图片
    else:
        # 动画模式：逐步展示分析过程（适用于 Jupyter Notebook）
        CAnimateDriver(
            chan,
            plot_config=plot_config,
            plot_para=plot_para,
        )