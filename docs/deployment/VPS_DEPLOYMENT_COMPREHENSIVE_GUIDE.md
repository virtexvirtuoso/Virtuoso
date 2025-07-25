# Virtuoso Trading Bot - Comprehensive VPS Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [VPS Requirements](#vps-requirements)
3. [Initial VPS Setup](#initial-vps-setup)
4. [Transferring Files](#transferring-files)
5. [Application Setup](#application-setup)
6. [Security Configuration](#security-configuration)
7. [Running the Application](#running-the-application)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)
9. [Troubleshooting](#troubleshooting)
10. [Performance Optimization](#performance-optimization)

## Prerequisites

### Local Machine
- Git repository with latest code
- `.rsync-exclude` file configured
- SSH key pair generated
- API keys and credentials ready

### VPS Access
- Root or sudo access to VPS
- SSH access configured
- Domain name (optional)

## VPS Requirements

### Minimum Specifications
- **CPU**: 2 vCPUs (4 recommended)
- **RAM**: 4GB (8GB recommended)
- **Storage**: 20GB SSD (50GB recommended)
- **Network**: 100Mbps (1Gbps preferred)
- **OS**: Ubuntu 22.04 LTS or Debian 11

### Recommended Providers
- Vultr (current: 45.77.40.77)
- DigitalOcean
- Linode
- AWS EC2
- Google Cloud Platform

## Initial VPS Setup

### 1. Connect to VPS
```bash
ssh root@YOUR_VPS_IP
```

### 2. Update System
```bash
apt update && apt upgrade -y
apt install -y build-essential curl wget git htop tmux
```

### 3. Create Non-Root User
```bash
# Create user
adduser linuxuser

# Grant sudo privileges
usermod -aG sudo linuxuser

# Switch to new user
su - linuxuser
```

### 4. Configure SSH for Security
```bash
# As linuxuser, create SSH directory
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# On your local machine, copy your SSH key
ssh-copy-id linuxuser@YOUR_VPS_IP

# On VPS, configure SSH
sudo nano /etc/ssh/sshd_config
```

Add/modify these settings:
```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

Restart SSH:
```bash
sudo systemctl restart sshd
```

### 5. Install Python 3.11
```bash
# Add deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils

# Install pip
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Verify installation
python3.11 --version
pip3.11 --version
```

### 6. Install System Dependencies
```bash
# Required for Python packages
sudo apt install -y \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    libldap2-dev \
    libsasl2-dev \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    libssl-dev

# Optional but recommended
sudo apt install -y \
    redis-server \
    postgresql \
    nginx \
    certbot \
    python3-certbot-nginx
```

## Transferring Files

### 1. Prepare Transfer (Local Machine)
```bash
# Navigate to project directory
cd /path/to/Virtuoso_ccxt

# Check what will be transferred
rsync -an --stats --exclude-from='.rsync-exclude' ./ linuxuser@YOUR_VPS_IP:~/trading/Virtuoso_ccxt/ | grep 'Total file size'
```

### 2. Transfer Files
```bash
# Using rsync (recommended)
rsync -avzP --exclude-from='.rsync-exclude' ./ linuxuser@YOUR_VPS_IP:~/trading/Virtuoso_ccxt/

# Alternative: Using tar
tar -czf virtuoso-optimized.tar.gz --exclude-from='.rsync-exclude' .
scp virtuoso-optimized.tar.gz linuxuser@YOUR_VPS_IP:~/
```

### 3. On VPS - Extract and Setup
```bash
# If using tar
mkdir -p ~/trading
cd ~/trading
tar -xzf ~/virtuoso-optimized.tar.gz
rm ~/virtuoso-optimized.tar.gz

# Create necessary directories
cd ~/trading/Virtuoso_ccxt
mkdir -p logs exports reports cache src/logs src/exports src/reports
mkdir -p exports/confluence_visualizations exports/market_reports/json
mkdir -p exports/bitcoin_beta_reports/png_exports
```

## Application Setup

### 1. Create Virtual Environment
```bash
cd ~/trading/Virtuoso_ccxt
python3.11 -m venv venv311
source venv311/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### 2. Install Dependencies
```bash
# Install main requirements
pip install -r requirements.txt

# If you have GPU support
# pip install -r requirements-gpu.txt
```

### 3. Configure Environment Variables
```bash
# Copy example env file
cp .env.example .env

# Edit with your credentials
nano .env
```

Required environment variables:
```env
# Exchange API Keys
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret
BYBIT_TESTNET=false

# Discord Webhook (optional)
DISCORD_WEBHOOK_URL=your_webhook_url

# Database
DATABASE_URL=sqlite:///trading.db

# Application Settings
ENV=production
DEBUG=false
LOG_LEVEL=INFO
```

### 4. Initialize Database
```bash
# Run database migrations if available
python scripts/init_database.py

# Or create tables manually
python -c "from src.database import init_db; init_db()"
```

## Security Configuration

### 1. Firewall Setup
```bash
# Install UFW
sudo apt install -y ufw

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8001/tcp  # API port
sudo ufw allow 8002/tcp  # WebSocket port
sudo ufw allow 8003/tcp  # Dashboard port

# Enable firewall
sudo ufw enable
```

### 2. Fail2ban Setup
```bash
# Install fail2ban
sudo apt install -y fail2ban

# Configure for SSH protection
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 3. SSL Certificate (if using domain)
```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com
```

## Running the Application

### 1. Using tmux (Recommended)
```bash
# Create new tmux session
tmux new -s virtuoso

# Inside tmux, activate venv and run
source venv311/bin/activate
python src/main.py

# Detach from tmux: Ctrl+B, then D
# Reattach: tmux attach -t virtuoso
```

### 2. Using systemd Service
Create service file:
```bash
sudo nano /etc/systemd/system/virtuoso.service
```

Content:
```ini
[Unit]
Description=Virtuoso Trading Bot
After=network.target

[Service]
Type=simple
User=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
Environment="PATH=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin"
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable virtuoso
sudo systemctl start virtuoso
sudo systemctl status virtuoso
```

### 3. Using Docker (Alternative)
```bash
# Build image
docker build -t virtuoso-trading .

# Run container
docker run -d \
  --name virtuoso \
  --restart unless-stopped \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/exports:/app/exports \
  -v $(pwd)/reports:/app/reports \
  --env-file .env \
  virtuoso-trading
```

## Monitoring and Maintenance

### 1. Log Monitoring
```bash
# View real-time logs
tail -f logs/market_reporter.log

# Check for errors
grep -i error logs/*.log | tail -20

# Monitor system resources
htop
```

### 2. Log Rotation
Create logrotate config:
```bash
sudo nano /etc/logrotate.d/virtuoso
```

Content:
```
/home/linuxuser/trading/Virtuoso_ccxt/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 linuxuser linuxuser
}
```

### 3. Backup Strategy
Create backup script:
```bash
nano ~/backup_virtuoso.sh
```

Content:
```bash
#!/bin/bash
BACKUP_DIR="/home/linuxuser/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
cp ~/trading/Virtuoso_ccxt/trading.db $BACKUP_DIR/trading_$DATE.db

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
  ~/trading/Virtuoso_ccxt/config \
  ~/trading/Virtuoso_ccxt/.env

# Keep only last 7 days
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

Make executable and add to cron:
```bash
chmod +x ~/backup_virtuoso.sh
crontab -e
# Add: 0 2 * * * /home/linuxuser/backup_virtuoso.sh
```

### 4. Monitoring Endpoints
```bash
# Health check
curl http://localhost:8001/health

# Metrics
curl http://localhost:8001/metrics

# System status
curl http://localhost:8001/api/system/status
```

## Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Add project to PYTHONPATH
export PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt:$PYTHONPATH
```

#### 2. Permission Errors
```bash
# Fix ownership
sudo chown -R linuxuser:linuxuser ~/trading/Virtuoso_ccxt

# Fix permissions
chmod -R 755 ~/trading/Virtuoso_ccxt
chmod 600 ~/trading/Virtuoso_ccxt/.env
```

#### 3. Memory Issues
```bash
# Check memory usage
free -h

# Add swap if needed
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 4. Connection Issues
```bash
# Check firewall
sudo ufw status

# Test API connectivity
curl -X GET https://api.bybit.com/v5/market/time

# Check DNS
nslookup api.bybit.com
```

### Debug Mode
```bash
# Run with debug logging
LOG_LEVEL=DEBUG python src/main.py

# Run specific component
python -m src.monitoring.market_reporter

# Test configuration
python scripts/test_config.py
```

## Performance Optimization

### 1. Python Optimization
```bash
# Enable Python optimizations
export PYTHONOPTIMIZE=1

# Use PyPy (optional)
pypy3 -m venv venv_pypy
source venv_pypy/bin/activate
pip install -r requirements.txt
```

### 2. System Tuning
```bash
# Increase file descriptors
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimize network settings
sudo sysctl -w net.core.rmem_max=134217728
sudo sysctl -w net.core.wmem_max=134217728
```

### 3. Redis Caching
```bash
# Configure Redis
sudo nano /etc/redis/redis.conf
# Set: maxmemory 1gb
# Set: maxmemory-policy allkeys-lru

sudo systemctl restart redis
```

### 4. Process Management
```bash
# Use supervisor for process management
sudo apt install -y supervisor

# Create config
sudo nano /etc/supervisor/conf.d/virtuoso.conf
```

Content:
```ini
[program:virtuoso]
command=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python src/main.py
directory=/home/linuxuser/trading/Virtuoso_ccxt
user=linuxuser
autostart=true
autorestart=true
stderr_logfile=/var/log/virtuoso.err.log
stdout_logfile=/var/log/virtuoso.out.log
```

## Update Procedure

### 1. Backup Current Version
```bash
cd ~/trading
tar -czf virtuoso_backup_$(date +%Y%m%d).tar.gz Virtuoso_ccxt/
```

### 2. Pull Updates
```bash
cd ~/trading/Virtuoso_ccxt
git pull origin main

# Or use rsync from local
rsync -avzP --exclude-from='.rsync-exclude' user@local:~/Virtuoso_ccxt/ ./
```

### 3. Update Dependencies
```bash
source venv311/bin/activate
pip install -r requirements.txt --upgrade
```

### 4. Restart Application
```bash
sudo systemctl restart virtuoso
# Or
tmux attach -t virtuoso
# Ctrl+C to stop, then restart
```

## Maintenance Checklist

### Daily
- [ ] Check application logs for errors
- [ ] Monitor disk usage (`df -h`)
- [ ] Verify API connectivity
- [ ] Check system resources (`htop`)

### Weekly
- [ ] Review and clean old logs
- [ ] Check for security updates
- [ ] Analyze performance metrics
- [ ] Backup database and configuration

### Monthly
- [ ] Update system packages
- [ ] Review firewall rules
- [ ] Audit user access
- [ ] Test backup restoration
- [ ] Review resource usage trends

## Additional Resources

- [Virtuoso Documentation](../README.md)
- [API Documentation](../api/README.md)
- [Troubleshooting Guide](../TROUBLESHOOTING.md)
- [Performance Tuning](../PERFORMANCE.md)

---

*Last Updated: January 2025*