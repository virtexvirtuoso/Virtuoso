# VT Control Panel Version 5.0 - Final Setup

**Version**: 5.0 (Production)  
**Date**: August 28, 2025  
**Status**: ✅ Deployed on both Vultr and Hetzner  

## 📋 Overview

Version 5.0 is the production control panel for Virtuoso Trading System, featuring:
- Interactive menu with 25 options
- Detailed Python process monitoring  
- Exchange connection status with ping times
- Database and cache monitoring
- Trading services status tracking
- Quick action commands

## 🚀 Current Deployment

### Hetzner VPS (Primary - VPS_HOST_REDACTED)
- **Control Script**: `/home/linuxuser/virtuoso_control.sh`
- **VT Command**: `/home/linuxuser/bin/vt`
- **Interactive**: `/home/linuxuser/virtuoso_control_interactive.sh`
- **Status**: ✅ Active and running

### Vultr VPS (Backup - 45.77.40.77)  
- **Control Script**: `/home/linuxuser/virtuoso_control.sh`
- **VT Command**: `/usr/local/bin/vt` (lightweight version)
- **Interactive**: `/home/linuxuser/virtuoso_control_interactive.sh`
- **Status**: ✅ Active (but CPU throttled)

## 📁 File Structure

### Production Files (Keep These)
```
scripts/
├── setup_vps_service_control_v5.sh    # V5 deployment script
└── vt_command_v5.sh                   # Documentation of vt command
```

### Deleted Files (To Avoid Confusion)
- ❌ setup_vps_service_control.sh (v1)
- ❌ setup_vps_service_control_v2.sh  
- ❌ setup_vps_service_control_v3.sh
- ❌ fix_and_enhance_control.sh
- ❌ merge_control_interfaces.sh
- ❌ setup_interactive_control.sh
- ❌ setup_unified_control.sh

## 💻 Usage

### Interactive Menu (Default)
```bash
vt
# Shows the full interactive menu with 25 options
```

### Quick Commands
```bash
vt status    # Full status panel
vt start     # Start all services
vt stop      # Stop all services  
vt restart   # Restart all services
vt logs      # View live logs
vt health    # Health check
```

### Interactive Menu Options
1. Enable/disable auto-start
2. Toggle web server
3. Start/stop services
4. View logs
5. Health checks
6. Clean temp files
7. Kill processes
8. System info
9. Network tests
10. Backup config
11. Force sync exchanges
12. Clear caches
13. Test API connections
14. Export logs
15. Emergency stop
...and more

## 🎯 Key Features

### Process Monitoring
- Shows each Python process with:
  - Process name/type
  - PID
  - CPU usage (color-coded)
  - Memory usage
  - Virtuoso process detection

### Exchange Status
- Bybit connection with ping
- Binance connection with ping  
- WebSocket status
- Connection quality indicators

### Cache & Database
- Redis status and key count
- File cache status
- Log storage sizes
- Backup timestamps

### Trading Services
- Bitcoin Beta modules
- Market metrics
- Ticker cache
- Cache monitor
- All service statuses

## 🔧 Configuration

### Dashboard URL
The control panel shows dashboard URL based on server IP:
- Hetzner: `http://VPS_HOST_REDACTED:8001/dashboard`
- Vultr: `http://45.77.40.77:8001/dashboard`

### Auto-Start Settings
- Main service boot auto-start
- Web server auto-start with main
- Configurable via menu options

### Maintenance Schedule  
- Daily restart at 3:00 AM SGT
- Cron job configuration
- Last restart tracking

## 📝 Important Notes

1. **Version 5.0 is the ONLY version to use**
2. All older versions have been deleted
3. The interactive menu appears when running `vt` without arguments
4. Process monitoring shows detailed Python process info
5. Exchange pings are real-time measurements

## 🚨 Troubleshooting

If the menu doesn't appear:
```bash
# Check if script exists
ls -la /home/linuxuser/virtuoso_control.sh

# Run directly
/home/linuxuser/virtuoso_control.sh

# Check vt command
which vt
cat /home/linuxuser/bin/vt
```

## 🔄 Updates

To update the control script on any server:
```bash
# From local machine
scp scripts/setup_vps_service_control_v5.sh vps:/home/linuxuser/virtuoso_control.sh

# Update IP addresses if needed
ssh vps "sed -i 's/OLD_IP/NEW_IP/g' /home/linuxuser/virtuoso_control.sh"
```

---

**Version Control**: Only Version 5.0 exists. All previous versions deleted on August 28, 2025.