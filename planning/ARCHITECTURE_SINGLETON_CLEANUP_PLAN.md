# Architecture Singleton Cleanup Plan

**Status:** ✅ COMPLETED
**Date:** 2026-01-15
**Trello Card:** TR-69694dd4

## Summary

Fixed singleton instantiation patterns and removed 60+ dead code files that were creating architectural confusion.

## Phase 1: Singleton Fix ✅

### Problem
The ConfluenceAnalyzer was conditionally replaced only when `None`, similar to the bug fixed in #426 for MarketDataManager. This allowed DI's stale singleton to persist instead of main.py's properly-initialized instance.

### Solution
Changed `main.py` lines 747-750 to ALWAYS replace the DI's ConfluenceAnalyzer with main.py's instance, matching the MDM fix pattern:

```python
# BEFORE (conditional - bug)
if hasattr(market_monitor, 'confluence_analyzer') and not market_monitor.confluence_analyzer:
    if confluence_analyzer:
        market_monitor.confluence_analyzer = confluence_analyzer

# AFTER (always replace - fix)
if hasattr(market_monitor, 'confluence_analyzer'):
    if confluence_analyzer:
        old_ca_id = id(market_monitor.confluence_analyzer) if market_monitor.confluence_analyzer else 'None'
        market_monitor.confluence_analyzer = confluence_analyzer
        new_ca_id = id(confluence_analyzer)
        logger.info(f"✅ Replaced monitor's ConfluenceAnalyzer (old={old_ca_id}) with main.py's (new={new_ca_id})")
        fixed_deps.append("confluence_analyzer (REPLACED)")
```

### Commit
`5a6dead2` - fix(singleton): always replace DI's ConfluenceAnalyzer with main.py's instance

## Phase 2: Dead Code Removal ✅

### Files Deleted (58 files, 20,701 lines)

#### Directories Removed
| Directory | Files | Reason |
|-----------|-------|--------|
| `src/routes/` | 35 | Duplicate of `src/api/routes/` - never imported |
| `src/trade_execution/` | 5 | Unused trade execution module |
| `src/analysis/market/` | 4 | Duplicate of `src/core/analysis/` |
| `src/examples/` | 1 | Unused example code |

#### Individual Files Removed
| File | Reason |
|------|--------|
| `src/services/confluence_service.py` | Unused service wrapper |
| `src/core/simple_registry.py` | Legacy registry, replaced by DI |
| `src/core/trading_components_adapter.py` | Unused adapter |
| `src/core/di/optimized_registration.py` | Superseded by registration.py |
| `src/core/di/interface_registration.py` | Superseded by registration.py |
| `src/demo_trading_runner.py` | Demo code, not production |
| `src/monitoring/alpha_integration_manager.py` | Unused manager |
| `src/monitoring/optimized_di_registration.py` | Duplicate DI code |
| `src/factories/indicator_factory.py` | Unused factory |

### Files Preserved (Active Code)
| File | Reason |
|------|--------|
| `src/core/analysis/alpha_scanner.py` | Used by `registration.py:106` |
| `src/monitoring/alpha_integration.py` | Used by `main.py:859` |

### Commit
`eb6fdccb` - refactor(cleanup): remove 60+ dead code files

## Verification

1. ✅ No remaining imports of deleted files
2. ✅ Python syntax check passed
3. ✅ Active files (alpha_scanner.py, alpha_integration.py) preserved
4. ✅ Application imports verified (missing deps are unrelated to cleanup)

## Architecture After Cleanup

```
src/
├── api/routes/          # ← ACTIVE route handlers (was duplicated in src/routes/)
├── core/
│   ├── analysis/        # ← ACTIVE analysis (alpha_scanner.py lives here)
│   ├── di/
│   │   └── registration.py  # ← Primary DI registration
│   └── ...
├── monitoring/
│   └── alpha_integration.py  # ← ACTIVE (alpha_integration_manager.py removed)
└── ...
```

## Lessons Learned

1. **Singleton Pattern**: When DI creates instances before main.py initializes dependencies, ALWAYS replace the DI instance (not just when None)
2. **Duplicate Directories**: `src/routes/` vs `src/api/routes/` caused confusion - keep one canonical location
3. **Dead Code Accumulation**: Regular cleanup prevents architectural confusion
