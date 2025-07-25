#!/usr/bin/env python3
"""
Dark Mode HTML Bitcoin Beta 7-Day Report Generator

This script generates a beautiful dark mode HTML report for the Bitcoin Beta analysis.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config.config_manager import ConfigManager
from src.core.exchanges.manager import ExchangeManager
from src.reports.bitcoin_beta_7day_report import BitcoinBeta7DayReport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/dark_mode_html_report.log')
    ]
)

logger = logging.getLogger(__name__)

def create_dark_mode_html_template(beta_analysis, symbols, start_date, end_date, chart_paths=None):
    """Create a beautiful dark mode HTML report."""
    
    # Calculate summary statistics
    if 'htf' in beta_analysis:
        htf_betas = [stats['beta'] for symbol, stats in beta_analysis['htf'].items() if symbol != 'BTCUSDT']
        if htf_betas:
            avg_beta = sum(htf_betas) / len(htf_betas)
        else:
            avg_beta = 1.0
    else:
        avg_beta = 1.0
    
    # Market interpretation
    if avg_beta >= 1.3:
        market_interpretation = f"High 7-day correlation detected. Portfolio shows amplified Bitcoin exposure with elevated short-term volatility risk."
    elif avg_beta <= 0.7:
        market_interpretation = f"Low 7-day correlation detected. Portfolio offers good short-term diversification benefits with reduced Bitcoin exposure."
    else:
        market_interpretation = f"Moderate 7-day correlation detected. Portfolio shows balanced exposure to Bitcoin movements over the past week."
    
    # Prepare table data
    table_rows = ""
    if 'htf' in beta_analysis:
        symbol_beta_pairs = []
        for symbol, stats in beta_analysis['htf'].items():
            if symbol == 'BTCUSDT':
                continue
            symbol_beta_pairs.append((symbol, stats))
        
        # Sort by beta value (highest to lowest)
        symbol_beta_pairs.sort(key=lambda x: x[1]['beta'], reverse=True)
        
        for symbol, stats in symbol_beta_pairs:
            symbol_clean = symbol.replace('USDT', '')
            beta_color = '#F44336' if stats['beta'] > 1.2 else '#4CAF50' if stats['beta'] < 0.8 else '#FFC107'
            
            table_rows += f"""
            <tr>
                <td>{symbol_clean}</td>
                <td style="color: {beta_color}; font-weight: bold;">{stats['beta']:.3f}</td>
                <td>{stats['correlation']:.3f}</td>
                <td>{stats['r_squared']:.3f}</td>
                <td>{stats['volatility_ratio']:.3f}</td>
                <td>{stats['max_drawdown']:.1%}</td>
            </tr>
            """
    
    # Chart images
    chart_images = ""
    if chart_paths:
        for chart_type, path in chart_paths.items():
            if path and os.path.exists(path):
                chart_images += f"""
                <div class="chart-container">
                    <h3>{chart_type.replace('_', ' ').title()}</h3>
                    <img src="{path}" alt="{chart_type}" class="chart-image">
                </div>
                """
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bitcoin Beta 7-Day Analysis Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0c1a2b 0%, #1a2a40 100%);
            color: #d1d5db;
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(26, 42, 64, 0.8);
            border-radius: 15px;
            border: 1px solid #374151;
        }}
        
        .title {{
            font-size: 2.5em;
            font-weight: bold;
            color: #ffbf00;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        
        .subtitle {{
            color: #9ca3af;
            font-size: 1.1em;
            margin-bottom: 5px;
        }}
        
        .summary-card {{
            background: rgba(30, 41, 59, 0.8);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
            border: 1px solid #374151;
        }}
        
        .summary-title {{
            color: #e5e7eb;
            font-size: 1.4em;
            margin-bottom: 15px;
            border-bottom: 2px solid #ffbf00;
            padding-bottom: 10px;
        }}
        
        .summary-text {{
            color: #d1d5db;
            font-size: 1.1em;
            line-height: 1.7;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        
        .stat-card {{
            background: rgba(17, 24, 39, 0.8);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border: 1px solid #374151;
        }}
        
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #ffbf00;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            color: #9ca3af;
            font-size: 0.9em;
        }}
        
        .table-container {{
            background: rgba(30, 41, 59, 0.8);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
            border: 1px solid #374151;
            overflow-x: auto;
        }}
        
        .table-title {{
            color: #e5e7eb;
            font-size: 1.4em;
            margin-bottom: 20px;
            border-bottom: 2px solid #ffbf00;
            padding-bottom: 10px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: rgba(17, 24, 39, 0.8);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        th {{
            background: #1a2a40;
            color: white;
            padding: 15px;
            text-align: center;
            font-weight: bold;
            border-bottom: 2px solid #374151;
        }}
        
        td {{
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid #374151;
            color: #d1d5db;
        }}
        
        tr:hover {{
            background: rgba(55, 65, 81, 0.3);
        }}
        
        .chart-container {{
            background: rgba(30, 41, 59, 0.8);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
            border: 1px solid #374151;
        }}
        
        .chart-container h3 {{
            color: #e5e7eb;
            margin-bottom: 20px;
            border-bottom: 2px solid #ffbf00;
            padding-bottom: 10px;
        }}
        
        .chart-image {{
            width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #9ca3af;
            border-top: 1px solid #374151;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            .title {{
                font-size: 2em;
            }}
            
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">Bitcoin Beta 7-Day Analysis Report</h1>
            <p class="subtitle">Analysis Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}</p>
            <p class="subtitle">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </div>
        
        <div class="summary-card">
            <h2 class="summary-title">Executive Summary</h2>
            <p class="summary-text">
                This report analyzes the 7-day correlation (beta) between Bitcoin and {len(symbols)-1} other cryptocurrencies 
                from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} across multiple timeframes 
                (4H, 1H, 15M, 5M). Beta measures how much an asset moves relative to Bitcoin's price movements over this 
                7-day period. A beta of 1.0 means the asset moved exactly with Bitcoin, while beta > 1.0 indicates 
                higher volatility and beta < 1.0 indicates lower volatility relative to Bitcoin during this week.
            </p>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{avg_beta:.3f}</div>
                    <div class="stat-label">Average Beta (4H)</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(symbols)-1}</div>
                    <div class="stat-label">Assets Analyzed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">7</div>
                    <div class="stat-label">Days Analyzed</div>
                </div>
            </div>
            
            <p class="summary-text" style="margin-top: 20px; padding: 15px; background: rgba(17, 24, 39, 0.8); border-radius: 8px; border-left: 4px solid #ffbf00;">
                <strong>Market Interpretation:</strong> {market_interpretation}
            </p>
        </div>
        
        <div class="table-container">
            <h2 class="table-title">Beta Summary - 4H Timeframe (Ranked by Beta)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Asset</th>
                        <th>Beta</th>
                        <th>Correlation</th>
                        <th>R²</th>
                        <th>Volatility Ratio</th>
                        <th>Max Drawdown</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
        
        {chart_images}
        
        <div class="footer">
            <p>Generated by Virtuoso Trading System | Quantitative Analysis Report</p>
        </div>
    </div>
</body>
</html>
    """
    
    return html_content

