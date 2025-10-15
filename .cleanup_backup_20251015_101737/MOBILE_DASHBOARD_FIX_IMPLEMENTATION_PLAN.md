# Mobile Dashboard Data Issue - Implementation Plan

**Date**: 2025-10-14
**Issue**: VPS mobile dashboard at http://5.223.63.4:8002/mobile shows zeros for Market Overview and missing Confluence Scores
**Status**: Ready for Implementation
**Estimated Effort**: 2-3 hours
**Risk Level**: Low
**Impact**: High

---

## Executive Summary

The mobile dashboard endpoint `/api/dashboard/mobile-data` is currently reading directly from raw memcached keys (`market:overview`, `market:breadth`, `analysis:signals`) that contain incompatible data schemas, resulting in zero values for all Market Overview metrics and empty Confluence Scores.

Meanwhile, the `/api/market/overview` endpoint works correctly because it uses a smart **web cache adapter** with automatic fallback logic to fetch live data when cache is stale or missing.

**Solution**: Refactor the mobile-data endpoint to use the existing, proven cache adapter pattern instead of direct memcached access.

---

## Problem Analysis

### Symptoms
1. **Market Overview shows all zeros:**
   - `trend_strength: 0`
   - `btc_dominance: 0`
   - `total_volume_24h: 0`

2. **Confluence Scores section is empty**
   - No symbols displayed
   - No scoring data

3. **Top Movers may work** (fetched directly from Bybit API)

### Root Causes

#### 1. Direct Memcached Access
The `/mobile-data` endpoint (line 831 in `src/api/routes/dashboard.py`) directly reads from memcached using `aiomcache`:

```python
# Current problematic code
cache_client = aiomcache.Client("localhost", 11211)
overview_data = await cache_client.get(b"market:overview")
```

This bypasses all error handling, fallback logic, and schema translation.

#### 2. Cache Schema Mismatch
The cached `market:overview` key has fields like:
- `total_symbols_monitored`
- `symbols_tracked`

But the mobile dashboard expects:
- `trend_strength`
- `btc_dominance`
- `total_volume_24h`

#### 3. Empty Signals Cache
The `analysis:signals` cache key has empty arrays:
- `recent_signals: []`
- `top_symbols: []`

#### 4. No Fallback Logic
When cache data is missing or incompatible, the endpoint just returns zeros instead of fetching live data.

---

## Solution Design

### Approach: Use Existing Cache Adapter Pattern

The codebase **already has working solutions** that we can leverage:

#### Option 1: WebServiceCacheAdapter (RECOMMENDED)
**File**: `src/core/cache/web_service_adapter.py`
**Method**: `get_mobile_data()` (line 312)

**Why this works:**
- ✅ Already has `get_mobile_data()` method specifically designed for this use case
- ✅ Uses shared cache bridge with fallback to live data
- ✅ Handles confluence scores with breakdown data
- ✅ Proper error handling and schema translation
- ✅ Currently used by `/market-overview` which is working correctly on VPS
- ✅ Returns live data when cache is stale

**Implementation**: Replace direct memcached access with a call to `web_cache.get_mobile_data()`

#### Option 2: DirectCacheAdapter
**File**: `src/api/cache_adapter_direct.py`
**Method**: `get_mobile_data()` (line 721)

**Why this works:**
- ✅ Has multi-tier caching (L1 memory, L2 memcached, L3 Redis)
- ✅ Automatic fallback to live data on cache miss
- ✅ Schema mapping and data enrichment
- ✅ Performance optimized

**Note**: This is a heavier solution and the WebServiceCacheAdapter is already being used successfully.

---

## Implementation Steps

### Phase 1: Code Changes (45 minutes)

#### Step 1.1: Verify web_cache is available
**File**: `src/api/routes/dashboard.py` (line 48-62)

The code already imports and initializes `web_cache`:
```python
try:
    from src.core.cache.web_service_adapter import get_web_service_cache_adapter
    web_cache = get_web_service_cache_adapter()
    logger.info("✅ Shared cache web adapter loaded for dashboard")
except ImportError as e:
    logger.warning(f"Shared cache web adapter not available: {e}")
```

✅ **Verification**: Check that this import succeeds

#### Step 1.2: Refactor /mobile-data endpoint
**File**: `src/api/routes/dashboard.py` (line 831-1040)

