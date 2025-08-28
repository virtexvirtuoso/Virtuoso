#!/usr/bin/env python3
"""Enhanced System Status Monitor with Process Identification"""

import subprocess
import psutil
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# Process identification mappings
PROCESS_MAPPINGS = {
    # Core Services
    'src/main.py': 'Main Trading Engine',
    'src/web_server.py': 'Web Dashboard Server',
    
    # Cache Services
    'ticker_cache_service.py': 'Price Ticker Cache Manager',
    'sync_real_confluence_scores.py': 'Confluence Cache Sync Service',
    'aggregate_confluence_cache.py': 'Confluence Aggregator Service',
    
    # Bitcoin Beta Services
    'bitcoin_beta_data_service_dynamic.py': 'Bitcoin Beta Dynamic Data Service',
    'bitcoin_beta_data_service.py': 'Bitcoin Beta Data Service',
    'bitcoin_beta_calculator_service.py': 'Bitcoin Beta Calculator Service',
    
    # Mobile Dashboard
    'fix_mobile_dashboard_final.py': 'Mobile Dashboard Service',
    
    # Monitoring Services
    'health_monitor.py': 'System Health Monitor',
    'resource_monitor.py': 'Resource Usage Monitor',
    'cache_monitor_fix.py': 'Cache Performance Monitor',
    
    # Security Services
    'fail2ban-server': 'Fail2ban Security Service',
    
    # System Services
    'unattended-upgr': 'System Update Service',
    
    # Web Server Workers
    'uvicorn': 'Web Server Worker',
}

def get_process_name(cmd_line: str, exe: str = '') -> str:
    """Identify process by command line"""
    cmd_lower = ' '.join(cmd_line).lower() if cmd_line else exe.lower()
    
    # Check exact mappings
    for pattern, name in PROCESS_MAPPINGS.items():
        if pattern.lower() in cmd_lower:
            return name
    
    # Check for worker processes
    if 'main.py' in cmd_lower and '--worker' in cmd_lower:
        return 'Main Trading Engine (Worker Process)'
    elif 'main.py' in cmd_lower:
        return 'Main Trading Engine (Primary Process)'
    
    # Default to exe name
    if 'python' in exe.lower():
        return 'Unknown Python Process'
    return os.path.basename(exe) if exe else 'Unknown Process'

def check_websocket_status() -> Dict:
    """Check WebSocket connection and log status"""
    ws_status = {
        'connected': False,
        'log_exists': False,
        'log_size': 0,
        'last_entry': None
    }
    
    log_path = '/home/linuxuser/trading/Virtuoso_ccxt/logs/websocket.log'
    
    # Check if log file exists
    if os.path.exists(log_path):
        ws_status['log_exists'] = True
        ws_status['log_size'] = os.path.getsize(log_path)
        
        # Get last log entry if file has content
        if ws_status['log_size'] > 0:
            try:
                result = subprocess.run(
                    ['tail', '-1', log_path],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    ws_status['last_entry'] = result.stdout.strip()
            except:
                pass
    
    # Check WebSocket connections via netstat
    try:
        result = subprocess.run(
            ['netstat', '-an'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Check for WebSocket connections (wss typically on port 443 or 9443)
            if 'ESTABLISHED' in result.stdout and ('443' in result.stdout or '9443' in result.stdout):
                ws_status['connected'] = True
    except:
        pass
    
    return ws_status

def get_python_processes() -> List[Dict]:
    """Get all Python processes with enhanced identification"""
    processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
        try:
            info = proc.info
            if 'python' in info['name'].lower():
                cmd_line = info.get('cmdline', [])
                process_name = get_process_name(cmd_line, info['name'])
                
                processes.append({
                    'pid': info['pid'],
                    'name': process_name,
                    'cpu': info.get('cpu_percent', 0),
                    'memory': info.get('memory_percent', 0),
                    'cmd': ' '.join(cmd_line) if cmd_line else info['name']
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return sorted(processes, key=lambda x: x['pid'])

def print_status_report():
    """Print comprehensive system status"""
    print("\n" + "="*60)
    print("     VIRTUOSO TRADING SYSTEM - ENHANCED STATUS REPORT")
    print("="*60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Python Processes
    print("🐍 Python Process Status")
    print("─" * 25)
    
    processes = get_python_processes()
    total_cpu = 0
    total_mem = 0
    
    for proc in processes:
        status_icon = "●" if proc['cpu'] > 0 else "○"
        print(f"  {status_icon} {proc['name']}")
        print(f"    PID: {proc['pid']} | CPU: {proc['cpu']:.1f}% | Memory: {proc['memory']:.1f}%")
        total_cpu += proc['cpu']
        total_mem += proc['memory']
    
    print(f"\n📈 Process Summary")
    print("─" * 20)
    print(f"Total Python:    {len(processes)} processes")
    print(f"Combined CPU:    {total_cpu:.1f}%")
    print(f"Combined Memory: {total_mem:.1f}%")
    
    # WebSocket Status
    print(f"\n🌐 WebSocket Status")
    print("─" * 20)
    
    ws_status = check_websocket_status()
    
    if ws_status['log_exists']:
        if ws_status['log_size'] > 0:
            print(f"Log File:        ✅ EXISTS ({ws_status['log_size']} bytes)")
            if ws_status['last_entry']:
                print(f"Last Entry:      {ws_status['last_entry'][:50]}...")
        else:
            print(f"Log File:        ⚠️  EMPTY (0 bytes)")
    else:
        print(f"Log File:        ❌ NOT FOUND")
    
    if ws_status['connected']:
        print(f"Connection:      ✅ ACTIVE")
    else:
        print(f"Connection:      ⚠️  NO ACTIVE CONNECTIONS DETECTED")
    
    # Service Status
    print(f"\n⚙️  Service Status")
    print("─" * 20)
    
    services = [
        'virtuoso.service',
        'virtuoso-web.service',
        'virtuoso-cache.service',
        'virtuoso-ticker.service'
    ]
    
    for service in services:
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service],
                capture_output=True,
                text=True,
                timeout=2
            )
            status = result.stdout.strip()
            icon = "✅" if status == "active" else "❌"
            print(f"{service:30} {icon} {status.upper()}")
        except:
            print(f"{service:30} ⚠️  UNKNOWN")
    
    print("\n" + "="*60)
    print("Report Complete\n")

if __name__ == "__main__":
    print_status_report()