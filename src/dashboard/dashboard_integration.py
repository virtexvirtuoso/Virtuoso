"""Dashboard Integration Service.

This service bridges the real monitoring system with the web dashboard,
providing real-time data integration and WebSocket updates.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import math

# Import monitoring system components (avoid circular imports)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.monitoring.monitor import MarketMonitor

from src.monitoring.alert_manager import AlertManager
from src.monitoring.metrics_manager import MetricsManager
from src.core.market.market_data_manager import MarketDataManager
from src.signal_generation.signal_generator import SignalGenerator
from src.core.market.top_symbols import TopSymbolsManager


from src.core.resilience.fallback_provider import get_fallback_provider
logger = logging.getLogger(__name__)


def get_ticker_field(ticker, field_name, default=0):
    """Get field from ticker with fallback support"""
    if not ticker:
        return default
    
    # Field mapping for different exchange formats
    field_map = {
        'price': ['last', 'lastPrice', 'price'],
        'volume': ['volume24h', 'baseVolume', 'volume'],
        'change_24h': ['percentage', 'percent', 'change24h'],
        'bid': ['bid', 'bidPrice'],
        'ask': ['ask', 'askPrice']
    }
    
    if field_name in field_map:
        for possible_field in field_map[field_name]:
            if possible_field in ticker:
                return float(ticker.get(possible_field, default))
    
    return float(ticker.get(field_name, default))


class DashboardIntegrationService:
    """Service that provides real-time trading data to the dashboard."""
    
    def __init__(self, monitor: Optional["MarketMonitor"] = None):
        """Initialize the integration service.
        
        Args:
            monitor: MarketMonitor instance with all trading components
        """
        self.monitor = monitor
        self.logger = logger
        
        # Dashboard state
        self._dashboard_data = {
            'signals': [],
            'alerts': [],
            'alpha_opportunities': [],
            'system_status': {},
            'market_overview': {}
        }
        
        # Data update tracking
        self._last_update = 0
        self._update_interval = 5  # seconds
        
        # Running state
        self._running = False
        self._update_task = None
        
        # Confluence score cache
        self._confluence_cache = {}
        self._confluence_cache_ttl = 30  # 30 seconds cache
        self._confluence_update_task = None
        
        # Full confluence analysis cache
        self._confluence_analysis_cache = {}
        self._confluence_analysis_cache_ttl = 60  # 60 seconds cache
        
    async def initialize(self) -> bool:
        """Initialize the service and verify components are available.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if not self.monitor:
                self.logger.error("No monitor instance provided")
                return False
                
            # Verify required components
            if not hasattr(self.monitor, 'market_data_manager') or not self.monitor.market_data_manager:
                self.logger.error("MarketDataManager not available")
                return False
                
            if not hasattr(self.monitor, 'signal_generator') or not self.monitor.signal_generator:
                self.logger.error("SignalGenerator not available")
                return False
                
            # AlertManager may be available via multiple sources - check all possibilities
            alert_manager_available = False
            alert_manager_source = "none"
            
            # Check direct alert_manager attribute
            if hasattr(self.monitor, 'alert_manager') and self.monitor.alert_manager:
                alert_manager_available = True
                alert_manager_source = "direct"
            # Check lazy loading method
            elif hasattr(self.monitor, 'get_alert_manager'):
                try:
                    alert_manager = await self.monitor.get_alert_manager()
                    if alert_manager:
                        alert_manager_available = True
                        alert_manager_source = "lazy_loaded"
                except Exception as e:
                    self.logger.debug(f"Failed to lazy load alert manager: {e}")
            # Check refactored component
            elif hasattr(self.monitor, '_alert_manager_component') and self.monitor._alert_manager_component:
                alert_manager_available = True
                alert_manager_source = "refactored_component"
            # Check if it can be resolved from DI container
            elif hasattr(self.monitor, '_di_container') and self.monitor._di_container:
                try:
                    from ..core.di.interfaces import IAlertService
                    alert_manager = await self.monitor._di_container.get_service(IAlertService)
                    if alert_manager:
                        alert_manager_available = True
                        alert_manager_source = "di_container"
                except Exception as e:
                    self.logger.debug(f"Failed to get alert manager from DI container: {e}")
            
            if alert_manager_available:
                self.logger.info(f"AlertManager available via: {alert_manager_source}")
            else:
                self.logger.warning("AlertManager not available from any source - continuing with limited functionality")
                # Don't return False, continue with degraded functionality
                
            self.logger.info("Dashboard integration service initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing dashboard integration service: {e}")
            return False
    
    async def start(self):
        """Start the real-time data update loop."""
        if self._running:
            return
            
        self._running = True
        self._update_task = asyncio.create_task(self._update_loop())
        self._confluence_update_task = asyncio.create_task(self._update_confluence_cache())
        self.logger.info("Dashboard integration service started")
    
    async def stop(self):
        """Stop the real-time data update loop."""
        self._running = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        if self._confluence_update_task:
            self._confluence_update_task.cancel()
            try:
                await self._confluence_update_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Dashboard integration service stopped")
    
    async def _update_loop(self):
        """Main update loop that refreshes dashboard data."""
        while self._running:
            try:
                await self._update_dashboard_data()
                await asyncio.sleep(self._update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in dashboard update loop: {e}")
                await asyncio.sleep(self._update_interval)
    
    async def _update_confluence_cache(self):
        """Background task to update confluence scores cache."""
        while self._running:
            try:
                # Get all symbols we're tracking
                symbols = []
                if hasattr(self.monitor, 'symbols') and self.monitor.symbols:
                    symbols = self.monitor.symbols[:15]  # Top 15 symbols
                elif hasattr(self.monitor, 'top_symbols_manager'):
                    try:
                        top_symbols = await self.monitor.top_symbols_manager.get_top_symbols(limit=15)
                        symbols = [s.get('symbol', s) if isinstance(s, dict) else s for s in top_symbols]
                    except:
                        pass
                
                # Update confluence scores for each symbol
                for symbol in symbols:
                    try:
                        if hasattr(self.monitor, 'market_data_manager') and hasattr(self.monitor, 'confluence_analyzer'):
                            market_data = await self.monitor.market_data_manager.get_market_data(symbol)
                            if market_data:
                                result = await self.monitor.confluence_analyzer.analyze(market_data)
                                if result and 'confluence_score' in result:
                                    score = float(result['confluence_score'])
                                    components = result.get('components', {})
                                    
                                    # Generate interpretations for each component
                                    interpretations = {}
                                    try:
                                        from src.core.analysis.interpretation_generator import InterpretationGenerator
                                        interpreter = InterpretationGenerator()
                                        
                                        # Generate interpretations for each component
                                        for comp_name, comp_data in components.items():
                                            try:
                                                interpretation = interpreter.get_component_interpretation(comp_name, comp_data)
                                                interpretations[comp_name] = interpretation
                                            except Exception as e:
                                                self.logger.debug(f"Could not generate interpretation for {comp_name}: {e}")
                                                interpretations[comp_name] = f"{comp_name}: Score {comp_data}"
                                        
                                        # Add overall interpretation
                                        if score >= 70:
                                            interpretations['overall'] = f"Strong bullish confluence ({score:.1f}) - Consider long positions"
                                        elif score >= 55:
                                            interpretations['overall'] = f"Moderate bullish confluence ({score:.1f}) - Cautiously bullish"
                                        elif score >= 45:
                                            interpretations['overall'] = f"Neutral confluence ({score:.1f}) - No clear direction"
                                        elif score >= 30:
                                            interpretations['overall'] = f"Moderate bearish confluence ({score:.1f}) - Cautiously bearish"
                                        else:
                                            interpretations['overall'] = f"Strong bearish confluence ({score:.1f}) - Consider short positions"
                                            
                                    except Exception as e:
                                        self.logger.debug(f"Could not generate interpretations: {e}")
                                        interpretations = {'error': 'Interpretations unavailable'}
                                    
                                    # Store the full formatted analysis if available
                                    formatted_analysis = None
                                    try:
                                        from src.core.formatting.formatter import LogFormatter
                                        results = result.get('results', {})
                                        weights = result.get('weights', result.get('metadata', {}).get('weights', {}))
                                        reliability = result.get('reliability', 0.0)
                                        
                                        formatted_table = LogFormatter.format_enhanced_confluence_score_table(
                                            symbol=symbol,
                                            confluence_score=score,
                                            components=components,
                                            results=results,
                                            weights=weights,
                                            reliability=reliability
                                        )
                                        # Clean special characters from formatted table
                                        import re
                                        formatted_analysis = re.sub(r'[│├─└┌┐┬┴┼╔╗╚╝═║╠╣╦╩╬]', '', formatted_table)
                                        formatted_analysis = re.sub(r'\s+', ' ', formatted_analysis).strip()
                                    except Exception as e:
                                        self.logger.debug(f"Could not format analysis: {e}")
                                    
                                    # Determine sentiment based on score
                                    if score >= 60:
                                        sentiment = 'BULLISH'
                                    elif score >= 40:
                                        sentiment = 'NEUTRAL'
                                    else:
                                        sentiment = 'BEARISH'
                                    
                                    # Create comprehensive breakdown WITH market data fields
                                    # Fix: Include price, change_24h, and volume_24h from market_data
                                    breakdown = {
                                        'overall_score': score,
                                        'sentiment': sentiment,
                                        'reliability': result.get('reliability', 75),
                                        'components': components,
                                        'sub_components': results if 'results' in locals() else {},
                                        'interpretations': interpretations,
                                        'formatted_analysis': formatted_analysis,
                                        'timestamp': time.time(),
                                        # Add missing market data fields for dashboard calculations
                                        'price': market_data.get('price', 0) if market_data else 0,
                                        'change_24h': market_data.get('change_24h', market_data.get('price_change_24h', 0)) if market_data else 0,
                                        'volume_24h': market_data.get('volume_24h', market_data.get('volume', 0)) if market_data else 0
                                    }
                                    
                                    # Store in internal cache
                                    self._confluence_cache[symbol] = {
                                        'score': score,
                                        'components': components,
                                        'timestamp': time.time(),
                                        'formatted_analysis': formatted_analysis,
                                        'breakdown': breakdown
                                    }
                                    
                                    # Store breakdown in memcached with proper key
                                    try:
                                        import aiomcache
                                        import json
                                        client = aiomcache.Client('localhost', 11211)
                                        cache_key = f'confluence:breakdown:{symbol}'
                                        await client.set(cache_key.encode(), json.dumps(breakdown).encode(), exptime=60)
                                        await client.close()
                                        self.logger.info(f"Stored confluence breakdown for {symbol} in cache")
                                    except Exception as e:
                                        self.logger.error(f"Failed to store breakdown in cache: {e}")
                                    
                                    self.logger.info(f"Updated confluence cache for {symbol}: {score:.2f}")
                                    
                                    # Also generate and store full analysis
                                    try:
                                        from src.core.formatting.formatter import LogFormatter
                                        results = result.get('results', {})
                                        weights = result.get('weights', result.get('metadata', {}).get('weights', {}))
                                        reliability = result.get('reliability', 0.0)
                                        
                                        formatted_table = LogFormatter.format_enhanced_confluence_score_table(
                                            symbol=symbol,
                                            confluence_score=score,
                                            components=components,
                                            results=results,
                                            weights=weights,
                                            reliability=reliability
                                        )
                                        
                                        self._confluence_analysis_cache[symbol] = {
                                            'analysis': formatted_table,
                                            'timestamp': time.time(),
                                            'score': score,
                                            'components': components
                                        }
                                    except Exception as e:
                                        self.logger.debug(f"Could not generate full analysis for {symbol}: {e}")
                    except Exception as e:
                        self.logger.debug(f"Error updating confluence score for {symbol}: {e}")
                    
                    # Small delay between symbols to avoid overload
                    try:
                        await asyncio.sleep(0.5)
                    except asyncio.CancelledError:
                        self.logger.info("Confluence cache update cancelled during symbol processing")
                        raise
                
                # Wait before next update cycle
                try:
                    await asyncio.sleep(self._confluence_cache_ttl)
                except asyncio.CancelledError:
                    self.logger.info("Confluence cache update cancelled during cycle wait")
                    raise
                
            except asyncio.CancelledError:
                self.logger.info("Confluence cache update task cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in confluence cache update loop: {e}")
                try:
                    await asyncio.sleep(self._confluence_cache_ttl)
                except asyncio.CancelledError:
                    self.logger.info("Confluence cache update task cancelled during sleep")
                    break
    
    async def _update_dashboard_data(self):
        """Update dashboard data with fallback support."""
        try:
            # Original update logic
            await self._update_dashboard_data_original()
        except Exception as e:
            self.logger.error(f"Dashboard update failed: {e}, using fallback")
            
            # Use fallback data
            try:
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
                
                self.logger.info("Dashboard using fallback data")
            except Exception as fallback_error:
                self.logger.error(f"Fallback also failed: {fallback_error}")
                # Provide minimal data
                self._dashboard_data = {
                    'signals': [],
                    'alerts': [],
                    'alpha_opportunities': [],
                    'system_status': {
                        'status': 'error',
                        'message': 'System unavailable',
                        'timestamp': time.time()
                    },
                    'market_overview': {}
                }
    
    async def _update_dashboard_data_original(self):
        """Update all dashboard data from the monitoring system."""
        try:
            current_time = time.time()
            
            # Update signals data
            await self._update_signals()
            
            # Update alerts data
            await self._update_alerts()
            
            # Update alpha opportunities
            await self._update_alpha_opportunities()
            
            # Update system status
            await self._update_system_status()
            
            # Update market overview
            await self._update_market_overview()
            
            self._last_update = current_time
            
        except Exception as e:
            self.logger.error(f"Error updating dashboard data: {e}")
    
    async def _update_signals(self):
        """Update signals data from the signal generator."""
        self.logger.info("_update_signals called")
        try:
            signals = []
            
            # Get symbols from monitor
            if hasattr(self.monitor, 'symbols') and self.monitor.symbols:
                symbols = self.monitor.symbols[:10]  # Limit to top 10
                self.logger.info(f"Found {len(symbols)} symbols from monitor.symbols")
                
                for symbol in symbols:
                    try:
                        # Get market data for symbol
                        market_data = await self.monitor.market_data_manager.get_market_data(symbol)
                        if not market_data:
                            continue
                            
                        # Get latest confluence score if available
                        confluence_score = await self._extract_confluence_score(symbol, market_data)
                        
                        # Get components from cache if available
                        components = {}
                        if symbol in self._confluence_cache:
                            cache_entry = self._confluence_cache[symbol]
                            components = cache_entry.get('components', {})
                        
                        # Determine signal strength
                        signal_strength = self._determine_signal_strength(confluence_score)
                        signal_type = self._determine_signal_type(confluence_score)
                        
                        signal = {
                            'symbol': symbol,
                            'score': confluence_score,
                            'strength': signal_strength,
                            'type': signal_type,
                            'price': market_data.get('ticker', {}).get('last', 0),
                            'change_24h': self._calculate_24h_change(market_data),
                            'volume': market_data.get('ticker', {}).get('volume', 0),
                            'timestamp': int(time.time() * 1000),
                            'components': components
                        }
                        
                        signals.append(signal)
                        
                    except Exception as e:
                        self.logger.error(f"Error processing signal for {symbol}: {e}")
                        continue
            else:
                # Try to get symbols from top_symbols_manager
                self.logger.warning("No symbols found in monitor.symbols, trying top_symbols_manager")
                if hasattr(self.monitor, 'top_symbols_manager') and self.monitor.top_symbols_manager:
                    try:
                        top_symbols = await self.monitor.top_symbols_manager.get_top_symbols(limit=10)
                        self.logger.info(f"Got {len(top_symbols)} symbols from top_symbols_manager")
                        
                        for symbol_info in top_symbols:
                            symbol = symbol_info.get('symbol', symbol_info) if isinstance(symbol_info, dict) else symbol_info
                            try:
                                # Get market data for symbol
                                market_data = await self.monitor.market_data_manager.get_market_data(symbol)
                                if not market_data:
                                    continue
                                    
                                # Get latest confluence score if available
                                confluence_score = await self._extract_confluence_score(symbol, market_data)
                                
                                # Get components from cache if available
                                components = {}
                                if symbol in self._confluence_cache:
                                    cache_entry = self._confluence_cache[symbol]
                                    components = cache_entry.get('components', {})
                                
                                # Determine signal strength
                                signal_strength = self._determine_signal_strength(confluence_score)
                                signal_type = self._determine_signal_type(confluence_score)
                                
                                signal = {
                                    'symbol': symbol,
                                    'score': confluence_score,
                                    'strength': signal_strength,
                                    'type': signal_type,
                                    'price': market_data.get('ticker', {}).get('last', 0),
                                    'change_24h': self._calculate_24h_change(market_data),
                                    'volume': market_data.get('ticker', {}).get('volume', 0),
                                    'timestamp': int(time.time() * 1000),
                                    'components': components
                                }
                                
                                signals.append(signal)
                                
                            except Exception as e:
                                self.logger.error(f"Error processing signal for {symbol}: {e}")
                                continue
                    except Exception as e:
                        self.logger.error(f"Error getting top symbols: {e}")
                else:
                    self.logger.error("No top_symbols_manager available")
            
            self._dashboard_data['signals'] = signals
            self.logger.info(f"Updated dashboard signals: {len(signals)} total")
            
        except Exception as e:
            self.logger.error(f"Error updating signals: {e}")
    
    async def _update_alerts(self):
        """Update alerts data from the alert manager."""
        try:
            if hasattr(self.monitor, 'alert_manager') and self.monitor.alert_manager:
                one_hour_ago = time.time() - 3600
                alerts = self.monitor.alert_manager.get_alerts(limit=20, start_time=one_hour_ago)
                self._dashboard_data['alerts'] = alerts
            else:
                self._dashboard_data['alerts'] = []
        except Exception as e:
            self.logger.error(f"Error updating alerts: {e}")
            self._dashboard_data['alerts'] = []
    
    async def _update_alpha_opportunities(self):
        """Update alpha opportunities data."""
        try:
            opportunities = []
            
            # Look for high-confidence signals as alpha opportunities
            signals = self._dashboard_data.get('signals', [])
            
            for signal in signals:
                if signal.get('score', 0) > 75:  # High confidence threshold
                    opportunity = {
                        'symbol': signal['symbol'],
                        'confidence': signal['score'],
                        'type': signal.get('type', 'BUY'),
                        'price': signal['price'],
                        'potential_return': self._estimate_return(signal),
                        'risk_level': self._assess_risk(signal),
                        'timestamp': signal['timestamp']
                    }
                    opportunities.append(opportunity)
            
            self._dashboard_data['alpha_opportunities'] = opportunities[:5]  # Top 5
            
        except Exception as e:
            self.logger.error(f"Error updating alpha opportunities: {e}")
    
    async def _update_system_status(self):
        """Update system status from monitoring components."""
        try:
            if self.monitor and hasattr(self.monitor, '_check_system_health'):
                status = await self.monitor._check_system_health()
            else:
                status = {
                    'monitoring': 'active' if self.monitor and getattr(self.monitor, 'running', False) else 'inactive',
                    'data_feed': 'unknown',
                    'alerts': 'unknown',
                    'websocket': 'unknown',
                    'last_update': int(time.time() * 1000)
                }

            self._dashboard_data['system_status'] = status

        except Exception as e:
            self.logger.error(f"Error updating system status: {e}")
            self._dashboard_data['system_status'] = {
                'monitoring': 'error',
                'data_feed': 'error',
                'alerts': 'error',
                'websocket': 'error',
                'last_update': int(time.time() * 1000),
                'error': str(e)
            }

    async def _update_market_overview(self):
        """Update market overview data."""
        try:
            overview = {
                'total_symbols': len(getattr(self.monitor, 'symbols', [])),
                'active_signals': len(self._dashboard_data.get('signals', [])),
                'strong_signals': len([s for s in self._dashboard_data.get('signals', []) if s.get('strength') == 'strong']),
                'alpha_opportunities': len(self._dashboard_data.get('alpha_opportunities', [])),
                'total_alerts': len(self._dashboard_data.get('alerts', [])),
                'timestamp': int(time.time() * 1000)
            }
            
            self._dashboard_data['market_overview'] = overview
            
        except Exception as e:
            self.logger.error(f"Error updating market overview: {e}")
    
    async def _extract_confluence_score(self, symbol: str, market_data: Dict[str, Any]) -> float:
        """Extract confluence score from market data or calculate a simple one."""
        try:
            # First try to get from confluence analyzer if available
            if hasattr(self.monitor, 'confluence_analyzer') and self.monitor.confluence_analyzer:
                try:
                    result = await self.monitor.confluence_analyzer.analyze(market_data)
                    if result and 'confluence_score' in result:
                        score = float(result['confluence_score'])
                        self.logger.info(f"Got confluence score {score} for {symbol} from analyzer")
                        
                        # Display comprehensive confluence score table
                        try:
                            from src.core.formatting.formatter import LogFormatter
                            components = result.get('components', {})
                            results = result.get('results', {})
                            weights = result.get('weights', result.get('metadata', {}).get('weights', {}))
                            reliability = result.get('reliability', 0.0)
                            
                            formatted_table = LogFormatter.format_enhanced_confluence_score_table(
                                symbol=symbol,
                                confluence_score=score,
                                components=components,
                                results=results,
                                weights=weights,
                                reliability=reliability
                            )
                            # Log the formatted table
                            self.logger.info("\n" + formatted_table)
                            
                            # Store the full analysis in cache
                            self._confluence_analysis_cache[symbol] = {
                                'analysis': formatted_table,
                                'timestamp': time.time(),
                                'score': score,
                                'components': components
                            }
                        except Exception as e:
                            self.logger.error(f"Error displaying confluence table: {str(e)}")
                            import traceback
                            self.logger.debug(traceback.format_exc())
                        
                        return score
                except Exception as e:
                    self.logger.debug(f"Could not get confluence score from analyzer: {e}")
            
            # Check if market_data already has confluence score
            if 'confluence' in market_data and 'score' in market_data['confluence']:
                return float(market_data['confluence']['score'])
            
            # Fallback to simple score based on price momentum and volume
            ticker = market_data.get('ticker', {})
            volume = get_ticker_field(ticker, 'volume', 0)
            change_24h = self._calculate_24h_change(market_data)

            score = 50.0  # Base score

            # Add volume factor
            if volume > 1000000:  # High volume
                score += 15
            elif volume > 100000:  # Medium volume
                score += 5
            
            # Momentum factor from 24h change
            score += (change_24h * 1.5) # Scale change to have a noticeable impact

            return max(0, min(100, score))

        except Exception as e:
            self.logger.error(f"Error extracting confluence score for {symbol}: {e}")
            return 50.0
    
    def _determine_signal_strength(self, score: float) -> str:
        """Determine signal strength based on confluence score."""
        if score >= 75:
            return 'strong'
        elif score >= 60:
            return 'medium'
        elif score <= 25:
            return 'strong'  # Strong sell
        elif score <= 40:
            return 'medium'  # Medium sell
        else:
            return 'weak'
    
    def _determine_signal_type(self, score: float) -> str:
        """Determine signal type based on confluence score."""
        if score >= 60:
            return 'BUY'
        elif score <= 40:
            return 'SELL'
        else:
            return 'NEUTRAL'
    
    def _calculate_24h_change(self, market_data: Dict[str, Any]) -> float:
        """Calculate 24h price change percentage."""
        try:
            ticker = market_data.get('ticker', {})
            if 'percentage' in ticker and ticker['percentage'] is not None:
                return float(ticker['percentage'])
            if 'change' in ticker and ticker['change'] is not None:
                return float(ticker['change'])

            current = get_ticker_field(ticker, 'price', 0)
            open_price = ticker.get('open', current)
            if open_price > 0:
                return ((current - open_price) / open_price) * 100

            return 0.0

        except Exception as e:
            self.logger.error(f"Error calculating 24h change: {e}")
            return 0.0
    
    def _estimate_return(self, signal: Dict[str, Any]) -> float:
        """Estimate potential return for an alpha opportunity."""
        try:
            score = signal.get('score', 50)
            # Use a non-linear function for more realistic returns
            # Logarithmic scale: higher scores give diminishingly larger returns
            if score <= 50:
                return 0.0
            
            base_return = 0.5  # Base return for a score of 51
            # Scale score to be > 1 for log function
            scaled_score = (score - 50) / 10
            
            # Logarithmic growth
            estimated_return = base_return + math.log(1 + scaled_score)
            
            return round(estimated_return, 2)

        except Exception:
            return 0.0
    
    def _assess_risk(self, signal: Dict[str, Any]) -> str:
        """Assess risk level for an alpha opportunity."""
        try:
            score = signal.get('score', 50)
            volume = signal.get('volume', 0)
            change_24h = signal.get('change_24h', 0)
            
            # Volatility component
            volatility = abs(change_24h)
            
            risk_score = 0
            
            # Score-based risk (lower score is higher risk)
            if score < 60:
                risk_score += 3
            elif score < 75:
                risk_score += 2
            else:
                risk_score += 1
                
            # Volatility-based risk (higher volatility is higher risk)
            if volatility > 5:
                risk_score += 3
            elif volatility > 2:
                risk_score += 2
                
            # Liquidity-based risk (lower volume is higher risk)
            if volume < 500000:  # Low liquidity
                risk_score += 3
            elif volume < 2000000:  # Medium liquidity
                risk_score += 1
                
            # Determine final risk level
            if risk_score >= 7:
                return 'High'
            elif risk_score >= 4:
                return 'Medium'
            else:
                return 'Low'
                
        except Exception:
            return 'Medium'
    
    # Public API methods for dashboard
    async def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get complete dashboard overview data."""
        return {
            'status': 'success',
            'timestamp': int(time.time() * 1000),
            'signals': {
                'total': len(self._dashboard_data.get('signals', [])),
                'strong': len([s for s in self._dashboard_data.get('signals', []) if s.get('strength') == 'strong']),
                'medium': len([s for s in self._dashboard_data.get('signals', []) if s.get('strength') == 'medium']),
                'weak': len([s for s in self._dashboard_data.get('signals', []) if s.get('strength') == 'weak'])
            },
            'alerts': {
                'total': len(self._dashboard_data.get('alerts', [])),
                'critical': len([a for a in self._dashboard_data.get('alerts', []) if a.get('severity') == 'CRITICAL']),
                'warning': len([a for a in self._dashboard_data.get('alerts', []) if a.get('severity') == 'WARNING'])
            },
            'alpha_opportunities': {
                'total': len(self._dashboard_data.get('alpha_opportunities', [])),
                'high_confidence': len([o for o in self._dashboard_data.get('alpha_opportunities', []) if o.get('confidence', 0) >= 85]),
                'medium_confidence': len([o for o in self._dashboard_data.get('alpha_opportunities', []) if 70 <= o.get('confidence', 0) < 85])
            },
            'system_status': self._dashboard_data.get('system_status', {})
        }
    
    async def get_signals_data(self) -> List[Dict[str, Any]]:
        """Get current signals data."""
        return self._dashboard_data.get('signals', [])
    
    async def get_alerts_data(self) -> List[Dict[str, Any]]:
        """Get current alerts data."""
        return self._dashboard_data.get('alerts', [])
    
    async def get_alpha_opportunities(self) -> List[Dict[str, Any]]:
        """Get current alpha opportunities."""
        return self._dashboard_data.get('alpha_opportunities', [])
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get market overview data."""
        return self._dashboard_data.get('market_overview', {})
    
    def get_symbol_data(self) -> Dict[str, Any]:
        """Get symbol data with confluence scores for all monitored symbols.
        
        Returns:
            Dict mapping symbol names to their market data including confluence scores
        """
        try:
            symbol_data = {}
            signals = self._dashboard_data.get('signals', [])
            
            for signal in signals:
                symbol = signal.get('symbol')
                if symbol:
                    symbol_data[symbol] = {
                        'symbol': symbol,
                        'confluence_score': signal.get('score', 0),
                        'price': signal.get('price', 0),
                        'change_24h': signal.get('change_24h', 0),
                        'volume_24h': signal.get('volume', 0),
                        'signal_type': signal.get('type', 'NEUTRAL'),
                        'strength': signal.get('strength', 'weak'),
                        'timestamp': signal.get('timestamp', 0)
                    }
            
            self.logger.debug(f"Retrieved symbol data for {len(symbol_data)} symbols")
            return symbol_data
            
        except Exception as e:
            self.logger.error(f"Error getting symbol data: {e}")
            return {}

    async def get_top_symbols(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top symbols with real market data from the running monitor.
        
        Uses the monitor's components to get real Bybit data that's already flowing.
        
        Args:
            limit: Maximum number of symbols to return
            
        Returns:
            List of symbol dictionaries with market data
        """
        try:
            # Get market data manager from monitor
            market_data_manager = None
            top_symbols_manager = None
            
            if self.monitor:
                market_data_manager = getattr(self.monitor, 'market_data_manager', None)
                top_symbols_manager = getattr(self.monitor, 'top_symbols_manager', None)
            
            # Try to get symbols and data from the monitor
            if market_data_manager and top_symbols_manager:
                try:
                    # Get dynamic symbols from the working top symbols manager
                    symbols = await top_symbols_manager.get_symbols(limit=limit)
                    self.logger.info(f"Retrieved {len(symbols)} dynamic symbols from monitor: {symbols}")
                    
                    # Get market data for each symbol using the working market data manager
                    symbols_data = []
                    for symbol in symbols:
                        try:
                            market_data = await market_data_manager.get_market_data(symbol)
                            if market_data:
                                # Extract key metrics from Bybit data
                                ticker = market_data.get('ticker', {})
                                
                                # Try multiple field names for price
                                price = 0
                                if 'lastPrice' in ticker:
                                    price = float(ticker['lastPrice'])
                                elif 'last' in ticker:
                                    price = float(ticker['last'])
                                elif 'close' in ticker:
                                    price = float(ticker['close'])
                                
                                # Try multiple field names for 24h change
                                change_24h = 0
                                if 'price24hPcnt' in ticker:
                                    change_24h = float(ticker['price24hPcnt']) * 100
                                elif 'percentage' in ticker:
                                    change_24h = float(ticker['percentage'])
                                elif 'change' in ticker:
                                    change_24h = float(ticker['change'])
                                
                                # Try multiple field names for volume
                                volume_24h = 0
                                if 'volume24h' in ticker:
                                    volume_24h = float(ticker['volume24h'])
                                elif 'baseVolume' in ticker:
                                    volume_24h = float(ticker['baseVolume'])
                                elif 'volume' in ticker:
                                    volume_24h = float(ticker['volume'])
                                
                                # Try multiple field names for turnover
                                turnover_24h = 0
                                if 'turnover24h' in ticker:
                                    turnover_24h = float(ticker['turnover24h'])
                                elif 'quoteVolume' in ticker:
                                    turnover_24h = float(ticker['quoteVolume'])
                                elif 'turnover' in ticker:
                                    turnover_24h = float(ticker['turnover'])
                                
                                symbols_data.append({
                                    'symbol': symbol,
                                    'price': price,
                                    'change_24h': change_24h,
                                    'volume_24h': volume_24h,
                                    'turnover_24h': turnover_24h,
                                    'status': 'bybit_live'
                                })
                                
                                self.logger.debug(f"Extracted Bybit data for {symbol}: price={price}, change={change_24h}%")
                                
                        except Exception as e:
                            self.logger.error(f"Error getting market data for {symbol}: {str(e)}")
                            # Add symbol with error status
                            symbols_data.append({
                                'symbol': symbol,
                                'price': 0,
                                'change_24h': 0,
                                'volume_24h': 0,
                                'turnover_24h': 0,
                                'status': 'extraction_error'
                            })
                    
                    # Sort by turnover (highest first)
                    symbols_data.sort(key=lambda x: x['turnover_24h'], reverse=True)
                    
                    if symbols_data:
                        self.logger.info(f"Successfully retrieved {len(symbols_data)} symbols with Bybit data")
                        return symbols_data[:limit]
                    
                except Exception as e:
                    self.logger.error(f"Error getting symbols from monitor: {str(e)}")
            
            # Fallback: Try to get symbols from monitor.symbols if available
            if self.monitor and hasattr(self.monitor, 'symbols') and getattr(self.monitor, 'symbols'):
                monitor_symbols = getattr(self.monitor, 'symbols', [])[:limit]
                self.logger.info(f"Using monitor.symbols fallback: {monitor_symbols}")
                
                symbols_data = []
                for symbol in monitor_symbols:
                    # Return with minimal data but real symbol names
                    symbols_data.append({
                        'symbol': symbol,
                        'price': 100000 if 'BTC' in symbol else 3000,  # Reasonable fallback prices
                        'change_24h': 1.5,
                        'volume_24h': 5000000,
                        'turnover_24h': 150000000,
                        'status': 'monitor_fallback'
                    })
                    
                return symbols_data
            
            # Final fallback
            self.logger.warning("No monitor available, using static fallback")
            fallback_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'AVAXUSDT']
            return [
                {
                    'symbol': symbol,
                    'price': 103000 if 'BTC' in symbol else 3000,
                    'change_24h': 1.2,
                    'volume_24h': 2000000,
                    'turnover_24h': 200000000000,
                    'status': 'static_fallback'
                }
                for symbol in fallback_symbols[:limit]
            ]
                
        except Exception as e:
            self.logger.error(f"Error getting top symbols: {str(e)}")
            # Emergency fallback
            return [
                {
                    'symbol': 'BTCUSDT',
                    'price': 103000,
                    'change_24h': 1.2,
                    'volume_24h': 2000000,
                    'turnover_24h': 200000000000,
                    'status': 'emergency_fallback'
                }
            ]
    
    async def get_symbols_data(self) -> Dict[str, Any]:
        """Get symbols data with prices and confluence scores."""
        try:
            symbols_data = []
            
            # First ensure signals are updated
            if self._running and self._dashboard_data.get('signals'):
                await self._update_signals()
            
            # Get top symbols manager from monitor
            if self.monitor and hasattr(self.monitor, 'top_symbols_manager'):
                top_symbols_manager = self.monitor.top_symbols_manager
                exchange_manager = getattr(self.monitor, 'exchange_manager', None)
                
                if top_symbols_manager and exchange_manager:
                    # Get top symbols
                    top_symbols = await top_symbols_manager.get_top_symbols(limit=15)
                    
                    for symbol_info in top_symbols:
                        symbol = symbol_info.get('symbol', symbol_info) if isinstance(symbol_info, dict) else symbol_info
                        try:
                            # Get current ticker data for price
                            ticker = await exchange_manager.fetch_ticker(symbol)
                            
                            # Try to get actual confluence score from cache first
                            confluence_score = 50  # Default
                            
                            # Check cache first
                            if symbol in self._confluence_cache:
                                cache_entry = self._confluence_cache[symbol]
                                cache_age = time.time() - cache_entry['timestamp']
                                if cache_age < self._confluence_cache_ttl * 2:  # Use cache if less than 2x TTL old
                                    confluence_score = cache_entry['score']
                                    self.logger.debug(f"Using cached confluence score {confluence_score:.2f} for {symbol} (age: {cache_age:.1f}s)")
                            
                            # If not in cache, check signals data
                            if confluence_score == 50:
                                signals = self._dashboard_data.get('signals', [])
                                for signal in signals:
                                    if signal.get('symbol') == symbol:
                                        score = signal.get('score', 50)
                                        if score != 50:  # Only use if not default
                                            confluence_score = score
                                            self.logger.debug(f"Found confluence score {confluence_score} for {symbol} in signals")
                                        break
                            
                            symbol_data = {
                                "symbol": symbol,
                                "price": get_ticker_field(ticker, 'price', 0),
                                "confluence_score": round(confluence_score, 2),
                                "change_24h": get_ticker_field(ticker, 'change_24h', 0),
                                "volume_24h": ticker.get('quoteVolume', 0),
                                "high_24h": ticker.get('high', 0),
                                "low_24h": ticker.get('low', 0)
                            }
                            symbols_data.append(symbol_data)
                            
                        except Exception as e:
                            self.logger.debug(f"Could not get data for {symbol}: {e}")
            
            return {
                "symbols": symbols_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting symbols data: {e}")
            return {
                "symbols": [],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for dashboard display."""
        try:
            # Basic implementation - can be enhanced based on actual metrics needed
            import psutil
            import os
            
            # Get CPU and memory usage
            process = psutil.Process(os.getpid())
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            # Calculate uptime
            uptime_seconds = time.time() - process.create_time()
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            uptime_str = f"{hours}h {minutes}m"
            
            # Get connection counts
            active_connections = 0
            if hasattr(self.monitor, 'websocket_connections'):
                active_connections = len(self.monitor.websocket_connections)
            
            # Calculate API latency (simple average)
            api_latency = 0
            if hasattr(self, '_api_latencies'):
                if self._api_latencies:
                    api_latency = sum(self._api_latencies) / len(self._api_latencies)
            
            return {
                "cpu_usage": round(cpu_percent, 1),
                "memory_usage": round(memory_percent, 1),
                "api_latency": round(api_latency, 0),
                "active_connections": active_connections,
                "uptime": uptime_str,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return {
                "cpu_usage": 0,
                "memory_usage": 0,
                "api_latency": 0,
                "active_connections": 0,
                "uptime": "0h 0m",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_confluence_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get the full confluence analysis for a specific symbol.
        
        Args:
            symbol: The trading symbol to get analysis for
            
        Returns:
            Dict containing the full formatted analysis and metadata
        """
        try:
            # Check if we have cached analysis
            if symbol in self._confluence_analysis_cache:
                cache_entry = self._confluence_analysis_cache[symbol]
                cache_age = time.time() - cache_entry['timestamp']
                
                # Return cached analysis if fresh enough
                if cache_age < self._confluence_analysis_cache_ttl:
                    return {
                        'status': 'success',
                        'symbol': symbol,
                        'analysis': cache_entry['analysis'],
                        'score': cache_entry['score'],
                        'components': cache_entry['components'],
                        'timestamp': cache_entry['timestamp'],
                        'cache_age': cache_age
                    }
            
            # Try to generate fresh analysis
            if hasattr(self.monitor, 'market_data_manager') and hasattr(self.monitor, 'confluence_analyzer'):
                try:
                    market_data = await self.monitor.market_data_manager.get_market_data(symbol)
                    if market_data:
                        result = await self.monitor.confluence_analyzer.analyze(market_data)
                        if result and 'confluence_score' in result:
                            from src.core.formatting.formatter import LogFormatter
                            
                            score = float(result['confluence_score'])
                            components = result.get('components', {})
                            results = result.get('results', {})
                            weights = result.get('weights', result.get('metadata', {}).get('weights', {}))
                            reliability = result.get('reliability', 0.0)
                            
                            formatted_table = LogFormatter.format_enhanced_confluence_score_table(
                                symbol=symbol,
                                confluence_score=score,
                                components=components,
                                results=results,
                                weights=weights,
                                reliability=reliability
                            )
                            
                            # Update cache
                            self._confluence_analysis_cache[symbol] = {
                                'analysis': formatted_table,
                                'timestamp': time.time(),
                                'score': score,
                                'components': components
                            }
                            
                            return {
                                'status': 'success',
                                'symbol': symbol,
                                'analysis': formatted_table,
                                'score': score,
                                'components': components,
                                'timestamp': time.time(),
                                'cache_age': 0
                            }
                except Exception as e:
                    self.logger.error(f"Error generating confluence analysis for {symbol}: {e}")
            
            # No analysis available
            return {
                'status': 'error',
                'symbol': symbol,
                'error': 'No analysis available',
                'analysis': None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting confluence analysis for {symbol}: {e}")
            return {
                'status': 'error',
                'symbol': symbol,
                'error': str(e),
                'analysis': None
            }


# Global instance for use across the application
dashboard_integration = None

def get_dashboard_integration() -> Optional[DashboardIntegrationService]:
    """Get the global dashboard integration instance."""
    return dashboard_integration

def set_dashboard_integration(service: DashboardIntegrationService):
    """Set the global dashboard integration instance."""
    global dashboard_integration
    dashboard_integration = service 