from src.core.formatting.formatter import LogFormatter, AnalysisFormatter

# Sample data
symbol = "XRPUSDT"
confluence_score = 55.44
components = {
    "orderbook": 74.30,
    "orderflow": 55.41,
    "price_structure": 54.50,
    "technical": 37.73,
    "sentiment": 61.19,
    "volume": 45.54
}

# Sample weights
weights = {
    "orderbook": 0.20,
    "orderflow": 0.25,
    "price_structure": 0.15,
    "technical": 0.17,
    "sentiment": 0.10,
    "volume": 0.12
}

# Sample results with component details
results = {
    "technical": {
        "score": 37.73,
        "components": {
            "ao": 49.94,
            "macd": 48.47,
            "atr": 45.07
        },
        "interpretation": "Technical indicators show slight bearish bias within overall neutrality."
    },
    "volume": {
        "score": 45.54,
        "components": {
            "cmf": 100.00,
            "obv": 64.64,
            "adl": 45.22
        },
        "interpretation": "Volume analysis shows increasing selling pressure with rising participation."
    },
    "orderbook": {
        "score": 74.30,
        "components": {
            "spread": 99.97,
            "liquidity": 99.64,
            "depth": 94.52
        },
        "interpretation": "Orderbook shows Strong bid-side dominance with high bid-side liquidity."
    },
    "orderflow": {
        "score": 55.41,
        "components": {
            "open_interest_score": 70.41,
            "imbalance_score": 68.51,
            "pressure_score": 68.51
        },
        "interpretation": "Neutral orderflow. Rising open interest confirms trend strength."
    },
    "sentiment": {
        "score": 61.19,
        "components": {
            "market_activity": 97.20,
            "risk": 72.30,
            "volatility": 62.42
        },
        "interpretation": "Moderately bullish market sentiment with high risk conditions."
    },
    "price_structure": {
        "score": 54.50,
        "components": {
            "support_resistance": 71.95,
            "order_block": 57.78,
            "volume_profile": 56.83
        },
        "interpretation": "Price structure indicates sideways consolidation within a defined range."
    }
}

print("=== STANDARD CONFLUENCE TABLE ===")
# Generate and print the table with fixed alignment
formatted_table = LogFormatter.format_confluence_score_table(
    symbol=symbol,
    confluence_score=confluence_score,
    components=components,
    results=results,
    weights=weights,
    reliability=1.0
)
print(formatted_table)

print("\n\n=== ENHANCED CONFLUENCE TABLE ===")
# Also test the enhanced version
try:
    # This uses the EnhancedFormatter which should be fixed as well
    enhanced_table = LogFormatter.format_enhanced_confluence_score_table(
        symbol=symbol,
        confluence_score=confluence_score,
        components=components,
        results=results,
        weights=weights,
        reliability=1.0
    )
    print(enhanced_table)
except Exception as e:
    print(f"Error generating enhanced table: {e}") 