#!/usr/bin/env python3
"""
Fix port configuration to prevent conflicts
"""

import yaml
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def fix_port_config():
    """Update config.yaml to use different ports for each service"""
    
    config_file = project_root / "config" / "config.yaml"
    
    # Read current config
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    # Update ports
    if 'api' not in config:
        config['api'] = {}
    
    # Set API port (used by main.py)
    config['api']['port'] = 8003
    config['api']['host'] = '0.0.0.0'
    
    # Set web server port (different from API)
    if 'web_server' not in config:
        config['web_server'] = {}
    
    config['web_server']['port'] = 8001  # Different from API port!
    config['web_server']['host'] = '0.0.0.0'
    config['web_server']['auto_fallback'] = True
    config['web_server']['fallback_ports'] = [8002, 8080, 3000, 5000]
    
    # Write back
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"✅ Updated port configuration:")
    print(f"   - API (main.py): {config['api']['port']}")
    print(f"   - Web Server: {config['web_server']['port']}")
    print(f"   - Fallback ports: {config['web_server']['fallback_ports']}")
    
    # Create systemd service files
    create_service_files()

def create_service_files():
    """Create proper systemd service files"""
    
    # Main service
    main_service = """[Unit]
Description=Virtuoso Trading System
After=network.target

[Service]
Type=simple
User=linuxuser
Group=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
Environment="PATH=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt"
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python -u src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    # Web service  
    web_service = """[Unit]
Description=Virtuoso Trading Web Dashboard
After=network.target virtuoso.service
Requires=virtuoso.service

[Service]
Type=simple
User=linuxuser
Group=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
Environment="PATH=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/uvicorn src.web_server:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    
    # Save service files
    services_dir = project_root / "scripts" / "systemd"
    services_dir.mkdir(exist_ok=True)
    
    with open(services_dir / "virtuoso.service", 'w') as f:
        f.write(main_service)
    
    with open(services_dir / "virtuoso-web.service", 'w') as f:
        f.write(web_service)
    
    print("\n✅ Created systemd service files:")
    print(f"   - {services_dir}/virtuoso.service")
    print(f"   - {services_dir}/virtuoso-web.service")
    
    print("\nTo install on VPS:")
    print("1. Copy service files to VPS")
    print("2. sudo cp virtuoso*.service /etc/systemd/system/")
    print("3. sudo systemctl daemon-reload")
    print("4. sudo systemctl enable virtuoso virtuoso-web")
    print("5. sudo systemctl start virtuoso virtuoso-web")

if __name__ == "__main__":
    fix_port_config()