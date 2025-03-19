import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from src.utils.error_handling import handle_indicator_error
import time
from src.core.logger import Logger
from .base_indicator import BaseIndicator
from src.core.analysis.indicator_utils import log_score_contributions, log_component_analysis, log_final_score, log_calculation_details

class SentimentIndicators(BaseIndicator):
    """
    A class to calculate various sentiment indicators based on market data.
    Each indicator provides a score from 1 (most bearish) to 100 (most bullish).
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[Logger] = None):
        """Initialize SentimentIndicators.
        
        Components and weights:
        - Funding Rate (15%): Analyzes funding rate trends and volatility
        - Long/Short Ratio (15%): Measures market positioning
        - Liquidations (15%): Tracks forced position closures
        - Volume Sentiment (15%): Analyzes buying/selling volume
        - Market Mood (15%): Overall market mood indicators
        - Risk Score (15%): Measures market risk
        - Funding Rate Volatility (10%): Analyzes funding rate volatility
        """
        # Set required attributes before calling super().__init__
        self.indicator_type = 'sentiment'
        
        # Default component weights
        default_weights = {
            'funding_rate': 0.15,
            'long_short_ratio': 0.15,
            'liquidations': 0.15,
            'volume_sentiment': 0.15,
            'market_mood': 0.15,
            'risk_score': 0.15,
            'funding_rate_volatility': 0.10
        }
        
        # Get sentiment specific config
        sentiment_config = config.get('analysis', {}).get('indicators', {}).get('sentiment', {})
        
        # Read component weights from config if available
        components_config = sentiment_config.get('components', {})
        self.component_weights = {}
        
        # Use weights from config or fall back to defaults
        for component, default_weight in default_weights.items():
            config_weight = components_config.get(component, {}).get('weight', default_weight)
            self.component_weights[component] = config_weight
        
        # Call parent class constructor
        super().__init__(config, logger)
        
        # Initialize parameters
        self.funding_threshold = sentiment_config.get('funding_threshold', 0.01)
        self.liquidation_threshold = sentiment_config.get('liquidation_threshold', 1000000)
        self.sentiment_window = sentiment_config.get('window', 20)
        
        # Initialize tracking variables
        self.sentiment_history = []
        self.last_update = 0
        
        # Cache for missing data
        self._missing_risk_data = False
        
        # Validate weights
        self._validate_weights()
        
        self.logger.info(f"Initialized {self.__class__.__name__} with config: {sentiment_config}")
        
        # Add cache for expensive operations
        self._cache = {
            'missing_risk_data': False,
            'last_funding_rate': None,
            'last_lsr': None,
            'last_calculation_time': 0
        }
        
        # Cache expiration time (10 minutes)
        self.cache_expiration = 10 * 60  # seconds
        
    def _validate_weights(self):
        """Validate that weights sum to 1.0"""
        comp_total = sum(self.component_weights.values())
        if not np.isclose(comp_total, 1.0, rtol=1e-5):
            self.logger.warning(f"Component weights sum to {comp_total}, normalizing")
            self.component_weights = {k: v/comp_total for k, v in self.component_weights.items()}
            self.logger.debug(f"Normalized weights: {self.component_weights}")

    def calculate_long_short_ratio(self, market_data: Dict[str, Any]) -> float:
        """Calculate sentiment score based on long/short ratio."""
        try:
            sentiment_data = market_data.get('sentiment', {})
            long_short_data = sentiment_data.get('long_short_ratio')
            
            self.logger.debug(f"Long/Short raw data: {long_short_data}")
            
            if not long_short_data:
                self.logger.debug("No long/short data available, returning neutral score")
                return 50.0

            # Extract long/short ratio from the data
            if isinstance(long_short_data, dict):
                long_ratio = float(long_short_data.get('long', 0))
                short_ratio = float(long_short_data.get('short', 0))
                self.logger.debug(f"Long ratio: {long_ratio}, Short ratio: {short_ratio}")
                
                if long_ratio == 0 and short_ratio == 0:
                    self.logger.debug("Both ratios are 0, returning neutral score")
                    return 50.0
                    
                total = long_ratio + short_ratio
                long_percentage = (long_ratio / total) if total > 0 else 0.5
            else:
                # If it's a single value, assume it's already a percentage
                long_percentage = float(long_short_data)
                self.logger.debug(f"Direct long percentage: {long_percentage}")
            
            # Convert ratio to score (0.5 ratio = 50 score)
            score = long_percentage * 100
            
            # Bound the score between 0 and 100
            score = max(0, min(100, score))
            
            self.logger.debug(f"Long percentage: {long_percentage:.3f}, Final Score: {score:.2f}")
            return float(score)
            
        except Exception as e:
            self.logger.error(f"Error calculating long/short ratio: {str(e)}", exc_info=True)
            return 50.0

    def calculate_funding_rate(self, market_data: Dict[str, Any]) -> float:
        """Calculate funding rate score (redirects to _calculate_funding_score)."""
        # Process sentiment data first
        sentiment = self._process_sentiment_data(market_data)
        # Use the canonical method
        return self._calculate_funding_score(sentiment)

    def calculate_funding_rate_volatility(self, market_data: Dict[str, Any]) -> float:
        """Calculate sentiment score based on funding rate volatility.
        
        Higher volatility (unstable funding rates) is considered bearish.
        Lower volatility (stable funding rates) is considered bullish.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: Score between 0-100
        """
        try:
            self.logger.debug("\n=== Calculating Funding Rate Volatility ===")
            
            # Extract funding rate history
            sentiment_data = market_data.get('sentiment', {})
            funding_history = sentiment_data.get('funding_history', [])
            
            # If no history is available, check if current funding rate is available
            if not funding_history or len(funding_history) < 2:
                self.logger.debug("Insufficient funding rate history")
                # If current funding rate is very close to zero, consider it stable (bullish)
                current_rate = abs(market_data.get('funding_rate', {}).get('fundingRate', 0.0))
                if isinstance(current_rate, str):
                    try:
                        current_rate = float(current_rate)
                    except:
                        current_rate = 0.0
                
                # If current rate is very small, consider it stable
                if current_rate < 0.0001:
                    self.logger.debug(f"Current funding rate is near zero ({current_rate}), considering stable")
                    return 60.0  # Slightly bullish due to stability
                
                self.logger.debug("No funding history available, using neutral score")
                return 50.0  # Neutral
            
            # Calculate volatility from historical funding rates
            try:
                # Try extracting rates in different formats
                if isinstance(funding_history[0], dict):
                    # Handle dict format
                    if 'rate' in funding_history[0]:
                        rates = [float(rate.get('rate', 0)) for rate in funding_history]
                    elif 'fundingRate' in funding_history[0]:
                        rates = [float(rate.get('fundingRate', 0)) for rate in funding_history]
                    else:
                        # Try to find the rate field
                        keys = funding_history[0].keys()
                        rate_key = next((k for k in keys if 'rate' in k.lower()), None)
                        if rate_key:
                            rates = [float(rate.get(rate_key, 0)) for rate in funding_history]
                        else:
                            self.logger.warning("Could not identify rate field in funding history")
                            return 50.0
                else:
                    # Handle direct array of values
                    rates = [float(rate) for rate in funding_history]
            except Exception as e:
                self.logger.error(f"Error extracting rates from funding history: {e}")
                return 50.0
            
            # Filter out any NaN or infinity values
            rates = [r for r in rates if not np.isnan(r) and not np.isinf(r)]
            
            if not rates or len(rates) < 2:
                self.logger.debug("Insufficient valid funding rates data")
                return 50.0
            
            # Calculate volatility metrics
            volatility = np.std(rates)
            mean_rate = np.mean(rates)
            abs_mean_rate = abs(mean_rate)
            
            self.logger.debug(f"Rates: {rates}")
            self.logger.debug(f"Volatility: {volatility:.6f}")
            self.logger.debug(f"Mean rate: {mean_rate:.6f}")
            
            # Account for the scale of the rates
            # A volatility of 0.001 is very different if mean_rate is 0.01 vs 0.0001
            if abs_mean_rate > 0:
                relative_volatility = volatility / (abs_mean_rate + 1e-10)
            else:
                relative_volatility = volatility * 1000  # Scale up when mean is near zero
            
            self.logger.debug(f"Relative volatility: {relative_volatility:.6f}")
            
            # Calculate volatility score (inverse - higher volatility = lower score)
            # Use scaled sigmoid-like function for smooth transition
            # Volatility threshold is set dynamically based on the mean rate
            threshold = max(0.0001, abs_mean_rate * 0.5)
            
            if relative_volatility <= threshold:
                # Low volatility
                volatility_score = 70 - (relative_volatility / threshold * 20)
            else:
                # High volatility
                volatility_score = 50 - min(30, (relative_volatility - threshold) * 50)
            
            self.logger.debug(f"Volatility threshold: {threshold:.6f}")
            self.logger.debug(f"Final volatility score: {volatility_score:.2f}")
            
            # Ensure final score is within bounds
            final_score = float(np.clip(volatility_score, 0, 100))
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"Error calculating funding rate volatility score: {str(e)}")
            return 50.0

    def calculate_liquidation_events(self, market_data: Dict[str, Any]) -> float:
        """
        Calculate sentiment score based on liquidation events with reversal detection.
        Returns score 0-100 where:
        - 0-30: Strong bearish pressure
        - 30-45: Moderate bearish with potential reversal
        - 45-55: Neutral
        - 55-70: Moderate bullish with potential reversal
        - 70-100: Strong bullish pressure
        """
        try:
            sentiment_data = market_data.get('sentiment', {})
            liquidations = sentiment_data.get('liquidations', [])
            
            if not liquidations:
                return 50.0

            # Extract and process liquidation data
            if isinstance(liquidations, dict):
                # Single liquidation event
                long_liq = float(liquidations.get('long', liquidations.get('longAmount', 0)))
                short_liq = float(liquidations.get('short', liquidations.get('shortAmount', 0)))
                timestamp = liquidations.get('timestamp', time.time() * 1000)
                liquidation_events = [{'amount': long_liq, 'side': 'long', 'timestamp': timestamp}] if long_liq > 0 else []
                liquidation_events.extend([{'amount': short_liq, 'side': 'short', 'timestamp': timestamp}] if short_liq > 0 else [])
            elif isinstance(liquidations, list):
                liquidation_events = liquidations
            else:
                return 50.0

            # Sort by timestamp
            liquidation_events.sort(key=lambda x: x.get('timestamp', 0))
            
            # Calculate time-weighted metrics
            now = time.time() * 1000
            window_size = 3600000  # 1 hour window
            cutoff_time = now - window_size
            
            recent_events = [event for event in liquidation_events 
                            if event.get('timestamp', 0) > cutoff_time]
            
            if not recent_events:
                return 50.0

            # Split into recent and older events
            very_recent_cutoff = now - (window_size * 0.25)  # Last 15 minutes
            very_recent = [event for event in recent_events 
                          if event.get('timestamp', 0) > very_recent_cutoff]
            older_recent = [event for event in recent_events 
                           if event.get('timestamp', 0) <= very_recent_cutoff]

            # Calculate liquidation patterns
            def get_side_totals(events):
                long_total = sum(float(e.get('amount', 0)) for e in events 
                               if e.get('side', '').lower() == 'long')
                short_total = sum(float(e.get('amount', 0)) for e in events 
                                if e.get('side', '').lower() == 'short')
                return long_total, short_total

            recent_long, recent_short = get_side_totals(very_recent)
            older_long, older_short = get_side_totals(older_recent)

            # Calculate acceleration factors
            recent_rate = (recent_long + recent_short) / (window_size * 0.25)
            older_rate = (older_long + older_short) / (window_size * 0.75) if older_recent else 0
            
            acceleration = recent_rate / older_rate if older_rate > 0 else 1.0

            self.logger.debug("\n=== Liquidation Analysis ===")
            self.logger.debug(f"Recent rate: {recent_rate:.2f} contracts/ms")
            self.logger.debug(f"Older rate: {older_rate:.2f} contracts/ms")
            self.logger.debug(f"Acceleration: {acceleration:.2f}x")

            # Determine immediate impact vs reversal weights
            if acceleration > 1.5:
                # Accelerating liquidations - weight immediate impact higher
                immediate_weight = 0.7
                reversal_weight = 0.3
                self.logger.debug("Liquidations accelerating - favoring immediate impact")
            elif acceleration < 0.5:
                # Decelerating liquidations - weight reversal higher
                immediate_weight = 0.3
                reversal_weight = 0.7
                self.logger.debug("Liquidations decelerating - favoring reversal potential")
            else:
                # Stable liquidations - balanced weights
                immediate_weight = 0.5
                reversal_weight = 0.5
                self.logger.debug("Liquidations stable - balanced weighting")

            # Calculate immediate impact score (inverted from liquidation direction)
            total_recent = recent_long + recent_short
            if total_recent > 0:
                long_ratio = recent_long / total_recent
                immediate_score = (1 - long_ratio) * 100  # More long liquidations = bearish immediate impact
            else:
                immediate_score = 50.0

            # Calculate reversal potential score (aligned with liquidation direction)
            total_older = older_long + older_short
            if total_older > 0:
                long_ratio = older_long / total_older
                reversal_score = long_ratio * 100  # More long liquidations = bullish reversal potential
            else:
                reversal_score = 50.0

            # Combine scores
            final_score = (immediate_score * immediate_weight + 
                          reversal_score * reversal_weight)

            self.logger.debug(f"Immediate impact score: {immediate_score:.2f}")
            self.logger.debug(f"Reversal potential score: {reversal_score:.2f}")
            self.logger.debug(f"Final liquidation score: {final_score:.2f}")

            return float(np.clip(final_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating liquidation events score: {str(e)}")
            return 50.0

    def calculate_volume_sentiment(self, market_data: Dict[str, Any]) -> float:
        """Calculate sentiment based on trade volumes."""
        try:
            # Check for trades data
            if 'trades' not in market_data or not market_data['trades']:
                self.logger.debug("No trades data for volume sentiment")
                return 50.0
                
            # Get volume ratio from helper method
            ratio = self._get_volume_sentiment_ratio(market_data)
            
            # Transform to 0-100 scale (1:1 ratio = 50)
            # Higher ratio (more buying) = higher score
            # Lower ratio (more selling) = lower score
            if ratio == 1.0:
                score = 50.0
            elif ratio > 1.0:
                # More buying pressure (max 2:1 = score 100)
                normalized_ratio = min(ratio, 2.0)
                score = 50.0 + (normalized_ratio - 1.0) * 50.0
            else:
                # More selling pressure (min 1:2 = score 0)
                normalized_ratio = max(ratio, 0.5)
                score = 50.0 - ((1.0 / normalized_ratio) - 1.0) * 50.0
                
            # Apply non-linear transformation to make mid-range more sensitive
            adjusted_score = self._apply_sigmoid_transformation(score, sensitivity=0.15)
            
            # Apply recent price trend impact
            if 'ohlcv' in market_data and market_data['ohlcv']:
                try:
                    # Get OHLCV data
                    ohlcv = market_data['ohlcv']
                    df = None
                    
                    # Extract DataFrame using various possible structures
                    if isinstance(ohlcv, dict):
                        if 'base' in ohlcv:
                            base_data = ohlcv['base']
                            if isinstance(base_data, pd.DataFrame):
                                df = base_data
                            elif isinstance(base_data, dict) and 'data' in base_data:
                                df = base_data['data']
                        elif 'data' in ohlcv:
                            df = ohlcv['data']
                    elif isinstance(ohlcv, pd.DataFrame):
                        df = ohlcv
                        
                    if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
                        # Calculate short-term price trend
                        window = min(12, len(df) - 1)
                        if window > 1:
                            oldest_price = df['close'].iloc[-window]
                            newest_price = df['close'].iloc[-1]
                            price_change = (newest_price / oldest_price - 1) * 100
                            
                            # If price trend doesn't match volume sentiment, reduce confidence
                            if (price_change > 0 and adjusted_score < 50) or (price_change < 0 and adjusted_score > 50):
                                # Pull score back toward neutral based on the divergence
                                pull_strength = min(0.3, abs(price_change) / 10)  # Cap at 30%
                                adjusted_score = adjusted_score * (1 - pull_strength) + 50 * pull_strength
                        
                except Exception as e:
                    self.logger.debug(f"Error calculating price trend impact: {e}")
                    
            # Log detailed calculation
            self.logger.debug(f"Volume sentiment - Buy/Sell ratio: {ratio:.3f}, Raw score: {score:.2f}, " +
                            f"Final score: {adjusted_score:.2f}")
            
            return float(np.clip(adjusted_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating volume sentiment: {str(e)}")
            return 50.0
            
    def _calculate_funding_score(self, sentiment_data: Dict[str, Any]) -> float:
        """Calculate sentiment score based on funding rate."""
        try:
            # Check cache for recent calculation
            current_time = time.time()
            if (self._cache['last_funding_rate'] is not None and 
                current_time - self._cache['last_calculation_time'] < self.cache_expiration):
                self.logger.debug("Using cached funding rate calculation")
                return self._cache['last_funding_rate']
                
            # Extract funding rate
            if 'funding_rate' not in sentiment_data:
                self.logger.debug("No funding rate data found")
                return 50.0
                
            funding_rate = sentiment_data['funding_rate']
            
            # Handle different funding rate formats
            if isinstance(funding_rate, dict):
                # Get current rate or last rate from dictionary
                rate = funding_rate.get('current', funding_rate.get('last', funding_rate.get('rate', 0.0)))
            elif isinstance(funding_rate, (int, float)):
                rate = funding_rate
            else:
                self.logger.debug(f"Unsupported funding rate format: {type(funding_rate)}")
                return 50.0
                
            # Ensure rate is a float
            try:
                rate = float(rate)
            except (ValueError, TypeError):
                self.logger.debug(f"Could not convert funding rate to float: {rate}")
                return 50.0
                
            # Normalize rate to percentage
            if abs(rate) > 1:
                # Already in percentage/bps format
                rate_pct = rate
            else:
                # Convert to percentage
                rate_pct = rate * 100
                
            # Calculate hourly, daily, and annual rates
            hourly_rate = rate_pct
            daily_rate = hourly_rate * 24
            annual_rate = daily_rate * 365
            
            # Apply sigmoid transformation to normalize extreme values
            normalized_rate = self._sigmoid_normalize(rate_pct, scale=0.05)
            
            # Calculate sentiment score (inverted - negative funding is bullish)
            score = 50 - normalized_rate * 50
            
            # Log detailed metrics
            self.logger.debug("\n=== Funding Rate Analysis ===")
            self.logger.debug(f"Raw rate: {rate:.6f}")
            self.logger.debug(f"Hourly: {hourly_rate:.4f}%")
            self.logger.debug(f"Daily: {daily_rate:.4f}%")
            self.logger.debug(f"Annual: {annual_rate:.2f}%")
            self.logger.debug(f"Normalized: {normalized_rate:.4f}")
            self.logger.debug(f"Score: {score:.2f}")
            
            # Apply confidence adjustment based on rate magnitude
            adjusted_score = self._apply_sigmoid_transformation(score, sensitivity=0.1)
            self.logger.debug(f"Adjusted score: {adjusted_score:.2f}")
            
            # Apply extreme value capping for very high/low rates
            final_score = np.clip(adjusted_score, 5, 95)
            
            # Cache the result
            self._cache['last_funding_rate'] = final_score
            self._cache['last_calculation_time'] = current_time
            
            return float(final_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating funding rate score: {str(e)}")
            return 50.0
            
    def _calculate_lsr_score(self, sentiment_data: Dict[str, Any]) -> float:
        """Calculate sentiment score based on long/short ratio."""
        try:
            # Check cache for recent calculation
            current_time = time.time()
            if (self._cache['last_lsr'] is not None and 
                current_time - self._cache['last_calculation_time'] < self.cache_expiration):
                self.logger.debug("Using cached long/short ratio calculation")
                return self._cache['last_lsr']
                
            # Extract long/short ratio
            if 'long_short_ratio' not in sentiment_data:
                self.logger.debug("No long/short ratio data found")
                return 50.0
                
            lsr_data = sentiment_data['long_short_ratio']
            
            # Handle different lsr formats
            if isinstance(lsr_data, dict):
                # Look for ratio or calculate from long/short values
                if 'ratio' in lsr_data:
                    ratio = float(lsr_data['ratio'])
                elif 'long' in lsr_data and 'short' in lsr_data:
                    # Calculate ratio from long and short values
                    long_value = float(lsr_data['long'])
                    short_value = float(lsr_data['short'])
                    
                    # Avoid division by zero
                    if short_value <= 0:
                        ratio = 2.0  # Cap at 2:1 for extreme cases
                    else:
                        ratio = long_value / short_value
                else:
                    self.logger.debug(f"No usable data in long_short_ratio: {lsr_data}")
                    return 50.0
            elif isinstance(lsr_data, (int, float)):
                ratio = float(lsr_data)
            else:
                self.logger.debug(f"Unsupported long/short ratio format: {type(lsr_data)}")
                return 50.0
                
            # Cap extreme values
            ratio = min(max(ratio, 0.1), 10.0)
            
            # Calculate score based on the ratio (1:1 = 50)
            if ratio == 1.0:
                score = 50.0
            elif ratio > 1.0:
                # More longs than shorts (bullish)
                # Transform to 50-100 range (max 2:1 ratio = score 100)
                normalized_ratio = min(ratio, 2.0)
                score = 50.0 + (normalized_ratio - 1.0) * 50.0
            else:
                # More shorts than longs (bearish)
                # Transform to 0-50 range (min 1:2 ratio = score 0)
                normalized_ratio = max(ratio, 0.5)
                score = 50.0 - ((1.0 / normalized_ratio) - 1.0) * 50.0
                
            # Apply non-linear transformation to enhance sensitivity around neutral mark
            adjusted_score = self._apply_sigmoid_transformation(score, sensitivity=0.15)
            
            # Log detailed metrics
            self.logger.debug("\n=== Long/Short Ratio Analysis ===")
            self.logger.debug(f"Raw ratio: {ratio:.4f}")
            self.logger.debug(f"Linear score: {score:.2f}")
            self.logger.debug(f"Adjusted score: {adjusted_score:.2f}")
            
            # Cache the result
            self._cache['last_lsr'] = adjusted_score
            self._cache['last_calculation_time'] = current_time
            
            return float(adjusted_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating long/short ratio score: {str(e)}")
            return 50.0
                
    def _apply_sigmoid_transformation(self, value, sensitivity=0.1, center=50):
        """
        Apply sigmoid transformation to make values more sensitive around the center.
        
        Args:
            value: Raw value to transform
            sensitivity: Controls the steepness of the curve
            center: Center point of the transformation
            
        Returns:
            Transformed value
        """
        try:
            # Normalize around center
            normalized = (value - center) / 50
            
            # Apply sigmoid with sensitivity parameter
            transformed = 1 / (1 + np.exp(-normalized / sensitivity))
            
            # Scale back to original range
            result = transformed * 100
            
            return float(result)
        except Exception:
            return value  # Return original value on error

    def calculate_market_mood(self, market_data: Dict[str, Any]) -> float:
        """Calculate overall market mood using multiple metrics."""
        try:
            # Check if we have OHLCV data
            if 'ohlcv' not in market_data:
                self.logger.debug("No OHLCV data available for market mood calculation")
                return 50.0

            # Get OHLCV data
            ohlcv = market_data['ohlcv']
            df = None
            
            # Try to extract dataframe using different structures
            if isinstance(ohlcv, dict):
                if 'base' in ohlcv:
                    # Try to get from standard structure
                    base_data = ohlcv['base']
                    if isinstance(base_data, pd.DataFrame):
                        df = base_data
                    elif isinstance(base_data, dict) and 'data' in base_data:
                        df = base_data['data']
                elif 'data' in ohlcv:
                    # Alternative structure
                    df = ohlcv['data']
            elif isinstance(ohlcv, pd.DataFrame):
                # Direct DataFrame access
                df = ohlcv
                
            # If we couldn't find a valid DataFrame, return neutral
            if df is None or not isinstance(df, pd.DataFrame) or df.empty:
                self.logger.debug("Could not extract valid DataFrame from OHLCV data")
                return 50.0

            # Calculate volatility safely
            try:
                returns = df['close'].pct_change().dropna()
                volatility = returns.std() * np.sqrt(252)  # Annualized volatility
            except (KeyError, ValueError) as e:
                self.logger.debug(f"Error calculating volatility: {e}")
                volatility = 0.01  # Default low volatility
            
            # Calculate momentum safely
            try:
                tail_size = min(20, len(returns))
                momentum = returns.tail(tail_size).mean() * 100
            except (KeyError, ValueError) as e:
                self.logger.debug(f"Error calculating momentum: {e}")
                momentum = 0.0  # Neutral momentum
            
            # Calculate volume trend safely
            try:
                window_size = min(20, len(df) - 1)
                if window_size > 1:
                    volume_ma = df['volume'].rolling(window=window_size).mean()
                    volume_trend = (df['volume'].iloc[-1] / volume_ma.iloc[-1] if not volume_ma.empty and volume_ma.iloc[-1] > 0 else 1.0) - 1
                else:
                    volume_trend = 0
            except (KeyError, ValueError, IndexError) as e:
                self.logger.debug(f"Error calculating volume trend: {e}")
                volume_trend = 0.0  # Neutral trend
            
            # Calculate price trend strength safely
            try:
                if len(df) >= 50:
                    sma_20 = df['close'].rolling(window=20).mean()
                    sma_50 = df['close'].rolling(window=50).mean()
                    trend_strength = (df['close'].iloc[-1] / sma_50.iloc[-1] - 1) * 100 if sma_50.iloc[-1] > 0 else 0
                else:
                    trend_strength = 0
            except (KeyError, ValueError, IndexError) as e:
                self.logger.debug(f"Error calculating trend strength: {e}")
                trend_strength = 0.0  # Neutral strength
            
            # Combine metrics into mood score
            volatility_score = 100 - np.clip(volatility * 100, 0, 100)  # Lower volatility = higher score
            momentum_score = np.clip(momentum * 5 + 50, 0, 100)  # Center around 50
            volume_score = np.clip(volume_trend * 50 + 50, 0, 100)  # Center around 50
            trend_score = np.clip(trend_strength * 2 + 50, 0, 100)  # Center around 50
            
            # Weighted combination
            mood_score = (
                volatility_score * 0.3 +
                momentum_score * 0.3 +
                volume_score * 0.2 +
                trend_score * 0.2
            )
            
            self.logger.debug(f"Market mood - Vol: {volatility_score:.2f}, Mom: {momentum_score:.2f}, Vol: {volume_score:.2f}, Trend: {trend_score:.2f}, Final: {mood_score:.2f}")
            return float(mood_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating market mood: {str(e)}")
            return 50.0

    def calculate_risk_score(self, market_data: Dict[str, Any]) -> float:
        """Calculate risk score with improved risk metrics."""
        try:
            # Check if we've already looked for risk limit data and found it missing
            if self._cache['missing_risk_data']:
                return 50.0

            risk_limit_data = market_data.get('risk_limit', {})
            if not risk_limit_data or 'list' not in risk_limit_data:
                # Cache the fact that risk data is missing to prevent repeated logging
                self._cache['missing_risk_data'] = True
                self.logger.debug("No risk limit data available")
                return 50.0

            risk_tiers = risk_limit_data['list']
            if not risk_tiers:
                self._cache['missing_risk_data'] = True
                return 50.0

            # Reset the missing flag since we found data
            self._cache['missing_risk_data'] = False

            # Get current tier
            current_tier = risk_tiers[0]
            
            # Extract key metrics
            risk_limit_value = float(current_tier.get('riskLimitValue', 0))
            initial_margin = float(current_tier.get('initialMargin', 0))
            max_leverage = float(current_tier.get('maxLeverage', 0))
            maintenance_margin = float(current_tier.get('maintenanceMargin', 0))
            
            self.logger.debug("\n=== Risk Score Calculation ===")
            self.logger.debug(f"Risk limit value: {risk_limit_value:,.0f}")
            self.logger.debug(f"Initial margin: {initial_margin:.4f}")
            self.logger.debug(f"Max leverage: {max_leverage:.2f}x")
            self.logger.debug(f"Maintenance margin: {maintenance_margin:.4f}")

            # Calculate risk metrics
            leverage_score = 100 - (max_leverage / 100 * 50)  # Higher leverage = higher risk
            margin_score = (1 - initial_margin) * 100  # Higher margin = lower risk
            maintenance_score = (1 - maintenance_margin) * 100  # Higher maintenance = lower risk

            self.logger.debug(f"Leverage score: {leverage_score:.2f}")
            self.logger.debug(f"Margin score: {margin_score:.2f}")
            self.logger.debug(f"Maintenance score: {maintenance_score:.2f}")

            # Combine scores with weights
            final_score = (
                leverage_score * 0.4 +
                margin_score * 0.3 +
                maintenance_score * 0.3
            )
            
            self.logger.debug(f"Final risk score: {final_score:.2f}")
            return float(np.clip(final_score, 0, 100))

        except Exception as e:
            self.logger.error(f"Error calculating risk score: {str(e)}")
            return 50.0

    def _log_component_breakdown(self, components: Dict[str, float]) -> None:
        """Log detailed breakdown of sentiment components."""
        try:
            self.logger.debug("\n=== Sentiment Component Breakdown ===")
            for component, score in components.items():
                weight = self.component_weights.get(component, 0.0)
                weighted_score = score * weight
                self.logger.debug(f"{component}:")
                self.logger.debug(f"  Raw Score: {score:.2f}")
                self.logger.debug(f"  Weight: {weight:.2f}")
                self.logger.debug(f"  Weighted Score: {weighted_score:.2f}")
            self.logger.debug("================================")
        except Exception as e:
            self.logger.error(f"Error logging component breakdown: {str(e)}")

    def _get_component_interpretation(self, component: str, score: float) -> str:
        """Get detailed interpretation for each component."""
        try:
            if score >= 80:
                strength = "strongly bullish"
            elif score >= 60:
                strength = "moderately bullish"
            elif score <= 20:
                strength = "strongly bearish"
            elif score <= 40:
                strength = "moderately bearish"
            else:
                strength = "neutral"

            interpretations = {
                'long_short_ratio': f"Long/Short ratio indicating {strength} sentiment",
                'funding_rate': f"Funding rate showing {strength} market expectations",
                'funding_rate_volatility': f"Funding rate volatility suggesting {strength} market stability",
                'liquidation_events': f"Liquidation events indicating {strength} market pressure",
                'volume_sentiment': f"Volume analysis showing {strength} buying/selling pressure",
                'market_mood': f"Overall market mood is {strength}",
                'risk_score': f"Risk metrics suggesting {strength} market conditions"
            }
            
            return interpretations.get(component, f"Score is {strength}")
            
        except Exception as e:
            self.logger.error(f"Error getting component interpretation: {str(e)}")
            return "Interpretation unavailable"

    def _get_detailed_sentiment_interpretation(self, components: Dict[str, float], weighted_score: float) -> Dict[str, Any]:
        """Generate detailed interpretation of sentiment analysis results."""
        try:
            # Get individual component interpretations
            component_interpretations = {
                component: self._get_component_interpretation(component, score)
                for component, score in components.items()
            }

            # Determine overall bias
            if weighted_score >= 70:
                bias = "strongly bullish"
                signal = "strong_buy"
            elif weighted_score >= 60:
                bias = "moderately bullish"
                signal = "buy"
            elif weighted_score <= 30:
                bias = "strongly bearish"
                signal = "strong_sell"
            elif weighted_score <= 40:
                bias = "moderately bearish"
                signal = "sell"
            else:
                bias = "neutral"
                signal = "neutral"

            # Add risk assessment
            risk_level = "favorable" if components.get('risk_score', 50) > 60 else "unfavorable"
            
            return {
                "signal": signal,
                "bias": bias,
                "risk_level": risk_level,
                "summary": f"Market sentiment is {bias} with {risk_level} risk conditions",
                "component_interpretations": component_interpretations
            }
            
        except Exception as e:
            self.logger.error(f"Error generating detailed sentiment interpretation: {str(e)}")
            return {
                "signal": "error",
                "summary": "Unable to generate sentiment interpretation",
                "error": str(e)
            }

    def _get_default_scores(self, reason: str = 'UNKNOWN') -> Dict[str, Any]:
        """Return default scores when analysis fails."""
        timestamp = int(time.time() * 1000)
        return {
            'score': 50.0,
            'components': {
                'long_short_ratio': 50.0,
                'funding_rate': 50.0,
                'funding_rate_volatility': 50.0,
                'liquidations': 50.0,
                'volume_sentiment': 50.0,
                'market_mood': 50.0,
                'risk_score': 50.0
            },
            'interpretation': 'Analysis failed: ' + reason,
            'metadata': {
                'timestamp': timestamp,
                'status': 'ERROR',
                'error': reason,
                'calculation_time_ms': 0
            }
        }

    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate sentiment input data."""
        try:
            if not isinstance(data, dict):
                self.logger.error("Input data must be a dictionary")
                return False
            
            if 'sentiment' not in data:
                self.logger.debug("Creating empty sentiment data structure")
                data['sentiment'] = {
                    'funding_rate': None,
                    'long_short_ratio': None,
                    'liquidations': []
                }
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error validating sentiment data: {str(e)}")
            return False

    @property
    def required_data(self) -> List[str]:
        """Required data fields for sentiment analysis."""
        return ['sentiment', 'ohlcv']

    def reset_cache(self):
        """Reset the calculation cache."""
        self._cache = {
            'missing_risk_data': False,
            'last_funding_rate': None,
            'last_lsr': None,
            'last_calculation_time': 0
        }

    def _calculate_sync(self, sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate sentiment indicators from market data (synchronous version).
        
        Args:
            sentiment_data: Dictionary containing market data
            
        Returns:
            Dictionary containing sentiment scores, components, and interpretation
        """
        try:
            # Track calculation start time
            start_time = time.time()
            
            # Reset any cached state from previous runs
            self.reset_cache()
            
            # Validate input data
            if not sentiment_data:
                self.logger.error("No sentiment data provided")
                return self._get_default_scores()
            
            self.logger.debug(f"Calculating sentiment with input keys: {list(sentiment_data.keys())}")
            
            # Process the sentiment data
            processed_data = self._process_sentiment_data(sentiment_data)
            
            # Calculate component scores
            component_scores = {}
            
            # Calculate funding rate score
            funding_score = self._calculate_funding_score(processed_data)
            component_scores['funding_rate'] = funding_score
            
            # Calculate long-short ratio score
            lsr_score = self._calculate_lsr_score(processed_data)
            component_scores['long_short_ratio'] = lsr_score
            
            # Calculate liquidation score
            liquidation_score = self._calculate_liquidation_score(processed_data)
            component_scores['liquidations'] = liquidation_score
            
            # Calculate volume sentiment
            volume_score = self.calculate_volume_sentiment(processed_data)
            component_scores['volume'] = volume_score
            
            # Calculate market mood
            mood_score = self._calculate_market_mood(processed_data)
            component_scores['market_mood'] = mood_score
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(processed_data)
            component_scores['risk'] = risk_score
            
            # Calculate weighted average of component scores
            weighted_score = self._compute_weighted_score(component_scores)
            component_scores['sentiment'] = weighted_score
            
            # Log the component breakdown
            self._log_component_breakdown(component_scores)
            
            # Get interpretation for each component
            interpretation = self._get_detailed_sentiment_interpretation(component_scores, weighted_score)
            
            # Generate signals based on the scores - handle async method from sync context
            try:
                # Use a non-async way to get signals
                signals = self._get_signals_sync(sentiment_data, existing_scores=component_scores)
            except Exception as e:
                self.logger.error(f"Error generating signals: {str(e)}")
                signals = []
            
            # Calculate time taken
            end_time = time.time()
            calculation_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            # Construct and return result
            result = {
                'score': weighted_score,
                'components': component_scores,
                'signals': signals,
                'interpretation': interpretation,
                'timestamp': end_time,
                'success': True,
                'metadata': {
                    'timestamp': int(end_time * 1000),
                    'status': 'SUCCESS',
                    'calculation_time_ms': calculation_time,
                    'component_weights': self.component_weights,
                    'raw_values': {
                        'funding_rate': processed_data.get('funding_rate', 0),
                        'long_short_ratio': processed_data.get('long_short_ratio', {})
                    }
                }
            }
            
            return result
            
        except Exception as e:
            error_time = time.time()
            self.logger.error(f"Error calculating sentiment: {str(e)}")
            return {
                'score': 50.0, 
                'components': {'sentiment': 50.0},
                'signals': [],
                'interpretation': {
                    'sentiment': 'Neutral (default due to calculation error)',
                    'error': str(e)
                },
                'timestamp': error_time,
                'success': False,
                'metadata': {
                    'timestamp': int(error_time * 1000),
                    'status': 'ERROR',
                    'error': str(e),
                    'calculation_time_ms': 0
                }
            }

    # Original calculate method - keep for backwards compatibility
    def calculate(self, sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate sentiment indicators from market data.
        
        Args:
            sentiment_data: Dictionary containing market data
            
        Returns:
            Dictionary containing sentiment scores, components, and interpretation
        """
        return self._calculate_sync(sentiment_data)

    async def calculate(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async version of calculate method to ensure compatibility with confluence analyzer.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Dictionary containing sentiment scores, components, and interpretation
        """
        try:
            self.logger.debug("Running async calculate for sentiment indicators")
            
            # Call the synchronous calculate method
            result = self._calculate_sync(market_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in async sentiment calculation: {str(e)}", exc_info=True)
            error_time = time.time()
            return {
                'score': 50.0, 
                'components': {'sentiment': 50.0},
                'signals': [],
                'interpretation': {
                    'sentiment': 'Neutral (default due to calculation error)',
                    'error': str(e)
                },
                'timestamp': error_time,
                'success': False,
                'metadata': {
                    'timestamp': int(error_time * 1000),
                    'status': 'ERROR',
                    'error': str(e),
                    'calculation_time_ms': 0
                }
            }

    async def calculate_score(self, market_data: Dict[str, Any]) -> float:
        """
        Calculate sentiment score asynchronously - required for confluence analyzer.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: Overall sentiment score (0-100)
        """
        try:
            self.logger.debug("Running async calculate_score for sentiment indicators")
            
            # Call the regular calculate method which does all the heavy lifting
            result = self.calculate(market_data)
            
            # Extract the overall score from the result
            score = result.get('score', 50.0)
            
            # Log detailed component breakdown using the standard format
            component_scores = result.get('components', {})
            if component_scores:
                from src.core.analysis.indicator_utils import log_score_contributions, log_final_score
                
                # Log component contributions
                log_score_contributions(
                    self.logger, 
                    "Sentiment Score Contribution Breakdown", 
                    component_scores, 
                    self.component_weights,
                    symbol=market_data.get('symbol', ''),
                    final_score=score
                )
                
                # Log final score
                log_final_score(
                    self.logger,
                    "Sentiment",
                    score,
                    symbol=market_data.get('symbol', '')
                )
            
            return float(score)
            
        except Exception as e:
            self.logger.error(f"Error in sentiment calculate_score: {str(e)}", exc_info=True)
            return 50.0  # Default neutral score on error

    async def get_signals(self, sentiment_data: Dict[str, Any], existing_scores: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Extract trading signals from sentiment analysis.
        
        Args:
            sentiment_data: Dictionary containing sentiment data
            existing_scores: Optional pre-calculated scores from a previous call to calculate()
            
        Returns:
            List of signal dictionaries
        """
        try:
            # Use existing scores if provided to avoid redundant calculations
            if existing_scores and isinstance(existing_scores, dict):
                self.logger.debug("Using existing scores for signal generation")
                sentiment_scores = existing_scores
            else:
                # Calculate sentiment scores if not provided
                self.logger.debug("Calculating new scores for signal generation")
                sentiment_result = await self.calculate(sentiment_data)
                sentiment_scores = sentiment_result['components']
            
            signals = []
            sentiment_score = sentiment_scores.get('sentiment', 50.0)
            
            # Generate signals based on overall sentiment score
            if sentiment_score >= 75:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'STRONG',
                    'confidence': min(sentiment_score / 100, 0.95),
                    'reason': 'Strong bullish sentiment detected'
                })
            elif sentiment_score >= 60:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'MEDIUM',
                    'confidence': min(sentiment_score / 100, 0.8),
                    'reason': 'Moderate bullish sentiment detected'
                })
            elif sentiment_score <= 25:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'STRONG',
                    'confidence': min((100 - sentiment_score) / 100, 0.95),
                    'reason': 'Strong bearish sentiment detected'
                })
            elif sentiment_score <= 40:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'MEDIUM',
                    'confidence': min((100 - sentiment_score) / 100, 0.8),
                    'reason': 'Moderate bearish sentiment detected'
                })
            
            # Check for component-specific signals
            
            # Check funding rate signals
            funding_score = sentiment_scores.get('funding_rate', 50.0)
            if funding_score >= 80:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'MEDIUM',
                    'confidence': min(funding_score / 100, 0.85),
                    'reason': 'Highly negative funding rate (favors longs)',
                    'component': 'funding_rate'
                })
            elif funding_score <= 20:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'MEDIUM',
                    'confidence': min((100 - funding_score) / 100, 0.85),
                    'reason': 'Highly positive funding rate (favors shorts)',
                    'component': 'funding_rate'
                })
            
            # Check liquidation signals
            liquidation_score = sentiment_scores.get('liquidations', 50.0)
            if liquidation_score >= 75:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'MEDIUM',
                    'confidence': min(liquidation_score / 100, 0.8),
                    'reason': 'Major short liquidations detected',
                    'component': 'liquidations'
                })
            elif liquidation_score <= 25:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'MEDIUM',
                    'confidence': min((100 - liquidation_score) / 100, 0.8),
                    'reason': 'Major long liquidations detected',
                    'component': 'liquidations'
                })
            
            # Add volume signals
            volume_score = sentiment_scores.get('volume', 50.0)
            if volume_score >= 70:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'WEAK',
                    'confidence': min(volume_score / 100, 0.7),
                    'reason': 'Strong buying volume detected',
                    'component': 'volume'
                })
            elif volume_score <= 30:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'WEAK',
                    'confidence': min((100 - volume_score) / 100, 0.7),
                    'reason': 'Strong selling volume detected',
                    'component': 'volume'
                })
            
            # Combine similar signals
            combined_signals = self._combine_similar_signals(signals)
            
            return combined_signals
        
        except Exception as e:
            self.logger.error(f"Error generating sentiment signals: {str(e)}")
            return []

    def _get_signals_sync(self, sentiment_data: Dict[str, Any], existing_scores: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Synchronous version of get_signals method to be used in _calculate_sync.
        
        Args:
            sentiment_data: Dictionary containing sentiment data
            existing_scores: Optional pre-calculated scores from a previous call to calculate()
            
        Returns:
            List of signal dictionaries
        """
        try:
            # Use existing scores to avoid redundant calculations
            if existing_scores and isinstance(existing_scores, dict):
                self.logger.debug("Using existing scores for signal generation")
                sentiment_scores = existing_scores
            else:
                # For synchronous context, we'll use the synchronous calculate method
                self.logger.debug("Calculating new scores for signal generation")
                sentiment_result = self.calculate(sentiment_data)  # Use synchronous calculate
                sentiment_scores = sentiment_result.get('components', {})
            
            signals = []
            sentiment_score = sentiment_scores.get('sentiment', 50.0)
            
            # Generate signals based on overall sentiment score
            if sentiment_score >= 75:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'STRONG',
                    'confidence': min(sentiment_score / 100, 0.95),
                    'reason': 'Strong bullish sentiment detected'
                })
            elif sentiment_score >= 60:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'MEDIUM',
                    'confidence': min(sentiment_score / 100, 0.8),
                    'reason': 'Moderate bullish sentiment detected'
                })
            elif sentiment_score <= 25:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'STRONG',
                    'confidence': min((100 - sentiment_score) / 100, 0.95),
                    'reason': 'Strong bearish sentiment detected'
                })
            elif sentiment_score <= 40:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'MEDIUM',
                    'confidence': min((100 - sentiment_score) / 100, 0.8),
                    'reason': 'Moderate bearish sentiment detected'
                })
            
            # Check for component-specific signals
            
            # Check funding rate signals
            funding_score = sentiment_scores.get('funding_rate', 50.0)
            if funding_score >= 80:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'MEDIUM',
                    'confidence': min(funding_score / 100, 0.85),
                    'reason': 'Highly negative funding rate (favors longs)',
                    'component': 'funding_rate'
                })
            elif funding_score <= 20:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'MEDIUM',
                    'confidence': min((100 - funding_score) / 100, 0.85),
                    'reason': 'Highly positive funding rate (favors shorts)',
                    'component': 'funding_rate'
                })
            
            # Check liquidation signals
            liquidation_score = sentiment_scores.get('liquidations', 50.0)
            if liquidation_score >= 75:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'MEDIUM',
                    'confidence': min(liquidation_score / 100, 0.8),
                    'reason': 'Major short liquidations detected',
                    'component': 'liquidations'
                })
            elif liquidation_score <= 25:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'MEDIUM',
                    'confidence': min((100 - liquidation_score) / 100, 0.8),
                    'reason': 'Major long liquidations detected',
                    'component': 'liquidations'
                })
            
            # Add volume signals
            volume_score = sentiment_scores.get('volume', 50.0)
            if volume_score >= 70:
                signals.append({
                    'signal': 'BUY',
                    'strength': 'WEAK',
                    'confidence': min(volume_score / 100, 0.7),
                    'reason': 'Strong buying volume detected',
                    'component': 'volume'
                })
            elif volume_score <= 30:
                signals.append({
                    'signal': 'SELL',
                    'strength': 'WEAK',
                    'confidence': min((100 - volume_score) / 100, 0.7),
                    'reason': 'Strong selling volume detected',
                    'component': 'volume'
                })
            
            # Combine similar signals
            combined_signals = self._combine_similar_signals(signals)
            
            return combined_signals
        
        except Exception as e:
            self.logger.error(f"Error generating sentiment signals in sync mode: {str(e)}")
            return []

    def _combine_similar_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Combine signals with the same direction but different sources.
        
        Args:
            signals: List of signal dictionaries
            
        Returns:
            List of combined signals
        """
        if not signals:
            return []
            
        try:
            # Group signals by direction
            buy_signals = [s for s in signals if s['signal'] == 'BUY']
            sell_signals = [s for s in signals if s['signal'] == 'SELL']
            
            result = []
            
            # Combine buy signals if there are multiple
            if len(buy_signals) > 1:
                # Take the strongest signal
                strengths = {'STRONG': 3, 'MEDIUM': 2, 'WEAK': 1}
                strongest = max(buy_signals, key=lambda x: strengths.get(x.get('strength', 'WEAK'), 0))
                
                # Calculate average confidence
                avg_confidence = sum(s.get('confidence', 0) for s in buy_signals) / len(buy_signals)
                
                # Combine reasons
                reasons = [s.get('reason', '') for s in buy_signals]
                combined_reason = "; ".join(reasons)
                
                # Create combined signal
                combined_buy = {
                    'signal': 'BUY',
                    'strength': strongest.get('strength', 'MEDIUM'),
                    'confidence': min(avg_confidence + 0.05, 0.95),  # Slightly boost confidence for multiple signals
                    'reason': combined_reason,
                    'components': [s.get('component', 'multiple') for s in buy_signals]
                }
                
                result.append(combined_buy)
            elif len(buy_signals) == 1:
                result.append(buy_signals[0])
                
            # Combine sell signals if there are multiple
            if len(sell_signals) > 1:
                # Take the strongest signal
                strengths = {'STRONG': 3, 'MEDIUM': 2, 'WEAK': 1}
                strongest = max(sell_signals, key=lambda x: strengths.get(x.get('strength', 'WEAK'), 0))
                
                # Calculate average confidence
                avg_confidence = sum(s.get('confidence', 0) for s in sell_signals) / len(sell_signals)
                
                # Combine reasons
                reasons = [s.get('reason', '') for s in sell_signals]
                combined_reason = "; ".join(reasons)
                
                # Create combined signal
                combined_sell = {
                    'signal': 'SELL',
                    'strength': strongest.get('strength', 'MEDIUM'),
                    'confidence': min(avg_confidence + 0.05, 0.95),  # Slightly boost confidence for multiple signals
                    'reason': combined_reason,
                    'components': [s.get('component', 'multiple') for s in sell_signals]
                }
                
                result.append(combined_sell)
            elif len(sell_signals) == 1:
                result.append(sell_signals[0])
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error combining signals: {str(e)}")
            return signals

    def _get_volume_sentiment_ratio(self, market_data: Dict[str, Any]) -> float:
        """
        Calculate the buy/sell volume ratio from trades.
        
        Args:
            market_data: Dictionary containing market data with trades
            
        Returns:
            float: Ratio of buy volume to sell volume (>1 means more buys)
        """
        try:
            trades = market_data.get('trades', [])
            if not trades:
                return 1.0  # Neutral ratio
                
            # Sum buy and sell volumes
            buy_volume = 0.0
            sell_volume = 0.0
            
            for trade in trades:
                side = trade.get('side', '').lower()
                amount = float(trade.get('amount', trade.get('size', 0)))
                
                if side == 'buy':
                    buy_volume += amount
                elif side == 'sell':
                    sell_volume += amount
            
            # Calculate ratio
            if sell_volume == 0:
                return 2.0  # Cap at 2:1 for extreme cases
            elif buy_volume == 0:
                return 0.5  # Cap at 1:2 for extreme cases
            else:
                return buy_volume / sell_volume
                
        except Exception as e:
            self.logger.error(f"Error calculating volume sentiment ratio: {str(e)}")
            return 1.0  # Neutral on error
            
    def _calculate_market_mood(self, sentiment_data: Dict[str, Any]) -> float:
        """Calculate overall market mood using multiple metrics."""
        try:
            # Check if we have OHLCV data
            if 'ohlcv' not in sentiment_data:
                self.logger.debug("No OHLCV data available for market mood calculation")
                return 50.0

            # Get OHLCV data
            ohlcv = sentiment_data.get('ohlcv')
            df = None
            
            # Try to extract dataframe using different structures
            if isinstance(ohlcv, dict):
                if 'base' in ohlcv:
                    # Try to get from standard structure
                    base_data = ohlcv['base']
                    if isinstance(base_data, pd.DataFrame):
                        df = base_data
                    elif isinstance(base_data, dict) and 'data' in base_data:
                        df = base_data['data']
                elif 'data' in ohlcv:
                    # Alternative structure
                    df = ohlcv['data']
            elif isinstance(ohlcv, pd.DataFrame):
                # Direct DataFrame access
                df = ohlcv
                
            # If we couldn't find a valid DataFrame, return neutral
            if df is None or not isinstance(df, pd.DataFrame) or df.empty:
                self.logger.debug("Could not extract valid DataFrame from OHLCV data")
                return 50.0

            # Calculate volatility safely
            try:
                returns = df['close'].pct_change().dropna()
                volatility = returns.std() * np.sqrt(252)  # Annualized volatility
            except (KeyError, ValueError) as e:
                self.logger.debug(f"Error calculating volatility: {e}")
                volatility = 0.01  # Default low volatility
            
            # Calculate momentum safely
            try:
                tail_size = min(20, len(returns))
                momentum = returns.tail(tail_size).mean() * 100
            except (KeyError, ValueError) as e:
                self.logger.debug(f"Error calculating momentum: {e}")
                momentum = 0.0  # Neutral momentum
            
            # Calculate volume trend safely
            try:
                window_size = min(20, len(df) - 1)
                if window_size > 1:
                    volume_ma = df['volume'].rolling(window=window_size).mean()
                    volume_trend = (df['volume'].iloc[-1] / volume_ma.iloc[-1] if not volume_ma.empty and volume_ma.iloc[-1] > 0 else 1.0) - 1
                else:
                    volume_trend = 0
            except (KeyError, ValueError, IndexError) as e:
                self.logger.debug(f"Error calculating volume trend: {e}")
                volume_trend = 0.0  # Neutral trend
            
            # Calculate price trend strength safely
            try:
                if len(df) >= 50:
                    sma_20 = df['close'].rolling(window=20).mean()
                    sma_50 = df['close'].rolling(window=50).mean()
                    trend_strength = (df['close'].iloc[-1] / sma_50.iloc[-1] - 1) * 100 if sma_50.iloc[-1] > 0 else 0
                else:
                    trend_strength = 0
            except (KeyError, ValueError, IndexError) as e:
                self.logger.debug(f"Error calculating trend strength: {e}")
                trend_strength = 0.0  # Neutral strength
            
            # Combine metrics into mood score
            volatility_score = 100 - np.clip(volatility * 100, 0, 100)  # Lower volatility = higher score
            momentum_score = np.clip(momentum * 5 + 50, 0, 100)  # Center around 50
            volume_score = np.clip(volume_trend * 50 + 50, 0, 100)  # Center around 50
            trend_score = np.clip(trend_strength * 2 + 50, 0, 100)  # Center around 50
            
            # Weighted combination
            mood_score = (
                volatility_score * 0.3 +
                momentum_score * 0.3 +
                volume_score * 0.2 +
                trend_score * 0.2
            )
            
            self.logger.debug(f"Market mood - Vol: {volatility_score:.2f}, Mom: {momentum_score:.2f}, Vol: {volume_score:.2f}, Trend: {trend_score:.2f}, Final: {mood_score:.2f}")
            return float(mood_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating market mood: {str(e)}")
            return 50.0
            
    def _sigmoid_normalize(self, value, scale=1.0):
        """Apply sigmoid normalization to a value."""
        try:
            return 2 / (1 + np.exp(-value * scale)) - 1
        except:
            return 0.0

    def _process_sentiment_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize sentiment data from market data."""
        try:
            # Extract sentiment from market data
            sentiment_data = market_data.get('sentiment', {})
            
            # Ensure we have a proper dictionary
            if not isinstance(sentiment_data, dict):
                self.logger.warning(f"Sentiment data is not a dictionary: {type(sentiment_data)}")
                sentiment_data = {}
                
            # Add additional data that might be needed for sentiment calculations
            if 'ohlcv' in market_data:
                sentiment_data['ohlcv'] = market_data['ohlcv']
                
            if 'trades' in market_data:
                sentiment_data['trades'] = market_data['trades']
                
            if 'ticker' in market_data:
                sentiment_data['ticker'] = market_data['ticker']
                
            if 'risk_limit' in market_data:
                sentiment_data['risk_limit'] = market_data['risk_limit']
                
            # Ensure all required fields exist
            if 'funding_rate' not in sentiment_data and 'ticker' in market_data:
                ticker = market_data['ticker']
                if isinstance(ticker, dict) and 'info' in ticker:
                    funding_rate = ticker['info'].get('fundingRate')
                    if funding_rate is not None:
                        sentiment_data['funding_rate'] = funding_rate
                        
            # Return the processed sentiment data
            return sentiment_data
            
        except Exception as e:
            self.logger.error(f"Error processing sentiment data: {str(e)}")
            return {}

    def _compute_weighted_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted average of sentiment scores."""
        try:
            self.logger.debug(f"\n=== Computing Weighted Score ===")
            self.logger.debug(f"Component weights: {self.component_weights}")
            self.logger.debug(f"Available scores: {scores}")
            
            # Filter to use only components that are in both weights and scores
            valid_components = set(self.component_weights.keys()).intersection(set(scores.keys()))
            
            if not valid_components:
                self.logger.warning("No valid components found for weighted score calculation")
                return 50.0
            
            # Calculate total weight of valid components
            valid_weights = {comp: weight for comp, weight in self.component_weights.items() if comp in valid_components}
            total_weight = sum(valid_weights.values())
            
            if total_weight == 0:
                self.logger.warning("Total weight of valid components is zero")
                return 50.0
            
            # Calculate weighted sum
            weighted_sum = sum(scores[component] * weight for component, weight in valid_weights.items())
            
            # Normalize by total weight
            final_score = weighted_sum / total_weight
            
            self.logger.debug(f"Valid components: {valid_components}")
            self.logger.debug(f"Total weight: {total_weight:.4f}")
            self.logger.debug(f"Weighted sum: {weighted_sum:.4f}")
            self.logger.debug(f"Final score: {final_score:.4f}")
            
            return float(np.clip(final_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error computing weighted score: {str(e)}")
            # Return average of available scores if possible
            if scores:
                avg_score = sum(scores.values()) / len(scores)
                self.logger.warning(f"Falling back to simple average: {avg_score:.2f}")
                return float(np.clip(avg_score, 0, 100))
            return 50.0

    def _calculate_liquidation_score(self, sentiment_data: Dict[str, Any]) -> float:
        """Calculate sentiment score based on liquidation events."""
        try:
            # Extract liquidation events
            if 'liquidations' not in sentiment_data:
                self.logger.debug("No liquidation data found")
                return 50.0
                
            liquidations = sentiment_data['liquidations']
            
            if not liquidations:
                self.logger.debug("Empty liquidation data")
                return 50.0

            # Extract and process liquidation data
            if isinstance(liquidations, dict):
                # Single liquidation event
                long_liq = float(liquidations.get('long', liquidations.get('longAmount', 0)))
                short_liq = float(liquidations.get('short', liquidations.get('shortAmount', 0)))
                timestamp = liquidations.get('timestamp', time.time() * 1000)
                liquidation_events = [{'amount': long_liq, 'side': 'long', 'timestamp': timestamp}] if long_liq > 0 else []
                liquidation_events.extend([{'amount': short_liq, 'side': 'short', 'timestamp': timestamp}] if short_liq > 0 else [])
            elif isinstance(liquidations, list):
                liquidation_events = liquidations
            else:
                self.logger.debug(f"Unsupported liquidation data format: {type(liquidations)}")
                return 50.0

            # Sort by timestamp
            liquidation_events.sort(key=lambda x: x.get('timestamp', 0))
            
            # Calculate time-weighted metrics
            now = time.time() * 1000
            window_size = 3600000  # 1 hour window
            cutoff_time = now - window_size
            
            recent_events = [event for event in liquidation_events 
                            if event.get('timestamp', 0) > cutoff_time]
            
            if not recent_events:
                self.logger.debug("No recent liquidation events")
                return 50.0

            # Split into recent and older events
            very_recent_cutoff = now - (window_size * 0.25)  # Last 15 minutes
            very_recent = [event for event in recent_events 
                          if event.get('timestamp', 0) > very_recent_cutoff]
            older_recent = [event for event in recent_events 
                           if event.get('timestamp', 0) <= very_recent_cutoff]

            # Calculate liquidation patterns
            def get_side_totals(events):
                long_total = sum(float(e.get('amount', 0)) for e in events 
                               if e.get('side', '').lower() == 'long')
                short_total = sum(float(e.get('amount', 0)) for e in events 
                                if e.get('side', '').lower() == 'short')
                return long_total, short_total

            recent_long, recent_short = get_side_totals(very_recent)
            older_long, older_short = get_side_totals(older_recent)

            # Calculate acceleration factors
            recent_rate = (recent_long + recent_short) / (window_size * 0.25)
            older_rate = (older_long + older_short) / (window_size * 0.75) if older_recent else 0
            
            acceleration = recent_rate / older_rate if older_rate > 0 else 1.0

            self.logger.debug("\n=== Liquidation Analysis ===")
            self.logger.debug(f"Recent rate: {recent_rate:.2f} contracts/ms")
            self.logger.debug(f"Older rate: {older_rate:.2f} contracts/ms")
            self.logger.debug(f"Acceleration: {acceleration:.2f}x")

            # Determine immediate impact vs reversal weights
            if acceleration > 1.5:
                # Accelerating liquidations - weight immediate impact higher
                immediate_weight = 0.7
                reversal_weight = 0.3
                self.logger.debug("Liquidations accelerating - favoring immediate impact")
            elif acceleration < 0.5:
                # Decelerating liquidations - weight reversal higher
                immediate_weight = 0.3
                reversal_weight = 0.7
                self.logger.debug("Liquidations decelerating - favoring reversal potential")
            else:
                # Stable liquidations - balanced weights
                immediate_weight = 0.5
                reversal_weight = 0.5
                self.logger.debug("Liquidations stable - balanced weighting")

            # Calculate immediate impact score (inverted from liquidation direction)
            total_recent = recent_long + recent_short
            if total_recent > 0:
                long_ratio = recent_long / total_recent
                immediate_score = (1 - long_ratio) * 100  # More long liquidations = bearish immediate impact
            else:
                immediate_score = 50.0

            # Calculate reversal potential score (aligned with liquidation direction)
            total_older = older_long + older_short
            if total_older > 0:
                long_ratio = older_long / total_older
                reversal_score = long_ratio * 100  # More long liquidations = bullish reversal potential
            else:
                reversal_score = 50.0

            # Combine scores
            final_score = (immediate_score * immediate_weight + 
                          reversal_score * reversal_weight)

            self.logger.debug(f"Immediate impact score: {immediate_score:.2f}")
            self.logger.debug(f"Reversal potential score: {reversal_score:.2f}")
            self.logger.debug(f"Final liquidation score: {final_score:.2f}")

            return float(np.clip(final_score, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error calculating liquidation score: {str(e)}")
            return 50.0

    def _calculate_risk_score(self, market_data: Dict[str, Any]) -> float:
        """Calculate risk score with improved risk metrics."""
        try:
            # Check if we've already looked for risk limit data and found it missing
            if self._cache['missing_risk_data']:
                return 50.0

            risk_limit_data = market_data.get('risk_limit', {})
            if not risk_limit_data or 'list' not in risk_limit_data:
                # Cache the fact that risk data is missing to prevent repeated logging
                self._cache['missing_risk_data'] = True
                self.logger.debug("No risk limit data available")
                return 50.0

            risk_tiers = risk_limit_data['list']
            if not risk_tiers:
                self._cache['missing_risk_data'] = True
                return 50.0

            # Reset the missing flag since we found data
            self._cache['missing_risk_data'] = False

            # Get current tier
            current_tier = risk_tiers[0]
            
            # Extract key metrics
            risk_limit_value = float(current_tier.get('riskLimitValue', 0))
            initial_margin = float(current_tier.get('initialMargin', 0))
            max_leverage = float(current_tier.get('maxLeverage', 0))
            maintenance_margin = float(current_tier.get('maintenanceMargin', 0))
            
            self.logger.debug("\n=== Risk Score Calculation ===")
            self.logger.debug(f"Risk limit value: {risk_limit_value:,.0f}")
            self.logger.debug(f"Initial margin: {initial_margin:.4f}")
            self.logger.debug(f"Max leverage: {max_leverage:.2f}x")
            self.logger.debug(f"Maintenance margin: {maintenance_margin:.4f}")

            # Calculate risk metrics
            leverage_score = 100 - (max_leverage / 100 * 50)  # Higher leverage = higher risk
            margin_score = (1 - initial_margin) * 100  # Higher margin = lower risk
            maintenance_score = (1 - maintenance_margin) * 100  # Higher maintenance = lower risk

            self.logger.debug(f"Leverage score: {leverage_score:.2f}")
            self.logger.debug(f"Margin score: {margin_score:.2f}")
            self.logger.debug(f"Maintenance score: {maintenance_score:.2f}")

            # Combine scores with weights
            final_score = (
                leverage_score * 0.4 +
                margin_score * 0.3 +
                maintenance_score * 0.3
            )
            
            self.logger.debug(f"Final risk score: {final_score:.2f}")
            return float(np.clip(final_score, 0, 100))

        except Exception as e:
            self.logger.error(f"Error calculating risk score: {str(e)}")
            return 50.0
