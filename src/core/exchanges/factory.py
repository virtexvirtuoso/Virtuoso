from typing import Dict, Optional
import logging
from .base import BaseExchange
from .bybit import BybitExchange
from .bybit_demo import BybitDemoExchange
from .coinbase import CoinbaseExchange
from .hyperliquid import HyperliquidExchange
from .ccxt_exchange import CCXTExchange

logger = logging.getLogger(__name__)

class ExchangeFactory:
    """Factory class for creating exchange instances"""
    
    EXCHANGE_MAP = {
        'bybit': BybitExchange,
        'bybit_demo': BybitDemoExchange,
        'coinbase': CoinbaseExchange,
        'hyperliquid': HyperliquidExchange,
        'ccxt': CCXTExchange
    }
    
    @classmethod
    async def create_exchange(cls, exchange_id: str, config: Dict) -> Optional[BaseExchange]:
        """Create and initialize an exchange instance
        
        Args:
            exchange_id: The identifier for the exchange
            config: Exchange configuration dictionary
            
        Returns:
            Initialized exchange instance or None if initialization fails
        """
        try:
            # Check if we're using demo mode
            if exchange_id == 'bybit' and config.get('demo_mode', False):
                exchange_id = 'bybit_demo'
                logger.info("Creating Bybit Demo exchange instance")
            
            # Check if we're using CCXT generic integration
            use_ccxt = config.get('use_ccxt', False)
            if use_ccxt and exchange_id != 'ccxt':
                # Store the original exchange_id for CCXT to use
                config['exchange_id'] = exchange_id
                exchange_id = 'ccxt'
                logger.info(f"Using CCXT for {config['exchange_id']} exchange integration")
            
            # Get exchange class
            exchange_class = cls.EXCHANGE_MAP.get(exchange_id)
            if not exchange_class:
                if use_ccxt:
                    logger.info(f"Exchange {exchange_id} not directly supported, using CCXT integration")
                    exchange_class = CCXTExchange
                    # Set the exchange_id for CCXT to use
                    config['exchange_id'] = exchange_id
                    exchange_id = 'ccxt'
                else:
                    logger.error(f"Unsupported exchange: {exchange_id}")
                    return None

            # Create exchange configuration with proper WebSocket endpoints
            exchange_config = {
                'exchanges': {
                    exchange_id: config
                }
            }
            
            # Ensure websocket configuration has mainnet_endpoint and testnet_endpoint
            if 'websocket' in config:
                if 'public' in config['websocket'] and 'mainnet_endpoint' not in config['websocket']:
                    config['websocket']['mainnet_endpoint'] = config['websocket']['public']
                
                if 'testnet_endpoint' not in config['websocket']:
                    config['websocket']['testnet_endpoint'] = config.get('testnet_endpoint', 'wss://stream-testnet.bybit.com/v5/public')
                
                # Add demo endpoint if needed
                if 'demo_endpoint' not in config['websocket'] and exchange_id == 'bybit_demo':
                    config['websocket']['demo_endpoint'] = 'wss://stream-demo.bybit.com/v5/public'
            
            # Create and initialize exchange instance
            logger.info(f"Creating {exchange_id} exchange instance...")
            exchange = exchange_class(exchange_config)
            
            # Initialize the exchange
            logger.info(f"Initializing {exchange_id} exchange...")
            if await exchange.initialize():
                logger.info(f"Successfully initialized {exchange_id} exchange")
                return exchange
            else:
                logger.error(f"Failed to initialize {exchange_id} exchange")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create exchange {exchange_id}: {str(e)}")
            logger.debug(f"Config used: {config}")
            return None 