import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from matplotlib.patches import Circle, RegularPolygon
from matplotlib.path import Path
from matplotlib.projections.polar import PolarAxes
from matplotlib.projections import register_projection
from matplotlib.spines import Spine
from matplotlib.transforms import Affine2D
import os
import logging
from datetime import datetime
import base64
from io import BytesIO
from pathlib import Path as PathLib

logger = logging.getLogger(__name__)

class ConfluenceVisualizer:
    """
    Creates visualizations for confluence model analysis results.
    Provides both a radar chart and a 3D visualization of the 6-dimensional model.
    """
    
    def __init__(self, export_dir=None):
        """
        Initialize the visualizer with export directory.
        
        Args:
            export_dir: Directory to save visualizations
        """
        self.export_dir = export_dir or os.path.join('exports', 'confluence_visualizations')
        os.makedirs(self.export_dir, exist_ok=True)
        
    def _radar_factory(self, num_vars, frame='circle'):
        """Create a radar chart with `num_vars` axes."""
        # Calculate evenly-spaced axis angles
        theta = np.linspace(0, 2*np.pi, num_vars, endpoint=False)
        
        class RadarAxes(PolarAxes):
            name = 'radar'
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.set_theta_zero_location('N')
                
            def fill(self, *args, closed=True, **kwargs):
                """Override fill so that line is closed by default"""
                return super().fill(closed=closed, *args, **kwargs)
                
            def plot(self, *args, **kwargs):
                """Override plot so that line is closed by default"""
                lines = super().plot(*args, **kwargs)
                for line in lines:
                    self._close_line(line)
                return lines
                
            def _close_line(self, line):
                x, y = line.get_data()
                # FIXME: markers at x[0], y[0] get doubled-up
                if x[0] != x[-1]:
                    x = np.append(x, x[0])
                    y = np.append(y, y[0])
                    line.set_data(x, y)
                    
            def set_varlabels(self, labels):
                self.set_thetagrids(np.degrees(theta), labels)
                
            def _gen_axes_patch(self):
                # The Spine defines the Path of the frame
                if frame == 'circle':
                    return Circle((0.5, 0.5), 0.5)
                elif frame == 'polygon':
                    return RegularPolygon((0.5, 0.5), num_vars, radius=0.5, orientation=np.pi/2)
                else:
                    raise ValueError("Unknown frame type: %s" % frame)
                    
            def _gen_axes_spines(self):
                if frame == 'circle':
                    return super()._gen_axes_spines()
                elif frame == 'polygon':
                    # spine_type must be 'left'/'right'/'top'/'bottom'/'circle'
                    spine = Spine(
                        axes=self,
                        spine_type='circle',
                        path=Path.unit_regular_polygon(num_vars)
                    )
                    # unit_regular_polygon returns a polygon of radius 1 centered at
                    # (0, 0) but we want a polygon of radius 0.5 centered at (0.5,
                    # 0.5) in axes coordinates.
                    spine.set_transform(Affine2D().scale(.5).translate(.5, .5) + self.transAxes)
                    return {'polar': spine}
                else:
                    raise ValueError("Unknown frame type: %s" % frame)
        
        register_projection(RadarAxes)
        return theta
        
    def create_radar_visualization(self, component_scores, overall_score, title=None):
        """
        Create a radar chart visualization of the confluence model components.
        
        Args:
            component_scores: Dictionary with component names as keys and scores as values
            overall_score: Overall confluence score
            title: Optional title for the chart
            
        Returns:
            Matplotlib figure object
        """
        components = list(component_scores.keys())
        N = len(components)
        
        # Get evenly spaced axis angles
        theta = self._radar_factory(N, frame='polygon')
        
        # Create figure and axes with radar projection
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='radar'))
        
        # Plot the data values
        values = [component_scores[component] for component in components]
        
        # Determine color based on overall score
        if overall_score < 35:
            color = '#FE4A49'  # Red for bearish
            category = 'Bearish'
        elif overall_score < 65:
            color = '#FED766'  # Yellow for neutral
            category = 'Neutral'
        else:
            color = '#009FB7'  # Green for bullish
            category = 'Bullish'
            
        # Plot data
        ax.plot(theta, values, color=color, linewidth=2.5)
        ax.fill(theta, values, color=color, alpha=0.25)
        
        # Set labels
        ax.set_varlabels(components)
        
        # Add reference circles and labels
        for i in [20, 40, 60, 80]:
            ax.plot(
                np.linspace(0, 2*np.pi, 100),
                np.ones(100) * i,
                color='gray',
                alpha=0.3,
                linestyle='--'
            )
            plt.text(
                0, i, 
                str(i), 
                color='gray', 
                ha='center', 
                va='bottom'
            )
        
        # Add title with overall score
        if title:
            plt.title(title, size=20, y=1.1)
        else:
            plt.title(
                f'Confluence Model: {overall_score:.1f} ({category})', 
                size=20, 
                y=1.1,
                color=color
            )
        
        return fig
    
    def create_3d_visualization(self, component_scores, overall_score):
        """
        Create a 3D visualization of the confluence model.
        
        Args:
            component_scores: Dictionary with component names as keys and scores as values
            overall_score: Overall confluence score
            
        Returns:
            Plotly figure object
        """
        # Extract component values
        tech_score = component_scores.get('Technical', 50)
        volume_score = component_scores.get('Volume', 50)
        orderbook_score = component_scores.get('Orderbook', 50)
        orderflow_score = component_scores.get('Orderflow', 50)
        sentiment_score = component_scores.get('Sentiment', 50)
        price_structure_score = component_scores.get('Price Structure', 50)
        
        # Determine color based on overall score
        if overall_score < 35:
            color = 'rgb(254, 74, 73)'  # Red for bearish
            category = 'Bearish'
        elif overall_score < 65:
            color = 'rgb(254, 215, 102)'  # Yellow for neutral
            category = 'Neutral'
        else:
            color = 'rgb(0, 159, 183)'  # Green for bullish
            category = 'Bullish'
            
        # Create the 3D scatter plot
        fig = go.Figure()
        
        # Create a more complex 3D visualization
        # Using X, Y, Z for the main 3 dimensions and size, color, opacity for others
        fig.add_trace(go.Scatter3d(
            x=[tech_score],
            y=[orderbook_score],
            z=[orderflow_score],
            mode='markers',
            marker=dict(
                size=volume_score/5 + 10,  # Size represents volume score
                color=color,
                opacity=sentiment_score/100,  # Opacity represents sentiment
                symbol='circle',
                line=dict(
                    color='rgb(255, 255, 255)',
                    width=2
                )
            ),
            text=[f'Overall Score: {overall_score:.1f}<br>' +
                  f'Technical: {tech_score:.1f}<br>' +
                  f'Volume: {volume_score:.1f}<br>' +
                  f'Orderbook: {orderbook_score:.1f}<br>' +
                  f'Orderflow: {orderflow_score:.1f}<br>' +
                  f'Sentiment: {sentiment_score:.1f}<br>' +
                  f'Price Structure: {price_structure_score:.1f}'],
            hoverinfo='text'
        ))
        
        # Add reference planes
        x = np.linspace(0, 100, 10)
        y = np.linspace(0, 100, 10)
        z = np.linspace(0, 100, 10)
        
        X, Y = np.meshgrid(x, y)
        Z = np.ones(X.shape) * 50
        
        # Add reference grids
        fig.add_trace(go.Surface(
            x=X, y=Y, z=Z,
            colorscale=[[0, 'rgba(200, 200, 200, 0.2)'], [1, 'rgba(200, 200, 200, 0.2)']],
            showscale=False, 
            opacity=0.2,
            name='Neutral Orderflow Plane'
        ))
        
        X, Z = np.meshgrid(x, z)
        Y = np.ones(X.shape) * 50
        
        fig.add_trace(go.Surface(
            x=X, y=Y, z=Z,
            colorscale=[[0, 'rgba(200, 200, 200, 0.2)'], [1, 'rgba(200, 200, 200, 0.2)']],
            showscale=False, 
            opacity=0.2,
            name='Neutral Orderbook Plane'
        ))
        
        Y, Z = np.meshgrid(y, z)
        X = np.ones(Y.shape) * 50
        
        fig.add_trace(go.Surface(
            x=X, y=Y, z=Z,
            colorscale=[[0, 'rgba(200, 200, 200, 0.2)'], [1, 'rgba(200, 200, 200, 0.2)']],
            showscale=False, 
            opacity=0.2,
            name='Neutral Technical Plane'
        ))
        
        # Configure the layout
        fig.update_layout(
            title=f'6D Confluence Model Visualization - Overall Score: {overall_score:.1f} ({category})',
            scene=dict(
                xaxis=dict(
                    title='Technical',
                    range=[0, 100],
                    backgroundcolor='rgb(230, 230, 230)',
                    gridcolor='white',
                    showbackground=True,
                    zerolinecolor='white',
                    nticks=6
                ),
                yaxis=dict(
                    title='Orderbook',
                    range=[0, 100],
                    backgroundcolor='rgb(230, 230, 230)',
                    gridcolor='white',
                    showbackground=True,
                    zerolinecolor='white',
                    nticks=6
                ),
                zaxis=dict(
                    title='Orderflow',
                    range=[0, 100],
                    backgroundcolor='rgb(230, 230, 230)',
                    gridcolor='white',
                    showbackground=True,
                    zerolinecolor='white',
                    nticks=6
                ),
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.25)
                )
            ),
            width=900,
            height=800,
            margin=dict(l=0, r=0, b=0, t=40),
            template='plotly_white',
            showlegend=False,
            annotations=[
                dict(
                    text=f"Price Structure: {price_structure_score:.1f}",
                    x=0.5,
                    y=0.03,
                    xref='paper',
                    yref='paper',
                    showarrow=False,
                    font=dict(size=14)
                ),
                dict(
                    text=f"Volume: {volume_score:.1f}",
                    x=0.85,
                    y=0.95,
                    xref='paper',
                    yref='paper',
                    showarrow=False,
                    font=dict(size=14)
                ),
                dict(
                    text=f"Sentiment: {sentiment_score:.1f}",
                    x=0.15,
                    y=0.95,
                    xref='paper',
                    yref='paper',
                    showarrow=False,
                    font=dict(size=14)
                )
            ]
        )
        
        return fig
    
    def save_visualizations(self, component_scores, overall_score, symbol="UNKNOWN", timestamp=None):
        """
        Save both radar and 3D visualizations to disk.
        
        Args:
            component_scores: Dictionary with component names as keys and scores as values
            overall_score: Overall confluence score
            symbol: Trading symbol
            timestamp: Optional timestamp for filenames
            
        Returns:
            Tuple of (radar_chart_path, 3d_chart_path)
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create radar chart
        fig_radar = self.create_radar_visualization(component_scores, overall_score)
        radar_filename = f"{symbol}_{timestamp}_radar.png"
        radar_path = os.path.join(self.export_dir, radar_filename)
        fig_radar.savefig(radar_path, dpi=150, bbox_inches='tight')
        plt.close(fig_radar)
        
        # Create 3D visualization
        fig_3d = self.create_3d_visualization(component_scores, overall_score)
        threed_filename = f"{symbol}_{timestamp}_3d.html"
        threed_path = os.path.join(self.export_dir, threed_filename)
        fig_3d.write_html(threed_path)
        
        logger.info(f"Saved confluence visualizations to {radar_path} and {threed_path}")
        
        return radar_path, threed_path
    
    def generate_base64_image(self, component_scores, overall_score):
        """
        Generate a base64-encoded image of the radar visualization.
        
        Args:
            component_scores: Dictionary with component names as keys and scores as values
            overall_score: Overall confluence score
            
        Returns:
            Base64-encoded image string
        """
        fig = self.create_radar_visualization(component_scores, overall_score)
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        return img_str

if __name__ == "__main__":
    # Example usage
    component_scores = {
        'Technical': 44.74,
        'Volume': 43.15,
        'Orderbook': 60.08,
        'Orderflow': 73.08,
        'Sentiment': 62.10,
        'Price Structure': 46.82
    }
    
    overall_score = 56.87
    
    visualizer = ConfluenceVisualizer()
    radar_path, threed_path = visualizer.save_visualizations(
        component_scores=component_scores,
        overall_score=overall_score,
        symbol="XRPUSDT"
    )
    
    print(f"Radar chart saved to: {radar_path}")
    print(f"3D visualization saved to: {threed_path}") 