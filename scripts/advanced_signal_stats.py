#!/usr/bin/env python3
"""
Advanced Statistical Tests for Trading Signals
Hypothesis testing and statistical validation
"""

import sqlite3
import pandas as pd
import numpy as np
import json
from scipy import stats
from datetime import datetime

DB_PATH = 'data/virtuoso.db'

def load_data():
    """Load and prepare data."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query('SELECT * FROM trading_signals', conn)
    conn.close()

    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['components'] = df['components'].apply(lambda x: json.loads(x) if pd.notna(x) and x else {})

    # Extract component scores
    component_names = ['technical', 'volume', 'orderbook', 'orderflow', 'sentiment', 'price_structure']
    for comp in component_names:
        def extract_score(components):
            if not components:
                return np.nan
            value = components.get(comp, np.nan)
            if isinstance(value, dict):
                return value.get('score', np.nan)
            elif isinstance(value, (int, float)):
                return value
            return np.nan

        df[f'comp_{comp}'] = df['components'].apply(extract_score)

    return df

def test_long_vs_short_scores(df):
    """Test if LONG signals have significantly different scores than SHORT signals."""
    print("\n" + "="*80)
    print("HYPOTHESIS TEST 1: LONG vs SHORT Signal Quality")
    print("="*80)

    long_scores = df[df['signal_type'] == 'LONG']['confluence_score']
    short_scores = df[df['signal_type'] == 'SHORT']['confluence_score']

    # Two-sample t-test
    t_stat, p_value = stats.ttest_ind(long_scores, short_scores)

    # Mann-Whitney U test (non-parametric alternative)
    u_stat, u_pvalue = stats.mannwhitneyu(long_scores, short_scores, alternative='two-sided')

    print(f"\nLONG signals (n={len(long_scores)}): mean={long_scores.mean():.2f}, std={long_scores.std():.2f}")
    print(f"SHORT signals (n={len(short_scores)}): mean={short_scores.mean():.2f}, std={short_scores.std():.2f}")
    print(f"\nDifference in means: {long_scores.mean() - short_scores.mean():.2f}")

    print(f"\nT-test:")
    print(f"  t-statistic = {t_stat:.4f}")
    print(f"  p-value = {p_value:.6f}")
    print(f"  Result: {'SIGNIFICANT' if p_value < 0.05 else 'NOT SIGNIFICANT'} at α=0.05")

    print(f"\nMann-Whitney U test (non-parametric):")
    print(f"  U-statistic = {u_stat:.4f}")
    print(f"  p-value = {u_pvalue:.6f}")
    print(f"  Result: {'SIGNIFICANT' if u_pvalue < 0.05 else 'NOT SIGNIFICANT'} at α=0.05")

    # Effect size (Cohen's d)
    pooled_std = np.sqrt(((len(long_scores)-1)*long_scores.std()**2 +
                          (len(short_scores)-1)*short_scores.std()**2) /
                         (len(long_scores) + len(short_scores) - 2))
    cohens_d = (long_scores.mean() - short_scores.mean()) / pooled_std

    print(f"\nEffect size (Cohen's d): {cohens_d:.4f}")
    if abs(cohens_d) < 0.2:
        effect = "negligible"
    elif abs(cohens_d) < 0.5:
        effect = "small"
    elif abs(cohens_d) < 0.8:
        effect = "medium"
    else:
        effect = "large"
    print(f"  Interpretation: {effect} effect")

def test_day_of_week_effect(df):
    """Test if day of week affects signal quality."""
    print("\n" + "="*80)
    print("HYPOTHESIS TEST 2: Day of Week Effect on Signal Quality")
    print("="*80)

    df['day_of_week'] = df['datetime'].dt.day_name()

    # ANOVA test
    groups = [group['confluence_score'].values for name, group in df.groupby('day_of_week')]
    f_stat, p_value = stats.f_oneway(*groups)

    print(f"\nOne-way ANOVA:")
    print(f"  F-statistic = {f_stat:.4f}")
    print(f"  p-value = {p_value:.6f}")
    print(f"  Result: {'SIGNIFICANT' if p_value < 0.05 else 'NOT SIGNIFICANT'} at α=0.05")

    # Show mean scores by day
    print("\nMean scores by day of week:")
    day_stats = df.groupby('day_of_week')['confluence_score'].agg(['count', 'mean', 'std'])
    print(day_stats.round(2))

def test_score_threshold_performance(df):
    """Analyze optimal score thresholds."""
    print("\n" + "="*80)
    print("ANALYSIS: Optimal Score Threshold Determination")
    print("="*80)

    thresholds = range(60, 85, 5)

    print("\nThreshold Analysis:")
    print(f"{'Threshold':<12} {'Count':<8} {'% of Total':<12} {'Avg Score':<12} {'Std':<8}")
    print("-" * 60)

    for threshold in thresholds:
        filtered = df[df['confluence_score'] >= threshold]
        count = len(filtered)
        pct = count / len(df) * 100
        avg = filtered['confluence_score'].mean()
        std = filtered['confluence_score'].std()

        print(f">= {threshold:<9} {count:<8} {pct:<12.1f} {avg:<12.2f} {std:<8.2f}")

def test_component_independence(df):
    """Test if components are independent (correlation analysis)."""
    print("\n" + "="*80)
    print("HYPOTHESIS TEST 3: Component Independence")
    print("="*80)

    component_names = ['technical', 'volume', 'orderbook', 'orderflow', 'sentiment', 'price_structure']
    comp_cols = [f'comp_{c}' for c in component_names]

    comp_df = df[comp_cols].dropna()

    print(f"\nAnalyzing {len(comp_df)} complete component records")
    print("\nSignificant correlations (|r| > 0.3):")

    for i, c1 in enumerate(component_names):
        for j, c2 in enumerate(component_names):
            if i < j:
                # Use only rows where both components are present
                valid_data = df[[f'comp_{c1}', f'comp_{c2}']].dropna()
                if len(valid_data) > 2:
                    r, p = stats.pearsonr(valid_data[f'comp_{c1}'], valid_data[f'comp_{c2}'])
                    if abs(r) > 0.3 and p < 0.05:
                        print(f"  {c1:15s} <-> {c2:15s}: r = {r:6.3f}, p = {p:.6f}")

def test_temporal_autocorrelation(df):
    """Test if signal scores are autocorrelated over time."""
    print("\n" + "="*80)
    print("HYPOTHESIS TEST 4: Temporal Autocorrelation")
    print("="*80)

    df_sorted = df.sort_values('datetime')
    scores = df_sorted['confluence_score'].values

    # Lag-1 autocorrelation
    if len(scores) > 1:
        lag1_corr = np.corrcoef(scores[:-1], scores[1:])[0, 1]

        print(f"\nLag-1 autocorrelation: {lag1_corr:.4f}")

        if abs(lag1_corr) > 0.2:
            print(f"  Interpretation: Moderate autocorrelation detected")
            print(f"  Implication: Signal quality may be influenced by previous signals")
        else:
            print(f"  Interpretation: Weak/no autocorrelation")
            print(f"  Implication: Signals appear independent over time")

def test_symbol_quality_differences(df):
    """Test if different symbols have significantly different signal quality."""
    print("\n" + "="*80)
    print("HYPOTHESIS TEST 5: Symbol Quality Differences")
    print("="*80)

    # Focus on symbols with sufficient samples
    symbol_counts = df['symbol'].value_counts()
    top_symbols = symbol_counts[symbol_counts >= 10].index

    print(f"\nAnalyzing {len(top_symbols)} symbols with >= 10 signals")

    groups = [group['confluence_score'].values for symbol, group in df.groupby('symbol')
              if symbol in top_symbols]

    f_stat, p_value = stats.f_oneway(*groups)

    print(f"\nOne-way ANOVA:")
    print(f"  F-statistic = {f_stat:.4f}")
    print(f"  p-value = {p_value:.6f}")
    print(f"  Result: {'SIGNIFICANT' if p_value < 0.05 else 'NOT SIGNIFICANT'} at α=0.05")

    # Pairwise comparisons for top symbols
    print("\nTop symbols quality comparison:")
    symbol_stats = df[df['symbol'].isin(top_symbols)].groupby('symbol')['confluence_score'].agg(['count', 'mean', 'std'])
    symbol_stats = symbol_stats.sort_values('mean', ascending=False)
    print(symbol_stats.round(2))

def normality_tests(df):
    """Test if confluence scores follow normal distribution."""
    print("\n" + "="*80)
    print("DISTRIBUTION ANALYSIS: Normality Tests")
    print("="*80)

    scores = df['confluence_score'].dropna()

    # Shapiro-Wilk test
    if len(scores) < 5000:  # Shapiro-Wilk works best for smaller samples
        shapiro_stat, shapiro_p = stats.shapiro(scores)
        print(f"\nShapiro-Wilk test:")
        print(f"  W-statistic = {shapiro_stat:.4f}")
        print(f"  p-value = {shapiro_p:.6f}")
        print(f"  Result: Distribution is {'NOT NORMAL' if shapiro_p < 0.05 else 'NORMAL'} at α=0.05")

    # Kolmogorov-Smirnov test
    ks_stat, ks_p = stats.kstest(scores, 'norm', args=(scores.mean(), scores.std()))
    print(f"\nKolmogorov-Smirnov test:")
    print(f"  KS-statistic = {ks_stat:.4f}")
    print(f"  p-value = {ks_p:.6f}")
    print(f"  Result: Distribution is {'NOT NORMAL' if ks_p < 0.05 else 'NORMAL'} at α=0.05")

    # D'Agostino-Pearson test
    k2_stat, k2_p = stats.normaltest(scores)
    print(f"\nD'Agostino-Pearson test:")
    print(f"  K2-statistic = {k2_stat:.4f}")
    print(f"  p-value = {k2_p:.6f}")
    print(f"  Result: Distribution is {'NOT NORMAL' if k2_p < 0.05 else 'NORMAL'} at α=0.05")

def component_weights_analysis(df):
    """Analyze current component weights vs optimal weights."""
    print("\n" + "="*80)
    print("ANALYSIS: Component Weight Optimization")
    print("="*80)

    component_names = ['technical', 'volume', 'orderbook', 'orderflow', 'sentiment', 'price_structure']
    comp_cols = [f'comp_{c}' for c in component_names]

    # Current weights (assumed equal or from system)
    current_weights = {
        'technical': 0.20,
        'volume': 0.15,
        'orderbook': 0.15,
        'orderflow': 0.20,
        'sentiment': 0.15,
        'price_structure': 0.15
    }

    print("\nCurrent component weights:")
    for comp, weight in current_weights.items():
        print(f"  {comp:20s}: {weight:.2%}")

    # Calculate correlations with confluence score
    print("\nComponent correlations with confluence score:")
    correlations = {}
    for comp in component_names:
        valid_data = df[[f'comp_{comp}', 'confluence_score']].dropna()
        if len(valid_data) > 0:
            r = valid_data[f'comp_{comp}'].corr(valid_data['confluence_score'])
            correlations[comp] = r
            print(f"  {comp:20s}: r = {r:.4f}")

    # Suggested weights based on correlation strength
    print("\nSuggested weights (normalized by correlation strength):")
    total_corr = sum(abs(r) for r in correlations.values())
    suggested_weights = {comp: abs(r) / total_corr for comp, r in correlations.items()}

    for comp, weight in sorted(suggested_weights.items(), key=lambda x: x[1], reverse=True):
        change = weight - current_weights[comp]
        print(f"  {comp:20s}: {weight:.2%} (change: {change:+.2%})")

def main():
    """Run all statistical tests."""
    print("="*80)
    print("  ADVANCED STATISTICAL ANALYSIS OF TRADING SIGNALS")
    print(f"  Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    print("\nLoading data...")
    df = load_data()
    print(f"Loaded {len(df)} trading signals\n")

    # Run all tests
    normality_tests(df)
    test_long_vs_short_scores(df)
    test_day_of_week_effect(df)
    test_score_threshold_performance(df)
    test_component_independence(df)
    test_temporal_autocorrelation(df)
    test_symbol_quality_differences(df)
    component_weights_analysis(df)

    print("\n" + "="*80)
    print("  STATISTICAL ANALYSIS COMPLETE")
    print("="*80)

if __name__ == '__main__':
    main()
