# 🚀 Vultr VPS Deployment Implementation Plan

## 📋 Overview
Complete step-by-step guide to deploy Virtuoso_ccxt trading bot on Vultr VPS in Singapore for optimal Bybit trading performance.

**Estimated Time**: 2-3 hours  
**Difficulty**: Intermediate  
**Cost**: $24/month (4GB RAM plan)

---

## 📊 Pre-Deployment Checklist

- [ ] Vultr account created
- [ ] Payment method added
- [ ] GitHub repository accessible
- [ ] Environment variables documented
- [ ] API keys ready (Bybit, Discord webhooks, etc.)
- [ ] SSH key pair generated (optional but recommended)

---

## Phase 1: Vultr Setup (15 minutes)

### 1.1 Create VPS Instance

1. **Login to Vultr Dashboard**
   ```
   https://my.vultr.com/
   ```

2. **Deploy New Instance**
   - Click "Deploy New Instance" or "+" button
   - Choose: **Cloud Compute → Regular Performance**

3. **Configuration**
   ```yaml
   Type: Cloud Compute (Regular)
   Location: Singapore
   OS: Ubuntu 22.04 LTS
   Plan: 4GB RAM, 2 vCPU, 80GB SSD ($24/month)
   Additional Features:
     - ✅ Enable IPv6
     - ✅ Auto Backups ($4.80/month - recommended)
     - ✅ DDoS Protection (free)
   ```

4. **SSH Key Setup** (Recommended)
   ```bash
   # On your local machine
   ssh-keygen -t ed25519 -C "your-email@example.com"
   # Copy public key content
   cat ~/.ssh/id_ed25519.pub
   ```
   - Add SSH key in Vultr dashboard during setup

5. **Server Hostname**
   ```
   virtuoso-trading-bot
   ```

6. **Deploy Now**
   - Wait 60 seconds for deployment
   - Note down IP address

### 1.2 Initial Connection

```bash
# Connect to your VPS
ssh root@YOUR_VPS_IP

# Or if using SSH key
ssh -i ~/.ssh/id_ed25519 root@YOUR_VPS_IP
```

---

## Phase 2: System Setup (30 minutes)

### 2.1 Create Setup Script

```bash
# On VPS, create setup script
cat > ~/setup-trading-bot.sh << 'EOF'
#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting Virtuoso Trading Bot Setup...${NC}"

# Update system
echo -e "${YELLOW}Updating system packages...${NC}"
apt update && apt upgrade -y

# Install Python 3.11
echo -e "${YELLOW}Installing Python 3.11...${NC}"
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils

# Install system dependencies
echo -e "${YELLOW}Installing system dependencies...${NC}"
apt install -y \
    build-essential \
    git \
    curl \
    wget \
    htop \
    tmux \
    redis-server \
    postgresql \
    postgresql-contrib \
    nginx \
    supervisor \
    ufw \
    fail2ban \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info

# Install TA-Lib
echo -e "${YELLOW}Installing TA-Lib...${NC}"
cd /tmp
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
make install
cd ~

# Install Docker (optional)
echo -e "${YELLOW}Installing Docker...${NC}"
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker root

# Setup firewall
echo -e "${YELLOW}Configuring firewall...${NC}"
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 8003/tcp  # Trading bot API
ufw --force enable

# Create trading user
echo -e "${YELLOW}Creating trading user...${NC}"
useradd -m -s /bin/bash trader
usermod -aG sudo trader

# Setup directories
mkdir -p /home/trader/logs
mkdir -p /home/trader/data
mkdir -p /home/trader/backups
chown -R trader:trader /home/trader/

# Install monitoring
echo -e "${YELLOW}Installing monitoring tools...${NC}"
wget -O /tmp/netdata-kickstart.sh https://my-netdata.io/kickstart.sh
bash /tmp/netdata-kickstart.sh --dont-wait

echo -e "${GREEN}System setup complete!${NC}"
EOF

chmod +x ~/setup-trading-bot.sh
```

### 2.2 Run System Setup

```bash
# Execute setup script
./setup-trading-bot.sh

# This will take 10-15 minutes
```

