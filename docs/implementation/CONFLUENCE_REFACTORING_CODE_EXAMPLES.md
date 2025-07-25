# ConfluenceAnalyzer Refactoring - Code Examples

## 1. Base Interfaces

### IValidator Interface
```python
# src/core/analysis/confluence/validators/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of validation operation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    validated_data: Optional[Dict[str, Any]] = None

class IValidator(ABC):
    """Base interface for all validators."""
    
    @abstractmethod
    async def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate the input data."""
        pass
    
    @abstractmethod
    def get_validation_rules(self) -> Dict[str, Any]:
        """Return validation rules for documentation."""
        pass
```

### ITransformer Interface
```python
# src/core/analysis/confluence/transformers/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import pandas as pd

@dataclass
class TransformedData:
    """Container for transformed data."""
    indicator_type: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: float

class ITransformer(ABC):
    """Base interface for data transformers."""
    
    @abstractmethod
    async def transform(self, market_data: Dict[str, Any]) -> TransformedData:
        """Transform market data for specific indicator."""
        pass
    
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """Return list of required data fields."""
        pass
    
    @abstractmethod
    def validate_input(self, market_data: Dict[str, Any]) -> bool:
        """Quick validation of input data."""
        pass
```

## 2. Validator Implementations

### Market Data Validator
```python
# src/core/analysis/confluence/validators/market_data.py
import pandas as pd
from typing import Dict, Any, List, Optional
from .base import IValidator, ValidationResult

class MarketDataValidator(IValidator):
    """Validates market data structure and content."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.required_fields = ['symbol', 'ohlcv', 'orderbook', 'trades']
        self.required_timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        
    async def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate market data comprehensively."""
        errors = []
        warnings = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate OHLCV data
        if 'ohlcv' in data:
            ohlcv_errors = self._validate_ohlcv(data['ohlcv'])
            errors.extend(ohlcv_errors)
        
        # Validate orderbook
        if 'orderbook' in data:
            orderbook_errors = self._validate_orderbook(data['orderbook'])
            errors.extend(orderbook_errors)
        
        # Validate trades
        if 'trades' in data:
            trades_warnings = self._validate_trades(data['trades'])
            warnings.extend(trades_warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            validated_data=data if len(errors) == 0 else None
        )
    
    def _validate_ohlcv(self, ohlcv_data: Dict[str, pd.DataFrame]) -> List[str]:
        """Validate OHLCV data structure."""
        errors = []
        
        for timeframe in self.required_timeframes:
            if timeframe not in ohlcv_data:
                errors.append(f"Missing timeframe: {timeframe}")
                continue
                
            df = ohlcv_data[timeframe]
            if not isinstance(df, pd.DataFrame):
                errors.append(f"Invalid data type for {timeframe}: expected DataFrame")
                continue
                
            # Check required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                errors.append(f"Missing columns in {timeframe}: {missing_cols}")
            
            # Check data quality
            if df.empty:
                errors.append(f"Empty DataFrame for {timeframe}")
            elif len(df) < 30:
                errors.append(f"Insufficient data for {timeframe}: {len(df)} rows")
        
        return errors
    
    def _validate_orderbook(self, orderbook: Dict[str, Any]) -> List[str]:
        """Validate orderbook structure."""
        errors = []
        
        if 'bids' not in orderbook:
            errors.append("Missing 'bids' in orderbook")
        if 'asks' not in orderbook:
            errors.append("Missing 'asks' in orderbook")
        
        # Validate depth
        if 'bids' in orderbook and len(orderbook['bids']) < 10:
            errors.append(f"Insufficient orderbook depth: {len(orderbook['bids'])} bids")
        
        return errors
    
    def _validate_trades(self, trades: List[Dict]) -> List[str]:
        """Validate trades data."""
        warnings = []
        
        if len(trades) < 50:
            warnings.append(f"Low trade count: {len(trades)}")
        
        return warnings
    
    def get_validation_rules(self) -> Dict[str, Any]:
        """Return validation rules."""
        return {
            'required_fields': self.required_fields,
            'required_timeframes': self.required_timeframes,
            'min_ohlcv_rows': 30,
            'min_orderbook_depth': 10,
            'min_trades': 50
        }
```

## 3. Transformer Implementations

