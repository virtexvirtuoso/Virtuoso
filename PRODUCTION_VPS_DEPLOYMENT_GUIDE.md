# Virtuoso Trading System - Production VPS Deployment Guide

## Quick Start

This guide will deploy a complete production-ready monitoring system to your VPS including health monitoring, security hardening, automated backups, and email alerts.

## 🚀 One-Command Deployment

```bash
cd /Users/ffv_macmini/Desktop/Virtuoso_ccxt
chmod +x scripts/deployment/deploy_production_monitoring.sh
./scripts/deployment/deploy_production_monitoring.sh
```

## ✅ What Gets Deployed

### 1. **Health Monitoring System**
- Continuous monitoring of all Virtuoso services
- Email alerts when services fail
- System resource monitoring (disk, memory, CPU)
- Alert thresholds: Disk >80%, Memory >85%, CPU >90%

### 2. **Security Hardening**
- Fail2ban intrusion detection system
- SSH brute force protection
- Custom security filters for trading system logs
- Automated IP blocking for suspicious activity

### 3. **Automated Backup System**
- Daily backups at 2:00 AM (critical files, configs, databases)
- Weekly backups at 3:00 AM Sunday (full system)
- Automatic rotation: 7 days (daily), 4 weeks (weekly)
- Backup integrity verification and restoration tools

### 4. **Email Notification System**
- Postfix mail server for local delivery
- Alert notifications for all critical events
- Daily system status reports
- Optional external email forwarding

### 5. **Systemd Services**
- `virtuoso-health-monitor.service` - Service and resource monitoring
- `virtuoso-resource-monitor.service` - Continuous resource monitoring
- Auto-restart on failure, resource limits, security hardening

## 📋 Prerequisites

1. **VPS Access**: SSH key authentication to `linuxuser@45.77.40.77`
2. **Sudo Access**: linuxuser must have sudo privileges
3. **Network**: Local machine can reach VPS

## 🔧 Post-Deployment Verification

### 1. Check Service Status
```bash
ssh linuxuser@45.77.40.77
/home/linuxuser/trading/Virtuoso_ccxt/scripts/monitoring/monitor_control.sh status
```

### 2. Test Email Alerts
```bash
ssh linuxuser@45.77.40.77
echo "Test alert from monitoring system" | mail -s "Test Alert" linuxuser
```

### 3. View Monitoring Dashboard
```bash
ssh linuxuser@45.77.40.77
/home/linuxuser/trading/Virtuoso_ccxt/scripts/monitoring/monitoring_dashboard.py
```

### 4. Check Security Status
```bash
ssh linuxuser@45.77.40.77
sudo fail2ban-client status
python3 /home/linuxuser/trading/Virtuoso_ccxt/scripts/security/fail2ban_monitor.py summary
```

### 5. Verify Backup System
```bash
ssh linuxuser@45.77.40.77
python3 /home/linuxuser/trading/Virtuoso_ccxt/scripts/backup/automated_backup.py status
/home/linuxuser/trading/Virtuoso_ccxt/scripts/backup/verify_backups.sh
```

## 📊 Monitoring Features

### Real-Time Dashboard
Shows service status, system metrics, and recent alerts:
```bash
ssh linuxuser@45.77.40.77
/home/linuxuser/trading/Virtuoso_ccxt/scripts/monitoring/monitoring_dashboard.py
```

### Service Status
All Virtuoso services monitored:
- virtuoso.service (main trading system)
- virtuoso-web.service (web interface)
- virtuoso-cache.service (caching system)
- virtuoso-ticker.service (market data)

### Alert Thresholds
- **Disk Space**: >80% usage (critical at >90%)
- **Memory Usage**: >85% usage (critical at >95%)
- **CPU Usage**: >90% usage (critical at >95%)
- **Load Average**: >8.0 (critical at >16.0)
- **Service Down**: Any Virtuoso service stops

## 🔒 Security Features

### Fail2ban Protection
- **SSH**: 3 failures = 1 hour ban
- **SSH Aggressive**: 2 failures = 24 hour ban  
- **Port Scan**: 5 attempts = 24 hour ban
- **Trading System**: 5 failures = 30 minute ban

### SSH Hardening (Optional)
⚠️ **Important**: SSH hardening is NOT automatically applied for safety.
To apply SSH hardening:
```bash
ssh linuxuser@45.77.40.77
sudo /home/linuxuser/trading/Virtuoso_ccxt/scripts/security/harden_ssh.sh
```

**SSH Hardening Changes:**
- Disables root login
- Disables password authentication (key-based only)
- Restricts access to linuxuser only
- Strong encryption algorithms only

## 💾 Backup Schedule

### Automated Schedule
- **Daily**: 2:00 AM - Critical files, configs, databases
- **Weekly**: 3:00 AM Sunday - Full system backup
- **Cleanup**: 4:00 AM - Remove old backups
- **Health Check**: 9:00 AM - Verify backup system

