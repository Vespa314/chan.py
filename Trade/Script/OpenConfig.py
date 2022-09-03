import os
import sys

cur_path = os.path.split(os.path.realpath(__file__))[0]
sys.path.append(f'{cur_path}/../..')
from Config.EnvConfig import GetYammlConfig  # noqa: E402


class COpenConfig:
    def __init__(self, area):
        self.config = GetYammlConfig(f'{cur_path}/OpenConfig.yaml')[area]

    def GetInterestType(self):
        type_pool = set()
        for type_list in self.config.keys():
            for _type in type_list.split(","):
                type_pool.add(_type)
        return type_pool

    def GetMinThred(self, record, metric):
        record_type = record['bstype']
        min_thred = float("inf")
        for _type in record_type.split(","):
            for interest_type, bsp_config in self.config.items():
                if _type in interest_type.split(","):
                    min_thred = min(min_thred, bsp_config[metric])
        return min_thred

    def GetModelType(self, record):
        record_type = record['bstype']
        for _type in record_type.split(","):
            for interest_type, bsp_config in self.config.items():
                if _type in interest_type.split(","):
                    return bsp_config['score_src']
        return "normal"

    def get_thred_info(self, record):
        stragety_sl = self.GetMinThred(record, 'max_sl')
        open_price = record['open_price']
        sl_thred = record['sl_thred']
        if record['is_buy'] and open_price*(1-stragety_sl) > sl_thred:
            sl_thred = open_price*(1-stragety_sl)
        if not record['is_buy'] and open_price*(1+stragety_sl) < sl_thred:
            sl_thred = open_price*(1+stragety_sl)
        return {
            'sl': sl_thred,
            'sw': self.GetMinThred(record, 'max_sw'),
            'dynamic_sl': self.GetMinThred(record, 'dynamic_sl'),
        }
