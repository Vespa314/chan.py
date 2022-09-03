print("#!/bin/bash")

wait_func = """
wait4finished(){
     while [ 1 ]
     do
          process_cnt=`ps aux | grep para_automl | grep -v grep | wc -l`
          if [ ${process_cnt} -ge $1 ];then
                sleep 60
          else
                # echo ${process_cnt}
                break
          fi
     done
}
"""

print(wait_func)


print("rm -rf ./exec_log/*")
print("rm -rf ./final_res/*")
print("rm -rf ./log/*")

for model_type in ["bsp_label-profit", "bsp_label-scale", "label-scale", "label-profit"]:
    for area in ['cn', 'us', 'hk']:
        for target_bsp_type in ['1', '2', '3', '2s']:
            for score_src in ['normal', 'bs_type', 'area']:
                print(f"nohup python3 ./para_automl.py {area} {target_bsp_type} {model_type} {score_src} > ./exec_log/{area}_{target_bsp_type}_{model_type}_{score_src}.log &")
                print("sleep 1")
                print("wait4finished 36")

print("wait4finished 0\n")
print("curl 'https://msg.jiamu.org/message?token=AmIWrvSNF27ZYc6' -F 'title=automl finished!!' -F 'message=rt'")
