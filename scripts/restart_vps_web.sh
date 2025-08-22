#!/bin/bash

ssh linuxuser@45.77.40.77 'bash -c "pkill -f web_server.py; sleep 2; cd /home/linuxuser/trading/Virtuoso_ccxt && PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt nohup venv311/bin/python src/web_server.py > logs/web_final.log 2>&1 & sleep 5 && tail -n 30 logs/web_final.log"'