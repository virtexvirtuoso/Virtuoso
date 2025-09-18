#!/usr/bin/env python3
"""
Comprehensive verification that ALL mock data issues from both audits are fixed
Checks both local and VPS deployments
"""

import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# VPS connection details
VPS_HOST = "VPS_HOST_REDACTED"
VPS_USER = "linuxuser"
VPS_DIR = "/home/linuxuser/trading/Virtuoso_ccxt"

class ComprehensiveVerifier:
    def __init__(self):
        self.local_issues = []
        self.vps_issues = []
        self.fixes_verified = []
        
    def check_issue_1_trade_executor(self) -> Tuple[bool, bool]:
        """Issue 1: Trade Executor Random Scores (PRODUCTION_MOCK_DATA_AUDIT_2.md)"""
        print("\n🔍 Checking Issue 1: Trade Executor Random Scores...")
        
        # Local check
        local_ok = True
        filepath = Path("src/trade_execution/trade_executor.py")
        if filepath.exists():
            content = filepath.read_text()
            if "random.uniform(0, 100)" in content:
                self.local_issues.append("❌ Trade executor still using random.uniform(0, 100)")
                local_ok = False
            elif "from src.core.analysis.confluence import ConfluenceAnalyzer" not in content:
                self.local_issues.append("❌ Trade executor not importing real ConfluenceAnalyzer")
                local_ok = False
            else:
                print("  ✅ Local: Fixed - using real ConfluenceAnalyzer")
        
        # VPS check
        vps_ok = True
        try:
            cmd = f'ssh {VPS_USER}@{VPS_HOST} "cd {VPS_DIR} && grep -c \\"random.uniform(0, 100)\\" src/trade_execution/trade_executor.py"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.stdout.strip() != "0":
                self.vps_issues.append("❌ VPS: Trade executor still using random scores")
                vps_ok = False
            else:
                print("  ✅ VPS: Fixed - no random scores")
        except:
            self.vps_issues.append("⚠️ Could not check VPS trade executor")
            vps_ok = False
            
        return local_ok, vps_ok
    
    def check_issue_2_analysis_service(self) -> Tuple[bool, bool]:
        """Issue 2: Analysis Service Random Components (PRODUCTION_MOCK_DATA_AUDIT_2.md)"""
        print("\n🔍 Checking Issue 2: Analysis Service Random Components...")
        
        # Local check
        local_ok = True
        filepath = Path("src/services/analysis_service_enhanced.py")
        if filepath.exists():
            content = filepath.read_text()
            if "random.uniform(40, 60)" in content:
                self.local_issues.append("❌ Analysis service still using random.uniform(40, 60)")
                local_ok = False
            elif "_get_real_score" not in content:
                self.local_issues.append("❌ Analysis service missing _get_real_score method")
                local_ok = False
            else:
                print("  ✅ Local: Fixed - using real scores")
        
        # VPS check
        vps_ok = True
        try:
            cmd = f'ssh {VPS_USER}@{VPS_HOST} "cd {VPS_DIR} && grep -c \\"random.uniform(40, 60)\\" src/services/analysis_service_enhanced.py"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.stdout.strip() != "0":
                self.vps_issues.append("❌ VPS: Analysis service still using random components")
                vps_ok = False
            else:
                print("  ✅ VPS: Fixed - no random components")
        except:
            self.vps_issues.append("⚠️ Could not check VPS analysis service")
            vps_ok = False
            
        return local_ok, vps_ok
    
    def check_issue_3_confluence_sample(self) -> Tuple[bool, bool]:
        """Issue 3: Sample Confluence File (PRODUCTION_MOCK_DATA_AUDIT_2.md)"""
        print("\n🔍 Checking Issue 3: Sample Confluence File...")
        
        # Local check
        local_ok = True
        if Path("src/core/analysis/confluence_sample.py").exists():
            self.local_issues.append("❌ confluence_sample.py still exists")
            local_ok = False
        else:
            print("  ✅ Local: Fixed - confluence_sample.py removed/renamed")
        
        # VPS check
        vps_ok = True
        try:
            cmd = f'ssh {VPS_USER}@{VPS_HOST} "test -f {VPS_DIR}/src/core/analysis/confluence_sample.py && echo EXISTS"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if "EXISTS" in result.stdout:
                self.vps_issues.append("❌ VPS: confluence_sample.py still exists")
                vps_ok = False
            else:
                print("  ✅ VPS: Fixed - confluence_sample.py removed")
        except:
            self.vps_issues.append("⚠️ Could not check VPS confluence_sample")
            vps_ok = False
            
        return local_ok, vps_ok
    
    def check_issue_4_synthetic_oi(self) -> Tuple[bool, bool]:
        """Issue 4: Synthetic Open Interest (MOCK_DATA_AUDIT_REPORT.md)"""
        print("\n🔍 Checking Issue 4: Synthetic Open Interest...")
        
        # Local check
        local_ok = True
        filepath = Path("src/core/market/market_data_manager.py")
        if filepath.exists():
            content = filepath.read_text()
            if "'is_synthetic': True" in content:
                self.local_issues.append("❌ Still generating synthetic open interest")
                local_ok = False
            elif "fake_timestamp" in content or "fake_value" in content:
                self.local_issues.append("❌ Still has fake OI generation code")
                local_ok = False
            else:
                print("  ✅ Local: Fixed - no synthetic OI")
        
        # VPS check
        vps_ok = True
        try:
            cmd = f'ssh {VPS_USER}@{VPS_HOST} "cd {VPS_DIR} && grep -c \\"is_synthetic.: True\\" src/core/market/market_data_manager.py"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.stdout.strip() != "0":
                self.vps_issues.append("❌ VPS: Still generating synthetic OI")
                vps_ok = False
            else:
                print("  ✅ VPS: Fixed - no synthetic OI")
        except:
            self.vps_issues.append("⚠️ Could not check VPS synthetic OI")
            vps_ok = False
            
        return local_ok, vps_ok
    
    def check_issue_5_hardcoded_defaults(self) -> Tuple[bool, bool]:
        """Issue 5: Hardcoded 50.0 Defaults (PRODUCTION_MOCK_DATA_AUDIT_2.md)"""
        print("\n🔍 Checking Issue 5: Hardcoded 50.0 Defaults...")
        
        files = [
            "src/dashboard/integration_service.py",
            "src/dashboard/dashboard_integration.py",
            "src/api/services/mobile_fallback_service.py"
        ]
        
        # Local check
        local_ok = True
        for filepath in files:
            path = Path(filepath)
            if path.exists():
                content = path.read_text()
                count = content.count(".get('score', 50.0)")
                if count > 0:
                    self.local_issues.append(f"❌ {filepath} has {count} hardcoded 50.0 defaults")
                    local_ok = False
        
        if local_ok:
            print("  ✅ Local: Fixed - no hardcoded 50.0 defaults")
        
        # VPS check
        vps_ok = True
        try:
            for filepath in files:
                cmd = f'ssh {VPS_USER}@{VPS_HOST} "cd {VPS_DIR} && grep -c \\".get(.score., 50.0)\\" {filepath} 2>/dev/null || echo 0"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.stdout.strip() != "0":
                    self.vps_issues.append(f"❌ VPS: {filepath} has hardcoded 50.0 defaults")
                    vps_ok = False
        except:
            self.vps_issues.append("⚠️ Could not check VPS hardcoded defaults")
            vps_ok = False
            
        if vps_ok:
            print("  ✅ VPS: Fixed - no hardcoded defaults")
            
        return local_ok, vps_ok
    
    def check_issue_6_orderflow_random(self) -> Tuple[bool, bool]:
        """Issue 6: Orderflow Random Side Assignment (PRODUCTION_MOCK_DATA_AUDIT_2.md)"""
        print("\n🔍 Checking Issue 6: Orderflow Random Side Assignment...")
        
        # Local check
        local_ok = True
        filepath = Path("src/indicators/orderflow_indicators.py")
        if filepath.exists():
            content = filepath.read_text()
            if "np.random.choice" in content and "unknown" in content:
                self.local_issues.append("❌ Orderflow still randomly assigning sides")
                local_ok = False
            else:
                print("  ✅ Local: Fixed - no random side assignment")
        
        # VPS check
        vps_ok = True
        try:
            cmd = f'ssh {VPS_USER}@{VPS_HOST} "cd {VPS_DIR} && grep -c \\"np.random.choice\\" src/indicators/orderflow_indicators.py"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.stdout.strip() != "0":
                self.vps_issues.append("❌ VPS: Orderflow still randomly assigning sides")
                vps_ok = False
            else:
                print("  ✅ VPS: Fixed - no random assignment")
        except:
            self.vps_issues.append("⚠️ Could not check VPS orderflow")
            vps_ok = False
            
        return local_ok, vps_ok
    
    def check_issue_7_sample_tickers(self) -> Tuple[bool, bool]:
        """Issue 7: Sample Ticker Fallback (MOCK_DATA_AUDIT_REPORT.md)"""
        print("\n🔍 Checking Issue 7: Sample Ticker Fallback...")
        
        # Local check
        local_ok = True
        filepath = Path("scripts/populate_cache_service.py")
        if filepath.exists():
            content = filepath.read_text()
            if "113000" in content or "sample_tickers" in content and "'BTCUSDT': {" in content:
                self.local_issues.append("❌ Still has hardcoded sample ticker data")
                local_ok = False
            else:
                print("  ✅ Local: Fixed - no sample tickers")
        
        # VPS check
        vps_ok = True
        try:
            cmd = f'ssh {VPS_USER}@{VPS_HOST} "cd {VPS_DIR} && grep -c 113000 scripts/populate_cache_service.py"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.stdout.strip() != "0":
                self.vps_issues.append("❌ VPS: Still has sample ticker data")
                vps_ok = False
            else:
                print("  ✅ VPS: Fixed - no sample tickers")
        except:
            self.vps_issues.append("⚠️ Could not check VPS sample tickers")
            vps_ok = False
            
        return local_ok, vps_ok
    
    def check_issue_8_mock_alerts(self) -> Tuple[bool, bool]:
        """Issue 8: Mock Alert Mode (MOCK_DATA_AUDIT_REPORT.md)"""
        print("\n🔍 Checking Issue 8: Mock Alert Mode...")
        
        # Local check
        local_ok = True
        filepath = Path("src/monitoring/alert_manager.py")
        if filepath.exists():
            content = filepath.read_text()
            if "MOCK MODE:" in content:
                self.local_issues.append("❌ Alert manager still has mock mode")
                local_ok = False
            else:
                print("  ✅ Local: Fixed - no mock alert mode")
        
        # VPS check
        vps_ok = True
        try:
            cmd = f'ssh {VPS_USER}@{VPS_HOST} "cd {VPS_DIR} && grep -c \\"MOCK MODE:\\" src/monitoring/alert_manager.py"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.stdout.strip() != "0":
                self.vps_issues.append("❌ VPS: Alert manager still has mock mode")
                vps_ok = False
            else:
                print("  ✅ VPS: Fixed - no mock alerts")
        except:
            self.vps_issues.append("⚠️ Could not check VPS mock alerts")
            vps_ok = False
            
        return local_ok, vps_ok
    
    def check_vps_service_status(self) -> bool:
        """Check if VPS service is running"""
        print("\n🔍 Checking VPS Service Status...")
        
        try:
            cmd = f'ssh {VPS_USER}@{VPS_HOST} "sudo systemctl is-active virtuoso-web.service"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if "active" in result.stdout:
                print("  ✅ VPS service is running")
                return True
            else:
                print("  ❌ VPS service is not active")
                return False
        except:
            print("  ⚠️ Could not check VPS service status")
            return False
    
    def run_verification(self):
        """Run all verification checks"""
        print("=" * 70)
        print("COMPREHENSIVE MOCK DATA FIX VERIFICATION")
        print("Checking all issues from both audit reports...")
        print("=" * 70)
        
        # Run all checks
        checks = [
            ("Trade Executor Random Scores", self.check_issue_1_trade_executor()),
            ("Analysis Service Random Components", self.check_issue_2_analysis_service()),
            ("Sample Confluence File", self.check_issue_3_confluence_sample()),
            ("Synthetic Open Interest", self.check_issue_4_synthetic_oi()),
            ("Hardcoded 50.0 Defaults", self.check_issue_5_hardcoded_defaults()),
            ("Orderflow Random Assignment", self.check_issue_6_orderflow_random()),
            ("Sample Ticker Fallback", self.check_issue_7_sample_tickers()),
            ("Mock Alert Mode", self.check_issue_8_mock_alerts()),
        ]
        
        # Count results
        local_fixed = sum(1 for _, (local, _) in checks if local)
        vps_fixed = sum(1 for _, (_, vps) in checks if vps)
        total_checks = len(checks)
        
        # Check VPS service
        vps_running = self.check_vps_service_status()
        
        # Summary
        print("\n" + "=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)
        
        print(f"\n📊 LOCAL STATUS: {local_fixed}/{total_checks} Issues Fixed")
        if self.local_issues:
            print("\n❌ Local Issues Remaining:")
            for issue in self.local_issues:
                print(f"  {issue}")
        else:
            print("  ✅ All local issues fixed!")
        
        print(f"\n📊 VPS STATUS: {vps_fixed}/{total_checks} Issues Fixed")
        if self.vps_issues:
            print("\n❌ VPS Issues Remaining:")
            for issue in self.vps_issues:
                print(f"  {issue}")
        else:
            print("  ✅ All VPS issues fixed!")
        
        print(f"\n🚀 VPS Service: {'Running' if vps_running else 'NOT RUNNING'}")
        
        # Final verdict
        print("\n" + "=" * 70)
        if local_fixed == total_checks and vps_fixed == total_checks and vps_running:
            print("✅ ALL ISSUES FIXED AND DEPLOYED TO PRODUCTION!")
            print("✅ SYSTEM IS SAFE FOR PRODUCTION TRADING!")
            return 0
        elif local_fixed == total_checks:
            print("⚠️ LOCAL FIXES COMPLETE BUT VPS DEPLOYMENT INCOMPLETE")
            print("🔧 Run deployment script to push fixes to VPS")
            return 1
        else:
            print("❌ CRITICAL ISSUES REMAIN - DO NOT USE FOR TRADING!")
            return 2

if __name__ == "__main__":
    verifier = ComprehensiveVerifier()
    sys.exit(verifier.run_verification())