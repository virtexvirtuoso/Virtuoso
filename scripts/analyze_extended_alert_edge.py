#!/usr/bin/env python3
"""
Extended Alert Predictive Edge Analysis
========================================
Analyzes predictive edge for:
1. Whale Trade alerts (196 alerts) - Large individual trades >$300K
2. GLOBAL Liquidation Cascades (84 alerts) - Cross-market liquidation events
3. Regime Change alerts (152 alerts) - Market regime transitions

Uses CCXT to fetch forward returns from Bybit.
"""

import sqlite3
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
import ccxt
import time
import warnings
warnings.filterwarnings('ignore')

# Configuration
DB_PATH = 'data/virtuoso.db'
FORWARD_TIMEFRAMES = ['5m', '15m', '1h', '4h']
TIMEFRAME_MINUTES = {'5m': 5, '15m': 15, '1h': 60, '4h': 240}


def get_bybit_client():
    """Initialize Bybit client."""
    return ccxt.bybit({
        'enableRateLimit': True,
        'options': {'defaultType': 'linear'}
    })


def fetch_ohlcv_safe(exchange, symbol, timeframe, since, limit=10):
    """Safely fetch OHLCV data with retries."""
    for attempt in range(3):
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            if ohlcv:
                return ohlcv
        except Exception as e:
            if attempt < 2:
                time.sleep(1)
            else:
                return None
    return None


def calculate_forward_return(exchange, symbol, alert_timestamp_ms, alert_price, timeframe_minutes):
    """Calculate forward return for a given alert."""
    try:
        # Fetch candles starting from alert time
        ohlcv = fetch_ohlcv_safe(
            exchange,
            symbol,
            '1m',  # Use 1m candles for precision
            since=alert_timestamp_ms,
            limit=timeframe_minutes + 5
        )

        if not ohlcv or len(ohlcv) < timeframe_minutes:
            return None

        # Get close price at forward timeframe
        forward_close = ohlcv[min(timeframe_minutes - 1, len(ohlcv) - 1)][4]

        # Calculate return
        if alert_price and alert_price > 0:
            return ((forward_close - alert_price) / alert_price) * 100
        return None

    except Exception as e:
        return None


