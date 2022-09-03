import os
import sys
from enum import Enum

cur_path = os.path.split(os.path.realpath(__file__))[0]
sys.path.append(f'{cur_path}/..')
from Common.tools import _metric_report, send_msg  # noqa: E402
from Config.EnvConfig import Env  # noqa: E402


class UPDATE_STATE(Enum):
    NORMAL_UPDATE = "normal"
    NOT_NEED_UPDATE = "not_need_update"
    RE_DOWNLOAD = "redownload"
    DOWNLOAD_FAIL = "fail"
    SKIP_UPDATE = "skip"
    INCONSISTENT = "inconsistent"


def report_download_metric(key, status_dict):
    content = []
    for status, cnt in status_dict.items():
        _metric_report(id="offline_data", key=f"{key}_{status.value}", value=cnt)
        content.append(f"- {status.value}: {cnt}")
    if Env.Data['send_offline_data_update_info']:
        send_msg(f"{key}更新状况", "\n".join(content))


def check_data_consistent(data1, data2):
    # 只判断日期，open,close,high,low
    return data1.rsplit(',', 3) == data2.rsplit(',', 3)
