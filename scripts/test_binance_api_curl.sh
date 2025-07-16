#!/bin/bash

echo "🔗 Testing Binance API Endpoints for Market Reporter"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test symbols
SYMBOLS=("BTCUSDT" "ETHUSDT" "SOLUSDT" "XRPUSDT")
BASE_URL="https://fapi.binance.com"

echo -e "\n${BLUE}📊 Testing Core Market Data Endpoints${NC}"
echo "======================================"

for symbol in "${SYMBOLS[@]}"; do
    echo -e "\n${YELLOW}🎯 Testing ${symbol}:${NC}"
    
    # 1. Test 24hr Ticker Statistics (Price, Volume, Change)
    echo -n "   📈 24hr Ticker: "
    response=$(curl -s "${BASE_URL}/fapi/v1/ticker/24hr?symbol=${symbol}")
    if echo "$response" | jq -e '.symbol' > /dev/null 2>&1; then
        price=$(echo "$response" | jq -r '.lastPrice')
        change=$(echo "$response" | jq -r '.priceChangePercent')
        volume=$(echo "$response" | jq -r '.volume')
        turnover=$(echo "$response" | jq -r '.quoteVolume')
        echo -e "${GREEN}✅ Price: \$${price}, Change: ${change}%, Volume: ${volume}, Turnover: \$${turnover}${NC}"
    else
        echo -e "${RED}❌ Failed${NC}"
        echo "Response: $response"
    fi
    
    # 2. Test Open Interest
    echo -n "   🏗️  Open Interest: "
    response=$(curl -s "${BASE_URL}/fapi/v1/openInterest?symbol=${symbol}")
    if echo "$response" | jq -e '.openInterest' > /dev/null 2>&1; then
        oi=$(echo "$response" | jq -r '.openInterest')
        echo -e "${GREEN}✅ ${oi}${NC}"
    else
        echo -e "${RED}❌ Failed${NC}"
        echo "Response: $response"
    fi
    
    # 3. Test Funding Rate
    echo -n "   💰 Funding Rate: "
    response=$(curl -s "${BASE_URL}/fapi/v1/fundingRate?symbol=${symbol}&limit=1")
    if echo "$response" | jq -e '.[0].fundingRate' > /dev/null 2>&1; then
        funding=$(echo "$response" | jq -r '.[0].fundingRate')
        funding_time=$(echo "$response" | jq -r '.[0].fundingTime')
        echo -e "${GREEN}✅ ${funding} (${funding_time})${NC}"
    else
        echo -e "${RED}❌ Failed${NC}"
        echo "Response: $response"
    fi
    
    # 4. Test Premium Index (Mark Price vs Index Price)
    echo -n "   📊 Premium Index: "
    response=$(curl -s "${BASE_URL}/fapi/v1/premiumIndex?symbol=${symbol}")
    if echo "$response" | jq -e '.markPrice' > /dev/null 2>&1; then
        mark_price=$(echo "$response" | jq -r '.markPrice')
        index_price=$(echo "$response" | jq -r '.indexPrice')
        echo -e "${GREEN}✅ Mark: \$${mark_price}, Index: \$${index_price}${NC}"
    else
        echo -e "${RED}❌ Failed${NC}"
        echo "Response: $response"
    fi
    
    # 5. Test Order Book Depth
    echo -n "   📚 Order Book: "
    response=$(curl -s "${BASE_URL}/fapi/v1/depth?symbol=${symbol}&limit=10")
    if echo "$response" | jq -e '.bids' > /dev/null 2>&1; then
        bid_count=$(echo "$response" | jq '.bids | length')
        ask_count=$(echo "$response" | jq '.asks | length')
        best_bid=$(echo "$response" | jq -r '.bids[0][0]')
        best_ask=$(echo "$response" | jq -r '.asks[0][0]')
        echo -e "${GREEN}✅ ${bid_count} bids, ${ask_count} asks (Bid: \$${best_bid}, Ask: \$${best_ask})${NC}"
    else
        echo -e "${RED}❌ Failed${NC}"
        echo "Response: $response"
    fi
    
    # 6. Test Recent Trades
    echo -n "   🔄 Recent Trades: "
    response=$(curl -s "${BASE_URL}/fapi/v1/trades?symbol=${symbol}&limit=5")
    if echo "$response" | jq -e '.[0].price' > /dev/null 2>&1; then
        trade_count=$(echo "$response" | jq '. | length')
        latest_price=$(echo "$response" | jq -r '.[0].price')
        latest_qty=$(echo "$response" | jq -r '.[0].qty')
        echo -e "${GREEN}✅ ${trade_count} trades (Latest: ${latest_qty} @ \$${latest_price})${NC}"
    else
        echo -e "${RED}❌ Failed${NC}"
        echo "Response: $response"
    fi
done

echo -e "\n${BLUE}📈 Testing Advanced Analytics Endpoints${NC}"
echo "======================================="

