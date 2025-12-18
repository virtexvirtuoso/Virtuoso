-- Kill Switch Database Schema
-- Adds necessary columns to trading_signals table for kill switch monitoring
--
-- Usage: sqlite3 data/virtuoso.db < scripts/create_kill_switch_schema.sql

-- Add columns to track signal outcomes
-- These columns allow us to monitor win rates and determine kill switch activation

-- Add closed_at timestamp (when signal was closed)
ALTER TABLE trading_signals ADD COLUMN closed_at TEXT DEFAULT NULL;

-- Add outcome (win/loss/breakeven)
ALTER TABLE trading_signals ADD COLUMN outcome TEXT DEFAULT NULL
  CHECK (outcome IS NULL OR outcome IN ('win', 'loss', 'breakeven'));

-- Add close_price (price when signal was closed)
ALTER TABLE trading_signals ADD COLUMN close_price REAL DEFAULT NULL;

-- Add pnl_percentage (profit/loss as percentage)
ALTER TABLE trading_signals ADD COLUMN pnl_percentage REAL DEFAULT NULL;

-- Add notes (optional closing notes)
ALTER TABLE trading_signals ADD COLUMN notes TEXT DEFAULT NULL;

-- Create kill switch state table (if not exists)
CREATE TABLE IF NOT EXISTS kill_switch_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Single row table
    state TEXT NOT NULL CHECK (state IN ('active', 'inactive', 'monitoring')),
    activated_at TEXT,  -- When kill switch was activated
    reason TEXT,  -- Reason for activation
    win_rate REAL,  -- Win rate that triggered activation
    closed_count INTEGER,  -- Number of closed signals when activated
    updated_at TEXT NOT NULL  -- Last update timestamp
);

-- Initialize kill switch state to monitoring
INSERT OR IGNORE INTO kill_switch_state (id, state, updated_at)
VALUES (1, 'monitoring', datetime('now'));

-- Create index for performance queries
CREATE INDEX IF NOT EXISTS idx_signals_short_closed
ON trading_signals(signal_type, timestamp, closed_at);

-- Create index for outcome queries
CREATE INDEX IF NOT EXISTS idx_signals_outcome
ON trading_signals(outcome, closed_at);

-- Display schema info
.schema trading_signals
.schema kill_switch_state