### Manual Backup Operations
```bash
# Create manual backup
python3 /home/linuxuser/trading/Virtuoso_ccxt/scripts/backup/automated_backup.py daily

# List available backups  
/home/linuxuser/trading/Virtuoso_ccxt/scripts/backup/restore_backup.sh list

# Restore latest backup
/home/linuxuser/trading/Virtuoso_ccxt/scripts/backup/restore_backup.sh latest daily

# Check backup health
python3 /home/linuxuser/trading/Virtuoso_ccxt/scripts/backup/backup_health_check.py
```

## 📧 Email Configuration

### Local Email (Default)
- Emails delivered to: `/home/linuxuser/Maildir/`
- Read mail: `/home/linuxuser/trading/Virtuoso_ccxt/scripts/monitoring/read_mail.sh`

### External Email Forwarding (Optional)
To forward alerts to external email (Gmail, etc.):
```bash
ssh linuxuser@45.77.40.77
/home/linuxuser/trading/Virtuoso_ccxt/scripts/monitoring/setup_external_email.sh
```

## 🛠️ Management Commands

### Service Control
```bash
# Control monitoring services
/home/linuxuser/trading/Virtuoso_ccxt/scripts/monitoring/monitor_control.sh {start|stop|restart|status}

# Individual service control
sudo systemctl {start|stop|restart|status} virtuoso-health-monitor.service
sudo systemctl {start|stop|restart|status} virtuoso-resource-monitor.service
```

### Log Viewing
```bash
# Service logs
sudo journalctl -u virtuoso-health-monitor.service -f
sudo journalctl -u virtuoso-resource-monitor.service -f

# Application logs
tail -f /home/linuxuser/trading/Virtuoso_ccxt/logs/health_monitor.log
tail -f /home/linuxuser/trading/Virtuoso_ccxt/logs/resource_monitor.log

# Mail logs
sudo tail -f /var/log/mail.log

# Security logs  
sudo tail -f /var/log/fail2ban.log
```

## 🔍 Troubleshooting

### Common Issues

#### No Email Alerts
```bash
# Check postfix service
sudo systemctl status postfix

# Test local mail
echo "test" | mail -s "test" linuxuser

# Check mail logs
sudo tail -f /var/log/mail.log
```

#### Monitoring Service Issues
```bash
# Check service status
systemctl status virtuoso-health-monitor.service

# View service logs
journalctl -u virtuoso-health-monitor.service -n 50

# Restart services
sudo systemctl restart virtuoso-health-monitor.service
```

#### High Resource Alerts
```bash
# Check current usage
htop

# View monitoring data
python3 /home/linuxuser/trading/Virtuoso_ccxt/scripts/monitoring/resource_monitor.py --summary

# Check processes
ps aux --sort=-%cpu | head -10
```

### Emergency Commands

#### Stop All Monitoring
```bash
/home/linuxuser/trading/Virtuoso_ccxt/scripts/monitoring/monitor_control.sh stop
```

#### Clean Disk Space
```bash
# Clean logs
sudo journalctl --vacuum-time=7d

# Clean backups
python3 /home/linuxuser/trading/Virtuoso_ccxt/scripts/backup/automated_backup.py cleanup
```

#### Unban IP Address
```bash
/home/linuxuser/trading/Virtuoso_ccxt/scripts/security/emergency_unban.sh <IP_ADDRESS>
```

## 📈 Daily Operations

### Morning Checklist (5 minutes)
1. Check email for overnight alerts
2. View monitoring dashboard
3. Verify all services running
4. Review backup report (if any)

### Commands for Daily Check
```bash
ssh linuxuser@45.77.40.77

# Quick status check
/home/linuxuser/trading/Virtuoso_ccxt/scripts/monitoring/monitor_control.sh status

# View dashboard (optional)
/home/linuxuser/trading/Virtuoso_ccxt/scripts/monitoring/monitoring_dashboard.py

# Check for any security events
python3 /home/linuxuser/trading/Virtuoso_ccxt/scripts/security/fail2ban_monitor.py summary
```

## 📚 Documentation

- **Complete Documentation**: `/home/linuxuser/trading/Virtuoso_ccxt/docs/PRODUCTION_MONITORING_SYSTEM_DOCUMENTATION.md`
- **Deployment Report**: Generated after deployment with full details
- **Log Files**: `/home/linuxuser/trading/Virtuoso_ccxt/logs/`

## 🆘 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review service logs: `journalctl -u service-name`
3. Check application logs in `/home/linuxuser/trading/Virtuoso_ccxt/logs/`
4. Use monitoring dashboard for real-time status

---

## Summary

This deployment provides enterprise-grade monitoring, security, and backup capabilities for your trading system VPS. After deployment, your system will:

- ✅ **Monitor itself** and send email alerts for any issues
- ✅ **Protect against attacks** with fail2ban and security monitoring  
- ✅ **Backup data automatically** with rotation and verification
- ✅ **Run reliably** with systemd services and auto-restart
- ✅ **Provide visibility** with real-time dashboards and reporting

**Total deployment time**: ~15-20 minutes  
**Ongoing maintenance**: ~5 minutes daily for status check

Your VPS will now be production-ready with comprehensive monitoring and protection!