#!/bin/bash

cur_path=$(cd "$(dirname "${BASH_SOURCE[0]}")";pwd)

# check config.yaml exist
if [ ! -f "$cur_path/config.yaml" ]; then
    echo "[ERROR]config.yaml not found, exist!!"
    exit 1
fi

parse_config(){
    res=`python3 ${cur_path}/EnvConfig.py $1 $2`
    echo ${res}
}

contain_cnt(){
    res=`echo $1 | grep -c $2`
    if [ ${res} -eq 0 ];then
        echo "false"
    else
        echo "true"
    fi
}

PROJECT_ROOT_PATH=$(cd "${cur_path}/../";pwd)

DATA_PATH=`parse_config Data offline_data_path`
LOG_PATH=`parse_config Data log_path`
MODEL_PATH=`parse_config Data model_path`
STOCK_INFO_PATH=`parse_config Data stock_info_path`
PICKLE_DATA_PATH=`parse_config Data pickle_data_path`


support_area=`parse_config Trade area`
cal_cn=`contain_cnt ${support_area}, "cn"`
cal_hk=`contain_cnt ${support_area}, "hk"`
cal_us=`contain_cnt ${support_area}, "us"`
