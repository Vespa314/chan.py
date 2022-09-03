#!/bin/bash

SHELL_FOLDER=$(cd "$(dirname "${BASH_SOURCE[0]}")";pwd)
source ${SHELL_FOLDER}/../Config/config.sh

nohup python3 ${PROJECT_ROOT_PATH}/ModelStragety/backtest.py > ${LOG_PATH}/backtest.log &
