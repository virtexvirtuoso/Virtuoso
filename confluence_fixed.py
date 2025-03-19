from typing import Dict, List, Optional, Any
import numpy as np
import logging
from datetime import datetime
import pandas as pd
import time
import traceback
import asyncio
import warnings  # For handling warnings gracefully
from typing import Union  # For more precise type hints
from dataclasses import dataclass  # If using dataclasses for structured data
from concurrent.futures import ThreadPoolExecutor  # For parallel processing if needed
from src.core.analysis.data_validator import DataValidator
import json
import copy
import re


# Import indicators
from src.core.logger import Logger
from src.indicators import (
    VolumeIndicators,
    OrderflowIndicators,
    OrderbookIndicators,
    TechnicalIndicators,
    SentimentIndicators,
    PriceStructureIndicators,
    BaseIndicator
)

logger = logging.getLogger(__name__)

class DataFlowTracker:
    """Track data transformation and flow through the system."""
    def __init__(self):
        self.events = []
        self.start_time = time.time()
        
    def log_transform(self, indicator_type, data_keys):
        """Log a data transformation event."""
        self.events.append({
            'type': 'transform',
            'indicator': indicator_type,
            'data_keys': data_keys,
            'timestamp': time.time()
        })
        
    def log_analysis(self, indicator_type, status, score=None):
        """Log an analysis event."""
        self.events.append({
            'type': 'analysis',
            'indicator': indicator_type,
            'status': status,
            'score': score,
            'timestamp': time.time()
        })
    
    def get_summary(self):
        """Get a summary of flow events."""
        return {
            'events': len(self.events),
            'duration': time.time() - self.start_time,
            'components': [e['indicator'] for e in self.events if e['type'] == 'transform']
        }

