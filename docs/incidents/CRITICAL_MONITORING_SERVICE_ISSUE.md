# CRITICAL: Monitoring Service High CPU Issue

## Problem
**Status**: CRITICAL - Service Degradation
**Affected**: Mobile dashboard showing zero/intermittent data
**Root Cause**: Monitoring service (main.py) consuming 98-100% CPU

## Symptoms
```bash
# Process stats (as of 2025-10-25 15:15 UTC)
PID: 2050927
CPU: 98.2%
Runtime: 21+ hours
Memory: 3GB RSS
Status: Running but degraded
```

## Impact
- Cache writes (`market:overview`, etc.) failing or delayed
- `/api/dashboard/market-overview` returns zeros intermittently
- Mobile dashboard shows "LOADING..." or zero values for:
  - Market Regime
  - Trend Strength
  - Volatility
  - Top Movers

## Data Flow
```
main.py (monitoring) → writes → Memcached → read by → web_server.py → serves → /mobile
     ↑ STUCK AT 100% CPU                                                    ↓ intermittent data
```

## Immediate Fix Required
```bash
# On VPS as linuxuser with sudo:
sudo systemctl restart virtuoso-monitoring.service

# Verify fix:
ps aux | grep 'main.py' | grep -v grep  # Should show <5% CPU
curl http://localhost:8001/health        # Should respond quickly
```

## Verification After Restart
```bash
# 1. Check CPU is normal
top -b -n 1 | grep python

# 2. Check cache is being written
# (Monitor for "Wrote market:overview" logs)
journalctl -u virtuoso-monitoring -f

# 3. Test endpoints return real data
curl http://5.223.63.4:8002/api/dashboard/market-overview | jq '{trend_strength, btc_price, gainers, losers}'
curl http://5.223.63.4:8002/api/dashboard/mobile-data | jq '.market_overview | {trend_strength, total_volume_24h}'
```

## Investigation Needed
After restart, investigate root cause of 100% CPU:

1. **Check for infinite loops** in:
   - `src/main.py` main monitoring loop
   - `src/monitoring/cache_warmer.py`
   - `src/monitoring/cache_writer.py`

2. **Profile the service** during next occurrence:
   ```bash
   py-spy top --pid <PID>
   py-spy dump --pid <PID>
   ```

3. **Review recent changes** that might have introduced inefficient polling

## Backend Code Status
✅ **Backend code is CORRECT** - no changes needed to:
- `/api/routes/dashboard.py` (market-overview endpoint)
- `/api/cache_adapter_direct.py` (cache adapter)
- `/core/cache/web_service_adapter.py` (web cache)

The endpoints properly handle data aggregation and fallbacks. The issue is purely operational (monitoring service performance).

## Workaround (If Restart Fails)
If monitoring service can't be fixed immediately:

1. **Disable monitoring service**:
   ```bash
   sudo systemctl stop virtuoso-monitoring.service
   ```

2. **Make web server cache-independent** by modifying dashboard routes to:
   - Fetch directly from exchange APIs when cache is empty
   - Increase frontend polling intervals to reduce load
   - Show "Data Unavailable" instead of zeros

## Related Files
- `src/main.py` - Monitoring service entry point
- `src/monitoring/cache_warmer.py` - Cache warming logic
- `src/monitoring/cache_writer.py` - Cache write operations
- `src/api/routes/dashboard.py` - Dashboard API routes
- `src/dashboard/templates/mobile.html` - Mobile frontend

## Timeline
- **2025-10-24**: Service started, CPU usage normal
- **2025-10-25 ~15:00 UTC**: CPU at 98-100% for 21+ hours
- **Impact**: Mobile dashboard intermittently showing zero data

## Priority
**P0** - Critical performance degradation affecting user-facing features

## Owner
System Administrator / DevOps

---
**Created**: 2025-10-25
**Status**: Open - Requires sudo access to restart service
