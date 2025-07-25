"""Session analysis module."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from src.core.error.utils import handle_calculation_error, log_exceptions
from src.validation import DataValidator
from src.indicators.technical_indicators import TechnicalIndicators
from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.orderflow_indicators import OrderflowIndicators
from src.indicators.sentiment_indicators import SentimentIndicators
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.indicators.orderbook_indicators import OrderbookIndicators

class SessionAnalyzer:
    """Analyzes market data for specific trading sessions."""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """Initialize session analyzer.
        
        Args:
            config: Configuration dictionary
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize indicators
        self.sentiment = SentimentIndicators(config)
        self.volume = VolumeIndicators(config)
        self.orderflow = OrderflowIndicators(config)
        self.technical = TechnicalIndicators(config)
        self.price_structure = PriceStructureIndicators(config)
        self.orderbook = OrderbookIndicators(config)
        # Session configuration
        self.sessions = {
            'asia': {
                'start': '23:00',  # UTC
                'end': '07:00'
            },
            'london': {
                'start': '07:00',
                'end': '15:00'
            },
            'ny': {
                'start': '13:00',
                'end': '21:00'
            }
        }
    
    @log_exceptions(logging.getLogger(__name__))
    async def analyze_session(self, market_data: Dict[str, Any], session: str) -> Dict[str, Any]:
        """Analyze market data for a specific session.
        
        Args:
            market_data: Market data dictionary
            session: Session name ('asia', 'london', 'ny')
            
        Returns:
            Dictionary containing session analysis results
        """
        try:
            if session not in self.sessions:
                raise ValueError(f"Invalid session: {session}")
            
            # Get session time range
            session_range = self.sessions[session]
            start_time = pd.Timestamp.now(tz='UTC').normalize() + pd.Timedelta(session_range['start'])
            end_time = pd.Timestamp.now(tz='UTC').normalize() + pd.Timedelta(session_range['end'])
            
            # Filter market data for session
            session_data = self._filter_session_data(market_data, start_time, end_time)
            
            # Analyze session data
            analysis = await self._analyze_session_data(session_data)
            
            return {
                'session': session,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'analysis': analysis
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing session {session}: {str(e)}")
            raise
    
    def _filter_session_data(self, market_data: Dict[str, Any], start_time: pd.Timestamp, 
                           end_time: pd.Timestamp) -> Dict[str, Any]:
        """Filter market data for session time range."""
        try:
            filtered_data = market_data.copy()
            
            # Filter price data
            for timeframe, df in market_data['price_data'].items():
                mask = (df.index >= start_time) & (df.index <= end_time)
                filtered_data['price_data'][timeframe] = df[mask].copy()
            
            # Filter trades
            if 'trades' in market_data:
                trades_df = market_data['trades']
                mask = (trades_df.index >= start_time) & (trades_df.index <= end_time)
                filtered_data['trades'] = trades_df[mask].copy()
            
            return filtered_data
            
        except Exception as e:
            self.logger.error(f"Error filtering session data: {str(e)}")
            raise
    
    @handle_calculation_error(default_value={})
    async def _analyze_session_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze filtered session data."""
        try:
            # Calculate technical indicators
            technical_analysis = await self.technical.calculate(market_data)
            
            # Calculate volume indicators
            volume_analysis = await self.volume.calculate(market_data)
            
            # Calculate orderflow indicators
            orderflow_analysis = await self.orderflow.analyze_orderflow(market_data)
            
            # Calculate session statistics
            stats = self._calculate_session_stats(market_data)
            
            return {
                'technical': technical_analysis,
                'volume': volume_analysis,
                'orderflow': orderflow_analysis,
                'statistics': stats
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing session data: {str(e)}")
            raise
    
    def _calculate_session_stats(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate basic session statistics."""
        try:
            base_df = market_data['price_data']['base']
            
            return {
                'open': float(base_df['open'].iloc[0]),
                'high': float(base_df['high'].max()),
                'low': float(base_df['low'].min()),
                'close': float(base_df['close'].iloc[-1]),
                'volume': float(base_df['volume'].sum()),
                'trades': len(market_data.get('trades', [])),
                'volatility': float(base_df['high'].max() - base_df['low'].min()),
                'return': float((base_df['close'].iloc[-1] / base_df['open'].iloc[0] - 1) * 100)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating session statistics: {str(e)}")
            raise
