# Confluence System Monitoring Guide

**Status:** 🟢 LIVE - Deployed 2025-10-15 17:20:56 UTC (Updated 2025-10-16 19:26:37 UTC with SNR method)
**Current Phase:** Day 2 - Post-SNR deployment monitoring
**Latest Change:** SNR-Based Confidence formula (fixes circular reasoning)

---

## Quick Daily Check (30 seconds)

```bash
# Run this command once per day to check system health
ssh vps "journalctl -u virtuoso-trading --since '2 hours ago' 2>&1 | \
  grep 'Quality metrics' > /tmp/confluence_check.txt && \
  python3 << 'EOF'
import re
with open('/tmp/confluence_check.txt', 'r') as f:
    lines = f.readlines()
    pattern = r'Confidence:\s+(\d+\.\d+)'
    confidences = [float(m.group(1)) for line in lines for m in [re.search(pattern, line)] if m]
    if confidences:
        mean = sum(confidences) / len(confidences)
        max_conf = max(confidences)
        amplified = sum(1 for c in confidences if c > 0.50)
        print(f'Sample: {len(confidences)} signals')
        print(f'Mean confidence: {mean:.3f}')
        print(f'Max confidence: {max_conf:.3f}')
        print(f'Amplified: {amplified} ({amplified/len(confidences)*100:.1f}%)')
        print(f'Status: {"✅ Normal" if mean < 0.15 else "⚠️ Trending market detected"}')
EOF
"
```

**Expected output (weak markets):**
```
Sample: 100-200 signals
Mean confidence: 0.050-0.100
Max confidence: 0.150-0.300
Amplified: 0 (0.0%)
Status: ✅ Normal
```

---

## What to Watch For

### ✅ **GOOD SIGNS** (Expected in current weak markets)
- Mean confidence: 0.05-0.15
- Amplification rate: 0-2%
- Max confidence: <0.50
- System stable, no crashes

### ⚠️  **INTERESTING** (Market conditions changing)
- Mean confidence: 0.20-0.40
- Amplification rate: 3-8%
- Max confidence: 0.50-0.70
- **Action:** Start watching closely for trending markets

### 🎯 **TARGET** (Strong trends - this is success!)
- Mean confidence: 0.30-0.50
- Amplification rate: 8-12%
- Max confidence: >0.50
- **Action:** System working as designed! Track win rates.

### 🔴 **PROBLEMS** (Need investigation)
- System crashes or errors
- Amplification rate >20%
- Mean confidence >0.70 (unrealistic)
- **Action:** Review logs, consider rollback

---

## Weekly Deep Dive (10 minutes)

Run this **every Sunday** for detailed analysis:

```bash
ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && \
  python3 scripts/monitoring/track_confluence_performance.py --since '7 days ago'"
```

**What to check:**
1. **Amplification Rate Trend**
   - Week 1: 0-3% (weak markets) ✓
   - Week 2: 5-10% (varied conditions) 🎯
   - Week 3+: 8-12% (stable target) 🎯

2. **Confidence Distribution**
   - Should gradually shift right as markets vary
   - P90 should eventually reach 0.40-0.50

3. **System Stability**
   - No crashes or errors
   - Consistent performance

---

## Check-in Schedule

| Date | Task | Expected Result |
|------|------|-----------------|
| **2025-10-16** | 24-hour check | Baseline confirmed, system stable |
| **2025-10-18** | 3-day review | Watch for first trending markets |
| **2025-10-22** | Week 1 analysis | Varied market exposure, rising amp rate |
| **2025-10-29** | Week 2 analysis | Final validation, decide if production-ready |

---

## One-Liner Health Check

```bash
# Fastest way to check system health
ssh vps "journalctl -u virtuoso-trading --since '1 hour ago' | \
  grep -c 'Quality metrics' && \
  systemctl status virtuoso-trading | grep Active"
```

**Expected:**
```
50-100          ← Signal count (system processing)
Active: active  ← Service running
```

---

## Current Baseline (2025-10-15)

**Established from first 2 hours:**
- Sample: 669 signals
- Amplification: 0.00%
- Mean confidence: 0.081
- Mean consensus: 0.909
- Status: ✅ System correctly dampening weak signals

---

## Quick Reference

**Thresholds (NEW):**
- Confidence: >0.50 (was 0.70)
- Consensus: >0.75 (was 0.80)
- Max amplification: 15%

**Success Criteria (14-day):**
- Amplification rate: 8-12%
- Mean confidence: 0.30-0.40 (during trends)
- No system errors
- Stable performance

**Rollback Command (if needed):**
```bash
git revert HEAD~1 && \
rsync -avz src/core/analysis/confluence.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/core/analysis/ && \
ssh vps "sudo systemctl restart virtuoso-trading"
```

---

## Documentation Links

- **Deployment Status:** `docs/reports/CONFLUENCE_DEPLOYMENT_STATUS.md`
- **Full Analysis:** `docs/reports/CONFLUENCE_TRANSFORMATION_SUMMARY.md`
- **Implementation Details:** `docs/fixes/confluence-scores/CONFLUENCE_FIXES_IMPLEMENTATION.md`
- **Tests:** `tests/validation/test_confluence_fixes_2025_10_15.py`

---

**Last Updated:** 2025-10-15
**Next Milestone:** 2025-10-16 (24-hour check)
