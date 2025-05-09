# Funding Rate and Long/Short Ratio Guide

This document provides guidance on how funding rate and long/short ratio data are obtained from the Bybit API and processed in the Virtuoso system for sentiment analysis.

## Funding Rate Data

### API Endpoint

Funding rate data is available from two primary Bybit API endpoints:

1. **Ticker Endpoint**: 
   - URL: `https://api.bybit.com/v5/market/tickers`
   - Parameters: `category=linear&symbol=BTCUSDT`
   - This endpoint provides the current funding rate in the ticker data

2. **Funding History Endpoint**:
   - URL: `https://api.bybit.com/v5/market/funding/history`
   - Parameters: `category=linear&symbol=BTCUSDT&limit=20`
   - This endpoint provides historical funding rates

### Data Structure

#### Ticker Response Structure
```json
{
  "retCode": 0,
  "retMsg": "OK",
  "result": {
    "list": [
      {
        "symbol": "BTCUSDT",
        "lastPrice": "96596.70",
        "indexPrice": "96653.31",
        "markPrice": "96596.70",
        "prevPrice24h": "96432.77",
        "price24hPcnt": "0.0017",
        "highPrice24h": "98185.00",
        "lowPrice24h": "94567.18",
        "prevPrice1h": "96584.94",
        "openInterest": "356984152",
        "openInterestValue": "34483456789.25",
        "turnover24h": "18396368327.54",
        "volume24h": "190585.82",
        "fundingRate": "-0.00013884",
        "nextFundingTime": "1714939200000",
        "predictedDeliveryPrice": "",
        "basisRate": "",
        "deliveryFeeRate": "",
        "deliveryTime": "0",
        "ask1Size": "13.075",
        "bid1Price": "96590.33",
        "ask1Price": "96590.34",
        "bid1Size": "13.326"
      }
    ]
  },
  "retExtInfo": {},
  "time": 1714929129107
}
```

#### Funding History Response Structure
```json
{
  "retCode": 0,
  "retMsg": "OK",
  "result": {
    "category": "linear",
    "list": [
      {
        "symbol": "BTCUSDT",
        "fundingRate": "-0.0000303",
        "fundingRateTimestamp": "1714651200000"
      },
      {
        "symbol": "BTCUSDT",
        "fundingRate": "0.00002857",
        "fundingRateTimestamp": "1714622400000"
      },
      ...
    ]
  },
  "time": 1714929168000
}
```

### Data Processing in Virtuoso

In `sentiment_indicators.py`, the funding rate is processed as follows:

1. The code attempts to find the funding rate from various sources:
   - Direct `funding_rate` field
   - Nested `sentiment.funding_rate` field
   - In funding history data
   - In ticker data as `fundingRate`

2. Once found, the funding rate (which is a decimal value like `-0.00013884`) is:
   - Converted to a percentage by multiplying by 100 (e.g., `-0.013884%`)
   - Clipped to a reasonable range (-0.2% to 0.2%)
   - Mapped to a 0-100 score with negative funding rates considered bullish:
     - -0.2% → score of 100 (strongly bullish)
     - 0% → score of 50 (neutral)
     - 0.2% → score of 0 (strongly bearish)
   - Optionally transformed with a sigmoid function for smoother transitions

## Long/Short Ratio Data

### API Endpoint
- URL: `https://api.bybit.com/v5/market/account-ratio`
- Parameters: `category=linear&symbol=BTCUSDT&period=1d&limit=5`

### Data Structure
```json
{
  "retCode": 0,
  "retMsg": "OK",
  "result": {
    "list": [
      {
        "symbol": "BTCUSDT",
        "buyRatio": "0.5034",
        "sellRatio": "0.4966",
        "timestamp": "1714593600000"
      },
      {
        "symbol": "BTCUSDT",
        "buyRatio": "0.5217",
        "sellRatio": "0.4783",
        "timestamp": "1714507200000"
      },
      ...
    ]
  },
  "time": 1714929208532
}
```

### Data Processing in Virtuoso

The long/short ratio is processed as follows:

1. Extract the most recent entry from the account ratio data
2. Get the `buyRatio` (long) and `sellRatio` (short) values
3. The long ratio directly becomes the sentiment percentage (e.g., 0.5034 → 50.34%)
4. This is interpreted as:
   - Values ≥ 65% are strongly bullish (strong long bias)
   - Values ≥ 55% are moderately bullish (slight long bias)
   - Values ≤ 35% are strongly bearish (strong short bias)
   - Values ≤ 45% are moderately bearish (slight short bias)
   - Other values are considered neutral (balanced positioning)

## Combined Sentiment Score

For a more comprehensive view, Virtuoso combines multiple sentiment indicators:

- Funding rate score
- Long/short ratio score
- Other indicators (e.g., open interest, liquidations, volume)

Each indicator is weighted differently based on its reliability and significance, providing a holistic view of market sentiment.

## Testing the Data

You can test the funding rate and long/short ratio data processing using the included `test_funding_rate.py` script:

```bash
python test_funding_rate.py [SYMBOL]
```

This will fetch real-time data from Bybit and show how it's processed into sentiment scores.

## Troubleshooting

Common issues with funding rate and long/short ratio data:

1. **Missing Data**: If the funding rate is not found in any of the expected locations, a neutral score (50) is returned
2. **Invalid Values**: Very extreme funding rates are clipped to prevent unrealistic sentiment scores
3. **API Connectivity**: If the API doesn't respond or returns an error, ensure your network connection is stable
4. **Data Structure Changes**: If Bybit changes their API structure, the code might need updating to find the data in new locations 