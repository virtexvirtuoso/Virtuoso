# 3D Signal Prism Visualization Guide

## Overview

The 3D Signal Prism visualization transforms your confluence analysis data into an intuitive, interactive 3D representation that gives traders a "physical" understanding of market signals. Each prism face represents a different signal component, with colors indicating strength and height showing overall confidence.

## Key Features

### 🎯 **Hexagonal Prism Design**
- **6 Faces**: Each represents a signal component (Technical, Volume, Orderflow, Sentiment, Orderbook, Price Structure)
- **Height**: Overall confluence score (taller = stronger signal)
- **Colors**: 
  - 🟢 **Green**: Bullish signals (60-100)
  - 🔴 **Red**: Bearish signals (0-40)
  - 🟡 **Orange**: Neutral signals (40-60)
- **Transparency**: Confidence level (more opaque = higher confidence)

### 🎮 **Interactive Controls**
- **Rotation**: Click and drag to examine from all angles
- **Animation**: Auto-rotation with play/pause controls
- **Hover**: Detailed component information on mouse-over
- **Zoom**: Mouse wheel to zoom in/out

## Quick Start

### Basic Usage

```python
from scripts.visualization.signal_prism_3d import SignalPrism3D

# Your confluence analysis scores
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

# Create visualizer
visualizer = SignalPrism3D()

# Generate interactive 3D prism
fig = visualizer.create_interactive_visualization(
    component_scores=component_scores,
    overall_score=overall_score,
    confidence=confidence,
    symbol="XRPUSDT",
    timestamp=datetime.now()
)

# Add rotation animation
fig = visualizer.add_animation_controls(fig)

# Save to HTML file
filepath = visualizer.save_visualization(fig, "my_signal_prism")
```

### Integration with Confluence Analyzer

```python
from scripts.visualization.confluence_prism_integration import ConfluencePrismIntegration

# Initialize with your config
integration = ConfluencePrismIntegration({
    'auto_save': True,
    'auto_rotate': True,
    'output_dir': 'my_output_directory'
})

# Analyze market data and create visualization
result = await integration.analyze_and_visualize(market_data, "BTCUSDT")

if result['success']:
    print(f"Signal: {result['trading_recommendation']['primary_signal']}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Files saved: {result['saved_files']}")
```

## Understanding the Visualization

### Signal Interpretation

| Overall Score | Interpretation | Action |
|---------------|----------------|---------|
| 75-100 | 🟢 **Strong Bullish** | Consider LONG positions |
| 60-74 | 🟢 **Moderate Bullish** | Look for pullback entries |
| 40-59 | 🟡 **Neutral** | Wait for clearer signals |
| 26-39 | 🔴 **Moderate Bearish** | Look for bounce entries |
| 0-25 | 🔴 **Strong Bearish** | Consider SHORT positions |

### Component Analysis

Each face of the prism shows:
- **Component Name**: Technical, Volume, etc.
- **Score**: 0-100 scale
- **Weight**: Importance in overall calculation
- **Impact**: Contribution to final score

### Confidence Levels

| Confidence | Interpretation | Risk Level |
|------------|----------------|------------|
| 80-100% | 🟢 **High** | Low Risk |
| 60-79% | 🟡 **Medium** | Medium Risk |
| 0-59% | 🔴 **Low** | High Risk |

## Advanced Features

### Dashboard View

Create multi-angle dashboard with different perspectives:

```python
dashboard_fig = visualizer.create_dashboard_view(
    component_scores, overall_score, confidence, symbol
)
```

### Live Updates

For real-time trading signals:

```python
async for result in integration.create_live_dashboard(market_data_stream, "BTCUSDT"):
    print(f"Live update: {result['overall_score']:.1f}")
    # Process real-time signal updates
```

### Custom Scenarios

Test different market conditions:

