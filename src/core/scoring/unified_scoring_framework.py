"""
Unified Scoring Framework - Fixed Version

This is a simplified version of the unified scoring framework that properly handles
dict-based configuration access without attribute errors.
"""

import numpy as np
import time
from typing import Dict, Any, Union, Optional
from enum import Enum
from src.core.logger import Logger

class ScoringMode(Enum):
    """Scoring modes for the unified framework."""
    AUTO_DETECT = "auto_detect"
    TRADITIONAL = "traditional"
    ENHANCED_LINEAR = "enhanced_linear"
    HYBRID = "hybrid"
    LINEAR_FALLBACK = "linear_fallback"

class ScoringConfig:
    """Configuration class for scoring framework."""
    def __init__(self, **kwargs):
        self.debug_mode = kwargs.get('debug_mode', False)
        self.mode = kwargs.get('mode', 'enhanced_linear')
        self.enable_caching = kwargs.get('enable_caching', True)
        self.performance_tracking = kwargs.get('performance_tracking', True)
        self.log_transformations = kwargs.get('log_transformations', False)
        self.sigmoid_steepness = kwargs.get('sigmoid_steepness', 0.1)
        self.tanh_sensitivity = kwargs.get('tanh_sensitivity', 1.0)
        self.market_regime_aware = kwargs.get('market_regime_aware', True)
        self.cache_timeout = kwargs.get('cache_timeout', 300)
        self.max_cache_size = kwargs.get('max_cache_size', 1000)

