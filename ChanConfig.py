# -*- coding: utf-8 -*-
"""
ChanConfig 配置模块 - 管理缠论分析的所有配置参数

Java 开发者注意：
- Python 的 dict.get(k, default) 类似于 Java 的 map.getOrDefault(k, default)
- Python 的 exec() 是动态执行字符串代码，类似于 Java 的 ScriptEngine.eval()
  Java 对比：Java 没有直接的 exec()，需要借助 ScriptEngine 或反射
- Python 的 **args 是字典解包，类似于将 Map 展开为命名参数
  Java 对比：Java 没有直接对应，通常需要通过 Builder 模式逐参数设置
- Python 的 isinstance(v, str) 是类型检查，类似于 Java 的 v instanceof String
- Python 的 yield 是生成器函数，返回一个惰性迭代器
  Java 对比：Java 没有 yield 关键字，需要手动实现 Iterator 接口
- Python 的 | 在类型注解中表示联合类型（Python 3.10+）
  Java 对比：类似于 Java 的泛型通配符或方法重载
"""

from typing import List

from Bi.BiConfig import CBiConfig
from BuySellPoint.BSPointConfig import CBSPointConfig
from Common.CEnum import TREND_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.func_util import _parse_inf
from Math.BOLL import BollModel
from Math.Demark import CDemarkEngine
from Math.KDJ import KDJ
from Math.MACD import CMACD
from Math.RSI import RSI
from Math.TrendModel import CTrendModel
from Seg.SegConfig import CSegConfig
from ZS.ZSConfig import CZSConfig