**Current code** (direct memcached, ~210 lines):
```python
@router.get("/mobile-data")
async def get_mobile_dashboard_data() -> Dict[str, Any]:
    try:
        import aiomcache
        import json
        cache_client = aiomcache.Client("localhost", 11211)
        overview_data = await cache_client.get(b"market:overview")
        # ... 200+ lines of manual parsing and Bybit API calls
```

**New code** (using cache adapter, ~30 lines):
```python
@router.get("/mobile-data")
async def get_mobile_dashboard_data() -> Dict[str, Any]:
    """Optimized endpoint for mobile dashboard using cache adapter with fallback."""
    try:
        # Use web cache adapter with automatic fallback to live data
        if web_cache:
            try:
                mobile_data = await web_cache.get_mobile_data()

                if mobile_data and mobile_data.get('data_source') != 'fallback':
                    logger.info(f"✅ Mobile data from shared cache: {len(mobile_data.get('confluence_scores', []))} confluence scores")

                    # Flatten structure for frontend compatibility
                    market_overview = mobile_data.get('market_overview', {})
                    mobile_data.update({
                        # Flatten market_overview fields to top level
                        "market_regime": market_overview.get("market_regime", "NEUTRAL"),
                        "regime": market_overview.get("market_regime", "NEUTRAL"),
                        "trend_strength": market_overview.get("trend_strength", 0),
                        "trend_score": market_overview.get("trend_strength", 0),
                        "current_volatility": market_overview.get("volatility", 0),
                        "btc_dominance": market_overview.get("btc_dominance", 0),
                        "total_volume_24h": market_overview.get("total_volume_24h", 0),
                        # Flatten top_movers to top level
                        "gainers": mobile_data.get("top_movers", {}).get("gainers", []),
                        "top_gainers": mobile_data.get("top_movers", {}).get("gainers", []),
                        "losers": mobile_data.get("top_movers", {}).get("losers", []),
                        # Add symbols array
                        "symbols": mobile_data.get('confluence_scores', []),
                        "top_symbols": mobile_data.get('confluence_scores', []),
                    })

                    return mobile_data

                logger.warning("Shared cache returned fallback data for mobile")
            except Exception as e:
                logger.error(f"Shared cache error in mobile data: {e}")

        # Fallback: Use direct cache adapter if web_cache not available
        if USE_DIRECT_CACHE:
            mobile_data = await direct_cache.get_mobile_data()
            logger.info(f"Mobile data from direct cache adapter")
            return mobile_data

        # Last resort: Return empty structure
        return {
            "status": "error",
            "error": "No cache adapter available",
            "market_overview": {
                "market_regime": "UNKNOWN",
                "trend_strength": 0,
                "volatility": 0,
                "btc_dominance": 0,
                "total_volume_24h": 0
            },
            "confluence_scores": [],
            "top_movers": {"gainers": [], "losers": []},
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in mobile dashboard endpoint: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
```

**Changes**:
1. Replace direct `aiomcache` access with `web_cache.get_mobile_data()`
2. Add fallback to `direct_cache.get_mobile_data()` if web_cache unavailable
3. Keep the flattening logic for frontend compatibility
4. Simplify error handling

#### Step 1.3: Remove redundant Bybit API code
The new implementation gets top movers from cache, which already includes live Bybit data via the monitoring system. Remove the duplicate Bybit API call (lines 950-1007).

---

### Phase 2: Testing (60 minutes)

#### Test 2.1: Local Testing
**Goal**: Verify the refactored endpoint works locally

```bash
# Start local services
PYTHONPATH=/Users/ffv_macmini/Desktop/Virtuoso_ccxt ./venv311/bin/python src/web_server.py

# Test mobile-data endpoint
curl http://localhost:8002/api/dashboard/mobile-data | jq .

# Verify response contains:
# - market_overview with non-zero values
# - confluence_scores array with data
# - top_movers with gainers/losers
```

**Success Criteria**:
- ✅ `trend_strength` > 0
- ✅ `btc_dominance` > 0
- ✅ `total_volume_24h` > 0
- ✅ `confluence_scores` has 10+ symbols
- ✅ Response time < 2 seconds

#### Test 2.2: Cache Fallback Testing
**Goal**: Verify fallback logic works when cache is empty

```bash
# Flush memcached to simulate cache miss
echo "flush_all" | nc localhost 11211

# Test endpoint
curl http://localhost:8002/api/dashboard/mobile-data | jq .

# Verify:
# - No errors/crashes
# - Falls back to live data fetch
# - Still returns valid data
```

