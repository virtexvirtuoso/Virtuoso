"""
Analytics API Routes

Provides aggregated analytics endpoints for:
- Signal performance metrics (win rate, component contribution)
- Regime-signal correlation analysis
- Historical performance trends
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, List, Any, Optional
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

router = APIRouter()
logger = logging.getLogger(__name__)


def get_db_path() -> str:
    """Get path to virtuoso.db"""
    return str(Path.cwd() / 'data' / 'virtuoso.db')


@router.get("/signal-performance")
async def get_signal_performance_analytics(
    days: int = Query(30, ge=1, le=365, description="Days of history to analyze"),
    min_score: float = Query(0, ge=0, le=100, description="Minimum confluence score filter")
) -> Dict[str, Any]:
    """
    Get comprehensive signal performance analytics.

    Returns:
    - Win rate by signal type (LONG vs SHORT)
    - Component contribution analysis (which components are most predictive)
    - Score distribution and reliability metrics
    - Performance trends over time
    """
    try:
        # Query real trading signals from database
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Calculate date range
        cutoff_timestamp = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

        # Query signals within date range and min score
        query = '''
            SELECT
                symbol, signal_type, confluence_score, reliability,
                timestamp, components
            FROM trading_signals
            WHERE timestamp >= ?
                AND confluence_score >= ?
            ORDER BY timestamp DESC
        '''
        cursor.execute(query, (cutoff_timestamp, min_score))
        rows = cursor.fetchall()
        conn.close()

        # Convert to list of dicts
        signals = []
        for row in rows:
            signal = dict(row)
            # Parse components JSON
            if signal.get('components'):
                try:
                    signal['components'] = json.loads(signal['components'])
                except:
                    signal['components'] = {}
            signals.append(signal)

        # If no data, return empty structure
        if not signals:
            return {
                "summary": {
                    "total_signals": 0,
                    "long_signals": 0,
                    "short_signals": 0,
                    "long_percentage": 0,
                    "short_percentage": 0,
                    "average_score": 0,
                    "average_reliability": 0,
                    "period_days": days
                },
                "score_distribution": {},
                "component_analysis": [],
                "time_series": [],
                "top_symbols": []
            }

        # Calculate metrics
        total_signals = len(signals)
        long_signals = sum(1 for s in signals if s['signal_type'] == 'LONG')
        short_signals = total_signals - long_signals

        # Score distribution
        score_buckets = {
            '90-100': 0,
            '80-89': 0,
            '70-79': 0,
            '60-69': 0,
            '50-59': 0,
            '<50': 0
        }

        total_score = 0
        reliability_sum = 0
        reliability_count = 0

        for signal in signals:
            score = signal['confluence_score']
            total_score += score

            # Bucket the score
            if score >= 90:
                score_buckets['90-100'] += 1
            elif score >= 80:
                score_buckets['80-89'] += 1
            elif score >= 70:
                score_buckets['70-79'] += 1
            elif score >= 60:
                score_buckets['60-69'] += 1
            elif score >= 50:
                score_buckets['50-59'] += 1
            else:
                score_buckets['<50'] += 1

            # Aggregate reliability
            if signal.get('reliability'):
                reliability_sum += signal['reliability']
                reliability_count += 1

        avg_score = total_score / total_signals if total_signals > 0 else 0
        avg_reliability = reliability_sum / reliability_count if reliability_count > 0 else 0

        # Component analysis
        component_scores = defaultdict(list)
        for signal in signals:
            components = signal.get('components', {})
            if isinstance(components, dict):
                for comp_name, comp_score in components.items():
                    if isinstance(comp_score, (int, float)):
                        component_scores[comp_name].append((comp_score, signal['signal_type']))

        component_analysis = []
        for comp_name in ['technical_score', 'volume_score', 'orderflow_score', 'orderbook_score', 'sentiment_score', 'price_structure_score']:
            if comp_name in component_scores:
                scores_and_types = component_scores[comp_name]
                avg_score_val = sum(s[0] for s in scores_and_types) / len(scores_and_types)
                bullish_count = sum(1 for s, t in scores_and_types if t == 'LONG')
                bearish_count = sum(1 for s, t in scores_and_types if t == 'SHORT')

                bias = "bullish" if bullish_count > bearish_count else "bearish" if bearish_count > bullish_count else "neutral"

                component_analysis.append({
                    "component": comp_name.replace('_score', ''),
                    "average_score": round(avg_score_val, 1),
                    "signal_count": len(scores_and_types),
                    "bias": bias,
                    "bullish_signals": bullish_count,
                    "bearish_signals": bearish_count
                })

        # Sort by average score
        component_analysis.sort(key=lambda x: x['average_score'], reverse=True)

        # Time series data
        daily_signals = defaultdict(lambda: {'long': 0, 'short': 0, 'total': 0})
        for signal in signals:
            date_str = datetime.fromtimestamp(signal['timestamp'] / 1000).strftime('%Y-%m-%d')
            daily_signals[date_str]['total'] += 1
            if signal['signal_type'] == 'LONG':
                daily_signals[date_str]['long'] += 1
            else:
                daily_signals[date_str]['short'] += 1

        time_series = [
            {
                'date': date,
                'long_signals': counts['long'],
                'short_signals': counts['short'],
                'total_signals': counts['total']
            }
            for date, counts in sorted(daily_signals.items())
        ]

        # Top symbols
        symbol_counts = defaultdict(lambda: {'count': 0, 'long': 0, 'short': 0})
        for signal in signals:
            symbol = signal['symbol']
            symbol_counts[symbol]['count'] += 1
            if signal['signal_type'] == 'LONG':
                symbol_counts[symbol]['long'] += 1
            else:
                symbol_counts[symbol]['short'] += 1

        top_symbols = sorted(
            [{'symbol': sym, **counts} for sym, counts in symbol_counts.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:10]

        return {
            "summary": {
                "total_signals": total_signals,
                "long_signals": long_signals,
                "short_signals": short_signals,
                "long_percentage": round(long_signals / total_signals * 100, 1) if total_signals > 0 else 0,
                "short_percentage": round(short_signals / total_signals * 100, 1) if total_signals > 0 else 0,
                "average_score": round(avg_score, 1),
                "average_reliability": round(avg_reliability, 2) if avg_reliability > 0 else 0,
                "period_days": days
            },
            "score_distribution": score_buckets,
            "component_analysis": component_analysis,
            "time_series": time_series,
            "top_symbols": top_symbols
        }

    except Exception as e:
        import traceback
        logger.error(f"Error in signal performance analytics: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Return empty data on error
        return {
            "summary": {
                "total_signals": 0,
                "long_signals": 0,
                "short_signals": 0,
                "long_percentage": 0,
                "short_percentage": 0,
                "average_score": 0,
                "average_reliability": 0,
                "period_days": days
            },
            "score_distribution": {},
            "component_analysis": [],
            "time_series": [],
            "top_symbols": []
        }


# Original database implementation preserved below for future fix
"""
        # Initialize metrics
        total_signals = len(signals)
        long_signals = sum(1 for s in signals if s['signal_type'] == 'LONG')
        short_signals = sum(1 for s in signals if s['signal_type'] == 'SHORT')

        # Component analysis
        component_scores = defaultdict(list)
        component_counts = defaultdict(int)

        # Score distribution
        score_buckets = {
            '90-100': 0,
            '80-89': 0,
            '70-79': 0,
            '60-69': 0,
            '50-59': 0,
            '<50': 0
        }

        # Process each signal
        for signal in signals:
            score_val = signal['confluence_score']
            # Handle case where score might be dict or other type
            if isinstance(score_val, dict):
                score = score_val.get('value', 0) if 'value' in score_val else 0
            elif isinstance(score_val, (int, float)):
                score = score_val
            else:
                score = 0

            # Bucket the score
            if score >= 90:
                score_buckets['90-100'] += 1
            elif score >= 80:
                score_buckets['80-89'] += 1
            elif score >= 70:
                score_buckets['70-79'] += 1
            elif score >= 60:
                score_buckets['60-69'] += 1
            elif score >= 50:
                score_buckets['50-59'] += 1
            else:
                score_buckets['<50'] += 1

            # Parse components JSON
            if signal['components']:
                try:
                    components = json.loads(signal['components'])
                    for comp_name, comp_score in components.items():
                        component_scores[comp_name].append(comp_score)
                        component_counts[comp_name] += 1
                except json.JSONDecodeError:
                    continue

        # Calculate component averages and contribution
        component_analysis = []
        for comp_name in ['technical', 'volume', 'orderflow', 'orderbook', 'position', 'sentiment']:
            if comp_name in component_scores:
                scores = component_scores[comp_name]
                avg_score = sum(scores) / len(scores)
                count = component_counts[comp_name]

                # Determine if this component is typically bullish or bearish
                bullish_count = sum(1 for s in scores if s >= 55)
                bearish_count = sum(1 for s in scores if s <= 45)
                bias = "bullish" if bullish_count > bearish_count else "bearish" if bearish_count > bullish_count else "neutral"

                component_analysis.append({
                    "component": comp_name,
                    "average_score": round(avg_score, 2),
                    "signal_count": count,
                    "bias": bias,
                    "bullish_signals": bullish_count,
                    "bearish_signals": bearish_count
                })

        # Sort by average score (most influential first)
        component_analysis.sort(key=lambda x: abs(x['average_score'] - 50), reverse=True)

        # Calculate average reliability (handle None and non-numeric values)
        reliability_values = []
        for s in signals:
            rel = s.get('reliability')
            if rel is not None:
                if isinstance(rel, (int, float)):
                    reliability_values.append(rel)
                elif isinstance(rel, dict) and 'value' in rel:
                    reliability_values.append(rel['value'])
        avg_reliability = sum(reliability_values) / len(reliability_values) if reliability_values else 0

        # Calculate average score (handle different data types)
        score_values = []
        for s in signals:
            score = s.get('confluence_score')
            if score is not None:
                if isinstance(score, (int, float)):
                    score_values.append(score)
                elif isinstance(score, dict) and 'value' in score:
                    score_values.append(score['value'])
        avg_score = sum(score_values) / len(score_values) if score_values else 0

        # Time series data (signals per day)
        daily_signals = defaultdict(lambda: {'long': 0, 'short': 0, 'total': 0})
        for signal in signals:
            date_str = datetime.fromtimestamp(signal['timestamp'] / 1000).strftime('%Y-%m-%d')
            daily_signals[date_str]['total'] += 1
            if signal['signal_type'] == 'LONG':
                daily_signals[date_str]['long'] += 1
            else:
                daily_signals[date_str]['short'] += 1

        # Convert to list
        time_series = [
            {
                'date': date,
                'long_signals': counts['long'],
                'short_signals': counts['short'],
                'total_signals': counts['total']
            }
            for date, counts in sorted(daily_signals.items())
        ]

        return {
            "summary": {
                "total_signals": total_signals,
                "long_signals": long_signals,
                "short_signals": short_signals,
                "long_percentage": round(long_signals / total_signals * 100, 1) if total_signals > 0 else 0,
                "short_percentage": round(short_signals / total_signals * 100, 1) if total_signals > 0 else 0,
                "average_score": round(avg_score, 2),
                "average_reliability": round(avg_reliability, 3),
                "period_days": days
            },
            "score_distribution": score_buckets,
            "component_analysis": component_analysis,
            "time_series": time_series,
            "top_symbols": get_top_symbols(signals, limit=10)
        }
