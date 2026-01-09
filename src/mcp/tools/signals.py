# Virtuoso MCP Server - Signal Tools
# Trading signal and symbol analysis tools

import sys
from pathlib import Path

# Ensure src is in path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.mcp.app import mcp
from src.mcp.utils.client import get_api_client, get_derivatives_client
from src.mcp.utils.normalizer import normalize_symbol, suggest_symbol
from src.mcp.formatters.response import (
    format_top_signals,
    format_symbol_analysis,
    format_recommendation,
    format_error,
    add_disclaimer,
    SIGNAL_EMOJIS,
    confidence_bar,
    format_percent,
    format_timestamp,
)


@mcp.tool()
async def get_top_signals(limit: int = 10) -> str:
    """
    Get the top trading signals ranked by confluence score.

    Returns symbols with the strongest bullish or bearish setups based on
    6-dimensional confluence analysis (technical, volume, orderflow, etc.).

    Args:
        limit: Maximum number of signals to return (default 10, max 30)

    Returns:
        Formatted list of top signals with scores and 24h changes.
    """
    limit = min(max(1, limit), 30)  # Clamp to 1-30

    client = get_api_client()
    result = await client.get("/api/dashboard/symbols")

    if "error" in result:
        return format_error(result["error"])

    data = result["data"]
    symbols = data.get("symbols", [])

    if not symbols:
        return "No trading signals available at this time."

    # Sort by distance from 50 (neutral) - strongest signals first
    # Both very bullish (>50) and very bearish (<50) are interesting
    def signal_strength(s):
        score = s.get("score", s.get("confluence_score", 50))
        return abs(score - 50)

    sorted_symbols = sorted(symbols, key=signal_strength, reverse=True)[:limit]

    # Format for display
    lines = ["📊 **Top Trading Signals**\n"]
    lines.append("_Ranked by confluence strength (distance from neutral)_\n")

    for i, sym in enumerate(sorted_symbols, 1):
        symbol = sym.get("symbol", "UNKNOWN")
        score = sym.get("score", sym.get("confluence_score", 50))
        change = sym.get("change_24h", 0)
        signal_type = sym.get("signal_type", "")

        # Determine direction
        if score >= 60:
            emoji = "🟢"
            direction = "BULLISH"
        elif score >= 50:
            emoji = "🟡"
            direction = "NEUTRAL+"
        elif score >= 40:
            emoji = "🟠"
            direction = "NEUTRAL-"
        else:
            emoji = "🔴"
            direction = "BEARISH"

        change_emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        change_str = format_percent(change)

        lines.append(
            f"{i}. **{symbol}** {emoji} {direction} "
            f"({score:.1f}) {change_emoji} {change_str}"
        )

    lines.append(f"\n_Updated: {format_timestamp()}_")
    return add_disclaimer("\n".join(lines), short=True)


