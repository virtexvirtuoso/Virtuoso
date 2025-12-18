"""
Risk Management Module

Contains risk management components including:
- Kill switches for automatic configuration reversion
- Position sizing calculators
- Risk-adjusted stop loss calculation
- Portfolio risk monitoring
"""

from .kill_switch import OrderflowKillSwitch, get_kill_switch, KillSwitchState

__all__ = [
    'OrderflowKillSwitch',
    'get_kill_switch',
    'KillSwitchState'
]
