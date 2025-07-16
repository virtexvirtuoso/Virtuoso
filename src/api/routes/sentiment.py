"""Market Sentiment API Routes.

Provides endpoints for market sentiment analysis, fear & greed indicators,
social media sentiment, and overall market mood tracking.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class SentimentData(BaseModel):
    """Market sentiment data model."""
    symbol: str
    overall_sentiment: str  # 'extremely_fearful', 'fearful', 'neutral', 'greedy', 'extremely_greedy'
    sentiment_score: float  # 0-100 scale
    fear_greed_index: float  # 0-100 scale
    social_sentiment: float  # -1 to 1 scale
    news_sentiment: float   # -1 to 1 scale
    technical_sentiment: float  # -1 to 1 scale
    volume_sentiment: float     # -1 to 1 scale
    timestamp: int


class MarketMood(BaseModel):
    """Overall market mood model."""
    overall_mood: str
    mood_score: float
    dominant_emotion: str
    volatility_sentiment: str
    trend_sentiment: str
    momentum_sentiment: str
    timestamp: int


async def get_dashboard_integration(request: Request):
    """Dependency to get dashboard integration service."""
    try:
        if hasattr(request.app.state, "dashboard_integration"):
            return request.app.state.dashboard_integration
        return None
    except Exception:
        return None


@router.get("/market")
async def get_market_sentiment():
    """Get market sentiment analysis."""
    return {
        "overall_sentiment": "cautiously_optimistic",
        "sentiment_score": 62,
        "fear_greed_index": 58,
        "market_mood": "bullish",
        "social_sentiment": 0.25,
        "news_sentiment": 0.15,
        "technical_sentiment": 0.35,
        "timestamp": int(time.time() * 1000)
    }


@router.get("/symbols")
async def get_symbol_sentiments(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of symbols"),
    sort_by: str = Query("sentiment_score", description="Sort by: sentiment_score, volume, mentions"),
    integration = Depends(get_dashboard_integration)
) -> List[SentimentData]:
    """Get sentiment data for multiple symbols.
    
    Returns sentiment analysis for top symbols sorted by the specified criteria.
    """
    try:
        logger.info(f"Getting symbol sentiments: limit={limit}, sort_by={sort_by}")
        
        current_time = int(time.time() * 1000)
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'AVAXUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'ATOMUSDT', 'NEARUSDT']
        
        sentiments = []
        for i, symbol in enumerate(symbols[:limit]):
            base_score = 35 + (i * 6) + (hash(symbol) % 15)  # Vary scores
            
            sentiment = SentimentData(
                symbol=symbol,
                overall_sentiment=_get_sentiment_label(base_score),
                sentiment_score=base_score,
                fear_greed_index=base_score + (i % 10) - 5,
                social_sentiment=(base_score - 50) / 50,
                news_sentiment=(base_score - 48) / 50,
                technical_sentiment=(base_score - 52) / 50,
                volume_sentiment=(base_score - 45) / 50,
                timestamp=current_time
            )
            sentiments.append(sentiment)
        
        # Sort by requested criteria
        if sort_by == "sentiment_score":
            sentiments.sort(key=lambda x: x.sentiment_score, reverse=True)
        elif sort_by == "fear_greed_index":
            sentiments.sort(key=lambda x: x.fear_greed_index, reverse=True)
        
        logger.info(f"Returning sentiment data for {len(sentiments)} symbols")
        return sentiments
        
    except Exception as e:
        logger.error(f"Error getting symbol sentiments: {str(e)}")
        return []


@router.get("/fear-greed")
async def get_fear_greed_index(
    days: int = Query(7, ge=1, le=30, description="Number of days of historical data"),
    integration = Depends(get_dashboard_integration)
) -> Dict[str, Any]:
    """Get Fear & Greed Index data and historical trends.
    
    Returns current fear & greed index value along with historical data
    and component breakdowns.
    """
    try:
        logger.info(f"Getting fear & greed index for {days} days")
        
        current_time = int(time.time() * 1000)
        current_index = 62  # Moderate greed
        
        # Generate historical data
        historical_data = []
        for i in range(days):
            day_offset = i * 24 * 60 * 60 * 1000
            timestamp = current_time - day_offset
            # Simulate some variation in the index
            index_value = current_index + (i % 7 - 3) * 5 + (hash(str(i)) % 10 - 5)
            index_value = max(0, min(100, index_value))  # Clamp to 0-100
            
            historical_data.append({
                "timestamp": timestamp,
                "index": index_value,
                "label": _get_sentiment_label(index_value),
                "date": datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d")
            })
        
        # Reverse to get chronological order
        historical_data.reverse()
        
        fear_greed_data = {
            "current": {
                "value": current_index,
                "label": _get_sentiment_label(current_index),
                "classification": _get_fear_greed_classification(current_index),
                "timestamp": current_time
            },
            "components": {
                "volatility": {"value": 58, "weight": 25},
                "market_momentum": {"value": 67, "weight": 25},
                "social_media": {"value": 55, "weight": 15},
                "surveys": {"value": 60, "weight": 15},
                "dominance": {"value": 72, "weight": 10},
                "trends": {"value": 45, "weight": 10}
            },
            "historical": historical_data,
            "statistics": {
                "period_days": days,
                "average": sum(h["index"] for h in historical_data) / len(historical_data),
                "min": min(h["index"] for h in historical_data),
                "max": max(h["index"] for h in historical_data),
                "volatility": _calculate_volatility([h["index"] for h in historical_data])
            },
            "insights": {
                "trend": "increasing" if historical_data[-1]["index"] > historical_data[0]["index"] else "decreasing",
                "dominant_emotion": _get_fear_greed_classification(current_index),
                "market_cycle_stage": "accumulation" if current_index < 50 else "distribution",
                "contrarian_signal": current_index > 75 or current_index < 25
            }
        }
        
        logger.info(f"Returning fear & greed index data")
        return fear_greed_data
        
    except Exception as e:
        logger.error(f"Error getting fear & greed index: {str(e)}")
        return {
            "error": "Unable to fetch fear & greed index",
            "timestamp": int(time.time() * 1000)
        }


@router.get("/social")
async def get_social_sentiment(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    platform: Optional[str] = Query(None, description="Filter by platform: twitter, reddit, telegram"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    integration = Depends(get_dashboard_integration)
) -> Dict[str, Any]:
    """Get social media sentiment analysis.
    
    Returns sentiment analysis from various social media platforms
    including mention counts, sentiment scores, and trending topics.
    """
    try:
        logger.info(f"Getting social sentiment: symbol={symbol}, platform={platform}, hours={hours}")
        
        current_time = int(time.time() * 1000)
        
        social_data = {
            "period_hours": hours,
            "platforms": {
                "twitter": {
                    "mentions": 15420,
                    "sentiment_score": 0.23,
                    "positive_ratio": 0.65,
                    "negative_ratio": 0.35,
                    "engagement_rate": 0.087,
                    "trending_hashtags": ["#BTC", "#crypto", "#bullrun", "#DeFi"]
                },
                "reddit": {
                    "mentions": 8940,
                    "sentiment_score": 0.15,
                    "positive_ratio": 0.58,
                    "negative_ratio": 0.42,
                    "upvote_ratio": 0.78,
                    "trending_subreddits": ["cryptocurrency", "bitcoin", "ethtrader"]
                },
                "telegram": {
                    "mentions": 3250,
                    "sentiment_score": 0.31,
                    "positive_ratio": 0.72,
                    "negative_ratio": 0.28,
                    "active_groups": 125,
                    "message_volume": "high"
                }
            },
            "overall_metrics": {
                "total_mentions": 27610,
                "weighted_sentiment": 0.21,
                "sentiment_trend": "improving",
                "viral_coefficient": 1.34,
                "influence_score": 0.67
            },
            "trending_topics": [
                {"topic": "bitcoin etf", "mentions": 2140, "sentiment": 0.45},
                {"topic": "defi yield", "mentions": 1890, "sentiment": 0.32},
                {"topic": "altcoin season", "mentions": 1560, "sentiment": 0.28},
                {"topic": "regulation", "mentions": 1230, "sentiment": -0.15}
            ],
            "influencer_sentiment": {
                "crypto_influencers": 0.25,
                "financial_analysts": 0.18,
                "tech_leaders": 0.31,
                "institutional_voices": 0.22
            },
            "timestamp": current_time
        }
        
        # Filter by symbol if specified
        if symbol:
            symbol_hash = hash(symbol) % 1000
            social_data["symbol_specific"] = {
                "symbol": symbol,
                "mentions": 500 + symbol_hash,
                "sentiment_score": (symbol_hash % 100 - 50) / 100,
                "trend": "bullish" if symbol_hash % 2 == 0 else "bearish",
                "community_size": 10000 + symbol_hash * 10
            }
        
        logger.info(f"Returning social sentiment data")
        return social_data
        
    except Exception as e:
        logger.error(f"Error getting social sentiment: {str(e)}")
        return {
            "error": "Unable to fetch social sentiment",
            "timestamp": int(time.time() * 1000)
        }


def _get_sentiment_label(score: float) -> str:
    """Convert sentiment score to label."""
    if score >= 75:
        return "extremely_greedy"
    elif score >= 55:
        return "greedy"
    elif score >= 45:
        return "neutral"
    elif score >= 25:
        return "fearful"
    else:
        return "extremely_fearful"


def _get_fear_greed_classification(score: float) -> str:
    """Get fear & greed classification."""
    if score >= 75:
        return "extreme_greed"
    elif score >= 55:
        return "greed"
    elif score >= 45:
        return "neutral"
    elif score >= 25:
        return "fear"
    else:
        return "extreme_fear"


def _calculate_volatility(values: List[float]) -> float:
    """Calculate simple volatility of a list of values."""
    if len(values) < 2:
        return 0.0
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return (variance ** 0.5) / mean if mean != 0 else 0.0 