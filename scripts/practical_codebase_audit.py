#!/usr/bin/env python3
"""
Practical Codebase Audit - Focuses on real issues that affect functionality
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import importlib.util
import yaml
import json

class PracticalAuditor:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.issues = []
        self.fixes_applied = []
        
    def run_command(self, cmd):
        """Run shell command and return output"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout, result.stderr, result.returncode
        except:
            return "", "Error running command", 1
    
    def check_environment(self):
        """Check Python environment and dependencies"""
        print("\n🔍 Checking Environment...")
        
        # Check Python version
        python_version = sys.version_info
        if python_version.major == 3 and python_version.minor >= 11:
            print(f"✅ Python version: {sys.version.split()[0]}")
        else:
            print(f"❌ Python version: {sys.version.split()[0]} (Need 3.11+)")
            self.issues.append("Python version should be 3.11 or higher")
        
        # Check virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("✅ Running in virtual environment")
        else:
            print("⚠️  Not running in virtual environment")
            self.issues.append("Not running in virtual environment")
        
        # Check critical dependencies
        critical_deps = {
            'fastapi': 'Web framework',
            'uvicorn': 'ASGI server',
            'pybit': 'Bybit API',
            'ccxt': 'Exchange library',
            'pandas': 'Data analysis',
            'pydantic': 'Data validation',
            'aiohttp': 'Async HTTP',
            'websockets': 'WebSocket client',
            'sqlalchemy': 'Database ORM',
            'ta': 'Technical analysis'
        }
        
        print("\n📦 Checking dependencies...")
        missing_deps = []
        for package, description in critical_deps.items():
            spec = importlib.util.find_spec(package)
            if spec is None:
                print(f"❌ {package:<15} - {description} (MISSING)")
                missing_deps.append(package)
            else:
                print(f"✅ {package:<15} - {description}")
        
        if missing_deps:
            self.issues.append(f"Missing dependencies: {', '.join(missing_deps)}")
    
    def check_configuration(self):
        """Check configuration files"""
        print("\n🔍 Checking Configuration...")
        
        # Check config.yaml
        config_path = self.project_root / "config" / "config.yaml"
        if config_path.exists():
            print("✅ config.yaml found")
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Check critical sections
                if 'database' in config and config['database'].get('url'):
                    print("✅ Database configured")
                else:
                    print("⚠️  Database not configured")
                    self.issues.append("Database URL not configured")
                
                # Check exchanges
                exchanges_enabled = []
                for exchange, settings in config.get('exchanges', {}).items():
                    if settings.get('enabled'):
                        exchanges_enabled.append(exchange)
                
                if exchanges_enabled:
                    print(f"✅ Exchanges enabled: {', '.join(exchanges_enabled)}")
                else:
                    print("⚠️  No exchanges enabled")
                    self.issues.append("No exchanges enabled in config")
                
                # Check web server port
                port = config.get('web_server', {}).get('port', 8000)
                print(f"✅ Web server port: {port}")
                
            except Exception as e:
                print(f"❌ Error reading config.yaml: {e}")
                self.issues.append(f"Config error: {e}")
        else:
            print("❌ config.yaml not found")
            self.issues.append("config.yaml missing")
        
        # Check .env file
        env_path = self.project_root / "config" / "env" / ".env"
        if env_path.exists():
            print("✅ .env file found")
        else:
            print("⚠️  .env file not found (API keys should be here)")
    
    def check_api_endpoints(self):
        """Check if API endpoints are properly registered"""
        print("\n🔍 Checking API Routes...")
        
        routes_init = self.project_root / "src" / "api" / "__init__.py"
        if routes_init.exists():
            with open(routes_init, 'r') as f:
                content = f.read()
            
            required_routes = [
                'dashboard', 'system', 'market', 'trading',
                'alpha', 'liquidation', 'signal_tracking'
            ]
            
            for route in required_routes:
                if route in content:
                    print(f"✅ {route} routes registered")
                else:
                    print(f"❌ {route} routes not registered")
                    self.issues.append(f"{route} routes not registered in API")
    
    def check_critical_files(self):
        """Check for critical files that must exist"""
        print("\n🔍 Checking Critical Files...")
        
        critical_files = {
            "src/main.py": "Main application entry",
            "src/monitoring/monitor.py": "Market monitor",
            "src/core/exchanges/manager.py": "Exchange manager",
            "src/core/analysis/confluence.py": "Confluence analyzer",
            "src/dashboard/templates/dashboard_v10.html": "Dashboard UI",
            "src/monitoring/alert_manager.py": "Alert system",
            "src/utils/indicators.py": "Technical indicators"
        }
        
        for file_path, description in critical_files.items():
            full_path = self.project_root / file_path
            if full_path.exists():
                print(f"✅ {description:<25} - {file_path}")
            else:
                print(f"❌ {description:<25} - {file_path} (MISSING)")
                self.issues.append(f"Missing critical file: {file_path}")
    
    def check_database(self):
        """Check database connectivity"""
        print("\n🔍 Checking Database...")
        
        # Check if database file exists (for SQLite)
        db_path = self.project_root / "data" / "trading.db"
        if db_path.exists():
            print(f"✅ Database file exists: {db_path}")
            # Check size
            size_mb = db_path.stat().st_size / (1024 * 1024)
            print(f"   Size: {size_mb:.1f} MB")
        else:
            print("ℹ️  No local database file (might be using remote DB)")
    
    def check_logs(self):
        """Check log directory and recent errors"""
        print("\n🔍 Checking Logs...")
        
        logs_dir = self.project_root / "logs"
        if logs_dir.exists():
            log_files = list(logs_dir.glob("*.log"))
            print(f"✅ Logs directory exists ({len(log_files)} log files)")
            
            # Check for recent errors in logs
            recent_log = max(log_files, key=os.path.getctime) if log_files else None
            if recent_log:
                print(f"   Most recent log: {recent_log.name}")
                
                # Count errors in recent log
                error_count = 0
                with open(recent_log, 'r') as f:
                    for line in f:
                        if 'ERROR' in line or 'CRITICAL' in line:
                            error_count += 1
                
                if error_count > 0:
                    print(f"   ⚠️  Found {error_count} errors in recent log")
                else:
                    print(f"   ✅ No errors in recent log")
        else:
            print("⚠️  No logs directory")
    
    def check_processes(self):
        """Check for running processes"""
        print("\n🔍 Checking Running Processes...")
        
        # Check if main.py is running
        stdout, _, _ = self.run_command("ps aux | grep 'python.*main.py' | grep -v grep")
        if stdout:
            print("✅ Application is running")
            for line in stdout.strip().split('\n'):
                parts = line.split()
                if len(parts) > 10:
                    pid = parts[1]
                    cpu = parts[2]
                    mem = parts[3]
                    print(f"   PID: {pid}, CPU: {cpu}%, Memory: {mem}%")
        else:
            print("ℹ️  Application is not running")
    
    def check_port_availability(self):
        """Check if required ports are available"""
        print("\n🔍 Checking Port Availability...")
        
        ports = [8000, 8001, 8002, 8003]
        for port in ports:
            stdout, _, returncode = self.run_command(f"lsof -i :{port}")
            if returncode == 0 and stdout:
                print(f"⚠️  Port {port} is in use")
            else:
                print(f"✅ Port {port} is available")
    
    def suggest_fixes(self):
        """Suggest fixes for found issues"""
        if self.issues:
            print("\n🔧 Suggested Fixes:")
            
            if "Missing dependencies" in str(self.issues):
                print("\n1. Install missing dependencies:")
                print("   pip install -r requirements.txt")
            
            if "Database URL not configured" in str(self.issues):
                print("\n2. Configure database in config/config.yaml:")
                print("   database:")
                print("     url: sqlite:///data/trading.db")
            
            if "No exchanges enabled" in str(self.issues):
                print("\n3. Enable exchange in config/config.yaml:")
                print("   exchanges:")
                print("     bybit:")
                print("       enabled: true")
            
            if "config.yaml missing" in str(self.issues):
                print("\n4. Copy config template:")
                print("   cp config/config.example.yaml config/config.yaml")
            
            if ".env file not found" in str(self.issues):
                print("\n5. Create .env file:")
                print("   mkdir -p config/env")
                print("   echo 'BYBIT_API_KEY=your_key' > config/env/.env")
                print("   echo 'BYBIT_API_SECRET=your_secret' >> config/env/.env")
    
    def generate_report(self):
        """Generate audit report"""
        print("\n" + "="*70)
        print("PRACTICAL AUDIT SUMMARY")
        print("="*70)
        
        if not self.issues:
            print("✅ No critical issues found! The codebase appears to be properly configured.")
        else:
            print(f"❌ Found {len(self.issues)} issues that need attention:\n")
            for i, issue in enumerate(self.issues, 1):
                print(f"{i}. {issue}")
        
        # Save report
        report = {
            "timestamp": datetime.now().isoformat(),
            "issues": self.issues,
            "fixes_applied": self.fixes_applied
        }
        
        report_path = self.project_root / "test_output" / f"practical_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved to: {report_path}")
    
    def run(self):
        """Run the practical audit"""
        print("🚀 Running Practical Codebase Audit...\n")
        
        self.check_environment()
        self.check_configuration()
        self.check_api_endpoints()
        self.check_critical_files()
        self.check_database()
        self.check_logs()
        self.check_processes()
        self.check_port_availability()
        
        self.suggest_fixes()
        self.generate_report()

if __name__ == "__main__":
    auditor = PracticalAuditor()
    auditor.run()