from Bi.CBi import CBi
from common.CEnum import BI_DIR


class CBS_Point:
    def __init__(self, bi: CBi, is_buy, bs_type, relate_bsp1, extrainfo={}):
        self.bi = bi
        self.klu = bi.get_end_klu()
        self.is_buy = is_buy
        self.type = [bs_type]
        self.relate_bsp1 = relate_bsp1

        self.extrainfo = extrainfo
        self.update_extrainfo()

    def __str__(self):
        return f"{self.klu.time}-{self.type2str()}{'b' if self.is_buy else 's'}"

    def add_type(self, bs_type, extrainfo={}):
        self.type.append(bs_type)
        self.add_feat(extrainfo)

    def type2str(self):
        return ",".join(self.type)

    def has_type(self, x):
        return str(x) in self.type

    def qjt_type(self):
        return [f"q{x}" for x in self.type]

    def toJson(self):
        return {
            "bi": self.bi.idx,
            "klu": self.klu.toJson(),
            "is_buy": self.is_buy,
            "type": self.type2str(),
            "extrainfo": self.extrainfo,
        }

    def add_feat(self, inp1, inp2=None):
        if inp2 is None:
            assert type(inp1) == dict
            self.extrainfo.update(inp1)
        else:
            self.extrainfo.update({inp1: inp2})

    def extract_feat(self, prefix):
        res = {}
        for k, v in self.extrainfo.items():
            if k.startswith(prefix):
                res[k] = v
        return res

    def update_extrainfo(self):
        self.extrainfo.update(self.bi.Get3KZSFeat())
        self.add_feat({
            "bsp_bi_klu_cnt": self.bi.get_end_klu().idx-self.bi.get_begin_klu().idx+1,
            "bsp_fx_break": self.bi.get_fx_break_rate(),
        })
        last_klu = self.bi.get_last_klu()
        if last_klu.boll:
            boll = last_klu.boll
            c = last_klu.close
            self.add_feat({
                "bsp_boll_theta": boll.theta,
                "bsp_boll_mid": (c-boll.MID)/boll.MID,
                "bsp_boll_up": (c-boll.UP)/boll.UP,
                "bsp_boll_down": (c-boll.DOWN)/boll.DOWN,
                "bsp_boll_theta_cnt": (c-boll.MID)/boll.theta,  # UP和DOWN不重要，可以推导出来的
            })
            self.add_feat(
                "bsp_boll_end",
                (last_klu.low-boll.DOWN)/boll.DOWN if self.bi.dir == BI_DIR.DOWN else (boll.UP-last_klu.high)/boll.UP,
            )
        if self.relate_bsp1:
            assert self.type2str().find("1") < 0
            self.add_feat(self.relate_bsp1.extract_feat("bsp1_"))
