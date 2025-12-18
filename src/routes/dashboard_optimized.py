from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
import json
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard-cached", tags=["cached-dashboard"])

# In-memory fallback cache
FALLBACK_CACHE = {}
CACHE_TIMESTAMPS = {}
CACHE_TTL = 30  # 30 seconds

class CircuitBreaker:
    """Simple circuit breaker to prevent cascading failures"""
    def __init__(self, failure_threshold=3, recovery_timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self.is_open = False
        
    def record_success(self):
        self.failure_count = 0
        self.is_open = False
        
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            
    def can_execute(self):
        if not self.is_open:
            return True
        # Check if recovery timeout has passed
        if time.time() - self.last_failure_time > self.recovery_timeout:
            self.is_open = False
            self.failure_count = 0
            return True
        return False

# Circuit breakers for different endpoints
circuit_breakers = {
    'mobile': CircuitBreaker(),
    'overview': CircuitBreaker(),
    'alerts': CircuitBreaker(),
    'opportunities': CircuitBreaker()
}

async def get_cached_or_compute(key: str, compute_func, ttl: int = 30):
    """Get from cache or compute with timeout"""
    # Check circuit breaker
    breaker = circuit_breakers.get(key.split(':')[0])
    if breaker and not breaker.can_execute():
        # Return fallback data if circuit is open
        if key in FALLBACK_CACHE:
            logger.warning(f"Circuit breaker open for {key}, returning fallback data")
            return FALLBACK_CACHE[key]
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    # Check in-memory cache first
    if key in FALLBACK_CACHE:
        timestamp = CACHE_TIMESTAMPS.get(key, 0)
        if time.time() - timestamp < ttl:
            return FALLBACK_CACHE[key]
    
    try:
        # Compute with timeout
        result = await asyncio.wait_for(compute_func(), timeout=2.0)
        # Update cache
        FALLBACK_CACHE[key] = result
        CACHE_TIMESTAMPS[key] = time.time()
        if breaker:
            breaker.record_success()
        return result
    except asyncio.TimeoutError:
        logger.error(f"Timeout computing {key}")
        if breaker:
            breaker.record_failure()
        # Return cached data if available
        if key in FALLBACK_CACHE:
            return FALLBACK_CACHE[key]
        # Return minimal fallback
        return get_fallback_data(key)
    except Exception as e:
        logger.error(f"Error computing {key}: {e}")
        if breaker:
            breaker.record_failure()
        if key in FALLBACK_CACHE:
            return FALLBACK_CACHE[key]
        return get_fallback_data(key)

def get_fallback_data(key: str) -> Dict[str, Any]:
    """Get fallback data for different endpoints"""
    base_response = {
        "status": "fallback",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Using fallback data due to temporary issue"
    }
    
    if "mobile" in key:
        return {
            **base_response,
            "market_metrics": {
                "breadth": {"advancing": 0, "declining": 0, "neutral": 0},
                "sentiment": 50,
                "volume_ratio": 1.0
            },
            "confluence_scores": [],
            "alerts": [],
            "opportunities": []
        }
    elif "overview" in key:
        return {
            **base_response,
            "summary": {
                "total_symbols": 0,
                "active_signals": 0,
                "market_trend": "neutral"
            },
            "top_movers": [],
            "recent_signals": []
        }
    elif "alerts" in key:
        return {
            **base_response,
            "alerts": [],
            "count": 0
        }
    elif "opportunities" in key:
        return {
            **base_response,
            "opportunities": [],
            "count": 0
        }
    return base_response

@router.get("/mobile-data")
async def get_mobile_dashboard_data():
    """Optimized mobile dashboard data endpoint"""
    async def compute():
        # Simulate data gathering (replace with actual logic)
        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "market_metrics": {
                "breadth": {
                    "advancing": 15,
                    "declining": 10,
                    "neutral": 5
                },
                "sentiment": 65,
                "volume_ratio": 1.2
            },
            "confluence_scores": [
                {"symbol": "BTC-USDT", "score": 75, "direction": "bullish"},
                {"symbol": "ETH-USDT", "score": 68, "direction": "bullish"}
            ],
            "alerts": [],
            "opportunities": [
                {"symbol": "BTC-USDT", "type": "breakout", "confidence": 0.8}
            ]
        }
    
    return await get_cached_or_compute("mobile:data", compute)

@router.get("/overview")
async def get_dashboard_overview():
    """Optimized dashboard overview endpoint"""
    async def compute():
        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_symbols": 30,
                "active_signals": 5,
                "market_trend": "bullish",
                "avg_confluence": 62.5
            },
            "top_movers": [
                {"symbol": "BTC-USDT", "change": 2.5},
                {"symbol": "ETH-USDT", "change": 1.8}
            ],
            "recent_signals": [
                {
                    "symbol": "BTC-USDT",
                    "signal": "buy",
                    "confidence": 0.75,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ]
        }
    
    return await get_cached_or_compute("overview:data", compute)

@router.get("/alerts")
async def get_dashboard_alerts(
    limit: int = Query(10, description="Number of alerts to return"),
    severity: Optional[str] = Query(None, description="Filter by severity")
):
    """Optimized alerts endpoint"""
    async def compute():
        alerts = [
            {
                "id": "alert_1",
                "symbol": "BTC-USDT",
                "message": "Price breakout detected",
                "severity": "high",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]
        
        return {
            "status": "success",
            "alerts": alerts[:limit],
            "count": len(alerts)
        }
    
    return await get_cached_or_compute(f"alerts:data:{severity}:{limit}", compute)

@router.get("/opportunities")
async def get_trading_opportunities():
    """Get current trading opportunities"""
    async def compute():
        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "opportunities": [
                {
                    "symbol": "BTC-USDT",
                    "type": "momentum",
                    "direction": "long",
                    "confidence": 0.82,
                    "entry": 65000,
                    "target": 68000,
                    "stop": 63500,
                    "risk_reward": 2.5
                },
                {
                    "symbol": "ETH-USDT",
                    "type": "reversal",
                    "direction": "long",
                    "confidence": 0.75,
                    "entry": 3200,
                    "target": 3400,
                    "stop": 3100,
                    "risk_reward": 2.0
                }
            ],
            "count": 2,
            "market_conditions": {
                "trend": "bullish",
                "volatility": "moderate",
                "volume": "above_average"
            }
        }
    
    return await get_cached_or_compute("opportunities:data", compute)

@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    circuit_status = {
        name: "open" if breaker.is_open else "closed"
        for name, breaker in circuit_breakers.items()
    }
    
    cache_size = len(FALLBACK_CACHE)
    cache_hit_rate = 0  # Would need to track this
    
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "circuit_breakers": circuit_status,
        "cache_size": cache_size,
        "cache_hit_rate": cache_hit_rate
    }