class CChanConfig:
    """
    缠论主配置类 - 集中管理所有子模块的配置参数

    参数:
        conf: 配置字典，key 为配置项名称，value 为配置值

    配置项包括：
    - 笔配置（bi_algo, bi_strict, bi_fx_check 等）
    - 线段配置（seg_algo, left_seg_method）
    - 中枢配置（zs_combine, zs_combine_mode, zs_algo 等）
    - 买卖点配置（divergence_rate, bs_type 等）
    - 指标配置（macd, rsi, kdj, boll, demark 等）
    - 数据校验配置（kl_data_check, max_kl_misalgin_cnt 等）

    缠论知识 - 配置参数对分析的影响：
    - bi_algo: 笔的算法选择，normal=标准笔，fx=分型笔
    - seg_algo: 线段算法，chan=特征序列法（默认），def=定义法，dyh=都业华法
    - zs_algo: 中枢算法，normal=标准中枢，over_seg=段内中枢，auto=自动
    - left_seg_method: 左侧线段处理方法，peak=峰值法，avg=平均法
    """

    def __init__(self, conf=None):
        if conf is None:
            conf = {}
        conf = ConfigWithCheck(conf)  # 包装为带校验的配置对象

        # ========== 笔配置 ==========
        self.bi_conf = CBiConfig(
            bi_algo=conf.get("bi_algo", "normal"),
            is_strict=conf.get("bi_strict", True),
            bi_fx_check=conf.get("bi_fx_check", "strict"),
            gap_as_kl=conf.get("gap_as_kl", False),
            bi_end_is_peak=conf.get('bi_end_is_peak', True),
            bi_allow_sub_peak=conf.get("bi_allow_sub_peak", True),
        )

        # ========== 线段配置 ==========
        self.seg_conf = CSegConfig(
            seg_algo=conf.get("seg_algo", "chan"),
            left_method=conf.get("left_seg_method", "peak"),
        )

        # ========== 中枢配置 ==========
        self.zs_conf = CZSConfig(
            need_combine=conf.get("zs_combine", True),
            zs_combine_mode=conf.get("zs_combine_mode", "zs"),
            one_bi_zs=conf.get("one_bi_zs", False),
            zs_algo=conf.get("zs_algo", "normal"),
        )

        # ========== 回放/步进模式 ==========
        self.trigger_step = conf.get("trigger_step", False)
        self.skip_step = conf.get("skip_step", 0)

        # ========== 数据校验配置 ==========
        self.kl_data_check = conf.get("kl_data_check", True)
        self.max_kl_misalgin_cnt = conf.get("max_kl_misalgin_cnt", 2)
        self.max_kl_inconsistent_cnt = conf.get("max_kl_inconsistent_cnt", 5)
        self.auto_skip_illegal_sub_lv = conf.get("auto_skip_illegal_sub_lv", False)
        self.print_warning = conf.get("print_warning", True)
        self.print_err_time = conf.get("print_err_time", True)

        # ========== 指标配置 ==========
        self.mean_metrics: List[int] = conf.get("mean_metrics", [])
        self.trend_metrics: List[int] = conf.get("trend_metrics", [])
        self.macd_config = conf.get("macd", {"fast": 12, "slow": 26, "signal": 9})
        self.cal_demark = conf.get("cal_demark", False)
        self.cal_rsi = conf.get("cal_rsi", False)
        self.cal_kdj = conf.get("cal_kdj", False)
        self.rsi_cycle = conf.get("rsi_cycle", 14)
        self.kdj_cycle = conf.get("kdj_cycle", 9)
        self.demark_config = conf.get("demark", {
            'demark_len': 9,
            'setup_bias': 4,
            'countdown_bias': 2,
            'max_countdown': 13,
            'tiaokong_st': True,
            'setup_cmp2close': True,
            'countdown_cmp2close': True,
        })
        self.boll_n = conf.get("boll_n", 20)

        # ========== 买卖点配置 ==========
        self.set_bsp_config(conf)

        # 校验：确保没有未识别的配置项
        conf.check()

    def GetMetricModel(self):
        """
        根据配置创建所有指标计算模型实例

        返回:
            List[指标模型] 包含 MACD、均线、趋势通道、布林带、Demark、RSI、KDJ 等

        每个指标模型都是可调用的，在 K 线更新时计算对应的指标值。

        Python 特性：列表推导式 extend 和 append 混合使用
        - res.extend(CTrendModel(...) for mean_T in ...) 是生成器表达式
          Java 对比：类似于 for (int mean_T : mean_metrics) res.add(new CTrendModel(...))
        """
        res: List[CMACD | CTrendModel | BollModel | CDemarkEngine | RSI | KDJ] = [
            CMACD(
                fastperiod=self.macd_config['fast'],
                slowperiod=self.macd_config['slow'],
                signalperiod=self.macd_config['signal'],
            )
        ]
        # 添加均线指标（如 5/10/20/60 日均线）
        res.extend(CTrendModel(TREND_TYPE.MEAN, mean_T) for mean_T in self.mean_metrics)

        # 添加趋势通道指标（MAX 和 MIN 成对出现）
        for trend_T in self.trend_metrics:
            res.append(CTrendModel(TREND_TYPE.MAX, trend_T))
            res.append(CTrendModel(TREND_TYPE.MIN, trend_T))
        res.append(BollModel(self.boll_n))
        if self.cal_demark:
            res.append(CDemarkEngine(
                demark_len=self.demark_config['demark_len'],
                setup_bias=self.demark_config['setup_bias'],
                countdown_bias=self.demark_config['countdown_bias'],
                max_countdown=self.demark_config['max_countdown'],
                tiaokong_st=self.demark_config['tiaokong_st'],
                setup_cmp2close=self.demark_config['setup_cmp2close'],
                countdown_cmp2close=self.demark_config['countdown_cmp2close'],
            ))
        if self.cal_rsi:
            res.append(RSI(self.rsi_cycle))
        if self.cal_kdj:
            res.append(KDJ(self.kdj_cycle))
        return res

    def set_bsp_config(self, conf):
        """
        设置买卖点配置

        参数:
            conf: 配置字典

        处理逻辑：
        1. 设置默认买卖点参数
        2. 创建笔级别的买卖点配置（bs_point_conf）和线段级别的买卖点配置（seg_bs_point_conf）
        3. 线段级别默认使用 slope 算法（而非 peak 算法）
        4. 通过后缀识别配置项的作用范围：
           - "-buy" 后缀 → 仅买入点
           - "-sell" 后缀 → 仅卖出点
           - "-segbuy" 后缀 → 仅线段买入点
           - "-segsell" 后缀 → 仅线段卖出点
           - "-seg" 后缀 → 线段买卖点通用
           - 无后缀 → 笔级别买卖点通用

        Python 特性：exec() 动态执行代码
        - exec(f"self.bs_point_conf.b_conf.set('{prop}', {v})") 在运行时动态构建方法调用
          Java 对比：需要使用反射机制 Reflection API 或动态代理
        """
        # 默认参数
        para_dict = {
            "divergence_rate": float("inf"),
            "min_zs_cnt": 1,
            "bsp1_only_multibi_zs": True,
            "max_bs2_rate": 0.9999,
            "macd_algo": "peak",
            "bs1_peak": True,
            "bs_type": "1,1p,2,2s,3a,3b",
            "bsp2_follow_1": True,
            "bsp3_follow_1": True,
            "bsp3_peak": False,
            "bsp2s_follow_2": False,
            "max_bsp2s_lv": None,
            "strict_bsp3": False,
            "bsp3a_max_zs_cnt": 1,
        }
        # 从 conf 中提取参数，使用默认值填充
        args = {para: conf.get(para, default_value) for para, default_value in para_dict.items()}
        self.bs_point_conf = CBSPointConfig(**args)  # **args 将字典解包为关键字参数

        # 线段级别买卖点配置（默认使用 slope 算法，且不要求多笔中枢）
        self.seg_bs_point_conf = CBSPointConfig(**args)
        self.seg_bs_point_conf.b_conf.set("macd_algo", "slope")
        self.seg_bs_point_conf.s_conf.set("macd_algo", "slope")
        self.seg_bs_point_conf.b_conf.set("bsp1_only_multibi_zs", False)
        self.seg_bs_point_conf.s_conf.set("bsp1_only_multibi_zs", False)

        # 通过后缀识别配置项的作用范围
        for k, v in conf.items():
            if isinstance(v, str):
                v = f'"{v}"'  # 字符串值需要加引号，以便 exec 时作为字符串字面量
            v = _parse_inf(v)  # 处理特殊值（如 "inf" → float("inf")）
            if k.endswith("-buy"):
                prop = k.replace("-buy", "")
                exec(f"self.bs_point_conf.b_conf.set('{prop}', {v})")
            elif k.endswith("-sell"):
                prop = k.replace("-sell", "")
                exec(f"self.bs_point_conf.s_conf.set('{prop}', {v})")
            elif k.endswith("-segbuy"):
                prop = k.replace("-segbuy", "")
                exec(f"self.seg_bs_point_conf.b_conf.set('{prop}', {v})")
            elif k.endswith("-segsell"):
                prop = k.replace("-segsell", "")
                exec(f"self.seg_bs_point_conf.s_conf.set('{prop}', {v})")
            elif k.endswith("-seg"):
                prop = k.replace("-seg", "")
                exec(f"self.seg_bs_point_conf.b_conf.set('{prop}', {v})")
                exec(f"self.seg_bs_point_conf.s_conf.set('{prop}', {v})")
            elif k in args:
                exec(f"self.bs_point_conf.b_conf.set({k}, {v})")
                exec(f"self.bs_point_conf.s_conf.set({k}, {v})")
            else:
                raise CChanException(f"unknown para = {k}", ErrCode.PARA_ERROR)

        # 解析买卖点类型字符串（如 "1,1p,2,2s,3a,3b"）
        self.bs_point_conf.b_conf.parse_target_type()
        self.bs_point_conf.s_conf.parse_target_type()
        self.seg_bs_point_conf.b_conf.parse_target_type()
        self.seg_bs_point_conf.s_conf.parse_target_type()


