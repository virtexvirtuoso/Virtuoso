"""
Risk Management System
Implements risk limits, position sizing, stop-loss, and take-profit based on configuration.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
import json


logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OrderType(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class RiskLimits:
    """Risk limits configuration."""
    max_drawdown: float
    max_leverage: float
    max_position_size: float
    max_daily_loss: float = 0.05  # 5% daily loss limit
    max_correlation_exposure: float = 0.3  # Max 30% in correlated assets
    
    def validate(self):
        """Validate risk limits are within acceptable ranges."""
        if not (0.0 <= self.max_drawdown <= 1.0):
            raise ValueError(f"max_drawdown must be between 0.0 and 1.0, got {self.max_drawdown}")
        if self.max_leverage < 1.0:
            raise ValueError(f"max_leverage must be >= 1.0, got {self.max_leverage}")
        if not (0.0 <= self.max_position_size <= 1.0):
            raise ValueError(f"max_position_size must be between 0.0 and 1.0, got {self.max_position_size}")


@dataclass
class StopLossConfig:
    """Stop-loss configuration."""
    activation_percentage: float
    default: float
    trailing: bool
    max_stop_distance: float = 0.10  # Max 10% stop distance
    min_stop_distance: float = 0.01  # Min 1% stop distance


@dataclass
class TakeProfitConfig:
    """Take-profit configuration."""
    activation_percentage: float
    default: float
    trailing: bool
    profit_target_ratio: float = 2.0  # Default 2:1 risk/reward


@dataclass
class PositionRisk:
    """Risk metrics for a single position."""
    symbol: str
    position_size_usd: float
    position_size_percent: float
    leverage: float
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    risk_amount_usd: float
    risk_amount_percent: float
    potential_profit_usd: float
    risk_reward_ratio: float
    correlation_risk: float = 0.0
    volatility_risk: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def risk_level(self) -> RiskLevel:
        """Determine risk level based on position metrics."""
        if self.risk_amount_percent > 0.05:  # > 5%
            return RiskLevel.CRITICAL
        elif self.risk_amount_percent > 0.03:  # > 3%
            return RiskLevel.HIGH
        elif self.risk_amount_percent > 0.015:  # > 1.5%
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW


@dataclass
class PortfolioRisk:
    """Overall portfolio risk metrics."""
    total_risk_usd: float
    total_risk_percent: float
    max_drawdown_current: float
    daily_pnl_percent: float
    leverage_ratio: float
    correlation_exposure: float
    var_95: float = 0.0  # Value at Risk (95% confidence)
    sharpe_ratio: float = 0.0
    risk_adjusted_return: float = 0.0
    position_count: int = 0
    
    @property
    def risk_level(self) -> RiskLevel:
        """Determine overall portfolio risk level."""
        if (self.total_risk_percent > 0.1 or 
            self.max_drawdown_current > 0.15 or 
            self.leverage_ratio > 5.0):
            return RiskLevel.CRITICAL
        elif (self.total_risk_percent > 0.06 or 
              self.max_drawdown_current > 0.1 or 
              self.leverage_ratio > 3.0):
            return RiskLevel.HIGH
        elif (self.total_risk_percent > 0.03 or 
              self.max_drawdown_current > 0.05):
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW


class RiskManager:
    """Comprehensive risk management system."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.risk_config = config.get('risk', {})
        self.logger = logging.getLogger(__name__)
        
        # Risk configuration
        self.default_risk_percentage = self.risk_config.get('default_risk_percentage', 1.0)
        self.max_risk_percentage = self.risk_config.get('max_risk_percentage', 2.0)
        self.min_risk_percentage = self.risk_config.get('min_risk_percentage', 0.5)
        self.risk_free_rate = self.risk_config.get('risk_free_rate', 0.02)
        self.risk_reward_ratio = self.risk_config.get('risk_reward_ratio', 2.0)
        self.long_stop_percentage = self.risk_config.get('long_stop_percentage', 3.5)
        self.short_stop_percentage = self.risk_config.get('short_stop_percentage', 3.5)
        
        # Risk limits
        risk_limits_config = self.risk_config.get('risk_limits', {})
        self.risk_limits = RiskLimits(
            max_drawdown=risk_limits_config.get('max_drawdown', 0.25),
            max_leverage=risk_limits_config.get('max_leverage', 3.0),
            max_position_size=risk_limits_config.get('max_position_size', 0.1)
        )
        
        # Stop-loss configuration
        stop_loss_config = self.risk_config.get('stop_loss', {})
        self.stop_loss = StopLossConfig(
            activation_percentage=stop_loss_config.get('activation_percentage', 0.01),
            default=stop_loss_config.get('default', 0.02),
            trailing=stop_loss_config.get('trailing', True)
        )
        
        # Take-profit configuration
        take_profit_config = self.risk_config.get('take_profit', {})
        self.take_profit = TakeProfitConfig(
            activation_percentage=take_profit_config.get('activation_percentage', 0.02),
            default=take_profit_config.get('default', 0.04),
            trailing=take_profit_config.get('trailing', True)
        )
        
        # Risk state tracking
        self.positions_risk: Dict[str, PositionRisk] = {}
        self.portfolio_value_history: List[Tuple[datetime, float]] = []
        self.risk_alerts: List[Dict[str, Any]] = []
        self.risk_overrides: Dict[str, Any] = {}
        
        # Validate configuration
        self._validate_configuration()
        
        self.logger.info("Risk Manager initialized")
        self.logger.info(f"Default risk: {self.default_risk_percentage}%")
        self.logger.info(f"Max risk: {self.max_risk_percentage}%")
        self.logger.info(f"Risk limits: {self.risk_limits}")
    
    def _validate_configuration(self):
        """Validate risk management configuration."""
        self.risk_limits.validate()
        
        if not (0.0 <= self.default_risk_percentage <= 100.0):
            raise ValueError(f"default_risk_percentage must be between 0.0 and 100.0")
        
        if self.max_risk_percentage < self.min_risk_percentage:
            raise ValueError("max_risk_percentage must be >= min_risk_percentage")
        
        if self.risk_reward_ratio <= 0:
            raise ValueError("risk_reward_ratio must be positive")
        
        self.logger.info("Risk configuration validation successful")
    
    def calculate_position_size(self, 
                              account_balance: float,
                              entry_price: float,
                              stop_loss_price: float,
                              risk_percentage: Optional[float] = None) -> Dict[str, Any]:
        """
        Calculate optimal position size based on risk parameters.
        
        Args:
            account_balance: Total account balance
            entry_price: Entry price for the position
            stop_loss_price: Stop-loss price
            risk_percentage: Risk percentage (defaults to configured value)
            
        Returns:
            Dictionary with position sizing information
        """
        if risk_percentage is None:
            risk_percentage = self.default_risk_percentage
        
        # Clamp risk percentage to limits
        risk_percentage = max(self.min_risk_percentage, 
                            min(risk_percentage, self.max_risk_percentage))
        
        # Calculate risk amount
        risk_amount = account_balance * (risk_percentage / 100.0)
        
        # Calculate price difference for risk calculation
        price_diff = abs(entry_price - stop_loss_price)
        if price_diff == 0:
            return {"error": "Entry price and stop-loss price cannot be the same"}
        
        risk_per_unit = price_diff
        
        # Calculate position size
        position_size_units = risk_amount / risk_per_unit
        position_value = position_size_units * entry_price
        position_size_percent = (position_value / account_balance) * 100
        
        # Check against position size limits
        max_position_value = account_balance * self.risk_limits.max_position_size
        if position_value > max_position_value:
            position_value = max_position_value
            position_size_units = position_value / entry_price
            actual_risk_amount = position_size_units * risk_per_unit
            actual_risk_percentage = (actual_risk_amount / account_balance) * 100
        else:
            actual_risk_amount = risk_amount
            actual_risk_percentage = risk_percentage
        
        return {
            "position_size_units": position_size_units,
            "position_value_usd": position_value,
            "position_size_percent": position_size_percent,
            "risk_amount_usd": actual_risk_amount,
            "risk_percentage": actual_risk_percentage,
            "risk_per_unit": risk_per_unit,
            "entry_price": entry_price,
            "stop_loss_price": stop_loss_price,
            "max_position_size_reached": position_value >= max_position_value
        }
    
    def calculate_stop_loss_take_profit(self,
                                      entry_price: float,
                                      order_type: OrderType,
                                      custom_stop_percentage: Optional[float] = None,
                                      custom_tp_ratio: Optional[float] = None) -> Dict[str, Any]:
        """
        Calculate stop-loss and take-profit levels.
        
        Args:
            entry_price: Entry price
            order_type: Buy or sell order
            custom_stop_percentage: Custom stop-loss percentage
            custom_tp_ratio: Custom take-profit ratio
            
        Returns:
            Dictionary with stop-loss and take-profit information
        """
        # Use custom values or defaults
        stop_percentage = custom_stop_percentage or (
            self.long_stop_percentage if order_type == OrderType.BUY 
            else self.short_stop_percentage
        ) / 100.0
        
        tp_ratio = custom_tp_ratio or self.risk_reward_ratio
        
        if order_type == OrderType.BUY:
            # Long position
            stop_loss_price = entry_price * (1 - stop_percentage)
            risk_per_unit = entry_price - stop_loss_price
            take_profit_price = entry_price + (risk_per_unit * tp_ratio)
        else:
            # Short position
            stop_loss_price = entry_price * (1 + stop_percentage)
            risk_per_unit = stop_loss_price - entry_price
            take_profit_price = entry_price - (risk_per_unit * tp_ratio)
        
        return {
            "entry_price": entry_price,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "stop_loss_percentage": stop_percentage * 100,
            "risk_reward_ratio": tp_ratio,
            "risk_per_unit": risk_per_unit,
            "order_type": order_type.value
        }
    
    def assess_position_risk(self,
                           symbol: str,
                           position_size_usd: float,
                           account_balance: float,
                           entry_price: float,
                           current_price: float,
                           stop_loss_price: Optional[float] = None,
                           take_profit_price: Optional[float] = None) -> PositionRisk:
        """
        Assess risk metrics for a specific position.
        
        Args:
            symbol: Trading symbol
            position_size_usd: Position size in USD
            account_balance: Total account balance
            entry_price: Entry price
            current_price: Current market price
            stop_loss_price: Stop-loss price (if set)
            take_profit_price: Take-profit price (if set)
            
        Returns:
            PositionRisk object with comprehensive risk metrics
        """
        position_size_percent = (position_size_usd / account_balance) * 100
        
        # Calculate current leverage (simplified)
        leverage = position_size_usd / account_balance
        
        # Calculate risk amount
        if stop_loss_price:
            risk_amount_usd = abs(entry_price - stop_loss_price) * (position_size_usd / entry_price)
            risk_amount_percent = (risk_amount_usd / account_balance) * 100
        else:
            # Use default stop-loss percentage for risk calculation
            default_stop = self.long_stop_percentage / 100.0
            risk_amount_usd = position_size_usd * default_stop
            risk_amount_percent = position_size_percent * default_stop
        
        # Calculate potential profit
        if take_profit_price:
            potential_profit_usd = abs(take_profit_price - entry_price) * (position_size_usd / entry_price)
            risk_reward_ratio = potential_profit_usd / risk_amount_usd if risk_amount_usd > 0 else 0
        else:
            potential_profit_usd = risk_amount_usd * self.risk_reward_ratio
            risk_reward_ratio = self.risk_reward_ratio
        
        return PositionRisk(
            symbol=symbol,
            position_size_usd=position_size_usd,
            position_size_percent=position_size_percent,
            leverage=leverage,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            risk_amount_usd=risk_amount_usd,
            risk_amount_percent=risk_amount_percent,
            potential_profit_usd=potential_profit_usd,
            risk_reward_ratio=risk_reward_ratio
        )
    
    def update_position_risk(self, position_risk: PositionRisk):
        """Update position risk tracking."""
        self.positions_risk[position_risk.symbol] = position_risk
        self.logger.debug(f"Updated risk for {position_risk.symbol}: "
                         f"{position_risk.risk_level.value} risk, "
                         f"{position_risk.risk_amount_percent:.2f}% of account")
    
    def get_portfolio_risk(self, account_balance: float) -> PortfolioRisk:
        """Calculate overall portfolio risk metrics."""
        if not self.positions_risk:
            return PortfolioRisk(
                total_risk_usd=0.0,
                total_risk_percent=0.0,
                max_drawdown_current=0.0,
                daily_pnl_percent=0.0,
                leverage_ratio=0.0,
                correlation_exposure=0.0
            )
        
        # Calculate total risk
        total_risk_usd = sum(pos.risk_amount_usd for pos in self.positions_risk.values())
        total_risk_percent = (total_risk_usd / account_balance) * 100
        
        # Calculate leverage ratio
        total_position_value = sum(pos.position_size_usd for pos in self.positions_risk.values())
        leverage_ratio = total_position_value / account_balance if account_balance > 0 else 0
        
        # Calculate drawdown from history
        max_drawdown_current = self._calculate_current_drawdown(account_balance)
        
        # Calculate daily PnL (placeholder - would need price history)
        daily_pnl_percent = 0.0
        
        # Calculate correlation exposure (simplified)
        correlation_exposure = min(1.0, len(self.positions_risk) * 0.1)  # Placeholder
        
        return PortfolioRisk(
            total_risk_usd=total_risk_usd,
            total_risk_percent=total_risk_percent,
            max_drawdown_current=max_drawdown_current,
            daily_pnl_percent=daily_pnl_percent,
            leverage_ratio=leverage_ratio,
            correlation_exposure=correlation_exposure,
            position_count=len(self.positions_risk)
        )
    
    def check_risk_violations(self, account_balance: float) -> List[Dict[str, Any]]:
        """Check for risk limit violations."""
        violations = []
        portfolio_risk = self.get_portfolio_risk(account_balance)
        
        # Check portfolio-level violations
        if portfolio_risk.total_risk_percent > self.max_risk_percentage:
            violations.append({
                "type": "portfolio_risk_exceeded",
                "severity": "high",
                "current": portfolio_risk.total_risk_percent,
                "limit": self.max_risk_percentage,
                "message": f"Portfolio risk {portfolio_risk.total_risk_percent:.2f}% exceeds limit {self.max_risk_percentage}%"
            })
        
        if portfolio_risk.leverage_ratio > self.risk_limits.max_leverage:
            violations.append({
                "type": "leverage_exceeded",
                "severity": "high",
                "current": portfolio_risk.leverage_ratio,
                "limit": self.risk_limits.max_leverage,
                "message": f"Leverage {portfolio_risk.leverage_ratio:.2f}x exceeds limit {self.risk_limits.max_leverage}x"
            })
        
        if portfolio_risk.max_drawdown_current > self.risk_limits.max_drawdown:
            violations.append({
                "type": "drawdown_exceeded",
                "severity": "critical",
                "current": portfolio_risk.max_drawdown_current,
                "limit": self.risk_limits.max_drawdown,
                "message": f"Drawdown {portfolio_risk.max_drawdown_current:.2%} exceeds limit {self.risk_limits.max_drawdown:.2%}"
            })
        
        # Check position-level violations
        for symbol, position in self.positions_risk.items():
            if position.position_size_percent > self.risk_limits.max_position_size * 100:
                violations.append({
                    "type": "position_size_exceeded",
                    "severity": "medium",
                    "symbol": symbol,
                    "current": position.position_size_percent,
                    "limit": self.risk_limits.max_position_size * 100,
                    "message": f"{symbol} position size {position.position_size_percent:.2f}% exceeds limit {self.risk_limits.max_position_size * 100:.2f}%"
                })
        
        return violations
    
    def _calculate_current_drawdown(self, current_balance: float) -> float:
        """Calculate current drawdown from portfolio value history."""
        if len(self.portfolio_value_history) < 2:
            return 0.0
        
        # Find peak value
        peak_value = max(value for _, value in self.portfolio_value_history)
        
        # Calculate drawdown
        if peak_value > 0:
            return (peak_value - current_balance) / peak_value
        return 0.0
    
    def update_portfolio_value(self, current_value: float):
        """Update portfolio value history for drawdown calculation."""
        self.portfolio_value_history.append((datetime.now(), current_value))
        
        # Keep only last 1000 values
        if len(self.portfolio_value_history) > 1000:
            self.portfolio_value_history = self.portfolio_value_history[-1000:]
    
    def get_risk_report(self, account_balance: float) -> Dict[str, Any]:
        """Generate comprehensive risk report."""
        portfolio_risk = self.get_portfolio_risk(account_balance)
        violations = self.check_risk_violations(account_balance)
        
        return {
            "portfolio_risk": {
                "total_risk_usd": portfolio_risk.total_risk_usd,
                "total_risk_percent": portfolio_risk.total_risk_percent,
                "risk_level": portfolio_risk.risk_level.value,
                "leverage_ratio": portfolio_risk.leverage_ratio,
                "max_drawdown_current": portfolio_risk.max_drawdown_current,
                "correlation_exposure": portfolio_risk.correlation_exposure,
                "position_count": portfolio_risk.position_count
            },
            "position_risks": {
                symbol: {
                    "risk_level": pos.risk_level.value,
                    "position_size_percent": pos.position_size_percent,
                    "risk_amount_percent": pos.risk_amount_percent,
                    "risk_reward_ratio": pos.risk_reward_ratio,
                    "leverage": pos.leverage
                }
                for symbol, pos in self.positions_risk.items()
            },
            "risk_limits": {
                "max_drawdown": self.risk_limits.max_drawdown,
                "max_leverage": self.risk_limits.max_leverage,
                "max_position_size": self.risk_limits.max_position_size,
                "max_risk_percentage": self.max_risk_percentage
            },
            "violations": violations,
            "recommendations": self._generate_risk_recommendations(portfolio_risk, violations)
        }
    
    def _generate_risk_recommendations(self, portfolio_risk: PortfolioRisk, violations: List[Dict[str, Any]]) -> List[str]:
        """Generate risk management recommendations."""
        recommendations = []
        
        if violations:
            recommendations.append("Immediate action required: Risk violations detected")
        
        if portfolio_risk.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            recommendations.append("Consider reducing position sizes or implementing hedging strategies")
        
        if portfolio_risk.leverage_ratio > 2.0:
            recommendations.append("High leverage detected - consider reducing exposure")
        
        if len(self.positions_risk) > 10:
            recommendations.append("Large number of positions - consider consolidation")
        
        if not recommendations:
            recommendations.append("Risk profile is within acceptable limits")
        
        return recommendations


