#!/usr/bin/env python3
"""
Tight Coupling Analysis Tool
Analyzes tight coupling patterns and provides detailed breakdown
"""

import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
import ast

class TightCouplingAnalyzer:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.src_path = self.root_path / "src"
        self.imports_by_file = {}  # file_path -> list of imports
        self.coupling_matrix = defaultdict(lambda: defaultdict(list))  # module1 -> module2 -> [files]
        
    def analyze_file_imports(self, file_path: Path) -> List[Tuple[str, str]]:
        """Extract detailed import information from a file."""
        imports = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract imports with line numbers
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Match various import patterns
                patterns = [
                    r'from\s+(src\.[^\s]+)\s+import\s+(.+)',  # from src.module import something
                    r'import\s+(src\.[^\s,]+)',               # import src.module
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, line)
                    for match in matches:
                        if isinstance(match, tuple):
                            module, imported_items = match
                            imports.append((module, imported_items, line_num, line))
                        else:
                            imports.append((match, '', line_num, line))
                            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            
        return imports
    
    def get_module_category(self, module_path: str) -> str:
        """Categorize a module path into main categories."""
        if module_path.startswith('src.'):
            module_path = module_path[4:]  # Remove 'src.' prefix
            
        parts = module_path.split('.')
        if parts:
            return parts[0]
        return 'unknown'
    
    def analyze_all_files(self):
        """Analyze all Python files for import patterns."""
        python_files = list(self.src_path.rglob("*.py"))
        
        for file_path in python_files:
            if file_path.name.startswith('.'):
                continue
                
            imports = self.analyze_file_imports(file_path)
            self.imports_by_file[file_path] = imports
            
            # Build coupling matrix
            file_module = self.get_file_module(file_path)
            file_category = self.get_module_category(file_module)
            
            for import_info in imports:
                imported_module = import_info[0]
                imported_category = self.get_module_category(imported_module)
                
                if file_category != imported_category:
                    self.coupling_matrix[file_category][imported_category].append({
                        'file': str(file_path),
                        'module': file_module,
                        'imports': imported_module,
                        'items': import_info[1] if len(import_info) > 1 else '',
                        'line_num': import_info[2] if len(import_info) > 2 else 0,
                        'line_content': import_info[3] if len(import_info) > 3 else ''
                    })
    
    def get_file_module(self, file_path: Path) -> str:
        """Convert file path to module name."""
        try:
            rel_path = file_path.relative_to(self.src_path)
            if rel_path.name == "__init__.py":
                module_parts = rel_path.parent.parts
            else:
                module_parts = rel_path.with_suffix("").parts
            return "src." + ".".join(module_parts)
        except ValueError:
            return str(file_path)
    
    def find_bidirectional_dependencies(self) -> List[Tuple[str, str, int, int]]:
        """Find pairs of modules that depend on each other."""
        bidirectional = []
        
        for module1, deps in self.coupling_matrix.items():
            for module2, files in deps.items():
                if module2 in self.coupling_matrix and module1 in self.coupling_matrix[module2]:
                    count1 = len(files)
                    count2 = len(self.coupling_matrix[module2][module1])
                    bidirectional.append((module1, module2, count1, count2))
        
        # Remove duplicates (A->B, B->A is the same as B->A, A->B)
        seen = set()
        unique_bidirectional = []
        for item in bidirectional:
            key = tuple(sorted([item[0], item[1]]))
            if key not in seen:
                seen.add(key)
                unique_bidirectional.append(item)
        
        return unique_bidirectional
    
    def analyze_core_monitor_coupling(self) -> Dict[str, Any]:
        """Detailed analysis of core-monitoring coupling."""
        core_to_monitor = self.coupling_matrix.get('core', {}).get('monitoring', [])
        monitor_to_core = self.coupling_matrix.get('monitoring', {}).get('core', [])
        
        analysis = {
            'core_to_monitoring': {
                'count': len(core_to_monitor),
                'files': {},
                'imports': set()
            },
            'monitoring_to_core': {
                'count': len(monitor_to_core),
                'files': {},
                'imports': set()
            }
        }
        
        # Analyze core -> monitoring
        for import_info in core_to_monitor:
            file_name = Path(import_info['file']).name
            if file_name not in analysis['core_to_monitoring']['files']:
                analysis['core_to_monitoring']['files'][file_name] = []
            analysis['core_to_monitoring']['files'][file_name].append({
                'imports': import_info['imports'],
                'items': import_info['items'],
                'line_num': import_info['line_num']
            })
            analysis['core_to_monitoring']['imports'].add(import_info['imports'])
        
        # Analyze monitoring -> core
        for import_info in monitor_to_core:
            file_name = Path(import_info['file']).name
            if file_name not in analysis['monitoring_to_core']['files']:
                analysis['monitoring_to_core']['files'][file_name] = []
            analysis['monitoring_to_core']['files'][file_name].append({
                'imports': import_info['imports'],
                'items': import_info['items'],
                'line_num': import_info['line_num']
            })
            analysis['monitoring_to_core']['imports'].add(import_info['imports'])
        
        return analysis
    
    def generate_detailed_report(self) -> str:
        """Generate a comprehensive tight coupling report."""
        report = []
        report.append("# Tight Coupling Analysis Report")
        report.append(f"Generated on: {datetime.now()}")
        report.append("")
        
        # Overall coupling statistics
        report.append("## Overall Coupling Statistics")
        total_cross_dependencies = sum(len(deps) for deps in self.coupling_matrix.values() for deps in deps.values())
        report.append(f"Total cross-module dependencies: {total_cross_dependencies}")
        report.append("")
        
        # Coupling matrix overview
        report.append("## Module Coupling Matrix")
        report.append("| From Module | To Module | Dependency Count |")
        report.append("|-------------|-----------|------------------|")
        
        for from_module in sorted(self.coupling_matrix.keys()):
            for to_module in sorted(self.coupling_matrix[from_module].keys()):
                count = len(self.coupling_matrix[from_module][to_module])
                report.append(f"| {from_module} | {to_module} | {count} |")
        
        report.append("")
        
        # Bidirectional dependencies
        bidirectional = self.find_bidirectional_dependencies()
        report.append(f"## Bidirectional Dependencies: {len(bidirectional)}")
        
        if bidirectional:
            for module1, module2, count1, count2 in bidirectional:
                report.append(f"\n### {module1} ↔ {module2}")
                report.append(f"- {module1} → {module2}: {count1} dependencies")
                report.append(f"- {module2} → {module1}: {count2} dependencies")
                report.append(f"- **Coupling Strength**: {count1 + count2}")
        else:
            report.append("No bidirectional dependencies found.")
        
        report.append("")
        
        # Detailed core-monitoring analysis
        core_monitor_analysis = self.analyze_core_monitor_coupling()
        report.append("## Core-Monitoring Coupling Detailed Analysis")
        
        report.append("\n### Core → Monitoring Dependencies")
        core_to_mon = core_monitor_analysis['core_to_monitoring']
        report.append(f"Total: {core_to_mon['count']} dependencies")
        
        if core_to_mon['files']:
            for file_name, imports in core_to_mon['files'].items():
                report.append(f"\n**{file_name}:**")
                for imp in imports:
                    report.append(f"  - Line {imp['line_num']}: `{imp['imports']}` ({imp['items']})")
        
        report.append("\n### Monitoring → Core Dependencies") 
        mon_to_core = core_monitor_analysis['monitoring_to_core']
        report.append(f"Total: {mon_to_core['count']} dependencies")
        
        if mon_to_core['files']:
            for file_name, imports in mon_to_core['files'].items():
                report.append(f"\n**{file_name}:**")
                for imp in imports:
                    report.append(f"  - Line {imp['line_num']}: `{imp['imports']}` ({imp['items']})")
        
        # High coupling modules
        report.append("\n\n## Modules with Highest Coupling")
        coupling_scores = {}
        for from_module, to_modules in self.coupling_matrix.items():
            outgoing = sum(len(deps) for deps in to_modules.values())
            incoming = sum(len(self.coupling_matrix[other][from_module]) 
                          for other in self.coupling_matrix 
                          if from_module in self.coupling_matrix[other])
            coupling_scores[from_module] = outgoing + incoming
        
        sorted_modules = sorted(coupling_scores.items(), key=lambda x: x[1], reverse=True)
        for module, score in sorted_modules[:10]:  # Top 10
            report.append(f"- **{module}**: {score} total dependencies")
        
        # Recommendations
        report.append("\n\n## Detailed Recommendations")
        
        report.append("\n### 1. Break Core-Monitoring Circular Dependency")
        report.append("**Problem**: Core and monitoring modules have bidirectional dependencies")
        report.append("**Solutions**:")
        report.append("- Create `src/interfaces/` module for shared contracts")
        report.append("- Move `AlertManager` and `MetricsManager` to `src/services/`")
        report.append("- Use dependency injection for core services in monitoring")
        report.append("- Implement observer pattern for notifications")
        
        report.append("\n### 2. Resolve Indicators-Analysis Circular Dependency")
        report.append("**Problem**: OrderflowIndicators imports DataValidator from confluence")
        report.append("**Solutions**:")
        report.append("- Move `DataValidator` to `src/utils/validation/`")
        report.append("- Create abstract base validator that both modules can inherit")
        report.append("- Use composition instead of inheritance for validation")
        
        report.append("\n### 3. Implement Dependency Injection Container")
        report.append("**Create**: `src/container/dependency_container.py`")
        report.append("**Benefits**: Centralized dependency management, easier testing, loose coupling")
        
        report.append("\n### 4. Create Shared Interfaces Module")
        report.append("**Create**: `src/interfaces/` with abstract base classes")
        report.append("**Move**: Common interfaces used by multiple modules")
        report.append("**Result**: Reduced coupling through abstraction")
        
        report.append("\n### 5. Event-Driven Architecture")
        report.append("**Create**: `src/events/` module with event bus")
        report.append("**Replace**: Direct method calls with event publishing/subscribing")
        report.append("**Benefits**: Loose coupling, better scalability")
        
        return "\n".join(report)

def main():
    if len(sys.argv) > 1:
        root_path = sys.argv[1]
    else:
        root_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    analyzer = TightCouplingAnalyzer(root_path)
    analyzer.analyze_all_files()
    
    report = analyzer.generate_detailed_report()
    print(report)
    
    # Save report to file
    report_path = Path(root_path) / "tight_coupling_analysis.md"
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"\nDetailed coupling report saved to: {report_path}")

if __name__ == "__main__":
    from datetime import datetime
    main()