from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time
import logging
from pydantic import BaseModel, Field

try:
    from ..models.alerts import (
        AlertResponse, AlertSummary, AlertFilter, AlertLevel,
        AlertType, AlertStats, RecentAlert
    )
except ImportError:
    # Fallback if models not available
    AlertResponse = AlertSummary = AlertFilter = AlertLevel = None
    AlertType = AlertStats = RecentAlert = None

# Import alert persistence
try:
    from src.monitoring.alert_persistence import AlertPersistence, AlertStatus
except ImportError:
    try:
        from monitoring.alert_persistence import AlertPersistence, AlertStatus
    except ImportError:
        AlertPersistence = None
        AlertStatus = None

logger = logging.getLogger(__name__)
router = APIRouter()

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
    level: str = Field(..., pattern="^(INFO|WARNING|ERROR|CRITICAL)$")
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

@router.get("/", response_model=List[AlertData])
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
    """
    Get alerts with optional filtering.
    
    Returns a list of alerts based on the provided filters.
    """
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

@router.get("/recent", response_model=List[AlertData])
async def get_recent_alerts(
    limit: int = Query(20, ge=1, le=100, description="Number of recent alerts"),
    level: Optional[str] = Query(None, description="Filter by alert level"),
    alert_manager = Depends(get_alert_manager)
) -> List[AlertData]:
    """
    Get recent alerts for dashboard display.
    """
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

@router.get("/stats", response_model=Dict[str, Any])
async def get_alert_stats(
    alert_manager = Depends(get_alert_manager)
) -> Dict[str, Any]:
    """
    Get alert statistics and metrics.
    """
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

@router.get("/summary", response_model=Dict[str, Any])
async def get_alert_summary(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    alert_manager = Depends(get_alert_manager)
) -> Dict[str, Any]:
    """
    Get alert summary for the specified time period.
    """
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

@router.post("/", response_model=Dict[str, str])
async def create_alert(
    alert_request: AlertCreateRequest,
    alert_manager = Depends(get_alert_manager)
) -> Dict[str, str]:
    """
    Create a new alert via API.
    """
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

@router.get("/types", response_model=List[str])
async def get_alert_types(
    alert_manager = Depends(get_alert_manager)
) -> List[str]:
    """
    Get list of available alert types.
    """
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

@router.delete("/{alert_id}")
async def acknowledge_alert(
    alert_id: str,
    alert_manager = Depends(get_alert_manager)
) -> Dict[str, str]:
    """
    Acknowledge an alert (mark as read).
    """
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

# Alert persistence endpoints
alert_persistence = None

def get_persistence():
    """Dependency to get alert persistence instance"""
    global alert_persistence
    if not alert_persistence and AlertPersistence:
        alert_persistence = AlertPersistence("data/alerts.db")
    return alert_persistence

@router.get("/persisted/list")
async def get_persisted_alerts(
    symbol: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    hours: int = Query(24),
    limit: int = Query(100),
    offset: int = Query(0)
):
    """Get persisted alerts from database"""
    try:
        persistence = get_persistence()
        if not persistence:
            raise HTTPException(status_code=503, detail="Alert persistence not available")
        
        end_time = datetime.utcnow().timestamp()
        start_time = end_time - (hours * 3600)
        
        alerts = await persistence.get_alerts(
            symbol=symbol,
            alert_type=alert_type,
            status=status,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )
        
        return {
            'success': True,
            'count': len(alerts),
            'alerts': [
                {
                    'alert_id': a.alert_id,
                    'type': a.alert_type,
                    'symbol': a.symbol,
                    'timestamp': a.timestamp,
                    'title': a.title,
                    'message': a.message,
                    'data': a.data,
                    'status': a.status,
                    'priority': a.priority
                } for a in alerts
            ]
        }
    except Exception as e:
        logger.error(f"Error getting persisted alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/persisted/{alert_id}")
async def get_persisted_alert(alert_id: str):
    """Get specific persisted alert by ID"""
    try:
        persistence = get_persistence()
        if not persistence:
            raise HTTPException(status_code=503, detail="Alert persistence not available")
        
        alert = await persistence.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        
        return {
            'success': True,
            'alert': {
                'alert_id': alert.alert_id,
                'type': alert.alert_type,
                'symbol': alert.symbol,
                'timestamp': alert.timestamp,
                'title': alert.title,
                'message': alert.message,
                'data': alert.data,
                'status': alert.status,
                'webhook_sent': alert.webhook_sent,
                'created_at': alert.created_at,
                'priority': alert.priority,
                'tags': alert.tags
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting persisted alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/persisted/stats")
async def get_persisted_stats(hours: int = Query(24)):
    """Get statistics from persisted alerts"""
    try:
        persistence = get_persistence()
        if not persistence:
            raise HTTPException(status_code=503, detail="Alert persistence not available")
        
        end_time = datetime.utcnow().timestamp()
        start_time = end_time - (hours * 3600) if hours else None
        
        stats = await persistence.get_alert_statistics(
            start_time=start_time,
            end_time=end_time
        )
        
        return {
            'success': True,
            'period_hours': hours,
            'statistics': stats
        }
    except Exception as e:
        logger.error(f"Error getting persisted stats: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 