#!/bin/bash

SHELL_FOLDER=$(cd "$(dirname "${BASH_SOURCE[0]}")";pwd)
source ${SHELL_FOLDER}/../Config/config.sh

if [ "${cal_us}" = "true" ];then
    nohup python3 ${SHELL_FOLDER}/ak_update.py -f -a us > ${LOG_PATH}/ak_us_qfq.log &
fi

if [ "${cal_hk}" = "true" ];then
    nohup python3 ${SHELL_FOLDER}/ak_update.py -f -a hk > ${LOG_PATH}/ak_hk_qfq.log &
fi

if [ "${cal_cn}" = "true" ];then
    nohup python3 ${SHELL_FOLDER}/ak_update.py -f -a cn > ${LOG_PATH}/ak_cn_qfq.log &
    nohup python3 ${SHELL_FOLDER}/etf_download.py > ${LOG_PATH}/etf.log &
fi