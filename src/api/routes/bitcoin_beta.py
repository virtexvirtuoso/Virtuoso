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
    """Get Bitcoin Beta analysis status and latest metrics from cache."""
    try:
        # Try to get cached beta overview data first (doesn't require reporter initialization)
        overview_data = await cache.get(b'beta:overview')

        if overview_data:
            overview = json.loads(overview_data.decode())
            return {
                "status": "active",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_beta": overview.get("market_beta", 1.0),
                "btc_dominance": overview.get("btc_dominance", 0.0),
                "total_symbols": overview.get("total_symbols", 0),
                "high_beta_count": overview.get("high_beta_count", 0),
                "low_beta_count": overview.get("low_beta_count", 0),
                "avg_correlation": overview.get("avg_correlation", 0.0),
                "market_regime": overview.get("market_regime", "NEUTRAL"),
                "last_update": datetime.fromtimestamp(overview.get("timestamp", 0) / 1000).isoformat() if overview.get("timestamp") else datetime.now(timezone.utc).isoformat(),
                "data_source": "cache"
            }

        # No cached data available - return service info
        return {
            "status": "available",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "description": "Bitcoin Beta Analysis Report Generator",
            "features": [
                "Multi-timeframe beta analysis (4H, 30M, 5M, 1M)",
                "Dynamic symbol selection",
                "Statistical measures for traders",
                "Professional PDF reports with charts"
            ],
            "schedule": {
                "frequency": "Every 6 hours",
                "times": ["00:00 UTC", "06:00 UTC", "12:00 UTC", "18:00 UTC"]
            },
            "cached_data": False,
            "message": "No cached beta data available. Data is populated by the trading service."
        }

    except Exception as e:
        logger.error(f"Error getting Bitcoin Beta status: {e}")
        # Return graceful fallback instead of 500 error
        return {
            "status": "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "message": "Could not retrieve beta status"
        }

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

@router.get("/predictive-signals")
async def get_predictive_signals(
    timeframe: float = 4,
    min_stability: float = 50.0
) -> Dict[str, Any]:
    """
    Get predictive trading signals for all altcoins.

    Returns all 5 signals: lead-lag, dynamic beta, stability, divergence, volatility.

    Args:
        timeframe: Hours of data (1 or 4, default: 4)
        min_stability: Minimum stability score to include (default: 60)

    Returns:
        Dict with predictive analysis for each altcoin
    """
    try:
        from src.core.chart.beta_chart_service import generate_beta_chart_data
        from src.core.analysis.bitcoin_altcoin_predictor import BitcoinAltcoinPredictor
        import pandas as pd

        # Fetch high-granularity data
        chart_data = await generate_beta_chart_data(timeframe_hours=timeframe)

        # Extract BTC and altcoin price series
        btc_data = chart_data['chart_data'].get('BTC', [])
        if not btc_data:
            raise HTTPException(status_code=500, detail="No BTC data available")

        # Convert rebased returns to price series
        # Rebased return formula: rebased[t] = (price[t] / price[0] - 1) * 100
        # So: price[t] = price[0] * (1 + rebased[t] / 100)
        # Start at base price of 100
        btc_prices = pd.Series([100 * (1 + point['value'] / 100) for point in btc_data])

        altcoin_prices = {}
        for symbol, data in chart_data['chart_data'].items():
            if symbol != 'BTC' and len(data) == len(btc_data):
                # Convert rebased returns to price series (same formula as BTC)
                altcoin_prices[symbol] = pd.Series([100 * (1 + point['value'] / 100) for point in data])

        # Run predictive analysis
        predictor = BitcoinAltcoinPredictor()
        results = predictor.analyze_all_altcoins(btc_prices, altcoin_prices)

        # Filter by stability
        filtered_results = [
            r for r in results
            if 'error' not in r and r.get('stability', {}).get('stability_score', 0) >= min_stability
        ]

        # Get volatility overview (applies to all)
        volatility_overview = None
        if filtered_results:
            volatility_overview = filtered_results[0].get('volatility', {})

        # Get actual BTC price from market-overview API
        actual_btc_price = None
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8002/api/dashboard/market-overview', timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        actual_btc_price = data.get('btc_price', 0)
                        if actual_btc_price and actual_btc_price > 1000:
                            logger.info(f"✅ Fetched actual BTC price: ${actual_btc_price:,.2f}")
        except Exception as price_error:
            logger.warning(f"Failed to fetch actual BTC price: {price_error}")

        # Fallback if fetch failed or returned 0
        if not actual_btc_price or actual_btc_price < 1000:
            logger.warning(f"Using normalized BTC price as fallback: ${btc_prices.iloc[-1]:.2f}")
            actual_btc_price = btc_prices.iloc[-1]

        return {
            'status': 'success',
            'timeframe_hours': timeframe,
            'btc_price': actual_btc_price,
            'data_points': len(btc_prices),
            'analysis_count': len(filtered_results),
            'volatility_overview': volatility_overview,
            'results': filtered_results,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error in predictive signals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/actionable-trades")
async def get_actionable_trades(
    timeframe: float = 4,
    min_stability: float = 70.0,
    min_z_score: float = 2.5
) -> Dict[str, Any]:
    """
    Get filtered actionable trading signals only.

    Returns only altcoins with:
    - Stability score >= min_stability
    - Active divergence signal with |Z| >= min_z_score

    Args:
        timeframe: Hours of data (1 or 4, default: 4)
        min_stability: Minimum stability score (default: 70)
        min_z_score: Minimum |Z-score| for divergence (default: 2.5)

    Returns:
        List of actionable trade signals
    """
    try:
        from src.core.chart.beta_chart_service import generate_beta_chart_data
        from src.core.analysis.bitcoin_altcoin_predictor import BitcoinAltcoinPredictor
        import pandas as pd

        # Fetch data
        chart_data = await generate_beta_chart_data(timeframe_hours=timeframe)

        btc_data = chart_data['chart_data'].get('BTC', [])
        if not btc_data:
            raise HTTPException(status_code=500, detail="No BTC data available")

        # Convert rebased returns to price series (same as predictive-signals endpoint)
        btc_prices = pd.Series([100 * (1 + point['value'] / 100) for point in btc_data])

        altcoin_prices = {}
        for symbol, data in chart_data['chart_data'].items():
            if symbol != 'BTC' and len(data) == len(btc_data):
                altcoin_prices[symbol] = pd.Series([100 * (1 + point['value'] / 100) for point in data])

        # Get actionable trades
        predictor = BitcoinAltcoinPredictor()
        actionable = predictor.get_actionable_trades(
            btc_prices=btc_prices,
            altcoin_prices=altcoin_prices,
            min_stability=min_stability,
            min_z_score=min_z_score
        )

        return {
            'status': 'success',
            'timeframe_hours': timeframe,
            'filters': {
                'min_stability': min_stability,
                'min_z_score': min_z_score
            },
            'signals_count': len(actionable),
            'signals': actionable,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting actionable trades: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

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