---

## Phase 3: Application Deployment (45 minutes)

### 3.1 Clone Repository

```bash
# Switch to trader user
su - trader

# Clone your repository
git clone https://github.com/YOUR_USERNAME/Virtuoso_ccxt.git
cd Virtuoso_ccxt

# Or use SSH if you have deploy keys
git clone git@github.com:YOUR_USERNAME/Virtuoso_ccxt.git
```

### 3.2 Python Environment Setup

```bash
# Create virtual environment
python3.11 -m venv venv311

# Activate environment
source venv311/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install Python dependencies
pip install -r requirements.txt

# Verify TA-Lib installation
python -c "import talib; print('TA-Lib version:', talib.__version__)"
```

### 3.3 Configuration Setup

```bash
# Create .env file
cat > .env << 'EOF'
# Exchange API Keys
BYBIT_API_KEY=your_api_key_here
BYBIT_API_SECRET=your_api_secret_here
BYBIT_TESTNET=false

# Discord Webhooks
DISCORD_WEBHOOK_URL=your_webhook_url_here
DISCORD_ALERT_WEBHOOK_URL=your_alert_webhook_url_here

# Database
DATABASE_URL=postgresql://trader:password@localhost/trading_db

# Redis
REDIS_URL=redis://localhost:6379

# API Settings
API_HOST=0.0.0.0
API_PORT=8003

# Environment
ENVIRONMENT=production
DEBUG=false
EOF

# Set proper permissions
chmod 600 .env
```

### 3.4 Database Setup (if using PostgreSQL)

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL prompt:
CREATE DATABASE trading_db;
CREATE USER trader WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE trading_db TO trader;
\q

# Test connection
psql -U trader -d trading_db -h localhost
```

---

## Phase 4: Process Management (30 minutes)

### 4.1 Create Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/trading-bot.service
```

```ini
[Unit]
Description=Virtuoso Trading Bot
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=trader
WorkingDirectory=/home/trader/Virtuoso_ccxt
Environment="PATH=/home/trader/Virtuoso_ccxt/venv311/bin"
ExecStart=/home/trader/Virtuoso_ccxt/venv311/bin/python src/main.py
Restart=always
RestartSec=10

# Resource limits
LimitNOFILE=65536
MemoryLimit=3G

# Logging
StandardOutput=append:/home/trader/logs/trading-bot.log
StandardError=append:/home/trader/logs/trading-bot-error.log

[Install]
WantedBy=multi-user.target
```

### 4.2 Alternative: Supervisor Configuration

```bash
# Create supervisor config
sudo nano /etc/supervisor/conf.d/trading-bot.conf
```

```ini
[program:trading-bot]
command=/home/trader/Virtuoso_ccxt/venv311/bin/python src/main.py
directory=/home/trader/Virtuoso_ccxt
user=trader
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
stdout_logfile=/home/trader/logs/trading-bot.log
stderr_logfile=/home/trader/logs/trading-bot-error.log
environment=PATH="/home/trader/Virtuoso_ccxt/venv311/bin"
```

### 4.3 Alternative: Docker Deployment

```bash
# If using Docker
cd /home/trader/Virtuoso_ccxt

# Build image
docker build -t virtuoso-trading:latest .

# Run with docker-compose
docker-compose up -d

# Or run directly
docker run -d \
  --name trading-bot \
  --restart unless-stopped \
  -p 8003:8003 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  virtuoso-trading:latest
```

---

## Phase 5: Monitoring & Maintenance (30 minutes)

### 5.1 Setup Nginx Reverse Proxy

```bash
# Configure Nginx
sudo nano /etc/nginx/sites-available/trading-bot
```

```nginx
server {
    listen 80;
    server_name YOUR_VPS_IP;

    location / {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /metrics {
        proxy_pass http://127.0.0.1:19999;  # Netdata
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/trading-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5.2 Setup Monitoring Scripts

```bash
# Create health check script
cat > ~/check-bot-health.sh << 'EOF'
#!/bin/bash

# Check if bot is running
if systemctl is-active --quiet trading-bot; then
    echo "✅ Bot is running"
