"""Patch dashboard integration for resilient operation."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def patch_dashboard_integration_resilience():
    """Apply resilience patches to dashboard integration."""
    
    try:
        from src.dashboard.dashboard_integration import DashboardIntegrationService
        from src.core.resilience.fallback_provider import get_fallback_provider
        
        # Store original method
        original_update = DashboardIntegrationService._update_dashboard_data
        
        async def resilient_update_dashboard_data(self):
            """Resilient version of dashboard data update."""
            try:
                # Try normal update
                await original_update(self)
            except Exception as e:
                logger.error(f"Dashboard update failed: {e}, using fallback data")
                
                # Use fallback data
                fallback = get_fallback_provider()
                
                self._dashboard_data = {
                    'signals': (await fallback.get_signals_fallback())['signals'],
                    'alerts': [],
                    'alpha_opportunities': [],
                    'system_status': {
                        'status': 'degraded',
                        'message': 'External services unavailable - showing cached data',
                        'timestamp': time.time()
                    },
                    'market_overview': await fallback.get_market_overview_fallback()
                }
                
                logger.info("Dashboard using fallback data")
        
        # Replace method
        DashboardIntegrationService._update_dashboard_data = resilient_update_dashboard_data
        
        logger.info("✅ Dashboard integration patched for resilience")
        
    except ImportError as e:
        logger.error(f"Could not patch dashboard integration: {e}")


def patch_api_routes_resilience():
    """Apply resilience patches to API routes."""
    
    try:
        from src.api.routes import market, dashboard
        from src.core.resilience.circuit_breaker import get_circuit_breaker, CircuitOpenError
        from src.core.resilience.fallback_provider import get_fallback_provider
        
        # Patch market ticker endpoint
        original_get_ticker = market.get_ticker
        
        async def resilient_get_ticker(
            symbol: str,
            exchange_id: str,
            exchange_manager = None
        ):
            """Resilient version of get_ticker."""
            breaker = get_circuit_breaker(f"ticker_{exchange_id}")
            
            try:
                # Try with circuit breaker
                async def fetch():
                    return await original_get_ticker(symbol, exchange_id, exchange_manager)
                
                return await breaker.async_call(fetch)
                
            except CircuitOpenError:
                # Circuit is open, use fallback
                fallback = get_fallback_provider()
                return await fallback.get_ticker_fallback(symbol, exchange_id)
            except Exception as e:
                logger.error(f"Ticker endpoint failed: {e}, using fallback")
                fallback = get_fallback_provider()
                return await fallback.get_ticker_fallback(symbol, exchange_id)
        
        # Replace endpoint
        market.get_ticker = resilient_get_ticker
        
        logger.info("✅ API routes patched for resilience")
        
    except ImportError as e:
        logger.error(f"Could not patch API routes: {e}")
