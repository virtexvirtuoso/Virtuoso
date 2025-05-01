import os
import json
import time
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union
from datetime import datetime, timedelta

# Import and apply matplotlib silencing before matplotlib imports
from src.utils.matplotlib_utils import silence_matplotlib_logs
silence_matplotlib_logs()

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import mplfinance as mpf
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
import base64

class ReportGenerator:
    """Utility class for generating PDF and JSON reports for trading signals."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the ReportGenerator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Create output directories if they don't exist
        self.reports_dir = Path(config.get('reports_dir', 'reports'))
        self.pdfs_dir = self.reports_dir / 'pdfs'
        self.charts_dir = self.reports_dir / 'charts'
        self.json_dir = self.reports_dir / 'json'
        
        for directory in [self.reports_dir, self.pdfs_dir, self.charts_dir, self.json_dir]:
            directory.mkdir(exist_ok=True, parents=True)
        
        # Set up matplotlib for non-interactive backend
        plt.switch_backend('Agg')
    
    def generate_report_files(self, signal: Dict[str, Any], ohlcv_data: pd.DataFrame = None) -> Dict[str, str]:
        """Generate PDF and JSON report files for a trading signal.
        
        Args:
            signal: The trading signal dictionary
            ohlcv_data: Optional OHLCV price data for charts
            
        Returns:
            Dictionary with paths to the generated files
        """
        try:
            symbol = signal.get('symbol', 'UNKNOWN')
            timestamp = signal.get('timestamp', int(time.time() * 1000))
            dt = datetime.fromtimestamp(timestamp / 1000)
            date_str = dt.strftime('%Y%m%d_%H%M%S')
            
            # Generate unique filenames
            pdf_filename = f"{symbol}_{date_str}_report.pdf"
            json_filename = f"{symbol}_{date_str}_data.json"
            chart_filename = f"{symbol}_{date_str}_chart.png"
            
            # Full paths
            pdf_path = self.pdfs_dir / pdf_filename
            json_path = self.json_dir / json_filename
            chart_path = self.charts_dir / chart_filename
            
            # Generate chart if we have OHLCV data
            chart_data = None
            if ohlcv_data is not None and not ohlcv_data.empty:
                self._generate_chart(ohlcv_data, signal, str(chart_path))
                chart_data = str(chart_path)
            
            # Save JSON data
            self._save_json_data(signal, str(json_path))
            
            # Generate PDF report
            self._generate_pdf_report(signal, chart_data, str(pdf_path))
            
            return {
                'pdf': str(pdf_path),
                'json': str(json_path),
                'chart': chart_data
            }
        except Exception as e:
            self.logger.error(f"Error generating report files: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {}
    
    def _save_json_data(self, signal: Dict[str, Any], output_path: str) -> None:
        """Save signal data as a JSON file.
        
        Args:
            signal: The trading signal dictionary
            output_path: Path to save the JSON file
        """
        try:
            # Create a clean copy of the signal data
            signal_copy = signal.copy()
            
            # Remove any large data that doesn't need to be in the JSON
            for key in list(signal_copy.keys()):
                # Skip binary or extremely large data
                if isinstance(signal_copy[key], bytes) or (
                    isinstance(signal_copy[key], str) and len(signal_copy[key]) > 10000
                ):
                    signal_copy.pop(key)
            
            # Add metadata
            signal_copy['_meta'] = {
                'generated_at': datetime.now().isoformat(),
                'type': 'signal_data'
            }
            
            # Write to file with pretty formatting
            with open(output_path, 'w') as f:
                json.dump(signal_copy, f, indent=2, default=str)
                
            self.logger.info(f"JSON data saved to {output_path}")
        except Exception as e:
            self.logger.error(f"Error saving JSON data: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def _generate_chart(self, ohlcv_data: pd.DataFrame, signal: Dict[str, Any], output_path: str) -> None:
        """Generate a candlestick chart with buy/sell zones.
        
        Args:
            ohlcv_data: OHLCV price data
            signal: The trading signal dictionary
            output_path: Path to save the chart image
        """
        try:
            # Ensure the dataframe has the right format for mplfinance
            df = ohlcv_data.copy()
            
            # Convert timestamp to datetime if needed
            if 'timestamp' in df.columns:
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('datetime', inplace=True)
            
            # Ensure we have standard OHLCV column names
            column_mapping = {
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }
            
            # Rename columns if they don't match mplfinance expected format
            df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns}, inplace=True)
            
            # Extract signal details
            symbol = signal.get('symbol', 'UNKNOWN')
            score = signal.get('score', signal.get('confluence_score', 0))
            signal_type = signal.get('signal', 'UNKNOWN').upper()
            
            # Prepare plot settings
            title = f"{symbol} - {signal_type} Signal (Score: {score:.2f})"
            
            # Extract buy/sell zones if available
            entry_price = signal.get('entry_price')
            stop_loss = signal.get('stop_loss')
            
            # Get targets if available
            targets = {}
            if 'targets' in signal and isinstance(signal['targets'], dict):
                targets = signal['targets']
            elif 'risk_management' in signal and isinstance(signal['risk_management'], dict):
                if 'targets' in signal['risk_management'] and isinstance(signal['risk_management']['targets'], dict):
                    targets = signal['risk_management']['targets']
            
            # Set up plot and style
            custom_style = mpf.make_mpf_style(
                base_mpf_style='charles',
                marketcolors={
                    'candle': {'up': '#26a69a', 'down': '#ef5350'},
                    'edge': {'up': '#26a69a', 'down': '#ef5350'},
                    'wick': {'up': '#26a69a', 'down': '#ef5350'},
                    'ohlc': {'up': '#26a69a', 'down': '#ef5350'},
                    'volume': {'up': '#26a69a', 'down': '#ef5350'},
                    'vcedge': {'up': '#26a69a', 'down': '#ef5350'}
                }
            )
            
            # Create plot markers and annotations
            annotations = []
            fill_zones = []
            
            # Add entry and stop-loss levels if available
            hlines = []
            if entry_price is not None:
                hlines.append(entry_price)
                annotations.append(
                    (df.index[-1], entry_price, f'Entry ${entry_price:.4f}', {'color': 'blue'})
                )
            
            if stop_loss is not None:
                hlines.append(stop_loss)
                annotations.append(
                    (df.index[-1], stop_loss, f'Stop ${stop_loss:.4f}', {'color': 'red'})
                )
                
                # Add fill zone between entry and stop
                if entry_price is not None:
                    # Calculate whether the stop loss is below entry (long) or above (short)
                    if stop_loss < entry_price:  # Long position
                        fill_zones.append((entry_price, stop_loss, dict(color='red', alpha=0.2)))
                    else:  # Short position
                        fill_zones.append((stop_loss, entry_price, dict(color='red', alpha=0.2)))
            
            # Add target levels
            for target_name, target_data in targets.items():
                if isinstance(target_data, dict) and 'price' in target_data:
                    target_price = target_data['price']
                    if target_price > 0:
                        hlines.append(target_price)
                        annotations.append(
                            (df.index[-1], target_price, f'{target_name} ${target_price:.4f}', 
                             {'color': 'green'})
                        )
                        
                        # Add fill zone between entry and target if entry exists
                        if entry_price is not None:
                            if entry_price < target_price:  # Long position target
                                fill_zones.append((target_price, entry_price, dict(color='green', alpha=0.2)))
                            else:  # Short position target
                                fill_zones.append((entry_price, target_price, dict(color='green', alpha=0.2)))
            
            # Create the plot
            fig, axes = mpf.plot(
                df,
                type='candle',
                style=custom_style,
                title=title,
                volume=True,
                figsize=(12, 8),
                panel_ratios=(4, 1),
                datetime_format='%Y-%m-%d %H:%M',
                xrotation=45,
                ylabel='Price',
                ylabel_lower='Volume',
                hlines=dict(hlines=hlines, colors=['blue' if i == 0 else 'red' if i == 1 else 'green' for i in range(len(hlines))], 
                            linestyle='--', linewidths=1),
                fill_between=fill_zones if fill_zones else None,
                alines=dict(alines=[(df.index[0], price, df.index[-1], price) for price in hlines], 
                           colors=['blue' if i == 0 else 'red' if i == 1 else 'green' for i in range(len(hlines))],
                           linestyle='--', linewidths=1),
                axtitle=title,
                returnfig=True
            )
            
            # Add annotations to the plot
            ax1 = axes[0]
            for ann in annotations:
                idx, price, text, style = ann
                ax1.annotate(
                    text,
                    xy=(idx, price),
                    xytext=(10, 0),
                    textcoords='offset points',
                    color=style.get('color', 'black'),
                    fontsize=8,
                    arrowprops=dict(
                        arrowstyle='-|>',
                        color=style.get('color', 'black')
                    )
                )
            
            # Save the figure
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            
            self.logger.info(f"Chart saved to {output_path}")
        except Exception as e:
            self.logger.error(f"Error generating chart: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def _generate_pdf_report(self, signal: Dict[str, Any], chart_path: Optional[str], output_path: str) -> None:
        """Generate a PDF report for a trading signal.
        
        Args:
            signal: The trading signal dictionary
            chart_path: Optional path to the chart image
            output_path: Path to save the PDF report
        """
        try:
            # Extract signal details
            symbol = signal.get('symbol', 'UNKNOWN')
            score = signal.get('score', signal.get('confluence_score', 0))
            signal_type = signal.get('signal', 'UNKNOWN').upper()
            reliability = signal.get('reliability', 100)
            price = signal.get('price', 0)
            
            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Get styles for document
            styles = getSampleStyleSheet()
            title_style = styles['Title']
            heading_style = styles['Heading1']
            normal_style = styles['Normal']
            
            # Create custom styles
            bullish_style = ParagraphStyle(
                'Bullish',
                parent=normal_style,
                textColor=colors.green
            )
            
            bearish_style = ParagraphStyle(
                'Bearish',
                parent=normal_style,
                textColor=colors.red
            )
            
            neutral_style = ParagraphStyle(
                'Neutral',
                parent=normal_style,
                textColor=colors.blue
            )
            
            # Select style based on signal type
            if signal_type in ['BUY', 'BULLISH']:
                signal_style = bullish_style
            elif signal_type in ['SELL', 'BEARISH']:
                signal_style = bearish_style
            else:
                signal_style = neutral_style
            
            # Build document content
            content = []
            
            # Add title
            content.append(Paragraph(f"{symbol} Trading Signal Report", title_style))
            content.append(Spacer(1, 12))
            
            # Add timestamp
            timestamp = signal.get('timestamp', int(time.time() * 1000))
            dt = datetime.fromtimestamp(timestamp / 1000)
            date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            content.append(Paragraph(f"Generated: {date_str}", normal_style))
            content.append(Spacer(1, 12))
            
            # Signal summary
            content.append(Paragraph("Signal Summary", heading_style))
            
            # Create summary table
            data = [
                ["Symbol", symbol],
                ["Signal Type", Paragraph(signal_type, signal_style)],
                ["Overall Score", f"{score:.2f}"],
                ["Reliability", f"{reliability:.2f}%"],
                ["Current Price", f"${price:.4f}"]
            ]
            
            t = Table(data, colWidths=[1.5*inch, 3*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            
            content.append(t)
            content.append(Spacer(1, 12))
            
            # Add chart if available
            if chart_path and os.path.exists(chart_path):
                content.append(Paragraph("Price Chart", heading_style))
                content.append(Spacer(1, 8))
                
                # Add chart image
                img = Image(chart_path, width=6*inch, height=4*inch)
                content.append(img)
                content.append(Spacer(1, 12))
            
            # Add components section if available
            if 'components' in signal and isinstance(signal['components'], dict):
                content.append(Paragraph("Component Analysis", heading_style))
                content.append(Spacer(1, 8))
                
                # Create components table
                comp_data = [["Component", "Score"]]
                
                for name, comp_score in signal['components'].items():
                    formatted_name = name.replace('_', ' ').title()
                    
                    # Determine style based on score
                    if comp_score >= 60:
                        style = bullish_style
                    elif comp_score <= 40:
                        style = bearish_style
                    else:
                        style = neutral_style
                    
                    comp_data.append([formatted_name, Paragraph(f"{comp_score:.2f}", style)])
                
                comp_table = Table(comp_data, colWidths=[3*inch, 1.5*inch])
                comp_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                
                content.append(comp_table)
                content.append(Spacer(1, 12))
            
            # Add interpretations if available
            if 'interpretations' in signal and isinstance(signal['interpretations'], dict):
                content.append(Paragraph("Market Interpretations", heading_style))
                content.append(Spacer(1, 8))
                
                for component, interpretation in signal['interpretations'].items():
                    if interpretation:
                        component_name = component.replace('_', ' ').title()
                        content.append(Paragraph(f"<b>{component_name}:</b> {interpretation}", normal_style))
                        content.append(Spacer(1, 6))
                
                content.append(Spacer(1, 6))
            
            # Add risk management section
            content.append(Paragraph("Risk Management", heading_style))
            content.append(Spacer(1, 8))
            
            # Get entry and stop loss
            entry_price = signal.get('entry_price', price)
            stop_loss = signal.get('stop_loss')
            
            if 'risk_management' in signal and isinstance(signal['risk_management'], dict):
                if not stop_loss:
                    stop_loss = signal['risk_management'].get('stop_loss')
            
            # Build risk management data
            risk_data = [["Parameter", "Value", "% Change"]]
            
            # Add entry price
            risk_data.append(["Entry Price", f"${entry_price:.4f}", "0.00%"])
            
            # Add stop loss if available
            if stop_loss:
                sl_pct = abs((stop_loss / entry_price) - 1) * 100
                risk_data.append(["Stop Loss", f"${stop_loss:.4f}", f"{sl_pct:.2f}%"])
            
            # Add targets if available
            targets = {}
            if 'targets' in signal and isinstance(signal['targets'], dict):
                targets = signal['targets']
            elif 'risk_management' in signal and isinstance(signal['risk_management'], dict):
                if 'targets' in signal['risk_management'] and isinstance(signal['risk_management']['targets'], dict):
                    targets = signal['risk_management']['targets']
            
            for target_name, target_data in targets.items():
                if isinstance(target_data, dict) and 'price' in target_data:
                    target_price = target_data.get("price", 0)
                    target_size = target_data.get("size", 0)
                    
                    if target_price > 0:
                        pct_change = abs((target_price / entry_price) - 1) * 100
                        risk_data.append([
                            f"Target {target_name}", 
                            f"${target_price:.4f}", 
                            f"{pct_change:.2f}% ({target_size * 100:.0f}%)"
                        ])
            
            # Create risk management table
            risk_table = Table(risk_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
            risk_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (1, 1), (2, -1), 'RIGHT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            
            content.append(risk_table)
            
            # Build and save the PDF
            doc.build(content)
            
            self.logger.info(f"PDF report saved to {output_path}")
        except Exception as e:
            self.logger.error(f"Error generating PDF report: {str(e)}")
            self.logger.error(traceback.format_exc())
    
    def get_report_as_base64(self, file_path: str) -> Optional[str]:
        """Convert a file to base64 encoding for embedding in Discord message.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Base64 encoded string or None if error
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return None
                
            with open(file_path, 'rb') as f:
                file_content = f.read()
                
            encoded = base64.b64encode(file_content).decode('utf-8')
            return encoded
        except Exception as e:
            self.logger.error(f"Error converting file to base64: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None 