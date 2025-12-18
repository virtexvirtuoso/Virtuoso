"""
Unit Tests for Orderflow Kill Switch

Tests the kill switch logic for automatic orderflow multiplier reversion.

Run with: pytest tests/risk/test_kill_switch.py -v
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import yaml

from src.core.risk.kill_switch import (
    OrderflowKillSwitch,
    KillSwitchState,
    get_kill_switch
)


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Initialize database schema
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # Create trading_signals table
    cursor.execute('''
        CREATE TABLE trading_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT UNIQUE NOT NULL,
            symbol TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            closed_at TEXT,
            outcome TEXT CHECK (outcome IN ('win', 'loss', 'breakeven')),
            entry_price REAL,
            close_price REAL,
            pnl_percentage REAL
        )
    ''')

    # Create kill_switch_state table
    cursor.execute('''
        CREATE TABLE kill_switch_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            state TEXT NOT NULL,
            activated_at TEXT,
            reason TEXT,
            win_rate REAL,
            closed_count INTEGER,
            updated_at TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

    yield path

    # Cleanup
    os.unlink(path)


@pytest.fixture
def temp_config():
    """Create temporary config file for testing."""
    fd, path = tempfile.mkstemp(suffix='.yaml')
    os.close(fd)

    config = {
        'analysis': {
            'indicators': {
                'orderflow': {
                    'use_symmetric_divergence': True
                }
            }
        }
    }

    with open(path, 'w') as f:
        yaml.dump(config, f)

    yield path

    # Cleanup
    os.unlink(path)


@pytest.fixture
def kill_switch(temp_db, temp_config, monkeypatch):
    """Create kill switch instance with test database."""
    config = {'test': 'config'}

    # Mock config path
    def mock_get_config_path():
        return temp_config

    # Create kill switch with test database
    ks = OrderflowKillSwitch(config, db_path=temp_db)

    # Override config path for testing
    monkeypatch.setattr(
        'src.core.risk.kill_switch.Path',
        lambda x: Path(temp_config).parent if 'config.yaml' in str(x) else Path(x)
    )

    return ks


def create_test_signals(db_path, signal_type='SHORT', num_wins=10, num_losses=5):
    """
    Helper to create test signals in database.

    Args:
        db_path: Path to test database
        signal_type: Signal type (SHORT/LONG)
        num_wins: Number of winning signals to create
        num_losses: Number of losing signals to create

    Returns:
        Total number of signals created
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    now = datetime.now(timezone.utc)

    # Create winning signals
    for i in range(num_wins):
        timestamp = now - timedelta(days=i % 7)
        timestamp_ms = int(timestamp.timestamp() * 1000)
        closed_at = (timestamp + timedelta(hours=1)).isoformat()

        cursor.execute('''
            INSERT INTO trading_signals (
                signal_id, symbol, signal_type, timestamp,
                closed_at, outcome, entry_price, close_price, pnl_percentage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f'test_win_{i}',
            'BTCUSDT',
            signal_type,
            timestamp_ms,
            closed_at,
            'win',
            50000.0,
            51000.0,
            2.0
        ))

    # Create losing signals
    for i in range(num_losses):
        timestamp = now - timedelta(days=i % 7)
        timestamp_ms = int(timestamp.timestamp() * 1000)
        closed_at = (timestamp + timedelta(hours=1)).isoformat()

        cursor.execute('''
            INSERT INTO trading_signals (
                signal_id, symbol, signal_type, timestamp,
                closed_at, outcome, entry_price, close_price, pnl_percentage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f'test_loss_{i}',
            'BTCUSDT',
            signal_type,
            timestamp_ms,
            closed_at,
            'loss',
            50000.0,
            49000.0,
            -2.0
        ))

    conn.commit()
    conn.close()

    return num_wins + num_losses


