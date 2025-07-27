#!/usr/bin/env python3
"""
Test script to verify admin dashboard is properly set up and connected.
"""

import os
import sys
import importlib.util
from pathlib import Path
import yaml
import json
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class AdminDashboardTester:
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.results = {
            "files": {},
            "imports": {},
            "routes": {},
            "config": {},
            "errors": []
        }
        
    def test_file_exists(self, file_path: str, description: str) -> bool:
        """Test if a file exists."""
        full_path = self.project_root / file_path
        exists = full_path.exists()
        self.results["files"][file_path] = {
            "exists": exists,
            "description": description,
            "full_path": str(full_path)
        }
        if not exists:
            self.results["errors"].append(f"Missing file: {file_path}")
        return exists
    
    def test_import(self, module_path: str) -> bool:
        """Test if a module can be imported."""
        try:
            # Convert file path to module path
            module_name = module_path.replace('/', '.').replace('.py', '')
            if module_name.startswith('src.'):
                # Try direct import
                module = importlib.import_module(module_name)
            else:
                # Use importlib.util for file-based import
                file_path = self.project_root / module_path
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            
            self.results["imports"][module_path] = {
                "success": True,
                "module": module_name
            }
            return True
        except Exception as e:
            self.results["imports"][module_path] = {
                "success": False,
                "error": str(e)
            }
            self.results["errors"].append(f"Import error for {module_path}: {str(e)}")
            return False
    
    def test_route_registration(self) -> bool:
        """Test if admin routes are properly registered."""
        try:
            # Check if admin is imported in API init
            api_init_path = self.project_root / "src/api/__init__.py"
            with open(api_init_path, 'r') as f:
                content = f.read()
            
            checks = {
                "admin_import": "from .routes import" in content and "admin" in content,
                "admin_router": "admin.router" in content,
                "admin_prefix": "dashboard/admin" in content
            }
            
            self.results["routes"]["registration"] = checks
            
            all_passed = all(checks.values())
            if not all_passed:
                self.results["errors"].append("Admin routes not properly registered in API init")
            
            return all_passed
            
        except Exception as e:
            self.results["routes"]["registration"] = {"error": str(e)}
            self.results["errors"].append(f"Route registration check failed: {str(e)}")
            return False
    
    def test_html_templates(self) -> bool:
        """Test HTML templates for basic validity."""
        templates = [
            "src/dashboard/templates/admin_login.html",
            "src/dashboard/templates/admin_dashboard.html"
        ]
        
        all_valid = True
        for template_path in templates:
            full_path = self.project_root / template_path
            if full_path.exists():
                try:
                    with open(full_path, 'r') as f:
                        content = f.read()
                    
                    # Basic HTML validation checks
                    checks = {
                        "has_doctype": "<!DOCTYPE html>" in content,
                        "has_html_tag": "<html" in content and "</html>" in content,
                        "has_head": "<head>" in content and "</head>" in content,
                        "has_body": "<body>" in content and "</body>" in content,
                        "has_script": "<script>" in content or "<script " in content,
                        "is_responsive": 'viewport' in content
                    }
                    
                    self.results["files"][template_path]["html_valid"] = checks
                    if not all(checks.values()):
                        all_valid = False
                        self.results["errors"].append(f"HTML validation issues in {template_path}")
                        
                except Exception as e:
                    self.results["errors"].append(f"Error reading template {template_path}: {str(e)}")
                    all_valid = False
            else:
                all_valid = False
                
        return all_valid
    
    def test_config_directory(self) -> bool:
        """Test if config directory exists and has YAML files."""
        config_dir = self.project_root / "config"
        
        if not config_dir.exists():
            self.results["config"]["directory_exists"] = False
            self.results["errors"].append("Config directory not found")
            return False
        
        yaml_files = list(config_dir.glob("*.yaml"))
        self.results["config"]["directory_exists"] = True
        self.results["config"]["yaml_files"] = [f.name for f in yaml_files]
        self.results["config"]["yaml_count"] = len(yaml_files)
        
        # Test if at least one YAML file can be parsed
        if yaml_files:
            test_file = yaml_files[0]
            try:
                with open(test_file, 'r') as f:
                    yaml.safe_load(f)
                self.results["config"]["yaml_parseable"] = True
            except Exception as e:
                self.results["config"]["yaml_parseable"] = False
                self.results["errors"].append(f"YAML parsing error in {test_file.name}: {str(e)}")
                return False
        
        return len(yaml_files) > 0
    
    def test_api_endpoints(self) -> bool:
        """Test if API endpoints are defined correctly."""
        try:
            admin_route_path = self.project_root / "src/api/routes/admin.py"
            with open(admin_route_path, 'r') as f:
                content = f.read()
            
            # Check for essential endpoints
            endpoints = {
                "login": '@router.post("/auth/login")',
                "logout": '@router.post("/auth/logout")',
                "verify": '@router.get("/auth/verify")',
                "config_files": '@router.get("/config/files")',
                "config_file": '@router.get("/config/file/{filename}")',
                "update_config": '@router.post("/config/file/{filename}")',
                "system_status": '@router.get("/system/status")',
                "dashboard_page": '@router.get("/dashboard")',
                "login_page": '@router.get("/login")'
            }
            
            endpoint_results = {}
            all_found = True
            
            for name, endpoint in endpoints.items():
                found = endpoint in content
                endpoint_results[name] = found
                if not found:
                    all_found = False
                    self.results["errors"].append(f"Missing endpoint: {name}")
            
            self.results["routes"]["endpoints"] = endpoint_results
            return all_found
            
        except Exception as e:
            self.results["routes"]["endpoints"] = {"error": str(e)}
            self.results["errors"].append(f"Endpoint check failed: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all tests and generate report."""
        print("🔍 Testing Admin Dashboard Setup...")
        print("=" * 50)
        
        # Test 1: Check all files exist
        print("\n📁 Checking Files...")
        files_to_check = [
            ("src/api/routes/admin.py", "Admin API routes"),
            ("src/dashboard/templates/admin_login.html", "Admin login page"),
            ("src/dashboard/templates/admin_dashboard.html", "Admin dashboard page"),
            ("scripts/setup_admin_password.py", "Password setup script"),
            ("docs/ADMIN_DASHBOARD_SETUP.md", "Setup documentation")
        ]
        
        file_test_passed = True
        for file_path, description in files_to_check:
            exists = self.test_file_exists(file_path, description)
            status = "✅" if exists else "❌"
            print(f"  {status} {file_path}")
            if not exists:
                file_test_passed = False
        
        # Test 2: Check imports
        print("\n📦 Testing Imports...")
        import_test_passed = True
        modules_to_test = [
            "src/api/routes/admin.py"
        ]
        
        for module in modules_to_test:
            success = self.test_import(module)
            status = "✅" if success else "❌"
            print(f"  {status} {module}")
            if not success:
                import_test_passed = False
        
        # Test 3: Check route registration
        print("\n🔗 Testing Route Registration...")
        route_test_passed = self.test_route_registration()
        if route_test_passed:
            print("  ✅ Admin routes properly registered")
        else:
            print("  ❌ Admin routes not properly registered")
        
        # Test 4: Validate HTML templates
        print("\n📄 Validating HTML Templates...")
        html_test_passed = self.test_html_templates()
        if html_test_passed:
            print("  ✅ HTML templates are valid")
        else:
            print("  ❌ HTML template issues found")
        
        # Test 5: Check config directory
        print("\n⚙️  Testing Config Directory...")
        config_test_passed = self.test_config_directory()
        if config_test_passed:
            print(f"  ✅ Config directory found with {self.results['config']['yaml_count']} YAML files")
        else:
            print("  ❌ Config directory issues")
        
        # Test 6: Check API endpoints
        print("\n🌐 Testing API Endpoints...")
        endpoint_test_passed = self.test_api_endpoints()
        if endpoint_test_passed:
            print("  ✅ All required endpoints found")
        else:
            print("  ❌ Missing endpoints")
        
        # Generate summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        all_passed = all([
            file_test_passed,
            import_test_passed,
            route_test_passed,
            html_test_passed,
            config_test_passed,
            endpoint_test_passed
        ])
        
        if all_passed:
            print("✅ ALL TESTS PASSED! Admin dashboard is properly set up.")
            print("\n🚀 Next Steps:")
            print("1. Run: python scripts/setup_admin_password.py")
            print("2. Start the application")
            print("3. Visit: http://localhost:8003/api/dashboard/admin/login")
        else:
            print(f"❌ TESTS FAILED! Found {len(self.results['errors'])} errors:")
            for error in self.results['errors']:
                print(f"   - {error}")
        
        # Save detailed report
        report_path = self.project_root / "test_admin_dashboard_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n📝 Detailed report saved to: {report_path}")
        
        return all_passed

def main():
    """Run the admin dashboard tests."""
    tester = AdminDashboardTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()