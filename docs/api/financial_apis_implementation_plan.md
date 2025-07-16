# Financial API Implementation Plan v1.0

**Goal**: Guide junior developers through implementing high-impact financial APIs prioritized by competitive advantage

## Executive Summary

This implementation plan provides step-by-step guidance for developing five high-impact financial APIs that leverage the existing Virtuoso trading system infrastructure. Each API builds incrementally on the established FastAPI architecture, CCXT exchange integration, and monitoring capabilities.

**Priority Order (by competitive advantage):**
1. **Alpha Scanner API** - Real-time opportunity detection
2. **Risk Analytics API** - Portfolio risk management
3. **Performance Analytics API** - Trading performance evaluation
4. **Liquidation Intelligence API** - Market stress detection
5. **Microstructure API** - Order flow analytics

---

## System Architecture Overview

### Current Infrastructure Strengths
- ✅ FastAPI framework with established routing patterns
- ✅ CCXT integration for multi-exchange connectivity
- ✅ Signal generation and storage (JSON-based)
- ✅ Real-time monitoring and alerting
- ✅ PDF report generation capabilities
- ✅ WebSocket support for real-time data

### Proposed Enhancement
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Alpha Scanner │    │  Risk Analytics │    │  Performance    │
│       API       │    │       API       │    │  Analytics API  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐    
│  Liquidation    │    │ Microstructure  │    
│ Intelligence API│    │       API       │    
└─────────────────┘    └─────────────────┘    
         │                       │
         └───────────────────────┘
                    │
            ┌─────────────────┐
            │   Core Engine   │
            │ (Existing Infra)│
            └─────────────────┘
```

---

# API 1: Alpha Scanner API

## System Overview
The Alpha Scanner API identifies predictive signals from real-time market data by analyzing confluence patterns across multiple indicators and timeframes. It serves as an automated screening system that flags potential investment opportunities based on quantitative criteria and technical analysis.

**Core Purpose**: Systematic detection of alpha-generating opportunities across cryptocurrency markets.

## Detailed Implementation Steps

### Step 1: Data Models and Schemas
Create `src/api/models/alpha.py`:

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

class AlphaStrength(str, Enum):
    WEAK = "weak"
    MODERATE = "moderate" 
    STRONG = "strong"
    EXCEPTIONAL = "exceptional"

class AlphaOpportunity(BaseModel):
    symbol: str = Field(..., description="Trading pair symbol")
    exchange: str = Field(..., description="Exchange identifier")
    score: float = Field(..., ge=0, le=100, description="Alpha score (0-100)")
    strength: AlphaStrength = Field(..., description="Signal strength category")
    timeframe: str = Field(..., description="Primary analysis timeframe")
    
    # Confluence components
    technical_score: float = Field(..., ge=0, le=100)
    momentum_score: float = Field(..., ge=0, le=100)
    volume_score: float = Field(..., ge=0, le=100)
    sentiment_score: float = Field(..., ge=0, le=100)
    
    # Risk metrics
    volatility: float = Field(..., description="Historical volatility")
    liquidity_score: float = Field(..., ge=0, le=100)
    
    # Price levels
    current_price: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    target_price: float = Field(..., gt=0)
    
    # Metadata
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    confidence: float = Field(..., ge=0, le=1, description="Confidence level")
    
    # Analysis details
    indicators: Dict[str, float] = Field(default_factory=dict)
    insights: List[str] = Field(default_factory=list)

class AlphaScanRequest(BaseModel):
    symbols: Optional[List[str]] = Field(None, description="Specific symbols to scan")
    exchanges: Optional[List[str]] = Field(None, description="Target exchanges")
    timeframes: List[str] = Field(default=["15m", "1h", "4h"], description="Analysis timeframes")
    min_score: float = Field(default=60.0, ge=0, le=100)
    max_results: int = Field(default=20, ge=1, le=100)
    
class AlphaScanResponse(BaseModel):
    opportunities: List[AlphaOpportunity]
    scan_timestamp: datetime
    total_symbols_scanned: int
    scan_duration_ms: int
    metadata: Dict[str, Union[str, int, float]]
```

### Step 2: Core Analysis Engine
Create `src/core/analysis/alpha_scanner.py`:

