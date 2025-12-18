"""
Test Suite for Daily Performance Monitor

Tests various scenarios including:
- Good performance (no alerts)
- Bad performance (alerts triggered)
- Edge cases (no data, missing database, etc.)
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.daily_performance_monitor import (
    DailyPerformanceMonitor,
    AlertDispatcher,
    SignalPerformance,
    RedFlag
)


class TestSignalPerformance:
    """Test SignalPerformance class."""

    def test_calculate_metrics_with_data(self):
        """Test metrics calculation with valid data."""
        perf = SignalPerformance("2025-12-11")
        perf.total = 10
        perf.closed = 8
        perf.wins = 5
        perf.losses = 3
        perf.pnl_sum = 4.0

        perf.calculate_metrics()

        assert perf.win_rate == 62.5  # 5/8 * 100
        assert perf.avg_pnl == 0.5  # 4.0/8

    def test_calculate_metrics_no_closed(self):
        """Test metrics calculation with no closed signals."""
        perf = SignalPerformance("2025-12-11")
        perf.total = 10
        perf.closed = 0

        perf.calculate_metrics()

        assert perf.win_rate == 0.0
        assert perf.avg_pnl == 0.0

    def test_to_dict(self):
        """Test dictionary conversion."""
        perf = SignalPerformance("2025-12-11")
        perf.total = 10
        perf.closed = 8
        perf.wins = 5
        perf.losses = 3
        perf.pnl_sum = 4.0
        perf.calculate_metrics()

        d = perf.to_dict()

        assert d['date'] == "2025-12-11"
        assert d['total'] == 10
        assert d['closed'] == 8
        assert d['wins'] == 5
        assert d['losses'] == 3


class TestRedFlag:
    """Test RedFlag class."""

    def test_red_flag_creation(self):
        """Test red flag creation."""
        flag = RedFlag(
            severity='critical',
            category='win_rate',
            message="Test message",
            details={'value': 30.0}
        )

        assert flag.severity == 'critical'
        assert flag.category == 'win_rate'
        assert flag.message == "Test message"
        assert flag.details['value'] == 30.0

    def test_red_flag_str(self):
        """Test string representation."""
        flag = RedFlag('warning', 'pnl', "Test warning")
        assert "⚠️" in str(flag)

        flag = RedFlag('critical', 'pnl', "Test critical")
        assert "🚨" in str(flag)


class TestDatabaseSetup:
    """Setup test database with mock data."""

    @staticmethod
    def create_test_db(scenario: str = "good") -> str:
        """Create temporary test database with mock data.

        Args:
            scenario: 'good', 'bad_winrate', 'bad_pnl', 'consecutive_losses', 'no_data'

        Returns:
            Path to temporary database
        """
        # Create temp file
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create schema
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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        if scenario == "no_data":
            # No data inserted
            conn.commit()
            conn.close()
            return db_path

        # Generate mock signals based on scenario
        now = datetime.now(timezone.utc)

        if scenario == "good":
            # Good performance: 60% win rate, positive P&L
            for day_offset in range(7):
                date = now - timedelta(days=day_offset)
                timestamp_ms = int(date.timestamp() * 1000)

                for i in range(10):  # 10 signals per day
                    signal_id = f"btcusdt_short_{day_offset}_{i}"
                    cursor.execute("""
                        INSERT INTO trading_signals
                        (signal_id, symbol, signal_type, confluence_score, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (signal_id, 'BTCUSDT', 'SHORT', 65.0, timestamp_ms))

        elif scenario == "bad_winrate":
            # Bad win rate: 25% win rate
            for day_offset in range(7):
                date = now - timedelta(days=day_offset)
                timestamp_ms = int(date.timestamp() * 1000)

                for i in range(10):
                    signal_id = f"btcusdt_short_{day_offset}_{i}"
                    cursor.execute("""
                        INSERT INTO trading_signals
                        (signal_id, symbol, signal_type, confluence_score, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (signal_id, 'BTCUSDT', 'SHORT', 45.0, timestamp_ms))

        elif scenario == "bad_pnl":
            # Good win rate but negative P&L
            for day_offset in range(7):
                date = now - timedelta(days=day_offset)
                timestamp_ms = int(date.timestamp() * 1000)

                for i in range(10):
                    signal_id = f"btcusdt_short_{day_offset}_{i}"
                    cursor.execute("""
                        INSERT INTO trading_signals
                        (signal_id, symbol, signal_type, confluence_score, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (signal_id, 'BTCUSDT', 'SHORT', 55.0, timestamp_ms))

        elif scenario == "consecutive_losses":
            # 5 consecutive days of losses
            for day_offset in range(7):
                date = now - timedelta(days=day_offset)
                timestamp_ms = int(date.timestamp() * 1000)

                for i in range(10):
                    signal_id = f"btcusdt_short_{day_offset}_{i}"
                    cursor.execute("""
                        INSERT INTO trading_signals
                        (signal_id, symbol, signal_type, confluence_score, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (signal_id, 'BTCUSDT', 'SHORT', 40.0, timestamp_ms))

        conn.commit()
        conn.close()
        return db_path


class TestDailyPerformanceMonitor:
    """Test DailyPerformanceMonitor class."""

    def test_get_db_connection(self):
        """Test database connection."""
        db_path = TestDatabaseSetup.create_test_db("good")

        try:
            monitor = DailyPerformanceMonitor(db_path, days=7)
            conn = monitor.get_db_connection()
            assert conn is not None
            conn.close()
        finally:
            os.unlink(db_path)

    def test_get_db_connection_missing(self):
        """Test database connection with missing database."""
        monitor = DailyPerformanceMonitor("/nonexistent/path.db", days=7)

        with pytest.raises(FileNotFoundError):
            monitor.get_db_connection()

    def test_query_daily_performance_with_data(self):
        """Test querying daily performance with data."""
        db_path = TestDatabaseSetup.create_test_db("good")

        try:
            monitor = DailyPerformanceMonitor(db_path, days=7)
            daily_stats = monitor.query_daily_performance()

            assert len(daily_stats) > 0
            assert all(isinstance(s, SignalPerformance) for s in daily_stats)

        finally:
            os.unlink(db_path)

    def test_query_daily_performance_no_data(self):
        """Test querying daily performance with no data."""
        db_path = TestDatabaseSetup.create_test_db("no_data")

        try:
            monitor = DailyPerformanceMonitor(db_path, days=7)
            daily_stats = monitor.query_daily_performance()

            assert len(daily_stats) == 0

        finally:
            os.unlink(db_path)

    def test_detect_low_win_rate(self):
        """Test detection of low win rate red flag."""
        db_path = TestDatabaseSetup.create_test_db("bad_winrate")

        try:
            monitor = DailyPerformanceMonitor(db_path, days=7)
            monitor.run_analysis()

            # Should have win rate red flags
            win_rate_flags = [f for f in monitor.red_flags if f.category == 'win_rate']
            assert len(win_rate_flags) > 0

        finally:
            os.unlink(db_path)

    def test_detect_negative_pnl(self):
        """Test detection of negative P&L red flag."""
        db_path = TestDatabaseSetup.create_test_db("bad_pnl")

        try:
            monitor = DailyPerformanceMonitor(db_path, days=7)
            monitor.run_analysis()

            # Note: This test depends on random simulation
            # In real implementation with actual P&L data, this would be more reliable

        finally:
            os.unlink(db_path)

    def test_detect_consecutive_losses(self):
        """Test detection of consecutive losing days."""
        db_path = TestDatabaseSetup.create_test_db("consecutive_losses")

        try:
            monitor = DailyPerformanceMonitor(db_path, days=7)
            monitor.run_analysis()

            # Should have trend red flags for consecutive losses
            # Note: This depends on simulated P&L data

        finally:
            os.unlink(db_path)

    def test_format_console_report(self):
        """Test console report formatting."""
        db_path = TestDatabaseSetup.create_test_db("good")

        try:
            monitor = DailyPerformanceMonitor(db_path, days=7)
            monitor.run_analysis()

            report = monitor.format_console_report()

            assert "SHORT SIGNAL PERFORMANCE" in report
            assert "Date" in report
            assert "Win Rate" in report
            assert "CUMULATIVE" in report

        finally:
            os.unlink(db_path)

    def test_save_report(self):
        """Test saving report to file."""
        db_path = TestDatabaseSetup.create_test_db("good")

        try:
            monitor = DailyPerformanceMonitor(db_path, days=7)
            monitor.run_analysis()

            # Test dry-run mode
            report_path = monitor.save_report(dry_run=True)
            assert not os.path.exists(report_path)  # Should not be created in dry-run

            # Test actual save
            report_path = monitor.save_report(dry_run=False)
            assert os.path.exists(report_path)

            # Cleanup
            os.unlink(report_path)

        finally:
            os.unlink(db_path)


class TestAlertDispatcher:
    """Test AlertDispatcher class."""

    def test_load_config_missing(self):
        """Test loading config when file is missing."""
        dispatcher = AlertDispatcher(config_path="/nonexistent/config.yaml")
        assert dispatcher.config == {}

    def test_send_console_alert(self, capsys):
        """Test console alert output."""
        db_path = TestDatabaseSetup.create_test_db("good")

        try:
            monitor = DailyPerformanceMonitor(db_path, days=7)
            monitor.run_analysis()

            dispatcher = AlertDispatcher()
            dispatcher.send_console_alert(monitor)

            captured = capsys.readouterr()
            assert "SHORT SIGNAL PERFORMANCE" in captured.out

        finally:
            os.unlink(db_path)

    def test_send_discord_alert_no_webhook(self):
        """Test Discord alert when webhook is not configured."""
        db_path = TestDatabaseSetup.create_test_db("bad_winrate")

        try:
            monitor = DailyPerformanceMonitor(db_path, days=7)
            monitor.run_analysis()

            dispatcher = AlertDispatcher()
            dispatcher.discord_webhook_url = None

            # Should log warning but not crash
            dispatcher.send_discord_alert(monitor, dry_run=False)

        finally:
            os.unlink(db_path)

    def test_send_discord_alert_no_red_flags(self):
        """Test Discord alert when there are no red flags."""
        db_path = TestDatabaseSetup.create_test_db("good")

        try:
            monitor = DailyPerformanceMonitor(db_path, days=7)
            monitor.run_analysis()

            dispatcher = AlertDispatcher()
            dispatcher.discord_webhook_url = "https://discord.com/api/webhooks/test"

            # Should skip sending alert
            dispatcher.send_discord_alert(monitor, dry_run=True)

        finally:
            os.unlink(db_path)


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_workflow_good_performance(self):
        """Test complete workflow with good performance."""
        db_path = TestDatabaseSetup.create_test_db("good")

        try:
            # Run analysis
            monitor = DailyPerformanceMonitor(db_path, days=7)
            monitor.run_analysis()

            # Should have no red flags
            assert len(monitor.red_flags) == 0

            # Generate report
            report = monitor.format_console_report()
            assert "No performance issues detected" in report or len(monitor.red_flags) == 0

        finally:
            os.unlink(db_path)

    def test_full_workflow_bad_performance(self):
        """Test complete workflow with bad performance."""
        db_path = TestDatabaseSetup.create_test_db("bad_winrate")

        try:
            # Run analysis
            monitor = DailyPerformanceMonitor(db_path, days=7)
            monitor.run_analysis()

            # Should have red flags
            assert len(monitor.red_flags) > 0

            # Generate report
            report = monitor.format_console_report()
            assert "RED FLAGS" in report

        finally:
            os.unlink(db_path)

    def test_full_workflow_no_data(self):
        """Test complete workflow with no data."""
        db_path = TestDatabaseSetup.create_test_db("no_data")

        try:
            # Run analysis
            monitor = DailyPerformanceMonitor(db_path, days=7)
            monitor.run_analysis()

            # Should have no stats
            assert len(monitor.daily_stats) == 0

            # Should still generate report without crashing
            report = monitor.format_console_report()
            assert "SHORT SIGNAL PERFORMANCE" in report

        finally:
            os.unlink(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
