"""
Twitter/X News Scraper Service for Virtuoso Dashboard News Ticker.

Uses twscrape library with cookie-based authentication to fetch
crypto news from curated accounts.

Environment Variables Required:
    X_AUTH_TOKEN: Twitter auth_token cookie value
    X_CT0: Twitter ct0 cookie value
"""

import asyncio
import os
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from collections import deque
import time

try:
    from twscrape import API
except ImportError:
    API = None

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """Represents a single news item from Twitter."""
    id: str
    source: str  # Twitter username
    text: str
    created_at: datetime
    likes: int = 0
    retweets: int = 0
    url: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "source": self.source,
            "text": self.text,
            "created_at": self.created_at.isoformat(),
            "timestamp": int(self.created_at.timestamp() * 1000),
            "likes": self.likes,
            "retweets": self.retweets,
            "url": self.url,
            "age_seconds": int((datetime.now(timezone.utc) - self.created_at).total_seconds())
        }


class TwitterNewsScraper:
    """
    Service for scraping crypto news from Twitter/X.

    Features:
    - Cookie-based authentication (more stable than login flow)
    - In-memory caching with TTL
    - Deduplication by tweet ID
    - Rate limit awareness
    - Background polling support
    """

    # Curated crypto news accounts
    DEFAULT_ACCOUNTS = [
        "tier10k",          # Breaking crypto news
        "whale_alert",      # Large transactions
        "DocumentingBTC",   # Bitcoin news
        "WatcherGuru",      # News aggregator
        "DeItaone",         # Fast macro/crypto news
        "unusual_whales",   # Options + crypto flow
        "zaboratz",         # Market structure
    ]

    def __init__(
        self,
        accounts: Optional[List[str]] = None,
        cache_ttl: int = 60,  # seconds
        max_tweets_per_account: int = 10,
        max_cached_items: int = 200
    ):
        """
        Initialize the Twitter news scraper.

        Args:
            accounts: List of Twitter usernames to monitor
            cache_ttl: How long to cache results (seconds)
            max_tweets_per_account: Max tweets to fetch per account per poll
            max_cached_items: Maximum items to keep in cache
        """
        if API is None:
            raise ImportError("twscrape not installed. Run: pip install twscrape")

        self.accounts = accounts or self.DEFAULT_ACCOUNTS
        self.cache_ttl = cache_ttl
        self.max_tweets_per_account = max_tweets_per_account
        self.max_cached_items = max_cached_items

        # State
        self._api: Optional[API] = None
        self._initialized = False
        self._cache: deque = deque(maxlen=max_cached_items)
        self._seen_ids: Set[str] = set()
        self._last_fetch: float = 0
        self._fetch_lock = asyncio.Lock()

        # Metrics
        self._fetch_count = 0
        self._error_count = 0
        self._last_error: Optional[str] = None

    async def initialize(self) -> bool:
        """
        Initialize the API with cookie authentication.

        Returns:
            True if initialization succeeded
        """
        if self._initialized:
            return True

        auth_token = os.getenv("X_AUTH_TOKEN")
        ct0 = os.getenv("X_CT0")

        if not auth_token or not ct0:
            logger.error(
                "Twitter credentials not configured. "
                "Set X_AUTH_TOKEN and X_CT0 environment variables."
            )
            return False

        try:
            self._api = API()
            cookies = f"auth_token={auth_token}; ct0={ct0}"

            await self._api.pool.add_account(
                username="cookie_auth",
                password="not_used",
                email="not_used@example.com",
                email_password="not_used",
                cookies=cookies
            )

            self._initialized = True
            logger.info(f"Twitter scraper initialized with {len(self.accounts)} accounts to monitor")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Twitter scraper: {e}")
            self._last_error = str(e)
            self._error_count += 1
            return False

    async def fetch_news(self, force: bool = False) -> List[NewsItem]:
        """
        Fetch news from all monitored accounts.

        Args:
            force: Bypass cache TTL and fetch fresh data

        Returns:
            List of NewsItem objects, sorted by date (newest first)
        """
        async with self._fetch_lock:
            now = time.time()

            # Return cached data if within TTL
            if not force and (now - self._last_fetch) < self.cache_ttl:
                return list(self._cache)

            if not self._initialized:
                if not await self.initialize():
                    logger.warning("Scraper not initialized, returning cached data")
                    return list(self._cache)

            try:
                new_items = []

                for username in self.accounts:
                    try:
                        user = await self._api.user_by_login(username)
                        if not user:
                            logger.warning(f"User @{username} not found")
                            continue

                        async for tweet in self._api.user_tweets(
                            user.id,
                            limit=self.max_tweets_per_account
                        ):
                            # Skip duplicates
                            tweet_id = str(tweet.id)
                            if tweet_id in self._seen_ids:
                                continue

                            self._seen_ids.add(tweet_id)

                            item = NewsItem(
                                id=tweet_id,
                                source=username,
                                text=tweet.rawContent,
                                created_at=tweet.date.replace(tzinfo=timezone.utc),
                                likes=tweet.likeCount,
                                retweets=tweet.retweetCount,
                                url=f"https://x.com/{username}/status/{tweet.id}"
                            )
                            new_items.append(item)

                        # Small delay between accounts to avoid rate limits
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.warning(f"Error fetching @{username}: {e}")
                        continue

                # Add new items to cache
                for item in new_items:
                    self._cache.append(item)

                # Sort cache by date (newest first)
                sorted_items = sorted(
                    self._cache,
                    key=lambda x: x.created_at,
                    reverse=True
                )
                self._cache = deque(sorted_items, maxlen=self.max_cached_items)

                # Trim seen_ids to prevent memory growth
                if len(self._seen_ids) > self.max_cached_items * 2:
                    current_ids = {item.id for item in self._cache}
                    self._seen_ids = current_ids

                self._last_fetch = now
                self._fetch_count += 1

                logger.info(
                    f"Fetched {len(new_items)} new items, "
                    f"cache size: {len(self._cache)}"
                )

                return list(self._cache)

            except Exception as e:
                logger.error(f"Error during fetch: {e}")
                self._last_error = str(e)
                self._error_count += 1
                return list(self._cache)

    def get_cached_news(self) -> List[NewsItem]:
        """Get currently cached news without fetching."""
        return list(self._cache)

    def get_status(self) -> Dict:
        """Get scraper status and metrics."""
        return {
            "initialized": self._initialized,
            "accounts_monitored": len(self.accounts),
            "accounts": self.accounts,
            "cache_size": len(self._cache),
            "cache_ttl_seconds": self.cache_ttl,
            "last_fetch": datetime.fromtimestamp(self._last_fetch).isoformat() if self._last_fetch else None,
            "seconds_since_fetch": int(time.time() - self._last_fetch) if self._last_fetch else None,
            "fetch_count": self._fetch_count,
            "error_count": self._error_count,
            "last_error": self._last_error
        }


# Singleton instance for the application
_scraper_instance: Optional[TwitterNewsScraper] = None


def get_twitter_scraper() -> TwitterNewsScraper:
    """Get or create the singleton TwitterNewsScraper instance."""
    global _scraper_instance
    if _scraper_instance is None:
        _scraper_instance = TwitterNewsScraper()
    return _scraper_instance
