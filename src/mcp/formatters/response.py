# Virtuoso MCP Server - Response Formatter
# Transform API responses into AI-friendly format with emojis and disclaimers

from datetime import datetime
from typing import Any, Optional

# Signal type to emoji mapping
SIGNAL_EMOJIS = {
    "LONG": "🟢",
    "SHORT": "🔴",
    "WAIT": "⚪",
    "HOLD": "🟡",
    "BULLISH": "🟢",
    "BEARISH": "🔴",
    "NEUTRAL": "⚪",
}

# Confidence level visual indicators
def confidence_bar(value: float, max_value: float = 100) -> str:
    """Create visual confidence bar."""
    if max_value == 0:
        return "░░░░░"
    pct = min(value / max_value, 1.0)
    filled = int(pct * 5)
    return "█" * filled + "░" * (5 - filled)


def confidence_emoji(value: float) -> str:
    """Get emoji based on confidence level (0-100)."""
    if value >= 80:
        return "🔥"  # Very high
    elif value >= 70:
        return "💪"  # High
    elif value >= 60:
        return "👍"  # Good
    elif value >= 50:
        return "🤔"  # Moderate
    else:
        return "⚠️"  # Low


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format timestamp for display."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%H:%M:%S UTC")


def freshness_indicator(age_seconds: float) -> str:
    """Get freshness indicator based on data age."""
    if age_seconds < 30:
        return "🟢 Live"
    elif age_seconds < 60:
        return "🟡 Recent"
    elif age_seconds < 300:
        return "🟠 Stale"
    else:
        return "🔴 Old"


# Standard disclaimers
DISCLAIMER = """
---
*This is not financial advice. Always do your own research and manage risk appropriately.*
"""

DISCLAIMER_SHORT = "*Not financial advice. DYOR.*"


def add_disclaimer(response: str, short: bool = False) -> str:
    """Add risk disclaimer to response."""
    return response + (DISCLAIMER_SHORT if short else DISCLAIMER)


def format_number(value: float, decimals: int = 2, prefix: str = "") -> str:
    """Format number with optional prefix."""
    if abs(value) >= 1_000_000:
        return f"{prefix}{value/1_000_000:.{decimals}f}M"
    elif abs(value) >= 1_000:
        return f"{prefix}{value/1_000:.{decimals}f}K"
    else:
        return f"{prefix}{value:.{decimals}f}"


def format_percent(value: float, show_sign: bool = True) -> str:
    """Format percentage with sign."""
    sign = "+" if value > 0 and show_sign else ""
    return f"{sign}{value:.2f}%"


def format_price(value: float, symbol: str = "") -> str:
    """Format price based on magnitude."""
    if value >= 1000:
        return f"${value:,.0f}"
    elif value >= 1:
        return f"${value:.2f}"
    elif value >= 0.01:
        return f"${value:.4f}"
    else:
        return f"${value:.8f}"


def format_signal_action(action: str, confidence: float) -> str:
    """Format signal action with emoji and confidence."""
    emoji = SIGNAL_EMOJIS.get(action.upper(), "❓")
    conf_emoji = confidence_emoji(confidence)
    return f"{emoji} **{action}** ({confidence:.0f}%) {conf_emoji}"


def format_market_regime(regime: str, strength: Optional[float] = None) -> str:
    """Format market regime with emoji."""
    regime_upper = regime.upper()
    emoji = SIGNAL_EMOJIS.get(regime_upper, "⚪")
    strength_str = f" ({strength:.1f})" if strength is not None else ""
    return f"{emoji} {regime}{strength_str}"


def format_error(error: str, suggestion: Optional[str] = None) -> str:
    """Format error message with optional suggestion."""
    msg = f"❌ **Error:** {error}"
    if suggestion:
        msg += f"\n💡 *Suggestion:* {suggestion}"
    return msg


def format_top_signals(signals: list[dict]) -> str:
    """Format list of top signals."""
    if not signals:
        return "No signals available at this time."

    lines = ["📊 **Top Trading Signals**\n"]

    for i, signal in enumerate(signals, 1):
        symbol = signal.get("symbol", "UNKNOWN")
        action = signal.get("action", signal.get("signal", "N/A"))
        confidence = signal.get("confidence", signal.get("score", 50))
        change_24h = signal.get("change_24h", signal.get("change", 0))

        emoji = SIGNAL_EMOJIS.get(str(action).upper(), "⚪")
        change_str = format_percent(change_24h)
        change_emoji = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"

        lines.append(
            f"{i}. **{symbol}** — {emoji} {action} "
            f"({confidence:.0f}%) {change_emoji} {change_str}"
        )

    lines.append(f"\n_Updated: {format_timestamp()}_")
    return "\n".join(lines)


def format_symbol_analysis(data: dict) -> str:
    """Format symbol confluence analysis."""
    symbol = data.get("symbol", "UNKNOWN")
    score = data.get("score", data.get("confluence_score", 50))

    # Determine bias
    if score >= 70:
        bias = "Strong Bullish"
        bias_emoji = "🟢🟢"
    elif score >= 50:
        bias = "Bullish"
        bias_emoji = "🟢"
    elif score >= 30:
        bias = "Bearish"
        bias_emoji = "🔴"
    else:
        bias = "Strong Bearish"
        bias_emoji = "🔴🔴"

    lines = [
        f"📊 **{symbol} Analysis**",
        f"",
        f"**Overall Score:** {score:.1f}/100 {confidence_bar(score)} {bias_emoji} {bias}",
        f"",
    ]

    # Component breakdown if available
    components = data.get("components", data.get("breakdown", {}))
    if components:
        lines.append("**Component Breakdown:**")
        for name, value in components.items():
            if isinstance(value, (int, float)):
                lines.append(f"  • {name}: {value:.1f} {confidence_bar(value)}")

    lines.append(f"\n_Updated: {format_timestamp()}_")
    return "\n".join(lines)


