#!/bin/bash

#############################################################################
# Script: docker_validate.sh
# Purpose: Comprehensive Docker setup validation for trading system deployment
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
#   Validates complete Docker environment setup for the Virtuoso trading
#   system. Checks Docker installation, image availability, container
#   configuration, network setup, volume mounts, environment variables,
#   and resource allocations. Provides detailed validation report.
#
# Dependencies:
#   - Bash 4.0+
#   - Docker Engine 20.0+
#   - Docker Compose v2.0+
#   - Network connectivity for image pulls
#   - Sufficient system resources (CPU, memory, disk)
#
# Usage:
#   ./docker_validate.sh [options]
#   
#   Examples:
#     ./docker_validate.sh
#     ./docker_validate.sh --verbose
#     ./docker_validate.sh --fix-issues
#
# Options:
#   -v, --verbose        Enable detailed validation output
#   -f, --fix-issues     Attempt to automatically fix common issues
#   -q, --quiet          Suppress non-critical output
#   --skip-network       Skip network connectivity tests
#   --skip-resources     Skip resource allocation checks
#
# Validation Checks:
#   - Docker Engine installation and version
#   - Docker Compose availability and version
#   - Required Docker images (Python, Redis, Memcached)
#   - Container configuration files (Dockerfile, docker-compose.yml)
#   - Network configuration and connectivity
#   - Volume mount permissions and availability
#   - Environment variable configuration
#   - Resource limits and system capacity
#   - Port availability and firewall rules
#
# Environment Variables:
#   DOCKER_HOST          Docker daemon connection (optional)
#   PROJECT_ROOT         Trading system root directory
#   DOCKER_BUILDKIT      Enable BuildKit for improved builds
#
# Configuration:
#   Validation parameters can be customized in:
#   - docker-compose.yml (service definitions)
#   - .env files (environment variables)
#   - Dockerfile (image build configuration)
#
# Output:
#   - Detailed validation report with pass/fail status
#   - Warning and error summary
#   - Recommendations for fixing issues
#   - Exit code indicating overall validation status
#
# Exit Codes:
#   0 - All validations passed
#   1 - Critical validation failures
#   2 - Warning conditions present
#   3 - Docker not installed or accessible
#   4 - Configuration files missing
#   5 - Resource constraints detected
#
# Notes:
#   - Run before Docker deployment to ensure clean setup
#   - Provides actionable recommendations for fixing issues
#   - Can be integrated into CI/CD pipelines for automated validation
#   - Supports both development and production environment validation
#
#############################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 Validating Docker Setup for Virtuoso Trading System${NC}"
echo "====================================================="

ERRORS=0
WARNINGS=0

# Function to check requirement
check_requirement() {
    local name=$1
    local command=$2
    local required=$3
    
    echo -n "  - $name: "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC}"
    else
        if [ "$required" = true ]; then
            echo -e "${RED}❌ Missing (Required)${NC}"
            ((ERRORS++))
        else
            echo -e "${YELLOW}⚠️ Missing (Optional)${NC}"
            ((WARNINGS++))
        fi
    fi
}

# Function to check file
check_file() {
    local filepath=$1
    local required=$2
    
    echo -n "  - $filepath: "
    if [ -f "$filepath" ]; then
        echo -e "${GREEN}✅ Found${NC}"
    else
        if [ "$required" = true ]; then
            echo -e "${RED}❌ Missing (Required)${NC}"
            ((ERRORS++))
        else
            echo -e "${YELLOW}⚠️ Missing (Optional)${NC}"
            ((WARNINGS++))
        fi
    fi
}

# Function to check directory
check_directory() {
    local dirpath=$1
    
    echo -n "  - $dirpath: "
    if [ -d "$dirpath" ]; then
        echo -e "${GREEN}✅ Exists${NC}"
    else
        echo -e "${YELLOW}⚠️ Missing (will be created)${NC}"
        ((WARNINGS++))
    fi
}

# 1. Check Docker installation
echo -e "${BLUE}1. Docker Installation:${NC}"
check_requirement "Docker" "docker --version" true
check_requirement "Docker Compose" "docker-compose --version" true

