import pytest
from datetime import datetime, timedelta, timezone
import pandas as pd
from src.data_storage.database import DatabaseClient, DatabaseConfig
from unittest.mock import Mock, patch, call
import os
from influxdb_client import Point

@pytest.fixture
def db_config():
    return {
        'influxDB': {
            'url': 'http://localhost:8086',
            'token': 'test_token',
            'org': 'test_org',
            'bucket': 'test_bucket',
            'max_retries': 3,
            'retry_delay': 0.1  # Short delay for tests
        }
    }

@pytest.fixture
def mock_influxdb():
    with patch('influxdb_client.InfluxDBClient') as mock_client:
        # Setup mock client
        mock_client.return_value.ping.return_value = True
        mock_client.return_value.write_api.return_value = Mock()
        mock_client.return_value.query_api.return_value = Mock()
        yield mock_client

@pytest.fixture
def db_client(db_config, mock_influxdb):
    return DatabaseClient(db_config)

def test_database_config_creation(db_config):
    """Test database configuration creation from dictionary."""
    config = DatabaseConfig.from_dict(db_config)
    assert config.url == 'http://localhost:8086'
    assert config.token == 'test_token'
    assert config.org == 'test_org'
    assert config.bucket == 'test_bucket'
    assert config.max_retries == 3
    assert config.retry_delay == 0.1

def test_database_config_from_env():
    """Test database configuration from environment variables."""
    os.environ['INFLUXDB_URL'] = 'http://test:8086'
    os.environ['INFLUXDB_TOKEN'] = 'env_token'
    os.environ['INFLUXDB_ORG'] = 'env_org'
    os.environ['INFLUXDB_BUCKET'] = 'env_bucket'
    
    config = DatabaseConfig.from_dict({})
    assert config.url == 'http://test:8086'
    assert config.token == 'env_token'
    assert config.org == 'env_org'
    assert config.bucket == 'env_bucket'
    assert config.max_retries == 3  # Default value
    assert config.retry_delay == 1.0  # Default value

def test_database_client_initialization_with_retries(db_config):
    """Test database client initialization with connection retries."""
    with patch('influxdb_client.InfluxDBClient') as mock_client:
        # Make the first two connection attempts fail
        mock_client.return_value.ping.side_effect = [
            Exception("Connection failed"),
            Exception("Connection failed"),
            True  # Third attempt succeeds
        ]
        
        client = DatabaseClient(db_config)
        assert client.client is not None
        assert client._retry_count == 2
        assert mock_client.return_value.ping.call_count == 3

@pytest.mark.asyncio
async def test_ensure_connection(db_client):
    """Test connection health check and reconnection."""
    # Make health check fail once
    db_client.client.ping.side_effect = [False, True]
    
    assert await db_client._ensure_connection()
    assert db_client.client.ping.call_count == 2

@pytest.mark.asyncio
async def test_store_market_data_with_connection_check(db_client):
    """Test storing market data with connection validation."""
    data = {
        'price': 100.0,
        'volume': 1.0,
        'timestamp': datetime.now(timezone.utc).timestamp()
    }
    
    # Test successful connection
    db_client.client.ping.return_value = True
    await db_client.store_market_data('BTC-USD', data)
    db_client.write_api.write.assert_called_once()
    
    # Test failed connection
    db_client.client.ping.return_value = False
    db_client.write_api.write.reset_mock()
    await db_client.store_market_data('BTC-USD', data)
    db_client.write_api.write.assert_not_called()

@pytest.mark.asyncio
async def test_store_signal_with_error_handling(db_client):
    """Test storing trading signal with error handling."""
    signal_data = {
        'type': 'buy',
        'value': 1.0,
        'confidence': 0.95
    }
    
    # Test successful case
    db_client.client.ping.return_value = True
    await db_client.store_signal('BTC-USD', signal_data)
    db_client.write_api.write.assert_called_once()
    
    # Test error case
    db_client.write_api.write.side_effect = Exception("Write failed")
    result = await db_client.store_signal('BTC-USD', signal_data)
    assert result is None

@pytest.mark.asyncio
async def test_write_dataframe_with_validation(db_client):
    """Test writing DataFrame with data validation."""
    df = pd.DataFrame({
        'price': [100.0, 101.0, float('nan')],  # Include NaN value
        'volume': [1.0, 2.0, 3.0]
    }, index=[datetime.now(timezone.utc) + timedelta(minutes=i) for i in range(3)])
    
    await db_client.write_dataframe(df, 'test_measurement')
    # Should only write non-NaN values
    assert db_client.write_api.write.call_count == 3

@pytest.mark.asyncio
async def test_get_imbalance_history_with_caching(db_client):
    """Test getting imbalance history with caching and error handling."""
    mock_df = pd.DataFrame({'value': [1.0]})
    db_client.query_api.query_data_frame.return_value = mock_df
    
    # First call should query database
    result1 = await db_client.get_imbalance_history('BTC-USD')
    assert result1.equals(mock_df)
    db_client.query_api.query_data_frame.assert_called_once()
    
    # Second call should use cache
    result2 = await db_client.get_imbalance_history('BTC-USD')
    assert result2.equals(mock_df)
    assert db_client.query_api.query_data_frame.call_count == 1
    
    # Test error handling
    db_client.query_api.query_data_frame.side_effect = Exception("Query failed")
    result3 = await db_client.get_imbalance_history('BTC-USD')
    assert result3 is None

