"""
News API Routes for Virtuoso Dashboard.

Provides endpoints for fetching crypto news from Twitter/X
for the dashboard news ticker.

Endpoints:
    GET /api/news/x - Get latest crypto news from Twitter
    GET /api/news/x/status - Get scraper status
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_scraper():
    """Lazy import to avoid startup issues if twscrape not installed."""
    try:
        from src.core.news.twitter_scraper import get_twitter_scraper
        return get_twitter_scraper()
    except ImportError as e:
        logger.error(f"Twitter scraper not available: {e}")
        return None


@router.get("/x", response_model=Dict[str, Any])
async def get_twitter_news(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of news items"),
    source: Optional[str] = Query(None, description="Filter by Twitter username"),
    force_refresh: bool = Query(False, description="Force refresh (bypass cache)")
) -> Dict[str, Any]:
    """
    Get latest crypto news from Twitter/X.

    Returns news items from curated crypto news accounts,
    sorted by date (newest first).

    The response is cached for 60 seconds by default.
    Use force_refresh=true to bypass the cache.
    """
    scraper = _get_scraper()

    if scraper is None:
        raise HTTPException(
            status_code=503,
            detail="Twitter news scraper not available. Check twscrape installation."
        )

    try:
        # Fetch news (uses cache unless force_refresh)
        items = await scraper.fetch_news(force=force_refresh)

        # Filter by source if specified
        if source:
            items = [item for item in items if item.source.lower() == source.lower()]

        # Apply limit
        items = items[:limit]

        # Convert to dicts
        news_data = [item.to_dict() for item in items]

        return {
            "success": True,
            "count": len(news_data),
            "news": news_data,
            "sources": scraper.accounts,
            "cached": not force_refresh and scraper._last_fetch > 0
        }

    except Exception as e:
        logger.error(f"Error fetching Twitter news: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch news: {str(e)}"
        )


@router.get("/x/status", response_model=Dict[str, Any])
async def get_twitter_scraper_status() -> Dict[str, Any]:
    """
    Get Twitter news scraper status and metrics.

    Returns information about:
    - Initialization status
    - Monitored accounts
    - Cache status
    - Fetch statistics
    - Error information
    """
    scraper = _get_scraper()

    if scraper is None:
        return {
            "success": False,
            "error": "Twitter news scraper not available",
            "status": {
                "initialized": False,
                "reason": "twscrape not installed or credentials not configured"
            }
        }

    return {
        "success": True,
        "status": scraper.get_status()
    }


@router.get("/x/accounts", response_model=Dict[str, Any])
async def get_monitored_accounts() -> Dict[str, Any]:
    """
    Get list of monitored Twitter accounts.

    Returns the curated list of crypto news accounts
    that are being scraped for the news ticker.
    """
    scraper = _get_scraper()

    if scraper is None:
        # Return default accounts even if scraper unavailable
        from src.core.news.twitter_scraper import TwitterNewsScraper
        return {
            "success": True,
            "accounts": TwitterNewsScraper.DEFAULT_ACCOUNTS,
            "note": "Default accounts (scraper not initialized)"
        }

    return {
        "success": True,
        "accounts": scraper.accounts,
        "count": len(scraper.accounts)
    }
