"""Dashboard Integration Service for real-time signal data."""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

class DashboardIntegrationService:
    """Service for fetching real-time signal data from dashboard."""
    
    def __init__(self, config: Dict[str, Any]):
        self.base_url = config.get('dashboard_url', 'http://localhost:8000')
        self.api_key = config.get('api_key')
        self.timeout = config.get('timeout', 30)
        self.logger = logging.getLogger(__name__)
    
    async def get_dashboard_overview(self) -> Dict[str, Any]:
        """Fetch complete dashboard overview with all signal data."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {self.api_key}'}
                url = f"{self.base_url}/api/v1/dashboard/overview"
                
                async with session.get(url, headers=headers, timeout=self.timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        return await self._process_dashboard_data(data)
                    else:
                        self.logger.error(f"Dashboard API error: {response.status}")
                        return {"signals": []}
                        
        except Exception as e:
            self.logger.error(f"Dashboard integration error: {e}")
            return {"signals": []}
    
    async def _process_dashboard_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate dashboard data structure."""
        processed_signals = []
        
        for signal_data in raw_data.get('signals', []):
            processed_signal = {
                "symbol": signal_data.get('symbol'),
                "confluence_signals": await self._build_confluence_signals(signal_data)
            }
            processed_signals.append(processed_signal)
        
        return {"signals": processed_signals}
    
    async def get_symbols_data(self) -> Dict[str, Any]:
        """Get symbols data with prices and confluence scores."""
        try:
            # For now, return empty symbols until we connect to the actual data source
            return {
                "symbols": [],
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting symbols data: {e}")
            return {
                "symbols": [],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _build_confluence_signals(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build complete confluence signals with all 11 components."""
        components = signal_data.get('components', {})
        confluence_signals = {}
        
        # Define signal type mappings and default values
        signal_mappings = {
            'momentum': self._calculate_momentum_signal,
            'technical': self._calculate_technical_signal,
            'volume': self._calculate_volume_signal,
            'orderflow': self._calculate_orderflow_signal,
            'orderbook': self._calculate_orderbook_signal,
            'sentiment': self._calculate_sentiment_signal,
            'price_action': self._calculate_price_action_signal,
            'beta_exp': self._calculate_beta_signal,
            'confluence': self._calculate_confluence_signal,
            'whale_act': self._calculate_whale_signal,
            'liquidation': self._calculate_liquidation_signal
        }
        
        for signal_type, calculator in signal_mappings.items():
            confluence_signals[signal_type] = await calculator(components, signal_data)
        
        return confluence_signals
    
    # Signal calculation methods (implement based on your specific logic)
    async def _calculate_momentum_signal(self, components: Dict, signal_data: Dict) -> Dict[str, Any]:
        """Calculate momentum signal from price data."""
        score = components.get('momentum', {}).get('score', 50.0)
        return {
            'confidence': float(score),
            'direction': 'bullish' if score > 60 else 'bearish' if score < 40 else 'neutral',
            'strength': 'strong' if abs(score - 50) > 20 else 'medium'
        }
    
    async def _calculate_technical_signal(self, components: Dict, signal_data: Dict) -> Dict[str, Any]:
        """Calculate technical analysis signal."""
        score = components.get('technical', {}).get('score', 50.0)
        return {
            'confidence': float(score),
            'direction': 'bullish' if score > 60 else 'bearish' if score < 40 else 'neutral',
            'strength': 'strong' if abs(score - 50) > 20 else 'medium'
        }
    
    async def _calculate_volume_signal(self, components: Dict, signal_data: Dict) -> Dict[str, Any]:
        """Calculate volume-based signal."""
        score = components.get('volume', {}).get('score', 50.0)
        return {
            'confidence': float(score),
            'direction': 'bullish' if score > 60 else 'bearish' if score < 40 else 'neutral',
            'strength': 'strong' if abs(score - 50) > 20 else 'medium'
        }
    
    async def _calculate_orderflow_signal(self, components: Dict, signal_data: Dict) -> Dict[str, Any]:
        """Calculate order flow signal."""
        score = components.get('orderflow', {}).get('score', 50.0)
        return {
            'confidence': float(score),
            'direction': 'bullish' if score > 60 else 'bearish' if score < 40 else 'neutral',
            'strength': 'strong' if abs(score - 50) > 20 else 'medium'
        }
    
    async def _calculate_orderbook_signal(self, components: Dict, signal_data: Dict) -> Dict[str, Any]:
        """Calculate order book signal."""
        score = components.get('orderbook', {}).get('score', 50.0)
        return {
            'confidence': float(score),
            'direction': 'bullish' if score > 60 else 'bearish' if score < 40 else 'neutral',
            'strength': 'strong' if abs(score - 50) > 20 else 'medium'
        }
    
    async def _calculate_sentiment_signal(self, components: Dict, signal_data: Dict) -> Dict[str, Any]:
        """Calculate sentiment signal."""
        score = components.get('sentiment', {}).get('score', 50.0)
        return {
            'confidence': float(score),
            'direction': 'bullish' if score > 60 else 'bearish' if score < 40 else 'neutral',
            'strength': 'strong' if abs(score - 50) > 20 else 'medium'
        }
    
    async def _calculate_price_action_signal(self, components: Dict, signal_data: Dict) -> Dict[str, Any]:
        """Calculate price action signal."""
        score = components.get('price_action', {}).get('score', 50.0)
        return {
            'confidence': float(score),
            'direction': 'bullish' if score > 60 else 'bearish' if score < 40 else 'neutral',
            'strength': 'strong' if abs(score - 50) > 20 else 'medium'
        }
    
    async def _calculate_beta_signal(self, components: Dict, signal_data: Dict) -> Dict[str, Any]:
        """Calculate beta exposure signal."""
        score = components.get('beta_exp', {}).get('score', 50.0)
        return {
            'confidence': float(score),
            'direction': 'bullish' if score > 60 else 'bearish' if score < 40 else 'neutral',
            'strength': 'strong' if abs(score - 50) > 20 else 'medium'
        }
    
    async def _calculate_confluence_signal(self, components: Dict, signal_data: Dict) -> Dict[str, Any]:
        """Calculate confluence signal."""
        score = components.get('confluence', {}).get('score', 50.0)
        return {
            'confidence': float(score),
            'direction': 'bullish' if score > 60 else 'bearish' if score < 40 else 'neutral',
            'strength': 'strong' if abs(score - 50) > 20 else 'medium'
        }
    
    async def _calculate_whale_signal(self, components: Dict, signal_data: Dict) -> Dict[str, Any]:
        """Calculate whale activity signal."""
        score = components.get('whale_act', {}).get('score', 50.0)
        return {
            'confidence': float(score),
            'direction': 'bullish' if score > 60 else 'bearish' if score < 40 else 'neutral',
            'strength': 'strong' if abs(score - 50) > 20 else 'medium'
        }
    
    async def _calculate_liquidation_signal(self, components: Dict, signal_data: Dict) -> Dict[str, Any]:
        """Calculate liquidation signal."""
        score = components.get('liquidation', {}).get('score', 50.0)
        return {
            'confidence': float(score),
            'direction': 'bullish' if score > 60 else 'bearish' if score < 40 else 'neutral',
            'strength': 'strong' if abs(score - 50) > 20 else 'medium'
        } 