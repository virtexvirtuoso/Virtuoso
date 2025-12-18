"""
Tests for Signal Performance Tracking

Validates the schema migration and performance tracking functionality.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import json

# Import the tracker
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.database.signal_performance import SignalPerformanceTracker


@pytest.fixture
def test_db():
    """Create a temporary test database with schema."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
        db_path = f.name

    # Create basic schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE trading_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT UNIQUE NOT NULL,
            symbol TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            confluence_score REAL NOT NULL,
            reliability REAL,
            entry_price REAL,
            stop_loss REAL,
            current_price REAL,
            timestamp INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            targets TEXT,
            components TEXT,
            interpretations TEXT,
            insights TEXT,
            influential_components TEXT,
            trade_params TEXT,
            sent_to_discord BOOLEAN DEFAULT 0,
            json_path TEXT,
            pdf_path TEXT
        )
    """)

    # Apply migration - read from file
    migration_file = Path(__file__).parent.parent.parent / "migrations" / "add_performance_tracking.sql"
    if migration_file.exists():
        with open(migration_file, "r") as f:
            migration_sql = f.read()
            # Execute statements one by one
            for statement in migration_sql.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    try:
                        cursor.execute(statement)
                    except Exception as e:
                        if "duplicate column" not in str(e).lower():
                            print(f"Migration statement error: {e}")

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink()


@pytest.fixture
def tracker(test_db):
    """Get tracker instance."""
    return SignalPerformanceTracker(test_db)


@pytest.fixture
def sample_signal(test_db):
    """Insert a sample signal."""
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    signal_data = {
        "signal_id": "BTCUSDT_SHORT_75_20251211_120000",
        "symbol": "BTCUSDT",
        "signal_type": "SHORT",
        "confluence_score": 75.5,
        "reliability": 0.8,
        "entry_price": 50000.0,
        "stop_loss": 51000.0,
        "current_price": 50000.0,
        "timestamp": int(datetime.now().timestamp() * 1000),
        "components": json.dumps({
            "orderflow": {"score": 80, "buyer_aggression": 0.3, "seller_aggression": 0.8},
            "technical": {"score": 70},
            "volume": {"score": 75},
        }),
    }

    cursor.execute(
        """
        INSERT INTO trading_signals
        (signal_id, symbol, signal_type, confluence_score, reliability,
         entry_price, stop_loss, current_price, timestamp, components)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            signal_data["signal_id"],
            signal_data["symbol"],
            signal_data["signal_type"],
            signal_data["confluence_score"],
            signal_data["reliability"],
            signal_data["entry_price"],
            signal_data["stop_loss"],
            signal_data["current_price"],
            signal_data["timestamp"],
            signal_data["components"],
        ),
    )

    conn.commit()
    conn.close()

    return signal_data


class TestSchemaMigration:
    """Test schema migration."""

    def test_columns_added(self, test_db):
        """Verify all performance tracking columns exist."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(trading_signals)")
        columns = {row[1] for row in cursor.fetchall()}

        required_columns = {
            "outcome",
            "status",
            "pnl_pct",
            "pnl_absolute",
            "r_multiple",
            "exit_price",
            "confirmed_price",
            "opened_at",
            "closed_at",
            "duration_hours",
            "signal_pattern",
            "divergence_type",
            "orderflow_tags",
            "mfe_pct",
            "mae_pct",
            "mfe_price",
            "mae_price",
            "mfe_at",
            "mae_at",
            "is_validation_cohort",
            "orderflow_config",
            "trigger_component",
            "exit_reason",
            "performance_notes",
        }

        missing = required_columns - columns
        assert len(missing) == 0, f"Missing columns: {missing}"

        conn.close()

    def test_indexes_created(self, test_db):
        """Verify performance indexes exist."""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'index'
            AND tbl_name = 'trading_signals'
            AND name LIKE 'idx_signals_%'
            """
        )
        indexes = {row[0] for row in cursor.fetchall()}

        expected_indexes = {
            "idx_signals_outcome",
            "idx_signals_type_outcome",
            "idx_signals_pattern",
            "idx_signals_closed_at",
            "idx_signals_validation",
            "idx_signals_daily_performance",
            "idx_signals_divergence",
            "idx_signals_pnl",
        }

        missing = expected_indexes - indexes
        assert len(missing) == 0, f"Missing indexes: {missing}"

        conn.close()