class UnifiedScoringFramework:
    """
    Unified scoring framework for all indicator transformations.
    
    Automatically detects method sophistication and applies appropriate enhancements.
    """
    
    def __init__(self, config: Union[Dict[str, Any], ScoringConfig] = None):
        self.config = config or {}
        self.logger = Logger(__name__)
        
        # Helper function to get config values
        def get_config_value(key, default):
            if hasattr(self.config, key):
                return getattr(self.config, key)
            elif isinstance(self.config, dict):
                return self.config.get(key, default)
            else:
                return default
        
        # Configuration defaults
        self.debug_mode = get_config_value('debug_mode', False)
        self.mode = get_config_value('mode', 'enhanced_linear')
        self.enable_caching = get_config_value('enable_caching', True)
        self.performance_tracking = get_config_value('performance_tracking', True)
        self.log_transformations = get_config_value('log_transformations', False)
        self.sigmoid_steepness = get_config_value('sigmoid_steepness', 0.1)
        self.tanh_sensitivity = get_config_value('tanh_sensitivity', 1.0)
        self.market_regime_aware = get_config_value('market_regime_aware', True)
        self.cache_timeout = get_config_value('cache_timeout', 300)  # 5 minutes
        self.max_cache_size = get_config_value('max_cache_size', 1000)
        
        if self.debug_mode:
            self.logger.debug("🔧 Initializing UnifiedScoringFramework (Fixed Version)")
            self.logger.debug(f"📋 Configuration: mode={self.mode}, debug={self.debug_mode}")
        
        # Registry of traditional sophisticated methods
        self.traditional_methods = {
            'obv_sigmoid': self._obv_sigmoid_transform,
            'vwap_tanh_log': self._vwap_tanh_log_transform,
            'volume_profile_tanh': self._volume_profile_tanh_transform,
            'cvd_tanh': self._cvd_tanh_transform,
            'relative_volume_tanh': self._relative_volume_tanh_transform
        }
        
        # Registry of enhanced methods for linear indicators
        self.enhanced_methods = {
            'rsi_enhanced': self._rsi_enhanced_transform,
            'volatility_enhanced': self._volatility_enhanced_transform,
            'volume_enhanced': self._volume_enhanced_transform,
            'oir_di_enhanced': self._oir_di_enhanced_transform,
            'momentum_enhanced': self._momentum_enhanced_transform
        }
        
        # Performance tracking
        self._method_performance = {}
        self._cache = {} if self.enable_caching else None
        self._cache_timestamps = {} if self.enable_caching else None
        
        if self.debug_mode:
            self.logger.debug(f"📚 Traditional methods: {len(self.traditional_methods)}")
            self.logger.debug(f"🚀 Enhanced methods: {len(self.enhanced_methods)}")
    
    def transform_score(self, value: Union[float, np.ndarray], method_name: str, **kwargs) -> float:
        """
        Main transformation method with automatic method detection.
        
        Args:
            value: Input value to transform
            method_name: Name of the transformation method
            **kwargs: Additional parameters for transformation
            
        Returns:
            Transformed score (0-100 range)
        """
        start_time = time.time()
        
        if self.debug_mode:
            self.logger.debug(f"🎯 transform_score: {method_name}, value={value}")
        
        try:
            # Input validation
            if value is None:
                return 50.0
            
            if isinstance(value, (list, tuple)):
                value = np.array(value)
            
            if isinstance(value, np.ndarray):
                if len(value) == 0:
                    return 50.0
                value = float(value[-1])
            
            # Check cache first
            cache_key = None
            if self._cache is not None:
                cache_key = f"{method_name}_{value}_{hash(str(sorted(kwargs.items())))}"
                if cache_key in self._cache:
                    cached_result = self._cache[cache_key]
                    if self.debug_mode:
                        self.logger.debug(f"💾 Cache hit: {cached_result}")
                    return cached_result
            
            # Apply transformation based on mode
            if self.mode == ScoringMode.AUTO_DETECT.value:
                if self._is_sophisticated_method(method_name):
                    result = self._apply_traditional_method(value, method_name, **kwargs)
                else:
                    result = self._apply_enhanced_method(value, method_name, **kwargs)
            elif self.mode == ScoringMode.TRADITIONAL.value:
                result = self._apply_traditional_method(value, method_name, **kwargs)
            elif self.mode == ScoringMode.ENHANCED_LINEAR.value:
                result = self._apply_enhanced_method(value, method_name, **kwargs)
            elif self.mode == ScoringMode.HYBRID.value:
                result = self._apply_hybrid_method(value, method_name, **kwargs)
            else:  # LINEAR_FALLBACK
                result = self._apply_linear_fallback(value, method_name, **kwargs)
            
            # Ensure result is valid
            if np.isnan(result) or np.isinf(result):
                result = 50.0
            
            # Ensure bounds
            result = np.clip(result, 0, 100)
            
            # Cache result
            if self._cache is not None:
                self._cache[cache_key] = result
                self._cache_timestamps[cache_key] = time.time()
            
            # Performance tracking
            calculation_time = time.time() - start_time
            if self.performance_tracking:
                self._track_performance(method_name, calculation_time, result)
            
            if self.debug_mode:
                self.logger.debug(f"✅ {method_name}: {value} → {result:.2f} ({calculation_time*1000:.2f}ms)")
            
            return result
                
        except Exception as e:
            self.logger.error(f"❌ Error in unified scoring for {method_name}: {e}")
            return 50.0
    
    def _is_sophisticated_method(self, method_name: str) -> bool:
        """Detect if method already uses sophisticated transformations."""
        sophisticated_patterns = [
            'obv', 'vwap', 'volume_profile', 'cvd', 'relative_volume',
            'orderbook_pressure', 'flow_velocity', 'sentiment_sigmoid'
        ]
        return any(pattern in method_name.lower() for pattern in sophisticated_patterns)
    
    def _apply_traditional_method(self, value: float, method_name: str, **kwargs) -> float:
        """Apply traditional sophisticated method."""
        if method_name in self.traditional_methods:
            return self.traditional_methods[method_name](value, **kwargs)
        else:
            return self._apply_enhanced_method(value, method_name, **kwargs)
    
    def _apply_enhanced_method(self, value: float, method_name: str, **kwargs) -> float:
        """Apply enhanced transformation method."""
        if method_name in self.enhanced_methods:
            return self.enhanced_methods[method_name](value, **kwargs)
        else:
            return self._apply_linear_fallback(value, method_name, **kwargs)
    
    def _apply_hybrid_method(self, value: float, method_name: str, **kwargs) -> float:
        """Combine traditional and enhanced approaches."""
        if self._is_sophisticated_method(method_name):
            traditional_score = self._apply_traditional_method(value, method_name, **kwargs)
            enhanced_score = self._apply_enhanced_method(value, method_name, **kwargs)
            return 0.7 * traditional_score + 0.3 * enhanced_score
        else:
            return self._apply_enhanced_method(value, method_name, **kwargs)
    
    def _apply_linear_fallback(self, value: float, method_name: str, **kwargs) -> float:
        """Linear fallback for compatibility."""
        return np.clip(value, 0, 100)
    
    # ==================== TRADITIONAL SOPHISTICATED METHODS ====================
    
    def _obv_sigmoid_transform(self, z_score: float, **kwargs) -> float:
        """Preserve existing OBV sigmoid transformation."""
        try:
            return 100 / (1 + np.exp(-0.5 * z_score))
        except:
            return 50.0
    
    def _vwap_tanh_log_transform(self, price_vwap_ratio: float, **kwargs) -> float:
        """Preserve existing VWAP tanh + log transformation."""
        try:
            if price_vwap_ratio <= 0:
                return 50.0
            return 50 * (1 + np.tanh(np.log(price_vwap_ratio)))
        except:
            return 50.0
    
    def _volume_profile_tanh_transform(self, position_ratio: float, **kwargs) -> float:
        """Preserve existing volume profile tanh transformation."""
        try:
            return 50 * (1 + np.tanh((position_ratio - 0.5) * 2))
        except:
            return 50.0
    
    def _cvd_tanh_transform(self, cvd_percentage: float, **kwargs) -> float:
        """Preserve existing CVD tanh transformation."""
        try:
            return 50 + (np.tanh(cvd_percentage * 3) * 50)
        except:
            return 50.0
    
    def _relative_volume_tanh_transform(self, relative_volume: float, **kwargs) -> float:
        """Preserve existing relative volume tanh transformation."""
        try:
            return 50 + (np.tanh(relative_volume - 1) * 50)
        except:
            return 50.0
    
    # ==================== ENHANCED TRANSFORMATIONS ====================
    
    def _rsi_enhanced_transform(self, rsi_value: float, overbought: float = 70, 
                               oversold: float = 30, market_regime: Dict = None, **kwargs) -> float:
        """Enhanced RSI scoring with non-linear extreme value handling."""
        try:
            # Dynamic thresholds based on market regime
            if market_regime and self.market_regime_aware:
                if market_regime.get('volatility') == 'HIGH':
                    overbought, oversold = 75, 25
                elif market_regime.get('trend') == 'STRONG':
                    overbought, oversold = 75, 25
            
            # Non-linear transformation for extreme values
            if rsi_value > overbought:
                excess = rsi_value - overbought
                return 50 - 50 * (1 - np.exp(-excess * 0.15))
            elif rsi_value < oversold:
                deficit = oversold - rsi_value
                return 50 + 50 * (1 - np.exp(-deficit * 0.15))
            else:
                # Smooth sigmoid in neutral zone
                center = (overbought + oversold) / 2
                return self._sigmoid_transform(rsi_value, center=center, steepness=0.05)
        except:
            return 50.0
    
    def _volatility_enhanced_transform(self, volatility: float, base_threshold: float = 60,
                                     market_regime: Dict = None, **kwargs) -> float:
        """Enhanced volatility scoring with regime awareness."""
        try:
            # Adjust threshold based on market regime
            if market_regime and self.market_regime_aware:
                regime_multiplier = {
                    'trending': 1.2, 'ranging': 0.8, 'volatile': 1.5
                }.get(market_regime.get('primary_regime', 'normal'), 1.0)
                threshold = base_threshold * regime_multiplier
            else:
                threshold = base_threshold
            
            # Non-linear transformation
            if volatility > threshold:
                excess = volatility - threshold
                return max(0, 50 - 50 * (1 - np.exp(-excess * 0.1)))
            else:
                return self._sigmoid_transform(volatility, center=threshold/2, steepness=0.05)
        except:
            return 50.0
    
    def _volume_enhanced_transform(self, volume_ratio: float, **kwargs) -> float:
        """Enhanced volume scoring with sigmoid normalization."""
        try:
            if volume_ratio > 3.0:
                excess = volume_ratio - 3.0
                return 75 + 25 * (1 - np.exp(-excess * 0.3))
            else:
                return self._sigmoid_transform(volume_ratio, center=1.0, steepness=0.5)
        except:
            return 50.0
    
    def _oir_di_enhanced_transform(self, ratio_value: float, confidence_weight: float = 1.0, **kwargs) -> float:
        """Enhanced OIR/DI scoring with confidence weighting."""
        try:
            base_score = 50 * (1 + np.tanh(ratio_value * 2))
            confidence_factor = 1 / (1 + np.exp(-(confidence_weight - 0.5))) * 0.3 + 0.7
            return base_score * confidence_factor + 50 * (1 - confidence_factor)
        except:
            return 50.0
    
    def _momentum_enhanced_transform(self, momentum_value: float, 
                                   volatility_adjustment: bool = True, **kwargs) -> float:
        """Enhanced momentum scoring with volatility adjustment."""
        try:
            base_score = 50 + 50 * np.tanh(momentum_value * 0.1)
            if volatility_adjustment:
                volatility_factor = kwargs.get('volatility_factor', 1.0)
                return base_score * volatility_factor
            return base_score
        except:
            return 50.0
    
    def _sigmoid_transform(self, value: float, center: float = 50, steepness: float = None) -> float:
        """Configurable sigmoid transformation."""
        steepness = steepness or self.sigmoid_steepness
        try:
            normalized = (value - center) * steepness
            return 100 / (1 + np.exp(-normalized))
        except:
            return 50.0
    
    def _track_performance(self, method_name: str, calculation_time: float, result: float) -> None:
        """Track method performance."""
        if method_name not in self._method_performance:
            self._method_performance[method_name] = {
                'calls': 0, 'total_time': 0.0, 'avg_time': 0.0,
                'min_time': float('inf'), 'max_time': 0.0, 'last_result': 0.0
            }
        
        perf = self._method_performance[method_name]
        perf['calls'] += 1
        perf['total_time'] += calculation_time
        perf['avg_time'] = perf['total_time'] / perf['calls']
        perf['min_time'] = min(perf['min_time'], calculation_time)
        perf['max_time'] = max(perf['max_time'], calculation_time)
        perf['last_result'] = result
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        total_calls = sum(perf['calls'] for perf in self._method_performance.values())
        total_time = sum(perf['total_time'] for perf in self._method_performance.values())
        
        return {
            'total_calls': total_calls,
            'total_time_ms': total_time * 1000,
            'average_time_ms': (total_time / total_calls * 1000) if total_calls > 0 else 0.0,
            'methods_tracked': len(self._method_performance),
            'cache_size': len(self._cache) if self._cache else 0,
            'config': {
                'mode': self.mode,
                'debug_mode': self.debug_mode,
                'caching_enabled': self.enable_caching
            }
        }
    
    def clear_cache(self) -> None:
        """Clear the cache."""
        if self._cache:
            self._cache.clear()
            self._cache_timestamps.clear()
            if self.debug_mode:
                self.logger.debug("💾 Cache cleared")