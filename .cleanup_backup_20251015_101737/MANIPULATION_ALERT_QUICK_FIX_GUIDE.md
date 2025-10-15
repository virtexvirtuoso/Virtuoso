# Manipulation Alert System - Quick Fix Guide

**Status:** PRODUCTION BLOCKER - NOT READY TO DEPLOY
**Estimated Fix Time:** 2-4 hours
**Severity:** CRITICAL

---

## IMMEDIATE ACTION REQUIRED

### CRITICAL BUG - Variable Scope Error (BLOCKER)

**File:** `src/monitoring/alert_manager.py`
**Lines:** 5231, 5233, 5241, 5247, 5248, 5255, 5261, 5262

**Problem:**
Code uses undefined variables `whale_buy_volume`, `whale_sell_volume`, `net_usd_value`, `whale_trades_count` which are NOT in scope. Function parameters are `buy_volume`, `sell_volume`, `usd_value`, `trades_count`.

**Impact:**
```python
NameError: name 'whale_buy_volume' is not defined
```
**All manipulation alerts will crash the system.**

**Fix:** (Apply immediately)

```python
# Line 5231 - Change from:
buy_sell_ratio = whale_buy_volume / max(whale_sell_volume, 1)

# To:
buy_sell_ratio = buy_volume / max(sell_volume, 1)


# Line 5233 - Change from:
volume_mismatch_severity = self._calculate_manipulation_severity(
    abs(net_usd_value), whale_trades_count, buy_sell_ratio
)

# To:
volume_mismatch_severity = self._calculate_manipulation_severity(
    usd_value, trades_count, buy_sell_ratio
)


# Line 5241 - Change from:
actual_trades=f"{whale_sell_volume:.0f} SELL trades",

# To:
actual_trades=f"{sell_volume:.0f} SELL trades",


# Line 5247-5248 - Change from:
volume=abs(net_usd_value),
trade_count=whale_trades_count

# To:
volume=usd_value,
trade_count=trades_count


# Line 5255 - Change from:
actual_trades=f"{whale_buy_volume:.0f} BUY trades",

# To:
actual_trades=f"{buy_volume:.0f} BUY trades",


# Line 5261-5262 - Change from:
volume=abs(net_usd_value),
trade_count=whale_trades_count

# To:
volume=usd_value,
trade_count=trades_count
```

**Verification:**
```bash
# After fix, run:
python3 -m py_compile src/monitoring/alert_manager.py

# Should produce no errors
```

---

## CRITICAL INPUT VALIDATION (BLOCKER)

**File:** `src/monitoring/alert_manager.py`
**Function:** `_calculate_manipulation_severity` (line 5267)

**Problem:**
No validation for:
- Infinity values (`float('inf')`)
- NaN values (`float('nan')`)
- Negative values
- Zero activity

**Fix:** (Add at start of function)

```python
def _calculate_manipulation_severity(self, volume: float, trade_count: int, buy_sell_ratio: float) -> str:
    """Calculate manipulation severity with input validation."""
    import math

    # CRITICAL: Validate finite values
    if not math.isfinite(volume):
        self.logger.error(f"Invalid volume in severity calculation: {volume}")
        return "LOW"  # Fail safe

    if not math.isfinite(buy_sell_ratio):
        self.logger.error(f"Invalid buy_sell_ratio in severity calculation: {buy_sell_ratio}")
        return "LOW"  # Fail safe

    # Handle negative values
    if volume < 0:
        self.logger.warning(f"Negative volume in severity calculation: {volume}, using absolute value")
        volume = abs(volume)

    if trade_count < 0:
        self.logger.warning(f"Negative trade count in severity calculation: {trade_count}, setting to 0")
        trade_count = 0

    # Zero activity check
    if volume < 100_000:  # Less than $100K
        self.logger.debug(f"Low volume activity in manipulation detection: ${volume:,.0f}")
        return "LOW"

    # Continue with existing logic...
```

---

## HIGH PRIORITY ERROR HANDLING

**File:** `src/monitoring/alert_manager.py`
**Function:** `_format_manipulation_alert` (line 5324)

**Problem:**
No error handling - will crash on invalid input.

**Fix:** (Add at start of function)

```python
def _format_manipulation_alert(self, ...) -> str:
    """Format manipulation alert with error handling."""
    import math

    try:
        # Validate inputs
        if not isinstance(volume, (int, float)) or not math.isfinite(volume):
            self.logger.error(f"Invalid volume for alert formatting: {volume}")
            volume = 0

        if not isinstance(trade_count, int) or trade_count < 0:
            self.logger.error(f"Invalid trade count for alert formatting: {trade_count}")
            trade_count = 0

    except Exception as e:
        self.logger.error(f"Error validating alert format inputs: {e}")
        pass  # Continue with best effort

    # Continue with existing formatting logic...
```

