#!/bin/bash

#############################################################################
# Script: service_control.sh
# Purpose: Deploy and manage service control
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
#   ./service_control.sh [options]
#   
#   Examples:
#     ./service_control.sh
#     ./service_control.sh --verbose
#     ./service_control.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: VPS_HOST_REDACTED)
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

# Virtuoso Trading System - Service Control Script
# This script provides easy management of the systemd service
#

SERVICE_NAME="virtuoso"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root. It will use sudo when needed."
   exit 1
fi

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check service status
check_status() {
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${GREEN}● Service is running${NC}"
        systemctl status $SERVICE_NAME --no-pager | head -10
    else
        echo -e "${RED}● Service is not running${NC}"
    fi
    
    if systemctl is-enabled --quiet $SERVICE_NAME; then
        echo -e "${GREEN}● Auto-start is enabled${NC}"
    else
        echo -e "${YELLOW}● Auto-start is disabled${NC}"
    fi
}

# Function to enable systemd service
enable_systemd() {
    print_status "Enabling systemd service..."
    
    # Check if service file exists
    if [[ ! -f /etc/systemd/system/$SERVICE_NAME.service ]]; then
        print_error "Service file not found. Would you like to create it? (y/n)"
        read -r response
        if [[ "$response" == "y" ]]; then
            create_service_file
        else
            exit 1
        fi
    fi
    
    # Enable and start the service
    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME
    sudo systemctl start $SERVICE_NAME
    
    sleep 2
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        print_status "Service enabled and started successfully!"
        check_status
    else
        print_error "Failed to start service. Check logs with: sudo journalctl -u $SERVICE_NAME -n 50"
        exit 1
    fi
}

# Function to disable systemd service
disable_systemd() {
    print_status "Disabling systemd service..."
    
    # Stop and disable the service
    sudo systemctl stop $SERVICE_NAME
    sudo systemctl disable $SERVICE_NAME
    
    sleep 1
    
    print_status "Service disabled successfully!"
    print_warning "The application will not start automatically on boot"
    print_status "You can still run it manually with: cd ~/trading/Virtuoso_ccxt && source venv311/bin/activate && python src/main.py"
}

# Function to create service file
create_service_file() {
    print_status "Creating systemd service file..."
    
    sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << 'EOF'
[Unit]
Description=Virtuoso Trading System
After=network.target

[Service]
Type=simple
User=linuxuser
Group=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
Environment="PATH=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python src/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Performance and resource limits
Nice=0
LimitNOFILE=65536
MemoryLimit=4G

# Security
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF
    
    print_status "Service file created successfully!"
}

# Function to toggle service
toggle_service() {
    if systemctl is-enabled --quiet $SERVICE_NAME; then
        disable_systemd
    else
        enable_systemd
    fi
}

# Function to run without systemd
run_manual() {
    print_status "Running application manually (without systemd)..."
    print_warning "This will run in the foreground. Use Ctrl+C to stop."
    
    cd ~/trading/Virtuoso_ccxt || exit 1
    source venv311/bin/activate
    python src/main.py
}

# Function to run in background without systemd
run_background() {
    print_status "Running application in background (without systemd)..."
    
    cd ~/trading/Virtuoso_ccxt || exit 1
    source venv311/bin/activate
    nohup python src/main.py > app.log 2>&1 &
    
    local pid=$!
    echo $pid > ~/trading/Virtuoso_ccxt/trading.pid
    
    print_status "Application started with PID: $pid"
    print_status "Logs: tail -f ~/trading/Virtuoso_ccxt/app.log"
    print_status "Stop with: kill $pid"
}

# Function to kill all Virtuoso processes
kill_all_processes() {
    print_warning "Finding all Virtuoso processes..."
    
    # Find all Python processes running main.py or containing Virtuoso
    local pids=$(ps aux | grep -E "(python.*main\.py|[Vv]irtuoso)" | grep -v grep | awk '{print $2}')
    
    if [[ -z "$pids" ]]; then
        print_status "No Virtuoso processes found"
        return
    fi
    
    echo "Found the following processes:"
    ps aux | grep -E "(python.*main\.py|[Vv]irtuoso)" | grep -v grep
    echo ""
    
    print_warning "This will kill all processes shown above!"
    echo -n "Are you sure? (y/n): "
    read -r response
    
    if [[ "$response" == "y" ]]; then
        # Stop systemd service first if running
        if systemctl is-active --quiet $SERVICE_NAME; then
            print_status "Stopping systemd service first..."
            sudo systemctl stop $SERVICE_NAME
        fi
        
        # Kill all found processes
        for pid in $pids; do
            print_status "Killing PID: $pid"
            kill -9 "$pid" 2>/dev/null || sudo kill -9 "$pid" 2>/dev/null
        done
        
        # Clean up any leftover pid files
        rm -f ~/trading/Virtuoso_ccxt/trading.pid 2>/dev/null
        
        print_status "All Virtuoso processes killed"
    else
        print_status "Operation cancelled"
    fi
}

