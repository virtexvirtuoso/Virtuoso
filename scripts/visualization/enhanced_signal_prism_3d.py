"""
Enhanced 3D Signal Prism Visualization
=====================================

Optimized version of the 3D prism visualization with improved:
- Visual design and component differentiation
- User experience and interactivity
- Performance and responsiveness
- Trading-specific features and insights
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


class EnhancedSignalPrism3D:
    """Enhanced 3D prism visualizations with optimized design and trader-focused features."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the enhanced 3D prism visualizer."""
        self.config = config or {}
        
        # Component mapping with enhanced visual properties
        self.components = {
            'technical': {
                'name': 'Technical Analysis', 
                'weight': 0.20, 
                'position': 0,
                'icon': '📈',
                'description': 'Price action & indicators'
            },
            'volume': {
                'name': 'Volume Analysis', 
                'weight': 0.10, 
                'position': 1,
                'icon': '📊',
                'description': 'Trading volume patterns'
            },
            'orderflow': {
                'name': 'Order Flow', 
                'weight': 0.25, 
                'position': 2,
                'icon': '🌊',
                'description': 'Market microstructure'
            },
            'sentiment': {
                'name': 'Market Sentiment', 
                'weight': 0.15, 
                'position': 3,
                'icon': '🎭',
                'description': 'Trader psychology'
            },
            'orderbook': {
                'name': 'Order Book', 
                'weight': 0.20, 
                'position': 4,
                'icon': '📋',
                'description': 'Bid/ask dynamics'
            },
            'price_structure': {
                'name': 'Price Structure', 
                'weight': 0.10, 
                'position': 5,
                'icon': '🏗️',
                'description': 'Support & resistance'
            }
        }
        
        # Enhanced color scheme with gradients
        self.color_scheme = {
            'bullish_strong': '#00FF88',      # Bright green
            'bullish_moderate': '#00CC66',    # Medium green
            'bullish_weak': '#66DD88',        # Light green
            'bearish_strong': '#FF4444',      # Bright red
            'bearish_moderate': '#CC3333',    # Medium red
            'bearish_weak': '#DD6666',        # Light red
            'neutral_high': '#FFB366',        # Orange
            'neutral_mid': '#FFAA44',         # Medium orange
            'neutral_low': '#DD9955',         # Dark orange
            'edge': '#FFFFFF',                # White edges for contrast
            'background': '#0a0a0a',          # Darker background
            'text': '#FFFFFF',                # White text
            'accent': '#00AAFF'               # Blue accent
        }
        
        # Enhanced geometry settings
        self.base_radius = 1.2
        self.min_height = 0.3
        self.max_height = 2.5
        self.edge_width = 3
        
    def get_enhanced_color(self, score: float, confidence: float = 1.0) -> str:
        """Get enhanced color with confidence-based gradients."""
        if score >= 75:
            return self.color_scheme['bullish_strong'] if confidence > 0.8 else self.color_scheme['bullish_moderate']
        elif score >= 60:
            return self.color_scheme['bullish_moderate'] if confidence > 0.6 else self.color_scheme['bullish_weak']
        elif score <= 25:
            return self.color_scheme['bearish_strong'] if confidence > 0.8 else self.color_scheme['bearish_moderate']
        elif score <= 40:
            return self.color_scheme['bearish_moderate'] if confidence > 0.6 else self.color_scheme['bearish_weak']
        else:
            if confidence > 0.7:
                return self.color_scheme['neutral_high']
            elif confidence > 0.5:
                return self.color_scheme['neutral_mid']
            else:
                return self.color_scheme['neutral_low']
    
    def calculate_enhanced_opacity(self, confidence: float, base_opacity: float = 0.85) -> float:
        """Calculate opacity with enhanced confidence visualization."""
        # Non-linear confidence mapping for better visual distinction
        confidence_factor = np.power(confidence, 0.7)  # Softer curve
        return min(base_opacity * (0.4 + 0.6 * confidence_factor), 1.0)
    
    def generate_enhanced_hexagon_vertices(self, radius: float = 1.0, z: float = 0.0) -> List[Tuple[float, float, float]]:
        """Generate hexagon vertices with enhanced positioning."""
        vertices = []
        for i in range(6):
            # Offset by 30 degrees for better component alignment
            angle = (i * np.pi / 3) + (np.pi / 6)
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            vertices.append((x, y, z))
        return vertices
    
    def create_enhanced_face_with_label(self, fig: go.Figure, face_vertices: List, 
                                      component_key: str, score: float, 
                                      confidence: float, weight: float) -> None:
        """Create an enhanced face with integrated labels and visual effects."""
        
        component_info = self.components[component_key]
        
        # Extract coordinates
        x_coords = [v[0] for v in face_vertices]
        y_coords = [v[1] for v in face_vertices]
        z_coords = [v[2] for v in face_vertices]
        
        # Get enhanced colors
        face_color = self.get_enhanced_color(score, confidence)
        opacity = self.calculate_enhanced_opacity(confidence)
        
        # Create enhanced hover text
        hover_text = (
            f"<b>{component_info['icon']} {component_info['name']}</b><br>"
            f"<b>Score: {score:.1f}/100</b><br>"
            f"Weight: {weight*100:.0f}%<br>"
            f"Confidence: {confidence*100:.0f}%<br>"
            f"Impact: {score * weight:.1f}<br>"
            f"Description: {component_info['description']}<br>"
            f"<i>Click to focus on this component</i>"
        )
        
        # Add face with enhanced properties
        fig.add_trace(go.Mesh3d(
            x=x_coords,
            y=y_coords,
            z=z_coords,
            i=[0, 0],
            j=[1, 2],
            k=[2, 3],
            color=face_color,
            opacity=opacity,
            hoverinfo='text',
            hovertext=hover_text,
            name=f"{component_info['icon']} {component_info['name']}: {score:.1f}",
            showlegend=True,
            lighting=dict(
                ambient=0.7,
                diffuse=0.9,
                specular=0.3,
                roughness=0.1,
                fresnel=0.2
            ),
            # Enhanced visual effects
            flatshading=False,
            alphahull=0
        ))
        
        # Add enhanced edge lines
        edge_coords_x = x_coords + [x_coords[0]]
        edge_coords_y = y_coords + [y_coords[0]]
        edge_coords_z = z_coords + [z_coords[0]]
        
        fig.add_trace(go.Scatter3d(
            x=edge_coords_x,
            y=edge_coords_y,
            z=edge_coords_z,
            mode='lines',
            line=dict(
                color=self.color_scheme['edge'], 
                width=self.edge_width,
                dash='solid'
            ),
            hoverinfo='skip',
            showlegend=False,
            name=f"{component_info['name']}_edge"
        ))
        
        # Add component label on face center
        center_x = np.mean(x_coords)
        center_y = np.mean(y_coords)
        center_z = np.mean(z_coords)
        
        fig.add_trace(go.Scatter3d(
            x=[center_x],
            y=[center_y],
            z=[center_z],
            mode='text',
            text=[f"{component_info['icon']}<br>{score:.0f}"],
            textfont=dict(
                size=16,
                color=self.color_scheme['text'],
                family="Arial Black"
            ),
            hoverinfo='skip',
            showlegend=False,
            name=f"{component_info['name']}_label"
        ))
    
    def create_enhanced_center_pillar(self, fig: go.Figure, overall_score: float, 
                                    height: float, confidence: float) -> None:
        """Create an enhanced center pillar with visual effects."""
        
        pillar_radius = 0.15
        pillar_height = height * 0.95
        
        # Create gradient effect with multiple cylinders
        segments = 20
        for i in range(segments):
            segment_height = pillar_height / segments
            z_bottom = i * segment_height + 0.05
            z_top = (i + 1) * segment_height + 0.05
            
            # Color gradient from bottom to top
            gradient_factor = i / segments
            if overall_score >= 60:
                color = f"rgba(0, {int(255 * (0.8 + 0.2 * gradient_factor))}, {int(136 * (0.8 + 0.2 * gradient_factor))}, 0.9)"
            elif overall_score <= 40:
                color = f"rgba({int(255 * (0.8 + 0.2 * gradient_factor))}, {int(68 * (0.8 + 0.2 * gradient_factor))}, 68, 0.9)"
            else:
                color = f"rgba({int(255 * (0.8 + 0.2 * gradient_factor))}, {int(170 * (0.8 + 0.2 * gradient_factor))}, 0, 0.9)"
            
            # Generate cylinder segment
            theta = np.linspace(0, 2*np.pi, 12)
            x_cylinder = pillar_radius * np.cos(theta)
            y_cylinder = pillar_radius * np.sin(theta)
            
            for j in range(len(theta)-1):
                x_quad = [x_cylinder[j], x_cylinder[j+1], x_cylinder[j+1], x_cylinder[j]]
                y_quad = [y_cylinder[j], y_cylinder[j+1], y_cylinder[j+1], y_cylinder[j]]
                z_quad = [z_bottom, z_bottom, z_top, z_top]
                
                fig.add_trace(go.Mesh3d(
                    x=x_quad,
                    y=y_quad,
                    z=z_quad,
                    i=[0, 0],
                    j=[1, 2],
                    k=[2, 3],
                    color=color,
                    opacity=0.95,
                    hoverinfo='text',
                    hovertext=f"<b>Overall Signal Strength</b><br>Score: {overall_score:.1f}<br>Confidence: {confidence*100:.0f}%",
                    showlegend=False,
                    lighting=dict(ambient=0.8, diffuse=0.9, specular=0.5)
                ))
    
    def add_enhanced_annotations(self, fig: go.Figure, overall_score: float, 
                               confidence: float, symbol: str) -> None:
        """Add enhanced annotations and visual indicators."""
        
        # Signal strength indicator
        if overall_score >= 75:
            signal_text = "🟢 STRONG BULLISH"
            signal_color = self.color_scheme['bullish_strong']
        elif overall_score >= 60:
            signal_text = "🟢 MODERATE BULLISH"
            signal_color = self.color_scheme['bullish_moderate']
        elif overall_score <= 25:
            signal_text = "🔴 STRONG BEARISH"
            signal_color = self.color_scheme['bearish_strong']
        elif overall_score <= 40:
            signal_text = "🔴 MODERATE BEARISH"
            signal_color = self.color_scheme['bearish_moderate']
        else:
            signal_text = "🟡 NEUTRAL"
            signal_color = self.color_scheme['neutral_high']
        
        # Confidence indicator
        if confidence >= 0.8:
            conf_text = "🟢 HIGH CONFIDENCE"
        elif confidence >= 0.6:
            conf_text = "🟡 MEDIUM CONFIDENCE"
        else:
            conf_text = "🔴 LOW CONFIDENCE"
        
        # Add floating annotations
        fig.add_trace(go.Scatter3d(
            x=[0],
            y=[0],
            z=[2.8],
            mode='text',
            text=[f"<b>{signal_text}</b><br>{conf_text}"],
            textfont=dict(
                size=18,
                color=signal_color,
                family="Arial Black"
            ),
            hoverinfo='skip',
            showlegend=False,
            name="signal_indicator"
        ))
    
    def create_enhanced_prism_mesh(self, component_scores: Dict[str, float], 
                                 overall_score: float, 
                                 confidence: float = 0.8) -> go.Figure:
        """Create the enhanced 3D prism mesh visualization."""
        
        # Calculate enhanced prism height
        height = self.min_height + (overall_score / 100.0) * (self.max_height - self.min_height)
        
        # Generate enhanced hexagon vertices
        base_vertices = self.generate_enhanced_hexagon_vertices(self.base_radius, 0)
        top_vertices = self.generate_enhanced_hexagon_vertices(self.base_radius, height)
        
        fig = go.Figure()
        
        # Create enhanced faces
        for i in range(6):
            component_key = list(self.components.keys())[i]
            score = component_scores.get(component_key, 50.0)
            weight = self.components[component_key]['weight']
            
            # Get next vertex index
            next_i = (i + 1) % 6
            
            # Define face vertices
            face_vertices = [
                base_vertices[i],
                base_vertices[next_i],
                top_vertices[next_i],
                top_vertices[i]
            ]
            
            # Create enhanced face
            self.create_enhanced_face_with_label(
                fig, face_vertices, component_key, score, confidence, weight
            )
        
        # Add enhanced center pillar
        self.create_enhanced_center_pillar(fig, overall_score, height, confidence)
        
        # Add enhanced annotations
        self.add_enhanced_annotations(fig, overall_score, confidence, "SYMBOL")
        
        return fig
    
    def create_enhanced_interactive_visualization(self, component_scores: Dict[str, float], 
                                                overall_score: float, 
                                                confidence: float = 0.8,
                                                symbol: str = "SYMBOL",
                                                timestamp: Optional[datetime] = None) -> go.Figure:
        """Create the enhanced interactive 3D prism visualization."""
        
        # Create enhanced prism
        fig = self.create_enhanced_prism_mesh(component_scores, overall_score, confidence)
        
        # Enhanced layout configuration
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "Live"
        
        # Determine signal status for title
        if overall_score >= 65:
            status_emoji = "🚀"
            status_text = "BULLISH SIGNAL"
        elif overall_score <= 35:
            status_emoji = "📉"
            status_text = "BEARISH SIGNAL"
        else:
            status_emoji = "⚖️"
            status_text = "NEUTRAL SIGNAL"
        
        fig.update_layout(
            title=dict(
                text=f"<b>{status_emoji} Enhanced Signal Prism - {symbol}</b><br>"
                     f"<span style='font-size:16px; color:#00AAFF'>Overall Score: {overall_score:.1f}/100 | "
                     f"Confidence: {confidence*100:.0f}% | {status_text}</span><br>"
                     f"<span style='font-size:12px; color:#888888'>{timestamp_str}</span>",
                x=0.5,
                xanchor='center',
                font=dict(size=20, color=self.color_scheme['text'])
            ),
            scene=dict(
                bgcolor=self.color_scheme['background'],
                xaxis=dict(
                    showbackground=True,
                    backgroundcolor='rgba(10,10,10,0.8)',
                    gridcolor='rgba(255,255,255,0.1)',
                    showticklabels=False,
                    title="",
                    showgrid=True,
                    zeroline=False
                ),
                yaxis=dict(
                    showbackground=True,
                    backgroundcolor='rgba(10,10,10,0.8)',
                    gridcolor='rgba(255,255,255,0.1)',
                    showticklabels=False,
                    title="",
                    showgrid=True,
                    zeroline=False
                ),
                zaxis=dict(
                    showbackground=True,
                    backgroundcolor='rgba(10,10,10,0.8)',
                    gridcolor='rgba(255,255,255,0.1)',
                    title=dict(text="Signal Strength", font=dict(color=self.color_scheme['text'], size=14)),
                    tickfont=dict(color=self.color_scheme['text'], size=12),
                    showgrid=True,
                    zeroline=False
                ),
                camera=dict(
                    eye=dict(x=2.2, y=2.2, z=1.8),
                    center=dict(x=0, y=0, z=0.8),
                    up=dict(x=0, y=0, z=1)
                ),
                aspectmode='cube',
                # Enhanced lighting
                annotations=[]
            ),
            paper_bgcolor=self.color_scheme['background'],
            plot_bgcolor=self.color_scheme['background'],
            font=dict(color=self.color_scheme['text'], family="Arial"),
            width=1000,
            height=800,
            legend=dict(
                bgcolor='rgba(10,10,10,0.8)',
                bordercolor='rgba(255,255,255,0.3)',
                borderwidth=2,
                font=dict(color=self.color_scheme['text'], size=12),
                x=1.02,
                y=1,
                xanchor='left',
                yanchor='top'
            ),
            # Enhanced interactivity
            hovermode='closest'
        )
        
        return fig
    
    def add_enhanced_animation_controls(self, fig: go.Figure) -> go.Figure:
        """Add enhanced rotation animation controls."""
        
        # Create smoother animation frames
        frames = []
        for angle in range(0, 360, 5):  # Smoother 5-degree increments
            angle_rad = np.radians(angle)
            camera_x = 2.2 * np.cos(angle_rad)
            camera_y = 2.2 * np.sin(angle_rad)
            
            frame = go.Frame(
                layout=dict(
                    scene_camera=dict(
                        eye=dict(x=camera_x, y=camera_y, z=1.8),
                        center=dict(x=0, y=0, z=0.8),
                        up=dict(x=0, y=0, z=1)
                    )
                )
            )
            frames.append(frame)
        
        fig.frames = frames
        
        # Enhanced animation controls
        fig.update_layout(
            updatemenus=[{
                'type': 'buttons',
                'showactive': False,
                'x': 0.02,
                'y': 0.98,
                'xanchor': 'left',
                'yanchor': 'top',
                'bgcolor': 'rgba(0,0,0,0.7)',
                'bordercolor': 'rgba(255,255,255,0.3)',
                'borderwidth': 1,
                'buttons': [
                    {
                        'label': '▶️ Rotate',
                        'method': 'animate',
                        'args': [None, {
                            'frame': {'duration': 80, 'redraw': True},
                            'fromcurrent': True,
                            'transition': {'duration': 40, 'easing': 'cubic-in-out'}
                        }]
                    },
                    {
                        'label': '⏸️ Pause',
                        'method': 'animate',
                        'args': [[None], {
                            'frame': {'duration': 0, 'redraw': False},
                            'mode': 'immediate',
                            'transition': {'duration': 0}
                        }]
                    },
                    {
                        'label': '🔄 Reset View',
                        'method': 'relayout',
                        'args': [{
                            'scene.camera': {
                                'eye': dict(x=2.2, y=2.2, z=1.8),
                                'center': dict(x=0, y=0, z=0.8),
                                'up': dict(x=0, y=0, z=1)
                            }
                        }]
                    }
                ]
            }]
        )
        
        return fig
    
    def save_enhanced_visualization(self, fig: go.Figure, filename: str, 
                                  output_dir: str = "examples/demo/3d_viz_output") -> str:
        """Save the enhanced visualization with optimized settings."""
        import os
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Full file path
        filepath = os.path.join(output_dir, f"enhanced_{filename}.html")
        
        # Save with enhanced configuration
        config = {
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': f'signal_prism_{filename}',
                'height': 800,
                'width': 1000,
                'scale': 2
            }
        }
        
        pyo.plot(fig, filename=filepath, auto_open=False, config=config)
        
        return filepath


def demo_enhanced_prism():
    """Demonstration of the enhanced 3D signal prism."""
    
    print("🚀 Enhanced 3D Signal Prism Demonstration")
    print("=" * 50)
    
    # Your actual data
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
    
    # Create enhanced visualizer
    visualizer = EnhancedSignalPrism3D()
    
    # Create enhanced visualization
    print("Creating enhanced 3D prism...")
    fig = visualizer.create_enhanced_interactive_visualization(
        component_scores, overall_score, confidence, symbol, datetime.now()
    )
    
    # Add enhanced animation controls
    fig = visualizer.add_enhanced_animation_controls(fig)
    
    # Save enhanced visualization
    filepath = visualizer.save_enhanced_visualization(
        fig, f"signal_prism_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    print(f"✅ Enhanced prism saved to: {filepath}")
    
    return fig


if __name__ == "__main__":
    demo_enhanced_prism() 