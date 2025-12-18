"""
HTML Report Generator for Daily Performance Monitor

Generates styled HTML reports with charts and tables.
"""

import os
from datetime import datetime
from typing import List, Optional
from pathlib import Path

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class HTMLReportGenerator:
    """Generate HTML reports for performance monitoring."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("reports/daily")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, monitor, report_path: Optional[Path] = None) -> Path:
        """Generate complete HTML report with charts and tables.

        Args:
            monitor: DailyPerformanceMonitor instance with analysis data
            report_path: Optional custom output path

        Returns:
            Path to generated HTML file
        """
        if report_path is None:
            timestamp = datetime.now().strftime("%Y-%m-%d")
            report_path = self.output_dir / f"performance_{timestamp}.html"

        # Generate charts if matplotlib available
        chart_paths = []
        if MATPLOTLIB_AVAILABLE:
            chart_paths = self._generate_charts(monitor)

        # Build HTML
        html = self._build_html(monitor, chart_paths)

        # Write to file
        with open(report_path, 'w') as f:
            f.write(html)

        return report_path

    def _generate_charts(self, monitor) -> List[str]:
        """Generate performance charts using matplotlib."""
        chart_paths = []

        if not monitor.daily_stats:
            return chart_paths

        # Extract data for plotting
        dates = [datetime.strptime(s.date, "%Y-%m-%d") for s in reversed(monitor.daily_stats)]
        win_rates = [s.win_rate if s.closed > 0 else None for s in reversed(monitor.daily_stats)]
        avg_pnls = [s.avg_pnl if s.closed > 0 else None for s in reversed(monitor.daily_stats)]
        closed_counts = [s.closed for s in reversed(monitor.daily_stats)]

        # Chart 1: Win Rate Trend
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(dates, win_rates, marker='o', linewidth=2, color='#3498db', label='Win Rate')
        ax.axhline(y=50, color='green', linestyle='--', alpha=0.5, label='50% Target')
        ax.axhline(y=40, color='red', linestyle='--', alpha=0.5, label='40% Threshold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Win Rate (%)')
        ax.set_title('SHORT Signal Win Rate Trend')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.xticks(rotation=45)
        plt.tight_layout()

        win_rate_path = self.output_dir / "chart_win_rate.png"
        plt.savefig(win_rate_path, dpi=100, bbox_inches='tight')
        plt.close()
        chart_paths.append(str(win_rate_path.name))

        # Chart 2: P&L Trend
        fig, ax = plt.subplots(figsize=(10, 5))
        colors = ['green' if pnl and pnl > 0 else 'red' for pnl in avg_pnls]
        ax.bar(dates, avg_pnls, color=colors, alpha=0.7)
        ax.axhline(y=0, color='black', linewidth=1)
        ax.set_xlabel('Date')
        ax.set_ylabel('Avg P&L (%)')
        ax.set_title('SHORT Signal Daily P&L')
        ax.grid(True, alpha=0.3, axis='y')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.xticks(rotation=45)
        plt.tight_layout()

        pnl_path = self.output_dir / "chart_pnl.png"
        plt.savefig(pnl_path, dpi=100, bbox_inches='tight')
        plt.close()
        chart_paths.append(str(pnl_path.name))

        # Chart 3: Closed Signals Volume
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(dates, closed_counts, color='#34495e', alpha=0.7)
        ax.set_xlabel('Date')
        ax.set_ylabel('Closed Signals')
        ax.set_title('SHORT Signal Volume (Closed)')
        ax.grid(True, alpha=0.3, axis='y')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.xticks(rotation=45)
        plt.tight_layout()

        volume_path = self.output_dir / "chart_volume.png"
        plt.savefig(volume_path, dpi=100, bbox_inches='tight')
        plt.close()
        chart_paths.append(str(volume_path.name))

        return chart_paths

    def _build_html(self, monitor, chart_paths: List[str]) -> str:
        """Build complete HTML report."""
        html_parts = []

        # HTML header
        html_parts.append(self._html_header())

        # Title and summary
        html_parts.append(f"""
        <div class="container">
            <h1>📊 SHORT Signal Performance Report</h1>
            <p class="subtitle">Analysis Period: Last {monitor.days} Days | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        """)

        # Red flags section (if any)
        if monitor.red_flags:
            html_parts.append(self._build_red_flags_section(monitor.red_flags))
        else:
            html_parts.append("""
            <div class="alert alert-success">
                <strong>✅ All Clear!</strong> No performance issues detected.
            </div>
            """)

        # Cumulative stats
        if monitor.cumulative_stats:
            html_parts.append(self._build_cumulative_stats(monitor.cumulative_stats))

        # Charts
        if chart_paths:
            html_parts.append(self._build_charts_section(chart_paths))

        # Daily breakdown table
        html_parts.append(self._build_daily_table(monitor.daily_stats, monitor.min_win_rate, monitor.min_signals_for_alert))

        # Close container
        html_parts.append("</div>")

        # HTML footer
        html_parts.append(self._html_footer())

        return "\n".join(html_parts)

    def _html_header(self) -> str:
        """HTML header with CSS."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Report - SHORT Signals</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
            line-height: 1.6;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            padding: 40px;
        }

        h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.5em;
        }

        .subtitle {
            color: #7f8c8d;
            margin-bottom: 30px;
            font-size: 1.1em;
        }

        .alert {
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 25px;
            border-left: 5px solid;
        }

        .alert-success {
            background-color: #d4edda;
            border-color: #28a745;
            color: #155724;
        }

        .alert-warning {
            background-color: #fff3cd;
            border-color: #ffc107;
            color: #856404;
        }

        .alert-danger {
            background-color: #f8d7da;
            border-color: #dc3545;
            color: #721c24;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }

        .charts {
            margin: 30px 0;
        }

        .chart-container {
            margin-bottom: 30px;
            text-align: center;
        }

        .chart-container img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }

        th {
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }

        tbody tr:hover {
            background-color: #f5f5f5;
        }

        .positive {
            color: #28a745;
            font-weight: bold;
        }

        .negative {
            color: #dc3545;
            font-weight: bold;
        }

        .warning-row {
            background-color: #fff3cd !important;
        }

        .red-flags {
            margin: 30px 0;
        }

        .red-flag-item {
            padding: 12px 15px;
            margin-bottom: 10px;
            border-radius: 6px;
            border-left: 4px solid;
        }

        .red-flag-warning {
            background-color: #fff3cd;
            border-color: #ffc107;
            color: #856404;
        }

        .red-flag-critical {
            background-color: #f8d7da;
            border-color: #dc3545;
            color: #721c24;
        }

        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