```python
import asyncio
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from dataclasses import dataclass

from src.core.exchanges.manager import ExchangeManager
from src.indicators.technical_analysis import TechnicalAnalyzer
from src.api.models.alpha import AlphaOpportunity, AlphaStrength

@dataclass
class MarketData:
    symbol: str
    exchange: str
    ohlcv: pd.DataFrame
    orderbook: Dict
    volume_profile: Optional[Dict] = None

class AlphaScannerEngine:
    """Core alpha scanning engine that analyzes market opportunities."""
    
    def __init__(self, exchange_manager: ExchangeManager):
        self.exchange_manager = exchange_manager
        self.technical_analyzer = TechnicalAnalyzer()
        
        # Scanning parameters
        self.lookback_periods = {
            "15m": 96,  # 24 hours
            "1h": 168,  # 7 days
            "4h": 180   # 30 days
        }
        
    async def scan_opportunities(self, 
                               symbols: Optional[List[str]] = None,
                               exchanges: Optional[List[str]] = None,
                               timeframes: List[str] = ["15m", "1h", "4h"],
                               min_score: float = 60.0,
                               max_results: int = 20) -> List[AlphaOpportunity]:
        """Main scanning method that identifies alpha opportunities."""
        
        start_time = time.time()
        opportunities = []
        
        # Get symbols to scan
        scan_symbols = symbols or await self._get_top_symbols()
        scan_exchanges = exchanges or list(self.exchange_manager.exchanges.keys())
        
        # Parallel scanning across exchanges
        tasks = []
        for exchange_id in scan_exchanges:
            for symbol in scan_symbols:
                task = self._analyze_symbol_opportunity(
                    symbol, exchange_id, timeframes, min_score
                )
                tasks.append(task)
        
        # Execute analysis in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, AlphaOpportunity):
                opportunities.append(result)
        
        # Sort by score and limit results
        opportunities.sort(key=lambda x: x.score, reverse=True)
        return opportunities[:max_results]
    
    async def _analyze_symbol_opportunity(self, 
                                        symbol: str, 
                                        exchange_id: str,
                                        timeframes: List[str],
                                        min_score: float) -> Optional[AlphaOpportunity]:
        """Analyze a single symbol for alpha opportunities."""
        
        try:
            # Gather market data
            market_data = await self._fetch_market_data(symbol, exchange_id, timeframes)
            
            if not market_data:
                return None
            
            # Calculate confluence scores
            scores = await self._calculate_confluence_scores(market_data, timeframes)
            
            # Calculate overall alpha score
            alpha_score = self._calculate_alpha_score(scores)
            
            if alpha_score < min_score:
                return None
            
            # Determine entry/exit levels
            levels = self._calculate_price_levels(market_data)
            
            # Create opportunity object
            opportunity = AlphaOpportunity(
                symbol=symbol,
                exchange=exchange_id,
                score=alpha_score,
                strength=self._categorize_strength(alpha_score),
                timeframe=self._determine_primary_timeframe(scores),
                technical_score=scores.get('technical', 0),
                momentum_score=scores.get('momentum', 0),
                volume_score=scores.get('volume', 0),
                sentiment_score=scores.get('sentiment', 0),
                volatility=self._calculate_volatility(market_data),
                liquidity_score=scores.get('liquidity', 0),
                current_price=levels['current'],
                entry_price=levels['entry'],
                stop_loss=levels['stop'],
                target_price=levels['target'],
                confidence=self._calculate_confidence(scores),
                indicators=self._extract_key_indicators(market_data),
                insights=self._generate_insights(scores, levels)
            )
            
            return opportunity
            
        except Exception as e:
            # Log error but don't break the scanning process
            import logging
            logging.error(f"Error analyzing {symbol} on {exchange_id}: {e}")
            return None
    
    async def _fetch_market_data(self, symbol: str, exchange_id: str, timeframes: List[str]) -> Optional[MarketData]:
        """Fetch comprehensive market data for analysis."""
        
        try:
            exchange = self.exchange_manager.exchanges[exchange_id]
            
            # Get OHLCV data for primary timeframe
            primary_tf = timeframes[0] if timeframes else "1h"
            limit = self.lookback_periods.get(primary_tf, 100)
            
            ohlcv = await exchange.fetch_ohlcv(symbol, primary_tf, limit=limit)
            
            if not ohlcv or len(ohlcv) < 20:  # Minimum data requirement
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Get order book data
            orderbook = await exchange.fetch_order_book(symbol, limit=20)
            
            return MarketData(
                symbol=symbol,
                exchange=exchange_id,
                ohlcv=df,
                orderbook=orderbook
            )
            
        except Exception as e:
            import logging
            logging.error(f"Error fetching market data for {symbol}: {e}")
            return None
```

