"""
Optuna Optimization Module for Virtuoso Trading System

This module provides comprehensive hyperparameter optimization using Optuna,
targeting all 1,247 parameters across the trading system for maximum performance.
"""

from .optuna_engine import VirtuosoOptunaEngine
from .parameter_spaces import ComprehensiveParameterSpaces
from .objectives import OptimizationObjectives

__all__ = [
    'VirtuosoOptunaEngine',
    'ComprehensiveParameterSpaces', 
    'OptimizationObjectives'
]