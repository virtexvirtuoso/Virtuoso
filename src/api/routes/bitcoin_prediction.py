"""
Bitcoin Lead/Lag Prediction API Routes

Provides endpoints to inspect Bitcoin prediction data for altcoins
before fully integrating into live trading signals.

Endpoints:
- GET /api/bitcoin-prediction/{symbol} - Get prediction for one symbol
- GET /api/bitcoin-prediction/analyze/all - Analyze all monitored symbols
- GET /api/bitcoin-prediction/status - Get predictor status and config
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Any, Optional
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import traceback
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bitcoin-prediction", tags=["Bitcoin Prediction"])


async def fetch_top_symbols_from_bybit(limit: int = 20) -> List[str]:
    """
    Fetch top symbols directly from Bybit (same logic as trading service's TopSymbolsProvider).
    Returns symbols sorted by 24h turnover (volume * price).

    This ensures Bitcoin prediction uses the SAME symbols as the trading service
    without needing cross-process communication.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Fetch tickers from Bybit public API (same as TopSymbolsProvider does)
            response = await client.get(
                "https://api.bybit.com/v5/market/tickers",
                params={"category": "linear"}
            )

            if response.status_code != 200:
                logger.error(f"Bybit API returned {response.status_code}")
                return []

            data = response.json()
            if data.get('retCode') != 0:
                logger.error(f"Bybit API error: {data.get('retMsg')}")
                return []

            tickers = data.get('result', {}).get('list', [])

            # Filter and calculate turnover (same logic as trading service)
            symbols_with_turnover = []
            for ticker in tickers:
                symbol = ticker.get('symbol', '')
                if not symbol.endswith('USDT'):
                    continue

                try:
                    volume_24h = float(ticker.get('volume24h', 0))
                    last_price = float(ticker.get('lastPrice', 0))
                    turnover = volume_24h * last_price

                    if turnover > 0:
                        symbols_with_turnover.append({
                            'symbol': symbol,
                            'turnover': turnover
                        })
                except (ValueError, TypeError):
                    continue

            # Sort by turnover and get top N (same as trading service)
            symbols_with_turnover.sort(key=lambda x: x['turnover'], reverse=True)
            top_symbols = [s['symbol'] for s in symbols_with_turnover[:limit]]

            logger.info(f"✅ Fetched {len(top_symbols)} top symbols from Bybit (same as trading service)")
            return top_symbols

    except Exception as e:
        logger.error(f"Error fetching symbols from Bybit: {e}")
        return []


def get_btc_predictor():
    """Get Bitcoin predictor instance from service registry."""
    try:
        # Get signal_generator from service registry (avoids circular import)
        from src.core.service_registry import get_signal_generator
        signal_gen = get_signal_generator()

        if signal_gen is None:
            return None, "Signal generator not initialized (system starting up)"

        if signal_gen.btc_predictor is None:
            return None, "Bitcoin predictor not initialized"

        return signal_gen, None
    except Exception as e:
        logger.error(f"Error getting BTC predictor: {e}")
        return None, str(e)


@router.get("/status")
async def get_predictor_status() -> Dict[str, Any]:
    """
    Get Bitcoin predictor status and configuration.

    Returns:
        - enabled: Whether predictor is active
        - config: Current configuration
        - btc_history_length: Number of BTC price points stored
        - ready: Whether predictor has enough data
    """
    try:
        signal_gen, error = get_btc_predictor()

        if error:
            return {
                "enabled": False,
                "error": error,
                "ready": False
            }

        btc_history_length = len(signal_gen.btc_price_history)
        min_required = signal_gen.config.get('bitcoin_prediction', {}).get('min_data_points', 60)

        return {
            "enabled": True,
            "ready": btc_history_length >= min_required,
            "btc_history_length": btc_history_length,
            "min_required": min_required,
            "config": {
                "min_confidence": signal_gen.btc_min_confidence,
                "boost_multiplier": signal_gen.btc_boost_multiplier,
                "full_config": signal_gen.config.get('bitcoin_prediction', {})
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting predictor status: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}")
async def get_prediction(
    symbol: str,
    include_raw_analysis: bool = Query(False, description="Include full analysis details")
) -> Dict[str, Any]:
    """
    Get Bitcoin lead/lag prediction for a specific altcoin.

    Args:
        symbol: Trading pair symbol (e.g., 'ETHUSDT')
        include_raw_analysis: Include full raw analysis from predictor

    Returns:
        Prediction data including:
        - active: Whether prediction signal is active
        - confidence: Prediction confidence (0-1)
        - boost_points: Confluence score boost amount
        - direction: Predicted direction ('long', 'short', 'neutral')
        - expected_move_pct: Expected altcoin move %
        - lag_minutes: Detected lag time
        - beta: Current beta coefficient
        - stability_score: Beta stability (0-100)
    """
    try:
        signal_gen, error = get_btc_predictor()

        if error:
            raise HTTPException(status_code=503, detail=f"Predictor unavailable: {error}")

        # Check if we have enough BTC history
        if len(signal_gen.btc_price_history) < 60:
            return {
                "symbol": symbol,
                "active": False,
                "error": "Insufficient BTC price history",
                "btc_history_length": len(signal_gen.btc_price_history),
                "min_required": 60,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Get prediction signal
        btc_signal = signal_gen._get_btc_prediction_signal(symbol)

        if btc_signal is None:
            # Try to get more detailed error by running analysis directly
            btc_prices = pd.Series([p['price'] for p in signal_gen.btc_price_history])

            # Try to get altcoin prices
            alt_prices = signal_gen._get_altcoin_prices(symbol)

            if alt_prices is None:
                return {
                    "symbol": symbol,
                    "active": False,
                    "error": "Could not fetch altcoin price data",
                    "suggestion": "Ensure market_data_manager is properly configured",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            # Run full analysis for debugging
            btc_returns = np.log(btc_prices / btc_prices.shift(1)).fillna(0)
            recent_btc_move_pct = btc_returns.iloc[-5:].sum() * 100

            analysis = signal_gen.btc_predictor.analyze_altcoin(
                symbol=symbol,
                btc_prices=btc_prices,
                alt_prices=alt_prices,
                btc_recent_move_pct=recent_btc_move_pct
            )

            if 'error' in analysis:
                return {
                    "symbol": symbol,
                    "active": False,
                    "error": analysis['error'],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            # Analysis succeeded but signal not active - return why
            lead_lag = analysis.get('lead_lag', {})
            stability = analysis.get('stability', {})

            reasons = []
            if not lead_lag.get('signal_active'):
                reasons.append(f"Lead/lag signal not active (BTC move: {recent_btc_move_pct:.2f}%)")
            if stability.get('stability_score', 0) < 50:
                reasons.append(f"Stability too low: {stability.get('stability_score', 0):.1f}/100")

            result = {
                "symbol": symbol,
                "active": False,
                "reasons": reasons,
                "recent_btc_move_pct": recent_btc_move_pct,
                "stability_score": stability.get('stability_score', 0),
                "beta": analysis.get('beta', 0),
                "r_squared": analysis.get('r_squared', 0),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            if include_raw_analysis:
                result['raw_analysis'] = analysis

            return result

        # Signal is active - return full prediction data
        result = {
            "symbol": symbol,
            "active": True,
            "prediction": btc_signal,
            "impact": {
                "example_score_55": 55 + btc_signal['boost_points'],
                "example_score_60": 60 + btc_signal['boost_points'],
                "example_score_65": 65 + btc_signal['boost_points'],
                "note": "Shows how different base scores would be affected"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prediction for {symbol}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/all")
async def analyze_all_symbols(
    symbols: Optional[List[str]] = Query(None, description="Symbols to analyze (default: top altcoins)")
) -> Dict[str, Any]:
    """
    Analyze Bitcoin predictions for multiple symbols.

    Args:
        symbols: List of symbols to analyze (if not provided, uses default list)

    Returns:
        Dictionary with predictions for each symbol, sorted by confidence
    """
    try:
        signal_gen, error = get_btc_predictor()

        if error:
            raise HTTPException(status_code=503, detail=f"Predictor unavailable: {error}")

        # Default symbols if none provided - fetch from Bybit (same as trading service does)
        if symbols is None:
            # Fetch top symbols directly from Bybit using same logic as trading service
            # This ensures both services independently get the same symbols
            fetched_symbols = await fetch_top_symbols_from_bybit(limit=20)

            if fetched_symbols:
                # Filter out BTCUSDT since we're predicting based on BTC
                symbols = [s for s in fetched_symbols if s != 'BTCUSDT']
                logger.info(f"📊 Bitcoin prediction using {len(symbols)} top symbols")
            else:
                # Fallback if Bybit fetch fails
                logger.warning("Failed to fetch symbols from Bybit, using fallback list")
                symbols = [
                    'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'AVAXUSDT',
                    'DOTUSDT', 'MATICUSDT', 'LINKUSDT', 'UNIUSDT', 'ATOMUSDT'
                ]

        # Check BTC history
        if len(signal_gen.btc_price_history) < 60:
            return {
                "error": "Insufficient BTC price history",
                "btc_history_length": len(signal_gen.btc_price_history),
                "min_required": 60,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        results = []
        btc_prices = pd.Series([p['price'] for p in signal_gen.btc_price_history])
        btc_returns = np.log(btc_prices / btc_prices.shift(1)).fillna(0)
        recent_btc_move_pct = btc_returns.iloc[-5:].sum() * 100

        for symbol in symbols:
            try:
                btc_signal = signal_gen._get_btc_prediction_signal(symbol)

                if btc_signal is not None:
                    results.append({
                        "symbol": symbol,
                        "active": True,
                        "confidence": btc_signal['confidence'],
                        "boost_points": btc_signal['boost_points'],
                        "direction": btc_signal['direction'],
                        "expected_move_pct": btc_signal['expected_move_pct'],
                        "lag_minutes": btc_signal['lag_minutes'],
                        "beta": btc_signal['beta'],
                        "stability_score": btc_signal['stability_score']
                    })

                    # Send Discord alert for active predictions with high confidence
                    if btc_signal['confidence'] >= 0.7:  # Only alert on >70% confidence
                        try:
                            await signal_gen.send_bitcoin_prediction_alert(
                                symbol=symbol,
                                prediction=btc_signal,
                                btc_move_pct=recent_btc_move_pct
                            )
                        except Exception as alert_error:
                            logger.warning(f"Failed to send alert for {symbol}: {alert_error}")
                else:
                    results.append({
                        "symbol": symbol,
                        "active": False,
                        "reason": "Signal not active or insufficient data"
                    })

            except Exception as e:
                logger.warning(f"Error analyzing {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "active": False,
                    "error": str(e)
                })

        # Sort by confidence (active signals first, then by confidence)
        results.sort(key=lambda x: (x.get('active', False), x.get('confidence', 0)), reverse=True)

        # Summary statistics
        active_count = sum(1 for r in results if r.get('active', False))
        avg_confidence = np.mean([r['confidence'] for r in results if r.get('active', False)]) if active_count > 0 else 0

        return {
            "summary": {
                "total_symbols": len(symbols),
                "active_signals": active_count,
                "avg_confidence": round(float(avg_confidence), 3),
                "btc_history_length": len(signal_gen.btc_price_history)
            },
            "predictions": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing all symbols: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/btc-history")
async def get_btc_history(
    limit: int = Query(60, ge=1, le=240, description="Number of recent prices to return")
) -> Dict[str, Any]:
    """
    Get recent BTC price history for debugging.

    Args:
        limit: Number of recent prices to return (1-240)

    Returns:
        Recent BTC prices with timestamps
    """
    try:
        signal_gen, error = get_btc_predictor()

        if error:
            raise HTTPException(status_code=503, detail=f"Predictor unavailable: {error}")

        history = list(signal_gen.btc_price_history)[-limit:]

        if len(history) == 0:
            return {
                "error": "No BTC price history available",
                "suggestion": "Call signal_generator.update_btc_price() to populate history",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Calculate some basic stats
        prices = [p['price'] for p in history]
        returns = np.diff(prices) / prices[:-1] * 100  # percentage returns

        return {
            "count": len(history),
            "oldest_timestamp": history[0]['timestamp'],
            "newest_timestamp": history[-1]['timestamp'],
            "price_range": {
                "min": float(np.min(prices)),
                "max": float(np.max(prices)),
                "current": history[-1]['price']
            },
            "statistics": {
                "mean_return_pct": float(np.mean(returns)),
                "std_return_pct": float(np.std(returns)),
                "total_change_pct": float((prices[-1] - prices[0]) / prices[0] * 100)
            },
            "recent_prices": [
                {
                    "timestamp": p['timestamp'],
                    "price": p['price'],
                    "datetime": datetime.fromtimestamp(p['timestamp'], tz=timezone.utc).isoformat()
                }
                for p in history
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting BTC history: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
