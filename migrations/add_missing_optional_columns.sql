-- Migration: Add missing optional technical indicator columns to liquidation_events table
-- Date: 2025-12-15
-- Description: Adds 5 missing optional columns that were in the SQLAlchemy model but not in the database
--              These are all technical indicators and timing metrics

-- Optional technical indicators (nullable)
ALTER TABLE liquidation_events ADD COLUMN rsi REAL;
ALTER TABLE liquidation_events ADD COLUMN volume_weighted_price REAL;
ALTER TABLE liquidation_events ADD COLUMN funding_rate REAL;
ALTER TABLE liquidation_events ADD COLUMN open_interest_change REAL;

-- Optional timing metric (nullable)
ALTER TABLE liquidation_events ADD COLUMN recovery_time_seconds INTEGER;
