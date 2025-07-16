"""Migration script to validate and upgrade existing signal files."""

import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List
import logging
import shutil
from datetime import datetime
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from src.models.signal_schema import (
        CompleteSignalData, 
        SignalDataValidator, 
        SignalValidationError,
        SignalComponent,
        SignalDirection,
        SignalStrength,
        SignalType
    )
except ImportError as e:
    print(f"Warning: Could not import signal schema: {e}")
    print("Running in basic mode without schema validation")

class SignalDataMigrator:
    """Migrate and validate existing signal files to new format."""
    
    def __init__(self, source_dir: str = "reports/json"):
        self.source_dir = Path(source_dir)
        self.backup_dir = Path(f"{source_dir}_backup_{int(datetime.now().timestamp())}")
        self.logger = self._setup_logger()
        
        # Statistics
        self.stats = {
            'total_files': 0,
            'migrated_successfully': 0,
            'migration_errors': 0,
            'validation_errors': 0,
            'skipped_files': 0
        }
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for migration process."""
        logger = logging.getLogger('signal_migration')
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        log_file = Path('logs/signal_migration.log')
        log_file.parent.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    async def migrate_all_files(self, dry_run: bool = False):
        """Migrate all signal files to new format."""
        self.logger.info(f"Starting signal data migration (dry_run={dry_run})")
        self.logger.info(f"Source directory: {self.source_dir}")
        
        if not self.source_dir.exists():
            self.logger.error(f"Source directory does not exist: {self.source_dir}")
            return
        
        # Create backup directory
        if not dry_run:
            self.backup_dir.mkdir(exist_ok=True)
            self.logger.info(f"Backup directory: {self.backup_dir}")
        
        # Find all signal files
        signal_files = list(self.source_dir.glob("*usdt_*.json"))
        signal_files.extend(list(self.source_dir.glob("*USDT_*.json")))
        
        # Filter out market reports and other non-signal files
        signal_files = [f for f in signal_files if not f.name.startswith('market_report')]
        
        self.stats['total_files'] = len(signal_files)
        self.logger.info(f"Found {len(signal_files)} signal files to process")
        
        # Process files in batches
        batch_size = 10
        for i in range(0, len(signal_files), batch_size):
            batch = signal_files[i:i + batch_size]
            await self._process_batch(batch, dry_run)
        
        # Print final statistics
        self._print_migration_summary()
    
    async def _process_batch(self, files: List[Path], dry_run: bool):
        """Process a batch of files."""
        for file_path in files:
            try:
                result = await self._migrate_single_file(file_path, dry_run)
                if result:
                    self.stats['migrated_successfully'] += 1
                else:
                    self.stats['migration_errors'] += 1
            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {e}")
                self.stats['migration_errors'] += 1
    
    async def _migrate_single_file(self, file_path: Path, dry_run: bool) -> bool:
        """Migrate a single signal file."""
        try:
            self.logger.debug(f"Processing file: {file_path}")
            
            # Load current data
            try:
                with open(file_path, 'r') as f:
                    current_data = json.load(f)
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error in {file_path}: {e}")
                
                # Attempt to repair JSON
                if not dry_run:
                    repaired_data = await self._attempt_json_repair(file_path)
                    if repaired_data:
                        current_data = repaired_data
                        self.logger.info(f"Successfully repaired JSON in {file_path}")
                    else:
                        self.stats['validation_errors'] += 1
                        return False
                else:
                    self.stats['validation_errors'] += 1
                    return False
            
            # Check if file already has complete structure
            if self._is_complete_signal(current_data):
                self.logger.debug(f"File {file_path} already has complete structure")
                self.stats['skipped_files'] += 1
                return True
            
            # Generate complete signal data
            complete_data = await self._complete_signal_data(current_data)
            
            if not dry_run:
                # Backup original file
                backup_path = self.backup_dir / file_path.name
                shutil.copy2(file_path, backup_path)
                
                # Write updated file
                with open(file_path, 'w') as f:
                    json.dump(complete_data, f, indent=2)
                
                self.logger.info(f"Successfully migrated {file_path}")
            else:
                self.logger.info(f"Would migrate {file_path} (dry run)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to migrate {file_path}: {e}")
            return False
    
    def _is_complete_signal(self, data: Dict[str, Any]) -> bool:
        """Check if signal data already has complete structure."""
        required_components = {
            'momentum', 'technical', 'volume', 'orderflow', 
            'orderbook', 'sentiment', 'price_action', 'beta_exp', 
            'confluence', 'whale_act', 'liquidation'
        }
        
        components = data.get('components', {})
        existing_components = set(components.keys())
        
        return required_components.issubset(existing_components)
    
    async def _complete_signal_data(self, current_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete missing signal components using estimation methods."""
        
        # Start with current data
        complete_data = current_data.copy()
        
        # Ensure required top-level fields
        complete_data.setdefault('symbol', complete_data.get('symbol', 'UNKNOWN'))
        complete_data.setdefault('signal_type', 'BUY')
        complete_data.setdefault('confluence_score', complete_data.get('confluence_score', 50.0))
        complete_data.setdefault('price', complete_data.get('price', 0.0))
        complete_data.setdefault('timestamp', complete_data.get('timestamp', int(datetime.now().timestamp() * 1000)))
        complete_data.setdefault('transaction_id', complete_data.get('transaction_id', f"migrated_{int(datetime.now().timestamp())}"))
        complete_data.setdefault('signal_id', complete_data.get('signal_id', f"signal_{int(datetime.now().timestamp())}"))
        
        # Ensure components dict exists
        if 'components' not in complete_data:
            complete_data['components'] = {}
        
        # Fill missing components with estimated values
        existing_components = complete_data['components']
        all_components = [
            'momentum', 'technical', 'volume', 'orderflow', 
            'orderbook', 'sentiment', 'price_action', 'beta_exp', 
            'confluence', 'whale_act', 'liquidation'
        ]
        
        for component in all_components:
            if component not in existing_components:
                estimated_component = await self._estimate_missing_component(
                    component, existing_components, complete_data
                )
                existing_components[component] = estimated_component
            else:
                # Ensure existing component has all required fields
                existing_components[component] = await self._normalize_component(
                    existing_components[component], component
                )
        
        # Ensure results dict is complete
        complete_data['results'] = await self._complete_results_data(
            complete_data.get('results', {}), existing_components
        )
        
        return complete_data
    
    async def _estimate_missing_component(
        self, 
        component: str, 
        existing: Dict[str, Any], 
        signal_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Estimate missing component based on existing data."""
        
        # Use confluence score as baseline
        base_score = signal_data.get('confluence_score', 50.0)
        
        # Component-specific estimation logic
        estimation_rules = {
            'momentum': lambda: base_score * 0.9,
            'technical': lambda: base_score * 1.0,
            'volume': lambda: base_score * 0.95,
            'orderflow': lambda: base_score * 1.1,
            'orderbook': lambda: base_score * 0.95,
            'sentiment': lambda: base_score * 0.8,
            'price_action': lambda: base_score,
            'beta_exp': lambda: 50.0,  # Neutral default
            'confluence': lambda: base_score,
            'whale_act': lambda: base_score * 0.8,
            'liquidation': lambda: base_score * 0.85
        }
        
        estimated_score = estimation_rules.get(component, lambda: base_score)()
        estimated_score = max(0, min(100, estimated_score))
        
        return {
            'score': estimated_score,
            'confidence': 0.5,  # Lower confidence for estimated data
            'direction': 'bullish' if estimated_score > 60 else 'bearish' if estimated_score < 40 else 'neutral',
            'strength': 'strong' if abs(estimated_score - 50) > 20 else 'medium',
            'raw_value': estimated_score,
            'calculation_method': 'estimated_migration',
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
    
    async def _normalize_component(self, component_data: Any, component_name: str) -> Dict[str, Any]:
        """Normalize existing component data to match schema."""
        if isinstance(component_data, (int, float)):
            # Simple score value
            score = float(component_data)
            return {
                'score': score,
                'confidence': 0.7,
                'direction': 'bullish' if score > 60 else 'bearish' if score < 40 else 'neutral',
                'strength': 'strong' if abs(score - 50) > 20 else 'medium',
                'raw_value': score,
                'calculation_method': 'legacy_migration',
                'timestamp': int(datetime.now().timestamp() * 1000)
            }
        elif isinstance(component_data, dict):
            # Ensure all required fields
            normalized = component_data.copy()
            normalized.setdefault('score', normalized.get('score', 50.0))
            normalized.setdefault('confidence', 0.7)
            
            score = normalized['score']
            normalized.setdefault('direction', 'bullish' if score > 60 else 'bearish' if score < 40 else 'neutral')
            normalized.setdefault('strength', 'strong' if abs(score - 50) > 20 else 'medium')
            normalized.setdefault('raw_value', score)
            normalized.setdefault('calculation_method', 'legacy_data')
            normalized.setdefault('timestamp', int(datetime.now().timestamp() * 1000))
            
            return normalized
        else:
            # Fallback for unexpected data types
            return await self._estimate_missing_component(component_name, {}, {'confluence_score': 50.0})
    
    async def _complete_results_data(
        self, 
        existing_results: Dict[str, Any], 
        components: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Complete results data structure."""
        results = existing_results.copy()
        
        # Ensure basic results for each component
        for component_name in components.keys():
            if component_name not in results:
                results[component_name] = {}
        
        return results
    
    async def _attempt_json_repair(self, file_path: Path) -> Dict[str, Any]:
        """Attempt to repair malformed JSON files."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Common JSON repair strategies
            repair_strategies = [
                self._fix_trailing_commas,
                self._fix_unquoted_keys
            ]
            
            for strategy in repair_strategies:
                try:
                    repaired = strategy(content)
                    if repaired:
                        return json.loads(repaired)
                except:
                    continue
            
            return None
            
        except Exception as e:
            self.logger.error(f"JSON repair failed for {file_path}: {e}")
            return None
    
    def _fix_trailing_commas(self, content: str) -> str:
        """Remove trailing commas that cause JSON parsing errors."""
        import re
        # Remove trailing commas before closing braces/brackets
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        return content
    
    def _fix_unquoted_keys(self, content: str) -> str:
        """Add quotes to unquoted JSON keys."""
        import re
        # Find unquoted keys and add quotes
        content = re.sub(r'(\w+)(\s*:)', r'"\1"\2', content)
        return content
    
    def _print_migration_summary(self):
        """Print migration statistics summary."""
        self.logger.info("=" * 60)
        self.logger.info("SIGNAL DATA MIGRATION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total files processed: {self.stats['total_files']}")
        self.logger.info(f"Successfully migrated: {self.stats['migrated_successfully']}")
        self.logger.info(f"Migration errors: {self.stats['migration_errors']}")
        self.logger.info(f"Validation errors: {self.stats['validation_errors']}")
        self.logger.info(f"Skipped (already complete): {self.stats['skipped_files']}")
        
        success_rate = (self.stats['migrated_successfully'] / self.stats['total_files'] * 100) if self.stats['total_files'] > 0 else 0
        self.logger.info(f"Success rate: {success_rate:.1f}%")
        
        if self.backup_dir.exists():
            self.logger.info(f"Backup directory: {self.backup_dir}")
        
        self.logger.info("=" * 60)

async def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate signal data files to complete format')
    parser.add_argument('--source-dir', default='reports/json', help='Source directory containing signal files')
    parser.add_argument('--dry-run', action='store_true', help='Validate files without making changes')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.verbose:
        logging.getLogger('signal_migration').setLevel(logging.DEBUG)
    
    # Create migrator and run
    migrator = SignalDataMigrator(args.source_dir)
    await migrator.migrate_all_files(dry_run=args.dry_run)

if __name__ == "__main__":
    asyncio.run(main()) 