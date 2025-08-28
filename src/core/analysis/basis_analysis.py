"""
Basis Analysis Module

This module provides sophisticated analysis of spot-futures basis trading opportunities
in cryptocurrency markets. It analyzes price discrepancies between spot and perpetual/futures
markets to identify arbitrage and carry trade opportunities.

Key Features:
    - Real-time basis calculation and monitoring
    - Market depth analysis for execution feasibility
    - Trade flow analysis for market sentiment
    - Execution cost estimation including slippage
    - Risk-adjusted trading signal generation
    - Multi-exchange arbitrage detection

Trading Strategies Supported:
    - Cash and carry arbitrage
    - Reverse cash and carry
    - Funding rate arbitrage
    - Basis momentum trading

Mathematical Models:
    - Basis = Futures Price - Spot Price
    - Basis % = (Basis / Spot Price) × 100
    - Implied Funding = Basis % × 365 × 3 (for 8-hour funding)
    - Risk Score = weighted combination of basis size, depth, and flow

Usage:
    >>> analyzer = BasisAnalysis()
    >>> result = await analyzer.analyze_basis(
    ...     spot_data=spot_market_data,
    ...     futures_data=futures_market_data,
    ...     symbol="BTC/USDT"
    ... )

Author: Virtuoso CCXT Development Team
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class BasisAnalysis:
    """
    Analyzes spot vs futures basis and funding opportunities.
    
    This class provides comprehensive analysis of price discrepancies between
    spot and futures markets, identifying profitable arbitrage opportunities
    while accounting for execution costs and market risks.
    
    Attributes:
        metrics (Dict): Storage for calculated basis metrics and historical data
    
    Methods:
        analyze_basis: Main analysis entry point for spot-futures comparison
        _calculate_market_depth: Analyze orderbook depth and liquidity
        _analyze_trade_flow: Evaluate recent trading activity and sentiment
        _calculate_execution_costs: Estimate slippage and trading costs
        _generate_trading_signals: Generate risk-adjusted trading signals
    """
    
    def __init__(self):
        """
        Initialize the Basis Analysis engine.
        
        Sets up the metrics storage dictionary for tracking historical basis
        data and analysis results. This allows for trend analysis and 
        performance tracking over time.
        
        The metrics dictionary will store:
        - Historical basis values by symbol
        - Average funding rates
        - Arbitrage opportunity counts
        - Execution success metrics
        """
        self.metrics = {}
        
    async def analyze_basis(
        self,
        spot_data: Dict[str, Any],
        futures_data: Dict[str, Any],
        symbol: str
    ) -> Dict[str, Any]:
        """Analyze basis between spot and futures markets"""
        try:
            # Extract prices
            spot_price = float(spot_data['ticker']['last'])
            futures_price = float(futures_data['ticker']['last'])
            
            # Calculate basis metrics
            basis = futures_price - spot_price
            basis_percentage = (basis / spot_price) * 100
            
            # Calculate implied funding rate (annualized)
            # Assuming 8-hour funding intervals (3 times per day)
            funding_rate = (basis_percentage / 100) * (365 * 3)
            
            # Calculate market depths
            spot_depth = self._calculate_market_depth(spot_data['orderbook'])
            futures_depth = self._calculate_market_depth(futures_data['orderbook'])
            
            # Calculate trade flow metrics
            spot_flow = self._analyze_trade_flow(spot_data['recent_trades'])
            futures_flow = self._analyze_trade_flow(futures_data['recent_trades'])
            
            # Calculate execution costs
            spot_costs = self._calculate_execution_costs(spot_data['orderbook'], 1.0)  # 1 BTC example size
            futures_costs = self._calculate_execution_costs(futures_data['orderbook'], 1.0)
            
            return {
                'symbol': symbol,
                'timestamp': int(datetime.now().timestamp() * 1000),
                'spot_exchange': 'coinbase',
                'futures_exchange': 'bybit',
                'spot_price': spot_price,
                'futures_price': futures_price,
                'basis': basis,
                'basis_percentage': basis_percentage,
                'implied_funding': funding_rate,
                'market_depth': {
                    'spot': spot_depth,
                    'futures': futures_depth
                },
                'trade_flow': {
                    'spot': spot_flow,
                    'futures': futures_flow
                },
                'execution_costs': {
                    'spot': spot_costs,
                    'futures': futures_costs
                },
                'signals': self._generate_trading_signals(
                    basis_percentage,
                    spot_depth,
                    futures_depth,
                    spot_flow,
                    futures_flow
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing basis: {str(e)}")
            raise
            
    def _calculate_market_depth(self, orderbook: Dict[str, Any]) -> Dict[str, float]:
        """Calculate market depth metrics"""
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        bid_depth = sum(float(bid[1]) for bid in bids[:5])  # Top 5 levels
        ask_depth = sum(float(ask[1]) for ask in asks[:5])
        
        mid_price = (float(bids[0][0]) + float(asks[0][0])) / 2 if bids and asks else 0
        spread = float(asks[0][0]) - float(bids[0][0]) if bids and asks else 0
        spread_bps = (spread / mid_price) * 10000 if mid_price else 0
        
        return {
            'bid_depth': bid_depth,
            'ask_depth': ask_depth,
            'total_depth': bid_depth + ask_depth,
            'bid_ask_ratio': bid_depth / ask_depth if ask_depth else 0,
            'spread': spread,
            'spread_bps': spread_bps
        }
        
    def _analyze_trade_flow(self, trades: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze recent trade flow"""
        if not trades:
            return {
                'buy_volume': 0,
                'sell_volume': 0,
                'buy_count': 0,
                'sell_count': 0,
                'avg_buy_size': 0,
                'avg_sell_size': 0,
                'net_flow': 0,
                'flow_ratio': 0
            }
            
        buy_trades = [t for t in trades if t['side'].lower() == 'buy']
        sell_trades = [t for t in trades if t['side'].lower() == 'sell']
        
        buy_volume = sum(float(t['amount']) for t in buy_trades)
        sell_volume = sum(float(t['amount']) for t in sell_trades)
        
        return {
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'buy_count': len(buy_trades),
            'sell_count': len(sell_trades),
            'avg_buy_size': buy_volume / len(buy_trades) if buy_trades else 0,
            'avg_sell_size': sell_volume / len(sell_trades) if sell_trades else 0,
            'net_flow': buy_volume - sell_volume,
            'flow_ratio': buy_volume / sell_volume if sell_volume else float('inf')
        }
        
    def _calculate_execution_costs(
        self,
        orderbook: Dict[str, Any],
        size: float
    ) -> Dict[str, float]:
        """Calculate execution costs for a given size"""
        remaining_size = size
        total_cost = 0
        avg_price = 0
        slippage = 0
        
        # Calculate execution price
        for price, amount in orderbook.get('asks', []):
            price = float(price)
            amount = float(amount)
            
            if remaining_size <= 0:
                break
                
            executable = min(remaining_size, amount)
            total_cost += executable * price
            remaining_size -= executable
            
        if size > 0:
            avg_price = total_cost / size
            mid_price = (float(orderbook['asks'][0][0]) + float(orderbook['bids'][0][0])) / 2
            slippage = ((avg_price / mid_price) - 1) * 10000  # in bps
            
        return {
            'avg_price': avg_price,
            'total_cost': total_cost,
            'slippage_bps': slippage,
            'unfilled_size': remaining_size
        }
        
    def _generate_trading_signals(
        self,
        basis_percentage: float,
        spot_depth: Dict[str, float],
        futures_depth: Dict[str, float],
        spot_flow: Dict[str, float],
        futures_flow: Dict[str, float]
    ) -> Dict[str, Any]:
        """Generate trading signals based on analysis"""
        signals = {
            'basis_opportunity': False,
            'confidence': 0.0,
            'recommended_size': 0.0,
            'entry_threshold': 0.0,
            'exit_threshold': 0.0,
            'risk_score': 0.0,
            'factors': []
        }
        
        # Basis opportunity detection
        if abs(basis_percentage) > 0.5:  # More than 0.5% basis
            signals['basis_opportunity'] = True
            signals['factors'].append(f"Basis divergence: {basis_percentage:.2f}%")
            
            # Calculate confidence based on market depth and flow
            depth_ratio = min(
                spot_depth['total_depth'] / futures_depth['total_depth'],
                futures_depth['total_depth'] / spot_depth['total_depth']
            )
            
            flow_agreement = (
                (spot_flow['net_flow'] > 0 and futures_flow['net_flow'] > 0) or
                (spot_flow['net_flow'] < 0 and futures_flow['net_flow'] < 0)
            )
            
            # Confidence calculation
            confidence = 0.0
            confidence += min(abs(basis_percentage) / 2.0, 0.5)  # Up to 50% from basis
            confidence += depth_ratio * 0.3  # Up to 30% from depth
            confidence += 0.2 if flow_agreement else 0  # Up to 20% from flow agreement
            
            signals['confidence'] = min(confidence, 1.0)
            
            # Size recommendation
            max_spot_size = spot_depth['total_depth'] * 0.1  # 10% of available depth
            max_futures_size = futures_depth['total_depth'] * 0.1
            signals['recommended_size'] = min(max_spot_size, max_futures_size)
            
            # Thresholds
            signals['entry_threshold'] = abs(basis_percentage)
            signals['exit_threshold'] = abs(basis_percentage) * 0.3  # Exit at 30% of entry basis
            
            # Risk scoring
            risk_score = 0.0
            risk_score += min(abs(basis_percentage) / 10.0, 0.4)  # Up to 40% from basis size
            risk_score += (1 - depth_ratio) * 0.3  # Up to 30% from depth imbalance
            risk_score += 0.3 if not flow_agreement else 0  # Up to 30% from flow disagreement
            
            signals['risk_score'] = risk_score
            
        return signals 