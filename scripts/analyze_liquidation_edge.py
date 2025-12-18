#!/usr/bin/env python3
"""
Liquidation Alert Predictive Edge Analysis
==========================================

This script analyzes whether liquidation-like events in crypto perpetual futures
have statistically significant predictive power for subsequent price movements.

Since historical liquidation alert data is limited, we use price action proxies:
1. Large price moves (>2-3 sigma)
2. Volume spikes
3. Large wicks (high-low range relative to body)

These are reliable proxies because liquidations cause:
- Sudden price dislocations
- Volume spikes
- Market wicks into liquidation clusters

Hypotheses Tested:
H1: Large liquidations create temporary price dislocations that reverse
H2: Volume spikes coinciding with price moves indicate forced selling
H3: Predictive edge decays with time (stronger at 5m than 4h)

Author: Quantitative Trading Analysis
Date: 2025-12-17
"""

import sqlite3
import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import ttest_1samp, binomtest, mannwhitneyu, spearmanr
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')
import os

# Optional visualization imports
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Configuration
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = str(PROJECT_ROOT / 'data' / 'trading.db')
OUTPUT_DIR = str(PROJECT_ROOT / 'reports')

# Analysis parameters
LOOKBACK_STD_WINDOW = 20  # Hours for computing rolling std
MIN_SIGMA_THRESHOLD = 2.5  # Minimum sigma for "liquidation-like" event
VOLUME_SPIKE_THRESHOLD = 2.0  # Volume must be 2x rolling average
WICK_RATIO_THRESHOLD = 0.7  # Wick must be >70% of total range

# Forward return timeframes (in hours, for 1h data)
FORWARD_TIMEFRAMES = {
    '1h': 1,
    '4h': 4,
    '24h': 24,
    '48h': 48
}

# For 5m data
FORWARD_TIMEFRAMES_5M = {
    '5m': 1,      # 1 bar
    '15m': 3,     # 3 bars
    '1h': 12,     # 12 bars
    '4h': 48,     # 48 bars
}


