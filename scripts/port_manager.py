#!/usr/bin/env python3
"""
Port management utility for Virtuoso Trading System.
Helps identify and resolve port conflicts.
"""

import os
import sys
import subprocess
import socket
import argparse
import yaml
from pathlib import Path
from typing import List, Optional

def check_port_in_use(port: int) -> bool:
    """Check if a port is currently in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex(('localhost', port))
        return result == 0

def find_process_using_port(port: int) -> Optional[str]:
    """Find which process is using a specific port."""
    try:
        result = subprocess.run(
            ['lsof', '-i', f':{port}'],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # Skip header line
                return lines[1]  # Return first process line
        return None
    except Exception as e:
        print(f"Error checking port {port}: {e}")
        return None

def kill_process_on_port(port: int) -> bool:
    """Kill the process using a specific port."""
    try:
        # Get PIDs using the port
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid.strip():
                    print(f"Killing process {pid} using port {port}")
                    subprocess.run(['kill', '-9', pid.strip()], check=True)
            return True
        else:
            print(f"No process found using port {port}")
            return False
            
    except Exception as e:
        print(f"Error killing process on port {port}: {e}")
        return False

def find_available_port(start_port: int = 8000, max_attempts: int = 100) -> Optional[int]:
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        if not check_port_in_use(port):
            return port
    return None

def get_config_path() -> Path:
    """Get the path to the config.yaml file."""
    # Try to find config.yaml relative to script location
    script_dir = Path(__file__).parent
    config_path = script_dir.parent / "config" / "config.yaml"
    
    if config_path.exists():
        return config_path
    
    # Fallback to current directory
    config_path = Path("config/config.yaml")
    if config_path.exists():
        return config_path
    
    raise FileNotFoundError("Could not find config/config.yaml file")

def read_config() -> dict:
    """Read the current configuration from config.yaml."""
    try:
        config_path = get_config_path()
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error reading config: {e}")
        return {}

def update_config_port(new_port: int) -> bool:
    """Update the web server port in config.yaml."""
    try:
        config_path = get_config_path()
        config = read_config()
        
        # Ensure web_server section exists
        if 'web_server' not in config:
            config['web_server'] = {}
        
        # Update the port
        config['web_server']['port'] = new_port
        
        # Write back to file
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ Updated config.yaml: web_server.port = {new_port}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating config: {e}")
        return False

def get_current_config_port() -> int:
    """Get the current port from config.yaml."""
    config = read_config()
    return config.get('web_server', {}).get('port', 8000)

def main():
    parser = argparse.ArgumentParser(description='Port management utility for Virtuoso Trading System')
    parser.add_argument('--check', type=int, help='Check if a specific port is in use')
    parser.add_argument('--kill', type=int, help='Kill process using a specific port')
    parser.add_argument('--find-available', type=int, default=8000, help='Find available port starting from specified port')
    parser.add_argument('--list-virtuoso', action='store_true', help='List all Virtuoso-related processes')
    parser.add_argument('--update-config', type=int, help='Update config.yaml with new port')
    parser.add_argument('--show-config', action='store_true', help='Show current web server configuration')
    parser.add_argument('--auto-fix', action='store_true', help='Automatically find and set available port in config')
    
    args = parser.parse_args()
    
    if args.show_config:
        config = read_config()
        web_config = config.get('web_server', {})
        print("Current web server configuration:")
        print(f"  Host: {web_config.get('host', '0.0.0.0')}")
        print(f"  Port: {web_config.get('port', 8000)}")
        print(f"  Auto fallback: {web_config.get('auto_fallback', True)}")
        print(f"  Fallback ports: {web_config.get('fallback_ports', [8001, 8002, 8080, 3000, 5000])}")
    
    elif args.update_config:
        new_port = args.update_config
        if update_config_port(new_port):
            print(f"✅ Configuration updated successfully")
            if check_port_in_use(new_port):
                print(f"⚠️  Warning: Port {new_port} is currently in use")
        else:
            print(f"❌ Failed to update configuration")
    
    elif args.auto_fix:
        current_port = get_current_config_port()
        if not check_port_in_use(current_port):
            print(f"✅ Current port {current_port} is available, no changes needed")
        else:
            print(f"🔍 Current port {current_port} is in use, finding alternative...")
            available_port = find_available_port(current_port)
            if available_port:
                if update_config_port(available_port):
                    print(f"✅ Auto-fixed: Updated config to use port {available_port}")
                else:
                    print(f"❌ Found available port {available_port} but failed to update config")
            else:
                print(f"❌ No available ports found starting from {current_port}")
    
    elif args.check:
        port = args.check
        if check_port_in_use(port):
            process_info = find_process_using_port(port)
            print(f"❌ Port {port} is IN USE")
            if process_info:
                print(f"Process: {process_info}")
        else:
            print(f"✅ Port {port} is AVAILABLE")
    
    elif args.kill:
        port = args.kill
        if kill_process_on_port(port):
            print(f"✅ Successfully killed process(es) using port {port}")
        else:
            print(f"❌ Failed to kill process using port {port}")
    
    elif args.find_available:
        start_port = args.find_available
        available_port = find_available_port(start_port)
        if available_port:
            print(f"✅ Available port found: {available_port}")
            print(f"To use this port, run: python scripts/port_manager.py --update-config {available_port}")
        else:
            print(f"❌ No available ports found starting from {start_port}")
    
    elif args.list_virtuoso:
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                check=True
            )
            
            virtuoso_processes = []
            for line in result.stdout.split('\n'):
                if 'virtuoso' in line.lower() or 'main.py' in line:
                    virtuoso_processes.append(line)
            
            if virtuoso_processes:
                print("Virtuoso-related processes:")
                for process in virtuoso_processes:
                    print(f"  {process}")
            else:
                print("No Virtuoso-related processes found")
                
        except Exception as e:
            print(f"Error listing processes: {e}")
    
    else:
        # Default behavior - check current config and common ports
        current_port = get_current_config_port()
        print(f"Current configured port: {current_port}")
        
        common_ports = [current_port, 8000, 8001, 8080, 3000, 5000]
        # Remove duplicates while preserving order
        seen = set()
        common_ports = [x for x in common_ports if not (x in seen or seen.add(x))]
        
        print("Checking ports:")
        
        for port in common_ports:
            if check_port_in_use(port):
                process_info = find_process_using_port(port)
                print(f"❌ Port {port}: IN USE")
                if process_info:
                    print(f"   Process: {process_info}")
            else:
                print(f"✅ Port {port}: AVAILABLE")
        
        # Find next available port
        available_port = find_available_port(current_port)
        if available_port and available_port != current_port:
            print(f"\n💡 Recommended available port: {available_port}")
            print(f"   To use: python scripts/port_manager.py --update-config {available_port}")
            print(f"   Or auto-fix: python scripts/port_manager.py --auto-fix")

if __name__ == "__main__":
    main() 