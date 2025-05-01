import logging
import time
from typing import Dict, Any, Optional, List
from .bybit import BybitExchange, BybitExchangeError

logger = logging.getLogger(__name__)

class BybitDemoExchange(BybitExchange):
    """Bybit Demo Exchange implementation for testing strategies"""
    
    def __init__(self, config: Dict[str, Any], error_handler: Optional[Any] = None):
        """Initialize Bybit Demo exchange."""
        super().__init__(config, error_handler)
        
        # Override endpoints for demo mode
        self.rest_endpoint = "https://api-demo.bybit.com"
        self.ws_endpoint = "wss://stream-demo.bybit.com/v5/public"
        self.api_url = self.rest_endpoint
        
        # Set demo flag
        self.is_demo = True
        
        logger.info(f"Initialized Bybit Demo Exchange with endpoint: {self.rest_endpoint}")
    
    async def initialize(self) -> bool:
        """Initialize the exchange connection with demo-specific setup."""
        success = await super().initialize()
        if success:
            # Request demo funds if needed
            await self._apply_for_demo_funds()
        return success
    
    async def _apply_for_demo_funds(self) -> None:
        """Request demo trading funds if balance is low."""
        try:
            # Check current balance first
            balance = await self.fetch_balance()
            usdt_balance = balance.get('total', {}).get('USDT', 0)
            
            # Only request funds if balance is low
            if usdt_balance < 1000:
                logger.info(f"Current USDT balance is low ({usdt_balance}), requesting demo funds...")
                
                # Request USDT demo funds
                request_data = {
                    "adjustType": 0,
                    "utaDemoApplyMoney": [
                        {
                            "coin": "USDT",
                            "amountStr": "100000"
                        }
                    ]
                }
                
                response = await self._make_request('POST', '/v5/account/demo-apply-money', request_data)
                
                if response.get('retCode') == 0:
                    logger.info("Successfully applied for demo trading funds")
                else:
                    logger.warning(f"Failed to apply for demo funds: {response.get('retMsg')}")
            else:
                logger.info(f"Current USDT balance is sufficient: {usdt_balance}")
                
        except Exception as e:
            logger.error(f"Error applying for demo funds: {str(e)}")
            
    async def _get_ws_url(self) -> str:
        """Override to return demo websocket URL."""
        return "wss://stream-demo.bybit.com/v5/public" 