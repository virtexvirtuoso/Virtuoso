# Database Performance Tuning Guide

## Overview

This guide covers performance optimization strategies for the DatabaseClient when working with InfluxDB. It includes configuration tuning, batch processing strategies, and monitoring recommendations.

## Configuration Optimization

### 1. Connection Settings

```python
config = {
    'influxDB': {
        'url': 'http://localhost:8086',
        'token': 'your_token',
        'org': 'your_org',
        'bucket': 'your_bucket',
        'max_retries': 3,
        'retry_delay': 1.0,
        'batch_size': 1000,
        'batch_timeout': 10.0
    }
}
```

#### Recommended Values:
- `batch_size`: 
  - Small writes (< 100KB): 100-500 points
  - Medium writes (100KB-1MB): 1000-5000 points
  - Large writes (>1MB): 5000-10000 points
- `batch_timeout`: 5-15 seconds
- `retry_delay`: 1-3 seconds
- `max_retries`: 3-5 attempts

## Batch Processing Strategies

### 1. DataFrame Batch Writing

For large DataFrames, use batch writing:

```python
# Inefficient for large datasets
await client.write_dataframe(large_df, 'measurement')

# Efficient batch processing
await client.write_dataframe_batch(large_df, 'measurement')
```

### 2. Point Batch Writing

For multiple points, use batch operations:

```python
# Inefficient point-by-point writing
for point in points:
    await client.write_api.write(bucket=bucket, record=point)

# Efficient batch writing
await client.write_batch(points)
```

### 3. Batch Context Manager

For manual control over batching:

```python
async with client.batch_context() as batch:
    for point in points:
        batch.write(point)
```

## Query Optimization

### 1. Caching Strategy

Configure caching for frequently accessed data:

```python
# Configure cache TTL based on data volatility
@cached(ttl=300)  # 5 minutes for volatile data
@cached(ttl=3600)  # 1 hour for stable data
```

### 2. Query Patterns

Optimize query patterns:

```python
# Inefficient: Too broad time range
query = '''
from(bucket: "market_data")
    |> range(start: -30d)
    |> filter(fn: (r) => r["symbol"] == "BTC-USD")
'''

# Efficient: Specific time range and fields
query = '''
from(bucket: "market_data")
    |> range(start: -24h)
    |> filter(fn: (r) => r["symbol"] == "BTC-USD")
    |> filter(fn: (r) => r["_field"] == "price" or r["_field"] == "volume")
'''
```

## Memory Management

### 1. DataFrame Optimization

```python
async def process_large_dataframe(client, df: pd.DataFrame):
    # Convert types before processing
    df = client._convert_df_types(df)
    
    # Process in chunks
    chunk_size = 10000
    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i + chunk_size]
        await client.write_dataframe_batch(chunk, 'measurement')
        
        # Optional: Force garbage collection
        import gc
        gc.collect()
```

### 2. Point Buffer Management

```python
async def manage_point_buffer(client, points: List[Point]):
    buffer_size = client.config.batch_size
    buffer = []
    
    for point in points:
        buffer.append(point)
        
        if len(buffer) >= buffer_size:
            await client.write_batch(buffer)
            buffer = []  # Clear buffer
    
    # Write remaining points
    if buffer:
        await client.write_batch(buffer)
```

## Performance Monitoring

### 1. System Metrics

Monitor system performance:

```python
async def monitor_performance(client):
    while True:
        stats = await client.get_database_stats()
        
        # Monitor write throughput
        points_written = stats['metrics'].get('points_last_hour', 0)
        writes_per_second = points_written / 3600
        
        # Monitor system health
        is_healthy = stats['health']
        
        print(f"Write throughput: {writes_per_second:.2f} points/second")
        print(f"System health: {is_healthy}")
        
        await asyncio.sleep(60)
```

### 2. Operation Timing

Monitor operation execution times:

```python
@measure_execution_time
async def performance_critical_operation(client):
    # Operation will be timed and logged
    result = await client.query_data("your_query")
    return result
```

## Performance Troubleshooting

### 1. Common Issues and Solutions

1. **Slow Write Performance**
   - Reduce batch size if too large
   - Increase batch size if too small
   - Check network latency
   - Verify disk I/O performance

2. **Memory Issues**
   - Implement chunking for large datasets
   - Monitor memory usage
   - Use batch processing
   - Clear unused caches

3. **Query Performance**
   - Optimize time ranges
   - Use specific field filters
   - Implement caching
   - Monitor query patterns

### 2. Monitoring Checklist

- [ ] Database health status
- [ ] Write throughput
- [ ] Query response times
- [ ] Memory usage
- [ ] Cache hit rates
- [ ] Error rates
- [ ] Connection pool usage

## Best Practices

1. **Write Operations**
   - Use batch operations for multiple points
   - Implement retry logic for failures
   - Monitor batch sizes and adjust
   - Use appropriate timestamp precision

2. **Query Operations**
   - Cache frequently accessed data
   - Use specific time ranges
   - Filter unnecessary fields
   - Monitor query patterns

3. **Resource Management**
   - Implement connection pooling
   - Close connections properly
   - Monitor memory usage
   - Use appropriate batch sizes

4. **Error Handling**
   - Implement circuit breakers
   - Use exponential backoff
   - Log errors appropriately
   - Monitor error rates 