def analyze_whale_trades(conn, exchange):
    """Analyze whale trade alerts for predictive edge."""
    print("\n" + "="*60)
    print("WHALE TRADE PREDICTIVE EDGE ANALYSIS")
    print("="*60)

    query = """
    SELECT
        alert_id, symbol, timestamp, price, details
    FROM alerts
    WHERE alert_type = 'whale_trade'
        AND details IS NOT NULL
    ORDER BY timestamp
    """

    df = pd.read_sql_query(query, conn)
    print(f"Total whale trade alerts: {len(df)}")

    # Parse details
    results = []
    for idx, row in df.iterrows():
        try:
            details = json.loads(row['details']) if isinstance(row['details'], str) else row['details']
            data = details.get('data', details)

            direction = data.get('direction', '').upper()
            if direction not in ['BUY', 'SELL']:
                continue

            symbol = row['symbol']
            if not symbol or symbol == 'GLOBAL':
                continue

            # Get price from details or row
            price = data.get('current_price') or row['price']
            if not price:
                continue

            timestamp_ms = int(row['timestamp'])
            value_usd = data.get('largest_trade_usd', 0)

            results.append({
                'alert_id': row['alert_id'],
                'symbol': symbol,
                'timestamp_ms': timestamp_ms,
                'price': float(price),
                'direction': direction,
                'value_usd': float(value_usd) if value_usd else 0,
                'net_usd': float(data.get('net_usd', 0))
            })
        except Exception as e:
            continue

    alerts_df = pd.DataFrame(results)
    print(f"Valid alerts with direction: {len(alerts_df)}")
    print(f"Direction distribution: BUY={len(alerts_df[alerts_df['direction']=='BUY'])}, SELL={len(alerts_df[alerts_df['direction']=='SELL'])}")
    print(f"Symbols: {alerts_df['symbol'].value_counts().to_dict()}")

    # Calculate forward returns
    print("\nCalculating forward returns (this may take a few minutes)...")

    for tf_name, tf_minutes in TIMEFRAME_MINUTES.items():
        alerts_df[f'return_{tf_name}'] = None

    processed = 0
    for idx, row in alerts_df.iterrows():
        for tf_name, tf_minutes in TIMEFRAME_MINUTES.items():
            ret = calculate_forward_return(
                exchange, row['symbol'], row['timestamp_ms'],
                row['price'], tf_minutes
            )
            alerts_df.at[idx, f'return_{tf_name}'] = ret

        processed += 1
        if processed % 20 == 0:
            print(f"  Processed {processed}/{len(alerts_df)} alerts...")
        time.sleep(0.1)  # Rate limiting

    # Analyze results
    print("\n" + "-"*40)
    print("WHALE TRADE RESULTS BY DIRECTION")
    print("-"*40)

    analysis_results = {'whale_trade': {}}

    for direction in ['BUY', 'SELL']:
        dir_df = alerts_df[alerts_df['direction'] == direction].copy()
        print(f"\n{direction} WHALE TRADES (n={len(dir_df)})")
        print("-"*30)

        analysis_results['whale_trade'][direction] = {'n': len(dir_df), 'timeframes': {}}

        for tf_name in TIMEFRAME_MINUTES.keys():
            col = f'return_{tf_name}'
            returns = dir_df[col].dropna()

            if len(returns) < 5:
                print(f"  {tf_name}: Insufficient data (n={len(returns)})")
                continue

            # Ensure numeric dtype
            returns = pd.to_numeric(returns, errors='coerce').dropna()
            if len(returns) < 5:
                print(f"  {tf_name}: Insufficient numeric data (n={len(returns)})")
                continue

            returns_arr = returns.astype(float).values

            mean_ret = float(np.mean(returns_arr))
            std_ret = float(np.std(returns_arr))

            # Expected direction: BUY should lead to positive returns, SELL to negative
            if direction == 'BUY':
                correct = int((returns_arr > 0).sum())
                expected_sign = 1
            else:  # SELL
                correct = int((returns_arr < 0).sum())
                expected_sign = -1

            accuracy = correct / len(returns_arr) * 100

            # Statistical tests
            t_stat, t_pval = stats.ttest_1samp(returns_arr, 0)
            # Use binomtest (scipy >= 1.7) or binom_test (scipy < 1.7)
            try:
                binom_result = stats.binomtest(correct, len(returns_arr), 0.5, alternative='greater')
                binom_pval = binom_result.pvalue
            except AttributeError:
                binom_pval = stats.binom_test(correct, len(returns_arr), 0.5, alternative='greater')

            analysis_results['whale_trade'][direction]['timeframes'][tf_name] = {
                'n': len(returns),
                'mean_return': mean_ret,
                'std': std_ret,
                'accuracy': accuracy,
                't_pval': t_pval,
                'binom_pval': binom_pval
            }

            sig_marker = "**" if binom_pval < 0.05 else ""
            print(f"  {tf_name}: Mean={mean_ret:+.3f}%, Accuracy={accuracy:.1f}%, p={binom_pval:.4f} {sig_marker}")

    # Analyze by trade size
    print("\n" + "-"*40)
    print("WHALE TRADE BY SIZE (5m timeframe)")
    print("-"*40)

    alerts_df['size_bucket'] = pd.cut(alerts_df['value_usd'],
                                       bins=[0, 500000, 1000000, float('inf')],
                                       labels=['$300K-500K', '$500K-1M', '>$1M'])

    for bucket in alerts_df['size_bucket'].dropna().unique():
        bucket_df = alerts_df[alerts_df['size_bucket'] == bucket]
        returns = bucket_df['return_5m'].dropna()
        if len(returns) >= 5:
            # Check if whale direction matches subsequent move
            buy_df = bucket_df[bucket_df['direction'] == 'BUY']['return_5m'].dropna()
            sell_df = bucket_df[bucket_df['direction'] == 'SELL']['return_5m'].dropna()

            buy_correct = (buy_df > 0).sum() / len(buy_df) * 100 if len(buy_df) > 0 else 0
            sell_correct = (sell_df < 0).sum() / len(sell_df) * 100 if len(sell_df) > 0 else 0

            print(f"  {bucket} (n={len(bucket_df)}): BUY accuracy={buy_correct:.1f}%, SELL accuracy={sell_correct:.1f}%")

    return alerts_df, analysis_results


