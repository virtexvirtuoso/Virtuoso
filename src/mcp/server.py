# Virtuoso MCP Server - FastMCP Entry Point
# Exposes trading intelligence to AI assistants via Model Context Protocol

from fastmcp import FastMCP
from datetime import datetime

from .config import settings

# Initialize FastMCP server
mcp = FastMCP(
    "virtuoso",
    instructions="""
    Virtuoso Trading Assistant - AI-powered crypto trading intelligence.

    Available capabilities:
    - Real-time trading signals with confluence scoring
    - Symbol-specific analysis (ETH, BTC, SOL, etc.)
    - Market overview and regime detection
    - Derivatives analysis (funding, OI, CVD)

    Tips:
    - Use natural queries like "What should I trade?" or "Analyze ETH"
    - All signals include confidence scores (0-100%)
    - Risk warnings are included automatically
    - Data is real-time from live exchange feeds
    """,
)


@mcp.tool()
async def hello_virtuoso() -> str:
    """
    Test tool to verify MCP server is running.
    Returns a greeting with current timestamp.
    """
    return f"""
Virtuoso MCP Server v0.1.0

Status: Online
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
API URL: {settings.virtuoso_api_url}
Derivatives URL: {settings.virtuoso_derivatives_url}

Ready to provide trading intelligence!
"""


@mcp.tool()
async def get_server_config() -> dict:
    """
    Returns current server configuration (non-sensitive).
    Useful for debugging connection issues.
    """
    return {
        "version": "0.1.0",
        "api_url": settings.virtuoso_api_url,
        "derivatives_url": settings.virtuoso_derivatives_url,
        "timeout": settings.request_timeout,
        "max_retries": settings.max_retries,
        "mock_mode": settings.mock_mode,
    }


# Entry point for running as module
if __name__ == "__main__":
    mcp.run()
