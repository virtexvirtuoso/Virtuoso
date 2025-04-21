# Sentiment Indicators

## Overview

The `SentimentIndicators` class provides comprehensive market sentiment analysis through multiple weighted components. Each indicator generates a score from 0 (most bearish) to 100 (most bullish), with 50 representing neutral sentiment.

## Component Weights

The sentiment analysis uses the following weighted components:

| Component | Weight | Description |
|-----------|--------|-------------|
| Funding Rate | 20% | Analyzes funding rate trends and volatility |
| Long/Short Ratio | 20% | Measures market positioning |
| Liquidations | 20% | Tracks forced position closures |
| Volume Sentiment | 20% | Analyzes buying/selling volume |
| Market Mood | 20% | Overall market mood indicators |
| Risk Score | 20% | Measures market risk |

## Available Indicators

### 1. Funding Rate Analysis
```python
def calculate_funding_rate(
    market_data: Dict[str, Any]
) -> float:
    """Calculate funding rate sentiment score.
    
    Process:
    1. Extract current funding rate
    2. Compare to threshold (default ±0.0075)
    3. Convert to sentiment score where:
       - High positive funding = bearish (longs pay shorts)
       - High negative funding = bullish (shorts pay longs)
       - Score mapping:
         * -threshold -> 100 (most bullish)
         * 0 -> 50 (neutral)
         * +threshold -> 0 (most bearish)
    """
```

### 2. Long/Short Ratio
```python
def calculate_long_short_ratio(
    market_data: Dict[str, Any]
) -> float:
    """Calculate long/short ratio sentiment.
    
    Process:
    1. Extract long and short positions
    2. Calculate ratio = long / (long + short)
    3. Convert to score where:
       - 100% long = 100 (extremely bullish)
       - 50% long = 50 (neutral)
       - 0% long = 0 (extremely bearish)
    """
```

### 3. Market Mood Analysis
```python
def _calculate_market_mood(
    sentiment_data: Dict[str, Any]
) -> float:
    """Calculate overall market mood score.
    
    Components and weights:
    - Social Sentiment (25%): Social media sentiment
    - Fear & Greed Index (40%): Market psychology
    - Search Trends (15%): Retail interest
    - Positive Mentions (20%): News/social mentions
    
    Fear & Greed Index mapping:
    - 0-24: Extreme Fear -> 0-40 score
    - 25-44: Fear -> 41-48 score
    - 45-55: Neutral -> 49-51 score
    - 56-75: Greed -> 52-60 score
    - 76-100: Extreme Greed -> 61-100 score
    """
```

### 4. Liquidation Events
```python
def calculate_liquidation_events(
    liquidations: List[Dict[str, Any]]
) -> float:
    """Calculate liquidation-based sentiment.
    
    Process:
    1. Analyze liquidation events
    2. Compare long vs short liquidations
    3. Consider liquidation sizes
    4. Score based on:
       - Net liquidation direction
       - Liquidation volume
       - Price impact
    """
```

## Configuration Parameters

```python
params = {
    # Sigmoid transformation
    'sigmoid_transformation': {
        'default_sensitivity': 0.12,
        'long_short_sensitivity': 0.12,
        'funding_sensitivity': 0.15,
        'liquidation_sensitivity': 0.10
    },
    
    # Funding rate
    'funding_threshold': 0.0075,
    'funding_ma_period': 24,
    
    # Market mood
    'mood_weights': {
        'social_sentiment': 0.25,
        'fear_and_greed': 0.40,
        'search_trends': 0.15,
        'positive_mentions': 0.20
    },
    
    # Confidence weights
    'confidence_weights': {
        'long_short_ratio': 0.2,
        'funding_rate': 0.2,
        'liquidations': 0.15,
        'market_mood': 0.15,
        'risk_limit': 0.15,
        'volume': 0.15
    }
}
```

## Signal Generation

### 1. Overall Sentiment Signals
```python
def _generate_signals(
    component_scores: Dict[str, float],
    overall_score: float
) -> List[Dict[str, Any]]:
    """Generate trading signals.
    
    Signal thresholds:
    - score < 30: Strong sell (0.8 confidence)
    - score < 45: Moderate sell (0.6 confidence)
    - score 45-55: Neutral (no signal)
    - score > 55: Moderate buy (0.6 confidence)
    - score > 70: Strong buy (0.8 confidence)
    
    Risk modifiers:
    - High risk (< 30): Reduce confidence by 30%
    - Low risk (> 70): Increase confidence by 20%
    """
```

### 2. Confidence Calculation
```python
def _calculate_confidence(
    market_data: Dict[str, Any]
) -> float:
    """Calculate confidence score (0-1).
    
    Factors considered:
    1. Data completeness
    2. Data quality
    3. Data timeliness
    
    Component weights:
    - Long/Short Ratio: 20%
    - Funding Rate: 20%
    - Liquidations: 15%
    - Market Mood: 15%
    - Risk Limit: 15%
    - Volume: 15%
    """
```

## Integration Examples

### 1. With Position Sizing
```python
# Calculate sentiment
sentiment = sentiment_indicators.calculate(market_data)

# Adjust position size
position_size = base_size * (1 + (sentiment.score - 50) / 100)
if sentiment.confidence < 0.5:
    position_size *= 0.5
```

### 2. With Risk Management
```python
# Get sentiment signals
signals = sentiment.get_signals()

# Update risk limits
for signal in signals:
    if signal.strength == 'strong':
        risk_limits.adjust_by_factor(1.2)
    elif signal.confidence < 0.5:
        risk_limits.adjust_by_factor(0.8)
```

### 3. With Order Flow
```python
# Combine sentiment with order flow
sentiment_score = sentiment.calculate(market_data)
flow_score = orderflow.calculate(market_data)

# Weight by confidence
combined_score = (
    sentiment_score * sentiment.confidence +
    flow_score * flow.confidence
) / (sentiment.confidence + flow.confidence)
```

## Best Practices

1. **Data Quality**
   ```python
   # Validate input data
   if not sentiment.validate_input(market_data):
       logger.warning("Insufficient sentiment data")
       return default_values
   ```

2. **Historical Context**
   ```python
   # Update historical metrics
   sentiment.update_history(
       funding_rate=current_funding,
       market_mood=current_mood
   )
   
   # Compare to typical values
   funding_ratio = current_funding / sentiment.typical_funding
   mood_ratio = current_mood / sentiment.typical_mood
   ```

3. **Performance Monitoring**
   ```python
   # Track calculation time
   with sentiment.timer('sentiment_analysis'):
       score = sentiment.calculate(market_data)
   
   # Log performance metrics
   stats = sentiment.get_performance_stats()
   logger.info(f"Average calculation time: {stats['avg_time']}")
   ```

4. **Component Analysis**
   ```python
   # Get detailed component breakdown
   components = sentiment.get_component_scores()
   
   # Log significant components
   for component, score in components.items():
       if abs(score - 50) > 20:  # Significant deviation
           logger.info(f"{component} showing strong signal: {score}")
   ```
``` 