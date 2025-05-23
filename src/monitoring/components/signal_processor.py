"""
Signal Processing Component

This module handles all signal processing functionality including:
- Signal generation from analysis results
- Trade parameter calculation
- Market interpretation formatting
- Report coordination
- Transaction tracking
"""

import logging
import time
import uuid
import os
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

from src.monitoring.utilities.timestamp_utils import TimestampUtility


class DataUnavailableError(Exception):
    """Exception raised when required data is not available for analysis."""
    pass


class SignalProcessor:
    """
    Handles signal processing functionality including signal generation,
    trade parameter calculation, and confluence analysis coordination.
    """
    
    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        config: Optional[Dict[str, Any]] = None,
        signal_generator=None,
        alert_manager=None,
        market_data_manager=None,
        database_client=None,
        confluence_analyzer=None,
        timestamp_utility: Optional[TimestampUtility] = None
    ):
        """
        Initialize SignalProcessor.
        
        Args:
            logger: Logger instance
            config: Configuration dictionary
            signal_generator: Signal generator instance
            alert_manager: Alert manager instance
            market_data_manager: Market data manager instance
            database_client: Database client instance
            confluence_analyzer: Confluence analyzer instance
            timestamp_utility: Timestamp utility instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or {}
        self.signal_generator = signal_generator
        self.alert_manager = alert_manager
        self.market_data_manager = market_data_manager
        self.database_client = database_client
        self.confluence_analyzer = confluence_analyzer
        self.timestamp_utility = timestamp_utility or TimestampUtility()
        
    async def process_analysis_result(self, symbol: str, result: Dict[str, Any]) -> None:
        """Process analysis result and generate signals if appropriate."""
        try:
            # Generate a transaction ID for tracking this analysis throughout the system
            transaction_id = str(uuid.uuid4())
            
            self.logger.info(f"[TXN:{transaction_id}] Processing analysis result for {symbol}")
            
            # Add transaction ID to result for tracking
            result['transaction_id'] = transaction_id
            
            # Generate signal if we have a valid result
            if result and isinstance(result, dict):
                await self._generate_signal(symbol, result)
                
            # Update metrics if available
            if hasattr(self, 'metrics_manager') and self.metrics_manager:
                await self.metrics_manager.update_analysis_metrics(symbol, result)

        except Exception as e:
            self.logger.error(f"Error processing analysis result: {str(e)}")
            self.logger.debug(traceback.format_exc())

    async def _generate_signal(self, symbol: str, analysis_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate trading signal based on analysis results with enhanced validation and tracking."""
        if not hasattr(self, 'signal_generator') or self.signal_generator is None:
            self.logger.error(f"Signal generator not available for {symbol}")
            return None

        try:
            # Generate transaction and signal IDs for tracking, or reuse existing ones
            transaction_id = analysis_result.get('transaction_id', str(uuid.uuid4()))
            signal_id = analysis_result.get('signal_id', str(uuid.uuid4())[:8])
            
            # Log the start of signal generation with transaction ID
            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Generating signal for {symbol}")
            
            # Extract critical information
            if not analysis_result or not isinstance(analysis_result, dict):
                self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Invalid analysis result for {symbol}")
                return None
                
            # Extract data from analysis result
            confluence_score = analysis_result.get('confluence_score', 0)
            components = analysis_result.get('components', {})
            results = analysis_result.get('results', {})
            
            # Get reliability score
            reliability = analysis_result.get('reliability', 0.5)
            
            # Get price information
            price = None
            if 'price' in analysis_result:
                price = analysis_result['price']
            elif 'market_data' in analysis_result and 'ticker' in analysis_result['market_data']:
                ticker = analysis_result['market_data']['ticker']
                price = ticker.get('last', ticker.get('close', None))
            
            if price is None and self.market_data_manager:
                try:
                    market_data = await self.market_data_manager.get_market_data(symbol)
                    if market_data and 'ticker' in market_data:
                        price = float(market_data['ticker'].get('last', market_data['ticker'].get('close', 0)))
                except Exception as e:
                    self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}] Error getting price from market data: {str(e)}")
            
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
            
            # Log signal data before setting trade parameters
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
            
            # Set trade parameters based on config
            try:
                signal_data['trade_params'] = self._calculate_trade_parameters(
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
                signal_data['trade_params'] = {
                    'entry_price': price,
                    'stop_loss': None,
                    'take_profit': None,
                    'position_size': None,
                    'risk_reward_ratio': None,
                    'risk_percentage': None,
                    'confidence': min(confluence_score / 100, 1.0) if confluence_score is not None else 0.5,
                    'timeframe': 'auto'
                }
            
            # Add timestamp
            signal_data['timestamp'] = int(time.time() * 1000)
            
            # Generate enhanced formatted data if signal_generator is available
            if self.signal_generator:
                try:
                    self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Generating enhanced formatted data for {symbol}")
                    enhanced_data = self.signal_generator._generate_enhanced_formatted_data(
                        symbol,
                        confluence_score,
                        components,
                        results,
                        reliability,
                        buy_threshold,
                        sell_threshold
                    )
                    # Add enhanced data to signal_data
                    if enhanced_data:
                        # Process market interpretations to ensure they're properly structured
                        if 'market_interpretations' in enhanced_data:
                            market_interpretations = enhanced_data['market_interpretations']
                            
                            # Check if interpretations are simple strings instead of properly structured objects
                            if market_interpretations and (isinstance(market_interpretations[0], str) or 
                                                        (isinstance(market_interpretations[0], dict) and 'component' not in market_interpretations[0])):
                                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Converting market interpretations to structured format")
                                
                                # Create properly structured interpretations
                                structured_interpretations = []
                                
                                # Component name mapping
                                component_mappings = {
                                    'technical': 'Technical',
                                    'volume': 'Volume',
                                    'orderbook': 'Orderbook',
                                    'orderflow': 'Orderflow',
                                    'sentiment': 'Sentiment',
                                    'price_structure': 'Price Structure',
                                    'structure': 'Price Structure'
                                }
                                
                                for interp in market_interpretations:
                                    # If it's a string, identify which component it belongs to
                                    if isinstance(interp, str):
                                        # Try to identify component from the text
                                        identified_component = None
                                        for comp_key, comp_name in component_mappings.items():
                                            if comp_key.lower() in interp.lower() or comp_name.lower() in interp.lower():
                                                identified_component = comp_name
                                                break
                                        
                                        # Default to Unknown if no component identified
                                        if not identified_component:
                                            # Try to extract from first few words
                                            first_words = interp.split(':', 1)[0] if ':' in interp else interp.split(' ', 1)[0]
                                            identified_component = component_mappings.get(first_words.strip().lower(), 'Analysis')
                                        
                                        # Create structured object
                                        structured_interpretations.append({
                                            'component': identified_component,
                                            'display_name': identified_component,
                                            'interpretation': interp
                                        })
                                    elif isinstance(interp, dict):
                                        # It's already a dict but might be missing the required structure
                                        if 'interpretation' in interp:
                                            # Already has interpretation field
                                            if 'component' not in interp or 'display_name' not in interp:
                                                # Add missing fields
                                                component_text = interp.get('component', 'Unknown')
                                                display_name = component_mappings.get(component_text.lower(), component_text)
                                                
                                                # Update with formatted fields
                                                interp['component'] = component_text
                                                interp['display_name'] = display_name
                                            
                                            structured_interpretations.append(interp)
                                        else:
                                            # Doesn't have interpretation field - reconstruct
                                            component_text = next(iter(interp.keys())) if interp else 'Unknown'
                                            interpretation_text = interp.get(component_text, str(interp))
                                            
                                            display_name = component_mappings.get(component_text.lower(), component_text)
                                            
                                            structured_interpretations.append({
                                                'component': component_text,
                                                'display_name': display_name,
                                                'interpretation': interpretation_text
                                            })
                                
                                # Replace original interpretations with structured ones
                                enhanced_data['market_interpretations'] = structured_interpretations
                                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Converted {len(structured_interpretations)} market interpretations to structured format")
                        
                        # Now update signal_data with the enhanced data
                        signal_data.update(enhanced_data)
                        self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Successfully added enhanced data: market_interpretations={len(enhanced_data.get('market_interpretations', []))}, actionable_insights={len(enhanced_data.get('actionable_insights', []))}")
                except Exception as e:
                    self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error generating enhanced data: {str(e)}")
                    self.logger.debug(traceback.format_exc())
            
            # Generate report if enabled
            if self.signal_generator and hasattr(self.signal_generator, 'report_manager'):
                try:
                    self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] Generating report for {symbol}")
                    
                    # Get cached OHLCV data for different timeframes for improved VWAP calculations
                    ltf_ohlcv = self._get_ohlcv_for_report(symbol, 'ltf')    # For daily VWAP (lower timeframe)
                    htf_ohlcv = self._get_ohlcv_for_report(symbol, 'htf')    # For weekly VWAP (higher timeframe)
                    
                    # Use ltf timeframe as the primary OHLCV dataset
                    ohlcv_data = ltf_ohlcv
                    
                    # Add HTF data as metadata if available (for the PDF generator to use for calculating weekly VWAP)
                    if ltf_ohlcv is not None and htf_ohlcv is not None:
                        if 'metadata' not in getattr(ltf_ohlcv, 'attrs', {}):
                            ltf_ohlcv.attrs['metadata'] = {}
                        ltf_ohlcv.attrs['metadata']['htf_data'] = htf_ohlcv
                        self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] Added HTF data ({len(htf_ohlcv)} records) for weekly VWAP calculation")
                    
                    # Generate a safe filename for the PDF
                    symbol_safe = symbol.lower().replace('/', '_')
                    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    pdf_filename = f"{symbol_safe}_{timestamp_str}.pdf"
                    pdf_path = os.path.join('exports', pdf_filename)
                    
                    self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] Will save PDF to {pdf_path}")
                    
                    if ohlcv_data is not None:
                        self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] Using cached OHLCV data for report ({len(ohlcv_data)} records)")
                        
                        # Use generate_and_attach_report method directly with explicit output_path
                        # Ensure output_path is a full file path with .pdf extension
                        success, generated_path, _ = await self.signal_generator.report_manager.generate_and_attach_report(
                            signal_data=signal_data,
                            ohlcv_data=ohlcv_data,
                            signal_type=signal_type.lower(),
                            output_path=pdf_path
                        )
                        
                        if success and generated_path and os.path.exists(generated_path) and not os.path.isdir(generated_path):
                            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] PDF generated successfully: {generated_path}")
                            signal_data['pdf_path'] = generated_path
                        else:
                            self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] Failed to generate PDF at {pdf_path}")
                    else:
                        self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] No OHLCV data available for report")
                        
                        # Try generating without OHLCV data
                        success, generated_path, _ = await self.signal_generator.report_manager.generate_and_attach_report(
                            signal_data=signal_data,
                            signal_type=signal_type.lower(),
                            output_path=pdf_path
                        )
                        
                        if success and generated_path and os.path.exists(generated_path) and not os.path.isdir(generated_path):
                            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] PDF generated without OHLCV data: {generated_path}")
                            signal_data['pdf_path'] = generated_path
                        else:
                            self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] Failed to generate PDF without OHLCV data")
                        
                    # Final validation of PDF path
                    pdf_path_val = signal_data.get('pdf_path') # Renamed to avoid conflict with outer scope pdf_path
                    if pdf_path_val:
                        if os.path.exists(pdf_path_val) and not os.path.isdir(pdf_path_val) and os.path.getsize(pdf_path_val) > 0:
                            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] Final PDF validation successful: {pdf_path_val}")
                        else:
                            self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] PDF path failed validation: {pdf_path_val}")
                            signal_data.pop('pdf_path', None)
                    else:
                        self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}][REPORT] No PDF path set after report generation")
                        
                except Exception as e:
                    self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error generating report: {str(e)}")
                    self.logger.error(traceback.format_exc())
            
            # Now send the alert (after PDF path is set)
            if self.alert_manager:
                # DISABLED: await self.alert_manager.send_signal_alert(signal_data)
                pass # Explicitly pass if the line is disabled and nothing else is done.
            else:
                self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}] Alert manager not available for {symbol}")
            
            # Return generated signal
            return signal_data
            
        except Exception as e:
            self.logger.error(f"Error generating signal for {symbol}: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None

    def _calculate_trade_parameters(self, symbol: str, price: float, signal_type: str, score: float, reliability: float) -> Dict[str, Any]:
        """
        Calculate trade parameters based on signal data and configuration.
        
        Args:
            symbol: Trading symbol
            price: Current price
            signal_type: Signal type (BUY, SELL, NEUTRAL)
            score: Confluence score (0-100)
            reliability: Signal reliability (0-1)
            
        Returns:
            Dict with calculated trade parameters
        """
        try:
            # Handle None values gracefully
            if price is None:
                self.logger.warning(f"Price is None for {symbol}, using default trade parameters")
                return {
                    'entry_price': None,
                    'stop_loss': None,
                    'take_profit': None,
                    'position_size': None,
                    'risk_reward_ratio': None,
                    'risk_percentage': None,
                    'confidence': min(score / 100, 1.0) if score is not None else None,
                    'timeframe': 'auto'
                }
                
            if score is None:
                score = 50.0  # Default to neutral score
                self.logger.warning(f"Score is None for {symbol}, using default value of {score}")
                
            if reliability is None:
                reliability = 0.5  # Default to medium reliability
                self.logger.warning(f"Reliability is None for {symbol}, using default value of {reliability}")
            
            # Default trade parameters
            trade_params = {
                'entry_price': price,
                'stop_loss': None,
                'take_profit': None,
                'position_size': None,
                'risk_reward_ratio': None,
                'risk_percentage': None,
                'confidence': min(score / 100, 1.0) if score is not None else 0.5,
                'timeframe': 'auto'
            }
            
            # If neutral signal, return default params
            if signal_type == "NEUTRAL":
                self.logger.debug(f"Neutral signal for {symbol}, using default trade parameters")
                return trade_params
                
            # Get trading config
            trading_config = self.config.get('trading', {})
            risk_config = trading_config.get('risk', {})
            
            # Calculate position size based on risk percentage
            risk_percentage = risk_config.get('max_risk_per_trade', 0.02)  # Default 2%
            account_balance = trading_config.get('account_balance', 10000)  # Default $10k
            
            # Adjust risk based on signal strength and reliability
            adjusted_risk = risk_percentage * reliability * (abs(score - 50) / 50)
            max_risk_amount = account_balance * adjusted_risk
            
            # Calculate stop loss distance based on signal type and volatility
            stop_loss_percentage = risk_config.get('stop_loss_percentage', 0.02)  # Default 2%
            
            if signal_type == "BUY":
                stop_loss_price = price * (1 - stop_loss_percentage)
                take_profit_price = price * (1 + stop_loss_percentage * 2)  # 2:1 RR ratio
            else:  # SELL
                stop_loss_price = price * (1 + stop_loss_percentage)
                take_profit_price = price * (1 - stop_loss_percentage * 2)  # 2:1 RR ratio
            
            # Calculate position size based on risk amount and stop loss distance
            stop_loss_distance = abs(price - stop_loss_price)
            if stop_loss_distance > 0:
                position_size = max_risk_amount / stop_loss_distance
            else:
                position_size = 0
            
            # Update trade parameters
            trade_params.update({
                'stop_loss': stop_loss_price,
                'take_profit': take_profit_price,
                'position_size': position_size,
                'risk_reward_ratio': 2.0,  # Default 2:1
                'risk_percentage': adjusted_risk,
                'confidence': min(score / 100, 1.0) * reliability
            })
            
            self.logger.debug(f"Calculated trade parameters for {symbol}: {trade_params}")
            return trade_params
            
        except Exception as e:
            self.logger.error(f"Error calculating trade parameters for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return {
                'entry_price': price,
                'stop_loss': None,
                'take_profit': None,
                'position_size': None,
                'risk_reward_ratio': None,
                'risk_percentage': None,
                'confidence': 0.5,
                'timeframe': 'auto'
            }

    async def analyze_confluence_and_generate_signals(self, market_data: Dict[str, Any]) -> None:
        """
        Analyze market data through confluence analyzer and generate trading signals
        
        Args:
            market_data: Dictionary containing all market data including:
                - symbol: Trading pair symbol
                - ticker: Latest ticker data
                - orderbook: Current orderbook
                - trades: Recent trades
                - ohlcv: OHLCV data for different timeframes
        """
        try:
            symbol = market_data.get('symbol', 'unknown')
            self.logger.info(f"🔄 CONFLUENCE: Running confluence analysis for {symbol}")
            
            # Ensure the symbol field is set correctly in market_data
            if 'symbol' not in market_data:
                self.logger.debug(f"🔄 CONFLUENCE: Adding missing 'symbol' field to market data for {symbol}")
                market_data['symbol'] = symbol
            
            # Add detailed logging of data structure
            self.logger.debug("=== Market Data Structure ===")
            self.logger.debug(f"Market data keys: {market_data.keys()}")
            self.logger.debug(f"OHLCV keys: {market_data.get('ohlcv', {}).keys()}")
            if 'ohlcv' in market_data and 'base' in market_data['ohlcv']:
                self.logger.debug(f"Base timeframe type: {type(market_data['ohlcv']['base'])}")
                self.logger.debug(f"Base timeframe structure: {market_data['ohlcv']['base']}")
            
            # Check if alert manager is available
            if not self.alert_manager:
                self.logger.error(f"🔄 CONFLUENCE: Alert manager not available for {symbol} - alerts won't be sent")
            else:
                self.logger.info(f"🔄 CONFLUENCE: Alert manager is available with handlers: {self.alert_manager.handlers}")
            
            # Check if signal generator is available
            if not self.signal_generator:
                self.logger.error(f"🔄 CONFLUENCE: Signal generator not available for {symbol} - signals won't be generated")
                return
            else:
                self.logger.info(f"🔄 CONFLUENCE: Signal generator is available for {symbol}")
            
            # Get analysis from confluence analyzer
            try:
                self.logger.info(f"🔄 CONFLUENCE: Getting analysis from confluence analyzer for {symbol}")
                analysis_result = await self.confluence_analyzer.analyze(market_data)
                self.logger.info(f"🔄 CONFLUENCE: Analysis complete for {symbol}")
            except DataUnavailableError as e:
                self.logger.error(f"🔄 CONFLUENCE: Aborting analysis: {str(e)}")
                return
            except Exception as e:
                self.logger.warning(f"🔄 CONFLUENCE: No confluence analysis result for {symbol}: {str(e)}")
                self.logger.debug(traceback.format_exc())
                analysis_result = self._get_default_scores(symbol)

            # Generate signals based on analysis
            try:
                self.logger.info(f"🔄 CONFLUENCE: Generating signals for {symbol} with analysis result")
                signals = await self.signal_generator.generate_signals(
                    symbol=symbol,
                    market_data=market_data,
                    analysis=analysis_result
                )
                self.logger.info(f"🔄 CONFLUENCE: Signal generation complete for {symbol}")
            except Exception as e:
                self.logger.error(f"🔄 CONFLUENCE: Error generating signals for {symbol}: {str(e)}")
                self.logger.debug(traceback.format_exc())
                return

            # Process any signals through alert manager
            if signals:
                self.logger.info(f"🔄 CONFLUENCE: Generated signals for {symbol}: {signals}")
                try:
                    if self.alert_manager:
                        self.logger.info(f"🔄 CONFLUENCE: Sending signals to alert manager for {symbol}")
                        await self.alert_manager.process_signals(signals)
                        self.logger.info(f"🔄 CONFLUENCE: Signals processed by alert manager for {symbol}")
                    else:
                        self.logger.error(f"🔄 CONFLUENCE: Alert manager not available for {symbol}")
                except Exception as e:
                    self.logger.error(f"🔄 CONFLUENCE: Error processing signals for {symbol}: {str(e)}")
                    self.logger.debug(traceback.format_exc())
            else:
                self.logger.debug(f"🔄 CONFLUENCE: No signals generated for {symbol}")

            # Store analysis results
            if self.database_client:
                await self.database_client.store_analysis(
                    symbol=symbol,
                    analysis=analysis_result,
                    signals=signals
                )

        except Exception as e:
            self.logger.error(f"Error in confluence analysis for {market_data.get('symbol')}: {str(e)}", exc_info=True)
            # Use default scores on error
            analysis_result = self._get_default_scores(market_data.get('symbol'))

    def _get_default_scores(self, symbol: str) -> Dict[str, Any]:
        """Get default analysis scores when analysis fails."""
        return {
            'confluence_score': 50.0,
            'components': {},
            'results': {},
            'reliability': 0.5,
            'symbol': symbol,
            'timestamp': int(time.time() * 1000)
        }

    def _get_ohlcv_for_report(self, symbol: str, timeframe: str = 'base') -> Optional[Any]:
        """Get OHLCV data for report generation. This is a placeholder that should be implemented by the calling code."""
        # This method would need to be implemented by the monitor or injected as a dependency
        # For now, return None to avoid errors
        self.logger.debug(f"OHLCV data requested for {symbol} timeframe {timeframe} - not implemented in SignalProcessor")
        return None 