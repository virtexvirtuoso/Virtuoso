# Kill Switch Integration Guide

## Overview

The Orderflow Kill Switch monitors SHORT signal performance and automatically reverts orderflow multipliers (CVD, OI) to legacy values if performance degrades below acceptable thresholds.

**Safety Mechanism:**
- Monitors 7-day rolling window of SHORT signals
- Triggers if win rate < 35% AND closed signals >= 20
- Reverts CVD multiplier: 50 → 35
- Reverts OI multiplier: 45 → 30
- Sends critical alerts to Discord
- Fully auditable with database state tracking

## Quick Start

### 1. Initialize Database Schema

```bash
# Run initialization script
python scripts/initialize_kill_switch.py
```

This creates:
- `kill_switch_state` table for configuration tracking
- Additional columns in `trading_signals` for outcome tracking
- Indexes for performance queries

### 2. Integrate into Main Loop

**In `src/main.py` or signal generation entry point:**

```python
from src.core.risk import get_kill_switch

# Initialize kill switch (one time, at startup)
config = load_config()
kill_switch = get_kill_switch(config)

# In main loop, before generating new signals
async def main_loop():
    while True:
        # Check kill switch every iteration
        if kill_switch.check_and_activate_if_needed():
            logger.critical("Kill switch activated - reverted to legacy multipliers")
            # Subsequent signals will use legacy multipliers

        # Generate signals as normal
        signals = await generate_signals()

        # ... rest of logic
```

### 3. Track Signal Outcomes

**When closing a signal (manually or via automation):**

```python
import sqlite3
from datetime import datetime, timezone

def close_signal(signal_id: str, outcome: str, close_price: float):
    """
    Close a signal and record outcome.

    Args:
        signal_id: Signal identifier from trading_signals table
        outcome: 'win', 'loss', or 'breakeven'
        close_price: Price at which signal was closed
    """
    conn = sqlite3.connect('data/virtuoso.db')
    cursor = conn.cursor()

    # Calculate PnL
    cursor.execute('SELECT entry_price FROM trading_signals WHERE signal_id = ?', (signal_id,))
    row = cursor.fetchone()
    entry_price = row[0] if row else None

    pnl_percentage = None
    if entry_price and close_price:
        pnl_percentage = ((close_price - entry_price) / entry_price) * 100

    # Update signal
    cursor.execute('''
        UPDATE trading_signals
        SET closed_at = ?, outcome = ?, close_price = ?, pnl_percentage = ?
        WHERE signal_id = ?
    ''', (
        datetime.now(timezone.utc).isoformat(),
        outcome,
        close_price,
        pnl_percentage,
        signal_id
    ))

    conn.commit()
    conn.close()
```

## Integration Points

### Option A: Main Loop Integration (Recommended)

**File:** `src/main.py` or `src/signal_generation/signal_generator.py`

```python
from src.core.risk import get_kill_switch

class TradingSystem:
    def __init__(self, config):
        self.config = config
        self.kill_switch = get_kill_switch(config)

    async def run(self):
        while True:
            # Check kill switch before generating signals
            self.kill_switch.check_and_activate_if_needed()

            # Generate signals
            signals = await self.generate_signals()

            await asyncio.sleep(60)
```

### Option B: Scheduled Check

**File:** `src/monitoring/monitor.py`

```python
from src.core.risk import get_kill_switch

class SystemMonitor:
    def __init__(self, config):
        self.kill_switch = get_kill_switch(config)

    async def health_check(self):
        """Run periodic health checks including kill switch."""
        # Check kill switch every 5 minutes
        self.kill_switch.check_and_activate_if_needed()

        # Other health checks...
```

## Configuration Management

The kill switch automatically updates `config/config.yaml`:

```yaml
analysis:
  indicators:
    orderflow:
      use_symmetric_divergence: false  # Set by kill switch
      _kill_switch_note: "Multipliers managed by kill switch. Current: CVD=35, OI=30"
```

**After kill switch activation:**
- `use_symmetric_divergence` → `false`
- Orderflow indicators use legacy multipliers automatically
- No code changes needed in indicator calculations

## Manual Override

To re-enable new multipliers after investigation:

```python
from src.core.risk import get_kill_switch

kill_switch = get_kill_switch(config)

# Deactivate kill switch (requires explicit flag)
kill_switch.deactivate(manual_override=True)
```

