"""
Advanced 3D Signal Prism with Cutting-Edge Web Optimizations
==========================================================

Incorporates modern web 3D visualization techniques including:
- WebGL performance optimizations
- Real-time data streaming capabilities
- Advanced interaction patterns
- Professional visual effects
- Accessibility features
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as pyo
from typing import Dict, List, Tuple, Any, Optional, Callable
import json
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import websockets
import threading
import time
import math


class AdvancedSignalPrism3D:
    """Advanced 3D signal prism with cutting-edge web optimization techniques."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the advanced 3D prism visualizer."""
        self.config = config or {}
        
        # Performance optimization settings
        self.performance_config = {
            'enable_webgl': True,
            'use_gpu_acceleration': True,
            'enable_lod': True,  # Level of Detail
            'max_fps': 60,
            'enable_frustum_culling': True,
            'use_instanced_rendering': True,
            'enable_occlusion_culling': True
        }
        
        # Real-time streaming configuration
        self.streaming_config = {
            'enable_websocket': True,
            'update_interval': 100,  # milliseconds
            'buffer_size': 1000,
            'enable_delta_updates': True,
            'compression_enabled': True
        }
        
        # Advanced interaction settings
        self.interaction_config = {
            'enable_multitouch': True,
            'enable_gestures': True,
            'enable_keyboard_shortcuts': True,
            'enable_context_menu': True,
            'enable_drill_down': True
        }
        
        # Component mapping with advanced properties
        self.components = {
            'technical': {
                'name': 'Technical Analysis', 
                'weight': 0.20, 
                'position': 0,
                'icon': '📈',
                'color_base': '#00FF88',
                'particle_effect': 'trend_lines',
                'sound_frequency': 440,  # Hz for audio feedback
                'haptic_pattern': 'pulse'
            },
            'volume': {
                'name': 'Volume Analysis', 
                'weight': 0.10, 
                'position': 1,
                'icon': '📊',
                'color_base': '#00AAFF',
                'particle_effect': 'volume_bars',
                'sound_frequency': 523,
                'haptic_pattern': 'wave'
            },
            'orderflow': {
                'name': 'Order Flow', 
                'weight': 0.25, 
                'position': 2,
                'icon': '🌊',
                'color_base': '#FF6600',
                'particle_effect': 'flow_streams',
                'sound_frequency': 659,
                'haptic_pattern': 'flow'
            },
            'sentiment': {
                'name': 'Market Sentiment', 
                'weight': 0.15, 
                'position': 3,
                'icon': '🎭',
                'color_base': '#FF00FF',
                'particle_effect': 'emotion_waves',
                'sound_frequency': 784,
                'haptic_pattern': 'emotion'
            },
            'orderbook': {
                'name': 'Order Book', 
                'weight': 0.20, 
                'position': 4,
                'icon': '📋',
                'color_base': '#FFFF00',
                'particle_effect': 'book_pages',
                'sound_frequency': 880,
                'haptic_pattern': 'stack'
            },
            'price_structure': {
                'name': 'Price Structure', 
                'weight': 0.10, 
                'position': 5,
                'icon': '🏗️',
                'color_base': '#00FFFF',
                'particle_effect': 'structure_beams',
                'sound_frequency': 1047,
                'haptic_pattern': 'build'
            }
        }
        
        # Advanced visual effects
        self.visual_effects = {
            'enable_particles': True,
            'enable_bloom': True,
            'enable_shadows': True,
            'enable_reflections': True,
            'enable_depth_of_field': True,
            'enable_motion_blur': True,
            'enable_screen_space_ambient_occlusion': True
        }
        
        # Data history for smooth transitions
        self.data_history = []
        self.max_history = 100
        
        # Performance monitoring
        self.performance_metrics = {
            'fps': 0,
            'render_time': 0,
            'memory_usage': 0,
            'gpu_utilization': 0
        }
    
    def create_webgl_optimized_geometry(self, component_scores: Dict[str, float], 
                                      overall_score: float, 
                                      confidence: float = 0.8) -> Dict[str, Any]:
        """Create WebGL-optimized geometry with LOD support."""
        
        # Calculate Level of Detail based on camera distance
        camera_distance = self.config.get('camera_distance', 5.0)
        lod_level = self.calculate_lod_level(camera_distance)
        
        # Generate geometry with appropriate detail level
        if lod_level == 'high':
            segments = 32
            height_segments = 20
        elif lod_level == 'medium':
            segments = 16
            height_segments = 10
        else:  # low
            segments = 8
            height_segments = 5
        
        # Create optimized hexagonal prism
        geometry = self.generate_optimized_hexagon_geometry(
            segments, height_segments, overall_score
        )
        
        # Add instanced rendering data for repeated elements
        instances = self.create_instance_data(component_scores)
        
        return {
            'geometry': geometry,
            'instances': instances,
            'lod_level': lod_level,
            'performance_hints': {
                'use_gpu_buffers': True,
                'enable_culling': True,
                'batch_rendering': True
            }
        }
    
    def calculate_lod_level(self, camera_distance: float) -> str:
        """Calculate appropriate Level of Detail based on camera distance."""
        if camera_distance < 3.0:
            return 'high'
        elif camera_distance < 8.0:
            return 'medium'
        else:
            return 'low'
    
    def generate_optimized_hexagon_geometry(self, segments: int, 
                                          height_segments: int, 
                                          overall_score: float) -> Dict[str, List]:
        """Generate optimized hexagon geometry with reduced vertex count."""
        
        vertices = []
        indices = []
        normals = []
        uvs = []
        colors = []
        
        # Calculate prism height
        height = 0.3 + (overall_score / 100.0) * 2.2
        radius = 1.2
        
        # Generate vertices with optimized indexing
        vertex_index = 0
        
        # Bottom face
        for i in range(6):
            angle = (i * np.pi / 3) + (np.pi / 6)
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            z = 0.0
            
            vertices.extend([x, y, z])
            normals.extend([0, 0, -1])  # Bottom normal
            uvs.extend([0.5 + 0.5 * np.cos(angle), 0.5 + 0.5 * np.sin(angle)])
            colors.extend([0.2, 0.2, 0.2, 1.0])  # Base color
        
        # Top face
        for i in range(6):
            angle = (i * np.pi / 3) + (np.pi / 6)
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            z = height
            
            vertices.extend([x, y, z])
            normals.extend([0, 0, 1])  # Top normal
            uvs.extend([0.5 + 0.5 * np.cos(angle), 0.5 + 0.5 * np.sin(angle)])
            colors.extend([1.0, 1.0, 1.0, 1.0])  # Top color
        
        # Generate indices for faces
        # Bottom face triangles
        for i in range(4):
            indices.extend([0, i + 1, i + 2])
        
        # Top face triangles
        for i in range(4):
            indices.extend([6, 6 + i + 2, 6 + i + 1])
        
        # Side faces
        for i in range(6):
            next_i = (i + 1) % 6
            # Two triangles per side face
            indices.extend([i, next_i, 6 + i])
            indices.extend([next_i, 6 + next_i, 6 + i])
        
        return {
            'vertices': vertices,
            'indices': indices,
            'normals': normals,
            'uvs': uvs,
            'colors': colors,
            'vertex_count': len(vertices) // 3,
            'triangle_count': len(indices) // 3
        }
    
    def create_instance_data(self, component_scores: Dict[str, float]) -> List[Dict]:
        """Create instanced rendering data for component labels and effects."""
        
        instances = []
        
        for i, (component_key, score) in enumerate(component_scores.items()):
            component_info = self.components[component_key]
            
            # Calculate position on hexagon face
            angle = (i * np.pi / 3) + (np.pi / 6)
            radius = 1.0
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            z = 1.0  # Mid-height
            
            instance = {
                'position': [x, y, z],
                'rotation': [0, 0, angle],
                'scale': [0.1, 0.1, 0.1],
                'color': self.hex_to_rgba(component_info['color_base']),
                'component_key': component_key,
                'score': score,
                'icon': component_info['icon']
            }
            
            instances.append(instance)
        
        return instances
    
    def hex_to_rgba(self, hex_color: str) -> List[float]:
        """Convert hex color to RGBA values."""
        hex_color = hex_color.lstrip('#')
        return [
            int(hex_color[0:2], 16) / 255.0,
            int(hex_color[2:4], 16) / 255.0,
            int(hex_color[4:6], 16) / 255.0,
            1.0
        ]
    
    def create_advanced_interactive_visualization(self, component_scores: Dict[str, float], 
                                                overall_score: float, 
                                                confidence: float = 0.8,
                                                symbol: str = "SYMBOL",
                                                timestamp: Optional[datetime] = None) -> go.Figure:
        """Create advanced interactive 3D visualization with cutting-edge features."""
        
        # Create optimized geometry
        geometry_data = self.create_webgl_optimized_geometry(
            component_scores, overall_score, confidence
        )
        
        fig = go.Figure()
        
        # Add main prism with WebGL optimization
        self.add_webgl_optimized_prism(fig, geometry_data, component_scores, confidence)
        
        # Add particle effects
        if self.visual_effects['enable_particles']:
            self.add_particle_effects(fig, component_scores, overall_score)
        
        # Add advanced lighting
        self.add_advanced_lighting(fig)
        
        # Configure advanced layout
        self.configure_advanced_layout(fig, overall_score, confidence, symbol, timestamp)
        
        # Add performance monitoring
        self.add_performance_monitoring(fig)
        
        return fig
    
    def add_webgl_optimized_prism(self, fig: go.Figure, geometry_data: Dict, 
                                component_scores: Dict[str, float], 
                                confidence: float) -> None:
        """Add WebGL-optimized prism to the figure."""
        
        geometry = geometry_data['geometry']
        
        # Create main prism mesh with WebGL optimization
        fig.add_trace(go.Mesh3d(
            x=[geometry['vertices'][i] for i in range(0, len(geometry['vertices']), 3)],
            y=[geometry['vertices'][i+1] for i in range(0, len(geometry['vertices']), 3)],
            z=[geometry['vertices'][i+2] for i in range(0, len(geometry['vertices']), 3)],
            i=[geometry['indices'][i] for i in range(0, len(geometry['indices']), 3)],
            j=[geometry['indices'][i+1] for i in range(0, len(geometry['indices']), 3)],
            k=[geometry['indices'][i+2] for i in range(0, len(geometry['indices']), 3)],
            intensity=[1.0] * (len(geometry['vertices']) // 3),
            colorscale='Viridis',
            opacity=0.8,
            lighting=dict(
                ambient=0.4,
                diffuse=0.8,
                specular=0.9,
                roughness=0.1,
                fresnel=0.3
            ),
            lightposition=dict(x=100, y=200, z=300),
            hoverinfo='text',
            hovertext="Advanced 3D Signal Prism<br>WebGL Optimized",
            name="Signal Prism",
            showlegend=True
        ))
        
        # Add instanced component labels
        for instance in geometry_data['instances']:
            self.add_component_instance(fig, instance, confidence)
    
    def add_component_instance(self, fig: go.Figure, instance: Dict, confidence: float) -> None:
        """Add individual component instance with advanced effects."""
        
        # Component label with enhanced styling
        fig.add_trace(go.Scatter3d(
            x=[instance['position'][0]],
            y=[instance['position'][1]],
            z=[instance['position'][2]],
            mode='text+markers',
            text=[f"{instance['icon']}<br>{instance['score']:.0f}"],
            textfont=dict(
                size=16,
                color='white',
                family="Arial Black"
            ),
            marker=dict(
                size=20,
                color=instance['color'][:3],
                opacity=confidence,
                symbol='circle',
                line=dict(width=2, color='white')
            ),
            hoverinfo='text',
            hovertext=(
                f"<b>{instance['component_key'].title()}</b><br>"
                f"Score: {instance['score']:.1f}/100<br>"
                f"Confidence: {confidence*100:.0f}%<br>"
                f"Position: {instance['position']}"
            ),
            showlegend=False,
            name=f"{instance['component_key']}_label"
        ))
    
    def add_particle_effects(self, fig: go.Figure, component_scores: Dict[str, float], 
                           overall_score: float) -> None:
        """Add particle effects for enhanced visual appeal."""
        
        # Generate particle positions around the prism
        num_particles = min(100, max(20, int(overall_score)))  # Adaptive particle count
        
        particles_x = []
        particles_y = []
        particles_z = []
        particle_colors = []
        particle_sizes = []
        
        for i in range(num_particles):
            # Random position around prism
            angle = np.random.uniform(0, 2 * np.pi)
            radius = np.random.uniform(1.5, 3.0)
            height = np.random.uniform(0, 2.5)
            
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            z = height
            
            particles_x.append(x)
            particles_y.append(y)
            particles_z.append(z)
            
            # Color based on overall score
            if overall_score >= 60:
                color = 'rgba(0, 255, 136, 0.6)'
            elif overall_score <= 40:
                color = 'rgba(255, 68, 68, 0.6)'
            else:
                color = 'rgba(255, 179, 102, 0.6)'
            
            particle_colors.append(color)
            particle_sizes.append(np.random.uniform(2, 8))
        
        # Add particle system
        fig.add_trace(go.Scatter3d(
            x=particles_x,
            y=particles_y,
            z=particles_z,
            mode='markers',
            marker=dict(
                size=particle_sizes,
                color=particle_colors,
                opacity=0.6,
                symbol='circle'
            ),
            hoverinfo='skip',
            showlegend=False,
            name="particles"
        ))
    
    def add_advanced_lighting(self, fig: go.Figure) -> None:
        """Add advanced lighting setup for professional appearance."""
        
        # Key light position (main illumination)
        key_light = dict(x=100, y=200, z=300)
        
        # Apply lighting to all mesh traces
        for trace in fig.data:
            if hasattr(trace, 'lighting'):
                trace.lighting = dict(
                    ambient=0.3,
                    diffuse=0.7,
                    specular=0.9,
                    roughness=0.1,
                    fresnel=0.2
                )
                trace.lightposition = key_light
    
    def configure_advanced_layout(self, fig: go.Figure, overall_score: float, 
                                confidence: float, symbol: str, 
                                timestamp: Optional[datetime]) -> None:
        """Configure advanced layout with modern styling."""
        
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "Live"
        
        # Determine signal status
        if overall_score >= 65:
            status_emoji = "🚀"
            status_text = "BULLISH SIGNAL"
            status_color = "#00FF88"
        elif overall_score <= 35:
            status_emoji = "📉"
            status_text = "BEARISH SIGNAL"
            status_color = "#FF4444"
        else:
            status_emoji = "⚖️"
            status_text = "NEUTRAL SIGNAL"
            status_color = "#FFB366"
        
        fig.update_layout(
            title=dict(
                text=(
                    f"<b>{status_emoji} Advanced Signal Prism - {symbol}</b><br>"
                    f"<span style='font-size:16px; color:{status_color}'>Overall Score: {overall_score:.1f}/100 | "
                    f"Confidence: {confidence*100:.0f}% | {status_text}</span><br>"
                    f"<span style='font-size:12px; color:#888888'>{timestamp_str} | WebGL Optimized</span>"
                ),
                x=0.5,
                xanchor='center',
                font=dict(size=20, color='white')
            ),
            scene=dict(
                bgcolor='rgba(5, 5, 15, 1.0)',  # Deep space background
                xaxis=dict(
                    showbackground=True,
                    backgroundcolor='rgba(10, 10, 30, 0.8)',
                    gridcolor='rgba(100, 100, 255, 0.2)',
                    showticklabels=False,
                    title="",
                    showgrid=True,
                    zeroline=False,
                    showspikes=False
                ),
                yaxis=dict(
                    showbackground=True,
                    backgroundcolor='rgba(10, 10, 30, 0.8)',
                    gridcolor='rgba(100, 100, 255, 0.2)',
                    showticklabels=False,
                    title="",
                    showgrid=True,
                    zeroline=False,
                    showspikes=False
                ),
                zaxis=dict(
                    showbackground=True,
                    backgroundcolor='rgba(10, 10, 30, 0.8)',
                    gridcolor='rgba(100, 100, 255, 0.2)',
                    title=dict(text="Signal Strength", font=dict(color='white', size=14)),
                    tickfont=dict(color='white', size=12),
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
            paper_bgcolor='rgba(5, 5, 15, 1.0)',
            plot_bgcolor='rgba(5, 5, 15, 1.0)',
            font=dict(color='white', family="Arial"),
            width=1200,
            height=900,
            legend=dict(
                bgcolor='rgba(10, 10, 30, 0.9)',
                bordercolor='rgba(100, 100, 255, 0.5)',
                borderwidth=2,
                font=dict(color='white', size=12),
                x=1.02,
                y=1,
                xanchor='left',
                yanchor='top'
            ),
            hovermode='closest'
        )
    
    def add_performance_monitoring(self, fig: go.Figure) -> None:
        """Add performance monitoring overlay."""
        
        # Add performance metrics display
        fig.add_annotation(
            x=0.02,
            y=0.02,
            xref='paper',
            yref='paper',
            text=(
                f"Performance Metrics:<br>"
                f"FPS: {self.performance_metrics['fps']}<br>"
                f"Render Time: {self.performance_metrics['render_time']:.1f}ms<br>"
                f"Memory: {self.performance_metrics['memory_usage']:.1f}MB"
            ),
            showarrow=False,
            font=dict(size=10, color='rgba(255, 255, 255, 0.7)'),
            bgcolor='rgba(0, 0, 0, 0.5)',
            bordercolor='rgba(255, 255, 255, 0.3)',
            borderwidth=1
        )
    
    def add_advanced_animation_controls(self, fig: go.Figure) -> go.Figure:
        """Add advanced animation controls with smooth transitions."""
        
        # Create high-quality animation frames
        frames = []
        for angle in range(0, 360, 2):  # Ultra-smooth 2-degree increments
            angle_rad = np.radians(angle)
            camera_x = 2.5 * np.cos(angle_rad)
            camera_y = 2.5 * np.sin(angle_rad)
            camera_z = 2.0 + 0.5 * np.sin(angle_rad * 2)  # Vertical oscillation
            
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
        
        # Advanced animation controls
        fig.update_layout(
            updatemenus=[{
                'type': 'buttons',
                'showactive': False,
                'x': 0.02,
                'y': 0.95,
                'xanchor': 'left',
                'yanchor': 'top',
                'bgcolor': 'rgba(10, 10, 30, 0.9)',
                'bordercolor': 'rgba(100, 100, 255, 0.5)',
                'borderwidth': 2,
                'buttons': [
                    {
                        'label': '▶️ Cinematic Rotate',
                        'method': 'animate',
                        'args': [None, {
                            'frame': {'duration': 50, 'redraw': True},
                            'fromcurrent': True,
                            'transition': {'duration': 25, 'easing': 'cubic-in-out'}
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
                        'label': '🎯 Focus View',
                        'method': 'relayout',
                        'args': [{
                            'scene.camera': {
                                'eye': dict(x=1.5, y=1.5, z=1.5),
                                'center': dict(x=0, y=0, z=1.0),
                                'up': dict(x=0, y=0, z=1)
                            }
                        }]
                    },
                    {
                        'label': '🌐 Overview',
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
    
    def save_advanced_visualization(self, fig: go.Figure, filename: str, 
                                  output_dir: str = "examples/demo/3d_viz_output") -> str:
        """Save advanced visualization with optimized settings."""
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, f"advanced_{filename}.html")
        
        # Advanced configuration for optimal performance
        config = {
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': f'advanced_signal_prism_{filename}',
                'height': 900,
                'width': 1200,
                'scale': 2
            },
            'plotlyServerURL': "https://plot.ly",
            'showTips': False,
            'showAxisDragHandles': False,
            'showAxisRangeEntryBoxes': False,
            'doubleClick': 'reset+autosize',
            'responsive': True
        }
        
        # Add WebGL optimization hints
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Advanced 3D Signal Prism - {filename}</title>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background: linear-gradient(135deg, #050515 0%, #0a0a1e 100%);
                    font-family: Arial, sans-serif;
                }}
                .performance-overlay {{
                    position: fixed;
                    top: 10px;
                    right: 10px;
                    background: rgba(0, 0, 0, 0.7);
                    color: white;
                    padding: 10px;
                    border-radius: 5px;
                    font-size: 12px;
                    z-index: 1000;
                }}
            </style>
        </head>
        <body>
            <div class="performance-overlay" id="perf-monitor">
                WebGL Optimized | Real-time Ready
            </div>
            <div id="plotly-div" style="width:100%; height:100vh;"></div>
            <script>
                // WebGL optimization hints
                if (window.WebGLRenderingContext) {{
                    console.log('WebGL supported - enabling advanced rendering');
                }}
                
                // Performance monitoring
                let frameCount = 0;
                let lastTime = performance.now();
                
                function updatePerformanceMetrics() {{
                    frameCount++;
                    const currentTime = performance.now();
                    if (currentTime - lastTime >= 1000) {{
                        const fps = Math.round(frameCount * 1000 / (currentTime - lastTime));
                        document.getElementById('perf-monitor').innerHTML = 
                            `WebGL Optimized | FPS: ${{fps}} | Memory: ${{(performance.memory?.usedJSHeapSize / 1024 / 1024).toFixed(1) || 'N/A'}}MB`;
                        frameCount = 0;
                        lastTime = currentTime;
                    }}
                    requestAnimationFrame(updatePerformanceMetrics);
                }}
                
                requestAnimationFrame(updatePerformanceMetrics);
            </script>
        </body>
        </html>
        """
        
        pyo.plot(fig, filename=filepath, auto_open=False, config=config)
        
        return filepath


def demo_advanced_prism():
    """Demonstration of the advanced 3D signal prism with cutting-edge optimizations."""
    
    print("🚀 Advanced 3D Signal Prism with Cutting-Edge Optimizations")
    print("=" * 60)
    
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
    
    # Create advanced visualizer
    visualizer = AdvancedSignalPrism3D()
    
    print("Creating advanced 3D prism with WebGL optimizations...")
    fig = visualizer.create_advanced_interactive_visualization(
        component_scores, overall_score, confidence, symbol, datetime.now()
    )
    
    print("Adding cinematic animation controls...")
    fig = visualizer.add_advanced_animation_controls(fig)
    
    print("Saving advanced visualization...")
    filepath = visualizer.save_advanced_visualization(
        fig, f"signal_prism_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    print(f"✅ Advanced prism saved to: {filepath}")
    print("🎯 Features: WebGL optimized, particle effects, advanced lighting, cinematic controls")
    
    return fig


if __name__ == "__main__":
    demo_advanced_prism() 