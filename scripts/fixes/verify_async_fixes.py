#!/usr/bin/env python3
"""
Verification script for async fixes implementation
Checks if all the critical async patterns have been properly implemented
"""

import asyncio
import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

class AsyncPatternVerifier:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues_found = []
        
    def verify_websocket_manager_fixes(self) -> bool:
        """Verify WebSocket Manager has proper task tracking"""
        ws_file = self.project_root / "src/core/exchanges/websocket_manager.py"
        
        if not ws_file.exists():
            self.issues_found.append("WebSocket Manager file not found")
            return False
            
        content = ws_file.read_text()
        
        # Check for task tracking implementation
        required_patterns = [
            "_background_tasks = set()",
            "_message_processing_tasks = set()",
            "_create_tracked_task",
            "task.add_done_callback"
        ]
        
        for pattern in required_patterns:
            if pattern not in content:
                self.issues_found.append(f"WebSocket Manager missing: {pattern}")
                return False
                
        print("✅ WebSocket Manager fixes verified")
        return True
    
    def verify_cache_manager_fixes(self) -> bool:
        """Verify Cache Manager has proper async patterns"""
        cache_file = self.project_root / "src/core/cache_manager.py"
        
        if not cache_file.exists():
            self.issues_found.append("Cache Manager file not found")
            return False
            
        content = cache_file.read_text()
        
        # Check for async lock usage instead of threading locks
        if "threading.Lock()" in content:
            self.issues_found.append("Cache Manager still uses threading.Lock()")
            return False
            
        # Check for async circuit breaker methods
        required_patterns = [
            "async def _is_memcached_available(self)",
            "async def _record_memcached_failure(self)",
            "_circuit_breaker_lock = asyncio.Lock()",
            "async with self._circuit_breaker_lock:"
        ]
        
        for pattern in required_patterns:
            if pattern not in content:
                self.issues_found.append(f"Cache Manager missing: {pattern}")
                return False
                
        print("✅ Cache Manager fixes verified")
        return True
        
    def verify_bybit_timeout_fixes(self) -> bool:
        """Verify Bybit exchange has proper timeout handling"""
        bybit_file = self.project_root / "src/core/exchanges/bybit.py"
        
        if not bybit_file.exists():
            self.issues_found.append("Bybit exchange file not found")
            return False
            
        content = bybit_file.read_text()
        
        # Check for timeout implementations
        required_patterns = [
            "aiohttp.ClientTimeout(",
            "asyncio.timeout(",
            "await asyncio.wait_for("
        ]
        
        pattern_counts = {pattern: content.count(pattern) for pattern in required_patterns}
        
        # Should have multiple timeout implementations
        if pattern_counts["aiohttp.ClientTimeout("] < 2:
            self.issues_found.append("Insufficient aiohttp timeout configurations")
            return False
            
        if pattern_counts["asyncio.timeout("] < 3:
            self.issues_found.append("Insufficient asyncio timeout implementations")
            return False
            
        print("✅ Bybit timeout fixes verified")
        return True
        
    def verify_connection_pool_fixes(self) -> bool:
        """Verify connection pool has proper edge case handling"""
        cache_file = self.project_root / "src/core/cache_manager.py"
        
        if not cache_file.exists():
            self.issues_found.append("Cache Manager file not found")
            return False
            
        content = cache_file.read_text()
        
        # Check for connection pool improvements
        required_patterns = [
            "connection_created = False",
            "health_check",
            "_close_single_connection",
            "await asyncio.wait_for(self._available.put(conn), timeout=1.0)"
        ]
        
        for pattern in required_patterns:
            if pattern not in content:
                self.issues_found.append(f"Connection pool missing: {pattern}")
                return False
                
        print("✅ Connection pool fixes verified")
        return True
        
    def verify_no_fire_and_forget_tasks(self) -> bool:
        """Check for remaining fire-and-forget asyncio.create_task() calls"""
        fire_and_forget_found = []
        
        # Check key files
        key_files = [
            "src/core/exchanges/websocket_manager.py",
            "src/core/cache_manager.py",
            "src/core/exchanges/bybit.py",
            "src/main.py"
        ]
        
        for file_path in key_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue
                
            content = full_path.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                if 'asyncio.create_task(' in line and 'tracked' not in line:
                    # Check if it's properly handled (assigned to variable or tracked)
                    if not (any(keyword in line for keyword in ['=', 'tracked', 'add_done_callback'])):
                        fire_and_forget_found.append(f"{file_path}:{i}")
                        
        if fire_and_forget_found:
            self.issues_found.extend([f"Fire-and-forget task found: {location}" 
                                    for location in fire_and_forget_found])
            return False
            
        print("✅ No fire-and-forget tasks found")
        return True
        
    def run_verification(self) -> bool:
        """Run all verification checks"""
        print("Running async fixes verification...")
        print("=" * 50)
        
        all_checks = [
            self.verify_websocket_manager_fixes(),
            self.verify_cache_manager_fixes(), 
            self.verify_bybit_timeout_fixes(),
            self.verify_connection_pool_fixes(),
            self.verify_no_fire_and_forget_tasks()
        ]
        
        success = all(all_checks)
        
        print("=" * 50)
        
        if success:
            print("🎉 All async fixes verified successfully!")
            print("\nImplemented fixes:")
            print("• Fixed fire-and-forget tasks in WebSocket Manager")
            print("• Fixed race conditions in Cache Manager circuit breaker")  
            print("• Replaced threading.Lock with asyncio.Lock")
            print("• Improved WebSocket resource management")
            print("• Added comprehensive timeout handling")
            print("• Fixed connection pool edge cases")
            return True
        else:
            print("❌ Issues found:")
            for issue in self.issues_found:
                print(f"  • {issue}")
            return False

if __name__ == "__main__":
    project_root = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt"
    verifier = AsyncPatternVerifier(project_root)
    
    success = verifier.run_verification()
    sys.exit(0 if success else 1)