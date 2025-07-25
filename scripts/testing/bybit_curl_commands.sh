#!/bin/bash
# Direct curl commands to test Bybit API endpoints

echo "======================================"
echo "Testing Bybit API Endpoints with CURL"
echo "======================================"
echo ""

# 1. Test OHLCV (1 minute candles)
echo "1. Testing OHLCV/Klines (1m):"
echo "Command: curl -X GET \"https://api.bybit.com/v5/market/kline?category=linear&symbol=BTCUSDT&interval=1&limit=2\""
curl -s -X GET "https://api.bybit.com/v5/market/kline?category=linear&symbol=BTCUSDT&interval=1&limit=2" | jq '.'
echo ""

# 2. Test Recent Trades
echo "2. Testing Recent Trades:"
echo "Command: curl -X GET \"https://api.bybit.com/v5/market/recent-trade?category=linear&symbol=BTCUSDT&limit=2\""
curl -s -X GET "https://api.bybit.com/v5/market/recent-trade?category=linear&symbol=BTCUSDT&limit=2" | jq '.'
echo ""

# 3. Test Orderbook
echo "3. Testing Orderbook:"
echo "Command: curl -X GET \"https://api.bybit.com/v5/market/orderbook?category=linear&symbol=BTCUSDT&limit=5\""
curl -s -X GET "https://api.bybit.com/v5/market/orderbook?category=linear&symbol=BTCUSDT&limit=5" | jq '.'
echo ""

# 4. Test Ticker
echo "4. Testing 24hr Ticker:"
echo "Command: curl -X GET \"https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT\""
curl -s -X GET "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT" | jq '.result.list[0] | {symbol, lastPrice, volume24h, bid1Price, ask1Price}'
echo ""

# 5. Test all timeframes we use
echo "5. Testing All Required Timeframes:"
for interval in 1 5 15 30 60 240; do
    echo "  Testing ${interval} minute interval..."
    response=$(curl -s -X GET "https://api.bybit.com/v5/market/kline?category=linear&symbol=BTCUSDT&interval=${interval}&limit=1")
    retCode=$(echo $response | jq -r '.retCode')
    if [ "$retCode" = "0" ]; then
        echo "  ✓ ${interval}m: Success"
    else
        echo "  ✗ ${interval}m: Failed"
    fi
done
echo ""

echo "======================================"
echo "Testing Complete!"
echo "======================================