def analyze_global_liquidations(conn, exchange):
    """Analyze GLOBAL liquidation cascade alerts."""
    print("\n" + "="*60)
    print("GLOBAL LIQUIDATION CASCADE PREDICTIVE EDGE ANALYSIS")
    print("="*60)

    query = """
    SELECT
        alert_id, symbol, timestamp, price, details
    FROM alerts
    WHERE alert_type = 'liquidation_cascade'
        AND symbol = 'GLOBAL'
        AND details IS NOT NULL
    ORDER BY timestamp
    """

    df = pd.read_sql_query(query, conn)
    print(f"Total GLOBAL liquidation alerts: {len(df)}")

    # Parse details and get affected symbols
    results = []
    for idx, row in df.iterrows():
        try:
            details = json.loads(row['details']) if isinstance(row['details'], str) else row['details']

            dominant = details.get('dominant', '').upper()
            if dominant not in ['LONG', 'SHORT']:
                continue

            affected = details.get('affected_symbols', [])
            total_value = details.get('total_value', 0)

            # Use BTC as reference for GLOBAL events
            ref_symbol = 'BTCUSDT'
            if 'BTCUSDT' not in affected and affected:
                ref_symbol = affected[0]

            timestamp_ms = int(row['timestamp'])

            results.append({
                'alert_id': row['alert_id'],
                'timestamp_ms': timestamp_ms,
                'dominant': dominant,
                'total_value': float(total_value) if total_value else 0,
                'affected_count': len(affected),
                'ref_symbol': ref_symbol,
                'affected_symbols': affected
            })
        except Exception as e:
            continue

    alerts_df = pd.DataFrame(results)
    print(f"Valid GLOBAL alerts: {len(alerts_df)}")
    print(f"Dominant distribution: LONG={len(alerts_df[alerts_df['dominant']=='LONG'])}, SHORT={len(alerts_df[alerts_df['dominant']=='SHORT'])}")

    # Need to fetch BTC price at alert time
    print("\nFetching reference prices and calculating returns...")

    for tf_name in TIMEFRAME_MINUTES.keys():
        alerts_df[f'return_{tf_name}'] = None
    alerts_df['ref_price'] = None

    processed = 0
    for idx, row in alerts_df.iterrows():
        # Get price at alert time
        try:
            ohlcv = fetch_ohlcv_safe(exchange, row['ref_symbol'], '1m',
                                      since=row['timestamp_ms'] - 60000, limit=5)
            if ohlcv:
                ref_price = ohlcv[0][4]  # Close of first candle
                alerts_df.at[idx, 'ref_price'] = ref_price

                for tf_name, tf_minutes in TIMEFRAME_MINUTES.items():
                    ret = calculate_forward_return(
                        exchange, row['ref_symbol'], row['timestamp_ms'],
                        ref_price, tf_minutes
                    )
                    alerts_df.at[idx, f'return_{tf_name}'] = ret
        except:
            pass

        processed += 1
        if processed % 10 == 0:
            print(f"  Processed {processed}/{len(alerts_df)} alerts...")
        time.sleep(0.1)

    # Analyze results
    print("\n" + "-"*40)
    print("GLOBAL LIQUIDATION RESULTS (Mean Reversion Hypothesis)")
    print("-"*40)
    print("Hypothesis: LONG liquidations → price bounces UP")
    print("           SHORT liquidations → price pulls back DOWN")

    analysis_results = {'global_liquidation': {}}

    for dominant in ['LONG', 'SHORT']:
        dom_df = alerts_df[alerts_df['dominant'] == dominant].copy()
        print(f"\n{dominant} LIQUIDATION CASCADES (n={len(dom_df)})")
        print("-"*30)

        analysis_results['global_liquidation'][dominant] = {'n': len(dom_df), 'timeframes': {}}

        for tf_name in TIMEFRAME_MINUTES.keys():
            col = f'return_{tf_name}'
            returns = dom_df[col].dropna()

            if len(returns) < 5:
                print(f"  {tf_name}: Insufficient data (n={len(returns)})")
                continue

            # Ensure numeric dtype
            returns = pd.to_numeric(returns, errors='coerce').dropna()
            if len(returns) < 5:
                print(f"  {tf_name}: Insufficient numeric data (n={len(returns)})")
                continue

            returns_arr = returns.astype(float).values

            mean_ret = float(np.mean(returns_arr))
            std_ret = float(np.std(returns_arr))

            # Mean reversion: LONG liq → expect UP (+), SHORT liq → expect DOWN (-)
            if dominant == 'LONG':
                correct = int((returns_arr > 0).sum())
            else:  # SHORT
                correct = int((returns_arr < 0).sum())

            accuracy = correct / len(returns_arr) * 100

            t_stat, t_pval = stats.ttest_1samp(returns_arr, 0)
            try:
                binom_result = stats.binomtest(correct, len(returns_arr), 0.5, alternative='greater')
                binom_pval = binom_result.pvalue
            except AttributeError:
                binom_pval = stats.binom_test(correct, len(returns_arr), 0.5, alternative='greater')

            analysis_results['global_liquidation'][dominant]['timeframes'][tf_name] = {
                'n': len(returns_arr),
                'mean_return': mean_ret,
                'std': std_ret,
                'accuracy': accuracy,
                't_pval': t_pval,
                'binom_pval': binom_pval
            }

            sig_marker = "**" if binom_pval < 0.05 else ""
            print(f"  {tf_name}: Mean={mean_ret:+.3f}%, Accuracy={accuracy:.1f}%, p={binom_pval:.4f} {sig_marker}")

    # Compare to symbol-specific liquidations
    print("\n" + "-"*40)
    print("GLOBAL vs SYMBOL-SPECIFIC COMPARISON")
    print("-"*40)

    return alerts_df, analysis_results


