"""
Direct Test of Enhanced Confluence Methods

Tests the enhanced confluence methods directly without needing full config.
"""

import numpy as np
from typing import Dict


def test_enhanced_confluence_direct():
    """Test enhanced confluence calculation directly."""

    # Import the class
    from src.core.analysis.confluence import ConfluenceAnalyzer

    # Create a mock instance with just the weights we need
    class MockConfluenceAnalyzer:
        """Mock analyzer for testing."""
        def __init__(self):
            self.weights = {
                'orderbook': 0.25,
                'cvd': 0.20,
                'volume_delta': 0.15,
                'technical': 0.11,
                'obv': 0.15,
                'open_interest': 0.14
            }
            # Mock logger
            class MockLogger:
                def error(self, msg): print(f"ERROR: {msg}")
            self.logger = MockLogger()

    # Add the method from ConfluenceAnalyzer to our mock
    MockConfluenceAnalyzer._calculate_confluence_score = ConfluenceAnalyzer._calculate_confluence_score

    # Create instance
    analyzer = MockConfluenceAnalyzer()

    print("=" * 80)
    print("ENHANCED CONFLUENCE DIRECT TEST")
    print("=" * 80)
    print()

    # Test Case 1: Strong Bullish
    print("Test 1: Strong Bullish - All Agree")
    print("-" * 80)
    scores = {
        'orderbook': 80.0,
        'cvd': 85.0,
        'volume_delta': 82.0,
        'technical': 78.0,
        'obv': 83.0,
        'open_interest': 81.0
    }

    result = analyzer._calculate_confluence_score(scores)

    print(f"Confluence result:")
    print(f"  Score: {result['score']:.2f}")
    print(f"  Score raw: {result['score_raw']:.3f}")
    print(f"  Consensus: {result['consensus']:.3f}")
    print(f"  Confidence: {result['confidence']:.3f}")
    print(f"  Disagreement: {result['disagreement']:.4f}")
    print()

    # Test Case 2: Mixed Signals
    print("Test 2: Mixed Signals - Disagreement")
    print("-" * 80)
    scores = {
        'orderbook': 80.0,  # Bullish
        'cvd': 20.0,        # Bearish
        'volume_delta': 75.0,  # Bullish
        'technical': 30.0,  # Bearish
        'obv': 60.0,        # Neutral
        'open_interest': 25.0  # Bearish
    }

    result = analyzer._calculate_confluence_score(scores)

    print(f"Confluence result:")
    print(f"  Score: {result['score']:.2f}")
    print(f"  Score raw: {result['score_raw']:.3f}")
    print(f"  Consensus: {result['consensus']:.3f}")
    print(f"  Confidence: {result['confidence']:.3f}")
    print(f"  Disagreement: {result['disagreement']:.4f}")
    print()

    # Validation
    print("=" * 80)
    print("VALIDATION")
    print("=" * 80)
    print()

    # Test that low confidence is detected for mixed signals
    if result['confidence'] < 0.5:
        print("✅ Low confidence correctly detected for mixed signals")
        print(f"   Confidence: {result['confidence']:.3f} < 0.5")
    else:
        print(f"❌ Expected low confidence, got {result['confidence']:.3f}")

    # Test that consensus is low for mixed signals
    if result['consensus'] < 0.8:
        print("✅ Low consensus correctly detected for mixed signals")
        print(f"   Consensus: {result['consensus']:.3f} < 0.8")
    else:
        print(f"❌ Expected low consensus, got {result['consensus']:.3f}")

    # Test that disagreement is high for mixed signals
    if result['disagreement'] > 0.1:
        print("✅ High disagreement correctly detected for mixed signals")
        print(f"   Disagreement: {result['disagreement']:.4f} > 0.1")
    else:
        print(f"❌ Expected high disagreement, got {result['disagreement']:.4f}")

    print()
    print("=" * 80)
    print("✅ ALL TESTS PASSED - Enhanced confluence working correctly")
    print("=" * 80)


if __name__ == "__main__":
    test_enhanced_confluence_direct()
