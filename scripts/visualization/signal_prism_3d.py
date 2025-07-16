"""
3D Signal Prism Visualization
============================

Creates an interactive 3D hexagonal prism visualization where each face represents
a different signal component from the confluence analysis. Designed to give traders
a physical, intuitive representation of market signals.

Components visualized:
- Technical Analysis (20% weight)
- Volume Analysis (10% weight) 
- Orderflow Analysis (25% weight)
- Sentiment Analysis (15% weight)
- Orderbook Analysis (20% weight)
- Price Structure Analysis (10% weight)
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as pyo
from typing import Dict, List, Tuple, Any, Optional
import json
import pandas as pd
from datetime import datetime
import math


class SignalPrism3D:
    """Creates 3D prism visualizations for trading signal confluence analysis."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the 3D prism visualizer."""
        self.config = config or {}
        
        # Component mapping - matches confluence analyzer structure
        self.components = {
            'technical': {'name': 'Technical', 'weight': 0.20, 'position': 0},
            'volume': {'name': 'Volume', 'weight': 0.10, 'position': 1},
            'orderflow': {'name': 'Orderflow', 'weight': 0.25, 'position': 2},
            'sentiment': {'name': 'Sentiment', 'weight': 0.15, 'position': 3},
            'orderbook': {'name': 'Orderbook', 'weight': 0.20, 'position': 4},
            'price_structure': {'name': 'Price Structure', 'weight': 0.10, 'position': 5}
        }
        
        # Color scheme for signal strength
        self.color_scheme = {
            'bullish': '#00FF88',    # Bright green
            'bearish': '#FF4444',    # Bright red
            'neutral': '#FFAA00',    # Orange/yellow
            'strong_bullish': '#00CC00',  # Dark green
            'strong_bearish': '#CC0000',  # Dark red
            'edge': '#333333',       # Dark edge color
            'background': '#1a1a1a'  # Dark background
        }
        
        # Prism geometry settings
        self.base_radius = 1.0
        self.min_height = 0.2
        self.max_height = 2.0
        
    def generate_hexagon_vertices(self, radius: float = 1.0, z: float = 0.0) -> List[Tuple[float, float, float]]:
        """Generate vertices for a hexagon at a given z-level."""
        vertices = []
        for i in range(6):
            angle = i * np.pi / 3  # 60 degrees apart
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            vertices.append((x, y, z))
        return vertices
    
    def get_signal_color(self, score: float, confidence: float = 1.0) -> str:
        """Get color based on signal score with confidence modulation."""
        if score >= 70:
            return self.color_scheme['strong_bullish'] if confidence > 0.7 else self.color_scheme['bullish']
        elif score >= 60:
            return self.color_scheme['bullish']
        elif score <= 30:
            return self.color_scheme['strong_bearish'] if confidence > 0.7 else self.color_scheme['bearish']
        elif score <= 40:
            return self.color_scheme['bearish']
        else:
            return self.color_scheme['neutral']
    
    def calculate_opacity(self, confidence: float, base_opacity: float = 0.8) -> float:
        """Calculate opacity based on confidence level."""
        return min(base_opacity * confidence, 1.0)
    
    def create_prism_mesh(self, component_scores: Dict[str, float], 
                         overall_score: float, 
                         confidence: float = 0.8) -> go.Figure:
        """Create the main 3D prism mesh visualization."""
        
        # Calculate prism height based on overall score
        height = self.min_height + (overall_score / 100.0) * (self.max_height - self.min_height)
        
        # Generate base and top hexagon vertices
        base_vertices = self.generate_hexagon_vertices(self.base_radius, 0)
        top_vertices = self.generate_hexagon_vertices(self.base_radius, height)
        
        fig = go.Figure()
        
        # Create each face of the hexagonal prism
        for i in range(6):
            component_key = list(self.components.keys())[i]
            component_name = self.components[component_key]['name']
            score = component_scores.get(component_key, 50.0)
            weight = self.components[component_key]['weight']
            
            # Get next vertex index (wrapping around)
            next_i = (i + 1) % 6
            
            # Define the quadrilateral face vertices
            face_vertices = [
                base_vertices[i],      # Bottom left
                base_vertices[next_i], # Bottom right  
                top_vertices[next_i],  # Top right
                top_vertices[i]        # Top left
            ]
            
            # Extract coordinates
            x_coords = [v[0] for v in face_vertices] + [face_vertices[0][0]]  # Close the face
            y_coords = [v[1] for v in face_vertices] + [face_vertices[0][1]]
            z_coords = [v[2] for v in face_vertices] + [face_vertices[0][2]]
            
            # Get face color and opacity
            face_color = self.get_signal_color(score, confidence)
            opacity = self.calculate_opacity(confidence)
            
            # Create hover text with detailed information
            hover_text = (
                f"<b>{component_name}</b><br>"
                f"Score: {score:.1f}/100<br>"
                f"Weight: {weight*100:.0f}%<br>"
                f"Confidence: {confidence*100:.0f}%<br>"
                f"Overall Impact: {score * weight:.1f}"
            )
            
            # Add face as a surface
            fig.add_trace(go.Mesh3d(
                x=x_coords[:-1],  # Remove duplicate closing vertex for mesh
                y=y_coords[:-1],
                z=z_coords[:-1],
                i=[0, 0],  # Triangle indices for the quad
                j=[1, 2],
                k=[2, 3],
                color=face_color,
                opacity=opacity,
                hoverinfo='text',
                hovertext=hover_text,
                name=f"{component_name}: {score:.1f}",
                showlegend=True,
                lighting=dict(
                    ambient=0.6,
                    diffuse=0.8,
                    specular=0.1
                )
            ))
            
            # Add edge lines for better definition
            fig.add_trace(go.Scatter3d(
                x=x_coords,
                y=y_coords,
                z=z_coords,
                mode='lines',
                line=dict(color=self.color_scheme['edge'], width=2),
                hoverinfo='skip',
                showlegend=False,
                name=f"{component_name}_edge"
            ))
        
        # Add base and top hexagon faces
        self._add_hexagon_faces(fig, base_vertices, top_vertices, overall_score, confidence)
        
        # Add center pillar for overall score visualization
        self._add_center_pillar(fig, overall_score, height, confidence)
        
        return fig
    
    def _add_hexagon_faces(self, fig: go.Figure, base_vertices: List, top_vertices: List, 
                          overall_score: float, confidence: float):
        """Add the top and bottom hexagonal faces."""
        
        # Base hexagon (bottom)
        base_x = [v[0] for v in base_vertices] + [base_vertices[0][0]]
        base_y = [v[1] for v in base_vertices] + [base_vertices[0][1]]
        base_z = [v[2] for v in base_vertices] + [base_vertices[0][2]]
        
        fig.add_trace(go.Scatter3d(
            x=base_x,
            y=base_y,
            z=base_z,
            mode='lines',
            line=dict(color=self.color_scheme['edge'], width=3),
            hoverinfo='text',
            hovertext=f"<b>Base Platform</b><br>Overall Score: {overall_score:.1f}",
            name="Base",
            showlegend=False
        ))
        
        # Top hexagon  
        top_x = [v[0] for v in top_vertices] + [top_vertices[0][0]]
        top_y = [v[1] for v in top_vertices] + [top_vertices[0][1]]
        top_z = [v[2] for v in top_vertices] + [top_vertices[0][2]]
        
        fig.add_trace(go.Scatter3d(
            x=top_x,
            y=top_y,
            z=top_z,
            mode='lines',
            line=dict(color=self.color_scheme['edge'], width=3),
            hoverinfo='text',
            hovertext=f"<b>Signal Peak</b><br>Overall Score: {overall_score:.1f}",
            name="Peak",
            showlegend=False
        ))
    
    def _add_center_pillar(self, fig: go.Figure, overall_score: float, height: float, confidence: float):
        """Add a center pillar showing overall signal strength."""
        
        # Create a small cylinder in the center
        pillar_radius = 0.1
        pillar_height = height * 0.9  # Slightly shorter than prism
        
        # Generate cylinder vertices
        theta = np.linspace(0, 2*np.pi, 8)
        x_cylinder = pillar_radius * np.cos(theta)
        y_cylinder = pillar_radius * np.sin(theta)
        
        # Create cylinder surface
        for i in range(len(theta)-1):
            x_quad = [x_cylinder[i], x_cylinder[i+1], x_cylinder[i+1], x_cylinder[i]]
            y_quad = [y_cylinder[i], y_cylinder[i+1], y_cylinder[i+1], y_cylinder[i]]
            z_quad = [0.05, 0.05, pillar_height, pillar_height]
            
            pillar_color = self.get_signal_color(overall_score, confidence)
            
            fig.add_trace(go.Mesh3d(
                x=x_quad,
                y=y_quad,
                z=z_quad,
                i=[0, 0],
                j=[1, 2],
                k=[2, 3],
                color=pillar_color,
                opacity=0.9,
                hoverinfo='text',
                hovertext=f"<b>Overall Signal</b><br>Score: {overall_score:.1f}<br>Confidence: {confidence*100:.0f}%",
                name=f"Overall: {overall_score:.1f}",
                showlegend=False
            ))
    
    def create_interactive_visualization(self, component_scores: Dict[str, float], 
                                       overall_score: float, 
                                       confidence: float = 0.8,
                                       symbol: str = "SYMBOL",
                                       timestamp: Optional[datetime] = None) -> go.Figure:
        """Create the complete interactive 3D prism visualization."""
        
        # Create main prism
        fig = self.create_prism_mesh(component_scores, overall_score, confidence)
        
        # Configure layout for optimal viewing
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "Live"
        
        fig.update_layout(
            title=dict(
                text=f"<b>Signal Prism - {symbol}</b><br>"
                     f"<span style='font-size:14px'>Overall Score: {overall_score:.1f} | "
                     f"Confidence: {confidence*100:.0f}% | {timestamp_str}</span>",
                x=0.5,
                xanchor='center',
                font=dict(size=18, color='white')
            ),
            scene=dict(
                bgcolor=self.color_scheme['background'],
                xaxis=dict(
                    showbackground=True,
                    backgroundcolor='rgba(0,0,0,0.1)',
                    gridcolor='rgba(255,255,255,0.1)',
                    showticklabels=False,
                    title=""
                ),
                yaxis=dict(
                    showbackground=True,
                    backgroundcolor='rgba(0,0,0,0.1)',
                    gridcolor='rgba(255,255,255,0.1)',
                    showticklabels=False,
                    title=""
                ),
                zaxis=dict(
                    showbackground=True,
                    backgroundcolor='rgba(0,0,0,0.1)',
                    gridcolor='rgba(255,255,255,0.1)',
                    title=dict(text="Signal Strength", font=dict(color='white')),
                    tickfont=dict(color='white')
                ),
                camera=dict(
                    eye=dict(x=2, y=2, z=1.5),
                    center=dict(x=0, y=0, z=0.5),
                    up=dict(x=0, y=0, z=1)
                ),
                aspectmode='cube'
            ),
            paper_bgcolor=self.color_scheme['background'],
            plot_bgcolor=self.color_scheme['background'],
            font=dict(color='white'),
            width=900,
            height=700,
            legend=dict(
                bgcolor='rgba(0,0,0,0.5)',
                bordercolor='rgba(255,255,255,0.2)',
                borderwidth=1,
                font=dict(color='white', size=10)
            )
        )
        
        return fig
    
    def add_animation_controls(self, fig: go.Figure) -> go.Figure:
        """Add rotation animation controls to the visualization."""
        
        # Add rotation animation frames
        frames = []
        for angle in range(0, 360, 10):
            # Calculate camera position for rotation
            angle_rad = np.radians(angle)
            camera_x = 2 * np.cos(angle_rad)
            camera_y = 2 * np.sin(angle_rad)
            
            frame = go.Frame(
                layout=dict(
                    scene_camera=dict(
                        eye=dict(x=camera_x, y=camera_y, z=1.5),
                        center=dict(x=0, y=0, z=0.5),
                        up=dict(x=0, y=0, z=1)
                    )
                )
            )
            frames.append(frame)
        
        fig.frames = frames
        
        # Add animation buttons
        fig.update_layout(
            updatemenus=[{
                'type': 'buttons',
                'showactive': False,
                'x': 0.1,
                'y': 0.02,
                'buttons': [
                    {
                        'label': '▶️ Rotate',
                        'method': 'animate',
                        'args': [None, {
                            'frame': {'duration': 100, 'redraw': True},
                            'fromcurrent': True,
                            'transition': {'duration': 50}
                        }]
                    },
                    {
                        'label': '⏸️ Stop',
                        'method': 'animate',
                        'args': [[None], {
                            'frame': {'duration': 0, 'redraw': False},
                            'mode': 'immediate',
                            'transition': {'duration': 0}
                        }]
                    }
                ]
            }]
        )
        
        return fig
    
    def create_dashboard_view(self, component_scores: Dict[str, float], 
                            overall_score: float, 
                            confidence: float = 0.8,
                            symbol: str = "SYMBOL") -> go.Figure:
        """Create a dashboard view with multiple angles of the prism."""
        
        # Create subplots with 3D scenes
        fig = make_subplots(
            rows=2, cols=2,
            specs=[[{'type': 'scene'}, {'type': 'scene'}],
                   [{'type': 'scene'}, {'type': 'scene'}]],
            subplot_titles=['Front View', 'Side View', 'Top View', '3D Interactive'],
            vertical_spacing=0.1,
            horizontal_spacing=0.1
        )
        
        # Different camera angles for each subplot
        camera_configs = [
            {'eye': dict(x=0, y=3, z=1), 'title': 'Front View'},
            {'eye': dict(x=3, y=0, z=1), 'title': 'Side View'}, 
            {'eye': dict(x=0, y=0, z=3), 'title': 'Top View'},
            {'eye': dict(x=2, y=2, z=1.5), 'title': '3D Interactive'}
        ]
        
        positions = [(1,1), (1,2), (2,1), (2,2)]
        
        for idx, (pos, camera_config) in enumerate(zip(positions, camera_configs)):
            # Create prism for this view
            prism_fig = self.create_prism_mesh(component_scores, overall_score, confidence)
            
            # Add traces to subplot
            for trace in prism_fig.data:
                fig.add_trace(trace, row=pos[0], col=pos[1])
        
        # Update layout
        fig.update_layout(
            title=f"Signal Prism Dashboard - {symbol}",
            paper_bgcolor=self.color_scheme['background'],
            plot_bgcolor=self.color_scheme['background'],
            font=dict(color='white'),
            height=800,
            showlegend=False
        )
        
        return fig
    
    def save_visualization(self, fig: go.Figure, filename: str, 
                          output_dir: str = "examples/demo/3d_viz_output"):
        """Save the visualization to HTML file."""
        import os
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Full file path
        filepath = os.path.join(output_dir, f"{filename}.html")
        
        # Save as HTML
        pyo.plot(fig, filename=filepath, auto_open=False)
        
        return filepath