def analyze_regime_changes(conn, exchange):
    """Analyze regime change alerts for predictive edge."""
    print("\n" + "="*60)
    print("REGIME CHANGE PREDICTIVE EDGE ANALYSIS")
    print("="*60)

    query = """
    SELECT
        alert_id, symbol, timestamp, price, details
    FROM alerts
    WHERE alert_type = 'regime_change'
        AND details IS NOT NULL
        AND symbol IN ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT')
    ORDER BY timestamp
    """

    df = pd.read_sql_query(query, conn)
    print(f"Total regime change alerts (major pairs): {len(df)}")

    # Parse details
    results = []
    for idx, row in df.iterrows():
        try:
            details = json.loads(row['details']) if isinstance(row['details'], str) else row['details']

            new_regime = details.get('new_regime', '')
            old_regime = details.get('previous_regime', '')
            confidence = details.get('new_confidence', 0)
            trend_dir = details.get('trend_direction', 0)

            if not new_regime:
                continue

            timestamp_ms = int(row['timestamp'])

            results.append({
                'alert_id': row['alert_id'],
                'symbol': row['symbol'],
                'timestamp_ms': timestamp_ms,
                'old_regime': old_regime,
                'new_regime': new_regime,
                'confidence': float(confidence) if confidence else 0,
                'trend_direction': float(trend_dir) if trend_dir else 0
            })
        except Exception as e:
            continue

    alerts_df = pd.DataFrame(results)
    print(f"Valid regime change alerts: {len(alerts_df)}")
    print(f"Regime transitions: {alerts_df['new_regime'].value_counts().to_dict()}")

    # Fetch prices and calculate returns
    print("\nFetching prices and calculating returns...")

    for tf_name in TIMEFRAME_MINUTES.keys():
        alerts_df[f'return_{tf_name}'] = None
    alerts_df['price'] = None

    processed = 0
    for idx, row in alerts_df.iterrows():
        try:
            ohlcv = fetch_ohlcv_safe(exchange, row['symbol'], '1m',
                                      since=row['timestamp_ms'] - 60000, limit=5)
            if ohlcv:
                price = ohlcv[0][4]
                alerts_df.at[idx, 'price'] = price

                for tf_name, tf_minutes in TIMEFRAME_MINUTES.items():
                    ret = calculate_forward_return(
                        exchange, row['symbol'], row['timestamp_ms'],
                        price, tf_minutes
                    )
                    alerts_df.at[idx, f'return_{tf_name}'] = ret
        except:
            pass

        processed += 1
        if processed % 10 == 0:
            print(f"  Processed {processed}/{len(alerts_df)} alerts...")
        time.sleep(0.1)

    # Analyze by regime type
    print("\n" + "-"*40)
    print("REGIME CHANGE RESULTS BY NEW REGIME")
    print("-"*40)

    analysis_results = {'regime_change': {}}

    # Define expected direction for each regime
    regime_expected = {
        'moderate_uptrend': 'UP',      # Expect positive returns
        'strong_uptrend': 'UP',
        'moderate_downtrend': 'DOWN',  # Expect negative returns
        'strong_downtrend': 'DOWN',
        'high_volatility': 'NEUTRAL',  # No directional bias
        'ranging': 'NEUTRAL'
    }

    for regime in alerts_df['new_regime'].unique():
        regime_df = alerts_df[alerts_df['new_regime'] == regime].copy()
        print(f"\n{regime.upper()} (n={len(regime_df)})")
        print("-"*30)

        analysis_results['regime_change'][regime] = {'n': len(regime_df), 'timeframes': {}}

        expected = regime_expected.get(regime, 'NEUTRAL')

        for tf_name in TIMEFRAME_MINUTES.keys():
            col = f'return_{tf_name}'
            returns = regime_df[col].dropna()

            if len(returns) < 3:
                print(f"  {tf_name}: Insufficient data (n={len(returns)})")
                continue

            # Ensure numeric dtype
            returns = pd.to_numeric(returns, errors='coerce').dropna()
            if len(returns) < 3:
                print(f"  {tf_name}: Insufficient numeric data (n={len(returns)})")
                continue

            returns_arr = returns.astype(float).values

            mean_ret = float(np.mean(returns_arr))
            std_ret = float(np.std(returns_arr))

            # Calculate accuracy based on expected direction
            if expected == 'UP':
                correct = int((returns_arr > 0).sum())
            elif expected == 'DOWN':
                correct = int((returns_arr < 0).sum())
            else:
                # For neutral, just show absolute accuracy vs zero
                correct = int(max((returns_arr > 0).sum(), (returns_arr < 0).sum()))

            accuracy = correct / len(returns_arr) * 100

            t_stat, t_pval = stats.ttest_1samp(returns_arr, 0)
            try:
                binom_result = stats.binomtest(correct, len(returns_arr), 0.5, alternative='greater')
                binom_pval = binom_result.pvalue
            except AttributeError:
                binom_pval = stats.binom_test(correct, len(returns_arr), 0.5, alternative='greater')

            analysis_results['regime_change'][regime]['timeframes'][tf_name] = {
                'n': len(returns_arr),
                'mean_return': mean_ret,
                'std': std_ret,
                'accuracy': accuracy,
                't_pval': t_pval,
                'binom_pval': binom_pval,
                'expected': expected
            }

            sig_marker = "**" if binom_pval < 0.05 else ""
            print(f"  {tf_name}: Mean={mean_ret:+.3f}%, Dir Accuracy={accuracy:.1f}%, p={binom_pval:.4f} {sig_marker}")

    return alerts_df, analysis_results


