from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import logging
import asyncio
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from src.indicators.technical_indicators import TechnicalIndicators
from src.indicators.orderflow_indicators import OrderflowIndicators
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.indicators.orderbook_indicators import OrderbookIndicators
from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.sentiment_indicators import SentimentIndicators

logger = logging.getLogger(__name__)

@dataclass
class AnalysisResult:
    timestamp: datetime
    symbol: str
    technical_score: float
    orderflow_score: float
    price_structure_score: float
    orderbook_score: float
    volume_score: float
    sentiment_score: float
    confluence_score: float
    signals: Dict[str, Any]
    metadata: Dict[str, Any]

class IntegratedAnalysis:
    def __init__(self, config: Dict[str, Any]):
        """Initialize the integrated analysis engine."""
        self.config = config
        
        # Initialize all indicator classes
        self.technical = TechnicalIndicators(config)
        self.orderflow = OrderflowIndicators(config)
        self.price_structure = PriceStructureIndicators(config)
        self.orderbook = OrderbookIndicators(config)
        self.volume = VolumeIndicators(config)
        self.sentiment = SentimentIndicators(config)
        
        # Get analysis weights from config
        self.weights = config.get('confluence', {}).get('weights', {
            'technical': 0.20,
            'orderflow': 0.20,
            'price_structure': 0.15,
            'orderbook': 0.15,
            'volume': 0.15,
            'sentiment': 0.15
        })
        
        self.logger.info(f"Using confluence weights: {self.weights}")
        
        # Initialize ThreadPoolExecutor for CPU-intensive calculations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        logger.info("Initialized IntegratedAnalysis engine")

    async def initialize(self, symbol: str) -> Dict[str, Any]:
        """Initialize analysis for a symbol."""
        try:
            # Initialize all indicator components in parallel
            tasks = [
                self.technical.initialize(symbol),
                self.orderflow.initialize(symbol),
                self.price_structure.initialize(symbol),
                self.orderbook.initialize(symbol),
                self.volume.initialize(symbol),
                self.sentiment.initialize(symbol)
            ]
            
            results = await asyncio.gather(*tasks)
            
            return {
                'symbol': symbol,
                'status': 'initialized',
                'components': {
                    'technical': results[0],
                    'orderflow': results[1],
                    'price_structure': results[2],
                    'orderbook': results[3],
                    'volume': results[4],
                    'sentiment': results[5]
                }
            }
            
        except Exception as e:
            logger.error(f"Error initializing analysis for {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'status': 'error',
                'error': str(e)
            }

    async def analyze(self, market_data: Dict[str, Any]) -> AnalysisResult:
        """Perform integrated analysis on market data."""
        try:
            symbol = market_data['symbol']
            timestamp = datetime.fromtimestamp(market_data['timestamp'] / 1000)
            
            # Run all analysis components in parallel
            tasks = [
                self._analyze_technical(market_data),
                self._analyze_orderflow(market_data),
                self._analyze_price_structure(market_data),
                self._analyze_orderbook(market_data),
                self._analyze_volume(market_data),
                self._analyze_sentiment(market_data)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Extract scores and signals
            technical_result, orderflow_result, price_structure_result, orderbook_result, volume_result, sentiment_result = results
            
            # Calculate confluence score
            confluence_score = self._calculate_confluence_score(results)
            
            # Combine all signals
            signals = self._combine_signals(results)
            
            # Create metadata
            metadata = {
                'analysis_duration': (datetime.now() - timestamp).total_seconds(),
                'component_scores': {
                    'technical': technical_result['score'],
                    'orderflow': orderflow_result['score'],
                    'price_structure': price_structure_result['score'],
                    'orderbook': orderbook_result['score'],
                    'volume': volume_result['score'],
                    'sentiment': sentiment_result['score']
                },
                'timeframes_analyzed': market_data.get('timeframes', []),
                'data_quality': self._assess_data_quality(market_data)
            }
            
            return AnalysisResult(
                timestamp=timestamp,
                symbol=symbol,
                technical_score=technical_result['score'],
                orderflow_score=orderflow_result['score'],
                price_structure_score=price_structure_result['score'],
                orderbook_score=orderbook_result['score'],
                volume_score=volume_result['score'],
                sentiment_score=sentiment_result['score'],
                confluence_score=confluence_score,
                signals=signals,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error in integrated analysis: {str(e)}")
            raise

    async def _analyze_technical(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze technical indicators."""
        return await self.technical.calculate(market_data)

    async def _analyze_orderflow(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze orderflow indicators."""
        return await self.orderflow.calculate(market_data)

    async def _analyze_price_structure(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze price structure indicators."""
        return await self.price_structure.calculate(market_data)

    async def _analyze_orderbook(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze orderbook indicators."""
        return await self.orderbook.calculate(market_data)

    async def _analyze_volume(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze volume indicators."""
        return await self.volume.calculate(market_data)

    async def _analyze_sentiment(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sentiment indicators."""
        return await self.sentiment.calculate(market_data)

    def _calculate_confluence_score(self, component_results: List[Dict[str, Any]]) -> float:
        """Calculate the overall confluence score."""
        try:
            # Extract scores
            scores = [
                component_results[0]['score'] * self.weights['technical'],
                component_results[1]['score'] * self.weights['orderflow'],
                component_results[2]['score'] * self.weights['price_structure'],
                component_results[3]['score'] * self.weights['orderbook'],
                component_results[4]['score'] * self.weights['volume'],
                component_results[5]['score'] * self.weights['sentiment']
            ]
            
            # Calculate weighted average
            weighted_score = sum(scores)
            
            # Calculate score alignment
            score_std = np.std(scores)
            alignment_factor = 1 - (score_std / 100)  # Higher alignment = lower std dev
            
            # Adjust score based on alignment
            final_score = weighted_score * alignment_factor
            
            return min(max(final_score, 0), 100)  # Ensure score is between 0 and 100
            
        except Exception as e:
            logger.error(f"Error calculating confluence score: {str(e)}")
            return 50.0  # Return neutral score on error

    def _combine_signals(self, component_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine signals from all components."""
        try:
            combined_signals = {
                'technical': component_results[0].get('signals', {}),
                'orderflow': component_results[1].get('signals', {}),
                'price_structure': component_results[2].get('signals', {}),
                'orderbook': component_results[3].get('signals', {}),
                'volume': component_results[4].get('signals', {}),
                'sentiment': component_results[5].get('signals', {})
            }
            
            # Add signal agreement analysis
            signal_agreement = self._analyze_signal_agreement(combined_signals)
            combined_signals['agreement'] = signal_agreement
            
            return combined_signals
            
        except Exception as e:
            logger.error(f"Error combining signals: {str(e)}")
            return {}

    def _analyze_signal_agreement(self, signals: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze agreement between different signal components."""
        try:
            # Count bullish and bearish signals
            signal_counts = {'bullish': 0, 'bearish': 0, 'neutral': 0}
            
            for component, component_signals in signals.items():
                if isinstance(component_signals, dict):
                    bias = component_signals.get('bias', 'neutral').lower()
                    signal_counts[bias] += 1
            
            # Calculate agreement percentage
            total_components = sum(signal_counts.values())
            if total_components > 0:
                agreement_percentage = (max(signal_counts.values()) / total_components) * 100
            else:
                agreement_percentage = 0
            
            # Determine overall bias
            if signal_counts['bullish'] > signal_counts['bearish']:
                overall_bias = 'bullish'
            elif signal_counts['bearish'] > signal_counts['bullish']:
                overall_bias = 'bearish'
            else:
                overall_bias = 'neutral'
            
            return {
                'overall_bias': overall_bias,
                'agreement_percentage': agreement_percentage,
                'signal_distribution': signal_counts
            }
            
        except Exception as e:
            logger.error(f"Error analyzing signal agreement: {str(e)}")
            return {
                'overall_bias': 'neutral',
                'agreement_percentage': 0,
                'signal_distribution': {'bullish': 0, 'bearish': 0, 'neutral': 0}
            }

    def _assess_data_quality(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of input market data."""
        try:
            quality_metrics = {
                'completeness': 0.0,
                'timeliness': 0.0,
                'reliability': 0.0
            }
            
            # Check data completeness
            required_fields = ['ohlcv', 'orderbook', 'trades']
            available_fields = sum(1 for field in required_fields if field in market_data)
            quality_metrics['completeness'] = (available_fields / len(required_fields)) * 100
            
            # Check data timeliness
            current_time = datetime.now().timestamp() * 1000
            data_timestamp = market_data.get('timestamp', 0)
            time_difference = (current_time - data_timestamp) / 1000  # Convert to seconds
            
            if time_difference <= 5:  # Within 5 seconds
                quality_metrics['timeliness'] = 100
            elif time_difference <= 30:  # Within 30 seconds
                quality_metrics['timeliness'] = 75
            elif time_difference <= 60:  # Within 1 minute
                quality_metrics['timeliness'] = 50
            else:
                quality_metrics['timeliness'] = 25
            
            # Check data reliability
            reliability_score = 100
            
            # Reduce score for missing or invalid data
            if 'ohlcv' in market_data and isinstance(market_data['ohlcv'], dict):
                if any(pd.isna(market_data['ohlcv'].get(field, 0)) for field in ['open', 'high', 'low', 'close', 'volume']):
                    reliability_score -= 20
            
            if 'orderbook' in market_data:
                if not market_data['orderbook'].get('bids') or not market_data['orderbook'].get('asks'):
                    reliability_score -= 20
            
            quality_metrics['reliability'] = max(reliability_score, 0)
            
            # Calculate overall quality score
            quality_metrics['overall'] = sum(quality_metrics.values()) / len(quality_metrics)
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Error assessing data quality: {str(e)}")
            return {
                'completeness': 0.0,
                'timeliness': 0.0,
                'reliability': 0.0,
                'overall': 0.0
            } 