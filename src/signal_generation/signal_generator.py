"""
Signal Generator Module - Trading Signal Generation System

This module implements the core signal generation system for the Virtuoso Trading
Platform, converting confluence analysis results into actionable trading signals.

The SignalGenerator processes confluence scores from market analysis and generates
buy/sell/neutral signals based on configurable thresholds. It integrates with the
alert system to notify users of trading opportunities in real-time.

Key Features:
- Threshold-based signal generation with configurable parameters
- Multi-timeframe signal aggregation and validation
- Signal strength calculation based on score deviation
- Integration with alert management for notifications
- Support for custom signal callbacks for external systems
- Comprehensive signal metadata including confidence levels

Signal Generation Logic:
1. Receives confluence scores from MarketMonitor (0-100 scale)
2. Evaluates scores against configurable thresholds:
   - Long Signal: Score > long_threshold (default 60)
   - Short Signal: Score < short_threshold (default 40)
   - Neutral: Score between thresholds with buffer zone
3. Calculates signal strength based on score distance from threshold
4. Validates signals across multiple timeframes for confirmation
5. Sends alerts through AlertManager when conditions are met
6. Stores signal history for performance tracking

Performance Characteristics:
- Time Complexity: O(1) for signal evaluation
- Space Complexity: O(n) for signal history storage
- Average Processing Time: <10ms per signal
- Alert Latency: <100ms from signal to notification

Configuration:
- Thresholds defined in config.yaml under analysis.confluence_thresholds
- Weights for different indicators in confluence.weights.components
- Alert filters and rate limiting in alerts configuration

Usage Example:
    generator = SignalGenerator(config, alert_manager)
    signal = await generator.generate_signal(analysis_result)
    if signal['type'] == 'LONG':
        await execute_trade(signal)

Author: Virtuoso Team
Version: 2.0.0
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
# Import AlertManager type for annotation only, not the actual class
from typing import TYPE_CHECKING
if TYPE_CHECKING:
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
from src.core.analysis.interpretation_generator import InterpretationGenerator
from src.core.interpretation.interpretation_manager import InterpretationManager
from src.monitoring.quality_metrics_tracker import QualityMetricsTracker

logger = logging.getLogger(__name__)

class SignalGenerator:
    """Generates trading signals based on analysis results."""
    
    def __init__(self, config: Dict[str, Any], alert_manager: Optional['AlertManager'] = None, market_data_manager=None):
        """Initialize signal generator with configuration settings.
        
        Args:
            config: Configuration dictionary
            alert_manager: Optional alert manager for notifications
            market_data_manager: Optional market data manager for OHLCV access
        """
        self.config = config
        self.alert_manager = alert_manager
        self.market_data_manager = market_data_manager
        self.logger = logging.getLogger(__name__ + ".SignalGenerator")

        # Custom signal handler for external integrations
        self._on_signal_callback = None
        
        # Load thresholds from config
        confluence_config = config.get('confluence', {})
        threshold_config = confluence_config.get('thresholds', {})
        
        # Set thresholds with defaults matching config.yaml defaults
        self.thresholds = {
            'long': float(threshold_config.get('long', threshold_config.get('buy', 60))),
            'short': float(threshold_config.get('short', threshold_config.get('sell', 40))),
            'neutral_buffer': float(threshold_config.get('neutral_buffer', 5))
        }
        
        # self.logger.debug(f"Loaded signal thresholds from config: {self.thresholds}")  # Disabled verbose config dump
        
        # Debug initialization
        self.logger.debug("Initializing SignalGenerator")  # Removed verbose config dump
        
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
        
        # logger.debug(f"Initialized SignalGenerator with config: {config}")  # Disabled verbose config dump
        
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
        
        # Initialize AlertManager if not provided
        if alert_manager:
            self.alert_manager = alert_manager
        else:
            try:
                # Import AlertManager here to avoid circular import
                from src.monitoring.alert_manager import AlertManager
                self.alert_manager = AlertManager(config)
                self.logger.info("Created new AlertManager instance")
                
                # Ensure Discord handler is registered
                if hasattr(self.alert_manager, 'register_discord_handler'):
                    self.alert_manager.register_discord_handler()
                    self.logger.info("Discord handler registered with AlertManager")
            except Exception as e:
                self.logger.error(f"Failed to initialize AlertManager: {str(e)}")
                self.logger.debug(traceback.format_exc())
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
        
        # Initialize InterpretationGenerator for market interpretations
        self.interpretation_generator = InterpretationGenerator()
        self.logger.info("InterpretationGenerator initialized for market analysis")
        
        # Initialize centralized InterpretationManager
        self.interpretation_manager = InterpretationManager()
        self.logger.info("Centralized InterpretationManager initialized")

        # Initialize quality metrics tracker
        self.quality_tracker = QualityMetricsTracker()
        self.logger.info("QualityMetricsTracker initialized for signal quality monitoring")

        # Verify AlertManager initialization
        if self.alert_manager and hasattr(self.alert_manager, 'discord_webhook_url') and self.alert_manager.discord_webhook_url:
            self.logger.info(f"✅ AlertManager initialized with Discord webhook URL")
            if hasattr(self.alert_manager, 'alert_handlers'):
                self.logger.info(f"✅ Registered handlers: {list(self.alert_manager.alert_handlers.keys())}")
            elif hasattr(self.alert_manager, 'handlers'):
                self.logger.info(f"✅ Registered handlers: {self.alert_manager.handlers}")
        else:
            # More detailed diagnostic information
            if not self.alert_manager:
                self.logger.warning("⚠️  WARNING: AlertManager is None")
            elif not hasattr(self.alert_manager, 'discord_webhook_url'):
                self.logger.warning("⚠️  WARNING: AlertManager missing discord_webhook_url attribute")
            elif not self.alert_manager.discord_webhook_url:
                self.logger.warning("⚠️  WARNING: AlertManager discord_webhook_url is empty")
            else:
                self.logger.warning("⚠️  WARNING: AlertManager not properly initialized")
        
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
            
            # Pass market_data_manager if available
            if hasattr(self, 'market_data_manager') and self.market_data_manager:
                self._processor.market_data_manager = self.market_data_manager
                self.logger.debug("✅ DEBUG: Passed market_data_manager to DataProcessor")
            
            # Pass monitor if available for direct cache access
            if hasattr(self, 'monitor') and self.monitor:
                self._processor.monitor = self.monitor
                self.logger.debug("✅ DEBUG: Passed monitor to DataProcessor")
                
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
                    if direction == 'LONG':
                        indicators['signal'] = 'LONG'
                    elif direction == 'SHORT':
                        indicators['signal'] = 'SHORT'
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
        """
        Generate trading signals based on indicator values and confluence scores.
        
        This method evaluates market indicators against configured thresholds to
        generate buy, sell, or neutral trading signals with associated metadata.
        
        Args:
            indicators: Dictionary containing analysis results:
                - 'symbol': str - Trading pair (e.g., 'BTC/USDT')
                - 'current_price': float - Current market price
                - 'confluence': float - Overall confluence score (0-100)
                - 'momentum_score': float - Momentum indicator score
                - 'volume_score': float - Volume analysis score
                - 'orderflow_score': float - Order flow imbalance score
                - 'orderbook_score': float - Order book depth score
                - 'sentiment_score': float - Market sentiment score
                - 'price_structure_score': float - Support/resistance score
                - 'futures_premium_score': float - Futures basis score
                - 'timeframe': str - Analysis timeframe
                - 'timestamp': int - Analysis timestamp
                
        Returns:
            Dict[str, Any]: Signal data containing:
                - 'id': str - Unique signal identifier (UUID)
                - 'type': str - Signal type ('LONG', 'SHORT', 'NEUTRAL')
                - 'symbol': str - Trading pair
                - 'price': float - Signal generation price
                - 'confluence_score': float - Overall score (0-100)
                - 'strength': float - Signal strength (0-1)
                - 'confidence': float - Confidence level (0-1)
                - 'component_scores': Dict - Individual component scores
                - 'timestamp': int - Signal generation timestamp
                - 'timeframe': str - Signal timeframe
                - 'recommendation': str - Human-readable recommendation
                - 'risk_level': str - Risk assessment ('LOW', 'MEDIUM', 'HIGH')
                - 'metadata': Dict - Additional signal metadata
                
        Signal Logic:
            - LONG: confluence_score > long_threshold (default 60)
            - SHORT: confluence_score < short_threshold (default 40)
            - NEUTRAL: score between thresholds or within buffer zone
            
        Signal Strength Calculation:
            - Distance from threshold normalized to 0-1 scale
            - Further from threshold = stronger signal
            - Maximum strength at scores 0 or 100
            
        Example:
            >>> indicators = {
            ...     'symbol': 'BTC/USDT',
            ...     'current_price': 50000,
            ...     'confluence': 75,
            ...     'momentum_score': 80,
            ...     'volume_score': 70
            ... }
            >>> signal = await generator.generate_signal(indicators)
            >>> print(f"Signal: {signal['type']} with strength {signal['strength']}")
            Signal: LONG with strength 0.75
        """
        try:
            # Get confluence score and current price from indicators
            symbol = indicators.get('symbol', 'UNKNOWN')
            current_price = indicators.get('current_price', 0.0)
            
            # Extract individual component scores first
            component_scores = {
                'momentum': indicators.get('momentum_score', 50.0),
                'volume': indicators.get('volume_score', 50.0),
                'orderflow': indicators.get('orderflow_score', 50.0),
                'orderbook': indicators.get('orderbook_score', 50.0),
                'sentiment': indicators.get('sentiment_score', 50.0),
                'price_structure': indicators.get('price_structure_score', 50.0),
                'futures_premium': indicators.get('futures_premium_score', 50.0)  # Add futures premium
            }
            
            # Calculate confluence score if not provided
            confluence_score = indicators.get('confluence', indicators.get('score', 0.0))
            if confluence_score == 0.0:
                # Calculate weighted confluence score from individual components
                weights = self.confluence_weights
                
                # Fallback to equal weights if no weights configured
                if not weights:
                    weights = {
                        'momentum': 1.0,
                        'volume': 1.0, 
                        'orderflow': 1.0,
                        'orderbook': 1.0,
                        'sentiment': 1.0,
                        'price_structure': 1.0
                    }
                    logger.debug(f"Using default equal weights for confluence calculation")
                
                # Calculate weighted average
                total_weight = 0
                weighted_sum = 0
                for comp, weight in weights.items():
                    if comp in component_scores:
                        weighted_sum += component_scores[comp] * weight
                        total_weight += weight
                
                if total_weight > 0:
                    confluence_score = weighted_sum / total_weight
                else:
                    confluence_score = sum(component_scores.values()) / len(component_scores)
                
                logger.info(f"Calculated confluence score for {symbol}: {confluence_score:.2f} from components: {component_scores}")
                logger.debug(f"Used weights: {weights}")
            
            logger.debug(f"Received data for {symbol}:")
            logger.debug(f"Raw indicators: {indicators}")
            logger.debug(f"Extracted score: {confluence_score}")

            # Use thresholds from the self.thresholds dictionary loaded during initialization
            long_threshold = self.thresholds['long']
            short_threshold = self.thresholds['short']
            
            logger.debug(f"Signal check for {symbol}:")
            logger.debug(f"Confluence score: {confluence_score}")
            logger.debug(f"Long threshold: {long_threshold}")
            logger.debug(f"Short threshold: {short_threshold}")

            # ═══════════════════════════════════════════════════════════════════
            # QUALITY METRICS MONITORING (HYBRID APPROACH)
            # ═══════════════════════════════════════════════════════════════════
            # Extract quality metrics from indicators for monitoring and logging
            # Note: With hybrid approach, quality is integrated into confluence_score
            # No separate filtering needed - weak signals automatically score low
            consensus = indicators.get('consensus', None)
            confidence = indicators.get('confidence', None)
            disagreement = indicators.get('disagreement', None)
            score_base = indicators.get('score_base', None)
            quality_impact = indicators.get('quality_impact', None)

            # Log quality metrics for monitoring (no filtering, just visibility)
            if confidence is not None:
                logger.info(f"[QUALITY METRICS] {symbol}")
                logger.info(f"  Adjusted Score: {confluence_score:.2f} (used for trading decisions)")
                if score_base is not None:
                    logger.info(f"  Base Score: {score_base:.2f} (before quality adjustment)")
                if quality_impact is not None:
                    logger.info(f"  Quality Impact: {quality_impact:+.2f} points ({'suppressed' if quality_impact < 0 else 'amplified'})")
                logger.info(f"  Confidence: {confidence:.3f} | Consensus: {consensus:.3f if consensus else 'N/A'} | "
                          f"Disagreement: {disagreement:.4f if disagreement else 'N/A'}")

                # Interpretation hint
                if quality_impact is not None and quality_impact < -5:
                    logger.info(f"  → Signal significantly suppressed by low quality")
                elif quality_impact is not None and abs(quality_impact) < 2:
                    logger.info(f"  → High quality signal, minimal adjustment")
            # ═══════════════════════════════════════════════════════════════════

            signal = None  # Initialize signal as None
            alerts_sent = False  # Track if alerts were sent

            # Extract component scores for the formatted alert (use calculated scores)
            components = {
                'volume': component_scores['volume'],
                'technical': component_scores['momentum'],  # Use momentum for technical
                'orderflow': component_scores['orderflow'],
                'orderbook': component_scores['orderbook'],
                'sentiment': component_scores['sentiment'],
                'price_structure': component_scores['price_structure'],
                'futures_premium': indicators.get('futures_premium_score', 50.0)  # Add futures premium
            }
            
            # Prepare results object with detailed interpretations for each component
            results = {}

            # Extract full indicator results if available
            full_results = indicators.get('results', {})

            for component_name, component_score in components.items():
                # Get the appropriate interpretation method based on component name
                # Use InterpretationGenerator instead of local interpretation methods

                try:
                    # CRITICAL FIX: Extract full indicator data from results instead of creating empty dicts
                    # Map component names to their corresponding indicator keys
                    indicator_key_map = {
                        'technical': 'technical',
                        'momentum': 'technical',  # Momentum is mapped to technical
                        'volume': 'volume',
                        'orderflow': 'orderflow',
                        'orderbook': 'orderbook',
                        'sentiment': 'sentiment',
                        'price_structure': 'price_structure',
                        'futures_premium': 'futures_premium'
                    }

                    indicator_key = indicator_key_map.get(component_name, component_name)
                    full_indicator_data = full_results.get(indicator_key, {})

                    # DEBUG: Log what data we're extracting
                    if component_name in ['orderbook', 'sentiment', 'price_structure']:
                        self.logger.info(f"[COMPONENT-DATA] {component_name}: full_indicator_data keys = {list(full_indicator_data.keys()) if isinstance(full_indicator_data, dict) else 'NOT A DICT'}")
                        if isinstance(full_indicator_data, dict):
                            has_signals = bool(full_indicator_data.get('signals'))
                            has_components = bool(full_indicator_data.get('components'))
                            has_metadata = bool(full_indicator_data.get('metadata'))
                            self.logger.info(f"[COMPONENT-DATA] {component_name}: has_signals={has_signals}, has_components={has_components}, has_metadata={has_metadata}")
                            if has_components:
                                comp_keys = list(full_indicator_data.get('components', {}).keys())[:5]
                                self.logger.info(f"[COMPONENT-DATA] {component_name}: component keys = {comp_keys}")

                    # Extract rich data from the full indicator results
                    component_data = {
                        'score': component_score,
                        'signals': full_indicator_data.get('signals', {}),
                        'components': full_indicator_data.get('components', {}),
                        'metadata': full_indicator_data.get('metadata', {'raw_values': indicators})
                    }

                    # If no rich data found, try legacy extract methods as fallback
                    if not component_data['components']:
                        extract_method = getattr(self, f"_extract_{component_name}_components", None)
                        if extract_method:
                            sub_components = extract_method(indicators)
                            component_data['components'] = sub_components

                    # CRITICAL FIX: Use interpretation from indicator if available, otherwise generate new one
                    if 'interpretation' in full_indicator_data and full_indicator_data['interpretation']:
                        # Use the interpretation that the indicator already generated
                        interpretation = full_indicator_data['interpretation']
                        self.logger.debug(f"Using pre-generated interpretation for {component_name}: {interpretation[:100]}")
                    else:
                        # Generate interpretation if indicator didn't provide one
                        interpretation = self.interpretation_generator.get_component_interpretation(
                            component_name, component_data
                        )
                        self.logger.debug(f"Generated new interpretation for {component_name}: {interpretation[:100]}")
                    
                    raw_interpretations.append({
                        'component': component_name,
                        'display_name': component_name.replace('_', ' ').title(),
                        'interpretation': interpretation
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Error generating interpretation for {component_name}: {str(e)}")
                    # Fallback to simple interpretation
                    if component_name == 'futures_premium':
                        # Special handling for futures premium
                        if component_score > 70:
                            interpretation = f"Strong Contango - Score: {component_score:.1f} - Futures trading at significant premium to spot"
                        elif component_score > 55:
                            interpretation = f"Contango - Score: {component_score:.1f} - Futures trading above spot prices"
                        elif component_score < 30:
                            interpretation = f"Strong Backwardation - Score: {component_score:.1f} - Futures trading at significant discount to spot"
                        elif component_score < 45:
                            interpretation = f"Backwardation - Score: {component_score:.1f} - Futures trading below spot prices"
                        else:
                            interpretation = f"Neutral Premium - Score: {component_score:.1f} - Balanced futures-spot relationship"
                    else:
                        interpretation = f"Score: {component_score:.1f} - {'Bullish' if component_score > 50 else 'Bearish'} bias"
                
                # Create component entry with full interpretation text
                results[component_name] = {
                    'score': component_score,
                    'components': sub_components,
                    'interpretation': interpretation
                }
            
            # Generate signals based on configured thresholds
            if confluence_score >= long_threshold:
                logger.info(f"Generating LONG signal - Score {confluence_score} >= {long_threshold}")
                signal = "LONG"
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
                
            elif confluence_score <= short_threshold:
                logger.info(f"Generating SHORT signal - Score {confluence_score} <= {short_threshold}")
                signal = "SHORT"
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
                
                # Check for futures premium alerts
                await self._check_futures_premium_alerts(indicators, symbol)

                # Log quality metrics for passed signals
                if consensus is not None or confidence is not None or disagreement is not None:
                    self.quality_tracker.log_quality_metrics(
                        symbol=symbol,
                        confluence_score=confluence_score,
                        consensus=consensus if consensus is not None else 0.0,
                        confidence=confidence if confidence is not None else 0.0,
                        disagreement=disagreement if disagreement is not None else 0.0,
                        signal_type=signal,
                        signal_filtered=False
                    )

                # Let the AlertManager handle all alerts in a centralized way
                # to avoid duplication
                return signal_result
            return None

        except Exception as e:
            logger.error(f"Error generating signal: {str(e)}")
            raise RuntimeError(f"Failed to generate signal: {str(e)}") from e

    async def _send_signal_alert(self, signal: Dict[str, Any], indicators: Dict[str, Any]) -> None:
        """Send a signal alert to the alert manager."""
        try:
            # Extract signal ID or create a new one
            transaction_id = signal.get('transaction_id', str(uuid.uuid4())[:8])
            signal_id = signal.get('signal_id', str(uuid.uuid4())[:8])
            
            # Extract call tracking information
            call_source = indicators.get('call_source', 'UNKNOWN_SOURCE')
            call_id = indicators.get('call_id', 'UNKNOWN_CALL')
            cycle_call_source = indicators.get('cycle_call_source', 'UNKNOWN_CYCLE')
            cycle_call_id = indicators.get('cycle_call_id', 'UNKNOWN_CYCLE_CALL')
            
            # CALL SOURCE TRACKING: Log alert sending with full call chain
            symbol = signal.get('symbol', 'UNKNOWN')
            self.logger.info(f"[CALL_TRACKING][ALERT_SEND][{call_source}→{cycle_call_source}][CALL_ID:{call_id}→{cycle_call_id}][TXN:{transaction_id}][SIG:{signal_id}] Sending alert for {symbol}")
            
            # Get price from signal data or try to resolve it
            price = signal.get('price')
            if price is None:
                price = self._resolve_price(signal, signal_id)
            
            # Extract key signal properties
            symbol = signal.get('symbol', 'UNKNOWN')
            score = signal.get('score', 50.0)
            components = signal.get('components', {})
            results = signal.get('results', {})
            standardized_data = self._standardize_signal_data(signal)
            
            # Calculate reliability factor (0-1)
            reliability = self._calculate_reliability(signal)
            
            # Generate enhanced formatted data for improved alerts
            enhanced_data = self._generate_enhanced_formatted_data(
                symbol=symbol,
                confluence_score=score,
                components=components,
                results=results,
                reliability=reliability,
                long_threshold=self.thresholds['long'],
                short_threshold=self.thresholds['short']
            )
            
            # Determine signal direction
            if score >= self.thresholds['long']:
                direction = 'LONG'
            elif score <= self.thresholds['short']:
                direction = 'SHORT'
            else:
                direction = 'NEUTRAL'
            
            # Skip processing if the signal is NEUTRAL or reliability is less than 100%
            if direction == 'NEUTRAL':
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Skipping alert for NEUTRAL signal on {symbol}")
                return
                
            # Check if reliability is less than 100% (1.0), if so, skip alert
            if reliability < 1.0:
                self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Skipping alert for {symbol} due to reliability {reliability*100:.1f}% < 100%")
                return
            
            # Note: PDF generation is handled internally by AlertManager.send_confluence_alert()
            # No need for separate PDF handling here as AlertManager generates and sends PDFs automatically
            self.logger.info(f"[DIAGNOSTICS] [PDF_GENERATION] [TXN:{transaction_id}][SIG:{signal_id}] PDF generation will be handled by AlertManager for {symbol}")
            
            # Fetch OHLCV data for chart generation
            ohlcv_data = None
            try:
                if self.market_data_manager:
                    self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Fetching OHLCV data for chart generation")
                    # Fetch recent OHLCV data (e.g., last 100 candles for 5m timeframe)
                    ohlcv_data = await self.market_data_manager.fetch_ohlcv(
                        symbol=symbol,
                        timeframe='5m',
                        limit=100
                    )
                    if ohlcv_data is not None and not ohlcv_data.empty:
                        self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Successfully fetched {len(ohlcv_data)} OHLCV candles")
                    else:
                        self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}] OHLCV data is empty or None")
                else:
                    self.logger.warning(f"[TXN:{transaction_id}][SIG:{signal_id}] market_data_manager not available for OHLCV fetch")
            except Exception as e:
                self.logger.error(f"[TXN:{transaction_id}][SIG:{signal_id}] Error fetching OHLCV data: {str(e)}")
                # Continue without OHLCV data - signal will still be sent but without chart

            # Create alert data for the alert manager
            alert_data = {
                'symbol': symbol,
                'confluence_score': score,
                'components': components,
                'results': results,
                'reliability': reliability,  # Use reliability directly without normalization
                'long_threshold': self.thresholds['long'],
                'short_threshold': self.thresholds['short'],
                'price': price,
                'transaction_id': transaction_id,
                'signal_id': signal_id,
                'ohlcv_data': ohlcv_data  # Add OHLCV data for chart generation
            }
            
            # Add enhanced formatted data to alert if available
            if enhanced_data:
                alert_data.update(enhanced_data)
            
            # PDF attachments are handled automatically by AlertManager.send_confluence_alert()
            # No need for manual PDF attachment logic here
            
            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Calling alert_manager.send_confluence_alert")
            
            # Add diagnostic logging to check alert data before sending
            self.logger.info(f"[DIAGNOSTICS] [ALERT_DATA] [TXN:{transaction_id}][SIG:{signal_id}] Preparing to send alert:")
            self.logger.info(f"[DIAGNOSTICS] [ALERT_DATA] [TXN:{transaction_id}][SIG:{signal_id}] - Confluence score: {score}")
            self.logger.info(f"[DIAGNOSTICS] [ALERT_DATA] [TXN:{transaction_id}][SIG:{signal_id}] - PDF generation: Handled by AlertManager")
            
            if enhanced_data:
                self.logger.info(f"[DIAGNOSTICS] [ALERT_DATA] [TXN:{transaction_id}][SIG:{signal_id}] - Influential components count: {len(enhanced_data.get('influential_components', []))}")
                self.logger.info(f"[DIAGNOSTICS] [ALERT_DATA] [TXN:{transaction_id}][SIG:{signal_id}] - Market interpretations count: {len(enhanced_data.get('market_interpretations', []))}")
                self.logger.info(f"[DIAGNOSTICS] [ALERT_DATA] [TXN:{transaction_id}][SIG:{signal_id}] - Top weighted subcomponents count: {len(enhanced_data.get('top_weighted_subcomponents', []))}")
                self.logger.info(f"[DIAGNOSTICS] [ALERT_DATA] [TXN:{transaction_id}][SIG:{signal_id}] - Actionable insights count: {len(enhanced_data.get('actionable_insights', []))}")
            
            # Verify the alert_manager is available
            if not self.alert_manager:
                self.logger.error(f"[DIAGNOSTICS] [ALERT_MANAGER] [TXN:{transaction_id}][SIG:{signal_id}] ERROR: AlertManager is None, cannot send alert")
            else:
                self.logger.info(f"[DIAGNOSTICS] [ALERT_MANAGER] [TXN:{transaction_id}][SIG:{signal_id}] AlertManager initialized: {type(self.alert_manager).__name__}")
                
                # Check for webhook URL
                if hasattr(self.alert_manager, 'discord_webhook_url'):
                    webhook_url = self.alert_manager.discord_webhook_url
                    if webhook_url:
                        webhook_length = len(webhook_url)
                        self.logger.info(f"[DIAGNOSTICS] [ALERT_MANAGER] [TXN:{transaction_id}][SIG:{signal_id}] Discord webhook URL found with length: {webhook_length}")
                    else:
                        self.logger.error(f"[DIAGNOSTICS] [ALERT_MANAGER] [TXN:{transaction_id}][SIG:{signal_id}] ERROR: Discord webhook URL is empty")
            
            # Pass top_weighted_subcomponents to the alert manager
            await self.alert_manager.send_confluence_alert(
                symbol=symbol,
                confluence_score=score,  # This is validated_data.score
                components=components,
                results=results,
                reliability=reliability,  # Use reliability directly without normalization
                long_threshold=self.thresholds['long'],
                short_threshold=self.thresholds['short'],
                price=price,
                transaction_id=transaction_id,
                signal_id=signal_id,
                influential_components=enhanced_data.get('influential_components') if enhanced_data else None,
                market_interpretations=enhanced_data.get('market_interpretations') if enhanced_data else None,
                actionable_insights=enhanced_data.get('actionable_insights') if enhanced_data else None,
                top_weighted_subcomponents=enhanced_data.get('top_weighted_subcomponents') if enhanced_data else None,
                ohlcv_data=ohlcv_data  # Pass OHLCV data for chart generation
            )
            
            # Log success - PDF attachment is handled automatically by AlertManager
            self.logger.info(f"[DIAGNOSTICS] [ALERT_SENT] [TXN:{transaction_id}][SIG:{signal_id}] Alert sent successfully for {symbol} (PDF handled by AlertManager)")
            self.logger.info(f"[TXN:{transaction_id}][SIG:{signal_id}] Alert sent successfully for {symbol}")
        except Exception as e:
            self.logger.error(f"[DIAGNOSTICS] [ALERT_ERROR] [TXN:{transaction_id}][SIG:{signal_id}] ERROR: Error sending confluence alert: {str(e)}")
            self.logger.error(f"[DIAGNOSTICS] [ALERT_ERROR] [TXN:{transaction_id}][SIG:{signal_id}] Error traceback: {traceback.format_exc()}")
            
            # Try direct send_alert method as fallback
            try:
                if hasattr(self.alert_manager, 'send_alert'):
                    self.logger.info(f"[DIAGNOSTICS] [ALERT_FALLBACK] [TXN:{transaction_id}][SIG:{signal_id}] Using fallback alert method for {symbol}")
                    fallback_message = f"{direction} SIGNAL: {symbol} with score {score:.2f}/100"
                    
                    # Add transaction info to details
                    standardized_data['transaction_id'] = transaction_id
                    standardized_data['signal_id'] = signal_id
                    
                    await self.alert_manager.send_alert(
                        level="INFO",
                        message=fallback_message,
                        details=standardized_data
                    )
                    self.logger.info(f"[DIAGNOSTICS] [ALERT_FALLBACK] [TXN:{transaction_id}][SIG:{signal_id}] Fallback alert sent for {symbol}")
            except Exception as e2:
                self.logger.error(f"[DIAGNOSTICS] [ALERT_FALLBACK] [TXN:{transaction_id}][SIG:{signal_id}] ERROR: Error in fallback alert: {str(e2)}")
                self.logger.error(f"[DIAGNOSTICS] [ALERT_FALLBACK] [TXN:{transaction_id}][SIG:{signal_id}] Fallback error traceback: {traceback.format_exc()}")

    def _collect_indicator_results(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Collect detailed indicator results for formatted alerts."""
        results = {}
        
        # Define component mappings
        component_mappings = {
            'volume': 'volume_score',
            'orderflow': 'orderflow_score', 
            'orderbook': 'orderbook_score',
            'technical': 'technical_score',
            'sentiment': 'sentiment_score',
            'price_structure': 'price_structure_score'
        }
        
        for component_name, score_key in component_mappings.items():
            # Get component score with fallbacks
            if component_name == 'technical':
                component_score = indicators.get(score_key, indicators.get('momentum_score', 50))
            elif component_name == 'price_structure':
                component_score = indicators.get(score_key, indicators.get('position_score', 50))
            else:
                component_score = indicators.get(score_key, 50)
            
            # Extract sub-components
            extract_method = getattr(self, f"_extract_{component_name}_components", None)
            sub_components = {}
            if extract_method:
                sub_components = extract_method(indicators)
            
            # Use InterpretationGenerator for interpretation
            try:
                component_data = {
                    'score': component_score,
                    'signals': {},
                    'components': sub_components,
                    'metadata': {'raw_values': indicators}
                }
                
                interpretation = self.interpretation_generator.get_component_interpretation(
                    component_name, component_data
                )
            except Exception as e:
                self.logger.error(f"Error generating interpretation for {component_name}: {str(e)}")
                interpretation = f"Score: {component_score:.1f} - {'Bullish' if component_score > 50 else 'Bearish'} bias"
            
            results[component_name] = {
                'components': sub_components,
                'interpretation': interpretation
            }
        
        return results

    def _extract_volume_components(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Extract volume-related component scores from indicators with robust error handling."""
        components = {}
        
        try:
            # Input validation
            if not isinstance(indicators, dict):
                self.logger.error(f"Invalid indicators input type: {type(indicators)}")
                return {}
            
            # First, check if we have the nested volume indicator structure from actual analysis
            volume_data = indicators.get('volume', {})
            if isinstance(volume_data, dict) and 'components' in volume_data:
                # Use the actual calculated component scores
                actual_components = volume_data['components']
                if isinstance(actual_components, dict):
                    for key, value in actual_components.items():
                        if isinstance(value, (int, float)) and not np.isnan(value) and np.isfinite(value):
                            if 0 <= value <= 100:  # Validate range
                                components[key] = float(value)
                    
                    # If we got actual components, return them
                    if components:
                        self.logger.debug(f"Using actual volume components: {components}")
                        return components
            
            # Second, look for direct volume indicators in the results
            for key, value in indicators.items():
                if key.startswith('volume_') and isinstance(value, (int, float)) and key != 'volume_score':
                    # Convert key from volume_indicator to indicator format
                    component_name = key.replace('volume_', '')
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[component_name] = float(value)
            
            # Third, look for volume-related indicators with common names (avoid duplicates)
            volume_indicators = {
                'volume_delta': indicators.get('volume_delta'),
                'cmf': indicators.get('cmf'),  # Chaikin Money Flow
                'adl': indicators.get('adl'),  # Accumulation/Distribution Line
                'obv': indicators.get('obv'),  # On-Balance Volume
                'vwap': indicators.get('vwap'),  # Volume Weighted Average Price
                'pvt': indicators.get('pvt'),  # Price Volume Trend
                'mfi': indicators.get('mfi'),  # Money Flow Index
                'volume_oscillator': indicators.get('volume_oscillator'),
                'volume_rate_of_change': indicators.get('volume_rate_of_change'),
                'ease_of_movement': indicators.get('ease_of_movement')
            }
            
            for key, value in volume_indicators.items():
                if value is not None and isinstance(value, (int, float)):
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        # Only add if not already present (avoid duplicates from prefixed keys)
                        if key not in components:
                            # For volume_delta, check if it was already added as 'delta'
                            if key == 'volume_delta' and 'delta' in components:
                                continue  # Skip adding volume_delta if delta already exists
                            components[key] = float(value)
            
            # Log result
            if not components:
                self.logger.debug("No actual volume components found, returning empty dictionary")
            
            return components
            
        except Exception as e:
            self.logger.error(f"Error in volume component extraction: {str(e)}")
            return {}

    def _extract_orderflow_components(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Extract orderflow-related component scores from indicators with robust error handling."""
        components = {}
        
        try:
            # Input validation
            if not isinstance(indicators, dict):
                self.logger.error(f"Invalid indicators input type: {type(indicators)}")
                return {}
            
            # First, check if we have the nested orderflow indicator structure from actual analysis
            orderflow_data = indicators.get('orderflow', {})
            if isinstance(orderflow_data, dict) and 'components' in orderflow_data:
                # Use the actual calculated component scores
                actual_components = orderflow_data['components']
                if isinstance(actual_components, dict):
                    for key, value in actual_components.items():
                        if isinstance(value, (int, float)) and not np.isnan(value) and np.isfinite(value):
                            if 0 <= value <= 100:  # Validate range
                                components[key] = float(value)
                    
                    # If we got actual components, return them
                    if components:
                        self.logger.debug(f"Using actual orderflow components: {components}")
                        return components
            
            # Second, look for direct orderflow indicators in the results
            for key, value in indicators.items():
                if key.startswith('orderflow_') and isinstance(value, (int, float)) and key != 'orderflow_score':
                    component_name = key.replace('orderflow_', '')
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[component_name] = float(value)
            
            # Third, look for orderflow-related indicators with common names
            orderflow_indicators = {
                'trade_flow_score': indicators.get('trade_flow_score'),
                'imbalance_score': indicators.get('imbalance_score'),
                'cvd': indicators.get('cvd'),  # Cumulative Volume Delta
                'delta': indicators.get('delta'),
                'buy_sell_ratio': indicators.get('buy_sell_ratio'),
                'aggressive_fills': indicators.get('aggressive_fills'),
                'passive_fills': indicators.get('passive_fills'),
                'large_trades': indicators.get('large_trades'),
                'block_trades': indicators.get('block_trades'),
                'market_impact': indicators.get('market_impact')
            }
            
            for key, value in orderflow_indicators.items():
                if value is not None and isinstance(value, (int, float)):
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[key] = float(value)
            
            # Log result
            if not components:
                self.logger.debug("No actual orderflow components found, returning empty dictionary")
            
            return components
            
        except Exception as e:
            self.logger.error(f"Error in orderflow component extraction: {str(e)}")
            return {}

    def _extract_orderbook_components(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Extract orderbook-related component scores from indicators with robust error handling."""
        components = {}
        
        try:
            # Input validation
            if not isinstance(indicators, dict):
                self.logger.error(f"Invalid indicators input type: {type(indicators)}")
                return {}
            
            # First, check if we have the nested orderbook indicator structure from actual analysis
            orderbook_data = indicators.get('orderbook', {})
            if isinstance(orderbook_data, dict) and 'components' in orderbook_data:
                # Use the actual calculated component scores
                actual_components = orderbook_data['components']
                if isinstance(actual_components, dict):
                    for key, value in actual_components.items():
                        if isinstance(value, (int, float)) and not np.isnan(value) and np.isfinite(value):
                            if 0 <= value <= 100:  # Validate range
                                components[key] = float(value)
                    
                    # If we got actual components, return them
                    if components:
                        self.logger.debug(f"Using actual orderbook components: {components}")
                        return components
            
            # Second, look for direct orderbook indicators in the results
            for key, value in indicators.items():
                if key.startswith('orderbook_') and isinstance(value, (int, float)) and key != 'orderbook_score':
                    component_name = key.replace('orderbook_', '')
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[component_name] = float(value)
            
            # Third, look for orderbook-related indicators with common names
            orderbook_indicators = {
                'support_resistance': indicators.get('support_resistance'),
                'price_impact': indicators.get('price_impact'),
                'liquidity': indicators.get('liquidity'),
                'spread': indicators.get('spread'),
                'depth': indicators.get('depth'),
                'bid_ask_strength': indicators.get('bid_ask_strength'),
                'order_imbalance': indicators.get('order_imbalance'),
                'level_2_pressure': indicators.get('level_2_pressure'),
                'liquidity_gaps': indicators.get('liquidity_gaps'),
                'wall_strength': indicators.get('wall_strength')
            }
            
            for key, value in orderbook_indicators.items():
                if value is not None and isinstance(value, (int, float)):
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[key] = float(value)
            
            # Log result
            if not components:
                self.logger.debug("No actual orderbook components found, returning empty dictionary")
            
            return components
            
        except Exception as e:
            self.logger.error(f"Error in orderbook component extraction: {str(e)}")
            return {}

    def _extract_technical_components(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Extract technical indicators from the provided data with robust error handling."""
        components = {}
        
        try:
            # Input validation
            if not isinstance(indicators, dict):
                self.logger.error(f"Invalid indicators input type: {type(indicators)}")
                return {}
            
            # First, check if we have the nested technical indicator structure from actual analysis
            technical_data = indicators.get('technical', {})
            if isinstance(technical_data, dict) and 'components' in technical_data:
                # Use the actual calculated component scores
                actual_components = technical_data['components']
                if isinstance(actual_components, dict):
                    for key, value in actual_components.items():
                        if isinstance(value, (int, float)) and not np.isnan(value) and np.isfinite(value):
                            if 0 <= value <= 100:  # Validate range
                                components[key] = float(value)
                    
                    # If we got actual components, return them
                    if components:
                        self.logger.debug(f"Using actual technical components: {components}")
                        return components
            
            # Second, look for direct technical indicators in the results
            technical_indicators = {
                'rsi': indicators.get('rsi'),
                'macd': indicators.get('macd'),
                'ao': indicators.get('ao'),  # Awesome Oscillator
                'williams_r': indicators.get('williams_r'),
                'atr': indicators.get('atr'),  # Average True Range
                'cci': indicators.get('cci'),  # Commodity Channel Index
                'stoch': indicators.get('stoch'),  # Stochastic
                'bb': indicators.get('bb'),  # Bollinger Bands
                'ema': indicators.get('ema'),  # Exponential Moving Average
                'sma': indicators.get('sma'),  # Simple Moving Average
                'momentum': indicators.get('momentum'),
                'roc': indicators.get('roc'),  # Rate of Change
                'adx': indicators.get('adx'),  # Average Directional Index
                'ppo': indicators.get('ppo'),  # Percentage Price Oscillator
                'ultimate_oscillator': indicators.get('ultimate_oscillator')
            }
            
            for key, value in technical_indicators.items():
                if value is not None and isinstance(value, (int, float)):
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[key] = float(value)
            
            # Log result
            if not components:
                self.logger.debug("No actual technical components found, returning empty dictionary")
            
            return components
            
        except Exception as e:
            self.logger.error(f"Error in technical component extraction: {str(e)}")
            return {}

    def _extract_sentiment_components(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Extract sentiment-related component scores from indicators with robust error handling."""
        components = {}
        
        try:
            # Input validation
            if not isinstance(indicators, dict):
                self.logger.error(f"Invalid indicators input type: {type(indicators)}")
                return {}
            
            # First, check if we have the nested sentiment indicator structure from actual analysis
            sentiment_data = indicators.get('sentiment', {})
            if isinstance(sentiment_data, dict) and 'components' in sentiment_data:
                # Use the actual calculated component scores
                actual_components = sentiment_data['components']
                if isinstance(actual_components, dict):
                    for key, value in actual_components.items():
                        if isinstance(value, (int, float)) and not np.isnan(value) and np.isfinite(value):
                            if 0 <= value <= 100:  # Validate range
                                components[key] = float(value)
                    
                    # If we got actual components, return them
                    if components:
                        self.logger.debug(f"Using actual sentiment components: {components}")
                        return components
            
            # Second, look for direct sentiment indicators in the results
            for key, value in indicators.items():
                if key.startswith('sentiment_') and isinstance(value, (int, float)) and key != 'sentiment_score':
                    component_name = key.replace('sentiment_', '')
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[component_name] = float(value)
            
            # Third, look for sentiment-related indicators with common names
            sentiment_indicators = {
                'risk_score': indicators.get('risk_score'),
                'funding_rate': indicators.get('funding_rate'),
                'long_short_ratio': indicators.get('long_short_ratio'),
                'fear_greed_index': indicators.get('fear_greed_index'),
                'put_call_ratio': indicators.get('put_call_ratio'),
                'volatility_index': indicators.get('volatility_index'),
                'social_sentiment': indicators.get('social_sentiment'),
                'news_sentiment': indicators.get('news_sentiment'),
                'whale_sentiment': indicators.get('whale_sentiment'),
                'institutional_flow': indicators.get('institutional_flow')
            }
            
            for key, value in sentiment_indicators.items():
                if value is not None and isinstance(value, (int, float)):
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[key] = float(value)
            
            # Log result
            if not components:
                self.logger.debug("No actual sentiment components found, returning empty dictionary")
            
            return components
            
        except Exception as e:
            self.logger.error(f"Error in sentiment component extraction: {str(e)}")
            return {}

    def _extract_price_structure_components(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Extract price structure-related component scores from indicators with robust error handling."""
        components = {}
        
        try:
            # Input validation
            if not isinstance(indicators, dict):
                self.logger.error(f"Invalid indicators input type: {type(indicators)}")
                return {}
            
            # First, check if we have the nested price structure indicator structure from actual analysis
            price_structure_data = indicators.get('price_structure', {})
            if isinstance(price_structure_data, dict) and 'components' in price_structure_data:
                # Use the actual calculated component scores
                actual_components = price_structure_data['components']
                if isinstance(actual_components, dict):
                    for key, value in actual_components.items():
                        if isinstance(value, (int, float)) and not np.isnan(value) and np.isfinite(value):
                            if 0 <= value <= 100:  # Validate range
                                components[key] = float(value)
                    
                    # If we got actual components, return them
                    if components:
                        self.logger.debug(f"Using actual price structure components: {components}")
                        return components
            
            # Second, look for direct price structure indicators in the results
            for key, value in indicators.items():
                if key.startswith('price_structure_') and isinstance(value, (int, float)) and key != 'price_structure_score':
                    component_name = key.replace('price_structure_', '')
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[component_name] = float(value)
            
            # Third, look for price structure-related indicators with common names
            price_structure_indicators = {
                'support_resistance': indicators.get('support_resistance'),
                'order_block': indicators.get('order_block'),
                'trend_position': indicators.get('trend_position'),
                'swing_structure': indicators.get('swing_structure'),
                'composite_value': indicators.get('composite_value'),
                'fair_value_gaps': indicators.get('fair_value_gaps'),
                'bos_choch': indicators.get('bos_choch'),  # Break of Structure / Change of Character
                'range_score': indicators.get('range_score'),
                'liquidity_pools': indicators.get('liquidity_pools'),
                'market_structure': indicators.get('market_structure'),
                'pivot_points': indicators.get('pivot_points'),
                'fibonacci_levels': indicators.get('fibonacci_levels')
            }
            
            for key, value in price_structure_indicators.items():
                if value is not None and isinstance(value, (int, float)):
                    if not np.isnan(value) and np.isfinite(value) and 0 <= value <= 100:
                        components[key] = float(value)
            
            # Log result
            if not components:
                self.logger.debug("No actual price structure components found, returning empty dictionary")
            
            return components
            
        except Exception as e:
            self.logger.error(f"Error in price structure component extraction: {str(e)}")
            return {}
    
    def _clean_interpretation_text(self, text: str) -> str:
        """
        Clean up malformed interpretation text by removing unwanted prefixes and duplications.
        
        Args:
            text: Raw interpretation text that may contain prefixes like "Signal [TOKEN] [NUMBER]:"
            
        Returns:
            str: Cleaned interpretation text
        """
        if not isinstance(text, str):
            return str(text)
        
        import re
        
        # Remove "Signal [TOKEN] [NUMBER]:" patterns
        text = re.sub(r'^Signal\s+\w+\s+\d+:\s*', '', text)
        
        # Remove duplicate market context patterns (more comprehensive)
        text = re.sub(r'Under neutral market conditions:\s*Under neutral market conditions:\s*', '', text)
        text = re.sub(r'Under (bullish|bearish) market conditions:\s*Under (bullish|bearish) market conditions:\s*', r'Under \1 market conditions: ', text)
        
        # Remove single market context prefixes
        text = re.sub(r'^Under (neutral|bullish|bearish) market conditions:\s*', '', text)
        
        # Remove duplicate momentum/conditions patterns
        text = re.sub(r'In current (neutral|bullish|bearish) momentum conditions:\s*In current (neutral|bullish|bearish) momentum conditions:\s*', r'In current \1 momentum conditions: ', text)
        text = re.sub(r'In current (neutral|bullish|bearish) conditions conditions:\s*', r'In current \1 conditions: ', text)
        text = re.sub(r'In current (neutral|bullish|bearish) momentum conditions:\s*', '', text)
        
        # Remove duplicate risk environment patterns
        text = re.sub(r'In this (favorable|elevated|stable) risk environment:\s*In this (favorable|elevated|stable) risk environment:\s*', r'In this \1 risk environment: ', text)
        text = re.sub(r'In this (favorable|elevated|stable) risk environment:\s*', '', text)
        
        # Remove duplicate buying/selling pressure patterns
        text = re.sub(r'With (buying|selling) pressure evident:\s*With (buying|selling) pressure evident:\s*', r'With \1 pressure evident: ', text)
        text = re.sub(r'With (buying|selling|typical) (pressure|participation) evident:\s*', '', text)
        
        # Remove duplicate sentiment patterns
        text = re.sub(r'Given (positive|negative) market sentiment:\s*Given (positive|negative) market sentiment:\s*', r'Given \1 market sentiment: ', text)
        text = re.sub(r'Given (positive|negative) market sentiment:\s*', '', text)
        
        # Clean up any remaining duplicate colons or spaces
        text = re.sub(r':\s*:', ':', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text

    def _generate_enhanced_formatted_data(
        self, 
        symbol: str,
        confluence_score: float,
        components: Dict[str, Any],
        results: Dict[str, Any], 
        reliability: float,
        long_threshold: float,
        short_threshold: float
    ) -> Dict[str, Any]:
        """
        Generate enhanced formatted data for Discord alerts with proper component analysis.
        
        This method creates detailed market interpretations, actionable insights, and 
        identifies the top weighted subcomponents that contribute most to the confluence score.
        """
        enhanced_data = {}
        
        try:
            # Generate transaction and signal IDs for tracking
            transaction_id = str(uuid.uuid4())
            signal_id = str(uuid.uuid4())[:8]
            
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Generating enhanced formatted data for {symbol}")

            # Determine signal direction
            if confluence_score >= long_threshold:
                signal_direction = "LONG"
            elif confluence_score <= short_threshold:
                signal_direction = "SHORT"
            else:
                signal_direction = "NEUTRAL"
                
            # Determine market state based on component alignment
            component_scores = [score for score in components.values() if isinstance(score, (int, float))]
            if component_scores:
                score_std = np.std(component_scores)
                avg_score = np.mean(component_scores)
                
                if score_std < 10 and avg_score > 65:
                    market_state = "TRENDING_BULLISH"
                elif score_std < 10 and avg_score < 35:
                    market_state = "TRENDING_BEARISH"
                elif score_std < 15 and 45 <= avg_score <= 55:
                    market_state = "RANGING"
                elif avg_score > 55:
                    market_state = "LEANING_BULLISH"
                elif avg_score < 45:
                    market_state = "LEANING_BEARISH"
                else:
                    market_state = "MIXED"
            else:
                market_state = "UNKNOWN"
            
            # Check for conflicting signals
            bullish_components = [name for name, score in components.items() if isinstance(score, (int, float)) and score > 60]
            bearish_components = [name for name, score in components.items() if isinstance(score, (int, float)) and score < 40]
            has_conflicts = len(bullish_components) > 0 and len(bearish_components) > 0
            
            # Generate market interpretations using InterpretationGenerator
            raw_interpretations = []
            
            # Use InterpretationGenerator if available
            if hasattr(self, 'interpretation_generator') and self.interpretation_generator:
                try:
                    # Component-specific interpretations
                    for component_name, component_score in components.items():
                        if isinstance(component_score, (int, float)):
                            try:
                                # Use InterpretationGenerator for detailed interpretation
                                component_data = {
                                    'score': component_score,
                                    'signals': {},
                                    'components': {},
                                    'metadata': {'raw_values': results}
                                }
                                
                                # Get sub-components if available
                                extract_method = getattr(self, f"_extract_{component_name}_components", None)
                                if extract_method:
                                    try:
                                        component_data['components'] = extract_method(results)
                                    except Exception as e:
                                        self.logger.warning(f"Error extracting {component_name} components: {str(e)}")
                                
                                interpretation = self.interpretation_generator.get_component_interpretation(
                                    component_name, component_data
                                )
                                
                                raw_interpretations.append({
                                    'component': component_name,
                                    'display_name': component_name.replace('_', ' ').title(),
                                    'interpretation': interpretation
                                })
                                
                            except Exception as e:
                                self.logger.warning(f"Error generating interpretation for {component_name}: {str(e)}")
                                # Fallback to simple interpretation
                                interpretation = self._generate_simple_interpretation(component_name, component_score)
                                raw_interpretations.append({
                                    'component': component_name,
                                    'display_name': component_name.replace('_', ' ').title(),
                                    'interpretation': interpretation
                                })
                    
                    # Process interpretations through InterpretationManager if available
                    if hasattr(self, 'interpretation_manager') and self.interpretation_manager:
                        # Prepare market data for context
                        market_data = {
                            'market_overview': {
                                'regime': 'BULLISH' if signal_direction == 'LONG' else 'BEARISH' if signal_direction == 'SHORT' else 'NEUTRAL',
                                'volatility': results.get('volatility', {}).get('atr_percentage', 2.0),
                                'trend_strength': components.get('technical', 50.0) / 100.0,
                                'volume_change': components.get('volume', 50.0) / 100.0
                            },
                            'smart_money_index': {'index': components.get('sentiment', 50.0)},
                            'whale_activity': {'sentiment': 'BULLISH' if components.get('orderflow', 50.0) > 60 else 'BEARISH' if components.get('orderflow', 50.0) < 40 else 'NEUTRAL'},
                            'funding_rate': {'average': results.get('funding_rate', {}).get('average', 0.0)}
                        }
                        
                        interpretation_set = self.interpretation_manager.process_interpretations(
                            raw_interpretations, 
                            f"confluence_{symbol}",
                            market_data,
                            datetime.now()
                        )
                        
                        # Generate enhanced synthesis with conflict detection and market state analysis
                        enhanced_synthesis = self.interpretation_manager._generate_enhanced_synthesis(
                            interpretation_set
                        )
                        
                        # CRITICAL FIX: Pass raw interpretations to AlertManager instead of converting to strings
                        # This allows AlertManager to properly process them through InterpretationManager
                        market_interpretations = raw_interpretations.copy()
                        
                    else:
                        # Use raw interpretations without InterpretationManager processing
                        market_interpretations = raw_interpretations.copy()
                        
                except Exception as e:
                    self.logger.error(f"Error processing interpretations: {str(e)}")
                    # Fallback to simple string interpretations
                    market_interpretations = [f"{interp['display_name']}: {interp['interpretation']}" for interp in raw_interpretations]
            else:
                # Fallback: Generate simple interpretations
                market_interpretations = []
                for component_name, component_score in components.items():
                    if isinstance(component_score, (int, float)):
                        interpretation = self._generate_simple_interpretation(component_name, component_score)
                        market_interpretations.append(f"{component_name.replace('_', ' ').title()}: {interpretation}")
            
            # Generate actionable insights based on signal direction and market state
            actionable_insights = []
            
            if signal_direction == "SHORT":
                if market_state == "TRENDING_BEARISH":
                    actionable_insights.extend([
                        f"🔴 Strong bearish trend confirmed - High confidence signal",
                        f"Consider short positions with trend-following strategy",
                        f"Trail stop losses to capture maximum downside"
                    ])
                elif market_state == "LEANING_BEARISH":
                    actionable_insights.extend([
                        f"📉 Moderate bearish bias - Standard position sizing recommended",
                        f"Monitor for trend confirmation before increasing exposure"
                    ])
                else:
                    actionable_insights.extend([
                        f"Strong bearish confluence suggests potential downward momentum",
                        f"Consider short positions with stop loss above key resistance levels",
                        f"Monitor volume confirmation for entry timing"
                    ])
                
                # Add component-specific insights
                if components.get('volume', 0) > 60:
                    actionable_insights.append("High volume score supports sell signal strength")
                if components.get('orderflow', 0) < 40:
                    actionable_insights.append("Negative orderflow indicates institutional selling pressure")
                if components.get('technical', 0) < 40:
                    actionable_insights.append("Technical indicators align with bearish trend")
                
            elif signal_direction == "LONG":
                if market_state == "TRENDING_BULLISH":
                    actionable_insights.extend([
                        f"🚀 Strong bullish trend confirmed - High confidence signal",
                        f"Consider larger position sizes with trend-following strategy",
                        f"Trail stop losses to capture maximum upside"
                    ])
                elif market_state == "LEANING_BULLISH":
                    actionable_insights.extend([
                        f"📈 Moderate bullish bias - Standard position sizing recommended",
                        f"Monitor for trend confirmation before increasing exposure"
                    ])
                else:
                    actionable_insights.extend([
                        f"Strong bullish confluence suggests potential upward momentum",
                        f"Consider long positions with stop loss below key support levels",
                        f"Monitor volume confirmation for entry timing"
                    ])
                
                # Add component-specific insights
                if components.get('volume', 0) > 60:
                    actionable_insights.append("High volume score supports buy signal strength")
                if components.get('orderflow', 0) > 60:
                    actionable_insights.append("Positive orderflow indicates institutional buying interest")
                if components.get('technical', 0) > 60:
                    actionable_insights.append("Technical indicators align with bullish trend")
                
            else:
                if market_state == "RANGING":
                    actionable_insights.extend([
                        f"📊 Range-bound market confirmed - Use range trading strategies",
                        f"Buy near support, sell near resistance",
                        f"Avoid breakout trades until clear direction emerges"
                    ])
                else:
                    actionable_insights.extend([
                        f"Neutral confluence suggests range-bound price action",
                        f"Wait for clear breakout direction before entering positions",
                        f"Consider range trading strategies between support and resistance"
                    ])
            
            # Add reliability and risk management insights
            if has_conflicts:
                actionable_insights.append("🔴 HIGH RISK: Conflicting signals require minimal position sizing")
            elif reliability > 0.8:
                actionable_insights.append("✅ High reliability score increases signal confidence")
            elif reliability < 0.5:
                actionable_insights.append("⚠️ Low reliability suggests cautious position sizing")
            
            # Identify influential components (top performing components)
            influential_components = []
            sorted_components = sorted(
                [(name, score) for name, score in components.items() if isinstance(score, (int, float))],
                key=lambda x: abs(x[1] - 50),  # Sort by distance from neutral (50)
                reverse=True
            )
            
            for component_name, score in sorted_components[:3]:  # Top 3 most influential
                influence_type = "bullish" if score > 50 else "bearish"
                strength = abs(score - 50)
                influence_desc = "strong" if strength > 20 else "moderate" if strength > 10 else "weak"
                influential_components.append({
                    'component': component_name,
                    'score': score,
                    'influence': f"{influence_desc} {influence_type}",
                    'weight': self.confluence_weights.get(component_name, 1.0)
                })
            
            # FIXED: Generate top weighted subcomponents with proper impact calculation
            # This creates the data structure that the alert manager expects with accurate weighted impact
            top_weighted_subcomponents = []
            
            # Calculate total weighted score for proper impact calculation
            total_weighted_score = 0
            component_weighted_scores = {}
            
            for component_name, score in components.items():
                if isinstance(score, (int, float)):
                    weight = self.confluence_weights.get(component_name, 1.0)
                    weighted_score = score * weight
                    component_weighted_scores[component_name] = weighted_score
                    total_weighted_score += weighted_score
            
            # Extract subcomponents and calculate their true impact
            for component_name in components.keys():
                extract_method = getattr(self, f"_extract_{component_name}_components", None)
                if extract_method:
                    try:
                        sub_components = extract_method(results)
                        component_weight = self.confluence_weights.get(component_name, 1.0)
                        component_score = components.get(component_name, 50.0)
                        
                        # Skip if no valid subcomponents found
                        if not sub_components or not isinstance(sub_components, dict):
                            continue
                            
                        # Calculate the component's contribution to the overall score
                        component_contribution = component_weighted_scores.get(component_name, 0)
                        
                        for sub_name, sub_score in sub_components.items():
                            if isinstance(sub_score, (int, float)):
                                # Calculate the subcomponent's contribution to the parent component
                                sub_component_count = len([s for s in sub_components.values() if isinstance(s, (int, float))])
                                if sub_component_count > 0:
                                    # Each subcomponent contributes equally to the parent component
                                    sub_contribution_to_parent = sub_score / sub_component_count
                                    
                                    # Calculate the subcomponent's impact on the overall confluence score
                                    # This is the subcomponent's contribution to its parent * parent's weight * parent's influence
                                    weighted_impact = (sub_contribution_to_parent / 100.0) * component_weight * (component_score / 100.0) * 100
                                    
                                    # Create display names
                                    parent_display_name = component_name.replace('_', ' ').title()
                                    sub_display_name = sub_name.replace('_', ' ').title()
                                    
                                    # Clean up display names
                                    if sub_display_name.endswith(' Score'):
                                        sub_display_name = sub_display_name[:-6]
                                    
                                    # Determine indicator based on score
                                    if sub_score >= 70:
                                        indicator = "↑"  # Strong bullish
                                    elif sub_score >= 55:
                                        indicator = "•"  # Moderate bullish
                                    elif sub_score >= 45:
                                        indicator = "•"  # Neutral
                                    elif sub_score >= 30:
                                        indicator = "•"  # Moderate bearish
                                    else:
                                        indicator = "↓"  # Strong bearish
                                    
                                    # Only include components with meaningful impact
                                    if weighted_impact > 0.5:  # Threshold for meaningful impact
                                        top_weighted_subcomponents.append({
                                            'component': f"{component_name}.{sub_name}",
                                            'name': sub_name,  # Add name field for filtering
                                            'display_name': sub_display_name,
                                            'parent_display_name': parent_display_name,
                                            'score': sub_score,
                                            'weighted_score': sub_score * component_weight,
                                            'weighted_impact': weighted_impact,
                                            'weight': component_weight,
                                            'indicator': indicator
                                        })
                    except Exception as e:
                        self.logger.warning(f"Error extracting subcomponents for {component_name}: {str(e)}")
            
            # Sort by weighted impact (highest impact first) and limit to top 5
            top_weighted_subcomponents.sort(key=lambda x: x['weighted_impact'], reverse=True)
            top_weighted_subcomponents = top_weighted_subcomponents[:5]
            
            # Log the top weighted subcomponents for debugging
            self.logger.debug(f"[TXN:{transaction_id}][SIG:{signal_id}] Top weighted subcomponents for {symbol}:")
            for i, comp in enumerate(top_weighted_subcomponents):
                self.logger.debug(f"  {i+1}. {comp['display_name']} ({comp['parent_display_name']}): "
                                f"Score={comp['score']:.1f}, Impact={comp['weighted_impact']:.2f}%")
            
            # Compile enhanced data
            enhanced_data = {
                'market_interpretations': market_interpretations,
                'actionable_insights': actionable_insights,
                'influential_components': influential_components,
                'top_weighted_subcomponents': top_weighted_subcomponents
            }
            
            self.logger.debug(f"Generated enhanced data for {symbol}: "
                            f"{len(market_interpretations)} interpretations, "
                            f"{len(actionable_insights)} insights, "
                            f"{len(influential_components)} influential components, "
                            f"{len(top_weighted_subcomponents)} weighted subcomponents")
            
        except Exception as e:
            self.logger.error(f"Error generating enhanced formatted data for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            # Return minimal data on error
            enhanced_data = {
                'market_interpretations': [f"{symbol} confluence score: {confluence_score:.1f}"],
                'actionable_insights': ["Monitor price action for trading opportunities"],
                'influential_components': [],
                'top_weighted_subcomponents': []
            }
        
        return enhanced_data
    
    def _generate_simple_interpretation(self, component_name: str, score: float) -> str:
        """Generate a simple interpretation for a component score."""
        if component_name == 'futures_premium':
            if score > 70:
                return f"Strong Contango - Score: {score:.1f} - Futures trading at significant premium to spot"
            elif score > 55:
                return f"Contango - Score: {score:.1f} - Futures trading above spot prices"
            elif score < 30:
                return f"Strong Backwardation - Score: {score:.1f} - Futures trading at significant discount to spot"
            elif score < 45:
                return f"Backwardation - Score: {score:.1f} - Futures trading below spot prices"
            else:
                return f"Neutral Premium - Score: {score:.1f} - Balanced futures-spot relationship"
        else:
            bias = "Bullish" if score > 50 else "Bearish" if score < 50 else "Neutral"
            strength = "Strong" if abs(score - 50) > 20 else "Moderate" if abs(score - 50) > 10 else "Weak"
            return f"{strength} {bias} bias - Score: {score:.1f}"

    def _extract_futures_premium_components(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Extract futures premium components from indicators data."""
        try:
            components = {}
            
            # Extract futures premium data if available
            futures_premium = indicators.get('futures_premium', {})
            if isinstance(futures_premium, dict) and futures_premium:  # Only process if dict has actual data
                # Extract overall premium metrics
                average_premium = futures_premium.get('average_premium')
                market_status = futures_premium.get('market_status')
                
                # Only add market structure if we have actual market status data
                if market_status and market_status != 'NEUTRAL':
                    # Convert market status to numeric score
                    status_scores = {
                        'STRONG_CONTANGO': 85.0,
                        'CONTANGO': 70.0,
                        'NEUTRAL': 50.0,
                        'BACKWARDATION': 30.0,
                        'STRONG_BACKWARDATION': 15.0
                    }
                    components['market_structure'] = status_scores.get(market_status, 50.0)
                
                # Extract individual symbol premiums
                premiums = futures_premium.get('premiums', {})
                if premiums:
                    premium_values = []
                    contango_count = 0
                    backwardation_count = 0
                    
                    for symbol, data in premiums.items():
                        if isinstance(data, dict):
                            premium_value = data.get('premium_value', 0.0)
                            premium_values.append(premium_value)
                            
                            # Count contango vs backwardation
                            if premium_value > 0:
                                contango_count += 1
                            elif premium_value < 0:
                                backwardation_count += 1
                    
                    if premium_values:
                        # Calculate premium distribution metrics
                        avg_premium = sum(premium_values) / len(premium_values)
                        components['average_premium'] = 50.0 + (avg_premium * 2)  # Scale to 0-100
                        
                        # Calculate market breadth (percentage in contango)
                        total_symbols = len(premium_values)
                        contango_ratio = contango_count / total_symbols if total_symbols > 0 else 0.5
                        components['market_breadth'] = contango_ratio * 100
                        
                        # Calculate premium volatility (spread of premiums)
                        if len(premium_values) > 1:
                            premium_std = (sum((x - avg_premium) ** 2 for x in premium_values) / len(premium_values)) ** 0.5
                            components['premium_volatility'] = min(100, max(0, 50 - (premium_std * 10)))
                        else:
                            components['premium_volatility'] = 50.0
                
                # Extract quarterly futures data
                quarterly_futures = futures_premium.get('quarterly_futures', {})
                if quarterly_futures:
                    term_structure_score = 50.0
                    
                    # Analyze term structure for major symbols
                    for symbol, contracts in quarterly_futures.items():
                        if isinstance(contracts, list) and len(contracts) > 1:
                            # Sort by expiry
                            sorted_contracts = sorted(contracts, key=lambda x: x.get('months_to_expiry', 12))
                            
                            # Check if term structure is in contango (upward sloping)
                            if len(sorted_contracts) >= 2:
                                near_basis = float(sorted_contracts[0].get('basis', '0%').replace('%', ''))
                                far_basis = float(sorted_contracts[-1].get('basis', '0%').replace('%', ''))
                                
                                if far_basis > near_basis:
                                    term_structure_score += 10  # Contango term structure
                                elif far_basis < near_basis:
                                    term_structure_score -= 10  # Backwardation term structure
                    
                    components['term_structure'] = max(0, min(100, term_structure_score))
                
                # Extract funding rates correlation
                funding_rates = futures_premium.get('funding_rates', {})
                if funding_rates:
                    funding_scores = []
                    for symbol, funding_data in funding_rates.items():
                        if isinstance(funding_data, dict):
                            current_rate = funding_data.get('current_rate', 0.0)
                            # Convert funding rate to score (positive funding = bullish)
                            funding_score = 50.0 + (current_rate * 10000)  # Scale funding rate
                            funding_scores.append(max(0, min(100, funding_score)))
                    
                    if funding_scores:
                        components['funding_sentiment'] = sum(funding_scores) / len(funding_scores)
            
            # REMOVED: No more hardcoded fallback values - return only actual calculated components
            if not components:
                self.logger.debug("No actual futures premium components found, returning empty dictionary")
            
            return components
            
        except Exception as e:
            self.logger.error(f"Error extracting futures premium components: {str(e)}")
            return {}

    async def _check_futures_premium_alerts(self, indicators: Dict[str, Any], symbol: str) -> None:
        """Check for extreme futures premium conditions and send alerts."""
        try:
            futures_premium = indicators.get('futures_premium', {})
            if not isinstance(futures_premium, dict):
                return
            
            # Check market-wide conditions
            market_status = futures_premium.get('market_status', 'NEUTRAL')
            average_premium = futures_premium.get('average_premium', 0.0)
            
            # Alert for extreme market-wide conditions
            if market_status in ['STRONG_CONTANGO', 'STRONG_BACKWARDATION']:
                alert_type = "FUTURES_PREMIUM_EXTREME"
                severity = "high"
                
                if market_status == 'STRONG_CONTANGO':
                    message = f"🚨 EXTREME CONTANGO DETECTED\n"
                    message += f"Market-wide average premium: {average_premium:.2f}%\n"
                    message += f"Futures significantly overpriced vs spot - potential short opportunity"
                else:
                    message = f"🚨 EXTREME BACKWARDATION DETECTED\n"
                    message += f"Market-wide average premium: {average_premium:.2f}%\n"
                    message += f"Futures significantly underpriced vs spot - potential long opportunity"
                
                await self._send_alert(alert_type, message, severity)
            
            # Check individual symbol conditions
            premiums = futures_premium.get('premiums', {})
            for symbol_name, data in premiums.items():
                if not isinstance(data, dict):
                    continue
                    
                premium_value = data.get('premium_value', 0.0)
                premium_type = data.get('premium_type', 'NEUTRAL')
                
                # Alert for extreme individual premiums
                if abs(premium_value) > 5.0:  # More than 5% premium/discount
                    alert_type = "SYMBOL_PREMIUM_EXTREME"
                    severity = "medium"
                    
                    if premium_value > 5.0:
                        message = f"📈 EXTREME CONTANGO: {symbol_name}\n"
                        message += f"Premium: {premium_value:.2f}%\n"
                        message += f"Futures significantly overpriced - consider shorting futures or buying spot"
                    else:
                        message = f"📉 EXTREME BACKWARDATION: {symbol_name}\n"
                        message += f"Premium: {premium_value:.2f}%\n"
                        message += f"Futures significantly underpriced - consider buying futures or shorting spot"
                    
                    await self._send_alert(alert_type, message, severity)
            
            # Check quarterly futures term structure
            quarterly_futures = futures_premium.get('quarterly_futures', {})
            for symbol_name, contracts in quarterly_futures.items():
                if not isinstance(contracts, list) or len(contracts) < 2:
                    continue
                
                # Sort by expiry
                sorted_contracts = sorted(contracts, key=lambda x: x.get('months_to_expiry', 12))
                
                if len(sorted_contracts) >= 2:
                    near_basis = float(sorted_contracts[0].get('basis', '0%').replace('%', ''))
                    far_basis = float(sorted_contracts[-1].get('basis', '0%').replace('%', ''))
                    
                    # Check for inverted term structure (backwardation)
                    if near_basis - far_basis > 3.0:  # Near future more than 3% above far future
                        alert_type = "TERM_STRUCTURE_INVERTED"
                        severity = "medium"
                        message = f"⚠️ INVERTED TERM STRUCTURE: {symbol_name}\n"
                        message += f"Near contract: {near_basis:.2f}% | Far contract: {far_basis:.2f}%\n"
                        message += f"Term structure in backwardation - potential supply shortage or high demand"
                        
                        await self._send_alert(alert_type, message, severity)
                    
                    # Check for steep contango
                    elif far_basis - near_basis > 5.0:  # Far future more than 5% above near future
                        alert_type = "TERM_STRUCTURE_STEEP"
                        severity = "medium"
                        message = f"📊 STEEP CONTANGO: {symbol_name}\n"
                        message += f"Near contract: {near_basis:.2f}% | Far contract: {far_basis:.2f}%\n"
                        message += f"Steep upward term structure - potential oversupply or low current demand"
                        
                        await self._send_alert(alert_type, message, severity)
                        
        except Exception as e:
            self.logger.error(f"Error checking futures premium alerts: {str(e)}")

    async def _send_alert(self, alert_type: str, message: str, severity: str = "info") -> None:
        """Send alert through the alert manager."""
        try:
            if self.alert_manager:
                await self.alert_manager.send_alert(
                    alert_type=alert_type,
                    message=message,
                    severity=severity,
                    source="SignalGenerator"
                )
            else:
                self.logger.warning(f"No alert manager available for {alert_type}: {message}")
        except Exception as e:
            self.logger.error(f"Error sending alert: {str(e)}")


    # ====== RESTORED METHODS FROM BACKUP ======

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
            if score >= self.thresholds['long']:
                direction = "LONG"
            elif score <= self.thresholds['short']:
                direction = "SHORT"
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
                                'reliability': reliability,
                                # Pass through enriched narrative data when available
                                'market_interpretations': signal_data.get('market_interpretations'),
                                'actionable_insights': signal_data.get('actionable_insights'),
                                'influential_components': signal_data.get('influential_components'),
                                'top_weighted_subcomponents': signal_data.get('top_weighted_subcomponents')
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
                                'reliability': reliability,
                                # Pass through enriched narrative data when available
                                'market_interpretations': signal_data.get('market_interpretations'),
                                'actionable_insights': signal_data.get('actionable_insights'),
                                'influential_components': signal_data.get('influential_components'),
                                'top_weighted_subcomponents': signal_data.get('top_weighted_subcomponents')
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
                    self.thresholds['long'],
                    self.thresholds['short']
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
                    'reliability': reliability,  # Already in 0-1 range
                    'long_threshold': self.thresholds['long'],
                    'short_threshold': self.thresholds['short'],
                    'price': price,
                    'transaction_id': transaction_id,
                    'signal_id': signal_id
                }
                
                # Add enhanced formatted data to alert if available
                if enhanced_data:
                    alert_data.update(enhanced_data)
                
                # COMMENTED OUT: This was causing duplicate reliability calculation
                # The reliability is already correctly calculated in confluence analysis
                # Keeping this code for potential future use as a "confidence score" based on component variance
                # confidence_score = self._calculate_confidence_score(signal_data)
                
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
                
                # Check if we have a chart_path from the signal_data
                chart_path = signal_data.get('chart_path')
                
                # Pass top_weighted_subcomponents to the alert manager
                await self.alert_manager.send_confluence_alert(
                    symbol=symbol,
                    confluence_score=score,  # This is validated_data.score
                    components=serialized_components,
                    results=serialized_results,
                    reliability=reliability,  # Use reliability directly without normalization
                    long_threshold=self.thresholds['long'],
                    short_threshold=self.thresholds['short'],
                    price=price,
                    transaction_id=transaction_id,
                    signal_id=signal_id,
                    influential_components=enhanced_data.get('influential_components'),
                    market_interpretations=enhanced_data.get('market_interpretations'),
                    actionable_insights=enhanced_data.get('actionable_insights'),
                    top_weighted_subcomponents=enhanced_data.get('top_weighted_subcomponents'),
                    pdf_path=pdf_path,  # Pass the PDF path
                    chart_path=chart_path  # Pass the chart path if available
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
            # This is the preferred case - confluence_score is present, copy to score for backward compatibility
            standardized['score'] = standardized['confluence_score']
        elif 'score' in standardized and 'confluence_score' not in standardized:
            # Old format - copy to confluence_score
            standardized['confluence_score'] = standardized['score']
        elif 'score' not in standardized and 'confluence_score' not in standardized:
            # Default score if both missing
            standardized['confluence_score'] = 50.0
            standardized['score'] = standardized['confluence_score']  # Copy from confluence_score
        
        # Always ensure both score fields are set to the same value
        if 'score' in standardized and 'confluence_score' in standardized:
            # Use confluence_score as the canonical value (changed from using 'score')
            standardized['score'] = standardized['confluence_score']
        
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
            if direction in ['LONG', 'SHORT', 'NEUTRAL'] and 'signal' not in standardized:
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
        
        # FIX: Convert market_interpretations from List[Dict] to List[str] for Pydantic validation
        if 'market_interpretations' in standardized:
            interpretations = standardized['market_interpretations']
            if interpretations and isinstance(interpretations, list):
                fixed_interpretations = []
                for item in interpretations:
                    if isinstance(item, dict):
                        # Extract string from dict format: {'component': 'technical', 'interpretation': 'Strong signal'}
                        if 'interpretation' in item:
                            fixed_interpretations.append(item['interpretation'])
                        elif 'text' in item:
                            fixed_interpretations.append(item['text'])
                        else:
                            # Fallback: convert dict to string
                            fixed_interpretations.append(str(item.get('component', 'Unknown')) + ': ' + str(item))
                    elif isinstance(item, str):
                        # Already a string, keep as is
                        fixed_interpretations.append(item)
                    else:
                        # Convert any other type to string
                        fixed_interpretations.append(str(item))
                standardized['market_interpretations'] = fixed_interpretations
        
        
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


    def _calculate_confidence_score(self, signal_data: Dict[str, Any]) -> float:
        """Calculate confidence score based on component variance.
        
        NOTE: This is different from reliability. This calculates a confidence
        score based on how much the component scores agree with each other.
        Lower variance = higher confidence.
        
        Calculates confidence score (0-100) based on:
        1. Component agreement (standard deviation of scores)
        2. Data quality
        3. Signal strength
        
        Returns:
            float: Confidence score between 0 and 100
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

            # Return as 0-1 range for consistency across the system
            return final_reliability / 100.0
            
        except Exception as e:
            self.logger.error(f"Error calculating reliability: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return 1.0  # Default to full reliability on error (0-1 range)


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
            self.logger.debug(f"🔍 DEBUG: Starting OHLCV fetch for {symbol} ({timeframe}, {limit} candles)")
            
            # Try to get monitor from direct attribute first, then confluence_analyzer
            monitor = None
            market_data_manager = None
            
            # Enhanced debug logging for attribute checking
            self.logger.debug(f"🔍 DEBUG: Checking for monitor and market_data_manager...")
            self.logger.debug(f"  - Instance ID: {id(self)}")
            self.logger.debug(f"  - hasattr(self, 'monitor'): {hasattr(self, 'monitor')}")
            self.logger.debug(f"  - hasattr(self, 'market_data_manager'): {hasattr(self, 'market_data_manager')}")
            self.logger.debug(f"  - hasattr(self, 'confluence_analyzer'): {hasattr(self, 'confluence_analyzer')}")
            
            # Check for direct monitor attribute (set by main.py)
            if hasattr(self, 'monitor') and self.monitor:
                monitor = self.monitor
                self.logger.debug(f"✅ DEBUG: Found monitor via direct attribute (ID: {id(monitor)})")
            elif hasattr(self, 'confluence_analyzer') and self.confluence_analyzer:
                self.logger.debug(f"  - Checking confluence_analyzer (ID: {id(self.confluence_analyzer)})")
                if hasattr(self.confluence_analyzer, 'monitor'):
                    monitor = self.confluence_analyzer.monitor
                    self.logger.debug(f"✅ DEBUG: Found monitor via confluence_analyzer (ID: {id(monitor) if monitor else 'None'})")
                else:
                    self.logger.debug(f"  - confluence_analyzer has no monitor attribute")
            
            # Check for direct market_data_manager attribute (set by main.py)
            if hasattr(self, 'market_data_manager') and self.market_data_manager:
                market_data_manager = self.market_data_manager
                self.logger.debug(f"✅ DEBUG: Found market_data_manager via direct attribute (ID: {id(market_data_manager)})")
            elif hasattr(self, 'confluence_analyzer') and self.confluence_analyzer:
                if hasattr(self.confluence_analyzer, 'market_data_manager'):
                    market_data_manager = self.confluence_analyzer.market_data_manager
                    self.logger.debug(f"✅ DEBUG: Found market_data_manager via confluence_analyzer (ID: {id(market_data_manager) if market_data_manager else 'None'})")
                else:
                    self.logger.debug(f"  - confluence_analyzer has no market_data_manager attribute")
            
            # Check if monitor is available (primary cache source)
            if monitor:
                self.logger.debug(f"✅ DEBUG: monitor is available, checking its cache")
                
                # Try to get data from monitor's cache
                if hasattr(monitor, '_ohlcv_cache') and symbol in monitor._ohlcv_cache:
                    cached_data = monitor._ohlcv_cache[symbol]
                    self.logger.debug(f"🎯 DEBUG: Found cached OHLCV data in monitor for {symbol}")
                    
                    if 'processed' in cached_data:
                        # Get the appropriate timeframe data
                        timeframe_map = {
                            '1m': 'ltf', '5m': 'ltf', '15m': 'mtf',
                            '30m': 'mtf', '1h': 'base', '4h': 'htf', '1d': 'htf'
                        }
                        tf_key = timeframe_map.get(timeframe, 'base')
                        
                        if tf_key in cached_data['processed']:
                            df_data = cached_data['processed'][tf_key]
                            if isinstance(df_data, pd.DataFrame):
                                self.logger.debug(f"✨ DEBUG: Using monitor's cached DataFrame with {len(df_data)} candles")
                                return df_data.tail(limit) if len(df_data) > limit else df_data
                            else:
                                self.logger.debug(f"📈 DEBUG: Converting monitor's cached data to DataFrame")
                                df = pd.DataFrame(df_data)
                                return df.tail(limit) if len(df) > limit else df
                else:
                    self.logger.debug(f"❌ DEBUG: No OHLCV data in monitor cache for {symbol}")
            
            # Check if market_data_manager is available (secondary cache source)
            if market_data_manager:
                self.logger.debug(f"✅ DEBUG: market_data_manager is available")
                
                # Try to get data directly from cache
                if hasattr(market_data_manager, '_ohlcv_cache'):
                    cache_keys = list(market_data_manager._ohlcv_cache.keys())
                    self.logger.debug(f"📊 DEBUG: Checking _ohlcv_cache with {len(cache_keys)} keys")
                    self.logger.debug(f"📊 DEBUG: Sample keys: {cache_keys[:5] if cache_keys else 'empty'}")
                    
                    # Map timeframe to cache keys
                    timeframe_map = {
                        '1m': 'ltf', '5m': 'ltf', '15m': 'mtf',
                        '30m': 'mtf', '1h': 'base', '4h': 'htf', '1d': 'htf'
                    }
                    cache_key = timeframe_map.get(timeframe, 'base')
                    
                    # Try different key formats (including just symbol for monitor-style cache)
                    for key_format in [symbol, f"{symbol}_{cache_key}", f"{symbol}_ohlcv_{cache_key}", f"{symbol}_base"]:
                        if key_format in market_data_manager._ohlcv_cache:
                            cached_entry = market_data_manager._ohlcv_cache[key_format]
                            
                            # Handle different cache formats
                            if isinstance(cached_entry, dict):
                                if 'processed' in cached_entry and cache_key in cached_entry['processed']:
                                    # Monitor-style cache format
                                    cached_data = cached_entry['processed'][cache_key]
                                elif 'data' in cached_entry:
                                    cached_data = cached_entry['data']
                                else:
                                    continue
                            else:
                                cached_data = cached_entry
                            
                            if cached_data is not None:
                                self.logger.debug(f"🎯 DEBUG: Found cached OHLCV data with key {key_format}")
                                if isinstance(cached_data, pd.DataFrame):
                                    self.logger.debug(f"✨ DEBUG: Using cached DataFrame with {len(cached_data)} candles")
                                    return cached_data.tail(limit) if len(cached_data) > limit else cached_data
                                else:
                                    self.logger.debug(f"📈 DEBUG: Converting cached data to DataFrame")
                                    df = pd.DataFrame(cached_data)
                                    return df.tail(limit) if len(df) > limit else df
            else:
                # Extensive debug logging to understand why references are missing
                self.logger.warning(f"⚠️ DEBUG: Neither monitor nor market_data_manager could be found")
                
                # Log all available attributes on the signal_generator instance
                self.logger.warning(f"🔍 DEBUG: SignalGenerator attributes check:")
                self.logger.warning(f"  - hasattr(self, 'monitor'): {hasattr(self, 'monitor')}")
                self.logger.warning(f"  - self.monitor is None: {getattr(self, 'monitor', 'ATTR_NOT_FOUND') is None}")
                self.logger.warning(f"  - hasattr(self, 'market_data_manager'): {hasattr(self, 'market_data_manager')}")
                self.logger.warning(f"  - self.market_data_manager is None: {getattr(self, 'market_data_manager', 'ATTR_NOT_FOUND') is None}")
                self.logger.warning(f"  - hasattr(self, 'confluence_analyzer'): {hasattr(self, 'confluence_analyzer')}")
                self.logger.warning(f"  - self.confluence_analyzer is None: {getattr(self, 'confluence_analyzer', 'ATTR_NOT_FOUND') is None}")
                
                # If confluence_analyzer exists, check its attributes
                if hasattr(self, 'confluence_analyzer') and self.confluence_analyzer:
                    self.logger.warning(f"📊 DEBUG: ConfluenceAnalyzer attributes:")
                    self.logger.warning(f"  - hasattr(confluence, 'monitor'): {hasattr(self.confluence_analyzer, 'monitor')}")
                    self.logger.warning(f"  - hasattr(confluence, 'market_data_manager'): {hasattr(self.confluence_analyzer, 'market_data_manager')}")
                
                # Log the object ID to track instance
                self.logger.warning(f"🆔 DEBUG: SignalGenerator instance ID: {id(self)}")
                
                # Check if we're in alert generation context
                import inspect
                frame = inspect.currentframe()
                if frame:
                    calling_function = frame.f_back.f_code.co_name if frame.f_back else "Unknown"
                    self.logger.warning(f"📍 DEBUG: Called from function: {calling_function}")
                
                # List all attributes of the instance
                attrs = [attr for attr in dir(self) if not attr.startswith('_')]
                self.logger.warning(f"📦 DEBUG: Available public attributes: {', '.join(attrs[:10])}...")  # First 10 to avoid spam
            
            # Fallback to processor
            self.logger.debug(f"🔄 DEBUG: Falling back to processor.fetch_ohlcv")
            processor = await self.processor
            
            # Fetch OHLCV data
            ohlcv_data = await processor.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit
            )
            
            if ohlcv_data is None or len(ohlcv_data) == 0:
                self.logger.warning(f"❌ DEBUG: No OHLCV data found for {symbol} from processor")
                return None
                
            self.logger.debug(f"✅ DEBUG: Retrieved {len(ohlcv_data)} OHLCV candles for {symbol} from processor")
            return ohlcv_data
            
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV data for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return None

