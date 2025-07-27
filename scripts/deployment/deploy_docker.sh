#!/bin/bash
# Docker Deployment Script for Virtuoso Trading System

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
PROJECT_NAME="virtuoso"
BACKUP_DIR="./backups/deployment_$(date +%Y%m%d_%H%M%S)"

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

check_requirements() {
    log_info "Checking requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        if ! docker compose version &> /dev/null; then
            log_error "Docker Compose is not installed. Please install Docker Compose."
            exit 1
        else
            # Use docker compose instead of docker-compose
            COMPOSE_CMD="docker compose"
        fi
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    log_info "All requirements satisfied ✓"
}

setup_environment() {
    log_info "Setting up environment..."
    
    # Create .env if it doesn't exist
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            log_warn "Created .env from .env.example - Please update with your credentials!"
        else
            log_error "No .env file found and no .env.example to copy from"
            exit 1
        fi
    fi
    
    # Create necessary directories
    directories=("logs" "reports" "exports" "cache" "data" "backups")
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
        fi
    done
    
    # Set proper permissions
    chmod -R 755 logs reports exports cache data
}

backup_existing() {
    log_info "Backing up existing data..."
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Backup important files
    if [ -f .env ]; then
        cp .env "$BACKUP_DIR/.env.backup"
    fi
    
    # Backup data directories if they exist and contain files
    for dir in logs reports exports data; do
        if [ -d "$dir" ] && [ "$(ls -A $dir)" ]; then
            cp -r "$dir" "$BACKUP_DIR/"
            log_info "Backed up $dir"
        fi
    done
    
    log_info "Backup completed to: $BACKUP_DIR"
}

deploy_basic() {
    log_info "Deploying basic services (app + redis)..."
    
    # Stop existing containers
    $COMPOSE_CMD down
    
    # Build and start services
    $COMPOSE_CMD build --no-cache
    $COMPOSE_CMD up -d app redis
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 10
    
    # Check service health
    if docker ps | grep -q virtuoso; then
        log_info "✅ Services are running!"
    else
        log_error "Services failed to start"
        $COMPOSE_CMD logs --tail=50
        exit 1
    fi
}

deploy_full() {
    log_info "Deploying full stack (including InfluxDB)..."
    
    # Stop existing containers
    $COMPOSE_CMD down
    
    # Build and start all services
    $COMPOSE_CMD --profile full build --no-cache
    $COMPOSE_CMD --profile full up -d
    
    # Wait for services
    log_info "Waiting for all services to be healthy..."
    sleep 20
    
    # Check services
    services=("virtuoso" "virtuoso-redis" "virtuoso-influxdb")
    for service in "${services[@]}"; do
        if docker ps | grep -q "$service"; then
            log_info "✅ $service is running"
        else
            log_warn "⚠️  $service is not running"
        fi
    done
}

show_status() {
    log_info "Deployment Status:"
    echo ""
    
    # Show running containers
    docker ps --filter "name=virtuoso-*" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    
    # Show logs tail
    log_info "Recent logs from main app:"
    docker logs virtuoso --tail=10
    echo ""
    
    # Show access URLs
    log_info "Access URLs:"
    echo "  📊 Main App: http://localhost:8000"
    echo "  🔌 API: http://localhost:8001"
    echo "  📈 Dashboard: http://localhost:8003"
    if docker ps | grep -q "virtuoso-influxdb"; then
        echo "  📉 InfluxDB: http://localhost:8086"
    fi
    echo ""
    
    # Show useful commands
    log_info "Useful commands:"
    echo "  📜 View logs: docker logs -f virtuoso"
    echo "  🔄 Restart: $COMPOSE_CMD restart"
    echo "  🛑 Stop: $COMPOSE_CMD down"
    echo "  🧹 Clean: $COMPOSE_CMD down -v"
    echo "  💻 Shell: docker exec -it virtuoso bash"
}

update_deployment() {
    log_info "Updating deployment..."
    
    # Pull latest changes if in git repo
    if [ -d .git ]; then
        log_info "Pulling latest changes..."
        git pull
    fi
    
    # Rebuild and restart
    $COMPOSE_CMD build --no-cache
    $COMPOSE_CMD up -d
    
    log_info "Update complete!"
}

# Main menu
main() {
    echo "🚀 Virtuoso Trading System - Docker Deployment"
    echo "=============================================="
    echo ""
    
    check_requirements
    setup_environment
    
    # Check if .env has been configured
    if grep -q "your_api_key_here" .env 2>/dev/null; then
        log_warn "⚠️  .env contains default values. Please update before deploying!"
        log_warn "Edit .env and run this script again."
        exit 1
    fi
    
    echo "Select deployment option:"
    echo "1) Basic deployment (App + Redis)"
    echo "2) Full deployment (App + Redis + InfluxDB)"
    echo "3) Update existing deployment"
    echo "4) Show deployment status"
    echo "5) Backup and fresh deploy"
    echo ""
    read -p "Enter option (1-5): " option
    
    case $option in
        1)
            deploy_basic
            show_status
            ;;
        2)
            deploy_full
            show_status
            ;;
        3)
            update_deployment
            show_status
            ;;
        4)
            show_status
            ;;
        5)
            backup_existing
            deploy_basic
            show_status
            ;;
        *)
            log_error "Invalid option"
            exit 1
            ;;
    esac
    
    log_info "Deployment script completed!"
}

# Handle command line arguments
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: $0 [option]"
    echo "Options:"
    echo "  --basic     Deploy basic services"
    echo "  --full      Deploy full stack"
    echo "  --update    Update deployment"
    echo "  --status    Show status"
    echo "  --help      Show this help"
    exit 0
elif [ "$1" == "--basic" ]; then
    check_requirements
    setup_environment
    deploy_basic
    show_status
elif [ "$1" == "--full" ]; then
    check_requirements
    setup_environment
    deploy_full
    show_status
elif [ "$1" == "--update" ]; then
    check_requirements
    update_deployment
    show_status
elif [ "$1" == "--status" ]; then
    show_status
else
    main
fi