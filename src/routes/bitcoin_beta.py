from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from datetime import datetime, timezone
import json
import logging
from aiomcache import Client

router = APIRouter()
logger = logging.getLogger(__name__)

# Cache client
cache = Client('localhost', 11211)

@router.get("/status")
async def get_bitcoin_beta_status() -> Dict[str, Any]:
    """Get Bitcoin Beta analysis status and latest metrics."""
    try:
        # Import here to avoid circular imports
        from src.reports.bitcoin_beta_report import BitcoinBetaReport
        
        # Initialize reporter
        reporter = BitcoinBetaReport()
        
        # Get latest beta analysis
        try:
            beta_data = await reporter.get_latest_beta_analysis()
            
            return {
                "status": "active",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "beta_coefficient": beta_data.get("beta_coefficient", 0.0),
                "correlation": beta_data.get("correlation", 0.0),
                "r_squared": beta_data.get("r_squared", 0.0),
                "alpha": beta_data.get("alpha", 0.0),
                "volatility_ratio": beta_data.get("volatility_ratio", 0.0),
                "last_update": beta_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "analysis_period": beta_data.get("analysis_period", "30d"),
                "market_regime": beta_data.get("market_regime", "neutral"),
                "confidence_level": beta_data.get("confidence_level", 0.0)
            }
            
        except Exception as e:
            logger.warning(f"Could not get latest beta analysis: {e}")
            # Return default/mock data if analysis fails
            return {
                "status": "inactive",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "beta_coefficient": 0.0,
                "correlation": 0.0,
                "r_squared": 0.0,
                "alpha": 0.0,
                "volatility_ratio": 0.0,
                "last_update": datetime.now(timezone.utc).isoformat(),
                "analysis_period": "30d",
                "market_regime": "neutral",
                "confidence_level": 0.0,
                "message": "Beta analysis temporarily unavailable"
            }
            
    except Exception as e:
        logger.error(f"Error getting Bitcoin Beta status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting Bitcoin Beta status: {str(e)}")

@router.get("/analysis")
async def get_bitcoin_beta_analysis() -> Dict[str, Any]:
    """Get detailed Bitcoin Beta analysis."""
    try:
        from src.reports.bitcoin_beta_report import BitcoinBetaReporter
        
        reporter = BitcoinBetaReporter()
        analysis = await reporter.generate_analysis()
        
        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Error getting Bitcoin Beta analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting analysis: {str(e)}")

@router.get("/realtime")
async def get_realtime_beta() -> Dict[str, Any]:
    """Get real-time beta values from cache"""
    try:
        # Get market overview
        overview_data = await cache.get(b'beta:overview')
        if overview_data:
            overview = json.loads(overview_data.decode())
        else:
            overview = {
                'market_beta': 1.0,
                'btc_dominance': 57.4,
                'total_symbols': 20,
                'high_beta_count': 0,
                'low_beta_count': 0,
                'neutral_beta_count': 0,
                'avg_correlation': 0.0,
                'market_regime': 'NEUTRAL',
                'timestamp': int(datetime.now(timezone.utc).timestamp() * 1000)
            }
        
        # Get all symbol betas
        symbols = []
        symbol_list = [
            'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT',
            'DOTUSDT', 'AVAXUSDT', 'MATICUSDT', 'LINKUSDT',
            'NEARUSDT', 'ATOMUSDT', 'FTMUSDT', 'ALGOUSDT',
            'AAVEUSDT', 'UNIUSDT', 'SUSHIUSDT', 'COMPUSDT',
            'SNXUSDT', 'CRVUSDT', 'MKRUSDT'
        ]
        
        for symbol in symbol_list:
            cache_key = f'beta:values:{symbol}'.encode()
            beta_data = await cache.get(cache_key)
            
            if beta_data:
                symbol_data = json.loads(beta_data.decode())
                symbols.append(symbol_data)
        
        # Sort by 30d beta value (highest first)
        symbols.sort(key=lambda x: x.get('beta_30d', 1.0), reverse=True)
        
        return {
            'status': 'success',
            'overview': overview,
            'symbols': symbols,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting realtime beta data: {e}")
        # Return minimal valid response
        return {
            'status': 'error',
            'overview': {
                'market_beta': 1.0,
                'btc_dominance': 57.4,
                'total_symbols': 0,
                'market_regime': 'NEUTRAL'
            },
            'symbols': [],
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': str(e)
        }

@router.get("/history/{symbol}")
async def get_beta_history(symbol: str) -> Dict[str, Any]:
    """Get historical beta values for charting"""
    try:
        cache_key = f'beta:history:{symbol}'.encode()
        history_data = await cache.get(cache_key)
        
        if history_data:
            history = json.loads(history_data.decode())
        else:
            history = []
        
        # Get current beta value
        current_beta = 1.0
        beta_cache_key = f'beta:values:{symbol}'.encode()
        beta_data = await cache.get(beta_cache_key)
        
        if beta_data:
            beta_values = json.loads(beta_data.decode())
            current_beta = beta_values.get('beta_30d', 1.0)
        
        return {
            'status': 'success',
            'symbol': symbol,
            'history': history,
            'current_beta': current_beta,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting beta history for {symbol}: {e}")
        return {
            'status': 'error',
            'symbol': symbol,
            'history': [],
            'current_beta': 1.0,
            'error': str(e)
        }

@router.get("/health")
async def bitcoin_beta_health() -> Dict[str, Any]:
    """Health check for Bitcoin Beta service."""
    try:
        # Check cache connection
        test_data = await cache.get(b'beta:overview')
        cache_healthy = test_data is not None
        
        # Count symbols with data
        symbols_with_data = 0
        symbol_list = [
            'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT',
            'DOTUSDT', 'AVAXUSDT', 'MATICUSDT', 'LINKUSDT'
        ]
        
        for symbol in symbol_list[:5]:  # Check first 5 for speed
            cache_key = f'beta:values:{symbol}'.encode()
            data = await cache.get(cache_key)
            if data:
                symbols_with_data += 1
        
        return {
            "status": "healthy" if cache_healthy else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "bitcoin_beta",
            "version": "2.0.0",
            "cache_connected": cache_healthy,
            "symbols_with_data": symbols_with_data
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "bitcoin_beta",
            "error": str(e)
        } 