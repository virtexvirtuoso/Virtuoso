# Virtuoso MCP Server - Market Tools
# Market overview and perpetuals analysis tools

from ..server import mcp
from ..utils.client import get_api_client
from ..formatters.response import (
    format_market_overview,
    format_perpetuals_pulse,
    format_error,
    add_disclaimer,
    format_number,
    format_percent,
    format_price,
    format_market_regime,
    format_timestamp,
    SIGNAL_EMOJIS,
)


@mcp.tool()
async def get_market_overview() -> str:
    """
    Get a snapshot of overall market conditions.

    Returns market regime, BTC price/dominance, volatility metrics,
    and overall market health indicators.

    Returns:
        Formatted market overview with key metrics and interpretation.
    """
    client = get_api_client()
    result = await client.get("/api/market/overview")

    if "error" in result:
        return format_error(result["error"])

    data = result["data"]

    lines = ["🌍 **Market Overview**\n"]

    # Timestamp and version
    version = data.get("version", "N/A")
    lines.append(f"_Version: {version}_\n")

    # Total symbols and volume
    total_symbols = data.get("total_symbols", 0)
    total_volume = data.get("total_volume_24h", 0)
    lines.append(f"**Active Symbols:** {total_symbols}")
    lines.append(f"**24h Volume:** {format_number(total_volume, prefix='$')}")
    lines.append("")

    # BTC Metrics
    btc_dom = data.get("btc_dominance", 0)
    btc_vol = data.get("btc_volatility", 0)
    btc_daily_vol = data.get("btc_daily_volatility", 0)

    lines.append("**BTC Metrics:**")
    if btc_dom:
        lines.append(f"  • Dominance: {btc_dom:.1f}%")
    if btc_vol:
        lines.append(f"  • Volatility: {btc_vol:.2f}%")
    if btc_daily_vol:
        lines.append(f"  • Daily Vol: {btc_daily_vol:.2f}%")
    lines.append("")

    # Trend strength
    trend_strength = data.get("trend_strength", 0)
    if trend_strength >= 70:
        trend_emoji = "🟢"
        trend_label = "Strong"
    elif trend_strength >= 50:
        trend_emoji = "🟡"
        trend_label = "Moderate"
    elif trend_strength >= 30:
        trend_emoji = "🟠"
        trend_label = "Weak"
    else:
        trend_emoji = "🔴"
        trend_label = "Very Weak"

    lines.append(f"**Market Trend:** {trend_emoji} {trend_label} ({trend_strength:.1f})")

    # Market regime from additional data if available
    regime = data.get("market_regime", data.get("regime"))
    if regime:
        lines.append(f"**Regime:** {format_market_regime(regime)}")

    # Sentiment if available
    sentiment = data.get("market_sentiment", data.get("sentiment"))
    if sentiment:
        sent_emoji = SIGNAL_EMOJIS.get(str(sentiment).upper(), "⚪")
        lines.append(f"**Sentiment:** {sent_emoji} {sentiment}")

    lines.append(f"\n_Updated: {format_timestamp()}_")
    return add_disclaimer("\n".join(lines), short=True)


@mcp.tool()
async def get_perpetuals_pulse() -> str:
    """
    Get perpetuals market summary with derivatives positioning.

    Returns open interest, funding rates, long/short ratios,
    and liquidation activity across monitored perpetual markets.

    Returns:
        Formatted perpetuals overview with positioning interpretation.
    """
    client = get_api_client()
    result = await client.get("/api/dashboard/perpetuals-pulse")

    if "error" in result:
        return format_error(result["error"])

    data = result["data"]

    lines = ["📊 **Perpetuals Market Pulse**\n"]

    # Status indicator
    status = data.get("status", "unknown")
    status_emoji = "🟢" if status == "ok" else "🟡" if status == "degraded" else "🔴"
    lines.append(f"_Status: {status_emoji} {status}_\n")

    # Open Interest
    total_oi = data.get("total_open_interest", 0)
    oi_change = data.get("oi_change_24h", data.get("open_interest_change_24h", 0))
    if total_oi:
        oi_emoji = "📈" if oi_change > 0 else "📉" if oi_change < 0 else "➡️"
        lines.append(
            f"**Open Interest:** {format_number(total_oi, prefix='$')} "
            f"{oi_emoji} {format_percent(oi_change)}"
        )

    # Volume
    total_vol = data.get("total_volume_24h", 0)
    if total_vol:
        lines.append(f"**24h Volume:** {format_number(total_vol, prefix='$')}")
    lines.append("")

    # Funding Rates
    funding = data.get("funding_rate", 0)
    funding_min = data.get("funding_rate_min", 0)
    funding_max = data.get("funding_rate_max", 0)

    if funding is not None:
        fund_emoji = "🟢" if funding > 0 else "🔴" if funding < 0 else "⚪"
        lines.append("**Funding Rates:**")
        lines.append(f"  • Average: {fund_emoji} {funding:.4f}%")
        if funding_min != 0 or funding_max != 0:
            lines.append(f"  • Range: {funding_min:.4f}% to {funding_max:.4f}%")
        lines.append("")

    # Long/Short Ratio
    ls_ratio = data.get("long_short_ratio", data.get("ls_ratio"))
    if ls_ratio:
        if ls_ratio > 1.2:
            ls_emoji = "🐂"
            ls_label = "Longs dominant"
        elif ls_ratio < 0.8:
            ls_emoji = "🐻"
            ls_label = "Shorts dominant"
        else:
            ls_emoji = "⚖️"
            ls_label = "Balanced"
        lines.append(f"**L/S Ratio:** {ls_emoji} {ls_ratio:.2f} ({ls_label})")
        lines.append("")

    # Liquidations if available
    liq_24h = data.get("liquidations_24h", data.get("total_liquidations"))
    if liq_24h:
        lines.append(f"**24h Liquidations:** {format_number(liq_24h, prefix='$')}")
        liq_long = data.get("liquidations_long_24h")
        liq_short = data.get("liquidations_short_24h")
        if liq_long and liq_short:
            lines.append(
                f"  • Longs: {format_number(liq_long, prefix='$')} | "
                f"Shorts: {format_number(liq_short, prefix='$')}"
            )
        lines.append("")

    # Market positioning interpretation
    if funding is not None and ls_ratio:
        lines.append("**Interpretation:**")
        if funding > 0.01 and ls_ratio > 1.2:
            lines.append(
                "💡 _Crowded longs with positive funding - potential squeeze risk if price drops_"
            )
        elif funding < -0.01 and ls_ratio < 0.8:
            lines.append(
                "💡 _Crowded shorts with negative funding - potential squeeze risk if price rises_"
            )
        elif abs(funding) < 0.005 and 0.9 < ls_ratio < 1.1:
            lines.append("💡 _Neutral positioning - no extreme imbalance detected_")
        else:
            lines.append("💡 _Mixed signals - monitor for developing trends_")

    lines.append(f"\n_Updated: {format_timestamp()}_")
    return add_disclaimer("\n".join(lines), short=True)
