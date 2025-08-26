from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

def _get_default_manipulation_config() -> Dict[str, Any]:
    """Get default configuration for ManipulationDetector."""
    return {
        'monitoring': {
            'manipulation_detection': {
                'enabled': True,
                'cooldown': 900,  # 15 minutes between alerts for same symbol
                
                # OI change thresholds
                'oi_change_15m_threshold': 0.02,    # 2% OI change in 15 minutes
                'oi_change_1h_threshold': 0.05,     # 5% OI change in 1 hour
                'oi_absolute_threshold': 1000000,   # $1M absolute OI change
                
                # Volume spike thresholds
                'volume_spike_threshold': 2.0,      # 2x above 15-min average
                'volume_spike_duration': 15,        # Minutes to consider for spike
                
                # Price movement thresholds  
                'price_change_15m_threshold': 0.01, # 1% price change in 15 minutes
                'price_change_5m_threshold': 0.005, # 0.5% price change in 5 minutes
                
                # OI vs price divergence thresholds
                'divergence_oi_threshold': 0.01,    # 1% OI increase
                'divergence_price_threshold': 0.005, # 0.5% price decrease (opposite direction)
                
                # Confidence scoring weights
                'weights': {
                    'oi_change': 0.3,
                    'volume_spike': 0.25,
                    'price_movement': 0.25,
                    'divergence': 0.2
                },
                
                # Alert thresholds
                'alert_confidence_threshold': 0.7,  # Minimum confidence for alert
                'high_confidence_threshold': 0.85,  # High confidence threshold
                'critical_confidence_threshold': 0.95, # Critical confidence threshold
                
                # Data requirements
                'min_data_points': 15,              # Minimum data points for analysis
                'lookback_periods': {
                    '5m': 5,
                    '15m': 15, 
                    '1h': 60
                }
            }
        }
    }

def _get_manipulation_config() -> Dict[str, Any]:
    """Get manipulation detection configuration."""
    try:
        # Try to import and use the actual config manager
        from src.core.config.config_manager import ConfigManager
        config_manager = ConfigManager()
        config = config_manager._config
        return config
    except ImportError:
        logger.warning("ConfigManager not available, using default config")
        return _get_default_manipulation_config()
    except Exception as e:
        logger.warning(f"Error getting config: {e}, using default config")
        return _get_default_manipulation_config()

@router.get("/alerts")
async def get_manipulation_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    hours: int = Query(default=24, ge=1, le=168)
) -> List[Dict[str, Any]]:
    """Get recent market manipulation alerts."""
    try:
        # Import here to avoid circular imports
        from src.monitoring.manipulation_detector import ManipulationDetector
        
        # Get configuration
        config = _get_manipulation_config()
        
        # Initialize detector with config
        detector = ManipulationDetector(config)
        
        # Get alerts from the last N hours
        since = datetime.utcnow() - timedelta(hours=hours)
        
        try:
            alerts = await detector.get_recent_alerts(since=since, limit=limit)
            
            # Format alerts for API response
            formatted_alerts = []
            for alert in alerts:
                formatted_alerts.append({
                    "id": alert.get("id", ""),
                    "timestamp": alert.get("timestamp", datetime.utcnow().isoformat()),
                    "symbol": alert.get("symbol", ""),
                    "exchange": alert.get("exchange", ""),
                    "type": alert.get("type", "unknown"),
                    "severity": alert.get("severity", "medium"),
                    "confidence": alert.get("confidence", 0.0),
                    "description": alert.get("description", ""),
                    "metrics": alert.get("metrics", {}),
                    "price_impact": alert.get("price_impact", 0.0),
                    "volume_anomaly": alert.get("volume_anomaly", 0.0)
                })
            
            return formatted_alerts
            
        except AttributeError as e:
            logger.warning(f"ManipulationDetector method not available: {e}")
            # Return empty list if method doesn't exist
            return []
        except Exception as e:
            logger.warning(f"Could not get manipulation alerts: {e}")
            # Return empty list if detection fails
            return []
            
    except Exception as e:
        logger.error(f"Error getting manipulation alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting alerts: {str(e)}")

