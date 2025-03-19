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


# Forward reference for type hints
BaseIndicator = 'src.indicators.BaseIndicator'

class DataFlowTracker:
    """Tracks data flow through the analysis pipeline."""
    
    def __init__(self):
        """Initialize the data flow tracker."""
        self.flow = {}
        self.data_flow = {
            'last_update': 0,
            'processed_count': 0,
            'error_count': 0,
            'component_stats': {}
        }
        
    def log_transform(self, indicator_type, data_keys):
        """Log data transformation for an indicator."""
        self.flow[indicator_type] = {
            'timestamp': time.time(),
            'data_keys': data_keys
        }
        
    def log_analysis(self, indicator_type, status, score=None):
        """Log analysis result for an indicator."""
        if indicator_type not in self.flow:
            self.flow[indicator_type] = {}
            
        self.flow[indicator_type].update({
            'status': status,
            'score': score,
            'analysis_time': time.time()
        })
        
    def get_summary(self):
        """Get summary of data flow."""
        return {
            'indicators': self.flow,
            'data_flow': self.data_flow
        }

class ConfluenceAnalyzer:
    """Analyzes market data using multiple indicators to generate confluence scores."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the ConfluenceAnalyzer with configuration."""
        self.logger = Logger(__name__)
        self.logger.info("Initializing ConfluenceAnalyzer")
        
        # Set default config if none provided
        self.config = config or {}
        
        # Initialize data flow tracker
        self.data_flow_tracker = DataFlowTracker()
        
        # Initialize debug info
        self.debug_info = {}
        
        # Get weights from the unified structure
        confluence_config = self.config.get('confluence', {}).get('weights', {})
        
        # Get component weights - THE single source of truth for all component weighting
        self.weights = confluence_config.get('components', {
            'technical': 0.20,
            'volume': 0.10,
            'orderflow': 0.25,
            'sentiment': 0.15,
            'orderbook': 0.20,
            'price_structure': 0.10
        })
        self.logger.info(f"Using component weights: {self.weights}")
        
        # Get sub-component weights for indicators
        self.sub_component_weights = confluence_config.get('sub_components', {})
        self.logger.debug(f"Using sub-component weights: {self.sub_component_weights}")
        
        # Normalize weights to ensure they sum to 1.0
        self._normalize_weights()
        
        # Import indicator classes here to avoid circular imports
        from src.indicators.base_indicator import BaseIndicator
        from src.indicators.volume_indicators import VolumeIndicators
        from src.indicators.orderflow_indicators import OrderflowIndicators
        from src.indicators.orderbook_indicators import OrderbookIndicators
        from src.indicators.technical_indicators import TechnicalIndicators
        from src.indicators.sentiment_indicators import SentimentIndicators
        from src.indicators.price_structure_indicators import PriceStructureIndicators
        
        # Initialize indicators
        self.indicators = {
            'technical': TechnicalIndicators(config, self.logger),
            'volume': VolumeIndicators(config, self.logger),
            'orderbook': OrderbookIndicators(config, self.logger),
            'orderflow': OrderflowIndicators(config, self.logger),
            'sentiment': SentimentIndicators(config, self.logger),
            'price_structure': PriceStructureIndicators(config, self.logger)
        }

    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data using multiple indicators."""
        try:
            self.logger.info("Starting confluence analysis")
            start_time = time.time()
            
            # Validate market data
            self.logger.info("Validating market data for analysis")
            if not self._validate_market_data(market_data):
                self.logger.error("Invalid market data for analysis - validation failed")
                self.logger.info(f"Market data keys: {list(market_data.keys())}")
                
                # Check if we have OHLCV data
                if 'ohlcv' in market_data:
                    self.logger.info(f"OHLCV keys: {list(market_data['ohlcv'].keys())}")
                    for tf, data in market_data['ohlcv'].items():
                        if isinstance(data, pd.DataFrame):
                            self.logger.info(f"OHLCV {tf} shape: {data.shape}, empty: {data.empty}")
                
                return self._get_default_response()
                
            # Initialize results
            results = {}
            scores = {}
            
            # Process each indicator
            for indicator_type, indicator in self.indicators.items():
                try:
                    # Log start of indicator analysis
                    self.logger.info(f"Processing {indicator_type} indicator")
                    indicator_start_time = time.time()
                    
                    # Transform data for this indicator
                    self.logger.debug(f"Transforming data for {indicator_type}")
                    transformed_data = self._transform_data(indicator_type, market_data)
                    
                    # Skip if transformation failed
                    if not transformed_data:
                        self.logger.warning(f"Skipping {indicator_type} analysis due to data transformation failure")
                        continue
                        
                    # Validate transformed data
                    if not self._validate_transformed_data(transformed_data, indicator_type):
                        self.logger.warning(f"Skipping {indicator_type} analysis due to invalid transformed data")
                        continue
                        
                    # Calculate indicator score
                    self.logger.info(f"Calculating {indicator_type} score")
                    
                    # Check if the calculate method is a coroutine function
                    if asyncio.iscoroutinefunction(indicator.calculate):
                        result = await indicator.calculate(transformed_data)
                    else:
                        # Call the method directly if it's not async
                        result = indicator.calculate(transformed_data)
                    
                    # Validate result
                    if not self._validate_indicator_result(result):
                        self.logger.warning(f"Invalid result from {indicator_type} indicator")
                        self.data_flow_tracker.log_analysis(indicator_type, 'error')
                        continue
                        
                    # Store result
                    results[indicator_type] = result
                    scores[indicator_type] = result.get('score', 50.0)
                    
                    # Log analysis completion
                    indicator_elapsed = time.time() - indicator_start_time
                    self.logger.info(f"{indicator_type.capitalize()} score: {scores[indicator_type]:.2f} (took {indicator_elapsed:.2f}s)")
                    self.data_flow_tracker.log_analysis(indicator_type, 'success', scores[indicator_type])
                    
                except Exception as e:
                    self.logger.error(f"Error analyzing {indicator_type}: {str(e)}")
                    self.logger.error(traceback.format_exc())
                    self.data_flow_tracker.log_analysis(indicator_type, 'error')
                    
            # Calculate confluence score
            if not scores:
                self.logger.error("No valid indicator scores calculated")
                return self._get_default_response()
                
            self.logger.info(f"Successfully calculated scores for {len(scores)} indicators: {list(scores.keys())}")
            
            confluence_score = self._calculate_confluence_score(scores)
            reliability = self._calculate_reliability(scores)
            
            # Format response
            response = self._format_response(scores)
            response['score'] = confluence_score
            response['reliability'] = reliability
            response['results'] = results
            response['debug'] = self._get_debug_info('confluence')
            
            elapsed = time.time() - start_time
            self.logger.info(f"Confluence analysis completed in {elapsed:.2f}s")
            self.logger.info(f"Final confluence score: {confluence_score:.2f} (reliability: {reliability:.2f})")
            return response
            
        except Exception as e:
            self.logger.error(f"Error in confluence analysis: {str(e)}")
            self.logger.error(traceback.format_exc())
            return self._get_default_response()

    def _track_data_flow(self, stage: str, flow_id: str, data: Dict[str, Any]) -> None:
        """Track data flow through the analysis pipeline."""
        try:
            timestamp = int(time.time() * 1000)
            
            # Initialize component if not exists
            if flow_id not in self.data_flow_tracker.data_flow.get('component_stats', {}):
                self.data_flow_tracker.data_flow['component_stats'][flow_id] = {
                    'processed': 0,
                    'errors': 0,
                    'last_update': 0,
                    'avg_processing_time': 0
                }
            
            # Update stats
            self.data_flow_tracker.data_flow['last_update'] = timestamp
            if stage == 'complete':
                self.data_flow_tracker.data_flow['processed_count'] += 1
            elif stage == 'error':
                self.data_flow_tracker.data_flow['error_count'] += 1
            
            # Log based on debug level
            if self.debug_mode and self.debug_level >= 2:
                self.logger.debug(f"Data flow: {stage} - {flow_id} - {timestamp}")
                if self.debug_level >= 3:
                    self.logger.debug(f"Data keys: {list(data.keys())}")
                    
        except Exception as e:
            self.logger.error(f"Error tracking data flow: {str(e)}")

    def _get_debug_info(self, flow_id: str) -> Dict[str, Any]:
        """Get debug information for response."""
        return {
            'flow_id': flow_id,
            'processed_count': self.data_flow_tracker.data_flow['processed_count'],
            'error_count': self.data_flow_tracker.data_flow['error_count'],
            'component_stats': self.data_flow_tracker.data_flow['component_stats']
        }

    def _transform_data(self, indicator_type: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform market data for specific indicator type."""
        # Create a deep copy to avoid modifying the original
        transformed_data = copy.deepcopy(market_data)
        
        try:
            # Track data flow
            self.data_flow_tracker.log_transform(indicator_type, list(transformed_data.keys()))
            
            # Ensure common required fields are present
            required_common_fields = ['symbol', 'exchange', 'timestamp']
            for field in required_common_fields:
                if field not in transformed_data and field in market_data:
                    transformed_data[field] = market_data[field]
                elif field not in transformed_data:
                    # Set default values for missing fields
                    if field == 'symbol':
                        transformed_data[field] = 'UNKNOWN'
                    elif field == 'exchange':
                        transformed_data[field] = 'UNKNOWN'
                    elif field == 'timestamp':
                        transformed_data[field] = int(time.time() * 1000)
            
            # Apply specific transformations based on indicator type
            if indicator_type == 'technical':
                transformed_data = self._prepare_data_for_technical(transformed_data)
            elif indicator_type == 'volume':
                transformed_data = self._prepare_data_for_volume(transformed_data)
            elif indicator_type == 'orderbook':
                transformed_data = self._prepare_data_for_orderbook(transformed_data)
            elif indicator_type == 'orderflow':
                transformed_data = self._prepare_data_for_orderflow(transformed_data)
            elif indicator_type == 'sentiment':
                transformed_data = self._prepare_data_for_sentiment(transformed_data)
            elif indicator_type == 'price_structure':
                transformed_data = self._prepare_data_for_price_structure(transformed_data)
                
            # Log the transformed data structure
            self.logger.debug(f"Transformed data for {indicator_type} has keys: {list(transformed_data.keys())}")
            
            return transformed_data
        except Exception as e:
            self.logger.error(f"Error transforming data for {indicator_type}: {str(e)}")
            self.logger.error(traceback.format_exc())
            return market_data

    def _prepare_data_for_technical(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare market data for technical indicators."""
        try:
            # Create a copy to avoid modifying the original
            technical_data = {
                'ohlcv': market_data.get('ohlcv', {}),
                'ticker': market_data.get('ticker', {}),
                'timeframe': market_data.get('timeframe', 'base'),
                'symbol': market_data.get('symbol', ''),
                'exchange': market_data.get('exchange', ''),
                'timestamp': market_data.get('timestamp', int(time.time() * 1000))
            }
            
            # Log the OHLCV data structure
            ohlcv_data = technical_data['ohlcv']
            if ohlcv_data:
                self.logger.debug(f"OHLCV timeframes: {list(ohlcv_data.keys())}")
                
                # Check each timeframe format
                for tf, data in ohlcv_data.items():
                    if isinstance(data, pd.DataFrame):
                        self.logger.debug(f"Timeframe {tf} is a DataFrame with shape {data.shape}")
                    elif isinstance(data, dict) and 'data' in data and isinstance(data['data'], pd.DataFrame):
                        self.logger.debug(f"Timeframe {tf} is a nested dict with DataFrame of shape {data['data'].shape}")
                    else:
                        self.logger.warning(f"Timeframe {tf} has unsupported data type: {type(data)}")
            
            # Ensure timeframes are available as a list
            technical_data['timeframes'] = list(technical_data['ohlcv'].keys()) if 'ohlcv' in technical_data and technical_data['ohlcv'] else []
            
            return technical_data
        except Exception as e:
            self.logger.error(f"Error preparing data for technical indicators: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return market_data

    def _prepare_data_for_volume(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare market data for volume indicators."""
        try:
            # Create a copy to avoid modifying the original
            volume_data = {
                'ohlcv': market_data.get('ohlcv', {}),
                'trades': market_data.get('trades', []),
                'ticker': market_data.get('ticker', {}),
                'symbol': market_data.get('symbol', ''),
                'exchange': market_data.get('exchange', ''),
                'timestamp': market_data.get('timestamp', int(time.time() * 1000))
            }
            
            # Process trades if available
            if volume_data['trades']:
                try:
                    # Store the original market data for reference in _process_trades
                    self.market_data = market_data
                    
                    # Process trades to standardize format
                    processed_trades = self._process_trades(volume_data['trades'])
                    
                    # Add processed trades to the data
                    volume_data['processed_trades'] = processed_trades
                    
                    self.logger.debug(f"Processed {len(processed_trades)} trades for volume analysis")
                except Exception as e:
                    self.logger.error(f"Error processing trades for volume: {str(e)}")
                    self.logger.error(traceback.format_exc())
            else:
                self.logger.debug("No trades data available for volume analysis")
            
            return volume_data
        except Exception as e:
            self.logger.error(f"Error preparing data for volume indicators: {str(e)}")
            return market_data

    def _prepare_data_for_orderbook(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for orderbook analysis by ensuring proper formatting."""
        try:
            # Make a deep copy to avoid modifying the original
            transformed_data = {
                'orderbook': market_data.get('orderbook', {}),
                'trades': market_data.get('trades', []),
                # Add required fields for OrderbookIndicators
                'symbol': market_data.get('symbol', 'UNKNOWN'),
                'exchange': market_data.get('exchange', 'UNKNOWN'),
                'timestamp': market_data.get('timestamp', int(time.time() * 1000))
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
                    
                # Ensure timestamp exists in the orderbook dict (this is the fix)
                if 'timestamp' not in orderbook or not orderbook['timestamp']:
                    orderbook['timestamp'] = transformed_data['timestamp']
                    self.logger.debug(f"Added missing timestamp to orderbook: {orderbook['timestamp']}")
                    
                # Log the orderbook structure for debugging
                self.logger.debug(f"Orderbook keys after preparation: {list(orderbook.keys())}")
                
                # Ensure pressure is calculated
                try:
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
                        try:
                            # Direct calculation of pressure
                            bid_price, ask_price = clean_bids[0][0], clean_asks[0][0]
                            spread = ask_price - bid_price
                            bid_volume = sum(float(bid[1]) for bid in clean_bids)
                            ask_volume = sum(float(ask[1]) for ask in clean_asks)
                            
                            imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume) if (bid_volume + ask_volume) > 0 else 0
                            bid_concentration = clean_bids[0][1] / bid_volume if bid_volume > 0 else 0
                            ask_concentration = clean_asks[0][1] / ask_volume if ask_volume > 0 else 0
                            
                            spread_pct = spread / bid_price if bid_price > 0 else 0
                            spread_factor = 1 - min(spread_pct * 100, 1)
                            
                            raw_imbalance = imbalance
                            adjusted_imbalance = imbalance - (ask_concentration - bid_concentration) * 0.1
                            
                            score = 50 + (adjusted_imbalance * 50)
                            final_score = 50 + (score - 50) * spread_factor
                            
                            # Always set the pressure field with comprehensive data
                            orderbook['pressure'] = {
                                'score': final_score,
                                'bid_pressure': bid_volume,
                                'ask_pressure': ask_volume,
                                'imbalance': adjusted_imbalance,
                                'raw_imbalance': raw_imbalance,
                                'spread': spread,
                                'spread_factor': spread_factor,
                                'bid_concentration': bid_concentration,
                                'ask_concentration': ask_concentration,
                                'ratio': bid_volume / ask_volume if ask_volume > 0 else 1.0
                            }
                            self.logger.debug(f"Calculated orderbook pressure directly: score={final_score:.2f}")
                        except Exception as e:
                            self.logger.error(f"Error calculating orderbook pressure: {str(e)}")
                            # Default pressure for empty orderbook
                            orderbook['pressure'] = {
                                'score': 50.0,
                                'bid_pressure': 0.0,
                                'ask_pressure': 0.0,
                                'imbalance': 0.0,
                                'ratio': 1.0
                            }
                    else:
                        # Default pressure for empty orderbook
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

    def _prepare_data_for_orderflow(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare market data for orderflow indicators. Ensures that all required fields are properly populated."""
        try:
            # Create a copy to avoid modifying the original
            orderflow_data = {
                'symbol': market_data.get('symbol', ''),
                'exchange': market_data.get('exchange', ''),
                'timestamp': market_data.get('timestamp', int(time.time() * 1000)),
                'trades': market_data.get('trades', []),
                # Add orderbook data (even if empty) to ensure it's available for orderflow analysis
                'orderbook': market_data.get('orderbook', {}),
                # Add other required fields
                'ohlcv': market_data.get('ohlcv', {}),
                'ticker': market_data.get('ticker', {}),
                # Add open interest data for price-OI divergence calculations
                'open_interest': market_data.get('open_interest', {})
            }
            
            # Ensure required fields are in orderflow_data structure
            if not orderflow_data['symbol'] and 'symbol' in market_data:
                orderflow_data['symbol'] = market_data['symbol']
                
            if not orderflow_data['exchange'] and 'exchange' in market_data:
                orderflow_data['exchange'] = market_data['exchange']
                
            if not orderflow_data['timestamp'] and 'timestamp' in market_data:
                orderflow_data['timestamp'] = market_data['timestamp']
            
            # Ensure orderbook has a timestamp (fix for missing timestamp)
            if 'orderbook' in orderflow_data and isinstance(orderflow_data['orderbook'], dict):
                if 'timestamp' not in orderflow_data['orderbook'] or not orderflow_data['orderbook']['timestamp']:
                    orderflow_data['orderbook']['timestamp'] = orderflow_data['timestamp']
                    self.logger.debug(f"Added missing timestamp to orderflow orderbook: {orderflow_data['orderbook']['timestamp']}")
                
                # Ensure bids and asks are present
                if 'bids' not in orderflow_data['orderbook']:
                    orderflow_data['orderbook']['bids'] = []
                if 'asks' not in orderflow_data['orderbook']:
                    orderflow_data['orderbook']['asks'] = []
            
            # Process trades if available
            if orderflow_data['trades'] and isinstance(orderflow_data['trades'], list) and len(orderflow_data['trades']) > 0:
                try:
                    # Store the original market data for reference in _process_trades
                    self.market_data = market_data
                    
                    # Process trades to standardize format
                    processed_trades = self._process_trades(orderflow_data['trades'])
                    
                    # Ensure processed_trades is a list of dictionaries, not a dict itself
                    if processed_trades and isinstance(processed_trades, dict):
                        self.logger.warning("Processed trades is a dictionary, converting to list")
                        processed_trades = [processed_trades]
                    elif not isinstance(processed_trades, list):
                        self.logger.warning(f"Unexpected processed_trades type: {type(processed_trades)}, converting to empty list")
                        processed_trades = []
                        
                    # Add processed trades to orderflow_data
                    orderflow_data['processed_trades'] = processed_trades
                    
                    # Create a DataFrame for easier analysis if we have processed trades
                    if processed_trades:
                        try:
                            trades_df = pd.DataFrame(processed_trades)
                            orderflow_data['trades_df'] = trades_df
                            self.logger.debug(f"Created trades DataFrame with {len(trades_df)} rows")
                        except Exception as e:
                            self.logger.error(f"Failed to create trades DataFrame: {str(e)}")
                except Exception as e:
                    self.logger.error(f"Error processing trades for orderflow: {str(e)}")
            
            # Ensure orderbook data is properly structured
            if 'orderbook' in orderflow_data and orderflow_data['orderbook']:
                if not isinstance(orderflow_data['orderbook'], dict):
                    self.logger.warning(f"Orderbook is not a dictionary, converting to empty dict")
                    orderflow_data['orderbook'] = {}
                else:
                    # Ensure bids and asks are present
                    if 'bids' not in orderflow_data['orderbook']:
                        orderflow_data['orderbook']['bids'] = []
                    if 'asks' not in orderflow_data['orderbook']:
                        orderflow_data['orderbook']['asks'] = []
            else:
                # Ensure orderbook is at least an empty dict with bids and asks
                orderflow_data['orderbook'] = {'bids': [], 'asks': []}
            
            return orderflow_data
            
        except Exception as e:
            self.logger.error(f"Error preparing data for orderflow: {str(e)}")
            # Return a minimal valid structure
            return {
                'symbol': market_data.get('symbol', ''),
                'exchange': market_data.get('exchange', ''),
                'timestamp': market_data.get('timestamp', int(time.time() * 1000)),
                'trades': [],
                'orderbook': {'bids': [], 'asks': []},
                'ohlcv': {},
                'ticker': {},
                'open_interest': {}  # Add empty open_interest dictionary in case of error
            }

    def _prepare_data_for_price_structure(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare market data for price structure indicators."""
        try:
            # Create a copy to avoid modifying the original
            price_structure_data = {
                'ohlcv': market_data.get('ohlcv', {}),
                'ticker': market_data.get('ticker', {}),
                'symbol': market_data.get('symbol', ''),
                'exchange': market_data.get('exchange', ''),
                'timestamp': market_data.get('timestamp', int(time.time() * 1000))
            }
            
            # Ensure timeframes are available
            price_structure_data['timeframes'] = list(price_structure_data['ohlcv'].keys()) if 'ohlcv' in price_structure_data else []
            
            return price_structure_data
        except Exception as e:
            self.logger.error(f"Error preparing data for price structure indicators: {str(e)}")
            return market_data

    def _prepare_data_for_sentiment(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare market data for sentiment indicators. Ensures that all required fields are properly populated."""
        try:
            self.logger.debug("\n=== Preparing Sentiment Data ===")
            
            # Create a copy to avoid modifying the original
            sentiment_data = {
                'symbol': market_data.get('symbol', ''),
                'exchange': market_data.get('exchange', ''),
                'timestamp': market_data.get('timestamp', int(time.time() * 1000)),
                'ohlcv': market_data.get('ohlcv', {}),
                'ticker': market_data.get('ticker', {})
            }
            
            # Process existing sentiment data if available
            if 'sentiment' in market_data:
                sentiment_data['sentiment'] = market_data['sentiment']
            else:
                # Create sentiment data structure if not present
                enhanced_sentiment = self._process_sentiment_data(market_data)
                sentiment_data['sentiment'] = enhanced_sentiment
            
            # Ensure OHLCV data is available for sentiment calculations
            if not sentiment_data['ohlcv'] and 'ohlcv' in market_data:
                sentiment_data['ohlcv'] = market_data['ohlcv']
            
            # Validate the prepared data
            if self._validate_sentiment_data(sentiment_data):
                self.logger.info("Sentiment data validation passed")
            else:
                self.logger.warning("Sentiment data validation failed, using default values")
                # Ensure we have at least the minimum required structure
                if 'sentiment' not in sentiment_data:
                    sentiment_data['sentiment'] = {
                        'funding_rate': 0.0001,
                        'long_short_ratio': 1.0,
                        'liquidations': []
                    }
            
            self.logger.debug(f"Prepared sentiment data with keys: {list(sentiment_data.keys())}")
            return sentiment_data
            
        except Exception as e:
            self.logger.error(f"Error preparing sentiment data: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            # Return a minimal valid structure
            return {
                'sentiment': {
                    'funding_rate': 0.0001,
                    'long_short_ratio': 1.0,
                    'liquidations': []
                },
                'ohlcv': market_data.get('ohlcv', {}),
                'symbol': market_data.get('symbol', ''),
                'exchange': market_data.get('exchange', ''),
                'timestamp': market_data.get('timestamp', int(time.time() * 1000))
            }

    def _setup_price_structure_attributes(self, price_structure_indicator):
        """Set up required attributes for price structure indicator."""
        # Define default timeframe map
        default_timeframe_map = {
            'base': '1',
            'ltf': '5',
            'mtf': '30',
            'htf': '240'
        }

        # Check if timeframe_map attribute exists, create it if missing
        if not hasattr(price_structure_indicator, 'timeframe_map'):
            # If the config has timeframes, use those instead of defaults
            if self.config and 'timeframes' in self.config:
                try:
                    timeframe_map = {
                        tf: str(self.config['timeframes'][tf]['interval'])
                        for tf in ['base', 'ltf', 'mtf', 'htf']
                        if tf in self.config['timeframes']
                    }
                    # Fill in any missing with defaults
                    for tf in default_timeframe_map:
                        if tf not in timeframe_map:
                            timeframe_map[tf] = default_timeframe_map[tf]
                except Exception as e:
                    self.logger.warning(f"Error getting timeframes from config: {str(e)}")
                    timeframe_map = default_timeframe_map.copy()
            else:
                # Use default values
                timeframe_map = default_timeframe_map.copy()
                
            # Assign the timeframe map to the indicator
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
        if 'base' in price_structure_indicator.timeframe_map:
            reverse_timeframe_map['base'] = 'base'
            base_interval = price_structure_indicator.timeframe_map['base']
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
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
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
            
            # Summary of validation results
            self.logger.info("\n=== Market Data Validation Summary ===")
            self.logger.info(f"Symbol: {symbol}")
            self.logger.info(f"Valid Timeframes: {len(valid_timeframes)}/{len(ohlcv)} ({', '.join(valid_timeframes)})")
            self.logger.info(f"Has Orderbook: {'Yes' if 'orderbook' in market_data and isinstance(market_data['orderbook'], dict) else 'No'}")
            self.logger.info(f"Has Trades: {'Yes' if 'trades' in market_data and isinstance(market_data['trades'], list) and market_data['trades'] else 'No'}")
            self.logger.info(f"Has Ticker: {'Yes' if 'ticker' in market_data and isinstance(market_data['ticker'], dict) else 'No'}")
            
            # Final validation result
            validation_result = len(valid_timeframes) > 0
            self.logger.info(f"Market data validation result: {'Success' if validation_result else 'Failed'}")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return False

    def _normalize_weights(self) -> None:
        """Normalize weights to ensure they sum to 1.0."""
        if not hasattr(self, 'weights') or not self.weights:
            self.logger.warning("No weights to normalize")
            return
            
        # Normalize main component weights
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {k: v / total_weight for k, v in self.weights.items()}
            self.logger.debug(f"Normalized component weights: {self.weights}")
        else:
            self.logger.warning("Total weight is zero, cannot normalize component weights")
            
        # Normalize sub-component weights if they exist
        if hasattr(self, 'sub_component_weights') and self.sub_component_weights:
            for component, weights in self.sub_component_weights.items():
                total = sum(weights.values())
                if total > 0:
                    self.sub_component_weights[component] = {k: v / total for k, v in weights.items()}
            self.logger.debug(f"Normalized sub-component weights")

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
            # Check if orderbook is valid
            if not isinstance(orderbook, dict):
                self.logger.error(f"Invalid orderbook type: {type(orderbook)}")
                # Return minimal valid structure
                return {
                    'bids': [],
                    'asks': [],
                    'timestamp': int(time.time() * 1000),
                    'spread': None,
                    'mid_price': None
                }
            
            # Handle Bybit's nested orderbook format
            if 'result' in orderbook and isinstance(orderbook['result'], dict):
                result_data = orderbook['result']
                if 'b' in result_data and 'a' in result_data:
                    self.logger.debug("Detected Bybit orderbook format in process method")
                    # Extract bids and asks from the result structure
                    orderbook['bids'] = result_data['b']
                    orderbook['asks'] = result_data['a']
                    if 'ts' in result_data:
                        orderbook['timestamp'] = result_data['ts']
            
            # Handle missing fields
            if 'bids' not in orderbook:
                self.logger.warning("Missing 'bids' in orderbook, using empty list")
                orderbook['bids'] = []
                
            if 'asks' not in orderbook:
                self.logger.warning("Missing 'asks' in orderbook, using empty list")
                orderbook['asks'] = []
                
            # Handle missing timestamp - this is the key fix
            if 'timestamp' not in orderbook or not orderbook['timestamp']:
                self.logger.warning("Missing 'timestamp' in orderbook, using current time")
                orderbook['timestamp'] = int(time.time() * 1000)
            
            # Convert string values to float
            processed = {
                'bids': [[float(p), float(s)] for p, s in orderbook['bids']] if orderbook['bids'] else [],
                'asks': [[float(p), float(s)] for p, s in orderbook['asks']] if orderbook['asks'] else [],
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
            # Return a minimal valid structure instead of None
            return {
                'bids': [],
                'asks': [],
                'timestamp': int(time.time() * 1000),
                'spread': None,
                'mid_price': None
            }

    def _prepare_data_for_orderflow(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare market data for orderflow indicators. Ensures that all required fields are properly populated."""
        try:
            # Create a copy to avoid modifying the original
            orderflow_data = {
                'symbol': market_data.get('symbol', ''),
                'exchange': market_data.get('exchange', ''),
                'timestamp': market_data.get('timestamp', int(time.time() * 1000)),
                'trades': market_data.get('trades', []),
                # Add orderbook data (even if empty) to ensure it's available for orderflow analysis
                'orderbook': market_data.get('orderbook', {}),
                # Add other required fields
                'ohlcv': market_data.get('ohlcv', {}),
                'ticker': market_data.get('ticker', {}),
                # Add open interest data for price-OI divergence calculations
                'open_interest': market_data.get('open_interest', {})
            }
            
            # Ensure required fields are in orderflow_data structure
            if not orderflow_data['symbol'] and 'symbol' in market_data:
                orderflow_data['symbol'] = market_data['symbol']
                
            if not orderflow_data['exchange'] and 'exchange' in market_data:
                orderflow_data['exchange'] = market_data['exchange']
                
            if not orderflow_data['timestamp'] and 'timestamp' in market_data:
                orderflow_data['timestamp'] = market_data['timestamp']
            
            # Ensure orderbook has a timestamp (fix for missing timestamp)
            if 'orderbook' in orderflow_data and isinstance(orderflow_data['orderbook'], dict):
                if 'timestamp' not in orderflow_data['orderbook'] or not orderflow_data['orderbook']['timestamp']:
                    orderflow_data['orderbook']['timestamp'] = orderflow_data['timestamp']
                    self.logger.debug(f"Added missing timestamp to orderflow orderbook: {orderflow_data['orderbook']['timestamp']}")
                
                # Ensure bids and asks are present
                if 'bids' not in orderflow_data['orderbook']:
                    orderflow_data['orderbook']['bids'] = []
                if 'asks' not in orderflow_data['orderbook']:
                    orderflow_data['orderbook']['asks'] = []
            
            # Process trades if available
            if orderflow_data['trades'] and isinstance(orderflow_data['trades'], list) and len(orderflow_data['trades']) > 0:
                try:
                    # Store the original market data for reference in _process_trades
                    self.market_data = market_data
                    
                    # Process trades to standardize format
                    processed_trades = self._process_trades(orderflow_data['trades'])
                    
                    # Ensure processed_trades is a list of dictionaries, not a dict itself
                    if processed_trades and isinstance(processed_trades, dict):
                        self.logger.warning("Processed trades is a dictionary, converting to list")
                        processed_trades = [processed_trades]
                    elif not isinstance(processed_trades, list):
                        self.logger.warning(f"Unexpected processed_trades type: {type(processed_trades)}, converting to empty list")
                        processed_trades = []
                        
                    # Add processed trades to orderflow_data
                    orderflow_data['processed_trades'] = processed_trades
                    
                    # Create a DataFrame for easier analysis if we have processed trades
                    if processed_trades:
                        try:
                            trades_df = pd.DataFrame(processed_trades)
                            orderflow_data['trades_df'] = trades_df
                            self.logger.debug(f"Created trades DataFrame with {len(trades_df)} rows")
                        except Exception as e:
                            self.logger.error(f"Failed to create trades DataFrame: {str(e)}")
                except Exception as e:
                    self.logger.error(f"Error processing trades for orderflow: {str(e)}")
            
            # Ensure orderbook data is properly structured
            if 'orderbook' in orderflow_data and orderflow_data['orderbook']:
                if not isinstance(orderflow_data['orderbook'], dict):
                    self.logger.warning(f"Orderbook is not a dictionary, converting to empty dict")
                    orderflow_data['orderbook'] = {}
                else:
                    # Ensure bids and asks are present
                    if 'bids' not in orderflow_data['orderbook']:
                        orderflow_data['orderbook']['bids'] = []
                    if 'asks' not in orderflow_data['orderbook']:
                        orderflow_data['orderbook']['asks'] = []
            else:
                # Ensure orderbook is at least an empty dict with bids and asks
                orderflow_data['orderbook'] = {'bids': [], 'asks': []}
            
            return orderflow_data
            
        except Exception as e:
            self.logger.error(f"Error preparing data for orderflow: {str(e)}")
            # Return a minimal valid structure
            return {
                'symbol': market_data.get('symbol', ''),
                'exchange': market_data.get('exchange', ''),
                'timestamp': market_data.get('timestamp', int(time.time() * 1000)),
                'trades': [],
                'orderbook': {'bids': [], 'asks': []},
                'ohlcv': {},
                'ticker': {},
                'open_interest': {}  # Add empty open_interest dictionary in case of error
            }

    def _prepare_data_for_price_structure(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare market data for price structure indicators."""
        try:
            # Create a copy to avoid modifying the original
            price_structure_data = {
                'ohlcv': market_data.get('ohlcv', {}),
                'ticker': market_data.get('ticker', {}),
                'symbol': market_data.get('symbol', ''),
                'exchange': market_data.get('exchange', ''),
                'timestamp': market_data.get('timestamp', int(time.time() * 1000))
            }
            
            # Ensure timeframes are available
            price_structure_data['timeframes'] = list(price_structure_data['ohlcv'].keys()) if 'ohlcv' in price_structure_data else []
            
            return price_structure_data
        except Exception as e:
            self.logger.error(f"Error preparing data for price structure indicators: {str(e)}")
            return market_data

    def _prepare_data_for_sentiment(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare market data for sentiment indicators. Ensures that all required fields are properly populated."""
        try:
            self.logger.debug("\n=== Preparing Sentiment Data ===")
            
            # Create a copy to avoid modifying the original
            sentiment_data = {
                'symbol': market_data.get('symbol', ''),
                'exchange': market_data.get('exchange', ''),
                'timestamp': market_data.get('timestamp', int(time.time() * 1000)),
                'ohlcv': market_data.get('ohlcv', {}),
                'ticker': market_data.get('ticker', {})
            }
            
            # Process existing sentiment data if available
            if 'sentiment' in market_data:
                sentiment_data['sentiment'] = market_data['sentiment']
            else:
                # Create sentiment data structure if not present
                enhanced_sentiment = self._process_sentiment_data(market_data)
                sentiment_data['sentiment'] = enhanced_sentiment
            
            # Ensure OHLCV data is available for sentiment calculations
            if not sentiment_data['ohlcv'] and 'ohlcv' in market_data:
                sentiment_data['ohlcv'] = market_data['ohlcv']
            
            # Validate the prepared data
            if self._validate_sentiment_data(sentiment_data):
                self.logger.info("Sentiment data validation passed")
            else:
                self.logger.warning("Sentiment data validation failed, using default values")
                # Ensure we have at least the minimum required structure
                if 'sentiment' not in sentiment_data:
                    sentiment_data['sentiment'] = {
                        'funding_rate': 0.0001,
                        'long_short_ratio': 1.0,
                        'liquidations': []
                    }
            
            self.logger.debug(f"Prepared sentiment data with keys: {list(sentiment_data.keys())}")
            return sentiment_data
            
        except Exception as e:
            self.logger.error(f"Error preparing sentiment data: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            # Return a minimal valid structure
            return {
                'sentiment': {
                    'funding_rate': 0.0001,
                    'long_short_ratio': 1.0,
                    'liquidations': []
                },
                'ohlcv': market_data.get('ohlcv', {}),
                'symbol': market_data.get('symbol', ''),
                'exchange': market_data.get('exchange', ''),
                'timestamp': market_data.get('timestamp', int(time.time() * 1000))
            }

    def _setup_price_structure_attributes(self, price_structure_indicator):
        """Set up required attributes for price structure indicator."""
        # Define default timeframe map
        default_timeframe_map = {
            'base': '1',
            'ltf': '5',
            'mtf': '30',
            'htf': '240'
        }

        # Check if timeframe_map attribute exists, create it if missing
        if not hasattr(price_structure_indicator, 'timeframe_map'):
            # If the config has timeframes, use those instead of defaults
            if self.config and 'timeframes' in self.config:
                try:
                    timeframe_map = {
                        tf: str(self.config['timeframes'][tf]['interval'])
                        for tf in ['base', 'ltf', 'mtf', 'htf']
                        if tf in self.config['timeframes']
                    }
                    # Fill in any missing with defaults
                    for tf in default_timeframe_map:
                        if tf not in timeframe_map:
                            timeframe_map[tf] = default_timeframe_map[tf]
                except Exception as e:
                    self.logger.warning(f"Error getting timeframes from config: {str(e)}")
                    timeframe_map = default_timeframe_map.copy()
            else:
                # Use default values
                timeframe_map = default_timeframe_map.copy()
                
            # Assign the timeframe map to the indicator
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
        if 'base' in price_structure_indicator.timeframe_map:
            reverse_timeframe_map['base'] = 'base'
            base_interval = price_structure_indicator.timeframe_map['base']
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
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
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
            
            # Summary of validation results
            self.logger.info("\n=== Market Data Validation Summary ===")
            self.logger.info(f"Symbol: {symbol}")
            self.logger.info(f"Valid Timeframes: {len(valid_timeframes)}/{len(ohlcv)} ({', '.join(valid_timeframes)})")
            self.logger.info(f"Has Orderbook: {'Yes' if 'orderbook' in market_data and isinstance(market_data['orderbook'], dict) else 'No'}")
            self.logger.info(f"Has Trades: {'Yes' if 'trades' in market_data and isinstance(market_data['trades'], list) and market_data['trades'] else 'No'}")
            self.logger.info(f"Has Ticker: {'Yes' if 'ticker' in market_data and isinstance(market_data['ticker'], dict) else 'No'}")
            
            # Final validation result
            validation_result = len(valid_timeframes) > 0
            self.logger.info(f"Market data validation result: {'Success' if validation_result else 'Failed'}")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return False

    def _normalize_weights(self) -> None:
        """Normalize weights to ensure they sum to 1.0."""
        if not hasattr(self, 'weights') or not self.weights:
            self.logger.warning("No weights to normalize")
            return
            
        # Normalize main component weights
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {k: v / total_weight for k, v in self.weights.items()}
            self.logger.debug(f"Normalized component weights: {self.weights}")
        else:
            self.logger.warning("Total weight is zero, cannot normalize component weights")
            
        # Normalize sub-component weights if they exist
        if hasattr(self, 'sub_component_weights') and self.sub_component_weights:
            for component, weights in self.sub_component_weights.items():
                total = sum(weights.values())
                if total > 0:
                    self.sub_component_weights[component] = {k: v / total for k, v in weights.items()}
            self.logger.debug(f"Normalized sub-component weights")

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
                    # If orderbook validation fails but indicator is orderflow, 
                    # ensure we have at least an empty but valid structure
                    if indicator_name == 'orderflow':
                        self.logger.warning("Orderbook validation failed for orderflow indicator, creating minimal valid structure")
                        data['orderbook'] = {'bids': [], 'asks': []}
                    else:
                        return False
            
            # Validate trades if required
            if 'trades' in required_fields:
                # For orderflow indicators, we need either processed_trades or trades
                if indicator_name == 'orderflow':
                    has_trades = (
                        ('processed_trades' in data and data['processed_trades']) or
                        ('trades' in data and data['trades']) or
                        ('trades_df' in data and not data['trades_df'].empty if isinstance(data.get('trades_df'), pd.DataFrame) else False)
                    )
                    
                    if not has_trades:
                        self.logger.error(f"No valid trade data found for {indicator_name}")
                        return False
                else:
                    # For other indicators, just check if trades exist
                    if 'trades' not in data or not data['trades']:
                        self.logger.error(f"Missing trades data for {indicator_name}")
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
            
            # Validate components field exists and is a dictionary
            if not isinstance(result['components'], dict):
                self.logger.error("Components field is not a dictionary")
                return False
                
            # Check if components are empty
            if not result['components']:
                self.logger.warning("Component scores dictionary is empty")
                # Don't fail validation for this, just warn
            
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
            self.logger.error(f"Error analyzing correlations: {str(e)}")
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
            
            for tf, data in ohlcv_data.items():
                self.logger.debug(f"\nTimeframe {tf}:")
                self.logger.debug(f"Data type: {type(data)}")
                
                # Handle different data formats
                df = None
                if isinstance(data, pd.DataFrame):
                    # Direct DataFrame format (new format)
                    df = data
                    self.logger.debug(f"Using direct DataFrame for {tf}")
                elif isinstance(data, dict) and 'data' in data and isinstance(data['data'], pd.DataFrame):
                    # Nested dict with 'data' key containing DataFrame (old format)
                    df = data['data']
                    self.logger.debug(f"Using nested dictionary DataFrame for {tf}")
                
                if df is not None:
                    self.logger.debug(f"DataFrame shape: {df.shape}, columns: {list(df.columns)}")
                    
                    # Check if DataFrame is empty
                    if df.empty:
                        self.logger.warning(f"Empty DataFrame for timeframe {tf}")
                        continue
                    
                    # Check for required columns
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    if missing_columns:
                        self.logger.warning(f"Missing columns in {tf} DataFrame: {', '.join(missing_columns)}")
                        continue
                    
                    # If we get here, we have a valid timeframe
                    valid_timeframe = True
                    self.logger.debug(f"Valid DataFrame for timeframe {tf}")
                else:
                    self.logger.warning(f"Unsupported data type for timeframe {tf}: {type(data)}")
            
            if not valid_timeframe:
                self.logger.error("No valid timeframe found in OHLCV data")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating OHLCV structure: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False

    def _validate_orderbook_structure(self, orderbook: Dict[str, Any]) -> bool:
        """Validate orderbook data structure."""
        try:
            self.logger.debug("\n=== Validating Orderbook Structure ===")
            self.logger.debug(f"Input keys: {list(orderbook.keys())}")
            
            # Handle Bybit's nested orderbook format
            if 'result' in orderbook and isinstance(orderbook['result'], dict):
                result_data = orderbook['result']
                if 'b' in result_data and 'a' in result_data:
                    self.logger.debug("Detected Bybit orderbook format with 'result.b' and 'result.a'")
                    # Extract and update the orderbook structure
                    orderbook['bids'] = result_data['b']
                    orderbook['asks'] = result_data['a']
                    if 'ts' in result_data:
                        orderbook['timestamp'] = result_data['ts']
                    self.logger.debug(f"Extracted {len(orderbook['bids'])} bids and {len(orderbook['asks'])} asks from Bybit format")
            
            # Required fields
            required_fields = ['bids', 'asks', 'timestamp']
            
            # Check all required fields exist
            if not all(field in orderbook for field in required_fields):
                missing = [f for f in required_fields if f not in orderbook]
                self.logger.error(f"Missing orderbook fields: {missing}")
                
                # Auto-fix: Add timestamp if it's missing
                if 'timestamp' in missing:
                    orderbook['timestamp'] = int(time.time() * 1000)
                    self.logger.warning(f"Added missing timestamp field to orderbook: {orderbook['timestamp']}")
                    missing.remove('timestamp')
                
                # If still missing fields after auto-fix attempts
                if missing:
                    self.logger.error(f"Still missing required orderbook fields after auto-fix: {missing}")
                    # Create minimal valid structure with empty lists for missing bid/ask fields
                    if 'bids' in missing:
                        orderbook['bids'] = []
                    if 'asks' in missing:
                        orderbook['asks'] = []
                    self.logger.warning("Orderbook validation failed, creating minimal valid structure")
                
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

    def _validate_trade_data(self, market_data: Dict[str, Any]) -> bool:
        """Validate trades data structure."""
        try:
            self.logger.debug("\n=== Validating Trade Data ===")
            
            # Check if trades data exists
            if 'trades' not in market_data:
                self.logger.error("Missing trades data")
                return False
                
            trades_data = market_data['trades']
            
            # Check if trades data is a list
            if not isinstance(trades_data, list):
                self.logger.error(f"Trades data must be a list, got {type(trades_data)}")
                return False
                
            # Check if trades data is empty
            if not trades_data:
                self.logger.warning("Trades data is empty")
                return False
                
            # Check required fields in each trade
            required_fields = ['price', 'amount', 'side', 'timestamp']
            invalid_trades = 0
            
            for i, trade in enumerate(trades_data[:100]):  # Check first 100 trades
                if not isinstance(trade, dict):
                    invalid_trades += 1
                    continue
                    
                missing_fields = [f for f in required_fields if f not in trade]
                if missing_fields:
                    self.logger.debug(f"Trade {i} missing fields: {missing_fields}")
                    invalid_trades += 1
                    
            # Log validation results
            self.logger.debug(f"Checked {min(100, len(trades_data))} trades, found {invalid_trades} invalid")
            
            # Allow some tolerance for invalid trades (10%)
            if invalid_trades > min(10, len(trades_data) * 0.1):
                self.logger.error(f"Too many invalid trades: {invalid_trades}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating trade data: {str(e)}")
            return False

    def _validate_technical_data(self, market_data: Dict[str, Any]) -> bool:
        """Validate technical analysis data requirements."""
        try:
            self.logger.debug("\n=== Validating Technical Data ===")
            
            # Check if OHLCV data exists
            if 'ohlcv' not in market_data:
                self.logger.error("Missing OHLCV data required for technical analysis")
                return False
                
            ohlcv_data = market_data['ohlcv']
            
            # Check if OHLCV data is a dictionary
            if not isinstance(ohlcv_data, dict):
                self.logger.error(f"OHLCV data must be a dictionary, got {type(ohlcv_data)}")
                return False
                
            # Check if OHLCV data is empty
            if not ohlcv_data:
                self.logger.error("OHLCV data is empty")
                return False
                
            # Check if at least one timeframe is available
            valid_timeframes = 0
            for timeframe, df in ohlcv_data.items():
                if not isinstance(df, pd.DataFrame):
                    self.logger.warning(f"Timeframe {timeframe} is not a DataFrame")
                    continue
                    
                if df.empty:
                    self.logger.warning(f"Timeframe {timeframe} DataFrame is empty")
                    continue
                    
                # Check required columns
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    self.logger.warning(f"Timeframe {timeframe} missing columns: {missing_columns}")
                    continue
                    
                # Check if there are enough data points
                if len(df) < 20:  # Minimum required for most technical indicators
                    self.logger.warning(f"Timeframe {timeframe} has insufficient data points: {len(df)}")
                    continue
                    
                valid_timeframes += 1
                
            # Log validation results
            self.logger.debug(f"Found {valid_timeframes} valid timeframes out of {len(ohlcv_data)}")
            
            # Require at least one valid timeframe
            if valid_timeframes == 0:
                self.logger.error("No valid timeframes found for technical analysis")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating technical data: {str(e)}")
            return False
            
    def _validate_volume_data(self, market_data: Dict[str, Any]) -> bool:
        """Validate volume analysis data requirements."""
        try:
            self.logger.debug("\n=== Validating Volume Data ===")
            
            # Check if OHLCV data exists
            if 'ohlcv' not in market_data:
                self.logger.error("Missing OHLCV data required for volume analysis")
                return False
                
            ohlcv_data = market_data['ohlcv']
            
            # Check if OHLCV data is a dictionary
            if not isinstance(ohlcv_data, dict):
                self.logger.error(f"OHLCV data must be a dictionary, got {type(ohlcv_data)}")
                return False
                
            # Check if OHLCV data is empty
            if not ohlcv_data:
                self.logger.error("OHLCV data is empty")
                return False
                
            # Check if at least one timeframe is available with volume data
            valid_timeframes = 0
            for timeframe, df in ohlcv_data.items():
                if not isinstance(df, pd.DataFrame):
                    self.logger.warning(f"Timeframe {timeframe} is not a DataFrame")
                    continue
                    
                if df.empty:
                    self.logger.warning(f"Timeframe {timeframe} DataFrame is empty")
                    continue
                    
                # Check required columns
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    self.logger.warning(f"Timeframe {timeframe} missing columns: {missing_columns}")
                    continue
                    
                # Check if there are enough data points
                if len(df) < 20:  # Minimum required for most volume indicators
                    self.logger.warning(f"Timeframe {timeframe} has insufficient data points: {len(df)}")
                    continue
                    
                # Check if volume data is valid
                if 'volume' in df.columns and df['volume'].sum() == 0:
                    self.logger.warning(f"Timeframe {timeframe} has zero volume data")
                    continue
                    
                valid_timeframes += 1
                
            # Log validation results
            self.logger.debug(f"Found {valid_timeframes} valid timeframes with volume data out of {len(ohlcv_data)}")
            
            # Check if trades data exists for enhanced volume analysis
            if 'trades' not in market_data or not market_data['trades']:
                self.logger.warning("Missing trades data for enhanced volume analysis")
                # Not a critical error if we have OHLCV with volume
                
            # Require at least one valid timeframe
            if valid_timeframes == 0:
                self.logger.error("No valid timeframes found for volume analysis")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating volume data: {str(e)}")
            return False
            
    def _validate_orderflow_data(self, market_data: Dict[str, Any]) -> bool:
        """Validate orderflow analysis data requirements."""
        try:
            self.logger.debug("\n=== Validating Orderflow Data ===")
            
            # Check if trades data exists
            if 'trades' not in market_data:
                self.logger.error("Missing trades data required for orderflow analysis")
                return False
                
            trades_data = market_data['trades']
            
            # Check if trades data is a list
            if not isinstance(trades_data, list):
                self.logger.error(f"Trades data must be a list, got {type(trades_data)}")
                return False
                
            # Check if trades data is empty
            if not trades_data:
                self.logger.error("Trades data is empty")
                return False
                
            # Check if trades have required fields
            required_fields = ['price', 'amount', 'side', 'timestamp']
            valid_trades = 0
            
            for trade in trades_data[:100]:  # Check first 100 trades
                if not isinstance(trade, dict):
                    continue
                    
                # Check for alternative field names
                trade_fields = set(trade.keys())
                
                # Map common alternative field names
                field_mapping = {
                    'price': ['price', 'p'],
                    'amount': ['amount', 'size', 'quantity', 'v'],
                    'side': ['side', 'S', 'direction'],
                    'timestamp': ['timestamp', 'time', 'T', 'date']
                }
                
                # Check if all required fields are present (with alternatives)
                missing_fields = []
                for req_field in required_fields:
                    alternatives = field_mapping.get(req_field, [req_field])
                    if not any(alt in trade_fields for alt in alternatives):
                        missing_fields.append(req_field)
                
                if missing_fields:
                    continue
                    
                valid_trades += 1
                
            # Log validation results
            self.logger.debug(f"Found {valid_trades} valid trades out of {min(len(trades_data), 100)} checked")
            
            # Check if orderbook data exists for enhanced orderflow analysis
            if 'orderbook' not in market_data:
                self.logger.warning("Missing orderbook data for enhanced orderflow analysis")
                # Not a critical error if we have valid trades
                
            # Require at least 10 valid trades
            if valid_trades < 10:
                self.logger.error(f"Insufficient valid trades for orderflow analysis: {valid_trades}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating orderflow data: {str(e)}")
            return False

    def _validate_sentiment_data(self, market_data: Dict[str, Any]) -> bool:
        """Validate sentiment data structure."""
        try:
            self.logger.debug("\n=== Validating Sentiment Data ===")
            
            # Check if sentiment data exists
            if 'sentiment' not in market_data:
                self.logger.error("Missing sentiment data")
                return False
                
            # Check if OHLCV data exists (required for some sentiment calculations)
            if 'ohlcv' not in market_data:
                self.logger.error("Missing OHLCV data required for sentiment analysis")
                return False
                
            sentiment_data = market_data['sentiment']
            
            # Check if sentiment data is a dictionary
            if not isinstance(sentiment_data, dict):
                self.logger.error(f"Sentiment data must be a dictionary, got {type(sentiment_data)}")
                return False
                
            # Check required fields
            required_fields = ['funding_rate', 'long_short_ratio']
            missing_fields = [f for f in required_fields if f not in sentiment_data]
            
            if missing_fields:
                self.logger.error(f"Missing required sentiment fields: {missing_fields}")
                return False
                
            # Validate data types
            if not isinstance(sentiment_data.get('funding_rate'), (int, float)):
                self.logger.error(f"Invalid funding_rate type: {type(sentiment_data.get('funding_rate'))}")
                return False
                
            if not isinstance(sentiment_data.get('long_short_ratio'), (int, float)):
                self.logger.error(f"Invalid long_short_ratio type: {type(sentiment_data.get('long_short_ratio'))}")
                return False
                
            # Validate OHLCV data for sentiment calculations
            ohlcv_data = market_data['ohlcv']
            if not isinstance(ohlcv_data, dict) or not ohlcv_data:
                self.logger.error("Invalid OHLCV data for sentiment analysis")
                return False
                
            # Check if at least one timeframe is available
            if not any(isinstance(df, pd.DataFrame) and not df.empty for df in ohlcv_data.values()):
                self.logger.error("No valid timeframes found in OHLCV data for sentiment analysis")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating sentiment data: {str(e)}")
            return False

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

    def _process_sentiment_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and standardize sentiment data with enhanced metrics."""
        try:
            self.logger.debug("Processing sentiment data with enhanced metrics")
            
            # Get existing sentiment data
            sentiment_data = market_data.get('sentiment', {})
            ticker_data = market_data.get('ticker', {})
            ohlcv_data = market_data.get('ohlcv', {})
            
            # Create a comprehensive sentiment data structure
            enhanced_sentiment = {
                # Basic sentiment metrics
                'funding_rate': 0.0001,  # Default value
                'long_short_ratio': 1.0,  # Neutral by default
                'liquidations': [],
                
                # Enhanced metrics
                'price_change_24h': 0.0,
                'volume_change_24h': 0.0,
                'volatility_24h': 0.0,
                'market_trend': 'neutral',
                'social_sentiment': 50.0,  # Neutral by default
                'fear_greed_index': 50,    # Neutral by default
                
                # Metadata
                'timestamp': int(time.time() * 1000),
                'source': 'enhanced_processor'
            }
            
            # Extract funding rate from ticker or sentiment data
            if 'funding_rate' in sentiment_data:
                enhanced_sentiment['funding_rate'] = float(sentiment_data['funding_rate'])
            elif ticker_data and 'fundingRate' in ticker_data:
                enhanced_sentiment['funding_rate'] = float(ticker_data['fundingRate'])
            
            # Extract long/short ratio
            if 'long_short_ratio' in sentiment_data:
                enhanced_sentiment['long_short_ratio'] = float(sentiment_data['long_short_ratio'])
            
            # Extract liquidations
            if 'liquidations' in sentiment_data:
                enhanced_sentiment['liquidations'] = sentiment_data['liquidations']
            
            # Calculate price change from ticker
            if ticker_data:
                if 'percentage' in ticker_data:
                    enhanced_sentiment['price_change_24h'] = float(ticker_data['percentage'])
                elif 'change' in ticker_data:
                    enhanced_sentiment['price_change_24h'] = float(ticker_data['change'])
                elif 'priceChangePercent' in ticker_data:
                    enhanced_sentiment['price_change_24h'] = float(ticker_data['priceChangePercent'])
            
            # Calculate volatility from OHLCV data
            if ohlcv_data and 'base' in ohlcv_data and isinstance(ohlcv_data['base'], pd.DataFrame) and not ohlcv_data['base'].empty:
                df = ohlcv_data['base']
                if len(df) > 1:
                    # Calculate daily volatility as normalized high-low range
                    try:
                        # Use the last 24 candles (assuming 1h candles) or all available
                        lookback = min(24, len(df))
                        recent_df = df.iloc[-lookback:]
                        
                        # Calculate normalized range
                        avg_price = recent_df['close'].mean()
                        if avg_price > 0:
                            ranges = (recent_df['high'] - recent_df['low']) / avg_price
                            enhanced_sentiment['volatility_24h'] = float(ranges.mean() * 100)  # As percentage
                            
                            # Calculate volume change
                            if len(df) > lookback:
                                current_vol = recent_df['volume'].sum()
                                prev_vol = df.iloc[-2*lookback:-lookback]['volume'].sum()
                                if prev_vol > 0:
                                    enhanced_sentiment['volume_change_24h'] = float((current_vol / prev_vol - 1) * 100)  # As percentage
                    except Exception as e:
                        self.logger.warning(f"Error calculating volatility: {str(e)}")
            
            # Determine market trend based on price change and volatility
            price_change = enhanced_sentiment['price_change_24h']
            volatility = enhanced_sentiment['volatility_24h']
            
            if price_change > 3:
                enhanced_sentiment['market_trend'] = 'strongly_bullish'
            elif price_change > 1:
                enhanced_sentiment['market_trend'] = 'bullish'
            elif price_change < -3:
                enhanced_sentiment['market_trend'] = 'strongly_bearish'
            elif price_change < -1:
                enhanced_sentiment['market_trend'] = 'bearish'
            else:
                enhanced_sentiment['market_trend'] = 'neutral'
            
            # Adjust for high volatility
            if volatility > 5 and abs(price_change) < 1:
                enhanced_sentiment['market_trend'] = 'volatile_neutral'
            
            # Calculate social sentiment (placeholder - would be replaced with actual data in production)
            # In a real implementation, this would come from social media sentiment analysis
            # Here we're just deriving it from price action as a placeholder
            social_sentiment = 50 + price_change
            enhanced_sentiment['social_sentiment'] = float(np.clip(social_sentiment, 0, 100))
            
            # Calculate fear & greed index (placeholder)
            # This combines multiple metrics into a single index
            fear_greed = 50
            fear_greed += price_change * 2  # Price action component
            fear_greed += enhanced_sentiment['volume_change_24h'] * 0.5  # Volume component
            fear_greed -= volatility * 2  # Volatility component (higher volatility = more fear)
            fear_greed += (enhanced_sentiment['long_short_ratio'] - 1) * 25  # Position component
            fear_greed -= enhanced_sentiment['funding_rate'] * 1000  # Funding rate component
            
            enhanced_sentiment['fear_greed_index'] = int(np.clip(fear_greed, 0, 100))
            
            # Log the enhanced sentiment data
            self.logger.debug(f"Enhanced sentiment metrics: funding_rate={enhanced_sentiment['funding_rate']:.6f}, "
                             f"price_change_24h={enhanced_sentiment['price_change_24h']:.2f}%, "
                             f"volatility_24h={enhanced_sentiment['volatility_24h']:.2f}%, "
                             f"market_trend={enhanced_sentiment['market_trend']}, "
                             f"fear_greed_index={enhanced_sentiment['fear_greed_index']}")
            
            return enhanced_sentiment
            
        except Exception as e:
            self.logger.error(f"Error processing enhanced sentiment data: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return {
                'funding_rate': 0.0001,
                'long_short_ratio': 1.0,
                'liquidations': [],
                'price_change_24h': 0.0,
                'volume_change_24h': 0.0,
                'volatility_24h': 0.0,
                'market_trend': 'neutral',
                'social_sentiment': 50.0,
                'fear_greed_index': 50,
                'timestamp': int(time.time() * 1000),
                'source': 'fallback'
            }

    def _process_trades(self, trades_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process trades data handling both WebSocket and REST formats with improved fallback mechanisms."""
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
            fixed_price_count = 0
            
            # Find fallback price sources
            fallback_price = None
            
            # Try to get latest price from ticker
            if hasattr(self, 'market_data') and isinstance(self.market_data, dict):
                if 'ticker' in self.market_data and isinstance(self.market_data['ticker'], dict):
                    ticker_price = self.market_data['ticker'].get('last', self.market_data['ticker'].get('last_price', 0))
                    if ticker_price and float(ticker_price) > 0:
                        fallback_price = float(ticker_price)
                        self.logger.debug(f"Using ticker price as fallback: {fallback_price}")
                
                # If no ticker price, try latest candle close price
                if fallback_price is None and 'ohlcv' in self.market_data:
                    ohlcv_data = self.market_data['ohlcv']
                    if isinstance(ohlcv_data, dict) and 'base' in ohlcv_data:
                        base_df = ohlcv_data['base']
                        if isinstance(base_df, pd.DataFrame) and not base_df.empty and 'close' in base_df.columns:
                            fallback_price = float(base_df['close'].iloc[-1])
                            self.logger.debug(f"Using latest OHLCV close as fallback: {fallback_price}")
            
            # Keep track of last valid price for fallback
            last_valid_price = fallback_price
            
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
                    
                    # If no valid price found and we have 'amount', try to derive price from 'cost'/'amount'
                    if price <= 0 and 'cost' in trade and 'amount' in trade:
                        cost = float(trade['cost'])
                        amount = float(trade['amount'])
                        if cost > 0 and amount > 0:
                            price = cost / amount
                            self.logger.debug(f"Derived price from cost/amount: {price}")
                    
                    # If still no valid price found, try to use ticker price if available
                    if price <= 0:
                        # Try ticker field inside trade
                        if 'ticker' in trade:
                            ticker_price = trade.get('ticker', {}).get('last', 0)
                            if ticker_price and float(ticker_price) > 0:
                                price = float(ticker_price)
                                self.logger.debug(f"Used ticker price from trade: {price}")
                                fixed_price_count += 1
                    
                    # If still no valid price and we have a fallback price, use it
                    if price <= 0 and fallback_price is not None:
                        price = fallback_price
                        self.logger.debug(f"Used global fallback price: {price}")
                        fixed_price_count += 1
                    
                    # If still no valid price, try using last valid price as fallback
                    if price <= 0 and last_valid_price is not None:
                        price = last_valid_price
                        self.logger.debug(f"Used last valid trade price: {price}")
                        fixed_price_count += 1
                    
                    # Extract and standardize trade data
                    processed_trade = {
                        'price': price,
                        'size': float(trade.get('size', trade.get('amount', trade.get('v', 0)))),
                        'side': trade.get('side', trade.get('S', '')).lower(),
                        'time': int(trade.get('time', trade.get('timestamp', trade.get('T', 0)))),
                        'id': str(trade.get('id', trade.get('trade_id', trade.get('i', trade.get('execId', '')))))
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
                        # Set a default side rather than rejecting the trade
                        processed_trade['side'] = 'buy' if processed_trade.get('id', '')[-1].isdigit() and int(processed_trade['id'][-1]) % 2 == 0 else 'sell'
                        self.logger.debug(f"Assigned default side: {processed_trade['side']}")
                        
                    if processed_trade['time'] <= 0:
                        invalid_time_count += 1
                        # Set current timestamp rather than rejecting
                        processed_trade['time'] = int(time.time() * 1000)
                        self.logger.debug(f"Assigned current timestamp: {processed_trade['time']}")
                        
                    processed_trades.append(processed_trade)
                    
                except Exception as e:
                    self.logger.error(f"Error processing trade: {str(e)}")
                    self.logger.debug(f"Problematic trade: {trade}")
                    continue
            
            # Log summary of validation issues instead of individual warnings
            if invalid_price_count > 0:
                self.logger.warning(f"Skipped {invalid_price_count} trades with invalid prices")
            if fixed_price_count > 0:
                self.logger.info(f"Fixed {fixed_price_count} trades using fallback prices")
            if invalid_size_count > 0:
                self.logger.warning(f"Skipped {invalid_size_count} trades with invalid sizes")
            if missing_side_count > 0:
                self.logger.info(f"Fixed {missing_side_count} trades with missing sides")
            if invalid_time_count > 0:
                self.logger.info(f"Fixed {invalid_time_count} trades with invalid timestamps")
                
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