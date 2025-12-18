-- Migration: Add status tracking columns to alerts table
-- Date: 2025-12-11
-- Purpose: Fix "no such column: status" error in alert_persistence.py

-- Add status column (required by AlertPersistence)
ALTER TABLE alerts ADD COLUMN status TEXT DEFAULT 'sent';

-- Add webhook tracking columns
ALTER TABLE alerts ADD COLUMN webhook_sent BOOLEAN DEFAULT 0;
ALTER TABLE alerts ADD COLUMN webhook_response TEXT;

-- Add timestamp tracking columns
ALTER TABLE alerts ADD COLUMN updated_at REAL;
ALTER TABLE alerts ADD COLUMN acknowledged_at REAL;
ALTER TABLE alerts ADD COLUMN resolved_at REAL;

-- Add user tracking columns
ALTER TABLE alerts ADD COLUMN acknowledged_by TEXT;
ALTER TABLE alerts ADD COLUMN resolved_by TEXT;

-- Add priority and tags columns
ALTER TABLE alerts ADD COLUMN priority TEXT DEFAULT 'normal';
ALTER TABLE alerts ADD COLUMN tags TEXT DEFAULT '[]';

-- Update existing records to have 'sent' status
UPDATE alerts SET status = 'sent' WHERE status IS NULL;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_status ON alerts (status);

-- Verification query
SELECT
    COUNT(*) as total_alerts,
    COUNT(CASE WHEN status IS NOT NULL THEN 1 END) as with_status
FROM alerts;
