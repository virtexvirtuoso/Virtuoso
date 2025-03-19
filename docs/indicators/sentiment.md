# Sentiment Indicators

## Overview

The `SentimentIndicators` class provides tools for analyzing market sentiment through various data sources including social media, news feeds, and market data. These indicators help identify market mood, crowd psychology, and potential trend shifts through sentiment analysis.

## Available Indicators

### 1. Social Media Sentiment
```python
def calculate_social_sentiment(
    posts: pd.DataFrame,
    sources: List[str] = ['twitter', 'reddit'],
    lookback: str = '24h'
) -> pd.DataFrame:
    """Calculate sentiment from social media sources.
    
    Args:
        posts: DataFrame with social media posts
        sources: List of social media sources
        lookback: Lookback period for analysis
        
    Returns:
        DataFrame with sentiment metrics by source
    """
```

### 2. News Sentiment Analysis
```python
def analyze_news_sentiment(
    news: pd.DataFrame,
    keywords: List[str],
    importance_weights: Dict[str, float] = None
) -> pd.DataFrame:
    """Analyze sentiment from news articles.
    
    Args:
        news: DataFrame with news articles
        keywords: List of keywords to track
        importance_weights: Weight for each news source
        
    Returns:
        DataFrame with news sentiment metrics
    """
```

### 3. Market Sentiment Indicators
```python
def calculate_market_sentiment(
    prices: pd.DataFrame,
    volumes: pd.DataFrame,
    volatility: pd.DataFrame
) -> pd.DataFrame:
    """Calculate market-based sentiment indicators.
    
    Args:
        prices: Price data
        volumes: Volume data
        volatility: Volatility data
        
    Returns:
        DataFrame with market sentiment metrics
    """
```

## Usage Examples

### Basic Usage
```python
from src.indicators import SentimentIndicators

# Initialize
sentiment = SentimentIndicators()

# Calculate social sentiment
social = sentiment.calculate_social_sentiment(posts)

# Analyze news sentiment
news = sentiment.analyze_news_sentiment(articles, keywords)

# Calculate market sentiment
market = sentiment.calculate_market_sentiment(prices, volumes, vol)
```

### Advanced Usage
```python
# Custom configuration
sentiment = SentimentIndicators(
    config={
        'social': {
            'nlp_model': 'bert-base-uncased',
            'min_confidence': 0.8
        },
        'news': {
            'language_detection': True,
            'source_weighting': True
        }
    }
)

# Batch calculation
results = sentiment.calculate_batch(
    data_sources={
        'social': posts,
        'news': articles,
        'market': prices
    },
    indicators=['social', 'news', 'market']
)
```

## Signal Generation

### Sentiment Signals
```python
def generate_sentiment_signals(
    sentiment_metrics: pd.DataFrame,
    threshold: float = 0.7,
    consensus_required: bool = True
) -> pd.Series:
    """Generate trading signals based on sentiment.
    
    Returns:
        Series with values:
        1: Buy signal (positive sentiment)
        -1: Sell signal (negative sentiment)
        0: No signal
    """
```

### Sentiment Divergence
```python
def detect_sentiment_divergence(
    sentiment: pd.Series,
    prices: pd.Series,
    window: int = 20
) -> pd.Series:
    """Detect divergence between sentiment and price.
    
    Returns:
        Series with divergence signals
    """
```

## Performance Optimization

### Caching
```python
# Enable caching for repeated calculations
sentiment.enable_cache()

# Cache with custom TTL
sentiment.enable_cache(ttl=60)  # 1 minute

# Clear cache
sentiment.clear_cache()
```

### Batch Processing
```python
# Process multiple assets
assets = ['BTC-USD', 'ETH-USD']
results = {}

for asset in assets:
    results[asset] = sentiment.calculate_batch(
        data_sources[asset],
        indicators=['social', 'news']
    )
```

## Configuration Options

```python
config = {
    'social': {
        'nlp_model': 'bert-base-uncased',
        'min_confidence': 0.8,
        'sources': ['twitter', 'reddit'],
        'language': 'en',
        'batch_size': 1000
    },
    'news': {
        'sources': ['reuters', 'bloomberg'],
        'importance_weights': {
            'reuters': 1.0,
            'bloomberg': 1.0
        },
        'update_interval': '1h'
    },
    'market': {
        'indicators': ['rsi', 'volume_ratio'],
        'lookback': '7d',
        'smoothing': 0.1,
        'threshold': 0.7
    }
}
```

## Error Handling

```python
try:
    sentiment = sentiment.calculate_social_sentiment(posts)
except ValidationError as e:
    logger.error(f"Invalid sentiment data: {e}")
except CalculationError as e:
    logger.error(f"Calculation failed: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

## Best Practices

1. **Data Preparation**
   ```python
   # Clean text data
   posts = sentiment.clean_text(posts)
   
   # Remove spam/noise
   posts = sentiment.filter_spam(posts)
   
   # Normalize sentiment scores
   sentiment = sentiment.normalize_scores(sentiment)
   ```

2. **Real-time Processing**
   ```python
   # Process streaming data
   sentiment.process_stream(
       stream_type='social',
       data=new_posts,
       update_interval='1m'
   )
   
   # Get latest sentiment
   current_sentiment = sentiment.get_current_sentiment()
   ```

3. **Analysis Integration**
   ```python
   # Combine with technical analysis
   sentiment_score = sentiment.calculate_social_sentiment(posts)
   technical_score = technical.calculate_indicators(prices)
   
   # Generate combined signal
   signal = sentiment.combine_signals([
       (sentiment_score, 0.4),
       (technical_score, 0.6)
   ])
   ```

4. **Performance Monitoring**
   ```python
   # Track calculation time
   with sentiment.timer('sentiment_calculation'):
       score = sentiment.calculate_social_sentiment(posts)
   
   # Get performance stats
   stats = sentiment.get_performance_stats()
   print(f"Average sentiment calculation time: {stats['sentiment_avg_time']}")
   ```

## Integration Examples

### 1. With Trading Strategy
```python
# Use sentiment for strategy adjustment
sentiment = sentiment.calculate_market_sentiment(prices, volumes, vol)
social_score = sentiment.calculate_social_sentiment(posts)

# Adjust strategy parameters
strategy.adjust_parameters(
    sentiment_score=sentiment,
    social_score=social_score,
    adaptation_rate=0.1
)
```

### 2. With Risk Management
```python
# Use sentiment for risk adjustment
news_sentiment = sentiment.analyze_news_sentiment(articles, keywords)
market_sentiment = sentiment.calculate_market_sentiment(prices, volumes, vol)

# Adjust risk limits
risk.adjust_limits(
    news_sentiment=news_sentiment,
    market_sentiment=market_sentiment,
    base_limits=default_limits
)
```

### 3. With Position Sizing
```python
# Use sentiment for position sizing
sentiment_scores = sentiment.calculate_batch(
    data_sources={'social': posts, 'news': articles},
    indicators=['social', 'news']
)

# Calculate position size
position_size = position.calculate_size(
    base_size=1.0,
    sentiment_scores=sentiment_scores,
    risk_factor=0.1
)
```
``` 