### Step 3: API Routes Implementation
Create `src/api/routes/alpha.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Optional
import asyncio
import time

from ..models.alpha import AlphaScanRequest, AlphaScanResponse, AlphaOpportunity
from src.core.analysis.alpha_scanner import AlphaScannerEngine
from src.core.exchanges.manager import ExchangeManager
from fastapi import Request

router = APIRouter()

async def get_exchange_manager(request: Request) -> ExchangeManager:
    """Dependency to get exchange manager from app state"""
    if not hasattr(request.app.state, "exchange_manager"):
        raise HTTPException(status_code=503, detail="Exchange manager not initialized")
    return request.app.state.exchange_manager

async def get_alpha_scanner(exchange_manager: ExchangeManager = Depends(get_exchange_manager)) -> AlphaScannerEngine:
    """Dependency to get alpha scanner engine"""
    return AlphaScannerEngine(exchange_manager)

@router.post("/scan", response_model=AlphaScanResponse)
async def scan_alpha_opportunities(
    scan_request: AlphaScanRequest,
    alpha_scanner: AlphaScannerEngine = Depends(get_alpha_scanner)
) -> AlphaScanResponse:
    """
    Scan for alpha opportunities across specified markets.
    
    This endpoint performs real-time analysis of cryptocurrency markets to identify
    potential alpha-generating opportunities based on confluence of technical indicators,
    momentum, volume, and sentiment analysis.
    """
    
    start_time = time.time()
    
    try:
        opportunities = await alpha_scanner.scan_opportunities(
            symbols=scan_request.symbols,
            exchanges=scan_request.exchanges,
            timeframes=scan_request.timeframes,
            min_score=scan_request.min_score,
            max_results=scan_request.max_results
        )
        
        scan_duration = int((time.time() - start_time) * 1000)
        
        return AlphaScanResponse(
            opportunities=opportunities,
            scan_timestamp=datetime.utcnow(),
            total_symbols_scanned=len(scan_request.symbols) if scan_request.symbols else 100,
            scan_duration_ms=scan_duration,
            metadata={
                "timeframes_analyzed": scan_request.timeframes,
                "min_score_threshold": scan_request.min_score,
                "opportunities_found": len(opportunities)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scanning failed: {str(e)}")

@router.get("/opportunities/top", response_model=List[AlphaOpportunity])
async def get_top_opportunities(
    limit: int = Query(default=10, ge=1, le=50),
    min_score: float = Query(default=70.0, ge=0, le=100),
    timeframe: Optional[str] = Query(default=None),
    alpha_scanner: AlphaScannerEngine = Depends(get_alpha_scanner)
) -> List[AlphaOpportunity]:
    """Get top alpha opportunities with optional filtering."""
    
    try:
        timeframes = [timeframe] if timeframe else ["15m", "1h", "4h"]
        
        opportunities = await alpha_scanner.scan_opportunities(
            timeframes=timeframes,
            min_score=min_score,
            max_results=limit
        )
        
        return opportunities
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch opportunities: {str(e)}")

@router.get("/opportunities/{symbol}", response_model=Optional[AlphaOpportunity])
async def get_symbol_opportunity(
    symbol: str,
    exchange: Optional[str] = Query(default=None),
    timeframe: str = Query(default="1h"),
    alpha_scanner: AlphaScannerEngine = Depends(get_alpha_scanner)
) -> Optional[AlphaOpportunity]:
    """Get alpha opportunity analysis for a specific symbol."""
    
    try:
        exchanges = [exchange] if exchange else None
        
        opportunities = await alpha_scanner.scan_opportunities(
            symbols=[symbol.upper()],
            exchanges=exchanges,
            timeframes=[timeframe],
            min_score=0.0,  # Return result regardless of score
            max_results=1
        )
        
        return opportunities[0] if opportunities else None
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
```

## File Structure
```
src/
├── api/
│   ├── models/
│   │   └── alpha.py                 # Alpha-specific data models
│   └── routes/
│       └── alpha.py                 # Alpha API endpoints
├── core/
│   └── analysis/
│       ├── alpha_scanner.py         # Main scanning engine
│       ├── confluence_analyzer.py   # Multi-indicator confluence
│       └── opportunity_ranker.py    # Scoring and ranking logic
└── tests/
    └── alpha/
        ├── test_alpha_api.py        # API endpoint tests
        ├── test_scanner_engine.py   # Core engine tests
        └── mocks/
            └── mock_market_data.json # Test data fixtures
```

## Dependencies
Add to `requirements.txt`:
```
# Alpha Scanner specific
scikit-learn>=1.0.0      # For ML-based scoring
TA-Lib>=0.4.25          # Advanced technical indicators  
yfinance>=0.1.70        # Market data validation
redis>=4.0.0            # Caching scan results
celery>=5.2.0           # Background scanning tasks
```

## Testing Strategy

### Unit Tests
Create `tests/alpha/test_scanner_engine.py`:

```python
import pytest
import pandas as pd
from unittest.mock import Mock, AsyncMock
from src.core.analysis.alpha_scanner import AlphaScannerEngine
from src.api.models.alpha import AlphaOpportunity

class TestAlphaScannerEngine:
    
    @pytest.fixture
    async def mock_exchange_manager(self):
        manager = Mock()
        exchange = Mock()
        exchange.fetch_ohlcv = AsyncMock(return_value=[
            [1640995200000, 47000, 47500, 46800, 47200, 1000],  # Mock OHLCV data
            [1640998800000, 47200, 47600, 47000, 47400, 1200],
        ])
        exchange.fetch_order_book = AsyncMock(return_value={
            'bids': [[47300, 10], [47200, 15]],
            'asks': [[47400, 8], [47500, 12]]
        })
        manager.exchanges = {'binance': exchange}
        return manager
    
    @pytest.fixture
    def alpha_scanner(self, mock_exchange_manager):
        return AlphaScannerEngine(mock_exchange_manager)
    
    async def test_scan_opportunities_basic(self, alpha_scanner):
        """Test basic opportunity scanning functionality."""
        opportunities = await alpha_scanner.scan_opportunities(
            symbols=['BTCUSDT'],
            exchanges=['binance'],
            min_score=0.0,
            max_results=5
        )
        
        assert isinstance(opportunities, list)
        # Should return results even with low threshold
        
    async def test_alpha_score_calculation(self, alpha_scanner):
        """Test alpha score calculation logic."""
        # Mock market data
        mock_data = Mock()
        mock_data.ohlcv = pd.DataFrame({
            'open': [47000, 47200],
            'high': [47500, 47600], 
            'low': [46800, 47000],
            'close': [47200, 47400],
            'volume': [1000, 1200]
        })
        
        scores = await alpha_scanner._calculate_confluence_scores(mock_data, ['1h'])
        alpha_score = alpha_scanner._calculate_alpha_score(scores)
        
        assert isinstance(alpha_score, float)
        assert 0 <= alpha_score <= 100
```

### Integration Tests
Create `tests/alpha/test_alpha_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_scan_alpha_opportunities(client):
    """Test the main scanning endpoint."""
    response = client.post("/api/alpha/scan", json={
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "timeframes": ["1h"],
        "min_score": 50.0,
        "max_results": 10
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert "opportunities" in data
    assert "scan_timestamp" in data
    assert "scan_duration_ms" in data
    assert isinstance(data["opportunities"], list)

def test_get_top_opportunities(client):
    """Test the top opportunities endpoint."""
    response = client.get("/api/alpha/opportunities/top?limit=5&min_score=60")
    
    assert response.status_code == 200
    opportunities = response.json()
    
    assert isinstance(opportunities, list)
    assert len(opportunities) <= 5
```

## Documentation

### API Documentation
The Alpha Scanner API will automatically generate OpenAPI documentation. Key endpoints:

- `POST /api/alpha/scan` - Comprehensive opportunity scanning
- `GET /api/alpha/opportunities/top` - Get highest-scoring opportunities
- `GET /api/alpha/opportunities/{symbol}` - Symbol-specific analysis

### Internal Documentation
Create `docs/alpha/scanner_architecture.md` documenting:
- Confluence scoring methodology
- Performance optimization strategies  
- Caching and rate limiting implementation
- Error handling and recovery procedures

## Deployment Considerations

### Environment Configuration
Add to `config/env/.env`:
```
# Alpha Scanner Configuration
ALPHA_SCAN_INTERVAL=300           # Scan every 5 minutes
ALPHA_CACHE_TTL=60               # Cache results for 1 minute
ALPHA_MAX_CONCURRENT_SCANS=10    # Parallel scan limit
ALPHA_MIN_VOLUME_THRESHOLD=1000000  # Minimum 24h volume
```

### Docker Configuration
Update `Dockerfile` to include alpha scanning dependencies:
```dockerfile
# Install TA-Lib for advanced indicators
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && pip install TA-Lib \
    && apt-get clean
```

### Monitoring and Alerting
- Set up CloudWatch/Grafana dashboards for scan performance
- Configure alerts for API response times > 5 seconds
- Monitor opportunity detection rates and false positives

---

# API 2: Risk Analytics API

## System Overview
The Risk Analytics API provides comprehensive portfolio risk assessment using Value-at-Risk (VaR), Conditional Value-at-Risk (CVaR), and stress testing scenarios. It evaluates portfolio exposure across multiple dimensions including market risk, concentration risk, and tail risk events.

**Core Purpose**: Real-time risk monitoring and portfolio optimization to prevent catastrophic losses.

## Detailed Implementation Steps

### Step 1: Risk Models and Schemas
Create `src/api/models/risk.py`:

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
import numpy as np

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskMetric(BaseModel):
    value: float
    confidence_level: float = Field(default=0.95)
    time_horizon_days: int = Field(default=1)
    currency: str = Field(default="USD")