class TestKillSwitchBasics:
    """Test basic kill switch functionality."""

    def test_initialization(self, kill_switch):
        """Test kill switch initializes correctly."""
        assert kill_switch is not None
        assert kill_switch._state == KillSwitchState.MONITORING

    def test_state_persistence(self, kill_switch):
        """Test state is persisted to database."""
        # Change state
        kill_switch._save_state(
            state=KillSwitchState.ACTIVE,
            reason="Test activation"
        )

        # Create new instance
        new_ks = OrderflowKillSwitch(
            kill_switch.config,
            db_path=kill_switch.db_path
        )

        # State should persist
        assert new_ks._state == KillSwitchState.ACTIVE

    def test_get_status(self, kill_switch):
        """Test status reporting."""
        status = kill_switch.get_status()

        assert 'state' in status
        assert 'is_active' in status
        assert 'performance' in status
        assert 'thresholds' in status
        assert 'multipliers' in status


class TestPerformanceCalculation:
    """Test SHORT signal performance calculation."""

    def test_no_signals(self, kill_switch):
        """Test performance with no signals."""
        win_rate, closed, total = kill_switch.get_short_performance()

        assert win_rate == 0.0
        assert closed == 0
        assert total == 0

    def test_good_performance(self, kill_switch, temp_db):
        """Test with good win rate (above threshold)."""
        # Create 15 wins, 5 losses = 75% win rate
        create_test_signals(temp_db, 'SHORT', num_wins=15, num_losses=5)

        win_rate, closed, total = kill_switch.get_short_performance()

        assert closed == 20
        assert win_rate == 0.75  # 15/20

    def test_poor_performance(self, kill_switch, temp_db):
        """Test with poor win rate (below threshold)."""
        # Create 5 wins, 15 losses = 25% win rate
        create_test_signals(temp_db, 'SHORT', num_wins=5, num_losses=15)

        win_rate, closed, total = kill_switch.get_short_performance()

        assert closed == 20
        assert win_rate == 0.25  # 5/20

    def test_exact_threshold(self, kill_switch, temp_db):
        """Test with win rate at exact threshold."""
        # Create 7 wins, 13 losses = 35% win rate (exact threshold)
        create_test_signals(temp_db, 'SHORT', num_wins=7, num_losses=13)

        win_rate, closed, total = kill_switch.get_short_performance()

        assert closed == 20
        assert win_rate == 0.35

    def test_ignores_open_signals(self, kill_switch, temp_db):
        """Test that open signals are not counted."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Create open signal (no closed_at)
        now = datetime.now(timezone.utc)
        timestamp_ms = int(now.timestamp() * 1000)

        cursor.execute('''
            INSERT INTO trading_signals (
                signal_id, symbol, signal_type, timestamp,
                closed_at, outcome
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', ('test_open', 'BTCUSDT', 'SHORT', timestamp_ms, None, None))

        conn.commit()
        conn.close()

        win_rate, closed, total = kill_switch.get_short_performance()

        # Should not count open signal
        assert closed == 0

    def test_ignores_long_signals(self, kill_switch, temp_db):
        """Test that LONG signals are not counted."""
        # Create LONG signals
        create_test_signals(temp_db, 'LONG', num_wins=10, num_losses=10)

        win_rate, closed, total = kill_switch.get_short_performance()

        # Should not count LONG signals
        assert closed == 0

    def test_seven_day_window(self, kill_switch, temp_db):
        """Test that only signals from last 7 days are counted."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        now = datetime.now(timezone.utc)

        # Create old signal (8 days ago)
        old_timestamp = now - timedelta(days=8)
        old_timestamp_ms = int(old_timestamp.timestamp() * 1000)
        old_closed_at = (old_timestamp + timedelta(hours=1)).isoformat()

        cursor.execute('''
            INSERT INTO trading_signals (
                signal_id, symbol, signal_type, timestamp,
                closed_at, outcome
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', ('test_old', 'BTCUSDT', 'SHORT', old_timestamp_ms, old_closed_at, 'win'))

        # Create recent signal (2 days ago)
        recent_timestamp = now - timedelta(days=2)
        recent_timestamp_ms = int(recent_timestamp.timestamp() * 1000)
        recent_closed_at = (recent_timestamp + timedelta(hours=1)).isoformat()

        cursor.execute('''
            INSERT INTO trading_signals (
                signal_id, symbol, signal_type, timestamp,
                closed_at, outcome
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', ('test_recent', 'BTCUSDT', 'SHORT', recent_timestamp_ms, recent_closed_at, 'win'))

        conn.commit()
        conn.close()

        win_rate, closed, total = kill_switch.get_short_performance()

        # Should only count recent signal
        assert closed == 1


class TestTriggerLogic:
    """Test kill switch trigger logic."""

    def test_insufficient_data(self, kill_switch, temp_db):
        """Test trigger with insufficient signals."""
        # Only 10 signals (need 20)
        create_test_signals(temp_db, 'SHORT', num_wins=3, num_losses=7)

        should_trigger, reason = kill_switch.should_trigger()

        assert not should_trigger
        assert 'Insufficient data' in reason

    def test_good_performance_no_trigger(self, kill_switch, temp_db):
        """Test no trigger with good performance."""
        # 75% win rate (above threshold)
        create_test_signals(temp_db, 'SHORT', num_wins=15, num_losses=5)

        should_trigger, reason = kill_switch.should_trigger()

        assert not should_trigger
        assert 'Performance OK' in reason

    def test_poor_performance_triggers(self, kill_switch, temp_db):
        """Test trigger with poor performance."""
        # 25% win rate (below threshold)
        create_test_signals(temp_db, 'SHORT', num_wins=5, num_losses=15)

        should_trigger, reason = kill_switch.should_trigger()

        assert should_trigger
        assert 'Poor performance' in reason

    def test_already_active_no_trigger(self, kill_switch, temp_db):
        """Test no trigger if already active."""
        # Set state to active
        kill_switch._state = KillSwitchState.ACTIVE

        # Even with poor performance, shouldn't trigger
        create_test_signals(temp_db, 'SHORT', num_wins=5, num_losses=15)

        should_trigger, reason = kill_switch.should_trigger()

        assert not should_trigger
        assert 'already active' in reason

    def test_exact_threshold_no_trigger(self, kill_switch, temp_db):
        """Test no trigger at exact threshold (35%)."""
        # Exactly 35% win rate
        create_test_signals(temp_db, 'SHORT', num_wins=7, num_losses=13)

        should_trigger, reason = kill_switch.should_trigger()

        # Should not trigger (need to be BELOW threshold)
        assert not should_trigger

    def test_just_below_threshold_triggers(self, kill_switch, temp_db):
        """Test trigger just below threshold."""
        # 34.78% win rate (just below 35%)
        create_test_signals(temp_db, 'SHORT', num_wins=8, num_losses=15)

        should_trigger, reason = kill_switch.should_trigger()

        assert should_trigger


class TestActivation:
    """Test kill switch activation."""

    def test_successful_activation(self, kill_switch, temp_db, monkeypatch):
        """Test successful kill switch activation."""
        # Mock alert sending to avoid errors
        def mock_send_alert(*args, **kwargs):
            pass

        monkeypatch.setattr(kill_switch, '_send_alert', mock_send_alert)

        # Create poor performance
        create_test_signals(temp_db, 'SHORT', num_wins=5, num_losses=15)

        # Activate
        success = kill_switch.activate()

        assert success
        assert kill_switch._state == KillSwitchState.ACTIVE

    def test_activation_updates_database(self, kill_switch, temp_db, monkeypatch):
        """Test activation updates database state."""
        # Mock alert sending
        monkeypatch.setattr(kill_switch, '_send_alert', lambda *args, **kwargs: None)

        # Create poor performance
        create_test_signals(temp_db, 'SHORT', num_wins=5, num_losses=15)

        # Activate
        kill_switch.activate()

        # Check database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute('SELECT state, reason, win_rate, closed_count FROM kill_switch_state')
        row = cursor.fetchone()
        conn.close()

        assert row[0] == KillSwitchState.ACTIVE
        assert 'Poor performance' in row[1]
        assert row[2] == 0.25  # 25% win rate
        assert row[3] == 20

    def test_idempotent_activation(self, kill_switch, temp_db, monkeypatch):
        """Test activation is idempotent."""
        # Mock alert sending
        monkeypatch.setattr(kill_switch, '_send_alert', lambda *args, **kwargs: None)

        # Create poor performance
        create_test_signals(temp_db, 'SHORT', num_wins=5, num_losses=15)

        # Activate twice
        kill_switch.activate()
        kill_switch.activate()

        # Should still be in active state
        assert kill_switch._state == KillSwitchState.ACTIVE

    def test_no_activation_with_good_performance(self, kill_switch, temp_db):
        """Test no activation with good performance."""
        # Create good performance
        create_test_signals(temp_db, 'SHORT', num_wins=15, num_losses=5)

        # Try to activate
        success = kill_switch.activate()

        assert not success
        assert kill_switch._state == KillSwitchState.MONITORING


class TestDeactivation:
    """Test kill switch deactivation."""

    def test_deactivation_requires_override(self, kill_switch):
        """Test deactivation requires manual override."""
        # Try to deactivate without override
        success = kill_switch.deactivate(manual_override=False)

        assert not success

    def test_successful_deactivation(self, kill_switch, monkeypatch):
        """Test successful deactivation with override."""
        # Mock alert sending
        monkeypatch.setattr(kill_switch, '_send_alert', lambda *args, **kwargs: None)

        # Set to active first
        kill_switch._state = KillSwitchState.ACTIVE

        # Deactivate with override
        success = kill_switch.deactivate(manual_override=True)

        assert success
        assert kill_switch._state == KillSwitchState.MONITORING


class TestRateLimiting:
    """Test rate limiting of checks."""

    def test_check_throttling(self, kill_switch, temp_db):
        """Test checks are throttled."""
        # Create poor performance
        create_test_signals(temp_db, 'SHORT', num_wins=5, num_losses=15)

        # First check should work
        should_trigger1, reason1 = kill_switch.should_trigger()
        assert should_trigger1

        # Immediate second check should be throttled
        should_trigger2, reason2 = kill_switch.should_trigger()
        assert not should_trigger2
        assert 'throttled' in reason2.lower()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_database_error_handling(self, kill_switch):
        """Test graceful handling of database errors."""
        # Point to non-existent database
        kill_switch.db_path = '/nonexistent/path.db'

        # Should not crash
        win_rate, closed, total = kill_switch.get_short_performance()

        assert win_rate == 0.0
        assert closed == 0
        assert total == 0

    def test_empty_database(self, kill_switch):
        """Test with empty database."""
        win_rate, closed, total = kill_switch.get_short_performance()

        assert win_rate == 0.0
        assert closed == 0

    def test_all_breakeven_signals(self, kill_switch, temp_db):
        """Test with all breakeven signals."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        now = datetime.now(timezone.utc)

        for i in range(20):
            timestamp_ms = int(now.timestamp() * 1000)
            closed_at = (now + timedelta(hours=1)).isoformat()

            cursor.execute('''
                INSERT INTO trading_signals (
                    signal_id, symbol, signal_type, timestamp,
                    closed_at, outcome
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (f'breakeven_{i}', 'BTCUSDT', 'SHORT', timestamp_ms, closed_at, 'breakeven'))

        conn.commit()
        conn.close()

        win_rate, closed, total = kill_switch.get_short_performance()

        assert closed == 20
        assert win_rate == 0.0  # No wins


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self, kill_switch, temp_db, monkeypatch):
        """Test complete activation workflow."""
        # Mock alert and config update
        monkeypatch.setattr(kill_switch, '_send_alert', lambda *args, **kwargs: None)
        monkeypatch.setattr(kill_switch, '_update_config_file', lambda *args: None)

        # 1. Initial state: monitoring
        assert kill_switch._state == KillSwitchState.MONITORING

        # 2. Create poor performance
        create_test_signals(temp_db, 'SHORT', num_wins=5, num_losses=15)

        # 3. Check and activate
        activated = kill_switch.check_and_activate_if_needed()

        assert activated
        assert kill_switch._state == KillSwitchState.ACTIVE

        # 4. Subsequent checks should not re-trigger
        activated_again = kill_switch.check_and_activate_if_needed()

        assert not activated_again

        # 5. Manual deactivation
        deactivated = kill_switch.deactivate(manual_override=True)

        assert deactivated
        assert kill_switch._state == KillSwitchState.MONITORING


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
