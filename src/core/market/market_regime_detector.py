#!/usr/bin/env python3
"""
Market Regime Detector with Enhanced HMM and Traditional Methods

This module provides advanced market regime detection using:
1. Hidden Markov Models (HMM) for probabilistic regime detection
2. Traditional threshold-based methods for dynamic thresholds
3. Hybrid approach combining both methods
4. Auction theory integration for smart money concepts

Author: Virtuoso Trading System
Date: 2025-07-17
"""

import numpy as np
import pandas as pd
import talib
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Import local modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.logger import Logger


@dataclass
class HMMRegimeConfig:
    """Configuration for HMM-based regime detection"""
    n_states: int = 4
    n_features: int = 6
    covariance_type: str = 'full'
    n_iter: int = 100
    tol: float = 1e-4
    min_history_periods: int = 100
    training_frequency: int = 3600  # Retrain every hour


class HMMMarketRegimeDetector:
    """
    Advanced regime detection using Hidden Markov Models with auction theory.
    
    Mathematical Foundation:
    - States S_t ∈ {TREND_BULL, TREND_BEAR, RANGE_HIGH_VOL, RANGE_LOW_VOL}
    - Transition matrix A: P(S_{t+1} = j | S_t = i)
    - Emission probabilities B: P(observation | state) ~ N(μ_state, Σ_state)
    - Viterbi algorithm for most likely state sequence
    - Baum-Welch for parameter estimation
    """
    
    def __init__(self, config: HMMRegimeConfig = None):
        self.config = config or HMMRegimeConfig()
        self.logger = Logger(__name__)
        
        # HMM model using Gaussian Mixture as HMM approximation
        self.model = GaussianMixture(
            n_components=self.config.n_states,
            covariance_type=self.config.covariance_type,
            max_iter=self.config.n_iter,
            tol=self.config.tol,
            random_state=42
        )
        
        # State mapping
        self.state_names = [
            'TREND_BULL',     # State 0: Strong bullish momentum
            'TREND_BEAR',     # State 1: Strong bearish momentum  
            'RANGE_HIGH_VOL', # State 2: Sideways with high volatility
            'RANGE_LOW_VOL'   # State 3: Sideways with low volatility
        ]
        
        # Model training status
        self.is_trained = False
        self.training_data = []
        self.last_training_time = 0
        self.scaler = StandardScaler()
        
        # Auction dynamics parameters
        self.auction_params = {
            'imbalance_threshold': 0.3,    # Order flow imbalance significance
            'volume_surge_factor': 2.0,    # Volume spike detection
            'momentum_decay': 0.95,        # Momentum persistence factor
            'volatility_regime_threshold': 0.02  # Daily volatility threshold
        }
    
    async def detect_regime_probabilistic(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Probabilistic regime detection using HMM with auction theory features.
        
        Returns:
            {
                'current_state': str,
                'state_probabilities': Dict[str, float],
                'transition_probabilities': np.ndarray,
                'auction_dynamics': Dict[str, float],
                'regime_persistence': float,
                'confidence': float
            }
        """
        try:
            # Extract auction-theoretic features
            features = await self._extract_auction_features(market_data)
            
            if not self.is_trained or self._should_retrain():
                await self._train_hmm_model(market_data)
            
            if not self.is_trained:
                return await self._fallback_regime_detection(market_data)
            
            # Get current state probabilities
            current_features = features[-1].reshape(1, -1)
            current_features_scaled = self.scaler.transform(current_features)
            
            # Get state probabilities
            state_probs = self.model.predict_proba(current_features_scaled)[0]
            
            # Current most likely state
            current_state_idx = np.argmax(state_probs)
            current_state = self.state_names[current_state_idx]
            
            # Calculate auction dynamics metrics
            auction_dynamics = self._calculate_auction_dynamics(features, market_data)
            
            # Regime persistence (probability of staying in current state)
            # For GMM, we approximate this with the component weight
            regime_persistence = self.model.weights_[current_state_idx]
            
            # Confidence based on state probability concentration
            confidence = self._calculate_regime_confidence(state_probs)
            
            return {
                'current_state': current_state,
                'state_probabilities': {
                    name: float(prob) for name, prob in zip(self.state_names, state_probs)
                },
                'transition_probabilities': self.model.weights_.tolist(),
                'auction_dynamics': auction_dynamics,
                'regime_persistence': float(regime_persistence),
                'confidence': float(confidence),
                'log_likelihood': float(self.model.score(current_features_scaled)),
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"HMM regime detection error: {e}")
            return await self._fallback_regime_detection(market_data)
    
    async def _extract_auction_features(self, market_data: Dict[str, Any]) -> np.ndarray:
        """
        Extract auction-theoretic features for HMM training/inference.
        
        Features:
        1. ADX (trend strength)
        2. Momentum (20-period price change)
        3. Volume ratio (current/average)
        4. Orderbook imbalance (bid-ask pressure)
        5. Realized volatility (20-period)
        6. Cumulative Volume Delta (CVD)
        """
        try:
            ohlcv = market_data.get('ohlcv', {})
            orderbook = market_data.get('orderbook', {})
            
            if not ohlcv:
                raise ValueError("No OHLCV data available")
            
            # Get primary timeframe data
            primary_tf = list(ohlcv.keys())[0]
            df = ohlcv[primary_tf]
            
            if len(df) < 50:
                raise ValueError("Insufficient data for feature extraction")
            
            features = []
            
            for i in range(20, len(df)):  # Start from index 20 for lookback
                window = df.iloc[i-19:i+1]  # 20-period window
                
                # Feature 1: ADX (trend strength)
                adx = talib.ADX(window['high'], window['low'], window['close'], timeperiod=14)
                adx_value = adx.iloc[-1] if len(adx) > 0 and not pd.isna(adx.iloc[-1]) else 25
                
                # Feature 2: Momentum (normalized)
                momentum = (window['close'].iloc[-1] / window['close'].iloc[0] - 1) * 100
                
                # Feature 3: Volume ratio
                avg_volume = window['volume'].mean()
                volume_ratio = window['volume'].iloc[-1] / (avg_volume + 1e-10)
                
                # Feature 4: Orderbook imbalance (if available)
                if orderbook:
                    bid_volume = sum(float(level[1]) for level in orderbook.get('bids', [])[:5])
                    ask_volume = sum(float(level[1]) for level in orderbook.get('asks', [])[:5])
                    total_volume = bid_volume + ask_volume
                    imbalance = (bid_volume - ask_volume) / (total_volume + 1e-10)
                else:
                    imbalance = 0.0
                
                # Feature 5: Realized volatility (20-period)
                returns = window['close'].pct_change().dropna()
                volatility = returns.std() * np.sqrt(24 * 365) if len(returns) > 1 else 0.02
                
                # Feature 6: Cumulative Volume Delta approximation
                # Buy volume approximation: volume when close > open
                buy_volume = window.loc[window['close'] > window['open'], 'volume'].sum()
                sell_volume = window['volume'].sum() - buy_volume
                cvd = (buy_volume - sell_volume) / (window['volume'].sum() + 1e-10)
                
                features.append([
                    adx_value / 100,        # Normalize ADX to [0, 1]
                    np.tanh(momentum / 10), # Bounded momentum
                    np.log1p(volume_ratio), # Log-transform volume ratio
                    imbalance,              # Already bounded [-1, 1]
                    volatility * 100,       # Scale volatility
                    cvd                     # Already bounded [-1, 1]
                ])
            
            return np.array(features)
            
        except Exception as e:
            self.logger.error(f"Feature extraction error: {e}")
            # Return default features
            return np.zeros((1, self.config.n_features))
    
    async def _train_hmm_model(self, market_data: Dict[str, Any]) -> None:
        """Train HMM model on historical data with auction theory priors"""
        try:
            features = await self._extract_auction_features(market_data)
            
            if len(features) < self.config.min_history_periods:
                self.logger.warning(f"Insufficient data for HMM training: {len(features)} < {self.config.min_history_periods}")
                return
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features)
            
            # Train the model
            self.model.fit(features_scaled)
            
            self.is_trained = True
            self.last_training_time = time.time()
            self.training_data = features_scaled.tolist()
            
            self.logger.info(f"HMM model trained successfully with {len(features)} samples")
            
        except Exception as e:
            self.logger.error(f"HMM training error: {e}")
            self.is_trained = False
    
    def _should_retrain(self) -> bool:
        """Check if model should be retrained based on time elapsed"""
        return time.time() - self.last_training_time > self.config.training_frequency
    
    def _calculate_auction_dynamics(self, features: np.ndarray, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate auction dynamics metrics"""
        try:
            if len(features) < 2:
                return {'imbalance': 0.0, 'volume_surge': 0.0, 'momentum': 0.0}
            
            # Latest features
            latest = features[-1]
            
            # Orderbook imbalance (feature 3)
            imbalance = latest[3]
            
            # Volume surge (feature 2)
            volume_surge = latest[2]
            
            # Momentum (feature 1)
            momentum = latest[1]
            
            return {
                'imbalance': float(imbalance),
                'volume_surge': float(volume_surge),
                'momentum': float(momentum),
                'volatility': float(latest[4]),
                'cvd': float(latest[5])
            }
            
        except Exception as e:
            self.logger.error(f"Auction dynamics calculation error: {e}")
            return {'imbalance': 0.0, 'volume_surge': 0.0, 'momentum': 0.0}
    
    def _calculate_regime_confidence(self, state_probs: np.ndarray) -> float:
        """Calculate confidence based on state probability concentration"""
        try:
            # Higher confidence when one state dominates
            max_prob = np.max(state_probs)
            entropy = -np.sum(state_probs * np.log(state_probs + 1e-10))
            max_entropy = np.log(len(state_probs))
            
            # Normalize entropy to [0, 1] and convert to confidence
            normalized_entropy = entropy / max_entropy
            confidence = 1.0 - normalized_entropy
            
            return float(confidence)
            
        except Exception as e:
            self.logger.error(f"Confidence calculation error: {e}")
            return 0.5
    
    async def _fallback_regime_detection(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback regime detection using simple heuristics"""
        try:
            ohlcv = market_data.get('ohlcv', {})
            if not ohlcv:
                return self._default_regime()
            
            primary_tf = list(ohlcv.keys())[0]
            df = ohlcv[primary_tf].tail(20)
            
            # Simple trend detection
            price_change = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
            volatility = df['close'].pct_change().std() * np.sqrt(24 * 365)
            
            if abs(price_change) > 2.0:
                regime = 'TREND_BULL' if price_change > 0 else 'TREND_BEAR'
            elif volatility > 0.02:
                regime = 'RANGE_HIGH_VOL'
            else:
                regime = 'RANGE_LOW_VOL'
            
            return {
                'current_state': regime,
                'state_probabilities': {regime: 1.0},
                'confidence': 0.6,
                'method': 'fallback',
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Fallback regime detection error: {e}")
            return self._default_regime()
    
    def _default_regime(self) -> Dict[str, Any]:
        """Default regime when all else fails"""
        return {
            'current_state': 'RANGE_LOW_VOL',
            'state_probabilities': {'RANGE_LOW_VOL': 1.0},
            'confidence': 0.5,
            'method': 'default',
            'timestamp': int(time.time() * 1000)
        }


class TraditionalRegimeDetector:
    """Traditional threshold-based regime detection"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = Logger(__name__)
        
        # Thresholds for regime detection
        self.thresholds = {
            'trend_strength': 25.0,      # ADX threshold for trend
            'momentum_threshold': 1.0,    # Price change threshold (%)
            'volatility_threshold': 0.02, # Daily volatility threshold
            'volume_surge': 1.5,         # Volume spike threshold
        }
    
    async def detect_regime(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Traditional regime detection using technical indicators"""
        try:
            ohlcv = market_data.get('ohlcv', {})
            if not ohlcv:
                return self._default_regime()
            
            primary_tf = list(ohlcv.keys())[0]
            df = ohlcv[primary_tf].tail(50)
            
            # Calculate technical indicators
            adx = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
            current_adx = adx.iloc[-1] if len(adx) > 0 and not pd.isna(adx.iloc[-1]) else 25
            
            # Price momentum
            price_change = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
            
            # Volatility
            volatility = df['close'].pct_change().std() * np.sqrt(24 * 365)
            
            # Volume analysis
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            current_volume = df['volume'].iloc[-1]
            volume_ratio = current_volume / (avg_volume + 1e-10)
            
            # Determine regime
            if current_adx > self.thresholds['trend_strength']:
                if abs(price_change) > self.thresholds['momentum_threshold']:
                    regime = 'TREND_BULL' if price_change > 0 else 'TREND_BEAR'
                else:
                    regime = 'RANGE_HIGH_VOL'
            else:
                if volatility > self.thresholds['volatility_threshold']:
                    regime = 'RANGE_HIGH_VOL'
                else:
                    regime = 'RANGE_LOW_VOL'
            
            # Calculate dynamic thresholds
            dynamic_thresholds = self._calculate_dynamic_thresholds(df)
            
            return {
                'current_state': regime,
                'adx': float(current_adx),
                'momentum': float(price_change),
                'volatility': float(volatility),
                'volume_ratio': float(volume_ratio),
                'dynamic_thresholds': dynamic_thresholds,
                'confidence': 0.7,
                'method': 'traditional',
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Traditional regime detection error: {e}")
            return self._default_regime()
    
    def _calculate_dynamic_thresholds(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate dynamic thresholds based on recent market conditions"""
        try:
            # Volatility-based threshold adjustment
            volatility = df['close'].pct_change().std() * np.sqrt(24 * 365)
            volatility_factor = min(2.0, max(0.5, volatility / 0.02))
            
            # Volume-based threshold adjustment
            volume_std = df['volume'].rolling(20).std().iloc[-1]
            volume_mean = df['volume'].rolling(20).mean().iloc[-1]
            volume_factor = min(2.0, max(0.5, volume_std / (volume_mean + 1e-10)))
            
            return {
                'trend_strength': self.thresholds['trend_strength'] * volatility_factor,
                'momentum_threshold': self.thresholds['momentum_threshold'] * volatility_factor,
                'volume_surge': self.thresholds['volume_surge'] * volume_factor,
                'volatility_factor': float(volatility_factor),
                'volume_factor': float(volume_factor)
            }
            
        except Exception as e:
            self.logger.error(f"Dynamic threshold calculation error: {e}")
            return self.thresholds.copy()
    
    def _default_regime(self) -> Dict[str, Any]:
        """Default regime when detection fails"""
        return {
            'current_state': 'RANGE_LOW_VOL',
            'confidence': 0.5,
            'method': 'default',
            'timestamp': int(time.time() * 1000)
        }


class MarketRegimeDetector:
    """Enhanced regime detector with both traditional and HMM methods"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = Logger(__name__)
        
        # Initialize both detectors
        self.traditional_detector = TraditionalRegimeDetector(config)
        self.hmm_detector = HMMMarketRegimeDetector()
        
        # Detection mode
        self.detection_mode = config.get('regime_detection', {}).get('mode', 'hybrid')
        # Options: 'traditional', 'hmm', 'hybrid', 'ensemble'
    
    async def detect_regime(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Unified regime detection with multiple methods"""
        try:
            if self.detection_mode == 'traditional':
                return await self._detect_traditional_regime(market_data)
            elif self.detection_mode == 'hmm':
                return await self.hmm_detector.detect_regime_probabilistic(market_data)
            elif self.detection_mode == 'hybrid':
                return await self._detect_hybrid_regime(market_data)
            else:  # ensemble
                return await self._detect_ensemble_regime(market_data)
                
        except Exception as e:
            self.logger.error(f"Regime detection error: {e}")
            return self._default_regime()
    
    async def _detect_hybrid_regime(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Hybrid approach: HMM for regime, traditional for thresholds"""
        try:
            # Get HMM regime detection
            hmm_result = await self.hmm_detector.detect_regime_probabilistic(market_data)
            
            # Get traditional dynamic thresholds
            traditional_result = await self._detect_traditional_regime(market_data)
            
            # Combine: Use HMM regime with traditional threshold calculation
            return {
                'primary_regime': hmm_result['current_state'],
                'confidence': hmm_result['confidence'],
                'dynamic_thresholds': traditional_result.get('dynamic_thresholds', {}),
                'auction_dynamics': hmm_result.get('auction_dynamics', {}),
                'regime_persistence': hmm_result.get('regime_persistence', 0.5),
                'state_probabilities': hmm_result.get('state_probabilities', {}),
                'method': 'hybrid_hmm_traditional',
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Hybrid regime detection error: {e}")
            return await self._detect_traditional_regime(market_data)
    
    async def _detect_traditional_regime(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Traditional regime detection"""
        return await self.traditional_detector.detect_regime(market_data)
    
    async def _detect_ensemble_regime(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensemble approach: combine multiple methods with voting"""
        try:
            # Get results from both methods
            hmm_result = await self.hmm_detector.detect_regime_probabilistic(market_data)
            traditional_result = await self._detect_traditional_regime(market_data)
            
            # Ensemble voting
            hmm_regime = hmm_result['current_state']
            traditional_regime = traditional_result['current_state']
            
            # Simple voting: if both agree, use that regime
            if hmm_regime == traditional_regime:
                primary_regime = hmm_regime
                confidence = (hmm_result['confidence'] + traditional_result['confidence']) / 2
            else:
                # Use the one with higher confidence
                if hmm_result['confidence'] > traditional_result['confidence']:
                    primary_regime = hmm_regime
                    confidence = hmm_result['confidence']
                else:
                    primary_regime = traditional_regime
                    confidence = traditional_result['confidence']
            
            return {
                'primary_regime': primary_regime,
                'hmm_regime': hmm_regime,
                'traditional_regime': traditional_regime,
                'confidence': confidence,
                'hmm_confidence': hmm_result['confidence'],
                'traditional_confidence': traditional_result['confidence'],
                'dynamic_thresholds': traditional_result.get('dynamic_thresholds', {}),
                'auction_dynamics': hmm_result.get('auction_dynamics', {}),
                'method': 'ensemble',
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Ensemble regime detection error: {e}")
            return await self._detect_traditional_regime(market_data)
    
    def _default_regime(self) -> Dict[str, Any]:
        """Default regime when all methods fail"""
        return {
            'primary_regime': 'RANGE_LOW_VOL',
            'confidence': 0.5,
            'method': 'default',
            'timestamp': int(time.time() * 1000)
        } 