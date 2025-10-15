"""
Test Enhanced Confluence Replacement

Validates that the enhanced confluence calculation is working correctly
in the actual codebase after replacement.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class TestEnhancedConfluenceReplacement:
    """Test that enhanced confluence works correctly."""

    def test_import_confluence_analyzer(self):
        """Test that ConfluenceAnalyzer can be imported."""
        try:
            from src.core.analysis.confluence import ConfluenceAnalyzer
            print("✅ ConfluenceAnalyzer imports successfully")
            assert ConfluenceAnalyzer is not None
        except ImportError as e:
            pytest.fail(f"Failed to import ConfluenceAnalyzer: {e}")

    def test_enhanced_confluence_method_exists(self):
        """Test that _calculate_enhanced_confluence method exists."""
        from src.core.analysis.confluence import ConfluenceAnalyzer

        # Check method exists
        assert hasattr(ConfluenceAnalyzer, '_calculate_enhanced_confluence'), \
            "ConfluenceAnalyzer should have _calculate_enhanced_confluence method"

        print("✅ _calculate_enhanced_confluence method exists")

    def test_backward_compatible_wrapper_exists(self):
        """Test that backward compatible wrapper still exists."""
        from src.core.analysis.confluence import ConfluenceAnalyzer

        # Check method exists
        assert hasattr(ConfluenceAnalyzer, '_calculate_confluence_score'), \
            "ConfluenceAnalyzer should have _calculate_confluence_score method"

        print("✅ _calculate_confluence_score wrapper exists")

    def test_enhanced_confluence_returns_expected_structure(self):
        """Test that enhanced confluence returns expected dict structure."""
        from src.core.analysis.confluence import ConfluenceAnalyzer

        # Create minimal config for testing
        config = {
            'confluence': {
                'weights': {
                    'components': {
                        'orderbook': 0.25,
                        'cvd': 0.20,
                        'volume_delta': 0.15,
                        'technical': 0.11,
                        'obv': 0.15,
                        'open_interest': 0.14
                    }
                }
            }
        }

        analyzer = ConfluenceAnalyzer(config)

        # Test scores (strong bullish)
        test_scores = {
            'orderbook': 80.0,
            'cvd': 85.0,
            'volume_delta': 82.0,
            'technical': 78.0,
            'obv': 83.0,
            'open_interest': 81.0
        }

        # Call enhanced method
        result = analyzer._calculate_enhanced_confluence(test_scores)

        # Verify structure
        assert isinstance(result, dict), "Result should be a dict"
        assert 'score' in result, "Result should contain 'score'"
        assert 'score_raw' in result, "Result should contain 'score_raw'"
        assert 'consensus' in result, "Result should contain 'consensus'"
        assert 'confidence' in result, "Result should contain 'confidence'"
        assert 'disagreement' in result, "Result should contain 'disagreement'"

        # Verify types
        assert isinstance(result['score'], float), "'score' should be float"
        assert isinstance(result['consensus'], float), "'consensus' should be float"
        assert isinstance(result['confidence'], float), "'confidence' should be float"

        # Verify ranges
        assert 0 <= result['score'] <= 100, "'score' should be 0-100"
        assert 0 <= result['consensus'] <= 1, "'consensus' should be 0-1"
        assert 0 <= result['confidence'] <= 1, "'confidence' should be 0-1"
        assert result['disagreement'] >= 0, "'disagreement' should be >= 0"

        print(f"✅ Enhanced confluence returns correct structure:")
        print(f"   Score: {result['score']:.2f}")
        print(f"   Consensus: {result['consensus']:.3f}")
        print(f"   Confidence: {result['confidence']:.3f}")
        print(f"   Disagreement: {result['disagreement']:.4f}")

    def test_backward_compatible_wrapper_works(self):
        """Test that backward compatible wrapper returns float score."""
        from src.core.analysis.confluence import ConfluenceAnalyzer

        # Create minimal config for testing
        config = {
            'confluence': {
                'weights': {
                    'components': {
                        'orderbook': 0.25,
                        'cvd': 0.20,
                        'volume_delta': 0.15,
                        'technical': 0.11,
                        'obv': 0.15,
                        'open_interest': 0.14
                    }
                }
            }
        }

        analyzer = ConfluenceAnalyzer(config)

        # Test scores
        test_scores = {
            'orderbook': 80.0,
            'cvd': 85.0,
            'volume_delta': 82.0,
            'technical': 78.0,
            'obv': 83.0,
            'open_interest': 81.0
        }

        # Call wrapper method
        score = analyzer._calculate_confluence_score(test_scores)

        # Verify it returns a float
        assert isinstance(score, float), "Score should be a float"
        assert 0 <= score <= 100, "Score should be 0-100"

        print(f"✅ Backward compatible wrapper works: score = {score:.2f}")

    def test_enhanced_vs_wrapper_consistency(self):
        """Test that wrapper returns same score as enhanced method."""
        from src.core.analysis.confluence import ConfluenceAnalyzer

        # Create minimal config for testing
        config = {
            'confluence': {
                'weights': {
                    'components': {
                        'orderbook': 0.25,
                        'cvd': 0.20,
                        'volume_delta': 0.15,
                        'technical': 0.11,
                        'obv': 0.15,
                        'open_interest': 0.14
                    }
                }
            }
        }

        analyzer = ConfluenceAnalyzer(config)

        # Test scores
        test_scores = {
            'orderbook': 80.0,
            'cvd': 85.0,
            'volume_delta': 82.0,
            'technical': 78.0,
            'obv': 83.0,
            'open_interest': 81.0
        }

        # Call both methods
        enhanced_result = analyzer._calculate_enhanced_confluence(test_scores)
        wrapper_score = analyzer._calculate_confluence_score(test_scores)

        # They should match
        assert abs(enhanced_result['score'] - wrapper_score) < 0.01, \
            f"Enhanced score ({enhanced_result['score']}) should match wrapper ({wrapper_score})"

        print(f"✅ Enhanced and wrapper are consistent:")
        print(f"   Enhanced score: {enhanced_result['score']:.2f}")
        print(f"   Wrapper score: {wrapper_score:.2f}")
        print(f"   Difference: {abs(enhanced_result['score'] - wrapper_score):.6f}")

    def test_low_confidence_detection(self):
        """Test that low confidence signals are properly detected."""
        from src.core.analysis.confluence import ConfluenceAnalyzer

        # Create minimal config for testing
        config = {
            'confluence': {
                'weights': {
                    'components': {
                        'orderbook': 0.25,
                        'cvd': 0.20,
                        'volume_delta': 0.15,
                        'technical': 0.11,
                        'obv': 0.15,
                        'open_interest': 0.14
                    }
                }
            }
        }

        analyzer = ConfluenceAnalyzer(config)

        # Test scores with high disagreement (mixed signals)
        mixed_scores = {
            'orderbook': 80.0,  # Bullish
            'cvd': 20.0,        # Bearish
            'volume_delta': 75.0,  # Bullish
            'technical': 30.0,  # Bearish
            'obv': 60.0,        # Neutral
            'open_interest': 25.0  # Bearish
        }

        # Call enhanced method
        result = analyzer._calculate_enhanced_confluence(mixed_scores)

        # Verify low confidence is detected
        assert result['confidence'] < 0.5, \
            f"Mixed signals should have low confidence, got {result['confidence']:.3f}"
        assert result['disagreement'] > 0.1, \
            f"Mixed signals should have high disagreement, got {result['disagreement']:.3f}"

        print(f"✅ Low confidence detection works:")
        print(f"   Confidence: {result['confidence']:.3f} (< 0.5 ✓)")
        print(f"   Disagreement: {result['disagreement']:.3f} (> 0.1 ✓)")
        print(f"   Consensus: {result['consensus']:.3f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