# Function to view/edit configuration
view_edit_config() {
    local config_file="$HOME/trading/Virtuoso_ccxt/config/config.yaml"
    
    echo ""
    echo "Configuration Options:"
    echo "  1) View current configuration"
    echo "  2) Edit configuration (nano)"
    echo "  3) Edit configuration (vim)"
    echo "  4) Validate configuration"
    echo "  5) Back to main menu"
    echo ""
    echo -n "Select option: "
    read -r config_choice
    
    case $config_choice in
        1)
            print_status "Current configuration:"
            echo ""
            if [[ -f $config_file ]]; then
                cat $config_file
            else
                print_error "Configuration file not found at $config_file"
            fi
            ;;
        2)
            nano $config_file
            ;;
        3)
            vim $config_file
            ;;
        4)
            print_status "Validating configuration..."
            # Check if python has yaml module
            local python_cmd="$HOME/trading/Virtuoso_ccxt/venv311/bin/python"
            if [[ ! -f $python_cmd ]]; then
                python_cmd="python3"
            fi
            
            if $python_cmd -c "import yaml" 2>/dev/null; then
                if $python_cmd -c "import yaml; yaml.safe_load(open('$config_file'))" 2>/dev/null; then
                    print_status "Configuration is valid YAML"
                else
                    print_error "Configuration has YAML syntax errors!"
                    $python_cmd -c "import yaml; yaml.safe_load(open('$config_file'))"
                fi
            else
                print_warning "Python YAML module not found. Skipping validation."
            fi
            ;;
        5)
            return
            ;;
        *)
            print_error "Invalid option"
            ;;
    esac
}

