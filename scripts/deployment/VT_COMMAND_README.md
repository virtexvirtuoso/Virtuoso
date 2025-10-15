# VT Command - Virtuoso Trading System Control

## Current Active Script
- **vt_latest.sh** (72KB, updated Sept 18, 2025)
  - Location: `/home/linuxuser/trading/Virtuoso_ccxt/scripts/deployment/vt_latest.sh`
  - Symlink: `/usr/local/bin/vt` → `vt_latest.sh`
  - Status: **ACTIVE** ✅

## Usage
```bash
vt              # Interactive control panel with menu
vt status       # Complete system status report
vt health       # Run comprehensive health check
vt start        # Start all services
vt stop         # Stop all services
vt restart      # Restart all services
vt logs         # View service logs
```

## Deprecated Scripts
The following scripts are **DEPRECATED** and should not be used:

- **vt_command_v5.sh** (4KB, Aug 28, 2024) - Replaced by vt_latest.sh
  - Location: `/home/linuxuser/trading/Virtuoso_ccxt/vt_command_v5.sh`
  - Status: **DEPRECATED** ⚠️
  - Action: Shows deprecation notice and exits

- **vt** (2KB, Aug 27, 2024) - Old minimal version
  - Location: `/home/linuxuser/trading/Virtuoso_ccxt/scripts/deployment/vt`
  - Status: **DEPRECATED** ⚠️

## Deployment Notes
When deploying updates to vt_latest.sh:

1. Upload new version to `scripts/deployment/vt_latest.sh`
2. Set execute permissions: `chmod +x scripts/deployment/vt_latest.sh`
3. Symlink is already configured, no changes needed
4. Test with: `vt status`

## Symlink Configuration
The global command is configured as:
```bash
/usr/local/bin/vt → /home/linuxuser/trading/Virtuoso_ccxt/scripts/deployment/vt_latest.sh
```

This allows the `vt` command to work from anywhere on the system.

## Version History
- **v5.0** (Sept 18, 2025) - vt_latest.sh - Enhanced monitoring, visual dashboard
- **v5.0** (Aug 28, 2024) - vt_command_v5.sh - Basic functionality (deprecated)
- **v4.x** (Aug 27, 2024) - vt - Minimal version (deprecated)

## Maintenance
- Keep only `vt_latest.sh` executable
- Old versions kept in archive for reference
- Update this README when releasing new versions
