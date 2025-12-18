-- Create trading_signals table for storing trading signal history
-- This table stores all generated trading signals for analytics and tracking

CREATE TABLE IF NOT EXISTS trading_signals (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Signal identification
    signal_id TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,  -- 'LONG' or 'SHORT'

    -- Scores and metrics
    confluence_score REAL NOT NULL,
    reliability REAL,  -- Overall signal reliability (0-1)

    -- Price and trade parameters
    entry_price REAL,
    stop_loss REAL,
    current_price REAL,

    -- Timestamp (milliseconds since epoch)
    timestamp INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- JSON fields for detailed data
    targets TEXT,  -- JSON array of target objects
    components TEXT,  -- JSON object with component scores
    interpretations TEXT,  -- JSON array of interpretations
    insights TEXT,  -- JSON array of actionable insights
    influential_components TEXT,  -- JSON array of influential component data
    trade_params TEXT,  -- JSON object with full trade parameters

    -- Metadata
    sent_to_discord BOOLEAN DEFAULT 0,
    json_path TEXT,
    pdf_path TEXT
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_trading_signals_symbol ON trading_signals(symbol);
CREATE INDEX IF NOT EXISTS idx_trading_signals_type ON trading_signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_trading_signals_timestamp ON trading_signals(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trading_signals_score ON trading_signals(confluence_score);
CREATE INDEX IF NOT EXISTS idx_trading_signals_created_at ON trading_signals(created_at DESC);

-- Composite index for common analytics queries
CREATE INDEX IF NOT EXISTS idx_trading_signals_analytics
    ON trading_signals(timestamp DESC, signal_type, confluence_score);
