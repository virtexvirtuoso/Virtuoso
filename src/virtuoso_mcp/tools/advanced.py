# Virtuoso MCP Server - Advanced Tools
# MCP tools for multi-timeframe analysis and fusion signals

from typing import Optional

from src.virtuoso_mcp.utils.client import get_api_client
from src.virtuoso_mcp.formatters.response import (
    format_timestamp,
    format_percent,
    add_disclaimer,
    format_error,
    confidence_bar,
    confidence_emoji,
)


# Valid cluster options for MTF analysis
VALID_CLUSTERS = {"scalping", "day_trading", "swing_trading", "comprehensive"}


def normalize_symbol(symbol: str) -> str:
    """Normalize symbol input to expected format."""
    s = symbol.upper().strip()
    # Remove common suffixes
    for suffix in ["/USDT", "-USDT", "USDT", "/USD", "-USD"]:
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return s


def format_fusion_signal(data: dict, symbol: Optional[str] = None, cluster: str = "day_trading") -> str:
    """
    Format multi-timeframe fusion signal response.

    Provides interpretation of MTF alignment and trading signals.
    """
    lines = ["🔀 **Multi-Timeframe Fusion Analysis**\n"]

    if symbol:
        lines[0] = f"🔀 **{symbol} Multi-Timeframe Fusion**\n"

    # Get rankings data
    rankings = data.get("rankings", [])
    timeframes = data.get("timeframes_analyzed", [])
    cluster_name = data.get("cluster", cluster).replace("_", " ").title()

    lines.append(f"**Cluster:** {cluster_name}")
    lines.append(f"**Timeframes:** {', '.join(str(tf) + 'H' for tf in timeframes)}")
    lines.append("")

    # If looking for specific symbol
    if symbol:
        normalized = normalize_symbol(symbol)
        symbol_data = None
        for ranking in rankings:
            if ranking.get("symbol", "").upper() == normalized:
                symbol_data = ranking
                break

        if symbol_data:
            lines.extend(_format_single_symbol(symbol_data))
        else:
            lines.append(f"⚠️ **{normalized}** not found in current rankings.")
            lines.append("Symbol may not have sufficient data or is not outperforming BTC.")
            lines.append("\n**Top Performers Instead:**")
            # Show top 3 as alternative
            for ranking in rankings[:3]:
                lines.extend(_format_ranking_entry(ranking))
                lines.append("")
    else:
        # Show top performers
        lines.append("**🏆 Top Performers vs BTC:**\n")
        for ranking in rankings[:5]:
            lines.extend(_format_ranking_entry(ranking))
            lines.append("")

        # Add summary interpretation
        if rankings:
            lines.extend(_format_market_interpretation(rankings, timeframes))

    lines.append(f"\n_Updated: {format_timestamp()}_")
    return "\n".join(lines)


def _format_single_symbol(data: dict) -> list[str]:
    """Format detailed analysis for a single symbol."""
    lines = []

    symbol = data.get("symbol", "UNKNOWN")
    mtf_score = data.get("mtf_score", 0)
    signal = data.get("signal", "UNKNOWN")
    total_outperf = data.get("total_outperformance", 0)
    avg_perf = data.get("avg_performance", 0)
    consistency = data.get("consistency_ratio", 0)
    aligned = data.get("aligned_timeframes", 0)
    total_tf = data.get("total_timeframes", 3)
    rank = data.get("rank", "N/A")

    # Signal emoji
    signal_emoji = _get_signal_emoji(signal)

    lines.append(f"**Rank:** #{rank}")
    lines.append(f"**MTF Score:** {mtf_score:.1f}/100 {confidence_bar(mtf_score)} {confidence_emoji(mtf_score)}")
    lines.append(f"**Signal:** {signal_emoji} **{signal}**")
    lines.append(f"**Total Outperformance:** {format_percent(total_outperf)}")
    lines.append(f"**Avg Performance/TF:** {format_percent(avg_perf)}")
    lines.append(f"**Consistency Ratio:** {consistency:.0%}")
    lines.append(f"**Aligned Timeframes:** {aligned}/{total_tf}")

    # Timeframe breakdown
    tf_details = data.get("timeframe_details", {})
    if tf_details:
        lines.append("\n**Timeframe Breakdown:**")
        for tf, perf in sorted(tf_details.items(), key=lambda x: int(x[0])):
            perf_emoji = "📈" if perf > 0 else "📉" if perf < 0 else "➡️"
            lines.append(f"  • {tf}H: {perf_emoji} {format_percent(perf)}")

    # Interpretation
    lines.append("\n**Interpretation:**")
    if consistency >= 1.0:
        lines.append("• ✅ **Perfect alignment** - All timeframes confirm the signal")
        lines.append("• Higher conviction trade setup")
    elif consistency >= 0.67:
        lines.append("• 📊 **Good alignment** - Majority of timeframes agree")
        lines.append("• Reasonable conviction setup")
    else:
        lines.append("• ⚠️ **Mixed signals** - Timeframes are conflicting")
        lines.append("• Lower conviction, wait for alignment")

    if total_outperf > 5:
        lines.append(f"• 🚀 Strong BTC outperformance ({format_percent(total_outperf)})")
    elif total_outperf > 0:
        lines.append(f"• 📈 Moderate BTC outperformance ({format_percent(total_outperf)})")

    return lines


