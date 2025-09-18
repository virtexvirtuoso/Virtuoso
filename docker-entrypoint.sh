#!/bin/bash
# Docker entrypoint script for Virtuoso CCXT

set -e

# Function to start monitoring service
start_monitoring() {
    echo "🚀 Starting Monitoring Service on port $MONITORING_PORT..."
    python src/main.py &
}

# Function to start web server
start_web_server() {
    echo "🌐 Starting Web Server on port $APP_PORT..."
    python src/web_server.py &
}

# Function to wait for services to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=0

    echo "⏳ Waiting for $service_name to be ready..."
    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done

    echo "❌ $service_name failed to start after $max_attempts attempts"
    return 1
}

# Main execution
case "${1:-all}" in
    monitoring)
        start_monitoring
        wait
        ;;
    web)
        start_web_server
        wait
        ;;
    all)
        echo "═══════════════════════════════════════════════════"
        echo "🚀 Virtuoso CCXT Trading System - Starting Services"
        echo "═══════════════════════════════════════════════════"

        # Start both services
        start_monitoring
        wait_for_service "http://localhost:$MONITORING_PORT/api/monitoring/status" "Monitoring Service"

        start_web_server
        wait_for_service "http://localhost:$APP_PORT/health" "Web Server"

        echo "═══════════════════════════════════════════════════"
        echo "✅ All services started successfully!"
        echo ""
        echo "📊 Access Points:"
        echo "   Desktop Dashboard: http://localhost:$APP_PORT/"
        echo "   Mobile Dashboard:  http://localhost:$APP_PORT/mobile"
        echo "   Configuration:     http://localhost:$API_PORT/api/config/wizard"
        echo "   Documentation:     http://localhost:$API_PORT/docs/"
        echo "   API Documentation: http://localhost:$APP_PORT/docs"
        echo "   Monitoring API:    http://localhost:$MONITORING_PORT/api/monitoring/status"
        echo "═══════════════════════════════════════════════════"

        # Keep container running
        tail -f /dev/null
        ;;
    *)
        echo "Usage: $0 {monitoring|web|all}"
        exit 1
        ;;
esac