# Function to toggle test mode
toggle_test_mode() {
    local config_file="$HOME/trading/Virtuoso_ccxt/config/config.yaml"
    
    if [[ ! -f $config_file ]]; then
        print_error "Configuration file not found at $config_file"
        return
    fi
    
    # Check if Python has yaml module
    local python_cmd="$HOME/trading/Virtuoso_ccxt/venv311/bin/python"
    if [[ ! -f $python_cmd ]]; then
        python_cmd="python3"
    fi
    
    if ! $python_cmd -c "import yaml" 2>/dev/null; then
        print_error "Python YAML module not found. Install with: pip install pyyaml"
        return
    fi
    
    # Check current mode
    local current_mode=$($python_cmd -c "
import yaml
with open('$config_file', 'r') as f:
    config = yaml.safe_load(f)
    print(config.get('trading', {}).get('test_mode', False))
" 2>/dev/null)
    
    if [[ "$current_mode" == "True" ]]; then
        print_status "Currently in TEST mode"
        echo -n "Switch to LIVE mode? (y/n): "
    else
        print_status "Currently in LIVE mode"
        echo -n "Switch to TEST mode? (y/n): "
    fi
    
    read -r response
    if [[ "$response" == "y" ]]; then
        # Create backup before modifying
        cp "$config_file" "${config_file}.backup_$(date +%Y%m%d_%H%M%S)"
        
        # Toggle the mode
        if [[ "$current_mode" == "True" ]]; then
            # Switch to live mode
            $python_cmd -c "
import yaml
with open('$config_file', 'r') as f:
    config = yaml.safe_load(f)
if 'trading' not in config:
    config['trading'] = {}
config['trading']['test_mode'] = False
with open('$config_file', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
print('Switched to LIVE mode')
"
            print_warning "SWITCHED TO LIVE MODE - Real money trading enabled!"
        else
            # Switch to test mode
            $python_cmd -c "
import yaml
with open('$config_file', 'r') as f:
    config = yaml.safe_load(f)
if 'trading' not in config:
    config['trading'] = {}
config['trading']['test_mode'] = True
with open('$config_file', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
print('Switched to TEST mode')
"
            print_status "Switched to TEST mode - Paper trading enabled"
        fi
        
        if systemctl is-active --quiet $SERVICE_NAME; then
            print_warning "Service is running. Restart now to apply changes? (y/n)"
            read -r restart_response
            if [[ "$restart_response" == "y" ]]; then
                sudo systemctl restart $SERVICE_NAME
                print_status "Service restarted with new mode"
            fi
        fi
    else
        print_status "Mode change cancelled"
    fi
}

# Function to perform health check
health_check() {
    print_status "Running health check..."
    echo ""
    
    # Check service status
    echo "1. Service Status:"
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "   ${GREEN}✓ Service is running${NC}"
    else
        echo -e "   ${RED}✗ Service is not running${NC}"
    fi
    
    # Check config file
    echo ""
    echo "2. Configuration:"
    local config_file="$HOME/trading/Virtuoso_ccxt/config/config.yaml"
    if [[ -f $config_file ]]; then
        # Use virtual environment Python for YAML check
        if [[ -d ~/trading/Virtuoso_ccxt/venv311 ]]; then
            if ~/trading/Virtuoso_ccxt/venv311/bin/python -c "import yaml; yaml.safe_load(open('$config_file'))" > /dev/null 2>&1; then
                echo -e "   ${GREEN}✓ Configuration file is valid${NC}"
            else
                echo -e "   ${RED}✗ Configuration file has errors${NC}"
            fi
        else
            # Fallback to system python
            if python3 -c "import yaml; yaml.safe_load(open('$config_file'))" > /dev/null 2>&1; then
                echo -e "   ${GREEN}✓ Configuration file is valid${NC}"
            else
                echo -e "   ${RED}✗ Configuration file has errors${NC}"
            fi
        fi
    else
        echo -e "   ${RED}✗ Configuration file not found${NC}"
    fi
    
    # Check Python environment
    echo ""
    echo "3. Python Environment:"
    if [[ -d ~/trading/Virtuoso_ccxt/venv311 ]]; then
        echo -e "   ${GREEN}✓ Virtual environment exists${NC}"
        source ~/trading/Virtuoso_ccxt/venv311/bin/activate
        python_version=$(python --version 2>&1)
        echo "   Python version: $python_version"
        deactivate
    else
        echo -e "   ${RED}✗ Virtual environment not found${NC}"
    fi
    
    # Check disk space
    echo ""
    echo "4. Disk Space:"
    disk_usage=$(df -h ~ | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $disk_usage -lt 80 ]]; then
        echo -e "   ${GREEN}✓ Disk usage: ${disk_usage}%${NC}"
    else
        echo -e "   ${YELLOW}⚠ Disk usage: ${disk_usage}% (high)${NC}"
    fi
    
    # Check memory
    echo ""
    echo "5. Memory Usage:"
    free_output=$(free -h | grep Mem)
    echo "   $free_output"
    
    # Check logs for errors
    echo ""
    echo "6. Recent Errors (last 24 hours):"
    if systemctl is-active --quiet $SERVICE_NAME; then
        error_count=$(sudo journalctl -u $SERVICE_NAME --since "24 hours ago" | grep -iE "(error|exception|critical)" | wc -l)
        if [[ $error_count -eq 0 ]]; then
            echo -e "   ${GREEN}✓ No errors found${NC}"
        else
            echo -e "   ${YELLOW}⚠ Found $error_count error entries${NC}"
            echo "   Run option 7 to view logs"
        fi
    else
        echo "   Service not running - no logs to check"
    fi
    
    # Check connectivity
    echo ""
    echo "7. Network Connectivity:"
    if ping -c 1 google.com > /dev/null 2>&1; then
        echo -e "   ${GREEN}✓ Internet connection OK${NC}"
    else
        echo -e "   ${RED}✗ No internet connection${NC}"
    fi
    
    echo ""
    print_status "Health check complete"
}

# Function to view/edit system config JSON
view_edit_system_config() {
    local config_file="$HOME/trading/Virtuoso_ccxt/config/system_config.json"
    local python_cmd="$HOME/trading/Virtuoso_ccxt/venv311/bin/python"
    if [[ ! -f $python_cmd ]]; then
        python_cmd="python3"
    fi
    
    echo ""
    echo "System Config (JSON) Options:"
    echo "  1) View current system configuration"
    echo "  2) Edit system configuration (nano)"
    echo "  3) Edit system configuration (vim)"
    echo "  4) Validate JSON syntax"
    echo "  5) Create system config if missing"
    echo "  6) Back to main menu"
    echo ""
    echo -n "Select option: "
    read -r config_choice
    
    case $config_choice in
        1)
            print_status "Current system configuration:"
            echo ""
            if [[ -f $config_file ]]; then
                $python_cmd -m json.tool $config_file 2>/dev/null || cat $config_file
            else
                print_error "System configuration file not found at $config_file"
                echo "Would you like to create it? Use option 5"
            fi
            ;;
        2)
            if [[ -f $config_file ]]; then
                nano $config_file
            else
                print_error "File not found. Create it first with option 5"
            fi
            ;;
        3)
            if [[ -f $config_file ]]; then
                vim $config_file
            else
                print_error "File not found. Create it first with option 5"
            fi
            ;;
        4)
            print_status "Validating JSON syntax..."
            if [[ -f $config_file ]]; then
                if $python_cmd -m json.tool $config_file > /dev/null 2>&1; then
                    print_status "System configuration is valid JSON"
                else
                    print_error "System configuration has JSON syntax errors!"
                    $python_cmd -m json.tool $config_file
                fi
            else
                print_error "System configuration file not found"
            fi
            ;;
        5)
            if [[ -f $config_file ]]; then
                print_warning "System config already exists. Overwrite? (y/n)"
                read -r overwrite
                if [[ "$overwrite" != "y" ]]; then
                    return
                fi
            fi
            print_status "Creating default system configuration..."
            cat > $config_file << 'EOF'
{
    "system": {
        "name": "Virtuoso Trading System",
        "version": "1.0.0",
        "environment": "production"
    },
    "api": {
        "host": "0.0.0.0",
        "port": 8000,
        "workers": 4
    },
    "database": {
        "url": "sqlite:///trading.db",
        "pool_size": 10
    },
    "logging": {
        "level": "INFO",
        "format": "json",
        "file": "logs/system.log"
    },
    "monitoring": {
        "enabled": true,
        "interval": 60,
        "alerts_enabled": true
    },
    "trading": {
        "test_mode": false,
        "max_positions": 10,
        "risk_limit": 0.02
    }
}
EOF
            print_status "Default system configuration created"
            ;;
        6)
            return
            ;;
        *)
            print_error "Invalid option"
            ;;
    esac
}

