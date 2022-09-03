#!/bin/bash

SHELL_FOLDER=$(cd "$(dirname "${BASH_SOURCE[0]}")";pwd)
source ${SHELL_FOLDER}/../Config/config.sh

wait4finished(){
     while [ 1 ]
     do
          if [ $# -eq 1 ];then
               process_cnt=`ps aux | grep "$1" | grep -v grep | wc -l`
          elif [ $# -eq 2 ];then
               process_cnt=`ps aux | grep "$1" | grep -v grep | grep "$2" | wc -l`
          else
               process_cnt=`ps aux | grep "$1" | grep "$2" | grep "$3" | grep -v grep | wc -l`
          fi
          echo "waitting $1 process_cnt = ${process_cnt}"
          if [ ${process_cnt} -ne 0 ];then
               sleep 300
          else
               break
          fi
     done
}


bash ${SHELL_FOLDER}/run_backtest.sh
sleep 80000
wait4finished backtest.py

nohup ${PROJECT_ROOT_PATH}/ModelStragety/models/Xgboost/train_all_model.sh > ${LOG_PATH}/train_all.log &
sleep 3600
wait4finished train_all_model

# nohup python3 ${PROJECT_ROOT_PATH}/ModelStragety/FeatureReconciliation.py > ${LOG_PATH}/FeatureReconciliation.log &
# sleep 86400
# wait4finished FeatureReconciliation
# python3 ${PROJECT_ROOT_PATH}/Common/send_msg_cmd.py "FeatureReconciliation Finished" "RT"

rm -rf ${DATA_PATH}/pickle
nohup python3 ${PROJECT_ROOT_PATH}/ModelStragety/parameterEvaluate/eval_stragety.py > ${LOG_PATH}/eval_stragety.log &
wait4finished eval_stragety.py
cd ${DATA_PATH}
zip -rq ${DATA_PATH}/pickle.zip pickle/*
