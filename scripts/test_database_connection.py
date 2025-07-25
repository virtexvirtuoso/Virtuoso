#!/usr/bin/env python3
"""Test database connection to identify issues."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data_storage.database import DatabaseClient
from src.config.manager import ConfigManager
from dotenv import load_dotenv

async def test_database_connection():
    """Test database connection and report status."""
    print("🔍 Testing Database Connection...")
    
    # Load environment variables
    load_dotenv()
    
    # Print environment variables
    print(f"INFLUXDB_URL: {os.getenv('INFLUXDB_URL')}")
    print(f"INFLUXDB_TOKEN: {os.getenv('INFLUXDB_TOKEN')[:20]}...")
    print(f"INFLUXDB_ORG: {os.getenv('INFLUXDB_ORG')}")
    print(f"INFLUXDB_BUCKET: {os.getenv('INFLUXDB_BUCKET')}")
    
    # Load config
    config_manager = ConfigManager()
    config_manager.load_config()
    
    # Test database client
    try:
        db_client = DatabaseClient(config_manager.config)
        print(f"✅ Database client created successfully")
        
        # Test health check
        is_healthy = await db_client.is_healthy()
        print(f"Database health check: {'✅ HEALTHY' if is_healthy else '❌ UNHEALTHY'}")
        
        if not is_healthy:
            print("❌ Database connection failed")
            return False
            
        # Test simple operations
        try:
            stats = await db_client.get_database_stats()
            print(f"✅ Database stats retrieved: {stats}")
        except Exception as e:
            print(f"⚠️ Error getting database stats: {e}")
            
        print("✅ Database connection test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            await db_client.close()
        except:
            pass

if __name__ == "__main__":
    result = asyncio.run(test_database_connection())
    sys.exit(0 if result else 1) 