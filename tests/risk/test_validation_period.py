"""
Test validation period position sizing for SHORT signals.

Validates that:
1. SHORT signals get 50% position size during validation period
2. LONG signals are unaffected during validation period
3. SHORT stop loss tightens to 1.5% during validation period
4. Validation period auto-disables after end_date
5. Manual override works (set active=false)
"""

import pytest
from datetime import datetime, timedelta
from src.risk.risk_manager import RiskManager, OrderType


@pytest.fixture
def base_config():
    """Base configuration without validation period."""
    return {
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
        },
        'risk_management': {
            'default_stop_loss': 0.04,
            'confidence_scaling': True
        }
    }


@pytest.fixture
def config_with_validation_active(base_config):
    """Configuration with active validation period."""
    # Set end date 30 days in the future
    future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    base_config['risk_management']['validation_period'] = {
        'active': True,
        'end_date': future_date,
        'short_position_multiplier': 0.5,
        'short_stop_loss_pct': 1.5
    }
    return base_config


@pytest.fixture
def config_with_validation_expired(base_config):
    """Configuration with expired validation period."""
    # Set end date 30 days in the past
    past_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    base_config['risk_management']['validation_period'] = {
        'active': True,
        'end_date': past_date,
        'short_position_multiplier': 0.5,
        'short_stop_loss_pct': 1.5
    }
    return base_config


@pytest.fixture
def config_with_validation_disabled(base_config):
    """Configuration with manually disabled validation period."""
    future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    base_config['risk_management']['validation_period'] = {
        'active': False,  # Manually disabled
        'end_date': future_date,
        'short_position_multiplier': 0.5,
        'short_stop_loss_pct': 1.5
    }
    return base_config


class TestValidationPeriodPositionSizing:
    """Test position sizing behavior during validation period."""

    def test_short_position_reduced_during_validation(self, config_with_validation_active):
        """SHORT positions should be reduced to 50% during active validation period."""
        risk_manager = RiskManager(config_with_validation_active)

        account_balance = 10000.0
        entry_price = 50000.0
        stop_loss_price = 51000.0  # SHORT: stop above entry

        # Calculate position for SHORT
        position = risk_manager.calculate_position_size(
            account_balance=account_balance,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            order_type=OrderType.SELL
        )

        # Verify validation period was applied
        assert position['validation_period_applied'] is True

        # Calculate what the position would be without validation
        position_no_validation = risk_manager.calculate_position_size(
            account_balance=account_balance,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            order_type=OrderType.BUY  # Use BUY to avoid validation logic
        )

        # Verify SHORT position is ~50% of normal
        assert abs(position['position_value_usd'] - position_no_validation['position_value_usd'] * 0.5) < 1.0
        assert abs(position['position_size_units'] - position_no_validation['position_size_units'] * 0.5) < 0.001

    def test_long_position_unaffected_during_validation(self, config_with_validation_active):
        """LONG positions should be unaffected during validation period."""
        risk_manager = RiskManager(config_with_validation_active)

        account_balance = 10000.0
        entry_price = 50000.0
        stop_loss_price = 48500.0  # LONG: stop below entry

        # Calculate position for LONG
        position = risk_manager.calculate_position_size(
            account_balance=account_balance,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            order_type=OrderType.BUY
        )

        # Verify validation period was NOT applied to LONG
        assert position['validation_period_applied'] is False

    def test_short_stop_loss_tightened_during_validation(self, config_with_validation_active):
        """SHORT stop loss should tighten to 1.5% during validation period."""
        risk_manager = RiskManager(config_with_validation_active)

        entry_price = 50000.0

        # Calculate stop loss for SHORT
        sl_tp = risk_manager.calculate_stop_loss_take_profit(
            entry_price=entry_price,
            order_type=OrderType.SELL
        )

        # Verify validation period was applied
        assert sl_tp['validation_period_applied'] is True

        # Verify stop loss is 1.5% (not 3.5%)
        assert abs(sl_tp['stop_loss_percentage'] - 1.5) < 0.01

        # Verify actual stop loss price
        expected_stop = entry_price * 1.015  # 1.5% above entry for SHORT
        assert abs(sl_tp['stop_loss_price'] - expected_stop) < 10.0

    def test_long_stop_loss_unaffected_during_validation(self, config_with_validation_active):
        """LONG stop loss should be unaffected during validation period."""
        risk_manager = RiskManager(config_with_validation_active)

        entry_price = 50000.0

        # Calculate stop loss for LONG
        sl_tp = risk_manager.calculate_stop_loss_take_profit(
            entry_price=entry_price,
            order_type=OrderType.BUY
        )

        # Verify validation period was NOT applied
        assert sl_tp['validation_period_applied'] is False

        # Verify stop loss is normal 3.5%
        assert abs(sl_tp['stop_loss_percentage'] - 3.5) < 0.01

    def test_validation_period_auto_disables_after_end_date(self, config_with_validation_expired):
        """Validation period should auto-disable after end_date."""
        risk_manager = RiskManager(config_with_validation_expired)

        # Validation period should be inactive (expired)
        assert risk_manager._is_validation_period_active() is False

        # SHORT position should NOT be reduced
        position = risk_manager.calculate_position_size(
            account_balance=10000.0,
            entry_price=50000.0,
            stop_loss_price=51000.0,
            order_type=OrderType.SELL
        )

        assert position['validation_period_applied'] is False

    def test_validation_period_manual_override(self, config_with_validation_disabled):
        """Manual override (active=false) should disable validation period."""
        risk_manager = RiskManager(config_with_validation_disabled)

        # Validation period should be inactive (manually disabled)
        assert risk_manager._is_validation_period_active() is False

        # SHORT position should NOT be reduced
        position = risk_manager.calculate_position_size(
            account_balance=10000.0,
            entry_price=50000.0,
            stop_loss_price=51000.0,
            order_type=OrderType.SELL
        )

        assert position['validation_period_applied'] is False

    def test_validation_period_risk_calculation(self, config_with_validation_active):
        """Risk amount should be reduced proportionally during validation period."""
        risk_manager = RiskManager(config_with_validation_active)

        account_balance = 10000.0
        entry_price = 50000.0

        # Calculate stop loss for SHORT (will use 1.5% during validation)
        sl_tp = risk_manager.calculate_stop_loss_take_profit(
            entry_price=entry_price,
            order_type=OrderType.SELL
        )

        # Verify tighter stop loss
        assert sl_tp['validation_period_applied'] is True
        assert abs(sl_tp['stop_loss_percentage'] - 1.5) < 0.01

        # Calculate position size for SHORT
        position = risk_manager.calculate_position_size(
            account_balance=account_balance,
            entry_price=entry_price,
            stop_loss_price=sl_tp['stop_loss_price'],
            order_type=OrderType.SELL
        )

        # Verify validation period was applied
        assert position['validation_period_applied'] is True

        # With 1.5% stop loss during validation:
        # - Risk per unit = entry * 0.015 = 50000 * 0.015 = 750
        # - Risk amount (1% of account) = 100
        # - Position size = 100 / 750 = 0.1333 units
        # - Position value = 0.1333 * 50000 = 6,666.67
        # - After 50% reduction = 3,333.33 (position) and 50.0 (risk)
        # But this is capped at max_position_size (10% = $1,000)
        # So actual position = $1,000, then reduced to $500
        # Actual risk = position_size * risk_per_unit = (500 / 50000) * 750 = 7.5

        # The actual risk depends on the tighter stop loss and position reduction
        # Expected: position capped at $1000, then reduced to $500
        # Risk = $500 / $50,000 * $750 = $7.50
        expected_risk = 7.5

        # Allow some tolerance for floating point arithmetic
        assert abs(position['risk_amount_usd'] - expected_risk) < 0.1

    def test_position_sizing_without_order_type(self, config_with_validation_active):
        """Position sizing should work without order_type (backward compatibility)."""
        risk_manager = RiskManager(config_with_validation_active)

        # Call without order_type (should not raise error)
        position = risk_manager.calculate_position_size(
            account_balance=10000.0,
            entry_price=50000.0,
            stop_loss_price=48500.0
            # No order_type provided
        )

        # Should not apply validation period (no order_type)
        assert 'validation_period_applied' in position
        assert position['validation_period_applied'] is False

    def test_validation_period_logging(self, config_with_validation_active, caplog):
        """Validation period should log when applied."""
        import logging
        caplog.set_level(logging.INFO)

        risk_manager = RiskManager(config_with_validation_active)

        # Calculate SHORT position
        risk_manager.calculate_position_size(
            account_balance=10000.0,
            entry_price=50000.0,
            stop_loss_price=51000.0,
            order_type=OrderType.SELL
        )

        # Verify logging occurred
        assert any("VALIDATION PERIOD" in record.message for record in caplog.records)
        assert any("SHORT position reduced" in record.message for record in caplog.records)


