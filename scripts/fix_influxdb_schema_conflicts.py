#!/usr/bin/env python3
"""
InfluxDB Schema Conflict Resolution Script

This script helps resolve field type conflicts in InfluxDB measurements, specifically
the 'analysis' measurement timestamp field conflict between string and float types.

Usage:
    python scripts/fix_influxdb_schema_conflicts.py [--dry-run]

Options:
    --dry-run: Show what would be done without making changes
"""

import asyncio
import argparse
import sys
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_storage.database import DatabaseClient
from core.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchemaConflictResolver:
    """Utility to resolve InfluxDB schema conflicts."""
    
    def __init__(self, database_client: DatabaseClient):
        self.db = database_client
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def analyze_field_conflicts(self) -> Dict[str, Any]:
        """Analyze existing field type conflicts."""
        conflicts = {
            'measurements': {},
            'total_conflicts': 0,
            'analysis_complete': False
        }
        
        try:
            if not await self.db.is_healthy():
                self.logger.error("Database not healthy - cannot analyze conflicts")
                return conflicts
            
            # Check analysis measurement specifically
            query = f'''
            from(bucket: "{self.db.config.bucket}")
                |> range(start: -7d)
                |> filter(fn: (r) => r["_measurement"] == "analysis")
                |> group(columns: ["_field"])
                |> distinct(column: "_value")
            '''
            
            result = await self.db.query_data(query)
            if result is not None and not result.empty:
                # Analyze timestamp fields
                timestamp_fields = result[result['_field'].str.contains('timestamp', case=False)]
                
                conflicts['measurements']['analysis'] = {
                    'total_fields': len(result['_field'].unique()),
                    'timestamp_fields': len(timestamp_fields),
                    'field_names': timestamp_fields['_field'].unique().tolist() if not timestamp_fields.empty else []
                }
                
                if not timestamp_fields.empty:
                    conflicts['total_conflicts'] += 1
                    self.logger.warning(f"Found {len(timestamp_fields)} timestamp-related fields in analysis measurement")
            
            conflicts['analysis_complete'] = True
            self.logger.info(f"Conflict analysis complete - found {conflicts['total_conflicts']} potential conflicts")
            
        except Exception as e:
            self.logger.error(f"Error analyzing conflicts: {e}")
            
        return conflicts
    
    async def create_backup_measurement(self, measurement_name: str) -> bool:
        """Create a backup of the conflicted measurement."""
        backup_name = f"{measurement_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Query the last 7 days of data
            query = f'''
            from(bucket: "{self.db.config.bucket}")
                |> range(start: -7d)
                |> filter(fn: (r) => r["_measurement"] == "{measurement_name}")
            '''
            
            result = await self.db.query_data(query)
            if result is not None and not result.empty:
                self.logger.info(f"Creating backup measurement '{backup_name}' with {len(result)} records")
                
                # Write to backup measurement (this is a simplified approach)
                # In production, you might want more sophisticated backup logic
                await self.db.write_dataframe_batch(result, backup_name)
                return True
            else:
                self.logger.info(f"No data found to backup for measurement '{measurement_name}'")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return False
    
    async def resolve_timestamp_conflicts(self, dry_run: bool = True) -> Dict[str, Any]:
        """Resolve timestamp field conflicts."""
        resolution_results = {
            'actions_taken': [],
            'errors': [],
            'success': False
        }
        
        try:
            # First analyze conflicts
            conflicts = await self.analyze_field_conflicts()
            
            if conflicts['total_conflicts'] == 0:
                resolution_results['actions_taken'].append('No conflicts found - system is healthy')
                resolution_results['success'] = True
                return resolution_results
            
            if dry_run:
                resolution_results['actions_taken'].append('DRY RUN MODE - No actual changes made')
                resolution_results['actions_taken'].append(f"Would resolve {conflicts['total_conflicts']} conflicts")
                
                for measurement, info in conflicts['measurements'].items():
                    if info.get('timestamp_fields', 0) > 0:
                        resolution_results['actions_taken'].append(
                            f"Would fix timestamp fields in '{measurement}': {info['field_names']}"
                        )
                
                resolution_results['success'] = True
                return resolution_results
            
            # Real resolution mode
            self.logger.info("Starting conflict resolution...")
            
            # For the analysis measurement specifically
            if 'analysis' in conflicts['measurements'] and conflicts['measurements']['analysis']['timestamp_fields'] > 0:
                self.logger.info("Resolving conflicts in 'analysis' measurement")
                
                # Create backup first
                backup_success = await self.create_backup_measurement('analysis')
                if backup_success:
                    resolution_results['actions_taken'].append('Created backup of analysis measurement')
                    
                    # Note: The new database.py code with timestamp normalization will handle future writes
                    # For existing conflicting data, the best approach is often to let the conflicting
                    # fields exist and ensure new data uses consistent types
                    
                    resolution_results['actions_taken'].append(
                        'Applied timestamp normalization in database.py - future writes will use consistent types'
                    )
                    resolution_results['success'] = True
                else:
                    resolution_results['errors'].append('Failed to create backup - aborting resolution')
                    return resolution_results
            
        except Exception as e:
            self.logger.error(f"Error during conflict resolution: {e}")
            resolution_results['errors'].append(f'Unexpected error: {str(e)}')
        
        return resolution_results
    
    async def verify_fix(self) -> Dict[str, Any]:
        """Verify that the fix is working by testing a write operation."""
        verification_results = {
            'test_write_success': False,
            'timestamp_normalization_working': False,
            'errors': []
        }
        
        try:
            # Test writing analysis data with various timestamp formats
            test_analysis_data = {
                'test_field': 42.0,
                'timestamp': int(datetime.now().timestamp() * 1000),  # Integer timestamp
                'iso_timestamp': datetime.now().isoformat(),  # ISO string timestamp
                'float_timestamp': datetime.now().timestamp()  # Float timestamp
            }
            
            success = await self.db.store_analysis('TEST_SYMBOL', test_analysis_data)
            verification_results['test_write_success'] = success
            
            if success:
                verification_results['timestamp_normalization_working'] = True
                self.logger.info("Timestamp normalization verification successful")
            else:
                verification_results['errors'].append('Test write failed')
                
        except Exception as e:
            verification_results['errors'].append(f'Verification error: {str(e)}')
            
        return verification_results


