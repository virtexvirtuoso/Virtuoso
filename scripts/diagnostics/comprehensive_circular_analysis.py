#!/usr/bin/env python3
"""
Comprehensive circular reference analysis with specific recommendations.
"""

import os
import ast
import sys
from collections import defaultdict, deque
from pathlib import Path
import re

class ComprehensiveCircularAnalyzer:
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.src_dir = self.root_dir / 'src'
        self.imports = defaultdict(set)
        self.reverse_imports = defaultdict(set)
        self.file_to_module = {}
        self.module_to_file = {}
        self.circular_imports = []
        self.problematic_imports = []
        
    def analyze(self):
        """Comprehensive analysis of circular dependencies."""
        print("🔍 Comprehensive Circular Dependency Analysis")
        print("=" * 60)
        
        # Step 1: Analyze imports
        self._analyze_imports()
        
        # Step 2: Find circular imports
        self._find_circular_imports()
        
        # Step 3: Analyze problematic import patterns
        self._analyze_problematic_patterns()
        
        # Step 4: Generate specific recommendations
        self._generate_recommendations()
        
        return self.circular_imports
    
    def _analyze_imports(self):
        """Analyze all import statements."""
        print("\n📊 Step 1: Analyzing import statements...")
        
        for py_file in self.src_dir.rglob("*.py"):
            if any(skip in str(py_file) for skip in ['_backup', '.bak', '_old', '__pycache__']):
                continue
                
            module_name = self._file_to_module_name(py_file)
            self.file_to_module[str(py_file)] = module_name
            self.module_to_file[module_name] = str(py_file)
        
        for py_file in self.src_dir.rglob("*.py"):
            if any(skip in str(py_file) for skip in ['_backup', '.bak', '_old', '__pycache__']):
                continue
            self._analyze_file_imports(py_file)
    
    def _file_to_module_name(self, file_path):
        """Convert file path to module name."""
        rel_path = file_path.relative_to(self.src_dir)
        if rel_path.name == "__init__.py":
            parts = list(rel_path.parts[:-1])
        else:
            parts = list(rel_path.parts[:-1]) + [rel_path.stem]
        return '.'.join(parts) if parts else ''
    
    def _analyze_file_imports(self, file_path):
        """Analyze imports in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            current_module = self.file_to_module.get(str(file_path), str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._add_import(current_module, alias.name, node.lineno, 'import')
                        
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module
                        if node.level > 0:
                            module_name = self._resolve_relative_import(
                                current_module, node.module, node.level
                            )
                        
                        import_type = 'from_import'
                        if node.level > 0:
                            import_type = 'relative_import'
                            
                        self._add_import(current_module, module_name, node.lineno, import_type)
                        
        except Exception as e:
            print(f"⚠️  Error analyzing {file_path}: {e}")
    
    def _resolve_relative_import(self, current_module, import_module, level):
        """Resolve relative imports."""
        current_parts = current_module.split('.')
        
        if level > len(current_parts):
            return import_module or ""
            
        base_parts = current_parts[:-level] if level > 0 else current_parts
        
        if import_module:
            return '.'.join(base_parts + [import_module])
        else:
            return '.'.join(base_parts)
    
    def _add_import(self, from_module, to_module, line_no, import_type):
        """Add an import relationship with metadata."""
        # Only track imports within our src directory
        if self._is_internal_module(to_module):
            self.imports[from_module].add((to_module, line_no, import_type))
            self.reverse_imports[to_module].add((from_module, line_no, import_type))
    
    def _is_internal_module(self, module_name):
        """Check if module is internal to our codebase."""
        # Check if it starts with known internal patterns
        internal_patterns = [
            'monitoring', 'core', 'utils', 'data_storage', 'dashboard',
            'data_acquisition', 'signal_generation', 'trade_execution'
        ]
        
        return any(module_name.startswith(pattern) for pattern in internal_patterns) or \
               module_name in self.module_to_file
    
    def _find_circular_imports(self):
        """Find circular import dependencies."""
        print("📊 Step 2: Finding circular import cycles...")
        
        # Build simplified graph for cycle detection
        graph = defaultdict(set)
        for from_module, imports in self.imports.items():
            for to_module, _, _ in imports:
                graph[from_module].add(to_module)
        
        visited = set()
        rec_stack = set()
        path_stack = []
        
        def dfs(module):
            if module in rec_stack:
                try:
                    cycle_start = path_stack.index(module)
                    cycle = path_stack[cycle_start:] + [module]
                    return cycle
                except ValueError:
                    return [module, module]
                
            if module in visited:
                return None
                
            visited.add(module)
            rec_stack.add(module)
            path_stack.append(module)
            
            for imported_module in graph.get(module, []):
                cycle = dfs(imported_module)
                if cycle:
                    return cycle
            
            rec_stack.remove(module)
            path_stack.pop()
            return None
        
        for module in graph.keys():
            if module not in visited:
                cycle = dfs(module)
                if cycle and len(cycle) > 2:
                    self.circular_imports.append(cycle)
    
    def _analyze_problematic_patterns(self):
        """Analyze specific problematic import patterns."""
        print("📊 Step 3: Analyzing problematic patterns...")
        
        # Pattern 1: Direct mutual imports
        for from_module, imports in self.imports.items():
            for to_module, line_no, import_type in imports:
                # Check if to_module imports back to from_module
                reverse_imports = self.imports.get(to_module, set())
                for rev_to_module, rev_line_no, rev_import_type in reverse_imports:
                    if rev_to_module == from_module:
                        self.problematic_imports.append({
                            'type': 'mutual_import',
                            'modules': [from_module, to_module],
                            'details': [
                                (from_module, to_module, line_no, import_type),
                                (to_module, from_module, rev_line_no, rev_import_type)
                            ]
                        })
        
        # Pattern 2: TYPE_CHECKING violations
        self._find_type_checking_violations()
        
        # Pattern 3: Late import opportunities
        self._find_late_import_opportunities()
    
    def _find_type_checking_violations(self):
        """Find imports that should be in TYPE_CHECKING blocks."""
        for py_file in self.src_dir.rglob("*.py"):
            if any(skip in str(py_file) for skip in ['_backup', '.bak', '_old']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for imports that are only used in type annotations
                lines = content.split('\n')
                
                # Find imports outside TYPE_CHECKING
                imports_outside_type_checking = []
                in_type_checking = False
                
                for i, line in enumerate(lines):
                    line = line.strip()
                    if 'TYPE_CHECKING' in line:
                        in_type_checking = True
                        continue
                    
                    if in_type_checking and line and not line.startswith(' ') and not line.startswith('\t'):
                        in_type_checking = False
                    
                    if not in_type_checking and ('from monitoring' in line or 'import.*Manager' in line):
                        if line.startswith('from ') or line.startswith('import '):
                            imports_outside_type_checking.append((i + 1, line))
                
                if imports_outside_type_checking:
                    module_name = self.file_to_module.get(str(py_file), str(py_file))
                    self.problematic_imports.append({
                        'type': 'type_checking_violation',
                        'module': module_name,
                        'file': str(py_file),
                        'imports': imports_outside_type_checking
                    })
                    
            except Exception as e:
                continue
    
    def _find_late_import_opportunities(self):
        """Find opportunities for late imports."""
        # This is a simplified heuristic - look for imports only used in methods
        pass
    
    def _generate_recommendations(self):
        """Generate specific recommendations for fixing circular dependencies."""
        print("📊 Step 4: Generating recommendations...")
        
        print(f"\n🔍 ANALYSIS RESULTS")
        print("=" * 50)
        
        if self.circular_imports:
            print(f"\n🚨 Found {len(self.circular_imports)} circular import cycle(s):")
            
            for i, cycle in enumerate(self.circular_imports, 1):
                print(f"\n📍 Circular Import #{i}:")
                for j, module in enumerate(cycle):
                    if j < len(cycle) - 1:
                        print(f"  {module}")
                        print(f"    ↓")
                    else:
                        print(f"  {module} (back to start)")
                
                # Specific recommendations for this cycle
                self._recommend_fixes_for_cycle(cycle)
        
        if self.problematic_imports:
            print(f"\n⚠️  Found {len(self.problematic_imports)} problematic import pattern(s):")
            
            for i, problem in enumerate(self.problematic_imports, 1):
                print(f"\n📍 Problem #{i}: {problem['type']}")
                
                if problem['type'] == 'mutual_import':
                    modules = problem['modules']
                    print(f"  Modules: {' ↔ '.join(modules)}")
                    for detail in problem['details']:
                        from_mod, to_mod, line_no, import_type = detail
                        file_path = self.module_to_file.get(from_mod, 'unknown')
                        print(f"    {from_mod} → {to_mod} (line {line_no}, {import_type})")
                        print(f"      File: {file_path}")
                
                elif problem['type'] == 'type_checking_violation':
                    print(f"  Module: {problem['module']}")
                    print(f"  File: {problem['file']}")
                    for line_no, import_line in problem['imports']:
                        print(f"    Line {line_no}: {import_line}")
                
                self._recommend_fixes_for_problem(problem)
        
        if not self.circular_imports and not self.problematic_imports:
            print("\n✅ No major circular dependency issues detected!")
        
        # General recommendations
        self._print_general_recommendations()
    
    def _recommend_fixes_for_cycle(self, cycle):
        """Recommend specific fixes for a circular import cycle."""
        print(f"\n💡 Recommended fixes for this cycle:")
        
        # Analyze the cycle to provide specific recommendations
        if 'monitoring.metrics_manager' in cycle and 'monitoring.alert_manager' in cycle:
            print("  🔧 SPECIFIC FIX for MetricsManager ↔ AlertManager:")
            print("     1. Move the AlertManager import in MetricsManager to TYPE_CHECKING")
            print("     2. Use dependency injection: pass AlertManager instance to MetricsManager")
            print("     3. Or create a shared interface/protocol that both can implement")
            
        elif any('utils.' in module for module in cycle):
            print("  🔧 SPECIFIC FIX for utils module cycle:")
            print("     1. Extract shared types to a separate types-only module")
            print("     2. Move utility functions to avoid cross-dependencies")
            print("     3. Use late imports inside functions where needed")
        
        else:
            print("  🔧 GENERAL FIXES:")
            print("     1. Use TYPE_CHECKING imports for type annotations only")
            print("     2. Implement dependency injection patterns")
            print("     3. Create shared interfaces or protocols")
            print("     4. Use late imports (import inside functions)")
            print("     5. Restructure modules to break the dependency chain")
    
    def _recommend_fixes_for_problem(self, problem):
        """Recommend fixes for specific problematic patterns."""
        print(f"  💡 Recommended fix:")
        
        if problem['type'] == 'mutual_import':
            print("     → Move one of the imports to TYPE_CHECKING block")
            print("     → Use dependency injection instead of direct imports")
            
        elif problem['type'] == 'type_checking_violation':
            print("     → Move these imports inside 'if TYPE_CHECKING:' blocks")
            print("     → Use string type annotations if needed at runtime")
    
    def _print_general_recommendations(self):
        """Print general recommendations for avoiding circular dependencies."""
        print(f"\n📋 GENERAL RECOMMENDATIONS:")
        print("=" * 40)
        print("1. 🎯 Use TYPE_CHECKING for type-only imports:")
        print("   ```python")
        print("   from typing import TYPE_CHECKING")
        print("   if TYPE_CHECKING:")
        print("       from .other_module import SomeClass")
        print("   ```")
        
        print("\n2. 🏗️  Implement Dependency Injection:")
        print("   ```python")
        print("   class MyClass:")
        print("       def __init__(self, dependency: 'SomeDependency'):")
        print("           self.dependency = dependency")
        print("   ```")
        
        print("\n3. ⏰ Use Late Imports:")
        print("   ```python")
        print("   def my_function():")
        print("       from .other_module import needed_function")
        print("       return needed_function()")
        print("   ```")
        
        print("\n4. 🔄 Create Shared Interfaces:")
        print("   ```python")
        print("   from abc import ABC, abstractmethod")
        print("   class SharedInterface(ABC):")
        print("       @abstractmethod")
        print("       def shared_method(self): pass")
        print("   ```")
        
        print("\n5. 📦 Restructure Module Hierarchy:")
        print("   - Move shared functionality to separate modules")
        print("   - Create clear dependency layers")
        print("   - Avoid cross-layer dependencies")

def main():
    """Main analysis function."""
    root_dir = Path(__file__).parent.parent.parent
    analyzer = ComprehensiveCircularAnalyzer(root_dir)
    
    circular_imports = analyzer.analyze()
    
    return circular_imports

if __name__ == "__main__":
    main() 