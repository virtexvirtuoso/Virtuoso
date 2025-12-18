"""
Comprehensive Validation Tests for Mark Price Divergence Detection System

Tests the complete implementation of Enhancement #2: Mark Price Kline Detection
- src/core/exchanges/bybit.py: fetch_mark_price_kline()
- src/core/risk/execution_quality.py: check_mark_price_divergence(), check_execution_quality()
- src/signal_generation/signal_generator.py: Integration with signal generation

Author: QA Validation Agent
Date: 2025-12-09
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd

# Import the modules under test
from src.core.risk.execution_quality import (
    check_mark_price_divergence,
    check_execution_quality,
    ExecutionQualityCheck
)


class TestExecutionQualityDataclass:
    """Test the ExecutionQualityCheck dataclass structure."""

    def test_dataclass_structure(self):
        """Verify ExecutionQualityCheck has required fields."""
        check = ExecutionQualityCheck(
            is_safe=True,
            divergence_pct=0.25,
            action='NORMAL',
            reason='Test reason',
            mark_price=50000.0,
            last_price=50100.0
        )

        assert check.is_safe is True
        assert check.divergence_pct == 0.25
        assert check.action == 'NORMAL'
        assert check.reason == 'Test reason'
        assert check.mark_price == 50000.0
        assert check.last_price == 50100.0

    def test_optional_fields(self):
        """Verify mark_price and last_price are optional."""
        check = ExecutionQualityCheck(
            is_safe=False,
            divergence_pct=1.5,
            action='REJECT_SIGNAL',
            reason='Critical divergence'
        )

        assert check.mark_price is None
        assert check.last_price is None


class TestDivergenceCalculation:
    """Test the core divergence calculation logic."""

    @pytest.mark.asyncio
    async def test_normal_divergence_0_1_percent(self):
        """Test divergence < 0.5% returns NORMAL action."""
        # Mock exchange with 0.1% divergence
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 50050.0  # 0.1% difference
        })

        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        assert result.action == 'NORMAL'
        assert result.is_safe is True
        assert result.divergence_pct < 0.5
        assert 'Normal market conditions' in result.reason

    @pytest.mark.asyncio
    async def test_normal_divergence_0_4_percent(self):
        """Test divergence just below 0.5% threshold returns NORMAL."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 50240.0  # 0.48% difference
        })

        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        assert result.action == 'NORMAL'
        assert result.is_safe is True
        assert 0.4 < result.divergence_pct < 0.5

    @pytest.mark.asyncio
    async def test_warning_divergence_0_5_percent(self):
        """Test divergence exactly at 0.5% returns WIDEN_STOPS."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 50250.0  # Exactly 0.5% difference
        })

        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        assert result.action == 'WIDEN_STOPS'
        assert result.is_safe is True
        assert 0.49 < result.divergence_pct < 0.51  # Allow floating point tolerance
        assert 'Moderate divergence' in result.reason

    @pytest.mark.asyncio
    async def test_warning_divergence_0_75_percent(self):
        """Test divergence between 0.5-1.0% returns WIDEN_STOPS."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 50375.0  # 0.75% difference
        })

        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        assert result.action == 'WIDEN_STOPS'
        assert result.is_safe is True
        assert 0.5 < result.divergence_pct < 1.0

    @pytest.mark.asyncio
    async def test_critical_divergence_1_0_percent(self):
        """Test divergence exactly at 1.0% returns REJECT_SIGNAL."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 50500.0  # Exactly 1.0% difference
        })

        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        assert result.action == 'REJECT_SIGNAL'
        assert result.is_safe is False
        assert 0.99 < result.divergence_pct < 1.01  # Allow floating point tolerance
        assert 'Critical divergence' in result.reason

    @pytest.mark.asyncio
    async def test_critical_divergence_2_5_percent(self):
        """Test divergence > 1.0% returns REJECT_SIGNAL."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 51250.0  # 2.5% difference
        })

        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        assert result.action == 'REJECT_SIGNAL'
        assert result.is_safe is False
        assert result.divergence_pct > 1.0
        assert 'Critical divergence' in result.reason

    @pytest.mark.asyncio
    async def test_divergence_calculation_accuracy(self):
        """Test divergence calculation formula is correct."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 48000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 50000.0  # 4.17% difference
        })

        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        # Expected: abs((48000 - 50000) / 50000) * 100 = 4.0%
        expected_divergence = abs((48000.0 - 50000.0) / 50000.0) * 100
        assert abs(result.divergence_pct - expected_divergence) < 0.01
        assert result.mark_price == 48000.0
        assert result.last_price == 50000.0


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_no_mark_price_data(self):
        """Test graceful handling when mark price is unavailable."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': None
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 50000.0
        })

        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        assert result.action == 'NORMAL'
        assert result.is_safe is True
        assert result.divergence_pct == 0.0
        assert 'Mark price data unavailable' in result.reason

    @pytest.mark.asyncio
    async def test_no_last_price_data(self):
        """Test graceful handling when last price is unavailable."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': None
        })

        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        assert result.action == 'NORMAL'
        assert result.is_safe is True
        assert result.divergence_pct == 0.0
        assert 'Last price data unavailable' in result.reason
        assert result.mark_price == 50000.0

    @pytest.mark.asyncio
    async def test_identical_prices(self):
        """Test when mark price and last price are identical (0% divergence)."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 50000.0
        })

        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        assert result.action == 'NORMAL'
        assert result.is_safe is True
        assert result.divergence_pct == 0.0

    @pytest.mark.asyncio
    async def test_api_exception_handling(self):
        """Test fail-safe behavior when API call raises exception."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(side_effect=Exception("API Error"))

        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        # Should fail safe - allow trade to proceed
        assert result.action == 'NORMAL'
        assert result.is_safe is True
        assert result.divergence_pct == 0.0
        assert 'Error during check' in result.reason

    @pytest.mark.asyncio
    async def test_negative_price_handling(self):
        """Test handling of negative prices (should still calculate correctly)."""
        # Note: In practice, prices shouldn't be negative, but test robustness
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': -50000.0  # Invalid but tests abs() in formula
        })

        # This should handle the calculation without crashing
        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        # Should calculate divergence as 200%
        assert result.divergence_pct == 200.0
        assert result.action == 'REJECT_SIGNAL'

    @pytest.mark.asyncio
    async def test_zero_last_price(self):
        """Test handling of zero last price (division by zero protection)."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 0.0
        })

        # Should raise ZeroDivisionError, which should be caught
        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        # Should fail safe
        assert result.action == 'NORMAL'
        assert result.is_safe is True
        assert 'Error during check' in result.reason


