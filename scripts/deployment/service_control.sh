#!/bin/bash
#
# Virtuoso Trading System - Service Control Script
# This script provides easy management of the systemd service
#

SERVICE_NAME="virtuoso-trading"
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