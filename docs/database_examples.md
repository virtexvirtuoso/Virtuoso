# Database Usage Examples

## Basic Setup

```python
from src.data_storage.database import DatabaseClient
import asyncio
import os
from datetime import datetime, timedelta

# Setup from environment variables
async def setup_database():
    config = {
        'influxDB': {
            'url': os.getenv('INFLUXDB_URL', 'http://localhost:8086'),
            'token': os.getenv('INFLUXDB_TOKEN'),
            'org': os.getenv('INFLUXDB_ORG', 'default'),
            'bucket': os.getenv('INFLUXDB_BUCKET', 'market_data')
        }
    }
    return DatabaseClient(config)
```

## Example 1: Real-time Market Data Storage

```python
async def store_market_updates(client, symbol: str):
    """Store real-time market updates."""
    try:
        while True:
            # Simulate market data updates
            data = {
                'price': 50000.0,
                'volume': 1.5,
                'timestamp': datetime.utcnow().timestamp()
            }
            
            await client.store_market_data(symbol, data)
            await asyncio.sleep(1)  # Wait for next update
            
    except KeyboardInterrupt:
        print("Stopping market data collection")

# Usage
async def main():
    client = await setup_database()
    try:
        await store_market_updates(client, "BTC-USD")
    finally:
        await client.close()

asyncio.run(main())
```

## Example 2: Batch Processing Historical Data

```python
import pandas as pd

async def process_historical_data(client, symbol: str, data_file: str):
    """Process and store historical data in batches."""
    # Load historical data
    df = pd.read_csv(data_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # Store in batches
    await client.write_dataframe_batch(df, 'historical_data')
    print(f"Processed {len(df)} records for {symbol}")

# Usage
async def import_history():
    client = await setup_database()
    try:
        await process_historical_data(client, "BTC-USD", "history.csv")
    finally:
        await client.close()
```

## Example 3: Market Analysis with Caching

```python
async def analyze_market(client, symbol: str):
    """Perform market analysis with cached data."""
    # Get recent market data
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    
    # This query will be cached
    imbalance_data = await client.get_imbalance_history(
        symbol,
        start_time=start_time,
        end_time=end_time
    )
    
    if imbalance_data is not None:
        # Perform analysis
        print(f"Analyzing {len(imbalance_data)} points for {symbol}")
        # ... analysis code ...

# Usage
async def run_analysis():
    client = await setup_database()
    try:
        await analyze_market(client, "BTC-USD")
    finally:
        await client.close()
```

## Example 4: System Monitoring

```python
async def monitor_system(client):
    """Monitor database system health and performance."""
    while True:
        # Check health
        is_healthy = await client.is_healthy()
        if not is_healthy:
            print("Database health check failed!")
            continue
            
        # Get statistics
        stats = await client.get_database_stats()
        print(f"System Statistics:")
        print(f"- Points in last hour: {stats['metrics'].get('points_last_hour', 0)}")
        print(f"- Health status: {stats['health']}")
        
        await asyncio.sleep(60)  # Check every minute

# Usage
async def run_monitoring():
    client = await setup_database()
    try:
        await monitor_system(client)
    finally:
        await client.close()
```

## Example 5: Error Handling and Retries

```python
async def robust_data_storage(client, symbol: str, data: dict):
    """Demonstrate robust error handling."""
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            if not await client.is_healthy():
                print(f"Database unhealthy, retrying... ({attempt + 1}/{max_retries})")
                await asyncio.sleep(retry_delay)
                continue
                
            await client.store_market_data(symbol, data)
            print("Data stored successfully")
            break
            
        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                print("Max retries reached, giving up")

# Usage
async def store_with_retries():
    client = await setup_database()
    data = {
        'price': 50000.0,
        'volume': 1.5,
        'timestamp': datetime.utcnow().timestamp()
    }
    try:
        await robust_data_storage(client, "BTC-USD", data)
    finally:
        await client.close()
```

## Example 6: Batch Context Usage

```python
async def batch_write_example(client):
    """Demonstrate batch context manager usage."""
    points = []
    
    # Create sample points
    for i in range(1000):
        point = Point("measurements")\
            .tag("type", "example")\
            .field("value", i)\
            .time(datetime.utcnow())
        points.append(point)
    
    # Write using batch context
    async with client.batch_context() as batch:
        for point in points:
            batch.write(point)
    
    print(f"Wrote {len(points)} points in batch")

# Usage
async def run_batch_example():
    client = await setup_database()
    try:
        await batch_write_example(client)
    finally:
        await client.close()
``` 