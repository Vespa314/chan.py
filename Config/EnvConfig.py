import os
import sys

import yaml


def GetYammlConfig(path):
    with open(path) as f:
        return yaml.safe_load(f)


class Env:
    config = GetYammlConfig(f"{os.path.split(os.path.realpath(__file__))[0]}/config.yaml")

    Data = config['Data']
    MODEL_PATH = Data['model_path']

    OFFLINE_DATA_PATH = Data['offline_data_path']

    MODEL = config['Model']

    Futu = config.get('Futu', {})
    FUTU_HOST = Futu.get('HOST', None)
    FUTU_PORT = Futu.get('PORT', None)
    FUTU_RSA_PATH = Futu.get('RSA_PATH', None)
    FUTU_PASSWD_MD5 = Futu.get('PASSWORD_MD5', None)

    DB = config.get('DB', {})

    CHAN_CODE_PATH = os.path.join(os.path.split(os.path.realpath(__file__))[0], "..")

    Trade = config.get('Trade', {})
    cn_stock = Trade.get("area", "").lower().find("cn") >= 0
    hk_stock = Trade.get("area", "").lower().find("hk") >= 0
    us_stock = Trade.get("area", "").lower().find("us") >= 0

    TRADE_MODEL_PATH = Trade.get('trade_model_path', MODEL_PATH)

    cal_feature = False
    debug_mode = config.get('Chan', {}).get('debug', False)


if __name__ == "__main__":
    config = Env.config
    for k in sys.argv[1:]:
        config = config[k]
    print(config)
