#!/bin/bash

# One-click Docker deployment script for Virtuoso CCXT
set -e

echo "═══════════════════════════════════════════════════════════════"
echo "🚀 Virtuoso CCXT - One-Click Docker Deployment"
echo "═══════════════════════════════════════════════════════════════"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env file. Please edit it with your API keys before continuing."
        echo ""
        echo "Edit the following file: $(pwd)/.env"
        echo "Then run this script again."
        exit 0
    else
        echo "❌ .env.example not found. Cannot proceed."
        exit 1
    fi
fi

# Parse command line arguments
ACTION=${1:-up}

case $ACTION in
    up|start)
        echo "📦 Building Docker images..."
        docker-compose build

        echo "🚀 Starting services..."
        docker-compose up -d

        echo "⏳ Waiting for services to be ready..."
        sleep 10

        # Check service health
        echo "🔍 Checking service health..."
        if curl -f -s http://localhost:8003/health > /dev/null 2>&1; then
            echo "✅ Web Server is healthy"
        else
            echo "⚠️  Web Server health check failed"
        fi

        if curl -f -s http://localhost:8001/api/monitoring/status > /dev/null 2>&1; then
            echo "✅ Monitoring Service is healthy"
        else
            echo "⚠️  Monitoring Service health check failed"
        fi

        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo "✅ Deployment Complete!"
        echo ""
        echo "📊 Access Points:"
        echo "   Desktop Dashboard:  http://localhost/"
        echo "   Mobile Dashboard:   http://localhost/mobile"
        echo "   Configuration:      http://localhost/config/wizard"
        echo "   Documentation:      http://localhost/docs/"
        echo "   Direct Web Access:  http://localhost:8003/"
        echo "   Monitoring API:     http://localhost:8001/api/monitoring/status"
        echo ""
        echo "📝 Manage Services:"
        echo "   View logs:    docker-compose logs -f"
        echo "   Stop:         ./scripts/docker_deploy.sh stop"
        echo "   Restart:      ./scripts/docker_deploy.sh restart"
        echo "   Status:       ./scripts/docker_deploy.sh status"
        echo "═══════════════════════════════════════════════════════════════"
        ;;

    stop|down)
        echo "🛑 Stopping services..."
        docker-compose down
        echo "✅ Services stopped"
        ;;

    restart)
        echo "🔄 Restarting services..."
        docker-compose restart
        echo "✅ Services restarted"
        ;;

    status)
        echo "📊 Service Status:"
        docker-compose ps
        ;;

    logs)
        echo "📜 Showing logs (press Ctrl+C to exit)..."
        docker-compose logs -f
        ;;

    clean)
        echo "🧹 Cleaning up..."
        docker-compose down -v
        echo "✅ Cleanup complete"
        ;;

    *)
        echo "Usage: $0 {up|start|stop|down|restart|status|logs|clean}"
        echo ""
        echo "Commands:"
        echo "  up/start  - Build and start all services"
        echo "  stop/down - Stop all services"
        echo "  restart   - Restart all services"
        echo "  status    - Show service status"
        echo "  logs      - Show service logs"
        echo "  clean     - Stop services and remove volumes"
        exit 1
        ;;
esac