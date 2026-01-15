# Performance Tracking Quick Reference

## Apply Migration

```bash
python scripts/apply_performance_migration.py
```

## Python Usage

```python
from src.database.signal_performance import get_tracker

tracker = get_tracker("data/virtuoso.db")

# Open signal
tracker.open_signal(
    signal_id="BTCUSDT_SHORT_75_...",
    signal_pattern="divergence",
    is_validation_cohort=True,
    orderflow_config="50_45"
)

# Update during lifetime
tracker.update_excursion(signal_id, current_price=49500.0)

# Close signal
tracker.close_signal(
    signal_id="BTCUSDT_SHORT_75_...",
    exit_price=49000.0,
    exit_reason="target_hit"
)

# Get summary
summary = tracker.get_performance_summary(signal_type="SHORT", days=7)
```

## Key Queries

### Pre-fix vs Post-fix Comparison
```sql
SELECT
    CASE WHEN is_validation_cohort = 1 THEN 'POST-FIX' ELSE 'PRE-FIX' END as cohort,
    COUNT(*) as signals,
    ROUND(COUNT(*) FILTER (WHERE outcome = 'win') * 100.0 / COUNT(*), 2) as win_rate_pct,
    ROUND(AVG(pnl_pct), 2) as avg_pnl_pct
FROM trading_signals
WHERE signal_type = 'SHORT' AND status = 'closed'
GROUP BY is_validation_cohort;
```

### Active Signals
```sql
SELECT signal_id, symbol, signal_type,
       ROUND((julianday('now') - julianday(opened_at)) * 24, 1) as hours_active,
       ROUND(mfe_pct, 2) as mfe, ROUND(mae_pct, 2) as mae
FROM trading_signals
WHERE status = 'active'
ORDER BY opened_at DESC;
```

### Daily Performance
```sql
SELECT DATE(created_at) as date,
       COUNT(*) as signals,
       ROUND(COUNT(*) FILTER (WHERE outcome = 'win') * 100.0 / COUNT(*), 2) as win_rate
FROM trading_signals
WHERE signal_type = 'SHORT' AND status = 'closed'
GROUP BY DATE(created_at)
ORDER BY date DESC
LIMIT 7;
```

## P&L Formulas

**LONG**: `pnl_pct = ((exit - entry) / entry) * 100`
**SHORT**: `pnl_pct = ((entry - exit) / entry) * 100`

## Outcomes

- `win`: Positive P&L
- `loss`: Negative P&L
- `stopped_out`: Hit stop loss
- `expired`: Time-based exit

## Pattern Types

- `divergence`: Orderflow contradicts price
- `confirmation`: All components aligned
- `momentum`: Strong directional scores
- `reversal`: Trend reversal pattern
- `continuation`: Trend continuation pattern

## Validation

```bash
# Verify migration
python scripts/apply_performance_migration.py --validate-only

# Run analysis
sqlite3 data/virtuoso.db < migrations/orderflow_validation_queries.sql
```

## Rollback

```bash
python scripts/apply_performance_migration.py --rollback
```

⚠️ **Warning**: Rollback deletes all performance data!

## VPS Deployment

```bash
ssh vps
cd ~/trading/Virtuoso
cp data/virtuoso.db data/virtuoso_backup_$(date +%Y%m%d).db
git pull origin main
source venv311/bin/activate
python scripts/apply_performance_migration.py
```

## Tag Validation Cohort

```python
from src.database.signal_performance import tag_validation_cohort
count = tag_validation_cohort("data/virtuoso.db", "50_45", "2025-12-09")
```

## Files

- `migrations/add_performance_tracking.sql` - Migration
- `migrations/rollback_performance_tracking.sql` - Rollback
- `migrations/validate_migration.sql` - Validation
- `migrations/orderflow_validation_queries.sql` - Analysis
- `migrations/README.md` - Full documentation
- `src/database/signal_performance.py` - Python API
- `scripts/apply_performance_migration.py` - Migration tool
