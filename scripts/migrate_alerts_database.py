#!/usr/bin/env python3
"""
Database Migration Script for Alerts Table
Adds missing status and tracking columns to fix alert_persistence.py initialization errors
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

def run_migration(db_path: str, dry_run: bool = False):
    """
    Run the alerts table migration

    Args:
        db_path: Path to the SQLite database
        dry_run: If True, only show what would be done without executing
    """

    print(f"{'[DRY RUN] ' if dry_run else ''}Migration: Add alert status columns")
    print(f"Database: {db_path}")
    print(f"Timestamp: {datetime.now().isoformat()}\n")

    # Check if database exists
    if not Path(db_path).exists():
        print(f"❌ Error: Database not found at {db_path}")
        return False

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check current schema
        cursor.execute("PRAGMA table_info(alerts)")
        columns = {row[1] for row in cursor.fetchall()}
        print(f"Current columns: {sorted(columns)}\n")

        # Determine which columns need to be added
        required_columns = {
            'status': ('TEXT', 'sent'),
            'webhook_sent': ('BOOLEAN', '0'),
            'webhook_response': ('TEXT', None),
            'updated_at': ('REAL', None),
            'acknowledged_at': ('REAL', None),
            'resolved_at': ('REAL', None),
            'acknowledged_by': ('TEXT', None),
            'resolved_by': ('TEXT', None),
            'priority': ('TEXT', 'normal'),
            'tags': ('TEXT', '[]')
        }

        missing_columns = {col: spec for col, spec in required_columns.items() if col not in columns}

        if not missing_columns:
            print("✅ All required columns already exist. No migration needed.")
            return True

        print(f"Missing columns to add: {list(missing_columns.keys())}\n")

        if dry_run:
            print("DRY RUN - Would execute the following:")
            for col, (col_type, default) in missing_columns.items():
                default_clause = f" DEFAULT {default}" if default else ""
                print(f"  ALTER TABLE alerts ADD COLUMN {col} {col_type}{default_clause};")
            print("\nDRY RUN complete. No changes made.")
            return True

        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")

        # Add each missing column
        for col, (col_type, default) in missing_columns.items():
            default_clause = f" DEFAULT {default}" if default else ""
            sql = f"ALTER TABLE alerts ADD COLUMN {col} {col_type}{default_clause}"
            print(f"Executing: {sql}")
            cursor.execute(sql)

        # Update existing records
        if 'status' in missing_columns:
            print("Updating existing records with default status='sent'")
            cursor.execute("UPDATE alerts SET status = 'sent' WHERE status IS NULL")
            updated_count = cursor.rowcount
            print(f"  Updated {updated_count} records")

        # Create index for status column
        print("Creating index on status column")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON alerts (status)")

        # Commit transaction
        conn.commit()

        # Verify migration
        cursor.execute("PRAGMA table_info(alerts)")
        new_columns = {row[1] for row in cursor.fetchall()}

        print("\n✅ Migration completed successfully!")
        print(f"New columns: {sorted(new_columns)}")

        # Get record counts
        cursor.execute("SELECT COUNT(*) FROM alerts")
        total_alerts = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM alerts WHERE status IS NOT NULL")
        with_status = cursor.fetchone()[0]

        print(f"\nVerification:")
        print(f"  Total alerts: {total_alerts}")
        print(f"  Alerts with status: {with_status}")

        return True

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    # Default database path
    db_path = "data/virtuoso.db"
    dry_run = False

    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--dry-run":
            dry_run = True
        elif sys.argv[1] == "--help":
            print("Usage: python migrate_alerts_database.py [--dry-run] [db_path]")
            print("\nOptions:")
            print("  --dry-run    Show what would be done without executing")
            print("  --help       Show this help message")
            print(f"\nDefault database: {db_path}")
            sys.exit(0)
        else:
            db_path = sys.argv[1]

    if len(sys.argv) > 2:
        db_path = sys.argv[2]

    success = run_migration(db_path, dry_run)
    sys.exit(0 if success else 1)
