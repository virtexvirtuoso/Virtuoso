# Virtuoso MCP Server - FastMCP Application Instance
# Shared mcp instance to avoid circular imports

import sys
from pathlib import Path

# Ensure src is in path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastmcp import FastMCP

# Initialize FastMCP server (shared instance)
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
