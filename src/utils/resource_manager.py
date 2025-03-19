import asyncio
import logging

logger = logging.getLogger(__name__)

class ResourceManager:
    """Manage system resources such as client sessions."""
    
    @staticmethod
    async def close_client_sessions() -> None:
        """Close any remaining client sessions."""
        try:
            for task in asyncio.all_tasks():
                if 'client_session' in str(task):
                    task.cancel()
            logger.info("Closed all client sessions")
        except Exception as e:
            logger.error(f"Error closing client sessions: {str(e)}") 