# Integration functions
def create_risk_manager(config: Dict[str, Any]) -> RiskManager:
    """Factory function to create risk manager from configuration."""
    return RiskManager(config)


async def test_risk_manager():
    """Test risk manager functionality."""
    config = {
        'risk': {
            'default_risk_percentage': 1.0,
            'max_risk_percentage': 2.0,
            'min_risk_percentage': 0.5,
            'risk_reward_ratio': 2.0,
            'long_stop_percentage': 3.5,
            'short_stop_percentage': 3.5,
            'risk_limits': {
                'max_drawdown': 0.25,
                'max_leverage': 3.0,
                'max_position_size': 0.1
            },
            'stop_loss': {
                'activation_percentage': 0.01,
                'default': 0.02,
                'trailing': True
            },
            'take_profit': {
                'activation_percentage': 0.02,
                'default': 0.04,
                'trailing': True
            }
        }
    }
    
    risk_manager = RiskManager(config)
    
    # Test position sizing
    account_balance = 10000.0
    entry_price = 50000.0
    stop_loss_price = 48500.0
    
    position_size = risk_manager.calculate_position_size(
        account_balance, entry_price, stop_loss_price
    )
    
    print("Position Sizing Test:")
    print(f"Account Balance: ${account_balance:,.2f}")
    print(f"Entry Price: ${entry_price:,.2f}")
    print(f"Stop Loss: ${stop_loss_price:,.2f}")
    print(f"Position Size: {position_size['position_size_units']:.6f} units")
    print(f"Position Value: ${position_size['position_value_usd']:,.2f}")
    print(f"Risk Amount: ${position_size['risk_amount_usd']:,.2f} ({position_size['risk_percentage']:.2f}%)")
    
    # Test stop-loss and take-profit calculation
    sl_tp = risk_manager.calculate_stop_loss_take_profit(entry_price, OrderType.BUY)
    
    print(f"\nStop-Loss/Take-Profit Test:")
    print(f"Entry: ${sl_tp['entry_price']:,.2f}")
    print(f"Stop Loss: ${sl_tp['stop_loss_price']:,.2f} ({sl_tp['stop_loss_percentage']:.2f}%)")
    print(f"Take Profit: ${sl_tp['take_profit_price']:,.2f}")
    print(f"Risk/Reward Ratio: {sl_tp['risk_reward_ratio']:.2f}")
    
    # Test position risk assessment
    position_risk = risk_manager.assess_position_risk(
        "BTCUSDT", position_size['position_value_usd'], account_balance,
        entry_price, 49000.0, stop_loss_price, sl_tp['take_profit_price']
    )
    
    print(f"\nPosition Risk Assessment:")
    print(f"Symbol: {position_risk.symbol}")
    print(f"Risk Level: {position_risk.risk_level.value}")
    print(f"Position Size: {position_risk.position_size_percent:.2f}% of account")
    print(f"Risk Amount: {position_risk.risk_amount_percent:.2f}% of account")
    print(f"Risk/Reward: {position_risk.risk_reward_ratio:.2f}")
    
    # Update risk manager and get portfolio risk
    risk_manager.update_position_risk(position_risk)
    risk_manager.update_portfolio_value(account_balance)
    
    risk_report = risk_manager.get_risk_report(account_balance)
    
    print(f"\nRisk Report:")
    print(f"Portfolio Risk Level: {risk_report['portfolio_risk']['risk_level']}")
    print(f"Total Risk: {risk_report['portfolio_risk']['total_risk_percent']:.2f}%")
    print(f"Leverage: {risk_report['portfolio_risk']['leverage_ratio']:.2f}x")
    print(f"Violations: {len(risk_report['violations'])}")
    print(f"Recommendations: {len(risk_report['recommendations'])}")


if __name__ == "__main__":
    asyncio.run(test_risk_manager())