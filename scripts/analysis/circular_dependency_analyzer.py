#!/usr/bin/env python3
"""
Circular Dependency Analysis Tool
Analyzes the codebase for circular import dependencies
"""

import os
import re
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import ast

class CircularDependencyAnalyzer:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.src_path = self.root_path / "src"
        self.dependencies = defaultdict(set)  # module -> set of modules it imports
        self.reverse_dependencies = defaultdict(set)  # module -> set of modules that import it
        self.all_modules = set()
        
    def normalize_module_path(self, file_path: Path) -> str:
        """Convert file path to module name."""
        try:
            rel_path = file_path.relative_to(self.src_path)
            if rel_path.name == "__init__.py":
                module_parts = rel_path.parent.parts
            else:
                module_parts = rel_path.with_suffix("").parts
            return ".".join(module_parts)
        except ValueError:
            # File is not under src/
            return str(file_path)
    
    def extract_imports_from_file(self, file_path: Path) -> List[str]:
        """Extract all src.* imports from a Python file."""
        imports = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST to get imports
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name.startswith('src.'):
                                imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.module.startswith('src.'):
                            imports.append(node.module)
            except SyntaxError:
                # Fall back to regex if AST parsing fails
                import_patterns = [
                    r'from\s+(src\.[^\s]+)',
                    r'import\s+(src\.[^\s,]+)'
                ]
                for pattern in import_patterns:
                    matches = re.findall(pattern, content)
                    imports.extend(matches)
                    
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
        return imports
    
    def analyze_all_files(self):
        """Analyze all Python files in the src directory."""
        python_files = list(self.src_path.rglob("*.py"))
        
        for file_path in python_files:
            if file_path.name.startswith('.'):
                continue
                
            module_name = self.normalize_module_path(file_path)
            self.all_modules.add(module_name)
            
            imports = self.extract_imports_from_file(file_path)
            
            for import_stmt in imports:
                # Convert import to module format
                if import_stmt.startswith('src.'):
                    imported_module = import_stmt[4:]  # Remove 'src.' prefix
                    self.dependencies[module_name].add(imported_module)
                    self.reverse_dependencies[imported_module].add(module_name)
    
    def find_cycles(self) -> List[List[str]]:
        """Find all cycles in the dependency graph using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node):
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
                
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.dependencies.get(node, set()):
                dfs(neighbor)
            
            rec_stack.remove(node)
            path.pop()
        
        for module in self.all_modules:
            if module not in visited:
                dfs(module)
        
        return cycles
    
    def find_strongly_connected_components(self) -> List[List[str]]:
        """Find strongly connected components using Tarjan's algorithm."""
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = {}
        sccs = []
        
        def strongconnect(node):
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack[node] = True
            
            for neighbor in self.dependencies.get(node, set()):
                if neighbor not in index:
                    strongconnect(neighbor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
                elif on_stack.get(neighbor, False):
                    lowlinks[node] = min(lowlinks[node], index[neighbor])
            
            if lowlinks[node] == index[node]:
                component = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    component.append(w)
                    if w == node:
                        break
                if len(component) > 1:
                    sccs.append(component)
        
        for node in self.all_modules:
            if node not in index:
                strongconnect(node)
        
        return sccs
    
    def analyze_module_coupling(self) -> Dict[str, Dict[str, int]]:
        """Analyze coupling between major modules."""
        major_modules = ['core', 'monitoring', 'analysis', 'indicators', 'api', 'signal_generation']
        coupling = defaultdict(lambda: defaultdict(int))
        
        for module, deps in self.dependencies.items():
            module_parts = module.split('.')
            if module_parts:
                main_module = module_parts[0]
                if main_module in major_modules:
                    for dep in deps:
                        dep_parts = dep.split('.')
                        if dep_parts:
                            dep_main_module = dep_parts[0]
                            if dep_main_module in major_modules and dep_main_module != main_module:
                                coupling[main_module][dep_main_module] += 1
        
        return dict(coupling)
    
    def generate_report(self) -> str:
        """Generate a comprehensive circular dependency report."""
        report = []
        report.append("# Circular Dependency Analysis Report")
        report.append(f"Generated on: {datetime.now()}")
        report.append(f"Total modules analyzed: {len(self.all_modules)}")
        report.append("")
        
        # Find cycles
        cycles = self.find_cycles()
        report.append(f"## Direct Cycles Found: {len(cycles)}")
        if cycles:
            for i, cycle in enumerate(cycles, 1):
                report.append(f"\n### Cycle {i}:")
                report.append(" -> ".join(cycle))
        else:
            report.append("No direct cycles found.")
        
        report.append("")
        
        # Find strongly connected components
        sccs = self.find_strongly_connected_components()
        report.append(f"## Strongly Connected Components: {len(sccs)}")
        if sccs:
            for i, scc in enumerate(sccs, 1):
                report.append(f"\n### SCC {i} ({len(scc)} modules):")
                for module in sorted(scc):
                    report.append(f"  - {module}")
                    
                # Show interconnections within this SCC
                report.append("  Interconnections:")
                for module in scc:
                    deps_in_scc = [dep for dep in self.dependencies.get(module, set()) if dep in scc]
                    if deps_in_scc:
                        report.append(f"    {module} -> {', '.join(sorted(deps_in_scc))}")
        else:
            report.append("No strongly connected components found.")
        
        report.append("")
        
        # Module coupling analysis
        coupling = self.analyze_module_coupling()
        report.append("## Module Coupling Analysis")
        report.append("Cross-module dependencies by major components:")
        report.append("")
        
        for main_module in sorted(coupling.keys()):
            deps = coupling[main_module]
            if deps:
                report.append(f"### {main_module}:")
                for dep_module, count in sorted(deps.items(), key=lambda x: x[1], reverse=True):
                    report.append(f"  - {dep_module}: {count} dependencies")
                report.append("")
        
        # Core-Monitor specific analysis
        report.append("## Core-Monitoring Circular Dependency Analysis")
        core_to_monitor = 0
        monitor_to_core = 0
        
        for module, deps in self.dependencies.items():
            if module.startswith('core.'):
                monitor_deps = [d for d in deps if d.startswith('monitoring.')]
                core_to_monitor += len(monitor_deps)
                if monitor_deps:
                    report.append(f"  {module} imports from monitoring: {', '.join(monitor_deps)}")
            elif module.startswith('monitoring.'):
                core_deps = [d for d in deps if d.startswith('core.')]
                monitor_to_core += len(core_deps)
                if core_deps:
                    report.append(f"  {module} imports from core: {', '.join(core_deps)}")
        
        report.append(f"Core -> Monitoring dependencies: {core_to_monitor}")
        report.append(f"Monitoring -> Core dependencies: {monitor_to_core}")
        
        if core_to_monitor > 0 and monitor_to_core > 0:
            report.append("⚠️  CIRCULAR DEPENDENCY DETECTED between core and monitoring modules!")
        
        report.append("")
        
        # Recommendations
        report.append("## Recommendations for Breaking Circular Dependencies")
        report.append("")
        
        if sccs or cycles:
            report.append("### Immediate Actions:")
            report.append("1. **Dependency Injection**: Use dependency injection instead of direct imports")
            report.append("2. **Interface Abstraction**: Create abstract base classes/interfaces")
            report.append("3. **Event-Driven Architecture**: Use events/signals instead of direct calls")
            report.append("4. **Factory Pattern**: Use factories to create dependencies at runtime")
            report.append("5. **Configuration-Based Wiring**: Wire dependencies through configuration")
            report.append("")
            
            report.append("### Specific Strategies:")
            report.append("- Move shared interfaces to a separate 'interfaces' module")
            report.append("- Create a 'common' module for shared utilities")
            report.append("- Use lazy imports (import inside functions when needed)")
            report.append("- Implement observer pattern for notifications")
            report.append("- Create a service locator or registry pattern")
        
        return "\n".join(report)

def main():
    if len(sys.argv) > 1:
        root_path = sys.argv[1]
    else:
        root_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    analyzer = CircularDependencyAnalyzer(root_path)
    analyzer.analyze_all_files()
    
    report = analyzer.generate_report()
    print(report)
    
    # Save report to file
    report_path = Path(root_path) / "circular_dependency_analysis.md"
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_path}")

if __name__ == "__main__":
    from datetime import datetime
    main()