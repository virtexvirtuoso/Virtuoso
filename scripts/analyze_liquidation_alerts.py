#!/usr/bin/env python3
"""Analyze liquidation alerts from virtuoso.db for threshold assessment."""
# MIGRATION 2025-12-06: Changed from alerts.db to virtuoso.db

import sqlite3
from datetime import datetime
import re
from collections import defaultdict

def main():
    conn = sqlite3.connect("data/virtuoso.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, alert_type, symbol, title, message
        FROM alerts
        WHERE alert_type = 'liquidation'
        ORDER BY timestamp DESC
    """)
    alerts = cursor.fetchall()

    print("=" * 70)
    print("LIQUIDATION ALERT EFFECTIVENESS ANALYSIS")
    print("=" * 70)
    print(f"\nTotal liquidation alerts in database: {len(alerts)}")

    cascades = []
    single_liqs = []

    for row in alerts:
        ts, atype, symbol, title, message = row
        dt = datetime.fromtimestamp(ts)

        # Extract dollar amount
        amount_match = re.search(r'\$([0-9,]+)', message or "")
        amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0

        # Extract event count
        events_match = re.search(r'\((\d+) events?\)', message or "")
        events = int(events_match.group(1)) if events_match else 1

        data = {
            "ts": dt,
            "sym": symbol,
            "title": title,
            "amt": amount,
            "events": events,
            "msg": message
        }

        if "CASCADE" in (title or "").upper():
            cascades.append(data)
        else:
            single_liqs.append(data)

    print(f"\n📊 Alert Breakdown:")
    print(f"   Cascade alerts: {len(cascades)}")
    print(f"   Single liquidation alerts: {len(single_liqs)}")

    # Cascade analysis
    if cascades:
        amounts = [c["amt"] for c in cascades if c["amt"] > 0]
        if amounts:
            print(f"\n{'='*70}")
            print("CASCADE ALERT STATISTICS")
            print(f"{'='*70}")
            print(f"   Minimum: ${min(amounts):,.0f}")
            print(f"   Maximum: ${max(amounts):,.0f}")
            print(f"   Average: ${sum(amounts)/len(amounts):,.0f}")
            print(f"   Median:  ${sorted(amounts)[len(amounts)//2]:,.0f}")

            # Distribution buckets
            buckets = {
                "$200k-$500k": len([a for a in amounts if a < 500000]),
                "$500k-$1M": len([a for a in amounts if 500000 <= a < 1000000]),
                "$1M-$2M": len([a for a in amounts if 1000000 <= a < 2000000]),
                "$2M-$5M": len([a for a in amounts if 2000000 <= a < 5000000]),
                "$5M+": len([a for a in amounts if a >= 5000000])
            }

            print(f"\n📊 CASCADE VALUE DISTRIBUTION:")
            for bucket, count in buckets.items():
                pct = count/len(amounts)*100 if amounts else 0
                bar = "█" * int(pct/3)
                print(f"   {bucket:15} : {count:3} ({pct:5.1f}%) {bar}")

            # Cumulative analysis - what % would be filtered at each threshold
            print(f"\n📈 THRESHOLD IMPACT ANALYSIS:")
            print("   (How many alerts would be filtered at each threshold)")
            for thresh in [500000, 1000000, 2000000, 3000000, 5000000]:
                filtered = len([a for a in amounts if a < thresh])
                remaining = len(amounts) - filtered
                pct_filtered = filtered/len(amounts)*100
                print(f"   ${thresh/1e6:.1f}M threshold: {remaining:3} alerts remain ({pct_filtered:.0f}% filtered)")

    # By symbol analysis
    print(f"\n{'='*70}")
    print("CASCADE ALERTS BY SYMBOL")
    print(f"{'='*70}")
    symbol_stats = defaultdict(lambda: {"count": 0, "total": 0, "amounts": []})

    for c in cascades:
        sym = c["sym"]
        symbol_stats[sym]["count"] += 1
        symbol_stats[sym]["total"] += c["amt"]
        symbol_stats[sym]["amounts"].append(c["amt"])

    for sym, stats in sorted(symbol_stats.items(), key=lambda x: x[1]["count"], reverse=True):
        avg = stats["total"]/stats["count"] if stats["count"] else 0
        min_amt = min(stats["amounts"]) if stats["amounts"] else 0
        max_amt = max(stats["amounts"]) if stats["amounts"] else 0
        print(f"   {sym:15} : {stats['count']:3} alerts | avg ${avg:>12,.0f} | range ${min_amt:,.0f} - ${max_amt:,.0f}")

    # Time distribution
    print(f"\n{'='*70}")
    print("ALERTS BY DATE (Last 14 Days)")
    print(f"{'='*70}")
    date_counts = defaultdict(int)
    for c in cascades:
        date_key = c["ts"].strftime("%Y-%m-%d")
        date_counts[date_key] += 1

    for date, count in sorted(date_counts.items(), reverse=True)[:14]:
        bar = "█" * count
        print(f"   {date}: {count:3} alerts {bar}")

    # Single liquidations
    if single_liqs:
        amounts = [s["amt"] for s in single_liqs if s["amt"] > 0]
        if amounts:
            print(f"\n{'='*70}")
            print("SINGLE LIQUIDATION STATISTICS")
            print(f"{'='*70}")
            print(f"   Minimum: ${min(amounts):,.0f}")
            print(f"   Maximum: ${max(amounts):,.0f}")
            print(f"   Average: ${sum(amounts)/len(amounts):,.0f}")

    # Recent alerts detail
    print(f"\n{'='*70}")
    print("RECENT CASCADE ALERTS (Last 20)")
    print(f"{'='*70}")
    for c in cascades[:20]:
        print(f"   {c['ts'].strftime('%m-%d %H:%M')} | {c['sym']:10} | ${c['amt']:>12,.0f} | {c['events']:3} events | {c['title'][:35]}")

    # Recommendations
    print(f"\n{'='*70}")
    print("THRESHOLD RECOMMENDATIONS")
    print(f"{'='*70}")

    if cascades:
        amounts = [c["amt"] for c in cascades if c["amt"] > 0]
        if amounts:
            p75 = sorted(amounts)[int(len(amounts)*0.75)]
            p90 = sorted(amounts)[int(len(amounts)*0.90)]

            print(f"\n   Based on historical data:")
            print(f"   - 75th percentile: ${p75:,.0f}")
            print(f"   - 90th percentile: ${p90:,.0f}")
            print(f"\n   Suggested thresholds to reduce noise:")
            print(f"   - Symbol cascade: ${max(p75, 2000000):,.0f} (captures top 25% of events)")
            print(f"   - Global cascade: ${max(p90, 3000000):,.0f} (captures top 10% of events)")

    conn.close()

if __name__ == "__main__":
    main()
