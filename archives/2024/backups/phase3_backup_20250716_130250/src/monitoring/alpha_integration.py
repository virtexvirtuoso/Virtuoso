"""
Alpha Generation Integration for Market Monitor
Integrates BitcoinBetaAlphaDetector with existing monitoring and alert systems.
Enhanced with volume confirmation and market regime filtering.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import numpy as np

try:
    from src.reports.bitcoin_beta_alpha_detector import BitcoinBetaAlphaDetector, AlphaOpportunity
except ImportError:
    try:
        from reports.bitcoin_beta_alpha_detector import BitcoinBetaAlphaDetector, AlphaOpportunity
    except ImportError:
        # Fallback for when the module is not available
        BitcoinBetaAlphaDetector = None
        AlphaOpportunity = None


class AlphaMonitorIntegration:
    """Integration layer for alpha generation with existing monitor system."""
    
    def __init__(self, monitor, alert_manager, config: Dict[str, Any] = None):
        """Initialize alpha monitoring integration.
        
        Args:
            monitor: MarketMonitor instance
            alert_manager: AlertManager instance
            config: Configuration dictionary
        """
        self.monitor = monitor
        self.alert_manager = alert_manager
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Alpha detection configuration
        alpha_config = self.config.get('alpha_detection', {})
        self.enabled = alpha_config.get('enabled', True)
        self.alpha_alert_threshold = alpha_config.get('alert_threshold', 0.85)  # Increased default
        self.check_interval = alpha_config.get('check_interval', 900)  # 15 minutes default
        
        # Enhanced detection parameters
        detection_params = alpha_config.get('detection_params', {})
        self.min_alpha_threshold = detection_params.get('min_alpha_threshold', 0.04)  # 4% minimum
        self.beta_expansion_threshold = detection_params.get('beta_expansion_threshold', 2.0)  # 100% increase
        self.volume_confirmation_required = detection_params.get('volume_confirmation_required', True)
        self.min_volume_multiplier = detection_params.get('min_volume_multiplier', 2.0)  # 2x average volume
        self.market_regime_filtering = detection_params.get('market_regime_filtering', True)
        self.allowed_regimes = detection_params.get('allowed_regimes', ["TRENDING_UP", "TRENDING_DOWN", "VOLATILE"])
        
        # Enhanced throttling configuration
        throttling_config = alpha_config.get('alerts', {}).get('throttling', {})
        self.min_interval_per_symbol = throttling_config.get('min_interval_per_symbol', 3600)  # 1 hour
        self.max_alerts_per_hour = throttling_config.get('max_alerts_per_hour', 5)
        self.high_confidence_cooldown = throttling_config.get('high_confidence_cooldown', 7200)  # 2 hours
        self.max_alerts_per_symbol_per_day = throttling_config.get('max_alerts_per_symbol_per_day', 3)
        self.priority_filtering = throttling_config.get('priority_filtering', True)
        
        # Debug logging configuration
        self.debug_logging = alpha_config.get('debug_logging', False)
        
        # Fallback symbols if dynamic symbols are not available
        self.fallback_symbols = alpha_config.get('symbols', [
            'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'XRPUSDT', 'DOGEUSDT'
        ])
        
        # Dynamic symbols cache
        self._dynamic_symbols_cache = set()
        self._last_symbols_update = 0
        
        # Enhanced statistics and tracking
        self.alpha_opportunities_sent = 0
        self.alpha_opportunities_filtered = 0  # New: track filtered alerts
        self.last_alpha_check = {}
        self.daily_alert_counts = {}  # Track daily alerts per symbol
        self.hourly_alert_counts = []  # Track hourly alert counts
        
        # Store original method for cleanup
        self._original_process_symbol = None
        
        # Initialize alpha detector
        if BitcoinBetaAlphaDetector is not None:
            try:
                self.alpha_detector = BitcoinBetaAlphaDetector(config=self.config)
                self.logger.info("Alpha detector initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize alpha detector: {str(e)}")
                self.alpha_detector = None
                self.enabled = False
        else:
            self.logger.warning("Alpha detector not available - module not found")
            self.alpha_detector = None
            self.enabled = False
        
        self.logger.info(f"Enhanced Alpha monitor integration initialized:")
        self.logger.info(f"  - Confidence threshold: {self.alpha_alert_threshold:.1%}")
        self.logger.info(f"  - Alpha threshold: {self.min_alpha_threshold:.1%}")
        self.logger.info(f"  - Volume confirmation: {self.volume_confirmation_required}")
        self.logger.info(f"  - Market regime filtering: {self.market_regime_filtering}")
        self.logger.info(f"  - Check interval: {self.check_interval}s")
        self.logger.info("🔄 Using DYNAMIC symbols from TopSymbolsManager for alpha detection")
    
    async def get_monitored_symbols(self) -> set:
        """Get current list of symbols to monitor for alpha opportunities.
        
        Returns:
            Set of symbol strings to monitor
        """
        try:
            current_time = datetime.now().timestamp()
            
            # Check if we need to refresh the symbols cache
            if (current_time - self._last_symbols_update) > self.check_interval:
                self.logger.debug("Refreshing dynamic symbols cache for alpha detection")
                
                # Try to get symbols from TopSymbolsManager
                if hasattr(self.monitor, 'top_symbols_manager') and self.monitor.top_symbols_manager:
                    try:
                        # Get top 15 symbols from the manager
                        dynamic_symbols = await self.monitor.top_symbols_manager.get_symbols(limit=15)
                        if dynamic_symbols:
                            self._dynamic_symbols_cache = set(dynamic_symbols)
                            self._last_symbols_update = current_time
                            self.logger.info(f"📊 Updated alpha monitoring to track {len(self._dynamic_symbols_cache)} dynamic symbols")
                            self.logger.debug(f"Dynamic symbols: {', '.join(sorted(self._dynamic_symbols_cache))}")
                        else:
                            self.logger.warning("TopSymbolsManager returned no symbols, using cached or fallback")
                    except Exception as e:
                        self.logger.error(f"Error getting dynamic symbols from TopSymbolsManager: {str(e)}")
                        # Keep using cached symbols or fallback
                else:
                    self.logger.warning("TopSymbolsManager not available, using fallback symbols")
            
            # Return dynamic symbols if available, otherwise fallback
            if self._dynamic_symbols_cache:
                return self._dynamic_symbols_cache
            else:
                self.logger.info("Using fallback symbols for alpha detection")
                return self.fallback_symbols
                
        except Exception as e:
            self.logger.error(f"Error getting monitored symbols: {str(e)}")
            return self.fallback_symbols
    
    async def integrate_with_monitor(self):
        """Integrate alpha detection with the existing monitor's processing cycle."""
        if not self.enabled:
            self.logger.info("Alpha detection disabled in config")
            return
            
        # Store original method
        self._original_process_symbol = self.monitor._process_symbol
        
        # Create enhanced version
        async def enhanced_process_symbol(symbol: str):
            """Enhanced symbol processing with alpha detection."""
            # Run original processing first
            await self._original_process_symbol(symbol)
            
            # Add alpha detection if this symbol qualifies
            if await self._should_check_alpha(symbol):
                await self._check_alpha_opportunities(symbol)
        
        # Replace monitor's method
        self.monitor._process_symbol = enhanced_process_symbol
        self.logger.info("Alpha detection integrated with monitor processing cycle")
    
    async def _should_check_alpha(self, symbol: str) -> bool:
        """Determine if we should check for alpha opportunities on this symbol."""
        try:
            # Extract symbol string if needed
            symbol_str = symbol['symbol'] if isinstance(symbol, dict) and 'symbol' in symbol else symbol
            
            # Get current monitored symbols (dynamic)
            monitored_symbols = await self.get_monitored_symbols()
            
            # Check if symbol is in monitored list
            if symbol_str not in monitored_symbols:
                return False
                
            # Check if enough time has passed since last check
            last_check = self.last_alpha_check.get(symbol_str, 0)
            return (datetime.now().timestamp() - last_check) >= self.check_interval
            
        except Exception as e:
            self.logger.error(f"Error checking if should analyze alpha for {symbol}: {str(e)}")
            return False
    
    async def _check_alpha_opportunities(self, symbol: str):
        """Check for alpha opportunities and send alerts if found."""
        try:
            # Extract symbol string
            symbol_str = symbol['symbol'] if isinstance(symbol, dict) and 'symbol' in symbol else symbol
            
            # Get market data for both the symbol and Bitcoin
            market_data = await self._get_alpha_market_data(symbol_str)
            
            if not market_data:
                self.logger.debug(f"No market data available for alpha analysis: {symbol_str}")
                return
            
            # Convert market data to beta analysis format expected by detector
            beta_analysis = self._convert_to_beta_analysis(market_data)
            
            if not beta_analysis:
                self.logger.debug(f"Could not convert market data to beta analysis format for {symbol_str}")
                return
            
            # Detect alpha opportunities
            opportunities = await asyncio.to_thread(
                self.alpha_detector.detect_alpha_opportunities,
                beta_analysis
            )
            
            # Update last check time
            self.last_alpha_check[symbol_str] = datetime.now().timestamp()
            
            # Send alerts for high-confidence opportunities
            for opportunity in opportunities:
                if opportunity.confidence >= self.alpha_alert_threshold:
                    await self._send_alpha_alert(symbol_str, opportunity, market_data)
                    
        except Exception as e:
            self.logger.error(f"Error checking alpha opportunities for {symbol}: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
    
    def _convert_to_beta_analysis(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Dict[str, Dict[str, float]]]]:
        """Convert market data to beta analysis format expected by alpha detector."""
        try:
            if self.debug_logging:
                self.logger.debug(f"Converting market data to beta analysis format")
            
            asset_data = market_data.get('asset', {})
            bitcoin_data = market_data.get('bitcoin', {})
            
            self.logger.debug(f"Asset data keys: {list(asset_data.keys()) if asset_data else 'None'}")
            self.logger.debug(f"Bitcoin data keys: {list(bitcoin_data.keys()) if bitcoin_data else 'None'}")
            
            symbol = asset_data.get('symbol', 'UNKNOWN')
            if symbol == 'UNKNOWN':
                self.logger.debug("No symbol found in asset data")
                return None
            
            # Get OHLCV data for both assets
            asset_ohlcv = asset_data.get('ohlcv', {})
            bitcoin_ohlcv = bitcoin_data.get('ohlcv', {})
            
            self.logger.debug(f"Asset OHLCV timeframes: {list(asset_ohlcv.keys()) if asset_ohlcv else 'None'}")
            self.logger.debug(f"Bitcoin OHLCV timeframes: {list(bitcoin_ohlcv.keys()) if bitcoin_ohlcv else 'None'}")
            
            if not asset_ohlcv or not bitcoin_ohlcv:
                self.logger.debug(f"Missing OHLCV data - Asset: {bool(asset_ohlcv)}, Bitcoin: {bool(bitcoin_ohlcv)}")
                return None
            
            # Build beta analysis structure: timeframe -> symbol -> metrics
            beta_analysis = {}
            
            # Map our timeframes to detector expected format
            timeframe_mapping = {
                '1m': 'base',
                'base': 'base',
                '5m': 'ltf', 
                'ltf': 'ltf',
                '30m': 'mtf',
                'mtf': 'mtf',
                '4h': 'htf',
                'htf': 'htf'
            }
            
            successful_conversions = 0
            
            for tf, detector_tf in timeframe_mapping.items():
                if tf in asset_ohlcv and tf in bitcoin_ohlcv:
                    asset_tf_data = asset_ohlcv[tf]
                    bitcoin_tf_data = bitcoin_ohlcv[tf]
                    
                    self.logger.debug(f"Processing timeframe {tf} -> {detector_tf} for {symbol}")
                    
                    # Calculate basic metrics for this timeframe
                    metrics = self._calculate_beta_metrics(
                        asset_tf_data, 
                        bitcoin_tf_data,
                        asset_data.get('price', 0),
                        bitcoin_data.get('price', 0)
                    )
                    
                    if metrics:
                        beta_analysis[detector_tf] = {
                            symbol: metrics
                        }
                        successful_conversions += 1
                        self.logger.debug(f"Successfully calculated metrics for {tf} timeframe: beta={metrics.get('beta', 'N/A')}")
                    else:
                        self.logger.debug(f"Failed to calculate metrics for {tf} timeframe")
                else:
                    missing_asset = tf not in asset_ohlcv
                    missing_bitcoin = tf not in bitcoin_ohlcv
                    self.logger.debug(f"Timeframe {tf} missing - Asset: {missing_asset}, Bitcoin: {missing_bitcoin}")
            
            if successful_conversions > 0:
                self.logger.debug(f"Beta analysis conversion successful for {symbol}: {successful_conversions} timeframes processed")
                return beta_analysis
            else:
                self.logger.debug(f"Beta analysis conversion failed for {symbol}: no valid timeframes found")
                return None
            
        except Exception as e:
            self.logger.error(f"Error converting market data to beta analysis: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None
    
    def _calculate_beta_metrics(self, asset_ohlcv: Dict[str, float], bitcoin_ohlcv: Dict[str, float], 
                               asset_price: float, bitcoin_price: float) -> Optional[Dict[str, float]]:
        """Calculate beta metrics from OHLCV data."""
        try:
            # Extract close prices
            asset_close = asset_ohlcv.get('close', asset_price)
            bitcoin_close = bitcoin_ohlcv.get('close', bitcoin_price)
            
            # Simple calculations for demonstration
            # In production, you'd want more sophisticated beta/alpha calculations
            
            # Mock beta calculation (normally requires price history)
            price_ratio = asset_close / bitcoin_close if bitcoin_close > 0 else 1.0
            
            # Estimate beta based on price action vs open
            asset_return = (asset_close - asset_ohlcv.get('open', asset_close)) / asset_ohlcv.get('open', asset_close) if asset_ohlcv.get('open', 0) > 0 else 0
            bitcoin_return = (bitcoin_close - bitcoin_ohlcv.get('open', bitcoin_close)) / bitcoin_ohlcv.get('open', bitcoin_close) if bitcoin_ohlcv.get('open', 0) > 0 else 0
            
            # Simple beta estimate
            beta = asset_return / bitcoin_return if bitcoin_return != 0 else 1.0
            
            # Cap extreme values
            beta = max(-5.0, min(5.0, beta))
            
            # Correlation estimate (simplified)
            correlation = 0.8 if abs(beta) > 0.5 else 0.6
            
            # Alpha estimate 
            alpha = asset_return - (beta * bitcoin_return)
            
            return {
                'beta': beta,
                'correlation': correlation,
                'alpha': alpha,
                'rolling_beta_30': beta,  # Simplified - same as beta
                'price': asset_close,
                'volume': asset_ohlcv.get('volume', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating beta metrics: {str(e)}")
            return None
    
    async def _get_alpha_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get market data needed for alpha detection with proper format conversion."""
        try:
            if self.debug_logging:
                self.logger.debug(f"Fetching alpha market data for {symbol}")
            
            # Get data for the target symbol
            symbol_data = await self.monitor.fetch_market_data(symbol)
            
            # Get Bitcoin data for comparison
            btc_data = await self.monitor.fetch_market_data('BTCUSDT')
            
            if self.debug_logging:
                self.logger.debug(f"Symbol data available: {bool(symbol_data)}")
                self.logger.debug(f"BTC data available: {bool(btc_data)}")
            
            if not symbol_data:
                self.logger.warning(f"No market data available for {symbol}")
                return None
                
            if not btc_data:
                self.logger.warning(f"No Bitcoin market data available for comparison")
                return None
            
            # Log the structure of the received data
            if self.debug_logging:
                if symbol_data:
                    self.logger.debug(f"Symbol data keys: {list(symbol_data.keys())}")
                if btc_data:
                    self.logger.debug(f"BTC data keys: {list(btc_data.keys())}")
            
            # Convert data to alpha detector format
            asset_formatted = self._format_asset_data(symbol, symbol_data)
            bitcoin_formatted = self._format_asset_data('BTCUSDT', btc_data)
            
            # Check if we have valid formatted data
            if not asset_formatted.get('price', 0) and not asset_formatted.get('ohlcv', {}):
                self.logger.warning(f"No valid price or OHLCV data for {symbol} after formatting")
                
            if not bitcoin_formatted.get('price', 0) and not bitcoin_formatted.get('ohlcv', {}):
                self.logger.warning(f"No valid price or OHLCV data for BTCUSDT after formatting")
            
            alpha_data = {
                'asset': asset_formatted,
                'bitcoin': bitcoin_formatted,
                'timestamp': datetime.now().timestamp()
            }
            
            if self.debug_logging:
                self.logger.debug(f"Alpha market data prepared for {symbol}")
            return alpha_data
            
        except Exception as e:
            self.logger.error(f"Error getting alpha market data for {symbol}: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None
    
    def _format_asset_data(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format market data for alpha detector consumption."""
        try:
            # Log the structure of market data for debugging
            self.logger.debug(f"Formatting asset data for {symbol}. Market data keys: {list(market_data.keys()) if market_data else 'None'}")
            
            # Extract price from multiple possible sources
            price = 0
            
            # Try ticker first
            if 'ticker' in market_data and market_data['ticker']:
                ticker = market_data['ticker']
                self.logger.debug(f"Found ticker data for {symbol}: {list(ticker.keys()) if isinstance(ticker, dict) else type(ticker)}")
                if isinstance(ticker, dict):
                    price = ticker.get('last', ticker.get('close', ticker.get('price', ticker.get('bid', ticker.get('ask', 0)))))
            
            # If no price from ticker, try to extract from OHLCV data
            if not price and 'ohlcv' in market_data and market_data['ohlcv']:
                ohlcv_data = market_data['ohlcv']
                self.logger.debug(f"Trying to extract price from OHLCV for {symbol}. OHLCV keys: {list(ohlcv_data.keys()) if isinstance(ohlcv_data, dict) else type(ohlcv_data)}")
                
                # Try different timeframes to get the latest close price
                for timeframe in ['base', '1m', 'ltf', '5m', 'mtf', '30m', 'htf', '4h']:
                    if timeframe in ohlcv_data:
                        tf_data = ohlcv_data[timeframe]
                        if hasattr(tf_data, 'iloc') and len(tf_data) > 0:
                            # DataFrame format
                            try:
                                latest_close = tf_data.iloc[-1]['close']
                                if latest_close and latest_close > 0:
                                    price = float(latest_close)
                                    self.logger.debug(f"Extracted price {price} from {timeframe} timeframe for {symbol}")
                                    break
                            except (KeyError, IndexError, ValueError) as e:
                                self.logger.debug(f"Could not extract price from {timeframe} DataFrame: {str(e)}")
                                continue
                        elif isinstance(tf_data, dict) and 'close' in tf_data:
                            # Dictionary format
                            try:
                                price = float(tf_data['close'])
                                self.logger.debug(f"Extracted price {price} from {timeframe} dict for {symbol}")
                                break
                            except (ValueError, TypeError) as e:
                                self.logger.debug(f"Could not extract price from {timeframe} dict: {str(e)}")
                                continue
            
            # Extract volume from ticker or other sources
            volume = 0
            if 'ticker' in market_data and market_data['ticker']:
                ticker = market_data['ticker']
                if isinstance(ticker, dict):
                    volume = ticker.get('baseVolume', ticker.get('volume', ticker.get('quoteVolume', 0)))
            
            # Format OHLCV data for multiple timeframes
            formatted_ohlcv = {}
            if 'ohlcv' in market_data and market_data['ohlcv']:
                ohlcv_data = market_data['ohlcv']
                self.logger.debug(f"Processing OHLCV data for {symbol} with keys: {list(ohlcv_data.keys()) if isinstance(ohlcv_data, dict) else type(ohlcv_data)}")
                
                if isinstance(ohlcv_data, dict):
                    for timeframe, ohlcv in ohlcv_data.items():
                        try:
                            formatted_tf_data = self._format_ohlcv_for_timeframe(ohlcv)
                            if formatted_tf_data and any(v > 0 for v in formatted_tf_data.values()):
                                formatted_ohlcv[timeframe] = formatted_tf_data
                                self.logger.debug(f"Successfully formatted {timeframe} data for {symbol}")
                            else:
                                self.logger.debug(f"Skipping {timeframe} - no valid data for {symbol}")
                        except Exception as e:
                            self.logger.debug(f"Error formatting {timeframe} for {symbol}: {str(e)}")
                            continue
            
            result = {
                'symbol': symbol,
                'price': float(price) if price else 0.0,
                'volume': float(volume) if volume else 0.0,
                'ohlcv': formatted_ohlcv
            }
            
            self.logger.debug(f"Formatted asset data for {symbol}: price={result['price']}, volume={result['volume']}, ohlcv_timeframes={list(result['ohlcv'].keys())}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error formatting asset data for {symbol}: {str(e)}")
            self.logger.debug(f"Market data structure: {market_data}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return {
                'symbol': symbol,
                'price': 0.0,
                'volume': 0.0,
                'ohlcv': {}
            }
    
    def _format_ohlcv_for_timeframe(self, ohlcv_data) -> Dict[str, float]:
        """Format OHLCV data for a specific timeframe."""
        try:
            self.logger.debug(f"Formatting OHLCV data of type: {type(ohlcv_data)}")
            
            if isinstance(ohlcv_data, list) and len(ohlcv_data) >= 5:
                # Handle [O,H,L,C,V] format
                self.logger.debug(f"Processing list format with {len(ohlcv_data)} elements")
                return {
                    'open': float(ohlcv_data[0]),
                    'high': float(ohlcv_data[1]),
                    'low': float(ohlcv_data[2]),
                    'close': float(ohlcv_data[3]),
                    'volume': float(ohlcv_data[4])
                }
            elif hasattr(ohlcv_data, 'iloc') and len(ohlcv_data) > 0:
                # Handle pandas DataFrame
                self.logger.debug(f"Processing DataFrame with {len(ohlcv_data)} rows")
                latest = ohlcv_data.iloc[-1]
                
                # Try different column name variations
                result = {}
                for key, possible_cols in [
                    ('open', ['open', 'Open', 'o', 'O']),
                    ('high', ['high', 'High', 'h', 'H']),
                    ('low', ['low', 'Low', 'l', 'L']),
                    ('close', ['close', 'Close', 'c', 'C']),
                    ('volume', ['volume', 'Volume', 'v', 'V', 'vol'])
                ]:
                    value = 0
                    for col in possible_cols:
                        if col in latest.index:
                            try:
                                value = float(latest[col])
                                break
                            except (ValueError, TypeError):
                                continue
                    result[key] = value
                
                self.logger.debug(f"Extracted from DataFrame: {result}")
                return result
                
            elif isinstance(ohlcv_data, dict):
                # Handle dictionary format
                self.logger.debug(f"Processing dict format with keys: {list(ohlcv_data.keys())}")
                
                # Try different key name variations
                result = {}
                for key, possible_keys in [
                    ('open', ['open', 'Open', 'o', 'O']),
                    ('high', ['high', 'High', 'h', 'H']),
                    ('low', ['low', 'Low', 'l', 'L']),
                    ('close', ['close', 'Close', 'c', 'C']),
                    ('volume', ['volume', 'Volume', 'v', 'V', 'vol'])
                ]:
                    value = 0
                    for k in possible_keys:
                        if k in ohlcv_data:
                            try:
                                value = float(ohlcv_data[k])
                                break
                            except (ValueError, TypeError):
                                continue
                    result[key] = value
                
                self.logger.debug(f"Extracted from dict: {result}")
                return result
            else:
                self.logger.debug(f"Unsupported OHLCV data format: {type(ohlcv_data)}")
                return {'open': 0, 'high': 0, 'low': 0, 'close': 0, 'volume': 0}
                
        except Exception as e:
            self.logger.error(f"Error formatting OHLCV data: {str(e)}")
            self.logger.debug(f"OHLCV data: {ohlcv_data}")
            import traceback
import talib
            self.logger.debug(traceback.format_exc())
            return {'open': 0, 'high': 0, 'low': 0, 'close': 0, 'volume': 0}
    
    async def _send_alpha_alert(self, symbol: str, opportunity: AlphaOpportunity, market_data: Dict[str, Any]):
        """Send alpha opportunity alert through existing alert system."""
        try:
            # Generate alert ID for tracking
            alert_id = str(uuid.uuid4())[:8]
            
            # Use the new alpha alert method in AlertManager
            await self.alert_manager.send_alpha_opportunity_alert(
                symbol=symbol,
                alpha_estimate=opportunity.alpha_potential,
                confidence_score=opportunity.confidence,
                divergence_type=opportunity.divergence_type,
                risk_level=opportunity.risk_level,
                trading_insight=opportunity.trading_insight,
                market_data=market_data,
                transaction_id=alert_id
            )
            
            self.alpha_opportunities_sent += 1
            self.logger.info(f"[ALERT:{alert_id}] Sent alpha opportunity alert for {symbol}: "
                           f"{opportunity.alpha_potential:.2%} alpha, {opportunity.confidence:.1%} confidence")
            
        except Exception as e:
            self.logger.error(f"Error sending alpha alert for {symbol}: {str(e)}")
    
    def get_alpha_stats(self) -> Dict[str, Any]:
        """Get alpha detection statistics."""
        try:
            # Get current monitored symbols synchronously for stats
            monitored_symbols = list(self._dynamic_symbols_cache) if self._dynamic_symbols_cache else list(self.fallback_symbols)
            
            return {
                'enabled': self.enabled,
                'alert_threshold': self.alpha_alert_threshold,
                'check_interval': self.check_interval,
                'opportunities_sent': self.alpha_opportunities_sent,
                'monitored_symbols': monitored_symbols,
                'symbols_source': 'dynamic' if self._dynamic_symbols_cache else 'fallback',
                'symbols_count': len(monitored_symbols),
                'last_symbols_update': self._last_symbols_update,
                'last_checks': dict(self.last_alpha_check),
                'detector_stats': getattr(self.alpha_detector, 'detection_stats', {})
            }
        except Exception as e:
            self.logger.error(f"Error getting alpha stats: {str(e)}")
            return {
                'enabled': self.enabled,
                'error': str(e),
                'opportunities_sent': self.alpha_opportunities_sent
            }
    
    async def cleanup(self):
        """Clean up integration and restore original methods."""
        if self._original_process_symbol:
            self.monitor._process_symbol = self._original_process_symbol
            self.logger.info("Alpha integration cleaned up and original methods restored")

    async def _check_volume_confirmation(self, symbol: str, market_data: Dict[str, Any]) -> bool:
        """Check if current volume meets confirmation requirements."""
        if not self.volume_confirmation_required:
            return True
            
        try:
            # Get primary timeframe OHLCV data
            ohlcv_data = market_data.get('ohlcv', {})
            if not ohlcv_data:
                self.logger.debug(f"No OHLCV data for volume confirmation: {symbol}")
                return False
                
            # Use the first available timeframe
            primary_tf = list(ohlcv_data.keys())[0]
            df = ohlcv_data[primary_tf]
            
            if len(df) < 20:  # Need sufficient data for average
                self.logger.debug(f"Insufficient data for volume confirmation: {symbol}")
                return False
                
            # Calculate current vs average volume
            current_volume = df['volume'].iloc[-1]
            avg_volume = pd.Series(talib.SMA(df['volume'].values.astype(float), timeperiod=20), index=df['volume'].index).iloc[-1]
            
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            if volume_ratio >= self.min_volume_multiplier:
                self.logger.debug(f"Volume confirmation passed for {symbol}: {volume_ratio:.1f}x average")
                return True
            else:
                self.logger.debug(f"Volume confirmation failed for {symbol}: {volume_ratio:.1f}x average (need {self.min_volume_multiplier}x)")
                return False
                
        except Exception as e:
            self.logger.debug(f"Error checking volume confirmation for {symbol}: {str(e)}")
            return False

    async def _check_market_regime(self, symbol: str, market_data: Dict[str, Any]) -> bool:
        """Check if current market regime allows for alpha alerts."""
        if not self.market_regime_filtering:
            return True
            
        try:
            # Try to get market regime from market reporter if available
            if hasattr(self.monitor, 'market_reporter'):
                # This would require market reporter integration
                # For now, implement basic volatility-based regime detection
                pass
                
            # Basic regime detection based on price volatility
            ohlcv_data = market_data.get('ohlcv', {})
            if not ohlcv_data:
                return True  # Allow if no data available
                
            primary_tf = list(ohlcv_data.keys())[0]
            df = ohlcv_data[primary_tf]
            
            if len(df) < 20:
                return True  # Allow if insufficient data
                
            # Calculate recent volatility
            returns = df['close'].pct_change().dropna()
            recent_volatility = returns.tail(10).std() * np.sqrt(24 * 60)  # Annualized
            
            # Simple regime classification
            if recent_volatility > 0.15:  # High volatility
                regime = "VOLATILE"
            elif abs(returns.tail(10).mean()) > 0.02:  # Strong trend
                regime = "TRENDING_UP" if returns.tail(10).mean() > 0 else "TRENDING_DOWN"
            else:
                regime = "RANGING"
                
            is_allowed = regime in self.allowed_regimes
            
            if not is_allowed:
                self.logger.debug(f"Market regime filtering blocked alert for {symbol}: {regime} not in {self.allowed_regimes}")
                
            return is_allowed
            
        except Exception as e:
            self.logger.debug(f"Error checking market regime for {symbol}: {str(e)}")
            return True  # Allow if error occurs

    async def _check_alert_throttling(self, symbol: str, confidence: float) -> bool:
        """Enhanced alert throttling with daily limits and priority filtering."""
        current_time = datetime.now()
        
        # Check per-symbol interval throttling
        last_alert_time = self.last_alpha_check.get(symbol, 0)
        time_since_last = current_time.timestamp() - last_alert_time
        
        # Use longer cooldown for high-confidence alerts
        required_interval = self.high_confidence_cooldown if confidence >= 0.9 else self.min_interval_per_symbol
        
        if time_since_last < required_interval:
            self.logger.debug(f"Alert throttled for {symbol}: {time_since_last:.0f}s < {required_interval}s required")
            return False
            
        # Check daily limits per symbol
        today = current_time.date()
        daily_key = f"{symbol}_{today}"
        daily_count = self.daily_alert_counts.get(daily_key, 0)
        
        if daily_count >= self.max_alerts_per_symbol_per_day:
            self.logger.debug(f"Daily limit reached for {symbol}: {daily_count}/{self.max_alerts_per_symbol_per_day}")
            return False
            
        # Check hourly global limits
        current_hour = current_time.replace(minute=0, second=0, microsecond=0)
        recent_alerts = [t for t in self.hourly_alert_counts if t >= current_hour]
        
        if len(recent_alerts) >= self.max_alerts_per_hour:
            self.logger.debug(f"Hourly global limit reached: {len(recent_alerts)}/{self.max_alerts_per_hour}")
            return False
            
        return True

    async def _update_alert_tracking(self, symbol: str, confidence: float):
        """Update alert tracking counters."""
        current_time = datetime.now()
        
        # Update last alert time
        self.last_alpha_check[symbol] = current_time.timestamp()
        
        # Update daily count
        today = current_time.date()
        daily_key = f"{symbol}_{today}"
        self.daily_alert_counts[daily_key] = self.daily_alert_counts.get(daily_key, 0) + 1
        
        # Update hourly count
        self.hourly_alert_counts.append(current_time)
        
        # Clean old hourly counts (keep last 24 hours)
        cutoff_time = current_time - timedelta(hours=24)
        self.hourly_alert_counts = [t for t in self.hourly_alert_counts if t >= cutoff_time]
        
        # Clean old daily counts (keep last 7 days)
        cutoff_date = today - timedelta(days=7)
        self.daily_alert_counts = {k: v for k, v in self.daily_alert_counts.items() 
                                 if datetime.strptime(k.split('_')[1], '%Y-%m-%d').date() >= cutoff_date}

    async def process_alpha_opportunity(self, symbol: str, market_data: Dict[str, Any]) -> bool:
        """
        Enhanced alpha opportunity processing with volume and market regime filtering.
        
        Args:
            symbol: Trading symbol to analyze
            market_data: Market data dictionary
            
        Returns:
            bool: True if alert was sent, False otherwise
        """
        if not self.enabled or not self.alpha_detector:
            return False
            
        try:
            # Detect alpha opportunities
            opportunities = await asyncio.to_thread(
                self.alpha_detector.detect_alpha_opportunities,
                symbol,
                market_data
            )
            
            if not opportunities:
                return False
                
            # Filter opportunities by enhanced criteria
            for opportunity in opportunities:
                # Check confidence threshold
                if opportunity.confidence < self.alpha_alert_threshold:
                    self.alpha_opportunities_filtered += 1
                    self.logger.debug(f"Opportunity filtered for {symbol}: confidence {opportunity.confidence:.1%} < {self.alpha_alert_threshold:.1%}")
                    continue
                    
                # Check alpha threshold
                if abs(opportunity.alpha_potential) < self.min_alpha_threshold:
                    self.alpha_opportunities_filtered += 1
                    self.logger.debug(f"Opportunity filtered for {symbol}: alpha {opportunity.alpha_potential:.1%} < {self.min_alpha_threshold:.1%}")
                    continue
                    
                # Check volume confirmation
                if not await self._check_volume_confirmation(symbol, market_data):
                    self.alpha_opportunities_filtered += 1
                    continue
                    
                # Check market regime
                if not await self._check_market_regime(symbol, market_data):
                    self.alpha_opportunities_filtered += 1
                    continue
                    
                # Check alert throttling
                if not await self._check_alert_throttling(symbol, opportunity.confidence):
                    self.alpha_opportunities_filtered += 1
                    continue
                    
                # All filters passed - send alert
                await self._send_enhanced_alpha_alert(symbol, opportunity, market_data)
                await self._update_alert_tracking(symbol, opportunity.confidence)
                self.alpha_opportunities_sent += 1
                
                self.logger.info(f"✅ High-quality alpha alert sent for {symbol}: "
                               f"{opportunity.alpha_potential:.1%} alpha, {opportunity.confidence:.1%} confidence")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error processing alpha opportunity for {symbol}: {str(e)}")
            return False

    async def _send_enhanced_alpha_alert(self, symbol: str, opportunity: AlphaOpportunity, market_data: Dict[str, Any]):
        """Send enhanced alpha alert with additional context."""
        try:
            # Get current price for context
            ticker = market_data.get('ticker', {})
            current_price = ticker.get('last', 0)
            
            # Get volume context
            volume_context = await self._get_volume_context(symbol, market_data)
            
            # Enhanced alert data
            alert_data = {
                'symbol': symbol,
                'alpha_estimate': opportunity.alpha_potential,
                'confidence_score': opportunity.confidence,
                'divergence_type': opportunity.divergence_type.value if hasattr(opportunity.divergence_type, 'value') else str(opportunity.divergence_type),
                'risk_level': opportunity.risk_level,
                'trading_insight': opportunity.trading_insight,
                'current_price': current_price,
                'volume_context': volume_context,
                'alert_id': str(uuid.uuid4())[:8],
                'timestamp': datetime.now(),
                'quality_score': self._calculate_quality_score(opportunity, volume_context)
            }
            
            # Send through alert manager
            await self.alert_manager.send_alpha_opportunity_alert(**alert_data)
            
        except Exception as e:
            self.logger.error(f"Error sending enhanced alpha alert for {symbol}: {str(e)}")

    async def _get_volume_context(self, symbol: str, market_data: Dict[str, Any]) -> str:
        """Get volume context for alert."""
        try:
            ohlcv_data = market_data.get('ohlcv', {})
            if not ohlcv_data:
                return "Volume data unavailable"
                
            primary_tf = list(ohlcv_data.keys())[0]
            df = ohlcv_data[primary_tf]
            
            current_volume = df['volume'].iloc[-1]
            avg_volume = pd.Series(talib.SMA(df['volume'].values.astype(float), timeperiod=20), index=df['volume'].index).iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            return f"{volume_ratio:.1f}x average volume"
            
        except Exception:
            return "Volume analysis unavailable"

    def _calculate_quality_score(self, opportunity: AlphaOpportunity, volume_context: str) -> float:
        """Calculate overall quality score for the opportunity."""
        try:
            # Base score from confidence
            quality_score = opportunity.confidence * 100
            
            # Boost for high alpha potential
            if abs(opportunity.alpha_potential) > 0.06:  # 6%+
                quality_score += 10
            elif abs(opportunity.alpha_potential) > 0.08:  # 8%+
                quality_score += 20
                
            # Boost for volume confirmation
            if "x average volume" in volume_context:
                try:
                    volume_multiplier = float(volume_context.split('x')[0])
                    if volume_multiplier >= 3.0:
                        quality_score += 15
                    elif volume_multiplier >= 2.0:
                        quality_score += 10
                except:
                    pass
                    
            return min(100.0, quality_score)
            
        except Exception:
            return opportunity.confidence * 100

    def get_enhanced_stats(self) -> Dict[str, Any]:
        """Get enhanced scanner statistics."""
        return {
            'enabled': self.enabled,
            'check_interval': self.check_interval,
            'alpha_opportunities_sent': self.alpha_opportunities_sent,
            'alpha_opportunities_filtered': self.alpha_opportunities_filtered,
            'filter_efficiency': (self.alpha_opportunities_filtered / 
                                (self.alpha_opportunities_sent + self.alpha_opportunities_filtered) * 100) 
                               if (self.alpha_opportunities_sent + self.alpha_opportunities_filtered) > 0 else 0,
            'thresholds': {
                'confidence': self.alpha_alert_threshold,
                'alpha': self.min_alpha_threshold,
                'volume_multiplier': self.min_volume_multiplier,
                'beta_expansion': self.beta_expansion_threshold
            },
            'throttling': {
                'min_interval_per_symbol': self.min_interval_per_symbol,
                'max_alerts_per_hour': self.max_alerts_per_hour,
                'max_alerts_per_symbol_per_day': self.max_alerts_per_symbol_per_day
            },
            'daily_alert_counts': dict(list(self.daily_alert_counts.items())[-10:]),  # Last 10 days
            'hourly_alert_count': len(self.hourly_alert_counts)
        }


async def setup_alpha_integration(monitor, alert_manager, config: Dict[str, Any] = None) -> AlphaMonitorIntegration:
    """Setup alpha generation integration with existing systems.
    
    Args:
        monitor: MarketMonitor instance
        alert_manager: AlertManager instance  
        config: Configuration dictionary
        
    Returns:
        AlphaMonitorIntegration instance
    """
    try:
        integration = AlphaMonitorIntegration(monitor, alert_manager, config)
        await integration.integrate_with_monitor()
        return integration
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to setup alpha integration: {str(e)}")
        raise 