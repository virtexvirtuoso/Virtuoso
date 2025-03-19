# Database API Documentation

## Overview

The `DatabaseClient` provides a high-performance, fault-tolerant interface to InfluxDB for time-series data storage and retrieval. It features connection pooling, automatic retries, batch operations, and caching.

## Configuration

### DatabaseConfig

```python
@dataclass
class DatabaseConfig:
    url: str                # InfluxDB server URL
    token: str             # Authentication token
    org: str              # Organization name
    bucket: str           # Bucket name
    max_retries: int = 3  # Maximum connection retry attempts
    retry_delay: float = 1.0  # Delay between retries (seconds)
    batch_size: int = 1000    # Maximum points per batch
    batch_timeout: float = 10.0  # Maximum batch write timeout
```

Configuration can be loaded from environment variables:
```bash
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_token
INFLUXDB_ORG=your_org
INFLUXDB_BUCKET=your_bucket
```

## Core Operations

### Market Data Operations

```python
# Store market data
await client.store_market_data(
    symbol="BTC-USD",
    data={
        'price': 50000.0,
        'volume': 1.5,
        'timestamp': datetime.utcnow().timestamp()
    }
)

# Store trading signal
await client.store_signal(
    symbol="BTC-USD",
    signal_data={
        'type': 'buy',
        'value': 1.0,
        'confidence': 0.95
    }
)
```

### DataFrame Operations

```python
# Write DataFrame
df = pd.DataFrame({
    'price': [100.0, 101.0],
    'volume': [1.0, 2.0]
}, index=[datetime.utcnow(), datetime.utcnow() + timedelta(minutes=1)])

await client.write_dataframe(df, 'market_data')

# Write DataFrame in batches (more efficient for large datasets)
await client.write_dataframe_batch(df, 'market_data')
```

### Batch Operations

```python
# Write multiple points in batches
points = [
    Point("measurement")
        .field("value", i)
        .time(datetime.utcnow())
    for i in range(1000)
]
await client.write_batch(points)

# Using batch context manager
async with client.batch_context() as batch:
    for i in range(1000):
        point = Point("measurement").field("value", i)
        batch.write(point)
```

### Query Operations

```python
# Query data
query = '''
from(bucket: "market_data")
    |> range(start: -1h)
    |> filter(fn: (r) => r["_measurement"] == "market_data")
'''
result = await client.query_data(query)

# Get imbalance history (with caching)
result = await client.get_imbalance_history(
    symbol="BTC-USD",
    start_time=datetime.utcnow() - timedelta(hours=1),
    end_time=datetime.utcnow()
)
```

### Health and Monitoring

```python
# Check database health
is_healthy = await client.is_healthy()

# Get database statistics
stats = await client.get_database_stats()
print(f"Points in last hour: {stats['metrics']['points_last_hour']}")
```

## Error Handling

The client includes comprehensive error handling:
- Connection errors are automatically retried
- Failed operations return None instead of raising exceptions
- All errors are logged with stack traces
- Health checks before operations

Example:
```python
# Operations handle errors gracefully
result = await client.query_data("invalid query")
if result is None:
    print("Query failed")
```

## Performance Features

1. Connection Management
   - Connection pooling
   - Automatic reconnection
   - Health checks

2. Batch Operations
   - Configurable batch sizes
   - Automatic batching of large datasets
   - Batch context manager

3. Caching
   - TTL-based caching
   - Cache invalidation
   - Memory-efficient cache storage

4. Performance Monitoring
   - Execution time tracking
   - Operation statistics
   - Resource usage metrics 