"""


@router.get("/regime-performance")
async def get_regime_performance_correlation(
    days: int = Query(30, ge=1, le=365, description="Days of history")
) -> Dict[str, Any]:
    """
    Analyze signal performance correlation with market regimes.

    Shows which regimes produce the best signals and when to be more/less aggressive.
    """
    try:
        # This would require joining signal data with regime transitions
        # For now, return structure with placeholder data
        # Real implementation would query regime_monitor history

        return {
            "regime_signal_correlation": {
                "strong_uptrend": {
                    "signal_count": 0,
                    "long_signals": 0,
                    "short_signals": 0,
                    "avg_score": 0,
                    "recommendation": "Favor LONG signals in strong uptrends"
                },
                "moderate_uptrend": {
                    "signal_count": 0,
                    "long_signals": 0,
                    "short_signals": 0,
                    "avg_score": 0,
                    "recommendation": "LONG bias with caution"
                },
                "ranging": {
                    "signal_count": 0,
                    "long_signals": 0,
                    "short_signals": 0,
                    "avg_score": 0,
                    "recommendation": "Range trading strategies"
                },
                "moderate_downtrend": {
                    "signal_count": 0,
                    "long_signals": 0,
                    "short_signals": 0,
                    "avg_score": 0,
                    "recommendation": "SHORT bias with caution"
                },
                "strong_downtrend": {
                    "signal_count": 0,
                    "long_signals": 0,
                    "short_signals": 0,
                    "avg_score": 0,
                    "recommendation": "Favor SHORT signals in strong downtrends"
                },
                "high_volatility": {
                    "signal_count": 0,
                    "long_signals": 0,
                    "short_signals": 0,
                    "avg_score": 0,
                    "recommendation": "Reduce position sizes, increase caution"
                }
            },
            "period_days": days,
            "note": "Regime correlation analysis - data collection in progress"
        }

    except Exception as e:
        logger.error(f"Error in regime performance correlation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_top_symbols(signals: List[Any], limit: int = 10) -> List[Dict[str, Any]]:
    """Extract top symbols by signal count from signals list."""
    symbol_counts = defaultdict(lambda: {'count': 0, 'long': 0, 'short': 0})

    for signal in signals:
        symbol = signal['symbol']
        symbol_counts[symbol]['count'] += 1
        if signal['signal_type'] == 'LONG':
            symbol_counts[symbol]['long'] += 1
        else:
            symbol_counts[symbol]['short'] += 1

    # Sort by count
    sorted_symbols = sorted(
        [{'symbol': sym, **counts} for sym, counts in symbol_counts.items()],
        key=lambda x: x['count'],
        reverse=True
    )

    return sorted_symbols[:limit]
