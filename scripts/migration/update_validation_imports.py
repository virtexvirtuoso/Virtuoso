#\!/usr/bin/env python3
"""
Update validation imports across the codebase
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

class ImportUpdater:
    def __init__(self, src_path: str, dry_run: bool = True):
        self.src_path = Path(src_path)
        self.dry_run = dry_run
        self.updated_files = []
        self.errors = []
        
        # Comprehensive import mapping
        self.import_map = {
            # Core validation
            'from core.validation import': 'from validation.core import',
            'from src.core.validation import': 'from src.validation.core import',
            'from ..core.validation import': 'from ..validation.core import',
            'from ...core.validation import': 'from ...validation.core import',
            'import core.validation': 'import validation.core',
            'import src.core.validation': 'import src.validation.core',
            
            # Specific module mappings
            'core.validation.base': 'validation.core.base',
            'core.validation.manager': 'validation.services.manager',
            'core.validation.service': 'validation.services.sync_service',
            'core.validation.cache': 'validation.cache.cache',
            'core.validation.context': 'validation.core.context',
            'core.validation.models': 'validation.core.models',
            'core.validation.protocols': 'validation.core.protocols',
            'core.validation.rules': 'validation.rules.base',
            'core.validation.schemas': 'validation.core.schemas',
            'core.validation.handler': 'validation.core.handler',
            'core.validation.startup_validator': 'validation.validators.startup_validator',
            'core.validation.validators': 'validation.validators.core_validators',
            
            # Config validators
            'from core.config.validators import': 'from validation.validators import',
            'from src.core.config.validators import': 'from src.validation.validators import',
            'core.config.validators.binance_validator': 'validation.validators.binance_validator',
            
            # Utils validators
            'from utils.validation import': 'from validation.utils.helpers import',
            'from src.utils.validation import': 'from src.validation.utils.helpers import',
            'from utils.data_validator import': 'from validation.validators.data_validator import',
            'from src.utils.data_validator import': 'from src.validation.validators.data_validator import',
            'from utils.market_context_validator import': 'from validation.validators.context_validator import',
            'from src.utils.market_context_validator import': 'from src.validation.validators.context_validator import',
            'utils.validation': 'validation.utils.helpers',
            'utils.data_validator': 'validation.validators.data_validator',
            'utils.market_context_validator': 'validation.validators.context_validator',
            
            # Data processing validators
            'from data_processing.market_validator import': 'from validation.validators.market_validator import',
            'from src.data_processing.market_validator import': 'from src.validation.validators.market_validator import',
            'data_processing.market_validator': 'validation.validators.market_validator',
            
            # Analysis validators
            'from analysis.data.validation import': 'from validation.data.analysis_validation import',
            'from src.analysis.data.validation import': 'from src.validation.data.analysis_validation import',
            'from analysis.data.validator import': 'from validation.data.analysis_validator import',
            'from src.analysis.data.validator import': 'from src.validation.data.analysis_validator import',
            'analysis.data.validation': 'validation.data.analysis_validation',
            'analysis.data.validator': 'validation.data.analysis_validator',
            
            # Config validator
            'from config.validator import': 'from validation.config.config_validator import',
            'from src.config.validator import': 'from src.validation.config.config_validator import',
            'config.validator': 'validation.config.config_validator',
        }
        
    def update_file(self, file_path: Path) -> bool:
        """Update imports in a single file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            
            # Apply all import mappings
            for old_import, new_import in self.import_map.items():
                if old_import in content:
                    content = content.replace(old_import, new_import)
            
            # Handle relative imports that might be affected
            if str(file_path).startswith(str(self.src_path / 'core')):
                # Files in core might have relative imports to validation
                content = re.sub(r'from \.validation\b', 'from ..validation.core', content)
                content = re.sub(r'from \.\.validation\b', 'from ...validation.core', content)
            
            # Fix any double validation paths that might have been created
            content = re.sub(r'validation\.validation', 'validation', content)
            
            # Check if file was modified
            if content != original_content:
                if not self.dry_run:
                    file_path.write_text(content, encoding='utf-8')
                
                self.updated_files.append(str(file_path.relative_to(self.src_path)))
                return True
                
        except Exception as e:
            self.errors.append(f"Error updating {file_path}: {e}")
            
        return False
    
    def find_validation_imports(self, file_path: Path) -> List[str]:
        """Find all validation-related imports in a file"""
        imports = []
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Find all import statements
            import_patterns = [
                r'from\s+[\w\.]*validation[\w\.]*\s+import\s+[\w\s,\(\)]+',
                r'import\s+[\w\.]*validation[\w\.]*',
                r'from\s+[\w\.]*validator[\w\.]*\s+import\s+[\w\s,\(\)]+',
                r'import\s+[\w\.]*validator[\w\.]*',
            ]
            
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                imports.extend(matches)
                
        except Exception as e:
            self.errors.append(f"Error reading {file_path}: {e}")
            
        return imports
    
    def run_update(self):
        """Run the import update process"""
        print(f"Starting import update (dry_run={self.dry_run})")
        print("=" * 60)
        
        # Find all Python files
        python_files = []
        for root, dirs, files in os.walk(self.src_path):
            # Skip __pycache__ directories
            if '__pycache__' in root:
                continue
                
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        print(f"Found {len(python_files)} Python files to check")
        
        # Update imports
        files_with_validation_imports = 0
        files_updated = 0
        
        for file_path in python_files:
            # Check if file has validation imports
            imports = self.find_validation_imports(file_path)
            if imports:
                files_with_validation_imports += 1
                
                # Update the file
                if self.update_file(file_path):
                    files_updated += 1
        
        # Print summary
        print(f"\nSummary:")
        print(f"  Files with validation imports: {files_with_validation_imports}")
        print(f"  Files updated: {files_updated}")
        print(f"  Errors: {len(self.errors)}")
        
        if self.updated_files and not self.dry_run:
            print(f"\nUpdated files:")
            for file in sorted(self.updated_files)[:10]:
                print(f"  - {file}")
            if len(self.updated_files) > 10:
                print(f"  ... and {len(self.updated_files) - 10} more")
        
        if self.errors:
            print(f"\nErrors:")
            for error in self.errors[:5]:
                print(f"  - {error}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more")
        
        # Save detailed log
        log_file = Path('import_update_log.txt')
        with open(log_file, 'w') as f:
            f.write("Import Update Log\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Updated Files ({len(self.updated_files)}):\n")
            for file in sorted(self.updated_files):
                f.write(f"  {file}\n")
            
            f.write(f"\nErrors ({len(self.errors)}):\n")
            for error in self.errors:
                f.write(f"  {error}\n")
        
        print(f"\nDetailed log saved to: {log_file}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Update validation imports')
    parser.add_argument('--execute', action='store_true', help='Execute updates (default is dry-run)')
    parser.add_argument('--src', default='/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src', help='Source directory')
    
    args = parser.parse_args()
    
    updater = ImportUpdater(args.src, dry_run=not args.execute)
    updater.run_update()

if __name__ == "__main__":
    main()