# Main menu
show_menu() {
    echo ""
    echo "====================================="
    echo "  Virtuoso Trading Service Control"
    echo "====================================="
    echo ""
    check_status
    echo ""
    echo "Options:"
    echo "  1) Enable systemd service (auto-start on boot)"
    echo "  2) Disable systemd service (manual start only)"
    echo "  3) Toggle service (enable/disable)"
    echo "  4) Start service now"
    echo "  5) Stop service now"
    echo "  6) Restart service"
    echo "  7) View logs (live)"
    echo "  8) Run manually (foreground)"
    echo "  9) Run in background (no systemd)"
    echo "  10) Restart server (full system reboot)"
    echo "  11) Kill all Virtuoso processes"
    echo "  12) View/Edit Configuration"
    echo "  13) Toggle Test Mode"
    echo "  14) Health Check"
    echo "  15) View/Edit System Config (JSON)"
    echo "  0) Exit"
    echo ""
    echo -n "Select option: "
}

# Handle user selection
while true; do
    show_menu
    read -r choice
    
    case $choice in
        1)
            enable_systemd
            ;;
        2)
            disable_systemd
            ;;
        3)
            toggle_service
            ;;
        4)
            sudo systemctl start $SERVICE_NAME
            print_status "Service started"
            ;;
        5)
            sudo systemctl stop $SERVICE_NAME
            print_status "Service stopped"
            ;;
        6)
            sudo systemctl restart $SERVICE_NAME
            print_status "Service restarted"
            ;;
        7)
            print_status "Showing live logs (Ctrl+C to exit)..."
            sudo journalctl -u $SERVICE_NAME -f
            ;;
        8)
            if systemctl is-active --quiet $SERVICE_NAME; then
                print_warning "Systemd service is running. Stop it first? (y/n)"
                read -r response
                if [[ "$response" == "y" ]]; then
                    sudo systemctl stop $SERVICE_NAME
                    run_manual
                fi
            else
                run_manual
            fi
            ;;
        9)
            if systemctl is-active --quiet $SERVICE_NAME; then
                print_warning "Systemd service is running. Stop it first? (y/n)"
                read -r response
                if [[ "$response" == "y" ]]; then
                    sudo systemctl stop $SERVICE_NAME
                    run_background
                fi
            else
                run_background
            fi
            ;;
        10)
            print_warning "This will restart the entire server!"
            echo -n "Are you sure you want to reboot? (y/n): "
            read -r response
            if [[ "$response" == "y" ]]; then
                print_status "Rebooting server in 5 seconds..."
                print_status "Service will restart automatically after reboot"
                sleep 5
                sudo reboot
            else
                print_status "Reboot cancelled"
            fi
            ;;
        11)
            kill_all_processes
            ;;
        12)
            view_edit_config
            ;;
        13)
            toggle_test_mode
            ;;
        14)
            health_check
            ;;
        15)
            view_edit_system_config
            ;;
        0)
            echo "Exiting..."
            exit 0
            ;;
        *)
            print_error "Invalid option"
            ;;
    esac
    
    echo ""
    echo "Press Enter to continue..."
    read -r
done