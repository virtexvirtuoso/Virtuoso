"""
Comprehensive QA Validation Test for Quality-Based Signal Filtering System

Tests the quality metrics and confidence-based filtering implementation across:
- confluence.py: Quality metrics calculation
- formatter.py: Quality metrics display
- signal_generator.py: Confidence-based filtering
- quality_metrics_tracker.py: Logging and analytics

Author: QA Validation Agent
Date: 2025-10-10
"""

import sys
import os
import asyncio
import logging
import json
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import numpy as np

# Add project root to path
sys.path.insert(0, '/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

from src.core.analysis.confluence import ConfluenceAnalyzer
from src.core.formatting.formatter import PrettyTableFormatter
from src.signal_generation.signal_generator import SignalGenerator
from src.monitoring.quality_metrics_tracker import QualityMetricsTracker

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QualityFilteringValidator:
    """Comprehensive validator for quality filtering system."""

    def __init__(self):
        """Initialize the validator."""
        self.test_results = []
        self.passed_count = 0
        self.failed_count = 0
        self.temp_dir = None

    def log_test(self, name: str, passed: bool, evidence: Dict[str, Any] = None):
        """Log test result."""
        status = "PASS" if passed else "FAIL"
        self.test_results.append({
            'name': name,
            'status': status,
            'passed': passed,
            'evidence': evidence or {},
            'timestamp': datetime.utcnow().isoformat()
        })

        if passed:
            self.passed_count += 1
            logger.info(f"✓ {name} - PASSED")
        else:
            self.failed_count += 1
            logger.error(f"✗ {name} - FAILED")
            if evidence:
                logger.error(f"  Evidence: {json.dumps(evidence, indent=2)}")

    # =========================================================================
    # TEST SUITE 1: Quality Metrics Calculation (confluence.py)
    # =========================================================================

    def test_quality_metrics_calculation_structure(self):
        """Test that _calculate_confluence_score returns correct dict structure."""
        logger.info("\n=== TEST 1.1: Quality Metrics Calculation Structure ===")

        try:
            # Create minimal config
            config = {'confluence': {'weights': {'components': {}}}}
            analyzer = ConfluenceAnalyzer(config)

            # Test scores
            scores = {
                'technical': 80,
                'volume': 82,
                'orderflow': 85,
                'orderbook': 78,
                'sentiment': 83,
                'price_structure': 80
            }

            result = analyzer._calculate_confluence_score(scores)

            # Verify structure
            required_keys = {'score', 'score_raw', 'consensus', 'confidence', 'disagreement'}
            has_all_keys = required_keys.issubset(set(result.keys()))

            # Verify types
            all_floats = all(isinstance(result[k], float) for k in required_keys)

            # Verify ranges
            score_in_range = 0 <= result['score'] <= 100
            score_raw_in_range = -1 <= result['score_raw'] <= 1
            consensus_in_range = 0 <= result['consensus'] <= 1
            confidence_in_range = 0 <= result['confidence'] <= 1
            disagreement_positive = result['disagreement'] >= 0

            passed = (
                has_all_keys and
                all_floats and
                score_in_range and
                score_raw_in_range and
                consensus_in_range and
                confidence_in_range and
                disagreement_positive
            )

            self.log_test(
                "Quality Metrics Calculation Structure",
                passed,
                {
                    'result': result,
                    'has_all_keys': has_all_keys,
                    'all_floats': all_floats,
                    'score_in_range': score_in_range,
                    'score_raw_in_range': score_raw_in_range,
                    'consensus_in_range': consensus_in_range,
                    'confidence_in_range': confidence_in_range,
                    'disagreement_positive': disagreement_positive
                }
            )

            return passed

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Quality Metrics Calculation Structure", False, {'error': str(e)})
            return False

    def test_consensus_calculation(self):
        """Test consensus calculation: exp(-variance * 2)."""
        logger.info("\n=== TEST 1.2: Consensus Calculation ===")

        try:
            config = {'confluence': {'weights': {'components': {}}}}
            analyzer = ConfluenceAnalyzer(config)

            # Test Case 1: All same scores (should have consensus ~1.0)
            scores_same = {
                'technical': 80,
                'volume': 80,
                'orderflow': 80,
                'orderbook': 80,
                'sentiment': 80,
                'price_structure': 80
            }

            result_same = analyzer._calculate_confluence_score(scores_same)

            # Manual calculation
            normalized = [(80 - 50) / 50] * 6  # All 0.6
            variance = np.var(normalized)  # Should be 0
            expected_consensus = np.exp(-variance * 2)  # Should be 1.0

            consensus_correct_same = abs(result_same['consensus'] - expected_consensus) < 0.01

            # Test Case 2: Mixed scores
            scores_mixed = {
                'technical': 80,
                'volume': 20,
                'orderflow': 75,
                'orderbook': 30,
                'sentiment': 55,
                'price_structure': 60
            }

            result_mixed = analyzer._calculate_confluence_score(scores_mixed)

            # Manual calculation
            normalized_mixed = [(s - 50) / 50 for s in scores_mixed.values()]
            variance_mixed = np.var(normalized_mixed)
            expected_consensus_mixed = np.exp(-variance_mixed * 2)

            consensus_correct_mixed = abs(result_mixed['consensus'] - expected_consensus_mixed) < 0.01

            # Low variance should have higher consensus
            consensus_ordering_correct = result_same['consensus'] > result_mixed['consensus']

            passed = consensus_correct_same and consensus_correct_mixed and consensus_ordering_correct

            self.log_test(
                "Consensus Calculation",
                passed,
                {
                    'same_scores': {
                        'calculated': result_same['consensus'],
                        'expected': expected_consensus,
                        'correct': consensus_correct_same
                    },
                    'mixed_scores': {
                        'calculated': result_mixed['consensus'],
                        'expected': expected_consensus_mixed,
                        'correct': consensus_correct_mixed,
                        'variance': variance_mixed
                    },
                    'ordering_correct': consensus_ordering_correct
                }
            )

            return passed

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Consensus Calculation", False, {'error': str(e)})
            return False

    def test_confidence_calculation(self):
        """Test confidence calculation: |weighted_sum| * consensus."""
        logger.info("\n=== TEST 1.3: Confidence Calculation ===")

        try:
            config = {'confluence': {'weights': {'components': {}}}}
            analyzer = ConfluenceAnalyzer(config)

            # Strong bullish (high scores, high agreement)
            scores_strong = {
                'technical': 85,
                'volume': 83,
                'orderflow': 88,
                'orderbook': 82,
                'sentiment': 86,
                'price_structure': 84
            }

            result_strong = analyzer._calculate_confluence_score(scores_strong)

            # Manual calculation
            weights = analyzer.weights
            normalized = {k: (v - 50) / 50 for k, v in scores_strong.items()}
            weighted_sum = sum(weights.get(k, 1/6) * normalized[k] for k in scores_strong.keys())
            variance = np.var(list(normalized.values()))
            consensus = np.exp(-variance * 2)
            expected_confidence = abs(weighted_sum) * consensus

            confidence_correct = abs(result_strong['confidence'] - expected_confidence) < 0.01

            # Near neutral (low confidence expected)
            scores_neutral = {
                'technical': 52,
                'volume': 51,
                'orderflow': 53,
                'orderbook': 50,
                'sentiment': 52,
                'price_structure': 51
            }

            result_neutral = analyzer._calculate_confluence_score(scores_neutral)

            # Strong signal should have higher confidence than neutral
            confidence_ordering_correct = result_strong['confidence'] > result_neutral['confidence']

            passed = confidence_correct and confidence_ordering_correct

            self.log_test(
                "Confidence Calculation",
                passed,
                {
                    'strong_signal': {
                        'calculated': result_strong['confidence'],
                        'expected': expected_confidence,
                        'correct': confidence_correct
                    },
                    'neutral_signal': {
                        'calculated': result_neutral['confidence']
                    },
                    'ordering_correct': confidence_ordering_correct
                }
            )

            return passed

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Confidence Calculation", False, {'error': str(e)})
            return False

    def test_disagreement_calculation(self):
        """Test disagreement calculation: variance(normalized_signals)."""
        logger.info("\n=== TEST 1.4: Disagreement Calculation ===")

        try:
            config = {'confluence': {'weights': {'components': {}}}}
            analyzer = ConfluenceAnalyzer(config)

            # Extreme disagreement
            scores_disagreement = {
                'technical': 95,
                'volume': 10,
                'orderflow': 90,
                'orderbook': 15,
                'sentiment': 85,
                'price_structure': 12
            }

            result_disagreement = analyzer._calculate_confluence_score(scores_disagreement)

            # Manual calculation
            normalized = [(s - 50) / 50 for s in scores_disagreement.values()]
            expected_disagreement = np.var(normalized)

            disagreement_correct = abs(result_disagreement['disagreement'] - expected_disagreement) < 0.01

            # High disagreement case
            high_disagreement = result_disagreement['disagreement'] > 0.3

            passed = disagreement_correct and high_disagreement

            self.log_test(
                "Disagreement Calculation",
                passed,
                {
                    'calculated': result_disagreement['disagreement'],
                    'expected': expected_disagreement,
                    'correct': disagreement_correct,
                    'high_disagreement': high_disagreement
                }
            )

            return passed

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Disagreement Calculation", False, {'error': str(e)})
            return False

    def test_edge_cases(self):
        """Test edge cases (single indicator, extreme values)."""
        logger.info("\n=== TEST 1.5: Edge Cases ===")

        try:
            config = {'confluence': {'weights': {'components': {}}}}
            analyzer = ConfluenceAnalyzer(config)

            # Single indicator (should not crash)
            scores_single = {'technical': 75}
            result_single = analyzer._calculate_confluence_score(scores_single)
            single_works = 'score' in result_single and 0 <= result_single['score'] <= 100

            # All zeros
            scores_zero = {k: 0 for k in ['technical', 'volume', 'orderflow', 'orderbook', 'sentiment', 'price_structure']}
            result_zero = analyzer._calculate_confluence_score(scores_zero)
            zero_works = result_zero['score'] == 0

            # All 100s
            scores_max = {k: 100 for k in ['technical', 'volume', 'orderflow', 'orderbook', 'sentiment', 'price_structure']}
            result_max = analyzer._calculate_confluence_score(scores_max)
            max_works = result_max['score'] == 100

            passed = single_works and zero_works and max_works

            self.log_test(
                "Edge Cases",
                passed,
                {
                    'single_indicator': {'works': single_works, 'result': result_single},
                    'all_zeros': {'works': zero_works, 'result': result_zero},
                    'all_100s': {'works': max_works, 'result': result_max}
                }
            )

            return passed

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Edge Cases", False, {'error': str(e)})
            return False

    # =========================================================================
    # TEST SUITE 2: Quality Metrics Display (formatter.py)
    # =========================================================================

    def test_quality_metrics_display(self):
        """Test that quality metrics appear in formatted output."""
        logger.info("\n=== TEST 2.1: Quality Metrics Display ===")

        try:
            symbol = "BTC/USDT"
            confluence_score = 75.5
            components = {
                'technical': 80,
                'volume': 75,
                'orderflow': 78,
                'orderbook': 72,
                'sentiment': 76,
                'price_structure': 74
            }
            results = {}
            reliability = 0.85
            consensus = 0.92
            confidence = 0.68
            disagreement = 0.05

            formatted = PrettyTableFormatter.format_enhanced_confluence_score_table(
                symbol=symbol,
                confluence_score=confluence_score,
                components=components,
                results=results,
                reliability=reliability,
                consensus=consensus,
                confidence=confidence,
                disagreement=disagreement
            )

            # Check for quality metrics section
            has_quality_section = "Quality Metrics:" in formatted
            has_consensus = "Consensus:" in formatted
            has_confidence = "Confidence:" in formatted
            has_disagreement = "Disagreement:" in formatted

            # Check for actual values
            has_consensus_value = f"{consensus:.3f}" in formatted
            has_confidence_value = f"{confidence:.3f}" in formatted
            has_disagreement_value = f"{disagreement:.4f}" in formatted

            passed = (
                has_quality_section and
                has_consensus and has_confidence and has_disagreement and
                has_consensus_value and has_confidence_value and has_disagreement_value
            )

            self.log_test(
                "Quality Metrics Display",
                passed,
                {
                    'has_quality_section': has_quality_section,
                    'has_consensus': has_consensus,
                    'has_confidence': has_confidence,
                    'has_disagreement': has_disagreement,
                    'formatted_output': formatted[:500]  # First 500 chars
                }
            )

            return passed

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Quality Metrics Display", False, {'error': str(e)})
            return False

    def test_color_coding_logic(self):
        """Test color coding and threshold checks in formatted output."""
        logger.info("\n=== TEST 2.2: Color Coding Logic ===")

        try:
            symbol = "BTC/USDT"

            # Test high quality (green checkmarks expected)
            formatted_high = PrettyTableFormatter.format_enhanced_confluence_score_table(
                symbol=symbol,
                confluence_score=80,
                components={},
                results={},
                reliability=0.9,
                consensus=0.85,  # > 0.8
                confidence=0.65,  # > 0.5
                disagreement=0.08  # < 0.1
            )

            high_quality_indicators = formatted_high.count("✅") >= 3  # Should have 3 green checks

            # Test low quality (red X's expected)
            formatted_low = PrettyTableFormatter.format_enhanced_confluence_score_table(
                symbol=symbol,
                confluence_score=50,
                components={},
                results={},
                reliability=0.4,
                consensus=0.55,  # <= 0.6
                confidence=0.25,  # <= 0.3
                disagreement=0.35  # >= 0.3
            )

            low_quality_indicators = formatted_low.count("❌") >= 3  # Should have 3 red X's

            passed = high_quality_indicators and low_quality_indicators

            self.log_test(
                "Color Coding Logic",
                passed,
                {
                    'high_quality_has_green': high_quality_indicators,
                    'low_quality_has_red': low_quality_indicators
                }
            )

            return passed

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Color Coding Logic", False, {'error': str(e)})
            return False

    def test_none_values_handling(self):
        """Test graceful handling of None values in formatter."""
        logger.info("\n=== TEST 2.3: None Values Handling ===")

        try:
            symbol = "BTC/USDT"

            # Test with all None
            formatted_none = PrettyTableFormatter.format_enhanced_confluence_score_table(
                symbol=symbol,
                confluence_score=75,
                components={},
                results={},
                reliability=0.8,
                consensus=None,
                confidence=None,
                disagreement=None
            )

            # Should not have Quality Metrics section
            no_quality_section = "Quality Metrics:" not in formatted_none

            # Test with partial None
            formatted_partial = PrettyTableFormatter.format_enhanced_confluence_score_table(
                symbol=symbol,
                confluence_score=75,
                components={},
                results={},
                reliability=0.8,
                consensus=0.85,
                confidence=None,
                disagreement=None
            )

            # Should have quality section but only consensus
            has_quality_section = "Quality Metrics:" in formatted_partial
            has_consensus = "Consensus:" in formatted_partial
            no_confidence = "Confidence:" not in formatted_partial or "N/A" in formatted_partial

            passed = no_quality_section and has_quality_section and has_consensus

            self.log_test(
                "None Values Handling",
                passed,
                {
                    'no_quality_section_when_all_none': no_quality_section,
                    'has_section_with_partial': has_quality_section,
                    'shows_available_metrics': has_consensus
                }
            )

            return passed

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("None Values Handling", False, {'error': str(e)})
            return False

    # =========================================================================
    # TEST SUITE 3: Confidence-Based Filtering (signal_generator.py)
    # =========================================================================

    async def test_low_confidence_filter(self):
        """Test that signals with confidence < 0.3 are filtered."""
        logger.info("\n=== TEST 3.1: Low Confidence Filter ===")

        try:
            # Create signal generator
            config = {
                'signal_thresholds': {
                    'buy_threshold': 60,
                    'sell_threshold': 40
                }
            }
            signal_gen = SignalGenerator(config)

            # Create indicators with low confidence
            indicators = {
                'symbol': 'BTC/USDT',
                'confluence_score': 75,  # High score
                'consensus': 0.95,  # High consensus
                'confidence': 0.25,  # LOW CONFIDENCE - should be filtered
                'disagreement': 0.05,
                'components': {
                    'technical': 75,
                    'volume': 75,
                    'orderflow': 75,
                    'orderbook': 75,
                    'sentiment': 75,
                    'price_structure': 75
                }
            }

            result = await signal_gen.generate_signal(indicators)

            # Should return None (filtered)
            filtered = result is None

            self.log_test(
                "Low Confidence Filter",
                filtered,
                {
                    'confidence': indicators['confidence'],
                    'threshold': 0.3,
                    'result': result,
                    'filtered': filtered
                }
            )

            return filtered

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Low Confidence Filter", False, {'error': str(e)})
            return False

    async def test_high_disagreement_filter(self):
        """Test that signals with disagreement > 0.3 are filtered."""
        logger.info("\n=== TEST 3.2: High Disagreement Filter ===")

        try:
            config = {
                'signal_thresholds': {
                    'buy_threshold': 60,
                    'sell_threshold': 40
                }
            }
            signal_gen = SignalGenerator(config)

            # Create indicators with high disagreement
            indicators = {
                'symbol': 'BTC/USDT',
                'confluence_score': 75,
                'consensus': 0.5,
                'confidence': 0.65,  # High confidence
                'disagreement': 0.35,  # HIGH DISAGREEMENT - should be filtered
                'components': {
                    'technical': 75,
                    'volume': 75,
                    'orderflow': 75,
                    'orderbook': 75,
                    'sentiment': 75,
                    'price_structure': 75
                }
            }

            result = await signal_gen.generate_signal(indicators)

            # Should return None (filtered)
            filtered = result is None

            self.log_test(
                "High Disagreement Filter",
                filtered,
                {
                    'disagreement': indicators['disagreement'],
                    'threshold': 0.3,
                    'result': result,
                    'filtered': filtered
                }
            )

            return filtered

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("High Disagreement Filter", False, {'error': str(e)})
            return False

    async def test_signals_pass_when_quality_good(self):
        """Test that high-quality signals pass through."""
        logger.info("\n=== TEST 3.3: Signals Pass When Quality Good ===")

        try:
            config = {
                'signal_thresholds': {
                    'buy_threshold': 60,
                    'sell_threshold': 40
                }
            }
            signal_gen = SignalGenerator(config)

            # Create high-quality indicators
            indicators = {
                'symbol': 'BTC/USDT',
                'confluence_score': 75,
                'consensus': 0.9,  # High
                'confidence': 0.7,  # High
                'disagreement': 0.08,  # Low
                'components': {
                    'technical': 75,
                    'volume': 75,
                    'orderflow': 75,
                    'orderbook': 75,
                    'sentiment': 75,
                    'price_structure': 75
                }
            }

            result = await signal_gen.generate_signal(indicators)

            # Should NOT be None (passed)
            passed_filter = result is not None

            self.log_test(
                "Signals Pass When Quality Good",
                passed_filter,
                {
                    'confidence': indicators['confidence'],
                    'disagreement': indicators['disagreement'],
                    'result_type': type(result).__name__ if result else 'None',
                    'passed': passed_filter
                }
            )

            return passed_filter

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Signals Pass When Quality Good", False, {'error': str(e)})
            return False

    async def test_no_filtering_when_metrics_none(self):
        """Test that filtering is skipped when quality metrics are None."""
        logger.info("\n=== TEST 3.4: No Filtering When Metrics None ===")

        try:
            config = {
                'signal_thresholds': {
                    'buy_threshold': 60,
                    'sell_threshold': 40
                }
            }
            signal_gen = SignalGenerator(config)

            # Create indicators WITHOUT quality metrics
            indicators = {
                'symbol': 'BTC/USDT',
                'confluence_score': 75,
                'components': {
                    'technical': 75,
                    'volume': 75,
                    'orderflow': 75,
                    'orderbook': 75,
                    'sentiment': 75,
                    'price_structure': 75
                }
                # No consensus, confidence, disagreement
            }

            result = await signal_gen.generate_signal(indicators)

            # Should not be filtered (no metrics to filter on)
            not_filtered = result is not None

            self.log_test(
                "No Filtering When Metrics None",
                not_filtered,
                {
                    'has_consensus': 'consensus' in indicators,
                    'has_confidence': 'confidence' in indicators,
                    'has_disagreement': 'disagreement' in indicators,
                    'result_type': type(result).__name__ if result else 'None',
                    'not_filtered': not_filtered
                }
            )

            return not_filtered

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("No Filtering When Metrics None", False, {'error': str(e)})
            return False

    # =========================================================================
    # TEST SUITE 4: Quality Metrics Tracker
    # =========================================================================

    def test_tracker_initialization(self):
        """Test quality metrics tracker initialization."""
        logger.info("\n=== TEST 4.1: Tracker Initialization ===")

        try:
            # Create temp directory for logs
            self.temp_dir = tempfile.mkdtemp()

            tracker = QualityMetricsTracker(log_dir=self.temp_dir)

            # Check log directory created
            log_dir_exists = Path(self.temp_dir).exists()

            # Check attributes
            has_cache = hasattr(tracker, 'metrics_cache')
            has_log_file = hasattr(tracker, 'current_log_file')

            passed = log_dir_exists and has_cache and has_log_file

            self.log_test(
                "Tracker Initialization",
                passed,
                {
                    'log_dir_exists': log_dir_exists,
                    'has_cache': has_cache,
                    'has_log_file': has_log_file,
                    'log_dir': self.temp_dir
                }
            )

            return passed

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Tracker Initialization", False, {'error': str(e)})
            return False

    def test_tracker_logging(self):
        """Test logging quality metrics to file."""
        logger.info("\n=== TEST 4.2: Tracker Logging ===")

        try:
            if not self.temp_dir:
                self.temp_dir = tempfile.mkdtemp()

            tracker = QualityMetricsTracker(log_dir=self.temp_dir)

            # Log a metric
            tracker.log_quality_metrics(
                symbol='BTC/USDT',
                confluence_score=75.5,
                consensus=0.85,
                confidence=0.68,
                disagreement=0.12,
                signal_type='BUY',
                signal_filtered=False
            )

            # Check log file exists
            log_files = list(Path(self.temp_dir).glob('quality_metrics_*.jsonl'))
            log_file_exists = len(log_files) > 0

            # Read log file
            if log_file_exists:
                with open(log_files[0], 'r') as f:
                    lines = f.readlines()

                has_entry = len(lines) > 0

                if has_entry:
                    entry = json.loads(lines[0])
                    correct_structure = all(k in entry for k in ['timestamp', 'symbol', 'quality_metrics', 'signal'])
                    correct_values = (
                        entry['symbol'] == 'BTC/USDT' and
                        entry['confluence_score'] == 75.5 and
                        entry['quality_metrics']['consensus'] == 0.85
                    )
                else:
                    correct_structure = False
                    correct_values = False
            else:
                has_entry = False
                correct_structure = False
                correct_values = False

            passed = log_file_exists and has_entry and correct_structure and correct_values

            self.log_test(
                "Tracker Logging",
                passed,
                {
                    'log_file_exists': log_file_exists,
                    'has_entry': has_entry,
                    'correct_structure': correct_structure,
                    'correct_values': correct_values
                }
            )

            return passed

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Tracker Logging", False, {'error': str(e)})
            return False

    def test_tracker_statistics(self):
        """Test statistical methods."""
        logger.info("\n=== TEST 4.3: Tracker Statistics ===")

        try:
            if not self.temp_dir:
                self.temp_dir = tempfile.mkdtemp()

            tracker = QualityMetricsTracker(log_dir=self.temp_dir)

            # Log multiple metrics
            for i in range(10):
                tracker.log_quality_metrics(
                    symbol='BTC/USDT',
                    confluence_score=70 + i,
                    consensus=0.8 + i * 0.01,
                    confidence=0.6 + i * 0.01,
                    disagreement=0.1 + i * 0.01,
                    signal_filtered=i % 2 == 0  # Filter every other
                )

            # Get statistics
            stats = tracker.get_statistics(hours=24)

            # Verify structure
            has_required_keys = all(k in stats for k in ['total_signals', 'signals_filtered', 'confidence', 'consensus', 'disagreement'])

            # Verify values
            correct_total = stats['total_signals'] == 10
            correct_filtered = stats['signals_filtered'] == 5

            # Verify confidence stats
            has_confidence_stats = all(k in stats['confidence'] for k in ['mean', 'median', 'min', 'max'])

            passed = has_required_keys and correct_total and correct_filtered and has_confidence_stats

            self.log_test(
                "Tracker Statistics",
                passed,
                {
                    'has_required_keys': has_required_keys,
                    'correct_total': correct_total,
                    'correct_filtered': correct_filtered,
                    'has_confidence_stats': has_confidence_stats,
                    'stats': stats
                }
            )

            return passed

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Tracker Statistics", False, {'error': str(e)})
            return False

    # =========================================================================
    # TEST SUITE 5: Test Data Scenarios
    # =========================================================================

    async def test_scenario_strong_bullish(self):
        """Test Scenario 1: Strong Bullish (High Quality)."""
        logger.info("\n=== TEST 5.1: Strong Bullish Scenario ===")

        try:
            config = {'confluence': {'weights': {'components': {}}}}
            analyzer = ConfluenceAnalyzer(config)

            scores = {
                'technical': 80,
                'volume': 82,
                'orderflow': 85,
                'orderbook': 78,
                'sentiment': 83,
                'price_structure': 81
            }

            result = analyzer._calculate_confluence_score(scores)

            # Expected: High consensus, high confidence, pass filtering
            high_consensus = result['consensus'] > 0.8
            high_confidence = result['confidence'] > 0.5
            low_disagreement = result['disagreement'] < 0.1
            would_pass_filter = high_confidence and low_disagreement

            passed = high_consensus and high_confidence and low_disagreement and would_pass_filter

            self.log_test(
                "Scenario: Strong Bullish",
                passed,
                {
                    'scores': scores,
                    'result': result,
                    'high_consensus': high_consensus,
                    'high_confidence': high_confidence,
                    'low_disagreement': low_disagreement,
                    'would_pass_filter': would_pass_filter
                }
            )

            return passed

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Scenario: Strong Bullish", False, {'error': str(e)})
            return False

    async def test_scenario_mixed_signals(self):
        """Test Scenario 2: Mixed Signals (Low Quality)."""
        logger.info("\n=== TEST 5.2: Mixed Signals Scenario ===")

        try:
            config = {'confluence': {'weights': {'components': {}}}}
            analyzer = ConfluenceAnalyzer(config)

            scores = {
                'technical': 80,
                'volume': 20,
                'orderflow': 75,
                'orderbook': 30,
                'sentiment': 55,
                'price_structure': 60
            }

            result = analyzer._calculate_confluence_score(scores)

            # Expected: Low consensus, low confidence, FILTERED
            low_consensus = result['consensus'] < 0.7
            low_confidence = result['confidence'] < 0.5
            would_be_filtered = low_confidence or result['disagreement'] > 0.3

            passed = low_consensus and would_be_filtered

            self.log_test(
                "Scenario: Mixed Signals",
                passed,
                {
                    'scores': scores,
                    'result': result,
                    'low_consensus': low_consensus,
                    'low_confidence': low_confidence,
                    'would_be_filtered': would_be_filtered
                }
            )

            return passed

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Scenario: Mixed Signals", False, {'error': str(e)})
            return False

    async def test_scenario_near_neutral(self):
        """Test Scenario 3: Near Neutral (Low Confidence)."""
        logger.info("\n=== TEST 5.3: Near Neutral Scenario ===")

        try:
            config = {'confluence': {'weights': {'components': {}}}}
            analyzer = ConfluenceAnalyzer(config)

            scores = {
                'technical': 52,
                'volume': 51,
                'orderflow': 53,
                'orderbook': 50,
                'sentiment': 52,
                'price_structure': 51
            }

            result = analyzer._calculate_confluence_score(scores)

            # Expected: High consensus (scores agree), low confidence (near neutral), FILTERED
            high_consensus = result['consensus'] > 0.8
            low_confidence = result['confidence'] < 0.3
            would_be_filtered = low_confidence

            passed = high_consensus and low_confidence and would_be_filtered

            self.log_test(
                "Scenario: Near Neutral",
                passed,
                {
                    'scores': scores,
                    'result': result,
                    'high_consensus': high_consensus,
                    'low_confidence': low_confidence,
                    'would_be_filtered': would_be_filtered
                }
            )

            return passed

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Scenario: Near Neutral", False, {'error': str(e)})
            return False

    async def test_scenario_extreme_disagreement(self):
        """Test Scenario 4: Extreme Disagreement."""
        logger.info("\n=== TEST 5.4: Extreme Disagreement Scenario ===")

        try:
            config = {'confluence': {'weights': {'components': {}}}}
            analyzer = ConfluenceAnalyzer(config)

            scores = {
                'technical': 95,
                'volume': 10,
                'orderflow': 90,
                'orderbook': 15,
                'sentiment': 85,
                'price_structure': 12
            }

            result = analyzer._calculate_confluence_score(scores)

            # Expected: High disagreement, FILTERED
            high_disagreement = result['disagreement'] > 0.3
            would_be_filtered = high_disagreement

            passed = high_disagreement and would_be_filtered

            self.log_test(
                "Scenario: Extreme Disagreement",
                passed,
                {
                    'scores': scores,
                    'result': result,
                    'high_disagreement': high_disagreement,
                    'disagreement_value': result['disagreement'],
                    'would_be_filtered': would_be_filtered
                }
            )

            return passed

        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            self.log_test("Scenario: Extreme Disagreement", False, {'error': str(e)})
            return False

    # =========================================================================
    # Report Generation
    # =========================================================================

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        total_tests = self.passed_count + self.failed_count
        pass_rate = (self.passed_count / total_tests * 100) if total_tests > 0 else 0

        overall_decision = "PASS" if self.failed_count == 0 else "FAIL"

        report = {
            'validation_metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'commit_sha': 'fd025b3, f4302a1, 2cf4185',
                'environment': 'local',
                'validator': 'QualityFilteringValidator'
            },
            'summary': {
                'total_tests': total_tests,
                'passed': self.passed_count,
                'failed': self.failed_count,
                'pass_rate': round(pass_rate, 2),
                'overall_decision': overall_decision
            },
            'test_results': self.test_results,
            'criteria_assessment': {
                'quality_metrics_calculation': {
                    'status': self._get_suite_status('TEST 1'),
                    'tests': [t for t in self.test_results if 'Calculation' in t['name'] or 'Edge Cases' in t['name']]
                },
                'quality_metrics_display': {
                    'status': self._get_suite_status('TEST 2'),
                    'tests': [t for t in self.test_results if 'Display' in t['name'] or 'Color' in t['name'] or 'None' in t['name']]
                },
                'confidence_based_filtering': {
                    'status': self._get_suite_status('TEST 3'),
                    'tests': [t for t in self.test_results if 'Filter' in t['name'] or 'Pass' in t['name']]
                },
                'quality_metrics_tracker': {
                    'status': self._get_suite_status('TEST 4'),
                    'tests': [t for t in self.test_results if 'Tracker' in t['name']]
                },
                'test_scenarios': {
                    'status': self._get_suite_status('TEST 5'),
                    'tests': [t for t in self.test_results if 'Scenario' in t['name']]
                }
            },
            'recommendations': self._generate_recommendations()
        }

        return report

    def _get_suite_status(self, suite_prefix: str) -> str:
        """Get status for a test suite."""
        suite_tests = [t for t in self.test_results if suite_prefix in t['name']]
        if not suite_tests:
            return 'NOT_RUN'

        all_passed = all(t['passed'] for t in suite_tests)
        return 'PASS' if all_passed else 'FAIL'

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        if self.failed_count == 0:
            recommendations.append("✅ All tests passed - System is production ready")
            recommendations.append("✅ Safe to deploy to VPS")
        else:
            recommendations.append("❌ Fix failing tests before deployment")

            # Check specific failures
            failed_tests = [t for t in self.test_results if not t['passed']]
            for test in failed_tests:
                recommendations.append(f"⚠️ Address failure in: {test['name']}")

        return recommendations

    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up temp directory: {self.temp_dir}")


