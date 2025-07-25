#!/bin/bash

echo "📦 Transferring Virtuoso Trading Bot to VPS"
echo "=========================================="

VPS_IP="45.77.40.77"
VPS_USER="linuxuser"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_PATH="$SCRIPT_DIR/.."
EXCLUDE_FILE="$LOCAL_PATH/.rsync-exclude"

# Check if exclude file exists
if [ ! -f "$EXCLUDE_FILE" ]; then
    echo "❌ Error: .rsync-exclude file not found!"
    echo "Please ensure .rsync-exclude exists in the project root."
    exit 1
fi

echo "✅ Using .rsync-exclude file for exclusions"
echo ""

# Show what will be excluded
echo "📋 Major exclusions:"
echo "  - Virtual environments (venv311/, venv/)"
echo "  - Logs and databases (logs/, *.log, *.db)"
echo "  - Large exports (exports/, reports/, src/exports/)"
echo "  - Test files and cache"
echo "  - Total excluded: ~8GB of data"
echo ""

# Method 1: Using rsync with exclude file (RECOMMENDED)
echo "Method 1: Using rsync with .rsync-exclude (RECOMMENDED)"
echo "=========================================="
echo "This will transfer only essential files (~100MB instead of 8.7GB)"
echo ""
echo "Run this command:"
echo "rsync -avzP --exclude-from='$EXCLUDE_FILE' $LOCAL_PATH/ $VPS_USER@$VPS_IP:~/trading/Virtuoso_ccxt/"
echo ""

# Calculate approximate size
echo "Checking transfer size..."
echo "Command to check size before transfer:"
echo "rsync -an --stats --exclude-from='$EXCLUDE_FILE' $LOCAL_PATH/ $VPS_USER@$VPS_IP:~/trading/Virtuoso_ccxt/ | grep 'Total file size'"
echo ""

# Method 2: Create optimized tar archive
echo "Method 2: Create optimized compressed archive"
echo "============================================"
echo "Run these commands:"
echo ""
echo "# Create archive locally (excluding large files)"
echo "cd $(dirname $LOCAL_PATH)"
echo "tar -czf virtuoso-optimized.tar.gz --exclude-from='Virtuoso_ccxt/.rsync-exclude' Virtuoso_ccxt/"
echo ""
echo "# Check archive size"
echo "ls -lh virtuoso-optimized.tar.gz"
echo ""
echo "# Transfer archive"
echo "scp virtuoso-optimized.tar.gz $VPS_USER@$VPS_IP:~/"
echo ""
echo "# On VPS, extract it"
echo "ssh $VPS_USER@$VPS_IP 'mkdir -p ~/trading && cd ~/trading && tar -xzf ~/virtuoso-optimized.tar.gz && rm ~/virtuoso-optimized.tar.gz'"
echo ""

# Post-transfer setup
echo "📝 After transfer, on the VPS:"
echo "=============================="
echo "1. SSH to VPS: ssh $VPS_USER@$VPS_IP"
echo "2. cd ~/trading/Virtuoso_ccxt"
echo "3. Create necessary directories:"
echo "   mkdir -p logs exports reports cache src/logs src/exports src/reports"
echo "4. Set up Python environment:"
echo "   python3.11 -m venv venv311"
echo "   source venv311/bin/activate"
echo "   pip install -r requirements.txt"
echo "5. Configure .env file with API keys"
echo "6. Run the application"