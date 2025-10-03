from src.utils.task_tracker import create_tracked_task
"""
Portfolio Management System
Implements portfolio allocation, rebalancing, and performance tracking based on configuration.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
import yaml
from pathlib import Path


logger = logging.getLogger(__name__)


class RebalanceFrequency(str, Enum):
    HOURLY = "1h"
    DAILY = "1d"
    WEEKLY = "1w"
    MONTHLY = "1M"


@dataclass
class PortfolioPosition:
    """Represents a single portfolio position."""
    symbol: str
    current_allocation: float
    target_allocation: float
    current_value_usd: float
    current_quantity: float
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def allocation_drift(self) -> float:
        """Calculate allocation drift from target."""
        return abs(self.current_allocation - self.target_allocation)
    
    def needs_rebalancing(self, threshold: float = 0.05) -> bool:
        """Check if position needs rebalancing based on threshold."""
        return self.allocation_drift > threshold


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics."""
    total_value_usd: float
    total_pnl_usd: float
    total_pnl_percent: float
    daily_pnl_usd: float
    daily_pnl_percent: float
    max_drawdown: float
    sharpe_ratio: float
    turnover: float
    last_rebalance: Optional[datetime] = None
    positions_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'total_value_usd': self.total_value_usd,
            'total_pnl_usd': self.total_pnl_usd,
            'total_pnl_percent': self.total_pnl_percent,
            'daily_pnl_usd': self.daily_pnl_usd,
            'daily_pnl_percent': self.daily_pnl_percent,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'turnover': self.turnover,
            'last_rebalance': self.last_rebalance.isoformat() if self.last_rebalance else None,
            'positions_count': self.positions_count
        }