@pytest.mark.asyncio
async def test_is_healthy_comprehensive(db_client):
    """Test health check with various scenarios."""
    # Test all components healthy
    db_client.client.ping.return_value = True
    assert await db_client.is_healthy() is True
    
    # Test missing write API
    db_client.write_api = None
    assert await db_client.is_healthy() is False
    
    # Test ping failure
    db_client.write_api = Mock()
    db_client.client.ping.side_effect = Exception("Connection failed")
    assert await db_client.is_healthy() is False

@pytest.mark.asyncio
async def test_close_with_error_handling(db_client):
    """Test closing connections with error handling."""
    # Test normal closure
    await db_client.close()
    db_client.write_api.close.assert_called_once()
    db_client.client.close.assert_called_once()
    
    # Test error handling
    db_client.write_api.close.side_effect = Exception("Close failed")
    await db_client.close()  # Should not raise exception 

@pytest.mark.asyncio
async def test_write_batch(db_client):
    """Test batch writing of points."""
    # Create test points
    points = [
        Point("test_measurement").field("value", i).time(datetime.now(timezone.utc))
        for i in range(5)
    ]
    
    # Test successful batch write
    db_client.client.ping.return_value = True
    await db_client.write_batch(points)
    db_client.write_api.write.assert_called_once()
    
    # Verify batch size
    args = db_client.write_api.write.call_args[1]
    assert len(args['record']) == 5

@pytest.mark.asyncio
async def test_write_dataframe_batch(db_client):
    """Test batch writing of DataFrame."""
    # Create test DataFrame
    df = pd.DataFrame({
        'value': range(1500),  # More than batch_size to test batching
        'timestamp': [datetime.now(timezone.utc) + timedelta(minutes=i) for i in range(1500)]
    }).set_index('timestamp')
    
    # Test successful batch write
    db_client.client.ping.return_value = True
    await db_client.write_dataframe_batch(df, 'test_measurement')
    
    # Should have written 2 batches (1000 + 500)
    assert db_client.write_api.write.call_count == 2

@pytest.mark.asyncio
async def test_batch_context(db_client):
    """Test batch context manager."""
    points = [
        Point("test_measurement").field("value", i).time(datetime.now(timezone.utc))
        for i in range(3)
    ]
    
    with db_client.batch_context() as batch:
        for point in points:
            batch.write(point)
    
    # Verify batch was closed
    batch.close.assert_called_once()

@pytest.mark.asyncio
async def test_get_database_stats(db_client):
    """Test database statistics retrieval."""
    # Mock healthy database with some data
    db_client.client.ping.return_value = True
    mock_df = pd.DataFrame({'_value': [1000]})
    db_client.query_api.query_data_frame.return_value = mock_df
    
    stats = await db_client.get_database_stats()
    assert stats['health'] is True
    assert stats['metrics']['points_last_hour'] == 1000
    
    # Test unhealthy database
    db_client.client.ping.return_value = False
    stats = await db_client.get_database_stats()
    assert stats['health'] is False

@pytest.mark.asyncio
async def test_performance_monitoring(db_client):
    """Test performance monitoring decorator."""
    # Create large DataFrame to test performance
    df = pd.DataFrame({
        'value': range(100),
        'timestamp': [datetime.now(timezone.utc) + timedelta(minutes=i) for i in range(100)]
    }).set_index('timestamp')
    
    # Test write operation with performance monitoring
    db_client.client.ping.return_value = True
    await db_client.write_dataframe_batch(df, 'test_measurement')
    
    # Performance metrics should have been logged (check debug logs)
    # This is a bit tricky to test directly since it goes to logs
    
@pytest.mark.asyncio
async def test_error_handling_in_batch_operations(db_client):
    """Test error handling in batch operations."""
    points = [
        Point("test_measurement").field("value", i).time(datetime.now(timezone.utc))
        for i in range(5)
    ]
    
    # Test connection failure
    db_client.client.ping.return_value = False
    result = await db_client.write_batch(points)
    assert result is None
    db_client.write_api.write.assert_not_called()
    
    # Test write failure
    db_client.client.ping.return_value = True
    db_client.write_api.write.side_effect = Exception("Write failed")
    result = await db_client.write_batch(points)
    assert result is None

@pytest.mark.asyncio
async def test_batch_size_configuration(db_client):
    """Test batch size configuration."""
    # Create DataFrame larger than batch size
    df = pd.DataFrame({
        'value': range(2500),  # More than 2 batches
        'timestamp': [datetime.now(timezone.utc) + timedelta(minutes=i) for i in range(2500)]
    }).set_index('timestamp')
    
    # Set smaller batch size
    db_client.config.batch_size = 1000
    db_client.client.ping.return_value = True
    
    await db_client.write_dataframe_batch(df, 'test_measurement')
    
    # Should have written 3 batches (1000 + 1000 + 500)
    assert db_client.write_api.write.call_count == 3
    
    # Verify batch sizes
    calls = db_client.write_api.write.call_args_list
    assert len(calls[0][1]['record']) == 1000  # First batch
    assert len(calls[1][1]['record']) == 1000  # Second batch
    assert len(calls[2][1]['record']) == 500   # Last batch 