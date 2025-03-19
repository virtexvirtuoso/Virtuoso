# Analysis Results Formatting

This module provides enhanced formatting utilities for displaying analysis results in a more structured and visually appealing way.

## Features

### Component Breakdown

The component breakdown feature provides a clean, structured view of analysis components with visual indicators:

```
┌────────────────────────────────────────────────┐
│              COMPONENT BREAKDOWN               │
├────────────────────────┬───────────────────────┤
│       COMPONENT        │         SCORE         │
├────────────────────────┼───────────────────────┤
│ Orderbook              │ 74.60 [███████████    ] ↑ │
│ Orderflow              │ 71.32 [██████████     ] ↑ │
│ Volume                 │ 62.68 [▓▓▓▓▓▓▓▓▓      ] → │
│ Price Structure        │ 52.52 [▓▓▓▓▓▓▓        ] → │
│ Sentiment              │ 51.32 [▓▓▓▓▓▓▓        ] → │
│ Technical              │ 31.61 [░░░░           ] ↓ │
└────────────────────────┴───────────────────────┘
```

### Analysis Dashboard

The full analysis dashboard provides a comprehensive view of all analysis components:

```
╔══════════════════════════════════════════════════════════════╗
║ BTCUSDT MARKET ANALYSIS - 2025-02-26 19:34:04 ║
╠═════════════════════════╦══════════╦═════════════════════╦════╣
║ COMPONENT               ║ SCORE    ║ GAUGE               ║ TREND ║
╠═════════════════════════╬══════════╬═════════════════════╬════╣
║ OVERALL CONFLUENCE      ║ 52.63    ║ ██████████▒▒▒▒▒▒▒▒▒▒ ║ →  ║
╠═════════════════════════╬══════════╬═════════════════════╬════╣
║ Orderbook                 ║ 74.60    ║ ██████████████▒▒▒▒▒▒ ║ ↑  ║
║ Orderflow                 ║ 71.32    ║ ██████████████▒▒▒▒▒▒ ║ ↑  ║
║ Volume                    ║ 62.68    ║ ████████████▒▒▒▒▒▒▒▒ ║ →  ║
║ Price Structure           ║ 52.52    ║ ██████████▒▒▒▒▒▒▒▒▒▒ ║ →  ║
║ Sentiment                 ║ 51.32    ║ ██████████▒▒▒▒▒▒▒▒▒▒ ║ →  ║
║ Technical                 ║ 31.61    ║ ██████▒▒▒▒▒▒▒▒▒▒▒▒▒▒ ║ ↓  ║
╠═════════════════════════╩══════════╩═════════════════════╩════╣
║ Reliability: 1.00                                              ║
╠══════════════════════════════════════════════════════════════╣
║ DETAILED COMPONENT BREAKDOWN:                                ║
║ Technical Analysis:                                         ║
║ ┌──────────────────────┬─────────┬──────────────────────┐ ║
║ │ Indicator            │ Score   │ Gauge                │ ║
║ ├──────────────────────┼─────────┼──────────────────────┤ ║
║ │ Rsi                  │ 49.45   │ ███████▒▒▒▒▒▒▒▒ │ ║
║ │ Atr                  │ 42.00   │ ██████▒▒▒▒▒▒▒▒▒ │ ║
║ │ Williams R           │ 41.76   │ ██████▒▒▒▒▒▒▒▒▒ │ ║
║ │ Cci                  │ 36.15   │ █████▒▒▒▒▒▒▒▒▒▒ │ ║
║ │ Macd                 │ 24.86   │ ███▒▒▒▒▒▒▒▒▒▒▒▒ │ ║
║ │ Ao                   │ 0.00   │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ │ ║
║ └──────────────────────┴─────────┴──────────────────────┘ ║
╠══════════════════════════════════════════════════════════════╣
║ MARKET INTERPRETATION:                                      ║
║ • Sentiment: Market sentiment is neutral with unfavorable ... ║
╚══════════════════════════════════════════════════════════════╝
```

## Visual Features

1. **Component Sorting**: Components are sorted by score to quickly identify strongest factors
2. **Visual Gauges**: Gauges provide a visual representation of scores
3. **Trend Indicators**: Arrows (↑, →, ↓) show the trend direction
4. **Detailed Breakdowns**: Sub-components are displayed with their own scores and gauges
5. **Structured Layout**: Clean box-drawing characters create a structured display
6. **Interpretations**: Key interpretations from the analysis are displayed

## Usage

### Basic Usage

```python
from src.core.formatting import AnalysisFormatter

# Create the formatter
formatter = AnalysisFormatter()

# Format an analysis result
formatted_output = formatter.format_analysis_result(analysis_result, symbol_str)
logger.info(formatted_output)

# Format just the component breakdown
component_breakdown = formatter.format_component_breakdown(components)
logger.debug(component_breakdown)
```

### Integration with Monitor

The monitor class automatically uses this formatter in the `log_analysis_result` method:

```python
def log_analysis_result(self, analysis_result, symbol_str):
    formatter = AnalysisFormatter()
    formatted_result = formatter.format_analysis_result(analysis_result, symbol_str)
    self.logger.info(f"\n{formatted_result}")
```

## Benefits

1. **Improved Readability**: Structured output makes analysis results easier to read at a glance
2. **Visual Indicators**: Visual elements help quickly interpret results
3. **Comprehensive View**: All important information is presented in a single view
4. **Reduced Log Spam**: Consolidated view reduces excessive log messages
5. **Quick Decision Making**: Easy to identify important signals and trends 