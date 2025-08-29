#!/bin/bash

#############################################################################
# Script: monitor.sh
# Purpose: Master Monitoring Script - System health monitoring
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
#   Master monitoring script that provides comprehensive system health checks
#   for the Virtuoso trading system. Monitors API endpoints, cache performance,
#   exchange connectivity, and overall system health with alerting capabilities.
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
#   ./monitor.sh [options]
#   
#   Examples:
#     ./monitor.sh
#     ./monitor.sh --verbose
#     ./monitor.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 45.77.40.77)
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

# Part of Phase 1: Emergency Stabilization

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_stat() {
    echo -e "${BLUE}[STAT]${NC} $1"
}

show_usage() {
    echo "Usage: $0 [MONITOR_TYPE] [OPTIONS]"
    echo ""
    echo "Monitor Types:"
    echo "  health      Check overall system health"
    echo "  api         Check API endpoints status"
    echo "  cache       Check cache performance"
    echo "  exchange    Check exchange connectivity"
    echo "  performance Check system performance"
    echo "  all         Run all monitoring checks"
    echo ""
    echo "Options:"
    echo "  --json      Output results in JSON format"
    echo "  --continuous Run continuously (Ctrl+C to stop)"
    echo "  --help      Show this help message"
}

check_health() {
    log_info "Checking system health..."
    
    # Check if main processes are running
    if pgrep -f "python.*main.py" >/dev/null; then
        log_stat "✓ Main application is running"
    else
        log_error "✗ Main application is not running"
    fi
    
    # Check memory usage
    if command -v free >/dev/null 2>&1; then
        memory_usage=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
        log_stat "Memory usage: ${memory_usage}%"
        if (( $(echo "$memory_usage > 85" | bc -l) )); then
            log_warn "High memory usage detected"
        fi
    elif command -v vm_stat >/dev/null 2>&1; then
        # macOS memory check
        vm_stat | head -5
    fi
    
    # Check disk space
    disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    log_stat "Disk usage: ${disk_usage}%"
    if [ "$disk_usage" -gt 85 ]; then
        log_warn "High disk usage detected"
    fi
    
    log_info "Health check completed"
}

check_api() {
    log_info "Checking API endpoints..."
    
    # Check main API (port 8003)
    if curl -s --connect-timeout 5 http://localhost:8003/health >/dev/null; then
        log_stat "✓ Main API (port 8003) is responding"
    else
        log_error "✗ Main API (port 8003) is not responding"
    fi
    
    # Check monitoring API (port 8001)
    if curl -s --connect-timeout 5 http://localhost:8001/api/monitoring/status >/dev/null; then
        log_stat "✓ Monitoring API (port 8001) is responding"
    else
        log_error "✗ Monitoring API (port 8001) is not responding"
    fi
    
    log_info "API check completed"
}

check_cache() {
    log_info "Checking cache performance..."
    
    # Check Memcached
    if echo "version" | nc localhost 11211 2>/dev/null | grep -q "VERSION"; then
        log_stat "✓ Memcached is running"
        
        # Get cache stats
        stats=$(echo "stats" | nc localhost 11211 2>/dev/null | grep -E "(get_hits|get_misses)" | awk '{print $3}')
        if [ -n "$stats" ]; then
            hits=$(echo "$stats" | head -1)
            misses=$(echo "$stats" | tail -1)
            if [ "$hits" -gt 0 ] && [ "$misses" -gt 0 ]; then
                hit_rate=$(( hits * 100 / (hits + misses) ))
                log_stat "Memcached hit rate: ${hit_rate}%"
                if [ "$hit_rate" -lt 80 ]; then
                    log_warn "Low cache hit rate detected"
                fi
            fi
        fi
    else
        log_error "✗ Memcached is not responding"
    fi
    
    # Check Redis
    if redis-cli ping 2>/dev/null | grep -q "PONG"; then
        log_stat "✓ Redis is running"
        
        # Get Redis info
        redis_info=$(redis-cli info stats 2>/dev/null | grep -E "(keyspace_hits|keyspace_misses)" || true)
        if [ -n "$redis_info" ]; then
            log_stat "Redis stats available"
        fi
    else
        log_error "✗ Redis is not responding"
    fi
    
    log_info "Cache check completed"
}