class TestThresholdBoundaries:
    """Test behavior at exact threshold boundaries."""

    @pytest.mark.asyncio
    async def test_just_below_warning_threshold(self):
        """Test 0.49% divergence (just below 0.5% threshold)."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 50245.0  # 0.49% difference
        })

        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        assert result.action == 'NORMAL'
        assert result.is_safe is True

    @pytest.mark.asyncio
    async def test_just_above_warning_threshold(self):
        """Test 0.51% divergence (just above 0.5% threshold)."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 50255.0  # 0.51% difference
        })

        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        assert result.action == 'WIDEN_STOPS'
        assert result.is_safe is True

    @pytest.mark.asyncio
    async def test_just_below_critical_threshold(self):
        """Test 0.99% divergence (just below 1.0% threshold)."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 50495.0  # 0.99% difference
        })

        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        assert result.action == 'WIDEN_STOPS'
        assert result.is_safe is True

    @pytest.mark.asyncio
    async def test_just_above_critical_threshold(self):
        """Test 1.01% divergence (just above 1.0% threshold)."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 50505.0  # 1.01% difference
        })

        result = await check_mark_price_divergence(exchange, 'BTC/USDT:USDT')

        assert result.action == 'REJECT_SIGNAL'
        assert result.is_safe is False


class TestCustomThresholds:
    """Test custom threshold parameters."""

    @pytest.mark.asyncio
    async def test_custom_warning_threshold(self):
        """Test custom warning threshold (1.0% instead of default 0.5%)."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 50375.0  # 0.75% difference
        })

        # With custom threshold, 0.75% should be NORMAL instead of WIDEN_STOPS
        result = await check_mark_price_divergence(
            exchange,
            'BTC/USDT:USDT',
            threshold_warning=1.0,
            threshold_critical=2.0
        )

        assert result.action == 'NORMAL'
        assert result.is_safe is True

    @pytest.mark.asyncio
    async def test_custom_critical_threshold(self):
        """Test custom critical threshold (2.0% instead of default 1.0%)."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 50750.0  # 1.5% difference
        })

        # With custom threshold, 1.5% should be WIDEN_STOPS instead of REJECT_SIGNAL
        result = await check_mark_price_divergence(
            exchange,
            'BTC/USDT:USDT',
            threshold_warning=1.0,
            threshold_critical=2.0
        )

        assert result.action == 'WIDEN_STOPS'
        assert result.is_safe is True


class TestCheckExecutionQuality:
    """Test the comprehensive execution quality check function."""

    @pytest.mark.asyncio
    async def test_passes_through_to_mark_price_check(self):
        """Verify check_execution_quality delegates to mark price divergence check."""
        exchange = Mock()
        exchange.fetch_mark_price_kline = AsyncMock(return_value={
            'current_mark_price': 50000.0
        })
        exchange.fetch_ticker = AsyncMock(return_value={
            'last': 50100.0  # 0.2% divergence
        })

        result = await check_execution_quality(exchange, 'BTC/USDT:USDT', signal_strength=75.0)

        assert result.action == 'NORMAL'
        assert result.is_safe is True
        assert result.divergence_pct < 0.5


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])
