"""
Unit Test for Quality Metrics Calculation Logic

Tests the core mathematical formulas without full system initialization.

Author: QA Validation Agent
Date: 2025-10-10
"""

import sys
import numpy as np
from typing import Dict

# Direct test of the calculation logic


def calculate_quality_metrics(scores: Dict[str, float], weights: Dict[str, float] = None) -> Dict[str, float]:
    """
    Replicate the quality metrics calculation from confluence.py.

    This is a standalone implementation for testing purposes.
    """
    try:
        # Default equal weights if not provided
        if weights is None:
            weights = {k: 1/len(scores) for k in scores.keys()}

        # Normalize signals to [-1, 1] range
        normalized_signals = {
            name: np.clip((score - 50) / 50, -1, 1)
            for name, score in scores.items()
        }

        # Calculate weighted average (direction)
        weighted_sum = sum(
            weights.get(name, 0) * normalized_signals[name]
            for name in scores.keys()
        )

        # Calculate signal variance (disagreement)
        signal_values = list(normalized_signals.values())
        signal_variance = np.var(signal_values) if len(signal_values) > 1 else 0.0

        # Consensus score: low variance = high consensus
        consensus = np.exp(-signal_variance * 2)

        # Combine direction and consensus for confidence
        confidence = abs(weighted_sum) * consensus

        return {
            'score_raw': float(weighted_sum),
            'score': float(np.clip(weighted_sum * 50 + 50, 0, 100)),
            'consensus': float(consensus),
            'confidence': float(confidence),
            'disagreement': float(signal_variance)
        }

    except Exception as e:
        return {
            'score_raw': 0.0,
            'score': 50.0,
            'consensus': 0.0,
            'confidence': 0.0,
            'disagreement': 0.0
        }