def _format_ranking_entry(data: dict) -> list[str]:
    """Format a single ranking entry for the leaderboard."""
    lines = []

    symbol = data.get("symbol", "UNKNOWN")
    mtf_score = data.get("mtf_score", 0)
    signal = data.get("signal", "UNKNOWN")
    total_outperf = data.get("total_outperformance", 0)
    consistency = data.get("consistency_ratio", 0)
    rank = data.get("rank", "?")

    signal_emoji = _get_signal_emoji(signal)
    consistency_str = "✅" if consistency >= 1.0 else "📊" if consistency >= 0.67 else "⚠️"

    lines.append(
        f"**#{rank} {symbol}** — {signal_emoji} {signal} "
        f"| Score: {mtf_score:.0f} | {format_percent(total_outperf)} vs BTC {consistency_str}"
    )

    return lines


def _format_market_interpretation(rankings: list, timeframes: list) -> list[str]:
    """Generate market-wide interpretation from rankings."""
    lines = ["\n**📊 Market Interpretation:**"]

    # Count strong signals
    strong_buys = sum(1 for r in rankings if r.get("signal") == "STRONG_BUY")
    buys = sum(1 for r in rankings if r.get("signal") == "BUY")
    sells = sum(1 for r in rankings if "SELL" in str(r.get("signal", "")))

    total = len(rankings)
    bullish_pct = ((strong_buys + buys) / total * 100) if total > 0 else 0

    if bullish_pct >= 70:
        lines.append("• 🟢 **Bullish Regime** - Most altcoins outperforming BTC")
        lines.append("• Consider: Altcoin exposure over BTC dominance")
    elif bullish_pct >= 50:
        lines.append("• 🟡 **Selective Bullish** - Some altcoins outperforming")
        lines.append("• Consider: Focus on top performers only")
    else:
        lines.append("• 🔴 **BTC Dominance** - Few altcoins outperforming")
        lines.append("• Consider: BTC exposure or defensive positioning")

    # Perfect alignment count
    perfect_aligned = sum(1 for r in rankings if r.get("consistency_ratio", 0) >= 1.0)
    if perfect_aligned >= 3:
        lines.append(f"• 🎯 {perfect_aligned} symbols with perfect MTF alignment")

    return lines


def _get_signal_emoji(signal: str) -> str:
    """Get emoji for signal type."""
    signal_upper = str(signal).upper()
    if "STRONG_BUY" in signal_upper:
        return "🟢🟢"
    elif "BUY" in signal_upper:
        return "🟢"
    elif "STRONG_SELL" in signal_upper:
        return "🔴🔴"
    elif "SELL" in signal_upper:
        return "🔴"
    elif "HOLD" in signal_upper:
        return "🟡"
    else:
        return "⚪"


