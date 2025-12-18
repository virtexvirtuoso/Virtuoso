#!/usr/bin/env python3
"""Analyze liquidation cascade alerts from VPS database."""

import sqlite3
import json
from datetime import datetime
from collections import defaultdict

def main():
    # MIGRATION 2025-12-06: Changed from alerts.db to virtuoso.db
    conn = sqlite3.connect('data/virtuoso.db')
    cursor = conn.cursor()

    # Get alert type counts
    cursor.execute('SELECT alert_type, COUNT(*) as cnt FROM alerts GROUP BY alert_type ORDER BY cnt DESC')
    print('=' * 70)
    print('ALERT TYPES IN DATABASE')
    print('=' * 70)
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]}')

    print()

    # Get liquidation cascade alerts with details
    cursor.execute('''
        SELECT timestamp, symbol, message, title, data
        FROM alerts
        WHERE alert_type = 'liquidation'
        ORDER BY timestamp DESC
        LIMIT 200
    ''')
    alerts = cursor.fetchall()

    print('=' * 70)
    print(f'LIQUIDATION CASCADE ALERTS ({len(alerts)} found)')
    print('=' * 70)

    amounts = []
    symbol_data = defaultdict(list)
    global_alerts = []
    symbol_alerts = []

    for row in alerts:
        ts, symbol, message, title, data_str = row
        dt = datetime.fromtimestamp(ts)

        try:
            data = json.loads(data_str) if data_str else {}
            total_value = data.get('total_value', 0)
            count = data.get('count', 0)
            is_global = data.get('is_global', False)

            if total_value > 0:
                amounts.append(total_value)
                symbol_data[symbol].append({
                    'value': total_value,
                    'count': count,
                    'is_global': is_global,
                    'timestamp': ts
                })

                if is_global:
                    global_alerts.append(total_value)
                else:
                    symbol_alerts.append(total_value)

            alert_type = "GLOBAL" if is_global else "SYMBOL"
            print(f'  {dt.strftime("%m-%d %H:%M")} | {symbol:12} | ${total_value:>12,.0f} | {count:3} events | {alert_type}')
        except Exception as e:
            print(f'  {dt.strftime("%m-%d %H:%M")} | {symbol:12} | Parse error: {e}')

    if amounts:
        amounts_clean = [a for a in amounts if a > 0]

        print()
        print('=' * 70)
        print('OVERALL STATISTICS')
        print('=' * 70)
        print(f'  Total alerts: {len(amounts_clean)}')
        print(f'  Min:    ${min(amounts_clean):>15,.0f}')
        print(f'  Max:    ${max(amounts_clean):>15,.0f}')
        print(f'  Mean:   ${sum(amounts_clean)/len(amounts_clean):>15,.0f}')
        print(f'  Median: ${sorted(amounts_clean)[len(amounts_clean)//2]:>15,.0f}')

        # Percentiles
        sorted_amounts = sorted(amounts_clean)
        p25 = sorted_amounts[int(len(sorted_amounts)*0.25)]
        p50 = sorted_amounts[int(len(sorted_amounts)*0.50)]
        p75 = sorted_amounts[int(len(sorted_amounts)*0.75)]
        p90 = sorted_amounts[int(len(sorted_amounts)*0.90)]
        p95 = sorted_amounts[int(len(sorted_amounts)*0.95)]

        print()
        print('  Percentiles:')
        print(f'    25th: ${p25:>15,.0f}')
        print(f'    50th: ${p50:>15,.0f}')
        print(f'    75th: ${p75:>15,.0f}')
        print(f'    90th: ${p90:>15,.0f}')
        print(f'    95th: ${p95:>15,.0f}')

        # Global vs Symbol breakdown
        if global_alerts and symbol_alerts:
            print()
            print('=' * 70)
            print('GLOBAL vs SYMBOL ALERTS')
            print('=' * 70)
            print(f'  Global alerts: {len(global_alerts)}')
            print(f'    Min:    ${min(global_alerts):>15,.0f}')
            print(f'    Max:    ${max(global_alerts):>15,.0f}')
            print(f'    Mean:   ${sum(global_alerts)/len(global_alerts):>15,.0f}')
            print()
            print(f'  Symbol alerts: {len(symbol_alerts)}')
            print(f'    Min:    ${min(symbol_alerts):>15,.0f}')
            print(f'    Max:    ${max(symbol_alerts):>15,.0f}')
            print(f'    Mean:   ${sum(symbol_alerts)/len(symbol_alerts):>15,.0f}')

        print()
        print('=' * 70)
        print('VALUE DISTRIBUTION')
        print('=' * 70)
        thresholds = [200000, 300000, 500000, 750000, 1000000, 1500000, 2000000, 3000000, 5000000]
        for thresh in thresholds:
            below = len([a for a in amounts_clean if a < thresh])
            above = len(amounts_clean) - below
            pct_below = below/len(amounts_clean)*100
            bar = '#' * int(pct_below/5)
            print(f'  < ${thresh/1e6:>4.1f}M: {below:4} ({pct_below:5.1f}%) | >= {above:4} | {bar}')

        print()
        print('=' * 70)
        print('THRESHOLD IMPACT ANALYSIS')
        print('=' * 70)
        print('  (How many alerts would be generated at each threshold)')
        for thresh in [200000, 300000, 500000, 1000000, 2000000, 3000000, 5000000]:
            remaining = len([a for a in amounts_clean if a >= thresh])
            filtered = len(amounts_clean) - remaining
            pct = remaining/len(amounts_clean)*100
            print(f'  ${thresh/1e6:>4.1f}M threshold: {remaining:4} alerts ({pct:5.1f}% of original) | {filtered} filtered')

        print()
        print('=' * 70)
        print('TOP SYMBOLS BY ALERT COUNT')
        print('=' * 70)
        for sym, sym_data in sorted(symbol_data.items(), key=lambda x: len(x[1]), reverse=True)[:15]:
            vals = [d['value'] for d in sym_data]
            avg_val = sum(vals)/len(vals)
            print(f'  {sym:12}: {len(sym_data):3} alerts | avg ${avg_val:>12,.0f} | range ${min(vals):,.0f} - ${max(vals):,.0f}')

        print()
        print('=' * 70)
        print('THRESHOLD RECOMMENDATIONS')
        print('=' * 70)

        # Current threshold is $200k
        current_thresh = 200000
        current_alerts = len([a for a in amounts_clean if a >= current_thresh])

        print(f'  Current symbol threshold: ${current_thresh/1e6:.1f}M')
        print(f'  Current global threshold: $5.0M')
        print(f'  Alerts at current threshold: {current_alerts}')
        print()

        # Recommendations based on data
        if p75 > current_thresh:
            print(f'  RECOMMENDATION: Consider raising symbol threshold to ${p75/1e6:.1f}M')
            print(f'    This would capture top 25% of events ({len([a for a in amounts_clean if a >= p75])} alerts)')

        if p90 > 5000000:
            print(f'  RECOMMENDATION: Consider raising global threshold to ${p90/1e6:.1f}M')
            print(f'    This would capture top 10% of events ({len([a for a in amounts_clean if a >= p90])} alerts)')

        # Alert frequency
        print()
        print('=' * 70)
        print('ALERT FREQUENCY BY DAY')
        print('=' * 70)
        date_counts = defaultdict(int)
        for row in alerts:
            ts = row[0]
            dt = datetime.fromtimestamp(ts)
            date_key = dt.strftime('%Y-%m-%d')
            date_counts[date_key] += 1

        for date, count in sorted(date_counts.items(), reverse=True)[:14]:
            bar = '#' * count
            print(f'  {date}: {count:3} alerts {bar}')

    conn.close()

if __name__ == "__main__":
    main()