```python
scenarios = {
    'strong_bullish': {
        'scores': {'technical': 85, 'volume': 80, 'orderbook': 75, 
                  'orderflow': 90, 'sentiment': 85, 'price_structure': 80},
        'overall': 82.5,
        'confidence': 0.9
    }
}
```

## File Structure

```
examples/demo/3d_viz_output/
├── signal_prism_SYMBOL_TIMESTAMP.html      # Main interactive prism
├── signal_dashboard_SYMBOL_TIMESTAMP.html  # Multi-view dashboard
└── analysis_data_SYMBOL_TIMESTAMP.json     # Raw analysis data
```

## Trading Workflow Integration

### 1. **Signal Generation**
```python
# Run your confluence analysis
analysis_result = await confluence_analyzer.analyze(market_data)

# Extract scores for visualization
component_scores = extract_component_scores(analysis_result)
```

### 2. **Visualization Creation**
```python
# Create 3D prism
prism_fig = visualizer.create_interactive_visualization(
    component_scores, overall_score, confidence, symbol
)
```

### 3. **Decision Making**
- **Green Prism (High)**: Strong signal, consider entry
- **Red Prism (Low)**: Strong counter-signal, consider opposite entry
- **Orange Prism (Medium)**: Wait for confirmation
- **Transparent Prism**: Low confidence, avoid trading

### 4. **Risk Assessment**
```python
recommendation = result['trading_recommendation']
if recommendation['confidence_level'] == 'HIGH' and recommendation['risk_level'] == 'LOW':
    # Proceed with trade
    execute_trade(recommendation['primary_signal'])
else:
    # Wait for better setup
    monitor_signals()
```

## Best Practices

### 🎯 **Signal Validation**
- Always check multiple timeframes
- Confirm with price action
- Consider market context
- Validate with volume

### 📊 **Visualization Tips**
- Use rotation to examine all components
- Focus on face colors for quick assessment
- Check transparency for confidence
- Compare height across different symbols

### ⚠️ **Risk Management**
- Never trade on visualization alone
- Always use stop losses
- Consider position sizing based on confidence
- Monitor for signal changes

## Troubleshooting

### Common Issues

**Q: Prism appears flat or distorted**
A: Check that all component scores are valid numbers (0-100)

**Q: Colors don't match expected signals**
A: Verify score ranges and confidence levels

**Q: Animation not working**
A: Ensure browser supports WebGL and JavaScript is enabled

**Q: Files not saving**
A: Check output directory permissions and disk space

### Performance Tips

- Use smaller datasets for faster rendering
- Limit animation frames for better performance
- Close unused browser tabs when viewing multiple prisms
- Use dashboard view for comparing multiple signals

## Examples

Check the `examples/demo/3d_viz_output/` directory for:
- **Strong Bullish Signal**: High green prism
- **Strong Bearish Signal**: Low red prism  
- **Mixed Signals**: Multi-colored faces
- **Low Confidence**: Transparent prism

## Integration with Existing Systems

### Dashboard Integration
```python
# Add to your existing dashboard
prism_html = visualizer.save_visualization(fig, "dashboard_prism")
# Embed in your web interface
```

### Alert Systems
```python
if overall_score > 75 and confidence > 0.8:
    send_alert(f"Strong bullish signal detected: {symbol}")
    create_prism_visualization(component_scores)
```

### Backtesting
```python
# Generate historical prisms for analysis
for historical_data in backtest_data:
    prism = create_historical_prism(historical_data)
    analyze_signal_accuracy(prism, actual_results)
```

## Next Steps

1. **Customize Colors**: Modify the color scheme to match your preferences
2. **Add Indicators**: Extend with additional technical indicators
3. **Real-time Streaming**: Connect to live market data feeds
4. **Mobile Optimization**: Adapt for mobile trading apps
5. **VR/AR Integration**: Explore immersive trading experiences

---

*The 3D Signal Prism transforms complex quantitative analysis into intuitive visual signals, giving traders the confidence to make better decisions faster.* 