def format_market_overview(data: dict) -> str:
    """Format market overview response."""
    lines = ["🌍 **Market Overview**\n"]

    # BTC price if available
    btc_price = data.get("btc_price", data.get("price", {}).get("BTC"))
    if btc_price:
        btc_change = data.get("btc_change_24h", 0)
        change_emoji = "📈" if btc_change > 0 else "📉" if btc_change < 0 else "➡️"
        lines.append(f"**Bitcoin:** {format_price(btc_price)} {change_emoji} {format_percent(btc_change)}")

    # Market regime
    regime = data.get("regime", data.get("market_regime", "NEUTRAL"))
    strength = data.get("trend_strength", data.get("regime_strength"))
    lines.append(f"**Regime:** {format_market_regime(regime, strength)}")

    # Sentiment
    sentiment = data.get("sentiment", data.get("market_sentiment", "NEUTRAL"))
    lines.append(f"**Sentiment:** {SIGNAL_EMOJIS.get(sentiment.upper(), '⚪')} {sentiment}")

    # Volatility if available
    volatility = data.get("volatility", data.get("vix"))
    if volatility:
        lines.append(f"**Volatility:** {volatility:.1f}")

    lines.append(f"\n_Updated: {format_timestamp()}_")
    return "\n".join(lines)


def format_recommendation(data: dict) -> str:
    """Format trading recommendation."""
    symbol = data.get("symbol", "UNKNOWN")
    action = data.get("action", data.get("recommendation", "WAIT"))
    confidence = data.get("action_confidence", data.get("confidence", 50))

    emoji = SIGNAL_EMOJIS.get(action.upper(), "⚪")

    lines = [
        f"{emoji} **{symbol}** — {action}",
        f"",
        f"**Confidence:** {confidence}% {confidence_bar(confidence)}",
    ]

    # Signal details
    grade = data.get("signal_grade", data.get("grade"))
    if grade:
        lines.append(f"**Grade:** {grade}")

    strength = data.get("signal_strength", data.get("strength"))
    if strength:
        lines.append(f"**Strength:** {strength}")

    # Why section
    why = data.get("why", data.get("reasons", {}))
    if why:
        lines.append("\n**Why:**")
        if isinstance(why, dict):
            for key, value in why.items():
                lines.append(f"  • {key}: {value}")
        elif isinstance(why, list):
            for item in why:
                lines.append(f"  • {item}")

    # Risk warning
    risk = data.get("risk_warning", "Always use proper risk management.")
    lines.append(f"\n⚠️ {risk}")

    lines.append(f"\n_Updated: {format_timestamp()}_")
    return "\n".join(lines)


def format_perpetuals_pulse(data: dict) -> str:
    """Format perpetuals market pulse."""
    lines = ["📊 **Perpetuals Market Pulse**\n"]

    # Open Interest
    oi = data.get("total_oi", data.get("open_interest"))
    if oi:
        oi_change = data.get("oi_change_24h", 0)
        lines.append(f"**Open Interest:** {format_number(oi, prefix='$')} ({format_percent(oi_change)})")

    # Funding Rate
    funding = data.get("avg_funding", data.get("funding_rate"))
    if funding is not None:
        funding_emoji = "🟢" if funding > 0 else "🔴" if funding < 0 else "⚪"
        lines.append(f"**Avg Funding:** {funding_emoji} {funding:.4f}%")

    # Long/Short Ratio
    ls_ratio = data.get("long_short_ratio", data.get("ls_ratio"))
    if ls_ratio:
        ls_emoji = "🐂" if ls_ratio > 1 else "🐻" if ls_ratio < 1 else "⚖️"
        lines.append(f"**L/S Ratio:** {ls_emoji} {ls_ratio:.2f}")

    # Market positioning interpretation
    if funding is not None and ls_ratio:
        if funding > 0.01 and ls_ratio > 1.2:
            lines.append("\n💡 *Crowded longs - potential squeeze risk*")
        elif funding < -0.01 and ls_ratio < 0.8:
            lines.append("\n💡 *Crowded shorts - potential squeeze risk*")
        elif abs(funding) < 0.005:
            lines.append("\n💡 *Neutral positioning*")

    lines.append(f"\n_Updated: {format_timestamp()}_")
    return "\n".join(lines)


# Export for easy import
__all__ = [
    "SIGNAL_EMOJIS",
    "confidence_bar",
    "confidence_emoji",
    "format_timestamp",
    "freshness_indicator",
    "add_disclaimer",
    "format_number",
    "format_percent",
    "format_price",
    "format_signal_action",
    "format_market_regime",
    "format_error",
    "format_top_signals",
    "format_symbol_analysis",
    "format_market_overview",
    "format_recommendation",
    "format_perpetuals_pulse",
    "DISCLAIMER",
    "DISCLAIMER_SHORT",
]
