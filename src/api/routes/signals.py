"""Consolidated Signals API Routes - Phase 2 API Consolidation

This module consolidates the following endpoints:
- Signal tracking and analysis (original signals.py)
- Alert management and persistence (alerts.py) 
- Whale activity monitoring (whale_activity.py)

Backward compatibility maintained for all existing endpoints.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Request
import time
import logging
import yaml
from pydantic import BaseModel, Field

from ..models.signals import Signal, SignalList, SymbolSignals, LatestSignals

router = APIRouter()

# Path to the signals JSON directory
SIGNALS_DIR = Path("reports/json")

# Load configuration to check if signal tracking is enabled
def is_signal_tracking_enabled() -> bool:
    """Check if signal tracking is enabled in configuration."""
    logger = logging.getLogger(__name__)
    try:
        # Try multiple possible config paths
        possible_paths = [
            Path("config/config.yaml"),
            Path("../config/config.yaml"),
            Path("../../config/config.yaml"),
            Path("/Users/ffv_macmini/Desktop/Virtuoso_ccxt/config/config.yaml")
        ]
        
        config_path = None
        for path in possible_paths:
            if path.exists():
                config_path = path
                break
        
        if config_path:
            logger.debug(f"Found config at: {config_path.absolute()}")
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                signal_tracking_config = config.get('signal_tracking', {})
                enabled = signal_tracking_config.get('enabled', True)
                logger.info(f"Signal tracking config: enabled={enabled}")
                return enabled
        else:
            logger.warning(f"Config file not found in any of these paths: {[str(p) for p in possible_paths]}")
    except Exception as e:
        logger.error(f"Error reading signal tracking config: {e}")
    
    logger.warning("Defaulting to signal tracking enabled due to config read failure")
    return True  # Default to enabled if config can't be read

def get_database_client(request: Request):
    """Dependency to get database client from app state"""
    if hasattr(request.app.state, "database_client"):
        return request.app.state.database_client
    return None

@router.get("/signals/latest", response_model=LatestSignals)
async def get_latest_signals(
    limit: int = Query(5, ge=1, le=20, description="Number of latest signals to return"),
    db_client = Depends(get_database_client)
) -> LatestSignals:
    """
    Get the latest signals across all symbols.
    """
    logger = logging.getLogger(__name__)
    
    try:
        if not SIGNALS_DIR.exists():
            logger.warning(f"Signals directory not found: {SIGNALS_DIR}")
            return LatestSignals(count=0, signals=[])
        
        # Get all JSON files with a reasonable limit to prevent timeout
        all_files = []
        file_count = 0
        max_files_to_check = 1000  # Limit file scanning to prevent timeouts
        
        for file_path in SIGNALS_DIR.glob("*.json"):
            if file_path.is_file():
                all_files.append(file_path)
                file_count += 1
                if file_count >= max_files_to_check:
                    break
        
        logger.info(f"Found {len(all_files)} signal files to process")
        
        if not all_files:
            logger.info("No signal files found")
            return LatestSignals(count=0, signals=[])
        
        # Sort files by modification time (newest first) - limit to prevent timeout
        try:
            all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        except Exception as e:
            logger.warning(f"Error sorting files by modification time: {e}")
            # Fall back to filename sorting
            all_files.sort(key=lambda x: x.name, reverse=True)
        
        latest_signals = []
        processed_count = 0
        max_process = min(limit * 3, 50)  # Process at most 3x limit or 50 files
        
        # Take the top N files
        for file_path in all_files[:max_process]:
            try:
                with open(file_path, 'r') as f:
                    signal_data = json.load(f)
                
                signal_data['filename'] = file_path.name
                signal_data['file_path'] = str(file_path)
                
                # Quick validation - don't use pydantic model validation for speed
                if isinstance(signal_data, dict) and signal_data.get('symbol'):
                    latest_signals.append(signal_data)
                    
                processed_count += 1
                
                # Stop once we have enough signals
                if len(latest_signals) >= limit:
                    break
                    
            except Exception as e:
                logger.debug(f"Error processing file {file_path}: {e}")
                continue
        
        logger.info(f"Successfully processed {processed_count} files, returning {len(latest_signals)} signals")
        
        return LatestSignals(
            count=len(latest_signals),
            signals=latest_signals[:limit]
        )
        
    except Exception as e:
        logger.error(f"Error in get_latest_signals: {e}")
        # Return empty result instead of raising exception
        return LatestSignals(count=0, signals=[])

# =============================================================================
# ALERTS ENDPOINTS (from alerts.py)
# =============================================================================

# Import alert persistence
try:
    from src.monitoring.alert_persistence import AlertPersistence, AlertStatus
except ImportError:
    try:
        from monitoring.alert_persistence import AlertPersistence, AlertStatus
    except ImportError:
        AlertPersistence = None
        AlertStatus = None

class AlertData(BaseModel):
    """Alert data model for API responses"""
    id: str
    level: str
    message: str
    details: Dict[str, Any] = {}
    timestamp: float
    source: Optional[str] = None
    alert_type: Optional[str] = None
    symbol: Optional[str] = None
    resolved: bool = False
    acknowledged: bool = False

class AlertCreateRequest(BaseModel):
    """Request model for creating alerts via API"""
    level: str = Field(..., regex="^(INFO|WARNING|ERROR|CRITICAL)$")
    message: str
    details: Optional[Dict[str, Any]] = {}
    source: Optional[str] = None
    alert_type: Optional[str] = None
    symbol: Optional[str] = None

async def get_alert_manager(request: Request):
    """Dependency to get alert manager from app state"""
    if not hasattr(request.app.state, "alert_manager"):
        raise HTTPException(status_code=503, detail="Alert manager not initialized")
    return request.app.state.alert_manager

@router.get("/alerts", response_model=List[AlertData])
async def get_alerts(
    level: Optional[str] = Query(None, description="Filter by alert level"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of alerts"),
    start_time: Optional[float] = Query(None, description="Start timestamp filter"),
    end_time: Optional[float] = Query(None, description="End timestamp filter"),
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    alert_manager = Depends(get_alert_manager)
) -> List[AlertData]:
    """Get alerts with optional filtering."""
    try:
        # Get alerts from alert manager
        alerts = alert_manager.get_alerts(
            level=level,
            limit=limit,
            start_time=start_time
        )
        
        # Convert to AlertData format and apply additional filters
        alert_data = []
        for alert in alerts:
            # Apply additional filters
            if alert_type and alert.get('details', {}).get('type') != alert_type:
                continue
            if symbol and alert.get('details', {}).get('symbol') != symbol:
                continue
            if source and alert.get('details', {}).get('source') != source:
                continue
            if end_time and alert.get('timestamp', 0) > end_time:
                continue
            if resolved is not None and alert.get('resolved', False) != resolved:
                continue
            
            alert_data.append(AlertData(
                id=alert.get('id', str(int(alert.get('timestamp', time.time()) * 1000000))),
                level=alert.get('level', 'INFO'),
                message=alert.get('message', ''),
                details=alert.get('details', {}),
                timestamp=alert.get('timestamp', time.time()),
                source=alert.get('details', {}).get('source'),
                alert_type=alert.get('details', {}).get('type'),
                symbol=alert.get('details', {}).get('symbol'),
                resolved=alert.get('resolved', False),
                acknowledged=alert.get('acknowledged', False)
            ))
        
        return alert_data
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {str(e)}")

@router.get("/alerts/recent", response_model=List[AlertData])
async def get_recent_alerts(
    limit: int = Query(20, ge=1, le=100, description="Number of recent alerts"),
    level: Optional[str] = Query(None, description="Filter by alert level"),
    alert_manager = Depends(get_alert_manager)
) -> List[AlertData]:
    """Get recent alerts for dashboard display."""
    try:
        # Get recent alerts (last hour by default)
        one_hour_ago = time.time() - 3600
        alerts = alert_manager.get_alerts(
            level=level,
            limit=limit,
            start_time=one_hour_ago
        )
        
        # Convert to AlertData format
        alert_data = []
        for alert in alerts:
            alert_data.append(AlertData(
                id=alert.get('id', str(int(alert.get('timestamp', time.time()) * 1000000))),
                level=alert.get('level', 'INFO'),
                message=alert.get('message', ''),
                details=alert.get('details', {}),
                timestamp=alert.get('timestamp', time.time()),
                source=alert.get('details', {}).get('source'),
                alert_type=alert.get('details', {}).get('type'),
                symbol=alert.get('details', {}).get('symbol'),
                resolved=alert.get('resolved', False),
                acknowledged=alert.get('acknowledged', False)
            ))
        
        # Sort by timestamp (most recent first)
        alert_data.sort(key=lambda x: x.timestamp, reverse=True)
        
        return alert_data
        
    except Exception as e:
        logger.error(f"Error getting recent alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving recent alerts: {str(e)}")

@router.get("/alerts/stats", response_model=Dict[str, Any])
async def get_alert_stats(
    alert_manager = Depends(get_alert_manager)
) -> Dict[str, Any]:
    """Get alert statistics and metrics."""
    try:
        stats = alert_manager.get_alert_stats()
        
        # Add additional computed stats
        total_alerts = stats.get('total', 0)
        stats['success_rate'] = (
            stats.get('sent', 0) / total_alerts * 100 
            if total_alerts > 0 else 0
        )
        stats['error_rate'] = (
            stats.get('errors', 0) / total_alerts * 100 
            if total_alerts > 0 else 0
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting alert stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving alert stats: {str(e)}")

@router.get("/alerts/summary", response_model=Dict[str, Any])
async def get_alert_summary(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    alert_manager = Depends(get_alert_manager)
) -> Dict[str, Any]:
    """Get alert summary for the specified time period."""
    try:
        # Calculate start time
        start_time = time.time() - (hours * 3600)
        
        # Get alerts for the period
        alerts = alert_manager.get_alerts(start_time=start_time)
        
        # Calculate summary statistics
        summary = {
            'period_hours': hours,
            'total_alerts': len(alerts),
            'by_level': {'INFO': 0, 'WARNING': 0, 'ERROR': 0, 'CRITICAL': 0},
            'by_type': {},
            'by_symbol': {},
            'by_source': {},
            'most_recent': None,
            'most_critical': None
        }
        
        most_recent_timestamp = 0
        most_critical_level = 0
        level_priority = {'INFO': 1, 'WARNING': 2, 'ERROR': 3, 'CRITICAL': 4}
        
        for alert in alerts:
            level = alert.get('level', 'INFO')
            alert_type = alert.get('details', {}).get('type', 'unknown')
            symbol = alert.get('details', {}).get('symbol', 'unknown')
            source = alert.get('details', {}).get('source', 'unknown')
            timestamp = alert.get('timestamp', 0)
            
            # Count by level
            if level in summary['by_level']:
                summary['by_level'][level] += 1
            
            # Count by type
            summary['by_type'][alert_type] = summary['by_type'].get(alert_type, 0) + 1
            
            # Count by symbol
            summary['by_symbol'][symbol] = summary['by_symbol'].get(symbol, 0) + 1
            
            # Count by source
            summary['by_source'][source] = summary['by_source'].get(source, 0) + 1
            
            # Track most recent
            if timestamp > most_recent_timestamp:
                most_recent_timestamp = timestamp
                summary['most_recent'] = {
                    'level': level,
                    'message': alert.get('message', ''),
                    'timestamp': timestamp
                }
            
            # Track most critical
            if level_priority.get(level, 0) > most_critical_level:
                most_critical_level = level_priority.get(level, 0)
                summary['most_critical'] = {
                    'level': level,
                    'message': alert.get('message', ''),
                    'timestamp': timestamp
                }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting alert summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving alert summary: {str(e)}")

@router.post("/alerts", response_model=Dict[str, str])
async def create_alert(
    alert_request: AlertCreateRequest,
    alert_manager = Depends(get_alert_manager)
) -> Dict[str, str]:
    """Create a new alert via API."""
    try:
        # Create alert details
        details = alert_request.details or {}
        if alert_request.source:
            details['source'] = alert_request.source
        if alert_request.alert_type:
            details['type'] = alert_request.alert_type
        if alert_request.symbol:
            details['symbol'] = alert_request.symbol
        
        # Send alert through alert manager
        await alert_manager.send_alert(
            level=alert_request.level,
            message=alert_request.message,
            details=details,
            throttle=False  # Don't throttle API-created alerts
        )
        
        return {
            "status": "success",
            "message": "Alert created successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating alert: {str(e)}")

@router.get("/alerts/types", response_model=List[str])
async def get_alert_types(
    alert_manager = Depends(get_alert_manager)
) -> List[str]:
    """Get list of available alert types."""
    try:
        # Get recent alerts to extract types
        alerts = alert_manager.get_alerts(limit=1000)
        
        # Extract unique alert types
        types = set()
        for alert in alerts:
            alert_type = alert.get('details', {}).get('type')
            if alert_type:
                types.add(alert_type)
        
        # Add common alert types
        common_types = [
            'signal', 'alpha', 'liquidation', 'whale_activity', 
            'large_order', 'manipulation', 'trade_execution',
            'system', 'api', 'database', 'performance'
        ]
        types.update(common_types)
        
        return sorted(list(types))
        
    except Exception as e:
        logger.error(f"Error getting alert types: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving alert types: {str(e)}")

@router.delete("/alerts/{alert_id}")
async def acknowledge_alert(
    alert_id: str,
    alert_manager = Depends(get_alert_manager)
) -> Dict[str, str]:
    """Acknowledge an alert (mark as read)."""
    try:
        # Try to acknowledge the alert
        success = False
        if hasattr(alert_manager, 'acknowledge_alert'):
            success = alert_manager.acknowledge_alert(alert_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Alert {alert_id} acknowledged",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        raise HTTPException(status_code=500, detail=f"Error acknowledging alert: {str(e)}")

# =============================================================================
# WHALE ACTIVITY ENDPOINTS (from whale_activity.py)
# =============================================================================

class WhaleAlert(BaseModel):
    """Whale activity alert model."""
    id: str
    symbol: str
    alert_type: str  # 'large_order', 'whale_accumulation', 'whale_distribution'
    amount: float
    value_usd: float
    price: float
    side: str  # 'buy' or 'sell'
    timestamp: int
    exchange: str
    confidence: float
    severity: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'

class WhaleActivity(BaseModel):
    """Whale activity data model."""
    symbol: str
    total_volume_24h: float
    whale_volume_24h: float
    whale_percentage: float
    large_orders_count: int
    accumulation_score: float
    distribution_score: float
    net_flow: float
    timestamp: int

@router.get("/whale/alerts")
async def get_whale_alerts():
    """Get whale activity alerts."""
    return [
        {
            "id": f"whale_{int(time.time())}",
            "symbol": "BTCUSDT",
            "alert_type": "large_order",
            "amount": 1250.0,
            "value_usd": 125000000.0,
            "price": 107500.0,
            "side": "buy",
            "timestamp": int(time.time() * 1000),
            "exchange": "bybit",
            "severity": "HIGH"
        }
    ]

@router.get("/whale/activity")
async def get_whale_activity(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of symbols")
) -> List[WhaleActivity]:
    """Get whale activity data for symbols."""
    try:
        logger.info(f"Getting whale activity: symbol={symbol}, limit={limit}")
        
        # Generate mock whale activity data
        current_time = int(time.time() * 1000)
        symbols = [symbol] if symbol else ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'AVAXUSDT', 'ADAUSDT', 'DOTUSDT']
        
        activities = []
        for i, sym in enumerate(symbols[:limit]):
            total_volume = 50000000.0 + (i * 10000000)
            whale_volume = total_volume * (0.15 + (i * 0.02))  # 15-30% whale volume
            
            activities.append(WhaleActivity(
                symbol=sym,
                total_volume_24h=total_volume,
                whale_volume_24h=whale_volume,
                whale_percentage=(whale_volume / total_volume) * 100,
                large_orders_count=25 + (i * 5),
                accumulation_score=65.0 + (i * 3.5),
                distribution_score=35.0 - (i * 2.0),
                net_flow=whale_volume * (0.6 if i % 2 == 0 else -0.4),  # Positive = accumulation
                timestamp=current_time
            ))
        
        logger.info(f"Returning whale activity for {len(activities)} symbols")
        return activities
        
    except Exception as e:
        logger.error(f"Error getting whale activity: {str(e)}")
        return []

@router.get("/whale/summary")
async def get_whale_summary(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back")
) -> Dict[str, Any]:
    """Get whale activity summary statistics."""
    try:
        logger.info(f"Getting whale summary for {hours} hours")
        
        current_time = int(time.time() * 1000)
        
        # Mock summary data
        summary = {
            "period_hours": hours,
            "total_whale_alerts": 45,
            "high_severity_alerts": 12,
            "critical_alerts": 3,
            "total_whale_volume_usd": 2.4e9,  # $2.4B
            "largest_single_order_usd": 15e6,  # $15M
            "most_active_symbol": "BTCUSDT",
            "accumulation_signals": 8,
            "distribution_signals": 3,
            "net_whale_flow_usd": 450e6,  # $450M net inflow
            "whale_dominance_percentage": 23.5,
            "alert_breakdown": {
                "large_order": 28,
                "whale_accumulation": 12,
                "whale_distribution": 5
            },
            "top_symbols_by_whale_activity": [
                {"symbol": "BTCUSDT", "whale_volume_usd": 1.2e9, "percentage": 28.5},
                {"symbol": "ETHUSDT", "whale_volume_usd": 800e6, "percentage": 22.1},
                {"symbol": "SOLUSDT", "whale_volume_usd": 250e6, "percentage": 35.2}
            ],
            "timestamp": current_time
        }
        
        logger.info("Returning whale activity summary")
        return summary
        
    except Exception as e:
        logger.error(f"Error getting whale summary: {str(e)}")
        return {
            "period_hours": hours,
            "total_whale_alerts": 0,
            "error": "Unable to fetch whale summary",
            "timestamp": int(time.time() * 1000)
        }

@router.get("/whale/large-orders")
async def get_large_orders(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    min_value: float = Query(100000, description="Minimum order value in USD"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of orders")
) -> List[Dict[str, Any]]:
    """Get recent large orders that may indicate whale activity."""
    try:
        logger.info(f"Getting large orders: symbol={symbol}, min_value={min_value}, limit={limit}")
        
        current_time = int(time.time() * 1000)
        symbols = [symbol] if symbol else ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT']
        
        large_orders = []
        for i, sym in enumerate(symbols):
            for j in range(limit // len(symbols)):
                order_value = min_value + (j * 50000) + (i * 100000)
                price = 107500.0 if 'BTC' in sym else (3000.0 if 'ETH' in sym else 150.0)
                amount = order_value / price
                
                large_orders.append({
                    "id": f"order_{current_time}_{i}_{j}",
                    "symbol": sym,
                    "side": "buy" if j % 2 == 0 else "sell",
                    "amount": round(amount, 6),
                    "price": price,
                    "value_usd": order_value,
                    "exchange": "bybit",
                    "timestamp": current_time - (i * 60000) - (j * 30000),
                    "is_whale": order_value > 500000,
                    "confidence": 0.75 + (order_value / 1000000) * 0.2
                })
        
        # Sort by timestamp (newest first)
        large_orders.sort(key=lambda x: x['timestamp'], reverse=True)
        
        logger.info(f"Returning {len(large_orders)} large orders")
        return large_orders[:limit]
        
    except Exception as e:
        logger.error(f"Error getting large orders: {str(e)}")
        return []

@router.get("/whale/flow-analysis")
async def get_whale_flow_analysis(
    symbol: str = Query(..., description="Symbol to analyze"),
    timeframe: str = Query("1h", description="Timeframe: 1h, 4h, 1d")
) -> Dict[str, Any]:
    """Get detailed whale flow analysis for a specific symbol."""
    try:
        logger.info(f"Getting whale flow analysis: symbol={symbol}, timeframe={timeframe}")
        
        current_time = int(time.time() * 1000)
        
        # Mock flow analysis data
        analysis = {
            "symbol": symbol,
            "timeframe": timeframe,
            "analysis_period": f"Last {timeframe}",
            "whale_metrics": {
                "total_inflow_usd": 125e6,  # $125M
                "total_outflow_usd": 98e6,   # $98M
                "net_flow_usd": 27e6,       # $27M net inflow
                "flow_ratio": 1.28,         # inflow/outflow
                "dominant_flow": "accumulation"
            },
            "transaction_analysis": {
                "large_buy_orders": 23,
                "large_sell_orders": 18,
                "average_buy_size_usd": 2.1e6,
                "average_sell_size_usd": 1.8e6,
                "buy_sell_ratio": 1.28
            },
            "pattern_detection": {
                "accumulation_pattern": True,
                "distribution_pattern": False,
                "consolidation_pattern": False,
                "breakout_potential": "high",
                "pattern_confidence": 0.84
            },
            "time_analysis": {
                "most_active_hour": 14,  # UTC
                "peak_volume_period": "08:00-16:00 UTC",
                "weekend_activity": "reduced",
                "session_preference": "london_ny_overlap"
            },
            "risk_assessment": {
                "manipulation_risk": "low",
                "liquidity_impact": "medium",
                "price_sensitivity": "high",
                "stability_score": 0.72
            },
            "timestamp": current_time
        }
        
        logger.info(f"Returning whale flow analysis for {symbol}")
        return analysis
        
    except Exception as e:
        logger.error(f"Error getting whale flow analysis: {str(e)}")
        return {
            "symbol": symbol,
            "error": "Unable to fetch flow analysis",
            "timestamp": int(time.time() * 1000)
        }

@router.get("/signals/symbol/{symbol}", response_model=SymbolSignals)
async def get_signals_by_symbol(
    symbol: str,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of signals to return"),
    db_client = Depends(get_database_client)
) -> SymbolSignals:
    """
    Get signals for a specific symbol sorted by date (newest first).
    """
    if not SIGNALS_DIR.exists():
        raise HTTPException(status_code=404, detail="Signals directory not found")
    
    symbol = symbol.upper()
    
    # Get all JSON files for the symbol
    all_files = [f for f in SIGNALS_DIR.glob(f"{symbol}_*.json") if f.is_file()]
    
    # If no files match the pattern, try a less strict pattern
    if not all_files:
        all_files = [f for f in SIGNALS_DIR.glob(f"*{symbol}*.json") if f.is_file()]
    
    signals = []
    
    for file_path in all_files:
        try:
            with open(file_path, 'r') as f:
                signal_data = json.load(f)
            
            # Verify the symbol matches
            if signal_data.get('symbol', '').upper() == symbol:
                signal_data['filename'] = file_path.name
                signal_data['file_path'] = str(file_path)
                
                # Validate the data
                signal_obj = Signal(**signal_data)
                signals.append(signal_data)
        except:
            # Skip files with errors
            continue
    
    # Sort by timestamp (descending) or filename
    signals.sort(key=lambda x: x.get('timestamp', x.get('filename', '')), reverse=True)
    
    # Limit the number of results
    signals = signals[:limit]
    
    return SymbolSignals(
        symbol=symbol,
        count=len(signals),
        signals=signals
    )

@router.get("/signals", response_model=SignalList)
async def get_all_signals(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    signal_type: Optional[str] = Query(None, description="Filter by signal type (BULLISH, BEARISH, etc.)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYYMMDD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYYMMDD)"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum score"),
    db_client = Depends(get_database_client)
) -> SignalList:
    """
    Get signal data with filtering and pagination.
    Retrieves signals from JSON files stored in the reports/json directory.
    """
    if not SIGNALS_DIR.exists():
        raise HTTPException(status_code=404, detail="Signals directory not found")
    
    # Get all JSON files in the directory
    all_files = [f for f in SIGNALS_DIR.glob("*.json") if f.is_file()]
    
    # Process files and apply filters
    filtered_signals = []
    
    for file_path in all_files:
        try:
            # Parse filename for quick filtering
            filename = file_path.stem  # Gets filename without extension
            
            # Quick filter by symbol and signal_type if present in filename
            if symbol and symbol.upper() not in filename.upper():
                continue
                
            if signal_type and signal_type.upper() not in filename.upper():
                continue
            
            # Load the JSON file
            with open(file_path, 'r') as f:
                signal_data = json.load(f)
            
            # Add filename and file_path to the data
            signal_data['filename'] = file_path.name
            signal_data['file_path'] = str(file_path)
            
            # Apply additional filters
            if symbol and signal_data.get('symbol', '').upper() != symbol.upper():
                continue
                
            if signal_type and signal_data.get('signal', '').upper() != signal_type.upper():
                continue
                
            if min_score is not None and signal_data.get('score', 0) < min_score:
                continue
                
            # Parse dates from filename if available (assuming format SYMBOL_TYPE_YYYYMMDD_HHMMSS)
            try:
                date_part = None
                parts = filename.split('_')
                if len(parts) >= 3:
                    date_part = parts[-2]  # Try to get date from second-to-last part
                
                if date_part and len(date_part) == 8:  # YYYYMMDD format
                    # Filter by date if provided
                    if start_date and date_part < start_date:
                        continue
                    if end_date and date_part > end_date:
                        continue
            except:
                # If date parsing fails, don't filter by date
                pass
            
            # Convert the data to a Signal object to validate it
            try:
                signal_obj = Signal(**signal_data)
                filtered_signals.append(signal_data)
            except Exception as e:
                # Skip invalid signal data
                continue
            
        except Exception as e:
            # Skip files with errors
            continue
    
    # Sort signals by timestamp (descending) if available or by filename
    filtered_signals.sort(key=lambda x: x.get('timestamp', x.get('filename', '')), reverse=True)
    
    # Calculate pagination
    total = len(filtered_signals)
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    paged_signals = filtered_signals[start_idx:end_idx]
    
    return SignalList(
        signals=paged_signals,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size if size > 0 else 0
    )

@router.get("/signals/{filename}", response_model=Signal)
async def get_signal_by_filename(
    filename: str,
    db_client = Depends(get_database_client)
) -> Signal:
    """
    Get a specific signal by its filename.
    """
    file_path = SIGNALS_DIR / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Signal file {filename} not found")
    
    try:
        with open(file_path, 'r') as f:
            signal_data = json.load(f)
        
        # Add filename and file_path to the data
        signal_data['filename'] = filename
        signal_data['file_path'] = str(file_path)
        
        # Validate the data by creating a Signal object
        return Signal(**signal_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading signal file: {str(e)}")

@router.get("/active")
async def get_active_signals(
    limit: int = Query(default=10, ge=1, le=50),
    db_client = Depends(get_database_client)
) -> Dict[str, Any]:
    """
    Get currently active trading signals.
    
    This unified endpoint:
    - Returns live tracking signals when signal_tracking.enabled = true
    - Returns recent historical signals when signal_tracking.enabled = false
    """
    try:
        logger = logging.getLogger(__name__)
        
        # Check if signal tracking is enabled
        if is_signal_tracking_enabled():
            # Signal tracking is enabled - return live tracking data
            logger.debug("Signal tracking enabled - attempting to fetch from tracking API")
            
            try:
                # Try to get live signals from signal_tracking module
                from .signal_tracking import active_signals, cleanup_expired_signals, format_duration
                
                # Clean up expired signals
                cleanup_expired_signals()
                
                # Convert to list and add current P&L calculations
                signals_list = []
                for signal_id, signal_data in active_signals.items():
                    signal_copy = signal_data.copy()
                    signal_copy['id'] = signal_id
                    
                    # Add duration
                    current_time = time.time()
                    duration_seconds = current_time - signal_data.get('created_at', current_time)
                    signal_copy['duration_seconds'] = int(duration_seconds)
                    signal_copy['duration_formatted'] = format_duration(duration_seconds)
                    
                    signals_list.append(signal_copy)
                
                logger.info(f"Returning {len(signals_list)} live tracking signals")
                return {
                    "signals": signals_list,
                    "count": len(signals_list),
                    "timestamp": int(time.time() * 1000),
                    "source": "live_tracking"
                }
                
            except ImportError as e:
                logger.warning(f"Could not import signal tracking module: {e}")
                # Fall back to historical signals
                pass
        else:
            # Signal tracking is explicitly disabled
            logger.debug("Signal tracking disabled - returning empty signals list")
            return {
                "signals": [],
                "count": 0,
                "timestamp": int(time.time() * 1000),
                "source": "disabled",
                "message": "Signal tracking disabled"
            }
        
        # This section should only be reached if signal tracking is enabled but import failed
        # Signal tracking enabled but unavailable - return historical signals as fallback
        logger.debug("Signal tracking enabled but unavailable - returning historical signals as fallback")
        
        if not SIGNALS_DIR.exists():
            return {
                "signals": [], 
                "count": 0, 
                "timestamp": int(time.time() * 1000),
                "source": "historical",
                "message": "No signals directory found"
            }
        
        # Get recent signal files (last 24 hours worth)
        all_files = [f for f in SIGNALS_DIR.glob("*.json") if f.is_file()]
        
        # Sort by modification time (most recent first)
        all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        active_signals_list = []
        
        for file_path in all_files[:limit]:
            try:
                with open(file_path, 'r') as f:
                    signal_data = json.load(f)
                
                # Skip signals without valid symbols
                symbol = signal_data.get("symbol")
                if not symbol or symbol.upper() in ['UNKNOWN', 'NULL', 'UNDEFINED', 'NONE', '', 'INVALID', 'ERROR']:
                    logger.debug(f"Skipping signal file {file_path} - invalid or missing symbol: '{symbol}'")
                    continue
                
                # Simulate active signal properties for historical data
                active_signal = {
                    "id": signal_data.get("filename", file_path.stem),
                    "symbol": symbol,
                    "action": signal_data.get("signal", "HOLD").upper(),
                    "signal_type": signal_data.get("signal", "HOLD").upper(),
                    "entry_price": signal_data.get("current_price", 0.0),
                    "price": signal_data.get("current_price", 0.0),
                    "confidence": signal_data.get("score", 50.0),
                    "score": signal_data.get("score", 50.0),
                    "quantity": 1.0,  # Default quantity
                    "timestamp": signal_data.get("timestamp", int(time.time() * 1000)),
                    "created_at": signal_data.get("timestamp", int(time.time() * 1000)),
                    "status": "historical"
                }
                
                active_signals_list.append(active_signal)
                
            except Exception as e:
                logger.debug(f"Error processing signal file {file_path}: {e}")
                continue
        
        logger.info(f"Returning {len(active_signals_list)} historical signals")
        return {
            "signals": active_signals_list,
            "count": len(active_signals_list),
            "timestamp": int(time.time() * 1000),
            "source": "historical"
        }
        
    except Exception as e:
        logger.error(f"Error getting active signals: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting active signals: {str(e)}") 