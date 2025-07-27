#!/bin/bash

# Verify async cleanup fixes on VPS
# Usage: ./verify_async_fixes.sh

VPS_HOST="45.77.40.77"
VPS_USER="linuxuser"

echo "🔍 Verifying async cleanup fixes on VPS..."

# Function to run command on VPS
run_remote() {
    ssh "$VPS_USER@$VPS_HOST" "$1"
}

echo "📋 Checking service status..."
run_remote "sudo systemctl status virtuoso --no-pager -l"

echo ""
echo "🔍 Testing graceful shutdown (should exit with code 0)..."
run_remote "
    sudo systemctl stop virtuoso
    exit_code=\$?
    echo 'Service stop exit code:' \$exit_code
    sleep 2
"

echo "🔍 Checking for old error patterns in recent logs..."
run_remote "
    echo 'Checking for Task was destroyed errors:'
    sudo journalctl -u virtuoso --since '10 minutes ago' | grep -c 'Task was destroyed' || echo 'None found ✅'
    
    echo 'Checking for GeneratorExit errors:'
    sudo journalctl -u virtuoso --since '10 minutes ago' | grep -c 'GeneratorExit' || echo 'None found ✅'
    
    echo 'Checking for no running event loop errors:'
    sudo journalctl -u virtuoso --since '10 minutes ago' | grep -c 'no running event loop' || echo 'None found ✅'
"

echo ""
echo "🔄 Restarting service to test startup..."
run_remote "
    sudo systemctl start virtuoso
    sleep 3
    sudo systemctl status virtuoso --no-pager -l
"

echo ""
echo "📊 Recent startup logs:"
run_remote "sudo journalctl -u virtuoso --since '1 minute ago' --no-pager | tail -15"

echo ""
echo "✅ Verification completed!"
echo ""
echo "💡 To monitor in real-time:"
echo "   ssh $VPS_USER@$VPS_HOST"
echo "   sudo journalctl -u virtuoso -f"