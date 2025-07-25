"""
Core scoring framework for indicator transformations.

This module provides the UnifiedScoringFramework that enables elegant integration
of linear and non-linear scoring methods across all indicators.
"""

from .unified_scoring_framework import (
    ScoringMode,
    ScoringConfig,
    UnifiedScoringFramework
)

__all__ = [
    'ScoringMode',
    'ScoringConfig', 
    'UnifiedScoringFramework'
] 