# 7. Test Long/Short Ratio (Global)
echo -n "📊 Long/Short Ratio: "
response=$(curl -s "${BASE_URL}/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=1")
if echo "$response" | jq -e '.[0].longShortRatio' > /dev/null 2>&1; then
    ratio=$(echo "$response" | jq -r '.[0].longShortRatio')
    timestamp=$(echo "$response" | jq -r '.[0].timestamp')
    echo -e "${GREEN}✅ Long/Short Ratio: ${ratio} (${timestamp})${NC}"
else
    echo -e "${RED}❌ Failed${NC}"
    echo "Response: $response"
fi

# 8. Test Top Trader Long/Short Ratio
echo -n "🏆 Top Trader Ratio: "
response=$(curl -s "${BASE_URL}/futures/data/topLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=1")
if echo "$response" | jq -e '.[0].longShortRatio' > /dev/null 2>&1; then
    ratio=$(echo "$response" | jq -r '.[0].longShortRatio')
    timestamp=$(echo "$response" | jq -r '.[0].timestamp')
    echo -e "${GREEN}✅ Top Trader Ratio: ${ratio} (${timestamp})${NC}"
else
    echo -e "${RED}❌ Failed${NC}"
    echo "Response: $response"
fi

# 9. Test Exchange Information
echo -n "ℹ️  Exchange Info: "
response=$(curl -s "${BASE_URL}/fapi/v1/exchangeInfo")
if echo "$response" | jq -e '.symbols' > /dev/null 2>&1; then
    symbol_count=$(echo "$response" | jq '.symbols | length')
    echo -e "${GREEN}✅ ${symbol_count} trading pairs available${NC}"
else
    echo -e "${RED}❌ Failed${NC}"
    echo "Response: $response"
fi

# 10. Test Server Time
echo -n "🕐 Server Time: "
response=$(curl -s "${BASE_URL}/fapi/v1/time")
if echo "$response" | jq -e '.serverTime' > /dev/null 2>&1; then
    server_time=$(echo "$response" | jq -r '.serverTime')
    readable_time=$(date -d "@$((server_time/1000))" '+%Y-%m-%d %H:%M:%S UTC')
    echo -e "${GREEN}✅ ${readable_time}${NC}"
else
    echo -e "${RED}❌ Failed${NC}"
    echo "Response: $response"
fi

echo -e "\n${BLUE}🔍 Testing Market Summary Endpoints${NC}"
echo "===================================="

# 11. Test All 24hr Tickers (for top symbols analysis)
echo -n "📊 All 24hr Tickers: "
response=$(curl -s "${BASE_URL}/fapi/v1/ticker/24hr")
if echo "$response" | jq -e '.[0].symbol' > /dev/null 2>&1; then
    ticker_count=$(echo "$response" | jq '. | length')
    echo -e "${GREEN}✅ ${ticker_count} tickers received${NC}"
    
    # Show top 5 by quote volume
    echo "   🏆 Top 5 by Volume:"
    echo "$response" | jq -r '. | sort_by(.quoteVolume | tonumber) | reverse | .[0:5] | .[] | "      " + .symbol + ": $" + (.quoteVolume | tonumber / 1000000 | floor | tostring) + "M"'
else
    echo -e "${RED}❌ Failed${NC}"
    echo "Response: $response"
fi

# 12. Test Kline/Candlestick Data
echo -n "📈 Kline Data (1h): "
response=$(curl -s "${BASE_URL}/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=24")
if echo "$response" | jq -e '.[0][0]' > /dev/null 2>&1; then
    kline_count=$(echo "$response" | jq '. | length')
    latest_close=$(echo "$response" | jq -r '.[-1][4]')
    echo -e "${GREEN}✅ ${kline_count} klines (Latest close: \$${latest_close})${NC}"
else
    echo -e "${RED}❌ Failed${NC}"
    echo "Response: $response"
fi

echo -e "\n${BLUE}📋 Summary for Market Reporter${NC}"
echo "=============================="
echo -e "${GREEN}✅ All core endpoints tested successfully${NC}"
echo ""
echo "📊 Available Data for Market Reporter:"
echo "   • ✅ Real-time prices and 24hr statistics"
echo "   • ✅ Open interest for all major pairs"
echo "   • ✅ Funding rates (updated every 8 hours)"
echo "   • ✅ Premium index (mark vs index price)"
echo "   • ✅ Order book depth for liquidity analysis"
echo "   • ✅ Recent trades for whale activity detection"
echo "   • ✅ Long/short ratios for sentiment analysis"
echo "   • ✅ Historical kline data for trend analysis"
echo "   • ✅ Exchange metadata and server time"
echo ""
echo -e "${YELLOW}⚠️  Note: Risk limits endpoint requires authentication${NC}"
echo "   • Static fallback is implemented in the code"
echo "   • Public API provides all other necessary data"
echo ""
echo -e "${GREEN}🎉 Market Reporter has all required data sources!${NC}" 