### Technical Data Transformer
```python
# src/core/analysis/confluence/transformers/technical.py
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from .base import ITransformer, TransformedData
import time

class TechnicalTransformer(ITransformer):
    """Transforms market data for technical indicators."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.required_timeframes = ['5m', '15m', '1h', '4h']
        
    async def transform(self, market_data: Dict[str, Any]) -> TransformedData:
        """Transform market data for technical analysis."""
        start_time = time.time()
        
        # Validate input
        if not self.validate_input(market_data):
            raise ValueError("Invalid market data for technical transformation")
        
        # Extract OHLCV data
        ohlcv_data = market_data['ohlcv']
        
        # Prepare data for each timeframe
        transformed = {}
        for timeframe in self.required_timeframes:
            if timeframe in ohlcv_data:
                df = ohlcv_data[timeframe].copy()
                
                # Add derived fields
                df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
                df['price_range'] = df['high'] - df['low']
                df['volume_weighted_price'] = (df['volume'] * df['typical_price']).cumsum() / df['volume'].cumsum()
                
                # Ensure proper indexing
                if 'timestamp' in df.columns:
                    df.set_index('timestamp', inplace=True)
                
                transformed[timeframe] = df
        
        # Add market context
        context = {
            'current_price': market_data.get('current_price', 0),
            'price_change_24h': market_data.get('price_change_24h', 0),
            'volume_24h': market_data.get('volume_24h', 0)
        }
        
        return TransformedData(
            indicator_type='technical',
            data={
                'ohlcv': transformed,
                'context': context
            },
            metadata={
                'transform_time': time.time() - start_time,
                'timeframes': list(transformed.keys())
            },
            timestamp=time.time()
        )
    
    def get_required_fields(self) -> List[str]:
        """Return required fields for technical analysis."""
        return ['ohlcv', 'current_price']
    
    def validate_input(self, market_data: Dict[str, Any]) -> bool:
        """Quick validation of input data."""
        if 'ohlcv' not in market_data:
            return False
            
        ohlcv = market_data['ohlcv']
        return any(tf in ohlcv for tf in self.required_timeframes)
```

## 4. Orchestration Components

### Indicator Executor
```python
# src/core/analysis/confluence/orchestration/executor.py
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import time
import logging

@dataclass
class ExecutionResult:
    """Result of indicator execution."""
    indicator_type: str
    result: Dict[str, Any]
    execution_time: float
    success: bool
    error: Optional[str] = None

class IndicatorExecutor:
    """Manages parallel execution of indicators."""
    
    def __init__(self, indicators: Dict[str, Any], config: Dict[str, Any]):
        self.indicators = indicators
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    async def execute(self, transformed_data: Dict[str, Any]) -> Dict[str, ExecutionResult]:
        """Execute all indicators in parallel."""
        tasks = []
        
        for indicator_type, indicator in self.indicators.items():
            if indicator_type in transformed_data:
                task = self._execute_indicator(
                    indicator_type, 
                    indicator, 
                    transformed_data[indicator_type]
                )
                tasks.append(task)
        
        # Execute all indicators in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        execution_results = {}
        for result in results:
            if isinstance(result, ExecutionResult):
                execution_results[result.indicator_type] = result
            else:
                self.logger.error(f"Unexpected result type: {type(result)}")
        
        return execution_results
    
    async def _execute_indicator(self, 
                                indicator_type: str, 
                                indicator: Any, 
                                data: Any) -> ExecutionResult:
        """Execute single indicator with error handling."""
        start_time = time.time()
        
        try:
            # Execute indicator analysis
            result = await indicator.analyze(data)
            
            return ExecutionResult(
                indicator_type=indicator_type,
                result=result,
                execution_time=time.time() - start_time,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Error executing {indicator_type}: {str(e)}")
            
            return ExecutionResult(
                indicator_type=indicator_type,
                result={},
                execution_time=time.time() - start_time,
                success=False,
                error=str(e)
            )
```

## 5. Scoring Engine

