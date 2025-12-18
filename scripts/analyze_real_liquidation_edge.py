#!/usr/bin/env python3
"""
Real Liquidation Alert Predictive Edge Analysis
================================================

Analyzes the 235 actual liquidation cascade alerts from the VPS database
to determine if they have statistically significant predictive power.

This script:
1. Loads real liquidation alerts from virtuoso_vps_backup.db
2. Fetches price data from trading.db or via CCXT
3. Calculates forward returns at 5m, 15m, 1h, 4h, 24h
4. Runs statistical tests for edge detection
5. Segments by symbol, magnitude, and direction

Author: Quantitative Trading Analysis
Date: 2025-12-17
"""

import sqlite3
import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import ttest_1samp, binomtest, mannwhitneyu
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import json
import os
import sys

# Add project root to path
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Optional: CCXT for fetching price data
try:
    import ccxt.async_support as ccxt
    HAS_CCXT = True
except ImportError:
    HAS_CCXT = False

# Optional visualization
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Configuration
ALERTS_DB = str(PROJECT_ROOT / 'data' / 'virtuoso_vps_backup.db')
TRADING_DB = str(PROJECT_ROOT / 'data' / 'trading.db')
OUTPUT_DIR = str(PROJECT_ROOT / 'reports')

# Forward timeframes to analyze (in minutes)
FORWARD_TIMEFRAMES = {
    '5m': 5,
    '15m': 15,
    '1h': 60,
    '4h': 240,
    '24h': 1440
}


def load_liquidation_alerts() -> pd.DataFrame:
    """Load liquidation cascade alerts from database."""
    conn = sqlite3.connect(ALERTS_DB)

    query = """
    SELECT
        alert_id,
        alert_type,
        symbol,
        severity,
        title,
        price,
        timestamp,
        created_at,
        details
    FROM alerts
    WHERE alert_type = 'liquidation_cascade'
    ORDER BY timestamp DESC
    """

    df = pd.read_sql(query, conn)
    conn.close()

    # Parse details JSON
    def parse_details(details_str):
        if pd.isna(details_str) or not details_str:
            return {}
        try:
            return json.loads(details_str)
        except:
            return {}

    df['details_parsed'] = df['details'].apply(parse_details)

    # Extract key fields from details
    df['total_value'] = df['details_parsed'].apply(lambda x: x.get('total_value', 0))
    df['long_value'] = df['details_parsed'].apply(lambda x: x.get('long_value', 0))
    df['short_value'] = df['details_parsed'].apply(lambda x: x.get('short_value', 0))
    df['event_count'] = df['details_parsed'].apply(lambda x: x.get('count', 0))
    df['dominant'] = df['details_parsed'].apply(lambda x: x.get('dominant', 'UNKNOWN'))
    df['rate_per_minute'] = df['details_parsed'].apply(lambda x: x.get('rate_per_minute', 0))
    df['is_global'] = df['details_parsed'].apply(lambda x: x.get('is_global', False))
    df['current_price'] = df['details_parsed'].apply(lambda x: x.get('current_price', 0))

    # Convert timestamp from milliseconds to datetime
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'], unit='ms')

    # Determine liquidation direction for mean-reversion hypothesis
    # LONG liquidations = longs got squeezed = price went DOWN = expect bounce UP
    # SHORT liquidations = shorts got squeezed = price went UP = expect pullback DOWN
    df['liquidation_direction'] = df['dominant'].apply(
        lambda x: 'long_liquidation' if x == 'LONG' else 'short_liquidation' if x == 'SHORT' else 'mixed'
    )

    # Expected mean-reversion direction
    # After long liquidation (longs squeezed), expect price to bounce UP
    # After short liquidation (shorts squeezed), expect price to pull back DOWN
    df['expected_direction'] = df['liquidation_direction'].apply(
        lambda x: 'up' if x == 'long_liquidation' else 'down' if x == 'short_liquidation' else 'unknown'
    )

    # Magnitude classification
    df['magnitude'] = pd.cut(
        df['total_value'],
        bins=[0, 500000, 1000000, 2000000, 5000000, float('inf')],
        labels=['small', 'medium', 'large', 'very_large', 'massive']
    )

    print(f"Loaded {len(df)} liquidation alerts")
    print(f"Date range: {df['timestamp_dt'].min()} to {df['timestamp_dt'].max()}")
    print(f"\nBy symbol:")
    print(df['symbol'].value_counts())
    print(f"\nBy dominant direction:")
    print(df['dominant'].value_counts())
    print(f"\nBy magnitude:")
    print(df['magnitude'].value_counts())

    return df