class VaRCalculation(RiskMetric):
    method: str = Field(..., description="VaR calculation method (historical, parametric, monte_carlo)")
    percentile: float = Field(..., ge=0, le=1)

class CVaRCalculation(RiskMetric):
    var_threshold: float = Field(..., description="VaR threshold for CVaR calculation")

class PortfolioRiskAssessment(BaseModel):
    portfolio_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_value: float = Field(..., gt=0)
    
    # Core risk metrics
    var_1d: VaRCalculation
    var_7d: VaRCalculation
    cvar_1d: CVaRCalculation
    cvar_7d: CVaRCalculation
    
    # Risk ratios
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float = Field(..., ge=0, le=1)
    
    # Concentration metrics
    concentration_risk: float = Field(..., ge=0, le=1)
    largest_position_weight: float = Field(..., ge=0, le=1)
    herfindahl_index: float = Field(..., ge=0, le=1)
    
    # Market exposure
    beta: float
    correlation_to_market: float = Field(..., ge=-1, le=1)
    
    # Risk decomposition
    position_contributions: Dict[str, float] = Field(default_factory=dict)
    risk_level: RiskLevel
    
    # Stress test results
    stress_test_results: Dict[str, float] = Field(default_factory=dict)
    
    # Recommendations
    risk_warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

class StressTestScenario(BaseModel):
    name: str
    description: str
    market_shocks: Dict[str, float]  # symbol -> percentage change
    correlation_adjustments: Optional[Dict[str, float]] = None

class RiskLimitBreaches(BaseModel):
    portfolio_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    breaches: List[Dict[str, Union[str, float]]]
    severity: RiskLevel
    immediate_actions_required: List[str]
```

### Step 2: Risk Calculation Engine
Create `src/core/analysis/risk_calculator.py`:

```python
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from scipy import stats
from scipy.optimize import minimize
import asyncio

from src.api.models.risk import (
    PortfolioRiskAssessment, VaRCalculation, CVaRCalculation, 
    RiskLevel, StressTestScenario
)