def format_liquidation_zones(data: dict, symbol: str) -> str:
    """
    Format liquidation zones response with cascade detection and interpretation.

    Shows clustered liquidation levels across exchanges with support/resistance implications.
    """
    lines = ["💥 **Liquidation Zones Analysis**\n"]
    lines[0] = f"💥 **{symbol} Liquidation Zones**\n"

    zones = data.get("zones", [])
    cascade_detected = data.get("cascade_detected", False)
    cascade_price = data.get("cascade_price")
    cascade_size = data.get("cascade_size")
    total_exchanges = data.get("total_exchanges", 0)
    lookback_hours = data.get("lookback_hours", 1)

    lines.append(f"**Lookback:** {lookback_hours}H | **Exchanges:** {total_exchanges}")
    lines.append("")

    # Cascade warning (prominent if detected)
    if cascade_detected and cascade_price and cascade_size:
        lines.append("⚠️ **CASCADE RISK DETECTED** ⚠️")
        lines.append(f"**Price Level:** ${cascade_price:,.2f}")
        lines.append(f"**Cluster Size:** ${cascade_size:,.0f}")
        lines.append("_Large liquidation cluster may trigger cascade effect_")
        lines.append("")

    # No zones found
    if not zones:
        lines.append("_No significant liquidation zones detected in this period._")
        lines.append("\n**Interpretation:**")
        lines.append("• Market appears stable with low liquidation activity")
        lines.append("• No major support/resistance from liquidation clusters")
        lines.append(f"\n_Updated: {format_timestamp()}_")
        return "\n".join(lines)

    # Format zones (top 5)
    lines.append("**📊 Liquidation Clusters:**\n")

    for i, zone in enumerate(zones[:5], 1):
        price = zone.get("price", 0)
        size_usd = zone.get("total_size_usd", 0)
        count = zone.get("count", 0)
        exchanges = zone.get("exchanges", [])
        side = zone.get("side", "unknown")
        confidence = zone.get("confidence", "low")

        # Side emoji
        side_emoji = "📈" if side == "long" else "📉" if side == "short" else "➡️"
        side_label = "Long Liqs" if side == "long" else "Short Liqs" if side == "short" else "Mixed"

        # Confidence indicator
        conf_indicator = _get_confidence_indicator(confidence)

        # Format exchanges
        exchanges_str = ", ".join(exchanges[:3]) + ("..." if len(exchanges) > 3 else "")

        lines.append(
            f"**#{i}** ${price:,.2f} — {side_emoji} {side_label} | "
            f"${size_usd:,.0f} ({count} events) {conf_indicator}"
        )
        lines.append(f"   _Exchanges: {exchanges_str}_")
        lines.append("")

    # Summary statistics
    total_long_zones = sum(1 for z in zones if z.get("side") == "long")
    total_short_zones = sum(1 for z in zones if z.get("side") == "short")
    total_value = sum(z.get("total_size_usd", 0) for z in zones)
    high_conf_zones = sum(1 for z in zones if z.get("confidence") == "high")

    lines.append("**📈 Summary:**")
    lines.append(f"• Total Zones: {len(zones)} (Long: {total_long_zones}, Short: {total_short_zones})")
    lines.append(f"• Total Value: ${total_value:,.0f}")
    lines.append(f"• High Confidence Zones: {high_conf_zones}")

    # Interpretation
    lines.append("\n**📋 Interpretation:**")

    if zones:
        top_zone = zones[0]
        top_side = top_zone.get("side", "unknown")
        top_price = top_zone.get("price", 0)
        top_size = top_zone.get("total_size_usd", 0)

        if top_side == "long":
            lines.append(f"• **Potential Resistance:** Large long liquidations clustered at ${top_price:,.2f}")
            lines.append("• If price drops to this level, liquidations may accelerate sell pressure")
            lines.append("• Consider this zone as potential support breakdown level")
        elif top_side == "short":
            lines.append(f"• **Potential Support:** Large short liquidations clustered at ${top_price:,.2f}")
            lines.append("• If price rises to this level, short squeezes may accelerate buying")
            lines.append("• Consider this zone as potential resistance breakthrough level")

        if cascade_detected:
            lines.append("• ⚠️ **High cascade risk** - large clusters may trigger chain liquidations")
            lines.append("• Consider reducing leverage near detected levels")

        # Long vs short imbalance
        if total_long_zones > total_short_zones * 2:
            lines.append("• Market leaning heavily long - more downside liquidation risk")
        elif total_short_zones > total_long_zones * 2:
            lines.append("• Market leaning heavily short - more upside squeeze potential")

    lines.append(f"\n_Updated: {format_timestamp()}_")
    return "\n".join(lines)


def _get_confidence_indicator(confidence: str) -> str:
    """Get visual indicator for confidence level."""
    conf_lower = confidence.lower()
    if conf_lower == "high":
        return "🟢 High"
    elif conf_lower == "medium":
        return "🟡 Med"
    else:
        return "🟠 Low"


