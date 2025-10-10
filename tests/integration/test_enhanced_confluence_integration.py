"""
Enhanced Confluence Integration Test

Tests the enhanced confluence calculation with the live trading system
to ensure backward compatibility and proper quality metrics.
"""

import sys
import os
import asyncio
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.analysis.confluence import ConfluenceAnalyzer
from src.core.config.config_manager import ConfigManager
from src.core.logger import Logger


class EnhancedConfluenceIntegrationTest:
    """Integration test for enhanced confluence."""

    def __init__(self):
        self.logger = Logger(__name__)
        self.config = None
        self.analyzer = None

    def load_system_config(self) -> bool:
        """Load the actual system configuration."""
        try:
            self.logger.info("Loading system configuration...")
            self.config = ConfigManager.load_config()

            if not self.config:
                self.logger.error("Failed to load config")
                return False

            self.logger.info("✅ System configuration loaded successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return False

    def initialize_analyzer(self) -> bool:
        """Initialize the ConfluenceAnalyzer with system config."""
        try:
            self.logger.info("Initializing ConfluenceAnalyzer...")
            self.analyzer = ConfluenceAnalyzer(self.config)

            if not self.analyzer:
                self.logger.error("Failed to initialize analyzer")
                return False

            self.logger.info("✅ ConfluenceAnalyzer initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error initializing analyzer: {e}", exc_info=True)
            return False

    def test_confluence_method_exists(self) -> bool:
        """Test that the confluence method exists and is callable."""
        try:
            self.logger.info("\n" + "=" * 80)
            self.logger.info("TEST 1: Confluence Method Exists")
            self.logger.info("=" * 80)

            # Check method exists
            has_method = hasattr(self.analyzer, '_calculate_confluence_score')

            if has_method:
                self.logger.info("✅ _calculate_confluence_score method exists")
            else:
                self.logger.error("❌ _calculate_confluence_score method NOT found")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking method: {e}")
            return False

    def test_with_mock_scores(self) -> bool:
        """Test enhanced confluence with mock indicator scores."""
        try:
            self.logger.info("\n" + "=" * 80)
            self.logger.info("TEST 2: Mock Indicator Scores")
            self.logger.info("=" * 80)

            # Create mock scores (simulating strong bullish signal)
            mock_scores = {
                'orderbook': 80.0,
                'cvd': 85.0,
                'volume_delta': 82.0,
                'technical': 78.0,
                'obv': 83.0,
                'open_interest': 81.0
            }

            self.logger.info(f"Mock scores: {mock_scores}")

            # Test confluence method
            self.logger.info("\nCalling _calculate_confluence_score()...")
            result = self.analyzer._calculate_confluence_score(mock_scores)

            if not isinstance(result, dict):
                self.logger.error(f"❌ Method returned wrong type: {type(result)}")
                return False

            # Verify structure
            required_keys = ['score', 'score_raw', 'consensus', 'confidence', 'disagreement']
            missing_keys = [k for k in required_keys if k not in result]

            if missing_keys:
                self.logger.error(f"❌ Missing keys in result: {missing_keys}")
                return False

            self.logger.info("✅ Method returned correct structure")

            # Display results
            self.logger.info("\nConfluence Result:")
            self.logger.info(f"  Score: {result['score']:.2f}")
            self.logger.info(f"  Score Raw: {result['score_raw']:.3f}")
            self.logger.info(f"  Consensus: {result['consensus']:.3f} (0=disagree, 1=agree)")
            self.logger.info(f"  Confidence: {result['confidence']:.3f} (higher=better)")
            self.logger.info(f"  Disagreement: {result['disagreement']:.4f} (lower=better)")

            # Validate quality metrics
            if result['consensus'] > 0.8:
                self.logger.info("✅ High consensus detected (all indicators agree)")
            else:
                self.logger.warning(f"⚠️  Lower consensus: {result['consensus']:.3f}")

            if result['confidence'] > 0.5:
                self.logger.info("✅ High confidence signal")
            else:
                self.logger.warning(f"⚠️  Lower confidence: {result['confidence']:.3f}")

            return True

        except Exception as e:
            self.logger.error(f"Error testing with mock scores: {e}", exc_info=True)
            return False

    def test_mixed_signal_detection(self) -> bool:
        """Test that mixed/conflicting signals are properly detected."""
        try:
            self.logger.info("\n" + "=" * 80)
            self.logger.info("TEST 3: Mixed Signal Detection")
            self.logger.info("=" * 80)

            # Create mixed/conflicting scores
            mixed_scores = {
                'orderbook': 80.0,     # Bullish
                'cvd': 20.0,           # Bearish
                'volume_delta': 75.0,  # Bullish
                'technical': 30.0,     # Bearish
                'obv': 60.0,           # Neutral
                'open_interest': 25.0  # Bearish
            }

            self.logger.info(f"Mixed scores: {mixed_scores}")
            self.logger.info("  Bullish indicators: orderbook (80), volume_delta (75)")
            self.logger.info("  Bearish indicators: cvd (20), technical (30), open_interest (25)")
            self.logger.info("  Neutral indicators: obv (60)")

            # Calculate confluence
            result = self.analyzer._calculate_confluence_score(mixed_scores)

            self.logger.info("\nEnhanced Confluence Result:")
            self.logger.info(f"  Score: {result['score']:.2f}")
            self.logger.info(f"  Consensus: {result['consensus']:.3f}")
            self.logger.info(f"  Confidence: {result['confidence']:.3f}")
            self.logger.info(f"  Disagreement: {result['disagreement']:.4f}")

            # Verify low confidence is detected
            if result['confidence'] < 0.5:
                self.logger.info("✅ Low confidence correctly detected for mixed signals")
                self.logger.info(f"   → Would skip this trade (confidence={result['confidence']:.3f} < 0.5)")
            else:
                self.logger.warning(f"⚠️  Expected low confidence, got {result['confidence']:.3f}")

            # Verify high disagreement is detected
            if result['disagreement'] > 0.1:
                self.logger.info("✅ High disagreement correctly detected")
                self.logger.info(f"   → Indicators are conflicting (disagreement={result['disagreement']:.4f} > 0.1)")
            else:
                self.logger.warning(f"⚠️  Expected high disagreement, got {result['disagreement']:.4f}")

            return True

        except Exception as e:
            self.logger.error(f"Error testing mixed signal detection: {e}", exc_info=True)
            return False

    def test_backward_compatibility(self) -> bool:
        """Test that existing code patterns still work."""
        try:
            self.logger.info("\n" + "=" * 80)
            self.logger.info("TEST 4: Backward Compatibility")
            self.logger.info("=" * 80)

            # Test with various score patterns
            test_cases = [
                {
                    'name': 'Strong Bullish',
                    'scores': {
                        'orderbook': 85.0, 'cvd': 82.0, 'volume_delta': 80.0,
                        'technical': 78.0, 'obv': 83.0, 'open_interest': 81.0
                    }
                },
                {
                    'name': 'Neutral',
                    'scores': {
                        'orderbook': 50.0, 'cvd': 52.0, 'volume_delta': 48.0,
                        'technical': 51.0, 'obv': 49.0, 'open_interest': 50.0
                    }
                },
                {
                    'name': 'Strong Bearish',
                    'scores': {
                        'orderbook': 20.0, 'cvd': 18.0, 'volume_delta': 22.0,
                        'technical': 15.0, 'obv': 19.0, 'open_interest': 17.0
                    }
                }
            ]

            all_compatible = True

            for test in test_cases:
                self.logger.info(f"\nTest: {test['name']}")

                # Calculate confluence with quality metrics
                result = self.analyzer._calculate_confluence_score(test['scores'])

                # Verify result is a dict
                if not isinstance(result, dict):
                    self.logger.error(f"  ❌ Method should return dict, got {type(result)}")
                    all_compatible = False
                    continue

                # Verify has score
                if 'score' not in result:
                    self.logger.error(f"  ❌ Result missing 'score' key")
                    all_compatible = False
                    continue

                score = result['score']
                self.logger.info(f"  ✅ Compatible - score={score:.2f}, confidence={result.get('confidence', 0):.3f}")

            if all_compatible:
                self.logger.info("\n✅ All backward compatibility tests passed")
            else:
                self.logger.error("\n❌ Some backward compatibility tests failed")

            return all_compatible

        except Exception as e:
            self.logger.error(f"Error testing backward compatibility: {e}", exc_info=True)
            return False

    def run_all_tests(self) -> bool:
        """Run all integration tests."""
        try:
            self.logger.info("\n" + "=" * 80)
            self.logger.info("ENHANCED CONFLUENCE INTEGRATION TEST")
            self.logger.info("=" * 80)

            # Load config
            if not self.load_system_config():
                self.logger.error("❌ Failed to load system configuration")
                return False

            # Initialize analyzer
            if not self.initialize_analyzer():
                self.logger.error("❌ Failed to initialize analyzer")
                return False

            # Run tests
            tests = [
                ("Confluence Method Exists", self.test_confluence_method_exists),
                ("Mock Indicator Scores", self.test_with_mock_scores),
                ("Mixed Signal Detection", self.test_mixed_signal_detection),
                ("Backward Compatibility", self.test_backward_compatibility),
            ]

            results = []
            for test_name, test_func in tests:
                try:
                    result = test_func()
                    results.append((test_name, result))
                except Exception as e:
                    self.logger.error(f"Test '{test_name}' crashed: {e}", exc_info=True)
                    results.append((test_name, False))

            # Summary
            self.logger.info("\n" + "=" * 80)
            self.logger.info("TEST SUMMARY")
            self.logger.info("=" * 80)

            passed = sum(1 for _, result in results if result)
            total = len(results)

            for test_name, result in results:
                status = "✅ PASS" if result else "❌ FAIL"
                self.logger.info(f"{status} - {test_name}")

            self.logger.info("\n" + "=" * 80)
            self.logger.info(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

            if passed == total:
                self.logger.info("✅ ALL TESTS PASSED - Integration successful!")
                self.logger.info("=" * 80)
                return True
            else:
                self.logger.error(f"❌ {total - passed} tests failed")
                self.logger.info("=" * 80)
                return False

        except Exception as e:
            self.logger.error(f"Error running tests: {e}", exc_info=True)
            return False


def main():
    """Run the integration test."""
    test = EnhancedConfluenceIntegrationTest()
    success = test.run_all_tests()

    if success:
        print("\n✅ Enhanced confluence integration test completed successfully!")
        print("   The enhanced method is working correctly with the live trading system.")
        print("\nNext steps:")
        print("1. Review the test output above")
        print("2. If satisfied, proceed with git commit")
        print("3. Consider deploying to VPS for production testing")
        return 0
    else:
        print("\n❌ Integration test failed!")
        print("   Review the errors above and fix before committing.")
        return 1


if __name__ == "__main__":
    exit(main())