class RiskCalculationEngine:
    """Advanced risk calculation engine for portfolio analysis."""
    
    def __init__(self):
        self.confidence_levels = [0.95, 0.99, 0.999]
        self.time_horizons = [1, 7, 30]  # days
        
        # Market stress scenarios
        self.stress_scenarios = {
            "market_crash": StressTestScenario(
                name="Market Crash",
                description="Severe market downturn similar to March 2020",
                market_shocks={"BTC": -0.50, "ETH": -0.60, "ALT": -0.70}
            ),
            "flash_crash": StressTestScenario(
                name="Flash Crash",
                description="Rapid liquidity-driven selloff",
                market_shocks={"BTC": -0.30, "ETH": -0.35, "ALT": -0.45}
            ),
            "correlation_breakdown": StressTestScenario(
                name="Correlation Breakdown", 
                description="Normal correlations fail during crisis",
                market_shocks={"BTC": -0.25, "ETH": -0.40, "ALT": -0.55},
                correlation_adjustments={"all_pairs": 0.85}
            )
        }
    
    async def calculate_portfolio_risk(self, 
                                     positions: Dict[str, float],
                                     price_history: Dict[str, pd.DataFrame],
                                     portfolio_value: float) -> PortfolioRiskAssessment:
        """Calculate comprehensive risk assessment for a portfolio."""
        
        # Calculate returns matrix
        returns_matrix = self._calculate_returns_matrix(price_history)
        
        if returns_matrix.empty:
            raise ValueError("Insufficient price history for risk calculation")
        
        # Portfolio weights
        weights = self._calculate_portfolio_weights(positions, portfolio_value)
        
        # Calculate portfolio returns
        portfolio_returns = self._calculate_portfolio_returns(returns_matrix, weights)
        
        # VaR calculations
        var_1d_hist = self._calculate_historical_var(portfolio_returns, 0.95, 1)
        var_7d_hist = self._calculate_historical_var(portfolio_returns, 0.95, 7)
        
        var_1d_param = self._calculate_parametric_var(portfolio_returns, 0.95, 1)
        var_7d_param = self._calculate_parametric_var(portfolio_returns, 0.95, 7)
        
        # CVaR calculations
        cvar_1d = self._calculate_cvar(portfolio_returns, var_1d_hist.value, 1)
        cvar_7d = self._calculate_cvar(portfolio_returns, var_7d_hist.value, 7)
        
        # Risk ratios
        sharpe = self._calculate_sharpe_ratio(portfolio_returns)
        sortino = self._calculate_sortino_ratio(portfolio_returns)
        max_dd = self._calculate_max_drawdown(portfolio_returns)
        
        # Concentration metrics
        concentration = self._calculate_concentration_risk(weights)
        largest_weight = max(weights.values()) if weights else 0
        herfindahl = self._calculate_herfindahl_index(weights)
        
        # Market exposure (using BTC as proxy)
        beta, correlation = self._calculate_market_exposure(portfolio_returns, returns_matrix)
        
        # Position contributions to risk
        risk_contributions = self._calculate_risk_contributions(returns_matrix, weights)
        
        # Stress testing
        stress_results = await self._run_stress_tests(positions, price_history)
        
        # Risk level assessment
        risk_level = self._assess_risk_level(var_1d_hist.value, portfolio_value, max_dd)
        
        # Generate warnings and recommendations
        warnings, recommendations = self._generate_risk_insights(
            var_1d_hist.value, cvar_1d.value, max_dd, concentration, stress_results
        )
        
        return PortfolioRiskAssessment(
            portfolio_id=f"portfolio_{int(datetime.utcnow().timestamp())}",
            total_value=portfolio_value,
            var_1d=var_1d_hist,
            var_7d=var_7d_hist,
            cvar_1d=cvar_1d,
            cvar_7d=cvar_7d,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            concentration_risk=concentration,
            largest_position_weight=largest_weight,
            herfindahl_index=herfindahl,
            beta=beta,
            correlation_to_market=correlation,
            position_contributions=risk_contributions,
            risk_level=risk_level,
            stress_test_results=stress_results,
            risk_warnings=warnings,
            recommendations=recommendations
        )
    
    def _calculate_historical_var(self, returns: pd.Series, confidence: float, horizon: int) -> VaRCalculation:
        """Calculate Value-at-Risk using historical simulation method."""
        
        # Scale returns to horizon
        scaled_returns = returns * np.sqrt(horizon)
        
        # Calculate percentile
        percentile = 1 - confidence
        var_value = np.percentile(scaled_returns.dropna(), percentile * 100)
        
        return VaRCalculation(
            value=abs(var_value),  # Make positive for easier interpretation
            method="historical",
            percentile=percentile,
            confidence_level=confidence,
            time_horizon_days=horizon
        )
    
    def _calculate_parametric_var(self, returns: pd.Series, confidence: float, horizon: int) -> VaRCalculation:
        """Calculate Value-at-Risk using parametric (normal distribution) method."""
        
        # Calculate parameters
        mean_return = returns.mean() * horizon
        std_return = returns.std() * np.sqrt(horizon)
        
        # Calculate VaR using normal distribution
        z_score = stats.norm.ppf(1 - confidence)
        var_value = abs(mean_return + z_score * std_return)
        
        return VaRCalculation(
            value=var_value,
            method="parametric",
            percentile=1 - confidence,
            confidence_level=confidence,
            time_horizon_days=horizon
        )
    
    def _calculate_cvar(self, returns: pd.Series, var_threshold: float, horizon: int) -> CVaRCalculation:
        """Calculate Conditional Value-at-Risk (Expected Shortfall)."""
        
        # Scale returns to horizon
        scaled_returns = returns * np.sqrt(horizon)
        
        # Find returns worse than VaR threshold
        tail_losses = scaled_returns[scaled_returns <= -var_threshold]
        
        # Calculate mean of tail losses
        cvar_value = abs(tail_losses.mean()) if len(tail_losses) > 0 else var_threshold
        
        return CVaRCalculation(
            value=cvar_value,
            var_threshold=var_threshold,
            time_horizon_days=horizon
        )
```

### Step 3: API Routes Implementation
Create `src/api/routes/risk.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, List, Optional
import asyncio

from ..models.risk import PortfolioRiskAssessment, StressTestScenario, RiskLimitBreaches
from src.core.analysis.risk_calculator import RiskCalculationEngine
from src.core.exchanges.manager import ExchangeManager
from fastapi import Request

router = APIRouter()

async def get_exchange_manager(request: Request) -> ExchangeManager:
    """Dependency to get exchange manager from app state"""
    if not hasattr(request.app.state, "exchange_manager"):
        raise HTTPException(status_code=503, detail="Exchange manager not initialized")
    return request.app.state.exchange_manager

async def get_risk_calculator() -> RiskCalculationEngine:
    """Dependency to get risk calculation engine"""
    return RiskCalculationEngine()

