#!/usr/bin/env python3
"""
Analyze utils directory and categorize files for cleanup
"""
import os
import ast
from pathlib import Path
from typing import Dict, List, Set

class UtilsAnalyzer:
    def __init__(self, src_path: str):
        self.src_path = Path(src_path)
        self.utils_path = self.src_path / 'utils'
        
        # Define categories
        self.categories = {
            'domain_specific': [],
            'true_utilities': [],
            'logging_related': [],
            'already_moved': [],
            'formatters': [],
            'uncertain': []
        }
        
        # Define domain-specific patterns
        self.domain_patterns = {
            'indicators': ['indicators', 'technical', 'analysis'],
            'cache': ['cache', 'liquidation', 'storage'],
            'validation': ['validator', 'validation', 'validate'],
            'market': ['market', 'trading', 'order'],
            'formatting': ['format', 'formatter', 'pretty'],
        }
        
    def analyze_file(self, file_path: Path) -> str:
        """Analyze a file and determine its category"""
        filename = file_path.name
        
        # Check if already moved
        if not file_path.exists():
            return 'already_moved'
            
        # Special cases
        if filename in ['__init__.py', '__pycache__']:
            return 'true_utilities'
            
        # Logging related
        if 'logging' in filename or 'log' in filename:
            return 'logging_related'
            
        # Formatters
        if 'formatter' in filename or filename == 'formatters':
            return 'formatters'
            
        # Check filename patterns
        for domain, patterns in self.domain_patterns.items():
            for pattern in patterns:
                if pattern in filename.lower():
                    return 'domain_specific'
        
        # Analyze content
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Parse imports to understand dependencies
            tree = ast.parse(content)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # Check if imports suggest domain-specific functionality
            domain_imports = ['indicators', 'core.market', 'monitoring', 'analysis', 'trading']
            for imp in imports:
                for domain in domain_imports:
                    if domain in imp:
                        return 'domain_specific'
            
            # True utilities typically have minimal domain imports
            if len(imports) < 5 and not any(d in str(imports) for d in domain_imports):
                return 'true_utilities'
                
        except Exception:
            pass
            
        return 'uncertain'
        
    def categorize_utils(self) -> Dict[str, List[str]]:
        """Categorize all files in utils directory"""
        for item in self.utils_path.iterdir():
            if item.is_file() and item.suffix == '.py':
                category = self.analyze_file(item)
                self.categories[category].append(item.name)
            elif item.is_dir() and item.name != '__pycache__':
                # Handle subdirectories
                self.categories['true_utilities'].append(f"{item.name}/")
                
        return self.categories
        
    def generate_migration_plan(self) -> Dict[str, str]:
        """Generate migration plan for domain-specific files"""
        migration_plan = {}
        
        # Already identified in the plan
        known_migrations = {
            'indicators.py': 'indicators/utils/indicators.py',
            'liquidation_cache.py': 'core/cache/liquidation_cache.py',
            'data_validator.py': 'validation/validators/data_validator.py',
            'market_context_validator.py': 'validation/validators/context_validator.py',
            'error_handling.py': 'core/error/utils.py',  # Already moved
            'validation.py': 'validation/utils/helpers.py',  # Already moved
        }
        
        # Add any found domain-specific files
        for file in self.categories['domain_specific']:
            if file in known_migrations:
                migration_plan[f'utils/{file}'] = known_migrations[file]
            else:
                # Determine target based on content
                if 'cache' in file:
                    migration_plan[f'utils/{file}'] = f'core/cache/{file}'
                elif 'market' in file or 'trading' in file:
                    migration_plan[f'utils/{file}'] = f'core/market/utils/{file}'
                elif 'indicator' in file:
                    migration_plan[f'utils/{file}'] = f'indicators/utils/{file}'
                    
        return migration_plan
        
    def generate_report(self):
        """Generate analysis report"""
        categories = self.categorize_utils()
        migration_plan = self.generate_migration_plan()
        
        print("=== Utils Directory Analysis ===\n")
        
        for category, files in categories.items():
            if files:
                print(f"{category.upper()} ({len(files)} files):")
                for file in sorted(files):
                    print(f"  - {file}")
                print()
        
        print("=== Migration Plan ===")
        if migration_plan:
            for src, dst in migration_plan.items():
                print(f"  {src} -> {dst}")
        else:
            print("  No files need migration")
            
        print("\n=== Summary ===")
        print(f"Total files analyzed: {sum(len(f) for f in categories.values())}")
        print(f"Files to migrate: {len(migration_plan)}")
        print(f"True utilities to keep: {len(categories['true_utilities'])}")

def main():
    analyzer = UtilsAnalyzer('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')
    analyzer.generate_report()

if __name__ == "__main__":
    main()