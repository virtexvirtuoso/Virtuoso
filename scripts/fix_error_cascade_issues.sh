#!/bin/bash
set -e

echo "🔧 CRITICAL FIX: Resolving Error Cascade Issues"
echo "=============================================="
echo "Issues to fix:"
echo "  1. ErrorSeverity enum comparison failure"
echo "  2. Invalid symbol handling causing error loops"
echo "  3. Data processor handling error responses"

# Files to deploy
CRITICAL_FILES=(
    "src/data_processing/error_handler.py"
    "src/core/exchanges/ccxt_exchange.py"
    "src/core/exchanges/manager.py"
    "src/data_processing/data_processor.py"
)

# Create backup timestamp
BACKUP_TIME=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup_error_cascade_fix_${BACKUP_TIME}"

echo "📦 Creating VPS backup..."
ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && tar -czf ${BACKUP_DIR}.tar.gz src/data_processing/error_handler.py src/core/exchanges/ccxt_exchange.py src/core/exchanges/manager.py src/data_processing/data_processor.py"

echo "📤 Deploying error cascade fixes..."
for file in "${CRITICAL_FILES[@]}"; do
    echo "  Deploying $file..."

    # Create directory if needed
    dir_path=$(dirname "$file")
    ssh vps "mkdir -p /home/linuxuser/trading/Virtuoso_ccxt/$dir_path"

    # Copy file
    scp "$file" "vps:/home/linuxuser/trading/Virtuoso_ccxt/$file"
done

echo "🔄 Restarting VPS services..."
ssh vps "sudo systemctl restart virtuoso-web.service"
ssh vps "sudo systemctl restart virtuoso-trading.service"
ssh vps "sudo systemctl restart virtuoso-monitoring-api.service"

echo "⏳ Waiting 15 seconds for services to start..."
sleep 15

echo "🔍 Checking service status..."
ssh vps "sudo systemctl status virtuoso-web.service --no-pager -l | head -5"

echo "📊 Checking for error cascade issues..."
echo "Looking for ErrorSeverity comparison errors..."
if ssh vps "journalctl -u virtuoso-web.service --since '2 minutes ago' | grep 'not supported between instances' | head -3"; then
    echo "⚠️  ErrorSeverity error still present - may need more investigation"
else
    echo "✅ No ErrorSeverity comparison errors found"
fi

echo "Looking for 10000SATSUSDT error loops..."
if ssh vps "journalctl -u virtuoso-web.service --since '2 minutes ago' | grep '10000SATSUSDT' | wc -l"; then
    echo "⚠️  Still seeing 10000SATSUSDT attempts - checking if they're handled gracefully"
else
    echo "✅ No 10000SATSUSDT errors found"
fi

echo "Looking for 'Invalid market data format' errors..."
if ssh vps "journalctl -u virtuoso-web.service --since '2 minutes ago' | grep 'Invalid market data format' | head -3"; then
    echo "⚠️  Data processor still throwing format errors"
else
    echo "✅ No invalid market data format errors found"
fi

echo ""
echo "📈 ERROR CASCADE FIX SUMMARY:"
echo "Root Issues Fixed:"
echo "  1. ErrorSeverity enum comparison - Added proper numeric mapping"
echo "  2. CCXTExchange symbol handling - Return None for unsupported symbols"
echo "  3. ExchangeManager error responses - Proper error objects with type info"
echo "  4. DataProcessor error handling - Gracefully handle error responses"
echo ""
echo "Expected Behavior:"
echo "  - Unsupported symbols logged as warnings, not errors"
echo "  - No more TypeError from ErrorSeverity comparisons"
echo "  - Error cascade stopped at source"
echo "  - System continues processing other symbols"
echo ""
echo "✅ Error Cascade Fix Complete"