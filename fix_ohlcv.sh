#!/bin/bash
cp src/core/exchanges/bybit.py src/core/exchanges/bybit.py.bak
head -n 2022 src/core/exchanges/bybit.py > bybit_fixed.py
