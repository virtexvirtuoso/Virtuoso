#!/usr/bin/env python3
"""
Enhanced Sentiment Indicator Test

This script creates a comprehensive test for the sentiment indicator with realistic
market data for all components to verify proper functioning.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
import numpy as np

from src.indicators.sentiment_indicators import SentimentIndicators

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TEST_SENTIMENT")

async def test_sentiment_async():
    """Test the sentiment indicator with realistic market data asynchronously."""
    print("\n=== Testing Sentiment with Realistic Market Data ===")
    
    # Create test symbol data
    symbol = "BTCUSDT"
    current_price = 40450
    funding_rate = -0.017773
    
    print(f"Symbol: {symbol}")
    print(f"Current Price: ${current_price}")
    print(f"Current Funding Rate: {funding_rate:.6f}%")
    print(f"Long/Short Ratio: 0.62/0.38")
    
    # Create sentiment indicator with proper config structure
    config = {
        # Required timeframes config
        "timeframes": {
            "base": {
                "interval": "5",
                "weight": 0.4,
                "validation": {
                    "min_candles": 50
                }
            },
            "ltf": {
                "interval": "1",
                "weight": 0.2,
                "validation": {
                    "min_candles": 50
                }
            },
            "mtf": {
                "interval": "15",
                "weight": 0.3,
                "validation": {
                    "min_candles": 50
                }
            },
            "htf": {
                "interval": "60",
                "weight": 0.1,
                "validation": {
                    "min_candles": 50
                }
            }
        },
        # Validation requirements
        "validation_requirements": {
            "trades": {
                "min_trades": 50,
                "max_age": 3600
            },
            "orderbook": {
                "min_levels": 10
            }
        },
        # Sentiment-specific configuration
        "analysis": {
            "indicators": {
                "sentiment": {
                    "funding_threshold": 0.01,
                    "liquidation_threshold": 1000000,
                    "window": 20
                }
            }
        },
        # Confluence configuration with correct component weights
        "confluence": {
            "weights": {
                "sub_components": {
                    "sentiment": {
                        "funding_rate": 0.15,
                        "funding_rate_volatility": 0.1,
                        "long_short_ratio": 0.2,
                        "liquidation_events": 0.2,
                        "volume_sentiment": 0.15,
                        "market_mood": 0.1,
                        "risk_score": 0.1
                    }
                }
            }
        }
    }
    
    sentiment = SentimentIndicators(config)
    
    # Generate complete market data
    now = datetime.now()
    market_data = {
        # Ticker data
        "ticker": {
            "last": current_price,
            "bid": current_price - 5,
            "ask": current_price + 5,
            "volume": 5000000,
            "timestamp": int(now.timestamp() * 1000)
        },
        
        # OHLCV data - last 24 candles (hourly)
        "ohlcv": generate_ohlcv_data(current_price, 24),
        
        # Funding rate data
        "funding_rate": {
            "current_rate": funding_rate / 100,  # Convert to decimal
            "predicted_rate": funding_rate / 100 * 0.9,  # Slightly lower predicted rate
            "next_funding_time": int((now + timedelta(hours=8)).timestamp() * 1000),
            "history": generate_funding_history(funding_rate / 100)
        },
        
        # Long/short ratio data - Slightly bullish
        "long_short_ratio": {
            "long_ratio": 0.62,
            "short_ratio": 0.38,
            "history": generate_long_short_history(0.62, 0.38)
        },
        
        # Liquidation data - Add significant short liquidations
        "liquidations": generate_liquidation_data(),
        
        # Trade data for volume sentiment
        "trades": generate_trade_data(current_price),
        
        # Risk limit data
        "risk_limit": {
            "levels": [
                {
                    "id": 1,
                    "symbol": symbol,
                    "starting_margin": 0.02,  # 2% initial margin
                    "maintain_margin": 0.01,  # 1% maintenance margin
                    "limit": 200000  # Position limit for this tier
                },
                {
                    "id": 2,
                    "symbol": symbol,
                    "starting_margin": 0.025,
                    "maintain_margin": 0.0125,
                    "limit": 500000
                },
                {
                    "id": 3,
                    "symbol": symbol,
                    "starting_margin": 0.03,
                    "maintain_margin": 0.015,
                    "limit": 1000000
                },
                {
                    "id": 4,
                    "symbol": symbol,
                    "starting_margin": 0.04,
                    "maintain_margin": 0.02,
                    "limit": 2000000
                }
            ],
            "current_level": 1,
            "current_utilization": 0.7  # 70% of the level is utilized
        },
        
        # Enhanced sentiment data
        "sentiment": {
            "fear_greed_index": 45,  # Slightly fearful
            "social_sentiment": 0.3,  # Slightly negative
            "search_trends": 120,  # Above average search activity
            "positive_mentions": 0.48,  # Almost balanced mentions
            "negative_mentions": 0.52
        },
        
        # Market statistics
        "market_stats": {
            "24h_volume": 12500000000,  # 24h volume in USD
            "24h_change": -2.3,  # 24h price change in percent
            "30d_volatility": 3.8  # 30-day volatility
        }
    }
    
    print("\nCalculating sentiment score...")
    start_time = datetime.now()
    result = await sentiment.calculate_score(market_data)
    calc_time = (datetime.now() - start_time).total_seconds() * 1000  # in ms
    
    print(f"\n=== Sentiment Analysis Results ===")
    if isinstance(result, dict):
        print(f"Overall Sentiment Score: {result['score']:.2f}")
        print(f"\nInterpretation:")
        for key, value in result.items():
            if key not in ['score', 'signals', 'component_scores']:
                print(f"  {key}: {value}")
        
        print(f"\nSignals:")
        if result.get('signals'):
            for signal in result['signals']:
                print(f"  {signal}")
    else:
        # Handle the case where result is a float
        print(f"Overall Sentiment Score: {result:.2f}")
    
    print(f"\nAnalysis succeeded")
    
    return result

async def test_sentiment_sync():
    """Test the sentiment indicator with realistic market data synchronously."""
    print("\n=== Testing Sentiment with Realistic Market Data (Sync) ===")
    
    # Create test symbol data
    symbol = "ETHUSDT"
    current_price = 40450
    funding_rate = -0.016736
    
    print(f"Symbol: {symbol}")
    print(f"Current Price: ${current_price}")
    print(f"Current Funding Rate: {funding_rate:.6f}%")
    print(f"Long/Short Ratio: 0.62/0.38")
    
    # Create sentiment indicator with proper config structure
    config = {
        # Required timeframes config
        "timeframes": {
            "base": {
                "interval": "5",
                "weight": 0.4,
                "validation": {
                    "min_candles": 50
                }
            },
            "ltf": {
                "interval": "1",
                "weight": 0.2,
                "validation": {
                    "min_candles": 50
                }
            },
            "mtf": {
                "interval": "15",
                "weight": 0.3,
                "validation": {
                    "min_candles": 50
                }
            },
            "htf": {
                "interval": "60",
                "weight": 0.1,
                "validation": {
                    "min_candles": 50
                }
            }
        },
        # Validation requirements
        "validation_requirements": {
            "trades": {
                "min_trades": 50,
                "max_age": 3600
            },
            "orderbook": {
                "min_levels": 10
            }
        },
        # Sentiment-specific configuration
        "analysis": {
            "indicators": {
                "sentiment": {
                    "funding_threshold": 0.01,
                    "liquidation_threshold": 1000000,
                    "window": 20
                }
            }
        },
        # Confluence configuration with correct component weights
        "confluence": {
            "weights": {
                "sub_components": {
                    "sentiment": {
                        "funding_rate": 0.15,
                        "funding_rate_volatility": 0.1,
                        "long_short_ratio": 0.2,
                        "liquidation_events": 0.2,
                        "volume_sentiment": 0.15,
                        "market_mood": 0.1,
                        "risk_score": 0.1
                    }
                }
            }
        }
    }
    
    sentiment = SentimentIndicators(config)
    
    # Generate complete market data
    now = datetime.now()
    market_data = {
        # Ticker data
        "ticker": {
            "last": current_price,
            "bid": current_price - 5,
            "ask": current_price + 5,
            "volume": 4500000,
            "timestamp": int(now.timestamp() * 1000)
        },
        
        # OHLCV data - last 24 candles (hourly)
        "ohlcv": generate_ohlcv_data(current_price, 24),
        
        # Funding rate data
        "funding_rate": {
            "current_rate": funding_rate / 100,  # Convert to decimal
            "predicted_rate": funding_rate / 100 * 0.9,  # Slightly lower predicted rate
            "next_funding_time": int((now + timedelta(hours=8)).timestamp() * 1000),
            "history": generate_funding_history(funding_rate / 100)
        },
        
        # Long/short ratio data - Slightly bullish
        "long_short_ratio": {
            "long_ratio": 0.62,
            "short_ratio": 0.38,
            "history": generate_long_short_history(0.62, 0.38)
        },
        
        # Liquidation data - Add significant short liquidations
        "liquidations": generate_liquidation_data(),
        
        # Trade data for volume sentiment
        "trades": generate_trade_data(current_price),
        
        # Risk limit data
        "risk_limit": {
            "levels": [
                {
                    "id": 1,
                    "symbol": symbol,
                    "starting_margin": 0.02,  # 2% initial margin
                    "maintain_margin": 0.01,  # 1% maintenance margin
                    "limit": 200000  # Position limit for this tier
                },
                {
                    "id": 2,
                    "symbol": symbol,
                    "starting_margin": 0.025,
                    "maintain_margin": 0.0125,
                    "limit": 500000
                },
                {
                    "id": 3,
                    "symbol": symbol,
                    "starting_margin": 0.03,
                    "maintain_margin": 0.015,
                    "limit": 1000000
                },
                {
                    "id": 4,
                    "symbol": symbol,
                    "starting_margin": 0.04,
                    "maintain_margin": 0.02,
                    "limit": 2000000
                }
            ],
            "current_level": 1,
            "current_utilization": 0.7  # 70% of the level is utilized
        },
        
        # Enhanced sentiment data
        "sentiment": {
            "fear_greed_index": 42,  # Slightly fearful
            "social_sentiment": 0.28,  # Slightly negative
            "search_trends": 115,  # Above average search activity
            "positive_mentions": 0.45,  # Slightly more negative mentions
            "negative_mentions": 0.55
        },
        
        # Market statistics
        "market_stats": {
            "24h_volume": 8500000000,  # 24h volume in USD
            "24h_change": -2.8,  # 24h price change in percent
            "30d_volatility": 4.2  # 30-day volatility
        }
    }
    
    print("\nCalculating sentiment score (sync)...")
    start_time = datetime.now()
    result = await sentiment.calculate(market_data)
    calc_time = (datetime.now() - start_time).total_seconds() * 1000  # in ms
    
    print(f"\n=== Sentiment Analysis Results (Sync) ===")
    if isinstance(result, dict):
        print(f"Overall Sentiment Score: {result['score']:.2f}")
        print(f"\nInterpretation:")
        for key, value in result.items():
            if key not in ['score', 'signals', 'component_scores']:
                print(f"  {key}: {value}")
    else:
        # Handle the case where result is a float
        print(f"Overall Sentiment Score: {result:.2f}")
    
    return result

def generate_ohlcv_data(current_price, num_candles=24):
    """Generate realistic OHLCV data with a slight downtrend."""
    ohlcv_data = []
    now = datetime.now()
    
    # Start from 24 hours ago and move forward
    base_price = current_price * 1.025  # Start slightly higher
    volatility = 0.015  # 1.5% volatility
    
    for i in range(num_candles):
        # Calculate time for this candle
        candle_time = now - timedelta(hours=num_candles-i)
        timestamp = int(candle_time.timestamp() * 1000)
        
        # Generate realistic price action with slight downtrend
        trend_factor = -0.001 * i  # Slight downtrend
        random_move = np.random.normal(trend_factor, volatility)
        
        # Calculate candle prices
        close_price = base_price * (1 + random_move)
        high_price = close_price * (1 + abs(np.random.normal(0, volatility/2)))
        low_price = close_price * (1 - abs(np.random.normal(0, volatility/2)))
        open_price = base_price
        
        # Ensure high is highest and low is lowest
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        # Generate realistic volume with random spikes
        base_volume = 5000 + np.random.normal(0, 2000)
        volume = max(1000, base_volume * (1 + abs(random_move*5)))
        
        # Set base price for next candle
        base_price = close_price
        
        ohlcv_data.append([timestamp, open_price, high_price, low_price, close_price, volume])
    
    return ohlcv_data

def generate_funding_history(current_rate, num_periods=8):
    """Generate funding rate history with a slight negative bias."""
    history = []
    now = datetime.now()
    
    # Start from 8 funding periods ago (normally 8 hours each)
    base_rate = current_rate * 0.8  # Start with a less negative value
    volatility = 0.0001  # Volatility in funding rate changes
    
    for i in range(num_periods):
        # Calculate time for this funding rate
        period_time = now - timedelta(hours=8*(num_periods-i))
        timestamp = int(period_time.timestamp() * 1000)
        
        # Generate realistic funding rate with increasing negative bias
        trend_factor = -0.00002 * i  # Increasing negative bias
        random_move = np.random.normal(trend_factor, volatility)
        
        rate = base_rate + random_move
        
        # Set base rate for next period
        base_rate = rate
        
        history.append({"timestamp": timestamp, "rate": rate})
    
    return history

def generate_long_short_history(long_ratio, short_ratio, num_periods=24):
    """Generate long/short ratio history with slight variations."""
    history = []
    now = datetime.now()
    
    # Start from 24 hours ago
    base_long_ratio = long_ratio * 0.95  # Start with a less bullish ratio
    volatility = 0.02  # Volatility in ratio changes
    
    for i in range(num_periods):
        # Calculate time for this ratio
        period_time = now - timedelta(hours=num_periods-i)
        timestamp = int(period_time.timestamp() * 1000)
        
        # Generate realistic ratio with increasing bullish bias
        trend_factor = 0.001 * i  # Increasing bullish bias
        random_move = np.random.normal(trend_factor, volatility)
        
        # Ensure ratio stays within bounds
        period_long_ratio = max(0.3, min(0.7, base_long_ratio + random_move))
        period_short_ratio = 1 - period_long_ratio
        
        # Set base ratio for next period
        base_long_ratio = period_long_ratio
        
        history.append({
            "timestamp": timestamp, 
            "long_ratio": period_long_ratio, 
            "short_ratio": period_short_ratio
        })
    
    return history

def generate_liquidation_data():
    """Generate liquidation data with significant short liquidations."""
    now = datetime.now()
    
    # Create a 24-hour window of liquidation data
    liquidation_data = {
        "last24h": {
            "total": 52500000,  # $52.5M total liquidations
            "long": 12500000,   # $12.5M long liquidations
            "short": 40000000   # $40M short liquidations (bearish indicator)
        },
        "history": []
    }
    
    # Generate hourly liquidation history
    for i in range(24):
        hour_time = now - timedelta(hours=24-i)
        timestamp = int(hour_time.timestamp() * 1000)
        
        # More shorts liquidated in recent hours
        recency_factor = min(3, 1 + (i / 8))
        
        # Base liquidation values
        base_long = 500000 + (np.random.random() * 300000)
        base_short = 1500000 + (np.random.random() * 900000 * recency_factor)
        
        liquidation_data["history"].append({
            "timestamp": timestamp,
            "long": base_long,
            "short": base_short,
            "total": base_long + base_short
        })
    
    return liquidation_data

def generate_trade_data(current_price, num_trades=100):
    """Generate realistic trade data with a slight buy bias."""
    trades = []
    now = datetime.now()
    
    # Start from 15 minutes ago
    start_time = now - timedelta(minutes=15)
    
    # Set up trade parameters
    buy_probability = 0.58  # Slight buy bias
    price_volatility = 0.0005  # 0.05% price volatility between trades
    size_base = 0.2  # Base size in BTC
    size_volatility = 0.3  # 30% volatility in size
    
    # Generate random trades
    for i in range(num_trades):
        # Calculate trade time
        seconds_ago = int((num_trades - i) * 15 * 60 / num_trades)
        trade_time = start_time + timedelta(seconds=seconds_ago)
        timestamp = int(trade_time.timestamp() * 1000)
        
        # Determine if buy or sell
        is_buy = np.random.random() < buy_probability
        
        # Generate price with small random deviation
        price_deviation = np.random.normal(0, price_volatility)
        price = current_price * (1 + price_deviation)
        
        # Generate trade size with random variation
        size_deviation = np.random.exponential(size_volatility)
        size = size_base * (1 + size_deviation)
        
        # Create trade object
        trade = {
            "id": f"t{i}",
            "timestamp": timestamp,
            "side": "buy" if is_buy else "sell",
            "price": price,
            "amount": size,
            "cost": price * size
        }
        
        trades.append(trade)
    
    return trades

async def main():
    print("=== ENHANCED SENTIMENT INDICATOR TEST ===")
    result = await test_sentiment_async()
    sync_result = await test_sentiment_sync()
    print("\nTest completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
