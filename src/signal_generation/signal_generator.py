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
from src.core.reporting.report_manager import ReportManager
import os
from dotenv import load_dotenv
import json
from src.utils.serializers import serialize_for_json, prepare_data_for_transmission
from src.utils.data_utils import resolve_price, format_price_string
from src.models.schema import SignalData, SignalType
import uuid
from uuid import uuid4
from pydantic import ValidationError

logger = logging.getLogger(__name__)

class SignalGenerator:
    """Generates trading signals based on analysis results."""
    
    def __init__(self, config: Dict[str, Any], alert_manager: Optional[AlertManager] = None):
        """Initialize signal generator with configuration settings.
        
        Args:
            config: Configuration dictionary
            alert_manager: Optional alert manager for notifications
        """
        self.config = config
        self.alert_manager = alert_manager
        self.logger = logging.getLogger(__name__ + ".SignalGenerator")

        # Custom signal handler for external integrations
        self._on_signal_callback = None
        
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
        
        # Initialize ReportManager for PDF generation
        self.report_manager = None
        # Only create if reporting is enabled in config
        reporting_config = config.get('reporting', {})
        if reporting_config.get('enabled', False):
            try:
                self.report_manager = ReportManager(config)
                self.logger.info("ReportManager initialized for PDF generation")
            except Exception as e:
                self.logger.error(f"Failed to initialize ReportManager: {str(e)}")
                self.logger.debug(traceback.format_exc())
        
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

    @property
    def on_signal(self):
        """Get the current signal callback handler."""
        return self._on_signal_callback
    
    @on_signal.setter
    def on_signal(self, callback):
        """Set a callback to be called when signals are generated.
        
        Args:
            callback: Async function that takes a signal_data dict as parameter
        """
        self._on_signal_callback = callback
        self.logger.info(f"Signal callback registered: {callback.__name__ if hasattr(callback, '__name__') else str(callback)}")

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

    def _save_signal_to_json(self, signal_data: Dict[str, Any]) -> Optional[str]:
        """
        Save signal data to a JSON file for debugging and auditing purposes.
        
        Args:
            signal_data: The signal data to save
            
        Returns:
            Optional[str]: Path to the saved JSON file if successful, None otherwise
        """
        try:
            # Create exports directory if it doesn't exist
            exports_dir = os.path.join(os.getcwd(), 'exports', 'signal_data')
            os.makedirs(exports_dir, exist_ok=True)
            
            # Create a filename with timestamp and symbol
            symbol = signal_data.get('symbol', 'UNKNOWN')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{symbol}_signal_{timestamp}.json"
            filepath = os.path.join(exports_dir, filename)
            
            # Use the centralized serializer to prepare data for JSON
            json_ready_data = prepare_data_for_transmission(signal_data)
            
            # Write to file with pretty formatting
            with open(filepath, 'w') as f:
                json.dump(json_ready_data, f, indent=2, default=str)
            
            self.logger.info(f"Saved signal data to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving signal data to JSON: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return None

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
                
                # Save signal data to JSON for debugging and auditing
                json_path = self._save_signal_to_json(signal_result)
                if json_path:
                    signal_result['json_path'] = json_path
                
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
                'symbol': symbol,
                'confluence_score': score,
                'components': serialized_components,
                'results': serialized_results,
                'reliability': reliability,  # Use reliability directly without normalization
                'buy_threshold': self.thresholds['buy'],
                'sell_threshold': self.thresholds['sell'],
                'price': price,
                'transaction_id': transaction_id,
                'signal_id': signal_id
            }
            
            # Add enhanced formatted data to alert if available
            if enhanced_data:
                alert_data.update(enhanced_data)
            
            # Add PDF path if available for attachment
            files = None
            if pdf_path and os.path.exists(pdf_path):
                files = [{
                    'path': pdf_path,
                    'filename': os.path.basename(pdf_path),
                    'description': f"Report for {symbol}"
                }]
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Adding PDF attachment: {pdf_path}")
            
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Calling alert_manager.send_confluence_alert")
            
            # Add diagnostic logging to check alert data before sending
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] ALERT DATA CHECK - Preparing to send alert:")
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] - Confluence score: {score}")
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] - Influential components count: {len(enhanced_data.get('influential_components', []))}")
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] - Market interpretations count: {len(enhanced_data.get('market_interpretations', []))}")
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] - Top weighted subcomponents count: {len(enhanced_data.get('top_weighted_subcomponents', []))}")
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] - Actionable insights count: {len(enhanced_data.get('actionable_insights', []))}")
            
            # Check market interpretations format
            market_interpretations = enhanced_data.get('market_interpretations', [])
            if market_interpretations:
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] - Sample market interpretation: {market_interpretations[0]}")
            
            # Pass top_weighted_subcomponents to the alert manager
            await self.alert_manager.send_confluence_alert(
                symbol=symbol,
                confluence_score=score,  # This is validated_data.score
                components=serialized_components,
                results=serialized_results,
                reliability=reliability,  # Use reliability directly without normalization
                buy_threshold=self.thresholds['buy'],
                sell_threshold=self.thresholds['sell'],
                price=price,
                transaction_id=transaction_id,
                signal_id=signal_id,
                influential_components=enhanced_data.get('influential_components'),
                market_interpretations=enhanced_data.get('market_interpretations'),
                actionable_insights=enhanced_data.get('actionable_insights'),
                top_weighted_subcomponents=enhanced_data.get('top_weighted_subcomponents')
            )
            
            # If we have files to attach but couldn't attach them directly through send_confluence_alert,
            # send them separately through the send_discord_webhook_message method
            if files and hasattr(self.alert_manager, 'send_discord_webhook_message'):
                webhook_message = {
                    'content': f"📑 PDF report for {symbol} {direction} signal",
                    'username': "Virtuoso Reports"
                }
                await self.alert_manager.send_discord_webhook_message(webhook_message, files=files)
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] PDF report sent as separate message")
            
            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Alert sent successfully for {symbol}")
        except Exception as e:
            self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error sending confluence alert: {str(e)}")
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] {traceback.format_exc()}")
            
            # Try direct send_alert method as fallback
            try:
                if hasattr(self.alert_manager, 'send_alert'):
                    self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Using fallback alert method for {symbol}")
                    fallback_message = f"{direction} SIGNAL: {symbol} with score {score:.2f}/100"
                    
                    # Add transaction info to details
                    standardized_data['transaction_id'] = transaction_id
                    standardized_data['signal_id'] = signal_id
                    
                    await self.alert_manager.send_alert(
                        level="INFO",
                        message=fallback_message,
                        details=standardized_data
                    )
                    self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Fallback alert sent for {symbol}")
            except Exception as e2:
                self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error in fallback alert: {str(e2)}")
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Fallback error traceback: {traceback.format_exc()}")
        except Exception as e:
            self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error processing signal: {str(e)}")
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] {traceback.format_exc()}")

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
            
            return [signal_result]
            
        except Exception as e:
            logger.error(f"🚨 SIGNAL GENERATOR: Error generating signals: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Failed to generate signals: {str(e)}") from e

    async def process_signal(self, signal_data: Dict[str, Any]) -> None:
        """
        Process a trading signal and send alerts.
        
        This method standardizes and validates the signal data, performs post-processing,
        and dispatches the signal to the appropriate handlers (alerts, database, etc).
        
        Args:
            signal_data: Dictionary containing the signal data
        """
        try:
            # Generate unique ID for this signal
            signal_id = str(uuid4())[:8]
            transaction_id = signal_data.get('transaction_id', 'unknown')
            
            self.logger.info(f"[TXN:{transaction_id}] Starting signal processing with signal_id={signal_id}")
            
            # Debug log received signal data keys
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Received signal data keys: {list(signal_data.keys())}")
            
            # Standardize field names
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Standardizing signal data")
            standardized_data = self._standardize_signal_data(signal_data)
            
            # Validate signal data with Pydantic model
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Validating with Pydantic model")
            try:
                validated_data = SignalData(**standardized_data)
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Signal data validated for {validated_data.symbol}")
            except ValidationError as e:
                self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Validation error: {str(e)}")
                raise
            
            # Extract key data for processing
            symbol = validated_data.symbol
            score = validated_data.score
            price = validated_data.price
            components = validated_data.components
            reliability = validated_data.reliability  # Use the validated reliability
            
            # Extract results data from signal_data
            results = signal_data.get('results', {})
            
            # If results is empty but we have a 'debug' field with raw component results, use that
            if not results and 'debug' in signal_data and 'results' in signal_data['debug']:
                results = signal_data['debug']['results']
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Using results from debug.results field")
                
            # Determine signal direction
            direction = signal_data.get('direction', 'NEUTRAL').upper()
            if score >= self.thresholds['buy']:
                direction = "BUY"
            elif score <= self.thresholds['sell']:
                direction = "SELL"
            else:
                # Default to direction from signal data or leave as NEUTRAL
                pass
                
            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Processing {direction} signal for {symbol} with score {score}")
            standardized_data['signal'] = direction  # Update signal with final direction

            # Get components 
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Components: {list(components.keys())}")
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Results: {list(results.keys() if isinstance(results, dict) else [])}")
            
            # Generate PDF report if possible
            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Generating PDF report for {symbol}")
            pdf_path = None
            json_path = None
            
            try:
                # Try to get OHLCV data for the symbol
                ohlcv_data = await self._fetch_ohlcv_data(symbol)
                
                if ohlcv_data is not None:
                    # Generate report with OHLCV data
                    try:
                        # Get the coroutine result
                        result = await self.report_manager.generate_and_attach_report(
                            signal_data={
                                'symbol': symbol,
                                'score': score,
                                'signal_type': direction,
                                'price': price,
                                'components': components,
                                'results': results,
                                'reliability': reliability
                            },
                            ohlcv_data=ohlcv_data
                        )
                        
                        # Check if we need to await again (double-awaiting pattern)
                        if asyncio.iscoroutine(result):
                            result = await result
                        
                        # Initialize default values
                        success = False
                        pdf_path = None
                        json_path = None
                        
                        # Safely extract tuple values if available
                        if isinstance(result, tuple):
                            if len(result) >= 1:
                                success = result[0]
                            if len(result) >= 2:
                                pdf_path = result[1]
                            if len(result) >= 3:
                                json_path = result[2]
                        
                        # Check if PDF was generated successfully
                        if success and pdf_path and os.path.exists(pdf_path):
                            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] PDF report generated at {pdf_path}")
                        else:
                            self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}] PDF report generation failed or not found")
                            pdf_path = None
                    except Exception as e:
                        self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error generating PDF report: {str(e)}")
                        self.logger.debug(traceback.format_exc())
                        success = False
                        pdf_path = None
                        json_path = None
                else:
                    self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}] No OHLCV data found for {symbol}")
                    
                    # Generate report without OHLCV data
                    try:
                        # Get the coroutine result
                        result = await self.report_manager.generate_and_attach_report(
                            signal_data={
                                'symbol': symbol,
                                'score': score,
                                'signal_type': direction,
                                'price': price,
                                'components': components,
                                'results': results,
                                'reliability': reliability
                            }
                        )
                        
                        # Check if we need to await again (double-awaiting pattern)
                        if asyncio.iscoroutine(result):
                            result = await result
                        
                        # Initialize default values
                        success = False
                        pdf_path = None
                        json_path = None
                        
                        # Safely extract tuple values if available
                        if isinstance(result, tuple):
                            if len(result) >= 1:
                                success = result[0]
                            if len(result) >= 2:
                                pdf_path = result[1]
                            if len(result) >= 3:
                                json_path = result[2]
                        
                        # Check if PDF was generated successfully
                        if success and pdf_path and os.path.exists(pdf_path):
                            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] PDF report generated at {pdf_path}")
                        else:
                            self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}] PDF report generation failed or not found")
                            pdf_path = None
                    except Exception as e:
                        self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error generating PDF report: {str(e)}")
                        self.logger.debug(traceback.format_exc())
                        success = False
                        pdf_path = None
                        json_path = None
            except Exception as e:
                self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error generating PDF report: {str(e)}")
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] {traceback.format_exc()}")

            # Send signal alert
            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Sending confluence alert for {symbol}")
            
            # Serialize data for alert sending to avoid JSON serialization issues
            try:
                # Prepare data for transmission
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Serializing data for alert")
                serialized_components = serialize_for_json(components)
                serialized_results = serialize_for_json(results)
                
                # Generate enhanced formatted data for the signal
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Generating enhanced formatted data")
                enhanced_data = self._generate_enhanced_formatted_data(
                    symbol, 
                    score, 
                    serialized_components, 
                    serialized_results, 
                    reliability,
                    self.thresholds['buy'],
                    self.thresholds['sell']
                )
                
                # Store the enhanced data in standardized_data
                if enhanced_data:
                    standardized_data.update(enhanced_data)
                    self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Enhanced data added to signal")
                
                # Add transaction ID for tracing
                alert_data = {
                    'symbol': symbol,
                    'confluence_score': score,
                    'components': serialized_components,
                    'results': serialized_results,
                    'reliability': reliability if reliability <= 1 else reliability / 100.0,  # Normalize to 0-1 range
                    'buy_threshold': self.thresholds['buy'],
                    'sell_threshold': self.thresholds['sell'],
                    'price': price,
                    'transaction_id': transaction_id,
                    'signal_id': signal_id
                }
                
                # Add enhanced formatted data to alert if available
                if enhanced_data:
                    alert_data.update(enhanced_data)
                
                # Add PDF path if available for attachment
                files = None
                if pdf_path and os.path.exists(pdf_path):
                    files = [{
                        'path': pdf_path,
                        'filename': os.path.basename(pdf_path),
                        'description': f"Report for {symbol}"
                    }]
                    self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Adding PDF attachment: {pdf_path}")
                
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Calling alert_manager.send_confluence_alert")
                
                # Add diagnostic logging to check alert data before sending
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] ALERT DATA CHECK - Preparing to send alert:")
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] - Confluence score: {score}")
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] - Influential components count: {len(enhanced_data.get('influential_components', []))}")
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] - Market interpretations count: {len(enhanced_data.get('market_interpretations', []))}")
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] - Top weighted subcomponents count: {len(enhanced_data.get('top_weighted_subcomponents', []))}")
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] - Actionable insights count: {len(enhanced_data.get('actionable_insights', []))}")
                
                # Check market interpretations format
                market_interpretations = enhanced_data.get('market_interpretations', [])
                if market_interpretations:
                    self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] - Sample market interpretation: {market_interpretations[0]}")
                
                # Pass top_weighted_subcomponents to the alert manager
                await self.alert_manager.send_confluence_alert(
                    symbol=symbol,
                    confluence_score=score,  # This is validated_data.score
                    components=serialized_components,
                    results=serialized_results,
                    reliability=reliability,  # Use reliability directly without normalization
                    buy_threshold=self.thresholds['buy'],
                    sell_threshold=self.thresholds['sell'],
                    price=price,
                    transaction_id=transaction_id,
                    signal_id=signal_id,
                    influential_components=enhanced_data.get('influential_components'),
                    market_interpretations=enhanced_data.get('market_interpretations'),
                    actionable_insights=enhanced_data.get('actionable_insights'),
                    top_weighted_subcomponents=enhanced_data.get('top_weighted_subcomponents')
                )
                
                # If we have files to attach but couldn't attach them directly through send_confluence_alert,
                # send them separately through the send_discord_webhook_message method
                if files and hasattr(self.alert_manager, 'send_discord_webhook_message'):
                    webhook_message = {
                        'content': f"📑 PDF report for {symbol} {direction} signal",
                        'username': "Virtuoso Reports"
                    }
                    await self.alert_manager.send_discord_webhook_message(webhook_message, files=files)
                    self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] PDF report sent as separate message")
                
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Alert sent successfully for {symbol}")
            except Exception as e:
                self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error sending confluence alert: {str(e)}")
                self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] {traceback.format_exc()}")
                
                # Try direct send_alert method as fallback
                try:
                    if hasattr(self.alert_manager, 'send_alert'):
                        self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Using fallback alert method for {symbol}")
                        fallback_message = f"{direction} SIGNAL: {symbol} with score {score:.2f}/100"
                        
                        # Add transaction info to details
                        standardized_data['transaction_id'] = transaction_id
                        standardized_data['signal_id'] = signal_id
                        
                        await self.alert_manager.send_alert(
                            level="INFO",
                            message=fallback_message,
                            details=standardized_data
                        )
                        self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Fallback alert sent for {symbol}")
                except Exception as e2:
                    self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error in fallback alert: {str(e2)}")
                    self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Fallback error traceback: {traceback.format_exc()}")
            
            # Send to registered callback if available
            if self._on_signal_callback:
                try:
                    self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Notifying external callback")
                    await self._on_signal_callback(standardized_data)
                except Exception as e:
                    self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error in signal callback: {str(e)}")
                    self.logger.debug(traceback.format_exc())
        except Exception as e:
            self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error processing signal: {str(e)}")
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] {traceback.format_exc()}")

    def _standardize_signal_data(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize signal data field names to ensure consistency.
        Normalizes various field naming conventions from different sources.
        
        Args:
            signal_data: Raw signal data with potentially inconsistent field names
            
        Returns:
            Dict with standardized field names
        """
        standardized = signal_data.copy()
        
        # Score field standardization
        if 'confluence_score' in standardized and 'score' not in standardized:
            standardized['score'] = standardized['confluence_score']
        elif 'score' in standardized and 'confluence_score' not in standardized:
            standardized['confluence_score'] = standardized['score']
        elif 'score' not in standardized and 'confluence_score' not in standardized:
            # Default score if both missing
            standardized['score'] = 50.0
            standardized['confluence_score'] = 50.0
        
        # Always ensure both score fields are set to the same value
        if 'score' in standardized and 'confluence_score' in standardized:
            # Use score as the canonical value
            standardized['confluence_score'] = standardized['score']
        
        # Technical/momentum score standardization
        if 'technical_score' in standardized and 'momentum_score' not in standardized:
            standardized['momentum_score'] = standardized['technical_score']
        elif 'momentum_score' in standardized and 'technical_score' not in standardized:
            standardized['technical_score'] = standardized['momentum_score']
            
        # Position/price structure score standardization
        if 'position_score' in standardized and 'price_structure_score' not in standardized:
            standardized['price_structure_score'] = standardized['position_score']
        elif 'price_structure_score' in standardized and 'position_score' not in standardized:
            standardized['position_score'] = standardized['price_structure_score']
            
        # Direction/signal standardization
        if 'direction' in standardized:
            direction = standardized['direction'].upper()
            if direction in ['BUY', 'SELL', 'NEUTRAL'] and 'signal' not in standardized:
                standardized['signal'] = direction
        
        # Ensure components dictionary exists
        if 'components' not in standardized:
            standardized['components'] = {}
            # Try to build components from individual scores
            component_keys = [
                ('technical_score', 'technical'), 
                ('momentum_score', 'technical'),
                ('volume_score', 'volume'),
                ('orderflow_score', 'orderflow'),
                ('orderbook_score', 'orderbook'),
                ('sentiment_score', 'sentiment'),
                ('price_structure_score', 'price_structure'),
                ('position_score', 'price_structure')
            ]
            
            for source_key, target_key in component_keys:
                if source_key in standardized and standardized.get(source_key) is not None:
                    standardized['components'][target_key] = standardized[source_key]
        
        return standardized

    def _resolve_price(self, signal_data: Dict[str, Any], signal_id: str) -> float:
        """
        Resolve price using the centralized utility function.
        
        Args:
            signal_data: Signal data dictionary
            signal_id: Logging identifier for tracing
            
        Returns:
            Resolved price value or None if not available
        """
        symbol = signal_data.get('symbol', 'UNKNOWN')
        price = resolve_price(signal_data, symbol)
        
        if price is not None:
            self.logger.info(f"[{signal_id}] Resolved price for {symbol}: {price}")
            return price
        else:
            self.logger.warning(f"[{signal_id}] Failed to resolve price for {symbol}")
            return None

    def _calculate_reliability(self, signal_data: Dict[str, Any]) -> float:
        """Calculate reliability based on various factors.
        
        Calculates reliability score (0-100) based on:
        1. Component agreement (standard deviation of scores)
        2. Data quality
        3. Signal strength
        
        Returns:
            float: Reliability score between 0 and 100
        """
        try:
            # Get component scores
            components = signal_data.get('components', {})
            if not components:
                self.logger.warning("No components found for reliability calculation")
                return 100.0  # Default to full reliability if no components
                
            # Calculate standard deviation of scores
            values = list(components.values())
            if not values:
                self.logger.warning("No component values found for reliability calculation")
                return 100.0
                
            std_dev = np.std(values)
            
            # Calculate base reliability from standard deviation
            # Lower std_dev = higher reliability
            # Max std_dev considered is 50 (gives 0% reliability)
            base_reliability = max(0.0, 100.0 - (std_dev * 2))
            
            # Get signal strength based on deviation from neutral
            score = signal_data.get('score', 50.0)
            deviation = abs(score - 50.0)
            signal_strength = min(100.0, (deviation / 30.0) * 100)
            
            # Calculate final reliability
            # Weight the components:
            # - Base reliability (component agreement): 70%
            # - Signal strength: 30%
            final_reliability = (base_reliability * 0.7) + (signal_strength * 0.3)
            
            # Ensure result is in 0-100 range
            final_reliability = max(0.0, min(100.0, final_reliability))
            
            self.logger.debug(f"Calculated reliability: {final_reliability:.2f}% (base: {base_reliability:.2f}%, strength: {signal_strength:.2f}%)")
            
            return final_reliability
            
        except Exception as e:
            self.logger.error(f"Error calculating reliability: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return 100.0  # Default to full reliability on error

    async def _fetch_ohlcv_data(self, symbol: str, timeframe: str = '1h', limit: int = 50) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data for a symbol to use in PDF reports.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Chart timeframe (default: 1h)
            limit: Number of candles to fetch
            
        Returns:
            DataFrame with OHLCV data or None if error
        """
        try:
            self.logger.debug(f"Fetching OHLCV data for {symbol} ({timeframe}, {limit} candles)")
            
            # Get the processor instance
            processor = await self.processor
            
            # Fetch OHLCV data
            ohlcv_data = await processor.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit
            )
            
            if ohlcv_data is None or len(ohlcv_data) == 0:
                self.logger.warning(f"No OHLCV data found for {symbol}")
                return None
                
            self.logger.debug(f"Retrieved {len(ohlcv_data)} OHLCV candles for {symbol}")
            return ohlcv_data
            
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV data for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return None

    def _generate_enhanced_formatted_data(
        self, 
        symbol: str, 
        confluence_score: float, 
        components: Dict[str, float], 
        results: Dict[str, Any],
        reliability: float,
        buy_threshold: float,
        sell_threshold: float
    ) -> Dict[str, Any]:
        """Generate enhanced formatted data for signal display.
        
        This method extracts detailed component information and creates
        rich, formatted data structures for displaying in alerts.
        
        Args:
            symbol: The trading symbol
            confluence_score: The overall score
            components: Component scores
            results: Detailed results
            reliability: Reliability score
            buy_threshold: Buy threshold
            sell_threshold: Sell threshold
            
        Returns:
            Dict containing enhanced formatted data
        """
        self.logger.debug(f"Generating enhanced formatted data for {symbol}")
        enhanced_data = {}
        
        try:
            # Normalize component weights if provided
            weights = {}
            total_weight = 0
            
            # Build weights dict based on component names
            for comp_name in components:
                # Default weight is 1 for each component
                weights[comp_name] = 1
                total_weight += 1
                
            # Normalize weights to sum to 1
            weights = {k: v/total_weight for k, v in weights.items()}
            
            # Use the normalized weights
            self.logger.debug(f"Component weights: {weights}")
            
            # Process main components
            main_components = []
            self.logger.debug(f"Processing {len(components)} main components")
            
            for component_name, component_score in components.items():
                # Calculate weighted impact
                weighted_impact = component_score * weights.get(component_name, 0)
                
                # Format main component
                main_component = {
                    'name': component_name,
                    'display_name': component_name.replace('_', ' ').title(),
                    'score': component_score,
                    'is_main': True,
                    'weight': weights.get(component_name, 0)
                }
                
                # Look for sub-components for this component in results
                sub_components = []
                if component_name in results:
                    # Extract components field from results
                    component_data = results[component_name]
                    
                    if isinstance(component_data, dict) and 'components' in component_data:
                        sub_comp_data = component_data.get('components', {})
                        self.logger.debug(f"Found {len(sub_comp_data)} subcomponents in results for {component_name}")
                        
                        # Process each sub-component
                        for sub_name, sub_score in sub_comp_data.items():
                            if isinstance(sub_score, (int, float)) and not pd.isna(sub_score):
                                # Determine direction indicator
                                indicator = '→'  # Default neutral
                                if sub_score >= 70:
                                    indicator = '↑'  # Bullish
                                elif sub_score <= 30:
                                    indicator = '↓'  # Bearish
                                    
                                # Calculate this subcomponent's weighted impact on overall score
                                # Formula: (sub_score * parent_weight) / number of subs
                                parent_weight = weights.get(component_name, 0)
                                sub_count = len(sub_comp_data)
                                weighted_sub_impact = 0
                                if sub_count > 0:
                                    weighted_sub_impact = sub_score * parent_weight
                                
                                # Safeguard: Cap weighted_impact to 1.0 (100%) to prevent inflated values
                                weighted_sub_impact = min(weighted_sub_impact, 1.0)
                                
                                # Add to sub-components list
                                sub_component = {
                                    'name': sub_name,
                                    'display_name': sub_name.replace('_', ' ').title(),
                                    'score': sub_score,
                                    'indicator': indicator,
                                    'is_main': False,
                                    'parent': component_name,
                                    'parent_display_name': component_name.replace('_', ' ').title(),
                                    'parent_weight': parent_weight,
                                    'weighted_impact': weighted_sub_impact
                                }
                                sub_components.append(sub_component)
                
                # Add sub-components to this main component
                main_component['sub_components'] = sub_components
                main_components.append(main_component)
                
            # Generate detailed component breakdown
            influential_components = sorted(main_components, key=lambda x: x['weight'], reverse=True)
            enhanced_data['influential_components'] = influential_components
            self.logger.debug(f"Generated detailed component breakdown with {len(influential_components)} components")
            
            # Generate top weighted sub-components by impact
            all_sub_components = []
            for main_comp in main_components:
                all_sub_components.extend(main_comp.get('sub_components', []))
                
            # Sort by weighted impact
            sorted_sub_components = sorted(all_sub_components, key=lambda x: x.get('weighted_impact', 0), reverse=True)
            enhanced_data['top_weighted_subcomponents'] = sorted_sub_components[:10]  # Top 10
            self.logger.debug(f"Generated top {len(enhanced_data['top_weighted_subcomponents'])} weighted sub-components by impact")
            
            # Get main components sorted by score for interpretation generation
            sorted_main_components = sorted([(c['name'], c['score']) for c in main_components], key=lambda x: x[1], reverse=True)
            
            # Get market interpretations
            try:
                # Extract interpretations from results
                market_interpretations = []
                
                # Log the results for debugging
                self.logger.debug(f"Extracting interpretations from {len(results)} result components")
                
                # Extract interpretations from individual component results
                for component_name, component_data in results.items():
                    self.logger.debug(f"Processing component {component_name} for interpretations: {type(component_data)}")
                    if not isinstance(component_data, dict):
                        self.logger.debug(f"Skipping non-dict component data for {component_name}: {type(component_data)}")
                        continue
                        
                    # First, check if there's a direct interpretation field
                    if 'interpretation' in component_data:
                        interpretation_text = component_data['interpretation']
                        self.logger.debug(f"Found interpretation for {component_name}: {type(interpretation_text)}")
                        
                        # Format interpretation object
                        interpretation_obj = {
                            'component': component_name,
                            'display_name': component_name.replace('_', ' ').title(),
                            'interpretation': interpretation_text
                        }
                        
                        market_interpretations.append(interpretation_obj)
                    
                    # Alternatively check for interpretations in signals or in a nested structure
                    elif 'signals' in component_data:
                        signals = component_data['signals']
                        self.logger.debug(f"Checking signals for {component_name}: {type(signals)}")
                        
                        # Special case for sentiment which has an 'interpretation' directly
                        if component_name == 'sentiment' and isinstance(signals, dict) and 'interpretation' in signals:
                            interp_data = signals['interpretation']
                            self.logger.debug(f"Found sentiment interpretation: {type(interp_data)}")
                            
                            # Create interpretation object
                            interpretation_obj = {
                                'component': component_name,
                                'display_name': component_name.replace('_', ' ').title(),
                                'interpretation': interp_data
                            }
                            
                            market_interpretations.append(interpretation_obj)
                            continue
                        
                        # Extract interpretation data from signals
                        if isinstance(signals, dict) and 'interpretation' in signals:
                            interp_data = signals['interpretation']
                            
                            # Extract message if available or use fallback
                            if isinstance(interp_data, dict) and 'message' in interp_data:
                                interpretation_text = interp_data['message']
                            else:
                                interpretation_text = str(interp_data)
                            
                            # Format interpretation object
                            interpretation_obj = {
                                'component': component_name,
                                'display_name': component_name.replace('_', ' ').title(),
                                'interpretation': interpretation_text
                            }
                            
                            market_interpretations.append(interpretation_obj)
                    
                    # Check for sentiment-specific format
                    elif component_name == 'sentiment' and 'interpretation' in component_data:
                        interp_data = component_data['interpretation']
                        self.logger.debug(f"Found sentiment interpretation (special case): {type(interp_data)}")
                        
                        # Create interpretation object
                        interpretation_obj = {
                            'component': component_name,
                            'display_name': component_name.replace('_', ' ').title(),
                            'interpretation': interp_data
                        }
                        
                        market_interpretations.append(interpretation_obj)
                    
                # Sort interpretations by component priority
                component_priority = {
                    'orderflow': 1,
                    'technical': 2,
                    'sentiment': 3,
                    'orderbook': 4,
                    'price_structure': 5,
                    'volume': 6
                }
                
                market_interpretations.sort(key=lambda x: component_priority.get(x['component'], 99))
                            
                # If we still don't have interpretations, add fallbacks
                if not market_interpretations:
                    self.logger.debug(f"No interpretations found, adding defaults")
                    
                    # Create default interpretations based on component scores
                    for comp_name, comp_score in sorted_main_components[:3]:
                        # Skip components with NaN scores
                        if pd.isna(comp_score):
                            continue
                        
                        # Generate default interpretation text
                        if comp_score >= 70:
                            strength = "Strong bullish signal"
                        elif comp_score >= 60:
                            strength = "Moderately bullish"
                        elif comp_score >= 45:
                            strength = "Neutral with slight bullish bias"
                        elif comp_score >= 35:
                            strength = "Neutral with slight bearish bias"
                        elif comp_score >= 25:
                            strength = "Moderately bearish"
                        else:
                            strength = "Strong bearish signal"
                            
                        default_interp = {
                            'component': comp_name,
                            'display_name': comp_name.replace('_', ' ').title(),
                            'interpretation': f"{strength} with score {comp_score:.1f}"
                        }
                        
                        market_interpretations.append(default_interp)
                        self.logger.debug(f"Added default interpretation for {comp_name}")
                
                # Add to enhanced data
                enhanced_data['market_interpretations'] = market_interpretations
                self.logger.debug(f"Generated {len(market_interpretations)} market interpretations")
                
                # Generate actionable insights
                # Basic trading insights based on score
                actionable_insights = []
                
                # Add directional bias insight
                if confluence_score >= buy_threshold + 5:
                    actionable_insights.append(f"BUY BIAS: Score ({confluence_score:.2f}) above buy threshold - consider long entries")
                elif confluence_score >= buy_threshold:
                    actionable_insights.append(f"NEUTRAL-BULLISH BIAS: Score ({confluence_score:.2f}) approaching buy threshold - monitor for confirmation")
                elif confluence_score <= sell_threshold - 5:
                    actionable_insights.append(f"SELL BIAS: Score ({confluence_score:.2f}) below sell threshold - consider short entries")
                elif confluence_score <= sell_threshold:
                    actionable_insights.append(f"NEUTRAL-BEARISH BIAS: Score ({confluence_score:.2f}) approaching sell threshold - monitor for confirmation")
                else:
                    actionable_insights.append(f"NEUTRAL BIAS: Score ({confluence_score:.2f}) suggests ranging conditions - avoid directional bias")
                
                # Add risk assessment based on reliability and volatility
                if reliability >= 0.9:
                    if 'sentiment' in components and components.get('sentiment', 50) > 65:
                        actionable_insights.append("RISK ASSESSMENT: LOW - Market conditions favorable for standard position sizing")
                    else:
                        actionable_insights.append("RISK ASSESSMENT: MODERATE - Use standard position sizing with defined risk parameters")
                elif reliability >= 0.7:
                    actionable_insights.append("RISK ASSESSMENT: MODERATE - Use standard position sizing with defined risk parameters")
                else:
                    actionable_insights.append("RISK ASSESSMENT: HIGH - Reduce position size despite bullish bias and use tighter stops")
                
                # Add timing insight based on momentum and orderflow
                if 'technical' in components and components.get('technical', 50) > 65:
                    actionable_insights.append("TIMING: Strong directional momentum; favorable for trend-following entries")
                elif 'orderflow' in components and components.get('orderflow', 50) > 65:
                    actionable_insights.append("TIMING: Strong directional momentum; favorable for trend-following entries")
                elif 'technical' in components and components.get('technical', 50) > 55:
                    actionable_insights.append("TIMING: Moderate momentum; consider entry on pullbacks/breakouts")
                else:
                    actionable_insights.append("TIMING: Declining sell pressure; potential for reversal")
                
                # Add to enhanced data
                enhanced_data['actionable_insights'] = actionable_insights
                self.logger.debug(f"Generated {len(actionable_insights)} actionable insights")
                
            except Exception as e:
                self.logger.error(f"Error generating interpretations: {str(e)}")
                self.logger.debug(f"Traceback: {traceback.format_exc()}")
                
        except Exception as e:
            self.logger.error(f"Error generating enhanced formatted data: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
        
        return enhanced_data
