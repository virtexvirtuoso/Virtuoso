#!/bin/bash

#############################################################################
# Script: deploy_vps.sh
# Purpose: VPS Deployment Script for Virtuoso Trading System
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
#   ./deploy_vps.sh [options]
#   
#   Examples:
#     ./deploy_vps.sh
#     ./deploy_vps.sh --verbose
#     ./deploy_vps.sh --dry-run
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

# Supports Ubuntu 20.04+ and Debian 10+

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/virtuoso"
SERVICE_USER="virtuoso"
PYTHON_VERSION="3.11"
REPO_URL="https://github.com/yourusername/virtuoso.git"  # Update this

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        log_error "Cannot detect OS"
        exit 1
    fi
    log_info "Detected OS: $OS $VER"
}

# Main installation process
main() {
    log_info "Starting Virtuoso Trading System deployment..."
    
    check_root
    detect_os
    
    # Step 1: Update system
    log_info "Updating system packages..."
    apt-get update && apt-get upgrade -y
    
    # Step 2: Install system dependencies
    log_info "Installing system dependencies..."
    apt-get install -y \
        software-properties-common \
        build-essential \
        git \
        curl \
        wget \
        nginx \
        redis-server \
        supervisor \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
        python${PYTHON_VERSION}-dev \
        wkhtmltopdf \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libffi-dev \
        libssl-dev \
        netcat \
        htop \
        ufw
    
    # Step 3: Create service user
    log_info "Creating service user..."
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -m -d /home/$SERVICE_USER -s /bin/bash $SERVICE_USER
        log_info "User $SERVICE_USER created"
    else
        log_warn "User $SERVICE_USER already exists"
    fi
    
    # Step 4: Setup firewall
    log_info "Configuring firewall..."
    ufw allow 22/tcp    # SSH
    ufw allow 80/tcp    # HTTP
    ufw allow 443/tcp   # HTTPS
    ufw allow 8000/tcp  # FastAPI
    ufw allow 8001/tcp  # API
    ufw allow 8003/tcp  # Dashboard
    echo "y" | ufw enable
    
    # Step 5: Create application directory
    log_info "Creating application directory..."
    mkdir -p $INSTALL_DIR
    mkdir -p $INSTALL_DIR/{logs,reports,exports,cache,data,backups}
    
    # Step 6: Clone or copy application
    if [ -d ".git" ]; then
        log_info "Copying local repository..."
        cp -r . $INSTALL_DIR/
    else
        log_info "Cloning repository..."
        git clone $REPO_URL $INSTALL_DIR
    fi
    
    # Step 7: Set permissions
    log_info "Setting permissions..."
    chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
    chmod -R 755 $INSTALL_DIR
    chmod -R 777 $INSTALL_DIR/logs
    chmod -R 777 $INSTALL_DIR/reports
    chmod -R 777 $INSTALL_DIR/exports
    chmod -R 777 $INSTALL_DIR/cache
    
    # Step 8: Setup Python environment
    log_info "Setting up Python virtual environment..."
    su - $SERVICE_USER -c "cd $INSTALL_DIR && python${PYTHON_VERSION} -m venv venv"
    
    # Step 9: Install Python dependencies
    log_info "Installing Python dependencies..."
    su - $SERVICE_USER -c "cd $INSTALL_DIR && source venv/bin/activate && pip install --upgrade pip"
    su - $SERVICE_USER -c "cd $INSTALL_DIR && source venv/bin/activate && pip install -r requirements.txt"
    
    # Step 10: Setup environment file
    log_info "Setting up environment configuration..."
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        cp $INSTALL_DIR/.env.example $INSTALL_DIR/.env
        log_warn "Please edit $INSTALL_DIR/.env with your credentials"
    fi
    
    # Step 11: Configure Redis
    log_info "Configuring Redis..."
    systemctl enable redis-server
    systemctl start redis-server
    
    # Step 12: Setup systemd service
    log_info "Creating systemd service..."
    cat > /etc/systemd/system/virtuoso.service << EOF
[Unit]
Description=Virtuoso Trading System
After=network.target redis.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/python -m src.main
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/logs/virtuoso.log
StandardError=append:$INSTALL_DIR/logs/virtuoso-error.log

[Install]
WantedBy=multi-user.target
EOF
    
    # Step 13: Setup nginx reverse proxy
    log_info "Configuring Nginx..."
    cat > /etc/nginx/sites-available/virtuoso << 'EOF'
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
    }
    
    location /api {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    location /dashboard {
        proxy_pass http://localhost:8003;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF
    
    ln -sf /etc/nginx/sites-available/virtuoso /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl restart nginx
    
    # Step 14: Setup log rotation
    log_info "Setting up log rotation..."
    cat > /etc/logrotate.d/virtuoso << EOF
$INSTALL_DIR/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 $SERVICE_USER $SERVICE_USER
    sharedscripts
    postrotate
        systemctl reload virtuoso >/dev/null 2>&1 || true
    endscript
}
EOF
    
    # Step 15: Setup monitoring
    log_info "Setting up basic monitoring..."
    cat > /usr/local/bin/virtuoso-health-check << 'EOF'
#!/bin/bash
if ! curl -f http://localhost:8001/health >/dev/null 2>&1; then
    echo "Virtuoso Trading System is not responding"
    systemctl restart virtuoso
fi
EOF
    chmod +x /usr/local/bin/virtuoso-health-check
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/virtuoso-health-check") | crontab -
    
    # Step 16: Enable and start services
    log_info "Enabling and starting services..."
    systemctl daemon-reload
    systemctl enable virtuoso
    systemctl start virtuoso
    
    # Step 17: Final checks
    log_info "Running final checks..."
    sleep 5
    
    if systemctl is-active --quiet virtuoso; then
        log_info "✅ Virtuoso Trading System is running!"
    else
        log_error "Service failed to start. Check logs: journalctl -u virtuoso -n 50"
        exit 1
    fi
    
    # Display status
    log_info "Installation complete!"
    echo ""
    echo "📊 Virtuoso Trading System Status:"
    echo "=================================="
    systemctl status virtuoso --no-pager
    echo ""
    echo "🔗 Access URLs:"
    echo "  - Main App: http://YOUR_SERVER_IP"
    echo "  - API: http://YOUR_SERVER_IP/api"
    echo "  - Dashboard: http://YOUR_SERVER_IP/dashboard"
    echo ""
    echo "📝 Important files:"
    echo "  - Config: $INSTALL_DIR/.env"
    echo "  - Logs: $INSTALL_DIR/logs/"
    echo "  - Service: systemctl status virtuoso"
    echo ""
    echo "⚠️  Next steps:"
    echo "  1. Edit $INSTALL_DIR/.env with your credentials"
    echo "  2. Restart service: systemctl restart virtuoso"
    echo "  3. Check logs: tail -f $INSTALL_DIR/logs/virtuoso.log"
    echo "  4. Configure SSL certificate for production"
}

# Run main function
main "$@"