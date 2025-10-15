#!/usr/bin/env python3
"""
InfluxDB Bucket Retention Management Script

This script helps manage InfluxDB bucket retention policies to prevent disk full conditions.
It can list current buckets, update retention policies, and estimate disk usage.
"""

import argparse
import json
import logging
import os
import sys
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InfluxDBRetentionManager:
    """Manages InfluxDB bucket retention policies."""

    def __init__(self, influx_host: str = "localhost:8086",
                 org: Optional[str] = None, token: Optional[str] = None):
        """Initialize the retention manager.

        Args:
            influx_host: InfluxDB host and port
            org: Organization name (from env if not provided)
            token: Auth token (from env if not provided)
        """
        self.host = influx_host
        self.org = org or os.getenv('INFLUXDB_ORG', 'virtuoso-org')
        self.token = token or os.getenv('INFLUXDB_TOKEN')

        if not self.token or self.token == 'demo-token-placeholder':
            logger.warning("No valid InfluxDB token found - some operations may fail")

    def _run_influx_command(self, command: List[str]) -> Optional[str]:
        """Run an InfluxDB CLI command and return output."""
        try:
            full_command = ['influx'] + command
            if self.token:
                full_command.extend(['--token', self.token])
            full_command.extend(['--host', f'http://{self.host}'])

            logger.debug(f"Running command: {' '.join(full_command)}")
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"InfluxDB command failed: {e.stderr}")
            return None
        except FileNotFoundError:
            logger.error("InfluxDB CLI not found - please install influxdb2-cli")
            return None

    def list_buckets(self) -> Optional[List[Dict[str, Any]]]:
        """List all buckets with their retention settings."""
        try:
            output = self._run_influx_command(['bucket', 'list', '--json'])
            if not output:
                return None

            # Safely parse JSON output
            try:
                buckets = json.loads(output)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse InfluxDB bucket list JSON: {e}")
                logger.debug(f"Raw output: {output}")
                return None

            if not isinstance(buckets, list):
                logger.error(f"Expected list from bucket list, got {type(buckets)}")
                return None

            # Format bucket information
            bucket_info = []
            for bucket in buckets:
                retention_rules = bucket.get('retentionRules', [])
                if retention_rules:
                    retention_seconds = retention_rules[0].get('everySeconds', 0)
                    if retention_seconds > 0:
                        retention_days = retention_seconds / 86400  # Convert to days
                        retention_str = f"{retention_days:.1f} days"
                    else:
                        retention_str = "infinite"
                else:
                    retention_str = "infinite"

                bucket_info.append({
                    'id': bucket['id'],
                    'name': bucket['name'],
                    'org_id': bucket['orgID'],
                    'retention': retention_str,
                    'retention_seconds': retention_rules[0].get('everySeconds', 0) if retention_rules else 0,
                    'created_at': bucket.get('createdAt', ''),
                    'updated_at': bucket.get('updatedAt', '')
                })

            return bucket_info
        except Exception as e:
            logger.error(f"Failed to list buckets: {e}")
            return None

    def update_bucket_retention(self, bucket_name: str, retention_days: int) -> bool:
        """Update bucket retention policy.

        Args:
            bucket_name: Name of the bucket to update
            retention_days: Retention period in days (1-3650)

        Returns:
            bool: True if successful, False otherwise
        """
        # Input validation
        if not isinstance(bucket_name, str) or not bucket_name.strip():
            logger.error("Bucket name must be a non-empty string")
            return False

        if not isinstance(retention_days, int) or retention_days < 1 or retention_days > 3650:
            logger.error("Retention days must be an integer between 1 and 3650 (10 years)")
            return False

        try:
            retention_seconds = retention_days * 86400  # Convert days to seconds

            # First get the bucket ID
            buckets = self.list_buckets()
            if not buckets:
                logger.error("Could not retrieve bucket list")
                return False

            bucket_id = None
            for bucket in buckets:
                try:
                    if bucket.get('name') == bucket_name:
                        bucket_id = bucket.get('id')
                        break
                except (TypeError, AttributeError) as e:
                    logger.warning(f"Malformed bucket entry in list: {e}")
                    continue

            if not bucket_id:
                available_buckets = [b.get('name', 'unknown') for b in buckets if isinstance(b, dict)]
                logger.error(f"Bucket '{bucket_name}' not found. Available buckets: {available_buckets}")
                return False

            # Update the retention policy
            retention_hours = retention_days * 24
            command = [
                'bucket', 'update',
                '--id', bucket_id,
                '--retention', f'{retention_hours}h'
            ]

            output = self._run_influx_command(command)
            if output is not None:
                logger.info(f"Successfully updated retention for bucket '{bucket_name}' to {retention_days} days")
                return True
            else:
                logger.error(f"Failed to update retention for bucket '{bucket_name}'")
                return False

        except Exception as e:
            logger.error(f"Error updating bucket retention: {e}")
            return False

    def estimate_data_size(self, bucket_name: str, days: int = 7) -> Optional[Dict[str, Any]]:
        """Estimate data size and growth rate for a bucket.

        Args:
            bucket_name: Name of the bucket to analyze
            days: Number of days to analyze for growth rate

        Returns:
            Dict with size estimates or None if error
        """
        try:
            # Use InfluxDB cardinality query to estimate data size
            # This is a rough estimation based on series cardinality
            query = f'''
            import "influxdata/influxdb/schema"

            schema.measurements(bucket: "{bucket_name}")
            '''

            # For now, return a placeholder - full implementation would require more complex queries
            logger.info(f"Data size estimation for bucket '{bucket_name}' requires manual analysis")
            logger.info("Use 'influx query' with cardinality queries or check disk usage directly")

            return {
                'bucket': bucket_name,
                'status': 'estimation_not_implemented',
                'recommendation': 'Check /var/lib/influxdb disk usage manually'
            }

        except Exception as e:
            logger.error(f"Error estimating data size: {e}")
            return None

    def get_disk_usage_recommendations(self, buckets: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on bucket configurations."""
        recommendations = []

        for bucket in buckets:
            if bucket['retention_seconds'] == 0:  # Infinite retention
                if bucket['name'] not in ['_monitoring', '_tasks']:  # System buckets
                    recommendations.append(
                        f"⚠️  Bucket '{bucket['name']}' has infinite retention - consider setting 30-90 days"
                    )
            elif bucket['retention_seconds'] > 7776000:  # More than 90 days
                recommendations.append(
                    f"📊 Bucket '{bucket['name']}' retains data for {bucket['retention'][:5]} - "
                    f"consider reducing if disk space is limited"
                )

        if not recommendations:
            recommendations.append("✅ All buckets have reasonable retention policies")

        return recommendations

    def create_emergency_cleanup_script(self, output_path: str = "emergency_cleanup.sh") -> bool:
        """Create an emergency cleanup script for disk full situations."""
        try:
            script_content = f'''#!/bin/bash
# Emergency InfluxDB Cleanup Script
# Generated on {datetime.utcnow().isoformat()}

echo "=== InfluxDB Emergency Cleanup ==="
echo "This script will help free up disk space for InfluxDB"
echo

# Check current disk usage
echo "Current disk usage:"
df -h /var/lib/influxdb 2>/dev/null || df -h /

echo
echo "InfluxDB directory usage:"
sudo du -sh /var/lib/influxdb/* 2>/dev/null | sort -h

echo
echo "WAL directory usage (potential cleanup target):"
sudo du -sh /var/lib/influxdb/engine/wal/* 2>/dev/null | sort -h | tail -10

echo
echo "=== EMERGENCY ACTIONS ==="
echo "1. Stop InfluxDB service:"
echo "   sudo systemctl stop influxdb"
echo
echo "2. Archive old WAL files (if absolutely necessary):"
echo "   sudo mkdir -p /tmp/influx_wal_backup"
echo "   sudo mv /var/lib/influxdb/engine/wal/_[0-9]* /tmp/influx_wal_backup/ 2>/dev/null || true"
echo
echo "3. Restart InfluxDB:"
echo "   sudo systemctl start influxdb"
echo
echo "4. Update bucket retention policies:"

# Add bucket update commands for each infinite retention bucket
influx bucket list --json 2>/dev/null | jq -r '.[] | select(.retentionRules[0].everySeconds == 0 or (.retentionRules | length == 0)) | .name' | while read bucket_name; do
    if [[ "$bucket_name" != "_monitoring" && "$bucket_name" != "_tasks" ]]; then
        echo "   influx bucket update --name $bucket_name --retention 720h  # 30 days"
    fi
done

echo
echo "5. Monitor status:"
echo "   influx ping"
echo "   df -h /var/lib/influxdb"
echo
echo "WARNING: Only run steps 1-3 if InfluxDB is completely unresponsive due to disk full"
'''

            with open(output_path, 'w') as f:
                f.write(script_content)

            os.chmod(output_path, 0o755)
            logger.info(f"Emergency cleanup script created: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create emergency cleanup script: {e}")
            return False

def main():
    """Main function for CLI usage."""
    parser = argparse.ArgumentParser(
        description='Manage InfluxDB bucket retention policies'
    )
    parser.add_argument(
        '--host',
        default='localhost:8086',
        help='InfluxDB host:port (default: localhost:8086)'
    )
    parser.add_argument(
        '--org',
        help='InfluxDB organization (default: from INFLUXDB_ORG env)'
    )
    parser.add_argument(
        '--token',
        help='InfluxDB token (default: from INFLUXDB_TOKEN env)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # List command
    list_parser = subparsers.add_parser('list', help='List all buckets and their retention')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update bucket retention')
    update_parser.add_argument('bucket_name', help='Name of the bucket to update')
    update_parser.add_argument('retention_days', type=int, help='Retention period in days')

    # Recommend command
    recommend_parser = subparsers.add_parser('recommend', help='Get retention recommendations')

    # Emergency command
    emergency_parser = subparsers.add_parser('emergency', help='Create emergency cleanup script')
    emergency_parser.add_argument(
        '--output',
        default='emergency_cleanup.sh',
        help='Output file for emergency script'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize manager
    manager = InfluxDBRetentionManager(
        influx_host=args.host,
        org=args.org,
        token=args.token
    )

    if args.command == 'list':
        buckets = manager.list_buckets()
        if buckets:
            print("\\n=== InfluxDB Buckets ===")
            df = pd.DataFrame(buckets)
            print(df[['name', 'retention', 'created_at']].to_string(index=False))
        else:
            print("Failed to list buckets")
            return 1

    elif args.command == 'update':
        success = manager.update_bucket_retention(args.bucket_name, args.retention_days)
        if not success:
            return 1

    elif args.command == 'recommend':
        buckets = manager.list_buckets()
        if buckets:
            recommendations = manager.get_disk_usage_recommendations(buckets)
            print("\\n=== Retention Policy Recommendations ===")
            for rec in recommendations:
                print(rec)
        else:
            print("Failed to get bucket information")
            return 1

    elif args.command == 'emergency':
        success = manager.create_emergency_cleanup_script(args.output)
        if not success:
            return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())