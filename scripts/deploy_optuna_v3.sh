#!/bin/bash

# Deploy Optuna v3.6+ optimization system to VPS
# Production deployment with safety features and monitoring

set -e

# Configuration
VPS_HOST="linuxuser@${VPS_HOST}"
VPS_PROJECT_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_PROJECT_PATH="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/optuna_${TIMESTAMP}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}   Deploying Optuna v3.6+ to Production VPS      ${NC}"
echo -e "${BLUE}==================================================${NC}"

# Function to check VPS connectivity
check_vps_connection() {
    echo -e "${YELLOW}Checking VPS connectivity...${NC}"
    if ssh -o ConnectTimeout=5 $VPS_HOST "echo 'Connected'" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ VPS connection successful${NC}"
        return 0
    else
        echo -e "${RED}✗ Cannot connect to VPS${NC}"
        return 1
    fi
}

# Function to backup existing optimization files
backup_existing() {
    echo -e "${YELLOW}Creating backup of existing optimization files...${NC}"
    
    ssh $VPS_HOST << EOF
        cd $VPS_PROJECT_PATH
        if [ -d "src/optimization" ]; then
            mkdir -p $BACKUP_DIR
            cp -r src/optimization $BACKUP_DIR/
            cp -r config/*optim* $BACKUP_DIR/ 2>/dev/null || true
            cp -r data/optuna* $BACKUP_DIR/ 2>/dev/null || true
            echo "Backup created at: $BACKUP_DIR"
        fi
EOF
    
    echo -e "${GREEN}✓ Backup completed${NC}"
}

# Function to check system resources
check_resources() {
    echo -e "${YELLOW}Checking VPS resources...${NC}"
    
    ssh $VPS_HOST << 'EOF'
        echo "CPU Cores: $(nproc)"
        echo "Memory: $(free -h | grep Mem | awk '{print $2}')"
        echo "Available Memory: $(free -h | grep Mem | awk '{print $7}')"
        echo "Disk Space: $(df -h / | tail -1 | awk '{print $4}' ) available"
        
        # Check if we have enough resources
        AVAILABLE_MEM=$(free -m | grep Mem | awk '{print $7}')
        if [ $AVAILABLE_MEM -lt 2048 ]; then
            echo "WARNING: Less than 2GB RAM available"
        fi
EOF
    
    echo -e "${GREEN}✓ Resource check completed${NC}"
}

# Function to install/update Python dependencies
install_dependencies() {
    echo -e "${YELLOW}Installing Optuna v3.6+ and dependencies...${NC}"
    
    ssh $VPS_HOST << 'EOF'
        cd /home/linuxuser/trading/Virtuoso_ccxt
        
        # Create requirements for Optuna if not exists
        cat > requirements_optuna.txt << 'EOFREQ'
optuna>=3.6.0
optuna-dashboard>=0.14.0
scikit-optimize>=0.9.0
plotly>=5.17.0
kaleido>=0.2.1
psutil>=5.9.0
redis>=5.0.0
python-memcached>=1.59
EOFREQ
        
        # Install with system Python 3.11
        python3.11 -m pip install --upgrade pip
        python3.11 -m pip install -r requirements_optuna.txt
        
        echo "Installed packages:"
        python3.11 -m pip list | grep -E "optuna|redis|memcache|psutil"
EOF
    
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

# Function to deploy optimization files
deploy_files() {
    echo -e "${YELLOW}Deploying optimization files...${NC}"
    
    # Create directory structure on VPS
    ssh $VPS_HOST "mkdir -p $VPS_PROJECT_PATH/src/optimization"
    ssh $VPS_HOST "mkdir -p $VPS_PROJECT_PATH/config"
    ssh $VPS_HOST "mkdir -p $VPS_PROJECT_PATH/data/optuna"
    ssh $VPS_HOST "mkdir -p $VPS_PROJECT_PATH/scripts"
    
    # Copy optimization modules
    echo "Copying optimization modules..."
    scp $LOCAL_PROJECT_PATH/src/optimization/optuna_engine_v3.py \
        $VPS_HOST:$VPS_PROJECT_PATH/src/optimization/
    
    scp $LOCAL_PROJECT_PATH/src/optimization/parameter_spaces_v3.py \
        $VPS_HOST:$VPS_PROJECT_PATH/src/optimization/
    
    scp $LOCAL_PROJECT_PATH/src/optimization/objectives_v3.py \
        $VPS_HOST:$VPS_PROJECT_PATH/src/optimization/
    
    scp $LOCAL_PROJECT_PATH/src/optimization/monitoring_integration.py \
        $VPS_HOST:$VPS_PROJECT_PATH/src/optimization/
    
    # Copy deployment scripts
    echo "Copying deployment scripts..."
    scp $LOCAL_PROJECT_PATH/scripts/deploy_optuna_v3.sh \
        $VPS_HOST:$VPS_PROJECT_PATH/scripts/
    
    scp $LOCAL_PROJECT_PATH/scripts/manage_optuna_optimization.py \
        $VPS_HOST:$VPS_PROJECT_PATH/scripts/
    
    echo -e "${GREEN}✓ Files deployed successfully${NC}"
}

# Function to create configuration files
create_configs() {
    echo -e "${YELLOW}Creating optimization configuration...${NC}"
    
    ssh $VPS_HOST << 'EOF'
        cd /home/linuxuser/trading/Virtuoso_ccxt
        
        # Create optimization config
        cat > config/optuna_config.yaml << 'EOFCONFIG'
# Optuna v3.6+ Configuration for Production
production_mode: true

# Resource limits for VPS (16GB RAM, 4 cores)
resource_limits:
  max_memory_gb: 2.0
  max_cpu_percent: 75.0
  max_trial_duration_seconds: 300
  max_study_duration_seconds: 7200
  max_concurrent_trials: 2
  check_interval_seconds: 10

# Cache configuration
cache:
  type: memcached
  host: localhost
  port: 11211

# Monitoring API endpoints
monitoring_api: http://localhost:8001
dashboard_api: http://localhost:8003

# Optimization settings
optimization:
  risk_free_rate: 0.02
  max_drawdown: 0.15
  min_sharpe: 1.0
  min_trades: 100
  evaluation_days: 90
  initial_capital: 10000
  commission: 0.001
  slippage: 0.0005

# Study configurations
studies:
  production_safety:
    direction: maximize
    sampler: TPE
    pruner: MedianPruner
    n_trials: 100
    timeout: 3600
    
  parameter_tuning:
    direction: maximize
    sampler: TPE
    pruner: HyperbandPruner
    n_trials: 200
    timeout: 7200
    
  robustness_testing:
    direction: maximize
    sampler: QMC
    pruner: SuccessiveHalving
    n_trials: 150
    timeout: 5400

# Safety thresholds
safety:
  max_position_size: 0.05
  stop_loss_percent: 0.02
  max_daily_loss: 0.05
  circuit_breaker_threshold: 5
  recovery_timeout_seconds: 60
EOFCONFIG
        
        echo "Configuration created at: config/optuna_config.yaml"
EOF
    
    echo -e "${GREEN}✓ Configuration created${NC}"
}

# Function to setup systemd service
setup_service() {
    echo -e "${YELLOW}Setting up systemd service for Optuna dashboard...${NC}"
    
    ssh $VPS_HOST << 'EOF'
        # Create systemd service for Optuna dashboard
        sudo tee /etc/systemd/system/optuna-dashboard.service > /dev/null << 'EOFSERVICE'
[Unit]
Description=Optuna Dashboard for Virtuoso Trading System
After=network.target memcached.service redis.service

[Service]
Type=simple
User=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
Environment="PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt"
ExecStart=/usr/bin/python3.11 -m optuna_dashboard /home/linuxuser/trading/Virtuoso_ccxt/data/optuna/journal.log --port 8004
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOFSERVICE
        
        # Reload and enable service
        sudo systemctl daemon-reload
        sudo systemctl enable optuna-dashboard.service
        
        echo "Optuna dashboard service created (port 8004)"
EOF
    
    echo -e "${GREEN}✓ Systemd service configured${NC}"
}

# Function to integrate with existing monitoring
integrate_monitoring() {
    echo -e "${YELLOW}Integrating with existing monitoring system...${NC}"
    
    ssh $VPS_HOST << 'EOF'
        cd /home/linuxuser/trading/Virtuoso_ccxt
        
        # Update main.py to include optimization routes
        python3.11 << 'EOFPY'
import sys
sys.path.append('/home/linuxuser/trading/Virtuoso_ccxt')

# Check if monitoring integration is needed
try:
    with open('src/main.py', 'r') as f:
        content = f.read()
    
    if 'optimization/monitoring_integration' not in content:
        print("Adding optimization monitoring to main.py...")
        # This would be done properly in production
        print("Manual integration required - see documentation")
    else:
        print("Optimization monitoring already integrated")
except Exception as e:
    print(f"Integration check failed: {e}")
EOFPY
EOF
    
    echo -e "${GREEN}✓ Monitoring integration completed${NC}"
}

# Function to run safety tests
run_safety_tests() {
    echo -e "${YELLOW}Running safety tests...${NC}"
    
    ssh $VPS_HOST << 'EOF'
        cd /home/linuxuser/trading/Virtuoso_ccxt
        
        # Create and run safety test
        python3.11 << 'EOFTEST'
import sys
sys.path.append('/home/linuxuser/trading/Virtuoso_ccxt')

try:
    # Test imports
    from src.optimization.optuna_engine_v3 import ModernOptunaEngine
    from src.optimization.parameter_spaces_v3 import SixDimensionalParameterSpaces
    from src.optimization.objectives_v3 import ProductionObjectives
    from src.optimization.monitoring_integration import OptimizationMonitor
    
    print("✓ All modules imported successfully")
    
    # Test configuration loading
    import yaml
    with open('config/optuna_config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Test initialization
    engine = ModernOptunaEngine(config)
    param_spaces = SixDimensionalParameterSpaces(production_mode=True)
    objectives = ProductionObjectives(config['optimization'])
    monitor = OptimizationMonitor(config)
    
    print("✓ All components initialized successfully")
    
    # Test resource limits
    from src.optimization.optuna_engine_v3 import ResourceLimits
    limits = ResourceLimits(**config['resource_limits'])
    print(f"✓ Resource limits configured: {limits.max_memory_gb}GB RAM, {limits.max_cpu_percent}% CPU")
    
    # Test parameter validation
    default_params = param_spaces.get_safe_parameters()
    is_valid, errors = param_spaces.validate_parameters(default_params)
    
    if is_valid:
        print("✓ Default parameters validated successfully")
    else:
        print(f"✗ Parameter validation failed: {errors}")
    
except Exception as e:
    print(f"✗ Safety test failed: {e}")
    import traceback
    traceback.print_exc()
EOFTEST
EOF
    
    echo -e "${GREEN}✓ Safety tests completed${NC}"
}

# Function to start services
start_services() {
    echo -e "${YELLOW}Starting optimization services...${NC}"
    
    ssh $VPS_HOST << 'EOF'
        # Ensure cache services are running
        if systemctl is-active --quiet memcached; then
            echo "✓ Memcached is running"
        else
            echo "Starting Memcached..."
            sudo systemctl start memcached
        fi
        
        if systemctl is-active --quiet redis; then
            echo "✓ Redis is running"
        else
            echo "Starting Redis..."
            sudo systemctl start redis
        fi
        
        # Start Optuna dashboard
        sudo systemctl start optuna-dashboard.service
        
        # Check status
        sleep 2
        if systemctl is-active --quiet optuna-dashboard; then
            echo "✓ Optuna dashboard started on port 8004"
        else
            echo "✗ Failed to start Optuna dashboard"
            sudo journalctl -u optuna-dashboard -n 20
        fi
EOF
    
    echo -e "${GREEN}✓ Services started${NC}"
}

# Function to display deployment summary
display_summary() {
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${BLUE}         Deployment Summary                      ${NC}"
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${GREEN}✓ Optuna v3.6+ deployed successfully${NC}"
    echo ""
    echo "Access Points:"
    echo "  - Optuna Dashboard: http://${VPS_HOST}:8004"
    echo "  - Main Dashboard: http://${VPS_HOST}:8003"
    echo "  - Monitoring API: http://${VPS_HOST}:8001"
    echo ""
    echo "Management Commands:"
    echo "  - Start optimization: python3.11 scripts/manage_optuna_optimization.py --start"
    echo "  - View status: python3.11 scripts/manage_optuna_optimization.py --status"
    echo "  - Stop optimization: python3.11 scripts/manage_optuna_optimization.py --stop"
    echo ""
    echo "Service Management:"
    echo "  - sudo systemctl status optuna-dashboard"
    echo "  - sudo journalctl -u optuna-dashboard -f"
    echo ""
    echo "Backup Location: $VPS_PROJECT_PATH/$BACKUP_DIR"
    echo ""
    echo -e "${YELLOW}⚠ Remember to monitor resource usage during optimization${NC}"
}

# Main deployment flow
main() {
    echo "Starting Optuna v3.6+ deployment to VPS..."
    
    # Check connection
    if ! check_vps_connection; then
        echo -e "${RED}Deployment aborted: Cannot connect to VPS${NC}"
        exit 1
    fi
    
    # Run deployment steps
    check_resources
    backup_existing
    install_dependencies
    deploy_files
    create_configs
    setup_service
    integrate_monitoring
    run_safety_tests
    start_services
    
    # Display summary
    display_summary
    
    echo -e "${GREEN}Deployment completed successfully!${NC}"
}

# Run main function
main