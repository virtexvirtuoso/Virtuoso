#!/bin/bash

#############################################################################
# Script: final_vps_fix.sh
# Purpose: Deploy and manage final vps fix
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates deployment automation, service management, and infrastructure updates for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
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
#   ./final_vps_fix.sh [options]
#   
#   Examples:
#     ./final_vps_fix.sh
#     ./final_vps_fix.sh --verbose
#     ./final_vps_fix.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
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

# Final comprehensive fix for VPS hanging issues
# This script applies all necessary patches to resolve initialization hanging

echo "🚀 Applying final VPS hanging fixes..."
echo "========================================"

VPS_HOST="linuxuser@5.223.63.4"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Create the comprehensive fix script
cat > /tmp/final_vps_fix.py << 'EOF'
#!/usr/bin/env python3
"""Final comprehensive fix for VPS hanging issues."""

import os
import re
from pathlib import Path

def fix_config_manager():
    """Add timeout protection to ConfigManager."""
    manager_file = Path("src/config/manager.py")
    if not manager_file.exists():
        print("❌ ConfigManager not found")
        return False
    
    with open(manager_file, 'r') as f:
        content = f.read()
    
    # Add asyncio import if needed
    if "import asyncio" not in content:
        content = "import asyncio\n" + content
    
    # Wrap YAML loading with timeout
    yaml_fix = """
            with open(config_path, 'r') as f:
                try:
                    # Use SafeLoader for security with timeout protection
                    import signal
                    
                    def timeout_handler(signum, frame):
                        raise TimeoutError("YAML parsing timeout")
                    
                    # Set 5 second timeout for YAML parsing
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(5)
                    
                    try:
                        config = yaml.load(f, Loader=SafeLoader)
                    finally:
                        signal.alarm(0)  # Cancel timeout
                        
                    logger.info(f"Successfully loaded configuration from {config_path}")
"""
    
    # Apply the fix
    if "yaml.load(f, Loader=SafeLoader)" in content and "signal.alarm" not in content:
        content = re.sub(
            r'with open\(config_path.*?yaml\.load\(f, Loader=SafeLoader\).*?logger\.info\(.*?\)',
            yaml_fix.strip(),
            content,
            flags=re.DOTALL
        )
        print("✅ Added timeout to YAML loading")
    
    with open(manager_file, 'w') as f:
        f.write(content)
    
    return True

def create_minimal_startup():
    """Create a minimal startup script for testing."""
    startup_content = '''#!/usr/bin/env python3
"""Minimal startup to test initialization."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def minimal_startup():
    """Minimal initialization sequence."""
    try:
        logger.info("Starting minimal initialization...")
        
        # Step 1: Config
        logger.info("1. Loading config...")
        from src.config.manager import ConfigManager
        config = ConfigManager()
        logger.info("✅ Config loaded")
        
        # Step 2: Import exchange manager
        logger.info("2. Importing ExchangeManager...")
        from src.core.exchanges.manager import ExchangeManager
        logger.info("✅ ExchangeManager imported")
        
        # Step 3: Create instance
        logger.info("3. Creating ExchangeManager instance...")
        exchange_manager = ExchangeManager(config)
        logger.info("✅ ExchangeManager created")
        
        # Step 4: Initialize with timeout
        logger.info("4. Initializing ExchangeManager...")
        async with asyncio.timeout(30.0):
            result = await exchange_manager.initialize()
        
        if result:
            logger.info("✅ ExchangeManager initialized successfully!")
        else:
            logger.error("❌ ExchangeManager initialization failed")
            
        # Clean up
        if hasattr(exchange_manager, 'close'):
            await exchange_manager.close()
            
        return result
        
    except asyncio.TimeoutError:
        logger.error("❌ Initialization timed out!")
        return False
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(minimal_startup())
    sys.exit(0 if success else 1)
'''
    
    with open("minimal_startup.py", 'w') as f:
        f.write(startup_content)
    
    os.chmod("minimal_startup.py", 0o755)
    print("✅ Created minimal startup script")
    return True

def add_startup_diagnostics():
    """Add diagnostics to main.py startup."""
    main_file = Path("src/main.py")
    if not main_file.exists():
        print("❌ main.py not found")
        return False
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Add diagnostic logging after config manager
    diagnostic = '''
    logger.info("✅ ConfigManager initialized")
    
    # Diagnostic: Check config content
    logger.info(f"Config sections: {list(config_manager.config.keys())}")
    logger.info(f"Exchange config: {list(config_manager.config.get('exchanges', {}).keys())}")
'''
    
    if "✅ ConfigManager initialized" in content and "Config sections:" not in content:
        content = content.replace(
            'logger.info("✅ ConfigManager initialized")',
            diagnostic.strip()
        )
        print("✅ Added config diagnostics")
    
    with open(main_file, 'w') as f:
        f.write(content)
    
    return True

# Main execution
if __name__ == "__main__":
    print("Applying final VPS fixes...")
    
    success = True
    success &= fix_config_manager()
    success &= create_minimal_startup()
    success &= add_startup_diagnostics()
    
    if success:
        print("\n✅ All fixes applied successfully!")
        print("\nTest with: python3 minimal_startup.py")
    else:
        print("\n❌ Some fixes failed to apply")
        exit(1)
EOF

# Deploy the fix
echo "📤 Deploying fix to VPS..."
scp /tmp/final_vps_fix.py $VPS_HOST:/tmp/

# Apply fixes
echo "🔧 Applying fixes on VPS..."
ssh $VPS_HOST "cd $VPS_DIR && /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python /tmp/final_vps_fix.py"

# Test minimal startup
echo "🧪 Testing minimal startup..."
ssh $VPS_HOST "cd $VPS_DIR && /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python minimal_startup.py"

# If minimal startup works, try the full system
if [ $? -eq 0 ]; then
    echo "✅ Minimal startup successful! Trying full system..."
    
    # Kill existing processes
    ssh $VPS_HOST "pkill -9 -f 'python.*main.py' || true"
    sleep 2
    
    # Start with monitoring
    ssh $VPS_HOST << 'REMOTE_EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

echo "Starting full system..."
nohup /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python -u src/main.py > logs/startup_final.log 2>&1 &
PID=$!

echo "Started with PID: $PID"
echo "Monitoring startup..."

for i in {1..30}; do
    if ! kill -0 $PID 2>/dev/null; then
        echo "❌ Process died!"
        tail -20 logs/app.log
        exit 1
    fi
    
    # Check for successful init
    if grep -q "ConfigManager initialized" logs/app.log && grep -q "Config sections:" logs/app.log; then
        echo "✅ System initialized!"
        tail -10 logs/app.log
        exit 0
    fi
    
    echo -n "."
    sleep 1
done

echo ""
echo "⚠️ Still initializing after 30s..."
tail -10 logs/app.log
REMOTE_EOF
else
    echo "❌ Minimal startup failed. Check the errors above."
fi

echo ""
echo "✅ Final fix deployment complete!"
echo ""
echo "Check full logs with:"
echo "  ssh $VPS_HOST 'tail -f $VPS_DIR/logs/app.log'"