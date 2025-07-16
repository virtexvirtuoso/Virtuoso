# Dashboard-Styled 3D Signal Prism Guide

## Overview

The Dashboard-Styled 3D Signal Prism is a specialized visualization that perfectly matches the Virtuoso Terminal dashboard aesthetic. It implements the exact color scheme, typography, and styling from `dashboard_v10.html` to provide a seamless visual experience.

## Key Features

### 🎨 Visual Design
- **Terminal Amber + Navy Blue Theme**: Exact color matching with dashboard_v10.html
- **JetBrains Mono Typography**: Professional monospace font throughout
- **Professional Dark Theme**: Deep navy backgrounds with amber accents
- **Terminal-Style Effects**: Ambient lighting, scan lines, and particle systems
- **Responsive Layout**: Optimized for various screen sizes

### 🎯 Technical Implementation
- **Hexagonal Prism Geometry**: 6-sided signal representation
- **Adaptive Height**: Prism height scales with overall signal score
- **Component Labels**: Direct face labeling with icons and percentages
- **Particle Effects**: Adaptive particle count based on signal strength
- **Animation Controls**: Terminal-style rotation and focus controls

## Color Scheme

### Primary Colors
```css
Background Primary:   #0c1a2b (Deep navy)
Background Secondary: #0f172a (Dark slate)
Background Hero:      #0f172a (Hero sections)
Background Satellite: #0f172a (Panel backgrounds)
Background Header:    #0a1525 (Header sections)
```

### Text Colors
```css
Text Primary:   #ffbf00 (Bright amber)
Text Secondary: #b8860b (Dark amber)
```

### Accent Colors
```css
Accent Primary:   #ff9900 (Orange)
Accent Positive:  #ffc107 (Signal amber)
Accent Negative:  #ff5722 (Red warning)
Accent Warning:   #ff9900 (Orange warning)
```

### Signal Confidence Colors
```css
Signal Strong:   #ffc107 (Bright amber)
Signal Medium:   #ff9900 (Orange)
Signal Weak:     #ff7043 (Light orange)
Signal Neutral:  #607d8b (Blue grey)
Signal Negative: #f44336 (Red)
```

## Component Configuration

### Signal Components (6 Total)
1. **Technical Analysis** (13.6% weight)
   - Icon: 📈
   - Color: #ffc107 (Accent Positive)
   - Description: Technical indicators and trend analysis

2. **Volume Analysis** (9.6% weight)
   - Icon: 📊
   - Color: #ffc107 (Signal Strong)
   - Description: Volume patterns and participation

3. **Order Flow** (20.0% weight)
   - Icon: 🌊
   - Color: #ff9900 (Accent Primary)
   - Description: Institutional order flow pressure

4. **Market Sentiment** (8.0% weight)
   - Icon: 🎭
   - Color: #ff9900 (Signal Medium)
   - Description: Market sentiment and positioning

5. **Order Book** (16.0% weight)
   - Icon: 📋
   - Color: #ffbf00 (Text Primary)
   - Description: Order book depth and liquidity

6. **Price Structure** (12.0% weight)
   - Icon: 🏗️
   - Color: #b8860b (Text Secondary)
   - Description: Support/resistance levels

## Typography Configuration

```python
typography = {
    'font_family': 'JetBrains Mono, Courier New, monospace',
    'title_size': 24,      # Main titles
    'subtitle_size': 16,   # Subtitles and status
    'label_size': 12,      # Component labels
    'small_size': 10       # Small text and details
}
```

## Usage Examples

### Basic Implementation
```python
from scripts.visualization.dashboard_styled_prism_3d import DashboardStyledPrism3D
from datetime import datetime

# Component scores (0-100)
component_scores = {
    'technical': 44.74,
    'volume': 43.15,
    'orderbook': 60.08,
    'orderflow': 73.08,
    'sentiment': 62.10,
    'price_structure': 46.82
}

# Create visualizer
visualizer = DashboardStyledPrism3D()

# Generate visualization
fig = visualizer.create_dashboard_styled_prism(
    component_scores=component_scores,
    overall_score=56.87,
    confidence=0.78,
    symbol="XRPUSDT",
    timestamp=datetime.now()
)

# Save with dashboard styling
filepath = visualizer.save_dashboard_visualization(fig, "my_signal_prism")
```

### Advanced Configuration
```python
# Custom configuration
config = {
    'particle_density': 0.8,
    'animation_speed': 60,
    'lighting_intensity': 0.9
}

visualizer = DashboardStyledPrism3D(config=config)
```