#### Test 2.3: Load Testing
**Goal**: Verify performance is acceptable

```bash
# Simple load test
for i in {1..10}; do
  time curl -s http://localhost:8002/api/dashboard/mobile-data > /dev/null
done
```

**Success Criteria**:
- ✅ Average response time < 2 seconds
- ✅ No timeouts
- ✅ No memory leaks

---

### Phase 3: VPS Deployment (30 minutes)

#### Step 3.1: Create deployment script
**File**: `scripts/deploy_mobile_data_fix.sh`

```bash
#!/bin/bash
set -e

echo "================================================"
echo "Mobile Dashboard Data Fix Deployment"
echo "================================================"

VPS_HOST="5.223.63.4"
VPS_USER="linuxuser"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
BACKUP_DIR="backup_mobile_data_$(date +%Y%m%d_%H%M%S)"

echo "📦 Creating backup on VPS..."
ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PATH} && mkdir -p backups/${BACKUP_DIR} && cp src/api/routes/dashboard.py backups/${BACKUP_DIR}/"

echo "📤 Deploying fixed dashboard.py..."
rsync -avz --progress \
    src/api/routes/dashboard.py \
    ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/api/routes/

echo "🔄 Restarting web server on VPS..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl restart virtuoso_web"

echo "⏳ Waiting for services to start..."
sleep 10

echo "✅ Testing mobile-data endpoint on VPS..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://${VPS_HOST}:8002/api/dashboard/mobile-data)

if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ Mobile data endpoint responding: HTTP $HTTP_CODE"

    # Test for actual data
    curl -s http://${VPS_HOST}:8002/api/dashboard/mobile-data | jq '{
        market_regime: .market_regime,
        trend_strength: .trend_strength,
        btc_dominance: .btc_dominance,
        total_volume_24h: .total_volume_24h,
        confluence_count: (.confluence_scores | length),
        gainers_count: (.gainers | length),
        losers_count: (.losers | length),
        status: .status
    }'
else
    echo "❌ Mobile data endpoint error: HTTP $HTTP_CODE"
    echo "Rolling back..."
    ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PATH} && cp backups/${BACKUP_DIR}/dashboard.py src/api/routes/"
    ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl restart virtuoso_web"
    exit 1
fi

echo ""
echo "================================================"
echo "✅ Deployment Complete!"
echo "================================================"
echo "Mobile Dashboard: http://${VPS_HOST}:8002/mobile"
echo "API Endpoint: http://${VPS_HOST}:8002/api/dashboard/mobile-data"
echo "Backup Location: backups/${BACKUP_DIR}"
```

#### Step 3.2: Deploy to VPS
```bash
chmod +x scripts/deploy_mobile_data_fix.sh
./scripts/deploy_mobile_data_fix.sh
```

#### Step 3.3: Post-deployment validation
```bash
# Check mobile dashboard in browser
open http://5.223.63.4:8002/mobile

# Verify data displays:
# 1. Market Overview section shows real data
# 2. Confluence Scores section has 10+ symbols
# 3. Top Movers shows gainers/losers
# 4. No console errors in browser dev tools

# Check API response
curl http://5.223.63.4:8002/api/dashboard/mobile-data | jq . | head -50

# Check logs for errors
ssh linuxuser@5.223.63.4 "tail -f /home/linuxuser/trading/Virtuoso_ccxt/logs/web_server.log"
```

---

### Phase 4: Monitoring & Validation (15 minutes)

#### Validation Checklist
- [ ] Market Overview displays non-zero `trend_strength`
- [ ] Market Overview displays non-zero `btc_dominance`
- [ ] Market Overview displays non-zero `total_volume_24h`
- [ ] Confluence Scores section has 10+ symbols
- [ ] Each symbol has component breakdown scores
- [ ] Top Movers shows 5 gainers and 5 losers
- [ ] API response time < 2 seconds
- [ ] No errors in web server logs
- [ ] No console errors in browser
- [ ] Data updates when page is refreshed

#### Performance Metrics
Monitor these metrics for 24 hours:
- API response time (should be < 2s)
- Cache hit rate (should be > 80%)
- Error rate (should be 0%)
- Data freshness (timestamps should be recent)

---

## Rollback Plan

If issues occur after deployment:

