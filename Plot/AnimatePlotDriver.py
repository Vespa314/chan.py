# -*- coding: utf-8 -*-
"""
动画绘图驱动模块 - 逐步展示缠论分析过程

Java 开发者注意：
- IPython.display.clear_output 用于在 Jupyter 中清除上一个输出
  Java 对比：Java 没有直接对应，GUI 中需要手动刷新组件
- IPython.display.display 用于在 Jupyter 中显示对象
  Java 对比：类似于在 GUI 中渲染组件到屏幕
- Python 的 for _ in iterator: 中 _ 表示不使用的变量名
  Java 对比：Java 没有这种约定，通常用 for (var ignored : iterator) 或直接不命名
"""

import matplotlib.pyplot as plt
from IPython.display import clear_output, display

from Chan import CChan

from .PlotDriver import CPlotDriver


class CAnimateDriver:
    """
    动画驱动 - 逐步展示缠论分析的可视化过程

    用于回放/步进模式，每加载一根K线就重新绘制一次图表，
    展示缠论分析过程的动态变化。

    参数:
        chan: CChan 实例（需开启 trigger_step 模式）
        plot_config: 绘图配置，控制显示哪些元素（笔、线段、中枢等）
        plot_para: 绘图参数，控制颜色、线宽等样式

    使用场景：
    - Jupyter Notebook 中逐步展示分析过程
    - 调试缠论算法时观察每一步的变化

    缠论知识 - 步进分析：
    通过逐步加载K线数据，可以观察：
    1. 笔是如何逐步形成和确认的
    2. 线段是如何在笔的基础上构建的
    3. 中枢是如何随着线段延伸而变化的
    4. 买卖点是在什么时机生成的
    """

    def __init__(self, chan: CChan, plot_config=None, plot_para=None):
        if plot_config is None:
            plot_config = {}
        if plot_para is None:
            plot_para = {}

        # chan.step_load() 是生成器，每次 yield 返回当前状态的 chan 对象
        # Java 对比：类似于实现了 Iterator<CChan> 的迭代器
        for _ in chan.step_load():
            g = CPlotDriver(chan, plot_config, plot_para)
            clear_output(wait=True)  # 清除上一个图，wait=True 表示等待新内容再清除
            display(g.figure)        # 在 Jupyter 中显示图表
            plt.close(g.figure)      # 关闭图表，释放内存