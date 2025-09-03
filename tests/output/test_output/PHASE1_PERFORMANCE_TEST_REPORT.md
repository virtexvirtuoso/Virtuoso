# Phase 1 Performance Test Report

**Status:** completed
**Execution Time:** 0.31 seconds
**Test Data Size:** 1000 rows

## Summary

- **Average Speedup:** 6.9x
- **Maximum Speedup:** 21.4x
- **Time Saved:** 232.45ms per 100 iterations
- **Numerical Accuracy:** High

## SMA Performance Results

### SMA_5
- Pandas time: 0.0092s
- TA-Lib time: 0.0024s
- Speedup: 3.8x
- Time saved: 6.78ms

### SMA_10
- Pandas time: 0.0061s
- TA-Lib time: 0.0022s
- Speedup: 2.7x
- Time saved: 3.87ms

### SMA_20
- Pandas time: 0.0598s
- TA-Lib time: 0.0054s
- Speedup: 11.0x
- Time saved: 54.33ms

### SMA_50
- Pandas time: 0.0084s
- TA-Lib time: 0.0022s
- Speedup: 3.9x
- Time saved: 6.24ms

## EMA Performance Results

### EMA_5
- Pandas time: 0.0064s
- TA-Lib time: 0.0062s
- Speedup: 1.0x
- Time saved: 0.17ms

### EMA_10
- Pandas time: 0.0068s
- TA-Lib time: 0.0024s
- Speedup: 2.9x
- Time saved: 4.47ms

### EMA_20
- Pandas time: 0.0052s
- TA-Lib time: 0.0023s
- Speedup: 2.3x
- Time saved: 2.89ms

### EMA_50
- Pandas time: 0.0050s
- TA-Lib time: 0.0024s
- Speedup: 2.1x
- Time saved: 2.65ms

## ATR Performance Results

### ATR_14
- Custom time: 0.0792s
- TA-Lib time: 0.0043s
- Speedup: 18.2x
- Time saved: 74.82ms

### ATR_21
- Custom time: 0.0800s
- TA-Lib time: 0.0037s
- Speedup: 21.4x
- Time saved: 76.22ms

## Numerical Accuracy

- SMA_correlation: 1.000000
- EMA_correlation: 0.999965