def generate_summary_report(whale_results, global_results, regime_results):
    """Generate comprehensive summary report."""
    print("\n" + "="*70)
    print("EXTENDED ALERT PREDICTIVE EDGE - SUMMARY REPORT")
    print("="*70)

    print("\n┌─────────────────────────────────────────────────────────────────────┐")
    print("│                    EXECUTIVE SUMMARY                                │")
    print("└─────────────────────────────────────────────────────────────────────┘")

    # Compile best findings
    findings = []

    # Whale trades
    if 'whale_trade' in whale_results:
        for direction, data in whale_results['whale_trade'].items():
            for tf, metrics in data.get('timeframes', {}).items():
                if metrics.get('binom_pval', 1) < 0.05:
                    findings.append({
                        'type': f'Whale {direction}',
                        'timeframe': tf,
                        'accuracy': metrics['accuracy'],
                        'mean_return': metrics['mean_return'],
                        'p_value': metrics['binom_pval'],
                        'n': metrics['n']
                    })

    # Global liquidations
    if 'global_liquidation' in global_results:
        for dominant, data in global_results['global_liquidation'].items():
            for tf, metrics in data.get('timeframes', {}).items():
                if metrics.get('binom_pval', 1) < 0.05:
                    findings.append({
                        'type': f'GLOBAL {dominant} Liq',
                        'timeframe': tf,
                        'accuracy': metrics['accuracy'],
                        'mean_return': metrics['mean_return'],
                        'p_value': metrics['binom_pval'],
                        'n': metrics['n']
                    })

    # Regime changes
    if 'regime_change' in regime_results:
        for regime, data in regime_results['regime_change'].items():
            for tf, metrics in data.get('timeframes', {}).items():
                if metrics.get('binom_pval', 1) < 0.05:
                    findings.append({
                        'type': f'Regime→{regime}',
                        'timeframe': tf,
                        'accuracy': metrics['accuracy'],
                        'mean_return': metrics['mean_return'],
                        'p_value': metrics['binom_pval'],
                        'n': metrics['n']
                    })

    # Sort by accuracy
    findings.sort(key=lambda x: x['accuracy'], reverse=True)

    print("\nSTATISTICALLY SIGNIFICANT FINDINGS (p < 0.05):")
    print("-" * 70)
    print(f"{'Alert Type':<25} {'TF':<6} {'Acc%':<8} {'Mean Ret':<10} {'p-value':<10} {'n':<5}")
    print("-" * 70)

    for f in findings[:15]:  # Top 15
        print(f"{f['type']:<25} {f['timeframe']:<6} {f['accuracy']:.1f}%   {f['mean_return']:+.3f}%    {f['p_value']:.4f}     {f['n']}")

    if not findings:
        print("  No statistically significant findings at p < 0.05")

    print("\n" + "="*70)
    print("TRADING IMPLICATIONS")
    print("="*70)

    # Summarize actionable insights
    whale_buys = [f for f in findings if 'Whale BUY' in f['type']]
    whale_sells = [f for f in findings if 'Whale SELL' in f['type']]
    global_longs = [f for f in findings if 'GLOBAL LONG' in f['type']]
    global_shorts = [f for f in findings if 'GLOBAL SHORT' in f['type']]
    regime_trends = [f for f in findings if 'Regime' in f['type']]

    print("\n1. WHALE TRADES:")
    if whale_buys:
        best = max(whale_buys, key=lambda x: x['accuracy'])
        print(f"   BUY signals: {best['accuracy']:.1f}% accuracy at {best['timeframe']} (Follow the whale)")
    if whale_sells:
        best = max(whale_sells, key=lambda x: x['accuracy'])
        print(f"   SELL signals: {best['accuracy']:.1f}% accuracy at {best['timeframe']} (Follow the whale)")
    if not whale_buys and not whale_sells:
        print("   No significant predictive edge found")

    print("\n2. GLOBAL LIQUIDATION CASCADES:")
    if global_longs:
        best = max(global_longs, key=lambda x: x['accuracy'])
        print(f"   After LONG cascade: {best['accuracy']:.1f}% bounce accuracy at {best['timeframe']} (Mean reversion)")
    if global_shorts:
        best = max(global_shorts, key=lambda x: x['accuracy'])
        print(f"   After SHORT cascade: {best['accuracy']:.1f}% pullback accuracy at {best['timeframe']} (Mean reversion)")
    if not global_longs and not global_shorts:
        print("   No significant predictive edge found")

    print("\n3. REGIME CHANGES:")
    if regime_trends:
        for r in regime_trends[:3]:
            print(f"   {r['type']}: {r['accuracy']:.1f}% at {r['timeframe']}, mean={r['mean_return']:+.3f}%")
    else:
        print("   No significant predictive edge found")

    return findings