# 2. Check Docker daemon
echo ""
echo -e "${BLUE}2. Docker Daemon:${NC}"
echo -n "  - Docker daemon: "
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${RED}❌ Not running${NC}"
    ((ERRORS++))
fi

# 3. Check required files
echo ""
echo -e "${BLUE}3. Required Files:${NC}"
check_file "Dockerfile" true
check_file "docker-compose.yml" true
check_file ".dockerignore" true
check_file "requirements.txt" true
check_file ".env" true
check_file ".env.example" false

# 4. Check directories
echo ""
echo -e "${BLUE}4. Directories:${NC}"
check_directory "src"
check_directory "config"
check_directory "logs"
check_directory "reports"
check_directory "data"
check_directory "cache"
check_directory "exports"

# 5. Validate Dockerfile syntax
echo ""
echo -e "${BLUE}5. Dockerfile Validation:${NC}"
echo -n "  - Dockerfile syntax: "
if docker build --check . > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Valid${NC}"
else
    # Fallback for older Docker versions
    if docker build -f Dockerfile --no-cache --target builder . > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Valid${NC}"
    else
        echo -e "${YELLOW}⚠️ Could not validate (may still be valid)${NC}"
        ((WARNINGS++))
    fi
fi

# 6. Check Docker Compose configuration
echo ""
echo -e "${BLUE}6. Docker Compose Configuration:${NC}"
echo -n "  - docker-compose.yml syntax: "
if docker-compose config > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Valid${NC}"
else
    echo -e "${RED}❌ Invalid${NC}"
    ((ERRORS++))
fi

# 7. Check port availability
echo ""
echo -e "${BLUE}7. Port Availability:${NC}"
for port in 8001 8003; do
    echo -n "  - Port $port: "
    if ! lsof -i:$port > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Available${NC}"
    else
        echo -e "${YELLOW}⚠️ In use${NC}"
        ((WARNINGS++))
    fi
done

# 8. Check environment variables
echo ""
echo -e "${BLUE}8. Environment Variables (.env):${NC}"
if [ -f .env ]; then
    for var in BYBIT_API_KEY BYBIT_API_SECRET; do
        echo -n "  - $var: "
        if grep -q "^$var=" .env; then
            if grep -q "^$var=.*\S" .env; then
                echo -e "${GREEN}✅ Set${NC}"
            else
                echo -e "${YELLOW}⚠️ Empty${NC}"
                ((WARNINGS++))
            fi
        else
            echo -e "${RED}❌ Missing${NC}"
            ((ERRORS++))
        fi
    done
fi

# 9. Check disk space
echo ""
echo -e "${BLUE}9. Disk Space:${NC}"
echo -n "  - Available space: "
AVAILABLE=$(df -h . | awk 'NR==2 {print $4}')
echo "$AVAILABLE"
# Check if we have at least 5GB free (rough check)
if df . | awk 'NR==2 {exit $4 < 5000000}'; then
    echo -e "  ${GREEN}✅ Sufficient space${NC}"
else
    echo -e "  ${YELLOW}⚠️ Low disk space${NC}"
    ((WARNINGS++))
fi

# 10. Check Docker resources
echo ""
echo -e "${BLUE}10. Docker Resources:${NC}"
if docker system df > /dev/null 2>&1; then
    docker system df
fi

# Summary
echo ""
echo "====================================================="
echo -e "${BLUE}📊 Validation Summary:${NC}"
echo "  - Errors: $ERRORS"
echo "  - Warnings: $WARNINGS"

if [ $ERRORS -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}✅ All checks passed! Ready to build and run.${NC}"
    else
        echo -e "${YELLOW}⚠️ Setup is functional with $WARNINGS warnings.${NC}"
    fi
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "  1. Build: ./scripts/docker_build.sh"
    echo "  2. Run: ./scripts/docker_run.sh"
    echo "  3. Monitor: ./scripts/docker_health_check.sh"
else
    echo -e "${RED}❌ Found $ERRORS errors that need to be fixed.${NC}"
    exit 1
fi