## Signal Interpretation

### Score Ranges
- **70-100**: 🚀 STRONG BULLISH (Green amber glow)
- **50-69**: 📈 BULLISH BIAS (Orange amber glow)
- **30-49**: ⚖️ NEUTRAL (Weak amber glow)
- **0-29**: 📉 BEARISH (Red warning glow)

### Confidence Levels
- **80-100%**: High confidence (Strong opacity)
- **60-79%**: Medium confidence (Medium opacity)
- **40-59%**: Low confidence (Reduced opacity)
- **0-39%**: Very low confidence (Minimal opacity)

## Terminal-Style Features

### HTML Template Enhancements
- **Terminal Header**: Fixed header with amber title and status indicator
- **Ambient Lighting**: Radial gradient overlays for depth
- **Scan Line Effect**: Animated bottom scan line
- **Status Indicator**: Live status with pulsing amber light
- **Responsive Design**: Mobile-optimized layout

### Animation Controls
- **▶️ TERMINAL ROTATE**: Smooth 360° rotation
- **⏸️ PAUSE**: Stop animation
- **🎯 FOCUS**: Close-up view
- **🌐 OVERVIEW**: Wide-angle view

## File Structure

```
scripts/visualization/
├── dashboard_styled_prism_3d.py     # Main implementation
examples/demo/
├── dashboard_prism_demo.py          # Demonstration script
examples/demo/3d_viz_output/
├── dashboard_*.html                 # Generated visualizations
docs/guides/
├── dashboard_styled_3d_prism_guide.md  # This guide
```

## Generated Files

### Main Visualization
- `dashboard_signal_prism_XRPUSDT_[timestamp].html`
- Complete dashboard-styled 3D prism with terminal effects

### Scenario Demonstrations
- `dashboard_strong_bullish_BTCUSDT_[timestamp].html`
- `dashboard_neutral_mixed_ETHUSDT_[timestamp].html`
- `dashboard_weak_bearish_ADAUSDT_[timestamp].html`

## Performance Optimizations

### WebGL Rendering
- Hardware-accelerated 3D graphics
- Smooth 60fps animations
- Efficient particle systems

### Mobile Optimization
- Touch-friendly controls
- Responsive scaling
- Reduced particle count on mobile

### Loading Performance
- Optimized mesh generation
- Compressed assets
- Progressive loading

## Integration with Dashboard

### Seamless Styling
The dashboard-styled prism uses identical CSS variables and styling patterns as `dashboard_v10.html`:

```css
/* Matching dashboard variables */
--bg-primary: #0c1a2b;
--text-primary: #ffbf00;
--accent-positive: #ffc107;
--font-family: 'JetBrains Mono', monospace;
```

### Consistent Typography
All text elements use JetBrains Mono with matching font sizes and weights from the main dashboard.

### Color Harmony
The prism colors are derived from the dashboard's signal confidence color system, ensuring visual consistency.

## Best Practices

### Signal Data Quality
- Ensure component scores are in 0-100 range
- Provide meaningful confidence values (0.0-1.0)
- Use descriptive symbol names

### Performance Considerations
- Limit particle count for mobile devices
- Use appropriate confidence levels for opacity
- Consider file size for web deployment

### Visual Clarity
- Maintain consistent color coding
- Use appropriate score thresholds
- Provide clear component labeling

## Troubleshooting

### Common Issues
1. **Missing Dependencies**: Ensure plotly and numpy are installed
2. **Font Loading**: JetBrains Mono requires internet connection
3. **File Size**: Large HTML files may load slowly

### Performance Tips
- Reduce particle count for better performance
- Use lower confidence values for transparency
- Optimize for target device capabilities

## Future Enhancements

### Planned Features
- Real-time data integration
- Interactive component drilling
- Export to various formats
- Custom color themes
- Advanced animation patterns

### API Integration
- Direct dashboard data connection
- WebSocket real-time updates
- RESTful API endpoints
- Database persistence

## Conclusion

The Dashboard-Styled 3D Signal Prism provides a professional, visually consistent way to display signal confluence data that perfectly matches the Virtuoso Terminal aesthetic. Its terminal amber + navy blue theme, JetBrains Mono typography, and advanced 3D effects create an immersive trading analysis experience.

The visualization successfully bridges the gap between complex quantitative analysis and intuitive visual representation, making it an essential tool for professional trading environments. 