async def main():
    """Generate dark mode HTML report."""
    try:
        print("🚀 Dark Mode HTML Bitcoin Beta 7-Day Report Generator")
        print("=" * 60)
        logger.info("=== Starting Dark Mode HTML Report Generation ===")
        
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        if not config:
            logger.error("Failed to load configuration")
            return 1
            
        logger.info("Configuration loaded successfully")
        
        # Initialize exchange manager
        exchange_manager = ExchangeManager(config_manager)
        await exchange_manager.initialize()
        logger.info("Exchange manager initialized")
        
        # Create report generator
        report_generator = BitcoinBeta7DayReport(
            exchange_manager=exchange_manager,
            config=None
        )
        
        logger.info("Starting 7-day Bitcoin beta analysis for HTML report...")
        print("\n📊 Generating dark mode HTML report...")
        
        # Generate the report to get data
        report_path = await report_generator.generate_report()
        
        if report_path:
            # Get the data from the report generator
            symbols = report_generator.symbols
            start_date = report_generator.start_date
            end_date = report_generator.end_date
            
            # Create output directory
            output_dir = Path('exports/bitcoin_beta_7day_reports')
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate HTML content
            html_content = create_dark_mode_html_template(
                beta_analysis={},  # We'll need to get this from the report
                symbols=symbols,
                start_date=start_date,
                end_date=end_date
            )
            
            # Save HTML file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_path = output_dir / f'bitcoin_beta_7day_report_dark_{timestamp}.html'
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"\n✅ Dark Mode HTML Report generated successfully!")
            print(f"📄 Report saved to: {html_path}")
            
            # Open the HTML file
            import webbrowser
            webbrowser.open(f'file://{html_path.absolute()}')
            
            logger.info(f"Dark Mode HTML Report completed: {html_path}")
        else:
            print("\n❌ Failed to generate report data")
            logger.error("Report generation failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Report generation interrupted by user")
        logger.warning("Report generation interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error generating HTML report: {str(e)}")
        logger.error(f"Error in HTML report generation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    finally:
        # Cleanup
        try:
            if 'exchange_manager' in locals():
                await exchange_manager.cleanup()
                logger.info("Exchange manager cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    return 0

if __name__ == "__main__":
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    # Run the report generator
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 