class TestSignalPerformanceTracker:
    """Test performance tracking functionality."""

    def test_open_signal(self, tracker, sample_signal):
        """Test opening a signal."""
        result = tracker.open_signal(
            signal_id=sample_signal["signal_id"],
            confirmed_price=49900.0,
            signal_pattern="divergence",
            divergence_type="bearish_divergence",
            orderflow_tags=["high_seller_aggression"],
            is_validation_cohort=True,
            orderflow_config="50_45",
            trigger_component="orderflow_divergence",
        )

        assert result is True

        # Verify data
        conn = tracker._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM trading_signals WHERE signal_id = ?",
            (sample_signal["signal_id"],),
        )
        row = cursor.fetchone()

        assert row["status"] == "active"
        assert row["confirmed_price"] == 49900.0
        assert row["signal_pattern"] == "divergence"
        assert row["divergence_type"] == "bearish_divergence"
        assert row["is_validation_cohort"] == 1
        assert row["orderflow_config"] == "50_45"
        assert row["opened_at"] is not None

        conn.close()

    def test_close_signal_winning(self, tracker, sample_signal):
        """Test closing a winning SHORT signal."""
        # Open first
        tracker.open_signal(
            signal_id=sample_signal["signal_id"],
            signal_pattern="divergence",
        )

        # Close with profit (SHORT: entry 50000, exit 49000 = +2% profit)
        result = tracker.close_signal(
            signal_id=sample_signal["signal_id"],
            exit_price=49000.0,
            exit_reason="target_hit",
            performance_notes="Hit first target",
        )

        assert result is True

        # Verify metrics
        conn = tracker._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM trading_signals WHERE signal_id = ?",
            (sample_signal["signal_id"],),
        )
        row = cursor.fetchone()

        assert row["status"] == "closed"
        assert row["outcome"] == "win"
        assert row["exit_price"] == 49000.0
        assert row["pnl_pct"] == pytest.approx(2.0, rel=0.01)  # +2% for SHORT
        assert row["exit_reason"] == "target_hit"
        assert row["duration_hours"] is not None
        assert row["r_multiple"] is not None  # Should calculate based on stop loss

        conn.close()

    def test_close_signal_losing(self, tracker, sample_signal):
        """Test closing a losing SHORT signal."""
        # Open first
        tracker.open_signal(signal_id=sample_signal["signal_id"])

        # Close with loss (SHORT: entry 50000, exit 50500 = -1% loss)
        result = tracker.close_signal(
            signal_id=sample_signal["signal_id"],
            exit_price=50500.0,
            exit_reason="stop_loss",
        )

        assert result is True

        # Verify
        conn = tracker._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT outcome, pnl_pct FROM trading_signals WHERE signal_id = ?",
            (sample_signal["signal_id"],),
        )
        row = cursor.fetchone()

        assert row["outcome"] == "stopped_out"  # stop_loss exit_reason
        assert row["pnl_pct"] == pytest.approx(-1.0, rel=0.01)

        conn.close()

    def test_update_excursion(self, tracker, sample_signal):
        """Test excursion tracking."""
        # Open signal
        tracker.open_signal(signal_id=sample_signal["signal_id"])

        # Update with favorable move (SHORT: price drops to 49500)
        tracker.update_excursion(
            signal_id=sample_signal["signal_id"], current_price=49500.0
        )

        # Verify MFE updated
        conn = tracker._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT mfe_pct, mfe_price FROM trading_signals WHERE signal_id = ?",
            (sample_signal["signal_id"],),
        )
        row = cursor.fetchone()

        expected_mfe = (50000 - 49500) / 50000 * 100  # +1% favorable for SHORT
        assert row["mfe_pct"] == pytest.approx(expected_mfe, rel=0.01)
        assert row["mfe_price"] == 49500.0

        # Update with adverse move (SHORT: price rises to 50200)
        tracker.update_excursion(
            signal_id=sample_signal["signal_id"], current_price=50200.0
        )

        cursor.execute(
            "SELECT mae_pct, mae_price FROM trading_signals WHERE signal_id = ?",
            (sample_signal["signal_id"],),
        )
        row = cursor.fetchone()

        expected_mae = (50000 - 50200) / 50000 * 100  # -0.4% adverse for SHORT
        assert row["mae_pct"] == pytest.approx(expected_mae, rel=0.01)
        assert row["mae_price"] == 50200.0

        conn.close()

    def test_classify_signal_pattern(self, tracker, sample_signal):
        """Test pattern classification."""
        components = {
            "orderflow": {"score": 75, "seller_aggression": 0.8},
            "technical": {"score": 30},  # Divergence: high orderflow, low technical
            "volume": {"score": 50},
        }

        result = tracker.classify_signal_pattern(
            signal_id=sample_signal["signal_id"], components=components
        )

        assert result is not None
        assert result["signal_pattern"] == "divergence"
        assert result["divergence_type"] == "bearish_divergence"

    def test_performance_summary(self, tracker, sample_signal):
        """Test performance summary calculation."""
        # Create multiple signals with outcomes
        tracker.open_signal(signal_id=sample_signal["signal_id"])
        tracker.close_signal(
            signal_id=sample_signal["signal_id"],
            exit_price=49000.0,
            exit_reason="target_hit",
        )

        # Get summary
        summary = tracker.get_performance_summary(signal_type="SHORT", days=1)

        assert summary["total_signals"] == 1
        assert summary["wins"] == 1
        assert summary["win_rate"] > 0
        assert summary["avg_pnl_pct"] is not None


