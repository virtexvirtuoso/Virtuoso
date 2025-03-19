"""Signal Generator Module.

This module is responsible for generating trading signals based on market analysis.

Signal Generation Process:
- The SignalGenerator receives confluence scores from the MarketMonitor
- It evaluates scores against thresholds defined in config.yaml under analysis.confluence_thresholds
- Buy signals are generated when scores exceed the buy threshold (60)
- Sell signals are generated when scores fall below the sell threshold (40)
- Signal strength is determined based on how far the score is from the threshold
- Alerts are sent through the AlertManager when thresholds are crossed
- All thresholds are consistently defined in one place (config.yaml)
"""

# src/signal_generation/signal_generator.py

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from src.utils.helpers import normalize_weights
from src.indicators.technical_indicators import TechnicalIndicators
from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.orderflow_indicators import OrderflowIndicators
from src.indicators.orderbook_indicators import OrderbookIndicators
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.indicators.sentiment_indicators import SentimentIndicators
import traceback
from datetime import datetime
import asyncio
import time
from src.monitoring.alert_manager import AlertManager
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class SignalGenerator:
    """Generates trading signals based on analysis results."""
    
    def __init__(self, config: Dict[str, Any], alert_manager: Optional[AlertManager] = None):
        """Initialize signal generator with configuration settings.
        
        Args:
            config: Configuration dictionary
            alert_manager: Optional alert manager instance
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Load thresholds from config
        confluence_config = config.get('confluence', {})
        threshold_config = confluence_config.get('thresholds', {})
        
        # Set thresholds with defaults matching config.yaml defaults
        self.thresholds = {
            'buy': float(threshold_config.get('buy', 60)),
            'sell': float(threshold_config.get('sell', 40)),
            'neutral_buffer': float(threshold_config.get('neutral_buffer', 5))
        }
        
        self.logger.debug(f"Loaded signal thresholds from config: {self.thresholds}")
        
        # Debug initialization
        self.logger.debug(f"Initializing SignalGenerator with config: {config}")
        
        # Initialize components using the new unified weight structure
        self.confluence_weights = config.get('confluence', {}).get('weights', {}).get('components', {})
        self.logger.debug(f"Loaded confluence component weights: {self.confluence_weights}")
        
        # Initialize indicators
        self.technical_indicators = TechnicalIndicators(config)
        self.volume_indicators = VolumeIndicators(config)
        self.orderflow_indicators = OrderflowIndicators(config)
        self.orderbook_indicators = OrderbookIndicators(config)
        self.price_structure_indicators = PriceStructureIndicators(config)
        self.sentiment_indicators = SentimentIndicators(config)
        
        logger.debug(f"Initialized SignalGenerator with config: {config}")
        
        # Initialize processor to None - will be lazy loaded
        self._processor = None
        
        # Load environment variables
        load_dotenv()
        
        # Initialize AlertManager with debug logging
        self.logger.debug("Initializing AlertManager...")
        
        # Add Discord webhook from environment to config
        if 'monitoring' not in config:
            config['monitoring'] = {}
        if 'alerts' not in config['monitoring']:
            config['monitoring']['alerts'] = {}
            
        # Get Discord webhook from environment
        discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        if discord_webhook:
            config['monitoring']['alerts']['discord_network'] = discord_webhook
            self.logger.info("Discord webhook loaded from environment variables")
        else:
            self.logger.warning("Discord webhook URL not found in environment variables")
        
        if alert_manager:
            self.alert_manager = alert_manager
        else:
            self.logger.warning("No alert manager provided")
            self.alert_manager = None
        
        # Verify AlertManager initialization
        if self.alert_manager and hasattr(self.alert_manager, 'discord_network'):
            self.logger.info(f"AlertManager initialized with Discord webhook: {bool(self.alert_manager.discord_network)}")
            self.logger.info(f"Registered handlers: {list(self.alert_manager.alert_handlers.keys())}")
        else:
            self.logger.warning("AlertManager not properly initialized")
        
        logger.debug("SignalGenerator initialized")
        
        # Replace hardcoded weights with config
        self.timeframe_weights = {
            tf: config['timeframes'][tf]['weight']
            for tf in ['base', 'ltf', 'mtf', 'htf']
        }
        
        # Normalize if needed
        total = sum(self.timeframe_weights.values())
        if total != 1.0:
            self.timeframe_weights = {k: v/total for k,v in self.timeframe_weights.items()}

    @property
    async def processor(self):
        """Lazy initialization of DataProcessor to avoid circular imports."""
        if self._processor is None:
            # Import here to avoid circular dependency
            from src.data_processing.data_processor import DataProcessor
            self._processor = DataProcessor(self.config)
            await self._processor.initialize()
        return self._processor

    async def generate_confluence_score(self, indicators: Dict[str, float]) -> float:
        """Generate and store confluence score from individual indicators.
        
        Args:
            indicators: Dictionary containing indicator scores and metadata
            
        Returns:
            float: Calculated confluence score between 0 and 100
            
        Raises:
            RuntimeError: If score calculation fails
        """
        try:
            symbol = indicators.get('symbol', 'UNKNOWN')
            logger.debug(f"Generating confluence score for {symbol}")
            
            # Create mapping between config weights and indicator scores
            score_mapping = {
                'momentum': 'momentum_score',
                'volume': 'volume_score',
                'orderflow': 'orderflow_score',
                'orderbook': 'orderbook_score',
                'position': 'position_score',
                'sentiment': 'sentiment_score'
            }
            
            # Replace NaN values with neutral scores using the mapping
            scores = {
                weight_key: indicators.get(score_key, 50.0)
                for weight_key, score_key in score_mapping.items()
            }
            
            # Replace any NaN values with 50
            scores = {k: 50.0 if pd.isna(v) else float(v) for k, v in scores.items()}
            
            # Calculate weighted sum using normalized weights
            confluence_weights = normalize_weights(self.confluence_weights)
            confluence_score = sum(
                scores[k] * w for k, w in confluence_weights.items()
            )
            
            # Clip the score between 0 and 100
            confluence_score = float(np.clip(confluence_score, 0, 100))
            
            # Get timestamp from indicators or use current time
            timestamp = indicators.get('timestamp', datetime.utcnow())
            
            # Get market conditions
            market_conditions = {
                'price': indicators.get('current_price', 0),
                'volume_24h': indicators.get('volume_24h', 0),
                'funding_rate': indicators.get('funding_rate', 0),
                'volatility': indicators.get('volatility', 0),
            }
            
            # Prepare scores for storage with additional metadata
            analysis_scores = {
                # Component scores
                'momentum': scores['momentum'],
                'volume': scores['volume'],
                'orderflow': scores['orderflow'],
                'orderbook': scores['orderbook'],
                'position': scores['position'],
                'sentiment': scores['sentiment'],
                'confluence_score': confluence_score,
                
                # Market metadata
                'market_conditions': market_conditions,
                
                # Additional metadata for historical analysis
                'timeframe': indicators.get('timeframe', '1m'),
                'session': indicators.get('session', 'unknown'),
                'market_type': indicators.get('market_type', 'unknown'),
                'volatility_regime': indicators.get('volatility_regime', 'unknown'),
            }
            
            try:
                # Store scores in database using lazy-loaded processor
                processor = await self.processor
                await processor.store_analysis_scores(
                    symbol=symbol,
                    scores=analysis_scores,
                    timestamp=timestamp
                )
                logger.info(f"Stored analysis scores for {symbol} in database with timestamp {timestamp}")
            except Exception as e:
                logger.error(f"Error storing analysis scores: {str(e)}")
                logger.error(traceback.format_exc())
                # Continue execution as storage failure shouldn't affect score calculation
            
            return confluence_score
            
        except Exception as e:
            logger.error(f"Error calculating confluence score: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Failed to calculate confluence score: {str(e)}") from e

    async def store_individual_scores(self, indicators: Dict[str, float], scores: Dict[str, float]) -> None:
        """Store individual scores for reference.
        
        Args:
            indicators: Dictionary to update with scores
            scores: Dictionary containing individual scores
        """
        symbol = indicators.get('symbol', 'UNKNOWN')
        logger.debug(f"Storing individual scores for {symbol}: {scores}")
        
        # Make sure to preserve the symbol
        indicators['symbol'] = symbol
        
        # Update indicators with scores
        score_keys = ['momentum_score', 'volume_score', 'orderflow_score', 
                     'orderbook_score', 'position_score', 'sentiment_score']
                     
        for key in score_keys:
            if key in scores:
                indicators[key] = scores[key]
                
        # Store in processor if available
        try:
            if self.processor:
                await self.processor.store_indicator_scores(symbol, scores)
        except Exception as e:
            logger.error(f"Failed to store indicator scores: {str(e)}")
            logger.debug(traceback.format_exc())

    async def _validate_signal_data(self, indicators: Dict[str, Any]) -> bool:
        """Validate signal generation input data.
        
        Args:
            indicators (Dict[str, Any]): Dictionary containing indicator data
            
        Returns:
            bool: True if valid, False if invalid
        """
        if indicators is None:
            self.logger.error("Signal validation failed: indicators is None")
            return False
            
        if not isinstance(indicators, dict):
            self.logger.error(f"Signal validation failed: indicators is not a dict, got {type(indicators)}")
            return False
            
        try:
            # CRITICAL: Special handling for signals from MarketMonitor
            # If the signal contains 'direction' key, it's from MarketMonitor._generate_signal
            if 'direction' in indicators:
                self.logger.info(f"Signal from MarketMonitor detected with direction: {indicators['direction']}")
                
                # Check for required fields from MarketMonitor
                required_monitor_fields = {'symbol', 'direction', 'confluence_score'}
                missing_fields = required_monitor_fields - set(indicators.keys())
                if missing_fields:
                    self.logger.error(f"Signal from MarketMonitor missing fields: {missing_fields}")
                    return False
                
                # Add required fields expected by downstream functions
                if 'current_price' not in indicators:
                    indicators['current_price'] = 0  # Will be fetched later if needed
                
                # Map to expected format
                if 'confluence_score' in indicators and 'score' not in indicators:
                    indicators['score'] = indicators['confluence_score']
                
                # Map direction to signal type
                if 'direction' in indicators and 'signal' not in indicators:
                    direction = indicators['direction'].upper()
                    if direction == 'BUY':
                        indicators['signal'] = 'BUY'
                    elif direction == 'SELL':
                        indicators['signal'] = 'SELL'
                    else:
                        indicators['signal'] = 'NEUTRAL'
                
                # Successfully validated MarketMonitor signal format
                self.logger.info(f"MarketMonitor signal for {indicators['symbol']} validated successfully")
                return True
            
            # Standard validation for regular indicator format
            # Check required fields
            required_fields = {
                'symbol', 
                'current_price', 
                'momentum_score', 
                'volume_score', 
                'orderflow_score'
            }
            missing_fields = required_fields - set(indicators.keys())
            if missing_fields:
                # Check for alternative field names
                alternative_mappings = {
                    'momentum_score': 'technical_score',
                    'volume_score': 'volume_score',
                    'orderflow_score': 'orderflow_score'
                }
                
                # Try to map alternative field names
                for missing in list(missing_fields):
                    alt = alternative_mappings.get(missing)
                    if alt and alt in indicators:
                        indicators[missing] = indicators[alt]
                        missing_fields.remove(missing)
                
                # If still missing fields, log and return false
                if missing_fields:
                    self.logger.error(f"Signal validation failed: missing required fields: {missing_fields}")
                    self.logger.error(f"Available fields: {set(indicators.keys())}")
                    return False
            
            # Validate numeric values
            numeric_fields = ['current_price', 'volume_24h']
            for field in numeric_fields:
                if field not in indicators:
                    continue  # Skip non-required fields
                    
                value = indicators.get(field)
                if not isinstance(value, (int, float)) or value < 0:
                    self.logger.error(f"Signal validation failed: {field} must be a positive number, got {value} ({type(value)})")
                    # Auto-fix if possible
                    if field == 'current_price':
                        indicators[field] = 0  # Will be fetched later
                
            # Validate score ranges
            score_fields = ['momentum_score', 'volume_score', 'orderflow_score']
            for field in score_fields:
                score = indicators.get(field)
                if not isinstance(score, (int, float)) or not 0 <= score <= 100:
                    self.logger.error(f"Signal validation failed: {field} must be 0-100, got {score} ({type(score)})")
                    return False
                    
            return True
            
        except Exception as e:
            # Log and return validation errors
            self.logger.error(f"Signal validation error: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    async def generate_signal(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trading signals based on indicator values."""
        try:
            # Get confluence score and current price from indicators
            confluence_score = indicators.get('confluence', indicators.get('score', 0.0))
            current_price = indicators.get('current_price', 0.0)
            symbol = indicators.get('symbol', 'UNKNOWN')

            logger.debug(f"Received data for {symbol}:")
            logger.debug(f"Raw indicators: {indicators}")
            logger.debug(f"Extracted score: {confluence_score}")

            # Use thresholds from the self.thresholds dictionary loaded during initialization
            buy_threshold = self.thresholds['buy']
            sell_threshold = self.thresholds['sell']
            
            logger.debug(f"Signal check for {symbol}:")
            logger.debug(f"Confluence score: {confluence_score}")
            logger.debug(f"Buy threshold: {buy_threshold}")
            logger.debug(f"Sell threshold: {sell_threshold}")
            
            signal = None  # Initialize signal as None
            alerts_sent = False  # Track if alerts were sent
            
            # Extract component scores for the formatted alert
            components = {
                'volume': indicators.get('volume_score', 50),
                'technical': indicators.get('technical_score', indicators.get('momentum_score', 50)),
                'orderflow': indicators.get('orderflow_score', 50),
                'orderbook': indicators.get('orderbook_score', 50),
                'sentiment': indicators.get('sentiment_score', 50),
                'price_structure': indicators.get('price_structure_score', indicators.get('position_score', 50))
            }
            
            # Prepare results object with detailed interpretations for each component
            results = {}
            for component_name, component_score in components.items():
                # Get the appropriate interpretation method based on component name
                interpret_method = getattr(self, f"_interpret_{component_name}", None)
                
                if not interpret_method:
                    # Fallback for missing methods
                    self.logger.warning(f"No interpretation method found for {component_name}")
                    interpretation = f"No interpretation available for {component_name}"
                else:
                    # Get detailed interpretation for this component's score
                    interpretation = interpret_method(component_score, indicators)
                
                # Extract sub-components if available
                extract_method = getattr(self, f"_extract_{component_name}_components", None)
                sub_components = {}
                if extract_method:
                    sub_components = extract_method(indicators)
                
                # Create component entry with full interpretation text
                results[component_name] = {
                    'score': component_score,
                    'components': sub_components,
                    'interpretation': interpretation
                }
            
            # Generate signals based on configured thresholds
            if confluence_score >= buy_threshold:
                logger.info(f"Generating BUY signal - Score {confluence_score} >= {buy_threshold}")
                signal = "BUY"
                # Determine signal strength and emoji
                if confluence_score >= 80:
                    strength = "Very Strong"
                    emoji = "🚀"
                elif confluence_score >= 70:
                    strength = "Strong"
                    emoji = "💫"
                else:
                    strength = "Moderate"
                    emoji = "⭐"
                
                # Create the signal but do NOT send any alerts here - let AlertManager handle it
                # This avoids double alerting
                
            elif confluence_score <= sell_threshold:
                logger.info(f"Generating SELL signal - Score {confluence_score} <= {sell_threshold}")
                signal = "SELL"
                # Determine signal strength and emoji
                if confluence_score <= 20:
                    strength = "Very Strong"
                    emoji = "💥"
                elif confluence_score <= 30:
                    strength = "Strong"
                    emoji = "⚡"
                else:
                    strength = "Moderate"
                    emoji = "🔻"
                
                # Create the signal but do NOT send any alerts here - let AlertManager handle it
                # This avoids double alerting
                
            else:
                logger.info(f"No signal generated - Score {confluence_score} in neutral zone")
                return None

            if signal:
                # Prepare the signal result to return
                signal_result = {
                    'signal': signal,
                    'score': confluence_score,
                    'price': current_price,
                    'symbol': symbol,
                    'components': components,
                    'results': results,
                    'already_processed': False,  # Not processed yet
                    'alert_sent': False,         # Alert not sent yet
                    'timestamp': indicators.get('timestamp', int(time.time() * 1000))
                }
                
                # Log detailed interpretations for debugging and analysis
                self.logger.info(f"\n=== DETAILED MARKET INTERPRETATIONS FOR {symbol} ===")
                for component_name, component_data in results.items():
                    if 'interpretation' in component_data:
                        interpretation = component_data['interpretation']
                        if isinstance(interpretation, str):
                            self.logger.info(f"{component_name.replace('_', ' ').title()}: {interpretation}")
                        elif isinstance(interpretation, dict) and 'summary' in interpretation:
                            self.logger.info(f"{component_name.replace('_', ' ').title()}: {interpretation['summary']}")
                
                # Let the AlertManager handle all alerts in a centralized way
                # to avoid duplication
                return signal_result
            return None

        except Exception as e:
            logger.error(f"Error generating signal: {str(e)}")
            raise RuntimeError(f"Failed to generate signal: {str(e)}") from e

    async def _send_signal_alert(self, signal: Dict[str, Any], indicators: Dict[str, Any]) -> None:
        """Send signal alert via configured channels."""
        try:
            if not self.alert_manager:
                self.logger.error("⚠️ AlertManager not initialized")
                return

            # ALERT PIPELINE DEBUG: Verify alert manager state
            self.logger.info(f"ALERT DEBUG: Verifying AlertManager state before sending signal for {signal.get('symbol')}")
            
            # Check if alert_manager has expected attributes
            if not hasattr(self.alert_manager, 'verify_handler_state'):
                self.logger.error(f"ALERT DEBUG: AlertManager missing verify_handler_state method - possible version mismatch")
            else:
                # Verify handler state before sending
                debug_info = await self.alert_manager.verify_handler_state()
                self.logger.info(f"ALERT DEBUG: AlertManager handlers: {debug_info.get('handlers', [])}") 
                
                # Check if there are issues
                if debug_info.get('status') == 'NO_HANDLERS':
                    self.logger.critical(f"ALERT DEBUG: No handlers registered in AlertManager when sending signal for {signal.get('symbol')}")
                    
                    # Verify discord webhook URL
                    if hasattr(self.alert_manager, 'discord_webhook_url') and self.alert_manager.discord_webhook_url:
                        self.logger.info(f"ALERT DEBUG: Discord webhook URL exists: {self.alert_manager.discord_webhook_url[:20]}...{self.alert_manager.discord_webhook_url[-10:]}")
                        
                        # Try to force register
                        self.logger.info("ALERT DEBUG: Attempting to force register Discord handler")
                        self.alert_manager.register_handler('discord')
                        self.logger.info(f"ALERT DEBUG: After force registration: {self.alert_manager.handlers}")

            # Debug log for troubleshooting
            self.logger.debug(f"_send_signal_alert called for {signal.get('symbol')} with score {signal.get('score', 0):.2f}")
            
            timestamp = indicators.get('timestamp')
            if isinstance(timestamp, datetime):
                timestamp = int(timestamp.timestamp() * 1000)
            else:
                timestamp = int(time.time() * 1000)
            
            # Get results/components needed for the fancy formatting
            components = {
                'volume': indicators.get('volume_score', 50),
                'technical': indicators.get('technical_score', indicators.get('momentum_score', 50)),
                'orderflow': indicators.get('orderflow_score', 50),
                'orderbook': indicators.get('orderbook_score', 50),
                'sentiment': indicators.get('sentiment_score', 50),
                'price_structure': indicators.get('price_structure_score', indicators.get('position_score', 50))
            }
            
            # ALERT PIPELINE DEBUG: Log component scores
            self.logger.info(f"ALERT DEBUG: Component scores for {signal.get('symbol')}: {components}")
            
            # Create a detailed results object with rich interpretations
            results = {}
            for component_name, component_score in components.items():
                # Get the appropriate interpretation method based on component name
                interpret_method = getattr(self, f"_interpret_{component_name}", None)
                
                if not interpret_method:
                    # Fallback for missing methods
                    self.logger.warning(f"No interpretation method found for {component_name}")
                    interpretation = f"No interpretation available for {component_name}"
                else:
                    # Get detailed interpretation for this component's score
                    interpretation = interpret_method(component_score, indicators)
                
                # Extract sub-components if available
                extract_method = getattr(self, f"_extract_{component_name}_components", None)
                sub_components = {}
                if extract_method:
                    sub_components = extract_method(indicators)
                
                # Create component entry with full interpretation text
                results[component_name] = {
                    'score': component_score,
                    'components': sub_components,
                    'interpretation': interpretation
                }
            
            # Get reliability if available
            reliability = indicators.get('reliability', 0.8)  # Default to 0.8 if not specified
            
            # Check if this is a threshold crossing signal that needs the fancy formatting
            score = signal.get('score', 0)
            
            # Create a signal data dictionary that indicates what's been processed
            alert_data = {
                'symbol': signal['symbol'],
                'signal_type': signal['signal'],
                'score': signal['score'],
                'price': signal['price'],
                'timestamp': timestamp,
                'indicators': components,
                'already_processed': True,  # Mark as already processed
                'metadata': {
                    'timeframe': indicators.get('timeframe', '1m'),
                    'market_type': indicators.get('market_type', 'unknown'),
                    'volatility': indicators.get('volatility', 0)
                }
            }
            
            # Use the thresholds from config instead of hardcoded values
            # Send fancy alerts for any score that meets or exceeds buy threshold or is at/below sell threshold
            self.logger.debug(f"Checking signal score {score:.2f} against thresholds: buy={self.thresholds['buy']}, sell={self.thresholds['sell']}")
            if score >= self.thresholds['buy'] or score <= self.thresholds['sell']:
                self.logger.info(f"Sending fancy confluence alert for {signal['symbol']} with score {score:.2f}")
                # Use the fancy formatter for threshold signals
                await self.alert_manager.send_confluence_alert(
                    symbol=signal['symbol'],
                    confluence_score=score,
                    components=components,
                    results=results,
                    reliability=reliability,
                    buy_threshold=self.thresholds['buy'],
                    sell_threshold=self.thresholds['sell']
                )
                
                # Mark that we've sent the alert
                alert_data['alert_sent'] = True
            else:
                self.logger.info(f"Score {score:.2f} is within neutral range, sending regular alert for {signal['symbol']}")
                # Use the regular alert for other signals
                await self.alert_manager.send_alert(
                    level="INFO",
                    message=f"🎯 {signal['signal']} Signal - {signal['symbol']}\n" +
                           f"Score: {signal['score']:.2f}\n" +
                           f"Price: ${signal['price']:,.6f}",
                    details=alert_data
                )
                
                # Mark that we've sent the signal alert
                alert_data['signal_sent'] = True
            
        except Exception as e:
            self.logger.error(f"Error sending signal alert: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def _collect_indicator_results(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Collect detailed indicator results for formatted alerts."""
        return {
            'volume': {
                'components': self._extract_volume_components(indicators),
                'interpretation': self._interpret_volume(indicators.get('volume_score', 50), indicators)
            },
            'orderflow': {
                'components': self._extract_orderflow_components(indicators),
                'interpretation': self._interpret_orderflow(indicators.get('orderflow_score', 50), indicators)
            },
            'orderbook': {
                'components': self._extract_orderbook_components(indicators),
                'interpretation': self._interpret_orderbook(indicators.get('orderbook_score', 50), indicators)
            },
            'technical': {
                'components': self._extract_technical_components(indicators),
                'interpretation': self._interpret_technical(indicators.get('technical_score', indicators.get('momentum_score', 50)), indicators)
            },
            'sentiment': {
                'components': self._extract_sentiment_components(indicators),
                'interpretation': self._interpret_sentiment(indicators.get('sentiment_score', 50), indicators)
            },
            'price_structure': {
                'components': self._extract_price_structure_components(indicators),
                'interpretation': self._interpret_price_structure(indicators.get('price_structure_score', indicators.get('position_score', 50)), indicators)
            }
        }

    def _extract_volume_components(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Extract volume-related component scores from indicators."""
        components = {}
        # Look for specific volume indicators
        for key, value in indicators.items():
            if key.startswith('volume_') and isinstance(value, (int, float)) and key != 'volume_score':
                # Convert key from volume_indicator to indicator format
                component_name = key.replace('volume_', '')
                components[component_name] = float(value)
        
        # Add some default components if none found
        if not components:
            components = {
                'volume_delta': indicators.get('volume_delta', 75.0),
                'cmf': indicators.get('cmf', 100.0),
                'adl': indicators.get('adl', 50.7)
            }
        
        return components

    def _extract_orderflow_components(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Extract orderflow-related component scores from indicators."""
        components = {}
        # Look for specific orderflow indicators
        for key, value in indicators.items():
            if key.startswith('orderflow_') and isinstance(value, (int, float)) and key != 'orderflow_score':
                component_name = key.replace('orderflow_', '')
                components[component_name] = float(value)
        
        # Add some default components if none found
        if not components:
            components = {
                'trade_flow_score': indicators.get('trade_flow_score', 75.07),
                'imbalance_score': indicators.get('imbalance_score', 71.67),
                'cvd': indicators.get('cvd', 57.42)
            }
        
        return components

    def _extract_orderbook_components(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Extract orderbook-related component scores from indicators."""
        components = {}
        # Look for specific orderbook indicators
        for key, value in indicators.items():
            if key.startswith('orderbook_') and isinstance(value, (int, float)) and key != 'orderbook_score':
                component_name = key.replace('orderbook_', '')
                components[component_name] = float(value)
        
        # Add some default components if none found
        if not components:
            components = {
                'support_resistance': indicators.get('support_resistance', 100.0),
                'price_impact': indicators.get('price_impact', 99.99),
                'liquidity': indicators.get('liquidity', 78.69)
            }
        
        return components

    def _extract_technical_components(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Extract technical indicators from the provided data."""
        return {
            'rsi': indicators.get('rsi', 50.0),
            'macd': indicators.get('macd', 50.0),
            'ao': indicators.get('ao', 50.0),
            'williams_r': indicators.get('williams_r', 50.0),
            'atr': indicators.get('atr', 50.0),
            'cci': indicators.get('cci', 50.0)
        }

    def _extract_sentiment_components(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Extract sentiment-related component scores from indicators."""
        components = {}
        # Look for specific sentiment indicators
        for key, value in indicators.items():
            if key.startswith('sentiment_') and isinstance(value, (int, float)) and key != 'sentiment_score':
                component_name = key.replace('sentiment_', '')
                components[component_name] = float(value)
        
        # Add some default components if none found
        if not components:
            components = {
                'risk_score': indicators.get('risk_score', 56.52),
                'funding_rate': indicators.get('funding_rate', 50.5),
                'long_short_ratio': indicators.get('long_short_ratio', 50.0)
            }
        
        return components

    def _extract_price_structure_components(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Extract price structure-related component scores from indicators."""
        components = {}
        # Look for specific price structure indicators
        for key, value in indicators.items():
            if key.startswith('price_structure_') and isinstance(value, (int, float)) and key != 'price_structure_score':
                component_name = key.replace('price_structure_', '')
                components[component_name] = float(value)
        
        # Add some default components if none found
        if not components:
            components = {
                'vwap': indicators.get('vwap', 49.15),
                'composite_value': indicators.get('composite_value', 48.63),
                'market_structure': indicators.get('market_structure', 45.0)
            }
        
        return components

    def _interpret_volume(self, score: float, indicators: Dict[str, Any] = None) -> str:
        """Interpret volume score with detailed market insights.
        
        Args:
            score: Volume score (0-100)
            indicators: Optional indicator data for more sophisticated interpretation
            
        Returns:
            Detailed market interpretation
        """
        # If indicators data is available, provide more nuanced analysis
        if indicators:
            # Extract specific volume indicators if available
            volume_delta = indicators.get('volume_delta', indicators.get('volume_change', 0))
            volume_sma_ratio = indicators.get('volume_sma_ratio', 0)
            adl = indicators.get('adl_score', indicators.get('adl', 0))
            mfi = indicators.get('mfi', 50)
            obv = indicators.get('obv_score', indicators.get('obv', 0))
            cmf = indicators.get('cmf', 0)
            
            # Check for volume-price divergence
            price_change = indicators.get('price_change_pct', 0)
            divergence = (volume_delta > 20 and price_change < 0) or (volume_delta < -20 and price_change > 0)
            
            # Check for specific volume patterns based on combination of indicators
            if score >= 80:
                if mfi > 80:
                    return "Strong Bullish Volume with High MFI - Heavy Institutional Buying 📈 (Potential Breakout Setup)"
                elif cmf > 0.2:
                    return "Strong Bullish Volume with High CMF - Significant Money Flow Into Asset 💰 (Accumulation Phase)"
                elif divergence:
                    return "Bullish Volume-Price Divergence - High Volume Despite Price Decline 💹 (Potential Reversal Signal)"
                else:
                    return "Strong Bullish Volume - Consistent Buying Pressure Across Timeframes 📈 (Strong Accumulation)"
                    
            elif score >= 65:
                if adl > 70:
                    return "Increasing Accumulation/Distribution Line - Steady Accumulation By Smart Money 📈 (Early Bull Phase)"
                elif volume_sma_ratio > 1.5:
                    return "Above Average Volume Trend - Rising Interest With Bullish Bias 📊 (Growing Institutional Interest)"
                else:
                    return "Moderate Bullish Volume - Buying Pressure Building 📈 (Accumulation Phase)"
                    
            elif score >= 50:
                if mfi > 60 and mfi < 80:
                    return "Moderate Money Flow - Slightly Bullish Without Overextension ↗️ (Sustainable Buying)"
                elif divergence:
                    return "Volume-Price Alignment - Healthy Volume Supporting Price Action ⚖️ (Equilibrium)"
                else:
                    return "Neutral Volume Trend - Balanced Trading Flow ↔️ (Consolidation Phase)"
                    
            elif score >= 35:
                if volume_sma_ratio < 0.7:
                    return "Below Average Volume With Bearish Bias - Lack of Buying Interest 📉 (Fading Bull Trend)"
                elif mfi < 30:
                    return "Low Money Flow Index - Selling Pressure Increasing 📉 (Early Distribution)"
                else:
                    return "Moderate Bearish Volume - Gradual Selling Pressure ⬇️ (Distribution Phase Beginning)"
                    
            else:
                if cmf < -0.2:
                    return "Strong Negative Money Flow - Heavy Capital Outflow 💸 (Institutional Selling)"
                elif volume_sma_ratio > 1.5 and price_change < -3:
                    return "High Volume Sell-Off - Panic Selling Across All Traders 📉 (Capitulation Phase)"
                elif divergence:
                    return "Bearish Volume-Price Divergence - Price Rising On Decreasing Volume ⚠️ (Potential Bull Trap)"
                else:
                    return "Strong Bearish Volume - Persistent Selling Pressure 📉 (Active Distribution)"
        
        # Default interpretations (when detailed indicators aren't available)
        if score >= 70: return "Strong Bullish Volume - Heavy Buying Flow 📈 (Accumulation)"
        elif score >= 60: return "Moderate Bullish Volume - Increased Buying 📈 (Accumulation Phase)"
        elif score >= 45: return "Neutral Volume - Balanced Trading ↔️ (Equilibrium)"
        elif score >= 30: return "Moderate Bearish Volume - Increased Selling ⬇️ (Distribution Phase)"
        else: return "Strong Bearish Volume - Heavy Selling Flow 📉 (Distribution)"

    def _interpret_orderbook(self, score: float, indicators: Dict[str, Any] = None) -> str:
        """Interpret orderbook score with market depth insights.
        
        Args:
            score: Orderbook score (0-100)
            indicators: Optional indicator data for more sophisticated interpretation
            
        Returns:
            Detailed market interpretation
        """
        if indicators:
            # Extract specific orderbook metrics if available
            bid_ask_ratio = indicators.get('bid_ask_ratio', 1.0)
            liquidity_score = indicators.get('liquidity', indicators.get('liquidity_score', 50))
            price_impact = indicators.get('price_impact', 50)
            support_resistance = indicators.get('support_resistance', 50)
            depth_imbalance = indicators.get('depth_imbalance', 0)
            spread = indicators.get('spread', 0)
            
            # Get current price
            current_price = indicators.get('current_price', 0)
            
            # More sophisticated analysis based on multiple factors
            if score >= 80:
                if bid_ask_ratio > 2:
                    return f"Heavy Bid Wall Dominance - Buy Orders Significantly Outweighing Asks 🧱 (Strong Support at {current_price:.2f})"
                elif liquidity_score > 80:
                    return "Exceptionally Deep Orderbook - High Liquidity Preventing Sharp Moves 💧 (Institutional Interest)"
                elif support_resistance > 90:
                    return "Major Support Level Active - Strong Buying Interest Defending Current Levels 💪 (Key Psychological Support)"
                else:
                    return "Strong Buy-Side Pressure Across All Depths - Robust Demand 📈 (Multiple Support Levels)"
                    
            elif score >= 65:
                if price_impact < 20:
                    return "Low Price Impact for Large Orders - Sufficient Liquidity For Institutional Entry 🛡️ (Deep Market)"
                elif bid_ask_ratio > 1.5:
                    return "Moderate Bid Dominance - More Buy Orders Than Sell Orders 📊 (Bullish Order Flow)"
                else:
                    return "Solid Buy-Side Depth - Stacked Limit Buy Orders 📈 (Building Support Structure)"
                    
            elif score >= 50:
                if spread < 0.05:
                    return "Tight Spread with Balanced Orders - High Market Efficiency ⚖️ (Liquid Trading Range)"
                elif abs(depth_imbalance) < 0.1:
                    return "Balanced Orderbook Depths - Equilibrium Between Buyers and Sellers ↔️ (Neutral Market Structure)"
                else:
                    return "Neutral Order Flow - Even Distribution of Buy and Sell Pressure ⚖️ (Range-Bound Market)"
                    
            elif score >= 35:
                if bid_ask_ratio < 0.7:
                    return "Ask-Side Dominance - Sell Orders Outweighing Buys 📉 (Overhead Resistance)"
                elif support_resistance < 30:
                    return "Weak Support Levels - Limited Buying Interest Below Current Price ⚠️ (Vulnerability to Breakdowns)"
                else:
                    return "Moderate Sell Pressure - Building Sell Orders Above Current Price ⬇️ (Forming Resistance)"
                    
            else:
                if bid_ask_ratio < 0.5:
                    return f"Heavy Ask Wall Dominance - Sell Orders Significantly Outweighing Bids 🧱 (Strong Resistance at {current_price:.2f})"
                elif depth_imbalance < -0.5:
                    return "Severely Imbalanced Orderbook - Overwhelming Sell Pressure 📉 (Potential Sharp Decline)"
                elif support_resistance < 20:
                    return "Critical Support Absence - Few Buy Orders Below Current Price 🕳️ (Air Pocket Risk)"
                else:
                    return "Strong Sell-Side Pressure Across All Depths - Minimal Demand 📉 (Multiple Resistance Levels)"
        
        # Default interpretations based solely on score
        if score >= 70: return "Strong Buy Pressure - Large Buy Orders 📈 (Demand Zone)"
        elif score >= 60: return "Moderate Buy Pressure - Buy Orders Stacking 📈 (Accumulation)"
        elif score >= 45: return "Neutral Order Flow - Balanced Orders ↔️ (Range-Bound)"
        elif score >= 30: return "Moderate Sell Pressure - Sell Orders Building ⬇️ (Supply Zone)"
        else: return "Strong Sell Pressure - Large Sell Orders 📉 (Distribution)"

    def _interpret_orderflow(self, score: float, indicators: Dict[str, Any] = None) -> str:
        """Interpret orderflow with detailed market dynamics.
        
        Args:
            score: Orderflow score (0-100)
            indicators: Optional indicator data for more sophisticated interpretation
            
        Returns:
            Detailed market interpretation
        """
        if indicators:
            # Extract specific orderflow metrics
            cvd = indicators.get('cvd', 0)
            cvd_slope = indicators.get('cvd_slope', 0) 
            trade_flow = indicators.get('trade_flow_score', indicators.get('trade_flow', 50))
            aggressive_buys = indicators.get('aggressive_buys', 0)
            aggressive_sells = indicators.get('aggressive_sells', 0)
            trade_size = indicators.get('avg_trade_size', 0)
            imbalance = indicators.get('imbalance_score', indicators.get('imbalance', 0))
            
            # Calculate buy/sell ratio if data available
            buy_sell_ratio = 1.0
            if aggressive_sells > 0:
                buy_sell_ratio = aggressive_buys / aggressive_sells
                
            # Check for absorption patterns (high aggressive counters to market direction)
            absorption = abs(cvd_slope) < 0.2 and max(aggressive_buys, aggressive_sells) > 0
            
            if score >= 80:
                if cvd > 0.8:
                    return "Extremely Positive Cumulative Volume Delta - Strong Buying Dominance 🚀 (Potential Breakout)"
                elif buy_sell_ratio > 3:
                    return "Heavy Aggressive Buying - Market Orders Absorbing All Available Asks 💫 (Strong Institutional Demand)"
                elif trade_size > 2 and imbalance > 70:
                    return "Large Traders Heavily Buying - Whales Entering Long Positions 🐋 (Smart Money Accumulation)"
                else:
                    return "Strong Bullish Order Flow - Consistent Large Buy Orders 📈 (Powerful Upward Pressure)"
                    
            elif score >= 65:
                if cvd_slope > 0.5:
                    return "Rising Cumulative Volume Delta - Consistent Buying Pressure ⬆️ (Building Momentum)"
                elif absorption and aggressive_buys > aggressive_sells:
                    return "Buy-Side Absorption - Limit Orders Containing Sell Pressure 🛡️ (Sellers Exhausting)"
                else:
                    return "Moderate Bullish Order Flow - More Market Buy Orders Than Sells 📈 (Healthy Demand)"
                    
            elif score >= 50:
                if abs(cvd) < 0.2:
                    return "Balanced Cumulative Volume Delta - Equilibrium Between Buying and Selling Forces ⚖️ (Range Trading)"
                elif abs(buy_sell_ratio - 1.0) < 0.2:
                    return "Even Trade Flow - Balanced Market Orders on Both Sides ↔️ (No Directional Edge)"
                else:
                    return "Neutral Order Flow - Mixed Trading Activity Without Clear Direction ↔️ (Consolidation Phase)"
                    
            elif score >= 35:
                if cvd_slope < -0.5:
                    return "Declining Cumulative Volume Delta - Consistent Selling Pressure ⬇️ (Building Downward Momentum)"
                elif absorption and aggressive_sells > aggressive_buys:
                    return "Sell-Side Absorption - Limit Orders Containing Buy Pressure 🛡️ (Buyers Exhausting)"
                else:
                    return "Moderate Bearish Order Flow - More Market Sell Orders Than Buys 📉 (Weakening Demand)"
                    
            else:
                if cvd < -0.8:
                    return "Extremely Negative Cumulative Volume Delta - Strong Selling Dominance 📉 (Potential Breakdown)"
                elif buy_sell_ratio < 0.33:
                    return "Heavy Aggressive Selling - Market Orders Absorbing All Available Bids 💥 (Strong Distribution)"
                elif trade_size > 2 and imbalance < 30:
                    return "Large Traders Heavily Selling - Whales Exiting Positions 🐋 (Smart Money Distribution)"
                else:
                    return "Strong Bearish Order Flow - Consistent Large Sell Orders 📉 (Powerful Downward Pressure)"
        
        # Default interpretations
        if score >= 80:
            return "Aggressive Buying - Large Orders Absorbing Asks 💫 (Strong Momentum)"
        elif score >= 65:
            return "Steady Buying Flow - Consistent Bid Support ⬆️ (Accumulation)"
        elif score >= 55:
            return "Mild Buying - Small Orders Stacking ↗️ (Early Trend Formation)"
        elif score >= 45:
            return "Mixed Flow - Balanced Buy/Sell Activity ↔️ (Range-Bound)"
        elif score >= 35:
            return "Mild Selling - Small Orders Hitting Bids ↘️ (Early Weakness)"
        elif score >= 20:
            return "Steady Selling Flow - Consistent Ask Pressure ⬇️ (Distribution)"
        else:
            return "Aggressive Selling - Large Orders Hitting Bids 🔻 (Strong Downside)"

    def _interpret_price_structure(self, score: float, indicators: Dict[str, Any] = None) -> str:
        """Interpret price structure with detailed market positioning.
        
        Args:
            score: Position/price structure score (0-100)
            indicators: Optional indicator data for more sophisticated interpretation
            
        Returns:
            Detailed market interpretation
        """
        if indicators:
            # Extract relevant position/structure indicators
            vwap_position = indicators.get('vwap_position', 0)  # -1 to 1, where positive means price > VWAP
            market_structure = indicators.get('market_structure', indicators.get('market_structure_score', 50))
            key_level_proximity = indicators.get('key_level_proximity', 0)  # 0-100, higher means closer to key level
            support_resistance = indicators.get('support_resistance', 50)
            trend_strength = indicators.get('trend_strength', 0)
            
            # Get price information
            current_price = indicators.get('current_price', 0)
            
            # Additional pattern indicators
            is_inside_bar = indicators.get('is_inside_bar', False)
            is_engulfing = indicators.get('is_engulfing', False)
            pivot_points = indicators.get('pivot_points', {})
            
            if score >= 80:
                if vwap_position > 0.5:
                    return f"Price Well Above VWAP - Strong Bullish Position Above Value Area 📈 (High-Probability Long Setup)"
                elif support_resistance > 80 and key_level_proximity > 80:
                    return "Trading At Major Support Zone - Heavy Buying Interest 🛡️ (Strong Technical Foundation)"
                elif market_structure > 80:
                    return "Higher Highs and Higher Lows - Textbook Bullish Structure 📈 (Strong Uptrend Confirmation)"
                else:
                    return "Optimal Bullish Position - Multiple Technical Supports Aligned 🎯 (Strategic Long Entry Point)"
                    
            elif score >= 65:
                if vwap_position > 0.1:
                    return "Price Above VWAP - Trading Above Value Area 📈 (Bullish Edge)"
                elif pivot_points and 'S1' in pivot_points:
                    return f"Price Near S1 Pivot Support - Technical Bounce Zone at {pivot_points['S1']:.2f} 📊 (Dip Buying Opportunity)"
                elif is_engulfing and market_structure > 60:
                    return "Bullish Engulfing Pattern Within Uptrend - Key Reversal Signal 🔄 (Trend Continuation Setup)"
                else:
                    return "Established Support Level - Historical Demand Zone 📈 (Technical Support Structure)"
                    
            elif score >= 50:
                if abs(vwap_position) < 0.1:
                    return "Price At VWAP - Trading At Fair Value ⚖️ (Equilibrium Point)"
                elif is_inside_bar:
                    return "Inside Bar Pattern - Compression Before Next Move 🔄 (Volatility Contraction)"
                elif support_resistance > 40 and support_resistance < 60:
                    return "Trading Between Support and Resistance - Balanced Structure ↔️ (Range-Bound Environment)"
                else:
                    return "Neutral Price Position - No Clear Structural Advantage ⚖️ (Waiting Pattern)"
                    
            elif score >= 35:
                if vwap_position < -0.1:
                    return "Price Below VWAP - Trading Below Value Area 📉 (Bearish Edge)"
                elif pivot_points and 'R1' in pivot_points:
                    return f"Price Near R1 Pivot Resistance - Technical Rejection Zone at {pivot_points['R1']:.2f} 📊 (Short Opportunity)"
                elif is_engulfing and market_structure < 40:
                    return "Bearish Engulfing Pattern Within Downtrend - Key Reversal Signal 🔄 (Trend Continuation Setup)"
                else:
                    return "Approaching Overhead Resistance - Historical Supply Zone 📉 (Technical Resistance Structure)"
                    
            else:
                if vwap_position < -0.5:
                    return f"Price Well Below VWAP - Strong Bearish Position Below Value Area 📉 (High-Probability Short Setup)"
                elif support_resistance < 20 and key_level_proximity > 80:
                    return "Trading At Major Resistance Zone - Heavy Selling Interest 🧱 (Strong Technical Ceiling)"
                elif market_structure < 20:
                    return "Lower Lows and Lower Highs - Textbook Bearish Structure 📉 (Strong Downtrend Confirmation)"
                else:
                    return "Weak Technical Position - Multiple Resistance Levels Aligned 🎯 (Strategic Short Entry Point)"
        
        # Default interpretations
        if score >= 80:
            return "Major Support Zone - High-Value Area 💪 (Strong Accumulation Base)"
        elif score >= 65:
            return "Established Support - Key Price Level 📈 (Historical Demand Zone)"
        elif score >= 55:
            return "Minor Support - Developing Structure ⬆️ (Early Formation)"
        elif score >= 45:
            return "Equilibrium Zone - Price Discovery Area ↔️ (Balance Point)"
        elif score >= 35:
            return "Minor Resistance - Overhead Supply ⬇️ (Selling Pressure Zone)"
        elif score >= 20:
            return "Established Resistance - Key Price Level 📉 (Historical Supply Zone)"
        else:
            return "Major Resistance Zone - Distribution Area ⚠️ (Strong Supply Level)"

    def _interpret_technical(self, score: float, indicators: Dict[str, Any] = None) -> str:
        """Interpret technical momentum with trend strength analysis.
        
        Args:
            score: Technical/momentum score (0-100)
            indicators: Optional indicator data for more sophisticated interpretation
            
        Returns:
            Detailed market interpretation
        """
        if indicators:
            # Extract relevant technical indicators
            rsi = indicators.get('rsi', 50)
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            macd_hist = indicators.get('macd_hist', 0)
            ao = indicators.get('ao', 0)
            stochastic = indicators.get('stoch_k', 50)
            ema_trend = indicators.get('ema_trend', 0)  # 1 for bullish alignment, -1 for bearish, 0 for mixed
            atr = indicators.get('atr', 0)
            bb_width = indicators.get('bb_width', 1)  # Bollinger Band width, higher means more volatility
            
            # Check for MACD crossover
            macd_crossover = (macd > macd_signal and macd_signal > 0) or (macd > 0 and macd_hist > 0)
            
            # Check for overbought/oversold conditions
            overbought = rsi > 70 or stochastic > 80
            oversold = rsi < 30 or stochastic < 20
            
            if score >= 80:
                if macd_crossover and rsi > 60 and not overbought:
                    return "Strong MACD Bullish Crossover with Rising RSI - Powerful Momentum Signal 🚀 (High Probability Uptrend)"
                elif ao > 0.5 and ema_trend > 0:
                    return "Awesome Oscillator Bullish with Aligned EMAs - Strong Trend Structure 📈 (Multiple Timeframe Confirmation)"
                elif oversold and macd_hist > 0:
                    return "Bullish Divergence From Oversold - Technical Spring Formation 🔄 (Strong Reversal Signal)"
                else:
                    return "Powerful Upward Momentum Across Multiple Indicators - Market Strength 🚀 (Confirmed Uptrend)"
                    
            elif score >= 65:
                if macd > 0 and rsi > 50:
                    return "Positive MACD with Bullish RSI - Healthy Momentum Development 📈 (Trending Market)"
                elif ema_trend > 0 and bb_width < 1.2:
                    return "Aligned EMAs with Narrowing Bollinger Bands - Controlled Momentum Growth 📊 (Low Volatility Uptrend)"
                else:
                    return "Bullish Momentum with Moderating Strength - Sustainable Trend 📈 (Higher Highs/Lows Formation)"
                    
            elif score >= 50:
                if abs(macd) < 0.1 and abs(rsi - 50) < 10:
                    return "Neutral MACD and RSI - Technical Equilibrium ⚖️ (Momentum Consolidation)"
                elif bb_width < 0.7:
                    return "Contracting Bollinger Bands - Low Volatility Compression 🔄 (Breakout Pending)"
                else:
                    return "Mixed Technical Signals - Balanced Momentum Indicators ↔️ (Sideways Pattern)"
                    
            elif score >= 35:
                if macd < 0 and rsi < 50:
                    return "Negative MACD with Bearish RSI - Deteriorating Momentum 📉 (Weakening Price Action)"
                elif ema_trend < 0 and bb_width < 1.2:
                    return "Bearish EMA Alignment with Narrowing Bollinger Bands - Controlled Downward Movement 📊 (Low Volatility Downtrend)"
                else:
                    return "Bearish Momentum Building - Early Trend Deterioration 📉 (Lower Highs Formation)"
                    
            else:
                if macd < 0 and macd < macd_signal and rsi < 40:
                    return "Strong MACD Bearish Crossover with Declining RSI - Powerful Momentum Breakdown 📉 (High Probability Downtrend)"
                elif ao < -0.5 and ema_trend < 0:
                    return "Awesome Oscillator Bearish with Aligned EMAs - Strong Downtrend Structure 📉 (Multiple Timeframe Confirmation)"
                elif overbought and macd_hist < 0:
                    return "Bearish Divergence From Overbought - Technical Exhaustion 🔄 (Strong Reversal Signal)"
                else:
                    return "Powerful Downward Momentum Across Multiple Indicators - Market Weakness 📉 (Confirmed Downtrend)"
        
        # Default interpretations
        if score >= 80:
            return "Powerful Upward Momentum - Strong Trend Force 🚀 (Breakout Phase)"
        elif score >= 65:
            return "Bullish Momentum - Trend Continuation 📈 (Higher Highs/Lows)"
        elif score >= 55:
            return "Rising Momentum - Early Trend Phase ⬆️ (Building Strength)"
        elif score >= 45:
            return "Neutral Momentum - Sideways Movement ↔️ (Consolidation)"
        elif score >= 35:
            return "Falling Momentum - Early Weakness ⬇️ (Losing Steam)"
        elif score >= 20:
            return "Bearish Momentum - Trend Continuation 📉 (Lower Highs/Lows)"
        else:
            return "Strong Downward Force - Accelerating Decline 💥 (Breakdown Phase)"

    def _interpret_sentiment(self, score: float, indicators: Dict[str, Any] = None) -> str:
        """Interpret sentiment with market psychology insights.
        
        Args:
            score: Sentiment score (0-100)
            indicators: Optional indicator data for more sophisticated interpretation
            
        Returns:
            Detailed market interpretation
        """
        if indicators:
            # Extract relevant sentiment indicators
            funding_rate = indicators.get('funding_rate', 0)  # Positive means longs pay shorts
            long_short_ratio = indicators.get('long_short_ratio', 1.0)  # >1 means more longs than shorts
            risk_score = indicators.get('risk_score', 50)
            fear_greed = indicators.get('fear_greed_index', 50)
            option_sentiment = indicators.get('option_put_call_ratio', 1.0)  # <1 means more calls than puts
            liquidations = indicators.get('liquidations', {})
            
            # Calculate liquidation imbalance if data is available
            liq_imbalance = 0
            if 'longs' in liquidations and 'shorts' in liquidations:
                longs = liquidations.get('longs', 0)
                shorts = liquidations.get('shorts', 0)
                total = max(longs + shorts, 1)
                liq_imbalance = (longs - shorts) / total  # -1 to 1, positive means more longs liquidated
            
            if score >= 80:
                if funding_rate < -0.01 and long_short_ratio > 1.5:
                    return "Negative Funding Rate Despite Long Bias - Contrarian Bullish Signal 🔄 (Shorts Paying Longs)"
                elif fear_greed < 30 and long_short_ratio > 1.0:
                    return "Extreme Fear With Accumulation - Strong Contrarian Buy Signal 💹 (Market Capitulation)"
                elif option_sentiment < 0.7:
                    return "Heavy Call Option Buying - Strong Bullish Conviction in Derivatives Market 📈 (Leveraged Upside Bets)"
                else:
                    return "Extremely Bullish Sentiment Metrics - Market Confidence Across Indicators 🚀 (FOMO Cycle Beginning)"
                    
            elif score >= 65:
                if funding_rate > 0 and long_short_ratio > 1.2:
                    return "Positive Funding With Healthy Long Interest - Sustainable Bullish Sentiment 📈 (Strong Hands Holding)"
                elif fear_greed > 40 and fear_greed < 60:
                    return "Balanced Fear/Greed With Bullish Bias - Rational Optimism 📊 (Healthy Market Psychology)"
                else:
                    return "Confidently Bullish Without Euphoria - Positive Market Outlook 📈 (Constructive Sentiment)"
                    
            elif score >= 50:
                if abs(funding_rate) < 0.005:
                    return "Neutral Funding Rate - Balanced Derivatives Positioning ⚖️ (No Overcrowding)"
                elif abs(liq_imbalance) < 0.1:
                    return "Balanced Liquidations - No Capitulation On Either Side ⚖️ (Stable Market Positioning)"
                else:
                    return "Neutral Market Sentiment - Mixed Signals Without Clear Bias ↔️ (Wait And See Approach)"
                    
            elif score >= 35:
                if funding_rate < 0 and long_short_ratio < 0.8:
                    return "Negative Funding With Bearish Positioning - Cautious Market Approach 📉 (Risk-Off Sentiment)"
                elif fear_greed > 60:
                    return "Elevated Greed Index - Early Warning Sign of Complacency ⚠️ (Potential Overextension)"
                else:
                    return "Mildly Bearish Sentiment Metrics - Growing Market Concerns 📉 (Defensive Positioning)"
                    
            else:
                if funding_rate > 0.01 and long_short_ratio < 0.7:
                    return "Positive Funding Rate Despite Short Bias - Contrarian Bearish Signal 🔄 (Longs Paying Shorts)"
                elif fear_greed > 70 and long_short_ratio < 1.0:
                    return "Extreme Greed With Distribution - Strong Contrarian Sell Signal 📉 (Market Euphoria)"
                elif option_sentiment > 1.5:
                    return "Heavy Put Option Buying - Strong Bearish Conviction in Derivatives Market 📉 (Leveraged Downside Protection)"
                else:
                    return "Extremely Bearish Sentiment Metrics - Market Fear Dominant Across Indicators 📉 (Capitulation Phase)"
        
        # Default interpretations
        if score >= 80:
            return "Extremely Bullish - Strong Market Confidence 🚀 (FOMO Phase)"
        elif score >= 65:
            return "Confidently Bullish - Positive Expectations 📈 (Uptrend Bias)"
        elif score >= 55:
            return "Mildly Bullish - Cautious Optimism ⬆️ (Building Confidence)"
        elif score >= 45:
            return "Market Equilibrium - Mixed Sentiment ⚖️ (Wait and See)"
        elif score >= 35:
            return "Mildly Bearish - Growing Concerns ⬇️ (Risk-Off Bias)"
        elif score >= 20:
            return "Confidently Bearish - Negative Outlook 📉 (Risk Aversion)"
        else:
            return "Extremely Bearish - Market Fear Dominant 💥 (Capitulation Risk)"

    async def generate_signals(self, market_data: Dict[str, Any], analysis: Dict[str, Any], symbol: str = None) -> List[Dict[str, Any]]:
        """Generate trading signals based on market data and analysis.
        
        Args:
            market_data: Dictionary containing market data
            analysis: Dictionary containing analysis results
            symbol: Optional symbol override
            
        Returns:
            List of signal dictionaries
        """
        try:
            self.logger.info("🚨 SIGNAL GENERATOR: === Generating Signals ===")
            self.logger.debug(f"🚨 SIGNAL GENERATOR: Input - Market Data Keys: {market_data.keys()}")
            self.logger.debug(f"🚨 SIGNAL GENERATOR: Input - Analysis Keys: {analysis.keys()}")
            
            # Get symbol from market data or use override
            symbol = symbol or market_data.get('symbol', 'UNKNOWN')
            self.logger.info(f"🚨 SIGNAL GENERATOR: Generating signals for {symbol}")
            
            # Get processor instance
            processor = await self.processor
            
            # Process raw data
            processed_data = await processor.process(market_data)
            self.logger.info(f"🚨 SIGNAL GENERATOR: Processed market data for {symbol}")
            
            # Calculate all indicator scores
            self.logger.info(f"🚨 SIGNAL GENERATOR: Calculating indicator scores for {symbol}")
            indicators = {
                'momentum': await self.technical_indicators.calculate(processed_data),
                'volume': await self.volume_indicators.calculate(processed_data),
                'orderflow': await self.orderflow_indicators.calculate(processed_data),
                'orderbook': await self.orderbook_indicators.calculate(processed_data),
                'price_structure': await self.price_structure_indicators.calculate(processed_data),
                'sentiment': await self.sentiment_indicators.calculate(processed_data)
            }
            self.logger.info(f"🚨 SIGNAL GENERATOR: Completed indicator calculations for {symbol}")
            
            # Combine all indicators
            combined_indicators = {
                'symbol': symbol,
                'timestamp': datetime.utcnow(),
                'current_price': processed_data.get('price', 0),
                'volume_24h': processed_data.get('volume_24h', 0),
                'funding_rate': processed_data.get('funding_rate', 0),
                'volatility': processed_data.get('volatility', 0),
                'timeframe': processed_data.get('timeframe', '1m'),
                'session': processed_data.get('session', 'unknown'),
                'market_type': processed_data.get('market_type', 'unknown'),
                'volatility_regime': processed_data.get('volatility_regime', 'unknown'),
            }
            
            # Add individual scores
            for category, scores in indicators.items():
                combined_indicators.update({
                    f"{category}_score": scores.get('score', 50.0),
                    **{f"{category}_{k}": v for k, v in scores.items() if k != 'score'}
                })
            
            # Generate final signal
            self.logger.info(f"🚨 SIGNAL GENERATOR: Generating final signal for {symbol}")
            signal_result = await self.generate_signal(combined_indicators)
            
            if signal_result:
                self.logger.info(f"🚨 SIGNAL GENERATOR: Generated {signal_result.get('signal', 'UNKNOWN')} signal for {symbol} with score {signal_result.get('score', 0):.2f}")
                
                # Check alert manager
                if not self.alert_manager:
                    self.logger.error(f"🚨 SIGNAL GENERATOR: Alert manager not available for {symbol} - alerts won't be sent")
                else:
                    self.logger.info(f"🚨 SIGNAL GENERATOR: Alert manager available with handlers: {self.alert_manager.handlers if hasattr(self.alert_manager, 'handlers') else 'No handlers'}")
            else:
                self.logger.info(f"🚨 SIGNAL GENERATOR: No signal generated for {symbol}")
            
            # Print signal summary
            try:
                self._print_signal_summary(signal_result)
            except Exception as e:
                logger.error(f"Error printing signal summary: {str(e)}")
                logger.debug(traceback.format_exc())
            
            return [signal_result]
            
        except Exception as e:
            logger.error(f"🚨 SIGNAL GENERATOR: Error generating signals: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Failed to generate signals: {str(e)}") from e

    def _print_signal_summary(self, result: Dict[str, Any]) -> None:
        """Print formatted signal summary.
        
        Args:
            result: Dictionary containing signal result data
            
        Raises:
            ValueError: If result is missing required fields
        """
        if not isinstance(result, dict):
            raise ValueError("Result must be a dictionary")
            
        indicators = result.get('indicators', {})
        if not indicators:
            raise ValueError("Result missing indicators data")
            
        symbol = result['symbol']
        current_price = result['entry_price']
        confluence_score = result['confluence_score']
        signal = result['signal']
        stop_loss = result['stop_loss']
        
        # Determine price format
        price_format = ",.2f" if symbol.startswith(('BTC', 'ETH')) else ",.6f"
        
        print(f"\n=== Signal Alert for {symbol} ===")
        print(f"Current Price: ${current_price:{price_format}}")
        print(f"Timestamp: {indicators.get('timestamp')}")
        print("\n=== Analysis Scores ===")
        print("┌─────────────────────┬────────────┐")
        print("│ Indicator           │     Score  │")
        print("├─────────────────────┼────────────┤")
        print(f"│ 📈 Technical       │  {indicators.get('momentum_score', 0):>8.2f} │")
        print(f"│ 📶 Volume          │  {indicators.get('volume_score', 0):>8.2f} │")
        print(f"│ 💹 Orderflow       │  {indicators.get('orderflow_score', 0):>8.2f} │")
        print(f"│ 📖 Orderbook       │  {indicators.get('orderbook_score', 0):>8.2f} │")
        print(f"│ 📊 Price Structure │  {indicators.get('position_score', 0):>8.2f} │")
        print(f"│ 💭 Sentiment       │  {indicators.get('sentiment_score', 0):>8.2f} │")
        print("├─────────────────────┼────────────┤")
        print(f"│ 🎯 Confluence Score │  {confluence_score:>8.2f} │")
        print("└─────────────────────┴────────────┘")
        
        print(f"\nSignal: {signal}")

        print("\n=== Trade Setup ===")
        print(f"Entry Price: ${current_price:{price_format}}")
        print(f"Stop Loss: ${stop_loss:{price_format}}")
        
        if indicators.get('volume_24h'):
            volume_usd = indicators.get('volume_24h', 0) * current_price
            print(f"24h Volume: ${volume_usd:,.2f}")
        if indicators.get('funding_rate'):
            print(f"Funding Rate: {indicators.get('funding_rate', 0):.6%}")
        print("\n")

    async def process_signal(self, signal_data: Dict[str, Any]) -> None:
        """Process trading signals and send alerts if thresholds are met.
        This method is the central entry point for handling signals from the monitoring system.
        """
        try:
            # CRITICAL DEBUG: Log entry into process_signal
            self.logger.critical(f"CRITICAL DEBUG: SignalGenerator.process_signal called for {signal_data.get('symbol', 'UNKNOWN')}")
            self.logger.critical(f"CRITICAL DEBUG: Signal data keys: {list(signal_data.keys())}")
            
            # Validate signal data
            validation_result = await self._validate_signal_data(signal_data)
            self.logger.critical(f"CRITICAL DEBUG: Signal data validation result: {validation_result}")
            
            if not validation_result:
                self.logger.critical(f"CRITICAL DEBUG: Signal data validation FAILED - signal will not be processed")
                return
            
            symbol = signal_data.get('symbol', 'UNKNOWN')
            score = signal_data.get('confluence_score', 0)
            components = signal_data.get('components', {})
            results = signal_data.get('results', signal_data.get('metadata', {}))
            reliability = signal_data.get('reliability', 0.8)
            
            # CRITICAL DEBUG: Log the alert manager state
            if self.alert_manager:
                self.logger.critical(f"CRITICAL DEBUG: AlertManager is available in SignalGenerator")
                if hasattr(self.alert_manager, 'handlers'):
                    self.logger.critical(f"CRITICAL DEBUG: AlertManager handlers: {self.alert_manager.handlers}")
                else:
                    self.logger.critical(f"CRITICAL DEBUG: AlertManager has no handlers attribute")
                    
                # Check webhook URL
                if hasattr(self.alert_manager, 'discord_webhook_url'):
                    webhook_url = self.alert_manager.discord_webhook_url
                    if webhook_url:
                        self.logger.critical(f"CRITICAL DEBUG: Discord webhook URL is set: {webhook_url[:20]}...{webhook_url[-10:]}")
                    else:
                        self.logger.critical(f"CRITICAL DEBUG: Discord webhook URL is NOT SET")
                else:
                    self.logger.critical(f"CRITICAL DEBUG: AlertManager has no discord_webhook_url attribute")
            else:
                self.logger.critical(f"CRITICAL DEBUG: NO AlertManager available in SignalGenerator")
            
            # Pass thresholds from config to signal data for consistency
            signal_data['buy_threshold'] = self.thresholds['buy']
            signal_data['sell_threshold'] = self.thresholds['sell']
            
            # Mark the signal as being processed by SignalGenerator to avoid duplicate processing
            signal_data['processed_by'] = 'SignalGenerator'
            
            # Generate a content hash for this signal
            signal_data['content_hash'] = f"{symbol}_{'BUY' if score >= self.thresholds['buy'] else 'SELL' if score <= self.thresholds['sell'] else 'NEUTRAL'}_{int(score)}"
            
            # Set a proper signal type for better logging and deduplication
            if score >= self.thresholds['buy']:
                signal_data['signal'] = 'BUY'
            elif score <= self.thresholds['sell']:
                signal_data['signal'] = 'SELL'
            else:
                signal_data['signal'] = 'NEUTRAL'
            
            # CRITICAL DEBUG: Log signal classification
            self.logger.critical(f"CRITICAL DEBUG: Classified signal as {signal_data['signal']} with score {score:.2f} (thresholds: buy={self.thresholds['buy']}, sell={self.thresholds['sell']})")
            
            # Log signal details
            self.logger.info(f"Processing {symbol} signal with score {score:.2f} (thresholds: buy={self.thresholds['buy']}, sell={self.thresholds['sell']})")
            
            # Process signal based on thresholds
            if score >= self.thresholds['buy'] or score <= self.thresholds['sell']:
                signal_type = 'BUY' if score >= self.thresholds['buy'] else 'SELL'
                self.logger.info(f"Generated {signal_type} signal for {symbol} with score {score:.2f} (threshold: {self.thresholds['buy'] if signal_type == 'BUY' else self.thresholds['sell']})")
                
                # CRITICAL DEBUG: Log before attempting to send alert
                self.logger.critical(f"CRITICAL DEBUG: About to send confluence alert for {symbol} with score {score:.2f}")
                
                # Send via alert manager if available
                if self.alert_manager:
                    self.logger.debug(f"ALERT DEBUG: Attempting to send confluence alert for {symbol} with score {score:.2f}")
                    try:
                        # CRITICAL DEBUG: Verify alert_manager has the method
                        if hasattr(self.alert_manager, 'send_confluence_alert'):
                            self.logger.critical(f"CRITICAL DEBUG: alert_manager.send_confluence_alert method exists")
                        else:
                            self.logger.critical(f"CRITICAL DEBUG: alert_manager.send_confluence_alert method DOES NOT EXIST!")
                            
                        # Attempt to force handler registration before sending alert
                        if hasattr(self.alert_manager, 'handlers') and not self.alert_manager.handlers:
                            self.logger.critical(f"CRITICAL DEBUG: No handlers registered in alert_manager - attempting to register discord handler")
                            if hasattr(self.alert_manager, 'register_handler'):
                                self.alert_manager.register_handler('discord')
                                self.logger.critical(f"CRITICAL DEBUG: After force registration: {self.alert_manager.handlers}")
                            else:
                                self.logger.critical(f"CRITICAL DEBUG: alert_manager has no register_handler method")
                        
                        # Actually send the alert
                        self.logger.critical(f"CRITICAL DEBUG: Calling alert_manager.send_confluence_alert NOW")
                        await self.alert_manager.send_confluence_alert(
                            symbol=symbol,
                            confluence_score=score,
                            components=components,
                            results=results,
                            reliability=reliability,
                            buy_threshold=self.thresholds['buy'],
                            sell_threshold=self.thresholds['sell']
                        )
                        self.logger.critical(f"CRITICAL DEBUG: alert_manager.send_confluence_alert call completed successfully")
                    except Exception as e:
                        self.logger.critical(f"CRITICAL DEBUG: Error sending confluence alert: {str(e)}")
                        self.logger.critical(traceback.format_exc())
                        
                        # CRITICAL DEBUG: Try alternative alert methods
                        self.logger.critical(f"CRITICAL DEBUG: Attempting alternative alert methods")
                        
                        # Try direct send_alert method
                        try:
                            if hasattr(self.alert_manager, 'send_alert'):
                                self.logger.critical(f"CRITICAL DEBUG: Trying alert_manager.send_alert as fallback")
                                await self.alert_manager.send_alert(
                                    level="INFO",
                                    message=f"🚨 {signal_type} SIGNAL: {symbol} with score {score:.2f}/100",
                                    details=signal_data
                                )
                                self.logger.critical(f"CRITICAL DEBUG: alert_manager.send_alert completed successfully")
                            else:
                                self.logger.critical(f"CRITICAL DEBUG: alert_manager has no send_alert method")
                        except Exception as e2:
                            self.logger.critical(f"CRITICAL DEBUG: Error in fallback send_alert: {str(e2)}")
                else:
                    self.logger.critical(f"CRITICAL DEBUG: AlertManager not properly initialized - can't send alert for {symbol}")
            else:
                self.logger.info(f"Signal for {symbol} with score {score:.2f} doesn't meet thresholds - no alert sent")
                
        except Exception as e:
            self.logger.critical(f"CRITICAL DEBUG: Error processing signal: {str(e)}")
            self.logger.critical(traceback.format_exc())