class PortfolioManager:
    """Manages portfolio allocation, rebalancing, and performance tracking."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.portfolio_config = config.get('portfolio', {})
        self.logger = logging.getLogger(__name__)
        
        # Portfolio configuration
        self.target_allocation = self.portfolio_config.get('target_allocation', {})
        self.rebalancing_config = self.portfolio_config.get('rebalancing', {})
        self.performance_config = self.portfolio_config.get('performance', {})
        
        # Rebalancing settings
        self.rebalancing_enabled = self.rebalancing_config.get('enabled', True)
        self.rebalancing_frequency = self.rebalancing_config.get('frequency', '1d')
        self.rebalancing_threshold = self.rebalancing_config.get('threshold', 0.05)
        
        # Performance settings
        self.max_turnover = self.performance_config.get('max_turnover', 2.0)
        
        # Portfolio state
        self.positions: Dict[str, PortfolioPosition] = {}
        self.portfolio_history: List[Dict[str, Any]] = []
        self.last_rebalance: Optional[datetime] = None
        self.rebalancing_task: Optional[asyncio.Task] = None
        
        # Validate configuration
        self._validate_configuration()
        
        self.logger.info(f"Portfolio Manager initialized")
        self.logger.info(f"Target allocation: {self.target_allocation}")
        self.logger.info(f"Rebalancing enabled: {self.rebalancing_enabled}")
        self.logger.info(f"Rebalancing frequency: {self.rebalancing_frequency}")
        self.logger.info(f"Rebalancing threshold: {self.rebalancing_threshold}")
    
    def _validate_configuration(self):
        """Validate portfolio configuration."""
        # Validate target allocation sums to 1.0
        if self.target_allocation:
            total_allocation = sum(self.target_allocation.values())
            if not (0.95 <= total_allocation <= 1.05):
                raise ValueError(f"Target allocation must sum to ~1.0, got {total_allocation}")
        
        # Validate rebalancing threshold
        if not (0.0 <= self.rebalancing_threshold <= 1.0):
            raise ValueError(f"Rebalancing threshold must be between 0.0 and 1.0, got {self.rebalancing_threshold}")
        
        # Validate max turnover
        if self.max_turnover <= 0:
            raise ValueError(f"Max turnover must be positive, got {self.max_turnover}")
        
        self.logger.info("Portfolio configuration validation successful")
    
    async def start(self):
        """Start portfolio management."""
        if self.rebalancing_enabled:
            self.rebalancing_task = create_tracked_task(self._rebalancing_loop(), name="auto_tracked_task")
            self.logger.info("Portfolio rebalancing task started")
    
    async def stop(self):
        """Stop portfolio management."""
        if self.rebalancing_task:
            self.rebalancing_task.cancel()
            try:
                await self.rebalancing_task
            except asyncio.CancelledError:
                pass
            self.logger.info("Portfolio rebalancing task stopped")
    
    def update_position(self, symbol: str, current_value_usd: float, current_quantity: float):
        """Update current position data."""
        target_allocation = self.target_allocation.get(symbol, 0.0)
        
        # Calculate total portfolio value for allocation calculation
        total_value = sum(pos.current_value_usd for pos in self.positions.values()) + current_value_usd
        if total_value > 0:
            current_allocation = current_value_usd / total_value
        else:
            current_allocation = 0.0
        
        # Update or create position
        if symbol in self.positions:
            self.positions[symbol].current_value_usd = current_value_usd
            self.positions[symbol].current_quantity = current_quantity
            self.positions[symbol].current_allocation = current_allocation
            self.positions[symbol].last_updated = datetime.now()
        else:
            self.positions[symbol] = PortfolioPosition(
                symbol=symbol,
                current_allocation=current_allocation,
                target_allocation=target_allocation,
                current_value_usd=current_value_usd,
                current_quantity=current_quantity
            )
        
        self.logger.debug(f"Updated position for {symbol}: ${current_value_usd:,.2f} ({current_allocation:.2%})")
    
    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Calculate and return current portfolio metrics."""
        if not self.positions:
            return PortfolioMetrics(
                total_value_usd=0.0, total_pnl_usd=0.0, total_pnl_percent=0.0,
                daily_pnl_usd=0.0, daily_pnl_percent=0.0, max_drawdown=0.0,
                sharpe_ratio=0.0, turnover=0.0
            )
        
        # Calculate basic metrics
        total_value = sum(pos.current_value_usd for pos in self.positions.values())
        
        # Calculate turnover from portfolio history
        turnover = self._calculate_turnover()
        
        # Calculate drawdown and sharpe ratio from history
        max_drawdown = self._calculate_max_drawdown()
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        # Calculate daily PnL (placeholder - would need price history)
        daily_pnl_usd = 0.0
        daily_pnl_percent = 0.0
        
        return PortfolioMetrics(
            total_value_usd=total_value,
            total_pnl_usd=0.0,  # Would need initial investment amount
            total_pnl_percent=0.0,  # Would need initial investment amount
            daily_pnl_usd=daily_pnl_usd,
            daily_pnl_percent=daily_pnl_percent,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            turnover=turnover,
            last_rebalance=self.last_rebalance,
            positions_count=len(self.positions)
        )
    
    def get_rebalancing_recommendations(self) -> List[Dict[str, Any]]:
        """Get rebalancing recommendations for positions that need adjustment."""
        recommendations = []
        total_value = sum(pos.current_value_usd for pos in self.positions.values())
        
        if total_value == 0:
            return recommendations
        
        for symbol, position in self.positions.items():
            # Recalculate current allocation
            position.current_allocation = position.current_value_usd / total_value
            
            if position.needs_rebalancing(self.rebalancing_threshold):
                target_value = position.target_allocation * total_value
                adjustment_usd = target_value - position.current_value_usd
                adjustment_percent = adjustment_usd / total_value
                
                recommendations.append({
                    'symbol': symbol,
                    'current_allocation': position.current_allocation,
                    'target_allocation': position.target_allocation,
                    'allocation_drift': position.allocation_drift,
                    'current_value_usd': position.current_value_usd,
                    'target_value_usd': target_value,
                    'adjustment_usd': adjustment_usd,
                    'adjustment_percent': adjustment_percent,
                    'action': 'BUY' if adjustment_usd > 0 else 'SELL'
                })
        
        # Sort by largest drift first
        recommendations.sort(key=lambda x: abs(x['allocation_drift']), reverse=True)
        return recommendations
    
    def check_rebalancing_needed(self) -> bool:
        """Check if portfolio needs rebalancing based on frequency and drift."""
        # Check frequency
        if self.last_rebalance:
            frequency_map = {
                '1h': timedelta(hours=1),
                '1d': timedelta(days=1),
                '1w': timedelta(weeks=1),
                '1M': timedelta(days=30)
            }
            
            min_interval = frequency_map.get(self.rebalancing_frequency, timedelta(days=1))
            if datetime.now() - self.last_rebalance < min_interval:
                return False
        
        # Check if any position needs rebalancing
        total_value = sum(pos.current_value_usd for pos in self.positions.values())
        if total_value == 0:
            return False
        
        for position in self.positions.values():
            position.current_allocation = position.current_value_usd / total_value
            if position.needs_rebalancing(self.rebalancing_threshold):
                return True
        
        return False
    
    async def execute_rebalancing(self) -> bool:
        """Execute portfolio rebalancing (placeholder for actual trading logic)."""
        recommendations = self.get_rebalancing_recommendations()
        
        if not recommendations:
            self.logger.info("No rebalancing needed")
            return False
        
        # Calculate total turnover for this rebalancing
        total_turnover = sum(abs(rec['adjustment_percent']) for rec in recommendations)
        
        if total_turnover > self.max_turnover:
            self.logger.warning(f"Rebalancing turnover {total_turnover:.2%} exceeds max {self.max_turnover:.2%}")
            return False
        
        self.logger.info(f"Executing rebalancing with {len(recommendations)} adjustments")
        
        # Execute rebalancing (placeholder - would integrate with exchange)
        for rec in recommendations:
            self.logger.info(
                f"{rec['action']} {rec['symbol']}: "
                f"${abs(rec['adjustment_usd']):,.2f} "
                f"({rec['current_allocation']:.2%} → {rec['target_allocation']:.2%})"
            )
        
        # Record rebalancing
        self.last_rebalance = datetime.now()
        self._record_portfolio_snapshot("rebalance")
        
        return True
    
    def _calculate_turnover(self) -> float:
        """Calculate portfolio turnover from history."""
        if len(self.portfolio_history) < 2:
            return 0.0
        
        # Simple turnover calculation (would be more sophisticated in practice)
        return 0.1  # Placeholder
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from portfolio history."""
        if len(self.portfolio_history) < 2:
            return 0.0
        
        # Simple drawdown calculation (would use actual value history)
        return 0.05  # Placeholder
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio from portfolio history."""
        if len(self.portfolio_history) < 10:
            return 0.0
        
        # Simple Sharpe calculation (would use actual returns)
        return 1.2  # Placeholder
    
    def _record_portfolio_snapshot(self, event_type: str = "update"):
        """Record current portfolio state to history."""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'total_value_usd': sum(pos.current_value_usd for pos in self.positions.values()),
            'positions': {
                symbol: {
                    'current_allocation': pos.current_allocation,
                    'target_allocation': pos.target_allocation,
                    'current_value_usd': pos.current_value_usd,
                    'allocation_drift': pos.allocation_drift
                }
                for symbol, pos in self.positions.items()
            }
        }
        
        self.portfolio_history.append(snapshot)
        
        # Keep only last 1000 snapshots
        if len(self.portfolio_history) > 1000:
            self.portfolio_history = self.portfolio_history[-1000:]
    
    async def _rebalancing_loop(self):
        """Background task for automatic rebalancing."""
        while True:
            try:
                if self.check_rebalancing_needed():
                    await self.execute_rebalancing()
                
                # Sleep based on frequency
                frequency_map = {
                    '1h': 3600,
                    '1d': 86400,
                    '1w': 604800,
                    '1M': 2592000
                }
                sleep_seconds = frequency_map.get(self.rebalancing_frequency, 86400)
                await asyncio.sleep(sleep_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in rebalancing loop: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def get_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive portfolio status report."""
        metrics = self.get_portfolio_metrics()
        recommendations = self.get_rebalancing_recommendations()
        
        return {
            'portfolio_summary': {
                'total_value_usd': metrics.total_value_usd,
                'positions_count': len(self.positions),
                'rebalancing_enabled': self.rebalancing_enabled,
                'last_rebalance': self.last_rebalance.isoformat() if self.last_rebalance else None,
                'needs_rebalancing': len(recommendations) > 0
            },
            'current_positions': {
                symbol: {
                    'current_allocation': pos.current_allocation,
                    'target_allocation': pos.target_allocation,
                    'current_value_usd': pos.current_value_usd,
                    'allocation_drift': pos.allocation_drift,
                    'needs_rebalancing': pos.needs_rebalancing(self.rebalancing_threshold)
                }
                for symbol, pos in self.positions.items()
            },
            'performance_metrics': metrics.to_dict(),
            'rebalancing_recommendations': recommendations,
            'configuration': {
                'target_allocation': self.target_allocation,
                'rebalancing_threshold': self.rebalancing_threshold,
                'rebalancing_frequency': self.rebalancing_frequency,
                'max_turnover': self.max_turnover
            }
        }


# Integration functions for existing system
def create_portfolio_manager(config: Dict[str, Any]) -> PortfolioManager:
    """Factory function to create portfolio manager from configuration."""
    return PortfolioManager(config)


async def test_portfolio_manager():
    """Test portfolio manager functionality."""
    # Sample configuration
    config = {
        'portfolio': {
            'target_allocation': {
                'BTC': 0.4,
                'ETH': 0.3,
                'SOL': 0.2,
                'DOGE': 0.1
            },
            'rebalancing': {
                'enabled': True,
                'frequency': '1d',
                'threshold': 0.05
            },
            'performance': {
                'max_turnover': 2.0
            }
        }
    }
    
    # Create portfolio manager
    portfolio = PortfolioManager(config)
    
    # Simulate position updates
    portfolio.update_position('BTC', 45000.0, 1.0)
    portfolio.update_position('ETH', 25000.0, 10.0)
    portfolio.update_position('SOL', 15000.0, 100.0)
    portfolio.update_position('DOGE', 5000.0, 1000.0)
    
    # Get status report
    report = portfolio.get_status_report()
    
    print("Portfolio Status Report:")
    print(f"Total Value: ${report['portfolio_summary']['total_value_usd']:,.2f}")
    print(f"Positions: {report['portfolio_summary']['positions_count']}")
    print(f"Needs Rebalancing: {report['portfolio_summary']['needs_rebalancing']}")
    
    print("\nCurrent Positions:")
    for symbol, pos in report['current_positions'].items():
        print(f"{symbol}: {pos['current_allocation']:.2%} (target: {pos['target_allocation']:.2%}, "
              f"drift: {pos['allocation_drift']:.2%})")
    
    print(f"\nRebalancing Recommendations: {len(report['rebalancing_recommendations'])}")
    for rec in report['rebalancing_recommendations']:
        print(f"{rec['action']} {rec['symbol']}: ${abs(rec['adjustment_usd']):,.2f}")


if __name__ == "__main__":
    asyncio.run(test_portfolio_manager())