def load_price_data(symbol: str, timeframe: str = '1m') -> pd.DataFrame:
    """Load price data from trading database."""
    conn = sqlite3.connect(TRADING_DB)

    # Try different symbol formats
    symbol_formats = [symbol, symbol.replace('USDT', '/USDT'), f"{symbol[:3]}/{symbol[3:]}"]

    for sym in symbol_formats:
        query = f"""
        SELECT timestamp, open, high, low, close, volume
        FROM market_data
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp
        """
        df = pd.read_sql(query, conn, params=[sym, timeframe])
        if len(df) > 0:
            break

    conn.close()

    if len(df) > 0:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

    return df


def get_price_at_time(price_df: pd.DataFrame, target_time: datetime, tolerance_minutes: int = 5) -> Optional[float]:
    """Get price closest to target time within tolerance."""
    if price_df.empty:
        return None

    # Find closest timestamp
    time_diffs = abs(price_df['timestamp'] - target_time)
    min_idx = time_diffs.idxmin()
    min_diff = time_diffs.loc[min_idx]

    # Check if within tolerance
    if min_diff <= timedelta(minutes=tolerance_minutes):
        return price_df.loc[min_idx, 'close']

    return None


def calculate_forward_returns(alerts_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate forward returns for each alert at various timeframes."""
    results = []

    # Get unique symbols (excluding GLOBAL)
    symbols = alerts_df[alerts_df['symbol'] != 'GLOBAL']['symbol'].unique()

    print(f"\nCalculating forward returns for {len(symbols)} symbols...")

    # Load price data for each symbol
    price_data = {}
    for symbol in symbols:
        # Try 1m data first, fall back to 5m, 15m, 1h
        for tf in ['1m', '5m', '15m', '1h']:
            df = load_price_data(symbol, tf)
            if len(df) > 100:
                price_data[symbol] = (df, tf)
                print(f"  {symbol}: {len(df)} rows ({tf})")
                break
        else:
            print(f"  {symbol}: No price data found")

    # Process each alert
    for idx, alert in alerts_df.iterrows():
        symbol = alert['symbol']

        # Skip GLOBAL alerts for now (would need index/aggregate price)
        if symbol == 'GLOBAL' or symbol not in price_data:
            continue

        price_df, data_tf = price_data[symbol]
        alert_time = alert['timestamp_dt']
        alert_price = alert['current_price']

        # If alert doesn't have price, get from price data
        if alert_price == 0 or pd.isna(alert_price):
            alert_price = get_price_at_time(price_df, alert_time)

        if alert_price is None or alert_price == 0:
            continue

        row_data = {
            'alert_id': alert['alert_id'],
            'symbol': symbol,
            'alert_time': alert_time,
            'alert_price': alert_price,
            'total_value': alert['total_value'],
            'dominant': alert['dominant'],
            'liquidation_direction': alert['liquidation_direction'],
            'expected_direction': alert['expected_direction'],
            'magnitude': alert['magnitude'],
            'event_count': alert['event_count'],
            'rate_per_minute': alert['rate_per_minute']
        }

        # Calculate forward returns
        for tf_label, minutes in FORWARD_TIMEFRAMES.items():
            forward_time = alert_time + timedelta(minutes=minutes)
            forward_price = get_price_at_time(price_df, forward_time, tolerance_minutes=max(5, minutes//4))

            if forward_price is not None and forward_price > 0:
                forward_return = (forward_price - alert_price) / alert_price
                row_data[f'return_{tf_label}'] = forward_return

                # Check if direction matches expectation (mean reversion)
                actual_direction = 'up' if forward_return > 0 else 'down'
                expected = alert['expected_direction']

                if expected in ['up', 'down']:
                    row_data[f'correct_{tf_label}'] = 1 if actual_direction == expected else 0
                else:
                    row_data[f'correct_{tf_label}'] = np.nan
            else:
                row_data[f'return_{tf_label}'] = np.nan
                row_data[f'correct_{tf_label}'] = np.nan

        results.append(row_data)

    return pd.DataFrame(results)


def run_statistical_tests(results_df: pd.DataFrame) -> Dict:
    """Run statistical tests on forward returns."""
    test_results = {
        'overall': {},
        'by_symbol': {},
        'by_magnitude': {},
        'by_direction': {}
    }

    # Overall tests
    print("\n" + "="*70)
    print("OVERALL STATISTICAL TESTS")
    print("="*70)

    for tf_label in FORWARD_TIMEFRAMES.keys():
        return_col = f'return_{tf_label}'
        correct_col = f'correct_{tf_label}'

        if return_col not in results_df.columns:
            continue

        returns = results_df[return_col].dropna()
        correct = results_df[correct_col].dropna()

        if len(returns) < 20:
            continue

        # T-test for mean return
        t_stat, p_value_return = ttest_1samp(returns, 0)

        # Binomial test for direction accuracy
        if len(correct) >= 20:
            n_correct = int(correct.sum())
            n_total = len(correct)
            accuracy = n_correct / n_total
            binom_result = binomtest(n_correct, n_total, p=0.5, alternative='greater')
            p_value_direction = binom_result.pvalue
        else:
            accuracy = np.nan
            p_value_direction = np.nan

        test_results['overall'][tf_label] = {
            'n': len(returns),
            'mean_return': returns.mean(),
            'std_return': returns.std(),
            'median_return': returns.median(),
            't_statistic': t_stat,
            'p_value_return': p_value_return,
            'significant_return': p_value_return < 0.05,
            'direction_accuracy': accuracy,
            'p_value_direction': p_value_direction,
            'significant_direction': p_value_direction < 0.05 if not np.isnan(p_value_direction) else False
        }

        sig_return = "***" if p_value_return < 0.01 else "**" if p_value_return < 0.05 else ""
        sig_dir = "***" if p_value_direction < 0.01 else "**" if p_value_direction < 0.05 else ""

        print(f"\n{tf_label} (n={len(returns)}):")
        print(f"  Mean Return: {returns.mean()*100:.4f}% {sig_return}")
        print(f"  Median Return: {returns.median()*100:.4f}%")
        print(f"  Std: {returns.std()*100:.4f}%")
        print(f"  t-stat: {t_stat:.3f}, p-value: {p_value_return:.6f}")
        if not np.isnan(accuracy):
            print(f"  Direction Accuracy: {accuracy*100:.1f}% {sig_dir}")
            print(f"  Direction p-value: {p_value_direction:.6f}")

    # Tests by symbol
    print("\n" + "="*70)
    print("BY SYMBOL")
    print("="*70)

    for symbol in results_df['symbol'].unique():
        symbol_data = results_df[results_df['symbol'] == symbol]
        test_results['by_symbol'][symbol] = {}

        print(f"\n{symbol}:")

        for tf_label in FORWARD_TIMEFRAMES.keys():
            return_col = f'return_{tf_label}'
            returns = symbol_data[return_col].dropna()

            if len(returns) < 10:
                continue

            mean_ret = returns.mean()
            t_stat, p_value = ttest_1samp(returns, 0)

            test_results['by_symbol'][symbol][tf_label] = {
                'n': len(returns),
                'mean_return': mean_ret,
                'p_value': p_value
            }

            sig = "***" if p_value < 0.01 else "**" if p_value < 0.05 else ""
            print(f"  {tf_label}: mean={mean_ret*100:.3f}% (n={len(returns)}) p={p_value:.4f} {sig}")

    # Tests by magnitude
    print("\n" + "="*70)
    print("BY MAGNITUDE")
    print("="*70)

    for magnitude in results_df['magnitude'].dropna().unique():
        magnitude_data = results_df[results_df['magnitude'] == magnitude]
        test_results['by_magnitude'][str(magnitude)] = {}

        print(f"\n{magnitude} (${magnitude_data['total_value'].mean():,.0f} avg):")

        for tf_label in FORWARD_TIMEFRAMES.keys():
            return_col = f'return_{tf_label}'
            returns = magnitude_data[return_col].dropna()

            if len(returns) < 10:
                continue

            mean_ret = returns.mean()
            t_stat, p_value = ttest_1samp(returns, 0)

            test_results['by_magnitude'][str(magnitude)][tf_label] = {
                'n': len(returns),
                'mean_return': mean_ret,
                'p_value': p_value
            }

            sig = "***" if p_value < 0.01 else "**" if p_value < 0.05 else ""
            print(f"  {tf_label}: mean={mean_ret*100:.3f}% (n={len(returns)}) p={p_value:.4f} {sig}")

    # Tests by liquidation direction
    print("\n" + "="*70)
    print("BY LIQUIDATION DIRECTION")
    print("="*70)

    for direction in ['long_liquidation', 'short_liquidation']:
        dir_data = results_df[results_df['liquidation_direction'] == direction]
        test_results['by_direction'][direction] = {}

        print(f"\n{direction} (longs squeezed = expect UP, shorts squeezed = expect DOWN):")

        for tf_label in FORWARD_TIMEFRAMES.keys():
            return_col = f'return_{tf_label}'
            correct_col = f'correct_{tf_label}'
            returns = dir_data[return_col].dropna()
            correct = dir_data[correct_col].dropna()

            if len(returns) < 10:
                continue

            mean_ret = returns.mean()
            t_stat, p_value = ttest_1samp(returns, 0)

            accuracy = correct.mean() if len(correct) > 0 else np.nan

            test_results['by_direction'][direction][tf_label] = {
                'n': len(returns),
                'mean_return': mean_ret,
                'p_value': p_value,
                'accuracy': accuracy
            }

            sig = "***" if p_value < 0.01 else "**" if p_value < 0.05 else ""
            print(f"  {tf_label}: mean={mean_ret*100:.3f}% accuracy={accuracy*100:.1f}% (n={len(returns)}) p={p_value:.4f} {sig}")

    return test_results


def generate_visualizations(results_df: pd.DataFrame, test_results: Dict, output_dir: str):
    """Generate visualization charts."""
    if not HAS_MATPLOTLIB:
        print("\nMatplotlib not available, skipping visualizations")
        return

    os.makedirs(output_dir, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    plt.style.use('seaborn-v0_8-darkgrid')

    # 1. Overall returns by timeframe
    ax = axes[0, 0]
    timeframes = list(FORWARD_TIMEFRAMES.keys())
    means = [test_results['overall'].get(tf, {}).get('mean_return', 0) * 100 for tf in timeframes]
    stds = [test_results['overall'].get(tf, {}).get('std_return', 0) * 100 for tf in timeframes]

    colors = ['green' if test_results['overall'].get(tf, {}).get('significant_return', False) else 'gray'
              for tf in timeframes]

    bars = ax.bar(timeframes, means, color=colors, alpha=0.7)
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax.set_xlabel('Forward Timeframe')
    ax.set_ylabel('Mean Return (%)')
    ax.set_title('Mean Return After Liquidation Alert\n(Green = p < 0.05)')

    # Add annotations
    for i, (bar, mean, std) in enumerate(zip(bars, means, stds)):
        ax.annotate(f'{mean:.3f}%', xy=(bar.get_x() + bar.get_width()/2, mean),
                   ha='center', va='bottom' if mean >= 0 else 'top', fontsize=9)

    # 2. Direction accuracy by timeframe
    ax = axes[0, 1]
    accuracies = [test_results['overall'].get(tf, {}).get('direction_accuracy', 0.5) * 100 for tf in timeframes]

    colors = ['green' if test_results['overall'].get(tf, {}).get('significant_direction', False) else 'gray'
              for tf in timeframes]

    bars = ax.bar(timeframes, accuracies, color=colors, alpha=0.7)
    ax.axhline(y=50, color='red', linestyle='--', label='Random (50%)')
    ax.set_xlabel('Forward Timeframe')
    ax.set_ylabel('Accuracy (%)')
    ax.set_title('Mean-Reversion Direction Accuracy\n(Green = p < 0.05)')
    ax.legend()
    ax.set_ylim(40, 65)

    # 3. Returns by symbol
    ax = axes[1, 0]
    symbols = list(test_results['by_symbol'].keys())
    returns_1h = [test_results['by_symbol'].get(s, {}).get('1h', {}).get('mean_return', 0) * 100 for s in symbols]

    ax.barh(symbols, returns_1h, color=['green' if r > 0 else 'red' for r in returns_1h], alpha=0.7)
    ax.axvline(x=0, color='black', linestyle='-', alpha=0.5)
    ax.set_xlabel('Mean Return at 1h (%)')
    ax.set_title('1h Forward Return by Symbol')

    # 4. Cumulative returns distribution
    ax = axes[1, 1]
    if 'return_1h' in results_df.columns:
        returns = results_df['return_1h'].dropna() * 100
        ax.hist(returns, bins=50, edgecolor='black', alpha=0.7)
        ax.axvline(x=returns.mean(), color='red', linestyle='--', label=f'Mean: {returns.mean():.3f}%')
        ax.axvline(x=0, color='black', linestyle='-', alpha=0.5)
        ax.set_xlabel('Return (%)')
        ax.set_ylabel('Frequency')
        ax.set_title('Distribution of 1h Forward Returns')
        ax.legend()

    plt.tight_layout()
    chart_path = os.path.join(output_dir, 'real_liquidation_edge_analysis.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\nVisualization saved to: {chart_path}")


def print_conclusions(test_results: Dict, results_df: pd.DataFrame):
    """Print final conclusions and trading implications."""
    print("\n" + "="*70)
    print("CONCLUSIONS & TRADING IMPLICATIONS")
    print("="*70)

    # Find significant results
    significant_returns = []
    significant_directions = []

    for tf, data in test_results['overall'].items():
        if data.get('significant_return'):
            significant_returns.append((tf, data['mean_return'], data['p_value_return']))
        if data.get('significant_direction'):
            significant_directions.append((tf, data['direction_accuracy'], data['p_value_direction']))

    print("\n📊 STATISTICALLY SIGNIFICANT FINDINGS:")
    print("-" * 40)

    if significant_returns:
        print("\n✅ Mean Returns (p < 0.05):")
        for tf, mean_ret, p_val in significant_returns:
            print(f"   {tf}: {mean_ret*100:.4f}% (p={p_val:.4f})")
    else:
        print("\n❌ No statistically significant mean returns found")

    if significant_directions:
        print("\n✅ Direction Accuracy > 50% (p < 0.05):")
        for tf, acc, p_val in significant_directions:
            print(f"   {tf}: {acc*100:.1f}% accuracy (p={p_val:.4f})")
    else:
        print("\n❌ No statistically significant directional edge found")

    # Trading implications
    print("\n💡 TRADING IMPLICATIONS:")
    print("-" * 40)

    # Check long vs short liquidation asymmetry
    long_liq = test_results.get('by_direction', {}).get('long_liquidation', {})
    short_liq = test_results.get('by_direction', {}).get('short_liquidation', {})

    if long_liq and short_liq:
        for tf in FORWARD_TIMEFRAMES.keys():
            long_ret = long_liq.get(tf, {}).get('mean_return', 0)
            short_ret = short_liq.get(tf, {}).get('mean_return', 0)

            if abs(long_ret) > 0.001 or abs(short_ret) > 0.001:
                print(f"\n{tf} Asymmetry:")
                print(f"  After LONG liquidation (expect UP): {long_ret*100:.3f}%")
                print(f"  After SHORT liquidation (expect DOWN): {short_ret*100:.3f}%")

                # Mean reversion check
                if long_ret > 0:
                    print(f"  ✅ Long liquidation → price bounces UP (mean reversion works)")
                if short_ret < 0:
                    print(f"  ✅ Short liquidation → price pulls back DOWN (mean reversion works)")

    # Sample size warning
    total_alerts = len(results_df)
    print(f"\n⚠️ CAVEATS:")
    print(f"  - Sample size: {total_alerts} alerts")
    print(f"  - Date range: ~20 days (Nov 27 - Dec 17, 2025)")
    print(f"  - Transaction costs NOT included")
    print(f"  - Slippage during liquidation events may be significant")


def main():
    """Run complete analysis."""
    print("="*70)
    print("REAL LIQUIDATION ALERT PREDICTIVE EDGE ANALYSIS")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load alerts
    alerts_df = load_liquidation_alerts()

    # Calculate forward returns
    print("\n" + "="*70)
    print("CALCULATING FORWARD RETURNS")
    print("="*70)
    results_df = calculate_forward_returns(alerts_df)

    print(f"\nProcessed {len(results_df)} alerts with price data")

    if len(results_df) < 20:
        print("ERROR: Insufficient data for statistical analysis")
        return None, None

    # Run statistical tests
    test_results = run_statistical_tests(results_df)

    # Generate visualizations
    generate_visualizations(results_df, test_results, OUTPUT_DIR)

    # Print conclusions
    print_conclusions(test_results, results_df)

    # Save results to CSV
    csv_path = os.path.join(OUTPUT_DIR, 'liquidation_edge_results.csv')
    results_df.to_csv(csv_path, index=False)
    print(f"\nResults saved to: {csv_path}")

    print(f"\nAnalysis completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return results_df, test_results


if __name__ == '__main__':
    results_df, test_results = main()
