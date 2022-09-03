#!/bin/bash

SHELL_FOLDER=$(cd "$(dirname "${BASH_SOURCE[0]}")";pwd)
python3 ${SHELL_FOLDER}/bao_download.py -a qfq -r sz > ~/data/data_warehouse/stock/log/bao_sz_qfq.log
python3 ${SHELL_FOLDER}/bao_download.py -a qfq -r sh > ~/data/data_warehouse/stock/log/bao_sh_qfq.log
python3 ${SHELL_FOLDER}/bao_download.py -a hfq -r sz > ~/data/data_warehouse/stock/log/bao_sz_hfq.log
python3 ${SHELL_FOLDER}/bao_download.py -a hfq -r sh > ~/data/data_warehouse/stock/log/bao_sh_hfq.log