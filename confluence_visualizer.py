import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from matplotlib.patches import Circle, RegularPolygon
from matplotlib.path import Path
from matplotlib.projections.polar import PolarAxes
from matplotlib.projections import register_projection
from matplotlib.spines import Spine
from matplotlib.transforms import Affine2D

# --- Extracted component data from log ---
component_scores = {
    'Technical': 44.74,
    'Volume': 43.15,
    'Orderbook': 60.08,
    'Orderflow': 73.08,
    'Sentiment': 62.10,
    'Price Structure': 46.82
}

overall_score = 56.87

# --- Radar Chart Implementation ---
def radar_factory(num_vars, frame='circle'):
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
            if frame == 'circle':
                return Circle((0.5, 0.5), 0.5)
            elif frame == 'polygon':
                return RegularPolygon((0.5, 0.5), num_vars, radius=0.5, edgecolor="k")
            else:
                raise ValueError("Unknown value for 'frame': %s" % frame)
                
        def _gen_axes_spines(self):
            if frame == 'circle':
                return super()._gen_axes_spines()
            elif frame == 'polygon':
                spine_type = 'circle'
                verts = unit_poly_verts(theta)
                verts.append(verts[0])  # Close the polygon
                path = Path(verts)
                spine = Spine(self, spine_type, path)
                spine.set_transform(self.transAxes)
                return {'polar': spine}
            else:
                raise ValueError("Unknown value for 'frame': %s" % frame)
                
    register_projection(RadarAxes)
    return theta

def unit_poly_verts(theta):
    """Return vertices of polygon for subplot axes"""
    x0, y0, r = [0.5] * 3
    verts = [(r*np.cos(t) + x0, r*np.sin(t) + y0) for t in theta]
    return verts