### Score Calculator
```python
# src/core/analysis/confluence/scoring/calculator.py
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import numpy as np

@dataclass
class ComponentScore:
    """Individual component score."""
    component: str
    score: float
    weight: float
    confidence: float
    signals: List[str]

class ScoreCalculator:
    """Calculates confluence scores from indicator results."""
    
    def __init__(self, weight_manager: 'WeightManager'):
        self.weight_manager = weight_manager
        
    def calculate(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall confluence score."""
        component_scores = {}
        
        # Calculate individual component scores
        for component, result in results.items():
            if result.success:
                score = self._calculate_component_score(component, result.result)
                component_scores[component] = score
        
        # Calculate weighted confluence score
        confluence_score = self._calculate_weighted_score(component_scores)
        
        # Calculate reliability
        reliability = self._calculate_reliability(component_scores)
        
        # Determine overall signal
        signal = self._determine_signal(confluence_score)
        
        return {
            'confluence_score': confluence_score,
            'reliability': reliability,
            'signal': signal,
            'component_scores': component_scores,
            'top_signals': self._get_top_signals(component_scores)
        }
    
    def _calculate_component_score(self, component: str, result: Dict[str, Any]) -> ComponentScore:
        """Calculate score for individual component."""
        # Extract score from result
        raw_score = result.get('score', 50.0)
        
        # Normalize score to 0-100 range
        normalized_score = max(0, min(100, raw_score))
        
        # Get component weight
        weight = self.weight_manager.get_component_weight(component)
        
        # Calculate confidence based on data quality
        confidence = result.get('confidence', 0.8)
        
        # Extract signals
        signals = result.get('signals', [])
        
        return ComponentScore(
            component=component,
            score=normalized_score,
            weight=weight,
            confidence=confidence,
            signals=signals
        )
    
    def _calculate_weighted_score(self, scores: Dict[str, ComponentScore]) -> float:
        """Calculate weighted average of component scores."""
        if not scores:
            return 50.0
        
        total_weight = sum(s.weight * s.confidence for s in scores.values())
        if total_weight == 0:
            return 50.0
        
        weighted_sum = sum(
            s.score * s.weight * s.confidence 
            for s in scores.values()
        )
        
        return weighted_sum / total_weight
    
    def _calculate_reliability(self, scores: Dict[str, ComponentScore]) -> float:
        """Calculate reliability based on component agreement."""
        if len(scores) < 2:
            return 0.5
        
        # Calculate standard deviation of scores
        score_values = [s.score for s in scores.values()]
        std_dev = np.std(score_values)
        
        # Lower std dev = higher reliability
        reliability = 1.0 - (std_dev / 50.0)  # Normalize by max possible std dev
        
        # Factor in confidence levels
        avg_confidence = np.mean([s.confidence for s in scores.values()])
        
        return reliability * avg_confidence
    
    def _determine_signal(self, score: float) -> str:
        """Determine trading signal from score."""
        if score >= 70:
            return 'STRONG_BUY'
        elif score >= 60:
            return 'BUY'
        elif score >= 40:
            return 'NEUTRAL'
        elif score >= 30:
            return 'SELL'
        else:
            return 'STRONG_SELL'
    
    def _get_top_signals(self, scores: Dict[str, ComponentScore], top_n: int = 5) -> List[Dict[str, Any]]:
        """Get top contributing signals."""
        all_signals = []
        
        for component, score in scores.items():
            for signal in score.signals:
                all_signals.append({
                    'component': component,
                    'signal': signal,
                    'impact': score.score * score.weight,
                    'confidence': score.confidence
                })
        
        # Sort by impact
        all_signals.sort(key=lambda x: x['impact'], reverse=True)
        
        return all_signals[:top_n]
```

## 6. New Slim ConfluenceAnalyzer

```python
# src/core/analysis/confluence/analyzer.py
from typing import Dict, Any
import logging
import time
from .validators import MarketDataValidator
from .transformers import TransformerPipeline
from .orchestration import IndicatorExecutor
from .scoring import ScoreCalculator
from .formatting import ResponseFormatter

class ConfluenceAnalyzer:
    """Slim orchestrator for confluence analysis."""
    
    def __init__(self, container: 'ConfluenceContainer'):
        """Initialize with dependency injection container."""
        self.logger = logging.getLogger(__name__)
        
        # Inject dependencies
        self.validator = container.get_validator()
        self.transformer_pipeline = container.get_transformer_pipeline()
        self.executor = container.get_executor()
        self.calculator = container.get_calculator()
        self.formatter = container.get_formatter()
        
    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data and return confluence scores."""
        self.logger.info("Starting confluence analysis")
        start_time = time.time()
        
        try:
            # Step 1: Validate market data
            validation_result = await self.validator.validate(market_data)
            if not validation_result.is_valid:
                return self.formatter.format_error(validation_result.errors)
            
            # Step 2: Transform data for all indicators
            transformed_data = await self.transformer_pipeline.transform(
                validation_result.validated_data
            )
            
            # Step 3: Execute indicators in parallel
            execution_results = await self.executor.execute(transformed_data)
            
            # Step 4: Calculate scores
            scores = self.calculator.calculate(execution_results)
            
            # Step 5: Format response
            response = self.formatter.format(scores)
            
            # Add metadata
            response['metadata'] = {
                'analysis_time': time.time() - start_time,
                'components_analyzed': len(execution_results),
                'warnings': validation_result.warnings
            }
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error in confluence analysis: {str(e)}")
            return self.formatter.format_error([str(e)])
```

## 7. Dependency Injection Container

