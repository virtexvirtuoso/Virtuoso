#!/usr/bin/env python3
"""Safely restart the Virtuoso Trading application with all fixes applied."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

def find_application_process():
    """Find the running application process."""
    try:
        # Look for the main application process
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'src/main.py' in line and 'python' in line.lower():
                parts = line.split()
                if len(parts) > 1:
                    return int(parts[1])  # PID is the second column
        return None
    except Exception as e:
        print(f"Error finding process: {e}")
        return None

def stop_application():
    """Stop the running application gracefully."""
    pid = find_application_process()
    if not pid:
        print("✅ No application process found running")
        return True
    
    print(f"🛑 Stopping application (PID: {pid})")
    
    try:
        # Send SIGTERM for graceful shutdown
        os.kill(pid, signal.SIGTERM)
        
        # Wait for process to stop
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            if not find_application_process():
                print("✅ Application stopped gracefully")
                return True
            print(f"⏳ Waiting for graceful shutdown... ({i+1}/30)")
        
        # If still running, force kill
        if find_application_process():
            print("⚠️ Forcing application shutdown...")
            os.kill(pid, signal.SIGKILL)
            time.sleep(2)
            
            if not find_application_process():
                print("✅ Application force-stopped")
                return True
            else:
                print("❌ Failed to stop application")
                return False
                
    except ProcessLookupError:
        print("✅ Application already stopped")
        return True
    except Exception as e:
        print(f"❌ Error stopping application: {e}")
        return False

def start_application():
    """Start the application with optimized settings."""
    print("🚀 Starting application with optimized settings...")
    
    # Change to project directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Activate virtual environment and start application
    try:
        # Start the application in the background
        process = subprocess.Popen(
            ['python', 'src/main.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid  # Create new process group
        )
        
        # Wait a moment to see if it starts successfully
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print(f"✅ Application started successfully (PID: {process.pid})")
            print("🌐 Dashboard will be available at: http://localhost:8003/dashboard")
            print("📊 API endpoints available at: http://localhost:8003/api")
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Application failed to start")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        return False

def main():
    """Main restart function."""
    print("🔄 Restarting Virtuoso Trading Application")
    print("=" * 50)
    
    # Summary of fixes applied
    print("📋 Applied Fixes Summary:")
    print("✅ Fixed WebSocket connections - Market Data Manager accessible")
    print("✅ Fixed database connection - InfluxDB token and bucket corrected")
    print("✅ Optimized CPU usage - Reduced monitoring frequencies")
    print("✅ Changed log level from DEBUG to INFO")
    print("✅ Increased update intervals to reduce system load")
    print()
    
    # Stop current application
    if not stop_application():
        print("❌ Failed to stop application. Please stop it manually.")
        return False
    
    # Brief pause
    print("⏳ Waiting 5 seconds before restart...")
    time.sleep(5)
    
    # Start application
    if not start_application():
        print("❌ Failed to start application")
        return False
    
    print("\n🎉 Application restart completed successfully!")
    print("\n📊 Dashboard Status Check:")
    print("- Dashboard URL: http://localhost:8003/dashboard")
    print("- API Status: http://localhost:8003/api/health")
    print("- WebSocket Status: http://localhost:8003/api/websocket/status")
    print("- Database Status: Should now be connected to InfluxDB")
    
    print("\n⚡ Performance Improvements:")
    print("- CPU usage should be significantly reduced")
    print("- Less verbose logging (INFO level instead of DEBUG)")
    print("- Optimized monitoring intervals")
    print("- WebSocket connections should work properly")
    
    print("\n🔍 Monitor the application with:")
    print("- ps aux | grep 'src/main.py' (check if running)")
    print("- curl http://localhost:8003/api/health (health check)")
    print("- curl http://localhost:8003/api/websocket/status (WebSocket status)")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 