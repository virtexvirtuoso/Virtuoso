"""Market data repository module."""

class MarketRepository:
    """Repository for market data storage and retrieval."""
    
    def __init__(self, database_client=None):
        self.database_client = database_client

    async def store_market_data(self, data, symbol):
        """Store market data."""
        if self.database_client:
            await self.database_client.store_market_data(data, symbol) 