@router.post("/portfolio/assess", response_model=PortfolioRiskAssessment)
async def assess_portfolio_risk(
    positions: Dict[str, float] = Body(..., description="Portfolio positions (symbol -> quantity)"),
    exchange_id: str = Body(..., description="Exchange for price data"),
    lookback_days: int = Body(default=252, description="Historical data lookback period"),
    exchange_manager: ExchangeManager = Depends(get_exchange_manager),
    risk_calculator: RiskCalculationEngine = Depends(get_risk_calculator)
) -> PortfolioRiskAssessment:
    """
    Perform comprehensive risk assessment for a portfolio.
    
    Calculates VaR, CVaR, stress test scenarios, concentration risk,
    and provides actionable risk management recommendations.
    """
    
    try:
        # Validate exchange
        if exchange_id not in exchange_manager.exchanges:
            raise HTTPException(status_code=404, detail=f"Exchange {exchange_id} not found")
        
        exchange = exchange_manager.exchanges[exchange_id]
        
        # Fetch historical price data for all positions
        price_history = {}
        total_value = 0.0
        
        for symbol, quantity in positions.items():
            try:
                # Get historical OHLCV data
                ohlcv = await exchange.fetch_ohlcv(
                    symbol, 
                    '1d', 
                    limit=lookback_days
                )
                
                if not ohlcv:
                    continue
                
                # Convert to DataFrame
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                price_history[symbol] = df
                
                # Calculate position value
                current_price = df['close'].iloc[-1]
                total_value += abs(quantity) * current_price
                
            except Exception as e:
                # Skip symbols with data issues
                continue
        
        if not price_history:
            raise HTTPException(status_code=400, detail="No valid price history found for portfolio")
        
        # Perform risk assessment
        risk_assessment = await risk_calculator.calculate_portfolio_risk(
            positions=positions,
            price_history=price_history,
            portfolio_value=total_value
        )
        
        return risk_assessment
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk assessment failed: {str(e)}")