"""

    def _html_footer(self) -> str:
        """HTML footer."""
        return """
    <div class="footer">
        <p>Generated by Virtuoso Trading System | Daily Performance Monitor</p>
    </div>
</body>
</html>
"""

    def _build_red_flags_section(self, red_flags: List) -> str:
        """Build red flags section."""
        html = ['<div class="red-flags">']
        html.append('<h2>🚨 Performance Issues Detected</h2>')

        for flag in red_flags:
            css_class = "red-flag-critical" if flag.severity == "critical" else "red-flag-warning"
            icon = "🚨" if flag.severity == "critical" else "⚠️"
            html.append(f'<div class="red-flag-item {css_class}">{icon} {flag.message}</div>')

        html.append('</div>')
        return "\n".join(html)

    def _build_cumulative_stats(self, stats) -> str:
        """Build cumulative statistics cards."""
        win_rate_color = "positive" if stats.win_rate >= 50 else "negative"
        pnl_color = "positive" if stats.avg_pnl >= 0 else "negative"

        return f"""
        <h2>Cumulative Performance (All-Time)</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{stats.total}</div>
                <div class="stat-label">Total Signals</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.closed}</div>
                <div class="stat-label">Closed Signals</div>
            </div>
            <div class="stat-card">
                <div class="stat-value {win_rate_color}">{stats.win_rate:.1f}%</div>
                <div class="stat-label">Win Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value {pnl_color}">{stats.avg_pnl:+.2f}%</div>
                <div class="stat-label">Avg P&L</div>
            </div>
        </div>
        """

    def _build_charts_section(self, chart_paths: List[str]) -> str:
        """Build charts section."""
        html = ['<div class="charts">']
        html.append('<h2>Performance Trends</h2>')

        for chart_path in chart_paths:
            html.append(f'<div class="chart-container"><img src="{chart_path}" alt="Chart"></div>')

        html.append('</div>')
        return "\n".join(html)

    def _build_daily_table(self, daily_stats: List, min_win_rate: float, min_signals: int) -> str:
        """Build daily breakdown table."""
        html = ['<h2>Daily Breakdown</h2>']
        html.append('<table>')
        html.append('<thead>')
        html.append('<tr>')
        html.append('<th>Date</th>')
        html.append('<th>Total</th>')
        html.append('<th>Closed</th>')
        html.append('<th>Wins</th>')
        html.append('<th>Losses</th>')
        html.append('<th>Win Rate</th>')
        html.append('<th>Avg P&L</th>')
        html.append('</tr>')
        html.append('</thead>')
        html.append('<tbody>')

        for stat in daily_stats:
            # Determine if row should be highlighted
            is_warning = (stat.closed >= min_signals and stat.win_rate < min_win_rate)
            row_class = 'class="warning-row"' if is_warning else ''

            win_rate_str = f"{stat.win_rate:.1f}%" if stat.closed > 0 else "N/A"
            avg_pnl_str = f"{stat.avg_pnl:+.2f}%" if stat.closed > 0 else "N/A"

            pnl_class = "positive" if stat.avg_pnl >= 0 else "negative"
            wr_class = "positive" if stat.win_rate >= 50 else "negative" if stat.closed > 0 else ""

            indicator = " ⚠️" if is_warning else ""

            html.append(f'<tr {row_class}>')
            html.append(f'<td>{stat.date}{indicator}</td>')
            html.append(f'<td>{stat.total}</td>')
            html.append(f'<td>{stat.closed}</td>')
            html.append(f'<td>{stat.wins}</td>')
            html.append(f'<td>{stat.losses}</td>')
            html.append(f'<td class="{wr_class}">{win_rate_str}</td>')
            html.append(f'<td class="{pnl_class}">{avg_pnl_str}</td>')
            html.append('</tr>')

        html.append('</tbody>')
        html.append('</table>')

        return "\n".join(html)
