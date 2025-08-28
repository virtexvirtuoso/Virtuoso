"""
Signal Processor Module

Handles analysis result processing, signal generation, and market monitoring
for the Virtuoso CCXT trading system.

This module is responsible for:
- Processing confluence analysis results
- Generating trading signals based on thresholds
- Calculating trade parameters and risk management
- Monitoring market indicators for significant changes
- Managing signal lifecycle and tracking
"""

import asyncio
import logging
import traceback
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Union
from decimal import Decimal

from src.core.formatting import LogFormatter
from src.core.interpretation.interpretation_manager import InterpretationManager


class SignalProcessor:
    """
    Handles signal processing and analysis result interpretation.
    
    This class processes confluence analysis results, generates trading signals,
    and manages the complete signal lifecycle including tracking and validation.
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        signal_generator,
        metrics_manager,
        interpretation_manager: InterpretationManager,
        market_data_manager,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the Signal Processor.
        
        Args:
            config: Configuration dictionary with confluence thresholds
            signal_generator: Signal generator instance
            metrics_manager: Metrics manager for tracking
            interpretation_manager: Manager for processing interpretations
            market_data_manager: Market data manager for price retrieval
            logger: Logger instance
        """
        self.config = config
        self.signal_generator = signal_generator
        self.metrics_manager = metrics_manager
        self.interpretation_manager = interpretation_manager
        self.market_data_manager = market_data_manager
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize monitoring thresholds
        self.monitoring_thresholds = self.config.get('monitoring', {}).get('thresholds', {
            'volume_change': 0.2,
            'orderflow_change': 0.15,
            'orderbook_change': 0.1,
            'position_change': 0.25,
            'sentiment_change': 0.2
        })
        
        self.logger.info("Signal Processor initialized")

    async def initialize(self) -> bool:
        """Initialize the signal processor.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            # Signal processor is already initialized in __init__
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize SignalProcessor: {str(e)}")
            return False

    async def process_analysis_result(self, symbol: str, result: Dict[str, Any]) -> None:
        """Process analysis result and generate signals if appropriate."""
        try:
            # Generate a transaction ID for tracking this analysis throughout the system
            transaction_id = str(uuid.uuid4())
            signal_id = str(uuid.uuid4())[:8]
            result['transaction_id'] = transaction_id
            result['signal_id'] = signal_id
            
            # Extract key information
            confluence_score = result.get('confluence_score', 0)
            reliability = result.get('reliability', 0)
            components = result.get('components', {})
            
            # Get thresholds from config
            confluence_config = self.config.get('confluence', {})
            threshold_config = confluence_config.get('thresholds', {})
            buy_threshold = float(threshold_config.get('buy', 60.0))
            sell_threshold = float(threshold_config.get('sell', 40.0))
            neutral_buffer = float(threshold_config.get('neutral_buffer', 5))
            
            # Log component scores
            self.logger.debug("\n=== Component Scores ===")
            for component, score in components.items():
                self.logger.debug(f"{component}: {score}")
            
            # Get formatter results directly from the ConfluenceAnalyzer output
            formatter_results = result.get('results', {})
            
            # Process interpretations using centralized InterpretationManager
            if 'market_interpretations' in result:
                try:
                    raw_interpretations = result['market_interpretations']
                    self.logger.debug(f"Processing {len(raw_interpretations) if isinstance(raw_interpretations, list) else 1} interpretations for {symbol}")
                    
                    # Use InterpretationManager to process and standardize interpretations
                    interpretation_set = self.interpretation_manager.process_interpretations(
                        raw_interpretations, 
                        f"analysis_{symbol}",
                        market_data=None,  # No market data available at this point
                        timestamp=datetime.now()
                    )
                    
                    # Format interpretations for legacy compatibility (alerts, PDF, etc.)
                    formatted_for_alerts = self.interpretation_manager.get_formatted_interpretation(
                        interpretation_set, 'alert'
                    )
                    
                    # Convert to legacy format for backward compatibility
                    legacy_interpretations = []
                    for interpretation in interpretation_set.interpretations:
                        legacy_interpretations.append({
                            'component': interpretation.component_name,
                            'display_name': interpretation.component_name.replace('_', ' ').title(),
                            'interpretation': interpretation.interpretation_text,
                            'severity': interpretation.severity.value,
                            'confidence': interpretation.confidence_score
                        })
                    
                    # Update result with processed interpretations
                    result['market_interpretations'] = legacy_interpretations
                    result['interpretation_set'] = interpretation_set  # Store standardized version
                    
                    self.logger.debug(f"Successfully processed interpretations for {symbol}: {len(legacy_interpretations)} components")
                    
                except Exception as e:
                    self.logger.error(f"Error processing interpretations for {symbol}: {e}")
                    # Keep original interpretations as fallback
                    self.logger.debug(f"Keeping original interpretations as fallback")
            
            # Only generate enhanced data if it's missing
            if not result.get('market_interpretations') and hasattr(self.signal_generator, '_generate_enhanced_formatted_data'):
                try:
                    self.logger.debug(f"Generating enhanced formatted data for {symbol} (interpretations missing)")
                    enhanced_data = self.signal_generator._generate_enhanced_formatted_data(
                        symbol,
                        confluence_score,
                        components,
                        formatter_results,
                        reliability,
                        buy_threshold,
                        sell_threshold
                    )
                    # Add enhanced data to the result
                    if enhanced_data:
                        result.update(enhanced_data)
                        self.logger.debug(f"Successfully added enhanced data: market_interpretations={len(enhanced_data.get('market_interpretations', []))}, actionable_insights={len(enhanced_data.get('actionable_insights', []))}")
                except Exception as e:
                    self.logger.error(f"Error generating enhanced data: {str(e)}")
                    self.logger.debug(traceback.format_exc())
            
            # Display comprehensive confluence score table with all the data
            display_results = result.get('results', formatter_results)
            
            # If enhanced data was added to result, merge it with display_results
            if result.get('market_interpretations'):
                if isinstance(display_results, dict):
                    display_results = display_results.copy()
                    display_results['market_interpretations'] = result['market_interpretations']
                else:
                    # If display_results is not a dict, create one with enhanced data
                    display_results = {
                        'market_interpretations': result['market_interpretations']
                    }
                    # Add formatter_results if it's a dict
                    if isinstance(formatter_results, dict):
                        display_results.update(formatter_results)
            
            formatted_table = LogFormatter.format_enhanced_confluence_score_table(
                symbol=symbol,
                confluence_score=confluence_score,
                components=components,
                results=display_results,
                weights=result.get('metadata', {}).get('weights', {}),
                reliability=reliability
            )
            self.logger.info(formatted_table)
            
            # Generate signal if score meets thresholds
            self.logger.debug(f"=== Generating Signal ===")
            # Store threshold information in result for downstream processing
            result['buy_threshold'] = buy_threshold
            result['sell_threshold'] = sell_threshold
            
            # Determine signal type based on thresholds
            signal_type = "NEUTRAL"
            if confluence_score >= buy_threshold:
                signal_type = "BUY"
            elif confluence_score <= sell_threshold:
                signal_type = "SELL"
                
            result['signal_type'] = signal_type
            
            # Only pass to signal generator if it's a BUY or SELL signal
            if signal_type in ["BUY", "SELL"]:
                await self.generate_signal(symbol, result)
                self.logger.info(f"Generated {signal_type} signal for {symbol} with score {confluence_score:.2f} (threshold: {buy_threshold if signal_type == 'BUY' else sell_threshold})")
            else:
                self.logger.info(f"Generated NEUTRAL signal for {symbol} with score {confluence_score:.2f} in neutral zone (buy: {buy_threshold}, sell: {sell_threshold})")

            # Update metrics
            if self.metrics_manager:
                await self.metrics_manager.update_analysis_metrics(symbol, result)

        except Exception as e:
            self.logger.error(f"Error processing analysis result: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def generate_signal(self, symbol: str, analysis_result: Dict[str, Any]) -> None:
        """Generate trading signal based on analysis results with enhanced validation and tracking."""
        if not self.signal_generator:
            self.logger.error(f"Signal generator not available for {symbol}")
            return

        try:
            # Generate transaction and signal IDs for tracking, or reuse existing ones
            transaction_id = analysis_result.get('transaction_id', str(uuid.uuid4()))
            signal_id = analysis_result.get('signal_id', str(uuid.uuid4())[:8])
            
            # Log the start of signal generation with transaction ID
            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Generating signal for {symbol}")
            
            # Extract critical information
            if not analysis_result or not isinstance(analysis_result, dict):
                self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Invalid analysis result for {symbol}")
                return
                
            # Extract data from analysis result
            confluence_score = analysis_result.get('confluence_score', 0)
            components = analysis_result.get('components', {})
            results = analysis_result.get('results', {})
            
            # Get reliability score
            reliability = analysis_result.get('reliability', 0.5)
            
            # Check if reliability is less than 100% (1.0), if so, log and return without generating an alert
            if reliability < 1.0:
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Skipping alert for {symbol} due to reliability {reliability*100:.1f}% < 100%")
                return
            
            # Get price information
            price = await self._get_current_price(symbol, analysis_result, transaction_id, signal_id)
            
            # Get thresholds from config
            config = self.config.get('confluence', {}).get('thresholds', {})
            buy_threshold = float(config.get('buy', 60.0))
            sell_threshold = float(config.get('sell', 40.0))
            
            # Create enhanced signal data
            signal_data = {
                'symbol': symbol,
                'confluence_score': confluence_score,
                'components': components,
                'results': results,
                'weights': analysis_result.get('metadata', {}).get('weights', {}),
                'reliability': reliability,
                'price': price,
                'transaction_id': transaction_id,
                'signal_id': signal_id,
                'buy_threshold': buy_threshold,
                'sell_threshold': sell_threshold
            }
            
            # Add enhanced analysis data if available
            if 'market_interpretations' in analysis_result:
                signal_data['market_interpretations'] = analysis_result['market_interpretations']
            
            if 'actionable_insights' in analysis_result:
                signal_data['actionable_insights'] = analysis_result['actionable_insights']
                
            if 'influential_components' in analysis_result:
                signal_data['influential_components'] = analysis_result['influential_components']
            
            # Determine signal type based on thresholds
            signal_type = "NEUTRAL"
            if confluence_score >= buy_threshold:
                signal_type = "BUY"
            elif confluence_score <= sell_threshold:
                signal_type = "SELL"
            
            signal_data['signal_type'] = signal_type
            
            # Log signal data with proper formatting
            self._log_signal_data(transaction_id, signal_id, symbol, confluence_score, reliability, price, signal_type)
            
            # Set trade parameters based on config
            try:
                signal_data['trade_params'] = self.calculate_trade_parameters(
                    symbol=symbol,
                    price=price,
                    signal_type=signal_type,
                    score=confluence_score,
                    reliability=reliability
                )
            except Exception as e:
                self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error calculating trade parameters: {str(e)}")
                self.logger.debug(traceback.format_exc())
                # Set default trade parameters on error
                signal_data['trade_params'] = self._get_default_trade_params(price, confluence_score)
                
            # Store signal for analysis and generate alert
            try:
                self.signal_generator.process_signal(signal_data)
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Signal successfully processed for {symbol}")
            except Exception as e:
                self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error processing signal: {str(e)}")
                self.logger.debug(traceback.format_exc())
                
        except Exception as e:
            self.logger.error(f"Error generating signal: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _get_current_price(self, symbol: str, analysis_result: Dict[str, Any], transaction_id: str, signal_id: str) -> Optional[float]:
        """Get current price from various sources."""
        price = None
        
        # Try to get price from analysis result
        if 'price' in analysis_result:
            price = analysis_result['price']
        elif 'market_data' in analysis_result and 'ticker' in analysis_result['market_data']:
            ticker = analysis_result['market_data']['ticker']
            price = ticker.get('last', ticker.get('close', None))
        
        # Fallback to market data manager
        if price is None and self.market_data_manager:
            try:
                market_data = await self.market_data_manager.get_market_data(symbol)
                if market_data and 'ticker' in market_data:
                    price = float(market_data['ticker'].get('last', market_data['ticker'].get('close', 0)))
            except Exception as e:
                self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}] Error getting price from market data: {str(e)}")
        
        return price

    def _log_signal_data(self, transaction_id: str, signal_id: str, symbol: str, confluence_score: float, reliability: float, price: Optional[float], signal_type: str) -> None:
        """Log signal data with proper error handling and formatting."""
        try:
            # Enhanced debugging for value types and formatting issues
            self.logger.debug(f"[FORMAT_DEBUG] Value types - confluence_score: {type(confluence_score).__name__}, " 
                             f"reliability: {type(reliability).__name__}, price: {type(price).__name__}")
            
            # Check for numpy types which might need special handling
            if hasattr(confluence_score, 'dtype'):
                self.logger.debug(f"[FORMAT_DEBUG] confluence_score is numpy type: {confluence_score.dtype}")
                confluence_score = float(confluence_score)
            if hasattr(reliability, 'dtype'):
                self.logger.debug(f"[FORMAT_DEBUG] reliability is numpy type: {reliability.dtype}")
                reliability = float(reliability)
            if hasattr(price, 'dtype'):
                self.logger.debug(f"[FORMAT_DEBUG] price is numpy type: {price.dtype}")
                price = float(price)
            
            # Format values with proper handling of None values
            score_str = "N/A" if confluence_score is None else f"{confluence_score:.2f}"
            reliability_str = "N/A" if reliability is None else f"{reliability:.2f}"
            price_str = "N/A" if price is None else f"${price:.2f}"
            
            signal_log = (
                f"[TXN:{transaction_id}][SIG:{signal_id}] {symbol} - "
                f"Score: {score_str} ({signal_type}) - "
                f"Reliability: {reliability_str} - "
                f"Price: {price_str}"
            )
            self.logger.info(signal_log)
        except Exception as format_error:
            # Fallback to simple formatting if any errors occur
            self.logger.error(f"Error formatting signal log: {format_error}")
            self.logger.debug(traceback.format_exc())
            # Safe fallback that doesn't use f-string formatting for values
            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] {symbol} - Generated {signal_type} signal")

    def calculate_trade_parameters(self, symbol: str, price: float, signal_type: str, score: float, reliability: float) -> Dict[str, Any]:
        """
        Calculate trade parameters based on signal data and configuration.
        
        Args:
            symbol: Trading symbol
            price: Current price
            signal_type: Signal type (BUY, SELL, NEUTRAL)
            score: Confluence score (0-100)
            reliability: Signal reliability (0-1)
            
        Returns:
            Dictionary containing trade parameters
        """
        try:
            # Get trading config
            trading_config = self.config.get('trading', {})
            
            # Risk management parameters
            default_risk_percent = trading_config.get('risk_percentage', 2.0)  # 2% default risk
            default_leverage = trading_config.get('leverage', 1)
            
            # Calculate position size based on risk percentage
            account_balance = trading_config.get('balance', 10000)  # Default $10k balance
            risk_amount = account_balance * (default_risk_percent / 100)
            
            # Adjust risk based on confluence score and reliability
            confidence_multiplier = min(score / 100, 1.0) * reliability
            adjusted_risk_percent = default_risk_percent * confidence_multiplier
            
            # Calculate stop loss and take profit based on signal type
            if signal_type == "BUY":
                stop_loss_percent = trading_config.get('stop_loss_percent', 2.0)
                take_profit_percent = trading_config.get('take_profit_percent', 6.0)  # 3:1 R/R
                
                stop_loss_price = price * (1 - stop_loss_percent / 100)
                take_profit_price = price * (1 + take_profit_percent / 100)
                
            elif signal_type == "SELL":
                stop_loss_percent = trading_config.get('stop_loss_percent', 2.0)
                take_profit_percent = trading_config.get('take_profit_percent', 6.0)
                
                stop_loss_price = price * (1 + stop_loss_percent / 100)
                take_profit_price = price * (1 - take_profit_percent / 100)
                
            else:  # NEUTRAL
                stop_loss_price = None
                take_profit_price = None
                
            # Calculate position size
            if stop_loss_price and price:
                stop_distance = abs(price - stop_loss_price)
                position_size = risk_amount / stop_distance if stop_distance > 0 else 0
            else:
                position_size = risk_amount / price if price > 0 else 0
                
            # Apply leverage if configured
            position_size *= default_leverage
            
            # Calculate risk/reward ratio
            risk_reward_ratio = None
            if stop_loss_price and take_profit_price and price:
                risk = abs(price - stop_loss_price)
                reward = abs(take_profit_price - price)
                risk_reward_ratio = reward / risk if risk > 0 else None
            
            return {
                'entry_price': price,
                'stop_loss': stop_loss_price,
                'take_profit': take_profit_price,
                'position_size': position_size,
                'risk_reward_ratio': risk_reward_ratio,
                'risk_percentage': adjusted_risk_percent,
                'confidence': confidence_multiplier,
                'leverage': default_leverage,
                'signal_strength': score
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating trade parameters: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return self._get_default_trade_params(price, score)

    def _get_default_trade_params(self, price: Optional[float], score: float) -> Dict[str, Any]:
        """Get default trade parameters when calculation fails."""
        return {
            'entry_price': price,
            'stop_loss': None,
            'take_profit': None,
            'position_size': None,
            'risk_reward_ratio': None,
            'risk_percentage': None,
            'confidence': min(score / 100, 1.0) if score is not None else 0.5,
            'leverage': 1,
            'signal_strength': score or 0
        }

    # Monitoring methods for market indicators
    async def monitor_volume(self, symbol: str, current: Dict[str, Any], previous: Optional[float], market_data: Dict[str, Any]) -> None:
        """Monitor volume indicators for significant changes."""
        try:
            if previous is None:
                return
                
            change = abs(current['score'] - previous)
            if change > self.monitoring_thresholds['volume_change']:
                await self._handle_volume_alert(symbol, current, previous)
                
        except Exception as e:
            self.logger.error(f"Error monitoring volume for {symbol}: {str(e)}")

    async def monitor_orderflow(self, symbol: str, current: Dict[str, Any], previous: Optional[float], market_data: Dict[str, Any]) -> None:
        """Monitor orderflow indicators for significant changes."""
        try:
            if previous is None:
                return
                
            change = abs(current['score'] - previous)
            if change > self.monitoring_thresholds['orderflow_change']:
                await self._handle_orderflow_alert(symbol, current, previous)
                
        except Exception as e:
            self.logger.error(f"Error monitoring orderflow for {symbol}: {str(e)}")

    async def monitor_orderbook(self, symbol: str, current: Dict[str, Any], previous: Optional[float], market_data: Dict[str, Any]) -> None:
        """Monitor orderbook indicators for significant changes."""
        try:
            if previous is None:
                return
                
            change = abs(current['score'] - previous)
            if change > self.monitoring_thresholds['orderbook_change']:
                await self._handle_orderbook_alert(symbol, current, previous)
                
        except Exception as e:
            self.logger.error(f"Error monitoring orderbook for {symbol}: {str(e)}")

    async def monitor_sentiment(self, symbol: str, current: Dict[str, Any], previous: Optional[float], market_data: Dict[str, Any]) -> None:
        """Monitor sentiment indicators for significant changes."""
        try:
            if previous is None:
                return
                
            change = abs(current['score'] - previous)
            if change > self.monitoring_thresholds['sentiment_change']:
                await self._handle_sentiment_alert(symbol, current, previous)
                
        except Exception as e:
            self.logger.error(f"Error monitoring sentiment for {symbol}: {str(e)}")

    # Alert handlers
    async def _handle_volume_alert(self, symbol: str, current: Dict[str, Any], previous: float) -> None:
        """Handle significant volume changes."""
        self.logger.info(f"Volume alert for {symbol}: {previous:.2f} -> {current['score']:.2f}")

    async def _handle_orderflow_alert(self, symbol: str, current: Dict[str, Any], previous: float) -> None:
        """Handle significant orderflow changes."""
        self.logger.info(f"Orderflow alert for {symbol}: {previous:.2f} -> {current['score']:.2f}")

    async def _handle_orderbook_alert(self, symbol: str, current: Dict[str, Any], previous: float) -> None:
        """Handle significant orderbook changes."""
        self.logger.info(f"Orderbook alert for {symbol}: {previous:.2f} -> {current['score']:.2f}")

    async def _handle_sentiment_alert(self, symbol: str, current: Dict[str, Any], previous: float) -> None:
        """Handle significant sentiment changes."""
        self.logger.info(f"Sentiment alert for {symbol}: {previous:.2f} -> {current['score']:.2f}")