@mcp.tool()
async def get_symbol_analysis(symbol: str) -> str:
    """
    Get detailed confluence analysis for a specific trading symbol.

    Breaks down the 6-dimensional analysis into components:
    Technical, Volume, OrderFlow, Orderbook, Position, Sentiment.

    Args:
        symbol: Trading symbol (e.g., 'ETH', 'BTCUSDT', 'ethereum')

    Returns:
        Detailed confluence breakdown with component scores and interpretation.
    """
    normalized = normalize_symbol(symbol)

    client = get_api_client()
    result = await client.get(f"/api/dashboard/confluence-analysis/{normalized}")

    if "error" in result:
        suggestion = suggest_symbol(symbol)
        if suggestion and suggestion != normalized:
            return format_error(
                result["error"], f"Did you mean {suggestion}?"
            )
        return format_error(result["error"])

    data = result["data"]

    # Build formatted output
    score = data.get("score", data.get("confluence_score", 50))

    # Determine bias
    if score >= 70:
        bias = "Strong Bullish"
        bias_emoji = "🟢🟢"
    elif score >= 55:
        bias = "Bullish"
        bias_emoji = "🟢"
    elif score >= 45:
        bias = "Neutral"
        bias_emoji = "⚪"
    elif score >= 30:
        bias = "Bearish"
        bias_emoji = "🔴"
    else:
        bias = "Strong Bearish"
        bias_emoji = "🔴🔴"

    lines = [
        f"📊 **{normalized} Confluence Analysis**",
        "",
        f"**Overall Score:** {score:.1f}/100 {confidence_bar(score)} {bias_emoji} {bias}",
        "",
    ]

    # Component breakdown
    components = data.get("components", {})
    if components:
        lines.append("**Component Breakdown:**")
        for name, value in components.items():
            if isinstance(value, (int, float)):
                # Determine component emoji
                if value >= 60:
                    c_emoji = "🟢"
                elif value >= 40:
                    c_emoji = "⚪"
                else:
                    c_emoji = "🔴"
                lines.append(f"  • {name}: {value:.1f} {confidence_bar(value)} {c_emoji}")
        lines.append("")

    # Interpretations
    interpretations = data.get("interpretations", {})
    if interpretations:
        lines.append("**Interpretation:**")
        for key, value in list(interpretations.items())[:5]:  # Limit to 5
            lines.append(f"  • {key}: {value}")
        lines.append("")

    # Reliability
    reliability = data.get("reliability")
    if reliability:
        lines.append(f"**Data Reliability:** {reliability}")

    lines.append(f"\n_Updated: {format_timestamp()}_")
    return add_disclaimer("\n".join(lines), short=True)


@mcp.tool()
async def get_recommendation(symbol: str) -> str:
    """
    Get AI-powered trading recommendation for a symbol.

    Analyzes derivatives data (funding, OI, CVD, L/S ratio) to generate
    a LONG/SHORT/WAIT recommendation with reasoning.

    Args:
        symbol: Trading symbol (e.g., 'BTC', 'ETHUSDT', 'solana')

    Returns:
        Trading recommendation with confidence, reasoning, and risk warning.
    """
    normalized = normalize_symbol(symbol)

    client = get_derivatives_client()
    result = await client.get(f"/recommendation/{normalized}")

    if "error" in result:
        suggestion = suggest_symbol(symbol)
        if suggestion and suggestion != normalized:
            return format_error(
                result["error"], f"Did you mean {suggestion}?"
            )
        return format_error(result["error"])

    response = result["data"]

    # Handle nested structure
    if "data" in response:
        data = response["data"]
    else:
        data = response

    action = data.get("action", "WAIT")
    confidence = data.get("action_confidence", "50%")
    # Parse confidence to number
    try:
        conf_num = float(str(confidence).replace("%", ""))
    except:
        conf_num = 50

    emoji = SIGNAL_EMOJIS.get(action.upper(), "⚪")

    lines = [
        f"{emoji} **{normalized}** — {action}",
        "",
        f"**Confidence:** {confidence} {confidence_bar(conf_num)}",
        f"**Signal Grade:** {data.get('signal_grade', 'N/A')}",
        f"**Signal Strength:** {data.get('signal_strength', 'N/A')}",
        "",
        f"**Market Bias:** {data.get('market_bias', 'NEUTRAL')} ({data.get('bias_strength', 'N/A')})",
        "",
    ]

    # Why section
    why = data.get("why", {})
    if why:
        lines.append("**Why:**")
        for key, value in why.items():
            # Truncate long values
            val_str = str(value)
            if len(val_str) > 80:
                val_str = val_str[:77] + "..."
            lines.append(f"  • {key}: {val_str}")
        lines.append("")

    # Summary
    summary = data.get("summary")
    if summary:
        lines.append(f"💡 *{summary}*")
        lines.append("")

    # Risk warning
    risk = data.get("risk_warning", "Always use proper risk management.")
    lines.append(f"⚠️ {risk}")

    lines.append(f"\n_Updated: {format_timestamp()}_")
    return add_disclaimer("\n".join(lines))