class TestValidationPeriodIntegration:
    """Integration tests for validation period."""

    def test_full_signal_flow_short_validation(self, config_with_validation_active):
        """Test full flow: stop loss calculation → position sizing for SHORT."""
        risk_manager = RiskManager(config_with_validation_active)

        account_balance = 10000.0
        entry_price = 50000.0

        # Step 1: Calculate stop loss and take profit
        sl_tp = risk_manager.calculate_stop_loss_take_profit(
            entry_price=entry_price,
            order_type=OrderType.SELL
        )

        # Verify tight stop loss
        assert sl_tp['validation_period_applied'] is True
        assert abs(sl_tp['stop_loss_percentage'] - 1.5) < 0.01

        # Step 2: Calculate position size using the stop loss
        position = risk_manager.calculate_position_size(
            account_balance=account_balance,
            entry_price=entry_price,
            stop_loss_price=sl_tp['stop_loss_price'],
            order_type=OrderType.SELL
        )

        # Verify reduced position size
        assert position['validation_period_applied'] is True

        # Verify risk is reasonable (tighter stop + smaller size)
        assert position['risk_percentage'] <= 1.0  # Should not exceed default 1%

    def test_full_signal_flow_long_normal(self, config_with_validation_active):
        """Test full flow: stop loss calculation → position sizing for LONG."""
        risk_manager = RiskManager(config_with_validation_active)

        account_balance = 10000.0
        entry_price = 50000.0

        # Step 1: Calculate stop loss and take profit
        sl_tp = risk_manager.calculate_stop_loss_take_profit(
            entry_price=entry_price,
            order_type=OrderType.BUY
        )

        # Verify normal stop loss
        assert sl_tp['validation_period_applied'] is False
        assert abs(sl_tp['stop_loss_percentage'] - 3.5) < 0.01

        # Step 2: Calculate position size using the stop loss
        position = risk_manager.calculate_position_size(
            account_balance=account_balance,
            entry_price=entry_price,
            stop_loss_price=sl_tp['stop_loss_price'],
            order_type=OrderType.BUY
        )

        # Verify normal position size
        assert position['validation_period_applied'] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