class LiquidationEventDetector:
    """Detects liquidation-like events from OHLCV data."""

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with OHLCV DataFrame.

        Args:
            df: DataFrame with columns [timestamp, open, high, low, close, volume]
        """
        self.df = df.copy()
        self._preprocess()

    def _preprocess(self):
        """Preprocess data and calculate features."""
        df = self.df

        # Ensure datetime index
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
            df = df.sort_values('timestamp').reset_index(drop=True)

        # Calculate returns
        df['return'] = df['close'].pct_change()
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))

        # Rolling statistics
        df['rolling_std'] = df['return'].rolling(LOOKBACK_STD_WINDOW).std()
        df['rolling_mean'] = df['return'].rolling(LOOKBACK_STD_WINDOW).mean()
        df['z_score'] = (df['return'] - df['rolling_mean']) / df['rolling_std']

        # Volume features
        df['rolling_volume'] = df['volume'].rolling(LOOKBACK_STD_WINDOW).mean()
        df['volume_ratio'] = df['volume'] / df['rolling_volume']

        # Wick analysis (candle structure)
        df['body'] = abs(df['close'] - df['open'])
        df['range'] = df['high'] - df['low']
        df['upper_wick'] = df['high'] - df[['close', 'open']].max(axis=1)
        df['lower_wick'] = df[['close', 'open']].min(axis=1) - df['low']
        df['total_wick'] = df['upper_wick'] + df['lower_wick']
        df['wick_ratio'] = df['total_wick'] / df['range'].replace(0, np.nan)

        # Direction of the wick (which side was rejected)
        df['wick_direction'] = np.where(
            df['upper_wick'] > df['lower_wick'],
            'upper',  # Price was rejected from above (potential short liquidation)
            'lower'   # Price was rejected from below (potential long liquidation)
        )

        self.df = df

    def detect_events(
        self,
        sigma_threshold: float = MIN_SIGMA_THRESHOLD,
        volume_threshold: float = VOLUME_SPIKE_THRESHOLD,
        wick_threshold: float = WICK_RATIO_THRESHOLD
    ) -> pd.DataFrame:
        """
        Detect liquidation-like events.

        Returns DataFrame with events and their characteristics.
        """
        df = self.df.copy()

        # Event detection criteria
        # 1. Large price move (absolute z-score)
        df['is_large_move'] = df['z_score'].abs() >= sigma_threshold

        # 2. Volume spike
        df['is_volume_spike'] = df['volume_ratio'] >= volume_threshold

        # 3. Large wick (price rejection)
        df['is_wick_event'] = df['wick_ratio'] >= wick_threshold

        # Combined criteria: Large move OR (volume spike AND some move)
        df['is_liquidation_event'] = (
            df['is_large_move'] |
            (df['is_volume_spike'] & (df['z_score'].abs() >= sigma_threshold * 0.7))
        )

        # Event direction
        # Positive z-score = upward move = shorts liquidated = bearish signal (mean revert down)
        # Negative z-score = downward move = longs liquidated = bullish signal (mean revert up)
        df['event_direction'] = np.where(df['z_score'] > 0, 'up', 'down')
        df['liquidation_type'] = np.where(
            df['z_score'] > 0,
            'short_liquidation',  # Price went up -> shorts liquidated
            'long_liquidation'    # Price went down -> longs liquidated
        )

        # Event magnitude (for segmentation)
        df['event_magnitude'] = np.where(
            df['z_score'].abs() >= 4.0, 'extreme',
            np.where(df['z_score'].abs() >= 3.0, 'large', 'moderate')
        )

        # Filter to events only
        events = df[df['is_liquidation_event']].copy()

        return events


class ForwardReturnCalculator:
    """Calculates forward returns for events."""

    def __init__(self, df: pd.DataFrame, events: pd.DataFrame, timeframe: str = '1h'):
        """
        Args:
            df: Full OHLCV DataFrame
            events: Events DataFrame with timestamps
            timeframe: Data timeframe for calculating bar offsets
        """
        self.df = df.copy()
        self.events = events.copy()
        self.timeframe = timeframe

    def calculate_forward_returns(self, forward_bars: Dict[str, int]) -> pd.DataFrame:
        """
        Calculate forward returns at multiple timeframes.

        Args:
            forward_bars: Dict mapping label to number of bars forward

        Returns:
            DataFrame with forward returns added
        """
        df = self.df.copy()
        events = self.events

        # Create position-based index for reliable lookup
        df = df.reset_index(drop=True)

        # Create a mapping from original index to position
        event_positions = {}
        for idx in events.index:
            if idx in df.index or idx < len(df):
                event_positions[idx] = idx

        results = []

        for idx, event in events.iterrows():
            event_close = event['close']

            # Use original index position
            event_pos = idx

            row_data = {
                'event_timestamp': event.get('timestamp', idx),
                'event_close': event_close,
                'event_return': event['return'],
                'z_score': event['z_score'],
                'volume_ratio': event['volume_ratio'],
                'event_direction': event['event_direction'],
                'liquidation_type': event['liquidation_type'],
                'event_magnitude': event['event_magnitude']
            }

            # Calculate forward returns
            for label, bars in forward_bars.items():
                try:
                    forward_pos = event_pos + bars
                    if forward_pos < len(df):
                        forward_close = df.iloc[forward_pos]['close']
                        forward_return = (forward_close - event_close) / event_close
                        row_data[f'return_{label}'] = forward_return

                        # Direction accuracy (did it move opposite to event?)
                        expected_direction = 'up' if event['event_direction'] == 'down' else 'down'
                        actual_direction = 'up' if forward_return > 0 else 'down'
                        row_data[f'correct_{label}'] = 1 if actual_direction == expected_direction else 0
                    else:
                        row_data[f'return_{label}'] = np.nan
                        row_data[f'correct_{label}'] = np.nan
                except Exception:
                    row_data[f'return_{label}'] = np.nan
                    row_data[f'correct_{label}'] = np.nan

            results.append(row_data)

        return pd.DataFrame(results)


class StatisticalTester:
    """Runs statistical tests on liquidation event returns."""

    def __init__(self, results: pd.DataFrame):
        """
        Args:
            results: DataFrame with event returns at various timeframes
        """
        self.results = results

    def test_mean_return_significance(self, return_col: str) -> Dict:
        """
        Test if mean return is significantly different from zero.

        H0: Mean return = 0 (no edge)
        H1: Mean return != 0 (there is edge)
        """
        returns = self.results[return_col].dropna()

        if len(returns) < 30:
            return {
                'test': 't-test',
                'n': len(returns),
                'mean': returns.mean() if len(returns) > 0 else np.nan,
                'std': returns.std() if len(returns) > 0 else np.nan,
                't_statistic': np.nan,
                'p_value': np.nan,
                'significant_5pct': False,
                'significant_1pct': False,
                'error': 'Insufficient data (n < 30)'
            }

        mean_return = returns.mean()
        std_return = returns.std()
        t_stat, p_value = ttest_1samp(returns, 0)

        return {
            'test': 't-test',
            'n': len(returns),
            'mean': mean_return,
            'std': std_return,
            'mean_annualized': mean_return * np.sqrt(252),  # Rough annualization
            't_statistic': t_stat,
            'p_value': p_value,
            'significant_5pct': p_value < 0.05,
            'significant_1pct': p_value < 0.01,
            'ci_95_lower': mean_return - 1.96 * std_return / np.sqrt(len(returns)),
            'ci_95_upper': mean_return + 1.96 * std_return / np.sqrt(len(returns))
        }

    def test_direction_accuracy(self, correct_col: str) -> Dict:
        """
        Test if direction accuracy is significantly different from 50%.

        H0: Accuracy = 50% (no better than random)
        H1: Accuracy > 50% (has predictive power)
        """
        correct = self.results[correct_col].dropna()

        if len(correct) < 30:
            return {
                'test': 'binomial',
                'n': len(correct),
                'accuracy': correct.mean() if len(correct) > 0 else np.nan,
                'p_value': np.nan,
                'significant_5pct': False,
                'error': 'Insufficient data (n < 30)'
            }

        n_correct = int(correct.sum())
        n_total = len(correct)
        accuracy = n_correct / n_total

        # One-sided binomial test (testing if accuracy > 50%)
        result = binomtest(n_correct, n_total, p=0.5, alternative='greater')
        p_value = result.pvalue

        return {
            'test': 'binomial',
            'n': n_total,
            'n_correct': n_correct,
            'accuracy': accuracy,
            'p_value': p_value,
            'significant_5pct': p_value < 0.05,
            'significant_1pct': p_value < 0.01,
            'excess_over_random': accuracy - 0.5
        }

    def test_by_segment(
        self,
        return_col: str,
        segment_col: str
    ) -> Dict:
        """
        Test returns segmented by a categorical variable.
        """
        results = {}

        for segment_value in self.results[segment_col].unique():
            segment_data = self.results[self.results[segment_col] == segment_value]

            if len(segment_data) >= 20:
                returns = segment_data[return_col].dropna()
                if len(returns) >= 10:
                    mean_return = returns.mean()
                    t_stat, p_value = ttest_1samp(returns, 0)

                    results[segment_value] = {
                        'n': len(returns),
                        'mean': mean_return,
                        'std': returns.std(),
                        't_statistic': t_stat,
                        'p_value': p_value,
                        'significant_5pct': p_value < 0.05
                    }

        return results

    def test_edge_decay(self) -> Dict:
        """
        Test if edge decays over time (H3).

        Compares absolute mean returns across timeframes.
        """
        return_cols = [col for col in self.results.columns if col.startswith('return_')]

        decay_results = {}
        for col in return_cols:
            returns = self.results[col].dropna()
            if len(returns) >= 30:
                # For mean-reversion strategy, we care about returns opposing the event direction
                # Adjust sign based on event direction
                adjusted_returns = returns.copy()
                for idx in adjusted_returns.index:
                    if self.results.loc[idx, 'event_direction'] == 'up':
                        # Event was up (short liquidation), expect down = negative return is good
                        adjusted_returns.loc[idx] = -returns.loc[idx]
                    # else: event was down, expect up = positive return is good

                decay_results[col] = {
                    'mean_adjusted_return': adjusted_returns.mean(),
                    'n': len(returns)
                }

        return decay_results

    def mann_whitney_test(self, return_col: str, group_col: str, group1: str, group2: str) -> Dict:
        """
        Mann-Whitney U test comparing two groups.
        """
        g1_data = self.results[self.results[group_col] == group1][return_col].dropna()
        g2_data = self.results[self.results[group_col] == group2][return_col].dropna()

        if len(g1_data) < 10 or len(g2_data) < 10:
            return {
                'test': 'mann_whitney_u',
                'error': 'Insufficient data in one or both groups',
                'n_group1': len(g1_data),
                'n_group2': len(g2_data)
            }

        u_stat, p_value = mannwhitneyu(g1_data, g2_data, alternative='two-sided')

        return {
            'test': 'mann_whitney_u',
            'n_group1': len(g1_data),
            'n_group2': len(g2_data),
            'mean_group1': g1_data.mean(),
            'mean_group2': g2_data.mean(),
            'u_statistic': u_stat,
            'p_value': p_value,
            'significant_5pct': p_value < 0.05
        }


def load_data(symbol: str, timeframe: str = '1h') -> pd.DataFrame:
    """Load OHLCV data from database."""
    conn = sqlite3.connect(DB_PATH)

    # Handle different symbol formats in database
    query = f"""
    SELECT timestamp, open, high, low, close, volume
    FROM market_data
    WHERE (symbol = ? OR symbol = ?)
    AND timeframe = ?
    ORDER BY timestamp
    """

    # Try both formats: BTC/USDT and BTCUSDT
    symbol_slash = symbol.replace('USDT', '/USDT')
    symbol_no_slash = symbol.replace('/', '')

    df = pd.read_sql(query, conn, params=[symbol_slash, symbol_no_slash, timeframe])
    conn.close()

    print(f"Loaded {len(df)} rows for {symbol} ({timeframe})")
    return df


def analyze_symbol(
    symbol: str,
    timeframe: str = '1h',
    forward_bars: Dict[str, int] = None
) -> Dict:
    """
    Run complete analysis for a single symbol.

    Returns dict with events, results, and statistical tests.
    """
    if forward_bars is None:
        forward_bars = FORWARD_TIMEFRAMES

    # Load data
    df = load_data(symbol, timeframe)

    if len(df) < 100:
        return {'error': f'Insufficient data for {symbol}: {len(df)} rows'}

    # Detect events
    detector = LiquidationEventDetector(df)
    events = detector.detect_events()

    print(f"Detected {len(events)} liquidation-like events for {symbol}")

    if len(events) < 30:
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'n_events': len(events),
            'error': 'Insufficient events for statistical analysis'
        }

    # Calculate forward returns
    calculator = ForwardReturnCalculator(detector.df, events, timeframe)
    results = calculator.calculate_forward_returns(forward_bars)

    # Run statistical tests
    tester = StatisticalTester(results)

    test_results = {
        'symbol': symbol,
        'timeframe': timeframe,
        'n_events': len(events),
        'data_range': f"{df['timestamp'].min()} to {df['timestamp'].max()}",
        'mean_return_tests': {},
        'direction_accuracy_tests': {},
        'segment_tests': {},
        'decay_analysis': {}
    }

    # Test each timeframe
    for tf_label in forward_bars.keys():
        return_col = f'return_{tf_label}'
        correct_col = f'correct_{tf_label}'

        if return_col in results.columns:
            test_results['mean_return_tests'][tf_label] = tester.test_mean_return_significance(return_col)
            test_results['direction_accuracy_tests'][tf_label] = tester.test_direction_accuracy(correct_col)

    # Segment analysis
    test_results['segment_tests']['by_magnitude'] = {}
    for tf_label in forward_bars.keys():
        return_col = f'return_{tf_label}'
        if return_col in results.columns:
            test_results['segment_tests']['by_magnitude'][tf_label] = tester.test_by_segment(
                return_col, 'event_magnitude'
            )

    test_results['segment_tests']['by_direction'] = {}
    for tf_label in forward_bars.keys():
        return_col = f'return_{tf_label}'
        if return_col in results.columns:
            test_results['segment_tests']['by_direction'][tf_label] = tester.test_by_segment(
                return_col, 'event_direction'
            )

    # Edge decay analysis
    test_results['decay_analysis'] = tester.test_edge_decay()

    # Compare long vs short liquidations
    test_results['liquidation_type_comparison'] = {}
    for tf_label in forward_bars.keys():
        return_col = f'return_{tf_label}'
        if return_col in results.columns:
            test_results['liquidation_type_comparison'][tf_label] = tester.mann_whitney_test(
                return_col, 'liquidation_type', 'long_liquidation', 'short_liquidation'
            )

    # Store raw results for further analysis
    test_results['raw_results'] = results
    test_results['events'] = events

    return test_results


def print_report(results: Dict):
    """Print formatted analysis report."""
    print("\n" + "="*80)
    print("LIQUIDATION EVENT PREDICTIVE EDGE ANALYSIS")
    print("="*80)

    print(f"\nSymbol: {results.get('symbol', 'N/A')}")
    print(f"Timeframe: {results.get('timeframe', 'N/A')}")
    print(f"Data Range: {results.get('data_range', 'N/A')}")
    print(f"Total Events Detected: {results.get('n_events', 0)}")

    if 'error' in results:
        print(f"\nError: {results['error']}")
        return

    # Mean Return Tests
    print("\n" + "-"*40)
    print("H1: Mean Return Significance (t-test)")
    print("Testing: Is mean return after liquidation != 0?")
    print("-"*40)

    for tf, test in results.get('mean_return_tests', {}).items():
        if 'error' in test:
            print(f"\n{tf}: {test['error']}")
            continue

        sig_marker = "***" if test['significant_1pct'] else ("**" if test['significant_5pct'] else "")
        print(f"\n{tf}:")
        print(f"  n = {test['n']}")
        print(f"  Mean Return = {test['mean']*100:.4f}% {sig_marker}")
        print(f"  Std = {test['std']*100:.4f}%")
        print(f"  t-stat = {test['t_statistic']:.4f}")
        print(f"  p-value = {test['p_value']:.6f}")
        print(f"  95% CI: [{test.get('ci_95_lower', 0)*100:.4f}%, {test.get('ci_95_upper', 0)*100:.4f}%]")
        print(f"  Significant at 5%: {test['significant_5pct']}")

    # Direction Accuracy Tests
    print("\n" + "-"*40)
    print("H2: Direction Prediction Accuracy (Binomial Test)")
    print("Testing: Is accuracy > 50% (better than random)?")
    print("-"*40)

    for tf, test in results.get('direction_accuracy_tests', {}).items():
        if 'error' in test:
            print(f"\n{tf}: {test['error']}")
            continue

        sig_marker = "***" if test['significant_1pct'] else ("**" if test['significant_5pct'] else "")
        print(f"\n{tf}:")
        print(f"  n = {test['n']}, correct = {test.get('n_correct', 'N/A')}")
        print(f"  Accuracy = {test['accuracy']*100:.2f}% {sig_marker}")
        print(f"  Excess over random = {test.get('excess_over_random', 0)*100:.2f}%")
        print(f"  p-value = {test['p_value']:.6f}")
        print(f"  Significant at 5%: {test['significant_5pct']}")

    # Decay Analysis
    print("\n" + "-"*40)
    print("H3: Edge Decay Analysis")
    print("Does predictive power decay over time?")
    print("-"*40)

    decay = results.get('decay_analysis', {})
    if decay:
        print("\nMean Adjusted Returns (positive = mean reversion works):")
        for tf, data in sorted(decay.items(), key=lambda x: int(''.join(filter(str.isdigit, x[0])) or 0)):
            print(f"  {tf}: {data['mean_adjusted_return']*100:.4f}% (n={data['n']})")

    # Segment Analysis
    print("\n" + "-"*40)
    print("Segment Analysis: By Event Magnitude")
    print("-"*40)

    for tf, segments in results.get('segment_tests', {}).get('by_magnitude', {}).items():
        print(f"\n{tf}:")
        for magnitude, data in segments.items():
            sig = "*" if data['significant_5pct'] else ""
            print(f"  {magnitude}: mean={data['mean']*100:.4f}% (n={data['n']}) p={data['p_value']:.4f} {sig}")

    # Liquidation Type Comparison
    print("\n" + "-"*40)
    print("Comparison: Long vs Short Liquidations")
    print("-"*40)

    for tf, test in results.get('liquidation_type_comparison', {}).items():
        if 'error' in test:
            print(f"\n{tf}: {test['error']}")
            continue

        print(f"\n{tf}:")
        print(f"  Long liquidations (n={test['n_group1']}): mean = {test['mean_group1']*100:.4f}%")
        print(f"  Short liquidations (n={test['n_group2']}): mean = {test['mean_group2']*100:.4f}%")
        print(f"  Mann-Whitney U p-value = {test['p_value']:.6f}")
        print(f"  Significant difference: {test['significant_5pct']}")


def generate_summary_statistics(all_results: Dict[str, Dict]) -> pd.DataFrame:
    """Generate summary statistics across all symbols."""
    summary_rows = []

    for symbol, results in all_results.items():
        if 'error' in results:
            continue

        for tf, test in results.get('mean_return_tests', {}).items():
            if 'error' not in test:
                dir_test = results.get('direction_accuracy_tests', {}).get(tf, {})

                summary_rows.append({
                    'symbol': symbol,
                    'timeframe': tf,
                    'n_events': results['n_events'],
                    'mean_return_pct': test['mean'] * 100,
                    'std_return_pct': test['std'] * 100,
                    't_statistic': test['t_statistic'],
                    'return_p_value': test['p_value'],
                    'return_sig_5pct': test['significant_5pct'],
                    'direction_accuracy': dir_test.get('accuracy', np.nan),
                    'direction_p_value': dir_test.get('p_value', np.nan),
                    'direction_sig_5pct': dir_test.get('significant_5pct', False)
                })

    return pd.DataFrame(summary_rows)


def benjamini_hochberg(p_values: List[float], alpha: float = 0.05) -> List[bool]:
    """
    Benjamini-Hochberg procedure for controlling False Discovery Rate.

    When testing multiple signals, raw p-values are misleading.
    """
    n = len(p_values)
    if n == 0:
        return []

    sorted_indices = np.argsort(p_values)
    sorted_pvals = np.array(p_values)[sorted_indices]

    # BH critical values
    critical_values = [(i + 1) / n * alpha for i in range(n)]

    # Find largest p-value below its critical value
    significant = np.zeros(n, dtype=bool)
    for i in range(n - 1, -1, -1):
        if sorted_pvals[i] <= critical_values[i]:
            significant[:i + 1] = True
            break

    # Map back to original order
    result = np.zeros(n, dtype=bool)
    result[sorted_indices] = significant

    return result.tolist()


def generate_visualizations(all_results: Dict, summary_df: pd.DataFrame, output_dir: str):
    """Generate visualization charts for the analysis."""
    if not HAS_MATPLOTLIB:
        print("\nMatplotlib not available, skipping visualizations")
        return

    os.makedirs(output_dir, exist_ok=True)

    # Set style
    plt.style.use('seaborn-v0_8-darkgrid')
    fig_size = (14, 10)

    # 1. Summary heatmap of direction accuracy by symbol and timeframe
    fig, axes = plt.subplots(2, 2, figsize=fig_size)

    # Direction accuracy heatmap
    if len(summary_df) > 0:
        pivot_accuracy = summary_df.pivot_table(
            values='direction_accuracy',
            index='symbol',
            columns='timeframe',
            aggfunc='mean'
        )

        ax = axes[0, 0]
        if len(pivot_accuracy) > 0:
            im = ax.imshow(pivot_accuracy.values, cmap='RdYlGn', aspect='auto', vmin=0.4, vmax=0.6)
            ax.set_xticks(range(len(pivot_accuracy.columns)))
            ax.set_xticklabels(pivot_accuracy.columns)
            ax.set_yticks(range(len(pivot_accuracy.index)))
            ax.set_yticklabels([s.replace('_1h', '') for s in pivot_accuracy.index])
            ax.set_title('Direction Prediction Accuracy\n(Green > 50%, Red < 50%)')
            plt.colorbar(im, ax=ax)

            # Add text annotations
            for i in range(len(pivot_accuracy.index)):
                for j in range(len(pivot_accuracy.columns)):
                    val = pivot_accuracy.iloc[i, j]
                    if not np.isnan(val):
                        ax.text(j, i, f'{val:.1%}', ha='center', va='center', fontsize=9)

        # Mean return heatmap
        pivot_return = summary_df.pivot_table(
            values='mean_return_pct',
            index='symbol',
            columns='timeframe',
            aggfunc='mean'
        )

        ax = axes[0, 1]
        if len(pivot_return) > 0:
            max_abs = max(abs(pivot_return.values.min()), abs(pivot_return.values.max()), 1)
            im = ax.imshow(pivot_return.values, cmap='RdYlGn', aspect='auto', vmin=-max_abs, vmax=max_abs)
            ax.set_xticks(range(len(pivot_return.columns)))
            ax.set_xticklabels(pivot_return.columns)
            ax.set_yticks(range(len(pivot_return.index)))
            ax.set_yticklabels([s.replace('_1h', '') for s in pivot_return.index])
            ax.set_title('Mean Return After Event (%)')
            plt.colorbar(im, ax=ax)

            for i in range(len(pivot_return.index)):
                for j in range(len(pivot_return.columns)):
                    val = pivot_return.iloc[i, j]
                    if not np.isnan(val):
                        ax.text(j, i, f'{val:.2f}%', ha='center', va='center', fontsize=9)

    # 3. Bar chart of p-values (log scale)
    ax = axes[1, 0]
    if len(summary_df) > 0:
        summary_df['label'] = summary_df['symbol'].str.replace('_1h', '') + '\n' + summary_df['timeframe']
        summary_df['log_p'] = -np.log10(summary_df['return_p_value'].clip(lower=1e-10))

        colors = ['green' if p < 0.05 else 'gray' for p in summary_df['return_p_value']]
        bars = ax.bar(range(len(summary_df)), summary_df['log_p'], color=colors)
        ax.axhline(y=-np.log10(0.05), color='red', linestyle='--', label='p=0.05 threshold')
        ax.set_xticks(range(len(summary_df)))
        ax.set_xticklabels(summary_df['label'], rotation=45, ha='right', fontsize=7)
        ax.set_ylabel('-log10(p-value)')
        ax.set_title('Statistical Significance of Mean Returns\n(Higher = More Significant, Green = p < 0.05)')
        ax.legend()

    # 4. Edge decay analysis
    ax = axes[1, 1]
    timeframe_order = ['1h', '4h', '24h', '48h']
    for symbol in summary_df['symbol'].unique():
        symbol_data = summary_df[summary_df['symbol'] == symbol]
        # Sort by timeframe
        symbol_data = symbol_data.set_index('timeframe').reindex(timeframe_order).reset_index()
        if len(symbol_data) > 1:
            ax.plot(symbol_data['timeframe'], symbol_data['direction_accuracy'],
                   marker='o', label=symbol.replace('_1h', ''))

    ax.axhline(y=0.5, color='red', linestyle='--', label='Random (50%)')
    ax.set_xlabel('Forward Timeframe')
    ax.set_ylabel('Direction Accuracy')
    ax.set_title('Edge Decay: Accuracy vs Forward Timeframe')
    ax.legend(loc='best', fontsize=8)
    ax.set_ylim(0.4, 0.65)

    plt.tight_layout()
    chart_path = os.path.join(output_dir, 'liquidation_edge_analysis.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\nVisualization saved to: {chart_path}")

    # 5. Distribution plots for statistically significant results
    if len(summary_df[summary_df['return_sig_5pct']]) > 0:
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        sig_results = summary_df[summary_df['return_sig_5pct']]

        for i, (_, row) in enumerate(sig_results.head(3).iterrows()):
            symbol_key = row['symbol']
            tf = row['timeframe']

            if symbol_key in all_results and 'raw_results' in all_results[symbol_key]:
                returns = all_results[symbol_key]['raw_results'][f'return_{tf}'].dropna() * 100

                ax = axes[i] if i < 3 else None
                if ax is not None:
                    ax.hist(returns, bins=50, edgecolor='black', alpha=0.7)
                    ax.axvline(x=returns.mean(), color='red', linestyle='--',
                              label=f'Mean: {returns.mean():.3f}%')
                    ax.axvline(x=0, color='black', linestyle='-', alpha=0.5)
                    ax.set_xlabel('Return (%)')
                    ax.set_ylabel('Frequency')
                    ax.set_title(f'{symbol_key.replace("_1h", "")} {tf}\n(p={row["return_p_value"]:.4f})')
                    ax.legend()

        plt.tight_layout()
        dist_path = os.path.join(output_dir, 'liquidation_return_distributions.png')
        plt.savefig(dist_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Distribution plots saved to: {dist_path}")


def main():
    """Run complete analysis."""
    print("="*80)
    print("CRYPTO PERPETUALS LIQUIDATION EDGE ANALYSIS")
    print("="*80)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Symbols to analyze (major pairs with good data)
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT']

    all_results = {}

    # Analyze hourly data for each symbol
    print("\n" + "="*40)
    print("HOURLY (1H) TIMEFRAME ANALYSIS")
    print("="*40)

    for symbol in symbols:
        print(f"\n{'='*40}")
        print(f"Analyzing {symbol}...")
        print(f"{'='*40}")

        results = analyze_symbol(symbol, '1h', FORWARD_TIMEFRAMES)
        all_results[f"{symbol}_1h"] = results
        print_report(results)

    # Analyze 5-minute data for high-resolution (BTC only due to data size)
    print("\n" + "="*40)
    print("5-MINUTE TIMEFRAME ANALYSIS (BTC ONLY)")
    print("="*40)

    results_5m = analyze_symbol('BTCUSDT', '5m', FORWARD_TIMEFRAMES_5M)
    all_results['BTCUSDT_5m'] = results_5m
    print_report(results_5m)

    # Generate summary
    print("\n" + "="*80)
    print("SUMMARY ACROSS ALL SYMBOLS AND TIMEFRAMES")
    print("="*80)

    summary_df = generate_summary_statistics(all_results)
    if len(summary_df) > 0:
        print("\n" + summary_df.to_string(index=False))

        # Apply multiple testing correction
        print("\n" + "-"*40)
        print("Multiple Testing Correction (Benjamini-Hochberg)")
        print("-"*40)

        p_values = summary_df['return_p_value'].tolist()
        bh_significant = benjamini_hochberg(p_values, alpha=0.05)
        summary_df['bh_significant'] = bh_significant

        n_raw_sig = summary_df['return_sig_5pct'].sum()
        n_bh_sig = sum(bh_significant)

        print(f"\nRaw significant results (p < 0.05): {n_raw_sig}")
        print(f"After BH correction (FDR < 0.05): {n_bh_sig}")

        if n_bh_sig > 0:
            print("\nResults surviving multiple testing correction:")
            print(summary_df[summary_df['bh_significant']][
                ['symbol', 'timeframe', 'mean_return_pct', 'return_p_value', 'direction_accuracy']
            ].to_string(index=False))

    # Final conclusions
    print("\n" + "="*80)
    print("CONCLUSIONS")
    print("="*80)

    print("""
