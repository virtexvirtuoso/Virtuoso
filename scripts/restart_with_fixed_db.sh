#!/bin/bash
# Restart Virtuoso with fixed InfluxDB credentials

echo "🔄 Restarting Virtuoso Trading System with fixed InfluxDB credentials..."

# Set the corrected environment variables
export INFLUXDB_URL="http://localhost:8086"
export INFLUXDB_TOKEN="auUwotDWSbRMNkZLAptfwRv8_lOm_GGJHzmKirgv-Zj8xZya4T6NWYaVqZGNpfaMyxsmtdgBtpaVNtx7PIxNbQ=="
export INFLUXDB_ORG="coinmaestro"
export INFLUXDB_BUCKET="VirtuosoDB"

echo "✅ Environment variables set:"
echo "   INFLUXDB_URL: $INFLUXDB_URL"
echo "   INFLUXDB_ORG: $INFLUXDB_ORG"
echo "   INFLUXDB_BUCKET: $INFLUXDB_BUCKET"
echo "   INFLUXDB_TOKEN: ${INFLUXDB_TOKEN:0:10}...${INFLUXDB_TOKEN: -10}"

# Check if port 8001 is in use
echo "🔍 Checking if port 8001 is in use..."
if lsof -i :8001 >/dev/null 2>&1; then
    echo "   Port 8001 is in use, finding process..."
    PORT_PID=$(lsof -ti :8001)
    echo "   Process using port 8001: $PORT_PID"
    
    # Find and stop the current main.py process
    echo "🛑 Stopping current Virtuoso process..."
    MAIN_PID=$(ps aux | grep "python.*main" | grep -v grep | awk '{print $2}' | head -1)

    if [ ! -z "$MAIN_PID" ]; then
        echo "   Found main process PID: $MAIN_PID"
        
        # Graceful shutdown first
        echo "   Sending SIGTERM for graceful shutdown..."
        kill -TERM $MAIN_PID
        
        # Wait up to 15 seconds for graceful shutdown
        for i in {1..15}; do
            if ! ps -p $MAIN_PID > /dev/null 2>&1; then
                echo "   ✅ Process stopped gracefully after ${i} seconds"
                break
            fi
            echo "   Waiting for graceful shutdown... (${i}/15)"
            sleep 1
        done
        
        # Force kill if still running
        if ps -p $MAIN_PID > /dev/null 2>&1; then
            echo "   Process still running, force killing..."
            kill -KILL $MAIN_PID
            sleep 2
            
            if ps -p $MAIN_PID > /dev/null 2>&1; then
                echo "   ❌ Failed to stop process $MAIN_PID"
                exit 1
            else
                echo "   ✅ Process force-stopped"
            fi
        fi
    else
        echo "   No main.py process found, but port is in use by PID: $PORT_PID"
        echo "   Killing process on port 8001..."
        kill -TERM $PORT_PID 2>/dev/null || kill -KILL $PORT_PID 2>/dev/null
        sleep 2
    fi
    
    # Verify port is free
    if lsof -i :8001 >/dev/null 2>&1; then
        echo "   ❌ Port 8001 still in use after cleanup"
        exit 1
    else
        echo "   ✅ Port 8001 is now free"
    fi
else
    echo "   ✅ Port 8001 is free"
fi

# Wait a moment for cleanup
echo "⏳ Waiting for system cleanup..."
sleep 3

# Start the application with new environment
echo "🚀 Starting Virtuoso with fixed database credentials..."
cd /Users/ffv_macmini/Desktop/Virtuoso_ccxt

# Activate virtual environment if it exists
if [ -d "venv311" ]; then
    source venv311/bin/activate
    echo "   ✅ Virtual environment activated"
fi

# Start the application in the background
echo "   Starting application..."
nohup python -m src.main > logs/restart.log 2>&1 &
NEW_PID=$!

echo "   ✅ Started new process with PID: $NEW_PID"
echo "   📋 Logs available at: logs/restart.log"

# Wait and verify startup
echo "⏳ Waiting for application startup..."
sleep 8

if ps -p $NEW_PID > /dev/null; then
    echo "✅ Process is running"
    
    # Check if web server is responding
    echo "🔍 Checking web server response..."
    for i in {1..10}; do
        if curl -s http://localhost:8001/health >/dev/null 2>&1; then
            echo "   ✅ Web server is responding"
            break
        fi
        echo "   Waiting for web server... (${i}/10)"
        sleep 2
    done
    
    # Final health check
    echo "🏥 Checking system health..."
    HEALTH_RESPONSE=$(curl -s http://localhost:8001/health 2>/dev/null)
    if [ $? -eq 0 ]; then
        DB_STATUS=$(echo "$HEALTH_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    db_status = data.get('components', {}).get('database_client', False)
    overall_status = data.get('status', 'unknown')
    print(f'{overall_status}:{db_status}')
except:
    print('error:false')
" 2>/dev/null)
        
        OVERALL=$(echo "$DB_STATUS" | cut -d: -f1)
        DB_HEALTH=$(echo "$DB_STATUS" | cut -d: -f2)
        
        if [ "$OVERALL" = "healthy" ] && [ "$DB_HEALTH" = "True" ]; then
            echo "🎉 SUCCESS! Virtuoso is running with healthy database connection!"
            echo "   Overall status: $OVERALL"
            echo "   Database client: ✅ HEALTHY"
        else
            echo "⚠️  Application started but health check shows issues:"
            echo "   Overall status: $OVERALL"
            echo "   Database client: $([ "$DB_HEALTH" = "True" ] && echo "✅ HEALTHY" || echo "❌ UNHEALTHY")"
        fi
    else
        echo "❌ Web server not responding - check logs/restart.log for details"
    fi
else
    echo "❌ Failed to start Virtuoso - check logs/restart.log for details"
    exit 1
fi 