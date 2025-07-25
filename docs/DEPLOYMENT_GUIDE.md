# 🚀 Virtuoso Trading System - Deployment Guide

This guide covers everything you need to deploy the Virtuoso Trading System on a VPS or local server.

## 📋 Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Docker Deployment](#docker-deployment)
- [Manual Installation](#manual-installation)
- [Configuration](#configuration)
- [SSL/HTTPS Setup](#sslhttps-setup)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+ or Debian 10+ (recommended)
- **RAM**: Minimum 4GB, 8GB recommended
- **CPU**: 2+ cores
- **Storage**: 20GB+ free space
- **Network**: Stable internet connection

### Software Requirements
- Python 3.11+
- Git
- Docker & Docker Compose (for Docker deployment)
- Redis
- Nginx (for reverse proxy)

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/virtuoso-trading.git
cd virtuoso-trading

# 2. Prepare environment
./scripts/deployment/prepare_env.sh

# 3. Deploy with Docker (recommended)
./scripts/deployment/deploy_docker.sh

# OR deploy manually
sudo ./scripts/deployment/deploy_vps.sh
```

## Docker Deployment

### 1. Install Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

### 2. Prepare Environment

```bash
# Run the environment setup script
./scripts/deployment/prepare_env.sh

# Or manually edit .env
cp .env.example .env
nano .env  # Edit with your credentials
```

### 3. Deploy with Docker

```bash
# Basic deployment (App + Redis)
./scripts/deployment/deploy_docker.sh --basic

# Full deployment (App + Redis + InfluxDB)
./scripts/deployment/deploy_docker.sh --full

# Interactive menu
./scripts/deployment/deploy_docker.sh
```

### 4. Docker Commands

```bash
# View logs
docker logs -f virtuoso-trading

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Update and redeploy
git pull
docker-compose build --no-cache
docker-compose up -d

# Access container shell
docker exec -it virtuoso-trading bash
```

## Manual Installation

### 1. Run Installation Script

```bash
# Must run as root
sudo ./scripts/deployment/deploy_vps.sh
```

This script will:
- Install all system dependencies
- Create a service user
- Setup Python environment
- Configure firewall
- Setup systemd service
- Configure Nginx reverse proxy
- Setup log rotation

### 2. Post-Installation

```bash
# Edit configuration
sudo nano /opt/virtuoso-trading/.env

# Restart service
sudo systemctl restart virtuoso-trading

# Check status
sudo systemctl status virtuoso-trading

# View logs
sudo journalctl -u virtuoso-trading -f
```

## Configuration

### Essential Environment Variables

```bash
# Exchange API (Required for trading)
BYBIT_API_KEY=your_api_key_here
BYBIT_API_SECRET=your_api_secret_here

# Discord Notifications (Optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Database (Required)
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_secure_token_here
INFLUXDB_ORG=virtuoso
INFLUXDB_BUCKET=market_data

# Security
JWT_SECRET_KEY=your_secure_jwt_secret_here

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
```

### Port Configuration

| Service | Port | Description |
|---------|------|-------------|
| FastAPI Main | 8000 | Main application |
| API Endpoints | 8001 | REST API |
| Dashboard | 8003 | Web dashboard |
| InfluxDB | 8086 | Time-series database |
| Redis | 6379 | Cache (internal) |

## SSL/HTTPS Setup

### Using Let's Encrypt (Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
sudo certbot renew --dry-run  # Test renewal
```

### Update Nginx Configuration

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # ... rest of configuration
}
```

## Monitoring

### Health Checks

```bash
# Check service health
curl http://localhost:8001/health

# Check all services (Docker)
docker ps

# System metrics
htop
```

### Log Monitoring

```bash
# Application logs
tail -f /opt/virtuoso-trading/logs/virtuoso.log

# Docker logs
docker logs -f virtuoso-trading --tail=100

# System logs
sudo journalctl -u virtuoso-trading -f
```

### Automated Monitoring

A basic health check is configured to run every 5 minutes:
```bash
# View health check cron
crontab -l

# Manual health check
/usr/local/bin/virtuoso-health-check
```

## Troubleshooting

### Common Issues

#### 1. Service Won't Start
```bash
# Check logs
sudo journalctl -u virtuoso-trading -n 100

# Check permissions
ls -la /opt/virtuoso-trading/

# Test configuration
cd /opt/virtuoso-trading
source venv/bin/activate
python -m src.main --test
```

#### 2. Port Already in Use
```bash
# Find process using port
sudo lsof -i :8001

# Kill process
sudo kill -9 <PID>
```

#### 3. Database Connection Issues
```bash
# Test Redis
redis-cli ping

# Test InfluxDB
curl http://localhost:8086/health
```

#### 4. Docker Issues
```bash
# Clean up Docker
docker system prune -a

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Debug Mode

```bash
# Enable debug mode temporarily
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run manually
python -m src.main
```

## Maintenance

### Regular Tasks

#### Daily
- Monitor logs for errors
- Check disk space: `df -h`
- Verify services are running

#### Weekly
- Review performance metrics
- Clean old logs/reports
- Update dependencies

#### Monthly
- Security updates: `sudo apt update && sudo apt upgrade`
- Backup configuration and data
- Review and rotate API keys

### Backup

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="/backup/virtuoso-$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup configuration
cp /opt/virtuoso-trading/.env $BACKUP_DIR/
cp -r /opt/virtuoso-trading/config $BACKUP_DIR/

# Backup data
cp -r /opt/virtuoso-trading/data $BACKUP_DIR/
cp -r /opt/virtuoso-trading/reports $BACKUP_DIR/

# Compress
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR
```

### Updates

```bash
# Docker deployment
cd /opt/virtuoso-trading
git pull
docker-compose build --no-cache
docker-compose up -d

# Manual deployment
cd /opt/virtuoso-trading
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart virtuoso-trading
```

## Security Best Practices

1. **Never commit .env files** to version control
2. **Use strong, unique passwords** for all services
3. **Enable firewall** and only open required ports
4. **Keep system updated** with security patches
5. **Use SSL/HTTPS** for all external connections
6. **Rotate API keys** regularly
7. **Monitor logs** for suspicious activity
8. **Backup regularly** and test restore procedures

## Support

### Getting Help

1. Check logs first - they often contain the solution
2. Review this guide and ensure all steps were followed
3. Search existing issues on GitHub
4. Create a new issue with:
   - System information
   - Error messages
   - Steps to reproduce

### Useful Resources

- [Project Documentation](./docs/)
- [API Documentation](./docs/api/)
- [Configuration Reference](./docs/configuration.md)
- [Troubleshooting Guide](./docs/troubleshooting.md)

---

## Quick Reference Card

```bash
# Service Management
sudo systemctl start virtuoso-trading
sudo systemctl stop virtuoso-trading
sudo systemctl restart virtuoso-trading
sudo systemctl status virtuoso-trading

# Docker Commands
docker-compose up -d          # Start
docker-compose down           # Stop
docker-compose logs -f        # Logs
docker-compose restart        # Restart

# Logs
tail -f logs/virtuoso.log     # App logs
journalctl -u virtuoso-trading -f  # System logs

# Health Check
curl http://localhost:8001/health
```

Remember: **Always backup your .env file and keep your credentials secure!** 🔒