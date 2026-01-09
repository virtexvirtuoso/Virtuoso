# Virtuoso MCP Server - HTTP Client
# Async HTTP client with retry, circuit breaker, and graceful error handling

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""

    failure_threshold: int = 5
    recovery_timeout: timedelta = timedelta(seconds=60)
    failures: int = 0
    last_failure: Optional[datetime] = None
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failures += 1
        self.last_failure = datetime.now()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                f"Circuit breaker OPEN after {self.failures} failures"
            )

    def record_success(self) -> None:
        """Record success and reset the circuit."""
        if self.state == "HALF_OPEN":
            logger.info("Circuit breaker recovered, closing")
        self.failures = 0
        self.state = "CLOSED"

    def can_execute(self) -> bool:
        """Check if we can execute a request."""
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if self.last_failure and (
                datetime.now() - self.last_failure > self.recovery_timeout
            ):
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker HALF_OPEN, testing recovery")
                return True
            return False
        return True  # HALF_OPEN allows one request


@dataclass
class VirtuosoClient:
    """
    Async HTTP client for Virtuoso API with retry and circuit breaker.

    Features:
    - Exponential backoff on failures
    - Circuit breaker to prevent cascading failures
    - Configurable timeout
    - Graceful error handling with user-friendly messages
    """

    base_url: str = field(default_factory=lambda: settings.virtuoso_api_url)
    timeout: float = field(default_factory=lambda: settings.request_timeout)
    max_retries: int = field(default_factory=lambda: settings.max_retries)
    retry_delay: float = field(default_factory=lambda: settings.retry_delay)
    circuit_breaker: CircuitBreaker = field(default_factory=CircuitBreaker)

    async def get(
        self,
        path: str,
        params: Optional[dict] = None,
        base_url: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Make a GET request with retry logic.

        Args:
            path: API endpoint path (e.g., "/api/signals/top")
            params: Optional query parameters
            base_url: Override base URL (for derivatives API)

        Returns:
            dict with either "data" key on success or "error" key on failure
        """
        url = f"{base_url or self.base_url}{path}"

        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            return {
                "error": "Service temporarily unavailable. Please try again in a moment.",
                "circuit_open": True,
            }

        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()

                    self.circuit_breaker.record_success()
                    return {"data": response.json(), "status": response.status_code}

            except httpx.TimeoutException:
                last_error = "Request timed out. Market data temporarily unavailable."
                logger.warning(f"Timeout on {url} (attempt {attempt + 1})")

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 404:
                    # Don't retry 404s
                    return {"error": f"Endpoint not found: {path}", "status": status}
                elif status == 429:
                    last_error = "Rate limit exceeded. Please wait a moment."
                    logger.warning(f"Rate limited on {url}")
                elif status >= 500:
                    last_error = f"Server error ({status}). Please try again."
                    logger.error(f"Server error {status} on {url}")
                else:
                    last_error = f"API error: {status}"
                    logger.error(f"HTTP {status} on {url}")

            except httpx.ConnectError:
                last_error = "Cannot connect to Virtuoso. VPS may be offline."
                logger.error(f"Connection failed to {url}")

            except Exception as e:
                last_error = f"Unexpected error: {type(e).__name__}"
                logger.exception(f"Unexpected error on {url}")

            # Exponential backoff before retry
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2**attempt)
                logger.info(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)

        # All retries failed
        self.circuit_breaker.record_failure()
        return {"error": last_error or "Request failed after retries"}


# Singleton clients for each API
_api_client: Optional[VirtuosoClient] = None
_derivatives_client: Optional[VirtuosoClient] = None


def get_api_client() -> VirtuosoClient:
    """Get or create the main API client (port 8002)."""
    global _api_client
    if _api_client is None:
        _api_client = VirtuosoClient(base_url=settings.virtuoso_api_url)
    return _api_client


def get_derivatives_client() -> VirtuosoClient:
    """Get or create the derivatives API client (port 8888)."""
    global _derivatives_client
    if _derivatives_client is None:
        _derivatives_client = VirtuosoClient(
            base_url=settings.virtuoso_derivatives_url
        )
    return _derivatives_client


# Export for easy import
__all__ = [
    "VirtuosoClient",
    "CircuitBreaker",
    "get_api_client",
    "get_derivatives_client",
]
