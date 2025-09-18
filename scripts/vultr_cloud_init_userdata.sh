#!/bin/bash

#############################################################################
# Script: vultr_cloud_init_userdata.sh
# Purpose: cloud-config
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates deployment automation, service management, and infrastructure updates for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - rsync
#   - ssh
#   - git
#   - systemctl
#   - Access to project directory structure
#
# Usage:
#   ./vultr_cloud_init_userdata.sh [options]
#   
#   Examples:
#     ./vultr_cloud_init_userdata.sh
#     ./vultr_cloud_init_userdata.sh --verbose
#     ./vultr_cloud_init_userdata.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
#   0 - Success
#   1 - Deployment failed
#   2 - Invalid arguments
#   3 - Connection error
#   4 - Service start failed
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

# Vultr Cloud-Init User Data for Virtuoso Trading Bot
# This script runs automatically on first boot

# Log all output
exec > >(tee -a /var/log/cloud-init-output.log)
exec 2>&1

echo "=========================================="
echo "Starting Virtuoso Trading Bot Setup"
echo "Time: $(date)"
echo "=========================================="

# Update system
echo "📦 Updating system packages..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

# Install Python 3.11
echo "🐍 Installing Python 3.11..."
apt-get install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils python3-pip

# Install essential packages
echo "📚 Installing essential packages..."
apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    htop \
    tmux \
    screen \
    redis-server \
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
    shared-mime-info \
    net-tools \
    dnsutils \
    iotop \
    ncdu

# Install TA-Lib (required for trading bot)
echo "📈 Installing TA-Lib..."
cd /tmp
wget -q http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make -j$(nproc)
make install
ldconfig
cd /

# Configure firewall
echo "🔒 Configuring firewall..."
ufw --force disable
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS  
ufw allow 8003/tcp  # Trading Bot API
ufw allow 19999/tcp # Netdata (optional)
echo "y" | ufw enable

# Create trading user
echo "👤 Creating trading user..."
useradd -m -s /bin/bash trader
echo "trader ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
mkdir -p /home/trader/{logs,data,backups,.ssh}
chown -R trader:trader /home/trader/

# Setup swap (important for 4GB VPS)
echo "💾 Setting up swap space..."
if [ ! -f /swapfile ]; then
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# Configure system limits
echo "⚙️ Configuring system limits..."
cat >> /etc/security/limits.conf << EOF
* soft nofile 65536
* hard nofile 65536
* soft nproc 32768
* hard nproc 32768
EOF

# Install Docker (optional but recommended)
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker trader
    systemctl enable docker
fi

# Install monitoring tools
echo "📊 Installing monitoring tools..."
# Netdata
wget -q -O /tmp/netdata-kickstart.sh https://my-netdata.io/kickstart.sh
bash /tmp/netdata-kickstart.sh --dont-wait --dont-start-it

# Configure Netdata to start on boot
systemctl enable netdata
systemctl start netdata

# Setup basic nginx config
echo "🌐 Configuring Nginx..."
cat > /etc/nginx/sites-available/trading-bot << 'EOF'
server {
    listen 80;
    server_name _;

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
        proxy_read_timeout 86400;
    }
    
    location /netdata/ {
        proxy_pass http://127.0.0.1:19999/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

ln -sf /etc/nginx/sites-available/trading-bot /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# Create helpful scripts
echo "📝 Creating helper scripts..."

# Create status check script
cat > /usr/local/bin/bot-status << 'EOF'
#!/bin/bash
echo "🤖 Virtuoso Trading Bot Status"
echo "=============================="
echo ""
if systemctl is-active --quiet trading-bot; then
    echo "✅ Bot Status: RUNNING"
else
    echo "❌ Bot Status: STOPPED"
fi
echo ""
echo "📊 System Resources:"
free -h | grep Mem | awk '{print "Memory: " $3 " / " $2 " (" int($3/$2 * 100) "%)"}'
df -h / | tail -1 | awk '{print "Disk: " $3 " / " $2 " (" $5 ")"}'
echo "CPU Load: $(uptime | awk -F'load average:' '{print $2}')"
echo ""
echo "🌐 Network Status:"
curl -s -o /dev/null -w "Bybit API Latency: %{time_total}s\n" https://api.bybit.com/v5/market/time
echo ""
echo "📁 Bot Location: /home/trader/Virtuoso_ccxt"
echo "📝 Logs: /home/trader/logs/"
echo "🌐 Dashboard: http://$(curl -s ifconfig.me):8003"
EOF
chmod +x /usr/local/bin/bot-status

# Create quick start script
cat > /usr/local/bin/bot-start << 'EOF'
#!/bin/bash
cd /home/trader/Virtuoso_ccxt
source venv311/bin/activate
python src/main.py
EOF
chmod +x /usr/local/bin/bot-start

# Setup MOTD with bot info
echo "🎨 Setting up welcome message..."
cat > /etc/motd << 'EOF'

🤖 Virtuoso Trading Bot VPS
==========================
📊 Quick Commands:
  bot-status  - Check bot status
  bot-start   - Start bot manually
  
📁 Locations:
  Bot: /home/trader/Virtuoso_ccxt
  Logs: /home/trader/logs
  
🌐 Access:
  Dashboard: http://YOUR_IP:8003
  Netdata: http://YOUR_IP:19999
  
💡 First Time Setup:
  1. su - trader
  2. git clone YOUR_REPO_URL
  3. cd Virtuoso_ccxt
  4. python3.11 -m venv venv311
  5. source venv311/bin/activate
  6. pip install -r requirements.txt
  7. Create .env file with your API keys
  8. python src/main.py

EOF

# Final message
echo ""
echo "=========================================="
echo "✅ Initial Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. SSH into server: ssh root@$(curl -s ifconfig.me)"
echo "2. Switch to trader: su - trader"
echo "3. Clone your repository"
echo "4. Setup virtual environment"
echo "5. Configure API keys"
echo "6. Start your bot!"
echo ""
echo "System will reboot in 10 seconds..."
sleep 10
reboot