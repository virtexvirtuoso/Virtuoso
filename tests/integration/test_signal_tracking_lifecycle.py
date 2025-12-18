"""
Integration Test: Signal Tracking Lifecycle

Tests the complete signal lifecycle from creation to close, including:
1. Signal creation → tracker.open_signal()
2. Price monitoring → tracker.update_excursion()
3. Signal close → tracker.close_signal()

This validates that all integration points work together correctly.
"""

import pytest
import os
import sqlite3
import asyncio
from datetime import datetime
from pathlib import Path

from src.database.signal_performance import SignalPerformanceTracker
from src.database.signal_tracking_helpers import (
    determine_signal_pattern,
    extract_orderflow_tags,
    get_divergence_type
)
from src.database.signal_storage import store_trading_signal


@pytest.fixture
def test_db_path(tmp_path):
    """Create a temporary test database."""
    db_path = str(tmp_path / "test_virtuoso.db")

    # Create trading_signals table
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trading_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT UNIQUE NOT NULL,
            symbol TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            confluence_score REAL,
            reliability REAL,
            entry_price REAL,
            stop_loss REAL,
            current_price REAL,
            timestamp INTEGER,
            created_at TEXT DEFAULT (datetime('now')),

            -- Performance tracking columns
            status TEXT DEFAULT 'pending',
            opened_at TEXT,
            closed_at TEXT,
            confirmed_price REAL,
            exit_price REAL,
            exit_reason TEXT,
            outcome TEXT,
            pnl_pct REAL,
            r_multiple REAL,
            duration_hours REAL,
            mfe_pct REAL,
            mae_pct REAL,
            mfe_price REAL,
            mae_price REAL,
            mfe_at TEXT,
            mae_at TEXT,

            -- Pattern classification
            signal_pattern TEXT,
            divergence_type TEXT,
            orderflow_tags TEXT,
            trigger_component TEXT,

            -- Validation metadata
            is_validation_cohort INTEGER DEFAULT 0,
            orderflow_config TEXT,
            performance_notes TEXT,

            -- Additional data
            targets TEXT,
            components TEXT,
            interpretations TEXT,
            insights TEXT,
            influential_components TEXT,
            sent_to_discord INTEGER DEFAULT 0,
            json_path TEXT,
            pdf_path TEXT,
            trade_params TEXT
        )
    ''')

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def tracker(test_db_path):
    """Create a tracker instance with test database."""
    return SignalPerformanceTracker(test_db_path)


@pytest.fixture
def sample_signal_data():
    """Sample signal data for testing."""
    return {
        'symbol': 'BTCUSDT',
        'signal_type': 'LONG',
        'score': 75.0,
        'price': 50000.0,
        'reliability': 0.8,
        'components': {
            'technical': {'score': 70},
            'orderflow': {'score': 80, 'buyer_aggression': 0.75},
            'volume': {'score': 72}
        },
        'trade_params': {
            'entry_price': 50000.0,
            'stop_loss': 49000.0,
            'targets': [
                {'name': 'Target 1', 'price': 51500, 'size': 50},
                {'name': 'Target 2', 'price': 52500, 'size': 30},
                {'name': 'Target 3', 'price': 54000, 'size': 20}
            ]
        }
    }


class TestSignalLifecycle:
    """Test complete signal lifecycle."""

    def test_pattern_classification(self, sample_signal_data):
        """Test that pattern classification works correctly."""
        components = sample_signal_data['components']
        signal_type = sample_signal_data['signal_type']

        # Test confirmation pattern (all aligned)
        pattern = determine_signal_pattern(components, signal_type)
        assert pattern in ['confirmation', 'other', 'momentum']

        # Test divergence pattern
        divergence_components = {
            'technical': {'score': 30},
            'orderflow': {'score': 75},
            'volume': {'score': 45}
        }
        pattern = determine_signal_pattern(divergence_components, 'LONG')
        assert pattern == 'divergence'

    def test_orderflow_tag_extraction(self, sample_signal_data):
        """Test orderflow tag extraction."""
        components = sample_signal_data['components']
        tags = extract_orderflow_tags(components)

        assert isinstance(tags, list)
        assert 'high_buyer_aggression' in tags

    def test_signal_creation_and_tracking(self, test_db_path, tracker, sample_signal_data):
        """
        Test 1: Signal Creation → tracker.open_signal()

        Simulates the PDF generator flow where signals are created and tracking is initialized.
        """
        # Step 1: Store signal in database (simulates store_trading_signal)
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()

        signal_id = 'btcusdt_long_75p0_20251211_120000'
        cursor.execute('''
            INSERT INTO trading_signals (
                signal_id, symbol, signal_type, confluence_score, reliability,
                entry_price, stop_loss, current_price, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal_id,
            sample_signal_data['symbol'],
            sample_signal_data['signal_type'],
            sample_signal_data['score'],
            sample_signal_data['reliability'],
            sample_signal_data['price'],
            sample_signal_data['trade_params']['stop_loss'],
            sample_signal_data['price'],
            int(datetime.now().timestamp() * 1000)
        ))

        conn.commit()
        conn.close()

        # Step 2: Initialize tracking (simulates PDF generator integration)
        components = sample_signal_data['components']
        signal_type = sample_signal_data['signal_type']

        pattern = determine_signal_pattern(components, signal_type)
        divergence_type = get_divergence_type(components, signal_type, pattern)
        orderflow_tags = extract_orderflow_tags(components)

        success = tracker.open_signal(
            signal_id=signal_id,
            confirmed_price=sample_signal_data['price'],
            signal_pattern=pattern,
            divergence_type=divergence_type,
            orderflow_tags=orderflow_tags,
            is_validation_cohort=True,
            orderflow_config='50_45',
            trigger_component='orderflow'
        )

        assert success is True

        # Verify tracking was initialized
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trading_signals WHERE signal_id = ?", (signal_id,))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row['status'] == 'active'
        assert row['opened_at'] is not None
        assert row['signal_pattern'] == pattern
        assert row['confirmed_price'] == sample_signal_data['price']

    def test_excursion_tracking(self, test_db_path, tracker):
        """
        Test 2: Position Monitoring → tracker.update_excursion()

        Simulates the position monitor updating MFE/MAE as price moves.
        """
        # Setup: Create an active signal
        signal_id = 'btcusdt_long_75p0_test'
        entry_price = 50000.0

        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trading_signals (
                signal_id, symbol, signal_type, entry_price, status
            ) VALUES (?, ?, ?, ?, ?)
        ''', (signal_id, 'BTCUSDT', 'LONG', entry_price, 'active'))
        conn.commit()
        conn.close()

        # Test 1: Price moves up (favorable)
        tracker.update_excursion(signal_id, 51000.0)

        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT mfe_pct, mfe_price FROM trading_signals WHERE signal_id = ?", (signal_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['mfe_pct'] == pytest.approx(2.0, abs=0.1)  # 2% favorable
        assert row['mfe_price'] == 51000.0

        # Test 2: Price moves down (adverse)
        tracker.update_excursion(signal_id, 49500.0)

        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT mae_pct, mae_price FROM trading_signals WHERE signal_id = ?", (signal_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['mae_pct'] == pytest.approx(-1.0, abs=0.1)  # -1% adverse
        assert row['mae_price'] == 49500.0

        # Test 3: New favorable extreme
        tracker.update_excursion(signal_id, 52000.0)

        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT mfe_pct FROM trading_signals WHERE signal_id = ?", (signal_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['mfe_pct'] == pytest.approx(4.0, abs=0.1)  # New MFE at 4%

    def test_signal_close_win(self, test_db_path, tracker):
        """
        Test 3a: Position Close → tracker.close_signal() (Win)

        Simulates closing a winning signal.
        """
        signal_id = 'btcusdt_long_win_test'
        entry_price = 50000.0
        exit_price = 51500.0

        # Setup
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trading_signals (
                signal_id, symbol, signal_type, entry_price, stop_loss, status, opened_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (signal_id, 'BTCUSDT', 'LONG', entry_price, 49000.0, 'active', datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

        # Close the signal
        success = tracker.close_signal(
            signal_id=signal_id,
            exit_price=exit_price,
            exit_reason='target_hit',
            performance_notes='Hit Target 1'
        )

        assert success is True

        # Verify outcomes
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trading_signals WHERE signal_id = ?", (signal_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['status'] == 'closed'
        assert row['outcome'] == 'win'
        assert row['exit_price'] == exit_price
        assert row['pnl_pct'] == pytest.approx(3.0, abs=0.1)  # 3% gain
        assert row['r_multiple'] is not None
        assert row['duration_hours'] is not None

    def test_signal_close_loss(self, test_db_path, tracker):
        """
        Test 3b: Position Close → tracker.close_signal() (Loss)

        Simulates closing a losing signal (stop loss).
        """
        signal_id = 'btcusdt_long_loss_test'
        entry_price = 50000.0
        stop_loss = 49000.0

        # Setup
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trading_signals (
                signal_id, symbol, signal_type, entry_price, stop_loss, status, opened_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (signal_id, 'BTCUSDT', 'LONG', entry_price, stop_loss, 'active', datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

        # Close at stop loss
        success = tracker.close_signal(
            signal_id=signal_id,
            exit_price=stop_loss,
            exit_reason='stop_loss',
            performance_notes='Stopped out'
        )

        assert success is True

        # Verify outcomes
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trading_signals WHERE signal_id = ?", (signal_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['status'] == 'closed'
        assert row['outcome'] == 'stopped_out'
        assert row['exit_price'] == stop_loss
        assert row['pnl_pct'] == pytest.approx(-2.0, abs=0.1)  # -2% loss
        assert row['r_multiple'] == pytest.approx(-1.0, abs=0.1)  # -1R

    def test_complete_lifecycle(self, test_db_path, tracker, sample_signal_data):
        """
        Test 4: Complete Lifecycle Integration

        Tests the full flow: create → monitor → close
        """
        signal_id = 'btcusdt_long_complete_test'
        entry_price = 50000.0

        # STEP 1: Create and open signal
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trading_signals (
                signal_id, symbol, signal_type, entry_price, stop_loss, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (signal_id, 'BTCUSDT', 'LONG', entry_price, 49000.0, 'pending'))
        conn.commit()
        conn.close()

        # Initialize tracking
        pattern = determine_signal_pattern(sample_signal_data['components'], 'LONG')
        tracker.open_signal(
            signal_id=signal_id,
            confirmed_price=entry_price,
            signal_pattern=pattern,
            orderflow_config='50_45'
        )

        # Verify opened
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM trading_signals WHERE signal_id = ?", (signal_id,))
        row = cursor.fetchone()
        conn.close()
        assert row['status'] == 'active'

        # STEP 2: Monitor price movements
        price_movements = [50500, 51000, 50800, 49800, 50200, 51500]

        for price in price_movements:
            tracker.update_excursion(signal_id, price)

        # Verify excursions tracked
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT mfe_pct, mae_pct FROM trading_signals WHERE signal_id = ?", (signal_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['mfe_pct'] > 0  # Should have positive MFE
        assert row['mae_pct'] < 0  # Should have negative MAE

        # STEP 3: Close signal
        tracker.close_signal(
            signal_id=signal_id,
            exit_price=51500.0,
            exit_reason='target_hit'
        )

        # Verify final state
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trading_signals WHERE signal_id = ?", (signal_id,))
        row = cursor.fetchone()
        conn.close()

        assert row['status'] == 'closed'
        assert row['outcome'] == 'win'
        assert row['pnl_pct'] == pytest.approx(3.0, abs=0.1)
        assert row['closed_at'] is not None
        assert row['duration_hours'] is not None


@pytest.mark.asyncio
async def test_position_monitor_integration(test_db_path):
    """
    Test 5: Position Monitor Service

    Tests the SignalPositionMonitor that continuously tracks excursions.
    """
    from src.monitoring.signal_position_monitor import SignalPositionMonitor

    # Create a mock market data manager
    class MockMarketDataManager:
        async def get_market_data(self, symbol):
            return {
                'ticker': {
                    'last': 51000.0,
                    'close': 51000.0
                }
            }

    # Setup active signal
    signal_id = 'btcusdt_monitor_test'
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO trading_signals (
            signal_id, symbol, signal_type, entry_price, status
        ) VALUES (?, ?, ?, ?, ?)
    ''', (signal_id, 'BTCUSDT', 'LONG', 50000.0, 'active'))
    conn.commit()
    conn.close()

    # Create monitor
    monitor = SignalPositionMonitor(
        db_path=test_db_path,
        market_data_manager=MockMarketDataManager(),
        auto_close_enabled=False,
        update_interval=1
    )

    # Run one update cycle
    await monitor.update_all_positions()

    # Verify excursion was updated
    conn = sqlite3.connect(test_db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT mfe_pct FROM trading_signals WHERE signal_id = ?", (signal_id,))
    row = cursor.fetchone()
    conn.close()

    assert row['mfe_pct'] == pytest.approx(2.0, abs=0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
