#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parallel Coordinates Plot Test for Confluence Model

This script demonstrates parallel coordinates plots as an alternative 
visualization for the 6-dimensional confluence model used in trading signals.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.offline import plot
import matplotlib.colors as mcolors
from matplotlib.colors import LinearSegmentedColormap
import base64
from io import BytesIO
import logging
from datetime import datetime

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class ParallelCoordinatesVisualizer:
    """
    Creates parallel coordinates visualizations for confluence model analysis results.
    Provides both interactive Plotly and static Matplotlib implementations.
    """
    
    def __init__(self, export_dir=None):
        """
        Initialize the visualizer with export directory.
        
        Args:
            export_dir: Directory to save visualizations
        """
        self.export_dir = export_dir or os.path.join('exports', 'confluence_visualizations')
        os.makedirs(self.export_dir, exist_ok=True)
    
    def _convert_to_dataframe(self, component_scores, overall_score):
        """
        Convert component scores dict to pandas DataFrame suitable for parallel coordinates.
        
        Args:
            component_scores: Dictionary with component names as keys and scores as values
            overall_score: Overall confluence score
            
        Returns:
            pandas DataFrame with all scores in a format suitable for plotting
        """
        # Create a DataFrame with one row containing all component scores
        df = pd.DataFrame([component_scores])
        
        # Add overall score
        df['Overall'] = overall_score
        
        return df
    
    def _get_color_for_score(self, score):
        """
        Get color based on score value (bearish/neutral/bullish).
        
        Args:
            score: Numerical score value
            
        Returns:
            Hex color string
        """
        if score < 35:
            return '#FE4A49'  # Red for bearish
        elif score < 65:
            return '#FED766'  # Yellow for neutral
        else:
            return '#009FB7'  # Blue/green for bullish
    
    def create_plotly_parallel_coordinates(self, component_scores, overall_score, title=None):
        """
        Create an interactive parallel coordinates plot using Plotly.
        
        Args:
            component_scores: Dictionary with component names as keys and scores as values
            overall_score: Overall confluence score
            title: Optional title for the plot
            
        Returns:
            Plotly figure object
        """
        # Convert to DataFrame
        df = self._convert_to_dataframe(component_scores, overall_score)
        
        # Determine color based on overall score
        if overall_score < 35:
            color = '#FE4A49'  # Red for bearish
            category = 'Bearish'
        elif overall_score < 65:
            color = '#FED766'  # Yellow for neutral
            category = 'Neutral'
        else:
            color = '#009FB7'  # Blue/green for bullish
            category = 'Bullish'
        
        # Define dimensions for the parallel coordinates plot
        dimensions = []
        for col in df.columns:
            dimensions.append(
                dict(
                    range=[0, 100],
                    label=col,
                    values=df[col],
                    tickvals=[0, 25, 35, 50, 65, 75, 100],
                    ticktext=['0', '25', '⇓ Bearish', '50', '⇑ Bullish', '75', '100']
                )
            )
        
        # Create the parallel coordinates plot
        fig = go.Figure(data=
            go.Parcoords(
                line=dict(
                    color=overall_score,
                    colorscale=[
                        [0, '#FE4A49'],    # Red for bearish
                        [0.35, '#FE4A49'],  # Red for bearish
                        [0.35, '#FED766'],  # Yellow for neutral (start)
                        [0.65, '#FED766'],  # Yellow for neutral (end)
                        [0.65, '#009FB7'],  # Blue/green for bullish
                        [1.0, '#009FB7']    # Blue/green for bullish
                    ],
                    showscale=True,
                    colorbar=dict(
                        title='Score',
                        tickvals=[0, 35, 50, 65, 100],
                        ticktext=['0', 'Bearish', 'Neutral', 'Bullish', '100']
                    ),
                    cmin=0,
                    cmax=100
                ),
                dimensions=dimensions,
                unselected=dict(line=dict(opacity=0.3))
            )
        )
        
        # Update layout and title
        fig.update_layout(
            title=title or f'Confluence Model Analysis: {overall_score:.1f} ({category})',
            font=dict(family="Arial, sans-serif", size=12),
            height=500,
            margin=dict(l=80, r=80, t=80, b=80),
            paper_bgcolor='white',
            plot_bgcolor='white'
        )
        
        return fig
    
    def create_matplotlib_parallel_coordinates(self, component_scores, overall_score, title=None):
        """
        Create a static parallel coordinates plot using Matplotlib.
        
        Args:
            component_scores: Dictionary with component names as keys and scores as values
            overall_score: Overall confluence score
            title: Optional title for the plot
            
        Returns:
            Matplotlib figure object
        """
        # Convert to DataFrame
        df = self._convert_to_dataframe(component_scores, overall_score)
        
        # Create custom colormap for the background (representing bearish/neutral/bullish zones)
        colors = [(1, 0.29, 0.29), (0.996, 0.843, 0.4), (0, 0.624, 0.718)]  # Red, Yellow, Blue
        positions = [0, 0.5, 1]
        cmap = LinearSegmentedColormap.from_list("custom_diverging", list(zip(positions, colors)))
        
        # Determine color based on overall score
        if overall_score < 35:
            line_color = '#FE4A49'  # Red for bearish
            category = 'Bearish'
        elif overall_score < 65:
            line_color = '#FED766'  # Yellow for neutral
            category = 'Neutral'
        else:
            line_color = '#009FB7'  # Blue/green for bullish
            category = 'Bullish'
        
        # Create the figure and axes
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot the parallel coordinates
        parallel_coordinates(df, class_column='Overall', ax=ax, color=[line_color])
        
        # Set y-axis limits
        ax.set_ylim(0, 100)
        
        # Add background zones
        ax.axhspan(0, 35, alpha=0.2, color='#FE4A49')  # Bearish zone
        ax.axhspan(35, 65, alpha=0.2, color='#FED766')  # Neutral zone
        ax.axhspan(65, 100, alpha=0.2, color='#009FB7')  # Bullish zone
        
        # Add zone labels
        ax.text(ax.get_xlim()[1] * 1.02, 17.5, 'Bearish', fontsize=10, va='center')
        ax.text(ax.get_xlim()[1] * 1.02, 50, 'Neutral', fontsize=10, va='center')
        ax.text(ax.get_xlim()[1] * 1.02, 82.5, 'Bullish', fontsize=10, va='center')
        
        # Set title
        if title:
            plt.title(title, fontsize=14)
        else:
            plt.title(f'Confluence Model Analysis: {overall_score:.1f} ({category})', fontsize=14)
        
        # Adjust layout
        plt.tight_layout()
        
        return fig
    
    def save_visualizations(self, component_scores, overall_score, symbol="UNKNOWN", timestamp=None):
        """
        Save both interactive and static parallel coordinates visualizations to disk.
        
        Args:
            component_scores: Dictionary with component names as keys and scores as values
            overall_score: Overall confluence score
            symbol: Trading symbol
            timestamp: Optional timestamp for filenames
            
        Returns:
            Tuple of (matplotlib_path, plotly_path)
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create matplotlib visualization
        fig_mpl = self.create_matplotlib_parallel_coordinates(component_scores, overall_score)
        mpl_filename = f"{symbol}_{timestamp}_parallel_mpl.png"
        mpl_path = os.path.join(self.export_dir, mpl_filename)
        fig_mpl.savefig(mpl_path, dpi=150, bbox_inches='tight')
        plt.close(fig_mpl)
        
        # Create plotly visualization
        fig_plotly = self.create_plotly_parallel_coordinates(component_scores, overall_score)
        plotly_filename = f"{symbol}_{timestamp}_parallel_plotly.html"
        plotly_path = os.path.join(self.export_dir, plotly_filename)
        fig_plotly.write_html(plotly_path)
        
        logger.info(f"Saved parallel coordinates visualizations to {mpl_path} and {plotly_path}")
        
        return mpl_path, plotly_path
    
    def generate_base64_image(self, component_scores, overall_score):
        """
        Generate a base64-encoded image of the parallel coordinates visualization.
        
        Args:
            component_scores: Dictionary with component names as keys and scores as values
            overall_score: Overall confluence score
            
        Returns:
            Base64-encoded image string
        """
        fig = self.create_matplotlib_parallel_coordinates(component_scores, overall_score)
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        return img_str

# Helper function for Matplotlib parallel coordinates (replacement for pandas.plotting function)
def parallel_coordinates(df, class_column, ax=None, color=None, **kwargs):
    """
    Custom parallel coordinates implementation for matplotlib.
    """
    if ax is None:
        ax = plt.gca()
    
    x = list(range(len(df.columns) - 1))
    
    # Get column names excluding the class column
    cols = [col for col in df.columns if col != class_column]
    
    # Plot each row
    for i, row in df.iterrows():
        y = [row[col] for col in cols]
        if color is not None:
            ax.plot(x, y, color=color[0], **kwargs)
        else:
            ax.plot(x, y, **kwargs)
    
    # Set x-tick labels
    ax.set_xticks(x)
    ax.set_xticklabels(cols, rotation=30)
    
    # Set gridlines
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    return ax

def test_parallel_coordinates():
    """Test the parallel coordinates visualization with sample data."""
    # Test with different confluence scenarios
    
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
    
    # Create output directory
    output_dir = os.path.join(current_dir, 'parallel_viz_output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize visualizer
    visualizer = ParallelCoordinatesVisualizer(export_dir=output_dir)
    
    # Generate and save visualizations
    all_results = []
    
    # Generate neutral-bullish visualizations
    logger.info("Generating neutral-bullish parallel coordinates visualizations...")
    mpl_path, plotly_path = visualizer.save_visualizations(
        component_scores=component_scores_neutral_bullish,
        overall_score=overall_score_neutral_bullish,
        symbol="XRPUSDT",
        timestamp="NeutralBullish"
    )
    all_results.append(("Neutral-Bullish", mpl_path, plotly_path))
    
    # Generate bullish visualizations
    logger.info("Generating bullish parallel coordinates visualizations...")
    mpl_path, plotly_path = visualizer.save_visualizations(
        component_scores=component_scores_bullish,
        overall_score=overall_score_bullish,
        symbol="BTCUSDT",
        timestamp="Bullish"
    )
    all_results.append(("Bullish", mpl_path, plotly_path))
    
    # Generate bearish visualizations
    logger.info("Generating bearish parallel coordinates visualizations...")
    mpl_path, plotly_path = visualizer.save_visualizations(
        component_scores=component_scores_bearish,
        overall_score=overall_score_bearish,
        symbol="ETHUSDT",
        timestamp="Bearish"
    )
    all_results.append(("Bearish", mpl_path, plotly_path))
    
    # Display results
    logger.info("\n===== Visualization Results =====")
    for label, mpl_path, plotly_path in all_results:
        logger.info(f"{label}:")
        logger.info(f"  - Static Chart: {mpl_path}")
        logger.info(f"  - Interactive Chart: {plotly_path}")
    
    # Open the visualizations in the browser
    import webbrowser
    for label, mpl_path, plotly_path in all_results:
        if os.path.exists(plotly_path):
            logger.info(f"Opening {label} interactive visualization in browser...")
            webbrowser.open(f"file://{os.path.abspath(plotly_path)}")
    
    # Create a simple HTML report with embedded base64 image
    logger.info("Generating sample report with parallel coordinates visualization...")
    base64_img = visualizer.generate_base64_image(component_scores_neutral_bullish, overall_score_neutral_bullish)
    
    # Create HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Parallel Coordinates Trading Signal Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
            .container {{ max-width: 1000px; margin: 0 auto; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .card {{ border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 20px; }}
            .chart-container {{ text-align: center; }}
            .score {{ font-size: 24px; text-align: center; margin: 20px 0; }}
            .neutral {{ color: #FED766; }}
            .bullish {{ color: #009FB7; }}
            .bearish {{ color: #FE4A49; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>XRPUSDT Trading Signal Report</h1>
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="card">
                <h2>Confluence Model Visualization (Parallel Coordinates)</h2>
                <div class="score">
                    Overall Score: <span class="neutral">{overall_score_neutral_bullish:.2f}</span> (Neutral)
                </div>
                <div class="chart-container">
                    <img src="data:image/png;base64,{base64_img}" alt="Confluence Model Visualization" style="max-width: 100%;" />
                </div>
                
                <div class="explanation">
                    <h3>How to Read This Chart</h3>
                    <p>The parallel coordinates plot shows all six components at once. Each vertical axis represents one component, with higher values being more bullish. The colored horizontal bands show the bearish (red), neutral (yellow), and bullish (green) zones.</p>
                    <p>The line connecting across all axes shows how the components relate to each other, making it easy to see which components are contributing most positively or negatively to the overall signal.</p>
                </div>
            </div>
            
            <div class="card">
                <h3>Component Values</h3>
                <ul>
                    <li><strong>Technical:</strong> {component_scores_neutral_bullish['Technical']:.2f}</li>
                    <li><strong>Volume:</strong> {component_scores_neutral_bullish['Volume']:.2f}</li>
                    <li><strong>Orderbook:</strong> {component_scores_neutral_bullish['Orderbook']:.2f}</li>
                    <li><strong>Orderflow:</strong> {component_scores_neutral_bullish['Orderflow']:.2f}</li>
                    <li><strong>Sentiment:</strong> {component_scores_neutral_bullish['Sentiment']:.2f}</li>
                    <li><strong>Price Structure:</strong> {component_scores_neutral_bullish['Price Structure']:.2f}</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save the HTML report
    html_path = os.path.join(output_dir, 'parallel_coordinates_report.html')
    with open(html_path, 'w') as f:
        f.write(html_content)
    
    logger.info(f"Sample report with parallel coordinates visualization saved to: {html_path}")
    webbrowser.open(f"file://{os.path.abspath(html_path)}")
    
    return all_results

if __name__ == "__main__":
    logger.info("Starting Parallel Coordinates Visualization Test")
    try:
        results = test_parallel_coordinates()
        logger.info("Test completed successfully!")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc()) 