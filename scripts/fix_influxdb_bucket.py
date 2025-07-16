#!/usr/bin/env python3
"""
InfluxDB Bucket Configuration Fix Script

This script helps diagnose and fix the InfluxDB bucket configuration issue
where the application is looking for 'virtuoso_trading' bucket but it may
be named differently or may not exist.
"""

import os
import sys
import requests
import json
from typing import Dict, Any, Optional

def check_environment_variables() -> Dict[str, str]:
    """Check InfluxDB environment variables."""
    env_vars = {
        'INFLUXDB_URL': os.getenv('INFLUXDB_URL', ''),
        'INFLUXDB_TOKEN': os.getenv('INFLUXDB_TOKEN', ''),
        'INFLUXDB_ORG': os.getenv('INFLUXDB_ORG', ''),
        'INFLUXDB_BUCKET': os.getenv('INFLUXDB_BUCKET', ''),
    }
    
    print("Current InfluxDB Environment Variables:")
    print("=" * 40)
    for key, value in env_vars.items():
        if value:
            # Mask the token for security
            display_value = value if key != 'INFLUXDB_TOKEN' else f"{value[:10]}...{value[-5:]}" if len(value) > 15 else "***"
            print(f"{key}: {display_value}")
        else:
            print(f"{key}: NOT SET")
    print()
    
    return env_vars

def list_buckets(url: str, token: str, org: str) -> Optional[Dict[str, Any]]:
    """List all buckets in the InfluxDB instance."""
    try:
        headers = {
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(f"{url}/api/v2/buckets", headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error listing buckets: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error connecting to InfluxDB: {str(e)}")
        return None

def create_bucket(url: str, token: str, org: str, bucket_name: str) -> bool:
    """Create a new bucket in InfluxDB."""
    try:
        headers = {
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'name': bucket_name,
            'orgID': org,
            'retentionRules': []
        }
        
        response = requests.post(f"{url}/api/v2/buckets", headers=headers, json=data, timeout=10)
        
        if response.status_code == 201:
            print(f"Successfully created bucket: {bucket_name}")
            return True
        else:
            print(f"Error creating bucket: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error creating bucket: {str(e)}")
        return False

def get_organization_id(url: str, token: str, org_name: str) -> Optional[str]:
    """Get organization ID by name."""
    try:
        headers = {
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(f"{url}/api/v2/orgs", headers=headers, timeout=10)
        
        if response.status_code == 200:
            orgs = response.json()
            for org in orgs.get('orgs', []):
                if org['name'] == org_name:
                    return org['id']
            print(f"Organization '{org_name}' not found")
            return None
        else:
            print(f"Error listing organizations: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting organization ID: {str(e)}")
        return None

def main():
    """Main function to diagnose and fix InfluxDB bucket issues."""
    print("InfluxDB Bucket Configuration Diagnostic Tool")
    print("=" * 50)
    
    # Check environment variables
    env_vars = check_environment_variables()
    
    # Check if required variables are set
    required_vars = ['INFLUXDB_URL', 'INFLUXDB_TOKEN', 'INFLUXDB_ORG']
    missing_vars = [var for var in required_vars if not env_vars[var]]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nTo fix this, set the missing environment variables:")
        for var in missing_vars:
            print(f"export {var}=your_value_here")
        print("\nOr run: source scripts/set_influxdb_env.sh")
        return 1
    
    url = env_vars['INFLUXDB_URL']
    token = env_vars['INFLUXDB_TOKEN']
    org = env_vars['INFLUXDB_ORG']
    bucket = env_vars['INFLUXDB_BUCKET'] or 'virtuoso_trading'
    
    print(f"✅ All required environment variables are set")
    print(f"Expected bucket name: {bucket}")
    print()
    
    # Test connection and list buckets
    print("Testing InfluxDB connection...")
    buckets_data = list_buckets(url, token, org)
    
    if buckets_data is None:
        print("❌ Failed to connect to InfluxDB")
        return 1
    
    print("✅ Successfully connected to InfluxDB")
    
    # List existing buckets
    buckets = buckets_data.get('buckets', [])
    print(f"\nFound {len(buckets)} buckets:")
    print("-" * 30)
    
    bucket_exists = False
    for bucket_info in buckets:
        bucket_name = bucket_info['name']
        print(f"  - {bucket_name}")
        if bucket_name == bucket:
            bucket_exists = True
    
    print()
    
    if bucket_exists:
        print(f"✅ Bucket '{bucket}' exists and is accessible")
        print("The configuration appears to be correct.")
        return 0
    else:
        print(f"❌ Bucket '{bucket}' not found")
        
        # Ask user if they want to create the bucket
        response = input(f"Would you like to create the bucket '{bucket}'? (y/n): ").lower().strip()
        
        if response in ['y', 'yes']:
            # Get organization ID
            org_id = get_organization_id(url, token, org)
            if org_id:
                if create_bucket(url, token, org_id, bucket):
                    print(f"✅ Bucket '{bucket}' created successfully")
                    return 0
                else:
                    print(f"❌ Failed to create bucket '{bucket}'")
                    return 1
            else:
                print(f"❌ Could not get organization ID for '{org}'")
                return 1
        else:
            print("\nOptions to fix this issue:")
            print("1. Create the bucket manually in InfluxDB UI")
            print("2. Update INFLUXDB_BUCKET environment variable to use an existing bucket")
            print("3. Run this script again and choose to create the bucket")
            
            if buckets:
                print(f"\nExisting buckets you could use:")
                for bucket_info in buckets:
                    print(f"  export INFLUXDB_BUCKET={bucket_info['name']}")
            
            return 1

if __name__ == "__main__":
    sys.exit(main()) 