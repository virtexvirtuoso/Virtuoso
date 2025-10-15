#!/usr/bin/env python3
"""
Confluence System Performance Tracker (Post-Fix Monitoring)

Tracks key metrics for the confluence system after applying the 2025-10-15 fixes:
1. Amplification rate (target: 8-12%)
2. Mean confidence levels (target: 0.30-0.40)
3. Confidence distribution
4. Comparison of old vs new thresholds

Usage:
    # Run locally against VPS logs
    ./scripts/monitoring/track_confluence_performance.py

    # Or on VPS directly
    ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && python3 scripts/monitoring/track_confluence_performance.py"

Outputs:
    - Daily summary to stdout
    - Detailed CSV to logs/confluence_metrics/YYYY-MM-DD.csv
"""

import re
import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class ConfluencePerformanceTracker:
    """Track and analyze confluence system performance"""

    # New thresholds (2025-10-15)
    NEW_CONF_THRESHOLD = 0.50
    NEW_CONS_THRESHOLD = 0.75

    # Old thresholds (for comparison)
    OLD_CONF_THRESHOLD = 0.70
    OLD_CONS_THRESHOLD = 0.80

    def __init__(self, log_source: str = "vps"):
        """
        Initialize tracker

        Args:
            log_source: "vps" for SSH logs or "local" for local file
        """
        self.log_source = log_source
        self.confidence_values: List[float] = []
        self.consensus_values: List[float] = []
        self.adjustment_types: List[str] = []
        self.symbols: List[str] = []
        self.timestamps: List[datetime] = []

    def fetch_logs(self, since: str = "1 hour ago") -> str:
        """
        Fetch logs from VPS or local source

        Args:
            since: Time period (e.g., "1 hour ago", "24 hours ago")

        Returns:
            Log content as string
        """
        if self.log_source == "vps":
            import subprocess
            cmd = f"ssh vps \"journalctl -u virtuoso-trading --since '{since}' | grep -E '(confidence|consensus|amplified|dampened)'\""
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout
        else:
            # Local log file (adjust path as needed)
            log_path = Path("/var/log/virtuoso-trading/monitoring.log")
            if log_path.exists():
                return log_path.read_text()
            return ""

    def parse_logs(self, log_content: str):
        """Parse logs and extract confluence metrics"""

        # Pattern to match "Quality metrics - Consensus: X, Confidence: Y, Disagreement: Z"
        quality_metrics_pattern = r"Quality metrics - Consensus:\s+(\d+\.\d+),\s+Confidence:\s+(\d+\.\d+),\s+Disagreement:\s+(\d+\.\d+)"

        symbol_pattern = r"([A-Z0-9]+USDT)"
        timestamp_pattern = r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"

        for line in log_content.split('\n'):
            # Look for "Quality metrics" line which has both consensus and confidence
            metrics_match = re.search(quality_metrics_pattern, line)

            if metrics_match:
                consensus = float(metrics_match.group(1))
                confidence = float(metrics_match.group(2))
                # disagreement = float(metrics_match.group(3))  # Can use later if needed

                self.consensus_values.append(consensus)
                self.confidence_values.append(confidence)

                # Determine adjustment type based on thresholds
                if confidence > self.NEW_CONF_THRESHOLD and consensus > self.NEW_CONS_THRESHOLD:
                    self.adjustment_types.append("amplified")
                else:
                    self.adjustment_types.append("dampened")

                # Extract symbol from line
                symbol_match = re.search(symbol_pattern, line)
                if symbol_match:
                    self.symbols.append(symbol_match.group(1))
                else:
                    self.symbols.append("UNKNOWN")

                # Extract timestamp
                ts_match = re.search(timestamp_pattern, line)
                if ts_match:
                    self.timestamps.append(datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M:%S"))
                else:
                    self.timestamps.append(datetime.now())

    def calculate_metrics(self) -> Dict:
        """Calculate performance metrics"""

        if not self.confidence_values:
            return {
                "error": "No data collected",
                "sample_size": 0
            }

        n = len(self.confidence_values)
        amplified_count = sum(1 for adj in self.adjustment_types if adj == "amplified")
        dampened_count = sum(1 for adj in self.adjustment_types if adj == "dampened")

        # Amplification rate
        amplification_rate = (amplified_count / n) * 100 if n > 0 else 0

        # Confidence statistics
        mean_confidence = sum(self.confidence_values) / n
        sorted_conf = sorted(self.confidence_values)
        median_confidence = sorted_conf[n // 2]
        p90_confidence = sorted_conf[int(n * 0.9)] if n > 10 else sorted_conf[-1]
        p99_confidence = sorted_conf[int(n * 0.99)] if n > 100 else sorted_conf[-1]

        # Consensus statistics
        if self.consensus_values:
            mean_consensus = sum(self.consensus_values) / len(self.consensus_values)
        else:
            mean_consensus = 0.0

        # Would have been amplified under old thresholds?
        would_be_amplified_old = 0
        for i in range(min(len(self.confidence_values), len(self.consensus_values))):
            if (self.confidence_values[i] > self.OLD_CONF_THRESHOLD and
                self.consensus_values[i] > self.OLD_CONS_THRESHOLD):
                would_be_amplified_old += 1

        old_amplification_rate = (would_be_amplified_old / n) * 100 if n > 0 else 0

        return {
            "sample_size": n,
            "time_period": f"{self.timestamps[0]} to {self.timestamps[-1]}" if self.timestamps else "Unknown",

            # Amplification metrics
            "amplification_rate": amplification_rate,
            "amplified_count": amplified_count,
            "dampened_count": dampened_count,
            "old_threshold_rate": old_amplification_rate,
            "amplification_improvement": amplification_rate - old_amplification_rate,

            # Confidence metrics
            "mean_confidence": mean_confidence,
            "median_confidence": median_confidence,
            "p90_confidence": p90_confidence,
            "p99_confidence": p99_confidence,

            # Consensus metrics
            "mean_consensus": mean_consensus,

            # Distribution
            "confidence_bins": self._bin_distribution(self.confidence_values),
            "unique_symbols": len(set(self.symbols)),
        }

    def _bin_distribution(self, values: List[float]) -> Dict[str, int]:
        """Bin values into ranges for distribution analysis"""
        bins = {
            "0.0-0.1": 0,
            "0.1-0.2": 0,
            "0.2-0.3": 0,
            "0.3-0.4": 0,
            "0.4-0.5": 0,
            "0.5-0.6": 0,
            "0.6-0.7": 0,
            "0.7-0.8": 0,
            "0.8-0.9": 0,
            "0.9-1.0": 0,
        }

        for v in values:
            if v < 0.1:
                bins["0.0-0.1"] += 1
            elif v < 0.2:
                bins["0.1-0.2"] += 1
            elif v < 0.3:
                bins["0.2-0.3"] += 1
            elif v < 0.4:
                bins["0.3-0.4"] += 1
            elif v < 0.5:
                bins["0.4-0.5"] += 1
            elif v < 0.6:
                bins["0.5-0.6"] += 1
            elif v < 0.7:
                bins["0.6-0.7"] += 1
            elif v < 0.8:
                bins["0.7-0.8"] += 1
            elif v < 0.9:
                bins["0.8-0.9"] += 1
            else:
                bins["0.9-1.0"] += 1

        return bins

    def print_report(self, metrics: Dict):
        """Print formatted report"""

        print("\n" + "=" * 80)
        print("CONFLUENCE SYSTEM PERFORMANCE REPORT")
        print("Post-Fix Monitoring (2025-10-15 Deployment)")
        print("=" * 80)

        if "error" in metrics:
            print(f"\n❌ {metrics['error']}")
            return

        print(f"\n📊 Sample Size: {metrics['sample_size']} signals")
        print(f"⏰ Time Period: {metrics['time_period']}")
        print(f"🎯 Unique Symbols: {metrics['unique_symbols']}")

        print("\n" + "-" * 80)
        print("AMPLIFICATION METRICS")
        print("-" * 80)

        amp_rate = metrics['amplification_rate']
        target = "🎯 TARGET MET" if 8 <= amp_rate <= 12 else "⚠️  NEEDS TUNING"

        print(f"\n  Amplification Rate: {amp_rate:.2f}% {target}")
        print(f"    ├─ Amplified: {metrics['amplified_count']} signals")
        print(f"    └─ Dampened:  {metrics['dampened_count']} signals")

        print(f"\n  OLD Threshold Rate: {metrics['old_threshold_rate']:.2f}%")
        print(f"  Improvement: +{metrics['amplification_improvement']:.2f}% vs old thresholds")

        if metrics['amplification_improvement'] > 0:
            print(f"  ✅ Fix is working! Amplification increased from old 0% baseline")

        print("\n" + "-" * 80)
        print("CONFIDENCE METRICS")
        print("-" * 80)

        mean_conf = metrics['mean_confidence']
        conf_target = "🎯 TARGET MET" if 0.30 <= mean_conf <= 0.40 else "⚠️  OUTSIDE TARGET"

        print(f"\n  Mean Confidence: {mean_conf:.3f} {conf_target}")
        print(f"  Median:          {metrics['median_confidence']:.3f}")
        print(f"  90th Percentile: {metrics['p90_confidence']:.3f}")
        print(f"  99th Percentile: {metrics['p99_confidence']:.3f}")

        print(f"\n  Mean Consensus:  {metrics['mean_consensus']:.3f}")

        print("\n" + "-" * 80)
        print("CONFIDENCE DISTRIBUTION")
        print("-" * 80)

        bins = metrics['confidence_bins']
        max_count = max(bins.values()) if bins else 1

        print()
        for bin_range, count in bins.items():
            pct = (count / metrics['sample_size']) * 100 if metrics['sample_size'] > 0 else 0
            bar_width = int((count / max_count) * 40) if max_count > 0 else 0
            bar = "█" * bar_width

            # Highlight threshold bins
            marker = ""
            if bin_range == "0.5-0.6":
                marker = " ← NEW THRESHOLD (0.50)"
            elif bin_range == "0.7-0.8":
                marker = " ← OLD THRESHOLD (0.70)"

            print(f"  {bin_range}: {bar} {count:4d} ({pct:5.1f}%){marker}")

        print("\n" + "=" * 80)
        print("SUCCESS CRITERIA")
        print("=" * 80)

        criteria = [
            ("Amplification Rate 8-12%", 8 <= amp_rate <= 12),
            ("Mean Confidence 0.30-0.40", 0.30 <= mean_conf <= 0.40),
            ("Improvement vs Old", metrics['amplification_improvement'] > 0),
            ("Sample Size > 100", metrics['sample_size'] > 100),
        ]

        print()
        for criterion, met in criteria:
            status = "✅" if met else "❌"
            print(f"  {status} {criterion}")

        all_met = all(met for _, met in criteria)

        print("\n" + "=" * 80)
        if all_met:
            print("✅ SYSTEM PERFORMING AS EXPECTED")
        else:
            print("⚠️  SYSTEM NEEDS MONITORING - Some criteria not met")
        print("=" * 80)

    def save_csv(self, metrics: Dict, output_dir: str = "logs/confluence_metrics"):
        """Save detailed data to CSV"""

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        csv_path = Path(output_dir) / f"confluence_metrics_{timestamp}.csv"

        with open(csv_path, 'w') as f:
            # Header
            f.write("timestamp,symbol,confidence,consensus,adjustment\n")

            # Data rows
            for i in range(len(self.confidence_values)):
                ts = self.timestamps[i].strftime("%Y-%m-%d %H:%M:%S") if i < len(self.timestamps) else ""
                symbol = self.symbols[i] if i < len(self.symbols) else ""
                confidence = self.confidence_values[i]
                consensus = self.consensus_values[i] if i < len(self.consensus_values) else ""
                adjustment = self.adjustment_types[i] if i < len(self.adjustment_types) else ""

                f.write(f"{ts},{symbol},{confidence},{consensus},{adjustment}\n")

        print(f"\n💾 Detailed data saved to: {csv_path}")


def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description="Track confluence system performance")
    parser.add_argument("--since", default="24 hours ago", help="Time period to analyze")
    parser.add_argument("--source", choices=["vps", "local"], default="vps", help="Log source")
    parser.add_argument("--save-csv", action="store_true", help="Save detailed CSV")

    args = parser.parse_args()

    print(f"\n🔍 Fetching logs from {args.source} (since: {args.since})...")

    tracker = ConfluencePerformanceTracker(log_source=args.source)

    # Fetch and parse logs
    log_content = tracker.fetch_logs(since=args.since)
    tracker.parse_logs(log_content)

    # Calculate metrics
    metrics = tracker.calculate_metrics()

    # Print report
    tracker.print_report(metrics)

    # Save CSV if requested
    if args.save_csv:
        tracker.save_csv(metrics)


if __name__ == "__main__":
    main()
