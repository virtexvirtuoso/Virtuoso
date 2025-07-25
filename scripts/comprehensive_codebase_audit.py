#!/usr/bin/env python3
"""
Comprehensive Codebase Audit Script
Checks for common issues, missing dependencies, and configuration problems
"""

import os
import sys
import json
import yaml
import ast
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Set

class CodebaseAuditor:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.src_dir = self.project_root / "src"
        self.config_dir = self.project_root / "config"
        self.issues = {
            "critical": [],
            "warning": [],
            "info": []
        }
        self.stats = {
            "total_files": 0,
            "python_files": 0,
            "config_files": 0,
            "test_files": 0
        }
        
    def add_issue(self, severity: str, category: str, message: str, file_path: str = None):
        """Add an issue to the audit report"""
        issue = {
            "category": category,
            "message": message,
            "file": str(file_path) if file_path else None,
            "timestamp": datetime.now().isoformat()
        }
        self.issues[severity].append(issue)
    
    def check_python_syntax(self, file_path: Path) -> bool:
        """Check if Python file has valid syntax"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            return True
        except SyntaxError as e:
            self.add_issue("critical", "Syntax Error", f"Syntax error: {e}", file_path)
            return False
        except Exception as e:
            self.add_issue("warning", "Parse Error", f"Could not parse: {e}", file_path)
            return False
    
    def check_imports(self, file_path: Path) -> List[str]:
        """Extract and check imports from Python file"""
        missing_imports = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split('.')[0]
                        if not self.is_module_available(module_name):
                            missing_imports.append(module_name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split('.')[0]
                        if module_name != 'src' and not self.is_module_available(module_name):
                            missing_imports.append(module_name)
        except:
            pass
        
        return missing_imports
    
    def is_module_available(self, module_name: str) -> bool:
        """Check if a module is available"""
        if module_name in sys.builtin_module_names:
            return True
        
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    
    def check_config_files(self):
        """Check configuration files"""
        print("\n🔍 Checking configuration files...")
        
        # Check main config.yaml
        config_path = self.config_dir / "config.yaml"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Check for required sections
                required_sections = ['exchanges', 'database', 'monitoring', 'web_server']
                for section in required_sections:
                    if section not in config:
                        self.add_issue("critical", "Config Missing", f"Missing section: {section}", config_path)
                
                # Check exchange configuration
                if 'exchanges' in config:
                    for exchange, settings in config['exchanges'].items():
                        if settings.get('enabled', False):
                            if not settings.get('api_key') or not settings.get('api_secret'):
                                self.add_issue("warning", "Config", f"{exchange} enabled but missing API credentials", config_path)
                
                self.stats['config_files'] += 1
            except Exception as e:
                self.add_issue("critical", "Config Error", f"Error reading config: {e}", config_path)
        else:
            self.add_issue("critical", "Config Missing", "Main config.yaml not found", config_path)
        
        # Check .env file
        env_path = self.config_dir / "env" / ".env"
        if not env_path.exists():
            self.add_issue("warning", "Config", ".env file not found", env_path)
    
    def check_circular_imports(self):
        """Check for potential circular imports"""
        print("\n🔍 Checking for circular imports...")
        
        import_graph = {}
        
        for py_file in self.src_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
                
            module_name = str(py_file.relative_to(self.src_dir)).replace("/", ".").replace(".py", "")
            imports = []
            
            try:
                with open(py_file, 'r') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and node.module.startswith("src"):
                            imports.append(node.module)
                
                import_graph[module_name] = imports
            except:
                pass
        
        # Simple circular import detection
        for module, imports in import_graph.items():
            for imported in imports:
                if imported in import_graph:
                    if module in import_graph[imported]:
                        self.add_issue("warning", "Circular Import", 
                                     f"Potential circular import: {module} <-> {imported}")
    
    def check_error_handling(self, file_path: Path):
        """Check for proper error handling patterns"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
            
            # Check for bare except clauses
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        line_no = node.lineno
                        self.add_issue("warning", "Error Handling", 
                                     f"Bare except clause at line {line_no}", file_path)
            
            # Check for missing error handling in async functions
            async_funcs = [n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)]
            for func in async_funcs:
                has_try = any(isinstance(n, ast.Try) for n in ast.walk(func))
                if not has_try and "test_" not in func.name:
                    self.add_issue("info", "Error Handling", 
                                 f"Async function '{func.name}' has no error handling", file_path)
        except:
            pass
    
    def check_deprecated_patterns(self, file_path: Path):
        """Check for deprecated patterns"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            deprecated_patterns = [
                ("print(", "Using print instead of logger"),
                ("time.sleep(", "Using blocking sleep in async code"),
                ("== None", "Using == None instead of is None"),
                ("!= None", "Using != None instead of is not None"),
            ]
            
            for pattern, message in deprecated_patterns:
                if pattern in content:
                    self.add_issue("info", "Code Quality", message, file_path)
        except:
            pass
    
    def check_missing_docstrings(self, file_path: Path):
        """Check for missing docstrings"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node) and not node.name.startswith('_'):
                        self.add_issue("info", "Documentation", 
                                     f"Missing docstring for {node.name}", file_path)
        except:
            pass
    
    def audit_python_files(self):
        """Audit all Python files"""
        print("\n🔍 Auditing Python files...")
        
        all_missing_imports = set()
        
        for py_file in self.src_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            
            self.stats['total_files'] += 1
            self.stats['python_files'] += 1
            
            if "test_" in py_file.name or "tests" in str(py_file):
                self.stats['test_files'] += 1
            
            # Check syntax
            if not self.check_python_syntax(py_file):
                continue
            
            # Check imports
            missing = self.check_imports(py_file)
            if missing:
                all_missing_imports.update(missing)
            
            # Check error handling
            self.check_error_handling(py_file)
            
            # Check deprecated patterns
            self.check_deprecated_patterns(py_file)
            
            # Check docstrings
            self.check_missing_docstrings(py_file)
        
        # Report missing imports
        if all_missing_imports:
            self.add_issue("warning", "Dependencies", 
                         f"Missing imports found: {', '.join(sorted(all_missing_imports))}")
    
    def check_database_models(self):
        """Check database models and migrations"""
        print("\n🔍 Checking database configuration...")
        
        # Check for database models
        models_dir = self.src_dir / "data_storage" / "models"
        if not models_dir.exists():
            self.add_issue("info", "Database", "No database models directory found")
        
        # Check database client
        db_client_path = self.src_dir / "data_storage" / "database.py"
        if db_client_path.exists():
            try:
                with open(db_client_path, 'r') as f:
                    content = f.read()
                if "async def create_tables" not in content:
                    self.add_issue("warning", "Database", 
                                 "No create_tables method found in database client", db_client_path)
            except:
                pass
    
    def check_api_routes(self):
        """Check API routes for consistency"""
        print("\n🔍 Checking API routes...")
        
        routes_dir = self.src_dir / "api" / "routes"
        if routes_dir.exists():
            route_files = list(routes_dir.glob("*.py"))
            
            for route_file in route_files:
                if route_file.name == "__init__.py":
                    continue
                
                try:
                    with open(route_file, 'r') as f:
                        content = f.read()
                    
                    # Check for router definition
                    if "router = " not in content:
                        self.add_issue("warning", "API", 
                                     "No router defined", route_file)
                    
                    # Check for dependency injection issues
                    if "Depends(" in content and "get_db" not in content:
                        self.add_issue("info", "API", 
                                     "Using Depends without database dependency", route_file)
                except:
                    pass
    
    def check_security_issues(self):
        """Check for common security issues"""
        print("\n🔍 Checking for security issues...")
        
        for py_file in self.src_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Check for hardcoded secrets
                if "api_key" in content and "=" in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if "api_key" in line and "=" in line and not "os.environ" in line:
                            self.add_issue("critical", "Security", 
                                         f"Possible hardcoded API key at line {i+1}", py_file)
                
                # Check for SQL injection vulnerabilities
                if "execute" in content and "%" in content:
                    self.add_issue("warning", "Security", 
                                 "Possible SQL injection vulnerability", py_file)
            except:
                pass
    
    def generate_report(self):
        """Generate the audit report"""
        print("\n" + "="*70)
        print("CODEBASE AUDIT REPORT")
        print("="*70)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\nProject Root: {self.project_root}")
        
        # Statistics
        print("\n📊 Statistics:")
        print(f"  Total files scanned: {self.stats['total_files']}")
        print(f"  Python files: {self.stats['python_files']}")
        print(f"  Test files: {self.stats['test_files']}")
        print(f"  Config files: {self.stats['config_files']}")
        
        # Issues by severity
        print(f"\n🚨 Critical Issues: {len(self.issues['critical'])}")
        for issue in self.issues['critical'][:10]:  # Show first 10
            print(f"  - [{issue['category']}] {issue['message']}")
            if issue['file']:
                print(f"    File: {issue['file']}")
        
        if len(self.issues['critical']) > 10:
            print(f"  ... and {len(self.issues['critical']) - 10} more")
        
        print(f"\n⚠️  Warnings: {len(self.issues['warning'])}")
        for issue in self.issues['warning'][:5]:  # Show first 5
            print(f"  - [{issue['category']}] {issue['message']}")
        
        if len(self.issues['warning']) > 5:
            print(f"  ... and {len(self.issues['warning']) - 5} more")
        
        print(f"\nℹ️  Info: {len(self.issues['info'])}")
        
        # Save detailed report
        report_path = self.project_root / "test_output" / f"codebase_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "stats": self.stats,
                "issues": self.issues
            }, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_path}")
        
        # Overall health score
        health_score = 100
        health_score -= len(self.issues['critical']) * 10
        health_score -= len(self.issues['warning']) * 2
        health_score -= len(self.issues['info']) * 0.5
        health_score = max(0, min(100, health_score))
        
        print(f"\n🏥 Overall Health Score: {health_score:.1f}/100")
        
        if health_score >= 80:
            print("✅ Codebase is in good health")
        elif health_score >= 60:
            print("⚠️  Codebase needs some attention")
        else:
            print("🚨 Codebase has significant issues that need addressing")
    
    def run_audit(self):
        """Run the complete audit"""
        print("🚀 Starting comprehensive codebase audit...")
        
        # Run all checks
        self.check_config_files()
        self.audit_python_files()
        self.check_circular_imports()
        self.check_database_models()
        self.check_api_routes()
        self.check_security_issues()
        
        # Generate report
        self.generate_report()

if __name__ == "__main__":
    auditor = CodebaseAuditor()
    auditor.run_audit()