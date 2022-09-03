#!/bin/bash

SHELL_FOLDER=$(cd "$(dirname "${BASH_SOURCE[0]}")";pwd)
source ${SHELL_FOLDER}/../../Config/config.sh

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


if [ "${cal_us}" = "true" ];then
    nohup python3 ${SHELL_FOLDER}/query_marketvalue.py -m us > ${LOG_PATH}/cal_market_value_us.log &
fi

if [ "${cal_hk}" = "true" ];then
    nohup python3 ${SHELL_FOLDER}/query_marketvalue.py -m hk > ${LOG_PATH}/cal_market_value_hk.log &
fi

if [ "${cal_cn}" = "true" ];then
    nohup python3 ${SHELL_FOLDER}/query_marketvalue.py -m cn > ${LOG_PATH}/cal_market_value_cn.log &
fi

wait4finished query_marketvalue.py

nohup python3 ${SHELL_FOLDER}/query_marketvalue.py -m combine > ${LOG_PATH}/cal_market_value_combine.log &