class TestPnLCalculations:
    """Test P&L calculation accuracy."""

    def test_long_pnl_win(self, tracker):
        """Test LONG P&L calculation for win."""
        pnl = tracker._calculate_pnl_pct("LONG", 100.0, 110.0)
        assert pnl == pytest.approx(10.0, rel=0.01)

    def test_long_pnl_loss(self, tracker):
        """Test LONG P&L calculation for loss."""
        pnl = tracker._calculate_pnl_pct("LONG", 100.0, 95.0)
        assert pnl == pytest.approx(-5.0, rel=0.01)

    def test_short_pnl_win(self, tracker):
        """Test SHORT P&L calculation for win."""
        pnl = tracker._calculate_pnl_pct("SHORT", 100.0, 90.0)
        assert pnl == pytest.approx(10.0, rel=0.01)

    def test_short_pnl_loss(self, tracker):
        """Test SHORT P&L calculation for loss."""
        pnl = tracker._calculate_pnl_pct("SHORT", 100.0, 105.0)
        assert pnl == pytest.approx(-5.0, rel=0.01)


class TestOutcomeDetermination:
    """Test outcome classification."""

    def test_stop_loss_outcome(self, tracker):
        """Test stop loss always returns stopped_out."""
        outcome = tracker._determine_outcome(pnl_pct=-2.0, exit_reason="stop_loss")
        assert outcome == "stopped_out"

    def test_time_exit_outcome(self, tracker):
        """Test time exit returns expired."""
        outcome = tracker._determine_outcome(pnl_pct=1.0, exit_reason="time_exit")
        assert outcome == "expired"

    def test_win_outcome(self, tracker):
        """Test positive P&L returns win."""
        outcome = tracker._determine_outcome(pnl_pct=2.5, exit_reason="target_hit")
        assert outcome == "win"

    def test_loss_outcome(self, tracker):
        """Test negative P&L returns loss."""
        outcome = tracker._determine_outcome(pnl_pct=-1.5, exit_reason="manual_close")
        assert outcome == "loss"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