@router.post("/stress-test", response_model=Dict[str, float])
async def run_stress_test(
    positions: Dict[str, float] = Body(...),
    scenario: StressTestScenario = Body(...),
    exchange_id: str = Body(...),
    exchange_manager: ExchangeManager = Depends(get_exchange_manager),
    risk_calculator: RiskCalculationEngine = Depends(get_risk_calculator)
) -> Dict[str, float]:
    """
    Run a custom stress test scenario against a portfolio.
    """
    
    try:
        # Fetch current prices
        exchange = exchange_manager.exchanges[exchange_id]
        current_prices = {}
        
        for symbol in positions.keys():
            ticker = await exchange.fetch_ticker(symbol)
            current_prices[symbol] = ticker['last']
        
        # Apply stress scenario
        stressed_portfolio_value = 0.0
        original_portfolio_value = 0.0
        
        for symbol, quantity in positions.items():
            current_price = current_prices.get(symbol, 0)
            original_value = quantity * current_price
            original_portfolio_value += original_value
            
            # Apply shock
            shock = scenario.market_shocks.get(symbol, scenario.market_shocks.get('ALL', 0))
            stressed_price = current_price * (1 + shock)
            stressed_value = quantity * stressed_price
            stressed_portfolio_value += stressed_value
        
        # Calculate results
        portfolio_loss = original_portfolio_value - stressed_portfolio_value
        portfolio_loss_pct = portfolio_loss / original_portfolio_value if original_portfolio_value > 0 else 0
        
        return {
            "scenario_name": scenario.name,
            "original_value": original_portfolio_value,
            "stressed_value": stressed_portfolio_value,
            "absolute_loss": portfolio_loss,
            "percentage_loss": portfolio_loss_pct * 100,
            "scenario_description": scenario.description
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stress test failed: {str(e)}")

@router.get("/limits/breaches", response_model=List[RiskLimitBreaches])
async def check_risk_limit_breaches(
    portfolio_id: str = Query(...),
    risk_calculator: RiskCalculationEngine = Depends(get_risk_calculator)
) -> List[RiskLimitBreaches]:
    """
    Check for risk limit breaches in a portfolio.
    
    This would integrate with your existing position tracking system
    to monitor ongoing risk exposures against predefined limits.
    """
    
    # This would integrate with your actual portfolio tracking system
    # For now, return a mock response
    return []

@router.get("/correlation-matrix")
async def get_correlation_matrix(
    symbols: List[str] = Query(...),
    timeframe: str = Query(default="1d"),
    lookback_days: int = Query(default=90),
    exchange_id: str = Query(...),
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
) -> Dict[str, Dict[str, float]]:
    """
    Calculate correlation matrix for specified symbols.
    """
    
    try:
        exchange = exchange_manager.exchanges[exchange_id]
        
        # Fetch price data for all symbols
        price_data = {}
        
        for symbol in symbols:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=lookback_days)
            if ohlcv:
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                price_data[symbol] = df['close'].pct_change().dropna()
        
        # Calculate correlation matrix
        if len(price_data) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 symbols for correlation")
        
        # Align data by length
        min_length = min(len(data) for data in price_data.values())
        aligned_data = {symbol: data.tail(min_length) for symbol, data in price_data.items()}
        
        # Create DataFrame and calculate correlations
        df = pd.DataFrame(aligned_data)
        correlation_matrix = df.corr()
        
        # Convert to nested dict format
        result = {}
        for symbol1 in symbols:
            result[symbol1] = {}
            for symbol2 in symbols:
                if symbol1 in correlation_matrix.index and symbol2 in correlation_matrix.columns:
                    result[symbol1][symbol2] = float(correlation_matrix.loc[symbol1, symbol2])
                else:
                    result[symbol1][symbol2] = 0.0
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Correlation calculation failed: {str(e)}")
```

## Dependencies
Add to requirements.txt:
```
# Risk Analytics specific
scipy>=1.7.0            # Statistical calculations
arch>=5.3.0             # GARCH models for volatility
statsmodels>=0.13.0     # Time series modeling
pyportfolioopt>=1.5.0   # Portfolio optimization
riskfolio-lib>=4.0.0    # Advanced risk calculations
cvxpy>=1.2.0            # Convex optimization
```

## Testing Strategy
Create comprehensive tests covering:
- VaR calculation accuracy across different methods
- Stress test scenario validation
- Portfolio risk decomposition
- Edge cases (empty portfolios, insufficient data)
- Performance benchmarks for large portfolios

---

# API 3: Performance Analytics API

## System Overview
The Performance Analytics API evaluates trading performance against benchmarks using industry-standard metrics including Sharpe ratio, Sortino ratio, Information ratio, maximum drawdown, and alpha generation. It provides detailed attribution analysis and peer comparison capabilities.

**Core Purpose**: Quantitative evaluation of trading strategy effectiveness and continuous performance improvement.

## Key Components
- **Return Analysis**: Time-weighted returns, risk-adjusted returns
- **Benchmark Comparison**: Relative performance vs market indices
- **Attribution Analysis**: Performance decomposition by strategy/sector
- **Risk Metrics**: Volatility, downside deviation, tail risk
- **Trading Analytics**: Win rate, profit factor, average trade metrics

[Continue with detailed implementation...]

---

# API 4: Liquidation Intelligence API

## System Overview
The Liquidation Intelligence API detects signals of forced liquidations in real-time by monitoring unusual trading patterns, leverage ratios, and market stress indicators. It provides early warning systems for cascade liquidation events that can trigger market-wide volatility.

**Core Purpose**: Proactive detection and mitigation of liquidation-driven market dislocations.

[Continue with detailed implementation...]

---

# API 5: Microstructure API

## System Overview
The Microstructure API analyzes intraday market behavior including order flow, bid-ask spreads, market depth, and trade classification to identify short-term alpha opportunities and optimal execution strategies.

**Core Purpose**: Ultra-high frequency analysis for execution optimization and short-term signal generation.

[Continue with detailed implementation...]

---

## Cross-API Integration Points

### Shared Infrastructure
All APIs leverage:
- Common caching layer (Redis)
- Unified logging and monitoring
- Standardized error handling
- Consistent authentication/authorization
- Shared market data connections

### Data Flow Architecture
```
Market Data Feeds → Data Normalization → API Processing Engines → Results Caching → Client APIs
      ↓                     ↓                      ↓                    ↓              ↓
WebSocket Streams → Exchange Managers → Analysis Modules → Redis Cache → FastAPI Routes
```

### Performance Optimization
- Implement connection pooling for exchange APIs
- Use async/await patterns throughout
- Leverage pandas/numpy for vectorized calculations
- Cache frequently requested computations
- Implement circuit breakers for external dependencies

---

## Production Deployment Checklist

### Security
- [ ] API key rotation strategy implemented
- [ ] Rate limiting configured
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (if using databases)
- [ ] HTTPS/TLS encryption enabled

### Monitoring
- [ ] Application performance monitoring (APM)
- [ ] Error tracking and alerting
- [ ] API response time dashboards
- [ ] Resource utilization monitoring
- [ ] Business metrics tracking

### Scalability
- [ ] Horizontal scaling configuration
- [ ] Load balancer setup
- [ ] Database connection pooling
- [ ] Caching strategy implementation
- [ ] Background task processing

### Documentation
- [ ] API documentation generated
- [ ] Integration examples provided
- [ ] Error code reference
- [ ] Performance benchmarks documented
- [ ] Troubleshooting guides created

This implementation plan provides a solid foundation for building production-ready financial APIs that leverage your existing infrastructure while adding significant competitive advantages through advanced analytics capabilities. 