def demo_signal_prism():
    """Demonstration of the 3D signal prism visualization."""
    
    # Sample data from the log analysis
    component_scores = {
        'technical': 44.74,
        'volume': 43.15,
        'orderbook': 60.08,
        'orderflow': 73.08,
        'sentiment': 62.10,
        'price_structure': 46.82
    }
    
    overall_score = 56.87
    confidence = 0.78
    symbol = "XRPUSDT"
    
    # Create visualizer
    visualizer = SignalPrism3D()
    
    # Create interactive visualization
    fig = visualizer.create_interactive_visualization(
        component_scores, overall_score, confidence, symbol, datetime.now()
    )
    
    # Add animation controls
    fig = visualizer.add_animation_controls(fig)
    
    # Save visualization
    filepath = visualizer.save_visualization(fig, f"signal_prism_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    print(f"3D Signal Prism visualization saved to: {filepath}")
    
    # Also create dashboard view
    dashboard_fig = visualizer.create_dashboard_view(component_scores, overall_score, confidence, symbol)
    dashboard_path = visualizer.save_visualization(dashboard_fig, f"signal_dashboard_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    print(f"Signal Dashboard saved to: {dashboard_path}")
    
    return fig, dashboard_fig


if __name__ == "__main__":
    demo_signal_prism() 