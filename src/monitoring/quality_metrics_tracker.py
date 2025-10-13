"""
Quality Metrics Tracker

Tracks and logs quality metrics (consensus, confidence, disagreement) over time
to measure their impact on signal quality and trading performance.

This module provides:
- Quality metrics logging to file and database
- Statistical aggregation and analysis
- Performance impact measurement
- Threshold optimization support

Author: Virtuoso Team
Version: 1.0.0
"""

import logging
import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
import statistics


class QualityMetricsTracker:
    """
    Track and analyze quality metrics for confluence analysis.

    Logs quality metrics alongside signal outcomes to enable performance
    analysis and threshold optimization.
    """

    def __init__(self, log_dir: str = "logs/quality_metrics"):
        """
        Initialize quality metrics tracker.

        Args:
            log_dir: Directory for quality metrics logs
        """
        self.logger = logging.getLogger(__name__)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Current day's log file
        self.current_log_file = None
        self._ensure_log_file()

        # In-memory cache for aggregation
        self.metrics_cache: List[Dict[str, Any]] = []
        self.cache_size_limit = 1000

        self.logger.info(f"QualityMetricsTracker initialized - logging to {self.log_dir}")

    def _ensure_log_file(self) -> Path:
        """Ensure log file exists for current date."""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        log_file = self.log_dir / f"quality_metrics_{date_str}.jsonl"

        if log_file != self.current_log_file:
            self.current_log_file = log_file
            if not log_file.exists():
                log_file.touch()
                self.logger.info(f"Created new quality metrics log: {log_file}")

        return log_file

    def log_quality_metrics(
        self,
        symbol: str,
        confluence_score: float,
        consensus: float,
        confidence: float,
        disagreement: float,
        signal_type: Optional[str] = None,
        signal_filtered: bool = False,
        filter_reason: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        score_base: Optional[float] = None,
        quality_impact: Optional[float] = None
    ) -> None:
        """
        Log quality metrics for a confluence analysis with hybrid quality-adjusted scores.

        Args:
            symbol: Trading symbol
            confluence_score: Quality-adjusted confluence score (0-100)
            consensus: Agreement level (0-1)
            confidence: Combined quality (0-1)
            disagreement: Signal variance
            signal_type: Signal type if generated (BUY/SELL/HOLD)
            signal_filtered: Whether signal was filtered by quality checks
            filter_reason: Reason for filtering if applicable
            additional_data: Additional metadata to log
            score_base: Base score before quality adjustment (0-100)
            quality_impact: How much quality changed the score (positive = amplification, negative = suppression)
        """
        try:
            # Build metrics entry
            entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'timestamp_ms': int(time.time() * 1000),
                'symbol': symbol,
                'scores': {
                    'adjusted': round(confluence_score, 2),
                    'base': round(score_base, 2) if score_base is not None else None,
                    'quality_impact': round(quality_impact, 2) if quality_impact is not None else None
                },
                'quality_metrics': {
                    'consensus': round(consensus, 4),
                    'confidence': round(confidence, 4),
                    'disagreement': round(disagreement, 4)
                },
                'signal': {
                    'type': signal_type,
                    'filtered': signal_filtered,
                    'filter_reason': filter_reason
                }
            }

            # Add additional data if provided
            if additional_data:
                entry['additional'] = additional_data

            # Write to log file (JSONL format)
            log_file = self._ensure_log_file()
            with open(log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')

            # Add to in-memory cache for aggregation
            self.metrics_cache.append(entry)

            # Trim cache if too large
            if len(self.metrics_cache) > self.cache_size_limit:
                self.metrics_cache = self.metrics_cache[-self.cache_size_limit:]

            self.logger.debug(f"Logged quality metrics for {symbol}: "
                            f"confidence={confidence:.3f}, filtered={signal_filtered}")

        except Exception as e:
            self.logger.error(f"Error logging quality metrics: {e}", exc_info=True)

    def get_statistics(self, hours: int = 24, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get aggregated statistics for quality metrics.

        Args:
            hours: Number of hours to include in statistics
            symbol: Optional symbol filter

        Returns:
            Dictionary containing aggregated statistics
        """
        try:
            # Load recent metrics from cache
            cutoff_time = time.time() - (hours * 3600)
            cutoff_ms = int(cutoff_time * 1000)

            # Filter metrics
            filtered_metrics = [
                m for m in self.metrics_cache
                if m['timestamp_ms'] >= cutoff_ms and (symbol is None or m['symbol'] == symbol)
            ]

            if not filtered_metrics:
                return {'error': 'No metrics available for the specified period'}

            # Calculate statistics
            confidences = [m['quality_metrics']['confidence'] for m in filtered_metrics]
            consensuses = [m['quality_metrics']['consensus'] for m in filtered_metrics]
            disagreements = [m['quality_metrics']['disagreement'] for m in filtered_metrics]

            filtered_count = sum(1 for m in filtered_metrics if m['signal']['filtered'])
            total_count = len(filtered_metrics)

            stats = {
                'period_hours': hours,
                'symbol': symbol or 'all',
                'total_signals': total_count,
                'signals_filtered': filtered_count,
                'filter_rate': round(filtered_count / total_count * 100, 2) if total_count > 0 else 0,
                'confidence': {
                    'mean': round(statistics.mean(confidences), 4),
                    'median': round(statistics.median(confidences), 4),
                    'min': round(min(confidences), 4),
                    'max': round(max(confidences), 4),
                    'stdev': round(statistics.stdev(confidences), 4) if len(confidences) > 1 else 0
                },
                'consensus': {
                    'mean': round(statistics.mean(consensuses), 4),
                    'median': round(statistics.median(consensuses), 4),
                    'min': round(min(consensuses), 4),
                    'max': round(max(consensuses), 4)
                },
                'disagreement': {
                    'mean': round(statistics.mean(disagreements), 4),
                    'median': round(statistics.median(disagreements), 4),
                    'min': round(min(disagreements), 4),
                    'max': round(max(disagreements), 4)
                },
                'filter_reasons': self._count_filter_reasons(filtered_metrics)
            }

            return stats

        except Exception as e:
            self.logger.error(f"Error calculating statistics: {e}", exc_info=True)
            return {'error': str(e)}

    def _count_filter_reasons(self, metrics: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count filter reasons from metrics."""
        reasons = {}
        for m in metrics:
            if m['signal']['filtered'] and m['signal']['filter_reason']:
                reason = m['signal']['filter_reason']
                reasons[reason] = reasons.get(reason, 0) + 1
        return reasons

    def get_filter_effectiveness(self, hours: int = 24) -> Dict[str, Any]:
        """
        Analyze effectiveness of quality-based filtering.

        Args:
            hours: Number of hours to analyze

        Returns:
            Dictionary with filter effectiveness metrics
        """
        try:
            cutoff_time = time.time() - (hours * 3600)
            cutoff_ms = int(cutoff_time * 1000)

            filtered_metrics = [
                m for m in self.metrics_cache
                if m['timestamp_ms'] >= cutoff_ms
            ]

            if not filtered_metrics:
                return {'error': 'No metrics available'}

            # Split into filtered and passed signals
            filtered_signals = [m for m in filtered_metrics if m['signal']['filtered']]
            passed_signals = [m for m in filtered_metrics if not m['signal']['filtered']]

            # Calculate average quality metrics for each group
            def calc_avg_metrics(signals):
                if not signals:
                    return None
                return {
                    'avg_confidence': round(statistics.mean([s['quality_metrics']['confidence'] for s in signals]), 4),
                    'avg_consensus': round(statistics.mean([s['quality_metrics']['consensus'] for s in signals]), 4),
                    'avg_disagreement': round(statistics.mean([s['quality_metrics']['disagreement'] for s in signals]), 4),
                    'count': len(signals)
                }

            return {
                'period_hours': hours,
                'total_signals': len(filtered_metrics),
                'filtered_signals': calc_avg_metrics(filtered_signals),
                'passed_signals': calc_avg_metrics(passed_signals),
                'filter_rate': round(len(filtered_signals) / len(filtered_metrics) * 100, 2) if filtered_metrics else 0,
                'filter_reasons': self._count_filter_reasons(filtered_signals)
            }

        except Exception as e:
            self.logger.error(f"Error analyzing filter effectiveness: {e}", exc_info=True)
            return {'error': str(e)}