## Monitoring

### Check Kill Switch Status

```python
status = kill_switch.get_status()
print(status)
# Output:
# {
#     'state': 'monitoring',
#     'is_active': False,
#     'performance': {
#         'win_rate': 0.42,
#         'closed_count': 25,
#         'total_count': 30
#     },
#     'multipliers': {
#         'current_mode': 'new'
#     }
# }
```

### Database Queries

```sql
-- Check kill switch state
SELECT * FROM kill_switch_state WHERE id = 1;

-- Get SHORT signal performance (last 7 days)
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN closed_at IS NOT NULL THEN 1 ELSE 0 END) as closed,
    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
    AVG(pnl_percentage) as avg_pnl
FROM trading_signals
WHERE signal_type = 'SHORT'
  AND timestamp >= (strftime('%s', 'now', '-7 days') * 1000);
```

## Alert Integration

The kill switch uses the existing alert system:

```python
# Sends to Discord via alert_manager
from src.monitoring.alert_manager import alert_manager

# Kill switch automatically calls:
alert_manager.send_critical_alert(
    title="KILL SWITCH ACTIVATED",
    message="Poor performance: 32% win rate (threshold: 35%), 23 closed signals",
    details={...}
)
```

## Testing

Run unit tests:

```bash
pytest tests/risk/test_kill_switch.py -v
```

Test manually:

```python
from src.core.risk import OrderflowKillSwitch

# Create test instance with in-memory database
kill_switch = OrderflowKillSwitch(config, db_path=':memory:')

# Check performance
win_rate, closed, total = kill_switch.get_short_performance()

# Test trigger logic
should_trigger, reason = kill_switch.should_trigger()

# Test activation
success = kill_switch.activate()
```

## Troubleshooting

### Kill Switch Not Triggering

**Check data availability:**
```sql
SELECT COUNT(*) FROM trading_signals WHERE signal_type = 'SHORT';
```

**Verify closed signals:**
```sql
SELECT COUNT(*) FROM trading_signals
WHERE signal_type = 'SHORT' AND closed_at IS NOT NULL;
```

### Kill Switch Stuck in Active State

**Check state:**
```sql
SELECT * FROM kill_switch_state;
```

**Manual reset:**
```python
kill_switch.deactivate(manual_override=True)
```

### Database Errors

**Check table exists:**
```bash
sqlite3 data/virtuoso.db "SELECT name FROM sqlite_master WHERE type='table';"
```

**Reinitialize schema:**
```bash
python scripts/initialize_kill_switch.py
```

## Architecture Decisions

### Why Database State Instead of Config File Only?

1. **Auditability:** Full history of state changes
2. **Reliability:** Survives config file edits
3. **Performance:** Fast queries without parsing YAML
4. **Atomicity:** Database transactions prevent race conditions

### Why Check Every Iteration vs. Scheduled?

1. **Responsiveness:** Catch degradation quickly
2. **Simplicity:** No separate cron/scheduler needed
3. **Rate Limiting:** Built-in throttling prevents spam

### Why Idempotent Activation?

1. **Safety:** Can call multiple times without side effects
2. **Resilience:** Crash during activation doesn't corrupt state
3. **Simplicity:** No complex state machine needed

## FAQ

**Q: What happens if the database is unavailable?**
A: Kill switch defaults to monitoring state and logs errors. System continues running.

**Q: Can I customize thresholds?**
A: Yes, modify `MIN_WIN_RATE`, `MIN_CLOSED_SIGNALS`, `LOOKBACK_DAYS` in `OrderflowKillSwitch` class.

**Q: Does this affect LONG signals?**
A: No, kill switch only monitors SHORT signal performance.

**Q: How do I know if multipliers have changed?**
A: Check `kill_switch_state` table or inspect config file for `_kill_switch_note`.

**Q: Can I disable the kill switch entirely?**
A: Remove `check_and_activate_if_needed()` calls from main loop. State persists in database.

## References

- Original issue: SHORT signal quality degradation (Dec 2025)
- Fix deployment: Orderflow multiplier adjustments (CVD 35→50, OI 30→45)
- Monitoring period: 7 days post-deployment
- Safety threshold: <35% win rate with ≥20 closed signals
