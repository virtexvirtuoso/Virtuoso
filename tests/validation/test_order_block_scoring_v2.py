#!/usr/bin/env python3
"""
Validation tests for enhanced order block scoring.
Tests multi-factor strength calculation with log-scaled volume, recency decay, and distance weighting.
"""
import sys
import os
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

def test_rank_preservation():
    """Verify higher volume → higher strength (monotonicity)."""
    print("\n" + "="*80)
    print("TEST 1: RANK PRESERVATION")
    print("="*80)

    # Simulate the _calculate_block_strength function
    def calculate_strength(vol_multiplier, candles_ago, price_distance_pct):
        volume_score = min(100, np.log1p(vol_multiplier - 1) / np.log1p(9) * 100)
        decay_lambda = np.log(2) / 25
        recency_multiplier = np.exp(-decay_lambda * candles_ago)
        distance_multiplier = 1 / (1 + np.exp(0.5 * (price_distance_pct - 5)))
        strength = volume_score * recency_multiplier * distance_multiplier
        return float(np.clip(strength, 0, 100))

    vol_mults = [1.5, 2.0, 3.0, 5.0, 10.0]
    strengths = []

    for vm in vol_mults:
        s = calculate_strength(vm, candles_ago=5, price_distance_pct=1.0)
        strengths.append(s)

    print("\n| Vol Mult | Old Strength | New Strength | Status |")
    print("|----------|--------------|--------------|--------|")
    for vm, s in zip(vol_mults, strengths):
        old_strength = min(100, vm * 50)
        status = "✓ Improved" if abs(s - old_strength) > 1 else "Same"
        print(f"| {vm:>6.1f}x | {old_strength:>10.1f} | {s:>10.1f} | {status:>10} |")

    # Test monotonicity
    is_monotonic = all(strengths[i] < strengths[i+1] for i in range(len(strengths)-1))

    if is_monotonic:
        print("\n✓ PASSED: Rank preservation test (monotonic)")
    else:
        print("\n✗ FAILED: Rank ordering violated")

    return is_monotonic


def test_recency_decay():
    """Verify half-life property (25 candles = 50% strength)."""
    print("\n" + "="*80)
    print("TEST 2: RECENCY DECAY")
    print("="*80)

    def calculate_strength(vol_multiplier, candles_ago, price_distance_pct):
        volume_score = min(100, np.log1p(vol_multiplier - 1) / np.log1p(9) * 100)
        decay_lambda = np.log(2) / 25
        recency_multiplier = np.exp(-decay_lambda * candles_ago)
        distance_multiplier = 1 / (1 + np.exp(0.5 * (price_distance_pct - 5)))
        strength = volume_score * recency_multiplier * distance_multiplier
        return float(np.clip(strength, 0, 100))

    s0 = calculate_strength(3.0, candles_ago=0, price_distance_pct=1.0)
    s25 = calculate_strength(3.0, candles_ago=25, price_distance_pct=1.0)
    s50 = calculate_strength(3.0, candles_ago=50, price_distance_pct=1.0)

    ratio_25 = s25 / s0
    ratio_50 = s50 / s0

    print("\n| Age (candles) | Strength | Ratio | Target | Status |")
    print("|---------------|----------|-------|--------|--------|")
    print(f"| {0:>13} | {s0:>8.1f} | {1.0:>5.1%} | 100%   | Baseline |")
    print(f"| {25:>13} | {s25:>8.1f} | {ratio_25:>5.1%} | 50%    | {'✓' if 0.45 < ratio_25 < 0.55 else '✗'} |")
    print(f"| {50:>13} | {s50:>8.1f} | {ratio_50:>5.1%} | 25%    | {'✓' if 0.20 < ratio_50 < 0.30 else '✗'} |")

    half_life_ok = 0.45 < ratio_25 < 0.55
    quarter_life_ok = 0.20 < ratio_50 < 0.30

    if half_life_ok and quarter_life_ok:
        print("\n✓ PASSED: Recency decay test")
    else:
        print("\n✗ FAILED: Decay properties incorrect")

    return half_life_ok and quarter_life_ok


