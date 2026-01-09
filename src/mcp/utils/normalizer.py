# Virtuoso MCP Server - Symbol Normalizer
# Convert user input to valid trading symbols

from typing import Optional

# Common symbol aliases and typos
SYMBOL_ALIASES: dict[str, str] = {
    # Bitcoin
    "bitcoin": "BTCUSDT",
    "btc": "BTCUSDT",
    "xbt": "BTCUSDT",
    "bitcion": "BTCUSDT",  # typo
    "bitconi": "BTCUSDT",  # typo
    # Ethereum
    "ethereum": "ETHUSDT",
    "eth": "ETHUSDT",
    "ether": "ETHUSDT",
    "etherium": "ETHUSDT",  # typo
    "etheruem": "ETHUSDT",  # typo
    "etherem": "ETHUSDT",  # typo
    # Solana
    "solana": "SOLUSDT",
    "sol": "SOLUSDT",
    # Ripple
    "ripple": "XRPUSDT",
    "xrp": "XRPUSDT",
    # Dogecoin
    "doge": "DOGEUSDT",
    "dogecoin": "DOGEUSDT",
    # Cardano
    "cardano": "ADAUSDT",
    "ada": "ADAUSDT",
    # Avalanche
    "avalanche": "AVAXUSDT",
    "avax": "AVAXUSDT",
    # Chainlink
    "chainlink": "LINKUSDT",
    "link": "LINKUSDT",
    # Polygon
    "polygon": "MATICUSDT",
    "matic": "MATICUSDT",
    # Polkadot
    "polkadot": "DOTUSDT",
    "dot": "DOTUSDT",
    # Litecoin
    "litecoin": "LTCUSDT",
    "ltc": "LTCUSDT",
    # Sui
    "sui": "SUIUSDT",
    # Pepe
    "pepe": "PEPEUSDT",
    # Near
    "near": "NEARUSDT",
    # Arbitrum
    "arbitrum": "ARBUSDT",
    "arb": "ARBUSDT",
    # Optimism
    "optimism": "OPUSDT",
    "op": "OPUSDT",
}

# Supported symbols (subset of most traded)
SUPPORTED_SYMBOLS: set[str] = {
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "MATICUSDT",
    "DOTUSDT",
    "LTCUSDT",
    "SUIUSDT",
    "PEPEUSDT",
    "NEARUSDT",
    "ARBUSDT",
    "OPUSDT",
    "APTUSDT",
    "INJUSDT",
    "SEIUSDT",
    "TIAUSDT",
    "ORDIUSDT",
    "WIFUSDT",
    "BONKUSDT",
    "FETUSDT",
    "RENDERUSDT",
    "AAVEUSDT",
    "MKRUSDT",
    "UNIUSDT",
    "LDOUSDT",
    "ATOMUSDT",
}


def normalize_symbol(user_input: str) -> str:
    """
    Convert user input to valid trading symbol.

    Examples:
        >>> normalize_symbol("eth")
        'ETHUSDT'
        >>> normalize_symbol("ETHUSDT")
        'ETHUSDT'
        >>> normalize_symbol("ethereum")
        'ETHUSDT'
        >>> normalize_symbol("etherium")  # typo
        'ETHUSDT'
        >>> normalize_symbol("BTC")
        'BTCUSDT'
    """
    # Clean input
    cleaned = user_input.strip().lower().replace(" ", "").replace("-", "")

    # Check aliases first
    if cleaned in SYMBOL_ALIASES:
        return SYMBOL_ALIASES[cleaned]

    # Already valid format?
    upper = cleaned.upper()
    if upper.endswith("USDT"):
        return upper

    # Try appending USDT
    with_usdt = f"{upper}USDT"
    return with_usdt


def normalize_base_coin(user_input: str) -> str:
    """
    Convert user input to base coin (for endpoints that need BTC not BTCUSDT).

    Examples:
        >>> normalize_base_coin("BTCUSDT")
        'BTC'
        >>> normalize_base_coin("bitcoin")
        'BTC'
        >>> normalize_base_coin("eth")
        'ETH'
    """
    symbol = normalize_symbol(user_input)
    # Strip USDT suffix
    if symbol.endswith("USDT"):
        return symbol[:-4]
    return symbol


def is_valid_symbol(symbol: str) -> bool:
    """Check if symbol is in supported list."""
    normalized = normalize_symbol(symbol)
    return normalized in SUPPORTED_SYMBOLS


def suggest_symbol(user_input: str) -> Optional[str]:
    """
    Suggest a valid symbol for invalid input.

    Returns None if no good suggestion found.
    """
    cleaned = user_input.strip().lower()

    # Check for partial matches
    for alias, symbol in SYMBOL_ALIASES.items():
        if alias.startswith(cleaned) or cleaned.startswith(alias):
            return symbol

    # Check supported symbols
    upper = cleaned.upper()
    for symbol in SUPPORTED_SYMBOLS:
        if symbol.startswith(upper) or upper in symbol:
            return symbol

    return None


def get_supported_symbols() -> list[str]:
    """Return list of all supported symbols."""
    return sorted(SUPPORTED_SYMBOLS)


# Export for easy import
__all__ = [
    "normalize_symbol",
    "normalize_base_coin",
    "is_valid_symbol",
    "suggest_symbol",
    "get_supported_symbols",
    "SYMBOL_ALIASES",
    "SUPPORTED_SYMBOLS",
]
