import json
import os
import sys
from collections import defaultdict


def parse(file, max_cnt):
    bsp_info = None
    metrics = []
    for line_num, line in enumerate(open(file)):
        if len(metrics) >= max_cnt:
            break
        line = json.loads(line.strip("\n"))
        if line_num == 0:
            bsp_info = line
        else:
            if line['metric']['win_cnt'] == 0:
                continue
            if line['metric']['avg_win_ratio'] <= 0.03:
                continue
            line['rank'] = line_num
            metrics.append(line)
    return bsp_info, metrics


def getWinLossRatio(x):
    return x['metric']['win_cnt']*x['metric']['avg_win_ratio']/x['metric']['loss_cnt']/x['metric']['avg_loss_ratio']


def parse_main(result_dir):
    bsp_type_dict = defaultdict(list)
    for file in os.listdir(result_dir):
        bsp_info, metrics = parse(os.path.join(result_dir, file), 5)
        bsp_token = f"{bsp_info['model_type']}#{bsp_info['area']}#{bsp_info['target_bsp_type']}"
        for para_combine in metrics:
            bsp_type_dict[bsp_token].append({
                'score_src': bsp_info['score_src'],
                'para': para_combine['para'],
                'winloss_ratio': getWinLossRatio(para_combine),
                'rank': para_combine['rank'],
                "metric": para_combine['metric']
            })
    yaml_config_content = {'cn': [], 'hk': [], 'us': []}
    for bsp_token, para_infos in bsp_type_dict.items():
        para_infos.sort(key=lambda para: para['winloss_ratio'], reverse=True)
        print(bsp_token)
        for para in para_infos[:5]:
            print("\t", para['score_src'], para['para'])
            print(f"\t\twin_cnt={para['metric']['win_cnt']}, loss_cnt={para['metric']['loss_cnt']}, avg_win_r={para['metric']['avg_win_ratio']}, avg_loss_r={para['metric']['avg_loss_ratio']}")
            print(f"\t\twinloss_ratio={para['winloss_ratio']}, rank={para['rank']}")

        area = bsp_token.split("#")[1]
        _type = bsp_token.split("#")[2]
        if _type == '1':
            yaml_config_content[area].append('  "1,1p":')
        elif _type == '2':
            yaml_config_content[area].append('  "2":')
        elif _type == '2s':
            yaml_config_content[area].append('  "2s":')
        elif _type == '3':
            yaml_config_content[area].append('  "3":')
        best_para = para_infos[0]
        default_market_value = 0.0
        yaml_config_content[area].append(f'    b_thred: {best_para["para"]["b_thred"]}')
        yaml_config_content[area].append(f'    s_thred: {best_para["para"]["s_thred"]}')
        yaml_config_content[area].append(f'    max_sw: {best_para["para"]["max_sw"]}')
        yaml_config_content[area].append(f'    max_sl: {best_para["para"]["max_sl"]}')
        yaml_config_content[area].append(f'    dynamic_sl: {best_para["para"]["dynamic_sl"]}')
        yaml_config_content[area].append(f'    market_value: {default_market_value}')
        yaml_config_content[area].append(f'    score_src: {best_para["score_src"]}')
    for area, config in yaml_config_content.items():
        print(f"{area}:")
        print("\n".join(config))


if __name__ == "__main__":
    parse_main(sys.argv[1])