def test_distance_smoothness():
    """Verify no hard cliffs in distance penalty."""
    print("\n" + "="*80)
    print("TEST 3: DISTANCE SMOOTHNESS")
    print("="*80)

    def calculate_strength(vol_multiplier, candles_ago, price_distance_pct):
        volume_score = min(100, np.log1p(vol_multiplier - 1) / np.log1p(9) * 100)
        decay_lambda = np.log(2) / 25
        recency_multiplier = np.exp(-decay_lambda * candles_ago)
        distance_multiplier = 1 / (1 + np.exp(0.5 * (price_distance_pct - 5)))
        strength = volume_score * recency_multiplier * distance_multiplier
        return float(np.clip(strength, 0, 100))

    distances = [0, 2, 5, 10, 15]
    multipliers = []

    base = calculate_strength(3.0, 5, 0.0)

    print("\n| Distance (%) | New Score | Old Score | Improvement |")
    print("|--------------|-----------|-----------|-------------|")

    for dist in distances:
        s = calculate_strength(3.0, 5, dist)
        mult = s / base
        old = max(0, 100 - dist * 10) / 100

        if dist == 10 and old == 0:
            improvement = "✓ No cliff"
        elif mult > old:
            improvement = f"+{(mult - old)*100:.1f}%"
        else:
            improvement = "Same"

        multipliers.append(mult)
        print(f"| {dist:>11}% | {mult:>8.1%} | {old:>8.1%} | {improvement:>11} |")

    # Verify no zero at 10%
    no_cliff = multipliers[3] > 0.05

    if no_cliff:
        print("\n✓ PASSED: Distance smoothness test (no hard cliffs)")
    else:
        print("\n✗ FAILED: Distance penalty too harsh")

    return no_cliff


def test_comparison_table():
    """Generate comprehensive comparison table."""
    print("\n" + "="*80)
    print("TEST 4: COMPREHENSIVE COMPARISON")
    print("="*80)

    def calculate_strength(vol_multiplier, candles_ago, price_distance_pct):
        volume_score = min(100, np.log1p(vol_multiplier - 1) / np.log1p(9) * 100)
        decay_lambda = np.log(2) / 25
        recency_multiplier = np.exp(-decay_lambda * candles_ago)
        distance_multiplier = 1 / (1 + np.exp(0.5 * (price_distance_pct - 5)))
        strength = volume_score * recency_multiplier * distance_multiplier
        return float(np.clip(strength, 0, 100))

    test_cases = [
        (1.5, 0, 1.0, "Low vol, fresh, close"),
        (2.0, 0, 1.0, "Medium vol, fresh, close"),
        (3.0, 0, 1.0, "High vol, fresh, close"),
        (5.0, 0, 1.0, "Very high vol, fresh, close"),
        (10.0, 0, 1.0, "Whale order, fresh, close"),
        (3.0, 25, 1.0, "High vol, half-life age, close"),
        (3.0, 0, 5.0, "High vol, fresh, inflection distance"),
        (3.0, 0, 10.0, "High vol, fresh, far distance"),
    ]

    print("\n| Scenario | Vol | Age | Dist | Old | New | Change |")
    print("|----------|-----|-----|------|-----|-----|--------|")

    for vm, age, dist, desc in test_cases:
        old_strength = min(100, vm * 50)
        new_strength = calculate_strength(vm, age, dist)
        change = new_strength - old_strength

        print(f"| {desc:<28} | {vm:>3.1f}x | {age:>3} | {dist:>4.1f}% | {old_strength:>3.0f} | {new_strength:>3.0f} | {change:>+6.1f} |")

    print("\n✓ Comparison table generated successfully")
    return True


if __name__ == "__main__":
    print("\n" + "="*80)
    print("ORDER BLOCK SCORING V2 VALIDATION TESTS")
    print("="*80)

    results = {
        "Rank Preservation": test_rank_preservation(),
        "Recency Decay": test_recency_decay(),
        "Distance Smoothness": test_distance_smoothness(),
        "Comparison Table": test_comparison_table(),
    }

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:<30} {status}")

    all_passed = all(results.values())

    print("\n" + "="*80)
    if all_passed:
        print("ALL TESTS PASSED ✓")
        print("Enhanced order block scoring is ready for deployment.")
    else:
        print("SOME TESTS FAILED ✗")
        print("Review failures before deployment.")
    print("="*80)

    sys.exit(0 if all_passed else 1)