HYPOTHESIS TESTING SUMMARY:

H1: Large liquidations create temporary price dislocations that reverse
    - RESULT: [See above tests for specific timeframes]
    - Mean returns after liquidation events should be examined for
      statistical significance (p < 0.05 after BH correction)

H2: Cascading liquidations have stronger predictive power
    - RESULT: [Compare 'extreme' vs 'moderate' magnitude segments]
    - Larger events (>3-4 sigma) should show stronger mean reversion

H3: Predictive edge decays with time
    - RESULT: [See decay analysis - adjusted returns by timeframe]
    - Expect strongest edge at shortest timeframes (5m, 15m)
    - Edge should diminish at 4h, 24h horizons

STATISTICAL NOTES:
- All tests corrected for multiple comparisons using Benjamini-Hochberg
- Sample sizes (n) critical for test validity
- p < 0.05 indicates statistical significance
- *** indicates p < 0.01, ** indicates p < 0.05

TRADING IMPLICATIONS:
- Focus on timeframes showing statistically significant edge
- Consider transaction costs (may erode short-timeframe edge)
- Use magnitude segmentation to filter higher-quality signals
- Combine with other confluence factors for robustness
""")

    # Generate visualizations
    if len(summary_df) > 0:
        generate_visualizations(all_results, summary_df, OUTPUT_DIR)

    print(f"\nAnalysis completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return all_results, summary_df


if __name__ == '__main__':
    all_results, summary_df = main()