def create_confluence_radar_chart(component_scores, overall_score):
    N = len(component_scores)
    theta = radar_factory(N, frame='polygon')
    
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='radar'))
    
    # Set chart limits and grid
    ax.set_ylim(0, 100)
    
    # Draw axis lines for key thresholds
    ax.set_rgrids([35, 50, 65], labels=['Bearish', 'Neutral', 'Bullish'], angle=0)
    
    # Get component names and scores
    component_names = list(component_scores.keys())
    values = list(component_scores.values())
    
    # Plot the data and fill the polygon
    ax.plot(theta, values, 'o-', linewidth=2)
    ax.fill(theta, values, alpha=0.25)
    
    # Add labels and customize
    ax.set_varlabels(component_names)
    plt.title('Confluence Model Analysis - XRPUSDT', size=15, y=1.1)
    
    # Add overall score in the center
    plt.figtext(0.5, 0.5, f'Overall: {overall_score:.2f}', 
                ha='center', va='center', fontsize=15, 
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
    
    plt.tight_layout()
    
    return fig

# --- 3D Visualization Implementation ---
def create_3d_confluence_visualization(component_scores, overall_score):
    # Set up the figure
    fig = go.Figure()
    
    # Create color scale based on score values
    def get_color(score):
        if score < 35:
            return 'red'  # Bearish
        elif score > 65:
            return 'green'  # Bullish
        else:
            return 'yellow'  # Neutral
    
    # Use the first 3 components for x, y, z coordinates
    x = component_scores['Technical']
    y = component_scores['Volume'] 
    z = component_scores['Orderbook']
    
    # Use the next 2 components for size and color
    size = component_scores['Orderflow'] / 2  # Scale down for appropriate marker size
    color = component_scores['Sentiment']
    
    # Create hover text with all component information
    hover_text = '<br>'.join([
        f"<b>Overall Score: {overall_score:.2f}</b>",
        f"Technical: {component_scores['Technical']:.2f}",
        f"Volume: {component_scores['Volume']:.2f}",
        f"Orderbook: {component_scores['Orderbook']:.2f}",
        f"Orderflow: {component_scores['Orderflow']:.2f}",
        f"Sentiment: {component_scores['Sentiment']:.2f}",
        f"Price Structure: {component_scores['Price Structure']:.2f}"
    ])
    
    # Add the main marker representing the current state
    fig.add_trace(go.Scatter3d(
        x=[x],
        y=[y],
        z=[z],
        mode='markers+text',
        marker=dict(
            size=size,
            color=get_color(color),
            opacity=0.7,
            line=dict(color='black', width=1)
        ),
        text=["Current State"],
        hoverinfo='text',
        hovertext=[hover_text],
        showlegend=True,
        name=f"Overall Score: {overall_score:.2f}"
    ))
    
    # Add reference points for bullish, bearish, and neutral territories
    # Bullish reference (all components at 75)
    fig.add_trace(go.Scatter3d(
        x=[75],
        y=[75],
        z=[75],
        mode='markers',
        marker=dict(
            size=8,
            color='green',
            symbol='circle',
            opacity=0.7
        ),
        hoverinfo='text',
        hovertext=["Bullish Reference (75)"],
        showlegend=True,
        name="Bullish Reference"
    ))
    
    # Bearish reference (all components at 25)
    fig.add_trace(go.Scatter3d(
        x=[25],
        y=[25],
        z=[25],
        mode='markers',
        marker=dict(
            size=8,
            color='red',
            symbol='circle',
            opacity=0.7
        ),
        hoverinfo='text',
        hovertext=["Bearish Reference (25)"],
        showlegend=True,
        name="Bearish Reference"
    ))
    
    # Neutral reference (all components at 50)
    fig.add_trace(go.Scatter3d(
        x=[50],
        y=[50],
        z=[50],
        mode='markers',
        marker=dict(
            size=8,
            color='yellow',
            symbol='circle',
            opacity=0.7
        ),
        hoverinfo='text',
        hovertext=["Neutral Reference (50)"],
        showlegend=True,
        name="Neutral Reference"
    ))
    
    # Add axis lines to show bullish/bearish thresholds
    axis_line_points = np.linspace(0, 100, 2)
    zeros = np.zeros(2)
    hundreds = np.ones(2) * 100
    
    # X-axis line
    fig.add_trace(go.Scatter3d(
        x=axis_line_points,
        y=zeros,
        z=zeros,
        mode='lines',
        line=dict(color='gray', width=2, dash='dash'),
        showlegend=False
    ))
    
    # Y-axis line
    fig.add_trace(go.Scatter3d(
        x=zeros,
        y=axis_line_points,
        z=zeros,
        mode='lines',
        line=dict(color='gray', width=2, dash='dash'),
        showlegend=False
    ))
    
    # Z-axis line
    fig.add_trace(go.Scatter3d(
        x=zeros,
        y=zeros,
        z=axis_line_points,
        mode='lines',
        line=dict(color='gray', width=2, dash='dash'),
        showlegend=False
    ))
    
    # Set up the layout
    fig.update_layout(
        title="6-Dimensional Confluence Model Visualization",
        scene=dict(
            xaxis_title="Technical",
            yaxis_title="Volume",
            zaxis_title="Orderbook",
            xaxis=dict(range=[0, 100], tickvals=[0, 25, 50, 75, 100]),
            yaxis=dict(range=[0, 100], tickvals=[0, 25, 50, 75, 100]),
            zaxis=dict(range=[0, 100], tickvals=[0, 25, 50, 75, 100]),
            aspectmode='cube'
        ),
        margin=dict(l=0, r=0, b=0, t=30),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        annotations=[
            dict(
                showarrow=False,
                x=0.5,
                y=1.12,
                text=f"<b>Orderflow: {component_scores['Orderflow']:.2f} (Size) | "
                     f"Sentiment: {component_scores['Sentiment']:.2f} (Color) | "
                     f"Price Structure: {component_scores['Price Structure']:.2f}</b>",
                xref="paper",
                yref="paper",
                font=dict(size=12)
            )
        ]
    )
    
    return fig

# --- Main execution ---
if __name__ == "__main__":
    # Create radar chart visualization
    radar_fig = create_confluence_radar_chart(component_scores, overall_score)
    plt.savefig('confluence_radar_chart.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Radar chart saved as 'confluence_radar_chart.png'")
    
    # Create 3D visualization
    threed_fig = create_3d_confluence_visualization(component_scores, overall_score)
    threed_fig.write_html('confluence_3d_visualization.html')
    print("3D visualization saved as 'confluence_3d_visualization.html'")
    
    # Optional: Add a simpler function to test the visualization with random data
    def test_with_random_data():
        import random
        random_scores = {
            'Technical': random.uniform(0, 100),
            'Volume': random.uniform(0, 100),
            'Orderbook': random.uniform(0, 100),
            'Orderflow': random.uniform(0, 100),
            'Sentiment': random.uniform(0, 100),
            'Price Structure': random.uniform(0, 100)
        }
        random_overall = sum(random_scores.values()) / len(random_scores)
        
        radar_fig = create_confluence_radar_chart(random_scores, random_overall)
        plt.savefig('random_radar_chart.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        threed_fig = create_3d_confluence_visualization(random_scores, random_overall)
        threed_fig.write_html('random_3d_visualization.html')
        
        print("Random data visualizations created for testing")

    # Uncomment the following line to test with random data
    # test_with_random_data() 