---

## TESTING CHECKLIST

After applying fixes:

1. **Syntax Check:**
   ```bash
   python3 -m py_compile src/monitoring/alert_manager.py
   ```

2. **Run Basic Tests:**
   ```bash
   python3 scripts/test_enhanced_manipulation_alerts.py
   ```
   Expected: All tests pass

3. **Run Comprehensive Validation:**
   ```bash
   python3 tests/validation/comprehensive_manipulation_alert_validation.py
   ```
   Expected: All tests pass (5/5)

4. **Manual Integration Test:**
   ```python
   # Test the fixed functions directly
   from src.monitoring.alert_manager import AlertManager

   # Create instance
   manager = AlertManager(...)

   # Test severity with edge cases
   assert manager._calculate_manipulation_severity(float('inf'), 10, 5.0) == "LOW"
   assert manager._calculate_manipulation_severity(-1000000, 5, 3.0) != "EXTREME"
   assert manager._calculate_manipulation_severity(0, 0, 0.0) == "LOW"

   # Test formatting
   result = manager._format_manipulation_alert(
       pattern="FAKE SELL WALL",
       orderbook_signal="test",
       actual_trades="test",
       manipulation_tactic="test",
       whale_action="test",
       risk_scenario="test",
       trader_action="test",
       severity="HIGH",
       volume=5000000,
       trade_count=5
   )
   assert "HIGH" in result
   assert "$5.0M" in result
   ```

5. **Staging Deployment:**
   - Deploy to staging environment
   - Monitor logs for 1 hour
   - Verify no NameError or TypeError exceptions
   - Verify alerts appear in Discord
   - Verify database persistence works

6. **Production Deployment:**
   - Only after staging verification
   - Deploy during low-traffic window
   - Monitor closely for first 2 hours
   - Have rollback plan ready

---

## QUICK APPLY SCRIPT

Save this as `apply_manipulation_alert_fix.sh`:

```bash
#!/bin/bash
set -e

echo "Applying critical manipulation alert fixes..."

# Backup original file
cp src/monitoring/alert_manager.py src/monitoring/alert_manager.py.backup.$(date +%Y%m%d_%H%M%S)

# Apply fixes using sed (macOS compatible)
sed -i '' 's/whale_buy_volume/buy_volume/g' src/monitoring/alert_manager.py
sed -i '' 's/whale_sell_volume/sell_volume/g' src/monitoring/alert_manager.py
sed -i '' 's/net_usd_value/usd_value/g' src/monitoring/alert_manager.py
sed -i '' 's/whale_trades_count/trades_count/g' src/monitoring/alert_manager.py

echo "Variable name fixes applied."

# Note: Input validation and error handling must be applied manually
# as they require code insertion, not simple replacement

echo ""
echo "Next steps:"
echo "1. Manually add input validation to _calculate_manipulation_severity (line 5267)"
echo "2. Manually add error handling to _format_manipulation_alert (line 5324)"
echo "3. Run: python3 -m py_compile src/monitoring/alert_manager.py"
echo "4. Run: python3 scripts/test_enhanced_manipulation_alerts.py"
echo "5. Run: python3 tests/validation/comprehensive_manipulation_alert_validation.py"

echo ""
echo "Backup saved to: src/monitoring/alert_manager.py.backup.*"
```

**WARNING:** This script only fixes the variable names. You must MANUALLY add input validation and error handling.

---

## TIME ESTIMATE

| Task | Time | Priority |
|------|------|----------|
| Fix variable scope (CRITICAL-3) | 10 min | P0 - BLOCKER |
| Add input validation (CRITICAL-1,2,4) | 30 min | P0 - BLOCKER |
| Add error handling (HIGH-2) | 30 min | P1 - HIGH |
| Run comprehensive validation | 15 min | P0 - BLOCKER |
| Test in staging | 60 min | P0 - BLOCKER |
| **TOTAL** | **2h 25min** | **BLOCKING** |

---

## ROLLBACK PLAN

If issues occur in production:

1. **Immediate Rollback:**
   ```bash
   # Restore backup
   cp src/monitoring/alert_manager.py.backup.YYYYMMDD_HHMMSS src/monitoring/alert_manager.py

   # Restart service
   systemctl restart virtuoso  # Or your restart command
   ```

2. **Verify Service Recovery:**
   - Check logs for errors
   - Verify alerts flow normally
   - Check Discord notifications

3. **Post-Mortem:**
   - Document what went wrong
   - Update fix approach
   - Re-test in staging

---

## CONTACT FOR ISSUES

- **QA Team:** Review validation report
- **DevOps:** Staging deployment support
- **On-Call:** Production issues

---

**Last Updated:** 2025-10-01
**Status:** AWAITING FIX APPLICATION
