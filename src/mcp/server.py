# Virtuoso MCP Server - FastMCP Entry Point
# Exposes trading intelligence to AI assistants via Model Context Protocol

import sys
from pathlib import Path

# Ensure src is in path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from src.mcp.app import mcp
from src.mcp.config import settings


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


# Import tools to register them with mcp
from src.mcp.tools import signals, market  # noqa: F401, E402

# Entry point for running as module
if __name__ == "__main__":
    mcp.run()
