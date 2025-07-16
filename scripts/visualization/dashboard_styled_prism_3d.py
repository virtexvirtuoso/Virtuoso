"""
Dashboard-Styled 3D Signal Prism
===============================

3D signal prism visualization that matches the Virtuoso Terminal dashboard style:
- Terminal amber + navy blue color scheme
- JetBrains Mono typography
- Professional dark theme
- Consistent with dashboard_v10.html aesthetics
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


class DashboardStyledPrism3D:
    """3D signal prism with dashboard terminal styling."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the dashboard-styled 3D prism visualizer."""
        self.config = config or {}
        
        # Dashboard color scheme (matching dashboard_v10.html)
        self.colors = {
            # Primary colors
            'bg_primary': '#0c1a2b',
            'bg_secondary': '#0f172a', 
            'bg_hero': '#0f172a',
            'bg_satellite': '#0f172a',
            'bg_header': '#0a1525',
            
            # Text colors
            'text_primary': '#ffbf00',
            'text_secondary': '#b8860b',
            
            # Accent colors
            'accent_primary': '#ff9900',
            'accent_positive': '#ffc107',
            'accent_negative': '#ff5722',
            'accent_warning': '#ff9900',
            
            # Border and glow
            'border_light': '#1a2a40',
            'glow_amber': '#ffbf00',
            
            # Signal confidence colors
            'signal_strong': '#ffc107',
            'signal_medium': '#ff9900',
            'signal_weak': '#ff7043',
            'signal_neutral': '#607d8b',
            'signal_negative': '#f44336'
        }
        
        # Component mapping with dashboard styling
        self.components = {
            'technical': {
                'name': 'TECHNICAL ANALYSIS',
                'weight': 0.136,
                'position': 0,
                'icon': '📈',
                'color_base': self.colors['accent_positive'],
                'description': 'Technical indicators and trend analysis'
            },
            'volume': {
                'name': 'VOLUME ANALYSIS',
                'weight': 0.096,
                'position': 1,
                'icon': '📊',
                'color_base': self.colors['signal_strong'],
                'description': 'Volume patterns and participation'
            },
            'orderflow': {
                'name': 'ORDER FLOW',
                'weight': 0.200,
                'position': 2,
                'icon': '🌊',
                'color_base': self.colors['accent_primary'],
                'description': 'Institutional order flow pressure'
            },
            'sentiment': {
                'name': 'MARKET SENTIMENT',
                'weight': 0.080,
                'position': 3,
                'icon': '🎭',
                'color_base': self.colors['signal_medium'],
                'description': 'Market sentiment and positioning'
            },
            'orderbook': {
                'name': 'ORDER BOOK',
                'weight': 0.160,
                'position': 4,
                'icon': '📋',
                'color_base': self.colors['text_primary'],
                'description': 'Order book depth and liquidity'
            },
            'price_structure': {
                'name': 'PRICE STRUCTURE',
                'weight': 0.120,
                'position': 5,
                'icon': '🏗️',
                'color_base': self.colors['text_secondary'],
                'description': 'Support/resistance levels and range analysis'
            }
        }
        
        # Dashboard typography
        self.typography = {
            'font_family': 'JetBrains Mono, Courier New, monospace',
            'title_size': 24,
            'subtitle_size': 16,
            'label_size': 12,
            'small_size': 10
        }
    
    def create_dashboard_styled_prism(self, component_scores: Dict[str, float],
                                    overall_score: float,
                                    confidence: float = 0.8,
                                    symbol: str = "SYMBOL",
                                    timestamp: Optional[datetime] = None) -> go.Figure:
        """Create dashboard-styled 3D prism visualization."""
        
        fig = go.Figure()
        
        # Add main hexagonal prism
        self.add_main_prism(fig, component_scores, overall_score, confidence, symbol)
        
        # Add component labels with dashboard styling
        self.add_component_labels(fig, component_scores, confidence)
        
        # Add terminal-style particle effects
        self.add_terminal_particles(fig, overall_score)
        
        # Configure dashboard layout
        self.configure_dashboard_layout(fig, overall_score, confidence, symbol, timestamp)
        
        # Add terminal-style animation controls
        self.add_terminal_animation_controls(fig)
        
        return fig
    
    def add_main_prism(self, fig: go.Figure, component_scores: Dict[str, float],
                      overall_score: float, confidence: float, symbol: str) -> None:
        """Add the main hexagonal prism with dashboard styling."""
        
        # Calculate prism height based on overall score
        height = 0.5 + (overall_score / 100.0) * 2.0
        radius = 1.2
        
        # Generate hexagon vertices
        angles = np.linspace(0, 2*np.pi, 7)  # 7 points to close the hexagon
        
        # Bottom face vertices
        x_bottom = radius * np.cos(angles)
        y_bottom = radius * np.sin(angles)
        z_bottom = np.zeros_like(angles)
        
        # Top face vertices
        x_top = radius * np.cos(angles)
        y_top = radius * np.sin(angles)
        z_top = np.full_like(angles, height)
        
        # Combine all vertices
        x_vertices = np.concatenate([x_bottom, x_top])
        y_vertices = np.concatenate([y_bottom, y_top])
        z_vertices = np.concatenate([z_bottom, z_top])
        
        # Create faces for the hexagonal prism
        faces = []
        
        # Bottom face (triangulated)
        for i in range(5):
            faces.append([0, i+1, i+2])
        
        # Top face (triangulated)
        for i in range(5):
            faces.append([7, 7+i+2, 7+i+1])
        
        # Side faces
        for i in range(6):
            next_i = (i + 1) % 6
            # Two triangles per side face
            faces.append([i, next_i, 7+i])
            faces.append([next_i, 7+next_i, 7+i])
        
        # Flatten faces for plotly
        i_faces = [face[0] for face in faces]
        j_faces = [face[1] for face in faces]
        k_faces = [face[2] for face in faces]
        
        # Determine prism color based on overall score
        if overall_score >= 70:
            prism_color = self.colors['accent_positive']
            prism_opacity = 0.8
        elif overall_score >= 50:
            prism_color = self.colors['signal_medium']
            prism_opacity = 0.7
        else:
            prism_color = self.colors['signal_weak']
            prism_opacity = 0.6
        
        # Add main prism mesh
        fig.add_trace(go.Mesh3d(
            x=x_vertices,
            y=y_vertices,
            z=z_vertices,
            i=i_faces,
            j=j_faces,
            k=k_faces,
            color=prism_color,
            opacity=prism_opacity * confidence,
            lighting=dict(
                ambient=0.4,
                diffuse=0.8,
                specular=0.9,
                roughness=0.2,
                fresnel=0.3
            ),
            lightposition=dict(x=100, y=200, z=300),
            hoverinfo='text',
            hovertext=f"<b>SIGNAL PRISM - {symbol}</b><br>Overall Score: {overall_score:.1f}/100<br>Confidence: {confidence*100:.0f}%",
            name="Signal Prism",
            showlegend=False
        ))
        
        # Add center pillar with gradient effect
        self.add_center_pillar(fig, overall_score, height)
    
    def add_center_pillar(self, fig: go.Figure, overall_score: float, height: float) -> None:
        """Add center pillar with terminal-style gradient."""
        
        # Create cylinder for center pillar
        theta = np.linspace(0, 2*np.pi, 20)
        pillar_radius = 0.15
        
        # Cylinder vertices
        x_cyl = []
        y_cyl = []
        z_cyl = []
        
        # Bottom circle
        for t in theta:
            x_cyl.append(pillar_radius * np.cos(t))
            y_cyl.append(pillar_radius * np.sin(t))
            z_cyl.append(0)
        
        # Top circle
        for t in theta:
            x_cyl.append(pillar_radius * np.cos(t))
            y_cyl.append(pillar_radius * np.sin(t))
            z_cyl.append(height)
        
        # Create cylinder faces
        n_points = len(theta)
        i_cyl = []
        j_cyl = []
        k_cyl = []
        
        # Side faces
        for i in range(n_points - 1):
            # Two triangles per side
            i_cyl.extend([i, i+1, i+n_points])
            j_cyl.extend([i+1, i+n_points+1, i+n_points+1])
            k_cyl.extend([i+n_points, i+n_points, i+1])
        
        # Determine pillar color based on score
        if overall_score >= 70:
            pillar_color = self.colors['accent_positive']
        elif overall_score >= 50:
            pillar_color = self.colors['signal_medium']
        else:
            pillar_color = self.colors['signal_weak']
        
        fig.add_trace(go.Mesh3d(
            x=x_cyl,
            y=y_cyl,
            z=z_cyl,
            i=i_cyl,
            j=j_cyl,
            k=k_cyl,
            color=pillar_color,
            opacity=0.9,
            lighting=dict(
                ambient=0.3,
                diffuse=0.7,
                specular=1.0,
                roughness=0.1,
                fresnel=0.4
            ),
            hoverinfo='skip',
            showlegend=False,
            name="center_pillar"
        ))
    
    def add_component_labels(self, fig: go.Figure, component_scores: Dict[str, float],
                           confidence: float) -> None:
        """Add component labels with dashboard terminal styling."""
        
        radius = 1.5
        
        for i, (component_key, score) in enumerate(component_scores.items()):
            if component_key not in self.components:
                continue
                
            component_info = self.components[component_key]
            
            # Calculate position on hexagon perimeter
            angle = (i * np.pi / 3) + (np.pi / 6)
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            z = 1.2  # Mid-height
            
            # Determine label color based on score
            if score >= 70:
                label_color = self.colors['accent_positive']
                bg_color = 'rgba(255, 193, 7, 0.2)'
            elif score >= 50:
                label_color = self.colors['signal_medium']
                bg_color = 'rgba(255, 153, 0, 0.2)'
            else:
                label_color = self.colors['signal_weak']
                bg_color = 'rgba(255, 112, 67, 0.2)'
            
            # Add component label with terminal styling
            fig.add_trace(go.Scatter3d(
                x=[x],
                y=[y],
                z=[z],
                mode='text+markers',
                text=[f"<b>{component_info['icon']}<br>{component_key.upper()}<br>{score:.0f}%</b>"],
                textfont=dict(
                    size=self.typography['label_size'],
                    color=label_color,
                    family=self.typography['font_family']
                ),
                marker=dict(
                    size=25,
                    color=bg_color,
                    opacity=confidence,
                    symbol='square',
                    line=dict(width=2, color=label_color)
                ),
                hoverinfo='text',
                hovertext=(
                    f"<b>{component_info['name']}</b><br>"
                    f"Score: {score:.1f}/100<br>"
                    f"Weight: {component_info['weight']*100:.1f}%<br>"
                    f"Confidence: {confidence*100:.0f}%<br>"
                    f"Description: {component_info['description']}"
                ),
                showlegend=False,
                name=f"{component_key}_label"
            ))
    
    def add_terminal_particles(self, fig: go.Figure, overall_score: float) -> None:
        """Add terminal-style particle effects."""
        
        # Adaptive particle count based on signal strength
        num_particles = min(80, max(20, int(overall_score * 0.8)))
        
        particles_x = []
        particles_y = []
        particles_z = []
        particle_colors = []
        particle_sizes = []
        
        for i in range(num_particles):
            # Create particles in terminal-style patterns
            if i < num_particles // 2:
                # Orbital particles around prism
                angle = np.random.uniform(0, 2 * np.pi)
                radius = np.random.uniform(2.0, 3.5)
                height = np.random.uniform(0, 2.5)
                
                x = radius * np.cos(angle)
                y = radius * np.sin(angle)
                z = height
            else:
                # Floating particles above prism
                x = np.random.uniform(-2.0, 2.0)
                y = np.random.uniform(-2.0, 2.0)
                z = np.random.uniform(2.5, 4.0)
            
            particles_x.append(x)
            particles_y.append(y)
            particles_z.append(z)
            
            # Terminal amber color scheme for particles
            if overall_score >= 70:
                color = self.colors['accent_positive']
                alpha = 0.8
            elif overall_score >= 50:
                color = self.colors['signal_medium']
                alpha = 0.6
            else:
                color = self.colors['signal_weak']
                alpha = 0.4
            
            particle_colors.append(color)
            particle_sizes.append(np.random.uniform(2, 6))
        
        # Add particle system
        fig.add_trace(go.Scatter3d(
            x=particles_x,
            y=particles_y,
            z=particles_z,
            mode='markers',
            marker=dict(
                size=particle_sizes,
                color=particle_colors,
                opacity=0.7,
                symbol='circle'
            ),
            hoverinfo='skip',
            showlegend=False,
            name="terminal_particles"
        ))
    
    def configure_dashboard_layout(self, fig: go.Figure, overall_score: float,
                                 confidence: float, symbol: str,
                                 timestamp: Optional[datetime]) -> None:
        """Configure layout with dashboard terminal styling."""
        
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "LIVE"
        
        # Determine signal status with terminal styling
        if overall_score >= 70:
            status_emoji = "🚀"
            status_text = "STRONG BULLISH"
            status_color = self.colors['accent_positive']
        elif overall_score >= 50:
            status_emoji = "📈"
            status_text = "BULLISH BIAS"
            status_color = self.colors['signal_medium']
        elif overall_score >= 30:
            status_emoji = "⚖️"
            status_text = "NEUTRAL"
            status_color = self.colors['signal_weak']
        else:
            status_emoji = "📉"
            status_text = "BEARISH"
            status_color = self.colors['signal_negative']
        
        fig.update_layout(
            title=dict(
                text=(
                    f"<b style='color:{self.colors['accent_positive']}; font-family:{self.typography['font_family']}'>"
                    f"{status_emoji} VIRTUOSO TERMINAL - SIGNAL PRISM</b><br>"
                    f"<span style='font-size:{self.typography['subtitle_size']}px; color:{status_color}; font-family:{self.typography['font_family']}'>"
                    f"ASSET: {symbol} | SCORE: {overall_score:.1f}/100 | CONFIDENCE: {confidence*100:.0f}% | {status_text}</span><br>"
                    f"<span style='font-size:{self.typography['small_size']}px; color:{self.colors['text_secondary']}; font-family:{self.typography['font_family']}'>"
                    f"TIMESTAMP: {timestamp_str} | CONFLUENCE ANALYSIS v10.0</span>"
                ),
                x=0.5,
                xanchor='center',
                font=dict(
                    size=self.typography['title_size'],
                    color=self.colors['text_primary'],
                    family=self.typography['font_family']
                )
            ),
            scene=dict(
                bgcolor=self.colors['bg_primary'],
                xaxis=dict(
                    showbackground=True,
                    backgroundcolor=self.colors['bg_satellite'],
                    gridcolor=self.colors['border_light'],
                    showticklabels=False,
                    title="",
                    showgrid=True,
                    zeroline=False,
                    showspikes=False
                ),
                yaxis=dict(
                    showbackground=True,
                    backgroundcolor=self.colors['bg_satellite'],
                    gridcolor=self.colors['border_light'],
                    showticklabels=False,
                    title="",
                    showgrid=True,
                    zeroline=False,
                    showspikes=False
                ),
                zaxis=dict(
                    showbackground=True,
                    backgroundcolor=self.colors['bg_satellite'],
                    gridcolor=self.colors['border_light'],
                    title=dict(
                        text="SIGNAL STRENGTH",
                        font=dict(
                            color=self.colors['text_primary'],
                            size=self.typography['label_size'],
                            family=self.typography['font_family']
                        )
                    ),
                    tickfont=dict(
                        color=self.colors['text_secondary'],
                        size=self.typography['small_size'],
                        family=self.typography['font_family']
                    ),
                    showgrid=True,
                    zeroline=False,
                    showspikes=False
                ),
                camera=dict(
                    eye=dict(x=2.5, y=2.5, z=2.0),
                    center=dict(x=0, y=0, z=1.0),
                    up=dict(x=0, y=0, z=1),
                    projection=dict(type='perspective')
                ),
                aspectmode='cube',
                dragmode='orbit'
            ),
            paper_bgcolor=self.colors['bg_primary'],
            plot_bgcolor=self.colors['bg_primary'],
            font=dict(
                color=self.colors['text_primary'],
                family=self.typography['font_family']
            ),
            width=1200,
            height=900,
            legend=dict(
                bgcolor=self.colors['bg_satellite'],
                bordercolor=self.colors['border_light'],
                borderwidth=2,
                font=dict(
                    color=self.colors['text_primary'],
                    size=self.typography['small_size'],
                    family=self.typography['font_family']
                ),
                x=1.02,
                y=1,
                xanchor='left',
                yanchor='top'
            ),
            hovermode='closest'
        )
    
    def add_terminal_animation_controls(self, fig: go.Figure) -> go.Figure:
        """Add terminal-style animation controls."""
        
        # Create smooth rotation frames
        frames = []
        for angle in range(0, 360, 3):  # 3-degree increments for smooth rotation
            angle_rad = np.radians(angle)
            camera_x = 2.5 * np.cos(angle_rad)
            camera_y = 2.5 * np.sin(angle_rad)
            camera_z = 2.0 + 0.3 * np.sin(angle_rad * 2)  # Slight vertical oscillation
            
            frame = go.Frame(
                layout=dict(
                    scene_camera=dict(
                        eye=dict(x=camera_x, y=camera_y, z=camera_z),
                        center=dict(x=0, y=0, z=1.0),
                        up=dict(x=0, y=0, z=1)
                    )
                ),
                name=f"frame_{angle}"
            )
            frames.append(frame)
        
        fig.frames = frames
        
        # Terminal-style animation controls
        fig.update_layout(
            updatemenus=[{
                'type': 'buttons',
                'showactive': False,
                'x': 0.02,
                'y': 0.95,
                'xanchor': 'left',
                'yanchor': 'top',
                'bgcolor': self.colors['bg_satellite'],
                'bordercolor': self.colors['border_light'],
                'borderwidth': 2,
                'font': dict(
                    color=self.colors['text_primary'],
                    family=self.typography['font_family'],
                    size=self.typography['small_size']
                ),
                'buttons': [
                    {
                        'label': '▶️ TERMINAL ROTATE',
                        'method': 'animate',
                        'args': [None, {
                            'frame': {'duration': 60, 'redraw': True},
                            'fromcurrent': True,
                            'transition': {'duration': 30, 'easing': 'cubic-in-out'}
                        }]
                    },
                    {
                        'label': '⏸️ PAUSE',
                        'method': 'animate',
                        'args': [[None], {
                            'frame': {'duration': 0, 'redraw': False},
                            'mode': 'immediate',
                            'transition': {'duration': 0}
                        }]
                    },
                    {
                        'label': '🎯 FOCUS',
                        'method': 'relayout',
                        'args': [{
                            'scene.camera': {
                                'eye': dict(x=1.8, y=1.8, z=1.5),
                                'center': dict(x=0, y=0, z=1.0),
                                'up': dict(x=0, y=0, z=1)
                            }
                        }]
                    },
                    {
                        'label': '🌐 OVERVIEW',
                        'method': 'relayout',
                        'args': [{
                            'scene.camera': {
                                'eye': dict(x=4.0, y=4.0, z=3.0),
                                'center': dict(x=0, y=0, z=1.0),
                                'up': dict(x=0, y=0, z=1)
                            }
                        }]
                    }
                ]
            }]
        )
        
        return fig
    
    def save_dashboard_visualization(self, fig: go.Figure, filename: str,
                                   output_dir: str = "examples/demo/3d_viz_output") -> str:
        """Save dashboard-styled visualization with terminal enhancements."""
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, f"dashboard_{filename}.html")
        
        # Terminal-style HTML template
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Virtuoso Terminal - 3D Signal Prism</title>
            <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background: linear-gradient(135deg, {self.colors['bg_primary']} 0%, {self.colors['bg_secondary']} 50%, {self.colors['bg_hero']} 100%);
                    font-family: 'JetBrains Mono', 'Courier New', monospace;
                    color: {self.colors['text_primary']};
                    overflow: hidden;
                }}
                
                /* Terminal ambient lighting */
                body::before {{
                    content: '';
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-image: 
                        radial-gradient(circle at 25% 25%, rgba(255, 191, 0, 0.05) 0%, transparent 50%),
                        radial-gradient(circle at 75% 75%, rgba(255, 153, 0, 0.05) 0%, transparent 50%);
                    background-size: 200px 200px;
                    opacity: 0.3;
                    z-index: -1;
                    pointer-events: none;
                }}
                
                .terminal-header {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    background: linear-gradient(135deg, {self.colors['bg_header']}, {self.colors['bg_satellite']});
                    border-bottom: 2px solid {self.colors['border_light']};
                    padding: 1rem 2rem;
                    z-index: 1000;
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
                }}
                
                .terminal-title {{
                    font-size: 1.5rem;
                    color: {self.colors['accent_positive']};
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 3px;
                    text-shadow: 0 0 8px {self.colors['accent_positive']};
                    margin: 0;
                }}
                
                .terminal-subtitle {{
                    font-size: 0.8rem;
                    color: {self.colors['text_secondary']};
                    margin-top: 0.5rem;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                
                .status-indicator {{
                    position: fixed;
                    top: 1rem;
                    right: 2rem;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    background: {self.colors['bg_satellite']};
                    padding: 0.5rem 1rem;
                    border: 1px solid {self.colors['border_light']};
                    border-radius: 4px;
                    z-index: 1001;
                }}
                
                .status-light {{
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: {self.colors['accent_positive']};
                    box-shadow: 0 0 10px {self.colors['accent_positive']};
                    animation: pulse 2s infinite;
                }}
                
                @keyframes pulse {{
                    0%, 100% {{ opacity: 1; }}
                    50% {{ opacity: 0.6; }}
                }}
                
                .status-text {{
                    font-size: 0.7rem;
                    color: {self.colors['text_primary']};
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                
                #plotly-div {{
                    width: 100vw;
                    height: 100vh;
                    padding-top: 80px;
                    box-sizing: border-box;
                }}
                
                /* Terminal scan line effect */
                .scan-line {{
                    position: fixed;
                    bottom: 0;
                    left: 0;
                    width: 100%;
                    height: 2px;
                    background: linear-gradient(90deg, 
                        transparent 0%, 
                        {self.colors['accent_primary']} 25%, 
                        {self.colors['accent_positive']} 50%, 
                        {self.colors['accent_primary']} 75%, 
                        transparent 100%);
                    animation: terminalScan 3s ease-in-out infinite;
                    z-index: 999;
                }}
                
                @keyframes terminalScan {{
                    0%, 100% {{ opacity: 0.3; }}
                    50% {{ opacity: 1; }}
                }}
            </style>
        </head>
        <body>
            <div class="terminal-header">
                <h1 class="terminal-title">🎯 VIRTUOSO TERMINAL</h1>
                <div class="terminal-subtitle">3D Signal Prism - Confluence Analysis</div>
            </div>
            
            <div class="status-indicator">
                <div class="status-light"></div>
                <span class="status-text">LIVE</span>
            </div>
            
            <div class="scan-line"></div>
            
            <div id="plotly-div"></div>
        """
        
        # Advanced configuration for terminal optimization
        config = {
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': f'dashboard_signal_prism_{filename}',
                'height': 900,
                'width': 1200,
                'scale': 2
            },
            'responsive': True,
            'doubleClick': 'reset+autosize'
        }
        
        pyo.plot(fig, filename=filepath, auto_open=False, config=config)
        
        return filepath


def demo_dashboard_prism():
    """Demonstration of the dashboard-styled 3D signal prism."""
    
    print("🎯 Dashboard-Styled 3D Signal Prism")
    print("=" * 50)
    
    # Your actual XRPUSDT data
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
    
    # Create dashboard-styled visualizer
    visualizer = DashboardStyledPrism3D()
    
    print("Creating dashboard-styled 3D prism...")
    fig = visualizer.create_dashboard_styled_prism(
        component_scores, overall_score, confidence, symbol, datetime.now()
    )
    
    print("Saving dashboard visualization...")
    filepath = visualizer.save_dashboard_visualization(
        fig, f"signal_prism_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    print(f"✅ Dashboard prism saved to: {filepath}")
    print("🎯 Features: Terminal styling, amber theme, JetBrains Mono, dashboard layout")
    
    return fig


if __name__ == "__main__":
    demo_dashboard_prism() 