check_exchange() {
    log_info "Checking exchange connectivity..."
    
    # Check Bybit connectivity
    if curl -s --connect-timeout 10 https://api.bybit.com/v2/public/time >/dev/null; then
        log_stat "✓ Bybit API is reachable"
        
        # Test API response time
        response_time=$(curl -o /dev/null -s -w "%{time_total}" --connect-timeout 10 https://api.bybit.com/v2/public/time)
        log_stat "Bybit response time: ${response_time}s"
        if (( $(echo "$response_time > 2.0" | bc -l) )); then
            log_warn "High response time from Bybit API"
        fi
    else
        log_error "✗ Bybit API is not reachable"
    fi
    
    # Check Binance connectivity (if used)
    if curl -s --connect-timeout 10 https://api.binance.com/api/v3/ping >/dev/null; then
        log_stat "✓ Binance API is reachable"
    else
        log_warn "Binance API is not reachable (may not be configured)"
    fi
    
    log_info "Exchange connectivity check completed"
}

check_performance() {
    log_info "Checking system performance..."
    
    # Check load average
    if command -v uptime >/dev/null 2>&1; then
        load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
        log_stat "Load average: $load_avg"
        if (( $(echo "$load_avg > 4.0" | bc -l) )); then
            log_warn "High system load detected"
        fi
    fi
    
    # Check for error logs in last 5 minutes
    if [ -d "$PROJECT_ROOT/logs" ]; then
        recent_errors=$(find "$PROJECT_ROOT/logs" -name "*.log" -mmin -5 -exec grep -c "ERROR\|CRITICAL" {} + 2>/dev/null | awk -F: '{sum += $2} END {print sum}' || echo "0")
        log_stat "Recent errors (5min): $recent_errors"
        if [ "$recent_errors" -gt 10 ]; then
            log_warn "High error rate detected"
        fi
    fi
    
    log_info "Performance check completed"
}

check_all() {
    log_info "Running comprehensive system monitoring..."
    echo "========================================"
    
    check_health
    echo "----------------------------------------"
    check_api  
    echo "----------------------------------------"
    check_cache
    echo "----------------------------------------"
    check_exchange
    echo "----------------------------------------"
    check_performance
    
    echo "========================================"
    log_info "Comprehensive monitoring completed"
}

# Main execution
main() {
    local monitor_type=""
    local json_output=false
    local continuous=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            health|api|cache|exchange|performance|all)
                monitor_type=$1
                shift
                ;;
            --json)
                json_output=true
                shift
                ;;
            --continuous)
                continuous=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    if [ -z "$monitor_type" ]; then
        log_error "Monitor type not specified"
        show_usage
        exit 1
    fi
    
    # Continuous monitoring loop
    if [ "$continuous" = true ]; then
        log_info "Starting continuous monitoring (Ctrl+C to stop)..."
        while true; do
            clear
            echo "=== Virtuoso CCXT System Monitor - $(date) ==="
            
            case $monitor_type in
                "health")
                    check_health
                    ;;
                "api")
                    check_api
                    ;;
                "cache")
                    check_cache
                    ;;
                "exchange")
                    check_exchange
                    ;;
                "performance")
                    check_performance
                    ;;
                "all")
                    check_all
                    ;;
            esac
            
            sleep 30
        done
    else
        # Single run
        case $monitor_type in
            "health")
                check_health
                ;;
            "api")
                check_api
                ;;
            "cache")
                check_cache
                ;;
            "exchange")
                check_exchange
                ;;
            "performance")
                check_performance
                ;;
            "all")
                check_all
                ;;
        esac
    fi
}

main "$@"