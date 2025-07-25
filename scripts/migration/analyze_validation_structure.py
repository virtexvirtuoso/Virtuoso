#!/usr/bin/env python3
"""
Analyze current validation structure and create migration map
"""
import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
import re

class ValidationAnalyzer:
    def __init__(self, src_path: str):
        self.src_path = Path(src_path)
        self.validation_files = {}
        self.imports = {}
        self.duplicates = []
        
    def find_validation_files(self) -> Dict[str, List[str]]:
        """Find all validation-related files in the codebase"""
        validation_files = {
            'core_validation': [],
            'new_validation': [],
            'scattered_validators': [],
            'validation_imports': []
        }
        
        for root, dirs, files in os.walk(self.src_path):
            for file in files:
                if not file.endswith('.py'):
                    continue
                    
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.src_path)
                
                # Categorize validation files
                if 'validation' in str(rel_path) or 'validator' in file.lower():
                    if str(rel_path).startswith('validation/'):
                        validation_files['new_validation'].append(str(rel_path))
                    elif str(rel_path).startswith('core/validation/'):
                        validation_files['core_validation'].append(str(rel_path))
                    else:
                        validation_files['scattered_validators'].append(str(rel_path))
                        
        return validation_files
    
    def analyze_imports(self) -> Dict[str, List[str]]:
        """Analyze validation imports across the codebase"""
        import_patterns = {}
        
        for root, dirs, files in os.walk(self.src_path):
            for file in files:
                if not file.endswith('.py'):
                    continue
                    
                file_path = Path(root) / file
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Find validation imports
                    imports = []
                    
                    # Pattern 1: from X.validation import Y
                    pattern1 = re.findall(r'from\s+[\w\.]*validation[\w\.]*\s+import\s+[\w\s,\(\)]+', content)
                    # Pattern 2: import X.validation
                    pattern2 = re.findall(r'import\s+[\w\.]*validation[\w\.]*', content)
                    # Pattern 3: from X import ValidationY
                    pattern3 = re.findall(r'from\s+[\w\.]+\s+import\s+[\w\s,\(\)]*[Vv]alidat[\w\s,\(\)]*', content)
                    
                    imports.extend(pattern1)
                    imports.extend(pattern2)
                    imports.extend(pattern3)
                    
                    if imports:
                        rel_path = file_path.relative_to(self.src_path)
                        import_patterns[str(rel_path)] = imports
                        
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    
        return import_patterns
    
    def find_duplicates(self) -> List[Tuple[str, str]]:
        """Find potential duplicate validation files"""
        duplicates = []
        file_map = {}
        
        validation_files = self.find_validation_files()
        all_files = []
        for category in validation_files.values():
            all_files.extend(category)
            
        for file_path in all_files:
            basename = Path(file_path).name
            if basename in file_map:
                duplicates.append((file_map[basename], file_path))
            else:
                file_map[basename] = file_path
                
        return duplicates
    
    def create_migration_map(self) -> Dict[str, str]:
        """Create a migration map from old locations to new locations"""
        migration_map = {}
        
        # Define the target structure
        target_structure = {
            # Core validation files
            'core/validation/base.py': 'validation/core/base.py',
            'core/validation/manager.py': 'validation/services/manager.py',
            'core/validation/service.py': 'validation/services/sync_service.py',
            'core/validation/cache.py': 'validation/cache/cache.py',
            'core/validation/context.py': 'validation/core/context.py',
            'core/validation/models.py': 'validation/core/models.py',
            'core/validation/protocols.py': 'validation/core/protocols.py',
            'core/validation/rules.py': 'validation/rules/base.py',
            'core/validation/schemas.py': 'validation/core/schemas.py',
            'core/validation/handler.py': 'validation/core/handler.py',
            
            # Validators
            'core/validation/startup_validator.py': 'validation/validators/startup_validator.py',
            'core/validation/validators.py': 'validation/validators/core_validators.py',
            'core/config/validators/binance_validator.py': 'validation/validators/binance_validator.py',
            'data_processing/market_validator.py': 'validation/validators/market_validator.py',
            'utils/data_validator.py': 'validation/validators/data_validator.py',
            'utils/market_context_validator.py': 'validation/validators/context_validator.py',
            'utils/validation.py': 'validation/utils/helpers.py',
            'analysis/data/validation.py': 'validation/data/analysis_validation.py',
            'analysis/data/validator.py': 'validation/data/analysis_validator.py',
            'config/validator.py': 'validation/config/config_validator.py',
        }
        
        return target_structure
    
    def generate_report(self) -> Dict:
        """Generate a comprehensive report"""
        validation_files = self.find_validation_files()
        imports = self.analyze_imports()
        duplicates = self.find_duplicates()
        migration_map = self.create_migration_map()
        
        report = {
            'summary': {
                'total_validation_files': sum(len(files) for files in validation_files.values()),
                'files_in_new_structure': len(validation_files['new_validation']),
                'files_in_old_structure': len(validation_files['core_validation']),
                'scattered_files': len(validation_files['scattered_validators']),
                'files_with_imports': len(imports),
                'duplicate_pairs': len(duplicates)
            },
            'validation_files': validation_files,
            'imports': imports,
            'duplicates': duplicates,
            'migration_map': migration_map
        }
        
        return report

def main():
    analyzer = ValidationAnalyzer('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src')
    report = analyzer.generate_report()
    
    # Save report
    with open('/Users/ffv_macmini/Desktop/Virtuoso_ccxt/scripts/migration/validation_analysis_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("=== Validation Structure Analysis ===")
    print(f"\nSummary:")
    for key, value in report['summary'].items():
        print(f"  {key}: {value}")
    
    print("\n=== Files by Category ===")
    for category, files in report['validation_files'].items():
        print(f"\n{category} ({len(files)} files):")
        for file in sorted(files)[:5]:  # Show first 5
            print(f"  - {file}")
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more")
    
    print("\n=== Duplicate Files ===")
    for dup1, dup2 in report['duplicates'][:5]:
        print(f"  - {dup1}")
        print(f"    {dup2}")
    
    print("\n=== Migration Required ===")
    for old, new in list(report['migration_map'].items())[:10]:
        print(f"  {old} -> {new}")
    
    print(f"\nFull report saved to: validation_analysis_report.json")

if __name__ == "__main__":
    main()