def register_advanced_tools(mcp):
    """Register all advanced analysis MCP tools."""

    @mcp.tool()
    async def get_fusion_signal(
        symbol: Optional[str] = None,
        cluster: str = "day_trading"
    ) -> str:
        """
        Get multi-timeframe fusion signal aggregating altcoin performance vs BTC.

        This tool analyzes how altcoins are performing relative to Bitcoin across
        multiple timeframes, providing:
        - MTF Score (0-100): Aggregated strength across timeframes
        - Trading Signal: STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
        - Outperformance %: How much the coin beats BTC
        - Consistency Ratio: How aligned the timeframes are (1.0 = perfect)

        High consistency (all timeframes aligned) = higher conviction trades.

        Available clusters (timeframe groupings):
        - scalping: 15m, 30m, 1H (short-term)
        - day_trading: 1H, 4H, 8H (intraday)
        - swing_trading: 4H, 8H, 1D (multi-day)
        - comprehensive: 1H, 4H, 8H, 1D (all timeframes)

        Args:
            symbol: Optional specific symbol (e.g., "ETH", "SOL").
                   If not provided, returns top performers across all symbols.
            cluster: Timeframe cluster - one of: scalping, day_trading,
                    swing_trading, comprehensive. Defaults to day_trading.

        Returns:
            Multi-timeframe fusion analysis with actionable trading signal.
        """
        client = get_api_client()

        # Validate cluster
        cluster_lower = cluster.lower().strip()
        if cluster_lower not in VALID_CLUSTERS:
            return format_error(
                f"Invalid cluster: {cluster}",
                f"Valid options: {', '.join(VALID_CLUSTERS)}"
            )

        # Build params
        params = {"cluster": cluster_lower, "top_n": 10}

        # Fetch MTF ranking data
        result = await client.get("/api/altcoins/mtf-ranking", params=params)

        if "error" in result:
            return format_error(
                result["error"],
                "Check if VPS is online and MTF ranking endpoint is available."
            )

        data = result.get("data", result)

        # Handle case where data might be wrapped
        if "status" in result and result.get("status") == "success":
            data = result.get("data", {})

        if not data.get("rankings"):
            return format_error(
                "No MTF ranking data available",
                "Market data may still be loading. Try again in a few moments."
            )

        # Format response
        normalized_symbol = normalize_symbol(symbol) if symbol else None
        formatted = format_fusion_signal(data, normalized_symbol, cluster_lower)

        return add_disclaimer(formatted, short=True)

    @mcp.tool()
    async def get_liquidation_zones(symbol: str = "BTCUSDT") -> str:
        """
        Get clustered liquidation zones across multiple exchanges.

        This tool analyzes recent liquidation events and clusters them into price
        zones, showing where significant liquidations have occurred. Useful for:
        - Identifying support/resistance levels from liquidation clusters
        - Detecting cascade risk (large clusters that may trigger chain liquidations)
        - Understanding market positioning (long vs short liquidations)

        Each zone includes:
        - Price: The liquidation cluster price level
        - Size (USD): Total value of liquidations in this zone
        - Side: Whether mostly long or short positions were liquidated
        - Confidence: Based on how many exchanges confirm the zone (high/medium/low)
        - Exchanges: Which exchanges contributed to the zone

        **Cascade Detection:**
        When a zone exceeds $200K, it's flagged as cascade risk - meaning price
        reaching this level could trigger a chain reaction of liquidations.

        **Interpretation:**
        - Long liquidation clusters below current price = potential support breakdown
        - Short liquidation clusters above current price = potential resistance breakthrough

        Args:
            symbol: Trading pair to analyze (e.g., "BTCUSDT", "ETHUSDT").
                   Defaults to BTCUSDT.

        Returns:
            Formatted liquidation zones with cascade warnings and trading interpretation.
        """
        client = get_api_client()

        # Normalize symbol
        sym = symbol.upper().strip()
        if not sym.endswith("USDT"):
            sym = sym.replace("/USDT", "").replace("-USDT", "") + "USDT"

        # Fetch liquidation zones
        result = await client.get("/api/liquidation/zones", params={"symbol": sym})

        if "error" in result:
            return format_error(
                result["error"],
                "Check if VPS is online and liquidation collector is running."
            )

        # Handle wrapped response
        data = result.get("data", result)

        # Format response
        formatted = format_liquidation_zones(data, sym)

        return add_disclaimer(formatted, short=True)


# Export for easy import
__all__ = [
    "register_advanced_tools",
    "format_fusion_signal",
    "format_liquidation_zones",
]
