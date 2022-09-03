#!/bin/bash

SHELL_FOLDER=$(cd "$(dirname "${BASH_SOURCE[0]}")";pwd)
source ${SHELL_FOLDER}/../../Config/config.sh


OfflineDataPath=$(cd "${PROJECT_ROOT_PATH}/OfflineData";pwd)
TradeScriptPath=$(cd "${PROJECT_ROOT_PATH}/Trade/Script";pwd)
NotionScriptPath=$(cd "${PROJECT_ROOT_PATH}/Script/Notion";pwd)

wait4finished(){
     total=0
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
               sleep 60
               let total+=1;
               if [ ${total} -eq 120 ];then
                    python3 ${PROJECT_ROOT_PATH}/Common/send_msg_cmd.py "chan monitor run($1) over 2 hours" "remember kill monitor_run first!!"
                    total=0
               fi
          else
               break
          fi
     done
}

main(){
     # 必须在SignalMonitor之前先跑
     nohup python3 ${TradeScriptPath}/CheckOpenScore.py -r $1 -b true -d $open_date > ${LOG_PATH}/CheckOpenScore_$1.log &
     nohup python3 ${TradeScriptPath}/CheckOpenScore.py -r $1 -b false -o -d $open_date > ${LOG_PATH}/CheckOpenScore_$1_cover.log &

     nohup python3 ${TradeScriptPath}/UpdatePeakPrice.py > ${LOG_PATH}/UpdatePeakPrice_$1.log &

     wait4finished CheckOpenScore $1
     wait4finished UpdatePeakPrice $1

     nohup python3 ${TradeScriptPath}/SignalMonitor.py -a $1 -s $date > ${LOG_PATH}/SignalMonitor_$1.log &

     nohup python3 ${NotionScriptPath}/DB_sync_Notioin.py -r $1 > ${LOG_PATH}/DB_sync_Notioin_$1.log &
}

if [ $# -eq 3 ];then
     date=$2  # 数据时间
     open_date=$3  # 开仓时间
elif [ $# -eq 2 ];then
     echo "para should be [area] or [area date(YYYYMMDD) opendate(YYYYMMDD)]"
     exit 0
elif [ "$1" = "cn" ];then
     date=`date +%Y%m%d`
     open_date=`date +%Y%m%d`
elif [ "$1" = "us" ];then
     date=`date -d "1 day ago" +%Y%m%d`
     open_date=`date +%Y%m%d`
elif [ "$1" = "hk" ];then
     date=`date -d "1 day ago" +%Y%m%d`
     open_date=`date -d "1 day ago" +%Y%m%d`
else
     echo "para area error"
     exit 0
fi

if [ "$1" = "us" -a "${cal_us}" = "true" ];then
     nohup python3 ${OfflineDataPath}/ak_update.py -a us -d ${date} > ${LOG_PATH}/ak_update_us.log &
     sleep 3
     wait4finished ak_update.py "\-u"

     main "us"
elif [ "$1" = "cn" -a "${cal_cn}" = "true" ];then
     nohup python3 ${OfflineDataPath}/ak_update.py -a cn -d ${date} > ${LOG_PATH}/ak_update_us.log &
     nohup python3 ${OfflineDataPath}/etf_download.py > ${LOG_PATH}/etf_download.log &
     sleep 3

     wait4finished bao_update.py qfq
     wait4finished etf_download.py

     main "cn"
elif [ "$1" = "hk" -a "${cal_hk}" = "true" ];then
     nohup python3 ${OfflineDataPath}/ak_update.py -a hk -d ${date} > ${LOG_PATH}/ak_update_hk.log &

     wait4finished ak_update.py

     main "hk"
else
     echo "./monitor_run.sh us/cn/hk"
fi