async def main():
    """Run all validation tests."""
    logger.info("=" * 80)
    logger.info("QUALITY-BASED SIGNAL FILTERING SYSTEM - COMPREHENSIVE VALIDATION")
    logger.info("=" * 80)

    validator = QualityFilteringValidator()

    try:
        # TEST SUITE 1: Quality Metrics Calculation
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUITE 1: Quality Metrics Calculation (confluence.py)")
        logger.info("=" * 80)
        validator.test_quality_metrics_calculation_structure()
        validator.test_consensus_calculation()
        validator.test_confidence_calculation()
        validator.test_disagreement_calculation()
        validator.test_edge_cases()

        # TEST SUITE 2: Quality Metrics Display
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUITE 2: Quality Metrics Display (formatter.py)")
        logger.info("=" * 80)
        validator.test_quality_metrics_display()
        validator.test_color_coding_logic()
        validator.test_none_values_handling()

        # TEST SUITE 3: Confidence-Based Filtering
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUITE 3: Confidence-Based Filtering (signal_generator.py)")
        logger.info("=" * 80)
        await validator.test_low_confidence_filter()
        await validator.test_high_disagreement_filter()
        await validator.test_signals_pass_when_quality_good()
        await validator.test_no_filtering_when_metrics_none()

        # TEST SUITE 4: Quality Metrics Tracker
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUITE 4: Quality Metrics Tracker")
        logger.info("=" * 80)
        validator.test_tracker_initialization()
        validator.test_tracker_logging()
        validator.test_tracker_statistics()

        # TEST SUITE 5: Test Data Scenarios
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUITE 5: Test Data Scenarios")
        logger.info("=" * 80)
        await validator.test_scenario_strong_bullish()
        await validator.test_scenario_mixed_signals()
        await validator.test_scenario_near_neutral()
        await validator.test_scenario_extreme_disagreement()

        # Generate report
        logger.info("\n" + "=" * 80)
        logger.info("GENERATING VALIDATION REPORT")
        logger.info("=" * 80)
        report = validator.generate_report()

        # Save report to file
        report_path = '/Users/ffv_macmini/Desktop/Virtuoso_ccxt/QUALITY_FILTERING_VALIDATION_REPORT.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"\n📄 Full report saved to: {report_path}")

        # Print summary
        logger.info("\n" + "=" * 80)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Tests: {report['summary']['total_tests']}")
        logger.info(f"Passed: {report['summary']['passed']}")
        logger.info(f"Failed: {report['summary']['failed']}")
        logger.info(f"Pass Rate: {report['summary']['pass_rate']}%")
        logger.info(f"Overall Decision: {report['summary']['overall_decision']}")

        logger.info("\n" + "=" * 80)
        logger.info("RECOMMENDATIONS")
        logger.info("=" * 80)
        for rec in report['recommendations']:
            logger.info(rec)

        return report

    finally:
        validator.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
