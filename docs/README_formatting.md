# Enhanced Market Analysis Formatting

This module provides enhanced visual formatting for market analysis results in the terminal.

## Features

- **Structured Dashboard Layout**: Uses Unicode box-drawing characters for clean, organized visual presentation
- **Color-Coded Indicators**: Automatically colors values based on their bullish/bearish implications
- **Visual Gauges**: Provides bar-style gauges to visualize numeric scores
- **Consistent Component Display**: Standardizes the presentation of different analysis components
- **Multi-line Text Handling**: Properly formats longer interpretations and explanations
- **Trend Indicators**: Shows directional arrows (↑, →, ↓) to indicate changes from previous values
- **Detailed Component Breakdowns**: Displays sub-indicators for each major component in tabular format

## Usage

### Basic Usage

```python
from core.formatting import AnalysisFormatter

# Your analysis result dictionary
analysis_result = {
    'score': 65.5,
    'reliability': 0.9,
    'components': {
        'technical': 75.0,
        'volume': 60.0,
        'orderbook': 40.0,
        'orderflow': 55.0,
        'sentiment': 50.0,
        'price_structure': 45.0
    },
    'overall_interpretation': "Market shows bullish technical indicators with neutral sentiment."
}

# Format and display the result
symbol = "BTCUSDT"
formatted_output = AnalysisFormatter.format_analysis_result(analysis_result, symbol)
print(formatted_output)
```

### With Trend Indicators

To show trend indicators comparing against previous values:

```python
# Previous analysis result
previous_result = {...}  # Previous analysis data

# Current analysis result
current_result = {...}   # Current analysis data

# Format with trend indicators
formatted_output = AnalysisFormatter.format_analysis_result(
    current_result, 
    symbol,
    previous_result=previous_result
)
print(formatted_output)
```

### Detailed Component Breakdowns

The formatter automatically extracts and displays detailed component breakdowns if they're available in the `results` field:

```python
analysis_result = {
    'score': 65.5,
    'components': {...},
    'results': {
        'technical': {
            'components': {
                'rsi': 70.5,
                'macd': 65.2,
                'ao': 80.1,
                # etc...
            },
            'score': 75.0
        },
        # Other components...
    }
}

# The formatter will automatically extract and display the detailed components
formatted_output = AnalysisFormatter.format_analysis_result(analysis_result, symbol)
```

### Individual Components

You can also use individual formatting components:

```python
# Just create a gauge for a specific value
gauge = AnalysisFormatter.create_gauge(75.5)
print(f"Technical Score: {gauge}")

# Get color for a value
color = AnalysisFormatter.get_color_for_value(42.0)
print(f"{color}This text is colored based on the value{AnalysisFormatter.RESET}")

# Get trend indicator
trend = AnalysisFormatter.get_trend_indicator(current=65.0, previous=60.0)
print(f"Trend: {trend}")  # Shows: "Trend: ↑"
```

## Installation

The formatting utilities have been integrated into the monitoring system. If you need to reinstall or update:

1. Run the `install_formatter.py` script:
   ```
   python src/install_formatter.py
   ```

2. Test the installation with the demo script:
   ```
   python src/demo_formatting.py
   ```

## Color Coding

The formatter uses the following color scheme:

- **Green** (>= 70): Strong bullish/positive indication
- **Yellow** (45-70): Neutral/moderate indication
- **Red** (< 45): Bearish/negative indication

## Trend Indicators

The trend indicators compare current values with previous values:

- **↑** (Up Arrow): Current value is significantly higher than previous (bullish)
- **→** (Right Arrow): Current value is similar to previous (neutral)
- **↓** (Down Arrow): Current value is significantly lower than previous (bearish)

The default threshold for determining significance is 2.0 points but can be customized.

## Example Output

```
╔══════════════════════════════════════════════════════════════╗
║ BTCUSDT MARKET ANALYSIS - 2025-02-26 19:12:13 ║
╠═════════════════════════╦══════════╦═════════════════════╦════╣
║ COMPONENT               ║ SCORE    ║ GAUGE               ║ TREND ║
╠═════════════════════════╬══════════╬═════════════════════╬════╣
║ OVERALL CONFLUENCE      ║ 56.79    ║ ███████████▒▒▒▒▒▒▒▒▒ ║ →  ║
╠═════════════════════════╬══════════╬═════════════════════╬════╣
║ Technical Analysis      ║ 71.82    ║ ██████████████▒▒▒▒▒▒ ║ ↑  ║
║ Volume Analysis         ║ 72.03    ║ ██████████████▒▒▒▒▒▒ ║ →  ║
║ Order Book              ║ 30.53    ║ ██████▒▒▒▒▒▒▒▒▒▒▒▒▒▒ ║ ↓  ║
║ Order Flow              ║ 50.67    ║ ██████████▒▒▒▒▒▒▒▒▒▒ ║ ↓  ║
║ Market Sentiment        ║ 54.41    ║ ██████████▒▒▒▒▒▒▒▒▒▒ ║ ↑  ║
║ Price Structure         ║ 40.97    ║ ████████▒▒▒▒▒▒▒▒▒▒▒▒ ║ ↓  ║
╠═════════════════════════╩══════════╩═════════════════════╩════╣
║ Reliability: 0.94                                              ║
╠══════════════════════════════════════════════════════════════╣
║ DETAILED COMPONENT BREAKDOWN:                                ║
║ Technical Analysis:                                         ║
║ ┌──────────────────────┬─────────┬──────────────────────┐ ║
║ │ Indicator            │ Score   │ Gauge                │ ║
║ ├──────────────────────┼─────────┼──────────────────────┤ ║
║ │ Rsi                  │ 87.69   │ █████████████▒▒ │ ║
║ │ Cci                  │ 74.66   │ ███████████▒▒▒▒ │ ║
║ │ Williams R           │ 69.37   │ ██████████▒▒▒▒▒ │ ║
║ │ Macd                 │ 67.92   │ ██████████▒▒▒▒▒ │ ║
║ │ Ao                   │ 62.86   │ █████████▒▒▒▒▒▒ │ ║
║ │ Atr                  │ 54.49   │ ████████▒▒▒▒▒▒▒ │ ║
║ └──────────────────────┴─────────┴──────────────────────┘ ║
╠══════════════════════════════════════════════════════════════╣
║ INTERPRETATION:                                                ║
║ Moderate bullish bias with technical indicators showing     ║
║   strength, but orderbook suggesting caution. Recent volume ║
║   patterns indicate growing interest.                       ║
╚══════════════════════════════════════════════════════════════╝
```

## Customization

The `AnalysisFormatter` class provides several class variables that can be customized:

- `GREEN`, `YELLOW`, `RED`: Color codes for different score ranges
- `CYAN`, `BLUE`, `MAGENTA`: Color codes for headers and supplementary information
- `BOLD`, `RESET`: Formatting control codes
- `TREND_UP`, `TREND_NEUTRAL`, `TREND_DOWN`: Trend indicator symbols

You can modify these in your own extensions of the formatter class or directly edit the module. 