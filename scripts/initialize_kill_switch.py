#!/usr/bin/env python3
"""
Initialize Kill Switch Database Schema

Adds necessary columns to trading_signals table for tracking signal outcomes
and creates kill_switch_state table for configuration management.

Usage:
    python scripts/initialize_kill_switch.py

This script is idempotent - safe to run multiple times.
"""

import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def get_db_path() -> str:
    """Get path to virtuoso.db."""
    return os.path.join(project_root, 'data', 'virtuoso.db')


def initialize_schema():
    """Initialize kill switch database schema."""
    db_path = get_db_path()

    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if trading_signals table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='trading_signals'
        """)

        if not cursor.fetchone():
            print("ERROR: trading_signals table does not exist!")
            print("Please create the table first using create_trading_signals_table.sql")
            return False

        # Add columns for signal outcome tracking
        columns_to_add = [
            ('closed_at', 'TEXT DEFAULT NULL'),
            ('outcome', "TEXT DEFAULT NULL CHECK (outcome IS NULL OR outcome IN ('win', 'loss', 'breakeven'))"),
            ('close_price', 'REAL DEFAULT NULL'),
            ('pnl_percentage', 'REAL DEFAULT NULL'),
            ('notes', 'TEXT DEFAULT NULL')
        ]

        for column_name, column_def in columns_to_add:
            try:
                cursor.execute(f'ALTER TABLE trading_signals ADD COLUMN {column_name} {column_def}')
                print(f"✓ Added column: {column_name}")
            except sqlite3.OperationalError as e:
                if 'duplicate column name' in str(e).lower():
                    print(f"  Column {column_name} already exists (skipped)")
                else:
                    raise

        # Create kill_switch_state table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kill_switch_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                state TEXT NOT NULL CHECK (state IN ('active', 'inactive', 'monitoring')),
                activated_at TEXT,
                reason TEXT,
                win_rate REAL,
                closed_count INTEGER,
                updated_at TEXT NOT NULL
            )
        ''')
        print("✓ Created kill_switch_state table")

        # Initialize kill switch state
        cursor.execute('''
            INSERT OR IGNORE INTO kill_switch_state (id, state, updated_at)
            VALUES (1, 'monitoring', ?)
        ''', (datetime.now(timezone.utc).isoformat(),))
        print("✓ Initialized kill switch state to 'monitoring'")

        # Create indexes for performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_signals_short_closed
            ON trading_signals(signal_type, timestamp, closed_at)
        ''')
        print("✓ Created index: idx_signals_short_closed")

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_signals_outcome
            ON trading_signals(outcome, closed_at)
        ''')
        print("✓ Created index: idx_signals_outcome")

        conn.commit()
        print("\n✅ Kill switch schema initialized successfully!")

        # Display current schema
        print("\n--- trading_signals schema ---")
        cursor.execute("PRAGMA table_info(trading_signals)")
        for row in cursor.fetchall():
            print(f"  {row[1]}: {row[2]}")

        print("\n--- kill_switch_state schema ---")
        cursor.execute("PRAGMA table_info(kill_switch_state)")
        for row in cursor.fetchall():
            print(f"  {row[1]}: {row[2]}")

        # Show current state
        cursor.execute("SELECT * FROM kill_switch_state WHERE id = 1")
        state = cursor.fetchone()
        if state:
            print(f"\nCurrent kill switch state: {state[1]}")
            print(f"Last updated: {state[6]}")

        return True

    except Exception as e:
        print(f"\n❌ Error initializing schema: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == '__main__':
    success = initialize_schema()
    sys.exit(0 if success else 1)
