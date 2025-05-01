#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Confluence Model Visualization Demo

This script demonstrates the ConfluenceVisualizer class that creates visualizations
of the 6-dimensional confluence model used for trading signal analysis.
"""

import os
import sys
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import webbrowser

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.monitoring.visualizers.confluence_visualizer import ConfluenceVisualizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def create_demo_visualizations():
    """Create demo visualizations for different confluence scenarios."""
    
    # Create export directory
    export_dir = os.path.join(os.path.dirname(__file__), 'confluence_viz_output')
    os.makedirs(export_dir, exist_ok=True)
    
    # Initialize the visualizer
    visualizer = ConfluenceVisualizer(export_dir=export_dir)
    
    # Example 1: Neutral leaning bullish (from log data)
    component_scores_neutral_bullish = {
        'Technical': 44.74,
        'Volume': 43.15,
        'Orderbook': 60.08,
        'Orderflow': 73.08,
        'Sentiment': 62.10,
        'Price Structure': 46.82
    }
    
    overall_score_neutral_bullish = 56.87
    
    # Example 2: Strong bullish signal
    component_scores_bullish = {
        'Technical': 78.32,
        'Volume': 82.94,
        'Orderbook': 71.45,
        'Sentiment': 75.63,
        'Orderflow': 85.08,
        'Price Structure': 80.21
    }
    
    overall_score_bullish = 79.82
    
    # Example 3: Strong bearish signal
    component_scores_bearish = {
        'Technical': 28.45,
        'Volume': 31.08,
        'Orderbook': 25.63,
        'Sentiment': 22.71,
        'Orderflow': 29.83,
        'Price Structure': 26.91
    }
    
    overall_score_bearish = 27.80
    
    # Generate and save all visualizations
    all_results = []
    
    # Generate neutral-bullish visualizations
    logger.info("Generating neutral-bullish visualizations...")
    radar_path, threed_path = visualizer.save_visualizations(
        component_scores=component_scores_neutral_bullish,
        overall_score=overall_score_neutral_bullish,
        symbol="XRPUSDT",
        timestamp="NeutralBullish"
    )
    all_results.append(("Neutral-Bullish", radar_path, threed_path))
    
    # Generate bullish visualizations
    logger.info("Generating bullish visualizations...")
    radar_path, threed_path = visualizer.save_visualizations(
        component_scores=component_scores_bullish,
        overall_score=overall_score_bullish,
        symbol="BTCUSDT",
        timestamp="Bullish"
    )
    all_results.append(("Bullish", radar_path, threed_path))
    
    # Generate bearish visualizations
    logger.info("Generating bearish visualizations...")
    radar_path, threed_path = visualizer.save_visualizations(
        component_scores=component_scores_bearish,
        overall_score=overall_score_bearish,
        symbol="ETHUSDT",
        timestamp="Bearish"
    )
    all_results.append(("Bearish", radar_path, threed_path))
    
    # Display results
    logger.info("\n===== Visualization Results =====")
    for label, radar, threed in all_results:
        logger.info(f"{label}:")
        logger.info(f"  - Radar Chart: {radar}")
        logger.info(f"  - 3D Visualization: {threed}")
        
    # Open the visualizations in the browser
    for label, radar, threed in all_results:
        if os.path.exists(threed):
            logger.info(f"Opening {label} 3D visualization in browser...")
            webbrowser.open(f"file://{os.path.abspath(threed)}")
    
    return all_results

def showcase_integrated_visualizations():
    """Showcase how the visualizations can be integrated into trading reports."""
    
    # Create sample component scores
    component_scores = {
        'Technical': 44.74,
        'Volume': 43.15,
        'Orderbook': 60.08,
        'Orderflow': 73.08,
        'Sentiment': 62.10,
        'Price Structure': 46.82
    }
    
    overall_score = 56.87
    
    # Initialize the visualizer
    visualizer = ConfluenceVisualizer()
    
    # Generate base64 image for HTML embedding
    logger.info("Generating base64 image for HTML embedding...")
    base64_img = visualizer.generate_base64_image(component_scores, overall_score)
    
    # Create a simple HTML report with the embedded image
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Trading Signal Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
            .container {{ max-width: 1000px; margin: 0 auto; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .card {{ border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 20px; }}
            .chart-container {{ text-align: center; }}
            .score {{ font-size: 24px; text-align: center; margin: 20px 0; }}
            .component-list {{ margin-top: 20px; }}
            .component-item {{ margin-bottom: 10px; }}
            .component-bar {{ height: 20px; background-color: #eee; border-radius: 3px; position: relative; }}
            .component-fill {{ height: 100%; border-radius: 3px; }}
            .neutral {{ background-color: #FED766; }}
            .bullish {{ background-color: #009FB7; }}
            .bearish {{ background-color: #FE4A49; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>XRPUSDT Trading Signal Report</h1>
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="card">
                <h2>Confluence Model Visualization</h2>
                <div class="score">
                    Overall Score: <span class="neutral">{overall_score:.2f}</span> (Neutral)
                </div>
                <div class="chart-container">
                    <img src="data:image/png;base64,{base64_img}" alt="Confluence Model Visualization" style="max-width: 100%;" />
                </div>
                
                <div class="component-list">
                    <h3>Component Breakdown</h3>
    """
    
    # Add component bars
    for component, score in component_scores.items():
        color_class = "bearish" if score < 35 else "bullish" if score > 65 else "neutral"
        html_content += f"""
                    <div class="component-item">
                        <strong>{component}:</strong> {score:.2f}
                        <div class="component-bar">
                            <div class="component-fill {color_class}" style="width: {score}%;"></div>
                        </div>
                    </div>
        """
    
    # Close the HTML
    html_content += """
                </div>
            </div>
            
            <div class="card">
                <h3>How to Use This Report</h3>
                <p>This visualization shows the 6-dimensional confluence model used for trading signal analysis:</p>
                <ul>
                    <li><strong>Technical</strong>: Classic technical indicators</li>
                    <li><strong>Volume</strong>: Volume-based market analysis</li>
                    <li><strong>Orderbook</strong>: Order book depth and structure</li>
                    <li><strong>Orderflow</strong>: Real-time order execution analysis</li>
                    <li><strong>Sentiment</strong>: Market sentiment indicators</li>
                    <li><strong>Price Structure</strong>: Price action patterns and structure</li>
                </ul>
                <p>Higher scores (closer to 100) indicate more bullish conditions, while lower scores (closer to 0) indicate bearish conditions.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save the HTML report
    html_path = os.path.join(os.path.dirname(__file__), 'sample_report_with_visualization.html')
    with open(html_path, 'w') as f:
        f.write(html_content)
    
    logger.info(f"Sample HTML report with visualization saved to: {html_path}")
    
    # Open the HTML report in a browser
    webbrowser.open(f"file://{os.path.abspath(html_path)}")
    
    return html_path

if __name__ == "__main__":
    logger.info("Starting Confluence Visualizer Demo")
    
    # Create demo visualizations
    results = create_demo_visualizations()
    
    # Showcase integrated visualizations
    html_path = showcase_integrated_visualizations()
    
    logger.info("Demo completed successfully!") 