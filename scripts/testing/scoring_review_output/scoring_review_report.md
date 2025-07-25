
# Comprehensive Indicator Scoring Review Report

## Executive Summary
This report analyzes all indicator scoring methods to ensure they follow the standardized 0-100 bullish/bearish scheme where:
- **100 = Extremely Bullish**
- **50 = Neutral** 
- **0 = Extremely Bearish**

## Analysis Results


### technical_indicators.py
**Scoring Methods Found:** 8
**Issues Found:** 10

**Issues:**
- ⚠️  _calculate_component_scores: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_component_scores: No neutral fallback (50.0) found
- ⚠️  _calculate_component_scores: Non-standard score range detected
- ⚠️  _calculate_ao_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_ao_score: Non-standard score range detected
- ⚠️  _calculate_atr_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_atr_score: Non-standard score range detected
- ⚠️  _calculate_cci_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_cci_score: Non-standard score range detected
- ⚠️  _calculate_rsi_divergence(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate RSI divergence."""
        try:
            # Validate input
            if not isinstance(df, pd.DataFrame) or df.empty:
                raise ValueError("Invalid or empty DataFrame passed to _calculate_rsi_divergence")
            
            # Calculate RSI
            rsi = talib.RSI(df['close'], timeperiod=self.rsi_period)
            
            # Check for NaN values
            if pd.isna(rsi.iloc[-1]):
                self.logger.debug("NaN value in RSI calculation")
                return {'strength': 50.0, 'type': 'neutral'}
            
            # Calculate divergence
            current_rsi = rsi.iloc[-1]
            prev_rsi = rsi.iloc[-2]
            
            if current_rsi > 70 and prev_rsi <= 70:
                return {'strength': 100.0, 'type': 'bullish'}
            elif current_rsi < 30 and prev_rsi >= 30:
                return {'strength': 100.0, 'type': 'bearish'}
            else:
                return {'strength': 50.0, 'type': 'neutral'}
        
        except Exception as e:
            self.logger.error(f"Error calculating RSI divergence: {str(e)}")
            return {'strength': 50.0, 'type': 'neutral'}

    def _calculate_ao_divergence(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate AO divergence."""
        try:
            # Validate input
            if not isinstance(df, pd.DataFrame) or df.empty:
                raise ValueError("Invalid or empty DataFrame passed to _calculate_ao_divergence")
            
            # Calculate AO manually since talib doesn't have it directly
            median_price = pd.Series(talib.MEDPRICE(df['high'].values, df['low'].values), index=df.index)
            
            # Need at least 34 data points for AO calculation
            if len(df) < 34:
                self.logger.debug(f"Insufficient data for AO calculation: {len(df)} < 34")
                return {'strength': 50.0, 'type': 'neutral'}
            
            # Calculate AO as 5-period SMA - 34-period SMA of median price
            fast_sma = talib.SMA(median_price, timeperiod=5)
            slow_sma = talib.SMA(median_price, timeperiod=34)
            ao = fast_sma - slow_sma
            
            # Check for NaN values
            if pd.isna(ao.iloc[-1]):
                self.logger.debug(f"NaN value in AO calculation: {len(df)}")
                return {'strength': 50.0, 'type': 'neutral'}
            
            # Calculate divergence
            current_ao = ao.iloc[-1]
            prev_ao = ao.iloc[-2]
            
            if current_ao > 0 and prev_ao <= 0:
                return {'strength': 100.0, 'type': 'bullish'}
            elif current_ao < 0 and prev_ao >= 0:
                return {'strength': 100.0, 'type': 'bearish'}
            else:
                return {'strength': 50.0, 'type': 'neutral'}
            
        except Exception as e:
            self.logger.error(f"Error calculating AO divergence: {str(e)}")
            return {'strength': 50.0, 'type': 'neutral'}

    def _apply_divergence_adjustments(self, component_scores: Dict[str, float], divergence_data: Dict[str, Any]) -> Dict[str, float]:
        """Apply divergence adjustments to component scores."""
        try:
            # For empty or None input, return default scores
            if not component_scores:
                return {comp: 50.0 for comp in self.component_weights}

            adjusted_scores = {}
            
            for comp, score in component_scores.items: No neutral fallback (50.0) found

**Scoring Methods:**
- `_calculate_component_scores`: ❌ 3 issues
- `_calculate_rsi_score`: ✅ OK
- `_calculate_macd_score`: ✅ OK
- `_calculate_ao_score`: ❌ 2 issues
- `_calculate_williams_r_score`: ✅ OK
- `_calculate_atr_score`: ❌ 2 issues
- `_calculate_cci_score`: ❌ 2 issues
- `_calculate_rsi_divergence(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate RSI divergence."""
        try:
            # Validate input
            if not isinstance(df, pd.DataFrame) or df.empty:
                raise ValueError("Invalid or empty DataFrame passed to _calculate_rsi_divergence")
            
            # Calculate RSI
            rsi = talib.RSI(df['close'], timeperiod=self.rsi_period)
            
            # Check for NaN values
            if pd.isna(rsi.iloc[-1]):
                self.logger.debug("NaN value in RSI calculation")
                return {'strength': 50.0, 'type': 'neutral'}
            
            # Calculate divergence
            current_rsi = rsi.iloc[-1]
            prev_rsi = rsi.iloc[-2]
            
            if current_rsi > 70 and prev_rsi <= 70:
                return {'strength': 100.0, 'type': 'bullish'}
            elif current_rsi < 30 and prev_rsi >= 30:
                return {'strength': 100.0, 'type': 'bearish'}
            else:
                return {'strength': 50.0, 'type': 'neutral'}
        
        except Exception as e:
            self.logger.error(f"Error calculating RSI divergence: {str(e)}")
            return {'strength': 50.0, 'type': 'neutral'}

    def _calculate_ao_divergence(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate AO divergence."""
        try:
            # Validate input
            if not isinstance(df, pd.DataFrame) or df.empty:
                raise ValueError("Invalid or empty DataFrame passed to _calculate_ao_divergence")
            
            # Calculate AO manually since talib doesn't have it directly
            median_price = pd.Series(talib.MEDPRICE(df['high'].values, df['low'].values), index=df.index)
            
            # Need at least 34 data points for AO calculation
            if len(df) < 34:
                self.logger.debug(f"Insufficient data for AO calculation: {len(df)} < 34")
                return {'strength': 50.0, 'type': 'neutral'}
            
            # Calculate AO as 5-period SMA - 34-period SMA of median price
            fast_sma = talib.SMA(median_price, timeperiod=5)
            slow_sma = talib.SMA(median_price, timeperiod=34)
            ao = fast_sma - slow_sma
            
            # Check for NaN values
            if pd.isna(ao.iloc[-1]):
                self.logger.debug(f"NaN value in AO calculation: {len(df)}")
                return {'strength': 50.0, 'type': 'neutral'}
            
            # Calculate divergence
            current_ao = ao.iloc[-1]
            prev_ao = ao.iloc[-2]
            
            if current_ao > 0 and prev_ao <= 0:
                return {'strength': 100.0, 'type': 'bullish'}
            elif current_ao < 0 and prev_ao >= 0:
                return {'strength': 100.0, 'type': 'bearish'}
            else:
                return {'strength': 50.0, 'type': 'neutral'}
            
        except Exception as e:
            self.logger.error(f"Error calculating AO divergence: {str(e)}")
            return {'strength': 50.0, 'type': 'neutral'}

    def _apply_divergence_adjustments(self, component_scores: Dict[str, float], divergence_data: Dict[str, Any]) -> Dict[str, float]:
        """Apply divergence adjustments to component scores."""
        try:
            # For empty or None input, return default scores
            if not component_scores:
                return {comp: 50.0 for comp in self.component_weights}

            adjusted_scores = {}
            
            for comp, score in component_scores.items`: ❌ 1 issues


### volume_indicators.py
**Scoring Methods Found:** 10
**Issues Found:** 14

**Issues:**
- ⚠️  _calculate_volume_trend(self, trades_data: pd.DataFrame) -> float:
        """Calculate volume trend score."""
        try:
            if isinstance(trades_data, list):
                trades_df = pd.DataFrame(trades_data)
            else:
                trades_df = trades_data.copy()

            if trades_df.empty:
                return 50.0

            # Convert volume to numeric if needed
            if 'amount' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['amount'], errors='coerce')
            elif 'volume' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['volume'], errors='coerce')
            else:
                return 50.0

            # Calculate volume trend using simple moving averages
            short_ma = talib.SMA(trades_df['volume'], timeperiod=5)
            long_ma = trades_talib.SMA(df['volume'], timeperiod=20)

            if short_ma.empty or long_ma.empty:
                return 50.0

            # Calculate trend strength
            trend = (short_ma.iloc[-1] / long_ma.iloc[-1] - 1) * 100
            
            # Normalize to 0-100 scale
            score = self._normalize_value(trend, -50, 50)
            return score

        except Exception as e:
            self.logger.error(f"Error calculating volume trend: {str(e)}")
            return 50.0

    def _calculate_volume_volatility(self, trades_data: pd.DataFrame) -> float:
        """Calculate volume volatility score."""
        try:
            if isinstance(trades_data, list):
                trades_df = pd.DataFrame(trades_data)
            else:
                trades_df = trades_data.copy()

            if trades_df.empty:
                return 50.0

            # Convert volume to numeric if needed
            if 'amount' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['amount'], errors='coerce')
            elif 'volume' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['volume'], errors='coerce')
            else:
                return 50.0

            # Calculate volume volatility using standard deviation
            volatility = trades_df['volume'].std() / trades_df['volume'].mean()
            
            # Normalize to 0-100 scale
            score = self._normalize_value(volatility, 0, 2)
            return score

        except Exception as e:
            self.logger.error(f"Error calculating volume volatility: {str(e)}")
            return 50.0

    def normalize_volume(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize volume values with safety checks."""
        try:
            if pd.isna(value) or pd.isna(min_val) or pd.isna(max_val):
                self.logger.warning("NaN values in normalization, returning neutral value")
                return 50.0
                
            if min_val == max_val:
                # Instead of returning 0, calculate relative to historical average
                historical_avg = self.calculate_historical_average(value)
                normalized = 50.0 * (value / historical_avg) if historical_avg > 0 else 50.0
                return float(np.clip(normalized, 0, 100))
                
            normalized = ((value - min_val) / (max_val - min_val)) * 100
            return float(np.clip(normalized, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error in normalize_volume: {e}")
            return 50.0

    def calculate_historical_average(self, current_value: float) -> float:
        """Calculate historical average for normalization when min equals max."""
        try:
            # Use exponential moving average of recent values
            if not hasattr(self, '_historical_values'):
                self._historical_values = []
            
            self._historical_values.append(current_value)
            if len(self._historical_values) > 100:  # Keep last 100 values
                self._historical_values.pop(0)
                
            if not self._historical_values:
                return current_value
                
            return np.mean(self._historical_values)
            
        except Exception as e:
            self.logger.error(f"Error calculating historical average: {e}")
            return current_value if current_value > 0 else 1.0

    def _normalize_value(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize a value to the range [0, 100]"""
        try:
            normalized = ((value - min_val) / (max_val - min_val)) * 100
            return float(np.clip(normalized, 0, 100))
        except:
            return 50.0

    def _compute_weighted_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_volume_trend(self, trades_data: pd.DataFrame) -> float:
        """Calculate volume trend score."""
        try:
            if isinstance(trades_data, list):
                trades_df = pd.DataFrame(trades_data)
            else:
                trades_df = trades_data.copy()

            if trades_df.empty:
                return 50.0

            # Convert volume to numeric if needed
            if 'amount' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['amount'], errors='coerce')
            elif 'volume' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['volume'], errors='coerce')
            else:
                return 50.0

            # Calculate volume trend using simple moving averages
            short_ma = talib.SMA(trades_df['volume'], timeperiod=5)
            long_ma = trades_talib.SMA(df['volume'], timeperiod=20)

            if short_ma.empty or long_ma.empty:
                return 50.0

            # Calculate trend strength
            trend = (short_ma.iloc[-1] / long_ma.iloc[-1] - 1) * 100
            
            # Normalize to 0-100 scale
            score = self._normalize_value(trend, -50, 50)
            return score

        except Exception as e:
            self.logger.error(f"Error calculating volume trend: {str(e)}")
            return 50.0

    def _calculate_volume_volatility(self, trades_data: pd.DataFrame) -> float:
        """Calculate volume volatility score."""
        try:
            if isinstance(trades_data, list):
                trades_df = pd.DataFrame(trades_data)
            else:
                trades_df = trades_data.copy()

            if trades_df.empty:
                return 50.0

            # Convert volume to numeric if needed
            if 'amount' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['amount'], errors='coerce')
            elif 'volume' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['volume'], errors='coerce')
            else:
                return 50.0

            # Calculate volume volatility using standard deviation
            volatility = trades_df['volume'].std() / trades_df['volume'].mean()
            
            # Normalize to 0-100 scale
            score = self._normalize_value(volatility, 0, 2)
            return score

        except Exception as e:
            self.logger.error(f"Error calculating volume volatility: {str(e)}")
            return 50.0

    def normalize_volume(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize volume values with safety checks."""
        try:
            if pd.isna(value) or pd.isna(min_val) or pd.isna(max_val):
                self.logger.warning("NaN values in normalization, returning neutral value")
                return 50.0
                
            if min_val == max_val:
                # Instead of returning 0, calculate relative to historical average
                historical_avg = self.calculate_historical_average(value)
                normalized = 50.0 * (value / historical_avg) if historical_avg > 0 else 50.0
                return float(np.clip(normalized, 0, 100))
                
            normalized = ((value - min_val) / (max_val - min_val)) * 100
            return float(np.clip(normalized, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error in normalize_volume: {e}")
            return 50.0

    def calculate_historical_average(self, current_value: float) -> float:
        """Calculate historical average for normalization when min equals max."""
        try:
            # Use exponential moving average of recent values
            if not hasattr(self, '_historical_values'):
                self._historical_values = []
            
            self._historical_values.append(current_value)
            if len(self._historical_values) > 100:  # Keep last 100 values
                self._historical_values.pop(0)
                
            if not self._historical_values:
                return current_value
                
            return np.mean(self._historical_values)
            
        except Exception as e:
            self.logger.error(f"Error calculating historical average: {e}")
            return current_value if current_value > 0 else 1.0

    def _normalize_value(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize a value to the range [0, 100]"""
        try:
            normalized = ((value - min_val) / (max_val - min_val)) * 100
            return float(np.clip(normalized, 0, 100))
        except:
            return 50.0

    def _compute_weighted_score: No neutral fallback (50.0) found
- ⚠️  _calculate_volume_trend(self, trades_data: pd.DataFrame) -> float:
        """Calculate volume trend score."""
        try:
            if isinstance(trades_data, list):
                trades_df = pd.DataFrame(trades_data)
            else:
                trades_df = trades_data.copy()

            if trades_df.empty:
                return 50.0

            # Convert volume to numeric if needed
            if 'amount' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['amount'], errors='coerce')
            elif 'volume' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['volume'], errors='coerce')
            else:
                return 50.0

            # Calculate volume trend using simple moving averages
            short_ma = talib.SMA(trades_df['volume'], timeperiod=5)
            long_ma = trades_talib.SMA(df['volume'], timeperiod=20)

            if short_ma.empty or long_ma.empty:
                return 50.0

            # Calculate trend strength
            trend = (short_ma.iloc[-1] / long_ma.iloc[-1] - 1) * 100
            
            # Normalize to 0-100 scale
            score = self._normalize_value(trend, -50, 50)
            return score

        except Exception as e:
            self.logger.error(f"Error calculating volume trend: {str(e)}")
            return 50.0

    def _calculate_volume_volatility(self, trades_data: pd.DataFrame) -> float:
        """Calculate volume volatility score."""
        try:
            if isinstance(trades_data, list):
                trades_df = pd.DataFrame(trades_data)
            else:
                trades_df = trades_data.copy()

            if trades_df.empty:
                return 50.0

            # Convert volume to numeric if needed
            if 'amount' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['amount'], errors='coerce')
            elif 'volume' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['volume'], errors='coerce')
            else:
                return 50.0

            # Calculate volume volatility using standard deviation
            volatility = trades_df['volume'].std() / trades_df['volume'].mean()
            
            # Normalize to 0-100 scale
            score = self._normalize_value(volatility, 0, 2)
            return score

        except Exception as e:
            self.logger.error(f"Error calculating volume volatility: {str(e)}")
            return 50.0

    def normalize_volume(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize volume values with safety checks."""
        try:
            if pd.isna(value) or pd.isna(min_val) or pd.isna(max_val):
                self.logger.warning("NaN values in normalization, returning neutral value")
                return 50.0
                
            if min_val == max_val:
                # Instead of returning 0, calculate relative to historical average
                historical_avg = self.calculate_historical_average(value)
                normalized = 50.0 * (value / historical_avg) if historical_avg > 0 else 50.0
                return float(np.clip(normalized, 0, 100))
                
            normalized = ((value - min_val) / (max_val - min_val)) * 100
            return float(np.clip(normalized, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error in normalize_volume: {e}")
            return 50.0

    def calculate_historical_average(self, current_value: float) -> float:
        """Calculate historical average for normalization when min equals max."""
        try:
            # Use exponential moving average of recent values
            if not hasattr(self, '_historical_values'):
                self._historical_values = []
            
            self._historical_values.append(current_value)
            if len(self._historical_values) > 100:  # Keep last 100 values
                self._historical_values.pop(0)
                
            if not self._historical_values:
                return current_value
                
            return np.mean(self._historical_values)
            
        except Exception as e:
            self.logger.error(f"Error calculating historical average: {e}")
            return current_value if current_value > 0 else 1.0

    def _normalize_value(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize a value to the range [0, 100]"""
        try:
            normalized = ((value - min_val) / (max_val - min_val)) * 100
            return float(np.clip(normalized, 0, 100))
        except:
            return 50.0

    def _compute_weighted_score: Non-standard score range detected
- ⚠️  _calculate_volume_divergence_bonus(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate volume divergence bonus."""
        try:
            # Ensure required columns exist
            required_cols = ['close']
            if not all(col in df.columns for col in required_cols):
                self.logger.error("Missing required columns for volume divergence calculation")
                return {'strength': 0.0, 'direction': 'neutral'}
            
            # Find volume column with expanded list
            volume_col = None
            for col in ['volume', 'amount', 'size', 'vol', 'quantity']:
                if col in df.columns:
                    volume_col = col
                    break
                
            if not volume_col:
                # Try to check if any column contains volume or size in its name
                volume_cols = [col for col in df.columns if any(term in col.lower() for term in ['volume', 'size', 'amount', 'quantity', 'vol'])]
                if volume_cols:
                    volume_col = volume_cols[0]
                else:
                    self.logger.warning("No volume column found for divergence calculation")
                    return {'strength': 0.0, 'direction': 'neutral'}
            
            # Get parameters directly from self.params which we've properly initialized in __init__
            max_divergence = self.params.get('max_divergence', 0.5)
            min_strength = self.params.get('min_strength', 0.3) 
            
            # Calculate price and volume changes with better error handling
            price_changes = pd.to_numeric(df['close'], errors='coerce').pct_change().fillna(0)
            volume_changes = pd.to_numeric(df[volume_col], errors='coerce').pct_change().fillna(0)
            
            # Get correlation window from params
            corr_window = self.params.get('correlation_window', 14)
            
            # Ensure window is reasonable
            if corr_window < 2:
                self.logger.warning(f"Correlation window too small: {corr_window}, using default 14")
                corr_window = 14
            elif corr_window > len(df) // 2:
                self.logger.warning(f"Correlation window too large: {corr_window}, using len(df)/2")
                corr_window = len(df) // 2
            
            # Calculate rolling correlations with validated window and error handling
            try:
                correlation = price_changes.rolling(window=corr_window).corr(volume_changes)
                
                # Debug: Check correlation structure
                self.logger.debug(f"Correlation type: {type(correlation)}")
                self.logger.debug(f"Correlation shape: {correlation.shape if hasattr(correlation, 'shape') else 'No shape'}")
                
                # Handle NaN in correlation - fix potential DataFrame ambiguity
                if hasattr(correlation, 'isna'):
                    if correlation.isna().all():
                        self.logger.warning("All correlation values are NaN, using neutral direction")
                        return {'strength': 0.0, 'direction': 'neutral'}
                else:
                    self.logger.warning("Correlation object has no isna method, using neutral direction")
                    return {'strength': 0.0, 'direction': 'neutral'}
                
                # Fill NaN values with 0 (neutral correlation)
                correlation = correlation.fillna(0)
                
                # Calculate divergence score
                recent_correlation = correlation.iloc[-1]
                historical_correlation = correlation.mean()
                
                divergence = abs(recent_correlation - historical_correlation)
                
                # Normalize divergence score
                normalized_score = min: No neutral fallback (50.0) found
- ⚠️  _calculate_vwap_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_vwap_score: Non-standard score range detected
- ⚠️  _calculate_volume_profile(self, data: Union[pd.DataFrame, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate volume profile metrics including Point of Control and Value Area.
        
        This method analyzes price and volume data to identify key volume-based price levels:
        - Point of Control (POC): The price level with the highest trading volume
        - Value Area High (VAH): Upper boundary containing specified % of volume
        - Value Area Low (VAL): Lower boundary containing specified % of volume
        
        Args:
            data: OHLCV data as DataFrame or dictionary with nested structure
            
        Returns:
            Dict containing:
                - poc: Point of Control price
                - va_high: Value Area High price
                - va_low: Value Area Low price
                - score: Volume profile score (0-100) based on price position
        """
        try:
            self.logger.debug("Calculating volume profile metrics")
            
            # Convert dictionary to DataFrame if needed
            if isinstance(data, dict):
                if 'data' in data:
                    df = pd.DataFrame(data['data'])
                    self.logger.debug(f"Extracted DataFrame from 'data' key, shape: {df.shape}")
                else:
                    df = pd.DataFrame(data)
                    self.logger.debug(f"Converted dict to DataFrame, shape: {df.shape}")
            elif isinstance(data, pd.DataFrame):
                df = data.copy()
                self.logger.debug(f"Using provided DataFrame, shape: {df.shape}")
            else:
                self.logger.error(f"Invalid data type for volume profile: {type(data)}")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            if df.empty or len(df) == 0:
                self.logger.warning("Empty DataFrame provided for volume profile calculation")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            # Ensure required columns exist
            required_cols = ['close', 'volume']
            if not all(col in df.columns for col in required_cols):
                missing = [col for col in required_cols if col not in df.columns]
                self.logger.error(f"Missing required columns for volume profile: {missing}")
                self.logger.debug(f"Available columns: {list(df.columns)}")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            # Calculate price levels with adaptive bin size based on data volatility
            price_min = df['close'].min()
            price_max = df['close'].max()
            price_range = price_max - price_min
            price_std = df['close'].std()
            
            # Determine optimal number of bins (more bins for higher volatility)
            volume_profile_bins = getattr(self, 'volume_profile_bins', 100)
            adaptive_bins = max(20, min(volume_profile_bins, 
                                       int(price_range / (price_std * 0.1))))
            self.logger.debug(f"Using {adaptive_bins} bins for volume profile")
            
            bins = np.linspace(price_min, price_max, num=adaptive_bins)
            
            # Create volume profile
            df['price_level'] = pd.cut(df['close'], bins=bins, labels=False)
            # Map labels back to price points for easier interpretation
            price_points = (bins[:-1] + bins[1:]) / 2
            volume_profile = df.groupby('price_level')['volume'].sum()
            volume_profile.index = price_points[volume_profile.index]
            
            # Find Point of Control (POC)
            if volume_profile.empty:
                self.logger.warning("Empty volume profile, returning default values")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            poc = float(volume_profile.idxmax())
            
            # Calculate Value Area (70% of total volume)
            total_volume = volume_profile.sum()
            value_area_volume = getattr(self, 'value_area_volume', 0.7)
            target_volume = total_volume * value_area_volume
            sorted_profile = volume_profile.sort_values(ascending=False)
            cumsum = sorted_profile.cumsum()
            value_area = sorted_profile[cumsum <= target_volume]
            
            if value_area.empty:
                self.logger.warning("Empty value area, using fallback calculation")
                # Fallback to simple percentage around POC
                value_area_range = price_range * 0.2
                va_high = poc + value_area_range/2
                va_low = poc - value_area_range/2
            else:
                va_high = float(max(value_area.index))
                va_low = float(min(value_area.index))
            
            # Calculate score based on price position relative to value area
            current_price = float(df['close'].iloc[-1])
            
            self.logger.debug(f"Volume Profile Results:")
            self.logger.debug(f"- Current Price: {current_price:.2f}")
            self.logger.debug(f"- POC: {poc:.2f}")
            self.logger.debug(f"- Value Area: {va_low:.2f} - {va_high:.2f}")
            
            # Score calculation based on price position
            if current_price < va_low:
                # Below value area - bearish bias
                distance_ratio = (current_price - va_low) / (va_low - price_min) if va_low != price_min else -1
                score = 30 * (1 + distance_ratio)
                position = "below_va"
            elif current_price > va_high:
                # Above value area - bullish bias
                distance_ratio = (current_price - va_high) / (price_max - va_high) if price_max != va_high else 1
                score = 70 + 30 * (1 - distance_ratio)
                position = "above_va"
            else:
                # Inside value area - score based on position relative to POC
                position_ratio = (current_price - va_low) / (va_high - va_low) if va_high != va_low else 0.5
                # Use tanh for smooth transition around POC
                score = 50 * (1 + np.tanh((position_ratio - 0.5) * 2))
                position = "inside_va"
                
            final_score = float: No neutral fallback (50.0) found
- ⚠️  _calculate_adl_score: No neutral fallback (50.0) found
- ⚠️  _calculate_adl_score: Non-standard score range detected
- ⚠️  _calculate_cmf_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_cmf_score: Non-standard score range detected
- ⚠️  _calculate_obv_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_obv_score: No neutral fallback (50.0) found
- ⚠️  _calculate_obv_score: Non-standard score range detected

**Scoring Methods:**
- `_calculate_confidence(self, market_data: Dict[str, Any]) -> float:
        """Calculate confidence in volume analysis."""
        try:
            primary_tf = list(market_data['ohlcv'].keys())[0]
            df = market_data['ohlcv'][primary_tf]
            
            # Calculate confidence based on data quality
            min_required_points = 20
            if len(df) < min_required_points:
                return 0.5
                
            # Check for consistent volume data
            volume_zeros = (df['volume'] == 0).sum()
            if volume_zeros / len(df) > 0.1:  # More than 10% zeros
                return 0.7
                
            return 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5

    def _calculate_volume_sma_score`: ✅ OK
- `_calculate_relative_volume(self, market_data: Dict[str, Any]) -> float:
        """
        Calculate relative volume score from market data.
        
        Supports both traditional RVOL and price-aware RVOL based on configuration.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            float: Relative volume score (0-100) where 0 is very bearish and 100 is very bullish
        """
        try:
            # Check if price-aware mode is enabled
            price_aware_mode = self.config.get('price_aware_mode', False)
            
            if price_aware_mode:
                self.logger.debug("Using price-aware RVOL calculation")
                return self._calculate_price_aware_relative_volume(market_data)
            
            # Traditional RVOL calculation
            self.logger.debug("Using traditional RVOL calculation")
            
            # Extract OHLCV data
            if 'ohlcv' not in market_data or not market_data['ohlcv'] or 'base' not in market_data['ohlcv']:
                self.logger.warning("No OHLCV data found for relative volume calculation")
                return 50.0
                
            df = market_data['ohlcv']['base']
            
            # Get period from config or use default
            period = self.config.get('relative_volume_period', 20)
            
            # Calculate relative volume using the existing method
            rel_vol_series = self.calculate_relative_volume(df, period=period)
            
            # Return the latest value or default to 50.0
            if rel_vol_series.empty:
                return 50.0
            
            # Get the raw RVOL value
            rel_vol = float(rel_vol_series.iloc[-1])
            
            # Normalize RVOL to 0-100 score where 0 is very bearish and 100 is very bullish
            # RVOL < 1: Below average volume (bearish)
            # RVOL > 1: Above average volume (bullish)
            
            # Define the boundaries for normalization
            # RVOL ranges typically from 0.1 to 3.0 in normal market conditions
            min_rvol = self.config.get('min_rvol', 0.1)
            max_rvol = self.config.get('max_rvol', 3.0)
            
            # For bearish signal (RVOL < 1), map 0.1 to 0 and 1.0 to 50
            if rel_vol < 1.0:
                # Normalize to 0-50 range
                score = 50 * (rel_vol - min_rvol) / (1.0 - min_rvol)
            # For bullish signal (RVOL >= 1), map 1.0 to 50 and 3.0 to 100
            else:
                # Normalize to 50-100 range
                score = 50 + 50 * (rel_vol - 1.0) / (max_rvol - 1.0)
            
            # Ensure the score is within 0-100 range
            score = np.clip(score, 0, 100)
            
            self.logger.debug(f"Traditional RVOL: {rel_vol:.2f}, Normalized score: {score:.2f}")
            
            return float(score)
            
        except Exception as e:
            self.logger.error(f"Error calculating relative volume score: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return 50.0

    def _calculate_base_volume_score`: ✅ OK
- `_calculate_volume_trend(self, trades_data: pd.DataFrame) -> float:
        """Calculate volume trend score."""
        try:
            if isinstance(trades_data, list):
                trades_df = pd.DataFrame(trades_data)
            else:
                trades_df = trades_data.copy()

            if trades_df.empty:
                return 50.0

            # Convert volume to numeric if needed
            if 'amount' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['amount'], errors='coerce')
            elif 'volume' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['volume'], errors='coerce')
            else:
                return 50.0

            # Calculate volume trend using simple moving averages
            short_ma = talib.SMA(trades_df['volume'], timeperiod=5)
            long_ma = trades_talib.SMA(df['volume'], timeperiod=20)

            if short_ma.empty or long_ma.empty:
                return 50.0

            # Calculate trend strength
            trend = (short_ma.iloc[-1] / long_ma.iloc[-1] - 1) * 100
            
            # Normalize to 0-100 scale
            score = self._normalize_value(trend, -50, 50)
            return score

        except Exception as e:
            self.logger.error(f"Error calculating volume trend: {str(e)}")
            return 50.0

    def _calculate_volume_volatility(self, trades_data: pd.DataFrame) -> float:
        """Calculate volume volatility score."""
        try:
            if isinstance(trades_data, list):
                trades_df = pd.DataFrame(trades_data)
            else:
                trades_df = trades_data.copy()

            if trades_df.empty:
                return 50.0

            # Convert volume to numeric if needed
            if 'amount' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['amount'], errors='coerce')
            elif 'volume' in trades_df.columns:
                trades_df['volume'] = pd.to_numeric(trades_df['volume'], errors='coerce')
            else:
                return 50.0

            # Calculate volume volatility using standard deviation
            volatility = trades_df['volume'].std() / trades_df['volume'].mean()
            
            # Normalize to 0-100 scale
            score = self._normalize_value(volatility, 0, 2)
            return score

        except Exception as e:
            self.logger.error(f"Error calculating volume volatility: {str(e)}")
            return 50.0

    def normalize_volume(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize volume values with safety checks."""
        try:
            if pd.isna(value) or pd.isna(min_val) or pd.isna(max_val):
                self.logger.warning("NaN values in normalization, returning neutral value")
                return 50.0
                
            if min_val == max_val:
                # Instead of returning 0, calculate relative to historical average
                historical_avg = self.calculate_historical_average(value)
                normalized = 50.0 * (value / historical_avg) if historical_avg > 0 else 50.0
                return float(np.clip(normalized, 0, 100))
                
            normalized = ((value - min_val) / (max_val - min_val)) * 100
            return float(np.clip(normalized, 0, 100))
            
        except Exception as e:
            self.logger.error(f"Error in normalize_volume: {e}")
            return 50.0

    def calculate_historical_average(self, current_value: float) -> float:
        """Calculate historical average for normalization when min equals max."""
        try:
            # Use exponential moving average of recent values
            if not hasattr(self, '_historical_values'):
                self._historical_values = []
            
            self._historical_values.append(current_value)
            if len(self._historical_values) > 100:  # Keep last 100 values
                self._historical_values.pop(0)
                
            if not self._historical_values:
                return current_value
                
            return np.mean(self._historical_values)
            
        except Exception as e:
            self.logger.error(f"Error calculating historical average: {e}")
            return current_value if current_value > 0 else 1.0

    def _normalize_value(self, value: float, min_val: float, max_val: float) -> float:
        """Normalize a value to the range [0, 100]"""
        try:
            normalized = ((value - min_val) / (max_val - min_val)) * 100
            return float(np.clip(normalized, 0, 100))
        except:
            return 50.0

    def _compute_weighted_score`: ❌ 3 issues
- `_calculate_volume_divergence_bonus(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate volume divergence bonus."""
        try:
            # Ensure required columns exist
            required_cols = ['close']
            if not all(col in df.columns for col in required_cols):
                self.logger.error("Missing required columns for volume divergence calculation")
                return {'strength': 0.0, 'direction': 'neutral'}
            
            # Find volume column with expanded list
            volume_col = None
            for col in ['volume', 'amount', 'size', 'vol', 'quantity']:
                if col in df.columns:
                    volume_col = col
                    break
                
            if not volume_col:
                # Try to check if any column contains volume or size in its name
                volume_cols = [col for col in df.columns if any(term in col.lower() for term in ['volume', 'size', 'amount', 'quantity', 'vol'])]
                if volume_cols:
                    volume_col = volume_cols[0]
                else:
                    self.logger.warning("No volume column found for divergence calculation")
                    return {'strength': 0.0, 'direction': 'neutral'}
            
            # Get parameters directly from self.params which we've properly initialized in __init__
            max_divergence = self.params.get('max_divergence', 0.5)
            min_strength = self.params.get('min_strength', 0.3) 
            
            # Calculate price and volume changes with better error handling
            price_changes = pd.to_numeric(df['close'], errors='coerce').pct_change().fillna(0)
            volume_changes = pd.to_numeric(df[volume_col], errors='coerce').pct_change().fillna(0)
            
            # Get correlation window from params
            corr_window = self.params.get('correlation_window', 14)
            
            # Ensure window is reasonable
            if corr_window < 2:
                self.logger.warning(f"Correlation window too small: {corr_window}, using default 14")
                corr_window = 14
            elif corr_window > len(df) // 2:
                self.logger.warning(f"Correlation window too large: {corr_window}, using len(df)/2")
                corr_window = len(df) // 2
            
            # Calculate rolling correlations with validated window and error handling
            try:
                correlation = price_changes.rolling(window=corr_window).corr(volume_changes)
                
                # Debug: Check correlation structure
                self.logger.debug(f"Correlation type: {type(correlation)}")
                self.logger.debug(f"Correlation shape: {correlation.shape if hasattr(correlation, 'shape') else 'No shape'}")
                
                # Handle NaN in correlation - fix potential DataFrame ambiguity
                if hasattr(correlation, 'isna'):
                    if correlation.isna().all():
                        self.logger.warning("All correlation values are NaN, using neutral direction")
                        return {'strength': 0.0, 'direction': 'neutral'}
                else:
                    self.logger.warning("Correlation object has no isna method, using neutral direction")
                    return {'strength': 0.0, 'direction': 'neutral'}
                
                # Fill NaN values with 0 (neutral correlation)
                correlation = correlation.fillna(0)
                
                # Calculate divergence score
                recent_correlation = correlation.iloc[-1]
                historical_correlation = correlation.mean()
                
                divergence = abs(recent_correlation - historical_correlation)
                
                # Normalize divergence score
                normalized_score = min`: ❌ 1 issues
- `_calculate_vwap_score`: ❌ 2 issues
- `_calculate_single_vwap_score`: ✅ OK
- `_calculate_volume_profile(self, data: Union[pd.DataFrame, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate volume profile metrics including Point of Control and Value Area.
        
        This method analyzes price and volume data to identify key volume-based price levels:
        - Point of Control (POC): The price level with the highest trading volume
        - Value Area High (VAH): Upper boundary containing specified % of volume
        - Value Area Low (VAL): Lower boundary containing specified % of volume
        
        Args:
            data: OHLCV data as DataFrame or dictionary with nested structure
            
        Returns:
            Dict containing:
                - poc: Point of Control price
                - va_high: Value Area High price
                - va_low: Value Area Low price
                - score: Volume profile score (0-100) based on price position
        """
        try:
            self.logger.debug("Calculating volume profile metrics")
            
            # Convert dictionary to DataFrame if needed
            if isinstance(data, dict):
                if 'data' in data:
                    df = pd.DataFrame(data['data'])
                    self.logger.debug(f"Extracted DataFrame from 'data' key, shape: {df.shape}")
                else:
                    df = pd.DataFrame(data)
                    self.logger.debug(f"Converted dict to DataFrame, shape: {df.shape}")
            elif isinstance(data, pd.DataFrame):
                df = data.copy()
                self.logger.debug(f"Using provided DataFrame, shape: {df.shape}")
            else:
                self.logger.error(f"Invalid data type for volume profile: {type(data)}")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            if df.empty or len(df) == 0:
                self.logger.warning("Empty DataFrame provided for volume profile calculation")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            # Ensure required columns exist
            required_cols = ['close', 'volume']
            if not all(col in df.columns for col in required_cols):
                missing = [col for col in required_cols if col not in df.columns]
                self.logger.error(f"Missing required columns for volume profile: {missing}")
                self.logger.debug(f"Available columns: {list(df.columns)}")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            # Calculate price levels with adaptive bin size based on data volatility
            price_min = df['close'].min()
            price_max = df['close'].max()
            price_range = price_max - price_min
            price_std = df['close'].std()
            
            # Determine optimal number of bins (more bins for higher volatility)
            volume_profile_bins = getattr(self, 'volume_profile_bins', 100)
            adaptive_bins = max(20, min(volume_profile_bins, 
                                       int(price_range / (price_std * 0.1))))
            self.logger.debug(f"Using {adaptive_bins} bins for volume profile")
            
            bins = np.linspace(price_min, price_max, num=adaptive_bins)
            
            # Create volume profile
            df['price_level'] = pd.cut(df['close'], bins=bins, labels=False)
            # Map labels back to price points for easier interpretation
            price_points = (bins[:-1] + bins[1:]) / 2
            volume_profile = df.groupby('price_level')['volume'].sum()
            volume_profile.index = price_points[volume_profile.index]
            
            # Find Point of Control (POC)
            if volume_profile.empty:
                self.logger.warning("Empty volume profile, returning default values")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            poc = float(volume_profile.idxmax())
            
            # Calculate Value Area (70% of total volume)
            total_volume = volume_profile.sum()
            value_area_volume = getattr(self, 'value_area_volume', 0.7)
            target_volume = total_volume * value_area_volume
            sorted_profile = volume_profile.sort_values(ascending=False)
            cumsum = sorted_profile.cumsum()
            value_area = sorted_profile[cumsum <= target_volume]
            
            if value_area.empty:
                self.logger.warning("Empty value area, using fallback calculation")
                # Fallback to simple percentage around POC
                value_area_range = price_range * 0.2
                va_high = poc + value_area_range/2
                va_low = poc - value_area_range/2
            else:
                va_high = float(max(value_area.index))
                va_low = float(min(value_area.index))
            
            # Calculate score based on price position relative to value area
            current_price = float(df['close'].iloc[-1])
            
            self.logger.debug(f"Volume Profile Results:")
            self.logger.debug(f"- Current Price: {current_price:.2f}")
            self.logger.debug(f"- POC: {poc:.2f}")
            self.logger.debug(f"- Value Area: {va_low:.2f} - {va_high:.2f}")
            
            # Score calculation based on price position
            if current_price < va_low:
                # Below value area - bearish bias
                distance_ratio = (current_price - va_low) / (va_low - price_min) if va_low != price_min else -1
                score = 30 * (1 + distance_ratio)
                position = "below_va"
            elif current_price > va_high:
                # Above value area - bullish bias
                distance_ratio = (current_price - va_high) / (price_max - va_high) if price_max != va_high else 1
                score = 70 + 30 * (1 - distance_ratio)
                position = "above_va"
            else:
                # Inside value area - score based on position relative to POC
                position_ratio = (current_price - va_low) / (va_high - va_low) if va_high != va_low else 0.5
                # Use tanh for smooth transition around POC
                score = 50 * (1 + np.tanh((position_ratio - 0.5) * 2))
                position = "inside_va"
                
            final_score = float`: ❌ 1 issues
- `_calculate_adl_score`: ❌ 2 issues
- `_calculate_cmf_score`: ❌ 2 issues
- `_calculate_obv_score`: ❌ 3 issues


### sentiment_indicators.py
**Scoring Methods Found:** 7
**Issues Found:** 9

**Issues:**
- ⚠️  _calculate_funding_score: Non-standard score range detected
- ⚠️  _calculate_sync(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate sentiment indicators synchronously.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Dictionary containing sentiment scores, components, and interpretation
        """
        try:
            start_time = time.time()
            self.logger.debug(f"Calculating sentiment with input keys: {list(market_data.keys())}")
            
            # Process sentiment data from market data
            processed_data = self._process_sentiment_data(market_data)
            self.logger.debug(f"Processed sentiment data: {processed_data}")
            
            # Initialize component scores dictionary
            components = {}
            
            # Calculate funding rate score
            try:
                self.logger.debug("Calculating funding rate score...")
                funding_score = self._calculate_funding_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_sync(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate sentiment indicators synchronously.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Dictionary containing sentiment scores, components, and interpretation
        """
        try:
            start_time = time.time()
            self.logger.debug(f"Calculating sentiment with input keys: {list(market_data.keys())}")
            
            # Process sentiment data from market data
            processed_data = self._process_sentiment_data(market_data)
            self.logger.debug(f"Processed sentiment data: {processed_data}")
            
            # Initialize component scores dictionary
            components = {}
            
            # Calculate funding rate score
            try:
                self.logger.debug("Calculating funding rate score...")
                funding_score = self._calculate_funding_score: No neutral fallback (50.0) found
- ⚠️  _calculate_sync(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate sentiment indicators synchronously.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Dictionary containing sentiment scores, components, and interpretation
        """
        try:
            start_time = time.time()
            self.logger.debug(f"Calculating sentiment with input keys: {list(market_data.keys())}")
            
            # Process sentiment data from market data
            processed_data = self._process_sentiment_data(market_data)
            self.logger.debug(f"Processed sentiment data: {processed_data}")
            
            # Initialize component scores dictionary
            components = {}
            
            # Calculate funding rate score
            try:
                self.logger.debug("Calculating funding rate score...")
                funding_score = self._calculate_funding_score: Non-standard score range detected
- ⚠️  _calculate_enhanced_metrics(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate enhanced metrics for sentiment analysis."""
        try:
            enhanced_metrics = {}
            
            # Extract OHLCV data if available
            ohlcv_data = market_data.get('ohlcv', {})
            
            # Calculate price change over last 24h
            if ohlcv_data and 'base' in ohlcv_data:
                df = ohlcv_data['base']
                if isinstance(df, pd.DataFrame) and len(df) > 24:
                    # Calculate price change
                    current_price = df['close'].iloc[-1]
                    price_24h_ago = df['close'].iloc[-25]  # 24 periods ago for 1-min data
                    
                    if price_24h_ago > 0:
                        price_change_pct = ((current_price - price_24h_ago) / price_24h_ago) * 100
                        enhanced_metrics['price_change_24h'] = round(price_change_pct, 2)
                    
                    # Calculate volatility (standard deviation of percent changes)
                    if len(df) > 30:
                        pct_changes = df['close'].pct_change().dropna()
                        volatility = pct_changes.std() * 100  # Convert to percentage
                        enhanced_metrics['volatility_24h'] = round(volatility, 2)
            
            # Determine market trend
            if 'price_change_24h' in enhanced_metrics:
                price_change = enhanced_metrics['price_change_24h']
                if price_change > 3:
                    enhanced_metrics['market_trend'] = 'bullish'
                elif price_change < -3:
                    enhanced_metrics['market_trend'] = 'bearish'
            else:
                    enhanced_metrics['market_trend'] = 'neutral'
            
            # Add fear & greed index if available from market_mood
            sentiment_data = market_data.get('sentiment', {})
            market_mood = sentiment_data.get('market_mood', {})
            
            if isinstance(market_mood, dict) and 'fear_and_greed' in market_mood:
                enhanced_metrics['fear_greed_index'] = market_mood['fear_and_greed']
            
            return enhanced_metrics
            
        except Exception as e:
            self.logger.warning(f"Error calculating enhanced metrics: {str(e)}")
            return {}

    def _calculate_liquidation_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_enhanced_metrics(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate enhanced metrics for sentiment analysis."""
        try:
            enhanced_metrics = {}
            
            # Extract OHLCV data if available
            ohlcv_data = market_data.get('ohlcv', {})
            
            # Calculate price change over last 24h
            if ohlcv_data and 'base' in ohlcv_data:
                df = ohlcv_data['base']
                if isinstance(df, pd.DataFrame) and len(df) > 24:
                    # Calculate price change
                    current_price = df['close'].iloc[-1]
                    price_24h_ago = df['close'].iloc[-25]  # 24 periods ago for 1-min data
                    
                    if price_24h_ago > 0:
                        price_change_pct = ((current_price - price_24h_ago) / price_24h_ago) * 100
                        enhanced_metrics['price_change_24h'] = round(price_change_pct, 2)
                    
                    # Calculate volatility (standard deviation of percent changes)
                    if len(df) > 30:
                        pct_changes = df['close'].pct_change().dropna()
                        volatility = pct_changes.std() * 100  # Convert to percentage
                        enhanced_metrics['volatility_24h'] = round(volatility, 2)
            
            # Determine market trend
            if 'price_change_24h' in enhanced_metrics:
                price_change = enhanced_metrics['price_change_24h']
                if price_change > 3:
                    enhanced_metrics['market_trend'] = 'bullish'
                elif price_change < -3:
                    enhanced_metrics['market_trend'] = 'bearish'
            else:
                    enhanced_metrics['market_trend'] = 'neutral'
            
            # Add fear & greed index if available from market_mood
            sentiment_data = market_data.get('sentiment', {})
            market_mood = sentiment_data.get('market_mood', {})
            
            if isinstance(market_mood, dict) and 'fear_and_greed' in market_mood:
                enhanced_metrics['fear_greed_index'] = market_mood['fear_and_greed']
            
            return enhanced_metrics
            
        except Exception as e:
            self.logger.warning(f"Error calculating enhanced metrics: {str(e)}")
            return {}

    def _calculate_liquidation_score: No neutral fallback (50.0) found
- ⚠️  _calculate_enhanced_metrics(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate enhanced metrics for sentiment analysis."""
        try:
            enhanced_metrics = {}
            
            # Extract OHLCV data if available
            ohlcv_data = market_data.get('ohlcv', {})
            
            # Calculate price change over last 24h
            if ohlcv_data and 'base' in ohlcv_data:
                df = ohlcv_data['base']
                if isinstance(df, pd.DataFrame) and len(df) > 24:
                    # Calculate price change
                    current_price = df['close'].iloc[-1]
                    price_24h_ago = df['close'].iloc[-25]  # 24 periods ago for 1-min data
                    
                    if price_24h_ago > 0:
                        price_change_pct = ((current_price - price_24h_ago) / price_24h_ago) * 100
                        enhanced_metrics['price_change_24h'] = round(price_change_pct, 2)
                    
                    # Calculate volatility (standard deviation of percent changes)
                    if len(df) > 30:
                        pct_changes = df['close'].pct_change().dropna()
                        volatility = pct_changes.std() * 100  # Convert to percentage
                        enhanced_metrics['volatility_24h'] = round(volatility, 2)
            
            # Determine market trend
            if 'price_change_24h' in enhanced_metrics:
                price_change = enhanced_metrics['price_change_24h']
                if price_change > 3:
                    enhanced_metrics['market_trend'] = 'bullish'
                elif price_change < -3:
                    enhanced_metrics['market_trend'] = 'bearish'
            else:
                    enhanced_metrics['market_trend'] = 'neutral'
            
            # Add fear & greed index if available from market_mood
            sentiment_data = market_data.get('sentiment', {})
            market_mood = sentiment_data.get('market_mood', {})
            
            if isinstance(market_mood, dict) and 'fear_and_greed' in market_mood:
                enhanced_metrics['fear_greed_index'] = market_mood['fear_and_greed']
            
            return enhanced_metrics
            
        except Exception as e:
            self.logger.warning(f"Error calculating enhanced metrics: {str(e)}")
            return {}

    def _calculate_liquidation_score: Non-standard score range detected
- ⚠️  _calculate_lsr_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_lsr_score: Non-standard score range detected

**Scoring Methods:**
- `_calculate_funding_score`: ❌ 1 issues
- `_calculate_risk_score`: ✅ OK
- `_calculate_volatility_score`: ✅ OK
- `_calculate_sync(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate sentiment indicators synchronously.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Dictionary containing sentiment scores, components, and interpretation
        """
        try:
            start_time = time.time()
            self.logger.debug(f"Calculating sentiment with input keys: {list(market_data.keys())}")
            
            # Process sentiment data from market data
            processed_data = self._process_sentiment_data(market_data)
            self.logger.debug(f"Processed sentiment data: {processed_data}")
            
            # Initialize component scores dictionary
            components = {}
            
            # Calculate funding rate score
            try:
                self.logger.debug("Calculating funding rate score...")
                funding_score = self._calculate_funding_score`: ❌ 3 issues
- `_calculate_enhanced_metrics(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate enhanced metrics for sentiment analysis."""
        try:
            enhanced_metrics = {}
            
            # Extract OHLCV data if available
            ohlcv_data = market_data.get('ohlcv', {})
            
            # Calculate price change over last 24h
            if ohlcv_data and 'base' in ohlcv_data:
                df = ohlcv_data['base']
                if isinstance(df, pd.DataFrame) and len(df) > 24:
                    # Calculate price change
                    current_price = df['close'].iloc[-1]
                    price_24h_ago = df['close'].iloc[-25]  # 24 periods ago for 1-min data
                    
                    if price_24h_ago > 0:
                        price_change_pct = ((current_price - price_24h_ago) / price_24h_ago) * 100
                        enhanced_metrics['price_change_24h'] = round(price_change_pct, 2)
                    
                    # Calculate volatility (standard deviation of percent changes)
                    if len(df) > 30:
                        pct_changes = df['close'].pct_change().dropna()
                        volatility = pct_changes.std() * 100  # Convert to percentage
                        enhanced_metrics['volatility_24h'] = round(volatility, 2)
            
            # Determine market trend
            if 'price_change_24h' in enhanced_metrics:
                price_change = enhanced_metrics['price_change_24h']
                if price_change > 3:
                    enhanced_metrics['market_trend'] = 'bullish'
                elif price_change < -3:
                    enhanced_metrics['market_trend'] = 'bearish'
            else:
                    enhanced_metrics['market_trend'] = 'neutral'
            
            # Add fear & greed index if available from market_mood
            sentiment_data = market_data.get('sentiment', {})
            market_mood = sentiment_data.get('market_mood', {})
            
            if isinstance(market_mood, dict) and 'fear_and_greed' in market_mood:
                enhanced_metrics['fear_greed_index'] = market_mood['fear_and_greed']
            
            return enhanced_metrics
            
        except Exception as e:
            self.logger.warning(f"Error calculating enhanced metrics: {str(e)}")
            return {}

    def _calculate_liquidation_score`: ❌ 3 issues
- `_calculate_lsr_score`: ❌ 2 issues
- `_calculate_open_interest_score`: ✅ OK


### orderbook_indicators.py
**Scoring Methods Found:** 7
**Issues Found:** 7

**Issues:**
- ⚠️  _calculate_orderbook_imbalance(self, market_data: Dict[str, Any]) -> float:
        """Calculate enhanced orderbook imbalance using volume and price sensitivity.
        
        Args:
            market_data: Dictionary containing market data including orderbook
            
        Returns:
            float: Normalized imbalance score (0-100) where:
                  0 = extremely bearish (ask-heavy)
                  50 = neutral
                  100 = extremely bullish (bid-heavy)
        """
        try:
            self.logger.debug("\n=== ORDERBOOK IMBALANCE CALCULATION DEBUG ===")
            
            # Extract orderbook data from market_data
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            self.logger.debug(f"Raw orderbook data - Bids: {len(bids)}, Asks: {len(asks)}")
            
            if not bids or not asks:
                self.logger.warning("Empty orderbook detected")
                return 50.0  # Neutral imbalance
            
            # Convert to numpy arrays if they aren't already
            if not isinstance(bids, np.ndarray):
                bids = np.array(bids, dtype=float)
            if not isinstance(asks, np.ndarray):
                asks = np.array(asks, dtype=float)
                
            self.logger.debug(f"Converted arrays - Bids shape: {bids.shape}, Asks shape: {asks.shape}")
                
            # 1. Dynamic depth and mid-price calculation
            levels = min(10, len(bids), len(asks))  # Use up to 10 levels
            self.logger.debug(f"Using {levels} levels for analysis")
            
            # Ensure values are floats before calculation
            try:
                bid_price = float(bids[0, 0])
                ask_price = float(asks[0, 0])
                mid_price = (bid_price + ask_price) / 2
                self.logger.debug(f"Price levels - Best bid: {bid_price:.4f}, Best ask: {ask_price:.4f}, Mid: {mid_price:.4f}")
            except (ValueError, TypeError, IndexError) as e:
                self.logger.error(f"Error converting price to float: {str(e)}")
                return 50.0  # Return neutral score on error
            
            # Calculate spread and total depth with error handling
            try:
                spread = (asks[0, 0] - bids[0, 0]) / mid_price
                total_depth = np.sum(bids[:levels, 1]) + np.sum(asks[:levels, 1])
                self.logger.debug(f"Market metrics - Spread: {spread:.6f} ({spread*10000:.2f} bps), Total depth: {total_depth:.2f}")
            except IndexError:
                self.logger.error("Invalid price/size data in orderbook")
                return 50.0
            
            # Update historical metrics
            self._update_historical_metrics(spread, total_depth)
            
            # Normalize spread using historical data with safety check
            normalized_spread = min(1.0, spread / (self.typical_spread + 1e-10)) if hasattr(self, 'typical_spread') else 0.5
            self.logger.debug(f"Normalized spread: {normalized_spread:.4f} (typical: {getattr(self, 'typical_spread', 'N/A')})")
            
            # 2. Volume-weighted imbalance with normalized weights
            level_weights = np.exp(-np.arange(levels) * 0.3)  # Slower decay
            level_weights /= np.sum(level_weights)  # Ensure weights sum to 1
            
            self.logger.debug("Level weights (exponential decay):")
            for i, weight in enumerate(level_weights):
                self.logger.debug(f"  Level {i+1}: {weight:.4f} ({weight*100:.1f}%)")
            
            try:
                weighted_bid_volume = np.sum(bids[:levels, 1] * level_weights)
                weighted_ask_volume = np.sum(asks[:levels, 1] * level_weights)
                total_weighted_volume = weighted_bid_volume + weighted_ask_volume
                
                self.logger.debug(f"Volume-weighted analysis:")
                self.logger.debug(f"  Weighted bid volume: {weighted_bid_volume:.2f}")
                self.logger.debug(f"  Weighted ask volume: {weighted_ask_volume:.2f}")
                self.logger.debug(f"  Total weighted volume: {total_weighted_volume:.2f}")
                
            except (IndexError, ValueError) as e:
                self.logger.error(f"Error calculating weighted volumes: {str(e)}")
                return 50.0
            
            # Check for meaningful volume with logging
            if total_weighted_volume < 1e-6:
                self.logger.warning("Negligible total weighted volume detected")
                return 50.0  # Neutral if no meaningful volume
                
            weighted_imbalance = (weighted_bid_volume - weighted_ask_volume) / total_weighted_volume
            self.logger.debug(f"Weighted imbalance: {weighted_imbalance:.6f}")
            
            # 3. Price-sensitive imbalance with dynamic sensitivity
            try:
                bid_distances = np.abs(bids[:levels, 0] - mid_price) / mid_price
                ask_distances = np.abs(asks[:levels, 0] - mid_price) / mid_price
                
                self.logger.debug("Price distance analysis:")
                for i in range(min(5, levels)):
                    self.logger.debug(f"  Level {i+1} - Bid distance: {bid_distances[i]:.6f}, Ask distance: {ask_distances[i]:.6f}")
                    
            except IndexError:
                self.logger.error("Error calculating price distances")
                return 50.0
            
            # Dynamic price sensitivity based on normalized spread
            price_sensitivity = 15 * min(1.5, 1 + normalized_spread)
            self.logger.debug(f"Price sensitivity factor: {price_sensitivity:.2f}")
            
            # Calculate and normalize price weights with epsilon
            bid_weights = np.exp(-bid_distances * price_sensitivity)
            ask_weights = np.exp(-ask_distances * price_sensitivity)
            
            self.logger.debug("Price-based weights (before normalization):")
            for i in range(min(5, levels)):
                self.logger.debug(f"  Level {i+1} - Bid weight: {bid_weights[i]:.4f}, Ask weight: {ask_weights[i]:.4f}")
            
            # Ensure weights sum to 1 even under edge cases
            bid_weights = bid_weights / (np.sum(bid_weights) + 1e-10)
            ask_weights = ask_weights / (np.sum(ask_weights) + 1e-10)
            
            self.logger.debug("Price-based weights (normalized):")
            for i in range(min(5, levels)):
                self.logger.debug(f"  Level {i+1} - Bid weight: {bid_weights[i]:.4f}, Ask weight: {ask_weights[i]:.4f}")
            
            # Calculate price-weighted volumes with error handling
            try:
                price_weighted_bid = np.sum(bids[:levels, 1] * bid_weights)
                price_weighted_ask = np.sum(asks[:levels, 1] * ask_weights)
                total_price_weighted = price_weighted_bid + price_weighted_ask
                
                self.logger.debug(f"Price-weighted analysis:")
                self.logger.debug(f"  Price-weighted bid volume: {price_weighted_bid:.2f}")
                self.logger.debug(f"  Price-weighted ask volume: {price_weighted_ask:.2f}")
                self.logger.debug(f"  Total price-weighted volume: {total_price_weighted:.2f}")
                
            except (IndexError, ValueError) as e:
                self.logger.error(f"Error calculating price-weighted volumes: {str(e)}")
                return 50.0
            
            # Check for meaningful price-weighted volume with logging
            if total_price_weighted < 1e-6:
                self.logger.warning("Negligible price-weighted volume detected")
                price_sensitive_imbalance = 0.0
            else:
                price_sensitive_imbalance = (price_weighted_bid - price_weighted_ask) / total_price_weighted
                
            self.logger.debug(f"Price-sensitive imbalance: {price_sensitive_imbalance:.6f}")
            
            # 4. Combine metrics with dynamic weighting based on normalized spread
            price_weight = min(0.8, 0.5 + normalized_spread)  # Cap at 0.8 for stability
            volume_weight = 1 - price_weight
            
            self.logger.debug(f"Combination weights - Volume: {volume_weight:.3f}, Price: {price_weight:.3f}")
            
            # Use numpy's average for cleaner weighted combination
            final_imbalance = np.average(
                [weighted_imbalance, price_sensitive_imbalance],
                weights=[volume_weight, price_weight]
            )
            
            self.logger.debug(f"Combined imbalance: {final_imbalance:.6f}")
            
            # 5. Apply sigmoid normalization for smoother distribution
            normalized_imbalance = 50 * (1 + np.tanh(2 * final_imbalance))
            self.logger.debug(f"Sigmoid normalized imbalance: {normalized_imbalance:.2f}")
            
            # 6. Dynamic depth confidence calculation using historical depth
            depth_confidence = min(1.0, total_depth / (self.typical_depth + 1e-10)) if hasattr(self, 'typical_depth') else 0.5
            self.logger.debug(f"Depth confidence: {depth_confidence:.3f} (typical depth: {getattr(self, 'typical_depth', 'N/A')})")
            
            # 7. Final score calculation with confidence adjustment
            final_score = 50 + : No neutral fallback (50.0) found
- ⚠️  _calculate_sr_from_orderbook(self, market_data: Dict[str, Any]) -> float:
        """Calculate support/resistance score from orderbook data."""
        try:
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return 50.0
                
            # Group orders by price levels to find clusters
            price_levels = 20  # Number of price levels to analyze
            price_step = 0.002  # 0.2% steps
            
            # Get current price
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid_price = (best_bid + best_ask) / 2
            
            # Create price bins
            min_price = mid_price * (1 - price_levels * price_step / 2)
            max_price = mid_price * (1 + price_levels * price_step / 2)
            price_bins = np.linspace(min_price, max_price, price_levels + 1)
            
            # Initialize volume arrays
            bid_volumes = np.zeros(price_levels)
            ask_volumes = np.zeros(price_levels)
            
            # Distribute bid volumes into bins
            for bid in bids:
                price = float(bid[0])
                volume = float(bid[1])
                
                if price < min_price:
                    continue
                    
                bin_index = min(int((price - min_price) / (max_price - min_price) * price_levels), price_levels - 1)
                if 0 <= bin_index < price_levels:
                    bid_volumes[bin_index] += volume
            
            # Distribute ask volumes into bins
            for ask in asks:
                price = float(ask[0])
                volume = float(ask[1])
                
                if price > max_price:
                    continue
                    
                bin_index = min(int((price - min_price) / (max_price - min_price) * price_levels), price_levels - 1)
                if 0 <= bin_index < price_levels:
                    ask_volumes[bin_index] += volume
            
            # Find support levels (high bid volume)
            support_strength = np.max(bid_volumes) / (np.mean(bid_volumes) + 1e-10)
            
            # Find resistance levels (high ask volume)
            resistance_strength = np.max(ask_volumes) / (np.mean(ask_volumes) + 1e-10)
            
            # Calculate overall S/R strength
            sr_strength = (support_strength + resistance_strength) / 2
            
            # Convert to score (higher strength = higher score)
            # Strength of 1.0 is average (score 50)
            # Strength of 3.0 or more is strong (score 100)
            sr_score = 50 * : No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_sr_from_orderbook(self, market_data: Dict[str, Any]) -> float:
        """Calculate support/resistance score from orderbook data."""
        try:
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return 50.0
                
            # Group orders by price levels to find clusters
            price_levels = 20  # Number of price levels to analyze
            price_step = 0.002  # 0.2% steps
            
            # Get current price
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid_price = (best_bid + best_ask) / 2
            
            # Create price bins
            min_price = mid_price * (1 - price_levels * price_step / 2)
            max_price = mid_price * (1 + price_levels * price_step / 2)
            price_bins = np.linspace(min_price, max_price, price_levels + 1)
            
            # Initialize volume arrays
            bid_volumes = np.zeros(price_levels)
            ask_volumes = np.zeros(price_levels)
            
            # Distribute bid volumes into bins
            for bid in bids:
                price = float(bid[0])
                volume = float(bid[1])
                
                if price < min_price:
                    continue
                    
                bin_index = min(int((price - min_price) / (max_price - min_price) * price_levels), price_levels - 1)
                if 0 <= bin_index < price_levels:
                    bid_volumes[bin_index] += volume
            
            # Distribute ask volumes into bins
            for ask in asks:
                price = float(ask[0])
                volume = float(ask[1])
                
                if price > max_price:
                    continue
                    
                bin_index = min(int((price - min_price) / (max_price - min_price) * price_levels), price_levels - 1)
                if 0 <= bin_index < price_levels:
                    ask_volumes[bin_index] += volume
            
            # Find support levels (high bid volume)
            support_strength = np.max(bid_volumes) / (np.mean(bid_volumes) + 1e-10)
            
            # Find resistance levels (high ask volume)
            resistance_strength = np.max(ask_volumes) / (np.mean(ask_volumes) + 1e-10)
            
            # Calculate overall S/R strength
            sr_strength = (support_strength + resistance_strength) / 2
            
            # Convert to score (higher strength = higher score)
            # Strength of 1.0 is average (score 50)
            # Strength of 3.0 or more is strong (score 100)
            sr_score = 50 * : No neutral fallback (50.0) found
- ⚠️  _calculate_sr_from_orderbook(self, market_data: Dict[str, Any]) -> float:
        """Calculate support/resistance score from orderbook data."""
        try:
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return 50.0
                
            # Group orders by price levels to find clusters
            price_levels = 20  # Number of price levels to analyze
            price_step = 0.002  # 0.2% steps
            
            # Get current price
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid_price = (best_bid + best_ask) / 2
            
            # Create price bins
            min_price = mid_price * (1 - price_levels * price_step / 2)
            max_price = mid_price * (1 + price_levels * price_step / 2)
            price_bins = np.linspace(min_price, max_price, price_levels + 1)
            
            # Initialize volume arrays
            bid_volumes = np.zeros(price_levels)
            ask_volumes = np.zeros(price_levels)
            
            # Distribute bid volumes into bins
            for bid in bids:
                price = float(bid[0])
                volume = float(bid[1])
                
                if price < min_price:
                    continue
                    
                bin_index = min(int((price - min_price) / (max_price - min_price) * price_levels), price_levels - 1)
                if 0 <= bin_index < price_levels:
                    bid_volumes[bin_index] += volume
            
            # Distribute ask volumes into bins
            for ask in asks:
                price = float(ask[0])
                volume = float(ask[1])
                
                if price > max_price:
                    continue
                    
                bin_index = min(int((price - min_price) / (max_price - min_price) * price_levels), price_levels - 1)
                if 0 <= bin_index < price_levels:
                    ask_volumes[bin_index] += volume
            
            # Find support levels (high bid volume)
            support_strength = np.max(bid_volumes) / (np.mean(bid_volumes) + 1e-10)
            
            # Find resistance levels (high ask volume)
            resistance_strength = np.max(ask_volumes) / (np.mean(ask_volumes) + 1e-10)
            
            # Calculate overall S/R strength
            sr_strength = (support_strength + resistance_strength) / 2
            
            # Convert to score (higher strength = higher score)
            # Strength of 1.0 is average (score 50)
            # Strength of 3.0 or more is strong (score 100)
            sr_score = 50 * : Non-standard score range detected
- ⚠️  _calculate_orderbook_pressure(self, market_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate orderbook pressure metrics.
        
        Returns:
            tuple: (pressure_score, metadata)
        """
        try:
            # Get orderbook data
            orderbook = market_data.get: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_orderbook_pressure(self, market_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate orderbook pressure metrics.
        
        Returns:
            tuple: (pressure_score, metadata)
        """
        try:
            # Get orderbook data
            orderbook = market_data.get: No neutral fallback (50.0) found
- ⚠️  _calculate_orderbook_pressure(self, market_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate orderbook pressure metrics.
        
        Returns:
            tuple: (pressure_score, metadata)
        """
        try:
            # Get orderbook data
            orderbook = market_data.get: Non-standard score range detected

**Scoring Methods:**
- `_calculate_oir_score`: ✅ OK
- `_calculate_di_score`: ✅ OK
- `_calculate_orderbook_imbalance(self, market_data: Dict[str, Any]) -> float:
        """Calculate enhanced orderbook imbalance using volume and price sensitivity.
        
        Args:
            market_data: Dictionary containing market data including orderbook
            
        Returns:
            float: Normalized imbalance score (0-100) where:
                  0 = extremely bearish (ask-heavy)
                  50 = neutral
                  100 = extremely bullish (bid-heavy)
        """
        try:
            self.logger.debug("\n=== ORDERBOOK IMBALANCE CALCULATION DEBUG ===")
            
            # Extract orderbook data from market_data
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            self.logger.debug(f"Raw orderbook data - Bids: {len(bids)}, Asks: {len(asks)}")
            
            if not bids or not asks:
                self.logger.warning("Empty orderbook detected")
                return 50.0  # Neutral imbalance
            
            # Convert to numpy arrays if they aren't already
            if not isinstance(bids, np.ndarray):
                bids = np.array(bids, dtype=float)
            if not isinstance(asks, np.ndarray):
                asks = np.array(asks, dtype=float)
                
            self.logger.debug(f"Converted arrays - Bids shape: {bids.shape}, Asks shape: {asks.shape}")
                
            # 1. Dynamic depth and mid-price calculation
            levels = min(10, len(bids), len(asks))  # Use up to 10 levels
            self.logger.debug(f"Using {levels} levels for analysis")
            
            # Ensure values are floats before calculation
            try:
                bid_price = float(bids[0, 0])
                ask_price = float(asks[0, 0])
                mid_price = (bid_price + ask_price) / 2
                self.logger.debug(f"Price levels - Best bid: {bid_price:.4f}, Best ask: {ask_price:.4f}, Mid: {mid_price:.4f}")
            except (ValueError, TypeError, IndexError) as e:
                self.logger.error(f"Error converting price to float: {str(e)}")
                return 50.0  # Return neutral score on error
            
            # Calculate spread and total depth with error handling
            try:
                spread = (asks[0, 0] - bids[0, 0]) / mid_price
                total_depth = np.sum(bids[:levels, 1]) + np.sum(asks[:levels, 1])
                self.logger.debug(f"Market metrics - Spread: {spread:.6f} ({spread*10000:.2f} bps), Total depth: {total_depth:.2f}")
            except IndexError:
                self.logger.error("Invalid price/size data in orderbook")
                return 50.0
            
            # Update historical metrics
            self._update_historical_metrics(spread, total_depth)
            
            # Normalize spread using historical data with safety check
            normalized_spread = min(1.0, spread / (self.typical_spread + 1e-10)) if hasattr(self, 'typical_spread') else 0.5
            self.logger.debug(f"Normalized spread: {normalized_spread:.4f} (typical: {getattr(self, 'typical_spread', 'N/A')})")
            
            # 2. Volume-weighted imbalance with normalized weights
            level_weights = np.exp(-np.arange(levels) * 0.3)  # Slower decay
            level_weights /= np.sum(level_weights)  # Ensure weights sum to 1
            
            self.logger.debug("Level weights (exponential decay):")
            for i, weight in enumerate(level_weights):
                self.logger.debug(f"  Level {i+1}: {weight:.4f} ({weight*100:.1f}%)")
            
            try:
                weighted_bid_volume = np.sum(bids[:levels, 1] * level_weights)
                weighted_ask_volume = np.sum(asks[:levels, 1] * level_weights)
                total_weighted_volume = weighted_bid_volume + weighted_ask_volume
                
                self.logger.debug(f"Volume-weighted analysis:")
                self.logger.debug(f"  Weighted bid volume: {weighted_bid_volume:.2f}")
                self.logger.debug(f"  Weighted ask volume: {weighted_ask_volume:.2f}")
                self.logger.debug(f"  Total weighted volume: {total_weighted_volume:.2f}")
                
            except (IndexError, ValueError) as e:
                self.logger.error(f"Error calculating weighted volumes: {str(e)}")
                return 50.0
            
            # Check for meaningful volume with logging
            if total_weighted_volume < 1e-6:
                self.logger.warning("Negligible total weighted volume detected")
                return 50.0  # Neutral if no meaningful volume
                
            weighted_imbalance = (weighted_bid_volume - weighted_ask_volume) / total_weighted_volume
            self.logger.debug(f"Weighted imbalance: {weighted_imbalance:.6f}")
            
            # 3. Price-sensitive imbalance with dynamic sensitivity
            try:
                bid_distances = np.abs(bids[:levels, 0] - mid_price) / mid_price
                ask_distances = np.abs(asks[:levels, 0] - mid_price) / mid_price
                
                self.logger.debug("Price distance analysis:")
                for i in range(min(5, levels)):
                    self.logger.debug(f"  Level {i+1} - Bid distance: {bid_distances[i]:.6f}, Ask distance: {ask_distances[i]:.6f}")
                    
            except IndexError:
                self.logger.error("Error calculating price distances")
                return 50.0
            
            # Dynamic price sensitivity based on normalized spread
            price_sensitivity = 15 * min(1.5, 1 + normalized_spread)
            self.logger.debug(f"Price sensitivity factor: {price_sensitivity:.2f}")
            
            # Calculate and normalize price weights with epsilon
            bid_weights = np.exp(-bid_distances * price_sensitivity)
            ask_weights = np.exp(-ask_distances * price_sensitivity)
            
            self.logger.debug("Price-based weights (before normalization):")
            for i in range(min(5, levels)):
                self.logger.debug(f"  Level {i+1} - Bid weight: {bid_weights[i]:.4f}, Ask weight: {ask_weights[i]:.4f}")
            
            # Ensure weights sum to 1 even under edge cases
            bid_weights = bid_weights / (np.sum(bid_weights) + 1e-10)
            ask_weights = ask_weights / (np.sum(ask_weights) + 1e-10)
            
            self.logger.debug("Price-based weights (normalized):")
            for i in range(min(5, levels)):
                self.logger.debug(f"  Level {i+1} - Bid weight: {bid_weights[i]:.4f}, Ask weight: {ask_weights[i]:.4f}")
            
            # Calculate price-weighted volumes with error handling
            try:
                price_weighted_bid = np.sum(bids[:levels, 1] * bid_weights)
                price_weighted_ask = np.sum(asks[:levels, 1] * ask_weights)
                total_price_weighted = price_weighted_bid + price_weighted_ask
                
                self.logger.debug(f"Price-weighted analysis:")
                self.logger.debug(f"  Price-weighted bid volume: {price_weighted_bid:.2f}")
                self.logger.debug(f"  Price-weighted ask volume: {price_weighted_ask:.2f}")
                self.logger.debug(f"  Total price-weighted volume: {total_price_weighted:.2f}")
                
            except (IndexError, ValueError) as e:
                self.logger.error(f"Error calculating price-weighted volumes: {str(e)}")
                return 50.0
            
            # Check for meaningful price-weighted volume with logging
            if total_price_weighted < 1e-6:
                self.logger.warning("Negligible price-weighted volume detected")
                price_sensitive_imbalance = 0.0
            else:
                price_sensitive_imbalance = (price_weighted_bid - price_weighted_ask) / total_price_weighted
                
            self.logger.debug(f"Price-sensitive imbalance: {price_sensitive_imbalance:.6f}")
            
            # 4. Combine metrics with dynamic weighting based on normalized spread
            price_weight = min(0.8, 0.5 + normalized_spread)  # Cap at 0.8 for stability
            volume_weight = 1 - price_weight
            
            self.logger.debug(f"Combination weights - Volume: {volume_weight:.3f}, Price: {price_weight:.3f}")
            
            # Use numpy's average for cleaner weighted combination
            final_imbalance = np.average(
                [weighted_imbalance, price_sensitive_imbalance],
                weights=[volume_weight, price_weight]
            )
            
            self.logger.debug(f"Combined imbalance: {final_imbalance:.6f}")
            
            # 5. Apply sigmoid normalization for smoother distribution
            normalized_imbalance = 50 * (1 + np.tanh(2 * final_imbalance))
            self.logger.debug(f"Sigmoid normalized imbalance: {normalized_imbalance:.2f}")
            
            # 6. Dynamic depth confidence calculation using historical depth
            depth_confidence = min(1.0, total_depth / (self.typical_depth + 1e-10)) if hasattr(self, 'typical_depth') else 0.5
            self.logger.debug(f"Depth confidence: {depth_confidence:.3f} (typical depth: {getattr(self, 'typical_depth', 'N/A')})")
            
            # 7. Final score calculation with confidence adjustment
            final_score = 50 + `: ❌ 1 issues
- `_calculate_liquidity_score`: ✅ OK
- `_calculate_price_impact_score`: ✅ OK
- `_calculate_sr_from_orderbook(self, market_data: Dict[str, Any]) -> float:
        """Calculate support/resistance score from orderbook data."""
        try:
            orderbook = market_data.get('orderbook', {})
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return 50.0
                
            # Group orders by price levels to find clusters
            price_levels = 20  # Number of price levels to analyze
            price_step = 0.002  # 0.2% steps
            
            # Get current price
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid_price = (best_bid + best_ask) / 2
            
            # Create price bins
            min_price = mid_price * (1 - price_levels * price_step / 2)
            max_price = mid_price * (1 + price_levels * price_step / 2)
            price_bins = np.linspace(min_price, max_price, price_levels + 1)
            
            # Initialize volume arrays
            bid_volumes = np.zeros(price_levels)
            ask_volumes = np.zeros(price_levels)
            
            # Distribute bid volumes into bins
            for bid in bids:
                price = float(bid[0])
                volume = float(bid[1])
                
                if price < min_price:
                    continue
                    
                bin_index = min(int((price - min_price) / (max_price - min_price) * price_levels), price_levels - 1)
                if 0 <= bin_index < price_levels:
                    bid_volumes[bin_index] += volume
            
            # Distribute ask volumes into bins
            for ask in asks:
                price = float(ask[0])
                volume = float(ask[1])
                
                if price > max_price:
                    continue
                    
                bin_index = min(int((price - min_price) / (max_price - min_price) * price_levels), price_levels - 1)
                if 0 <= bin_index < price_levels:
                    ask_volumes[bin_index] += volume
            
            # Find support levels (high bid volume)
            support_strength = np.max(bid_volumes) / (np.mean(bid_volumes) + 1e-10)
            
            # Find resistance levels (high ask volume)
            resistance_strength = np.max(ask_volumes) / (np.mean(ask_volumes) + 1e-10)
            
            # Calculate overall S/R strength
            sr_strength = (support_strength + resistance_strength) / 2
            
            # Convert to score (higher strength = higher score)
            # Strength of 1.0 is average (score 50)
            # Strength of 3.0 or more is strong (score 100)
            sr_score = 50 * `: ❌ 3 issues
- `_calculate_orderbook_pressure(self, market_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate orderbook pressure metrics.
        
        Returns:
            tuple: (pressure_score, metadata)
        """
        try:
            # Get orderbook data
            orderbook = market_data.get`: ❌ 3 issues


### orderflow_indicators.py
**Scoring Methods Found:** 9
**Issues Found:** 17

**Issues:**
- ⚠️  _calculate_confidence(self, market_data: Dict[str, Any]) -> float:
        """Calculate confidence in orderflow analysis."""
        try:
            trades = market_data.get('trades', [])
            
            # Check data quality
            if len(trades) < self.min_trades:
                return 0.5
                
            # Check for consistent trade data
            if not all(isinstance(t, dict) and 'price' in t and 'amount' in t for t in trades):
                return 0.7
                
            return 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5

    async def _calculate_component_scores: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_confidence(self, market_data: Dict[str, Any]) -> float:
        """Calculate confidence in orderflow analysis."""
        try:
            trades = market_data.get('trades', [])
            
            # Check data quality
            if len(trades) < self.min_trades:
                return 0.5
                
            # Check for consistent trade data
            if not all(isinstance(t, dict) and 'price' in t and 'amount' in t for t in trades):
                return 0.7
                
            return 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5

    async def _calculate_component_scores: No neutral fallback (50.0) found
- ⚠️  _calculate_confidence(self, market_data: Dict[str, Any]) -> float:
        """Calculate confidence in orderflow analysis."""
        try:
            trades = market_data.get('trades', [])
            
            # Check data quality
            if len(trades) < self.min_trades:
                return 0.5
                
            # Check for consistent trade data
            if not all(isinstance(t, dict) and 'price' in t and 'amount' in t for t in trades):
                return 0.7
                
            return 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5

    async def _calculate_component_scores: Non-standard score range detected
- ⚠️  _calculate_cvd(self, market_data: Dict[str, Any]) -> float:
        """Calculate Cumulative Volume Delta (CVD) from trade data.
        
        Args:
            market_data: Market data dictionary containing trades
            
        Returns:
            float: CVD value
        """
        # Use caching to avoid redundant calculations
        cache_key = 'cvd'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING CVD CALCULATION (OPTIMIZED)")
        self.logger.debug("=" * 50)
        
        try:
            # Use the centralized processed trades
            trades_df = self._get_processed_trades(market_data)
            
            if trades_df.empty:
                self.logger.warning("No valid trade data available for CVD calculation")
                return 50.0
            
            # Now just use the pre-calculated signed_volume
            cvd = trades_df['signed_volume'].sum()
            total_volume = trades_df['amount'].sum()
            
            self.logger.debug(f"CVD calculation using processed trades:")
            self.logger.debug(f"- Raw CVD: {cvd:.2f}")
            self.logger.debug(f"- Total volume: {total_volume:.2f}")
            
            # Calculate CVD percentage
            if total_volume > 0:
                cvd_percentage = cvd / total_volume
            else:
                cvd_percentage = 0.0
            
            # Get price direction for CVD-Price divergence analysis
            price_change_pct = self._get_price_direction(market_data)
            
            self.logger.debug(f"CVD: {cvd:.2f}, CVD percentage: {cvd_percentage:.4f}, Price change: {price_change_pct:.3f}%")
            
            # Analyze CVD-Price relationship for divergences
            cvd_score = self._analyze_cvd_price_relationship: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_cvd(self, market_data: Dict[str, Any]) -> float:
        """Calculate Cumulative Volume Delta (CVD) from trade data.
        
        Args:
            market_data: Market data dictionary containing trades
            
        Returns:
            float: CVD value
        """
        # Use caching to avoid redundant calculations
        cache_key = 'cvd'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING CVD CALCULATION (OPTIMIZED)")
        self.logger.debug("=" * 50)
        
        try:
            # Use the centralized processed trades
            trades_df = self._get_processed_trades(market_data)
            
            if trades_df.empty:
                self.logger.warning("No valid trade data available for CVD calculation")
                return 50.0
            
            # Now just use the pre-calculated signed_volume
            cvd = trades_df['signed_volume'].sum()
            total_volume = trades_df['amount'].sum()
            
            self.logger.debug(f"CVD calculation using processed trades:")
            self.logger.debug(f"- Raw CVD: {cvd:.2f}")
            self.logger.debug(f"- Total volume: {total_volume:.2f}")
            
            # Calculate CVD percentage
            if total_volume > 0:
                cvd_percentage = cvd / total_volume
            else:
                cvd_percentage = 0.0
            
            # Get price direction for CVD-Price divergence analysis
            price_change_pct = self._get_price_direction(market_data)
            
            self.logger.debug(f"CVD: {cvd:.2f}, CVD percentage: {cvd_percentage:.4f}, Price change: {price_change_pct:.3f}%")
            
            # Analyze CVD-Price relationship for divergences
            cvd_score = self._analyze_cvd_price_relationship: Non-standard score range detected
- ⚠️  _calculate_trade_flow_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_trade_flow_score: Non-standard score range detected
- ⚠️  _calculate_trades_imbalance_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_trades_imbalance_score: Non-standard score range detected
- ⚠️  _calculate_open_interest_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_open_interest_score: Non-standard score range detected
- ⚠️  _calculate_trades_pressure_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_trades_pressure_score: Non-standard score range detected
- ⚠️  _calculate_liquidity_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_liquidity_score: Non-standard score range detected
- ⚠️  _calculate_price_cvd_divergence(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate divergence between price and CVD.
        
        This method detects when price is moving in one direction but CVD is moving in the opposite direction,
        which can indicate potential reversals.
        
        Args:
            market_data: Dictionary containing market data with OHLCV and trades
            
        Returns:
            Dict: Divergence information including type and strength
        """
        # Use caching to avoid redundant calculations
        cache_key = 'price_cvd_divergence'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        calculation_start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING PRICE-CVD DIVERGENCE CALCULATION")
        self.logger.debug("=" * 50)
        
        try:
            # Check if we have the required data
            if 'ohlcv' not in market_data:
                self.logger.warning("Missing OHLCV data for price-CVD divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            ohlcv_data = market_data['ohlcv']
            
            # Check if ohlcv_data is a dictionary
            if not isinstance(ohlcv_data, dict):
                self.logger.warning(f"OHLCV data is not a dictionary: {type(ohlcv_data)}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log available timeframes
            self.logger.debug(f"Available OHLCV timeframes: {list(ohlcv_data.keys())}")
                
            # Try to find a valid timeframe
            valid_timeframe = None
            ohlcv_df = None
            
            # First check for direct DataFrame access (for backward compatibility)
            for tf in ['base', 'ltf', '1', '5']:
                if tf in ohlcv_data:
                    # Check if it's a direct DataFrame
                    if isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
                    # Check if it's a nested structure with 'data' key
                    elif isinstance(ohlcv_data[tf], dict) and 'data' in ohlcv_data[tf] and isinstance(ohlcv_data[tf]['data'], pd.DataFrame) and not ohlcv_data[tf]['data'].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]['data']
                        self.logger.debug(f"Found nested DataFrame at timeframe {tf}['data']")
                        break
            
            # Also check for timeframes with '_direct' suffix (added for testing)
            if not valid_timeframe:
                for tf in ['base_direct', 'ltf_direct', '1_direct', '5_direct']:
                    if tf in ohlcv_data and isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
            
            if not valid_timeframe or ohlcv_df is None:
                self.logger.warning("No valid OHLCV timeframe found for price-CVD divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Verify that the DataFrame has the required columns
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in ohlcv_df.columns]
            if missing_columns:
                self.logger.warning(f"OHLCV data missing required columns: {missing_columns}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log OHLCV DataFrame info
            self.logger.debug(f"OHLCV DataFrame for {valid_timeframe}: shape={ohlcv_df.shape}, columns={list(ohlcv_df.columns)}")
            self.logger.debug(f"OHLCV DataFrame index type: {type(ohlcv_df.index)}")
            if len(ohlcv_df) > 0:
                self.logger.debug(f"OHLCV first row: {ohlcv_df.iloc[0].to_dict()}")
                self.logger.debug(f"OHLCV last row: {ohlcv_df.iloc[-1].to_dict()}")
                
            # Use configurable lookback period
            lookback = min(len(ohlcv_df), self.divergence_lookback)
            if lookback < 2:
                self.logger.warning(f"Insufficient OHLCV data for divergence calculation: {len(ohlcv_df)} rows")
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.debug(f"Using lookback period of {lookback} candles for divergence calculation")
            
            # Get trades data
            trades = market_data.get('trades', [])
            if not trades or len(trades) < self.min_trades:
                self.logger.warning(f"Insufficient trade data for price-CVD divergence calculation: {len(trades)} trades, minimum required: {self.min_trades}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Convert trades to DataFrame if needed
            trades_df = trades if isinstance(trades, pd.DataFrame) else pd.DataFrame(trades)
            
            # Log trades DataFrame info
            self.logger.debug(f"Trades DataFrame: shape={trades_df.shape}, columns={list(trades_df.columns)}")
            
            # Ensure we have timestamp in trades
            if 'time' not in trades_df.columns and 'timestamp' in trades_df.columns:
                trades_df['time'] = trades_df['timestamp']
                self.logger.debug("Mapped 'timestamp' to 'time' in trades DataFrame")
            elif 'time' not in trades_df.columns and 'T' in trades_df.columns:
                trades_df['time'] = trades_df['T']
                self.logger.debug("Mapped 'T' to 'time' in trades DataFrame")
                
            if 'time' not in trades_df.columns:
                self.logger.warning("Missing time/timestamp in trades data for price-CVD divergence")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Ensure time column is numeric
            try:
                trades_df['time'] = pd.to_numeric(trades_df['time'])
                self.logger.debug(f"Converted time column to numeric. Sample values: {trades_df['time'].head(3).tolist()}")
            except Exception as e:
                self.logger.warning(f"Failed to convert time column to numeric: {str(e)}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Ensure we have side in trades
            if 'side' not in trades_df.columns and 'S' in trades_df.columns:
                trades_df['side'] = trades_df['S']
                self.logger.debug("Mapped 'S' to 'side' in trades DataFrame")
                
            if 'side' not in trades_df.columns:
                self.logger.warning("Missing side in trades data for price-CVD divergence")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Ensure we have amount/size in trades
            if 'amount' not in trades_df.columns:
                for col in ['size', 'v', 'volume', 'qty', 'quantity']:
                    if col in trades_df.columns:
                        trades_df['amount'] = trades_df[col]
                        self.logger.debug(f"Mapped '{col}' to 'amount' in trades DataFrame")
                        break
                        
            if 'amount' not in trades_df.columns:
                self.logger.warning("Missing amount/size in trades data for price-CVD divergence")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Get price trend
            price_changes = ohlcv_df['close'].diff().tail(lookback)
            price_trend = price_changes.sum()
            
            self.logger.debug(f"Price trend over {lookback} candles: {price_trend:.4f}")
            self.logger.debug(f"Price changes: min={price_changes.min():.4f}, max={price_changes.max():.4f}, mean={price_changes.mean():.4f}")
            
            # Calculate CVD for each candle period
            candle_cvds = []
            candle_timestamps = []
            
            # Ensure proper time tracking for candle processing
            candle_start_time = time.time()
            
            for i in range(1, lookback + 1):
                if i >= len(ohlcv_df):
                    break
                    
                # Get timestamp range for this candle
                # Check if we have a timestamp column or need to use the index
                if 'timestamp' in ohlcv_df.columns:
                    candle_end_time = ohlcv_df.iloc[-i]['timestamp']
                    candle_start_time_ts = ohlcv_df.iloc[-(i+1)]['timestamp'] if i+1 < len(ohlcv_df) else ohlcv_df.iloc[-i]['timestamp'] - 60000  # Fallback: 1 minute earlier
                    self.logger.debug(f"Candle {i} timestamp from column: start={candle_start_time_ts}, end={candle_end_time}")
                    # Save the timestamp for potential interpolation later
                    candle_timestamps.append(candle_end_time)
                else:
                    # Try to use index as timestamp
                    try:
                        candle_end_time = ohlcv_df.index[-i]
                        candle_start_time_ts = ohlcv_df.index[-(i+1)] if i+1 < len(ohlcv_df) else candle_end_time - pd.Timedelta(minutes=1)
                        self.logger.debug(f"Candle {i} timestamp from index: start={candle_start_time_ts}, end={candle_end_time}")
                        # Save the timestamp for potential interpolation later
                        candle_timestamps.append(candle_end_time)
                    except Exception as e:
                        self.logger.debug(f"Failed to get timestamp from index: {str(e)}")
                        continue
                
                # Ensure start_time and end_time are numeric
                try:
                    # Convert pandas Timestamp to milliseconds since epoch
                    if isinstance(candle_start_time_ts, pd.Timestamp):
                        start_time_orig = candle_start_time_ts
                        candle_start_time_ts = int(candle_start_time_ts.timestamp() * 1000)
                        self.logger.debug(f"Converted start_time from pd.Timestamp {start_time_orig} to {candle_start_time_ts}")
                    elif isinstance(candle_start_time_ts, str):
                        start_time_orig = candle_start_time_ts
                        candle_start_time_ts = pd.to_numeric(candle_start_time_ts)
                        self.logger.debug(f"Converted start_time from string {start_time_orig} to {candle_start_time_ts}")
                    
                    if isinstance(candle_end_time, pd.Timestamp):
                        end_time_orig = candle_end_time
                        candle_end_time = int(candle_end_time.timestamp() * 1000)
                        self.logger.debug(f"Converted end_time from pd.Timestamp {end_time_orig} to {candle_end_time}")
                    elif isinstance(candle_end_time, str):
                        end_time_orig = candle_end_time
                        candle_end_time = pd.to_numeric(candle_end_time)
                        self.logger.debug(f"Converted end_time from string {end_time_orig} to {candle_end_time}")
                except Exception as e:
                    self.logger.debug(f"Failed to convert timestamp to numeric: {str(e)}")
                    continue
                
                # Filter trades for this candle
                candle_trades_filtered = trades_df[(trades_df['time'] >= candle_start_time_ts) & (trades_df['time'] < candle_end_time)]
                
                if candle_trades_filtered.empty:
                    self.logger.debug(f"No trades found for candle {i} (time range: {candle_start_time_ts} to {candle_end_time})")
                    candle_cvds.append(0)
                    continue
                
                # Create a copy to avoid SettingWithCopyWarning
                candle_trades = candle_trades_filtered.copy()
                
                self.logger.debug(f"Found {len(candle_trades)} trades for candle {i}")
                    
                # Calculate CVD for this candle
                try:
                    # Log the unique side values to aid in debugging
                    unique_sides = candle_trades['side'].astype(str).unique()
                    self.logger.debug(f"Unique side values in candle {i} trades: {unique_sides}")
                    
                    # Ensure amount column is numeric
                    try:
                        candle_trades.loc[:, 'amount'] = pd.to_numeric(candle_trades['amount'], errors='coerce')
                    except Exception as e:
                        self.logger.warning(f"Error converting amount to numeric: {str(e)}, trying fallback")
                        candle_trades.loc[:, 'amount'] = candle_trades['amount'].apply(lambda x: float(x) if isinstance(x, str) else x)
                    
                    # More robust way to determine buy/sell sides
                    def is_buy_side(side_val):
                        if pd.isna(side_val):
                            return False
                        s = str(side_val).lower().strip()
                        return s in ['buy', 'b', '1', 'true', 'bid', 'long']
                    
                    def is_sell_side(side_val):
                        if pd.isna(side_val):
                            return False
                        s = str(side_val).lower().strip()
                        return s in ['sell', 's', '-1', 'false', 'ask', 'short']
                    
                    # Apply the side detection functions
                    candle_trades.loc[:, 'is_buy'] = candle_trades['side'].apply(is_buy_side)
                    candle_trades.loc[:, 'is_sell'] = candle_trades['side'].apply(is_sell_side)
                    
                    # Log side detection results
                    buy_count = candle_trades['is_buy'].sum()
                    sell_count = candle_trades['is_sell'].sum()
                    unclassified = len(candle_trades) - buy_count - sell_count
                    self.logger.debug(f"Side classification: buy={buy_count}, sell={sell_count}, unclassified={unclassified}")
                    
                    if unclassified > 0 and len(unique_sides) > 0:
                        # If we have unclassified trades, try a more flexible approach
                        if all(side.lower() in ['buy', 'sell'] for side in unique_sides if isinstance(side, str)):
                            self.logger.debug(f"Using simpler case-insensitive matching for side values")
                            candle_trades.loc[:, 'is_buy'] = candle_trades['side'].astype(str).str.lower() == 'buy'
                            candle_trades.loc[:, 'is_sell'] = candle_trades['side'].astype(str).str.lower() == 'sell'
                            buy_count = candle_trades['is_buy'].sum()
                            sell_count = candle_trades['is_sell'].sum()
                            unclassified = len(candle_trades) - buy_count - sell_count
                            self.logger.debug(f"Updated side classification: buy={buy_count}, sell={sell_count}, unclassified={unclassified}")
                    
                    # Check for any remaining unclassified trades
                    if unclassified > 0 and buy_count == 0 and sell_count == 0:
                        # Last resort attempt - case-insensitive partial matching
                        self.logger.debug(f"Attempting case-insensitive partial matching for sides")
                        candle_trades.loc[:, 'is_buy'] = candle_trades['side'].astype(str).str.lower().str.contains('buy', na=False) | candle_trades['side'].astype(str).str.lower().str.contains('bid', na=False)
                        candle_trades.loc[:, 'is_sell'] = candle_trades['side'].astype(str).str.lower().str.contains('sell', na=False) | candle_trades['side'].astype(str).str.lower().str.contains('ask', na=False)
                        buy_count = candle_trades['is_buy'].sum()
                        sell_count = candle_trades['is_sell'].sum()
                        self.logger.debug(f"Final side classification: buy={buy_count}, sell={sell_count}, unclassified={len(candle_trades) - buy_count - sell_count}")
                    
                    # Calculate buy and sell volumes
                    buy_volume = candle_trades[candle_trades['is_buy']]['amount'].sum()
                    sell_volume = candle_trades[candle_trades['is_sell']]['amount'].sum()
                    
                    # Replace NaN with 0
                    buy_volume = 0.0 if pd.isna(buy_volume) else float(buy_volume)
                    sell_volume = 0.0 if pd.isna(sell_volume) else float(sell_volume)
                    
                    # Additional diagnostic for debugging
                    if buy_volume == 0 and sell_volume == 0:
                        # This shouldn't happen if we have trades and properly classified sides
                        # Log a sample of the trades to diagnose the issue
                        if not candle_trades.empty:
                            sample_trades = candle_trades.head(3)
                            self.logger.warning(f"Both buy and sell volumes are 0 despite having {len(candle_trades)} trades. Sample trades:")
                            for idx, trade in sample_trades.iterrows():
                                self.logger.warning(f"Trade {idx}: side={trade['side']}, amount={trade['amount']}, is_buy={trade.get('is_buy', False)}, is_sell={trade.get('is_sell', False)}")
                            
                            # Check for data quality issues
                            amounts = candle_trades['amount'].tolist()
                            amount_stats = {
                                'min': candle_trades['amount'].min() if not candle_trades['amount'].empty else 'N/A',
                                'max': candle_trades['amount'].max() if not candle_trades['amount'].empty else 'N/A',
                                'mean': candle_trades['amount'].mean() if not candle_trades['amount'].empty else 'N/A',
                                'nan_count': candle_trades['amount'].isna().sum(),
                                'zero_count': (candle_trades['amount'] == 0).sum()
                            }
                            self.logger.warning(f"Amount stats: {amount_stats}")
                    
                    self.logger.debug(f"Candle {i} CVD calculation: buy_volume={buy_volume:.4f}, sell_volume={sell_volume:.4f}, types: {type(buy_volume)}, {type(sell_volume)}")
                    
                    candle_cvd = buy_volume - sell_volume
                    candle_cvds.append(candle_cvd)
                    self.logger.debug(f"Candle {i} CVD: {candle_cvd:.4f}")
                except Exception as e:
                    self.logger.warning(f"Error calculating candle {i} CVD: {str(e)}, using 0 instead")
                    # Log more details about the error for debugging
                    import traceback
                    self.logger.debug(f"Error details: {traceback.format_exc()}")
                    
                    # Try to get information about the candle_trades DataFrame
                    try:
                        if 'candle_trades' in locals() and not candle_trades.empty:
                            self.logger.debug(f"Candle trades info: shape={candle_trades.shape}, columns={list(candle_trades.columns)}")
                            self.logger.debug(f"Sample trades: {candle_trades.head(2).to_dict('records')}")
                            self.logger.debug(f"Side values: {candle_trades['side'].value_counts().to_dict()}")
                    except Exception as inner_e:
                        self.logger.debug(f"Failed to log candle trades information: {str(inner_e)}")
                    
                    candle_cvds.append(0)
            
            # Check if we have enough candle CVD values
            if len(candle_cvds) < 2:
                self.logger.warning(f"Insufficient candle CVD data: {len(candle_cvds)} values")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Interpolate for candles without trades if enabled
            if getattr(self, 'interpolate_missing_cvd', True) and 0 in candle_cvds:
                self.logger.debug("Interpolating CVD values for candles without trades")
                # Create a series with timestamps and CVD values
                cvd_series = pd.Series(candle_cvds, index=candle_timestamps[:len(candle_cvds)])
                
                # Find indices of non-zero values
                non_zero_indices = [i for i, cvd in enumerate(candle_cvds) if cvd != 0]
                if not non_zero_indices:
                    self.logger.debug("No non-zero CVD values found for interpolation")
                else:
                    self.logger.debug(f"Found {len(non_zero_indices)} non-zero values at indices: {non_zero_indices}")
                    
                    # Handle zeros before first non-zero (backfill)
                    first_non_zero_idx = non_zero_indices[0]
                    first_non_zero_val = candle_cvds[first_non_zero_idx]
                    if first_non_zero_idx > 0:
                        self.logger.debug(f"Backfilling {first_non_zero_idx} initial zeros before first value {first_non_zero_val}")
                        for j in range(0, first_non_zero_idx):
                            # Use a linear ramp up to the first value
                            candle_cvds[j] = first_non_zero_val * (j + 1) / (first_non_zero_idx + 1)
                    
                    # Handle zeros between non-zero values (interpolation)
                    for idx_pos in range(len(non_zero_indices) - 1):
                        start_idx = non_zero_indices[idx_pos]
                        end_idx = non_zero_indices[idx_pos + 1]
                        start_val = candle_cvds[start_idx]
                        end_val = candle_cvds[end_idx]
                        
                        if end_idx - start_idx > 1:  # If there are zeros between
                            self.logger.debug(f"Interpolating between index {start_idx} ({start_val}) and {end_idx} ({end_val})")
                            for j in range(start_idx + 1, end_idx):
                                # Linear interpolation
                                ratio = (j - start_idx) / (end_idx - start_idx)
                                candle_cvds[j] = start_val + (end_val - start_val) * ratio
                    
                    # Handle zeros after last non-zero (extrapolation)
                    last_non_zero_idx = non_zero_indices[-1]
                    last_non_zero_val = candle_cvds[last_non_zero_idx]
                    
                    if last_non_zero_idx < len(candle_cvds) - 1:
                        # Calculate trend from available non-zero values
                        if len(non_zero_indices) >= 2:
                            # Use the last two non-zero values to determine trend
                            prev_idx = non_zero_indices[-2]
                            prev_val = candle_cvds[prev_idx]
                            last_idx = non_zero_indices[-1]
                            last_val = candle_cvds[last_idx]
                            
                            # Calculate slope (per candle)
                            trend_slope = (last_val - prev_val) / (last_idx - prev_idx)
                            self.logger.debug(f"Extrapolating with slope {trend_slope:.4f} based on last values {prev_val:.4f} and {last_val:.4f}")
                            
                            # Apply diminishing trend after last value (decay factor reduces impact over time)
                            decay_factor = 0.8  # Reduce impact by 20% each candle
                            for j in range(last_non_zero_idx + 1, len(candle_cvds)):
                                steps = j - last_non_zero_idx
                                # Calculate diminishing effect with distance
                                decay = decay_factor ** steps
                                extrapolated_val = last_non_zero_val + (trend_slope * steps * decay)
                                candle_cvds[j] = extrapolated_val
                        else:
                            # Only one non-zero value, use decay from that value
                            self.logger.debug(f"Only one non-zero value ({last_non_zero_val:.4f}), using decay extrapolation")
                            decay_factor = 0.7  # Stronger decay when we have less information
                            for j in range(last_non_zero_idx + 1, len(candle_cvds)):
                                steps = j - last_non_zero_idx
                                # Apply decay from last known value
                                candle_cvds[j] = last_non_zero_val * (decay_factor ** steps)
                        
                        self.logger.debug(f"Extrapolated {len(candle_cvds) - last_non_zero_idx - 1} values after last non-zero value")
                
                zero_count = candle_cvds.count(0)
                self.logger.debug(f"After interpolation, zero values remaining: {zero_count}")
                if zero_count > 0:
                    zero_indices = [i for i, val in enumerate(candle_cvds) if val == 0]
                    self.logger.debug(f"Remaining zeros at indices: {zero_indices}")
                    # Last attempt to fill any remaining zeros with small random values
                    for idx in zero_indices:
                        # Use a small percentage of the max absolute CVD as a fallback
                        max_abs_cvd = max(abs(cvd) for cvd in candle_cvds if cvd != 0) if any(cvd != 0 for cvd in candle_cvds) else 1.0
                        candle_cvds[idx] = max_abs_cvd * 0.01  # 1% of max as fallback
            
            self.logger.debug(f"Calculated CVD for {len(candle_cvds)} candles")
            self.logger.debug(f"Candle CVDs: min={min(candle_cvds):.4f}, max={max(candle_cvds):.4f}, mean={sum(candle_cvds)/len(candle_cvds):.4f}")
            
            # Apply time weighting if enabled
            weighted_candle_cvds = []
            if self.time_weighting_enabled:
                self.logger.debug(f"Applying time weighting with recency factor {self.recency_factor}")
                for i, cvd in enumerate(candle_cvds):
                    # Apply exponential weighting - more recent candles get higher weight
                    # i=0 is the most recent candle
                    weight = self.recency_factor ** (len(candle_cvds) - 1 - i)
                    weighted_candle_cvds.append(cvd * weight)
                    self.logger.debug(f"Candle {i} CVD: {cvd:.2f}, Weight: {weight:.2f}, Weighted: {cvd * weight:.2f}")
            else:
                self.logger.debug("Time weighting disabled, using raw CVD values")
                weighted_candle_cvds = candle_cvds
            
            # Calculate CVD trend with time weighting
            cvd_trend = sum(weighted_candle_cvds)
            
            # For normalization, we need the sum of absolute weighted values
            abs_sum = sum(abs(c) for c in weighted_candle_cvds)
            
            self.logger.debug(f"CVD trend: {cvd_trend:.4f}, Absolute sum: {abs_sum:.4f}")
            
            # Calculate divergence
            divergence_strength = 0.0
            divergence_type = 'neutral'
            
            if (price_trend > 0 and cvd_trend < 0):
                # Bearish divergence: Price up, CVD down
                divergence_type = 'bearish'
                divergence_strength = min(abs(cvd_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bearish divergence: Price trend={price_trend:.4f} (up), CVD trend={cvd_trend:.4f} (down)")
            elif (price_trend < 0 and cvd_trend > 0):
                # Bullish divergence: Price down, CVD up
                divergence_type = 'bullish'
                divergence_strength = min(abs(cvd_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bullish divergence: Price trend={price_trend:.4f} (down), CVD trend={cvd_trend:.4f} (up)")
            else:
                self.logger.debug(f"No divergence detected: Price trend={price_trend:.4f}, CVD trend={cvd_trend:.4f}")
            
            # Only return significant divergences
            if divergence_strength < self.divergence_strength_threshold:
                self.logger.debug(f"Divergence strength {divergence_strength:.2f} below threshold {self.divergence_strength_threshold}, returning neutral")
                
                # Log execution time
                calculation_end_time = time.time()
                execution_time = calculation_end_time - calculation_start_time
                self.logger.debug(f"Price-CVD divergence calculation completed in {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.info(f"Price-CVD divergence: {divergence_type}, strength: {divergence_strength:.2f}")
            
            # Fix time tracking for candle processing
            candle_processing_end_time = time.time()
            candle_processing_time = candle_processing_end_time - candle_start_time
            self.logger.debug(f"Processed {lookback} candles in {candle_processing_time:.4f} seconds")
            
            # Calculate the final execution time
            calculation_end_time = time.time()
            execution_time = calculation_end_time - calculation_start_time
            self.logger.debug(f"Price-CVD divergence calculation completed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            result = {
                'type': divergence_type,
                'strength': float(divergence_strength)
            }
            
            # Store in cache before returning
            self._cache[cache_key] = result
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating price-CVD divergence: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # Calculate the final execution time
            calculation_end_time = time.time()
            execution_time = calculation_end_time - calculation_start_time
            self.logger.debug(f"Price-CVD divergence calculation failed after {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            return {'type': 'neutral', 'strength': 0.0}

    def _calculate_price_oi_divergence(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate divergence between price and open interest.
        
        This method detects when price is moving in one direction but open interest is moving in the opposite direction,
        which can indicate potential reversals.
        
        Args:
            market_data: Dictionary containing market data with OHLCV and open interest data
            
        Returns:
            Dict: Divergence information including type and strength
        """
        # Use caching to avoid redundant calculations
        cache_key = 'price_oi_divergence'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        # Enhanced debugging: Log market_data top-level keys
        self.logger.debug(f"OI-PRICE DIVERGENCE: Market data keys: {list(market_data.keys())}")
        
        # Check if open interest data is available before proceeding
        if ('open_interest' not in market_data and 
            ('sentiment' not in market_data or 'open_interest' not in market_data.get('sentiment', {}))):
            self.logger.warning("Missing open interest data for price-OI divergence calculation")
            
            # Enhanced debugging: More details about the structure if data is missing
            if 'sentiment' in market_data:
                self.logger.debug(f"OI-PRICE DIVERGENCE: Sentiment keys available: {list(market_data['sentiment'].keys())}")
            if 'open_interest' in market_data:
                self.logger.debug(f"OI-PRICE DIVERGENCE: Open interest appears empty or malformed: {market_data['open_interest']}")
                
            return {'type': 'neutral', 'strength': 0.0}
            
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING PRICE-OI DIVERGENCE CALCULATION")
        self.logger.debug("=" * 50)
        
        # Enhanced debugging: Log concise OI structure info
        if 'open_interest' in market_data:
            oi_dump = market_data['open_interest']
            if isinstance(oi_dump, dict):
                # Log only essential info instead of full structure
                history_count = len(oi_dump.get('history', []))
                current_oi = oi_dump.get('current', 'N/A')
                previous_oi = oi_dump.get('previous', 'N/A')
                self.logger.debug(f"OI-PRICE DIVERGENCE: OI data - current: {current_oi}, previous: {previous_oi}, history entries: {history_count}")
            else:
                self.logger.debug(f"OI-PRICE DIVERGENCE: OI not a dictionary: {type(oi_dump)}")
        
        try:
            # Check if we have the required data
            if 'ohlcv' not in market_data:
                self.logger.warning("Missing OHLCV data for price-OI divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            ohlcv_data = market_data['ohlcv']
            
            # Check if ohlcv_data is a dictionary
            if not isinstance(ohlcv_data, dict):
                self.logger.warning(f"OHLCV data is not a dictionary: {type(ohlcv_data)}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log available timeframes
            self.logger.debug(f"Available OHLCV timeframes: {list(ohlcv_data.keys())}")
                
            # Try to find a valid timeframe
            valid_timeframe = None
            ohlcv_df = None
            
            # First check for direct DataFrame access (for backward compatibility)
            for tf in ['base', 'ltf', '1', '5']:
                if tf in ohlcv_data:
                    # Check if it's a direct DataFrame
                    if isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
                    # Check if it's a nested structure with 'data' key
                    elif isinstance(ohlcv_data[tf], dict) and 'data' in ohlcv_data[tf] and isinstance(ohlcv_data[tf]['data'], pd.DataFrame) and not ohlcv_data[tf]['data'].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]['data']
                        self.logger.debug(f"Found nested DataFrame at timeframe {tf}['data']")
                        break
            
            # Also check for timeframes with '_direct' suffix (added for testing)
            if not valid_timeframe:
                for tf in ['base_direct', 'ltf_direct', '1_direct', '5_direct']:
                    if tf in ohlcv_data and isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
            
            if not valid_timeframe or ohlcv_df is None:
                self.logger.warning("No valid OHLCV timeframe found for price-OI divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Verify that the DataFrame has the required columns
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in ohlcv_df.columns]
            if missing_columns:
                self.logger.warning(f"OHLCV data missing required columns: {missing_columns}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log OHLCV DataFrame info
            self.logger.debug(f"OHLCV DataFrame for {valid_timeframe}: shape={ohlcv_df.shape}, columns={list(ohlcv_df.columns)}")
            self.logger.debug(f"OHLCV DataFrame index type: {type(ohlcv_df.index)}")
            if len(ohlcv_df) > 0:
                self.logger.debug(f"OHLCV first row: {ohlcv_df.iloc[0].to_dict()}")
                self.logger.debug(f"OHLCV last row: {ohlcv_df.iloc[-1].to_dict()}")
                
            # Use configurable lookback period
            lookback = min(len(ohlcv_df), self.divergence_lookback)
            if lookback < 2:
                self.logger.warning(f"Insufficient OHLCV data for divergence calculation: {len(ohlcv_df)} rows")
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.debug(f"Using lookback period of {lookback} candles for divergence calculation")
            
            # Check if we have open interest data at the top level
            oi_data = None
            oi_history = []
            
            # First check for open interest at the top level (new structure)
            if 'open_interest' in market_data:
                oi_data = market_data['open_interest']
                self.logger.debug("Found open interest data at top level")
                if isinstance(oi_data, dict):
                    self.logger.debug(f"Open interest data keys: {list(oi_data.keys())}")
            # Fallback to sentiment.open_interest for backward compatibility
            elif 'sentiment' in market_data and 'open_interest' in market_data['sentiment']:
                oi_data = market_data['sentiment']['open_interest']
                self.logger.debug("Found open interest data in sentiment section")
                if isinstance(oi_data, dict):
                    self.logger.debug(f"Open interest data keys: {list(oi_data.keys())}")
            else:
                self.logger.warning("Missing open interest data for price-OI divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Get open interest history
            if 'open_interest_history' in market_data and isinstance(market_data['open_interest_history'], list):
                # ADDED: Check for direct reference first
                oi_history = market_data['open_interest_history']
                self.logger.debug(f"Using direct open_interest_history reference with {len(oi_history)} entries")
                if len(oi_history) > 0:
                    first_entry = oi_history[0]
                    if isinstance(first_entry, dict):
                        timestamp = first_entry.get('timestamp', 'N/A')
                        value = first_entry.get('value', 'N/A')
                        self.logger.debug(f"First OI entry: timestamp={timestamp}, value={value}")
                    else:
                        self.logger.debug(f"First OI entry: {first_entry}")
            elif isinstance(oi_data, dict) and 'history' in oi_data and isinstance(oi_data['history'], list):
                oi_history = oi_data['history']
                self.logger.debug(f"Using open interest history from 'history' key with {len(oi_history)} entries")
                # Enhanced debugging: Sample of history data
                if len(oi_history) > 0:
                    first_entry = oi_history[0]
                    if isinstance(first_entry, dict):
                        timestamp = first_entry.get('timestamp', 'N/A')
                        value = first_entry.get('value', 'N/A')
                        self.logger.debug(f"OI-PRICE DIVERGENCE: First history entry: timestamp={timestamp}, value={value}")
                    else:
                        self.logger.debug(f"OI-PRICE DIVERGENCE: First history entry: {first_entry}")
                    
                    if len(oi_history) > 1:
                        second_entry = oi_history[1]
                        if isinstance(second_entry, dict):
                            timestamp = second_entry.get('timestamp', 'N/A')
                            value = second_entry.get('value', 'N/A')
                            self.logger.debug(f"OI-PRICE DIVERGENCE: Second history entry: timestamp={timestamp}, value={value}")
                        else:
                            self.logger.debug(f"OI-PRICE DIVERGENCE: Second history entry: {second_entry}")
            elif isinstance(oi_data, list):
                # If OI data is already a list
                oi_history = oi_data
                self.logger.debug(f"Using open interest data directly as list with {len(oi_history)} entries")
            else:
                # Enhanced debugging: Log what was found in the structure
                self.logger.warning(f"OI-PRICE DIVERGENCE: No proper history found. OI data type: {type(oi_data)}")
                if isinstance(oi_data, dict):
                    self.logger.warning(f"OI-PRICE DIVERGENCE: OI data keys: {list(oi_data.keys())}")
                # If we don't have history, we can't calculate divergence
                self.logger.warning("No open interest history available for divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            if len(oi_history) < 2:
                self.logger.warning(f"Insufficient open interest history for divergence calculation: {len(oi_history)} entries")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Log sample of OI history
            if len(oi_history) > 0:
                sample_entry = oi_history[0]
                self.logger.debug(f"OI history sample entry: {sample_entry}")
                if isinstance(sample_entry, dict):
                    self.logger.debug(f"OI history entry keys: {list(sample_entry.keys())}")
            
            # Get timestamps for alignment
            # Check if we have a timestamp column or need to use the index
            if 'timestamp' in ohlcv_df.columns:
                start_timestamp = ohlcv_df.iloc[-lookback]['timestamp']
                self.logger.debug(f"Using timestamp column for alignment, start_timestamp: {start_timestamp}")
            else:
                # Try to use index as timestamp
                try:
                    start_timestamp = ohlcv_df.index[-lookback]
                    self.logger.debug(f"Using index for alignment, start_timestamp: {start_timestamp}")
                except Exception as e:
                    self.logger.warning(f"Failed to get start timestamp from OHLCV data: {str(e)}")
                    return {'type': 'neutral', 'strength': 0.0}
            
            # Ensure start_timestamp is numeric
            try:
                # Convert pandas Timestamp to milliseconds since epoch
                if isinstance(start_timestamp, pd.Timestamp):
                    start_timestamp_orig = start_timestamp
                    start_timestamp = int(start_timestamp.timestamp() * 1000)
                    self.logger.debug(f"Converted start_timestamp from pd.Timestamp {start_timestamp_orig} to {start_timestamp}")
                elif isinstance(start_timestamp, str):
                    start_timestamp_orig = start_timestamp
                    start_timestamp = pd.to_numeric(start_timestamp)
                    self.logger.debug(f"Converted start_timestamp from string {start_timestamp_orig} to {start_timestamp}")
            except Exception as e:
                self.logger.warning(f"Failed to convert start_timestamp to numeric: {str(e)}")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Filter OI history to match the same time period as price data
            aligned_oi_values = []
            aligned_timestamps = []
            
            self.logger.debug(f"Aligning OI history with price data, start_timestamp: {start_timestamp}")
            
            for entry in oi_history:
                entry_timestamp = entry['timestamp'] if isinstance(entry, dict) and 'timestamp' in entry else None
                
                # Ensure entry_timestamp is numeric for comparison
                try:
                    if entry_timestamp is not None:
                        entry_timestamp = pd.to_numeric(entry_timestamp) if isinstance(entry_timestamp, (str, pd.Timestamp)) else entry_timestamp
                        
                        if entry_timestamp >= start_timestamp:
                            entry_value = float(entry['value']) if isinstance(entry, dict) and 'value' in entry else float(entry)
                            aligned_oi_values.append(entry_value)
                            aligned_timestamps.append(entry_timestamp)
                except Exception as e:
                    self.logger.debug(f"Failed to process OI entry timestamp: {str(e)}")
                    continue
            
            # Continue with aligned OI values
            if len(aligned_oi_values) < 2:
                self.logger.warning(f"Insufficient aligned OI data for divergence calculation: {len(aligned_oi_values)} entries")
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.debug(f"Successfully aligned {len(aligned_oi_values)} OI entries with price data")
            self.logger.debug(f"Aligned OI values: min={min(aligned_oi_values):.2f}, max={max(aligned_oi_values):.2f}, mean={sum(aligned_oi_values)/len(aligned_oi_values):.2f}")
            
            # Calculate price trend
            price_changes = ohlcv_df['close'].diff().tail(lookback)
            price_trend = price_changes.sum()
            
            self.logger.debug(f"Price trend over {lookback} candles: {price_trend:.4f}")
            self.logger.debug(f"Price changes: min={price_changes.min():.4f}, max={price_changes.max():.4f}, mean={price_changes.mean():.4f}")
            
            # Calculate OI changes
            oi_changes = [aligned_oi_values[i] - aligned_oi_values[i-1] for i in range(1, len(aligned_oi_values))]
            
            self.logger.debug(f"OI changes: {len(oi_changes)} entries")
            self.logger.debug(f"OI changes: min={min(oi_changes):.2f}, max={max(oi_changes):.2f}, mean={sum(oi_changes)/len(oi_changes):.2f}")
            
            # Enhanced debugging: Detailed OI change data (only show first few entries)
            if self.debug_level >= 3:  # Only show detailed changes at highest debug level
                self.logger.debug("OI-PRICE DIVERGENCE: Detailed OI changes (first 3 entries):")
                for i, change in enumerate(oi_changes[:3]):  # Only show first 3 entries
                    self.logger.debug(f"  Entry {i}: Value: {aligned_oi_values[i]:.2f}, Previous: {aligned_oi_values[i-1]:.2f}, Change: {change:.2f}")
                if len(oi_changes) > 3:
                    self.logger.debug(f"  ... and {len(oi_changes) - 3} more entries")
            
            # Apply time weighting if enabled
            weighted_oi_changes = []
            if self.time_weighting_enabled:
                self.logger.debug(f"Applying time weighting with recency factor {self.recency_factor}")
                for i, change in enumerate(oi_changes):
                    # Apply exponential weighting - more recent changes get higher weight
                    weight = self.recency_factor ** (len(oi_changes) - 1 - i)
                    weighted_oi_changes.append(change * weight)
                    # Only log detailed weighting at highest debug level
                    if self.debug_level >= 3:
                        self.logger.debug(f"OI Change {i}: {change:.2f}, Weight: {weight:.2f}, Weighted: {change * weight:.2f}")
            else:
                self.logger.debug("Time weighting disabled, using raw OI changes")
                weighted_oi_changes = oi_changes
            
            # Calculate OI trend with time weighting
            oi_trend = sum(weighted_oi_changes)
            
            # For normalization, we need the sum of absolute weighted values
            abs_sum = sum(abs(c) for c in weighted_oi_changes)
            
            self.logger.debug(f"OI trend: {oi_trend:.4f}, Absolute sum: {abs_sum:.4f}")
            
            # Calculate divergence
            divergence_strength = 0.0
            divergence_type = 'neutral'
            
            # Enhanced debugging: Detailed comparison
            self.logger.debug(f"OI-PRICE DIVERGENCE: Final comparison - Price trend: {price_trend:.4f}, OI trend: {oi_trend:.4f}")
            
            if (price_trend > 0 and oi_trend < 0):
                # Bearish divergence: Price up, OI down
                divergence_type = 'bearish'
                divergence_strength = min(abs(oi_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bearish divergence: Price trend={price_trend:.4f} (up), OI trend={oi_trend:.4f} (down)")
                # Enhanced debugging: Strength calculation (only at highest debug level)
                if self.debug_level >= 3:
                    self.logger.debug(f"OI-PRICE DIVERGENCE: Bearish strength calculation: |{oi_trend:.4f}| / max(1, {abs_sum:.4f}) * 100 = {divergence_strength:.2f}")
            elif (price_trend < 0 and oi_trend > 0):
                # Bullish divergence: Price down, OI up
                divergence_type = 'bullish'
                divergence_strength = min(abs(oi_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bullish divergence: Price trend={price_trend:.4f} (down), OI trend={oi_trend:.4f} (up)")
                # Enhanced debugging: Strength calculation (only at highest debug level)
                if self.debug_level >= 3:
                    self.logger.debug(f"OI-PRICE DIVERGENCE: Bullish strength calculation: |{oi_trend:.4f}| / max(1, {abs_sum:.4f}) * 100 = {divergence_strength:.2f}")
            else:
                self.logger.debug(f"No divergence detected: Price trend={price_trend:.4f}, OI trend={oi_trend:.4f}")
                # Enhanced debugging: Why no divergence was detected (only at highest debug level)
                if self.debug_level >= 3:
                    if price_trend > 0 and oi_trend >= 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: Both price and OI trending up (no divergence)")
                    elif price_trend < 0 and oi_trend <= 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: Both price and OI trending down (no divergence)")
                    elif price_trend == 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: No price trend detected")
                    elif oi_trend == 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: No OI trend detected")
            
            # Only return significant divergences
            if divergence_strength < self.divergence_strength_threshold:
                self.logger.debug(f"Divergence strength {divergence_strength:.2f} below threshold {self.divergence_strength_threshold}, returning neutral")
                
                # Log execution time
                execution_time = time.time() - start_time
                self.logger.debug(f"Price-OI divergence calculation completed in {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                
                return {'type': 'neutral', 'strength': 0.0}
                
            self.logger.info(f"Price-OI divergence: {divergence_type}, strength: {divergence_strength:.2f}")
            
            # Log execution time
            execution_time = time.time() - start_time
            self.logger.debug(f"Price-OI divergence calculation completed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            result = {
                'type': divergence_type,
                'strength': float(divergence_strength)
            }
            
            # Store in cache before returning
            self._cache[cache_key] = result
            return result
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error calculating price-OI divergence: {str(e)}")
            self.logger.error(f"OI-PRICE DIVERGENCE Error traceback: {traceback.format_exc()}")
            
            # Log market data structure for debugging (concise version)
            try:
                if 'open_interest' in market_data:
                    oi_data = market_data['open_interest']
                    if isinstance(oi_data, dict):
                        history_count = len(oi_data.get('history', []))
                        current_oi = oi_data.get('current', 'N/A')
                        self.logger.error(f"OI-PRICE DIVERGENCE: Error with OI structure - current: {current_oi}, history entries: {history_count}")
                    else:
                        self.logger.error(f"OI-PRICE DIVERGENCE: Error with OI structure - type: {type(oi_data)}")
                self.logger.error(f"OI-PRICE DIVERGENCE: Market data keys: {list(market_data.keys())}")
            except Exception as json_err:
                self.logger.error(f"OI-PRICE DIVERGENCE: Could not log market data structure due to error: {str(json_err)}")
                
            # Log execution time even in error case
            execution_time = time.time() - start_time if 'start_time' in locals() else -1
            self.logger.debug(f"Price-OI divergence calculation failed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            return {'type': 'neutral', 'strength': 0.0}

    def _calculate_trade_flow(self, trades_df: Union[pd.DataFrame, Dict, List]) -> float:
        """Calculate trade flow indicator (buy vs sell pressure).
        
        Args:
            trades_df: DataFrame, dictionary or list containing trade data
            
        Returns:
            float: Trade flow value between -1 and 1
        """
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING TRADE FLOW CALCULATION")
        self.logger.debug("=" * 50)
        
        try:
            # Initialize variables
            df = None
            
            # Log input data type
            self.logger.debug(f"Input trades_df type: {type(trades_df)}")
            
            # Handle different input types
            if isinstance(trades_df, pd.DataFrame):
                # Input is already a DataFrame
                df = trades_df.copy()
                self.logger.debug(f"Using trades DataFrame directly, shape: {df.shape}, columns: {list(df.columns)}")
            
            elif isinstance(trades_df, list) and trades_df:
                # Input is a list of trade dictionaries
                try:
                    self.logger.debug(f"Input is a list with {len(trades_df)} trade records")
                    if len(trades_df) > 0:
                        self.logger.debug(f"First trade sample: {trades_df[0]}")
                    df = pd.DataFrame(trades_df)
                    self.logger.debug(f"Converted trades list to DataFrame with {len(trades_df)} records, columns: {list(df.columns)}")
                except Exception as e:
                    self.logger.error(f"Failed to convert trades list to DataFrame: {e}")
                    self.logger.debug(traceback.format_exc())
                    return 0.0
            
            elif isinstance(trades_df, dict):
                # Input is a dictionary, try to find trades data
                self.logger.debug(f"Input is a dictionary with keys: {list(trades_df.keys())}")
                
                if 'trades_df' in trades_df and isinstance(trades_df['trades_df'], pd.DataFrame):
                    df = trades_df['trades_df'].copy()
                    self.logger.debug(f"Using trades_df from dictionary, shape: {df.shape}, columns: {list(df.columns)}")
                
                elif 'trades' in trades_df and isinstance(trades_df['trades'], list) and trades_df['trades']:
                    try:
                        self.logger.debug(f"Using trades list from dictionary with {len(trades_df['trades'])} records")
                        if len(trades_df['trades']) > 0:
                            self.logger.debug(f"First trade sample: {trades_df['trades'][0]}")
                        df = pd.DataFrame(trades_df['trades'])
                        self.logger.debug(f"Converted trades list from dictionary to DataFrame, shape: {df.shape}, columns: {list(df.columns)}")
                    except Exception as e:
                        self.logger.error(f"Failed to convert trades list from dictionary to DataFrame: {e}")
                        self.logger.debug(traceback.format_exc())
                        return 0.0
                
                elif 'processed_trades' in trades_df and isinstance(trades_df['processed_trades'], list) and trades_df['processed_trades']:
                    try:
                        self.logger.debug(f"Using processed_trades from dictionary with {len(trades_df['processed_trades'])} records")
                        if len(trades_df['processed_trades']) > 0:
                            self.logger.debug(f"First processed trade sample: {trades_df['processed_trades'][0]}")
                        df = pd.DataFrame(trades_df['processed_trades'])
                        self.logger.debug(f"Converted processed_trades to DataFrame, shape: {df.shape}, columns: {list(df.columns)}")
                    except Exception as e:
                        self.logger.error(f"Failed to convert processed_trades to DataFrame: {e}")
                        self.logger.debug(traceback.format_exc())
                        return 0.0
                
                else:
                    self.logger.warning("No valid trade data found in dictionary")
                    return 0.0
            
            else:
                self.logger.error(f"Unsupported trades_df type: {type(trades_df)}")
                return 0.0
            
            # Check if we have a valid DataFrame
            if df is None or df.empty:
                self.logger.warning("No trade data available for trade flow calculation")
                return 0.0
            
            # Log DataFrame info
            self.logger.debug(f"Trade DataFrame info: {len(df)} rows, columns: {list(df.columns)}")
            
            # Map column names to standard names
            column_mappings = {
                'side': ['side', 'S', 'type', 'trade_type'],
                'amount': ['amount', 'size', 'v', 'volume', 'qty', 'quantity']
            }
            
            # Try to find and map the required columns
            for std_col, possible_cols in column_mappings.items():
                if std_col not in df.columns:
                    for col in possible_cols:
                        if col in df.columns:
                            df[std_col] = df[col]
                            self.logger.debug(f"Mapped '{col}' to '{std_col}'")
                            break
            
            # Check if we have the required columns after mapping
            if 'side' not in df.columns or 'amount' not in df.columns:
                missing = []
                if 'side' not in df.columns:
                    missing.append('side')
                if 'amount' not in df.columns:
                    missing.append('amount')
                self.logger.warning(f"Missing required columns after mapping: {missing}. Available columns: {list(df.columns)}")
                return 0.0
            
            # Normalize side values
            try:
                # Convert to string first to handle numeric side values
                df['side'] = df['side'].astype(str)
                self.logger.debug(f"Side value counts before normalization: {df['side'].value_counts().to_dict()}")
                
                # Ensure amount column is numeric
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                
                # Log amount statistics before dropping NaN values
                amount_stats_before = {
                    'count': len(df),
                    'nan_count': df['amount'].isna().sum(),
                    'min': df['amount'].min() if not df['amount'].isna().all() else 'N/A',
                    'max': df['amount'].max() if not df['amount'].isna().all() else 'N/A',
                    'mean': df['amount'].mean() if not df['amount'].isna().all() else 'N/A',
                    'sum': df['amount'].sum() if not df['amount'].isna().all() else 'N/A'
                }
                self.logger.debug(f"Amount statistics before dropping NaN: {amount_stats_before}")
                
                # Drop rows with non-numeric amounts
                df = df.dropna(subset=['amount'])
                
                # Log amount statistics after dropping NaN values
                amount_stats_after = {
                    'count': len(df),
                    'min': df['amount'].min() if not df.empty else 'N/A',
                    'max': df['amount'].max() if not df.empty else 'N/A',
                    'mean': df['amount'].mean() if not df.empty else 'N/A',
                    'sum': df['amount'].sum() if not df.empty else 'N/A'
                }
                self.logger.debug(f"Amount statistics after dropping NaN: {amount_stats_after}")
                
                # Normalize to lowercase
                df['side'] = df['side'].str.lower()
                
                # Map different side values to buy/sell
                buy_values = ['buy', 'b', 'bid', '1', 'true', 'long']
                sell_values = ['sell', 's', 'ask', 'offer', '-1', 'false', 'short']
                
                # Create a normalized side column
                df['norm_side'] = 'unknown'
                df.loc[df['side'].isin(buy_values), 'norm_side'] = 'buy'
                df.loc[df['side'].isin(sell_values), 'norm_side'] = 'sell'
                
                # Log normalized side value counts
                norm_side_counts = df['norm_side'].value_counts().to_dict()
                self.logger.debug(f"Normalized side value counts: {norm_side_counts}")
                
                # Log unknown sides
                unknown_count = (df['norm_side'] == 'unknown').sum()
                if unknown_count > 0:
                    unknown_pct = (unknown_count / len(df)) * 100
                    self.logger.warning(f"Found {unknown_count} trades ({unknown_pct:.2f}%) with unknown side values")
                    
                    # Log some examples of unknown side values
                    unknown_sides = df[df['norm_side'] == 'unknown']['side'].unique()
                    self.logger.debug(f"Examples of unknown side values: {unknown_sides[:10]}")
                    
                    # Randomly assign sides to unknown values to avoid bias
                    unknown_mask = df['norm_side'] == 'unknown'
                    random_sides = np.random.choice(['buy', 'sell'], size=unknown_count)
                    df.loc[unknown_mask, 'norm_side'] = random_sides
                    self.logger.debug(f"Randomly assigned sides to {unknown_count} trades")
                    
                    # Log updated normalized side value counts
                    updated_norm_side_counts = df['norm_side'].value_counts().to_dict()
                    self.logger.debug(f"Updated normalized side value counts after random assignment: {updated_norm_side_counts}")
                
                # Calculate buy and sell volumes
                buy_volume = pd.to_numeric(df[df['norm_side'] == 'buy']['amount'].sum(), errors='coerce')
                sell_volume = pd.to_numeric(df[df['norm_side'] == 'sell']['amount'].sum(), errors='coerce')
                
                # Replace NaN with 0
                buy_volume = 0.0 if pd.isna(buy_volume) else float(buy_volume)
                sell_volume = 0.0 if pd.isna(sell_volume) else float(sell_volume)
                
                self.logger.debug(f"Trade flow volumes: buy_volume={buy_volume}, sell_volume={sell_volume}, types: {type(buy_volume)}, {type(sell_volume)}")
                
                total_volume = buy_volume + sell_volume
                
                if total_volume > 0:
                    # Calculate trade flow: range from -1 (all sells) to 1 (all buys)
                    trade_flow = (buy_volume - sell_volume) / total_volume
                    buy_pct = (buy_volume / total_volume) * 100
                    sell_pct = (sell_volume / total_volume) * 100
                    self.logger.debug(f"Trade flow calculated: {trade_flow:.4f} (buy: {buy_volume:.4f} [{buy_pct:.2f}%], sell: {sell_volume:.4f} [{sell_pct:.2f}%])")
                    
                    # Log execution time
                    execution_time = time.time() - start_time
                    self.logger.debug(f"Trade flow calculation completed in {execution_time:.4f} seconds")
                    self.logger.debug("=" * 50)
                    
                    return float(trade_flow)
                else:
                    self.logger.warning("Zero total volume, cannot calculate trade flow")
                    execution_time = time.time() - start_time
                    self.logger.debug(f"Trade flow calculation completed in {execution_time:.4f} seconds with zero volume")
                    self.logger.debug("=" * 50)
                    return 0.0
                    
            except Exception as e:
                self.logger.error(f"Error calculating trade flow volumes: {str(e)}")
                self.logger.debug(traceback.format_exc())
                execution_time = time.time() - start_time
                self.logger.debug(f"Trade flow calculation failed after {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error in trade flow calculation: {str(e)}")
            self.logger.debug(traceback.format_exc())
            execution_time = time.time() - start_time
            self.logger.debug(f"Trade flow calculation failed after {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            return 0.0

    # ===== SMART MONEY CONCEPTS - LIQUIDITY ZONES =====
    # Moved from price_structure_indicators.py as this is pure order flow analysis
    
    def _calculate_liquidity_zones_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_price_cvd_divergence(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate divergence between price and CVD.
        
        This method detects when price is moving in one direction but CVD is moving in the opposite direction,
        which can indicate potential reversals.
        
        Args:
            market_data: Dictionary containing market data with OHLCV and trades
            
        Returns:
            Dict: Divergence information including type and strength
        """
        # Use caching to avoid redundant calculations
        cache_key = 'price_cvd_divergence'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        calculation_start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING PRICE-CVD DIVERGENCE CALCULATION")
        self.logger.debug("=" * 50)
        
        try:
            # Check if we have the required data
            if 'ohlcv' not in market_data:
                self.logger.warning("Missing OHLCV data for price-CVD divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            ohlcv_data = market_data['ohlcv']
            
            # Check if ohlcv_data is a dictionary
            if not isinstance(ohlcv_data, dict):
                self.logger.warning(f"OHLCV data is not a dictionary: {type(ohlcv_data)}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log available timeframes
            self.logger.debug(f"Available OHLCV timeframes: {list(ohlcv_data.keys())}")
                
            # Try to find a valid timeframe
            valid_timeframe = None
            ohlcv_df = None
            
            # First check for direct DataFrame access (for backward compatibility)
            for tf in ['base', 'ltf', '1', '5']:
                if tf in ohlcv_data:
                    # Check if it's a direct DataFrame
                    if isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
                    # Check if it's a nested structure with 'data' key
                    elif isinstance(ohlcv_data[tf], dict) and 'data' in ohlcv_data[tf] and isinstance(ohlcv_data[tf]['data'], pd.DataFrame) and not ohlcv_data[tf]['data'].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]['data']
                        self.logger.debug(f"Found nested DataFrame at timeframe {tf}['data']")
                        break
            
            # Also check for timeframes with '_direct' suffix (added for testing)
            if not valid_timeframe:
                for tf in ['base_direct', 'ltf_direct', '1_direct', '5_direct']:
                    if tf in ohlcv_data and isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
            
            if not valid_timeframe or ohlcv_df is None:
                self.logger.warning("No valid OHLCV timeframe found for price-CVD divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Verify that the DataFrame has the required columns
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in ohlcv_df.columns]
            if missing_columns:
                self.logger.warning(f"OHLCV data missing required columns: {missing_columns}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log OHLCV DataFrame info
            self.logger.debug(f"OHLCV DataFrame for {valid_timeframe}: shape={ohlcv_df.shape}, columns={list(ohlcv_df.columns)}")
            self.logger.debug(f"OHLCV DataFrame index type: {type(ohlcv_df.index)}")
            if len(ohlcv_df) > 0:
                self.logger.debug(f"OHLCV first row: {ohlcv_df.iloc[0].to_dict()}")
                self.logger.debug(f"OHLCV last row: {ohlcv_df.iloc[-1].to_dict()}")
                
            # Use configurable lookback period
            lookback = min(len(ohlcv_df), self.divergence_lookback)
            if lookback < 2:
                self.logger.warning(f"Insufficient OHLCV data for divergence calculation: {len(ohlcv_df)} rows")
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.debug(f"Using lookback period of {lookback} candles for divergence calculation")
            
            # Get trades data
            trades = market_data.get('trades', [])
            if not trades or len(trades) < self.min_trades:
                self.logger.warning(f"Insufficient trade data for price-CVD divergence calculation: {len(trades)} trades, minimum required: {self.min_trades}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Convert trades to DataFrame if needed
            trades_df = trades if isinstance(trades, pd.DataFrame) else pd.DataFrame(trades)
            
            # Log trades DataFrame info
            self.logger.debug(f"Trades DataFrame: shape={trades_df.shape}, columns={list(trades_df.columns)}")
            
            # Ensure we have timestamp in trades
            if 'time' not in trades_df.columns and 'timestamp' in trades_df.columns:
                trades_df['time'] = trades_df['timestamp']
                self.logger.debug("Mapped 'timestamp' to 'time' in trades DataFrame")
            elif 'time' not in trades_df.columns and 'T' in trades_df.columns:
                trades_df['time'] = trades_df['T']
                self.logger.debug("Mapped 'T' to 'time' in trades DataFrame")
                
            if 'time' not in trades_df.columns:
                self.logger.warning("Missing time/timestamp in trades data for price-CVD divergence")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Ensure time column is numeric
            try:
                trades_df['time'] = pd.to_numeric(trades_df['time'])
                self.logger.debug(f"Converted time column to numeric. Sample values: {trades_df['time'].head(3).tolist()}")
            except Exception as e:
                self.logger.warning(f"Failed to convert time column to numeric: {str(e)}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Ensure we have side in trades
            if 'side' not in trades_df.columns and 'S' in trades_df.columns:
                trades_df['side'] = trades_df['S']
                self.logger.debug("Mapped 'S' to 'side' in trades DataFrame")
                
            if 'side' not in trades_df.columns:
                self.logger.warning("Missing side in trades data for price-CVD divergence")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Ensure we have amount/size in trades
            if 'amount' not in trades_df.columns:
                for col in ['size', 'v', 'volume', 'qty', 'quantity']:
                    if col in trades_df.columns:
                        trades_df['amount'] = trades_df[col]
                        self.logger.debug(f"Mapped '{col}' to 'amount' in trades DataFrame")
                        break
                        
            if 'amount' not in trades_df.columns:
                self.logger.warning("Missing amount/size in trades data for price-CVD divergence")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Get price trend
            price_changes = ohlcv_df['close'].diff().tail(lookback)
            price_trend = price_changes.sum()
            
            self.logger.debug(f"Price trend over {lookback} candles: {price_trend:.4f}")
            self.logger.debug(f"Price changes: min={price_changes.min():.4f}, max={price_changes.max():.4f}, mean={price_changes.mean():.4f}")
            
            # Calculate CVD for each candle period
            candle_cvds = []
            candle_timestamps = []
            
            # Ensure proper time tracking for candle processing
            candle_start_time = time.time()
            
            for i in range(1, lookback + 1):
                if i >= len(ohlcv_df):
                    break
                    
                # Get timestamp range for this candle
                # Check if we have a timestamp column or need to use the index
                if 'timestamp' in ohlcv_df.columns:
                    candle_end_time = ohlcv_df.iloc[-i]['timestamp']
                    candle_start_time_ts = ohlcv_df.iloc[-(i+1)]['timestamp'] if i+1 < len(ohlcv_df) else ohlcv_df.iloc[-i]['timestamp'] - 60000  # Fallback: 1 minute earlier
                    self.logger.debug(f"Candle {i} timestamp from column: start={candle_start_time_ts}, end={candle_end_time}")
                    # Save the timestamp for potential interpolation later
                    candle_timestamps.append(candle_end_time)
                else:
                    # Try to use index as timestamp
                    try:
                        candle_end_time = ohlcv_df.index[-i]
                        candle_start_time_ts = ohlcv_df.index[-(i+1)] if i+1 < len(ohlcv_df) else candle_end_time - pd.Timedelta(minutes=1)
                        self.logger.debug(f"Candle {i} timestamp from index: start={candle_start_time_ts}, end={candle_end_time}")
                        # Save the timestamp for potential interpolation later
                        candle_timestamps.append(candle_end_time)
                    except Exception as e:
                        self.logger.debug(f"Failed to get timestamp from index: {str(e)}")
                        continue
                
                # Ensure start_time and end_time are numeric
                try:
                    # Convert pandas Timestamp to milliseconds since epoch
                    if isinstance(candle_start_time_ts, pd.Timestamp):
                        start_time_orig = candle_start_time_ts
                        candle_start_time_ts = int(candle_start_time_ts.timestamp() * 1000)
                        self.logger.debug(f"Converted start_time from pd.Timestamp {start_time_orig} to {candle_start_time_ts}")
                    elif isinstance(candle_start_time_ts, str):
                        start_time_orig = candle_start_time_ts
                        candle_start_time_ts = pd.to_numeric(candle_start_time_ts)
                        self.logger.debug(f"Converted start_time from string {start_time_orig} to {candle_start_time_ts}")
                    
                    if isinstance(candle_end_time, pd.Timestamp):
                        end_time_orig = candle_end_time
                        candle_end_time = int(candle_end_time.timestamp() * 1000)
                        self.logger.debug(f"Converted end_time from pd.Timestamp {end_time_orig} to {candle_end_time}")
                    elif isinstance(candle_end_time, str):
                        end_time_orig = candle_end_time
                        candle_end_time = pd.to_numeric(candle_end_time)
                        self.logger.debug(f"Converted end_time from string {end_time_orig} to {candle_end_time}")
                except Exception as e:
                    self.logger.debug(f"Failed to convert timestamp to numeric: {str(e)}")
                    continue
                
                # Filter trades for this candle
                candle_trades_filtered = trades_df[(trades_df['time'] >= candle_start_time_ts) & (trades_df['time'] < candle_end_time)]
                
                if candle_trades_filtered.empty:
                    self.logger.debug(f"No trades found for candle {i} (time range: {candle_start_time_ts} to {candle_end_time})")
                    candle_cvds.append(0)
                    continue
                
                # Create a copy to avoid SettingWithCopyWarning
                candle_trades = candle_trades_filtered.copy()
                
                self.logger.debug(f"Found {len(candle_trades)} trades for candle {i}")
                    
                # Calculate CVD for this candle
                try:
                    # Log the unique side values to aid in debugging
                    unique_sides = candle_trades['side'].astype(str).unique()
                    self.logger.debug(f"Unique side values in candle {i} trades: {unique_sides}")
                    
                    # Ensure amount column is numeric
                    try:
                        candle_trades.loc[:, 'amount'] = pd.to_numeric(candle_trades['amount'], errors='coerce')
                    except Exception as e:
                        self.logger.warning(f"Error converting amount to numeric: {str(e)}, trying fallback")
                        candle_trades.loc[:, 'amount'] = candle_trades['amount'].apply(lambda x: float(x) if isinstance(x, str) else x)
                    
                    # More robust way to determine buy/sell sides
                    def is_buy_side(side_val):
                        if pd.isna(side_val):
                            return False
                        s = str(side_val).lower().strip()
                        return s in ['buy', 'b', '1', 'true', 'bid', 'long']
                    
                    def is_sell_side(side_val):
                        if pd.isna(side_val):
                            return False
                        s = str(side_val).lower().strip()
                        return s in ['sell', 's', '-1', 'false', 'ask', 'short']
                    
                    # Apply the side detection functions
                    candle_trades.loc[:, 'is_buy'] = candle_trades['side'].apply(is_buy_side)
                    candle_trades.loc[:, 'is_sell'] = candle_trades['side'].apply(is_sell_side)
                    
                    # Log side detection results
                    buy_count = candle_trades['is_buy'].sum()
                    sell_count = candle_trades['is_sell'].sum()
                    unclassified = len(candle_trades) - buy_count - sell_count
                    self.logger.debug(f"Side classification: buy={buy_count}, sell={sell_count}, unclassified={unclassified}")
                    
                    if unclassified > 0 and len(unique_sides) > 0:
                        # If we have unclassified trades, try a more flexible approach
                        if all(side.lower() in ['buy', 'sell'] for side in unique_sides if isinstance(side, str)):
                            self.logger.debug(f"Using simpler case-insensitive matching for side values")
                            candle_trades.loc[:, 'is_buy'] = candle_trades['side'].astype(str).str.lower() == 'buy'
                            candle_trades.loc[:, 'is_sell'] = candle_trades['side'].astype(str).str.lower() == 'sell'
                            buy_count = candle_trades['is_buy'].sum()
                            sell_count = candle_trades['is_sell'].sum()
                            unclassified = len(candle_trades) - buy_count - sell_count
                            self.logger.debug(f"Updated side classification: buy={buy_count}, sell={sell_count}, unclassified={unclassified}")
                    
                    # Check for any remaining unclassified trades
                    if unclassified > 0 and buy_count == 0 and sell_count == 0:
                        # Last resort attempt - case-insensitive partial matching
                        self.logger.debug(f"Attempting case-insensitive partial matching for sides")
                        candle_trades.loc[:, 'is_buy'] = candle_trades['side'].astype(str).str.lower().str.contains('buy', na=False) | candle_trades['side'].astype(str).str.lower().str.contains('bid', na=False)
                        candle_trades.loc[:, 'is_sell'] = candle_trades['side'].astype(str).str.lower().str.contains('sell', na=False) | candle_trades['side'].astype(str).str.lower().str.contains('ask', na=False)
                        buy_count = candle_trades['is_buy'].sum()
                        sell_count = candle_trades['is_sell'].sum()
                        self.logger.debug(f"Final side classification: buy={buy_count}, sell={sell_count}, unclassified={len(candle_trades) - buy_count - sell_count}")
                    
                    # Calculate buy and sell volumes
                    buy_volume = candle_trades[candle_trades['is_buy']]['amount'].sum()
                    sell_volume = candle_trades[candle_trades['is_sell']]['amount'].sum()
                    
                    # Replace NaN with 0
                    buy_volume = 0.0 if pd.isna(buy_volume) else float(buy_volume)
                    sell_volume = 0.0 if pd.isna(sell_volume) else float(sell_volume)
                    
                    # Additional diagnostic for debugging
                    if buy_volume == 0 and sell_volume == 0:
                        # This shouldn't happen if we have trades and properly classified sides
                        # Log a sample of the trades to diagnose the issue
                        if not candle_trades.empty:
                            sample_trades = candle_trades.head(3)
                            self.logger.warning(f"Both buy and sell volumes are 0 despite having {len(candle_trades)} trades. Sample trades:")
                            for idx, trade in sample_trades.iterrows():
                                self.logger.warning(f"Trade {idx}: side={trade['side']}, amount={trade['amount']}, is_buy={trade.get('is_buy', False)}, is_sell={trade.get('is_sell', False)}")
                            
                            # Check for data quality issues
                            amounts = candle_trades['amount'].tolist()
                            amount_stats = {
                                'min': candle_trades['amount'].min() if not candle_trades['amount'].empty else 'N/A',
                                'max': candle_trades['amount'].max() if not candle_trades['amount'].empty else 'N/A',
                                'mean': candle_trades['amount'].mean() if not candle_trades['amount'].empty else 'N/A',
                                'nan_count': candle_trades['amount'].isna().sum(),
                                'zero_count': (candle_trades['amount'] == 0).sum()
                            }
                            self.logger.warning(f"Amount stats: {amount_stats}")
                    
                    self.logger.debug(f"Candle {i} CVD calculation: buy_volume={buy_volume:.4f}, sell_volume={sell_volume:.4f}, types: {type(buy_volume)}, {type(sell_volume)}")
                    
                    candle_cvd = buy_volume - sell_volume
                    candle_cvds.append(candle_cvd)
                    self.logger.debug(f"Candle {i} CVD: {candle_cvd:.4f}")
                except Exception as e:
                    self.logger.warning(f"Error calculating candle {i} CVD: {str(e)}, using 0 instead")
                    # Log more details about the error for debugging
                    import traceback
                    self.logger.debug(f"Error details: {traceback.format_exc()}")
                    
                    # Try to get information about the candle_trades DataFrame
                    try:
                        if 'candle_trades' in locals() and not candle_trades.empty:
                            self.logger.debug(f"Candle trades info: shape={candle_trades.shape}, columns={list(candle_trades.columns)}")
                            self.logger.debug(f"Sample trades: {candle_trades.head(2).to_dict('records')}")
                            self.logger.debug(f"Side values: {candle_trades['side'].value_counts().to_dict()}")
                    except Exception as inner_e:
                        self.logger.debug(f"Failed to log candle trades information: {str(inner_e)}")
                    
                    candle_cvds.append(0)
            
            # Check if we have enough candle CVD values
            if len(candle_cvds) < 2:
                self.logger.warning(f"Insufficient candle CVD data: {len(candle_cvds)} values")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Interpolate for candles without trades if enabled
            if getattr(self, 'interpolate_missing_cvd', True) and 0 in candle_cvds:
                self.logger.debug("Interpolating CVD values for candles without trades")
                # Create a series with timestamps and CVD values
                cvd_series = pd.Series(candle_cvds, index=candle_timestamps[:len(candle_cvds)])
                
                # Find indices of non-zero values
                non_zero_indices = [i for i, cvd in enumerate(candle_cvds) if cvd != 0]
                if not non_zero_indices:
                    self.logger.debug("No non-zero CVD values found for interpolation")
                else:
                    self.logger.debug(f"Found {len(non_zero_indices)} non-zero values at indices: {non_zero_indices}")
                    
                    # Handle zeros before first non-zero (backfill)
                    first_non_zero_idx = non_zero_indices[0]
                    first_non_zero_val = candle_cvds[first_non_zero_idx]
                    if first_non_zero_idx > 0:
                        self.logger.debug(f"Backfilling {first_non_zero_idx} initial zeros before first value {first_non_zero_val}")
                        for j in range(0, first_non_zero_idx):
                            # Use a linear ramp up to the first value
                            candle_cvds[j] = first_non_zero_val * (j + 1) / (first_non_zero_idx + 1)
                    
                    # Handle zeros between non-zero values (interpolation)
                    for idx_pos in range(len(non_zero_indices) - 1):
                        start_idx = non_zero_indices[idx_pos]
                        end_idx = non_zero_indices[idx_pos + 1]
                        start_val = candle_cvds[start_idx]
                        end_val = candle_cvds[end_idx]
                        
                        if end_idx - start_idx > 1:  # If there are zeros between
                            self.logger.debug(f"Interpolating between index {start_idx} ({start_val}) and {end_idx} ({end_val})")
                            for j in range(start_idx + 1, end_idx):
                                # Linear interpolation
                                ratio = (j - start_idx) / (end_idx - start_idx)
                                candle_cvds[j] = start_val + (end_val - start_val) * ratio
                    
                    # Handle zeros after last non-zero (extrapolation)
                    last_non_zero_idx = non_zero_indices[-1]
                    last_non_zero_val = candle_cvds[last_non_zero_idx]
                    
                    if last_non_zero_idx < len(candle_cvds) - 1:
                        # Calculate trend from available non-zero values
                        if len(non_zero_indices) >= 2:
                            # Use the last two non-zero values to determine trend
                            prev_idx = non_zero_indices[-2]
                            prev_val = candle_cvds[prev_idx]
                            last_idx = non_zero_indices[-1]
                            last_val = candle_cvds[last_idx]
                            
                            # Calculate slope (per candle)
                            trend_slope = (last_val - prev_val) / (last_idx - prev_idx)
                            self.logger.debug(f"Extrapolating with slope {trend_slope:.4f} based on last values {prev_val:.4f} and {last_val:.4f}")
                            
                            # Apply diminishing trend after last value (decay factor reduces impact over time)
                            decay_factor = 0.8  # Reduce impact by 20% each candle
                            for j in range(last_non_zero_idx + 1, len(candle_cvds)):
                                steps = j - last_non_zero_idx
                                # Calculate diminishing effect with distance
                                decay = decay_factor ** steps
                                extrapolated_val = last_non_zero_val + (trend_slope * steps * decay)
                                candle_cvds[j] = extrapolated_val
                        else:
                            # Only one non-zero value, use decay from that value
                            self.logger.debug(f"Only one non-zero value ({last_non_zero_val:.4f}), using decay extrapolation")
                            decay_factor = 0.7  # Stronger decay when we have less information
                            for j in range(last_non_zero_idx + 1, len(candle_cvds)):
                                steps = j - last_non_zero_idx
                                # Apply decay from last known value
                                candle_cvds[j] = last_non_zero_val * (decay_factor ** steps)
                        
                        self.logger.debug(f"Extrapolated {len(candle_cvds) - last_non_zero_idx - 1} values after last non-zero value")
                
                zero_count = candle_cvds.count(0)
                self.logger.debug(f"After interpolation, zero values remaining: {zero_count}")
                if zero_count > 0:
                    zero_indices = [i for i, val in enumerate(candle_cvds) if val == 0]
                    self.logger.debug(f"Remaining zeros at indices: {zero_indices}")
                    # Last attempt to fill any remaining zeros with small random values
                    for idx in zero_indices:
                        # Use a small percentage of the max absolute CVD as a fallback
                        max_abs_cvd = max(abs(cvd) for cvd in candle_cvds if cvd != 0) if any(cvd != 0 for cvd in candle_cvds) else 1.0
                        candle_cvds[idx] = max_abs_cvd * 0.01  # 1% of max as fallback
            
            self.logger.debug(f"Calculated CVD for {len(candle_cvds)} candles")
            self.logger.debug(f"Candle CVDs: min={min(candle_cvds):.4f}, max={max(candle_cvds):.4f}, mean={sum(candle_cvds)/len(candle_cvds):.4f}")
            
            # Apply time weighting if enabled
            weighted_candle_cvds = []
            if self.time_weighting_enabled:
                self.logger.debug(f"Applying time weighting with recency factor {self.recency_factor}")
                for i, cvd in enumerate(candle_cvds):
                    # Apply exponential weighting - more recent candles get higher weight
                    # i=0 is the most recent candle
                    weight = self.recency_factor ** (len(candle_cvds) - 1 - i)
                    weighted_candle_cvds.append(cvd * weight)
                    self.logger.debug(f"Candle {i} CVD: {cvd:.2f}, Weight: {weight:.2f}, Weighted: {cvd * weight:.2f}")
            else:
                self.logger.debug("Time weighting disabled, using raw CVD values")
                weighted_candle_cvds = candle_cvds
            
            # Calculate CVD trend with time weighting
            cvd_trend = sum(weighted_candle_cvds)
            
            # For normalization, we need the sum of absolute weighted values
            abs_sum = sum(abs(c) for c in weighted_candle_cvds)
            
            self.logger.debug(f"CVD trend: {cvd_trend:.4f}, Absolute sum: {abs_sum:.4f}")
            
            # Calculate divergence
            divergence_strength = 0.0
            divergence_type = 'neutral'
            
            if (price_trend > 0 and cvd_trend < 0):
                # Bearish divergence: Price up, CVD down
                divergence_type = 'bearish'
                divergence_strength = min(abs(cvd_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bearish divergence: Price trend={price_trend:.4f} (up), CVD trend={cvd_trend:.4f} (down)")
            elif (price_trend < 0 and cvd_trend > 0):
                # Bullish divergence: Price down, CVD up
                divergence_type = 'bullish'
                divergence_strength = min(abs(cvd_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bullish divergence: Price trend={price_trend:.4f} (down), CVD trend={cvd_trend:.4f} (up)")
            else:
                self.logger.debug(f"No divergence detected: Price trend={price_trend:.4f}, CVD trend={cvd_trend:.4f}")
            
            # Only return significant divergences
            if divergence_strength < self.divergence_strength_threshold:
                self.logger.debug(f"Divergence strength {divergence_strength:.2f} below threshold {self.divergence_strength_threshold}, returning neutral")
                
                # Log execution time
                calculation_end_time = time.time()
                execution_time = calculation_end_time - calculation_start_time
                self.logger.debug(f"Price-CVD divergence calculation completed in {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.info(f"Price-CVD divergence: {divergence_type}, strength: {divergence_strength:.2f}")
            
            # Fix time tracking for candle processing
            candle_processing_end_time = time.time()
            candle_processing_time = candle_processing_end_time - candle_start_time
            self.logger.debug(f"Processed {lookback} candles in {candle_processing_time:.4f} seconds")
            
            # Calculate the final execution time
            calculation_end_time = time.time()
            execution_time = calculation_end_time - calculation_start_time
            self.logger.debug(f"Price-CVD divergence calculation completed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            result = {
                'type': divergence_type,
                'strength': float(divergence_strength)
            }
            
            # Store in cache before returning
            self._cache[cache_key] = result
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating price-CVD divergence: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # Calculate the final execution time
            calculation_end_time = time.time()
            execution_time = calculation_end_time - calculation_start_time
            self.logger.debug(f"Price-CVD divergence calculation failed after {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            return {'type': 'neutral', 'strength': 0.0}

    def _calculate_price_oi_divergence(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate divergence between price and open interest.
        
        This method detects when price is moving in one direction but open interest is moving in the opposite direction,
        which can indicate potential reversals.
        
        Args:
            market_data: Dictionary containing market data with OHLCV and open interest data
            
        Returns:
            Dict: Divergence information including type and strength
        """
        # Use caching to avoid redundant calculations
        cache_key = 'price_oi_divergence'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        # Enhanced debugging: Log market_data top-level keys
        self.logger.debug(f"OI-PRICE DIVERGENCE: Market data keys: {list(market_data.keys())}")
        
        # Check if open interest data is available before proceeding
        if ('open_interest' not in market_data and 
            ('sentiment' not in market_data or 'open_interest' not in market_data.get('sentiment', {}))):
            self.logger.warning("Missing open interest data for price-OI divergence calculation")
            
            # Enhanced debugging: More details about the structure if data is missing
            if 'sentiment' in market_data:
                self.logger.debug(f"OI-PRICE DIVERGENCE: Sentiment keys available: {list(market_data['sentiment'].keys())}")
            if 'open_interest' in market_data:
                self.logger.debug(f"OI-PRICE DIVERGENCE: Open interest appears empty or malformed: {market_data['open_interest']}")
                
            return {'type': 'neutral', 'strength': 0.0}
            
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING PRICE-OI DIVERGENCE CALCULATION")
        self.logger.debug("=" * 50)
        
        # Enhanced debugging: Log concise OI structure info
        if 'open_interest' in market_data:
            oi_dump = market_data['open_interest']
            if isinstance(oi_dump, dict):
                # Log only essential info instead of full structure
                history_count = len(oi_dump.get('history', []))
                current_oi = oi_dump.get('current', 'N/A')
                previous_oi = oi_dump.get('previous', 'N/A')
                self.logger.debug(f"OI-PRICE DIVERGENCE: OI data - current: {current_oi}, previous: {previous_oi}, history entries: {history_count}")
            else:
                self.logger.debug(f"OI-PRICE DIVERGENCE: OI not a dictionary: {type(oi_dump)}")
        
        try:
            # Check if we have the required data
            if 'ohlcv' not in market_data:
                self.logger.warning("Missing OHLCV data for price-OI divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            ohlcv_data = market_data['ohlcv']
            
            # Check if ohlcv_data is a dictionary
            if not isinstance(ohlcv_data, dict):
                self.logger.warning(f"OHLCV data is not a dictionary: {type(ohlcv_data)}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log available timeframes
            self.logger.debug(f"Available OHLCV timeframes: {list(ohlcv_data.keys())}")
                
            # Try to find a valid timeframe
            valid_timeframe = None
            ohlcv_df = None
            
            # First check for direct DataFrame access (for backward compatibility)
            for tf in ['base', 'ltf', '1', '5']:
                if tf in ohlcv_data:
                    # Check if it's a direct DataFrame
                    if isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
                    # Check if it's a nested structure with 'data' key
                    elif isinstance(ohlcv_data[tf], dict) and 'data' in ohlcv_data[tf] and isinstance(ohlcv_data[tf]['data'], pd.DataFrame) and not ohlcv_data[tf]['data'].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]['data']
                        self.logger.debug(f"Found nested DataFrame at timeframe {tf}['data']")
                        break
            
            # Also check for timeframes with '_direct' suffix (added for testing)
            if not valid_timeframe:
                for tf in ['base_direct', 'ltf_direct', '1_direct', '5_direct']:
                    if tf in ohlcv_data and isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
            
            if not valid_timeframe or ohlcv_df is None:
                self.logger.warning("No valid OHLCV timeframe found for price-OI divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Verify that the DataFrame has the required columns
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in ohlcv_df.columns]
            if missing_columns:
                self.logger.warning(f"OHLCV data missing required columns: {missing_columns}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log OHLCV DataFrame info
            self.logger.debug(f"OHLCV DataFrame for {valid_timeframe}: shape={ohlcv_df.shape}, columns={list(ohlcv_df.columns)}")
            self.logger.debug(f"OHLCV DataFrame index type: {type(ohlcv_df.index)}")
            if len(ohlcv_df) > 0:
                self.logger.debug(f"OHLCV first row: {ohlcv_df.iloc[0].to_dict()}")
                self.logger.debug(f"OHLCV last row: {ohlcv_df.iloc[-1].to_dict()}")
                
            # Use configurable lookback period
            lookback = min(len(ohlcv_df), self.divergence_lookback)
            if lookback < 2:
                self.logger.warning(f"Insufficient OHLCV data for divergence calculation: {len(ohlcv_df)} rows")
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.debug(f"Using lookback period of {lookback} candles for divergence calculation")
            
            # Check if we have open interest data at the top level
            oi_data = None
            oi_history = []
            
            # First check for open interest at the top level (new structure)
            if 'open_interest' in market_data:
                oi_data = market_data['open_interest']
                self.logger.debug("Found open interest data at top level")
                if isinstance(oi_data, dict):
                    self.logger.debug(f"Open interest data keys: {list(oi_data.keys())}")
            # Fallback to sentiment.open_interest for backward compatibility
            elif 'sentiment' in market_data and 'open_interest' in market_data['sentiment']:
                oi_data = market_data['sentiment']['open_interest']
                self.logger.debug("Found open interest data in sentiment section")
                if isinstance(oi_data, dict):
                    self.logger.debug(f"Open interest data keys: {list(oi_data.keys())}")
            else:
                self.logger.warning("Missing open interest data for price-OI divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Get open interest history
            if 'open_interest_history' in market_data and isinstance(market_data['open_interest_history'], list):
                # ADDED: Check for direct reference first
                oi_history = market_data['open_interest_history']
                self.logger.debug(f"Using direct open_interest_history reference with {len(oi_history)} entries")
                if len(oi_history) > 0:
                    first_entry = oi_history[0]
                    if isinstance(first_entry, dict):
                        timestamp = first_entry.get('timestamp', 'N/A')
                        value = first_entry.get('value', 'N/A')
                        self.logger.debug(f"First OI entry: timestamp={timestamp}, value={value}")
                    else:
                        self.logger.debug(f"First OI entry: {first_entry}")
            elif isinstance(oi_data, dict) and 'history' in oi_data and isinstance(oi_data['history'], list):
                oi_history = oi_data['history']
                self.logger.debug(f"Using open interest history from 'history' key with {len(oi_history)} entries")
                # Enhanced debugging: Sample of history data
                if len(oi_history) > 0:
                    first_entry = oi_history[0]
                    if isinstance(first_entry, dict):
                        timestamp = first_entry.get('timestamp', 'N/A')
                        value = first_entry.get('value', 'N/A')
                        self.logger.debug(f"OI-PRICE DIVERGENCE: First history entry: timestamp={timestamp}, value={value}")
                    else:
                        self.logger.debug(f"OI-PRICE DIVERGENCE: First history entry: {first_entry}")
                    
                    if len(oi_history) > 1:
                        second_entry = oi_history[1]
                        if isinstance(second_entry, dict):
                            timestamp = second_entry.get('timestamp', 'N/A')
                            value = second_entry.get('value', 'N/A')
                            self.logger.debug(f"OI-PRICE DIVERGENCE: Second history entry: timestamp={timestamp}, value={value}")
                        else:
                            self.logger.debug(f"OI-PRICE DIVERGENCE: Second history entry: {second_entry}")
            elif isinstance(oi_data, list):
                # If OI data is already a list
                oi_history = oi_data
                self.logger.debug(f"Using open interest data directly as list with {len(oi_history)} entries")
            else:
                # Enhanced debugging: Log what was found in the structure
                self.logger.warning(f"OI-PRICE DIVERGENCE: No proper history found. OI data type: {type(oi_data)}")
                if isinstance(oi_data, dict):
                    self.logger.warning(f"OI-PRICE DIVERGENCE: OI data keys: {list(oi_data.keys())}")
                # If we don't have history, we can't calculate divergence
                self.logger.warning("No open interest history available for divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            if len(oi_history) < 2:
                self.logger.warning(f"Insufficient open interest history for divergence calculation: {len(oi_history)} entries")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Log sample of OI history
            if len(oi_history) > 0:
                sample_entry = oi_history[0]
                self.logger.debug(f"OI history sample entry: {sample_entry}")
                if isinstance(sample_entry, dict):
                    self.logger.debug(f"OI history entry keys: {list(sample_entry.keys())}")
            
            # Get timestamps for alignment
            # Check if we have a timestamp column or need to use the index
            if 'timestamp' in ohlcv_df.columns:
                start_timestamp = ohlcv_df.iloc[-lookback]['timestamp']
                self.logger.debug(f"Using timestamp column for alignment, start_timestamp: {start_timestamp}")
            else:
                # Try to use index as timestamp
                try:
                    start_timestamp = ohlcv_df.index[-lookback]
                    self.logger.debug(f"Using index for alignment, start_timestamp: {start_timestamp}")
                except Exception as e:
                    self.logger.warning(f"Failed to get start timestamp from OHLCV data: {str(e)}")
                    return {'type': 'neutral', 'strength': 0.0}
            
            # Ensure start_timestamp is numeric
            try:
                # Convert pandas Timestamp to milliseconds since epoch
                if isinstance(start_timestamp, pd.Timestamp):
                    start_timestamp_orig = start_timestamp
                    start_timestamp = int(start_timestamp.timestamp() * 1000)
                    self.logger.debug(f"Converted start_timestamp from pd.Timestamp {start_timestamp_orig} to {start_timestamp}")
                elif isinstance(start_timestamp, str):
                    start_timestamp_orig = start_timestamp
                    start_timestamp = pd.to_numeric(start_timestamp)
                    self.logger.debug(f"Converted start_timestamp from string {start_timestamp_orig} to {start_timestamp}")
            except Exception as e:
                self.logger.warning(f"Failed to convert start_timestamp to numeric: {str(e)}")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Filter OI history to match the same time period as price data
            aligned_oi_values = []
            aligned_timestamps = []
            
            self.logger.debug(f"Aligning OI history with price data, start_timestamp: {start_timestamp}")
            
            for entry in oi_history:
                entry_timestamp = entry['timestamp'] if isinstance(entry, dict) and 'timestamp' in entry else None
                
                # Ensure entry_timestamp is numeric for comparison
                try:
                    if entry_timestamp is not None:
                        entry_timestamp = pd.to_numeric(entry_timestamp) if isinstance(entry_timestamp, (str, pd.Timestamp)) else entry_timestamp
                        
                        if entry_timestamp >= start_timestamp:
                            entry_value = float(entry['value']) if isinstance(entry, dict) and 'value' in entry else float(entry)
                            aligned_oi_values.append(entry_value)
                            aligned_timestamps.append(entry_timestamp)
                except Exception as e:
                    self.logger.debug(f"Failed to process OI entry timestamp: {str(e)}")
                    continue
            
            # Continue with aligned OI values
            if len(aligned_oi_values) < 2:
                self.logger.warning(f"Insufficient aligned OI data for divergence calculation: {len(aligned_oi_values)} entries")
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.debug(f"Successfully aligned {len(aligned_oi_values)} OI entries with price data")
            self.logger.debug(f"Aligned OI values: min={min(aligned_oi_values):.2f}, max={max(aligned_oi_values):.2f}, mean={sum(aligned_oi_values)/len(aligned_oi_values):.2f}")
            
            # Calculate price trend
            price_changes = ohlcv_df['close'].diff().tail(lookback)
            price_trend = price_changes.sum()
            
            self.logger.debug(f"Price trend over {lookback} candles: {price_trend:.4f}")
            self.logger.debug(f"Price changes: min={price_changes.min():.4f}, max={price_changes.max():.4f}, mean={price_changes.mean():.4f}")
            
            # Calculate OI changes
            oi_changes = [aligned_oi_values[i] - aligned_oi_values[i-1] for i in range(1, len(aligned_oi_values))]
            
            self.logger.debug(f"OI changes: {len(oi_changes)} entries")
            self.logger.debug(f"OI changes: min={min(oi_changes):.2f}, max={max(oi_changes):.2f}, mean={sum(oi_changes)/len(oi_changes):.2f}")
            
            # Enhanced debugging: Detailed OI change data (only show first few entries)
            if self.debug_level >= 3:  # Only show detailed changes at highest debug level
                self.logger.debug("OI-PRICE DIVERGENCE: Detailed OI changes (first 3 entries):")
                for i, change in enumerate(oi_changes[:3]):  # Only show first 3 entries
                    self.logger.debug(f"  Entry {i}: Value: {aligned_oi_values[i]:.2f}, Previous: {aligned_oi_values[i-1]:.2f}, Change: {change:.2f}")
                if len(oi_changes) > 3:
                    self.logger.debug(f"  ... and {len(oi_changes) - 3} more entries")
            
            # Apply time weighting if enabled
            weighted_oi_changes = []
            if self.time_weighting_enabled:
                self.logger.debug(f"Applying time weighting with recency factor {self.recency_factor}")
                for i, change in enumerate(oi_changes):
                    # Apply exponential weighting - more recent changes get higher weight
                    weight = self.recency_factor ** (len(oi_changes) - 1 - i)
                    weighted_oi_changes.append(change * weight)
                    # Only log detailed weighting at highest debug level
                    if self.debug_level >= 3:
                        self.logger.debug(f"OI Change {i}: {change:.2f}, Weight: {weight:.2f}, Weighted: {change * weight:.2f}")
            else:
                self.logger.debug("Time weighting disabled, using raw OI changes")
                weighted_oi_changes = oi_changes
            
            # Calculate OI trend with time weighting
            oi_trend = sum(weighted_oi_changes)
            
            # For normalization, we need the sum of absolute weighted values
            abs_sum = sum(abs(c) for c in weighted_oi_changes)
            
            self.logger.debug(f"OI trend: {oi_trend:.4f}, Absolute sum: {abs_sum:.4f}")
            
            # Calculate divergence
            divergence_strength = 0.0
            divergence_type = 'neutral'
            
            # Enhanced debugging: Detailed comparison
            self.logger.debug(f"OI-PRICE DIVERGENCE: Final comparison - Price trend: {price_trend:.4f}, OI trend: {oi_trend:.4f}")
            
            if (price_trend > 0 and oi_trend < 0):
                # Bearish divergence: Price up, OI down
                divergence_type = 'bearish'
                divergence_strength = min(abs(oi_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bearish divergence: Price trend={price_trend:.4f} (up), OI trend={oi_trend:.4f} (down)")
                # Enhanced debugging: Strength calculation (only at highest debug level)
                if self.debug_level >= 3:
                    self.logger.debug(f"OI-PRICE DIVERGENCE: Bearish strength calculation: |{oi_trend:.4f}| / max(1, {abs_sum:.4f}) * 100 = {divergence_strength:.2f}")
            elif (price_trend < 0 and oi_trend > 0):
                # Bullish divergence: Price down, OI up
                divergence_type = 'bullish'
                divergence_strength = min(abs(oi_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bullish divergence: Price trend={price_trend:.4f} (down), OI trend={oi_trend:.4f} (up)")
                # Enhanced debugging: Strength calculation (only at highest debug level)
                if self.debug_level >= 3:
                    self.logger.debug(f"OI-PRICE DIVERGENCE: Bullish strength calculation: |{oi_trend:.4f}| / max(1, {abs_sum:.4f}) * 100 = {divergence_strength:.2f}")
            else:
                self.logger.debug(f"No divergence detected: Price trend={price_trend:.4f}, OI trend={oi_trend:.4f}")
                # Enhanced debugging: Why no divergence was detected (only at highest debug level)
                if self.debug_level >= 3:
                    if price_trend > 0 and oi_trend >= 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: Both price and OI trending up (no divergence)")
                    elif price_trend < 0 and oi_trend <= 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: Both price and OI trending down (no divergence)")
                    elif price_trend == 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: No price trend detected")
                    elif oi_trend == 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: No OI trend detected")
            
            # Only return significant divergences
            if divergence_strength < self.divergence_strength_threshold:
                self.logger.debug(f"Divergence strength {divergence_strength:.2f} below threshold {self.divergence_strength_threshold}, returning neutral")
                
                # Log execution time
                execution_time = time.time() - start_time
                self.logger.debug(f"Price-OI divergence calculation completed in {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                
                return {'type': 'neutral', 'strength': 0.0}
                
            self.logger.info(f"Price-OI divergence: {divergence_type}, strength: {divergence_strength:.2f}")
            
            # Log execution time
            execution_time = time.time() - start_time
            self.logger.debug(f"Price-OI divergence calculation completed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            result = {
                'type': divergence_type,
                'strength': float(divergence_strength)
            }
            
            # Store in cache before returning
            self._cache[cache_key] = result
            return result
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error calculating price-OI divergence: {str(e)}")
            self.logger.error(f"OI-PRICE DIVERGENCE Error traceback: {traceback.format_exc()}")
            
            # Log market data structure for debugging (concise version)
            try:
                if 'open_interest' in market_data:
                    oi_data = market_data['open_interest']
                    if isinstance(oi_data, dict):
                        history_count = len(oi_data.get('history', []))
                        current_oi = oi_data.get('current', 'N/A')
                        self.logger.error(f"OI-PRICE DIVERGENCE: Error with OI structure - current: {current_oi}, history entries: {history_count}")
                    else:
                        self.logger.error(f"OI-PRICE DIVERGENCE: Error with OI structure - type: {type(oi_data)}")
                self.logger.error(f"OI-PRICE DIVERGENCE: Market data keys: {list(market_data.keys())}")
            except Exception as json_err:
                self.logger.error(f"OI-PRICE DIVERGENCE: Could not log market data structure due to error: {str(json_err)}")
                
            # Log execution time even in error case
            execution_time = time.time() - start_time if 'start_time' in locals() else -1
            self.logger.debug(f"Price-OI divergence calculation failed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            return {'type': 'neutral', 'strength': 0.0}

    def _calculate_trade_flow(self, trades_df: Union[pd.DataFrame, Dict, List]) -> float:
        """Calculate trade flow indicator (buy vs sell pressure).
        
        Args:
            trades_df: DataFrame, dictionary or list containing trade data
            
        Returns:
            float: Trade flow value between -1 and 1
        """
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING TRADE FLOW CALCULATION")
        self.logger.debug("=" * 50)
        
        try:
            # Initialize variables
            df = None
            
            # Log input data type
            self.logger.debug(f"Input trades_df type: {type(trades_df)}")
            
            # Handle different input types
            if isinstance(trades_df, pd.DataFrame):
                # Input is already a DataFrame
                df = trades_df.copy()
                self.logger.debug(f"Using trades DataFrame directly, shape: {df.shape}, columns: {list(df.columns)}")
            
            elif isinstance(trades_df, list) and trades_df:
                # Input is a list of trade dictionaries
                try:
                    self.logger.debug(f"Input is a list with {len(trades_df)} trade records")
                    if len(trades_df) > 0:
                        self.logger.debug(f"First trade sample: {trades_df[0]}")
                    df = pd.DataFrame(trades_df)
                    self.logger.debug(f"Converted trades list to DataFrame with {len(trades_df)} records, columns: {list(df.columns)}")
                except Exception as e:
                    self.logger.error(f"Failed to convert trades list to DataFrame: {e}")
                    self.logger.debug(traceback.format_exc())
                    return 0.0
            
            elif isinstance(trades_df, dict):
                # Input is a dictionary, try to find trades data
                self.logger.debug(f"Input is a dictionary with keys: {list(trades_df.keys())}")
                
                if 'trades_df' in trades_df and isinstance(trades_df['trades_df'], pd.DataFrame):
                    df = trades_df['trades_df'].copy()
                    self.logger.debug(f"Using trades_df from dictionary, shape: {df.shape}, columns: {list(df.columns)}")
                
                elif 'trades' in trades_df and isinstance(trades_df['trades'], list) and trades_df['trades']:
                    try:
                        self.logger.debug(f"Using trades list from dictionary with {len(trades_df['trades'])} records")
                        if len(trades_df['trades']) > 0:
                            self.logger.debug(f"First trade sample: {trades_df['trades'][0]}")
                        df = pd.DataFrame(trades_df['trades'])
                        self.logger.debug(f"Converted trades list from dictionary to DataFrame, shape: {df.shape}, columns: {list(df.columns)}")
                    except Exception as e:
                        self.logger.error(f"Failed to convert trades list from dictionary to DataFrame: {e}")
                        self.logger.debug(traceback.format_exc())
                        return 0.0
                
                elif 'processed_trades' in trades_df and isinstance(trades_df['processed_trades'], list) and trades_df['processed_trades']:
                    try:
                        self.logger.debug(f"Using processed_trades from dictionary with {len(trades_df['processed_trades'])} records")
                        if len(trades_df['processed_trades']) > 0:
                            self.logger.debug(f"First processed trade sample: {trades_df['processed_trades'][0]}")
                        df = pd.DataFrame(trades_df['processed_trades'])
                        self.logger.debug(f"Converted processed_trades to DataFrame, shape: {df.shape}, columns: {list(df.columns)}")
                    except Exception as e:
                        self.logger.error(f"Failed to convert processed_trades to DataFrame: {e}")
                        self.logger.debug(traceback.format_exc())
                        return 0.0
                
                else:
                    self.logger.warning("No valid trade data found in dictionary")
                    return 0.0
            
            else:
                self.logger.error(f"Unsupported trades_df type: {type(trades_df)}")
                return 0.0
            
            # Check if we have a valid DataFrame
            if df is None or df.empty:
                self.logger.warning("No trade data available for trade flow calculation")
                return 0.0
            
            # Log DataFrame info
            self.logger.debug(f"Trade DataFrame info: {len(df)} rows, columns: {list(df.columns)}")
            
            # Map column names to standard names
            column_mappings = {
                'side': ['side', 'S', 'type', 'trade_type'],
                'amount': ['amount', 'size', 'v', 'volume', 'qty', 'quantity']
            }
            
            # Try to find and map the required columns
            for std_col, possible_cols in column_mappings.items():
                if std_col not in df.columns:
                    for col in possible_cols:
                        if col in df.columns:
                            df[std_col] = df[col]
                            self.logger.debug(f"Mapped '{col}' to '{std_col}'")
                            break
            
            # Check if we have the required columns after mapping
            if 'side' not in df.columns or 'amount' not in df.columns:
                missing = []
                if 'side' not in df.columns:
                    missing.append('side')
                if 'amount' not in df.columns:
                    missing.append('amount')
                self.logger.warning(f"Missing required columns after mapping: {missing}. Available columns: {list(df.columns)}")
                return 0.0
            
            # Normalize side values
            try:
                # Convert to string first to handle numeric side values
                df['side'] = df['side'].astype(str)
                self.logger.debug(f"Side value counts before normalization: {df['side'].value_counts().to_dict()}")
                
                # Ensure amount column is numeric
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                
                # Log amount statistics before dropping NaN values
                amount_stats_before = {
                    'count': len(df),
                    'nan_count': df['amount'].isna().sum(),
                    'min': df['amount'].min() if not df['amount'].isna().all() else 'N/A',
                    'max': df['amount'].max() if not df['amount'].isna().all() else 'N/A',
                    'mean': df['amount'].mean() if not df['amount'].isna().all() else 'N/A',
                    'sum': df['amount'].sum() if not df['amount'].isna().all() else 'N/A'
                }
                self.logger.debug(f"Amount statistics before dropping NaN: {amount_stats_before}")
                
                # Drop rows with non-numeric amounts
                df = df.dropna(subset=['amount'])
                
                # Log amount statistics after dropping NaN values
                amount_stats_after = {
                    'count': len(df),
                    'min': df['amount'].min() if not df.empty else 'N/A',
                    'max': df['amount'].max() if not df.empty else 'N/A',
                    'mean': df['amount'].mean() if not df.empty else 'N/A',
                    'sum': df['amount'].sum() if not df.empty else 'N/A'
                }
                self.logger.debug(f"Amount statistics after dropping NaN: {amount_stats_after}")
                
                # Normalize to lowercase
                df['side'] = df['side'].str.lower()
                
                # Map different side values to buy/sell
                buy_values = ['buy', 'b', 'bid', '1', 'true', 'long']
                sell_values = ['sell', 's', 'ask', 'offer', '-1', 'false', 'short']
                
                # Create a normalized side column
                df['norm_side'] = 'unknown'
                df.loc[df['side'].isin(buy_values), 'norm_side'] = 'buy'
                df.loc[df['side'].isin(sell_values), 'norm_side'] = 'sell'
                
                # Log normalized side value counts
                norm_side_counts = df['norm_side'].value_counts().to_dict()
                self.logger.debug(f"Normalized side value counts: {norm_side_counts}")
                
                # Log unknown sides
                unknown_count = (df['norm_side'] == 'unknown').sum()
                if unknown_count > 0:
                    unknown_pct = (unknown_count / len(df)) * 100
                    self.logger.warning(f"Found {unknown_count} trades ({unknown_pct:.2f}%) with unknown side values")
                    
                    # Log some examples of unknown side values
                    unknown_sides = df[df['norm_side'] == 'unknown']['side'].unique()
                    self.logger.debug(f"Examples of unknown side values: {unknown_sides[:10]}")
                    
                    # Randomly assign sides to unknown values to avoid bias
                    unknown_mask = df['norm_side'] == 'unknown'
                    random_sides = np.random.choice(['buy', 'sell'], size=unknown_count)
                    df.loc[unknown_mask, 'norm_side'] = random_sides
                    self.logger.debug(f"Randomly assigned sides to {unknown_count} trades")
                    
                    # Log updated normalized side value counts
                    updated_norm_side_counts = df['norm_side'].value_counts().to_dict()
                    self.logger.debug(f"Updated normalized side value counts after random assignment: {updated_norm_side_counts}")
                
                # Calculate buy and sell volumes
                buy_volume = pd.to_numeric(df[df['norm_side'] == 'buy']['amount'].sum(), errors='coerce')
                sell_volume = pd.to_numeric(df[df['norm_side'] == 'sell']['amount'].sum(), errors='coerce')
                
                # Replace NaN with 0
                buy_volume = 0.0 if pd.isna(buy_volume) else float(buy_volume)
                sell_volume = 0.0 if pd.isna(sell_volume) else float(sell_volume)
                
                self.logger.debug(f"Trade flow volumes: buy_volume={buy_volume}, sell_volume={sell_volume}, types: {type(buy_volume)}, {type(sell_volume)}")
                
                total_volume = buy_volume + sell_volume
                
                if total_volume > 0:
                    # Calculate trade flow: range from -1 (all sells) to 1 (all buys)
                    trade_flow = (buy_volume - sell_volume) / total_volume
                    buy_pct = (buy_volume / total_volume) * 100
                    sell_pct = (sell_volume / total_volume) * 100
                    self.logger.debug(f"Trade flow calculated: {trade_flow:.4f} (buy: {buy_volume:.4f} [{buy_pct:.2f}%], sell: {sell_volume:.4f} [{sell_pct:.2f}%])")
                    
                    # Log execution time
                    execution_time = time.time() - start_time
                    self.logger.debug(f"Trade flow calculation completed in {execution_time:.4f} seconds")
                    self.logger.debug("=" * 50)
                    
                    return float(trade_flow)
                else:
                    self.logger.warning("Zero total volume, cannot calculate trade flow")
                    execution_time = time.time() - start_time
                    self.logger.debug(f"Trade flow calculation completed in {execution_time:.4f} seconds with zero volume")
                    self.logger.debug("=" * 50)
                    return 0.0
                    
            except Exception as e:
                self.logger.error(f"Error calculating trade flow volumes: {str(e)}")
                self.logger.debug(traceback.format_exc())
                execution_time = time.time() - start_time
                self.logger.debug(f"Trade flow calculation failed after {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error in trade flow calculation: {str(e)}")
            self.logger.debug(traceback.format_exc())
            execution_time = time.time() - start_time
            self.logger.debug(f"Trade flow calculation failed after {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            return 0.0

    # ===== SMART MONEY CONCEPTS - LIQUIDITY ZONES =====
    # Moved from price_structure_indicators.py as this is pure order flow analysis
    
    def _calculate_liquidity_zones_score: Non-standard score range detected

**Scoring Methods:**
- `_calculate_confidence(self, market_data: Dict[str, Any]) -> float:
        """Calculate confidence in orderflow analysis."""
        try:
            trades = market_data.get('trades', [])
            
            # Check data quality
            if len(trades) < self.min_trades:
                return 0.5
                
            # Check for consistent trade data
            if not all(isinstance(t, dict) and 'price' in t and 'amount' in t for t in trades):
                return 0.7
                
            return 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5

    async def _calculate_component_scores`: ❌ 3 issues
- `_calculate_cvd(self, market_data: Dict[str, Any]) -> float:
        """Calculate Cumulative Volume Delta (CVD) from trade data.
        
        Args:
            market_data: Market data dictionary containing trades
            
        Returns:
            float: CVD value
        """
        # Use caching to avoid redundant calculations
        cache_key = 'cvd'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING CVD CALCULATION (OPTIMIZED)")
        self.logger.debug("=" * 50)
        
        try:
            # Use the centralized processed trades
            trades_df = self._get_processed_trades(market_data)
            
            if trades_df.empty:
                self.logger.warning("No valid trade data available for CVD calculation")
                return 50.0
            
            # Now just use the pre-calculated signed_volume
            cvd = trades_df['signed_volume'].sum()
            total_volume = trades_df['amount'].sum()
            
            self.logger.debug(f"CVD calculation using processed trades:")
            self.logger.debug(f"- Raw CVD: {cvd:.2f}")
            self.logger.debug(f"- Total volume: {total_volume:.2f}")
            
            # Calculate CVD percentage
            if total_volume > 0:
                cvd_percentage = cvd / total_volume
            else:
                cvd_percentage = 0.0
            
            # Get price direction for CVD-Price divergence analysis
            price_change_pct = self._get_price_direction(market_data)
            
            self.logger.debug(f"CVD: {cvd:.2f}, CVD percentage: {cvd_percentage:.4f}, Price change: {price_change_pct:.3f}%")
            
            # Analyze CVD-Price relationship for divergences
            cvd_score = self._analyze_cvd_price_relationship`: ❌ 2 issues
- `_calculate_base_cvd_score`: ✅ OK
- `_calculate_trade_flow_score`: ❌ 2 issues
- `_calculate_trades_imbalance_score`: ❌ 2 issues
- `_calculate_open_interest_score`: ❌ 2 issues
- `_calculate_trades_pressure_score`: ❌ 2 issues
- `_calculate_liquidity_score`: ❌ 2 issues
- `_calculate_price_cvd_divergence(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate divergence between price and CVD.
        
        This method detects when price is moving in one direction but CVD is moving in the opposite direction,
        which can indicate potential reversals.
        
        Args:
            market_data: Dictionary containing market data with OHLCV and trades
            
        Returns:
            Dict: Divergence information including type and strength
        """
        # Use caching to avoid redundant calculations
        cache_key = 'price_cvd_divergence'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        calculation_start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING PRICE-CVD DIVERGENCE CALCULATION")
        self.logger.debug("=" * 50)
        
        try:
            # Check if we have the required data
            if 'ohlcv' not in market_data:
                self.logger.warning("Missing OHLCV data for price-CVD divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            ohlcv_data = market_data['ohlcv']
            
            # Check if ohlcv_data is a dictionary
            if not isinstance(ohlcv_data, dict):
                self.logger.warning(f"OHLCV data is not a dictionary: {type(ohlcv_data)}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log available timeframes
            self.logger.debug(f"Available OHLCV timeframes: {list(ohlcv_data.keys())}")
                
            # Try to find a valid timeframe
            valid_timeframe = None
            ohlcv_df = None
            
            # First check for direct DataFrame access (for backward compatibility)
            for tf in ['base', 'ltf', '1', '5']:
                if tf in ohlcv_data:
                    # Check if it's a direct DataFrame
                    if isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
                    # Check if it's a nested structure with 'data' key
                    elif isinstance(ohlcv_data[tf], dict) and 'data' in ohlcv_data[tf] and isinstance(ohlcv_data[tf]['data'], pd.DataFrame) and not ohlcv_data[tf]['data'].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]['data']
                        self.logger.debug(f"Found nested DataFrame at timeframe {tf}['data']")
                        break
            
            # Also check for timeframes with '_direct' suffix (added for testing)
            if not valid_timeframe:
                for tf in ['base_direct', 'ltf_direct', '1_direct', '5_direct']:
                    if tf in ohlcv_data and isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
            
            if not valid_timeframe or ohlcv_df is None:
                self.logger.warning("No valid OHLCV timeframe found for price-CVD divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Verify that the DataFrame has the required columns
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in ohlcv_df.columns]
            if missing_columns:
                self.logger.warning(f"OHLCV data missing required columns: {missing_columns}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log OHLCV DataFrame info
            self.logger.debug(f"OHLCV DataFrame for {valid_timeframe}: shape={ohlcv_df.shape}, columns={list(ohlcv_df.columns)}")
            self.logger.debug(f"OHLCV DataFrame index type: {type(ohlcv_df.index)}")
            if len(ohlcv_df) > 0:
                self.logger.debug(f"OHLCV first row: {ohlcv_df.iloc[0].to_dict()}")
                self.logger.debug(f"OHLCV last row: {ohlcv_df.iloc[-1].to_dict()}")
                
            # Use configurable lookback period
            lookback = min(len(ohlcv_df), self.divergence_lookback)
            if lookback < 2:
                self.logger.warning(f"Insufficient OHLCV data for divergence calculation: {len(ohlcv_df)} rows")
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.debug(f"Using lookback period of {lookback} candles for divergence calculation")
            
            # Get trades data
            trades = market_data.get('trades', [])
            if not trades or len(trades) < self.min_trades:
                self.logger.warning(f"Insufficient trade data for price-CVD divergence calculation: {len(trades)} trades, minimum required: {self.min_trades}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Convert trades to DataFrame if needed
            trades_df = trades if isinstance(trades, pd.DataFrame) else pd.DataFrame(trades)
            
            # Log trades DataFrame info
            self.logger.debug(f"Trades DataFrame: shape={trades_df.shape}, columns={list(trades_df.columns)}")
            
            # Ensure we have timestamp in trades
            if 'time' not in trades_df.columns and 'timestamp' in trades_df.columns:
                trades_df['time'] = trades_df['timestamp']
                self.logger.debug("Mapped 'timestamp' to 'time' in trades DataFrame")
            elif 'time' not in trades_df.columns and 'T' in trades_df.columns:
                trades_df['time'] = trades_df['T']
                self.logger.debug("Mapped 'T' to 'time' in trades DataFrame")
                
            if 'time' not in trades_df.columns:
                self.logger.warning("Missing time/timestamp in trades data for price-CVD divergence")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Ensure time column is numeric
            try:
                trades_df['time'] = pd.to_numeric(trades_df['time'])
                self.logger.debug(f"Converted time column to numeric. Sample values: {trades_df['time'].head(3).tolist()}")
            except Exception as e:
                self.logger.warning(f"Failed to convert time column to numeric: {str(e)}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Ensure we have side in trades
            if 'side' not in trades_df.columns and 'S' in trades_df.columns:
                trades_df['side'] = trades_df['S']
                self.logger.debug("Mapped 'S' to 'side' in trades DataFrame")
                
            if 'side' not in trades_df.columns:
                self.logger.warning("Missing side in trades data for price-CVD divergence")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Ensure we have amount/size in trades
            if 'amount' not in trades_df.columns:
                for col in ['size', 'v', 'volume', 'qty', 'quantity']:
                    if col in trades_df.columns:
                        trades_df['amount'] = trades_df[col]
                        self.logger.debug(f"Mapped '{col}' to 'amount' in trades DataFrame")
                        break
                        
            if 'amount' not in trades_df.columns:
                self.logger.warning("Missing amount/size in trades data for price-CVD divergence")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Get price trend
            price_changes = ohlcv_df['close'].diff().tail(lookback)
            price_trend = price_changes.sum()
            
            self.logger.debug(f"Price trend over {lookback} candles: {price_trend:.4f}")
            self.logger.debug(f"Price changes: min={price_changes.min():.4f}, max={price_changes.max():.4f}, mean={price_changes.mean():.4f}")
            
            # Calculate CVD for each candle period
            candle_cvds = []
            candle_timestamps = []
            
            # Ensure proper time tracking for candle processing
            candle_start_time = time.time()
            
            for i in range(1, lookback + 1):
                if i >= len(ohlcv_df):
                    break
                    
                # Get timestamp range for this candle
                # Check if we have a timestamp column or need to use the index
                if 'timestamp' in ohlcv_df.columns:
                    candle_end_time = ohlcv_df.iloc[-i]['timestamp']
                    candle_start_time_ts = ohlcv_df.iloc[-(i+1)]['timestamp'] if i+1 < len(ohlcv_df) else ohlcv_df.iloc[-i]['timestamp'] - 60000  # Fallback: 1 minute earlier
                    self.logger.debug(f"Candle {i} timestamp from column: start={candle_start_time_ts}, end={candle_end_time}")
                    # Save the timestamp for potential interpolation later
                    candle_timestamps.append(candle_end_time)
                else:
                    # Try to use index as timestamp
                    try:
                        candle_end_time = ohlcv_df.index[-i]
                        candle_start_time_ts = ohlcv_df.index[-(i+1)] if i+1 < len(ohlcv_df) else candle_end_time - pd.Timedelta(minutes=1)
                        self.logger.debug(f"Candle {i} timestamp from index: start={candle_start_time_ts}, end={candle_end_time}")
                        # Save the timestamp for potential interpolation later
                        candle_timestamps.append(candle_end_time)
                    except Exception as e:
                        self.logger.debug(f"Failed to get timestamp from index: {str(e)}")
                        continue
                
                # Ensure start_time and end_time are numeric
                try:
                    # Convert pandas Timestamp to milliseconds since epoch
                    if isinstance(candle_start_time_ts, pd.Timestamp):
                        start_time_orig = candle_start_time_ts
                        candle_start_time_ts = int(candle_start_time_ts.timestamp() * 1000)
                        self.logger.debug(f"Converted start_time from pd.Timestamp {start_time_orig} to {candle_start_time_ts}")
                    elif isinstance(candle_start_time_ts, str):
                        start_time_orig = candle_start_time_ts
                        candle_start_time_ts = pd.to_numeric(candle_start_time_ts)
                        self.logger.debug(f"Converted start_time from string {start_time_orig} to {candle_start_time_ts}")
                    
                    if isinstance(candle_end_time, pd.Timestamp):
                        end_time_orig = candle_end_time
                        candle_end_time = int(candle_end_time.timestamp() * 1000)
                        self.logger.debug(f"Converted end_time from pd.Timestamp {end_time_orig} to {candle_end_time}")
                    elif isinstance(candle_end_time, str):
                        end_time_orig = candle_end_time
                        candle_end_time = pd.to_numeric(candle_end_time)
                        self.logger.debug(f"Converted end_time from string {end_time_orig} to {candle_end_time}")
                except Exception as e:
                    self.logger.debug(f"Failed to convert timestamp to numeric: {str(e)}")
                    continue
                
                # Filter trades for this candle
                candle_trades_filtered = trades_df[(trades_df['time'] >= candle_start_time_ts) & (trades_df['time'] < candle_end_time)]
                
                if candle_trades_filtered.empty:
                    self.logger.debug(f"No trades found for candle {i} (time range: {candle_start_time_ts} to {candle_end_time})")
                    candle_cvds.append(0)
                    continue
                
                # Create a copy to avoid SettingWithCopyWarning
                candle_trades = candle_trades_filtered.copy()
                
                self.logger.debug(f"Found {len(candle_trades)} trades for candle {i}")
                    
                # Calculate CVD for this candle
                try:
                    # Log the unique side values to aid in debugging
                    unique_sides = candle_trades['side'].astype(str).unique()
                    self.logger.debug(f"Unique side values in candle {i} trades: {unique_sides}")
                    
                    # Ensure amount column is numeric
                    try:
                        candle_trades.loc[:, 'amount'] = pd.to_numeric(candle_trades['amount'], errors='coerce')
                    except Exception as e:
                        self.logger.warning(f"Error converting amount to numeric: {str(e)}, trying fallback")
                        candle_trades.loc[:, 'amount'] = candle_trades['amount'].apply(lambda x: float(x) if isinstance(x, str) else x)
                    
                    # More robust way to determine buy/sell sides
                    def is_buy_side(side_val):
                        if pd.isna(side_val):
                            return False
                        s = str(side_val).lower().strip()
                        return s in ['buy', 'b', '1', 'true', 'bid', 'long']
                    
                    def is_sell_side(side_val):
                        if pd.isna(side_val):
                            return False
                        s = str(side_val).lower().strip()
                        return s in ['sell', 's', '-1', 'false', 'ask', 'short']
                    
                    # Apply the side detection functions
                    candle_trades.loc[:, 'is_buy'] = candle_trades['side'].apply(is_buy_side)
                    candle_trades.loc[:, 'is_sell'] = candle_trades['side'].apply(is_sell_side)
                    
                    # Log side detection results
                    buy_count = candle_trades['is_buy'].sum()
                    sell_count = candle_trades['is_sell'].sum()
                    unclassified = len(candle_trades) - buy_count - sell_count
                    self.logger.debug(f"Side classification: buy={buy_count}, sell={sell_count}, unclassified={unclassified}")
                    
                    if unclassified > 0 and len(unique_sides) > 0:
                        # If we have unclassified trades, try a more flexible approach
                        if all(side.lower() in ['buy', 'sell'] for side in unique_sides if isinstance(side, str)):
                            self.logger.debug(f"Using simpler case-insensitive matching for side values")
                            candle_trades.loc[:, 'is_buy'] = candle_trades['side'].astype(str).str.lower() == 'buy'
                            candle_trades.loc[:, 'is_sell'] = candle_trades['side'].astype(str).str.lower() == 'sell'
                            buy_count = candle_trades['is_buy'].sum()
                            sell_count = candle_trades['is_sell'].sum()
                            unclassified = len(candle_trades) - buy_count - sell_count
                            self.logger.debug(f"Updated side classification: buy={buy_count}, sell={sell_count}, unclassified={unclassified}")
                    
                    # Check for any remaining unclassified trades
                    if unclassified > 0 and buy_count == 0 and sell_count == 0:
                        # Last resort attempt - case-insensitive partial matching
                        self.logger.debug(f"Attempting case-insensitive partial matching for sides")
                        candle_trades.loc[:, 'is_buy'] = candle_trades['side'].astype(str).str.lower().str.contains('buy', na=False) | candle_trades['side'].astype(str).str.lower().str.contains('bid', na=False)
                        candle_trades.loc[:, 'is_sell'] = candle_trades['side'].astype(str).str.lower().str.contains('sell', na=False) | candle_trades['side'].astype(str).str.lower().str.contains('ask', na=False)
                        buy_count = candle_trades['is_buy'].sum()
                        sell_count = candle_trades['is_sell'].sum()
                        self.logger.debug(f"Final side classification: buy={buy_count}, sell={sell_count}, unclassified={len(candle_trades) - buy_count - sell_count}")
                    
                    # Calculate buy and sell volumes
                    buy_volume = candle_trades[candle_trades['is_buy']]['amount'].sum()
                    sell_volume = candle_trades[candle_trades['is_sell']]['amount'].sum()
                    
                    # Replace NaN with 0
                    buy_volume = 0.0 if pd.isna(buy_volume) else float(buy_volume)
                    sell_volume = 0.0 if pd.isna(sell_volume) else float(sell_volume)
                    
                    # Additional diagnostic for debugging
                    if buy_volume == 0 and sell_volume == 0:
                        # This shouldn't happen if we have trades and properly classified sides
                        # Log a sample of the trades to diagnose the issue
                        if not candle_trades.empty:
                            sample_trades = candle_trades.head(3)
                            self.logger.warning(f"Both buy and sell volumes are 0 despite having {len(candle_trades)} trades. Sample trades:")
                            for idx, trade in sample_trades.iterrows():
                                self.logger.warning(f"Trade {idx}: side={trade['side']}, amount={trade['amount']}, is_buy={trade.get('is_buy', False)}, is_sell={trade.get('is_sell', False)}")
                            
                            # Check for data quality issues
                            amounts = candle_trades['amount'].tolist()
                            amount_stats = {
                                'min': candle_trades['amount'].min() if not candle_trades['amount'].empty else 'N/A',
                                'max': candle_trades['amount'].max() if not candle_trades['amount'].empty else 'N/A',
                                'mean': candle_trades['amount'].mean() if not candle_trades['amount'].empty else 'N/A',
                                'nan_count': candle_trades['amount'].isna().sum(),
                                'zero_count': (candle_trades['amount'] == 0).sum()
                            }
                            self.logger.warning(f"Amount stats: {amount_stats}")
                    
                    self.logger.debug(f"Candle {i} CVD calculation: buy_volume={buy_volume:.4f}, sell_volume={sell_volume:.4f}, types: {type(buy_volume)}, {type(sell_volume)}")
                    
                    candle_cvd = buy_volume - sell_volume
                    candle_cvds.append(candle_cvd)
                    self.logger.debug(f"Candle {i} CVD: {candle_cvd:.4f}")
                except Exception as e:
                    self.logger.warning(f"Error calculating candle {i} CVD: {str(e)}, using 0 instead")
                    # Log more details about the error for debugging
                    import traceback
                    self.logger.debug(f"Error details: {traceback.format_exc()}")
                    
                    # Try to get information about the candle_trades DataFrame
                    try:
                        if 'candle_trades' in locals() and not candle_trades.empty:
                            self.logger.debug(f"Candle trades info: shape={candle_trades.shape}, columns={list(candle_trades.columns)}")
                            self.logger.debug(f"Sample trades: {candle_trades.head(2).to_dict('records')}")
                            self.logger.debug(f"Side values: {candle_trades['side'].value_counts().to_dict()}")
                    except Exception as inner_e:
                        self.logger.debug(f"Failed to log candle trades information: {str(inner_e)}")
                    
                    candle_cvds.append(0)
            
            # Check if we have enough candle CVD values
            if len(candle_cvds) < 2:
                self.logger.warning(f"Insufficient candle CVD data: {len(candle_cvds)} values")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Interpolate for candles without trades if enabled
            if getattr(self, 'interpolate_missing_cvd', True) and 0 in candle_cvds:
                self.logger.debug("Interpolating CVD values for candles without trades")
                # Create a series with timestamps and CVD values
                cvd_series = pd.Series(candle_cvds, index=candle_timestamps[:len(candle_cvds)])
                
                # Find indices of non-zero values
                non_zero_indices = [i for i, cvd in enumerate(candle_cvds) if cvd != 0]
                if not non_zero_indices:
                    self.logger.debug("No non-zero CVD values found for interpolation")
                else:
                    self.logger.debug(f"Found {len(non_zero_indices)} non-zero values at indices: {non_zero_indices}")
                    
                    # Handle zeros before first non-zero (backfill)
                    first_non_zero_idx = non_zero_indices[0]
                    first_non_zero_val = candle_cvds[first_non_zero_idx]
                    if first_non_zero_idx > 0:
                        self.logger.debug(f"Backfilling {first_non_zero_idx} initial zeros before first value {first_non_zero_val}")
                        for j in range(0, first_non_zero_idx):
                            # Use a linear ramp up to the first value
                            candle_cvds[j] = first_non_zero_val * (j + 1) / (first_non_zero_idx + 1)
                    
                    # Handle zeros between non-zero values (interpolation)
                    for idx_pos in range(len(non_zero_indices) - 1):
                        start_idx = non_zero_indices[idx_pos]
                        end_idx = non_zero_indices[idx_pos + 1]
                        start_val = candle_cvds[start_idx]
                        end_val = candle_cvds[end_idx]
                        
                        if end_idx - start_idx > 1:  # If there are zeros between
                            self.logger.debug(f"Interpolating between index {start_idx} ({start_val}) and {end_idx} ({end_val})")
                            for j in range(start_idx + 1, end_idx):
                                # Linear interpolation
                                ratio = (j - start_idx) / (end_idx - start_idx)
                                candle_cvds[j] = start_val + (end_val - start_val) * ratio
                    
                    # Handle zeros after last non-zero (extrapolation)
                    last_non_zero_idx = non_zero_indices[-1]
                    last_non_zero_val = candle_cvds[last_non_zero_idx]
                    
                    if last_non_zero_idx < len(candle_cvds) - 1:
                        # Calculate trend from available non-zero values
                        if len(non_zero_indices) >= 2:
                            # Use the last two non-zero values to determine trend
                            prev_idx = non_zero_indices[-2]
                            prev_val = candle_cvds[prev_idx]
                            last_idx = non_zero_indices[-1]
                            last_val = candle_cvds[last_idx]
                            
                            # Calculate slope (per candle)
                            trend_slope = (last_val - prev_val) / (last_idx - prev_idx)
                            self.logger.debug(f"Extrapolating with slope {trend_slope:.4f} based on last values {prev_val:.4f} and {last_val:.4f}")
                            
                            # Apply diminishing trend after last value (decay factor reduces impact over time)
                            decay_factor = 0.8  # Reduce impact by 20% each candle
                            for j in range(last_non_zero_idx + 1, len(candle_cvds)):
                                steps = j - last_non_zero_idx
                                # Calculate diminishing effect with distance
                                decay = decay_factor ** steps
                                extrapolated_val = last_non_zero_val + (trend_slope * steps * decay)
                                candle_cvds[j] = extrapolated_val
                        else:
                            # Only one non-zero value, use decay from that value
                            self.logger.debug(f"Only one non-zero value ({last_non_zero_val:.4f}), using decay extrapolation")
                            decay_factor = 0.7  # Stronger decay when we have less information
                            for j in range(last_non_zero_idx + 1, len(candle_cvds)):
                                steps = j - last_non_zero_idx
                                # Apply decay from last known value
                                candle_cvds[j] = last_non_zero_val * (decay_factor ** steps)
                        
                        self.logger.debug(f"Extrapolated {len(candle_cvds) - last_non_zero_idx - 1} values after last non-zero value")
                
                zero_count = candle_cvds.count(0)
                self.logger.debug(f"After interpolation, zero values remaining: {zero_count}")
                if zero_count > 0:
                    zero_indices = [i for i, val in enumerate(candle_cvds) if val == 0]
                    self.logger.debug(f"Remaining zeros at indices: {zero_indices}")
                    # Last attempt to fill any remaining zeros with small random values
                    for idx in zero_indices:
                        # Use a small percentage of the max absolute CVD as a fallback
                        max_abs_cvd = max(abs(cvd) for cvd in candle_cvds if cvd != 0) if any(cvd != 0 for cvd in candle_cvds) else 1.0
                        candle_cvds[idx] = max_abs_cvd * 0.01  # 1% of max as fallback
            
            self.logger.debug(f"Calculated CVD for {len(candle_cvds)} candles")
            self.logger.debug(f"Candle CVDs: min={min(candle_cvds):.4f}, max={max(candle_cvds):.4f}, mean={sum(candle_cvds)/len(candle_cvds):.4f}")
            
            # Apply time weighting if enabled
            weighted_candle_cvds = []
            if self.time_weighting_enabled:
                self.logger.debug(f"Applying time weighting with recency factor {self.recency_factor}")
                for i, cvd in enumerate(candle_cvds):
                    # Apply exponential weighting - more recent candles get higher weight
                    # i=0 is the most recent candle
                    weight = self.recency_factor ** (len(candle_cvds) - 1 - i)
                    weighted_candle_cvds.append(cvd * weight)
                    self.logger.debug(f"Candle {i} CVD: {cvd:.2f}, Weight: {weight:.2f}, Weighted: {cvd * weight:.2f}")
            else:
                self.logger.debug("Time weighting disabled, using raw CVD values")
                weighted_candle_cvds = candle_cvds
            
            # Calculate CVD trend with time weighting
            cvd_trend = sum(weighted_candle_cvds)
            
            # For normalization, we need the sum of absolute weighted values
            abs_sum = sum(abs(c) for c in weighted_candle_cvds)
            
            self.logger.debug(f"CVD trend: {cvd_trend:.4f}, Absolute sum: {abs_sum:.4f}")
            
            # Calculate divergence
            divergence_strength = 0.0
            divergence_type = 'neutral'
            
            if (price_trend > 0 and cvd_trend < 0):
                # Bearish divergence: Price up, CVD down
                divergence_type = 'bearish'
                divergence_strength = min(abs(cvd_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bearish divergence: Price trend={price_trend:.4f} (up), CVD trend={cvd_trend:.4f} (down)")
            elif (price_trend < 0 and cvd_trend > 0):
                # Bullish divergence: Price down, CVD up
                divergence_type = 'bullish'
                divergence_strength = min(abs(cvd_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bullish divergence: Price trend={price_trend:.4f} (down), CVD trend={cvd_trend:.4f} (up)")
            else:
                self.logger.debug(f"No divergence detected: Price trend={price_trend:.4f}, CVD trend={cvd_trend:.4f}")
            
            # Only return significant divergences
            if divergence_strength < self.divergence_strength_threshold:
                self.logger.debug(f"Divergence strength {divergence_strength:.2f} below threshold {self.divergence_strength_threshold}, returning neutral")
                
                # Log execution time
                calculation_end_time = time.time()
                execution_time = calculation_end_time - calculation_start_time
                self.logger.debug(f"Price-CVD divergence calculation completed in {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.info(f"Price-CVD divergence: {divergence_type}, strength: {divergence_strength:.2f}")
            
            # Fix time tracking for candle processing
            candle_processing_end_time = time.time()
            candle_processing_time = candle_processing_end_time - candle_start_time
            self.logger.debug(f"Processed {lookback} candles in {candle_processing_time:.4f} seconds")
            
            # Calculate the final execution time
            calculation_end_time = time.time()
            execution_time = calculation_end_time - calculation_start_time
            self.logger.debug(f"Price-CVD divergence calculation completed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            result = {
                'type': divergence_type,
                'strength': float(divergence_strength)
            }
            
            # Store in cache before returning
            self._cache[cache_key] = result
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating price-CVD divergence: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # Calculate the final execution time
            calculation_end_time = time.time()
            execution_time = calculation_end_time - calculation_start_time
            self.logger.debug(f"Price-CVD divergence calculation failed after {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            return {'type': 'neutral', 'strength': 0.0}

    def _calculate_price_oi_divergence(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate divergence between price and open interest.
        
        This method detects when price is moving in one direction but open interest is moving in the opposite direction,
        which can indicate potential reversals.
        
        Args:
            market_data: Dictionary containing market data with OHLCV and open interest data
            
        Returns:
            Dict: Divergence information including type and strength
        """
        # Use caching to avoid redundant calculations
        cache_key = 'price_oi_divergence'
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        # Enhanced debugging: Log market_data top-level keys
        self.logger.debug(f"OI-PRICE DIVERGENCE: Market data keys: {list(market_data.keys())}")
        
        # Check if open interest data is available before proceeding
        if ('open_interest' not in market_data and 
            ('sentiment' not in market_data or 'open_interest' not in market_data.get('sentiment', {}))):
            self.logger.warning("Missing open interest data for price-OI divergence calculation")
            
            # Enhanced debugging: More details about the structure if data is missing
            if 'sentiment' in market_data:
                self.logger.debug(f"OI-PRICE DIVERGENCE: Sentiment keys available: {list(market_data['sentiment'].keys())}")
            if 'open_interest' in market_data:
                self.logger.debug(f"OI-PRICE DIVERGENCE: Open interest appears empty or malformed: {market_data['open_interest']}")
                
            return {'type': 'neutral', 'strength': 0.0}
            
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING PRICE-OI DIVERGENCE CALCULATION")
        self.logger.debug("=" * 50)
        
        # Enhanced debugging: Log concise OI structure info
        if 'open_interest' in market_data:
            oi_dump = market_data['open_interest']
            if isinstance(oi_dump, dict):
                # Log only essential info instead of full structure
                history_count = len(oi_dump.get('history', []))
                current_oi = oi_dump.get('current', 'N/A')
                previous_oi = oi_dump.get('previous', 'N/A')
                self.logger.debug(f"OI-PRICE DIVERGENCE: OI data - current: {current_oi}, previous: {previous_oi}, history entries: {history_count}")
            else:
                self.logger.debug(f"OI-PRICE DIVERGENCE: OI not a dictionary: {type(oi_dump)}")
        
        try:
            # Check if we have the required data
            if 'ohlcv' not in market_data:
                self.logger.warning("Missing OHLCV data for price-OI divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            ohlcv_data = market_data['ohlcv']
            
            # Check if ohlcv_data is a dictionary
            if not isinstance(ohlcv_data, dict):
                self.logger.warning(f"OHLCV data is not a dictionary: {type(ohlcv_data)}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log available timeframes
            self.logger.debug(f"Available OHLCV timeframes: {list(ohlcv_data.keys())}")
                
            # Try to find a valid timeframe
            valid_timeframe = None
            ohlcv_df = None
            
            # First check for direct DataFrame access (for backward compatibility)
            for tf in ['base', 'ltf', '1', '5']:
                if tf in ohlcv_data:
                    # Check if it's a direct DataFrame
                    if isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
                    # Check if it's a nested structure with 'data' key
                    elif isinstance(ohlcv_data[tf], dict) and 'data' in ohlcv_data[tf] and isinstance(ohlcv_data[tf]['data'], pd.DataFrame) and not ohlcv_data[tf]['data'].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]['data']
                        self.logger.debug(f"Found nested DataFrame at timeframe {tf}['data']")
                        break
            
            # Also check for timeframes with '_direct' suffix (added for testing)
            if not valid_timeframe:
                for tf in ['base_direct', 'ltf_direct', '1_direct', '5_direct']:
                    if tf in ohlcv_data and isinstance(ohlcv_data[tf], pd.DataFrame) and not ohlcv_data[tf].empty:
                        valid_timeframe = tf
                        ohlcv_df = ohlcv_data[tf]
                        self.logger.debug(f"Found direct DataFrame at timeframe {tf}")
                        break
            
            if not valid_timeframe or ohlcv_df is None:
                self.logger.warning("No valid OHLCV timeframe found for price-OI divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Verify that the DataFrame has the required columns
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in ohlcv_df.columns]
            if missing_columns:
                self.logger.warning(f"OHLCV data missing required columns: {missing_columns}")
                return {'type': 'neutral', 'strength': 0.0}
                
            # Log OHLCV DataFrame info
            self.logger.debug(f"OHLCV DataFrame for {valid_timeframe}: shape={ohlcv_df.shape}, columns={list(ohlcv_df.columns)}")
            self.logger.debug(f"OHLCV DataFrame index type: {type(ohlcv_df.index)}")
            if len(ohlcv_df) > 0:
                self.logger.debug(f"OHLCV first row: {ohlcv_df.iloc[0].to_dict()}")
                self.logger.debug(f"OHLCV last row: {ohlcv_df.iloc[-1].to_dict()}")
                
            # Use configurable lookback period
            lookback = min(len(ohlcv_df), self.divergence_lookback)
            if lookback < 2:
                self.logger.warning(f"Insufficient OHLCV data for divergence calculation: {len(ohlcv_df)} rows")
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.debug(f"Using lookback period of {lookback} candles for divergence calculation")
            
            # Check if we have open interest data at the top level
            oi_data = None
            oi_history = []
            
            # First check for open interest at the top level (new structure)
            if 'open_interest' in market_data:
                oi_data = market_data['open_interest']
                self.logger.debug("Found open interest data at top level")
                if isinstance(oi_data, dict):
                    self.logger.debug(f"Open interest data keys: {list(oi_data.keys())}")
            # Fallback to sentiment.open_interest for backward compatibility
            elif 'sentiment' in market_data and 'open_interest' in market_data['sentiment']:
                oi_data = market_data['sentiment']['open_interest']
                self.logger.debug("Found open interest data in sentiment section")
                if isinstance(oi_data, dict):
                    self.logger.debug(f"Open interest data keys: {list(oi_data.keys())}")
            else:
                self.logger.warning("Missing open interest data for price-OI divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Get open interest history
            if 'open_interest_history' in market_data and isinstance(market_data['open_interest_history'], list):
                # ADDED: Check for direct reference first
                oi_history = market_data['open_interest_history']
                self.logger.debug(f"Using direct open_interest_history reference with {len(oi_history)} entries")
                if len(oi_history) > 0:
                    first_entry = oi_history[0]
                    if isinstance(first_entry, dict):
                        timestamp = first_entry.get('timestamp', 'N/A')
                        value = first_entry.get('value', 'N/A')
                        self.logger.debug(f"First OI entry: timestamp={timestamp}, value={value}")
                    else:
                        self.logger.debug(f"First OI entry: {first_entry}")
            elif isinstance(oi_data, dict) and 'history' in oi_data and isinstance(oi_data['history'], list):
                oi_history = oi_data['history']
                self.logger.debug(f"Using open interest history from 'history' key with {len(oi_history)} entries")
                # Enhanced debugging: Sample of history data
                if len(oi_history) > 0:
                    first_entry = oi_history[0]
                    if isinstance(first_entry, dict):
                        timestamp = first_entry.get('timestamp', 'N/A')
                        value = first_entry.get('value', 'N/A')
                        self.logger.debug(f"OI-PRICE DIVERGENCE: First history entry: timestamp={timestamp}, value={value}")
                    else:
                        self.logger.debug(f"OI-PRICE DIVERGENCE: First history entry: {first_entry}")
                    
                    if len(oi_history) > 1:
                        second_entry = oi_history[1]
                        if isinstance(second_entry, dict):
                            timestamp = second_entry.get('timestamp', 'N/A')
                            value = second_entry.get('value', 'N/A')
                            self.logger.debug(f"OI-PRICE DIVERGENCE: Second history entry: timestamp={timestamp}, value={value}")
                        else:
                            self.logger.debug(f"OI-PRICE DIVERGENCE: Second history entry: {second_entry}")
            elif isinstance(oi_data, list):
                # If OI data is already a list
                oi_history = oi_data
                self.logger.debug(f"Using open interest data directly as list with {len(oi_history)} entries")
            else:
                # Enhanced debugging: Log what was found in the structure
                self.logger.warning(f"OI-PRICE DIVERGENCE: No proper history found. OI data type: {type(oi_data)}")
                if isinstance(oi_data, dict):
                    self.logger.warning(f"OI-PRICE DIVERGENCE: OI data keys: {list(oi_data.keys())}")
                # If we don't have history, we can't calculate divergence
                self.logger.warning("No open interest history available for divergence calculation")
                return {'type': 'neutral', 'strength': 0.0}
                
            if len(oi_history) < 2:
                self.logger.warning(f"Insufficient open interest history for divergence calculation: {len(oi_history)} entries")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Log sample of OI history
            if len(oi_history) > 0:
                sample_entry = oi_history[0]
                self.logger.debug(f"OI history sample entry: {sample_entry}")
                if isinstance(sample_entry, dict):
                    self.logger.debug(f"OI history entry keys: {list(sample_entry.keys())}")
            
            # Get timestamps for alignment
            # Check if we have a timestamp column or need to use the index
            if 'timestamp' in ohlcv_df.columns:
                start_timestamp = ohlcv_df.iloc[-lookback]['timestamp']
                self.logger.debug(f"Using timestamp column for alignment, start_timestamp: {start_timestamp}")
            else:
                # Try to use index as timestamp
                try:
                    start_timestamp = ohlcv_df.index[-lookback]
                    self.logger.debug(f"Using index for alignment, start_timestamp: {start_timestamp}")
                except Exception as e:
                    self.logger.warning(f"Failed to get start timestamp from OHLCV data: {str(e)}")
                    return {'type': 'neutral', 'strength': 0.0}
            
            # Ensure start_timestamp is numeric
            try:
                # Convert pandas Timestamp to milliseconds since epoch
                if isinstance(start_timestamp, pd.Timestamp):
                    start_timestamp_orig = start_timestamp
                    start_timestamp = int(start_timestamp.timestamp() * 1000)
                    self.logger.debug(f"Converted start_timestamp from pd.Timestamp {start_timestamp_orig} to {start_timestamp}")
                elif isinstance(start_timestamp, str):
                    start_timestamp_orig = start_timestamp
                    start_timestamp = pd.to_numeric(start_timestamp)
                    self.logger.debug(f"Converted start_timestamp from string {start_timestamp_orig} to {start_timestamp}")
            except Exception as e:
                self.logger.warning(f"Failed to convert start_timestamp to numeric: {str(e)}")
                return {'type': 'neutral', 'strength': 0.0}
            
            # Filter OI history to match the same time period as price data
            aligned_oi_values = []
            aligned_timestamps = []
            
            self.logger.debug(f"Aligning OI history with price data, start_timestamp: {start_timestamp}")
            
            for entry in oi_history:
                entry_timestamp = entry['timestamp'] if isinstance(entry, dict) and 'timestamp' in entry else None
                
                # Ensure entry_timestamp is numeric for comparison
                try:
                    if entry_timestamp is not None:
                        entry_timestamp = pd.to_numeric(entry_timestamp) if isinstance(entry_timestamp, (str, pd.Timestamp)) else entry_timestamp
                        
                        if entry_timestamp >= start_timestamp:
                            entry_value = float(entry['value']) if isinstance(entry, dict) and 'value' in entry else float(entry)
                            aligned_oi_values.append(entry_value)
                            aligned_timestamps.append(entry_timestamp)
                except Exception as e:
                    self.logger.debug(f"Failed to process OI entry timestamp: {str(e)}")
                    continue
            
            # Continue with aligned OI values
            if len(aligned_oi_values) < 2:
                self.logger.warning(f"Insufficient aligned OI data for divergence calculation: {len(aligned_oi_values)} entries")
                return {'type': 'neutral', 'strength': 0.0}
            
            self.logger.debug(f"Successfully aligned {len(aligned_oi_values)} OI entries with price data")
            self.logger.debug(f"Aligned OI values: min={min(aligned_oi_values):.2f}, max={max(aligned_oi_values):.2f}, mean={sum(aligned_oi_values)/len(aligned_oi_values):.2f}")
            
            # Calculate price trend
            price_changes = ohlcv_df['close'].diff().tail(lookback)
            price_trend = price_changes.sum()
            
            self.logger.debug(f"Price trend over {lookback} candles: {price_trend:.4f}")
            self.logger.debug(f"Price changes: min={price_changes.min():.4f}, max={price_changes.max():.4f}, mean={price_changes.mean():.4f}")
            
            # Calculate OI changes
            oi_changes = [aligned_oi_values[i] - aligned_oi_values[i-1] for i in range(1, len(aligned_oi_values))]
            
            self.logger.debug(f"OI changes: {len(oi_changes)} entries")
            self.logger.debug(f"OI changes: min={min(oi_changes):.2f}, max={max(oi_changes):.2f}, mean={sum(oi_changes)/len(oi_changes):.2f}")
            
            # Enhanced debugging: Detailed OI change data (only show first few entries)
            if self.debug_level >= 3:  # Only show detailed changes at highest debug level
                self.logger.debug("OI-PRICE DIVERGENCE: Detailed OI changes (first 3 entries):")
                for i, change in enumerate(oi_changes[:3]):  # Only show first 3 entries
                    self.logger.debug(f"  Entry {i}: Value: {aligned_oi_values[i]:.2f}, Previous: {aligned_oi_values[i-1]:.2f}, Change: {change:.2f}")
                if len(oi_changes) > 3:
                    self.logger.debug(f"  ... and {len(oi_changes) - 3} more entries")
            
            # Apply time weighting if enabled
            weighted_oi_changes = []
            if self.time_weighting_enabled:
                self.logger.debug(f"Applying time weighting with recency factor {self.recency_factor}")
                for i, change in enumerate(oi_changes):
                    # Apply exponential weighting - more recent changes get higher weight
                    weight = self.recency_factor ** (len(oi_changes) - 1 - i)
                    weighted_oi_changes.append(change * weight)
                    # Only log detailed weighting at highest debug level
                    if self.debug_level >= 3:
                        self.logger.debug(f"OI Change {i}: {change:.2f}, Weight: {weight:.2f}, Weighted: {change * weight:.2f}")
            else:
                self.logger.debug("Time weighting disabled, using raw OI changes")
                weighted_oi_changes = oi_changes
            
            # Calculate OI trend with time weighting
            oi_trend = sum(weighted_oi_changes)
            
            # For normalization, we need the sum of absolute weighted values
            abs_sum = sum(abs(c) for c in weighted_oi_changes)
            
            self.logger.debug(f"OI trend: {oi_trend:.4f}, Absolute sum: {abs_sum:.4f}")
            
            # Calculate divergence
            divergence_strength = 0.0
            divergence_type = 'neutral'
            
            # Enhanced debugging: Detailed comparison
            self.logger.debug(f"OI-PRICE DIVERGENCE: Final comparison - Price trend: {price_trend:.4f}, OI trend: {oi_trend:.4f}")
            
            if (price_trend > 0 and oi_trend < 0):
                # Bearish divergence: Price up, OI down
                divergence_type = 'bearish'
                divergence_strength = min(abs(oi_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bearish divergence: Price trend={price_trend:.4f} (up), OI trend={oi_trend:.4f} (down)")
                # Enhanced debugging: Strength calculation (only at highest debug level)
                if self.debug_level >= 3:
                    self.logger.debug(f"OI-PRICE DIVERGENCE: Bearish strength calculation: |{oi_trend:.4f}| / max(1, {abs_sum:.4f}) * 100 = {divergence_strength:.2f}")
            elif (price_trend < 0 and oi_trend > 0):
                # Bullish divergence: Price down, OI up
                divergence_type = 'bullish'
                divergence_strength = min(abs(oi_trend / max(1, abs_sum)) * 100, 100)
                self.logger.debug(f"Detected bullish divergence: Price trend={price_trend:.4f} (down), OI trend={oi_trend:.4f} (up)")
                # Enhanced debugging: Strength calculation (only at highest debug level)
                if self.debug_level >= 3:
                    self.logger.debug(f"OI-PRICE DIVERGENCE: Bullish strength calculation: |{oi_trend:.4f}| / max(1, {abs_sum:.4f}) * 100 = {divergence_strength:.2f}")
            else:
                self.logger.debug(f"No divergence detected: Price trend={price_trend:.4f}, OI trend={oi_trend:.4f}")
                # Enhanced debugging: Why no divergence was detected (only at highest debug level)
                if self.debug_level >= 3:
                    if price_trend > 0 and oi_trend >= 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: Both price and OI trending up (no divergence)")
                    elif price_trend < 0 and oi_trend <= 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: Both price and OI trending down (no divergence)")
                    elif price_trend == 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: No price trend detected")
                    elif oi_trend == 0:
                        self.logger.debug("OI-PRICE DIVERGENCE: No OI trend detected")
            
            # Only return significant divergences
            if divergence_strength < self.divergence_strength_threshold:
                self.logger.debug(f"Divergence strength {divergence_strength:.2f} below threshold {self.divergence_strength_threshold}, returning neutral")
                
                # Log execution time
                execution_time = time.time() - start_time
                self.logger.debug(f"Price-OI divergence calculation completed in {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                
                return {'type': 'neutral', 'strength': 0.0}
                
            self.logger.info(f"Price-OI divergence: {divergence_type}, strength: {divergence_strength:.2f}")
            
            # Log execution time
            execution_time = time.time() - start_time
            self.logger.debug(f"Price-OI divergence calculation completed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            result = {
                'type': divergence_type,
                'strength': float(divergence_strength)
            }
            
            # Store in cache before returning
            self._cache[cache_key] = result
            return result
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error calculating price-OI divergence: {str(e)}")
            self.logger.error(f"OI-PRICE DIVERGENCE Error traceback: {traceback.format_exc()}")
            
            # Log market data structure for debugging (concise version)
            try:
                if 'open_interest' in market_data:
                    oi_data = market_data['open_interest']
                    if isinstance(oi_data, dict):
                        history_count = len(oi_data.get('history', []))
                        current_oi = oi_data.get('current', 'N/A')
                        self.logger.error(f"OI-PRICE DIVERGENCE: Error with OI structure - current: {current_oi}, history entries: {history_count}")
                    else:
                        self.logger.error(f"OI-PRICE DIVERGENCE: Error with OI structure - type: {type(oi_data)}")
                self.logger.error(f"OI-PRICE DIVERGENCE: Market data keys: {list(market_data.keys())}")
            except Exception as json_err:
                self.logger.error(f"OI-PRICE DIVERGENCE: Could not log market data structure due to error: {str(json_err)}")
                
            # Log execution time even in error case
            execution_time = time.time() - start_time if 'start_time' in locals() else -1
            self.logger.debug(f"Price-OI divergence calculation failed in {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            
            return {'type': 'neutral', 'strength': 0.0}

    def _calculate_trade_flow(self, trades_df: Union[pd.DataFrame, Dict, List]) -> float:
        """Calculate trade flow indicator (buy vs sell pressure).
        
        Args:
            trades_df: DataFrame, dictionary or list containing trade data
            
        Returns:
            float: Trade flow value between -1 and 1
        """
        start_time = time.time()
        self.logger.debug("=" * 50)
        self.logger.debug("STARTING TRADE FLOW CALCULATION")
        self.logger.debug("=" * 50)
        
        try:
            # Initialize variables
            df = None
            
            # Log input data type
            self.logger.debug(f"Input trades_df type: {type(trades_df)}")
            
            # Handle different input types
            if isinstance(trades_df, pd.DataFrame):
                # Input is already a DataFrame
                df = trades_df.copy()
                self.logger.debug(f"Using trades DataFrame directly, shape: {df.shape}, columns: {list(df.columns)}")
            
            elif isinstance(trades_df, list) and trades_df:
                # Input is a list of trade dictionaries
                try:
                    self.logger.debug(f"Input is a list with {len(trades_df)} trade records")
                    if len(trades_df) > 0:
                        self.logger.debug(f"First trade sample: {trades_df[0]}")
                    df = pd.DataFrame(trades_df)
                    self.logger.debug(f"Converted trades list to DataFrame with {len(trades_df)} records, columns: {list(df.columns)}")
                except Exception as e:
                    self.logger.error(f"Failed to convert trades list to DataFrame: {e}")
                    self.logger.debug(traceback.format_exc())
                    return 0.0
            
            elif isinstance(trades_df, dict):
                # Input is a dictionary, try to find trades data
                self.logger.debug(f"Input is a dictionary with keys: {list(trades_df.keys())}")
                
                if 'trades_df' in trades_df and isinstance(trades_df['trades_df'], pd.DataFrame):
                    df = trades_df['trades_df'].copy()
                    self.logger.debug(f"Using trades_df from dictionary, shape: {df.shape}, columns: {list(df.columns)}")
                
                elif 'trades' in trades_df and isinstance(trades_df['trades'], list) and trades_df['trades']:
                    try:
                        self.logger.debug(f"Using trades list from dictionary with {len(trades_df['trades'])} records")
                        if len(trades_df['trades']) > 0:
                            self.logger.debug(f"First trade sample: {trades_df['trades'][0]}")
                        df = pd.DataFrame(trades_df['trades'])
                        self.logger.debug(f"Converted trades list from dictionary to DataFrame, shape: {df.shape}, columns: {list(df.columns)}")
                    except Exception as e:
                        self.logger.error(f"Failed to convert trades list from dictionary to DataFrame: {e}")
                        self.logger.debug(traceback.format_exc())
                        return 0.0
                
                elif 'processed_trades' in trades_df and isinstance(trades_df['processed_trades'], list) and trades_df['processed_trades']:
                    try:
                        self.logger.debug(f"Using processed_trades from dictionary with {len(trades_df['processed_trades'])} records")
                        if len(trades_df['processed_trades']) > 0:
                            self.logger.debug(f"First processed trade sample: {trades_df['processed_trades'][0]}")
                        df = pd.DataFrame(trades_df['processed_trades'])
                        self.logger.debug(f"Converted processed_trades to DataFrame, shape: {df.shape}, columns: {list(df.columns)}")
                    except Exception as e:
                        self.logger.error(f"Failed to convert processed_trades to DataFrame: {e}")
                        self.logger.debug(traceback.format_exc())
                        return 0.0
                
                else:
                    self.logger.warning("No valid trade data found in dictionary")
                    return 0.0
            
            else:
                self.logger.error(f"Unsupported trades_df type: {type(trades_df)}")
                return 0.0
            
            # Check if we have a valid DataFrame
            if df is None or df.empty:
                self.logger.warning("No trade data available for trade flow calculation")
                return 0.0
            
            # Log DataFrame info
            self.logger.debug(f"Trade DataFrame info: {len(df)} rows, columns: {list(df.columns)}")
            
            # Map column names to standard names
            column_mappings = {
                'side': ['side', 'S', 'type', 'trade_type'],
                'amount': ['amount', 'size', 'v', 'volume', 'qty', 'quantity']
            }
            
            # Try to find and map the required columns
            for std_col, possible_cols in column_mappings.items():
                if std_col not in df.columns:
                    for col in possible_cols:
                        if col in df.columns:
                            df[std_col] = df[col]
                            self.logger.debug(f"Mapped '{col}' to '{std_col}'")
                            break
            
            # Check if we have the required columns after mapping
            if 'side' not in df.columns or 'amount' not in df.columns:
                missing = []
                if 'side' not in df.columns:
                    missing.append('side')
                if 'amount' not in df.columns:
                    missing.append('amount')
                self.logger.warning(f"Missing required columns after mapping: {missing}. Available columns: {list(df.columns)}")
                return 0.0
            
            # Normalize side values
            try:
                # Convert to string first to handle numeric side values
                df['side'] = df['side'].astype(str)
                self.logger.debug(f"Side value counts before normalization: {df['side'].value_counts().to_dict()}")
                
                # Ensure amount column is numeric
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                
                # Log amount statistics before dropping NaN values
                amount_stats_before = {
                    'count': len(df),
                    'nan_count': df['amount'].isna().sum(),
                    'min': df['amount'].min() if not df['amount'].isna().all() else 'N/A',
                    'max': df['amount'].max() if not df['amount'].isna().all() else 'N/A',
                    'mean': df['amount'].mean() if not df['amount'].isna().all() else 'N/A',
                    'sum': df['amount'].sum() if not df['amount'].isna().all() else 'N/A'
                }
                self.logger.debug(f"Amount statistics before dropping NaN: {amount_stats_before}")
                
                # Drop rows with non-numeric amounts
                df = df.dropna(subset=['amount'])
                
                # Log amount statistics after dropping NaN values
                amount_stats_after = {
                    'count': len(df),
                    'min': df['amount'].min() if not df.empty else 'N/A',
                    'max': df['amount'].max() if not df.empty else 'N/A',
                    'mean': df['amount'].mean() if not df.empty else 'N/A',
                    'sum': df['amount'].sum() if not df.empty else 'N/A'
                }
                self.logger.debug(f"Amount statistics after dropping NaN: {amount_stats_after}")
                
                # Normalize to lowercase
                df['side'] = df['side'].str.lower()
                
                # Map different side values to buy/sell
                buy_values = ['buy', 'b', 'bid', '1', 'true', 'long']
                sell_values = ['sell', 's', 'ask', 'offer', '-1', 'false', 'short']
                
                # Create a normalized side column
                df['norm_side'] = 'unknown'
                df.loc[df['side'].isin(buy_values), 'norm_side'] = 'buy'
                df.loc[df['side'].isin(sell_values), 'norm_side'] = 'sell'
                
                # Log normalized side value counts
                norm_side_counts = df['norm_side'].value_counts().to_dict()
                self.logger.debug(f"Normalized side value counts: {norm_side_counts}")
                
                # Log unknown sides
                unknown_count = (df['norm_side'] == 'unknown').sum()
                if unknown_count > 0:
                    unknown_pct = (unknown_count / len(df)) * 100
                    self.logger.warning(f"Found {unknown_count} trades ({unknown_pct:.2f}%) with unknown side values")
                    
                    # Log some examples of unknown side values
                    unknown_sides = df[df['norm_side'] == 'unknown']['side'].unique()
                    self.logger.debug(f"Examples of unknown side values: {unknown_sides[:10]}")
                    
                    # Randomly assign sides to unknown values to avoid bias
                    unknown_mask = df['norm_side'] == 'unknown'
                    random_sides = np.random.choice(['buy', 'sell'], size=unknown_count)
                    df.loc[unknown_mask, 'norm_side'] = random_sides
                    self.logger.debug(f"Randomly assigned sides to {unknown_count} trades")
                    
                    # Log updated normalized side value counts
                    updated_norm_side_counts = df['norm_side'].value_counts().to_dict()
                    self.logger.debug(f"Updated normalized side value counts after random assignment: {updated_norm_side_counts}")
                
                # Calculate buy and sell volumes
                buy_volume = pd.to_numeric(df[df['norm_side'] == 'buy']['amount'].sum(), errors='coerce')
                sell_volume = pd.to_numeric(df[df['norm_side'] == 'sell']['amount'].sum(), errors='coerce')
                
                # Replace NaN with 0
                buy_volume = 0.0 if pd.isna(buy_volume) else float(buy_volume)
                sell_volume = 0.0 if pd.isna(sell_volume) else float(sell_volume)
                
                self.logger.debug(f"Trade flow volumes: buy_volume={buy_volume}, sell_volume={sell_volume}, types: {type(buy_volume)}, {type(sell_volume)}")
                
                total_volume = buy_volume + sell_volume
                
                if total_volume > 0:
                    # Calculate trade flow: range from -1 (all sells) to 1 (all buys)
                    trade_flow = (buy_volume - sell_volume) / total_volume
                    buy_pct = (buy_volume / total_volume) * 100
                    sell_pct = (sell_volume / total_volume) * 100
                    self.logger.debug(f"Trade flow calculated: {trade_flow:.4f} (buy: {buy_volume:.4f} [{buy_pct:.2f}%], sell: {sell_volume:.4f} [{sell_pct:.2f}%])")
                    
                    # Log execution time
                    execution_time = time.time() - start_time
                    self.logger.debug(f"Trade flow calculation completed in {execution_time:.4f} seconds")
                    self.logger.debug("=" * 50)
                    
                    return float(trade_flow)
                else:
                    self.logger.warning("Zero total volume, cannot calculate trade flow")
                    execution_time = time.time() - start_time
                    self.logger.debug(f"Trade flow calculation completed in {execution_time:.4f} seconds with zero volume")
                    self.logger.debug("=" * 50)
                    return 0.0
                    
            except Exception as e:
                self.logger.error(f"Error calculating trade flow volumes: {str(e)}")
                self.logger.debug(traceback.format_exc())
                execution_time = time.time() - start_time
                self.logger.debug(f"Trade flow calculation failed after {execution_time:.4f} seconds")
                self.logger.debug("=" * 50)
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error in trade flow calculation: {str(e)}")
            self.logger.debug(traceback.format_exc())
            execution_time = time.time() - start_time
            self.logger.debug(f"Trade flow calculation failed after {execution_time:.4f} seconds")
            self.logger.debug("=" * 50)
            return 0.0

    # ===== SMART MONEY CONCEPTS - LIQUIDITY ZONES =====
    # Moved from price_structure_indicators.py as this is pure order flow analysis
    
    def _calculate_liquidity_zones_score`: ❌ 2 issues


### price_structure_indicators.py
**Scoring Methods Found:** 18
**Issues Found:** 26

**Issues:**
- ⚠️  _calculate_component_scores: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_component_scores: No neutral fallback (50.0) found
- ⚠️  _calculate_component_scores: Non-standard score range detected
- ⚠️  _calculate_vwap_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_vwap_score: Non-standard score range detected
- ⚠️  _calculate_composite_value_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_composite_value_score: Non-standard score range detected
- ⚠️  _calculate_value_area_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_short_term_trend(self, df: pd.DataFrame, period: int = 10) -> float:
        """Calculate short-term trend direction and strength."""
        try:
            if len(df) < period:
                return 0.0
            
            # Get recent closes
            recent_closes = df['close'].tail(period)
            
            # Calculate linear regression slope
            x = np.arange(len(recent_closes))
            slope, _ = np.polyfit(x, recent_closes, 1)
            
            # Normalize slope to percentage
            return slope / recent_closes.mean()

        except Exception as e:
            logger.error(f"Error calculating trend: {str(e)}")
            return 0.0

    def _calculate_weighted_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_short_term_trend(self, df: pd.DataFrame, period: int = 10) -> float:
        """Calculate short-term trend direction and strength."""
        try:
            if len(df) < period:
                return 0.0
            
            # Get recent closes
            recent_closes = df['close'].tail(period)
            
            # Calculate linear regression slope
            x = np.arange(len(recent_closes))
            slope, _ = np.polyfit(x, recent_closes, 1)
            
            # Normalize slope to percentage
            return slope / recent_closes.mean()

        except Exception as e:
            logger.error(f"Error calculating trend: {str(e)}")
            return 0.0

    def _calculate_weighted_score: Non-standard score range detected
- ⚠️  _calculate_volume_profile(self, data: Union[pd.DataFrame, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate volume profile metrics including Point of Control and Value Area.
        
        This method analyzes price and volume data to identify key volume-based price levels:
        - Point of Control (POC): The price level with the highest trading volume
        - Value Area High (VAH): Upper boundary containing specified % of volume
        - Value Area Low (VAL): Lower boundary containing specified % of volume
        
        Args:
            data: OHLCV data as DataFrame or dictionary with nested structure
            
        Returns:
            Dict containing:
                - poc: Point of Control price
                - va_high: Value Area High price
                - va_low: Value Area Low price
                - score: Volume profile score (0-100) based on price position
        """
        try:
            self.logger.debug("Calculating volume profile metrics")
            
            # Convert dictionary to DataFrame if needed
            if isinstance(data, dict):
                if 'data' in data:
                    df = pd.DataFrame(data['data'])
                    self.logger.debug(f"Extracted DataFrame from 'data' key, shape: {df.shape}")
                else:
                    df = pd.DataFrame(data)
                    self.logger.debug(f"Converted dict to DataFrame, shape: {df.shape}")
            elif isinstance(data, pd.DataFrame):
                df = data.copy()
                self.logger.debug(f"Using provided DataFrame, shape: {df.shape}")
            else:
                self.logger.error(f"Invalid data type for volume profile: {type(data)}")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            if df.empty or len(df) == 0:
                self.logger.warning("Empty DataFrame provided for volume profile calculation")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            # Ensure required columns exist
            required_cols = ['close', 'volume']
            if not all(col in df.columns for col in required_cols):
                missing = [col for col in required_cols if col not in df.columns]
                self.logger.error(f"Missing required columns for volume profile: {missing}")
                self.logger.debug(f"Available columns: {list(df.columns)}")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            # Calculate price levels with adaptive bin size based on data volatility
            price_min = df['close'].min()
            price_max = df['close'].max()
            price_range = price_max - price_min
            price_std = df['close'].std()
            
            # Determine optimal number of bins (more bins for higher volatility)
            adaptive_bins = max(20, min(self.volume_profile_bins, 
                                       int(price_range / (price_std * 0.1))))
            self.logger.debug(f"Using {adaptive_bins} bins for volume profile")
            
            bins = np.linspace(price_min, price_max, num=adaptive_bins)
            
            # Create volume profile
            df['price_level'] = pd.cut(df['close'], bins=bins, labels=False)
            # Map labels back to price points for easier interpretation
            price_points = (bins[:-1] + bins[1:]) / 2
            volume_profile = df.groupby('price_level')['volume'].sum()
            volume_profile.index = price_points[volume_profile.index]
            
            # Find Point of Control (POC)
            if volume_profile.empty:
                self.logger.warning("Empty volume profile, returning default values")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            poc = float(volume_profile.idxmax())
            
            # Calculate Value Area (70% of total volume)
            total_volume = volume_profile.sum()
            target_volume = total_volume * self.value_area_volume
            sorted_profile = volume_profile.sort_values(ascending=False)
            cumsum = sorted_profile.cumsum()
            value_area = sorted_profile[cumsum <= target_volume]
            
            if value_area.empty:
                self.logger.warning("Empty value area, using fallback calculation")
                # Fallback to simple percentage around POC
                value_area_range = price_range * 0.2
                va_high = poc + value_area_range/2
                va_low = poc - value_area_range/2
            else:
                va_high = float(max(value_area.index))
                va_low = float(min(value_area.index))
            
            # Calculate score based on price position relative to value area
            current_price = float(df['close'].iloc[-1])
            
            self.logger.debug(f"Volume Profile Results:")
            self.logger.debug(f"- Current Price: {current_price:.2f}")
            self.logger.debug(f"- POC: {poc:.2f}")
            self.logger.debug(f"- Value Area: {va_low:.2f} - {va_high:.2f}")
            
            # Score calculation based on price position
            if current_price < va_low:
                # Below value area - bearish bias
                distance_ratio = (current_price - va_low) / (va_low - price_min) if va_low != price_min else -1
                score = 30 * (1 + distance_ratio)
                position = "below_va"
            elif current_price > va_high:
                # Above value area - bullish bias
                distance_ratio = (current_price - va_high) / (price_max - va_high) if price_max != va_high else 1
                score = 70 + 30 * (1 - distance_ratio)
                position = "above_va"
            else:
                # Inside value area - score based on position relative to POC
                position_ratio = (current_price - va_low) / (va_high - va_low) if va_high != va_low else 0.5
                # Use tanh for smooth transition around POC
                score = 50 * (1 + np.tanh((position_ratio - 0.5) * 2))
                position = "inside_va"
                
            final_score = float: No neutral fallback (50.0) found
- ⚠️  _calculate_sr_levels(self, df: pd.DataFrame) -> float:
        """Calculate support/resistance levels using DBSCAN clustering and Market Profile."""
        debug = DebugMetrics(start_time=time.time())
        
        try:
            if len(df) < 20:
                return 50.0
            
            logger.debug("Starting S/R level analysis with clustering and Market Profile")
            
            # Prepare price and volume data
            prices = df['close'].values.reshape(-1, 1)
            volumes = df['volume'].values
            current_price = df['close'].iloc[-1]
            
            # 1. DBSCAN Clustering for price levels
            # Scale epsilon based on price volatility
            price_std = df['close'].std()
            eps = price_std * 0.001  # Adaptive epsilon
            
            try:
                # Try with sample_weight parameter
                clustering = DBSCAN(
                    eps=eps,
                    min_samples=3,  # Minimum points to form a cluster
                    n_jobs=-1
                ).fit(prices, sample_weight=volumes)
                
                # Get cluster centers and strengths if original method worked
                cluster_data = defaultdict(lambda: {'prices': [], 'volumes': []})
                for idx, label in enumerate(clustering.labels_):
                    if label != -1:  # Ignore noise points
                        cluster_data[label]['prices'].append(prices[idx][0])
                        cluster_data[label]['volumes'].append(volumes[idx])
                        
            except TypeError as e:
                if "got an unexpected keyword argument 'sample_weight'" in str(e):
                    # Fallback for newer scikit-learn versions that don't support sample_weight
                    self.logger.warning("DBSCAN.fit() doesn't support sample_weight, using alternative approach")
                    
                    # Alternative approach - pre-weight points by duplicating based on volume
                    weighted_prices = []
                    for i, p in enumerate(prices):
                        # Scale down to avoid too many duplicates
                        weight = max(1, int(volumes[i] / max(volumes) * 10))
                        weighted_prices.extend([p] * weight)
                    
                    weighted_prices = np.array(weighted_prices)
                    clustering = DBSCAN(
                        eps=eps,
                        min_samples=3,
                        n_jobs=-1
                    ).fit(weighted_prices)
                    
                    # Adjust labels to match original points
                    # This needs careful handling since we're changing dimensions
                    cluster_data = defaultdict(lambda: {'prices': [], 'volumes': []})
                    
                    # Process the clusters from weighted points
                    labels_counter = {}
                    for idx, p in enumerate(weighted_prices):
                        label = clustering.labels_[idx]
                        if label != -1:  # Ignore noise points
                            # Find closest original point
                            distances = np.linalg.norm(prices - p, axis=1)
                            closest_idx = np.argmin(distances)
                            
                            cluster_data[label]['prices'].append(prices[closest_idx][0])
                            cluster_data[label]['volumes'].append(volumes[closest_idx])
                else:
                    # Re-raise if it's a different error
                    raise
            
            sr_levels = []
            for label, data in cluster_data.items():
                # Volume-weighted average price for cluster
                vwap = np.average(data['prices'], weights=data['volumes'])
                total_volume = sum(data['volumes'])
                price_range = max(data['prices']) - min(data['prices'])
                
                sr_levels.append({
                    'price': vwap,
                    'strength': total_volume / df['volume'].sum(),
                    'range': price_range
                })
            
            # 2. Market Profile Integration
            time_blocks = 30  # Number of time blocks for TPO
            price_blocks = 100  # Number of price blocks
            
            # Create time-price matrix
            matrix = np.zeros((price_blocks, time_blocks))
            
            # Calculate price levels
            price_min = df['low'].min()
            price_max = df['high'].max()
            price_step = (price_max - price_min) / price_blocks
            
            # Fill TPO matrix
            for t in range(time_blocks):
                block_data = df.iloc[t::time_blocks]  # Get data for this time block
                if len(block_data) == 0:
                    continue
                
                for _, row in block_data.iterrows():
                    price_idx = int((row['close'] - price_min) / price_step)
                    if 0 <= price_idx < price_blocks:
                        matrix[price_idx, t] = 1
            
            # Calculate TPO profile
            tpo_profile = matrix.sum(axis=1)
            price_levels = np.linspace(price_min, price_max, price_blocks)
            
            # Find TPO peaks
            tpo_peaks, _ = find_peaks(tpo_profile, distance=5)
            
            # Add TPO-based levels
            for peak in tpo_peaks:
                price_level = price_levels[peak]
                tpo_strength = tpo_profile[peak] / time_blocks
                
                sr_levels.append({
                    'price': price_level,
                    'strength': tpo_strength,
                    'range': price_step * 2
                })
            
            # Combine and score levels
            if not sr_levels:
                logger.warning("No S/R levels detected")
                return 50.0
            
            # Sort levels by strength
            sr_levels.sort(key=lambda x: x['strength'], reverse=True)
            
            # Calculate score components
            
            # 1. Distance to nearest strong level (40%)
            distances = []
            for level in sr_levels:
                dist = abs(current_price - level['price']) / current_price
                strength_weighted_dist = dist / (level['strength'] + 0.001)  # Avoid division by zero
                distances.append((strength_weighted_dist, level['strength']))
            
            nearest_dist, nearest_strength = min(distances, key=lambda x: x[0])
            distance_score = 100 * : No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_sr_levels(self, df: pd.DataFrame) -> float:
        """Calculate support/resistance levels using DBSCAN clustering and Market Profile."""
        debug = DebugMetrics(start_time=time.time())
        
        try:
            if len(df) < 20:
                return 50.0
            
            logger.debug("Starting S/R level analysis with clustering and Market Profile")
            
            # Prepare price and volume data
            prices = df['close'].values.reshape(-1, 1)
            volumes = df['volume'].values
            current_price = df['close'].iloc[-1]
            
            # 1. DBSCAN Clustering for price levels
            # Scale epsilon based on price volatility
            price_std = df['close'].std()
            eps = price_std * 0.001  # Adaptive epsilon
            
            try:
                # Try with sample_weight parameter
                clustering = DBSCAN(
                    eps=eps,
                    min_samples=3,  # Minimum points to form a cluster
                    n_jobs=-1
                ).fit(prices, sample_weight=volumes)
                
                # Get cluster centers and strengths if original method worked
                cluster_data = defaultdict(lambda: {'prices': [], 'volumes': []})
                for idx, label in enumerate(clustering.labels_):
                    if label != -1:  # Ignore noise points
                        cluster_data[label]['prices'].append(prices[idx][0])
                        cluster_data[label]['volumes'].append(volumes[idx])
                        
            except TypeError as e:
                if "got an unexpected keyword argument 'sample_weight'" in str(e):
                    # Fallback for newer scikit-learn versions that don't support sample_weight
                    self.logger.warning("DBSCAN.fit() doesn't support sample_weight, using alternative approach")
                    
                    # Alternative approach - pre-weight points by duplicating based on volume
                    weighted_prices = []
                    for i, p in enumerate(prices):
                        # Scale down to avoid too many duplicates
                        weight = max(1, int(volumes[i] / max(volumes) * 10))
                        weighted_prices.extend([p] * weight)
                    
                    weighted_prices = np.array(weighted_prices)
                    clustering = DBSCAN(
                        eps=eps,
                        min_samples=3,
                        n_jobs=-1
                    ).fit(weighted_prices)
                    
                    # Adjust labels to match original points
                    # This needs careful handling since we're changing dimensions
                    cluster_data = defaultdict(lambda: {'prices': [], 'volumes': []})
                    
                    # Process the clusters from weighted points
                    labels_counter = {}
                    for idx, p in enumerate(weighted_prices):
                        label = clustering.labels_[idx]
                        if label != -1:  # Ignore noise points
                            # Find closest original point
                            distances = np.linalg.norm(prices - p, axis=1)
                            closest_idx = np.argmin(distances)
                            
                            cluster_data[label]['prices'].append(prices[closest_idx][0])
                            cluster_data[label]['volumes'].append(volumes[closest_idx])
                else:
                    # Re-raise if it's a different error
                    raise
            
            sr_levels = []
            for label, data in cluster_data.items():
                # Volume-weighted average price for cluster
                vwap = np.average(data['prices'], weights=data['volumes'])
                total_volume = sum(data['volumes'])
                price_range = max(data['prices']) - min(data['prices'])
                
                sr_levels.append({
                    'price': vwap,
                    'strength': total_volume / df['volume'].sum(),
                    'range': price_range
                })
            
            # 2. Market Profile Integration
            time_blocks = 30  # Number of time blocks for TPO
            price_blocks = 100  # Number of price blocks
            
            # Create time-price matrix
            matrix = np.zeros((price_blocks, time_blocks))
            
            # Calculate price levels
            price_min = df['low'].min()
            price_max = df['high'].max()
            price_step = (price_max - price_min) / price_blocks
            
            # Fill TPO matrix
            for t in range(time_blocks):
                block_data = df.iloc[t::time_blocks]  # Get data for this time block
                if len(block_data) == 0:
                    continue
                
                for _, row in block_data.iterrows():
                    price_idx = int((row['close'] - price_min) / price_step)
                    if 0 <= price_idx < price_blocks:
                        matrix[price_idx, t] = 1
            
            # Calculate TPO profile
            tpo_profile = matrix.sum(axis=1)
            price_levels = np.linspace(price_min, price_max, price_blocks)
            
            # Find TPO peaks
            tpo_peaks, _ = find_peaks(tpo_profile, distance=5)
            
            # Add TPO-based levels
            for peak in tpo_peaks:
                price_level = price_levels[peak]
                tpo_strength = tpo_profile[peak] / time_blocks
                
                sr_levels.append({
                    'price': price_level,
                    'strength': tpo_strength,
                    'range': price_step * 2
                })
            
            # Combine and score levels
            if not sr_levels:
                logger.warning("No S/R levels detected")
                return 50.0
            
            # Sort levels by strength
            sr_levels.sort(key=lambda x: x['strength'], reverse=True)
            
            # Calculate score components
            
            # 1. Distance to nearest strong level (40%)
            distances = []
            for level in sr_levels:
                dist = abs(current_price - level['price']) / current_price
                strength_weighted_dist = dist / (level['strength'] + 0.001)  # Avoid division by zero
                distances.append((strength_weighted_dist, level['strength']))
            
            nearest_dist, nearest_strength = min(distances, key=lambda x: x[0])
            distance_score = 100 * : No neutral fallback (50.0) found
- ⚠️  _calculate_sr_levels(self, df: pd.DataFrame) -> float:
        """Calculate support/resistance levels using DBSCAN clustering and Market Profile."""
        debug = DebugMetrics(start_time=time.time())
        
        try:
            if len(df) < 20:
                return 50.0
            
            logger.debug("Starting S/R level analysis with clustering and Market Profile")
            
            # Prepare price and volume data
            prices = df['close'].values.reshape(-1, 1)
            volumes = df['volume'].values
            current_price = df['close'].iloc[-1]
            
            # 1. DBSCAN Clustering for price levels
            # Scale epsilon based on price volatility
            price_std = df['close'].std()
            eps = price_std * 0.001  # Adaptive epsilon
            
            try:
                # Try with sample_weight parameter
                clustering = DBSCAN(
                    eps=eps,
                    min_samples=3,  # Minimum points to form a cluster
                    n_jobs=-1
                ).fit(prices, sample_weight=volumes)
                
                # Get cluster centers and strengths if original method worked
                cluster_data = defaultdict(lambda: {'prices': [], 'volumes': []})
                for idx, label in enumerate(clustering.labels_):
                    if label != -1:  # Ignore noise points
                        cluster_data[label]['prices'].append(prices[idx][0])
                        cluster_data[label]['volumes'].append(volumes[idx])
                        
            except TypeError as e:
                if "got an unexpected keyword argument 'sample_weight'" in str(e):
                    # Fallback for newer scikit-learn versions that don't support sample_weight
                    self.logger.warning("DBSCAN.fit() doesn't support sample_weight, using alternative approach")
                    
                    # Alternative approach - pre-weight points by duplicating based on volume
                    weighted_prices = []
                    for i, p in enumerate(prices):
                        # Scale down to avoid too many duplicates
                        weight = max(1, int(volumes[i] / max(volumes) * 10))
                        weighted_prices.extend([p] * weight)
                    
                    weighted_prices = np.array(weighted_prices)
                    clustering = DBSCAN(
                        eps=eps,
                        min_samples=3,
                        n_jobs=-1
                    ).fit(weighted_prices)
                    
                    # Adjust labels to match original points
                    # This needs careful handling since we're changing dimensions
                    cluster_data = defaultdict(lambda: {'prices': [], 'volumes': []})
                    
                    # Process the clusters from weighted points
                    labels_counter = {}
                    for idx, p in enumerate(weighted_prices):
                        label = clustering.labels_[idx]
                        if label != -1:  # Ignore noise points
                            # Find closest original point
                            distances = np.linalg.norm(prices - p, axis=1)
                            closest_idx = np.argmin(distances)
                            
                            cluster_data[label]['prices'].append(prices[closest_idx][0])
                            cluster_data[label]['volumes'].append(volumes[closest_idx])
                else:
                    # Re-raise if it's a different error
                    raise
            
            sr_levels = []
            for label, data in cluster_data.items():
                # Volume-weighted average price for cluster
                vwap = np.average(data['prices'], weights=data['volumes'])
                total_volume = sum(data['volumes'])
                price_range = max(data['prices']) - min(data['prices'])
                
                sr_levels.append({
                    'price': vwap,
                    'strength': total_volume / df['volume'].sum(),
                    'range': price_range
                })
            
            # 2. Market Profile Integration
            time_blocks = 30  # Number of time blocks for TPO
            price_blocks = 100  # Number of price blocks
            
            # Create time-price matrix
            matrix = np.zeros((price_blocks, time_blocks))
            
            # Calculate price levels
            price_min = df['low'].min()
            price_max = df['high'].max()
            price_step = (price_max - price_min) / price_blocks
            
            # Fill TPO matrix
            for t in range(time_blocks):
                block_data = df.iloc[t::time_blocks]  # Get data for this time block
                if len(block_data) == 0:
                    continue
                
                for _, row in block_data.iterrows():
                    price_idx = int((row['close'] - price_min) / price_step)
                    if 0 <= price_idx < price_blocks:
                        matrix[price_idx, t] = 1
            
            # Calculate TPO profile
            tpo_profile = matrix.sum(axis=1)
            price_levels = np.linspace(price_min, price_max, price_blocks)
            
            # Find TPO peaks
            tpo_peaks, _ = find_peaks(tpo_profile, distance=5)
            
            # Add TPO-based levels
            for peak in tpo_peaks:
                price_level = price_levels[peak]
                tpo_strength = tpo_profile[peak] / time_blocks
                
                sr_levels.append({
                    'price': price_level,
                    'strength': tpo_strength,
                    'range': price_step * 2
                })
            
            # Combine and score levels
            if not sr_levels:
                logger.warning("No S/R levels detected")
                return 50.0
            
            # Sort levels by strength
            sr_levels.sort(key=lambda x: x['strength'], reverse=True)
            
            # Calculate score components
            
            # 1. Distance to nearest strong level (40%)
            distances = []
            for level in sr_levels:
                dist = abs(current_price - level['price']) / current_price
                strength_weighted_dist = dist / (level['strength'] + 0.001)  # Avoid division by zero
                distances.append((strength_weighted_dist, level['strength']))
            
            nearest_dist, nearest_strength = min(distances, key=lambda x: x[0])
            distance_score = 100 * : Non-standard score range detected
- ⚠️  _calculate_alignment_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_alignment_score: No neutral fallback (50.0) found
- ⚠️  _calculate_alignment_score: Non-standard score range detected
- ⚠️  _calculate_confidence(self, component_scores: Dict[str, float]) -> float:
        """Calculate confidence score based on component scores."""
        try:
            if not component_scores:
                return 0.0
            
            # Calculate mean and standard deviation
            scores = list: No neutral fallback (50.0) found
- ⚠️  _calculate_order_blocks_score: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_order_blocks_score: Non-standard score range detected
- ⚠️  _calculate_order_block_proximity(self, current_price, bullish_blocks, bearish_blocks):
        """
        Calculate proximity score to the nearest order block.
        
        Args:
            current_price (float): Current price
            bullish_blocks (list): List of bullish order blocks
            bearish_blocks (list): List of bearish order blocks
            
        Returns:
            float: Proximity score between 0 and 100
        """
        try:
            if not bullish_blocks and not bearish_blocks:
                return 50.0  # Neutral score if no order blocks
                
            # Find closest bullish block
            closest_bullish_distance = float('inf')
            for _, _, low, high in bullish_blocks:
                if current_price >= low and current_price <= high:
                    # Price is inside a bullish block
                    closest_bullish_distance = 0
                    break
                else:
                    # Calculate distance to block
                    distance = min(abs(current_price - low), abs(current_price - high))
                    closest_bullish_distance = min(closest_bullish_distance, distance)
            
            # Find closest bearish block
            closest_bearish_distance = float('inf')
            for _, _, low, high in bearish_blocks:
                if current_price >= low and current_price <= high:
                    # Price is inside a bearish block
                    closest_bearish_distance = 0
                    break
                else:
                    # Calculate distance to block
                    distance = min(abs(current_price - low), abs(current_price - high))
                    closest_bearish_distance = min(closest_bearish_distance, distance)
            
            # Normalize distances relative to current price
            if closest_bullish_distance != float('inf'):
                closest_bullish_distance = closest_bullish_distance / current_price * 100
            else:
                closest_bullish_distance = 100  # Maximum distance
                
            if closest_bearish_distance != float('inf'):
                closest_bearish_distance = closest_bearish_distance / current_price * 100
            else:
                closest_bearish_distance = 100  # Maximum distance
            
            # Calculate scores based on proximity
            bullish_score = 100 - min: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_order_block_proximity(self, current_price, bullish_blocks, bearish_blocks):
        """
        Calculate proximity score to the nearest order block.
        
        Args:
            current_price (float): Current price
            bullish_blocks (list): List of bullish order blocks
            bearish_blocks (list): List of bearish order blocks
            
        Returns:
            float: Proximity score between 0 and 100
        """
        try:
            if not bullish_blocks and not bearish_blocks:
                return 50.0  # Neutral score if no order blocks
                
            # Find closest bullish block
            closest_bullish_distance = float('inf')
            for _, _, low, high in bullish_blocks:
                if current_price >= low and current_price <= high:
                    # Price is inside a bullish block
                    closest_bullish_distance = 0
                    break
                else:
                    # Calculate distance to block
                    distance = min(abs(current_price - low), abs(current_price - high))
                    closest_bullish_distance = min(closest_bullish_distance, distance)
            
            # Find closest bearish block
            closest_bearish_distance = float('inf')
            for _, _, low, high in bearish_blocks:
                if current_price >= low and current_price <= high:
                    # Price is inside a bearish block
                    closest_bearish_distance = 0
                    break
                else:
                    # Calculate distance to block
                    distance = min(abs(current_price - low), abs(current_price - high))
                    closest_bearish_distance = min(closest_bearish_distance, distance)
            
            # Normalize distances relative to current price
            if closest_bullish_distance != float('inf'):
                closest_bullish_distance = closest_bullish_distance / current_price * 100
            else:
                closest_bullish_distance = 100  # Maximum distance
                
            if closest_bearish_distance != float('inf'):
                closest_bearish_distance = closest_bearish_distance / current_price * 100
            else:
                closest_bearish_distance = 100  # Maximum distance
            
            # Calculate scores based on proximity
            bullish_score = 100 - min: No neutral fallback (50.0) found
- ⚠️  _calculate_order_block_proximity(self, current_price, bullish_blocks, bearish_blocks):
        """
        Calculate proximity score to the nearest order block.
        
        Args:
            current_price (float): Current price
            bullish_blocks (list): List of bullish order blocks
            bearish_blocks (list): List of bearish order blocks
            
        Returns:
            float: Proximity score between 0 and 100
        """
        try:
            if not bullish_blocks and not bearish_blocks:
                return 50.0  # Neutral score if no order blocks
                
            # Find closest bullish block
            closest_bullish_distance = float('inf')
            for _, _, low, high in bullish_blocks:
                if current_price >= low and current_price <= high:
                    # Price is inside a bullish block
                    closest_bullish_distance = 0
                    break
                else:
                    # Calculate distance to block
                    distance = min(abs(current_price - low), abs(current_price - high))
                    closest_bullish_distance = min(closest_bullish_distance, distance)
            
            # Find closest bearish block
            closest_bearish_distance = float('inf')
            for _, _, low, high in bearish_blocks:
                if current_price >= low and current_price <= high:
                    # Price is inside a bearish block
                    closest_bearish_distance = 0
                    break
                else:
                    # Calculate distance to block
                    distance = min(abs(current_price - low), abs(current_price - high))
                    closest_bearish_distance = min(closest_bearish_distance, distance)
            
            # Normalize distances relative to current price
            if closest_bullish_distance != float('inf'):
                closest_bullish_distance = closest_bullish_distance / current_price * 100
            else:
                closest_bullish_distance = 100  # Maximum distance
                
            if closest_bearish_distance != float('inf'):
                closest_bearish_distance = closest_bearish_distance / current_price * 100
            else:
                closest_bearish_distance = 100  # Maximum distance
            
            # Calculate scores based on proximity
            bullish_score = 100 - min: Non-standard score range detected
- ⚠️  _calculate_level_proximity(self, current_price, levels):
        """
        Calculate the proximity of the current price to support and resistance levels.
        
        Args:
            current_price (float): The current price
            levels (list): List of support and resistance levels
            
        Returns:
            list: List of scores for each level
        """
        try:
            if not levels or len(levels) == 0:
                self.logger.warning("No support/resistance levels found")
                return [50.0]
                
            scores = []
            for level in levels:
                # Calculate distance as percentage
                distance_pct = abs(current_price - level) / current_price * 100
                
                # Closer levels have higher scores (inverse relationship)
                # Max score at 0% distance, min score at 5% or more distance
                if distance_pct >= 5:
                    score = 0
                else:
                    score = 100 * (1 - distance_pct / 5)
                    
                scores.append(score)
                
            return scores
            
        except Exception as e:
            self.logger.error(f"Error calculating level proximity: {str(e)}")
            return [50.0]

    def _analyze_volume(self, ohlcv_data):
        """
        Analyze volume patterns across timeframes.
        
        Args:
            ohlcv_data (dict): Dictionary of OHLCV data by timeframe
            
        Returns:
            float: Volume analysis score (0-100)
        """
        try:
            if not ohlcv_data or not isinstance(ohlcv_data, dict):
                self.logger.warning("Invalid OHLCV data for volume analysis - using DEFAULT value 50.0")
                return 50.0
                
            available_timeframes = [tf for tf in ohlcv_data.keys() 
                                   if isinstance(ohlcv_data[tf], pd.DataFrame) 
                                   and not ohlcv_data[tf].empty]
                               
            if not available_timeframes:
                self.logger.warning("No valid timeframes available for volume analysis - using DEFAULT value 50.0")
                return 50.0
            
            self.logger.debug(f"Volume analysis using {len(available_timeframes)} timeframes: {available_timeframes}")
                
            # Calculate volume profile score
            vp_scores = []
            for tf in available_timeframes:
                df = ohlcv_data[tf]
                if 'volume' not in df.columns:
                    self.logger.debug: No score clipping found - scores may exceed 0-100 range
- ⚠️  _calculate_level_proximity(self, current_price, levels):
        """
        Calculate the proximity of the current price to support and resistance levels.
        
        Args:
            current_price (float): The current price
            levels (list): List of support and resistance levels
            
        Returns:
            list: List of scores for each level
        """
        try:
            if not levels or len(levels) == 0:
                self.logger.warning("No support/resistance levels found")
                return [50.0]
                
            scores = []
            for level in levels:
                # Calculate distance as percentage
                distance_pct = abs(current_price - level) / current_price * 100
                
                # Closer levels have higher scores (inverse relationship)
                # Max score at 0% distance, min score at 5% or more distance
                if distance_pct >= 5:
                    score = 0
                else:
                    score = 100 * (1 - distance_pct / 5)
                    
                scores.append(score)
                
            return scores
            
        except Exception as e:
            self.logger.error(f"Error calculating level proximity: {str(e)}")
            return [50.0]

    def _analyze_volume(self, ohlcv_data):
        """
        Analyze volume patterns across timeframes.
        
        Args:
            ohlcv_data (dict): Dictionary of OHLCV data by timeframe
            
        Returns:
            float: Volume analysis score (0-100)
        """
        try:
            if not ohlcv_data or not isinstance(ohlcv_data, dict):
                self.logger.warning("Invalid OHLCV data for volume analysis - using DEFAULT value 50.0")
                return 50.0
                
            available_timeframes = [tf for tf in ohlcv_data.keys() 
                                   if isinstance(ohlcv_data[tf], pd.DataFrame) 
                                   and not ohlcv_data[tf].empty]
                               
            if not available_timeframes:
                self.logger.warning("No valid timeframes available for volume analysis - using DEFAULT value 50.0")
                return 50.0
            
            self.logger.debug(f"Volume analysis using {len(available_timeframes)} timeframes: {available_timeframes}")
                
            # Calculate volume profile score
            vp_scores = []
            for tf in available_timeframes:
                df = ohlcv_data[tf]
                if 'volume' not in df.columns:
                    self.logger.debug: No neutral fallback (50.0) found
- ⚠️  _calculate_level_proximity(self, current_price, levels):
        """
        Calculate the proximity of the current price to support and resistance levels.
        
        Args:
            current_price (float): The current price
            levels (list): List of support and resistance levels
            
        Returns:
            list: List of scores for each level
        """
        try:
            if not levels or len(levels) == 0:
                self.logger.warning("No support/resistance levels found")
                return [50.0]
                
            scores = []
            for level in levels:
                # Calculate distance as percentage
                distance_pct = abs(current_price - level) / current_price * 100
                
                # Closer levels have higher scores (inverse relationship)
                # Max score at 0% distance, min score at 5% or more distance
                if distance_pct >= 5:
                    score = 0
                else:
                    score = 100 * (1 - distance_pct / 5)
                    
                scores.append(score)
                
            return scores
            
        except Exception as e:
            self.logger.error(f"Error calculating level proximity: {str(e)}")
            return [50.0]

    def _analyze_volume(self, ohlcv_data):
        """
        Analyze volume patterns across timeframes.
        
        Args:
            ohlcv_data (dict): Dictionary of OHLCV data by timeframe
            
        Returns:
            float: Volume analysis score (0-100)
        """
        try:
            if not ohlcv_data or not isinstance(ohlcv_data, dict):
                self.logger.warning("Invalid OHLCV data for volume analysis - using DEFAULT value 50.0")
                return 50.0
                
            available_timeframes = [tf for tf in ohlcv_data.keys() 
                                   if isinstance(ohlcv_data[tf], pd.DataFrame) 
                                   and not ohlcv_data[tf].empty]
                               
            if not available_timeframes:
                self.logger.warning("No valid timeframes available for volume analysis - using DEFAULT value 50.0")
                return 50.0
            
            self.logger.debug(f"Volume analysis using {len(available_timeframes)} timeframes: {available_timeframes}")
                
            # Calculate volume profile score
            vp_scores = []
            for tf in available_timeframes:
                df = ohlcv_data[tf]
                if 'volume' not in df.columns:
                    self.logger.debug: Non-standard score range detected

**Scoring Methods:**
- `_calculate_component_scores`: ❌ 3 issues
- `_calculate_volume_profile_score`: ✅ OK
- `_calculate_vwap_score`: ❌ 2 issues
- `_calculate_composite_value_score`: ❌ 2 issues
- `_calculate_value_areas(self, data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Calculate value areas from price data."""
        try:
            value_areas = {}
            for tf, tf_data in data.items():
                # Extract DataFrame from the nested structure
                df = tf_data.get('data', pd.DataFrame())
                if isinstance(df, pd.DataFrame) and not df.empty:
                    # Calculate value area high/low
                    volume_profile = self._calculate_volume_profile(df)
                    if all(v != 0 for v in volume_profile.values()):
                        value_areas[tf] = volume_profile
            return value_areas
        except Exception as e:
            self.logger.error(f"Error calculating value areas: {str(e)}")
            return {}

    def calculate_trend_score`: ✅ OK
- `_calculate_dynamic_thresholds(self, df: pd.DataFrame, settings: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate dynamic thresholds for imbalance detection based on historical data.
        
        Args:
            df: DataFrame containing price and volume data
            settings: Dictionary containing threshold settings
            
        Returns:
            Dictionary containing calculated threshold values
        """
        try:
            # Get base threshold values from settings
            base_volume_threshold = settings.get('volume_threshold', 1.5)
            base_price_threshold = settings.get('price_threshold', 0.01)
            
            # Calculate volume statistics
            mean_volume = df['volume'].mean()
            std_volume = df['volume'].std()
            
            # Calculate price statistics
            price_changes = df['close'].pct_change().abs()
            mean_price_change = price_changes.mean()
            std_price_change = price_changes.std()
            
            # Calculate dynamic thresholds
            volume_threshold = mean_volume + (std_volume * base_volume_threshold)
            price_threshold = mean_price_change + (std_price_change * base_price_threshold)
            
            # Calculate additional thresholds for different levels
            return {
                'volume_threshold': volume_threshold,
                'price_threshold': price_threshold,
                'strong_volume_threshold': volume_threshold * 2,
                'strong_price_threshold': price_threshold * 2,
                'extreme_volume_threshold': volume_threshold * 3,
                'extreme_price_threshold': price_threshold * 3
            }
            
        except Exception as e:
            logger.error(f"Error calculating dynamic thresholds: {str(e)}")
            # Return default thresholds if calculation fails
            return {
                'volume_threshold': 1.5,
                'price_threshold': 0.01,
                'strong_volume_threshold': 3.0,
                'strong_price_threshold': 0.02,
                'extreme_volume_threshold': 4.5,
                'extreme_price_threshold': 0.03
            }

    async def _detect_imbalance_levels(self, df: pd.DataFrame, thresholds: Dict[str, float], settings: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect imbalance levels in price data using dynamic thresholds.
        """
        try:
            bullish_levels = []
            bearish_levels = []
            
            # Get threshold values with defaults
            volume_threshold = thresholds.get('volume_threshold', 1.5)
            price_threshold = thresholds.get('price_threshold', 0.01)
            
            # Group data into price rows for analysis
            df['price_row'] = (df['close'] / settings.get('ticks_per_row', 50)).round() * settings.get('ticks_per_row', 50)
            grouped = df.groupby('price_row').agg({
                'volume': 'sum',
                'close': ['first', 'last']
            })
            
            # Analyze each price level for imbalances
            for idx, row in grouped.iterrows():
                price_change = row['close']['last'] - row['close']['first']
                price_level = idx
                volume = row['volume']
                
                if price_change > 0:
                    imbalance_ratio = 1 + (price_change / row['close']['first'])
                    if imbalance_ratio > volume_threshold:
                        bullish_levels.append({
                            'price_level': price_level,
                            'strength': min(imbalance_ratio / volume_threshold, 1.0),
                            'volume': volume,
                            'ratio': imbalance_ratio
                        })
                elif price_change < 0:
                    imbalance_ratio = 1 / (1 - (price_change / row['close']['first']))
                    if imbalance_ratio > volume_threshold:
                        bearish_levels.append({
                            'price_level': price_level,
                            'strength': min(imbalance_ratio / volume_threshold, 1.0),
                            'volume': volume,
                            'ratio': imbalance_ratio
                        })
            
            # Sort levels by strength
            bullish_levels.sort(key=lambda x: x['strength'], reverse=True)
            bearish_levels.sort(key=lambda x: x['strength'], reverse=True)
            
            # Limit to most significant levels
            max_levels = settings.get('max_levels', 5)
            bullish_levels = bullish_levels[:max_levels]
            bearish_levels = bearish_levels[:max_levels]
            
            return {
                'bullish': bullish_levels,
                'bearish': bearish_levels
            }
            
        except Exception as e:
            logger.error(f"Error detecting imbalance levels: {str(e)}")
            return {'bullish': [], 'bearish': []}

    def _calculate_imbalance_strength(self, ratio: float, thresholds: Dict[str, float]) -> float:
        """
        Calculate the strength of an imbalance based on its ratio and thresholds.
        
        Args:
            ratio (float): Imbalance ratio
            thresholds (Dict[str, float]): Threshold levels
            
        Returns:
            float: Strength score between 0 and 1
        """
        try:
            if ratio >= thresholds['extreme_volume_threshold']:
                return 1.0
            elif ratio >= thresholds['strong_volume_threshold']:
                return 0.75
            elif ratio >= thresholds['volume_threshold']:
                return 0.5
            else:
                return 0.0
        except Exception as e:
            logger.error(f"Error calculating imbalance strength: {str(e)}")
            return 0.0

    def _calculate_volume_score`: ✅ OK
- `_calculate_value_area_score`: ❌ 1 issues
- `_calculate_structural_score`: ✅ OK
- `_calculate_short_term_trend(self, df: pd.DataFrame, period: int = 10) -> float:
        """Calculate short-term trend direction and strength."""
        try:
            if len(df) < period:
                return 0.0
            
            # Get recent closes
            recent_closes = df['close'].tail(period)
            
            # Calculate linear regression slope
            x = np.arange(len(recent_closes))
            slope, _ = np.polyfit(x, recent_closes, 1)
            
            # Normalize slope to percentage
            return slope / recent_closes.mean()

        except Exception as e:
            logger.error(f"Error calculating trend: {str(e)}")
            return 0.0

    def _calculate_weighted_score`: ❌ 2 issues
- `_calculate_volume_profile(self, data: Union[pd.DataFrame, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate volume profile metrics including Point of Control and Value Area.
        
        This method analyzes price and volume data to identify key volume-based price levels:
        - Point of Control (POC): The price level with the highest trading volume
        - Value Area High (VAH): Upper boundary containing specified % of volume
        - Value Area Low (VAL): Lower boundary containing specified % of volume
        
        Args:
            data: OHLCV data as DataFrame or dictionary with nested structure
            
        Returns:
            Dict containing:
                - poc: Point of Control price
                - va_high: Value Area High price
                - va_low: Value Area Low price
                - score: Volume profile score (0-100) based on price position
        """
        try:
            self.logger.debug("Calculating volume profile metrics")
            
            # Convert dictionary to DataFrame if needed
            if isinstance(data, dict):
                if 'data' in data:
                    df = pd.DataFrame(data['data'])
                    self.logger.debug(f"Extracted DataFrame from 'data' key, shape: {df.shape}")
                else:
                    df = pd.DataFrame(data)
                    self.logger.debug(f"Converted dict to DataFrame, shape: {df.shape}")
            elif isinstance(data, pd.DataFrame):
                df = data.copy()
                self.logger.debug(f"Using provided DataFrame, shape: {df.shape}")
            else:
                self.logger.error(f"Invalid data type for volume profile: {type(data)}")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            if df.empty or len(df) == 0:
                self.logger.warning("Empty DataFrame provided for volume profile calculation")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            # Ensure required columns exist
            required_cols = ['close', 'volume']
            if not all(col in df.columns for col in required_cols):
                missing = [col for col in required_cols if col not in df.columns]
                self.logger.error(f"Missing required columns for volume profile: {missing}")
                self.logger.debug(f"Available columns: {list(df.columns)}")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            # Calculate price levels with adaptive bin size based on data volatility
            price_min = df['close'].min()
            price_max = df['close'].max()
            price_range = price_max - price_min
            price_std = df['close'].std()
            
            # Determine optimal number of bins (more bins for higher volatility)
            adaptive_bins = max(20, min(self.volume_profile_bins, 
                                       int(price_range / (price_std * 0.1))))
            self.logger.debug(f"Using {adaptive_bins} bins for volume profile")
            
            bins = np.linspace(price_min, price_max, num=adaptive_bins)
            
            # Create volume profile
            df['price_level'] = pd.cut(df['close'], bins=bins, labels=False)
            # Map labels back to price points for easier interpretation
            price_points = (bins[:-1] + bins[1:]) / 2
            volume_profile = df.groupby('price_level')['volume'].sum()
            volume_profile.index = price_points[volume_profile.index]
            
            # Find Point of Control (POC)
            if volume_profile.empty:
                self.logger.warning("Empty volume profile, returning default values")
                return {
                    'poc': 0,
                    'va_high': 0,
                    'va_low': 0,
                    'score': 50.0
                }
                
            poc = float(volume_profile.idxmax())
            
            # Calculate Value Area (70% of total volume)
            total_volume = volume_profile.sum()
            target_volume = total_volume * self.value_area_volume
            sorted_profile = volume_profile.sort_values(ascending=False)
            cumsum = sorted_profile.cumsum()
            value_area = sorted_profile[cumsum <= target_volume]
            
            if value_area.empty:
                self.logger.warning("Empty value area, using fallback calculation")
                # Fallback to simple percentage around POC
                value_area_range = price_range * 0.2
                va_high = poc + value_area_range/2
                va_low = poc - value_area_range/2
            else:
                va_high = float(max(value_area.index))
                va_low = float(min(value_area.index))
            
            # Calculate score based on price position relative to value area
            current_price = float(df['close'].iloc[-1])
            
            self.logger.debug(f"Volume Profile Results:")
            self.logger.debug(f"- Current Price: {current_price:.2f}")
            self.logger.debug(f"- POC: {poc:.2f}")
            self.logger.debug(f"- Value Area: {va_low:.2f} - {va_high:.2f}")
            
            # Score calculation based on price position
            if current_price < va_low:
                # Below value area - bearish bias
                distance_ratio = (current_price - va_low) / (va_low - price_min) if va_low != price_min else -1
                score = 30 * (1 + distance_ratio)
                position = "below_va"
            elif current_price > va_high:
                # Above value area - bullish bias
                distance_ratio = (current_price - va_high) / (price_max - va_high) if price_max != va_high else 1
                score = 70 + 30 * (1 - distance_ratio)
                position = "above_va"
            else:
                # Inside value area - score based on position relative to POC
                position_ratio = (current_price - va_low) / (va_high - va_low) if va_high != va_low else 0.5
                # Use tanh for smooth transition around POC
                score = 50 * (1 + np.tanh((position_ratio - 0.5) * 2))
                position = "inside_va"
                
            final_score = float`: ❌ 1 issues
- `_calculate_sr_levels(self, df: pd.DataFrame) -> float:
        """Calculate support/resistance levels using DBSCAN clustering and Market Profile."""
        debug = DebugMetrics(start_time=time.time())
        
        try:
            if len(df) < 20:
                return 50.0
            
            logger.debug("Starting S/R level analysis with clustering and Market Profile")
            
            # Prepare price and volume data
            prices = df['close'].values.reshape(-1, 1)
            volumes = df['volume'].values
            current_price = df['close'].iloc[-1]
            
            # 1. DBSCAN Clustering for price levels
            # Scale epsilon based on price volatility
            price_std = df['close'].std()
            eps = price_std * 0.001  # Adaptive epsilon
            
            try:
                # Try with sample_weight parameter
                clustering = DBSCAN(
                    eps=eps,
                    min_samples=3,  # Minimum points to form a cluster
                    n_jobs=-1
                ).fit(prices, sample_weight=volumes)
                
                # Get cluster centers and strengths if original method worked
                cluster_data = defaultdict(lambda: {'prices': [], 'volumes': []})
                for idx, label in enumerate(clustering.labels_):
                    if label != -1:  # Ignore noise points
                        cluster_data[label]['prices'].append(prices[idx][0])
                        cluster_data[label]['volumes'].append(volumes[idx])
                        
            except TypeError as e:
                if "got an unexpected keyword argument 'sample_weight'" in str(e):
                    # Fallback for newer scikit-learn versions that don't support sample_weight
                    self.logger.warning("DBSCAN.fit() doesn't support sample_weight, using alternative approach")
                    
                    # Alternative approach - pre-weight points by duplicating based on volume
                    weighted_prices = []
                    for i, p in enumerate(prices):
                        # Scale down to avoid too many duplicates
                        weight = max(1, int(volumes[i] / max(volumes) * 10))
                        weighted_prices.extend([p] * weight)
                    
                    weighted_prices = np.array(weighted_prices)
                    clustering = DBSCAN(
                        eps=eps,
                        min_samples=3,
                        n_jobs=-1
                    ).fit(weighted_prices)
                    
                    # Adjust labels to match original points
                    # This needs careful handling since we're changing dimensions
                    cluster_data = defaultdict(lambda: {'prices': [], 'volumes': []})
                    
                    # Process the clusters from weighted points
                    labels_counter = {}
                    for idx, p in enumerate(weighted_prices):
                        label = clustering.labels_[idx]
                        if label != -1:  # Ignore noise points
                            # Find closest original point
                            distances = np.linalg.norm(prices - p, axis=1)
                            closest_idx = np.argmin(distances)
                            
                            cluster_data[label]['prices'].append(prices[closest_idx][0])
                            cluster_data[label]['volumes'].append(volumes[closest_idx])
                else:
                    # Re-raise if it's a different error
                    raise
            
            sr_levels = []
            for label, data in cluster_data.items():
                # Volume-weighted average price for cluster
                vwap = np.average(data['prices'], weights=data['volumes'])
                total_volume = sum(data['volumes'])
                price_range = max(data['prices']) - min(data['prices'])
                
                sr_levels.append({
                    'price': vwap,
                    'strength': total_volume / df['volume'].sum(),
                    'range': price_range
                })
            
            # 2. Market Profile Integration
            time_blocks = 30  # Number of time blocks for TPO
            price_blocks = 100  # Number of price blocks
            
            # Create time-price matrix
            matrix = np.zeros((price_blocks, time_blocks))
            
            # Calculate price levels
            price_min = df['low'].min()
            price_max = df['high'].max()
            price_step = (price_max - price_min) / price_blocks
            
            # Fill TPO matrix
            for t in range(time_blocks):
                block_data = df.iloc[t::time_blocks]  # Get data for this time block
                if len(block_data) == 0:
                    continue
                
                for _, row in block_data.iterrows():
                    price_idx = int((row['close'] - price_min) / price_step)
                    if 0 <= price_idx < price_blocks:
                        matrix[price_idx, t] = 1
            
            # Calculate TPO profile
            tpo_profile = matrix.sum(axis=1)
            price_levels = np.linspace(price_min, price_max, price_blocks)
            
            # Find TPO peaks
            tpo_peaks, _ = find_peaks(tpo_profile, distance=5)
            
            # Add TPO-based levels
            for peak in tpo_peaks:
                price_level = price_levels[peak]
                tpo_strength = tpo_profile[peak] / time_blocks
                
                sr_levels.append({
                    'price': price_level,
                    'strength': tpo_strength,
                    'range': price_step * 2
                })
            
            # Combine and score levels
            if not sr_levels:
                logger.warning("No S/R levels detected")
                return 50.0
            
            # Sort levels by strength
            sr_levels.sort(key=lambda x: x['strength'], reverse=True)
            
            # Calculate score components
            
            # 1. Distance to nearest strong level (40%)
            distances = []
            for level in sr_levels:
                dist = abs(current_price - level['price']) / current_price
                strength_weighted_dist = dist / (level['strength'] + 0.001)  # Avoid division by zero
                distances.append((strength_weighted_dist, level['strength']))
            
            nearest_dist, nearest_strength = min(distances, key=lambda x: x[0])
            distance_score = 100 * `: ❌ 3 issues
- `_calculate_alignment_score`: ❌ 3 issues
- `_calculate_confidence(self, component_scores: Dict[str, float]) -> float:
        """Calculate confidence score based on component scores."""
        try:
            if not component_scores:
                return 0.0
            
            # Calculate mean and standard deviation
            scores = list`: ❌ 1 issues
- `_calculate_price_volume_correlation(self, df: pd.DataFrame) -> float:
        """Calculate score based on correlation between price moves and volume.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            float: Score from 0-100
        """
        try:
            if df.empty or not all(col in df.columns for col in ['close', 'volume']) or len(df) < 10:
                return 50.0
                
            # Calculate price changes
            df_copy = df.copy()
            df_copy['price_change'] = df_copy['close'].pct_change()
            df_copy['abs_price_change'] = df_copy['price_change'].abs()
            
            # Remove NaN values
            df_copy = df_copy.dropna()
            
            if len(df_copy) < 5:
                return 50.0
                
            # Calculate correlation between absolute price change and volume
            correlation = df_copy['abs_price_change'].corr(df_copy['volume'])
            
            # Calculate directional bias
            # Check if volume is higher on up days vs down days
            up_days = df_copy[df_copy['price_change'] > 0]
            down_days = df_copy[df_copy['price_change'] < 0]
            
            if len(up_days) > 0 and len(down_days) > 0:
                avg_up_volume = up_days['volume'].mean()
                avg_down_volume = down_days['volume'].mean()
                
                if avg_up_volume > avg_down_volume:
                    # Higher volume on up days is bullish
                    direction = 1.0
                else:
                    # Higher volume on down days is bearish
                    direction = -1.0
            else:
                direction = 0.0
                
            # Convert correlation to score (0-100)
            # High correlation is good, direction determines bullish/bearish
            base_score = 50 + `: ✅ OK
- `_calculate_order_blocks_score`: ❌ 2 issues
- `_calculate_order_block_proximity(self, current_price, bullish_blocks, bearish_blocks):
        """
        Calculate proximity score to the nearest order block.
        
        Args:
            current_price (float): Current price
            bullish_blocks (list): List of bullish order blocks
            bearish_blocks (list): List of bearish order blocks
            
        Returns:
            float: Proximity score between 0 and 100
        """
        try:
            if not bullish_blocks and not bearish_blocks:
                return 50.0  # Neutral score if no order blocks
                
            # Find closest bullish block
            closest_bullish_distance = float('inf')
            for _, _, low, high in bullish_blocks:
                if current_price >= low and current_price <= high:
                    # Price is inside a bullish block
                    closest_bullish_distance = 0
                    break
                else:
                    # Calculate distance to block
                    distance = min(abs(current_price - low), abs(current_price - high))
                    closest_bullish_distance = min(closest_bullish_distance, distance)
            
            # Find closest bearish block
            closest_bearish_distance = float('inf')
            for _, _, low, high in bearish_blocks:
                if current_price >= low and current_price <= high:
                    # Price is inside a bearish block
                    closest_bearish_distance = 0
                    break
                else:
                    # Calculate distance to block
                    distance = min(abs(current_price - low), abs(current_price - high))
                    closest_bearish_distance = min(closest_bearish_distance, distance)
            
            # Normalize distances relative to current price
            if closest_bullish_distance != float('inf'):
                closest_bullish_distance = closest_bullish_distance / current_price * 100
            else:
                closest_bullish_distance = 100  # Maximum distance
                
            if closest_bearish_distance != float('inf'):
                closest_bearish_distance = closest_bearish_distance / current_price * 100
            else:
                closest_bearish_distance = 100  # Maximum distance
            
            # Calculate scores based on proximity
            bullish_score = 100 - min`: ❌ 3 issues
- `_calculate_level_proximity(self, current_price, levels):
        """
        Calculate the proximity of the current price to support and resistance levels.
        
        Args:
            current_price (float): The current price
            levels (list): List of support and resistance levels
            
        Returns:
            list: List of scores for each level
        """
        try:
            if not levels or len(levels) == 0:
                self.logger.warning("No support/resistance levels found")
                return [50.0]
                
            scores = []
            for level in levels:
                # Calculate distance as percentage
                distance_pct = abs(current_price - level) / current_price * 100
                
                # Closer levels have higher scores (inverse relationship)
                # Max score at 0% distance, min score at 5% or more distance
                if distance_pct >= 5:
                    score = 0
                else:
                    score = 100 * (1 - distance_pct / 5)
                    
                scores.append(score)
                
            return scores
            
        except Exception as e:
            self.logger.error(f"Error calculating level proximity: {str(e)}")
            return [50.0]

    def _analyze_volume(self, ohlcv_data):
        """
        Analyze volume patterns across timeframes.
        
        Args:
            ohlcv_data (dict): Dictionary of OHLCV data by timeframe
            
        Returns:
            float: Volume analysis score (0-100)
        """
        try:
            if not ohlcv_data or not isinstance(ohlcv_data, dict):
                self.logger.warning("Invalid OHLCV data for volume analysis - using DEFAULT value 50.0")
                return 50.0
                
            available_timeframes = [tf for tf in ohlcv_data.keys() 
                                   if isinstance(ohlcv_data[tf], pd.DataFrame) 
                                   and not ohlcv_data[tf].empty]
                               
            if not available_timeframes:
                self.logger.warning("No valid timeframes available for volume analysis - using DEFAULT value 50.0")
                return 50.0
            
            self.logger.debug(f"Volume analysis using {len(available_timeframes)} timeframes: {available_timeframes}")
                
            # Calculate volume profile score
            vp_scores = []
            for tf in available_timeframes:
                df = ohlcv_data[tf]
                if 'volume' not in df.columns:
                    self.logger.debug`: ❌ 3 issues
- `_calculate_single_vwap_score`: ✅ OK


## Summary Statistics
- **Total Scoring Methods:** 59
- **Total Issues Found:** 83
- **Overall Health:** ❌ Critical

## Recommendations

### High Priority Fixes
1. **Score Clipping**: Ensure all scoring methods use `np.clip(score, 0, 100)` to bound results
2. **Neutral Fallbacks**: All methods should return 50.0 for error/neutral conditions
3. **Bullish/Bearish Logic**: Verify directional logic is correct (bullish increases score, bearish decreases)

### Implementation Guidelines
1. **Standard Score Range**: Always use 0-100 range with 50 as neutral
2. **Error Handling**: Return 50.0 for any error conditions
3. **Consistent Clipping**: Use `float(np.clip(score, 0, 100))` for final return
4. **Clear Documentation**: Document the bullish/bearish logic for each component

### Validation Requirements
1. **Range Tests**: Verify all scores stay within 0-100 bounds
2. **Logic Tests**: Confirm bullish conditions produce higher scores than bearish
3. **Edge Case Tests**: Test with extreme values, NaN, and zero data
4. **Consistency Tests**: Ensure similar market conditions produce similar scores

## Next Steps
1. Review and fix identified issues
2. Implement comprehensive validation tests
3. Add automated scoring range checks to CI/CD pipeline
4. Create documentation for scoring methodology
