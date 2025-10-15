"""
WebSocket Health Monitoring Module
==================================

Provides comprehensive WebSocket health monitoring and diagnostics
for the Virtuoso CCXT Trading System.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class WebSocketHealthMonitor:
    """
    Comprehensive WebSocket health monitoring with detailed diagnostics
    """

    def __init__(self):
        self.last_check_time = None
        self.health_history = []
        self.max_history_length = 100

    async def get_comprehensive_websocket_health(self, market_data_manager=None) -> Dict[str, Any]:
        """
        Get comprehensive WebSocket health status with detailed diagnostics

        Args:
            market_data_manager: MarketDataManager instance to check

        Returns:
            Dictionary containing detailed WebSocket health status
        """
        check_time = datetime.utcnow()
        self.last_check_time = check_time

        health_status = {
            "timestamp": check_time.isoformat(),
            "overall_status": "unknown",
            "websocket": {
                "connected": False,
                "connection_count": 0,
                "status": "disconnected",
                "last_message_time": None,
                "seconds_since_last_message": None,
                "messages_received": 0,
                "errors": 0,
                "details": {}
            },
            "checks": [],
            "recommendations": [],
            "diagnostics": {}
        }

        # Check 1: Basic WebSocket availability
        ws_available = await self._check_websocket_availability(market_data_manager, health_status)

        # Check 2: Connection status
        connection_status = await self._check_connection_status(market_data_manager, health_status)

        # Check 3: Message flow health
        message_health = await self._check_message_flow_health(market_data_manager, health_status)

        # Check 4: Performance metrics
        performance_status = await self._check_performance_metrics(market_data_manager, health_status)

        # Determine overall status
        overall_status = self._determine_overall_status(health_status["checks"])
        health_status["overall_status"] = overall_status

        # Add recommendations based on status
        self._add_health_recommendations(health_status)

        # Store in history
        self._store_health_history(health_status)

        return health_status

    async def _check_websocket_availability(self, market_data_manager, health_status: Dict[str, Any]) -> bool:
        """Check if WebSocket manager is available and accessible"""
        check = {
            "name": "websocket_availability",
            "status": "failed",
            "message": "WebSocket manager not available",
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            if not market_data_manager:
                check["message"] = "MarketDataManager not available"
                check["details"] = {"error": "market_data_manager_missing"}
                health_status["checks"].append(check)
                return False

            if not hasattr(market_data_manager, 'websocket_manager'):
                check["message"] = "WebSocket manager not found in MarketDataManager"
                check["details"] = {"error": "websocket_manager_missing"}
                health_status["checks"].append(check)
                return False

            ws_manager = market_data_manager.websocket_manager
            if not ws_manager:
                check["message"] = "WebSocket manager is None"
                check["details"] = {"error": "websocket_manager_none"}
                health_status["checks"].append(check)
                return False

            check["status"] = "passed"
            check["message"] = "WebSocket manager available"
            check["details"] = {
                "manager_type": type(ws_manager).__name__,
                "has_get_status": hasattr(ws_manager, 'get_status'),
                "has_connections": hasattr(ws_manager, 'connections')
            }

            health_status["checks"].append(check)
            return True

        except Exception as e:
            check["message"] = f"Error checking WebSocket availability: {str(e)}"
            check["details"] = {"exception": str(e), "type": type(e).__name__}
            health_status["checks"].append(check)
            return False

    async def _check_connection_status(self, market_data_manager, health_status: Dict[str, Any]) -> bool:
        """Check WebSocket connection status and details"""
        check = {
            "name": "websocket_connections",
            "status": "failed",
            "message": "Unable to check connection status",
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            if not market_data_manager or not hasattr(market_data_manager, 'websocket_manager'):
                check["message"] = "WebSocket manager not accessible"
                health_status["checks"].append(check)
                return False

            ws_manager = market_data_manager.websocket_manager
            if not ws_manager:
                check["message"] = "WebSocket manager is None"
                health_status["checks"].append(check)
                return False

            # Get WebSocket status
            if hasattr(ws_manager, 'get_status'):
                ws_status = ws_manager.get_status()
                health_status["websocket"].update(ws_status)

                # Check if connected
                connected = ws_status.get('connected', False)
                connection_count = ws_status.get('active_connections', 0)

                if connected and connection_count > 0:
                    check["status"] = "passed"
                    check["message"] = f"WebSocket connected with {connection_count} active connections"
                    health_status["websocket"]["status"] = "connected"
                elif connected and connection_count == 0:
                    check["status"] = "warning"
                    check["message"] = "WebSocket manager reports connected but no active connections"
                    health_status["websocket"]["status"] = "connected_no_streams"
                else:
                    check["status"] = "failed"
                    check["message"] = "WebSocket not connected"
                    health_status["websocket"]["status"] = "disconnected"

                check["details"] = {
                    "connected": connected,
                    "connection_count": connection_count,
                    "messages_received": ws_status.get('messages_received', 0),
                    "errors": ws_status.get('errors', 0),
                    "last_message_time": ws_status.get('last_message_time', 0)
                }

            else:
                check["message"] = "WebSocket manager missing get_status method"
                check["details"] = {"error": "missing_get_status_method"}

            health_status["checks"].append(check)
            return check["status"] == "passed"

        except Exception as e:
            check["message"] = f"Error checking WebSocket connections: {str(e)}"
            check["details"] = {"exception": str(e), "type": type(e).__name__}
            health_status["checks"].append(check)
            return False

    async def _check_message_flow_health(self, market_data_manager, health_status: Dict[str, Any]) -> bool:
        """Check WebSocket message flow health and recency"""
        check = {
            "name": "websocket_message_flow",
            "status": "unknown",
            "message": "Unable to check message flow",
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            ws_info = health_status.get("websocket", {})
            last_message_time = ws_info.get('last_message_time', 0)

            if not last_message_time:
                check["status"] = "failed"
                check["message"] = "No messages received yet"
                check["details"] = {"last_message_time": "never"}
                health_status["checks"].append(check)
                return False

            # Calculate time since last message
            current_time = time.time()
            seconds_since_last = current_time - last_message_time
            health_status["websocket"]["seconds_since_last_message"] = int(seconds_since_last)

            # Determine status based on message recency
            if seconds_since_last <= 30:  # Fresh messages
                check["status"] = "passed"
                check["message"] = f"Recent messages received ({int(seconds_since_last)}s ago)"
            elif seconds_since_last <= 120:  # Stale but acceptable
                check["status"] = "warning"
                check["message"] = f"Messages somewhat stale ({int(seconds_since_last)}s ago)"
            else:  # Very stale messages
                check["status"] = "failed"
                check["message"] = f"Messages very stale ({int(seconds_since_last)}s ago)"

            check["details"] = {
                "last_message_time": last_message_time,
                "last_message_datetime": datetime.fromtimestamp(last_message_time).isoformat(),
                "seconds_since_last_message": int(seconds_since_last),
                "messages_received": ws_info.get('messages_received', 0)
            }

            health_status["checks"].append(check)
            return check["status"] == "passed"

        except Exception as e:
            check["message"] = f"Error checking message flow: {str(e)}"
            check["details"] = {"exception": str(e), "type": type(e).__name__}
            health_status["checks"].append(check)
            return False

    async def _check_performance_metrics(self, market_data_manager, health_status: Dict[str, Any]) -> bool:
        """Check WebSocket performance metrics and error rates"""
        check = {
            "name": "websocket_performance",
            "status": "unknown",
            "message": "Unable to check performance metrics",
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            ws_info = health_status.get("websocket", {})

            messages_received = ws_info.get('messages_received', 0)
            error_count = ws_info.get('errors', 0)

            # Calculate error rate
            error_rate = 0.0
            if messages_received > 0:
                error_rate = error_count / (messages_received + error_count)

            # Determine performance status
            if error_count == 0 and messages_received > 0:
                check["status"] = "passed"
                check["message"] = f"Excellent performance: {messages_received} messages, no errors"
            elif error_rate < 0.01:  # Less than 1% error rate
                check["status"] = "passed"
                check["message"] = f"Good performance: {messages_received} messages, {error_count} errors ({error_rate:.2%})"
            elif error_rate < 0.05:  # Less than 5% error rate
                check["status"] = "warning"
                check["message"] = f"Moderate performance: {messages_received} messages, {error_count} errors ({error_rate:.2%})"
            else:  # High error rate
                check["status"] = "failed"
                check["message"] = f"Poor performance: {messages_received} messages, {error_count} errors ({error_rate:.2%})"

            check["details"] = {
                "messages_received": messages_received,
                "error_count": error_count,
                "error_rate": round(error_rate, 4),
                "error_percentage": f"{error_rate:.2%}"
            }

            health_status["diagnostics"]["performance"] = check["details"]
            health_status["checks"].append(check)
            return check["status"] == "passed"

        except Exception as e:
            check["message"] = f"Error checking performance metrics: {str(e)}"
            check["details"] = {"exception": str(e), "type": type(e).__name__}
            health_status["checks"].append(check)
            return False

    def _determine_overall_status(self, checks: List[Dict[str, Any]]) -> str:
        """Determine overall WebSocket health status from individual checks"""
        if not checks:
            return "unknown"

        failed_checks = [c for c in checks if c["status"] == "failed"]
        warning_checks = [c for c in checks if c["status"] == "warning"]
        passed_checks = [c for c in checks if c["status"] == "passed"]

        if failed_checks:
            return "critical"
        elif warning_checks:
            return "warning"
        elif passed_checks:
            return "healthy"
        else:
            return "unknown"

    def _add_health_recommendations(self, health_status: Dict[str, Any]) -> None:
        """Add actionable recommendations based on health status"""
        recommendations = []
        overall_status = health_status["overall_status"]
        checks = health_status["checks"]

        # Analyze failed checks for recommendations
        for check in checks:
            if check["status"] == "failed":
                if check["name"] == "websocket_availability":
                    recommendations.append({
                        "priority": "high",
                        "category": "configuration",
                        "title": "WebSocket Manager Initialization",
                        "description": "WebSocket manager is not properly initialized",
                        "action": "Check WebSocket configuration and restart service"
                    })
                elif check["name"] == "websocket_connections":
                    recommendations.append({
                        "priority": "high",
                        "category": "connectivity",
                        "title": "WebSocket Connection Issues",
                        "description": "WebSocket connections are not established",
                        "action": "Check network connectivity and WebSocket endpoints"
                    })
                elif check["name"] == "websocket_message_flow":
                    recommendations.append({
                        "priority": "medium",
                        "category": "data_flow",
                        "title": "Stale WebSocket Messages",
                        "description": "WebSocket messages are not being received recently",
                        "action": "Restart WebSocket connections or check exchange status"
                    })
                elif check["name"] == "websocket_performance":
                    recommendations.append({
                        "priority": "medium",
                        "category": "performance",
                        "title": "High WebSocket Error Rate",
                        "description": "WebSocket is experiencing high error rates",
                        "action": "Review error logs and consider connection optimization"
                    })

        # Analyze warning checks
        for check in checks:
            if check["status"] == "warning":
                if check["name"] == "websocket_message_flow":
                    recommendations.append({
                        "priority": "low",
                        "category": "monitoring",
                        "title": "WebSocket Message Latency",
                        "description": "WebSocket messages are slightly stale",
                        "action": "Monitor message flow and consider connection refresh"
                    })

        # Add general recommendations
        if overall_status == "critical":
            recommendations.append({
                "priority": "critical",
                "category": "immediate_action",
                "title": "WebSocket Service Restart Required",
                "description": "WebSocket health is critical and requires immediate attention",
                "action": "Restart the WebSocket service and verify connectivity"
            })

        health_status["recommendations"] = recommendations

    def _store_health_history(self, health_status: Dict[str, Any]) -> None:
        """Store health status in history for trend analysis"""
        health_summary = {
            "timestamp": health_status["timestamp"],
            "overall_status": health_status["overall_status"],
            "connected": health_status["websocket"]["connected"],
            "connection_count": health_status["websocket"]["connection_count"],
            "messages_received": health_status["websocket"]["messages_received"],
            "errors": health_status["websocket"]["errors"]
        }

        self.health_history.append(health_summary)

        # Keep history within limits
        if len(self.health_history) > self.max_history_length:
            self.health_history = self.health_history[-self.max_history_length:]

    def get_health_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get WebSocket health history"""
        if limit:
            return self.health_history[-limit:]
        return self.health_history.copy()

    def get_health_trends(self) -> Dict[str, Any]:
        """Get WebSocket health trends and statistics"""
        if not self.health_history:
            return {"status": "no_data", "message": "No health history available"}

        recent_history = self.health_history[-10:] if len(self.health_history) >= 10 else self.health_history

        # Calculate trends
        connected_ratio = sum(1 for h in recent_history if h["connected"]) / len(recent_history)
        avg_connections = sum(h["connection_count"] for h in recent_history) / len(recent_history)
        total_messages = sum(h["messages_received"] for h in recent_history)
        total_errors = sum(h["errors"] for h in recent_history)

        status_counts = {}
        for status in ["healthy", "warning", "critical", "unknown"]:
            status_counts[status] = sum(1 for h in recent_history if h["overall_status"] == status)

        return {
            "period": f"Last {len(recent_history)} checks",
            "connected_ratio": round(connected_ratio, 3),
            "average_connections": round(avg_connections, 1),
            "total_messages": total_messages,
            "total_errors": total_errors,
            "status_distribution": status_counts,
            "last_check": recent_history[-1]["timestamp"] if recent_history else None
        }


# Global instance
websocket_health_monitor = WebSocketHealthMonitor()


async def get_websocket_health(market_data_manager=None) -> Dict[str, Any]:
    """
    Get comprehensive WebSocket health status

    Args:
        market_data_manager: MarketDataManager instance to check

    Returns:
        Dictionary containing detailed WebSocket health information
    """
    return await websocket_health_monitor.get_comprehensive_websocket_health(market_data_manager)