#!/usr/bin/env python3
"""
Phase 3 Signal Analysis for October-November 2025
Analyzes signals with realistic TP/SL execution using historical price data.
"""

import json
import os
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
import math

# Use ccxt for fetching historical data
try:
    import ccxt.async_support as ccxt
except ImportError:
    import ccxt

SIGNAL_DIR = "/home/linuxuser/trading/Virtuoso_ccxt/reports/json/"
OUTPUT_FILE = "/home/linuxuser/trading/Virtuoso_ccxt/reports/signal_analysis_phase3_octnov_results.json"

# Wilson score confidence interval
def wilson_score_interval(successes: int, trials: int, confidence: float = 0.95) -> tuple:
    if trials == 0:
        return (0, 0, 0)
    z = 1.96
    p = successes / trials
    n = trials
    denominator = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
    lower = max(0, center - margin) * 100
    upper = min(1, center + margin) * 100
    point = p * 100
    return (round(lower, 2), round(upper, 2), round(point, 2))


def normalize_symbol(symbol: str) -> str:
    """Normalize symbol for Bybit API."""
    return symbol.replace('/', '').replace('-', '').replace('_', '').upper()


def parse_signal_file(filepath: str) -> dict:
    """Parse a signal JSON file and extract relevant fields."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Handle different JSON structures
        signal_data = data.get('signal', data)

        # Extract fields with fallbacks
        result = {
            'symbol': normalize_symbol(signal_data.get('symbol', '')),
            'signal_type': signal_data.get('signal', signal_data.get('type', 'UNKNOWN')),
            'entry_price': float(signal_data.get('entry_price', signal_data.get('entry', 0))),
            'take_profit': float(signal_data.get('take_profit', signal_data.get('tp', 0))),
            'stop_loss': float(signal_data.get('stop_loss', signal_data.get('sl', 0))),
            'confluence_score': float(signal_data.get('score', signal_data.get('confluence_score', 0))),
            'timestamp': signal_data.get('timestamp', signal_data.get('generated_at', '')),
            'rr_ratio': float(signal_data.get('risk_reward', signal_data.get('rr_ratio', 0))),
        }

        # Parse timestamp
        ts = result['timestamp']
        if isinstance(ts, str):
            for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']:
                try:
                    result['entry_time'] = datetime.strptime(ts.replace('Z', ''), fmt.replace('Z', ''))
                    break
                except:
                    continue
        elif isinstance(ts, (int, float)):
            result['entry_time'] = datetime.fromtimestamp(ts)

        # Normalize signal type
        sig = result['signal_type'].upper()
        if sig in ['BUY', 'LONG']:
            result['signal_type'] = 'LONG'
        elif sig in ['SELL', 'SHORT']:
            result['signal_type'] = 'SHORT'

        return result
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None


async def fetch_candles(exchange, symbol: str, since: datetime, limit: int = 200) -> list:
    """Fetch historical 1h candles from Bybit."""
    try:
        since_ms = int(since.timestamp() * 1000)
        candles = await exchange.fetch_ohlcv(
            symbol=symbol,
            timeframe='1h',
            since=since_ms,
            limit=limit
        )
        return candles
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None


def check_tpsl_hit(candles: list, entry_price: float, take_profit: float, stop_loss: float, signal_type: str) -> dict:
    """
    Check if TP or SL was hit in the candle sequence.
    Returns outcome, exit price, and hours held.
    """
    for i, candle in enumerate(candles):
        timestamp, open_p, high, low, close, volume = candle

        if signal_type == 'LONG':
            # For LONG: SL hit if low <= stop_loss, TP hit if high >= take_profit
            if low <= stop_loss:
                return {
                    'outcome': 'LOSS',
                    'exit_price': stop_loss,
                    'hours_held': i + 1,
                    'pnl_pct': round(((stop_loss - entry_price) / entry_price) * 100, 4)
                }
            elif high >= take_profit:
                return {
                    'outcome': 'WIN',
                    'exit_price': take_profit,
                    'hours_held': i + 1,
                    'pnl_pct': round(((take_profit - entry_price) / entry_price) * 100, 4)
                }

        elif signal_type == 'SHORT':
            # For SHORT: SL hit if high >= stop_loss, TP hit if low <= take_profit
            if high >= stop_loss:
                return {
                    'outcome': 'LOSS',
                    'exit_price': stop_loss,
                    'hours_held': i + 1,
                    'pnl_pct': round(((entry_price - stop_loss) / entry_price) * 100, 4)
                }
            elif low <= take_profit:
                return {
                    'outcome': 'WIN',
                    'exit_price': take_profit,
                    'hours_held': i + 1,
                    'pnl_pct': round(((entry_price - take_profit) / entry_price) * 100, 4)
                }

    # Neither hit within candle limit
    return {
        'outcome': 'OPEN',
        'exit_price': None,
        'hours_held': len(candles),
        'pnl_pct': None
    }


async def analyze_signals():
    """Main analysis function."""
    print("=" * 60)
    print("PHASE 3 ANALYSIS: October-November 2025 Signals")
    print("=" * 60)

    # Collect signal files for Oct-Nov 2025
    signal_files = []
    for f in os.listdir(SIGNAL_DIR):
        if f.endswith('.json') and ('202510' in f or '202511' in f):
            # Only signal files with direction indicator
            if any(x in f for x in ['LONG', 'SHORT', 'BUY', 'SELL']):
                signal_files.append(os.path.join(SIGNAL_DIR, f))

    print(f"\nFound {len(signal_files)} signal files for Oct-Nov 2025")

    # Parse all signals
    signals = []
    for filepath in signal_files:
        signal = parse_signal_file(filepath)
        if signal and signal.get('entry_time') and signal.get('entry_price', 0) > 0:
            signals.append(signal)

    print(f"Parsed {len(signals)} valid signals")

    # Initialize exchange
    exchange = ccxt.bybit({
        'enableRateLimit': True,
        'options': {'defaultType': 'linear'}
    })

    # Analyze each signal
    results = []
    semaphore = asyncio.Semaphore(3)  # Limit concurrent requests

    async def process_signal(signal):
        async with semaphore:
            try:
                symbol = signal['symbol']
                # Try with USDT suffix if not present
                if not symbol.endswith('USDT'):
                    symbol = symbol + 'USDT'

                # Format for Bybit
                bybit_symbol = f"{symbol.replace('USDT', '')}/USDT:USDT"

                candles = await fetch_candles(
                    exchange,
                    bybit_symbol,
                    signal['entry_time'],
                    limit=168  # 7 days max
                )

                if candles and len(candles) > 0:
                    result = check_tpsl_hit(
                        candles,
                        signal['entry_price'],
                        signal['take_profit'],
                        signal['stop_loss'],
                        signal['signal_type']
                    )

                    return {
                        'symbol': symbol,
                        'signal_type': signal['signal_type'],
                        'confluence_score': signal['confluence_score'],
                        'entry_price': signal['entry_price'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit': signal['take_profit'],
                        'entry_time': signal['entry_time'].strftime('%Y-%m-%d %H:%M'),
                        'rr_ratio': signal['rr_ratio'],
                        **result
                    }
            except Exception as e:
                print(f"Error processing {signal.get('symbol', 'unknown')}: {e}")
            return None

    # Process all signals
    print("\nFetching historical data and analyzing trades...")
    tasks = [process_signal(s) for s in signals]
    results = await asyncio.gather(*tasks)
    results = [r for r in results if r is not None]

    await exchange.close()

    # Filter to closed trades only
    closed_trades = [r for r in results if r['outcome'] in ['WIN', 'LOSS']]
    open_trades = [r for r in results if r['outcome'] == 'OPEN']

    print(f"\nClosed trades: {len(closed_trades)}")
    print(f"Open trades: {len(open_trades)}")

    # Calculate metrics
    if not closed_trades:
        print("No closed trades to analyze!")
        return

    wins = [t for t in closed_trades if t['outcome'] == 'WIN']
    losses = [t for t in closed_trades if t['outcome'] == 'LOSS']

    # Overall metrics
    total = len(closed_trades)
    win_count = len(wins)
    win_rate = (win_count / total) * 100 if total > 0 else 0

    avg_win_pnl = sum(t['pnl_pct'] for t in wins) / len(wins) if wins else 0
    avg_loss_pnl = sum(t['pnl_pct'] for t in losses) / len(losses) if losses else 0
    total_pnl = sum(t['pnl_pct'] for t in closed_trades)
    avg_pnl = total_pnl / total if total > 0 else 0

    profit_factor = abs(sum(t['pnl_pct'] for t in wins)) / abs(sum(t['pnl_pct'] for t in losses)) if losses and sum(t['pnl_pct'] for t in losses) != 0 else float('inf')

    ci = wilson_score_interval(win_count, total)

    # By signal type
    long_trades = [t for t in closed_trades if t['signal_type'] == 'LONG']
    short_trades = [t for t in closed_trades if t['signal_type'] == 'SHORT']

    long_wins = len([t for t in long_trades if t['outcome'] == 'WIN'])
    short_wins = len([t for t in short_trades if t['outcome'] == 'WIN'])

    long_ci = wilson_score_interval(long_wins, len(long_trades))
    short_ci = wilson_score_interval(short_wins, len(short_trades))

    # By symbol
    by_symbol = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': []})
    for t in closed_trades:
        sym = t['symbol']
        if t['outcome'] == 'WIN':
            by_symbol[sym]['wins'] += 1
        else:
            by_symbol[sym]['losses'] += 1
        by_symbol[sym]['pnl'].append(t['pnl_pct'])

    symbol_stats = {}
    for sym, data in by_symbol.items():
        total_sym = data['wins'] + data['losses']
        ci_sym = wilson_score_interval(data['wins'], total_sym)
        symbol_stats[sym] = {
            'total': total_sym,
            'wins': data['wins'],
            'win_rate': ci_sym[2],
            'ci_lower': ci_sym[0],
            'ci_upper': ci_sym[1],
            'avg_pnl': round(sum(data['pnl']) / len(data['pnl']), 4),
            'total_pnl': round(sum(data['pnl']), 2)
        }

    # By score range
    by_score = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': []})
    for t in closed_trades:
        score = t['confluence_score']
        if score < 60:
            bucket = '50-60'
        elif score < 70:
            bucket = '60-70'
        elif score < 80:
            bucket = '70-80'
        else:
            bucket = '80+'

        if t['outcome'] == 'WIN':
            by_score[bucket]['wins'] += 1
        else:
            by_score[bucket]['losses'] += 1
        by_score[bucket]['pnl'].append(t['pnl_pct'])

    score_stats = {}
    for bucket, data in by_score.items():
        total_bucket = data['wins'] + data['losses']
        if total_bucket > 0:
            ci_bucket = wilson_score_interval(data['wins'], total_bucket)
            score_stats[bucket] = {
                'total': total_bucket,
                'wins': data['wins'],
                'win_rate': ci_bucket[2],
                'ci_lower': ci_bucket[0],
                'ci_upper': ci_bucket[1],
                'avg_pnl': round(sum(data['pnl']) / len(data['pnl']), 4)
            }

    # Build results
    output = {
        'analysis_period': 'October-November 2025',
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'metrics': {
            'overall': {
                'total_signals': len(signals),
                'closed_trades': total,
                'open_trades': len(open_trades),
                'wins': win_count,
                'losses': len(losses),
                'win_rate': round(win_rate, 2),
                'win_rate_ci': f"{ci[2]}% [{ci[0]}% - {ci[1]}%]",
                'avg_pnl': round(avg_pnl, 4),
                'total_pnl': round(total_pnl, 2),
                'avg_win': round(avg_win_pnl, 4),
                'avg_loss': round(avg_loss_pnl, 4),
                'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else 'inf'
            },
            'by_type': {
                'LONG': {
                    'total': len(long_trades),
                    'wins': long_wins,
                    'win_rate': round((long_wins / len(long_trades) * 100) if long_trades else 0, 2),
                    'win_rate_ci': f"{long_ci[2]}% [{long_ci[0]}% - {long_ci[1]}%]",
                    'avg_pnl': round(sum(t['pnl_pct'] for t in long_trades) / len(long_trades), 4) if long_trades else 0,
                    'total_pnl': round(sum(t['pnl_pct'] for t in long_trades), 2)
                },
                'SHORT': {
                    'total': len(short_trades),
                    'wins': short_wins,
                    'win_rate': round((short_wins / len(short_trades) * 100) if short_trades else 0, 2),
                    'win_rate_ci': f"{short_ci[2]}% [{short_ci[0]}% - {short_ci[1]}%]",
                    'avg_pnl': round(sum(t['pnl_pct'] for t in short_trades) / len(short_trades), 4) if short_trades else 0,
                    'total_pnl': round(sum(t['pnl_pct'] for t in short_trades), 2)
                }
            },
            'by_symbol': dict(sorted(symbol_stats.items(), key=lambda x: x[1]['total'], reverse=True)),
            'by_score': score_stats
        },
        'trades': closed_trades
    }

    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"\nOverall Win Rate: {win_rate:.1f}% [{ci[0]}% - {ci[1]}%]")
    print(f"Total P&L: {total_pnl:.2f}%")
    print(f"Profit Factor: {profit_factor:.2f}")

    print(f"\nLONG Signals: {len(long_trades)} trades, {long_ci[2]}% win rate [{long_ci[0]}% - {long_ci[1]}%]")
    print(f"SHORT Signals: {len(short_trades)} trades, {short_ci[2]}% win rate [{short_ci[0]}% - {short_ci[1]}%]")

    print("\nBy Score Range:")
    for bucket in sorted(score_stats.keys()):
        stats = score_stats[bucket]
        print(f"  {bucket}: {stats['total']} trades, {stats['win_rate']}% win rate")

    print("\nBy Symbol:")
    for sym, stats in sorted(symbol_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:10]:
        print(f"  {sym}: {stats['total']} trades, {stats['win_rate']}% WR, {stats['total_pnl']:.2f}% P&L")

    # Save results
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nResults saved to: {OUTPUT_FILE}")

    return output


if __name__ == '__main__':
    asyncio.run(analyze_signals())
