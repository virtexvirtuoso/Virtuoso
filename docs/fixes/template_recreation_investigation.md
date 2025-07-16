# Template Recreation Investigation and Fix

## Problem Summary

The file `templates/market_report_dark.html` was being automatically recreated after deletion, indicating an active process was monitoring and restoring it.

## Investigation Process

### 1. Initial Monitoring
- Created a monitoring script that detected the template being recreated after ~57 seconds
- File was recreated with exact same size (37548 bytes), suggesting copying from another location

### 2. Code Analysis
Identified several problematic references:
- `src/monitoring/market_reporter.py` - Fixed fallback logic
- `tests/reporting/test_market_report.py` - Fixed template path
- `src/core/reporting/pdf_generator.py` - **Root cause identified**

### 3. Root Cause Discovery

The real issue was in `src/core/reporting/pdf_generator.py` line 207:
```python
possible_dirs = [
    os.path.join(os.getcwd(), "src", "core", "reporting", "templates"),
    os.path.join(os.getcwd(), "templates"),  # THIS WAS THE PROBLEM
    # ... other fallback directories
]
```

Combined with the fact that `templates/` is a **symlink** to `src/core/reporting/templates/`:
```bash
$ ls -la | grep templates
lrwxr-xr-x@ 1 ffv_macmini staff 28 May 23 23:38 templates -> src/core/reporting/templates
```

### 4. The Recreation Mechanism

1. PDF Generator initializes and checks `possible_dirs` for templates
2. When it finds `templates/` directory (symlink), it treats it as a valid template source
3. Any template loading/discovery logic would see both locations as valid
4. If template copying or validation occurs, it writes to the canonical location
5. Due to the symlink, changes appear in both `templates/` and `src/core/reporting/templates/`

## The Fix

### Code Changes
Removed the problematic fallback from PDF generator:
```python
# In src/core/reporting/pdf_generator.py, line ~207
possible_dirs = [
    os.path.join(os.getcwd(), "src", "core", "reporting", "templates"),
    # Removed: os.path.join(os.getcwd(), "templates"),  # Prevented symlink conflicts
    # ... other fallback directories
]
```

### Verification
1. ✅ Template removal no longer triggers recreation
2. ✅ PDF Generator still finds templates correctly
3. ✅ Template directory points to canonical location
4. ✅ Symlink structure preserved for backward compatibility

## Previous Fixes Applied

1. **Market Reporter fallback logic** - Removed fallback to root `templates/` directory
2. **Test file template paths** - Updated to use canonical location  
3. **Backup file corrections** - Updated 5 backup files with correct paths

## Final Status

- ✅ Template recreation issue **SOLVED**
- ✅ All components use canonical template location (`src/core/reporting/templates/`)
- ✅ Symlink preserved for backward compatibility
- ✅ No active processes recreating templates
- ✅ Both HTML and PDF generation working correctly

## Architecture

```
templates/ (symlink) -> src/core/reporting/templates/ (canonical)
                           │
                           ├── market_report_dark.html
                           ├── trading_report_dark.html
                           ├── pdf_signal_template.html
                           └── signal_report_template.html
```

## Testing

The fix was verified by:
1. Removing the template and confirming no recreation occurs
2. Testing PDF generator initialization and template discovery
3. Verifying symlink functionality is preserved
4. Confirming all components can access templates through canonical location

**Result: Template recreation issue completely resolved.** 