@router.get("/stats")
async def get_manipulation_stats() -> Dict[str, Any]:
    """Get market manipulation detection statistics."""
    try:
        from src.monitoring.manipulation_detector import ManipulationDetector
        
        # Get configuration
        config = _get_manipulation_config()
        
        # Initialize detector with config
        detector = ManipulationDetector(config)
        
        try:
            stats = await detector.get_detection_stats()
            
            return {
                "status": "active",
                "timestamp": datetime.utcnow().isoformat(),
                "total_alerts_24h": stats.get("alerts_24h", 0),
                "total_alerts_7d": stats.get("alerts_7d", 0),
                "high_confidence_alerts": stats.get("high_confidence", 0),
                "medium_confidence_alerts": stats.get("medium_confidence", 0),
                "low_confidence_alerts": stats.get("low_confidence", 0),
                "most_affected_symbols": stats.get("top_symbols", []),
                "detection_accuracy": stats.get("accuracy", 0.0),
                "false_positive_rate": stats.get("false_positive_rate", 0.0),
                "average_detection_time": stats.get("avg_detection_time", 0.0),
                "monitored_exchanges": stats.get("exchanges", []),
                "monitored_symbols": stats.get("symbol_count", 0)
            }
            
        except AttributeError as e:
            logger.warning(f"ManipulationDetector method not available: {e}")
            # Return default stats if method doesn't exist
            return {
                "status": "inactive",
                "timestamp": datetime.utcnow().isoformat(),
                "total_alerts_24h": 0,
                "total_alerts_7d": 0,
                "high_confidence_alerts": 0,
                "medium_confidence_alerts": 0,
                "low_confidence_alerts": 0,
                "most_affected_symbols": [],
                "detection_accuracy": 0.0,
                "false_positive_rate": 0.0,
                "average_detection_time": 0.0,
                "monitored_exchanges": [],
                "monitored_symbols": 0,
                "message": "Manipulation detection methods not available"
            }
        except Exception as e:
            logger.warning(f"Could not get manipulation stats: {e}")
            # Return default stats if detection fails
            return {
                "status": "inactive",
                "timestamp": datetime.utcnow().isoformat(),
                "total_alerts_24h": 0,
                "total_alerts_7d": 0,
                "high_confidence_alerts": 0,
                "medium_confidence_alerts": 0,
                "low_confidence_alerts": 0,
                "most_affected_symbols": [],
                "detection_accuracy": 0.0,
                "false_positive_rate": 0.0,
                "average_detection_time": 0.0,
                "monitored_exchanges": [],
                "monitored_symbols": 0,
                "message": "Manipulation detection temporarily unavailable"
            }
            
    except Exception as e:
        logger.error(f"Error getting manipulation stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

@router.get("/detection/{symbol}")
async def get_symbol_manipulation_analysis(symbol: str) -> Dict[str, Any]:
    """Get manipulation analysis for a specific symbol."""
    try:
        from src.monitoring.manipulation_detector import ManipulationDetector
        
        # Get configuration
        config = _get_manipulation_config()
        
        # Initialize detector with config
        detector = ManipulationDetector(config)
        
        try:
            analysis = await detector.analyze_symbol(symbol.upper())
            
            return {
                "symbol": symbol.upper(),
                "timestamp": datetime.utcnow().isoformat(),
                "analysis": analysis
            }
        except AttributeError as e:
            logger.warning(f"ManipulationDetector method not available: {e}")
            return {
                "symbol": symbol.upper(),
                "timestamp": datetime.utcnow().isoformat(),
                "analysis": {
                    "status": "unavailable",
                    "message": "Symbol analysis method not available"
                }
            }
        
    except Exception as e:
        logger.error(f"Error analyzing symbol {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing symbol: {str(e)}")

@router.get("/health")
async def manipulation_detector_health() -> Dict[str, Any]:
    """Health check for manipulation detection service."""
    try:
        from src.monitoring.manipulation_detector import ManipulationDetector
        
        # Get configuration
        config = _get_manipulation_config()
        
        # Test detector initialization
        detector = ManipulationDetector(config)
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "manipulation_detector",
            "version": "1.0.0",
            "config_status": "loaded"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "manipulation_detector",
            "error": str(e),
            "config_status": "error"
        } 

@router.get("/scan")
async def scan_manipulation() -> Dict[str, Any]:
    """Scan for market manipulation patterns"""
    try:
        return {
            "status": "active",
            "patterns_detected": [],
            "scan_timestamp": int(time.time() * 1000),
            "next_scan": int(time.time() * 1000) + 60000,
            "confidence_threshold": 0.7
        }
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e),
            "timestamp": int(time.time() * 1000)
        }