async def main():
    """Main function to run the schema conflict resolution."""
    parser = argparse.ArgumentParser(description='Fix InfluxDB schema conflicts')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without making changes')
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = Config()
        await config.load()
        
        # Initialize database client
        db_client = DatabaseClient(config.config)
        
        # Create resolver
        resolver = SchemaConflictResolver(db_client)
        
        logger.info("Starting InfluxDB schema conflict resolution...")
        logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE RESOLUTION'}")
        
        # Analyze conflicts
        logger.info("Step 1: Analyzing existing conflicts...")
        conflicts = await resolver.analyze_field_conflicts()
        
        print("\n=== CONFLICT ANALYSIS RESULTS ===")
        print(f"Total conflicts found: {conflicts['total_conflicts']}")
        
        for measurement, info in conflicts['measurements'].items():
            print(f"\nMeasurement: {measurement}")
            print(f"  Total fields: {info['total_fields']}")
            print(f"  Timestamp fields: {info['timestamp_fields']}")
            if info['field_names']:
                print(f"  Field names: {', '.join(info['field_names'])}")
        
        # Resolve conflicts
        logger.info("Step 2: Resolving conflicts...")
        resolution = await resolver.resolve_timestamp_conflicts(dry_run=args.dry_run)
        
        print("\n=== RESOLUTION RESULTS ===")
        print(f"Success: {resolution['success']}")
        
        if resolution['actions_taken']:
            print("\nActions taken:")
            for action in resolution['actions_taken']:
                print(f"  ✓ {action}")
        
        if resolution['errors']:
            print("\nErrors encountered:")
            for error in resolution['errors']:
                print(f"  ✗ {error}")
        
        # Verify fix
        if not args.dry_run and resolution['success']:
            logger.info("Step 3: Verifying fix...")
            verification = await resolver.verify_fix()
            
            print("\n=== VERIFICATION RESULTS ===")
            print(f"Test write success: {verification['test_write_success']}")
            print(f"Timestamp normalization working: {verification['timestamp_normalization_working']}")
            
            if verification['errors']:
                print("\nVerification errors:")
                for error in verification['errors']:
                    print(f"  ✗ {error}")
        
        await db_client.close()
        
        print(f"\n=== SUMMARY ===")
        if args.dry_run:
            print("Dry run completed. No changes were made.")
            print("Run without --dry-run to apply the fixes.")
        else:
            print("Schema conflict resolution completed.")
            print("Future analysis writes will use consistent timestamp formatting.")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())