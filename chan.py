from common.CEnum import DATA_SRC, KL_TYPE
from KLine.CKline_List import CKline_List
from common.CTime import CTime
from common.func_util import check_kltype_order
from ChanConfig import CChanConfig
from common.ChanException import CChanException, ErrCode


def GetStockAPI(src):
    _dict = {}
    if src == DATA_SRC.FUTU:
        from dataSrc.FutuApi import CFutu_api
        _dict[DATA_SRC.FUTU] = CFutu_api
    elif src == DATA_SRC.BAO_STOCK:
        from dataSrc.BaoStockApi import CBaoStock
        _dict[DATA_SRC.BAO_STOCK] = CBaoStock
    if src in _dict:
        return _dict[src]
    if src.find("custom:") >= 0:  # custom:custom_reader.xxx
        package_info = src.split(":")[1]
        package_name, cls_name = package_info.split(".")
        exec(f"from dataSrc.{package_name} import {cls_name}")
        return eval(cls_name)
    else:
        raise Exception("load src type error")


class CChan:
    def __init__(self, code, begin_time=None, end_time=None, data_src=DATA_SRC.FUTU, lv_list=[KL_TYPE.K_DAY, KL_TYPE.K_60M], config=CChanConfig()):
        check_kltype_order(lv_list)  # lv_list顺序从高到低
        self.code = code
        self.begin_time = begin_time
        self.end_time = end_time
        self.data_src = data_src
        self.lv_list = lv_list
        self.conf = config

        self.do_init()

        self.name = None
        self.is_stock = None
        if not config.triger_step:
            for _ in self.load():
                ...

    def do_init(self):
        self.kl_datas = {}
        for idx in range(len(self.lv_list)):
            self.kl_datas[self.lv_list[idx]] = CKline_List(self.lv_list[idx], zs_mode=self.conf.GetZSMode(len(self.lv_list), idx), conf=self.conf)

    def load_stock_date(self, stockapi_cls, lv):
        stockapi_instance = stockapi_cls(code=self.code, k_type=lv, begin_date=self.begin_time, end_date=self.end_time)
        self.name = stockapi_instance.name
        self.is_stock = stockapi_instance.is_stock
        for kline_info in stockapi_instance.get_kl_data():
            yield kline_info

    def step_load(self):
        assert self.conf.triger_step
        self.do_init()  # 清空数据，防止再次重跑没有数据
        yielded = False  # 是否曾经返回过结果
        for idx, snapshot in enumerate(self.load(self.conf.triger_step)):
            if idx < self.conf.skip_step:
                continue
            yield snapshot
            yielded = True
        if not yielded:
            yield self

    def GetTopLvLastDay(self, stockapi_cls):
        last_klu = None
        for klu in self.load_stock_date(stockapi_cls, self.lv_list[0]):
            last_klu = klu
        return last_klu.time.toDate()

    def load(self, step=False):
        try:
            stockapi_cls = GetStockAPI(self.data_src)
            stockapi_cls.do_init()
            self.lv_klu_iter = [self.load_stock_date(stockapi_cls, lv) for lv in self.lv_list]
            if self.conf.bs_point_conf.only_judge_last:
                self.last_day = self.GetTopLvLastDay(stockapi_cls)
            self.klu_cache = [None for _ in self.lv_list]
            self.klu_last_t = [CTime(1970, 1, 1, 0, 0) for _ in self.lv_list]

            for snapshop in self.load_iterator(lv_idx=0, parent_klu=None, step=step):
                yield snapshop
            if not step and not self.conf.stragety_cls:  # 非回放模式全部算完之后才算一次中枢和线段
                for lv in self.lv_list:
                    self.kl_datas[lv].cal_seg_and_zs()
            if self.conf.stragety_cls:
                for lv in self.lv_list:
                    self[lv].cal_cbsp_summary()
        except Exception:
            raise
        finally:
            stockapi_cls.do_close()

    def load_iterator(self, lv_idx, parent_klu, step):
        # K线时间天级别以下描述的是结束时间，如60M线，每天第一根是10点30的
        # 天以上是当天日期
        cur_lv = self.lv_list[lv_idx]
        while True:
            if self.klu_cache[lv_idx]:
                kline_unit = self.klu_cache[lv_idx]
                self.klu_cache[lv_idx] = None
            else:
                try:
                    kline_unit = self.lv_klu_iter[lv_idx].__next__()
                    assert kline_unit.time > self.klu_last_t[lv_idx]
                    self.klu_last_t[lv_idx] = kline_unit.time
                except StopIteration:
                    break

            if parent_klu and kline_unit.time > parent_klu.time:
                self.klu_cache[lv_idx] = kline_unit
                break

            self.kl_datas[cur_lv].add_single_klu(kline_unit)
            if parent_klu:
                parent_klu.add_chindren(kline_unit)
                kline_unit.set_parent(parent_klu)
            if lv_idx != len(self.lv_list)-1:
                for _ in self.load_iterator(lv_idx+1, kline_unit, step):
                    ...
                if len(kline_unit.sub_kl_list) == 0:
                    raise CChanException(f"当前{kline_unit.time}没在次级别{self.lv_list[lv_idx+1]}找到K线！！", ErrCode.KL_DATA_NOT_ALIGN)
            if self.conf.stragety_cls:
                if not self.conf.bs_point_conf.only_judge_last:
                    self[lv_idx].stragety_cls.update(self, lv_idx)
                elif kline_unit.time >= self.last_day:
                    self.kl_datas[cur_lv].cal_seg_and_zs()
                    self[lv_idx].stragety_cls.update(self, lv_idx)
            if lv_idx == 0 and step:
                yield self

    def update_stragety(self):
        for lv in range(len(self.lv_list)-1, -1, -1):  # 先算小级别的
            if self.conf.stragety_cls:
                self[lv].stragety_cls.update(self, lv)

    def __getitem__(self, n):
        if isinstance(n, KL_TYPE):
            return self.kl_datas[n]
        elif isinstance(n, int):
            return self.kl_datas[list(self.kl_datas.keys())[n]]
        else:
            raise Exception("unspoourt query type")

    def toJson(self):
        return {str(lv): self[lv].toJson() for lv in self.lv_list}
