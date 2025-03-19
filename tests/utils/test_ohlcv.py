#!/usr/bin/env python3
import asyncio
import logging
import sys
import yaml
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def load_config() -> dict:
    """Load configuration from YAML file."""
    try:
        # Try loading from config/config.yaml first
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            # Fallback to src/config/config.yaml
            config_path = Path("src/config/config.yaml")
            
        if not config_path.exists():
            raise FileNotFoundError("Config file not found in config/ or src/config/")
            
        logger.info(f"Loading config from {config_path}")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Validate required config sections
        required_sections = ['monitoring', 'exchanges', 'analysis']
        missing_sections = [s for s in required_sections if s not in config]
        if missing_sections:
            raise ValueError(f"Missing required config sections: {missing_sections}")
            
        return config
        
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        raise

async def test_ohlcv():
    try:
        from src.core.exchanges.bybit import BybitExchange
        
        # Load config
        config = load_config()
        
        # Initialize exchange
        exchange = await BybitExchange.get_instance(config)
        
        # Test different timeframes
        timeframes = ['1m', '5m', '30m', '4h']
        symbol = 'BTCUSDT'
        
        for timeframe in timeframes:
            print(f"\nTesting {timeframe} timeframe...")
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, 10)
            print(f'OHLCV data length: {len(ohlcv)}')
            if ohlcv:
                print(f'First 2 candles: {ohlcv[:2]}')
            else:
                print('No data returned')
        
        # Close exchange connection
        await exchange.close()
        
        return True
    except Exception as e:
        print(f"Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ohlcv())
    sys.exit(0 if success else 1) 