class ConfigWithCheck:
    """
    带校验的配置包装器

    功能：
    1. 记录哪些配置项已被读取
    2. 在最后检查是否有未识别的配置项（防止拼写错误）

    Python 特性：
    - self.conf.get(k, default_value) 类似于 Java 的 Map.getOrDefault
    - del self.conf[k] 删除字典中的键，类似于 Java 的 Map.remove(k)
    - yield 生成器，惰性返回数据
      Java 对比：Java 没有 yield，需要手动实现迭代器
    """

    def __init__(self, conf):
        self.conf = conf

    def get(self, k, default_value=None):
        """
        获取配置值并标记为已读取

        参数:
            k: 配置键
            default_value: 默认值

        返回:
            配置值或默认值

        读取后从字典中删除该键，这样最后剩下的就是未被识别的配置项。
        """
        res = self.conf.get(k, default_value)
        if k in self.conf:
            del self.conf[k]
        return res

    def items(self):
        """
        迭代所有配置项并标记为已读取

        用于 set_bsp_config 中遍历所有自定义配置项
        """
        visit_keys = set()
        for k, v in self.conf.items():
            yield k, v
            visit_keys.add(k)
        for k in visit_keys:
            del self.conf[k]

    def check(self):
        """
        检查是否有未识别的配置项

        如果配置字典中还有剩余的键，说明用户传入了不存在的配置项
        （可能是拼写错误），抛出异常提醒。
        """
        if len(self.conf) > 0:
            invalid_key_lst = ",".join(list(self.conf.keys()))
            raise CChanException(f"invalid CChanConfig: {invalid_key_lst}", ErrCode.PARA_ERROR)