def main():
    """Main analysis function."""
    print("="*70)
    print("EXTENDED ALERT PREDICTIVE EDGE ANALYSIS")
    print("="*70)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {DB_PATH}")
    print(f"Timeframes: {list(TIMEFRAME_MINUTES.keys())}")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)

    # Initialize exchange
    print("\nInitializing Bybit connection...")
    exchange = get_bybit_client()

    # Test connection
    try:
        exchange.fetch_ticker('BTCUSDT')
        print("✓ Bybit connection successful")
    except Exception as e:
        print(f"✗ Bybit connection failed: {e}")
        return

    # Run analyses
    whale_df, whale_results = analyze_whale_trades(conn, exchange)
    global_df, global_results = analyze_global_liquidations(conn, exchange)
    regime_df, regime_results = analyze_regime_changes(conn, exchange)

    # Generate summary
    findings = generate_summary_report(whale_results, global_results, regime_results)

    # Save results
    print("\n" + "="*70)
    print("SAVING RESULTS")
    print("="*70)

    # Save DataFrames
    whale_df.to_csv('reports/whale_trade_edge_analysis.csv', index=False)
    global_df.to_csv('reports/global_liquidation_edge_analysis.csv', index=False)
    regime_df.to_csv('reports/regime_change_edge_analysis.csv', index=False)

    print("✓ Saved whale_trade_edge_analysis.csv")
    print("✓ Saved global_liquidation_edge_analysis.csv")
    print("✓ Saved regime_change_edge_analysis.csv")

    # Save summary JSON
    summary = {
        'analysis_date': datetime.now().isoformat(),
        'whale_trade': whale_results.get('whale_trade', {}),
        'global_liquidation': global_results.get('global_liquidation', {}),
        'regime_change': regime_results.get('regime_change', {}),
        'significant_findings': findings
    }

    with open('reports/extended_alert_edge_summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print("✓ Saved extended_alert_edge_summary.json")

    conn.close()
    print("\n✓ Analysis complete!")


if __name__ == "__main__":
    main()
