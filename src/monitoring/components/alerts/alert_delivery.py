"""
Alert Delivery Component - Handles Discord webhook communication
Part of the AlertManager refactoring to reduce complexity from 4,716 to ~600 lines
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
import aiohttp
import hashlib
import json

logger = logging.getLogger(__name__)


class AlertDelivery:
    """
    Handles Discord webhook delivery with retry logic and error handling.
    Simplified from the original complex Discord integration.
    """
    
    def __init__(self, webhook_url: str, config: Dict[str, Any]):
        """
        Initialize AlertDelivery component.
        
        Args:
            webhook_url: Discord webhook URL
            config: Configuration dictionary
        """
        self.webhook_url = webhook_url
        self.max_retries = config.get('max_retries', 3)
        self.timeout = config.get('timeout', 30)
        self.base_delay = config.get('base_delay', 1.0)
        self.max_delay = config.get('max_delay', 60.0)
        
        # Session for reuse
        self._session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_session()
        
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
            
    async def _close_session(self):
        """Close aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
            
    async def send_webhook(self, 
                          content: str, 
                          embeds: Optional[List[Dict]] = None,
                          username: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Send Discord webhook with retry logic.
        
        Args:
            content: Message content
            embeds: Optional Discord embeds (simplified)
            username: Optional username override
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self.webhook_url:
            logger.warning("No webhook URL configured")
            return False, "No webhook URL configured"
            
        payload = self._build_payload(content, embeds, username)
        
        try:
            await self._ensure_session()
            success, error = await self._retry_with_backoff(self._execute_webhook, payload)
            return success, error
        except Exception as e:
            logger.error(f"Webhook delivery failed: {e}")
            return False, str(e)
            
    def _build_payload(self, 
                      content: str, 
                      embeds: Optional[List[Dict]] = None, 
                      username: Optional[str] = None) -> Dict:
        """
        Build Discord webhook payload.
        
        Args:
            content: Message content
            embeds: Optional embeds
            username: Optional username
            
        Returns:
            Webhook payload dictionary
        """
        payload = {
            'content': content[:2000],  # Discord content limit
        }
        
        if username:
            payload['username'] = username[:80]  # Discord username limit
            
        if embeds:
            # Simplified embed handling - take first embed only
            payload['embeds'] = embeds[:1]  # Discord allows up to 10, we limit to 1
            
        return payload
        
    async def _execute_webhook(self, payload: Dict) -> Tuple[bool, Optional[str]]:
        """
        Execute single webhook request.
        
        Args:
            payload: Webhook payload
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            async with self._session.post(self.webhook_url, json=payload) as response:
                if response.status == 200:
                    logger.debug("Webhook sent successfully")
                    return True, None
                elif response.status == 429:
                    # Rate limited
                    retry_after = response.headers.get('retry-after', '5')
                    error_msg = f"Rate limited, retry after {retry_after}s"
                    logger.warning(error_msg)
                    return False, error_msg
                else:
                    error_msg = f"Webhook failed with status {response.status}"
                    logger.error(error_msg)
                    return False, error_msg
                    
        except asyncio.TimeoutError:
            error_msg = "Webhook request timed out"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Webhook request failed: {e}"
            logger.error(error_msg)
            return False, error_msg
            
    async def _retry_with_backoff(self, func, *args, **kwargs) -> Tuple[bool, Optional[str]]:
        """
        Execute function with exponential backoff retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Tuple of (success, error_message)
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                success, error = await func(*args, **kwargs)
                
                if success:
                    if attempt > 0:
                        logger.info(f"Webhook succeeded on attempt {attempt + 1}")
                    return True, None
                    
                last_error = error
                
                # Don't retry on certain errors
                if error and "No webhook URL" in error:
                    break
                    
                # Calculate delay for next attempt
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.warning(f"Webhook attempt {attempt + 1} failed: {error}. Retrying in {delay}s")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.error(f"Webhook attempt {attempt + 1} error: {e}. Retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Webhook failed after {self.max_retries + 1} attempts: {e}")
                    
        return False, last_error or "Max retries exceeded"
        
    def create_simple_embed(self, 
                           title: str, 
                           description: str, 
                           color: int = 0x00ff00) -> Dict:
        """
        Create a simple Discord embed.
        
        Args:
            title: Embed title
            description: Embed description  
            color: Embed color (default green)
            
        Returns:
            Discord embed dictionary
        """
        return {
            'title': title[:256],  # Discord title limit
            'description': description[:4096],  # Discord description limit
            'color': color,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
        }
        
    async def send_simple_alert(self, 
                               level: str, 
                               message: str, 
                               details: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Send a simple alert with basic formatting.
        
        Args:
            level: Alert level (info, warning, error, critical)
            message: Alert message
            details: Optional additional details
            
        Returns:
            Tuple of (success, error_message)
        """
        # Color mapping for different levels
        colors = {
            'info': 0x0099ff,      # Blue
            'warning': 0xff9900,   # Orange  
            'error': 0xff0000,     # Red
            'critical': 0x8b0000,  # Dark red
        }
        
        color = colors.get(level.lower(), 0x808080)  # Default gray
        
        # Create simple embed
        embed = self.create_simple_embed(
            title=f"{level.upper()} Alert",
            description=message,
            color=color
        )
        
        # Add details if provided
        if details:
            embed['fields'] = [{
                'name': 'Details',
                'value': details[:1024],  # Discord field value limit
                'inline': False
            }]
            
        return await self.send_webhook(
            content=f"🚨 **{level.upper()}**: {message[:100]}...",
            embeds=[embed]
        )