### Immediate Rollback
```bash
ssh linuxuser@5.223.63.4
cd /home/linuxuser/trading/Virtuoso_ccxt
cp backups/backup_mobile_data_*/dashboard.py src/api/routes/
sudo systemctl restart virtuoso_web
```

### Verify Rollback
```bash
curl http://5.223.63.4:8002/api/dashboard/mobile-data
```

---

## Risk Assessment

### Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| web_cache not initialized on VPS | Low | High | Add fallback to direct_cache |
| Performance degradation | Low | Medium | Cache already optimized, monitor metrics |
| Breaking existing functionality | Very Low | High | Extensive local testing first |
| Frontend compatibility issues | Low | Medium | Keep flattened response structure |

---

## Success Criteria

### Functional Requirements
✅ Market Overview displays real-time data (non-zero values)
✅ Confluence Scores displays 10+ symbols with scores
✅ Top Movers displays gainers and losers
✅ Data updates when page refreshes

### Technical Requirements
✅ API response time < 2 seconds
✅ Cache hit rate > 80%
✅ No errors in logs
✅ Fallback logic works when cache is empty
✅ Works on both local and VPS environments

### Performance Requirements
✅ Throughput: 100+ requests/second
✅ Latency: p95 < 2 seconds
✅ Error rate: < 0.1%
✅ Cache efficiency: > 80% hit rate

---

## Key Files Modified

1. **`src/api/routes/dashboard.py`**
   - Line 831-1040: Refactor `/mobile-data` endpoint
   - Remove direct memcached access
   - Use `web_cache.get_mobile_data()` instead
   - Add fallback to `direct_cache.get_mobile_data()`

2. **`scripts/deploy_mobile_data_fix.sh`** (NEW)
   - Automated deployment script
   - Backup, deploy, restart, validate
   - Rollback on failure

---

## Dependencies

### Required Services
- ✅ Memcached (port 11211) - must be running
- ✅ Web server (port 8002) - will be restarted
- ✅ Monitoring system - should be populating cache

### Code Dependencies
- ✅ `WebServiceCacheAdapter` - already exists and working
- ✅ `DirectCacheAdapter` - fallback option
- ✅ Shared cache bridge - already initialized

---

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| **Phase 1: Code Changes** | 45 min | Not Started |
| - Verify web_cache availability | 10 min | Not Started |
| - Refactor mobile-data endpoint | 25 min | Not Started |
| - Remove redundant code | 10 min | Not Started |
| **Phase 2: Testing** | 60 min | Not Started |
| - Local testing | 30 min | Not Started |
| - Cache fallback testing | 15 min | Not Started |
| - Load testing | 15 min | Not Started |
| **Phase 3: VPS Deployment** | 30 min | Not Started |
| - Create deployment script | 15 min | Not Started |
| - Deploy and validate | 15 min | Not Started |
| **Phase 4: Monitoring** | 15 min | Not Started |
| **Total** | **2.5 hours** | Not Started |

---

## References

### Working Implementations
1. **`/api/market/overview` endpoint** (line 413, dashboard.py)
   - Uses `web_cache.get_market_overview()`
   - Proven to work on VPS

2. **`WebServiceCacheAdapter.get_mobile_data()`** (line 312, web_service_adapter.py)
   - Already implements the exact functionality we need
   - Has fallback logic, schema translation, error handling

3. **`DirectCacheAdapter.get_mobile_data()`** (line 721, cache_adapter_direct.py)
   - Alternative implementation with multi-tier caching
   - Can be used as fallback

### QA Agent Report
The QA validation agent identified:
- Root cause: Direct memcached access with schema mismatch
- Working solution: Cache adapter with fallback logic
- Recommended fix: Refactor to use web cache adapter pattern
- Estimated effort: 2-3 hours, low risk, high impact

---

## Next Steps

1. **Review this plan** - Verify approach and timeline
2. **Execute Phase 1** - Make code changes locally
3. **Execute Phase 2** - Test thoroughly on local environment
4. **Execute Phase 3** - Deploy to VPS
5. **Execute Phase 4** - Monitor and validate

---

## Notes

- The solution **reuses existing, proven code** rather than writing new code
- The WebServiceCacheAdapter is already used by `/market-overview` which works correctly
- The refactored endpoint will be **simpler and more maintainable** (~30 lines vs 210 lines)
- Performance should **improve** due to better caching strategy
- This fix will benefit other endpoints that may have similar issues

---

**Ready to proceed with implementation?**