```python
# src/core/analysis/confluence/container.py
from typing import Dict, Any
from .validators import MarketDataValidator, TimeframeValidator
from .transformers import (
    TechnicalTransformer, VolumeTransformer, 
    OrderbookTransformer, OrderflowTransformer,
    PriceStructureTransformer, SentimentTransformer,
    TransformerPipeline
)
from .orchestration import IndicatorExecutor, FlowTracker
from .scoring import ScoreCalculator, WeightManager
from .formatting import ResponseFormatter

class ConfluenceContainer:
    """Dependency injection container for confluence components."""
    
    def __init__(self, config: Dict[str, Any], indicators: Dict[str, Any]):
        self.config = config
        self.indicators = indicators
        self._instances = {}
        
    def get_validator(self) -> MarketDataValidator:
        """Get or create validator instance."""
        if 'validator' not in self._instances:
            self._instances['validator'] = MarketDataValidator(self.config)
        return self._instances['validator']
    
    def get_transformer_pipeline(self) -> TransformerPipeline:
        """Get or create transformer pipeline."""
        if 'transformer_pipeline' not in self._instances:
            transformers = {
                'technical': TechnicalTransformer(self.config),
                'volume': VolumeTransformer(self.config),
                'orderbook': OrderbookTransformer(self.config),
                'orderflow': OrderflowTransformer(self.config),
                'price_structure': PriceStructureTransformer(self.config),
                'sentiment': SentimentTransformer(self.config)
            }
            self._instances['transformer_pipeline'] = TransformerPipeline(transformers)
        return self._instances['transformer_pipeline']
    
    def get_executor(self) -> IndicatorExecutor:
        """Get or create executor instance."""
        if 'executor' not in self._instances:
            self._instances['executor'] = IndicatorExecutor(
                self.indicators, 
                self.config
            )
        return self._instances['executor']
    
    def get_calculator(self) -> ScoreCalculator:
        """Get or create calculator instance."""
        if 'calculator' not in self._instances:
            weight_manager = WeightManager(self.config)
            self._instances['calculator'] = ScoreCalculator(weight_manager)
        return self._instances['calculator']
    
    def get_formatter(self) -> ResponseFormatter:
        """Get or create formatter instance."""
        if 'formatter' not in self._instances:
            self._instances['formatter'] = ResponseFormatter(self.config)
        return self._instances['formatter']
```

## 8. Legacy Adapter for Backward Compatibility

```python
# src/core/analysis/confluence_legacy_adapter.py
from typing import Dict, Any
from .confluence import ConfluenceAnalyzer as NewConfluenceAnalyzer
from .confluence.container import ConfluenceContainer

class ConfluenceAnalyzer:
    """Legacy adapter maintaining old API while using new implementation."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize with legacy interface."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize indicators (legacy compatibility)
        self._init_indicators()
        
        # Create new container and analyzer
        container = ConfluenceContainer(self.config, self.indicators)
        self._new_analyzer = NewConfluenceAnalyzer(container)
        
        # Copy legacy attributes for compatibility
        self.weights = self.config.get('confluence', {}).get('weights', {})
        self.sub_component_weights = self.config.get('confluence', {}).get('sub_components', {})
        
    def _init_indicators(self):
        """Initialize indicators (legacy method)."""
        # Legacy indicator initialization
        # This would be replaced by proper indicator injection
        self.indicators = {}
        
    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze using new implementation with legacy interface."""
        return await self._new_analyzer.analyze(market_data)
    
    # Legacy methods for compatibility
    def _validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Legacy validation method."""
        # Delegate to new validator
        return True  # Simplified for example
    
    def _calculate_confluence_score(self, scores: Dict[str, float]) -> float:
        """Legacy score calculation."""
        # Delegate to new calculator
        return 50.0  # Simplified for example
```

## Testing Strategy

### Unit Test Example
```python
# tests/test_confluence/test_validators.py
import pytest
from src.core.analysis.confluence.validators import MarketDataValidator
import pandas as pd

class TestMarketDataValidator:
    
    @pytest.fixture
    def validator(self):
        config = {'min_data_points': 30}
        return MarketDataValidator(config)
    
    @pytest.mark.asyncio
    async def test_valid_market_data(self, validator):
        """Test validation of valid market data."""
        market_data = {
            'symbol': 'BTC/USDT',
            'ohlcv': {
                '1m': pd.DataFrame({
                    'open': [100] * 50,
                    'high': [101] * 50,
                    'low': [99] * 50,
                    'close': [100.5] * 50,
                    'volume': [1000] * 50
                })
            },
            'orderbook': {
                'bids': [[100, 10]] * 20,
                'asks': [[101, 10]] * 20
            },
            'trades': [{'price': 100, 'amount': 1}] * 100
        }
        
        result = await validator.validate(market_data)
        
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.validated_data is not None
    
    @pytest.mark.asyncio
    async def test_missing_required_field(self, validator):
        """Test validation with missing field."""
        market_data = {
            'symbol': 'BTC/USDT'
            # Missing ohlcv, orderbook, trades
        }
        
        result = await validator.validate(market_data)
        
        assert not result.is_valid
        assert 'Missing required field: ohlcv' in result.errors
```

This comprehensive refactoring plan transforms the monolithic ConfluenceAnalyzer into a modular, testable, and maintainable system while preserving all functionality and ensuring smooth migration.