def run_tests():
    """Run unit tests for quality metrics calculation."""
    print("=" * 80)
    print("QUALITY METRICS CALCULATION - UNIT TESTS")
    print("=" * 80)

    passed = 0
    failed = 0

    # Test 1: Structure and types
    print("\n[TEST 1] Structure and Types")
    scores_test1 = {
        'technical': 80,
        'volume': 82,
        'orderflow': 85,
        'orderbook': 78,
        'sentiment': 83,
        'price_structure': 80
    }

    result1 = calculate_quality_metrics(scores_test1)
    required_keys = {'score', 'score_raw', 'consensus', 'confidence', 'disagreement'}

    if required_keys.issubset(set(result1.keys())):
        print("  ✓ Has all required keys")
        passed += 1
    else:
        print(f"  ✗ Missing keys: {required_keys - set(result1.keys())}")
        failed += 1

    if all(isinstance(result1[k], float) for k in required_keys):
        print("  ✓ All values are floats")
        passed += 1
    else:
        print("  ✗ Some values are not floats")
        failed += 1

    if 0 <= result1['score'] <= 100:
        print(f"  ✓ Score in range [0,100]: {result1['score']:.2f}")
        passed += 1
    else:
        print(f"  ✗ Score out of range: {result1['score']:.2f}")
        failed += 1

    if -1 <= result1['score_raw'] <= 1:
        print(f"  ✓ Raw score in range [-1,1]: {result1['score_raw']:.3f}")
        passed += 1
    else:
        print(f"  ✗ Raw score out of range: {result1['score_raw']:.3f}")
        failed += 1

    if 0 <= result1['consensus'] <= 1:
        print(f"  ✓ Consensus in range [0,1]: {result1['consensus']:.3f}")
        passed += 1
    else:
        print(f"  ✗ Consensus out of range: {result1['consensus']:.3f}")
        failed += 1

    if 0 <= result1['confidence'] <= 1:
        print(f"  ✓ Confidence in range [0,1]: {result1['confidence']:.3f}")
        passed += 1
    else:
        print(f"  ✗ Confidence out of range: {result1['confidence']:.3f}")
        failed += 1

    if result1['disagreement'] >= 0:
        print(f"  ✓ Disagreement non-negative: {result1['disagreement']:.4f}")
        passed += 1
    else:
        print(f"  ✗ Disagreement negative: {result1['disagreement']:.4f}")
        failed += 1

    # Test 2: Consensus calculation
    print("\n[TEST 2] Consensus Calculation")

    # All same scores
    scores_same = {k: 80 for k in ['technical', 'volume', 'orderflow', 'orderbook', 'sentiment', 'price_structure']}
    result_same = calculate_quality_metrics(scores_same)

    # Manual calculation
    normalized = [(80 - 50) / 50] * 6  # All 0.6
    variance = np.var(normalized)  # Should be 0
    expected_consensus = np.exp(-variance * 2)  # Should be 1.0

    if abs(result_same['consensus'] - expected_consensus) < 0.01:
        print(f"  ✓ Same scores consensus correct: {result_same['consensus']:.3f} ≈ {expected_consensus:.3f}")
        passed += 1
    else:
        print(f"  ✗ Same scores consensus wrong: {result_same['consensus']:.3f} != {expected_consensus:.3f}")
        failed += 1

    # Mixed scores
    scores_mixed = {
        'technical': 80,
        'volume': 20,
        'orderflow': 75,
        'orderbook': 30,
        'sentiment': 55,
        'price_structure': 60
    }
    result_mixed = calculate_quality_metrics(scores_mixed)

    # Manual calculation
    normalized_mixed = [(s - 50) / 50 for s in scores_mixed.values()]
    variance_mixed = np.var(normalized_mixed)
    expected_consensus_mixed = np.exp(-variance_mixed * 2)

    if abs(result_mixed['consensus'] - expected_consensus_mixed) < 0.01:
        print(f"  ✓ Mixed scores consensus correct: {result_mixed['consensus']:.3f} ≈ {expected_consensus_mixed:.3f}")
        passed += 1
    else:
        print(f"  ✗ Mixed scores consensus wrong: {result_mixed['consensus']:.3f} != {expected_consensus_mixed:.3f}")
        failed += 1

    if result_same['consensus'] > result_mixed['consensus']:
        print(f"  ✓ Low variance has higher consensus than high variance")
        passed += 1
    else:
        print(f"  ✗ Consensus ordering incorrect")
        failed += 1

    # Test 3: Confidence calculation
    print("\n[TEST 3] Confidence Calculation")

    scores_strong = {
        'technical': 85,
        'volume': 83,
        'orderflow': 88,
        'orderbook': 82,
        'sentiment': 86,
        'price_structure': 84
    }
    result_strong = calculate_quality_metrics(scores_strong)

    # Manual calculation
    weights = {k: 1/6 for k in scores_strong.keys()}
    normalized = {k: (v - 50) / 50 for k, v in scores_strong.items()}
    weighted_sum = sum(weights[k] * normalized[k] for k in scores_strong.keys())
    variance = np.var(list(normalized.values()))
    consensus = np.exp(-variance * 2)
    expected_confidence = abs(weighted_sum) * consensus

    if abs(result_strong['confidence'] - expected_confidence) < 0.01:
        print(f"  ✓ Strong signal confidence correct: {result_strong['confidence']:.3f} ≈ {expected_confidence:.3f}")
        passed += 1
    else:
        print(f"  ✗ Strong signal confidence wrong: {result_strong['confidence']:.3f} != {expected_confidence:.3f}")
        failed += 1

    # Near neutral
    scores_neutral = {k: 51 + i for i, k in enumerate(['technical', 'volume', 'orderflow', 'orderbook', 'sentiment', 'price_structure'])}
    result_neutral = calculate_quality_metrics(scores_neutral)

    if result_strong['confidence'] > result_neutral['confidence']:
        print(f"  ✓ Strong signal has higher confidence than neutral: {result_strong['confidence']:.3f} > {result_neutral['confidence']:.3f}")
        passed += 1
    else:
        print(f"  ✗ Confidence ordering incorrect")
        failed += 1

    # Test 4: Disagreement calculation
    print("\n[TEST 4] Disagreement Calculation")

    scores_disagreement = {
        'technical': 95,
        'volume': 10,
        'orderflow': 90,
        'orderbook': 15,
        'sentiment': 85,
        'price_structure': 12
    }
    result_disagreement = calculate_quality_metrics(scores_disagreement)

    # Manual calculation
    normalized_dis = [(s - 50) / 50 for s in scores_disagreement.values()]
    expected_disagreement = np.var(normalized_dis)

    if abs(result_disagreement['disagreement'] - expected_disagreement) < 0.01:
        print(f"  ✓ Disagreement calculation correct: {result_disagreement['disagreement']:.4f} ≈ {expected_disagreement:.4f}")
        passed += 1
    else:
        print(f"  ✗ Disagreement calculation wrong: {result_disagreement['disagreement']:.4f} != {expected_disagreement:.4f}")
        failed += 1

    if result_disagreement['disagreement'] > 0.3:
        print(f"  ✓ Extreme disagreement detected: {result_disagreement['disagreement']:.4f} > 0.3")
        passed += 1
    else:
        print(f"  ✗ Disagreement too low: {result_disagreement['disagreement']:.4f}")
        failed += 1

    # Test 5: Edge cases
    print("\n[TEST 5] Edge Cases")

    # Single indicator
    scores_single = {'technical': 75}
    result_single = calculate_quality_metrics(scores_single)
    if 0 <= result_single['score'] <= 100:
        print(f"  ✓ Single indicator works: score={result_single['score']:.2f}")
        passed += 1
    else:
        print(f"  ✗ Single indicator fails")
        failed += 1

    # All zeros
    scores_zero = {k: 0 for k in ['technical', 'volume', 'orderflow', 'orderbook', 'sentiment', 'price_structure']}
    result_zero = calculate_quality_metrics(scores_zero)
    if result_zero['score'] == 0:
        print(f"  ✓ All zeros gives score 0: {result_zero['score']:.2f}")
        passed += 1
    else:
        print(f"  ✗ All zeros wrong score: {result_zero['score']:.2f}")
        failed += 1

    # All 100s
    scores_max = {k: 100 for k in ['technical', 'volume', 'orderflow', 'orderbook', 'sentiment', 'price_structure']}
    result_max = calculate_quality_metrics(scores_max)
    if result_max['score'] == 100:
        print(f"  ✓ All 100s gives score 100: {result_max['score']:.2f}")
        passed += 1
    else:
        print(f"  ✗ All 100s wrong score: {result_max['score']:.2f}")
        failed += 1

    # Test 6: Scenario Tests
    print("\n[TEST 6] Test Scenarios")

    # Scenario 1: Strong Bullish
    print("  Scenario 1: Strong Bullish (High Quality)")
    scores_s1 = {'technical': 80, 'volume': 82, 'orderflow': 85, 'orderbook': 78, 'sentiment': 83, 'price_structure': 81}
    result_s1 = calculate_quality_metrics(scores_s1)

    high_consensus_s1 = result_s1['consensus'] > 0.8
    high_confidence_s1 = result_s1['confidence'] > 0.5
    low_disagreement_s1 = result_s1['disagreement'] < 0.1
    would_pass_s1 = high_confidence_s1 and low_disagreement_s1

    print(f"    Consensus: {result_s1['consensus']:.3f} (>0.8: {high_consensus_s1})")
    print(f"    Confidence: {result_s1['confidence']:.3f} (>0.5: {high_confidence_s1})")
    print(f"    Disagreement: {result_s1['disagreement']:.4f} (<0.1: {low_disagreement_s1})")
    print(f"    Would pass filter: {would_pass_s1}")

    if high_consensus_s1 and high_confidence_s1 and low_disagreement_s1:
        print("    ✓ Strong bullish scenario correct")
        passed += 1
    else:
        print("    ✗ Strong bullish scenario failed")
        failed += 1

    # Scenario 2: Mixed Signals
    print("  Scenario 2: Mixed Signals (Low Quality)")
    scores_s2 = {'technical': 80, 'volume': 20, 'orderflow': 75, 'orderbook': 30, 'sentiment': 55, 'price_structure': 60}
    result_s2 = calculate_quality_metrics(scores_s2)

    low_consensus_s2 = result_s2['consensus'] < 0.7
    would_filter_s2 = result_s2['confidence'] < 0.5 or result_s2['disagreement'] > 0.3

    print(f"    Consensus: {result_s2['consensus']:.3f} (<0.7: {low_consensus_s2})")
    print(f"    Confidence: {result_s2['confidence']:.3f}")
    print(f"    Disagreement: {result_s2['disagreement']:.4f}")
    print(f"    Would be filtered: {would_filter_s2}")

    if would_filter_s2:
        print("    ✓ Mixed signals would be filtered")
        passed += 1
    else:
        print("    ✗ Mixed signals should be filtered")
        failed += 1

    # Scenario 3: Near Neutral
    print("  Scenario 3: Near Neutral (Low Confidence)")
    scores_s3 = {'technical': 52, 'volume': 51, 'orderflow': 53, 'orderbook': 50, 'sentiment': 52, 'price_structure': 51}
    result_s3 = calculate_quality_metrics(scores_s3)

    high_consensus_s3 = result_s3['consensus'] > 0.8
    low_confidence_s3 = result_s3['confidence'] < 0.3
    would_filter_s3 = low_confidence_s3

    print(f"    Consensus: {result_s3['consensus']:.3f} (>0.8: {high_consensus_s3})")
    print(f"    Confidence: {result_s3['confidence']:.3f} (<0.3: {low_confidence_s3})")
    print(f"    Disagreement: {result_s3['disagreement']:.4f}")
    print(f"    Would be filtered: {would_filter_s3}")

    if high_consensus_s3 and low_confidence_s3:
        print("    ✓ Near neutral scenario correct")
        passed += 1
    else:
        print("    ✗ Near neutral scenario failed")
        failed += 1

    # Scenario 4: Extreme Disagreement
    print("  Scenario 4: Extreme Disagreement")
    scores_s4 = {'technical': 95, 'volume': 10, 'orderflow': 90, 'orderbook': 15, 'sentiment': 85, 'price_structure': 12}
    result_s4 = calculate_quality_metrics(scores_s4)

    high_disagreement_s4 = result_s4['disagreement'] > 0.3
    would_filter_s4 = high_disagreement_s4

    print(f"    Consensus: {result_s4['consensus']:.3f}")
    print(f"    Confidence: {result_s4['confidence']:.3f}")
    print(f"    Disagreement: {result_s4['disagreement']:.4f} (>0.3: {high_disagreement_s4})")
    print(f"    Would be filtered: {would_filter_s4}")

    if high_disagreement_s4:
        print("    ✓ Extreme disagreement detected")
        passed += 1
    else:
        print("    ✗ Extreme disagreement not detected")
        failed += 1

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    total = passed + failed
    pass_rate = (passed / total * 100) if total > 0 else 0
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Pass Rate: {pass_rate:.2f}%")
    print(f"Overall: {'PASS' if failed == 0 else 'FAIL'}")

    return failed == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