else
    echo "❌ Bot is not running"
    systemctl start trading-bot
fi

# Check API endpoint
if curl -s http://localhost:8003/health > /dev/null; then
    echo "✅ API is responsive"
else
    echo "❌ API is not responding"
fi

# Check memory usage
MEMORY=$(free -m | awk 'NR==2{printf "%.1f", $3*100/$2}')
echo "📊 Memory usage: ${MEMORY}%"

# Check disk usage
DISK=$(df -h / | awk 'NR==2{print $5}')
echo "💾 Disk usage: ${DISK}"
EOF

chmod +x ~/check-bot-health.sh
```

### 5.3 Setup Automated Backups

```bash
# Create backup script
cat > ~/backup-trading-bot.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/home/trader/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
pg_dump -U trader trading_db > $BACKUP_DIR/db_backup_$DATE.sql

# Backup configuration
tar -czf $BACKUP_DIR/config_backup_$DATE.tar.gz \
    /home/trader/Virtuoso_ccxt/.env \
    /home/trader/Virtuoso_ccxt/config/

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x ~/backup-trading-bot.sh

# Add to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * /root/backup-trading-bot.sh") | crontab -
```

---

## Phase 6: Testing & Validation (15 minutes)

### 6.1 Start the Bot

```bash
# Using systemd
sudo systemctl start trading-bot
sudo systemctl enable trading-bot
sudo systemctl status trading-bot

# Check logs
sudo journalctl -u trading-bot -f
```

### 6.2 Verify Functionality

```bash
# Test API endpoints
curl http://localhost:8003/health
curl http://localhost:8003/api/v1/status
curl http://localhost:8003/api/v1/market/summary

# Check WebSocket connections
netstat -an | grep 9443  # Bybit WebSocket

# Monitor resource usage
htop
```

### 6.3 Performance Benchmark

```bash
# Run the benchmark script
cd /home/trader/Virtuoso_ccxt
source venv311/bin/activate
python scripts/testing/benchmark_system_performance.py

# Compare with local results
```

---

## 📱 Post-Deployment Checklist

- [ ] Bot is running without errors
- [ ] API endpoints are accessible
- [ ] WebSocket connections are stable
- [ ] Discord alerts are working
- [ ] Monitoring dashboard accessible
- [ ] Automated backups configured
- [ ] Firewall rules applied
- [ ] SSH key-only access configured
- [ ] Performance benchmark completed

---

## 🔧 Maintenance Commands

```bash
# View logs
sudo journalctl -u trading-bot -f

# Restart bot
sudo systemctl restart trading-bot

# Update code
cd /home/trader/Virtuoso_ccxt
git pull
source venv311/bin/activate
pip install -r requirements.txt
sudo systemctl restart trading-bot

# Check system resources
htop
df -h
free -m

# Monitor network
netstat -tuln
ss -t -a

# View Netdata monitoring
http://YOUR_VPS_IP:19999
```

---

## 🚨 Troubleshooting

### Common Issues:

1. **Import Errors**
   ```bash
   # Reinstall TA-Lib
   pip uninstall talib
   pip install --no-cache-dir talib
   ```

2. **Memory Issues**
   ```bash
   # Add swap space
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

3. **Connection Timeouts**
   ```bash
   # Check firewall
   sudo ufw status
   # Check if Bybit IPs are accessible
   ping api.bybit.com
   ```

---

## 💰 Cost Optimization

- **Development**: Use hourly billing for testing
- **Production**: Switch to monthly billing after validation
- **Snapshots**: Enable automatic backups
- **Monitoring**: Use free Netdata instead of paid services

---

## 🎯 Success Metrics

After deployment, you should see:
- API latency: 10-15ms (vs 1000ms+ local)
- WebSocket latency: <20ms
- 99.9% uptime
- Stable memory usage <3GB
- CPU usage <50% average

---

## 📞 Support Resources

- Vultr Support: https://www.vultr.com/docs/
- Ubuntu Forums: https://ubuntuforums.org/
- Your Bot Documentation: /docs/
- Discord Community: [Your Discord Link]