class ConfluenceAnalyzer:
    """Analyzes market data using multiple indicators for confluence."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the confluence analyzer"""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Debug mode from config
        self.debug_mode = self.config.get('debug', {}).get('enabled', False)
        self.debug_level = self.config.get('debug', {}).get('level', 1)
        
        # Initialize data flow tracking
        self.data_flow = {
            'last_update': 0,
            'processed_count': 0,
            'error_count': 0,
            'component_stats': {}
        }
        
        # Add flow tracker
        self.flow = DataFlowTracker()
        
        # Initialize indicators
        self.indicators = {
            'technical': TechnicalIndicators(config, self.logger),
            'volume': VolumeIndicators(config, self.logger),
            'orderflow': OrderflowIndicators(config, self.logger),
            'orderbook': OrderbookIndicators(config, self.logger),
            'sentiment': SentimentIndicators(config, self.logger),
            'price_structure': PriceStructureIndicators(config, self.logger)
        }
        
        # Initialize weights
        # Try to get from config first
        if self.config and 'analysis' in self.config and 'weights' in self.config['analysis']:
            self.weights = self.config['analysis']['weights'].copy()
            self.logger.info(f"Using weights from config: {self.weights}")
        else:
            # Use default weights
                self.weights = {
                'technical': 0.25,
                'volume': 0.15,     # Added volume component
                'orderflow': 0.15,  # Reduced from 0.2
                'sentiment': 0.15,  # Reduced from 0.2
                'orderbook': 0.15,
                'price_structure': 0.15
            }
            self.logger.info(f"Using default weights: {self.weights}")
        
        # Ensure all indicators have a weight
        for indicator_name in self.indicators:
            if indicator_name not in self.weights:
                self.weights[indicator_name] = 0.1
                self.logger.warning(f"Missing weight for {indicator_name}, using default 0.1")
        
        self._normalize_weights()

    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data with debug tracking."""
        flow_id = f"flow_{int(time.time())}"
        self.logger.debug(f"\n=== Analysis Flow {flow_id} ===")
        
        try:
            # Track data flow
            self._track_data_flow('start', flow_id, {
                'symbol': market_data.get('symbol'),
                'data_keys': list(market_data.keys())
            })

            # Validate input
            if not self._validate_market_data(market_data):
                self._track_data_flow('error', flow_id, {'error': 'validation_failed'})
                return self._get_default_response()

            # Process indicators
            scores = {}
            components = {}
            
            for name, indicator in self.indicators.items():
                try:
                    # Transform and track data
                    indicator_data = self._transform_data(name, market_data)
                    self._track_data_flow('transform', flow_id, {
                        'indicator': name,
                        'data_keys': list(indicator_data.keys())
                    })
                    
                    # Calculate score
                    result = await indicator.calculate(indicator_data)
                    scores[name] = result.get('score', 50.0)
                    components[name] = result.get('components', {})
                    
                    self._track_data_flow('score', flow_id, {
                        'indicator': name,
                        'score': scores[name]
                    })
                    
                    # Add detailed component summary logging
                    self.logger.info(f"\n=== {name.upper()} Component Summary ===")
                    self.logger.info(f"Overall Score: {scores[name]:.2f}")
                    if isinstance(components[name], dict):
                        for comp_name, comp_score in components[name].items():
                            if isinstance(comp_score, (int, float)):
                                self.logger.info(f"- {comp_name}: {comp_score:.2f}")
                            elif isinstance(comp_score, dict) and 'score' in comp_score:
                                self.logger.info(f"- {comp_name}: {comp_score['score']:.2f}")
                
                except Exception as e:
                    self.logger.error(f"Error in {name}: {str(e)}")
                    self._track_data_flow('error', flow_id, {
                        'indicator': name,
                        'error': str(e)
                    })
                    scores[name] = 50.0
                    components[name] = {}

            # Calculate final scores
            confluence_score = self._calculate_confluence_score(scores)
            reliability = self._calculate_reliability(scores)

            # Log detailed component breakdown before final calculation
            self.logger.info("\n=== Component Score Breakdown ===")
            for name, score in scores.items():
                weight = self.weights.get(name, 0)
                contribution = score * weight
                self.logger.info(f"{name}: {score:.2f} × {weight:.2f} = {contribution:.2f}")

            # Track completion
            self._track_data_flow('complete', flow_id, {
                'confluence_score': confluence_score,
                'reliability': reliability
            })

            return {
                'timestamp': int(time.time() * 1000),
                'confluence_score': confluence_score,
                'reliability': reliability,
                'scores': scores,
                'components': components,
                'metadata': {
                    'flow_id': flow_id,
                    'symbol': market_data.get('symbol'),
                    'calculation_time': time.time(),
                    'debug_info': self._get_debug_info(flow_id) if self.debug_mode else None
                }
            }

        except Exception as e:
            self._track_data_flow('error', flow_id, {'error': str(e)})
            self.logger.error(f"Analysis error: {str(e)}")
            return self._get_default_response()

    def _track_data_flow(self, stage: str, flow_id: str, data: Dict[str, Any]) -> None:
        """Track data flow for debugging."""
        try:
            if not getattr(self, 'debug_mode', False):
                return
            
            timestamp = time.time()
            
            # Update stats
            self.data_flow['last_update'] = timestamp
            if stage == 'complete':
                self.data_flow['processed_count'] += 1
            elif stage == 'error':
                self.data_flow['error_count'] += 1
            
            # Log based on debug level
            debug_level = getattr(self, 'debug_level', 1)
            if debug_level >= 2:
                self.logger.debug(f"Flow {flow_id} | {stage} | {json.dumps(data)}")
            elif debug_level >= 1 and stage in ['error', 'complete']:
                self.logger.debug(f"Flow {flow_id} | {stage} | {data.get('error', '')}")
            
        except Exception as e:
            self.logger.error(f"Error tracking data flow: {str(e)}")

    def _get_debug_info(self, flow_id: str) -> Dict[str, Any]:
        """Get debug information for response."""
        return {
            'flow_id': flow_id,
            'processed_count': self.data_flow['processed_count'],
            'error_count': self.data_flow['error_count'],
            'component_stats': self.data_flow['component_stats']
        }

    def _transform_data(self, indicator_type: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform market data into the format expected by specific indicators."""
            transformed_data = {}
        
        try:
            if indicator_type == 'technical':
                # Technical indicators need OHLCV data at various timeframes
                try:
                    technical_indicator = self.indicators['technical']
                    
                    # Log OHLCV timeframes
                    ohlcv_data = market_data.get('ohlcv', {})
                    self.logger.debug(f"OHLCV timeframes: {list(ohlcv_data.keys())}")
                    for tf, df in ohlcv_data.items():
                        if isinstance(df, pd.DataFrame):
                            self.logger.debug(f"- {tf}: shape {df.shape}")
                    
                    transformed_data = {
                        'ohlcv': ohlcv_data
                    }
                except Exception as e:
                    self.logger.error(f"Error transforming technical data: {str(e)}")
                    transformed_data = {
                        'ohlcv': {}
                    }
                
            elif indicator_type == 'volume':
                # Volume indicators need OHLCV and trades data
                try:
                    volume_indicator = self.indicators['volume']
                    
                    # Log OHLCV timeframes
                    ohlcv_data = market_data.get('ohlcv', {})
                    self.logger.debug(f"OHLCV timeframes: {list(ohlcv_data.keys())}")
                    for tf, df in ohlcv_data.items():
                        if isinstance(df, pd.DataFrame):
                            self.logger.debug(f"- {tf}: shape {df.shape}")
                    
                    # Process trades
                    processed_trades = self._process_trades(market_data.get('trades', []))
                    
                    transformed_data = {
                        'ohlcv': ohlcv_data,
                        'trades': processed_trades
                    }
                except Exception as e:
                    self.logger.error(f"Error transforming volume data: {str(e)}")
                    transformed_data = {
                        'ohlcv': {},
                        'trades': []
                    }
                
            elif indicator_type == 'orderflow':
                # Orderflow indicators need trades and orderbook data
                # Include OHLCV data for context
                try:
                    orderflow_indicator = self.indicators['orderflow']
                    
                    # Log OHLCV timeframes for context
                    ohlcv_data = market_data.get('ohlcv', {})
                    self.logger.debug(f"OHLCV timeframes: {list(ohlcv_data.keys())}")
                    for tf, df in ohlcv_data.items():
                        if isinstance(df, pd.DataFrame):
                            self.logger.debug(f"- {tf}: shape {df.shape}")
                    
                    # Process trades
                    processed_trades = self._process_trades(market_data.get('trades', []))
                    
                    if not processed_trades:
                        self.logger.error("Missing trades data")
                        
                    transformed_data = {
                        'orderbook': market_data.get('orderbook', {}),
                        'trades': processed_trades,
                        'ohlcv': ohlcv_data  # Including OHLCV for context
                    }
                except Exception as e:
                    self.logger.error(f"Error transforming orderflow data: {str(e)}")
                    transformed_data = {
                        'orderbook': {},
                        'trades': [],
                        'ohlcv': {}
                    }
                
            elif indicator_type == 'orderbook':
                # Orderbook indicators need orderbook data
                try:
                    orderbook_indicator = self.indicators['orderbook']
                    
                    # Log OHLCV timeframes for context
                    ohlcv_data = market_data.get('ohlcv', {})
                    self.logger.debug(f"OHLCV timeframes: {list(ohlcv_data.keys())}")
                    for tf, df in ohlcv_data.items():
                        if isinstance(df, pd.DataFrame):
                            self.logger.debug(f"- {tf}: shape {df.shape}")
                    
                    # Handle orderbook pressure calculation
                    orderbook_data = market_data.get('orderbook', {})
                    if orderbook_data:
                        try:
                            bid_price, ask_price = (
                                orderbook_data.get('bids', [[0, 0]])[0][0],
                                orderbook_data.get('asks', [[0, 0]])[0][0]
                            )
                            spread = ask_price - bid_price
                            bid_volume = sum(bid[1] for bid in orderbook_data.get('bids', [])[:10])
                            ask_volume = sum(ask[1] for ask in orderbook_data.get('asks', [])[:10])
                            imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume) if (bid_volume + ask_volume) > 0 else 0
                            
                            self.logger.debug(f"\nOrderbook Pressure Analysis:")
                            self.logger.debug(f"  Bid pressure: {bid_volume:.2f}, Ask pressure: {ask_volume:.2f}")
                            self.logger.debug(f"  Adjusted - Bid: {bid_volume * 1.53:.2f}, Ask: {ask_volume * 1.65:.2f}")
                            bid_concentration = orderbook_data.get('bids', [[0, 0]])[:3][0][1] / bid_volume if bid_volume > 0 else 0
                            ask_concentration = orderbook_data.get('asks', [[0, 0]])[:3][0][1] / ask_volume if ask_volume > 0 else 0
                            self.logger.debug(f"  Concentration - Bid: {bid_concentration:.2f}, Ask: {ask_concentration:.2f}")
                            
                            spread_pct = spread / bid_price if bid_price > 0 else 0
                            spread_factor = 1 - min(spread_pct * 100, 1)  # Closer spread = higher factor
                            
                            self.logger.debug(f"  Spread: {spread:.2f} ({spread_pct:.4%}), Factor: {spread_factor:.2f}")
                            
                            raw_imbalance = imbalance
                            adjusted_imbalance = imbalance - (ask_concentration - bid_concentration) * 0.1
                            
                            self.logger.debug(f"  Imbalance: {raw_imbalance:.4f}, Adjusted: {adjusted_imbalance:.4f}")
                            
                            # Calculate a score (0-100) with 50 being neutral
                            score = 50 + (adjusted_imbalance * 50)
                            
                            # Apply spread factor to reduce score impact with wider spreads
                            final_score = 50 + (score - 50) * spread_factor
                            
                            self.logger.debug(f"  Final score: {final_score:.2f}")
                            
                            if abs(adjusted_imbalance) > 0.1:
                                direction = "bid dominance" if adjusted_imbalance > 0 else "ask dominance"
                                self.logger.info(f"Significant orderbook imbalance: {adjusted_imbalance:.2f} ({direction})")
                        except Exception as e:
                            self.logger.error(f"Error in orderbook analysis: {str(e)}")
                    
                    transformed_data = {
                        'orderbook': orderbook_data,
                        'trades': self._process_trades(market_data.get('trades', []))
                    }
                except Exception as e:
                    self.logger.error(f"Error transforming orderbook data: {str(e)}")
                    transformed_data = {
                        'orderbook': {},
                        'trades': []
                    }
                
            elif indicator_type == 'sentiment':
                # Sentiment indicators need sentiment data and OHLCV for context
                try:
                    sentiment_indicator = self.indicators['sentiment']
                    
                    # Log OHLCV timeframes for context
                    ohlcv_data = market_data.get('ohlcv', {})
                    self.logger.debug(f"OHLCV timeframes: {list(ohlcv_data.keys())}")
                    for tf, df in ohlcv_data.items():
                        if isinstance(df, pd.DataFrame):
                            self.logger.debug(f"- {tf}: shape {df.shape}")
                    
                    transformed_data = {
                        'sentiment': market_data.get('sentiment', {}),
                        'ohlcv': ohlcv_data
                    }
                except Exception as e:
                    self.logger.error(f"Error transforming sentiment data: {str(e)}")
                    transformed_data = {
                        'sentiment': {},
                        'ohlcv': {}
                    }
                
            elif indicator_type == 'price_structure':
                # Price structure indicators need OHLCV, orderbook, trades, and ticker
                # Make sure OHLCV data uses the right timeframe keys
                try:
                    price_structure_indicator = self.indicators['price_structure']
                    
                    # Check and initialize required attributes for price structure analysis
                    self._setup_price_structure_attributes(price_structure_indicator)
                    
                    # Get OHLCV data with potential timeframe mapping
                    ohlcv_data = market_data.get('ohlcv', {})
                    
                    # Log available and required timeframes
                    available_timeframes = set(ohlcv_data.keys())
                    required_timeframes = set(getattr(price_structure_indicator, 'required_timeframes', []))
                    
                    self.logger.debug(f"Available timeframes: {available_timeframes}")
                    self.logger.debug(f"Required timeframes: {required_timeframes}")
                    
                    # Initialize mapping dictionaries for ease of reference
                    tf_map = price_structure_indicator.timeframe_map if hasattr(price_structure_indicator, 'timeframe_map') else {}
                    rev_map = price_structure_indicator.reverse_timeframe_map if hasattr(price_structure_indicator, 'reverse_timeframe_map') else {}
                    
                    # Create a more comprehensive mapping with variations
                    complete_rev_map = {}
                    for key, value in rev_map.items():
                        complete_rev_map[key] = value
                        # Add common variations
                        if key.isdigit():
                            complete_rev_map[f"{key}m"] = value
                        elif key.endswith('m') and key[:-1].isdigit():
                            complete_rev_map[key[:-1]] = value
                    
                    if required_timeframes and not required_timeframes.issubset(available_timeframes):
                        missing_timeframes = required_timeframes - available_timeframes
                        self.logger.warning(f"Missing timeframes for price structure analysis: {missing_timeframes}")
                        
                        # Try to map available timeframes to required timeframes
                        available_with_aliases = set()
                        for avail_tf in available_timeframes:
                            available_with_aliases.add(avail_tf)
                            if avail_tf in complete_rev_map:
                                available_with_aliases.add(complete_rev_map[avail_tf])
                        
                        # Check again with aliases
                        still_missing = required_timeframes - available_with_aliases
                        if still_missing:
                            self.logger.warning(f"Still missing timeframes after alias check: {still_missing}")
                        else:
                            self.logger.info("All required timeframes found when considering aliases")
                        
                        # Check if we have at least one required timeframe
                        if not required_timeframes.intersection(available_with_aliases):
                            self.logger.error("No required timeframes available for price structure analysis")
                    
                    # Validate and prepare timeframes
                    transformed_ohlcv = self._validate_and_prepare_timeframes(ohlcv_data, price_structure_indicator)
                    
                    # Check if we got valid data back
                    if not transformed_ohlcv:
                        self.logger.warning("Could not prepare timeframe data for price structure analysis")
                        # Create empty DataFrames for missing timeframes
                        empty_df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
                        transformed_ohlcv = {tf: empty_df for tf in required_timeframes}
                    
                    # Check if all required timeframes are present
                    transformed_keys = set(transformed_ohlcv.keys())
                    if required_timeframes and not required_timeframes.issubset(transformed_keys):
                        missing = required_timeframes - transformed_keys
                        # Don't log an error if we resolved the timeframes via aliases
                        if missing:
                            self.logger.debug(f"Still missing timeframes after transformation: {missing}")
                            self.logger.debug(f"Available transformed timeframes: {transformed_keys}")
                            
                            # Try to fix the issue by creating copies of timeframes
                            fixed = False
                            for missing_tf in missing:
                                self.logger.info(f"Attempting to fix missing timeframe: {missing_tf}")
                                
                                # Log what we have and what we need
                                self.logger.debug(f"Available transformed timeframes: {transformed_keys}")
                                self.logger.debug(f"Required timeframes: {required_timeframes}")
                                
                                # Try to find a match based on interval values
                                if hasattr(price_structure_indicator, 'timeframe_map'):
                                    missing_interval = tf_map.get(missing_tf)
                                    
                                    if missing_interval:
                                        self.logger.debug(f"Missing interval: {missing_interval}")
                                        
                                        # Try to find a match in transformed keys first
                                        for existing_tf in transformed_keys:
                                            if existing_tf in tf_map and tf_map[existing_tf] == missing_interval:
                                                # Same interval, use directly
                                                transformed_ohlcv[missing_tf] = transformed_ohlcv[existing_tf].copy()
                                                self.logger.info(f"Fixed by copying from {existing_tf} (same interval)")
                                                fixed = True
                                                break
                                            
                                            # Try reverse mapping
                                            if existing_tf in complete_rev_map and complete_rev_map[existing_tf] == missing_tf:
                                                transformed_ohlcv[missing_tf] = transformed_ohlcv[existing_tf].copy()
                                                self.logger.info(f"Fixed via reverse mapping: {existing_tf} → {missing_tf}")
                                                fixed = True
                                                break
                                        
                                        # If not found in transformed keys, look in original data
                                    # If we still couldn't fix, just duplicate another timeframe
                                    if not fixed:
                                        # Just use any available timeframe
                                        source_tf = list(transformed_keys)[0]
                                        transformed_ohlcv[missing_tf] = transformed_ohlcv[source_tf].copy()
                                        self.logger.warning(f"Last resort fix: copied {source_tf} to {missing_tf}")
                                        fixed = True
                            
                            # If we fixed it, update our check
                            if fixed:
                                transformed_keys = set(transformed_ohlcv.keys())
                                missing = required_timeframes - transformed_keys
                                if not missing:
                                    self.logger.info("Successfully fixed all missing timeframes!")
                                else:
                                    self.logger.warning(f"Still missing timeframes after fix attempt: {missing}")
                    
                    transformed_data = {
                        'ohlcv': transformed_ohlcv,
                        'orderbook': market_data.get('orderbook', {}),
                        'trades': self._process_trades(market_data.get('trades', [])),
                        'ticker': market_data.get('ticker', {})
                    }
                    
                except Exception as e:
                    self.logger.error(f"Error preparing price structure data: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    # Create default data structure with empty DataFrames for required timeframes
                    price_structure_indicator = self.indicators['price_structure']
                    required_timeframes = getattr(price_structure_indicator, 'required_timeframes', 
                                                ['base', 'ltf', 'mtf', 'htf'])
                    empty_df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
                    transformed_data = {
                        'ohlcv': {tf: empty_df for tf in required_timeframes},
                        'orderbook': market_data.get('orderbook', {}),
                        'trades': self._process_trades(market_data.get('trades', [])),
                        'ticker': market_data.get('ticker', {})
                    }
            
            self.logger.debug(f"Transformed data keys: {list(transformed_data.keys())}")
            self.flow.log_transform(indicator_type, list(transformed_data.keys()))
            return transformed_data
            
        except Exception as e:
            self.logger.error(f"Error transforming data for {indicator_type}: {str(e)}")
            return {}

    def _setup_price_structure_attributes(self, price_structure_indicator):
        """Set up required attributes for price structure indicator."""
        # Check if timeframe_map attribute exists
        if not hasattr(price_structure_indicator, 'timeframe_map'):
            # Add timeframe_map if missing
            timeframe_map = {
                'base': '1',
                'ltf': '5',
                'mtf': '30',
                'htf': '240'
            }
            # If the config has timeframes, use those instead
            if 'timeframes' in self.config:
                        try:
                    timeframe_map = {
                        tf: str(self.config['timeframes'][tf]['interval'])
                        for tf in ['base', 'ltf', 'mtf', 'htf']
                        if tf in self.config['timeframes']
                    }
                        except Exception as e:
                    self.logger.warning(f"Error getting timeframes from config: {str(e)}")
            price_structure_indicator.timeframe_map = timeframe_map
            self.logger.info(f"Added missing timeframe_map: {timeframe_map}")
        
        # Add reverse timeframe map for recognizing interval formats
        reverse_timeframe_map = {}
        for tf, interval in price_structure_indicator.timeframe_map.items():
            reverse_timeframe_map[interval] = tf
            # Also add minute format (e.g., '1m')
            reverse_timeframe_map[f"{interval}m"] = tf
            # Add minute format for hours too
            if interval.isdigit() and int(interval) >= 60 and int(interval) % 60 == 0:
                hours = int(interval) // 60
                reverse_timeframe_map[f"{hours}h"] = tf

        # Add explicit aliases to ensure '1', '1m', and 'base' are recognized as the same
        if 'base' in timeframe_map:
            reverse_timeframe_map['base'] = 'base'
            base_interval = timeframe_map['base']
            reverse_timeframe_map[base_interval] = 'base'
            reverse_timeframe_map[f"{base_interval}m"] = 'base'
            
        price_structure_indicator.reverse_timeframe_map = reverse_timeframe_map
        self.logger.info(f"Added reverse timeframe map: {reverse_timeframe_map}")
        
        # Ensure required timeframes attribute is set
        if not hasattr(price_structure_indicator, 'required_timeframes'):
            price_structure_indicator.required_timeframes = ['base', 'ltf', 'mtf', 'htf']
            self.logger.info("Added missing required_timeframes attribute")
            
        # Ensure timeframe_weights attribute is set
        if not hasattr(price_structure_indicator, 'timeframe_weights'):
            price_structure_indicator.timeframe_weights = {
                'base': 0.4,
                'ltf': 0.3,
                'mtf': 0.2,
                'htf': 0.1
            }
            self.logger.info("Added missing timeframe_weights attribute")

    def _validate_and_prepare_timeframes(self, ohlcv_data: Dict[str, Any], indicator) -> Dict[str, Any]:
        """Validate and prepare timeframes for price structure analysis with enhanced error handling."""
        try:
            self.logger.debug(f"Validating and preparing timeframes for {indicator.indicator_type} analysis")
            
            # Validate input
            if not isinstance(ohlcv_data, dict):
                self.logger.error(f"Invalid OHLCV data type: {type(ohlcv_data)}, expected dictionary")
            return {}
                
            if not ohlcv_data:
                self.logger.error("Empty OHLCV data dictionary")
                return {}
                
            # Create a more comprehensive mapping that includes all possible timeframe formats
            all_timeframe_formats = {}
            
            # Add standard named timeframes
            for tf in ['base', 'ltf', 'mtf', 'htf']:
                all_timeframe_formats[tf] = tf
            
            # Add numeric and formatted timeframes from indicator.timeframe_map
            if hasattr(indicator, 'timeframe_map'):
                for named_tf, interval_value in indicator.timeframe_map.items():
                    all_timeframe_formats[interval_value] = named_tf
                    all_timeframe_formats[f"{interval_value}m"] = named_tf
                    # Add hour format if applicable
                    if interval_value.isdigit() and int(interval_value) >= 60 and int(interval_value) % 60 == 0:
                        hours = int(interval_value) // 60
                        all_timeframe_formats[f"{hours}h"] = named_tf
                    
            # Add any reverse mappings
            if hasattr(indicator, 'reverse_timeframe_map'):
                for format_key, named_tf in indicator.reverse_timeframe_map.items():
                    all_timeframe_formats[format_key] = named_tf
                    
            # Handle special case for '1', '1m', and 'base'
            if 'base' in all_timeframe_formats:
                all_timeframe_formats['1'] = 'base'
                all_timeframe_formats['1m'] = 'base'
                all_timeframe_formats['base'] = 'base'
                
            self.logger.debug(f"Comprehensive timeframe mapping: {all_timeframe_formats}")
                
            # Check which timeframes we have in the data
            available_timeframes = set(ohlcv_data.keys())
            required_timeframes = set(getattr(indicator, 'required_timeframes', []))
            
            if not required_timeframes:
                self.logger.warning("No required timeframes specified, using all available timeframes")
                required_timeframes = available_timeframes
            
            # Log which timeframes are present and which are missing
            missing_timeframes = required_timeframes - available_timeframes
            present_timeframes = required_timeframes & available_timeframes
            
            self.logger.debug(f"Available timeframes: {', '.join(available_timeframes)}")
            self.logger.debug(f"Required timeframes: {', '.join(required_timeframes)}")
            
            # Create a mapping from available formats to required timeframes
            available_to_required = {}
            for avail_tf in available_timeframes:
                # First check if this is a standard required timeframe
                if avail_tf in required_timeframes:
                    available_to_required[avail_tf] = avail_tf
                # Then check if it maps to a required timeframe
                elif avail_tf in all_timeframe_formats and all_timeframe_formats[avail_tf] in required_timeframes:
                    available_to_required[avail_tf] = all_timeframe_formats[avail_tf]
                    
            self.logger.debug(f"Available to required mapping: {available_to_required}")
            
            if missing_timeframes:
                self.logger.warning(f"Missing timeframes: {', '.join(missing_timeframes)}")
                
            if not available_to_required:
                self.logger.error("No available timeframes map to required timeframes")
                # Create empty DataFrames as placeholders
                return {tf: pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume']) 
                        for tf in required_timeframes}
            
            # Create a new dictionary with the required timeframe keys
            prepared_data = {}
            
            # First, process timeframes that are directly available
            for tf in required_timeframes:
                if tf in ohlcv_data:
                    # Validate DataFrame
                    if isinstance(ohlcv_data[tf], pd.DataFrame):
                        if ohlcv_data[tf].empty:
                            self.logger.warning(f"Empty DataFrame for timeframe {tf}")
                            continue
                            
                        # Check required columns
                        required_columns = ['open', 'high', 'low', 'close', 'volume']
                        missing_columns = [col for col in required_columns if col not in ohlcv_data[tf].columns]
                        
                        if missing_columns:
                            self.logger.warning(f"Missing columns in {tf} DataFrame: {', '.join(missing_columns)}")
                            continue
                            
                        # Validate data types
                        for col in required_columns:
                            if col in ohlcv_data[tf].columns and not np.issubdtype(ohlcv_data[tf][col].dtype, np.number):
                                self.logger.warning(f"Non-numeric data in {tf} DataFrame column {col}: {ohlcv_data[tf][col].dtype}")
                                # Try to convert to numeric
                                try:
                                    ohlcv_data[tf][col] = pd.to_numeric(ohlcv_data[tf][col], errors='coerce')
                                except Exception as e:
                                    self.logger.error(f"Failed to convert {tf} DataFrame column {col} to numeric: {str(e)}")
                                    continue
                        
                        # Check for NaN values
                        nan_counts = ohlcv_data[tf][required_columns].isna().sum()
                        if nan_counts.sum() > 0:
                            self.logger.warning(f"NaN values in {tf} DataFrame: {nan_counts.to_dict()}")
                            # Fill NaN values if less than 10% of the data
                            if nan_counts.max() < len(ohlcv_data[tf]) * 0.1:
                                self.logger.info(f"Filling NaN values in {tf} DataFrame")
                                ohlcv_data[tf] = ohlcv_data[tf].fillna(method='ffill').fillna(method='bfill')
                            else:
                                self.logger.warning(f"Too many NaN values in {tf} DataFrame, skipping")
                                continue
                        
                        prepared_data[tf] = ohlcv_data[tf]
                    else:
                        self.logger.warning(f"Invalid data type for timeframe {tf}: {type(ohlcv_data[tf])}, expected DataFrame")
                        # Try to convert dictionary to DataFrame
                        if isinstance(ohlcv_data[tf], dict) and 'data' in ohlcv_data[tf]:
                            try:
                                if isinstance(ohlcv_data[tf]['data'], pd.DataFrame):
                                    prepared_data[tf] = ohlcv_data[tf]['data']
                                    self.logger.info(f"Extracted DataFrame from dictionary for {tf}")
                                elif isinstance(ohlcv_data[tf]['data'], list) and ohlcv_data[tf]['data']:
                                    df = pd.DataFrame(ohlcv_data[tf]['data'])
                                    if len(df.columns) >= 5:  # Basic validation
                                        df.columns = ['timestamp', 'open', 'high', 'low', 'close'] + list(df.columns[5:])
                                        prepared_data[tf] = df
                                        self.logger.info(f"Converted list to DataFrame for {tf}")
                            except Exception as e:
                                self.logger.error(f"Failed to convert data for {tf}: {str(e)}")
            
            # Then, try to map from available timeframes to missing required timeframes
            missing_after_direct = [tf for tf in required_timeframes if tf not in prepared_data]
            if missing_after_direct:
                self.logger.info(f"Looking for alternative timeframes for: {', '.join(missing_after_direct)}")
                
                # For each missing timeframe, look for an available timeframe that maps to it
                for missing_tf in missing_after_direct:
                    found = False
                    
                    # First try to find a direct mapping from available timeframes
                    for avail_tf, mapped_tf in available_to_required.items():
                        if mapped_tf == missing_tf:
                            self.logger.info(f"Found mapping from {avail_tf} to {missing_tf}")
                            if isinstance(ohlcv_data[avail_tf], pd.DataFrame) and not ohlcv_data[avail_tf].empty:
                                prepared_data[missing_tf] = ohlcv_data[avail_tf].copy()
                                found = True
                                break
                                
                    # If we didn't find a direct mapping, try to find any format that maps to the same timeframe
                    if not found:
                        # Try to find based on interval values (e.g., '1' ⟶ 'base')
                        if hasattr(indicator, 'timeframe_map'):
                            interval_value = indicator.timeframe_map.get(missing_tf)
                            if interval_value:
                                # Look for this interval in available timeframes
                                for avail_tf in available_timeframes:
                                    if avail_tf == interval_value or avail_tf == f"{interval_value}m":
                                        if isinstance(ohlcv_data[avail_tf], pd.DataFrame) and not ohlcv_data[avail_tf].empty:
                                            self.logger.info(f"Found interval mapping from {avail_tf} to {missing_tf}")
                                            prepared_data[missing_tf] = ohlcv_data[avail_tf].copy()
                                            found = True
                                            break
                
                    # If still not found, and this is 'base' timeframe, try '1' or '1m'
                    if not found and missing_tf == 'base':
                        for base_format in ['1', '1m']:
                            if base_format in ohlcv_data and isinstance(ohlcv_data[base_format], pd.DataFrame) and not ohlcv_data[base_format].empty:
                                self.logger.info(f"Using {base_format} for base timeframe")
                                prepared_data['base'] = ohlcv_data[base_format].copy()
                                found = True
                                break
                
                    # If still not found, try to derive from another timeframe or use empty DataFrame
                    if not found:
                        if prepared_data:  # If we have at least one prepared timeframe
                            # Just use the first available timeframe as a fallback
                            source_tf = list(prepared_data.keys())[0]
                            self.logger.warning(f"Could not find data for {missing_tf}, copying from {source_tf} as fallback")
                            prepared_data[missing_tf] = prepared_data[source_tf].copy()
                        else:
                            self.logger.error(f"No data available to derive {missing_tf}")
                            prepared_data[missing_tf] = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            
            # Check if we have at least one valid timeframe
            if not prepared_data:
                self.logger.error("No valid timeframes available for analysis")
                # Create empty DataFrames as placeholders to avoid errors
                for tf in required_timeframes:
                    prepared_data[tf] = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
                self.logger.warning("Using empty DataFrames as placeholders")
            else:
                self.logger.info(f"Successfully prepared {len(prepared_data)} timeframes: {', '.join(prepared_data.keys())}")
            
            return prepared_data
            
        except Exception as e:
            self.logger.error(f"Error preparing timeframes: {str(e)}")
            self.logger.error(traceback.format_exc())
            return ohlcv_data

    def _validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Validate market data with enhanced error handling and type validation."""
        try:
            self.logger.debug("\n=== Validating Market Data ===")
            self.logger.debug(f"Market data type: {type(market_data)}")
            
            # Basic structure check
            if not isinstance(market_data, dict):
                self.logger.error(f"Market data must be a dictionary, got {type(market_data)}")
                return False
            
            # Log available keys
            self.logger.debug(f"Available keys: {list(market_data.keys())}")
            
            # Check minimum required data
            required_fields = ['symbol', 'ohlcv']
            missing_fields = [field for field in required_fields if field not in market_data]
            if missing_fields:
                self.logger.error(f"Missing required data: {', '.join(missing_fields)}")
                return False
            
            # Validate symbol
            symbol = market_data.get('symbol')
            if not isinstance(symbol, str) or not symbol:
                self.logger.error(f"Invalid symbol: {symbol} (type: {type(symbol)})")
                return False
                
            # Validate exchange
            if 'exchange' in market_data:
                exchange = market_data.get('exchange')
                if not isinstance(exchange, str) or not exchange:
                    self.logger.warning(f"Invalid exchange identifier: {exchange} (type: {type(exchange)})")
                    
            # Validate timestamp
            if 'timestamp' in market_data:
                timestamp = market_data.get('timestamp')
                if not isinstance(timestamp, (int, float)) or timestamp <= 0:
                    self.logger.warning(f"Invalid timestamp: {timestamp} (type: {type(timestamp)})")
                    # Try to fix by setting current timestamp
                    market_data['timestamp'] = int(time.time() * 1000)
                    self.logger.info(f"Set timestamp to current time: {market_data['timestamp']}")
            
            # Validate OHLCV data structure
            ohlcv = market_data.get('ohlcv', {})
            self.logger.debug(f"OHLCV data type: {type(ohlcv)}")
            
            if not isinstance(ohlcv, dict):
                self.logger.error(f"OHLCV data must be a dictionary, got {type(ohlcv)}")
                return False
            
            if not ohlcv:
                self.logger.error("Empty OHLCV data dictionary")
                return False
                
            # Log timeframes
            self.logger.debug(f"Available timeframes: {list(ohlcv.keys())}")
            
            # Check for at least one valid timeframe
            valid_timeframes = []
            for tf, data in ohlcv.items():
                is_valid = False
                self.logger.debug(f"Checking timeframe {tf} (type: {type(data)})")
                
                if isinstance(data, pd.DataFrame):
                    if data.empty:
                        self.logger.warning(f"Empty DataFrame for timeframe {tf}")
                    else:
                        required_columns = ['open', 'high', 'low', 'close', 'volume']
                        missing_columns = [col for col in required_columns if col not in data.columns]
                        if missing_columns:
                            self.logger.warning(f"Missing columns in {tf} DataFrame: {', '.join(missing_columns)}")
                        else:
                            is_valid = True
                            self.logger.debug(f"Valid DataFrame for timeframe {tf}: shape {data.shape}")
                elif isinstance(data, dict) and 'data' in data:
                    if isinstance(data['data'], pd.DataFrame):
                        if data['data'].empty:
                            self.logger.warning(f"Empty DataFrame in dictionary for timeframe {tf}")
                        else:
                            is_valid = True
                            self.logger.debug(f"Valid DataFrame in dictionary for timeframe {tf}: shape {data['data'].shape}")
                    elif isinstance(data['data'], list) and data['data']:
                        self.logger.debug(f"List data for timeframe {tf}: {len(data['data'])} items")
                        # Assume list data is valid if not empty
                        is_valid = True
                else:
                    self.logger.warning(f"Unsupported data type for timeframe {tf}: {type(data)}")
                
                if is_valid:
                    valid_timeframes.append(tf)
                
            if not valid_timeframes:
                self.logger.error("No valid timeframes found in OHLCV data")
                return False
            
            self.logger.info(f"Valid timeframes found: {valid_timeframes}")
            
            # Validate other optional data components with detailed logging
            
            # Orderbook validation
            if 'orderbook' in market_data:
                self.logger.debug("Validating orderbook data")
                orderbook = market_data['orderbook']
                if not isinstance(orderbook, dict):
                    self.logger.warning(f"Invalid orderbook data type: {type(orderbook)}")
                else:
                    # Check required fields
                    ob_required = ['bids', 'asks', 'timestamp']
                    ob_missing = [f for f in ob_required if f not in orderbook]
                    if ob_missing:
                        self.logger.warning(f"Missing orderbook fields: {', '.join(ob_missing)}")
                    else:
                        # Validate bids and asks
                        for side in ['bids', 'asks']:
                            if not isinstance(orderbook[side], list):
                                self.logger.warning(f"Invalid {side} type: {type(orderbook[side])}")
                            elif not orderbook[side]:
                                self.logger.warning(f"Empty {side} list")
                            else:
                                self.logger.debug(f"Valid {side} data: {len(orderbook[side])} levels")
                                
            # Trades validation
            if 'trades' in market_data:
                self.logger.debug("Validating trades data")
                trades = market_data['trades']
                if not isinstance(trades, list):
                    self.logger.warning(f"Invalid trades data type: {type(trades)}")
                elif not trades:
                    self.logger.warning("Empty trades list")
                else:
                    self.logger.debug(f"Found {len(trades)} trades")
                    # Check sample trade
                    if len(trades) > 0:
                        sample = trades[0]
                        if isinstance(sample, dict):
                            self.logger.debug(f"Sample trade keys: {list(sample.keys())}")
                
            # Ticker validation
            if 'ticker' in market_data:
                self.logger.debug("Validating ticker data")
                ticker = market_data['ticker']
                if not isinstance(ticker, dict):
                    self.logger.warning(f"Invalid ticker data type: {type(ticker)}")
                else:
                    self.logger.debug(f"Ticker keys: {list(ticker.keys())}")
                    # Check for last price
                    if 'last' in ticker or 'last_price' in ticker:
                        self.logger.debug("Found last price in ticker data")
                
            # Create validator instance for additional checks
            validator = DataValidator()
            
            # Basic structure validation using DataValidator
            if not await validator.validate_market_data(market_data):
                self.logger.warning("DataValidator reported issues with market data")
                # Continue anyway - we'll try to work with what we have
            
            # Standardize OHLCV data
            if 'ohlcv' in market_data:
                market_data['ohlcv'] = self._standardize_timeframes(market_data['ohlcv'])
            
            # Validate using BaseIndicator's validation logic - but don't fail if one indicator fails
            valid_indicators = 0
            total_indicators = len(self.indicators)
            indicator_results = {}
            
            self.logger.debug("\n=== Indicator Validation ===")
            for indicator_name, indicator in self.indicators.items():
                self.logger.debug(f"\nValidating data for {indicator_name}")
                try:
                    is_valid = indicator.validate_input(market_data)
                    indicator_results[indicator_name] = is_valid
                    if is_valid:
                        valid_indicators += 1
                        self.logger.debug(f"✓ {indicator_name} validation passed")
                    else:
                        self.logger.warning(f"✗ {indicator_name} validation failed")
                except Exception as e:
                    self.logger.error(f"Error validating {indicator_name}: {str(e)}")
                    indicator_results[indicator_name] = False
            
            # Calculate validation ratio and log detailed report
            validation_ratio = valid_indicators / total_indicators if total_indicators > 0 else 0
            self.logger.info(f"Indicator validation: {valid_indicators}/{total_indicators} ({validation_ratio:.0%})")
            
            # Log indicator validation details
            self.logger.debug("\nIndicator Validation Results:")
            for name, result in indicator_results.items():
                self.logger.debug(f"{name}: {'✓' if result else '✗'}")
            
            # For highly permissive validation, accept with warning if at least one indicator passed
            if validation_ratio < 0.6 and validation_ratio > 0:
                self.logger.warning(f"Only {validation_ratio:.0%} of indicators validated successfully")
                # Don't fail completely - we'll still try to analyze with partial data
            elif validation_ratio == 0:
                self.logger.error("All indicators failed validation")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return False

    def _normalize_weights(self) -> None:
        """Normalize indicator weights to sum to 1.0."""
        total = sum(self.weights.values())
        if not np.isclose(total, 1.0):
            self.logger.warning(f"Component weights sum to {total}, normalizing")
            self.weights = {k: v/total for k, v in self.weights.items()}

    def _calculate_confluence_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted confluence score."""
        try:
            weighted_sum = sum(
                scores[indicator] * self.weights.get(indicator, 0)
                for indicator in scores
            )
            return float(np.clip(weighted_sum, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating confluence score: {str(e)}")
            return 50.0

    def _calculate_reliability(self, scores: Dict[str, float]) -> float:
        """Calculate reliability of the analysis."""
        try:
            # Count non-default scores
            valid_scores = sum(1 for score in scores.values() if score != 50.0)
            total_indicators = len(scores)
            
            return valid_scores / total_indicators if total_indicators > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating reliability: {str(e)}")
            return 0.0

    def _get_default_response(self) -> Dict[str, Any]:
        """Return a default analysis response when analysis fails"""
        return {
            'timestamp': int(time.time() * 1000),
            'score': 50.0,  # Neutral score
            'signal': 'neutral',
            'confidence': 0.0,
            'components': {
                'technical': {'score': 50.0, 'signals': {}},
                'orderflow': {'score': 50.0, 'signals': {}},
                'sentiment': {'score': 50.0, 'signals': {}},
                'orderbook': {'score': 50.0, 'signals': {}},
                'price_structure': {'score': 50.0, 'signals': {}}
            },
            'weights': self.weights,
            'metadata': {
                'error': 'Analysis failed',
                'calculation_time': time.time()
            }
        }

    def _standardize_timeframes(self, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert timeframes to standard format with enhanced validation and error handling."""
        try:
            self.logger.debug("\n=== Timeframe Standardization ===")
            self.logger.debug(f"Input timeframes: {list(ohlcv_data.keys())}")
            
            # Validate input
            if not isinstance(ohlcv_data, dict):
                self.logger.error(f"OHLCV data must be a dictionary, got {type(ohlcv_data)}")
                return {}
            
            if not ohlcv_data:
                self.logger.error("Empty OHLCV data dictionary")
                return {}
                
            # Initialize standardized dictionary with None values
            standardized = {
                'base': None,
                'ltf': None,
                'mtf': None,
                'htf': None
            }
            
            # Process each timeframe from input
            for tf_key, tf_data in ohlcv_data.items():
                # Determine which standard timeframe this corresponds to
                target_tf = None
                
                # Check if key directly matches a standard timeframe
                if tf_key in standardized:
                    target_tf = tf_key
                else:
                    # Try to match based on numeric value (e.g., '1' -> 'base', '5' -> 'ltf')
                    tf_map = {
                        '1': 'base',
                        '5': 'ltf',
                        '30': 'mtf',
                        '240': 'htf',
                        '1m': 'base',
                        '5m': 'ltf',
                        '30m': 'mtf',
                        '4h': 'htf',
                        '60': 'mtf',  # Fallback for 1h to mtf
                        '1h': 'mtf',
                        '60m': 'mtf',
                        '120': 'mtf',
                        '120m': 'mtf',
                        '2h': 'mtf',
                        '180': 'mtf',
                        '180m': 'mtf',
                        '3h': 'mtf',
                        '360': 'htf',
                        '360m': 'htf',
                        '6h': 'htf',
                        '720': 'htf',
                        '720m': 'htf',
                        '12h': 'htf',
                        '1440': 'htf',
                        '1440m': 'htf',
                        '24h': 'htf',
                        '1d': 'htf',
                        # Add more mappings as needed
                    }
                    if tf_key in tf_map:
                        target_tf = tf_map[tf_key]
                    else:
                        # Try more sophisticated matching (e.g., '1min', '01m', etc.)
                        try:
                            # First extract any numeric part
                            numeric_part = re.search(r'(\d+)', tf_key)
                            if numeric_part:
                                numeric_value = int(numeric_part.group(1))
                                
                                # Match by numeric value
                                if numeric_value == 1:
                                    target_tf = 'base'
                                elif numeric_value == 5:
                                    target_tf = 'ltf'
                                elif 15 <= numeric_value <= 60:
                                    target_tf = 'mtf'
                                elif numeric_value >= 120:
                                    target_tf = 'htf'
                                    
                                self.logger.debug(f"Matched {tf_key} to {target_tf} based on numeric value {numeric_value}")
                        except Exception as e:
                            self.logger.error(f"Error in sophisticated timeframe matching: {e}")
                
                # If we found a target timeframe, process the data
                if target_tf:
                    # Handle different input formats
                    if isinstance(tf_data, pd.DataFrame):
                        # Validate DataFrame
                        if tf_data.empty:
                            self.logger.warning(f"Empty DataFrame for timeframe {tf_key}")
                            continue
                            
                        # Check required columns
                        required_columns = ['open', 'high', 'low', 'close', 'volume']
                        missing_columns = [col for col in required_columns if col not in tf_data.columns]
                        
                        if missing_columns:
                            self.logger.warning(f"Missing columns in {tf_key} DataFrame: {', '.join(missing_columns)}")
                            
                            # Try to adapt column names if they follow a pattern
                            if len(tf_data.columns) >= 5:
                                self.logger.info(f"Attempting to adapt column names for {tf_key}")
                                # OHLCV data is often in this order
                                if len(missing_columns) == len(required_columns):  # All columns missing
                                    column_map = dict(zip(tf_data.columns[:5], required_columns))
                                    tf_data = tf_data.rename(columns=column_map)
                                    self.logger.info(f"Renamed columns for {tf_key}: {column_map}")
                        
                        # Check data types and convert if needed
                        for col in [c for c in required_columns if c in tf_data.columns]:
                            if not np.issubdtype(tf_data[col].dtype, np.number):
                                self.logger.warning(f"Non-numeric data in {tf_key} column {col}: {tf_data[col].dtype}")
                                try:
                                    tf_data[col] = pd.to_numeric(tf_data[col], errors='coerce')
                                    self.logger.info(f"Converted {tf_key} column {col} to numeric")
                                except Exception as e:
                                    self.logger.error(f"Failed to convert {tf_key} column {col}: {str(e)}")
                        
                        standardized[target_tf] = tf_data
                    elif isinstance(tf_data, dict) and 'data' in tf_data:
                        # Extract DataFrame from dictionary
                        if isinstance(tf_data['data'], pd.DataFrame):
                            standardized[target_tf] = tf_data['data']
                        elif isinstance(tf_data['data'], list) and tf_data['data']:
                            # Convert list to DataFrame
                            try:
                                df = pd.DataFrame(tf_data['data'])
                                if len(df.columns) >= 5:
                                    df.columns = ['timestamp', 'open', 'high', 'low', 'close'] + list(df.columns[5:])
                                    standardized[target_tf] = df
                                    self.logger.info(f"Converted list to DataFrame for {tf_key}")
                            except Exception as e:
                                self.logger.error(f"Failed to convert list data for {tf_key}: {str(e)}")
                    else:
                        self.logger.warning(f"Unsupported data type for {tf_key}: {type(tf_data)}")
            
            # Log standardization results
            self.logger.debug("\nStandardization Results:")
            for tf, data in standardized.items():
                if isinstance(data, pd.DataFrame):
                    self.logger.debug(f"{tf}: DataFrame shape {data.shape}")
                else:
                    self.logger.debug(f"{tf}: Invalid data type {type(data)}")
            
            # Validate all timeframes are present
            missing = [tf for tf, data in standardized.items() if not isinstance(data, pd.DataFrame)]
            if missing:
                self.logger.warning(f"Missing or invalid timeframes after standardization: {missing}")
                
                # Try to fill missing timeframes with derived data if possible
                for missing_tf in missing:
                    filled = self._derive_missing_timeframe(standardized, missing_tf)
                    if filled:
                        self.logger.info(f"Derived data for missing timeframe {missing_tf}")
                        
            # Final validation: ensure we have at least one valid timeframe
            valid_timeframes = [tf for tf, data in standardized.items() if isinstance(data, pd.DataFrame) and not data.empty]
            if not valid_timeframes:
                self.logger.error("No valid timeframes after standardization")
                # Create empty DataFrames as placeholders
                for tf in standardized:
                    standardized[tf] = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
                self.logger.warning("Using empty DataFrames as placeholders")
            else:
                self.logger.info(f"Successfully standardized {len(valid_timeframes)} timeframes: {valid_timeframes}")
            
            return standardized
            
        except Exception as e:
            self.logger.error(f"Error standardizing timeframes: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return ohlcv_data
            
    def _derive_missing_timeframe(self, timeframes: Dict[str, pd.DataFrame], missing_tf: str) -> bool:
        """Attempt to derive a missing timeframe from existing ones."""
        try:
            # Define relationships between timeframes
            derivation_map = {
                'base': {'source': ['ltf', 'mtf', 'htf'], 'method': 'downsample'},
                'ltf': {'source': ['base', 'mtf', 'htf'], 'method': 'mixed'},
                'mtf': {'source': ['ltf', 'htf'], 'method': 'upsample'},
                'htf': {'source': ['mtf'], 'method': 'upsample'}
            }
            
            if missing_tf not in derivation_map:
                return False
                
            # Check if we have any valid source timeframes
            sources = [tf for tf in derivation_map[missing_tf]['source'] 
                      if tf in timeframes and isinstance(timeframes[tf], pd.DataFrame) and not timeframes[tf].empty]
            
            if not sources:
                return False
                
            # Use the first available source
            source_tf = sources[0]
            source_df = timeframes[source_tf]
            method = derivation_map[missing_tf]['method']
            
            self.logger.info(f"Attempting to derive {missing_tf} from {source_tf} using {method}")
            
            # Simple implementation - just copy data for now
            # In a real implementation, proper resampling would be applied
            timeframes[missing_tf] = source_df.copy()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error deriving timeframe {missing_tf}: {str(e)}")
            return False

    def _process_orderbook_data(self, orderbook: Dict[str, Any]) -> Dict[str, Any]:
        """Process and normalize orderbook data."""
        try:
            # Convert string values to float
            processed = {
                'bids': [[float(p), float(s)] for p, s in orderbook['bids']],
                'asks': [[float(p), float(s)] for p, s in orderbook['asks']],
                'timestamp': int(orderbook['timestamp']),
                'spread': None,  # Will be calculated
                'mid_price': None  # Will be calculated
            }
            
            # Calculate spread and mid price if we have bids and asks
            if processed['bids'] and processed['asks']:
                best_bid = processed['bids'][0][0]
                best_ask = processed['asks'][0][0]
                processed['spread'] = best_ask - best_bid
                processed['mid_price'] = (best_ask + best_bid) / 2
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Error processing orderbook data: {str(e)}")
            return None

    async def _calculate_component_score(self, component: str, market_data: Dict[str, Any]) -> float:
        """Calculate individual component score with better error handling."""
        try:
            self.logger.debug(f"\n=== Calculating {component} Score ===")
            self.logger.debug(f"Input data keys: {list(market_data.keys())}")
            
            indicator = self.indicators[component]
            
            # Pre-validate data for this component
            if not self._validate_component_data(component, market_data):
                self.logger.error(f"Invalid data for {component}")
                return 0.0
            
            # Calculate score with timing
            start = time.time()
            score = await indicator.calculate_score(market_data)
            elapsed = time.time() - start
            
            self.logger.debug(f"{component} calculation time: {elapsed:.3f}s")
            self.logger.debug(f"{component} score: {score}")
            
            return float(score)
            
        except Exception as e:
            self.logger.error(f"Error calculating {component} score: {str(e)}")
            return 0.0

    def _validate_component_data(self, component: str, market_data: Dict[str, Any]) -> bool:
        """Validate data required for specific component."""
        try:
            if component == 'volume':
                return ('ohlcv' in market_data and 
                        isinstance(market_data['ohlcv'], dict) and
                        'base' in market_data['ohlcv'])
                        
            elif component == 'orderflow':
                return 'trades' in market_data and isinstance(market_data['trades'], list)
                
            elif component == 'orderbook':
                if 'orderbook' not in market_data:
                    return False
                ob = market_data['orderbook']
                return (isinstance(ob, dict) and
                        all(k in ob for k in ['bids', 'asks', 'timestamp']) and
                        isinstance(ob['bids'], list) and
                        isinstance(ob['asks'], list))
                        
            elif component == 'position':
                return 'ohlcv' in market_data
                
            elif component == 'sentiment':
                return 'sentiment' in market_data
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error validating {component} data: {str(e)}")
            return False

    def _format_response(self, scores: Dict[str, float]) -> Dict[str, Any]:
        """Format the response for the confluence analysis."""
        try:
            # Calculate final confluence score
            confluence_score = self._calculate_confluence_score(scores)
            
            # Calculate reliability score
            reliability = self._calculate_reliability(scores)

            return {
                'timestamp': pd.Timestamp.now().isoformat(),
                'confluence_score': confluence_score,
                'reliability': reliability,
                'components': scores,
                'metadata': {
                    'calculation_time': 0,
                    'timings': {},
                    'errors': [],
                    'weights': self.weights
                }
            }

        except Exception as e:
            self.logger.error(f"Error formatting response: {str(e)}")
            return self._get_default_response()

    def _validate_timeframe_base(self, market_data: Dict[str, Any]) -> bool:
        """Validate timeframe base structure."""
        try:
            self.logger.debug("\n=== Validating Timeframe Base Structure ===")
            self.logger.debug(f"Market data keys: {list(market_data.keys())}")
            
            if 'timeframes' not in market_data:
                self.logger.debug("Missing timeframes data")
                self.logger.error("Missing timeframes data")
                return False
                
            # Get base timeframe from config
            base_config = self.config['timeframes']['base']
            base_interval = str(base_config['interval'])
            
            if base_interval not in market_data['timeframes']:
                self.logger.error(f"Missing base timeframe (interval {base_interval})")
                return False
                
            base_data = market_data['timeframes'][base_interval]
            if not isinstance(base_data, pd.DataFrame):
                self.logger.error(f"Invalid base data type: {type(base_data)}")
                return False
                
            # Validate DataFrame columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in base_data.columns]
            
            if missing_columns:
                self.logger.error(f"Missing required columns in base data: {missing_columns}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating timeframe base: {str(e)}")
            return False

    def validate_timeframe_structure(self, timeframe_data):
        """
        Validate the timeframe data structure has all required fields
        """
        required_fields = ['interval', 'start', 'end', 'data']
        
        if not isinstance(timeframe_data, dict):
            return False, f"Expected dict, got {type(timeframe_data)}"
        
        missing_fields = [f for f in required_fields if f not in timeframe_data]
        if missing_fields:
            return False, f"Missing required fields: {missing_fields}"
        
        if not isinstance(timeframe_data['data'], pd.DataFrame):
            return False, "Data must be a pandas DataFrame"
        
        return True, None

    def process_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and standardize market data."""
        try:
            if not isinstance(market_data, dict):
                raise ValueError("Market data must be a dictionary")
            
            # Ensure OHLCV data exists
            if 'ohlcv' not in market_data:
                raise ValueError("Missing OHLCV data")
            
            # Process each timeframe
            for tf in market_data['ohlcv']:
                tf_data = market_data['ohlcv'][tf]
                if not isinstance(tf_data.get('data'), pd.DataFrame):
                    continue
                
                # Convert to DataFrame if needed
                if isinstance(tf_data.get('data'), dict):
                    market_data['ohlcv'][tf]['data'] = pd.DataFrame(tf_data['data'])
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error processing market data: {str(e)}")
            return market_data

    def _validate_indicator_data(self, data: Dict[str, Any]) -> bool:
        """Validate data structure before passing to indicators"""
        required_keys = ['ohlcv']
        if not all(key in data for key in required_keys):
            return False
        
        if not isinstance(data['ohlcv'], dict):
            return False
        
        required_timeframes = ['base', 'ltf', 'mtf', 'htf']
        if not all(tf in data['ohlcv'] for tf in required_timeframes):
            return False
        
        return True

    def _validate_transformed_data(self, data: Dict[str, Any], indicator_name: str) -> bool:
        """Validate transformed data for specific indicator."""
        try:
            indicator = self.indicators[indicator_name]
            
            # Check required fields
            required_fields = indicator.required_data
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                self.logger.error(f"Missing required fields for {indicator_name}: {missing_fields}")
                return False
            
            # Validate OHLCV if required
            if 'ohlcv' in required_fields:
                if not self._validate_ohlcv_structure(data['ohlcv']):
                    return False
            
            # Validate orderbook if required
            if 'orderbook' in required_fields:
                if not self._validate_orderbook_structure(data['orderbook']):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating transformed data: {str(e)}")
            return False

    def _analyze_indicator_correlations(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Analyze correlations between different indicators."""
        try:
            correlations = {}
            scores = {
                name: result['score'] 
                for name, result in results.items()
            }
            
            # Calculate correlations between pairs
            for i1 in scores:
                for i2 in scores:
                    if i1 < i2:  # Avoid duplicates
                        key = f"{i1}_{i2}"
                        s1, s2 = scores[i1], scores[i2]
                        correlation = np.corrcoef([s1], [s2])[0,1]
                        correlations[key] = float(correlation)
                        
            return correlations
            
        except Exception as e:
            self.logger.error(f"Error analyzing correlations: {str(e)}")
            return {}

    def _validate_indicator_result(self, result: Dict[str, Any]) -> bool:
        """Validate indicator result format."""
        try:
            # Check result matches BaseIndicator.IndicatorResult type
            required_fields = {'score', 'components', 'signals', 'metadata'}
            if not all(f in result for f in required_fields):
                self.logger.error(f"Missing required fields: {required_fields - set(result.keys())}")
                return False
            
            # Validate score
            if not isinstance(result['score'], (int, float)):
                self.logger.error(f"Invalid score type: {type(result['score'])}")
                return False
            
            if not 0 <= result['score'] <= 100:
                self.logger.error(f"Score out of range: {result['score']}")
                return False
            
            # Validate components match indicator weights
            if not all(c in result['components'] for c in self.component_weights):
                self.logger.error("Missing component scores")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating result: {str(e)}")
            return False

    def _analyze_cross_indicator_signals(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze signals across different indicators."""
        try:
            cross_signals = {}
            
            # Extract all indicator signals
            signals = {
                name: result.get('signals', {})
                for name, result in results.items()
            }
            
            # Check primary confluence (volume, technical, orderbook)
            primary_bullish = all(
                signals.get(ind, {}).get('trend', {}).get('signal') == 'bullish'
                for ind in ['volume', 'technical', 'orderbook']
            )
            
            primary_bearish = all(
                signals.get(ind, {}).get('trend', {}).get('signal') == 'bearish'
                for ind in ['volume', 'technical', 'orderbook']
            )
            
            # Check secondary confirmation
            sentiment_bullish = signals.get('sentiment', {}).get('trend', {}).get('signal') == 'bullish'
            orderflow_bullish = signals.get('orderflow', {}).get('trend', {}).get('signal') == 'bullish'
            structure_bullish = signals.get('price_structure', {}).get('trend', {}).get('signal') == 'bullish'
            
            sentiment_bearish = signals.get('sentiment', {}).get('trend', {}).get('signal') == 'bearish'
            orderflow_bearish = signals.get('orderflow', {}).get('trend', {}).get('signal') == 'bearish'
            structure_bearish = signals.get('price_structure', {}).get('trend', {}).get('signal') == 'bearish'
            
            # Determine confluence level
            if primary_bullish:
                secondary_confirms = sum([sentiment_bullish, orderflow_bullish, structure_bullish])
                if secondary_confirms >= 2:
                    cross_signals['confluence'] = 'strong_bullish'
                else:
                    cross_signals['confluence'] = 'moderate_bullish'
                    
            elif primary_bearish:
                secondary_confirms = sum([sentiment_bearish, orderflow_bearish, structure_bearish])
                if secondary_confirms >= 2:
                    cross_signals['confluence'] = 'strong_bearish'
                else:
                    cross_signals['confluence'] = 'moderate_bearish'
                    
            else:
                cross_signals['confluence'] = 'mixed'
                
            return cross_signals
            
        except Exception as e:
            self.logger.error(f"Error analyzing cross indicator signals: {str(e)}")
            return {}

    def _validate_indicator_dependencies(self, results: Dict[str, Dict[str, Any]]) -> bool:
        """Validate dependencies between different indicators."""
        try:
            # Define primary and secondary indicators
            primary_indicators = {'volume', 'technical', 'orderbook'}
            secondary_indicators = {'orderflow', 'sentiment', 'price_structure'}
            
            # Check primary indicators (required)
            missing_primary = primary_indicators - set(results.keys())
            if missing_primary:
                self.logger.error(f"Missing required primary indicators: {missing_primary}")
                return False
                
            # Check secondary indicators (warn but don't fail)
            missing_secondary = secondary_indicators - set(results.keys())
            if missing_secondary:
                self.logger.warning(f"Missing secondary indicators: {missing_secondary}")
                
            # Validate result structure for each indicator
            for name, result in results.items():
                if not self._validate_indicator_result(result):
                    self.logger.error(f"Invalid result structure for {name}")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating indicator dependencies: {str(e)}")
            return False

    def _validate_cross_indicator_data(self, market_data: Dict[str, Any]) -> bool:
        """Validate data consistency across indicators."""
        try:
            # Check OHLCV consistency
            if 'ohlcv' in market_data:
                for tf in ['base', 'ltf', 'mtf', 'htf']:
                    df = market_data['ohlcv'].get(tf)
                    if not isinstance(df, pd.DataFrame) or df.empty:
                        self.logger.error(f"Invalid {tf} OHLCV data")
                        return False
                        
            # Check orderbook-trade consistency
            if 'orderbook' in market_data and 'trades' in market_data:
                ob_time = market_data['orderbook'].get('timestamp', 0)
                trade_times = [t.get('timestamp', 0) for t in market_data['trades']]
                if trade_times and abs(ob_time - max(trade_times)) > 60000:  # 1 minute
                    self.logger.warning("Large time gap between orderbook and trades")
                    
            # Check sentiment data consistency
            if 'sentiment' in market_data:
                sentiment = market_data['sentiment']
                if not all(k in sentiment for k in ['funding_rate', 'long_short_ratio']):
                    self.logger.error("Missing required sentiment fields")
                    return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error in cross validation: {str(e)}")
            return False

    def analyze_correlations(self, metrics):
        try:
            # Convert IndicatorMetrics to dictionary if needed
            metrics_dict = metrics if isinstance(metrics, dict) else metrics.__dict__
            
            # Perform correlation analysis
            correlations = {}
            for key1, value1 in metrics_dict.items():
                for key2, value2 in metrics_dict.items():
                    if key1 != key2:
                        # Calculate correlation only for numeric values
                        if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
                            correlations[f"{key1}_{key2}"] = self.calculate_correlation(value1, value2)
                            
            return correlations
            
        except Exception as e:
            logger.error(f"Error analyzing correlations: {str(e)}")
            return {}

    def calculate_correlation(self, value1, value2):
        # Simple correlation calculation
        try:
            return float(value1 * value2) / (abs(value1) * abs(value2)) if value1 and value2 else 0
        except:
            return 0 

    def analyze_trades(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trade data"""
        try:
            if not trades:
                return {}
            
            # Ensure required fields
            required_fields = ['id', 'price', 'size', 'side', 'time']
            if not all(field in trades[0] for field in required_fields):
                self.logger.error(f"Missing required trade fields")
                return {}

            return {}
            
        except Exception as e:
            self.logger.error(f"Error analyzing trades: {str(e)}")
            return {}

    def _validate_indicators(self) -> bool:
        """Validate all indicators are properly configured."""
        try:
            # Check all required indicators exist
            missing = BaseIndicator.VALID_INDICATOR_TYPES - set(self.indicators.keys())
            if missing:
                self.logger.error(f"Missing indicators: {missing}")
                return False
                
            # Validate each indicator's weights
            for name, indicator in self.indicators.items():
                weights = indicator.component_weights
                if not np.isclose(sum(weights.values()), 1.0):
                    self.logger.error(f"Invalid weights for {name}: {sum(weights.values())}")
                    return False
                    
            # Validate required data consistency
            for name, indicator in self.indicators.items():
                required = indicator.required_data
                if not set(required).issubset(set(['ohlcv', 'orderbook', 'trades', 'ticker', 'sentiment'])):
                    self.logger.error(f"Invalid required data for {name}: {required}")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating indicators: {str(e)}")
            return False

    def _validate_ohlcv_structure(self, ohlcv_data: Dict[str, Any]) -> bool:
        """Validate OHLCV data structure."""
        try:
            self.logger.debug("\n=== Validating OHLCV Structure ===")
            self.logger.debug(f"OHLCV data type: {type(ohlcv_data)}")
            self.logger.debug(f"OHLCV keys: {list(ohlcv_data.keys()) if isinstance(ohlcv_data, dict) else 'Not a dict'}")
            
            # Check if we have at least one timeframe
            if not isinstance(ohlcv_data, dict) or not ohlcv_data:
                self.logger.error("OHLCV data must be a non-empty dictionary")
                return False
                
            # Check at least one DataFrame has required columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            valid_timeframe = False
            
            for tf, df in ohlcv_data.items():
                self.logger.debug(f"\nTimeframe {tf}:")
                self.logger.debug(f"Data type: {type(df)}")
                if isinstance(df, pd.DataFrame):
                    self.logger.debug(f"Columns: {list(df.columns)}")
                    if all(col in df.columns for col in required_columns):
                        valid_timeframe = True
                        break
                    
            if not valid_timeframe:
                self.logger.error("No timeframe contains all required columns")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating OHLCV structure: {str(e)}")
            return False

    def _validate_orderbook_structure(self, orderbook: Dict[str, Any]) -> bool:
        """Validate orderbook data structure."""
        try:
            self.logger.debug("\n=== Validating Orderbook Structure ===")
            self.logger.debug(f"Input keys: {list(orderbook.keys())}")
            
            # Required fields
            required_fields = ['bids', 'asks', 'timestamp']
            
            # Check all required fields exist
            if not all(field in orderbook for field in required_fields):
                missing = [f for f in required_fields if f not in orderbook]
                self.logger.error(f"Missing orderbook fields: {missing}")
                return False
            
            # Log data samples
            self.logger.debug("\nData Samples:")
            if 'bids' in orderbook:
                self.logger.debug(f"Bids type: {type(orderbook['bids'])}")
                if orderbook['bids']:
                    self.logger.debug(f"First bid: {orderbook['bids'][0]}")
                    
            if 'asks' in orderbook:
                self.logger.debug(f"Asks type: {type(orderbook['asks'])}")
                if orderbook['asks']:
                    self.logger.debug(f"First ask: {orderbook['asks'][0]}")
                    
            if 'timestamp' in orderbook:
                self.logger.debug(f"Timestamp type: {type(orderbook['timestamp'])}")
                self.logger.debug(f"Timestamp value: {orderbook['timestamp']}")
                
            # Validate structure
            for side in ['bids', 'asks']:
                if side in orderbook:
                    for i, level in enumerate(orderbook[side][:5]):  # Check first 5 levels
                        self.logger.debug(f"{side.capitalize()} level {i+1}: {level}")
                        if not isinstance(level, list) or len(level) != 2:
                            self.logger.error(f"Invalid {side} format at level {i+1}")
                            return False
                        try:
                            price, size = float(level[0]), float(level[1])
                            self.logger.debug(f"  Converted: Price={price}, Size={size}")
                        except (TypeError, ValueError) as e:
                            self.logger.error(f"Invalid numeric values at {side} level {i+1}: {e}")
                            return False
                            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating orderbook structure: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def _validate_trade_data(self, trades: List[Dict[str, Any]]) -> bool:
        """Validate trade data structure"""
        try:
            if not trades:
                self.logger.error("Empty trades list")
                return False
            
            required_fields = ['price', 'amount', 'side', 'timestamp']
            
            # Check first trade has all required fields
            sample_trade = trades[0]
            missing_fields = [f for f in required_fields if f not in sample_trade]
            
            if missing_fields:
                self.logger.error(f"Missing trade fields: {missing_fields}")
                return False
            
            # Validate data types
            for trade in trades[:5]:  # Check first 5 trades
                if not isinstance(trade['price'], (int, float)):
                    self.logger.error(f"Invalid price type: {type(trade['price'])}")
                    return False
                if not isinstance(trade['amount'], (int, float)):
                    self.logger.error(f"Invalid amount type: {type(trade['amount'])}")
                    return False
                if not isinstance(trade['side'], str):
                    self.logger.error(f"Invalid side type: {type(trade['side'])}")
                    return False
                if not isinstance(trade['timestamp'], (int, float)):
                    self.logger.error(f"Invalid timestamp type: {type(trade['timestamp'])}")
                    return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating trade data: {str(e)}")
            return False 

    def _process_trades(self, trades_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process trades data handling both WebSocket and REST formats."""
        try:
            if not trades_data:
                self.logger.warning("Empty trades data received")
                return []
            
            self.logger.debug(f"\n=== Processing Trades ===")
            self.logger.debug(f"Input trades count: {len(trades_data)}")
            if trades_data:
                self.logger.debug(f"Sample input trade: {trades_data[0]}")
            
            # Track statistics for logging
            invalid_price_count = 0
            invalid_size_count = 0
            missing_side_count = 0
            invalid_time_count = 0
            
            # Keep track of last valid price for fallback
            last_valid_price = None
            
            processed_trades = []
            for trade in trades_data:
                try:
                    # Look for price in multiple fields with fallbacks
                    price = 0.0
                    for price_field in ['price', 'p', 'trade_price', 'last_price', 'lastPrice']:
                        price_value = trade.get(price_field)
                        if price_value and float(price_value) > 0:
                            price = float(price_value)
                            break
                    
                    # If no valid price found, try to use ticker price if available
                    if price <= 0:
                        # Try ticker field inside trade
                        if 'ticker' in trade:
                            ticker_price = trade.get('ticker', {}).get('last', 0)
                            if ticker_price and float(ticker_price) > 0:
                                price = float(ticker_price)
                                self.logger.debug(f"Used ticker price from trade: {price}")
                        
                        # Try direct ticker data
                        elif hasattr(self, 'market_data') and isinstance(self.market_data, dict) and 'ticker' in self.market_data:
                            ticker = self.market_data.get('ticker', {})
                            if isinstance(ticker, dict):
                                ticker_price = ticker.get('last', ticker.get('last_price', 0))
                                if ticker_price and float(ticker_price) > 0:
                                    price = float(ticker_price)
                                    self.logger.debug(f"Used global ticker price: {price}")
                    
                    # If still no valid price, try using last valid price as fallback
                    if price <= 0 and last_valid_price is not None:
                        price = last_valid_price
                        self.logger.debug(f"Used last valid trade price: {price}")
                    
                    # Extract and standardize trade data
                    processed_trade = {
                        'price': price,
                        'size': float(trade.get('size', trade.get('amount', trade.get('v', 0)))),
                        'side': trade.get('side', trade.get('S', '')).lower(),
                        'time': int(trade.get('time', trade.get('timestamp', trade.get('T', 0)))),
                        'id': str(trade.get('id', trade.get('trade_id', trade.get('i', ''))))
                    }
                    
                    # Validate processed trade
                    if processed_trade['price'] <= 0:
                        invalid_price_count += 1
                        continue
                    
                    # Update last valid price for future fallbacks
                    last_valid_price = processed_trade['price']
                        
                    if processed_trade['size'] <= 0:
                        invalid_size_count += 1
                        continue
                        
                    if not processed_trade['side']:
                        missing_side_count += 1
                        continue
                        
                    if processed_trade['time'] <= 0:
                        invalid_time_count += 1
                        continue
                        
                    processed_trades.append(processed_trade)
                    
                except Exception as e:
                    self.logger.error(f"Error processing trade: {str(e)}")
                    self.logger.debug(f"Problematic trade: {trade}")
                    continue
            
            # Log summary of validation issues instead of individual warnings
            if invalid_price_count > 0:
                self.logger.warning(f"Skipped {invalid_price_count} trades with invalid prices")
            if invalid_size_count > 0:
                self.logger.warning(f"Skipped {invalid_size_count} trades with invalid sizes")
            if missing_side_count > 0:
                self.logger.warning(f"Skipped {missing_side_count} trades with missing sides")
            if invalid_time_count > 0:
                self.logger.warning(f"Skipped {invalid_time_count} trades with invalid timestamps")
                
            self.logger.debug(f"Successfully processed {len(processed_trades)} of {len(trades_data)} trades")
            if processed_trades:
                self.logger.debug(f"Sample processed trade: {processed_trades[0]}")
            elif len(trades_data) > 0:
                self.logger.warning("All trades were rejected during validation")
            
            return processed_trades
            
        except Exception as e:
            self.logger.error(f"Error in trade processing: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return [] 

    def validate_data_for_type(self, data_type: str, market_data: Dict[str, Any]) -> bool:
        """Validate data required for specific analysis type."""
        self.logger.debug(f"\nValidating data for {data_type}")
        
        # Add debug logging for trades data
        if data_type in ['volume', 'orderflow']:
            self.logger.debug("\n=== Trades Data Inspection ===")
            trades = market_data.get('trades', [])
            self.logger.debug(f"Trades type: {type(trades)}")
            self.logger.debug(f"Number of trades: {len(trades) if isinstance(trades, list) else 'Not a list'}")
            if isinstance(trades, list) and trades:
                self.logger.debug(f"First trade: {trades[0]}")
                self.logger.debug(f"Available fields: {list(trades[0].keys()) if isinstance(trades[0], dict) else 'Not a dict'}")
        
        try:
            if data_type == 'technical':
                return self._validate_technical_data(market_data)
            elif data_type == 'volume':
                return self._validate_volume_data(market_data)
            elif data_type == 'orderflow':
                return self._validate_orderflow_data(market_data)
            elif data_type == 'sentiment':
                return self._validate_sentiment_data(market_data)
            else:
                self.logger.error(f"Unknown data type: {data_type}")
                return False
        except Exception as e:
            self.logger.error(f"Error validating {data_type} data: {str(e)}")
            return False 

    def _prepare_data_for_orderbook(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for orderbook analysis by ensuring proper formatting."""
        try:
            # Make a deep copy to avoid modifying the original
            transformed_data = {
                'orderbook': market_data.get('orderbook', {}),
                'trades': market_data.get('trades', [])
            }
            
            # Ensure orderbook has the expected format
            if 'orderbook' in transformed_data and isinstance(transformed_data['orderbook'], dict):
                orderbook = transformed_data['orderbook']
                
                # Make sure bids and asks are in the expected format
                if 'bids' not in orderbook:
                    orderbook['bids'] = []
                if 'asks' not in orderbook:
                    orderbook['asks'] = []
                    
                # Ensure bids and asks are valid lists
                if not isinstance(orderbook['bids'], list):
                    self.logger.warning(f"Invalid bids format, converting to empty list")
                    orderbook['bids'] = []
                    
                if not isinstance(orderbook['asks'], list):
                    self.logger.warning(f"Invalid asks format, converting to empty list")
                    orderbook['asks'] = []
                    
                # Ensure timestamp exists
                if 'timestamp' not in orderbook:
                    orderbook['timestamp'] = int(time.time() * 1000)
                    
                # Ensure pressure is calculated
                try:
                    # First check if we have valid orderbook data
                    if not orderbook['bids'] or not orderbook['asks']:
                        self.logger.warning("Empty orderbook data, using default pressure values")
                        orderbook['pressure'] = {
                            'score': 50.0,
                            'bid_pressure': 0.0,
                            'ask_pressure': 0.0,
                            'imbalance': 0.0,
                            'ratio': 1.0
                        }
                    elif hasattr(self.indicators['orderbook'], 'calculate_pressure'):
                        # Pre-validate bid and ask entries to ensure they are [price, size] format
                        clean_bids = []
                        clean_asks = []
                        
                        for bid in orderbook['bids']:
                            if isinstance(bid, list) and len(bid) >= 2:
                                try:
                                    price = float(bid[0])
                                    size = float(bid[1])
                                    if price > 0 and size > 0:
                                        clean_bids.append([price, size])
                                except (ValueError, TypeError):
                                    pass
                                    
                        for ask in orderbook['asks']:
                            if isinstance(ask, list) and len(ask) >= 2:
                                try:
                                    price = float(ask[0])
                                    size = float(ask[1])
                                    if price > 0 and size > 0:
                                        clean_asks.append([price, size])
                                except (ValueError, TypeError):
                                    pass
                        
                        # Replace with clean data
                        orderbook['bids'] = clean_bids
                        orderbook['asks'] = clean_asks
                        
                        # Now calculate pressure with clean data
                        if clean_bids and clean_asks:
                                pressure = self.indicators['orderbook'].calculate_pressure(orderbook)
                            orderbook['pressure'] = pressure
                        else:
                            self.logger.warning("No valid bid/ask entries after cleaning, using default pressure")
                            orderbook['pressure'] = {
                                'score': 50.0,
                                'bid_pressure': 0.0,
                                'ask_pressure': 0.0,
                                'imbalance': 0.0,
                                'ratio': 1.0
                            }
                    else:
                        self.logger.debug("No calculate_pressure method found")
                        orderbook['pressure'] = {
                            'score': 50.0,
                            'bid_pressure': 0.0,
                            'ask_pressure': 0.0,
                            'imbalance': 0.0,
                            'ratio': 1.0
                        }
                except Exception as e:
                    self.logger.error(f"Error calculating orderbook pressure: {str(e)}")
                    self.logger.debug(f"Error details: {traceback.format_exc()}")
                    orderbook['pressure'] = {
                        'score': 50.0,
                        'bid_pressure': 0.0,
                        'ask_pressure': 0.0,
                        'imbalance': 0.0,
                        'ratio': 1.0
                    }
                
            return transformed_data
            
        except Exception as e:
            self.logger.error(f"Error preparing orderbook data: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return {'orderbook': {}, 'trades': []} 

    def _process_sentiment_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and standardize sentiment data."""
        try:
            sentiment_data = market_data.get('sentiment', {})
            ticker_data = market_data.get('ticker', {})
            
            # Ensure required fields exist
            if 'funding_rate' not in sentiment_data and ticker_data:
                sentiment_data['funding_rate'] = float(ticker_data.get('fundingRate', 0.0001))
            
            if 'long_short_ratio' not in sentiment_data:
                sentiment_data['long_short_ratio'] = 1.0  # Neutral by default
            
            if 'liquidations' not in sentiment_data:
                sentiment_data['liquidations'] = []
            
            return sentiment_data
        except Exception as e:
            self.logger.error(f"Error processing sentiment data: {str(e)}")
            return {
                'funding_rate': 0.0001,
                'long_short_ratio': 1.0,
                'liquidations': []
            } 