#!/usr/bin/env python3
"""
Deploy DI container fixes to VPS.
This script deploys the updated dependency injection registration
to support refactored monitoring components.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description=None, check=True):
    """Run a command with optional description."""
    if description:
        print(f"📋 {description}...")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0 and check:
        print(f"❌ Command failed: {command}")
        print(f"Error: {result.stderr}")
        return False
    
    if result.stdout:
        print(result.stdout)
    
    return True

def main():
    """Deploy DI fixes to VPS."""
    print("🚀 Deploying DI Container Fixes for Refactored Components...")
    
    # Check if we're in the right directory
    if not Path("src/core/di/registration.py").exists():
        print("❌ Please run this script from the Virtuoso_ccxt root directory")
        return 1
    
    # Ensure local changes are saved
    print("💾 Saving local changes...")
    run_command("git add src/core/di/registration.py", "Adding DI registration changes")
    
    # Deploy to VPS
    vps_commands = [
        "cd /home/linuxuser/trading/Virtuoso_ccxt/",
        "git pull origin main",
        "sudo systemctl stop virtuoso.service",
        "sleep 2",
        "sudo systemctl start virtuoso.service",
        "sleep 5",
        "sudo systemctl status virtuoso.service --no-pager -l",
    ]
    
    vps_command = " && ".join(vps_commands)
    
    print("🌐 Deploying to VPS...")
    if not run_command(f'ssh linuxuser@45.77.40.77 "{vps_command}"', "Executing VPS deployment"):
        print("❌ VPS deployment failed")
        return 1
    
    # Verify deployment
    print("🔍 Verifying deployment...")
    log_command = 'ssh linuxuser@45.77.40.77 "sudo journalctl -u virtuoso.service --since \\"5 minutes ago\\" -n 50 --no-pager"'
    
    if run_command(log_command, "Checking service logs", check=False):
        print("✅ Deployment completed successfully!")
        print("\n📊 To monitor the service:")
        print("ssh linuxuser@45.77.40.77")
        print("sudo journalctl -u virtuoso.service -f")
        return 0
    else:
        print("⚠️ Deployment may have issues. Check logs manually:")
        print("ssh linuxuser@45.77.40.77")
        print("sudo journalctl -u virtuoso.service -f")
        return 1

if __name__ == "__main__":
    sys.exit(main())