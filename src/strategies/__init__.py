"""
Trading Strategies Module

This module contains various trading strategies for the Virtuoso trading system.
Each strategy implements a consistent interface and integrates with the existing
signal generation and risk management frameworks.
"""

from .momentum_strategy import MomentumStrategy

__all__ = ['MomentumStrategy']