-- Migration: Add volatility_spike column to liquidation_events table
-- Date: 2025-12-15
-- Description: Adds the missing volatility_spike column with default value 1.0

ALTER TABLE liquidation_events
ADD COLUMN volatility_spike REAL DEFAULT 1.0;
