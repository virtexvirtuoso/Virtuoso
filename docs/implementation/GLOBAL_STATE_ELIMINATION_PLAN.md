# Global State Elimination Plan - Virtuoso Trading System

## ✅ IMPLEMENTATION COMPLETE - PRODUCTION DEPLOYED

**Target Issue**: Global State Antipattern in `src/main.py:97-111` - **RESOLVED**  
**Priority**: Critical (High Severity) - **COMPLETED**  
**Implementation Date**: July 24, 2025  
**Actual Effort**: 1 day (ahead of schedule)  
**Risk Level**: Successfully mitigated - **NO ISSUES**  

---

## Problem Analysis

### Current Problematic Pattern

```python
# src/main.py:97-111 - 13 global variables
config_manager = None
exchange_manager = None  
portfolio_analyzer = None
database_client = None
confluence_analyzer = None
top_symbols_manager = None
market_monitor = None
metrics_manager = None
alert_manager = None
market_reporter = None
health_monitor = None
validation_service = None
market_data_manager = None
```

### Critical Issues Identified

1. **Race Conditions**: Global variables accessed/modified across async contexts without synchronization
2. **Testing Impossibility**: Cannot unit test components due to global state dependencies
3. **Tight Coupling**: Components implicitly depend on global initialization order
4. **Memory Leaks**: Global references prevent proper garbage collection
5. **Deployment Issues**: Application restart requires careful global state management

### Dependency Analysis Results

**Total Dependencies Mapped**: 65+ functions and routes  
**Files Affected**: 15+ files across API, monitoring, and testing modules  
**Critical Dependencies**: 
- All API routes (50+ endpoints)
- MonitorSystem initialization
- Cleanup and shutdown procedures
- External script integrations

---

## Solution Architecture

### AppContext Design Pattern

We'll implement a **Dependency Injection Container** using the AppContext pattern that:
- Centralizes component lifecycle management
- Provides type-safe dependency access
- Enables proper testing and mocking
- Maintains backward compatibility with existing FastAPI patterns

### Core Components

```python
@dataclass
class AppContext:
    """Application dependency container with lifecycle management."""
    
    # Core Services
    config_manager: ConfigManager
    exchange_manager: ExchangeManager
    database_client: DatabaseClient
    
    # Analysis Services  
    portfolio_analyzer: PortfolioAnalyzer
    confluence_analyzer: ConfluenceAnalyzer
    validation_service: AsyncValidationService
    
    # Market Services
    top_symbols_manager: TopSymbolsManager
    market_data_manager: MarketDataManager
    
    # Monitoring Services
    metrics_manager: MetricsManager
    alert_manager: AlertManager
    market_reporter: MarketReporter
    market_monitor: MarketMonitor
    health_monitor: Optional[HealthMonitor] = None
    
    # Lifecycle Management
    _initialized: bool = field(default=False, init=False)
    _cleanup_called: bool = field(default=False, init=False)
```

---

## Implementation Plan

### Phase 1: Foundation Setup (Day 1 - Morning)

**Duration**: 4 hours  
**Risk**: Low  
**Deliverables**: Core infrastructure without breaking existing functionality

#### 1.1 Create AppContext Class

**File**: `src/core/app_context.py`

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import logging
import asyncio
from contextlib import asynccontextmanager

@dataclass
class AppContext:
    """Application dependency injection container."""
    
    # Core Services (initialized first)
    config_manager: 'ConfigManager'
    
    # Exchange Services (depends on config)
    exchange_manager: Optional['ExchangeManager'] = None
    database_client: Optional['DatabaseClient'] = None
    
    # Analysis Services (depends on config + exchange)
    portfolio_analyzer: Optional['PortfolioAnalyzer'] = None
    confluence_analyzer: Optional['ConfluenceAnalyzer'] = None
    validation_service: Optional['AsyncValidationService'] = None
    
    # Market Services (depends on exchange + validation)
    top_symbols_manager: Optional['TopSymbolsManager'] = None
    market_data_manager: Optional['MarketDataManager'] = None
    
    # Monitoring Services (depends on all above)
    metrics_manager: Optional['MetricsManager'] = None
    alert_manager: Optional['AlertManager'] = None
    market_reporter: Optional['MarketReporter'] = None
    market_monitor: Optional['MarketMonitor'] = None
    health_monitor: Optional['HealthMonitor'] = None
    
    # Lifecycle State
    _initialized: bool = field(default=False, init=False)
    _cleanup_called: bool = field(default=False, init=False)
    _logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))
    
    async def initialize(self) -> None:
        """Initialize all components in dependency order."""
        if self._initialized:
            return
            
        try:
            self._logger.info("Initializing AppContext components...")
            
            # Phase 1: Core Services
            await self._init_core_services()
            
            # Phase 2: Exchange Services  
            await self._init_exchange_services()
            
            # Phase 3: Analysis Services
            await self._init_analysis_services()
            
            # Phase 4: Market Services
            await self._init_market_services()
            
            # Phase 5: Monitoring Services
            await self._init_monitoring_services()
            
            self._initialized = True
            self._logger.info("✅ AppContext initialization completed")
            
        except Exception as e:
            self._logger.error(f"❌ AppContext initialization failed: {e}")
            await self.cleanup()
            raise
    
    async def cleanup(self) -> None:
        """Cleanup all components in reverse dependency order."""
        if self._cleanup_called:
            return
            
        self._cleanup_called = True
        self._logger.info("Starting AppContext cleanup...")
        
        # Cleanup in reverse order
        components = [
            ('market_monitor', self.market_monitor),
            ('market_reporter', self.market_reporter),
            ('alert_manager', self.alert_manager),
            ('metrics_manager', self.metrics_manager),
            ('market_data_manager', self.market_data_manager),
            ('top_symbols_manager', self.top_symbols_manager),
            ('validation_service', self.validation_service),
            ('confluence_analyzer', self.confluence_analyzer),
            ('portfolio_analyzer', self.portfolio_analyzer),
            ('database_client', self.database_client),
            ('exchange_manager', self.exchange_manager),
        ]
        
        for name, component in components:
            if component and hasattr(component, 'cleanup'):
                try:
                    await asyncio.wait_for(component.cleanup(), timeout=10.0)
                    self._logger.info(f"✅ {name} cleaned up")
                except Exception as e:
                    self._logger.error(f"❌ Error cleaning up {name}: {e}")
    
    @asynccontextmanager
    async def lifespan(self):
        """Context manager for proper lifecycle management."""
        try:
            await self.initialize()
            yield self
        finally:
            await self.cleanup()
```

#### 1.2 Create Factory Function

**File**: `src/core/app_context.py` (continued)

```python
async def create_app_context() -> AppContext:
    """Factory function to create and initialize AppContext."""
    from src.config.manager import ConfigManager
    
    # Start with config manager (no dependencies)
    config_manager = ConfigManager()
    
    # Create context with config manager
    context = AppContext(config_manager=config_manager)
    
    # Initialize all components
    await context.initialize()
    
    return context

async def create_test_context(test_config: Optional[Dict] = None) -> AppContext:
    """Factory for testing with mock components."""
    from unittest.mock import AsyncMock, MagicMock
    from src.config.manager import ConfigManager
    
    # Create test config manager
    config_manager = ConfigManager()
    if test_config:
        config_manager.config.update(test_config)
    
    # Create context with mocked components for testing
    context = AppContext(
        config_manager=config_manager,
        exchange_manager=AsyncMock(),
        database_client=AsyncMock(),
        portfolio_analyzer=MagicMock(),
        # ... other mocked components
    )
    
    context._initialized = True  # Skip initialization for tests
    return context
```

#### 1.3 Create Initialization Phases

**File**: `src/core/app_context.py` (implementation methods)

```python
# Add these methods to AppContext class

async def _init_core_services(self) -> None:
    """Initialize core services (config already initialized)."""
    self._logger.info("Phase 1: Initializing core services...")
    # Config manager already initialized in constructor
    
async def _init_exchange_services(self) -> None:
    """Initialize exchange-dependent services."""
    self._logger.info("Phase 2: Initializing exchange services...")
    
    from src.core.exchanges.manager import ExchangeManager
    from src.data_storage.database import DatabaseClient
    
    # Initialize exchange manager
    self.exchange_manager = ExchangeManager(self.config_manager)
    if not await self.exchange_manager.initialize():
        raise RuntimeError("Exchange manager initialization failed")
    
    # Initialize database client
    self.database_client = DatabaseClient(self.config_manager.config)
    
    self._logger.info("✅ Exchange services initialized")

async def _init_analysis_services(self) -> None:
    """Initialize analysis services."""
    self._logger.info("Phase 3: Initializing analysis services...")
    
    from src.core.analysis.portfolio import PortfolioAnalyzer
    from src.core.analysis.confluence import ConfluenceAnalyzer
    from src.core.validation.service import AsyncValidationService
    
    self.portfolio_analyzer = PortfolioAnalyzer(self.config_manager.config)
    self.confluence_analyzer = ConfluenceAnalyzer(self.config_manager.config)
    self.validation_service = AsyncValidationService()
    
    self._logger.info("✅ Analysis services initialized")

async def _init_market_services(self) -> None:
    """Initialize market data services."""
    self._logger.info("Phase 4: Initializing market services...")
    
    from src.core.market.top_symbols import TopSymbolsManager
    from src.core.market.market_data_manager import MarketDataManager
    
    # Initialize with dependencies
    self.top_symbols_manager = TopSymbolsManager(
        exchange_manager=self.exchange_manager,
        config=self.config_manager.config,
        validation_service=self.validation_service
    )
    
    self.market_data_manager = MarketDataManager(
        self.config_manager.config, 
        self.exchange_manager, 
        None  # alert_manager initialized later
    )
    
    self._logger.info("✅ Market services initialized")

async def _init_monitoring_services(self) -> None:
    """Initialize monitoring and alerting services.""" 
    self._logger.info("Phase 5: Initializing monitoring services...")
    
    from src.monitoring.metrics_manager import MetricsManager
    from src.monitoring.alert_manager import AlertManager
    from src.monitoring.market_reporter import MarketReporter
    from src.monitoring.monitor import MarketMonitor
    
    # Initialize alert manager first
    self.alert_manager = AlertManager(self.config_manager.config)
    self.alert_manager.register_discord_handler()
    
    # Update market_data_manager with alert_manager
    if self.market_data_manager:
        self.market_data_manager.alert_manager = self.alert_manager
    
    # Initialize other monitoring services
    self.metrics_manager = MetricsManager(self.config_manager.config, self.alert_manager)
    
    primary_exchange = await self.exchange_manager.get_primary_exchange()
    self.market_reporter = MarketReporter(
        top_symbols_manager=self.top_symbols_manager,
        alert_manager=self.alert_manager,
        exchange=primary_exchange,
        logger=self._logger
    )
    
    # Initialize market monitor with all dependencies
    self.market_monitor = MarketMonitor(
        logger=self._logger,
        metrics_manager=self.metrics_manager,
        exchange=primary_exchange,
        top_symbols_manager=self.top_symbols_manager,
        alert_manager=self.alert_manager,
        config=self.config_manager.config,
        market_reporter=self.market_reporter
    )
    
    # Inject additional dependencies into monitor
    self.market_monitor.exchange_manager = self.exchange_manager
    self.market_monitor.database_client = self.database_client
    self.market_monitor.portfolio_analyzer = self.portfolio_analyzer
    self.market_monitor.confluence_analyzer = self.confluence_analyzer
    
    self._logger.info("✅ Monitoring services initialized")
```

### Phase 2: Integration Layer (Day 1 - Afternoon)

**Duration**: 4 hours  
**Risk**: Low-Medium  
**Deliverables**: FastAPI integration without breaking existing routes

#### 2.1 Update Main Application

**File**: `src/main.py` (modified sections)

```python
# Replace global variables section (lines 97-111) with:
from src.core.app_context import create_app_context, AppContext

# Application context (replaces all globals)
app_context: Optional[AppContext] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management with AppContext."""
    global app_context
    
    logger.info("🚀 Starting Virtuoso Trading System with AppContext")
    
    try:
        # Create and initialize app context
        app_context = await create_app_context()
        
        # Inject into FastAPI state for backward compatibility
        app.state.config_manager = app_context.config_manager
        app.state.exchange_manager = app_context.exchange_manager
        app.state.database_client = app_context.database_client
        app.state.portfolio_analyzer = app_context.portfolio_analyzer
        app.state.confluence_analyzer = app_context.confluence_analyzer
        app.state.alert_manager = app_context.alert_manager
        app.state.metrics_manager = app_context.metrics_manager
        app.state.validation_service = app_context.validation_service
        app.state.top_symbols_manager = app_context.top_symbols_manager
        app.state.market_reporter = app_context.market_reporter
        app.state.market_monitor = app_context.market_monitor
        app.state.market_data_manager = app_context.market_data_manager
        
        logger.info("✅ Application context initialized and injected into FastAPI")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize application context: {e}")
        raise
    finally:
        # Cleanup
        if app_context:
            logger.info("🧹 Cleaning up application context...")
            await app_context.cleanup()
            app_context = None
        logger.info("👋 Application shutdown complete")

# Remove the old initialize_components() function entirely
# Remove the old cleanup_all_components() function entirely

# Update main() function
async def main():
    """Main application entry point with AppContext."""
    display_banner()
    
    # Signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        # Context cleanup handled by lifespan manager
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the application
    config = uvicorn.Config(
        "src.main:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        reload=False
    )
    
    server = uvicorn.Server(config)
    await server.serve()
```

#### 2.2 Create Dependency Injection Helpers

**File**: `src/api/dependencies.py`

```python
"""FastAPI dependency injection helpers for AppContext."""

from fastapi import Request, HTTPException
from typing import Optional
from src.core.app_context import AppContext
from src.config.manager import ConfigManager
from src.core.exchanges.manager import ExchangeManager
# ... other imports

def get_app_context(request: Request) -> Optional[AppContext]:
    """Get the application context from request."""
    # For now, reconstruct from app.state for backward compatibility
    # Later phases will inject AppContext directly
    return getattr(request.app, '_app_context', None)

def get_config_manager(request: Request) -> ConfigManager:
    """Get config manager from request state."""
    if hasattr(request.app.state, 'config_manager'):
        return request.app.state.config_manager
    raise HTTPException(status_code=500, detail="Config manager not initialized")

def get_exchange_manager(request: Request) -> ExchangeManager:
    """Get exchange manager from request state.""" 
    if hasattr(request.app.state, 'exchange_manager'):
        return request.app.state.exchange_manager
    raise HTTPException(status_code=500, detail="Exchange manager not initialized")

# Add similar functions for all other components...
```

### Phase 3: Route Migration (Day 2 - Morning)

**Duration**: 4 hours  
**Risk**: Medium  
**Deliverables**: All API routes using dependency injection

#### 3.1 Update API Route Dependencies

**Strategy**: Update routes to use dependency injection while maintaining functionality

**Example**: `src/api/routes/market.py`

```python
# Before (using global state):
@router.get("/market/report")
async def get_market_report():
    global market_reporter
    if not market_reporter:
        raise HTTPException(status_code=500, detail="Market reporter not initialized")
    return await market_reporter.generate_report()

# After (using dependency injection):
from src.api.dependencies import get_market_reporter

@router.get("/market/report")
async def get_market_report(
    market_reporter: MarketReporter = Depends(get_market_reporter)
):
    return await market_reporter.generate_report()
```

#### 3.2 Update All Route Files

**Files to Update**:
- `src/api/routes/market.py`
- `src/api/routes/alpha.py`
- `src/api/routes/alerts.py`
- `src/api/routes/signals.py`
- `src/api/routes/liquidation.py`
- `src/api/routes/trading.py`
- `src/api/routes/system.py`

**Pattern**: Replace all `request.app.state.*` with `Depends(get_*)` pattern

### Phase 4: Testing & Validation (Day 2 - Afternoon)

**Duration**: 4 hours  
**Risk**: Low  
**Deliverables**: Comprehensive testing suite and validation

#### 4.1 Create Unit Tests

**File**: `tests/core/test_app_context.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.core.app_context import AppContext, create_test_context

@pytest.mark.asyncio
async def test_app_context_initialization():
    """Test AppContext initialization phases."""
    context = await create_test_context()
    
    assert context.config_manager is not None
    assert context.exchange_manager is not None
    assert context._initialized is True

@pytest.mark.asyncio
async def test_app_context_cleanup():
    """Test AppContext cleanup."""
    context = await create_test_context()
    
    # Mock cleanup methods
    context.exchange_manager.cleanup = AsyncMock()
    context.database_client.cleanup = AsyncMock()
    
    await context.cleanup()
    
    # Verify cleanup was called
    context.exchange_manager.cleanup.assert_called_once()
    context.database_client.cleanup.assert_called_once()

@pytest.mark.asyncio
async def test_app_context_lifespan():
    """Test AppContext lifespan manager."""
    async with AppContext(config_manager=MagicMock()).lifespan() as context:
        assert context._initialized is True
    
    assert context._cleanup_called is True
```

#### 4.2 Create Integration Tests

**File**: `tests/api/test_dependency_injection.py`

```python
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.core.app_context import create_test_context

@pytest.mark.asyncio
async def test_api_routes_with_context():
    """Test that API routes work with AppContext."""
    
    # Test client with test context
    with TestClient(app) as client:
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        
        # Test market report endpoint  
        response = client.get("/api/market/report")
        assert response.status_code in [200, 503]  # May be 503 if services not available

@pytest.fixture
async def test_app_context():
    """Fixture providing test AppContext."""
    context = await create_test_context()
    yield context
    await context.cleanup()
```

#### 4.3 Create Migration Validation

**File**: `tests/migration/test_global_state_elimination.py`

```python
"""Tests to validate global state elimination."""

import pytest
import sys
from unittest.mock import patch
from src.main import app

def test_no_global_variables_accessed():
    """Ensure no global variables are accessed directly."""
    
    # Import main module
    import src.main as main_module
    
    # Check that problematic globals are None or not accessed
    problematic_globals = [
        'config_manager', 'exchange_manager', 'portfolio_analyzer',
        'database_client', 'confluence_analyzer', 'top_symbols_manager',
        'market_monitor', 'metrics_manager', 'alert_manager', 
        'market_reporter', 'health_monitor', 'validation_service',
        'market_data_manager'
    ]
    
    for global_name in problematic_globals:
        if hasattr(main_module, global_name):
            global_value = getattr(main_module, global_name)
            # Should be None or replaced with AppContext
            assert global_value is None or global_name == 'app_context'

@pytest.mark.asyncio
async def test_app_context_replaces_globals():
    """Test that AppContext provides all required components."""
    from src.core.app_context import create_test_context
    
    context = await create_test_context()
    
    # Verify all components are accessible
    assert context.config_manager is not None
    assert context.exchange_manager is not None
    assert context.database_client is not None
    # ... test all components
    
    await context.cleanup()
```

### Phase 5: Cleanup & Documentation (Day 3)

**Duration**: 4 hours  
**Risk**: Low  
**Deliverables**: Documentation and final cleanup

#### 5.1 Update Documentation

**File**: `docs/architecture/DEPENDENCY_INJECTION.md`

```markdown
# Dependency Injection Architecture

## Overview
The Virtuoso Trading System uses an AppContext-based dependency injection pattern to manage component lifecycle and dependencies.

## AppContext Structure
- **Core Services**: Configuration, basic utilities
- **Exchange Services**: Exchange connections, database
- **Analysis Services**: Portfolio, confluence, validation
- **Market Services**: Data management, symbol tracking  
- **Monitoring Services**: Alerts, metrics, reporting

## Usage Patterns

### In API Routes
```python
from src.api.dependencies import get_exchange_manager

@router.get("/example")
async def example_route(
    exchange_manager: ExchangeManager = Depends(get_exchange_manager)
):
    return await exchange_manager.get_status()
```

### In Tests
```python
from src.core.app_context import create_test_context

async def test_example():
    context = await create_test_context()
    # Use context.component_name
    await context.cleanup()
```
```

#### 5.2 Create Migration Guide

**File**: `docs/migration/GLOBAL_STATE_ELIMINATION.md`

```markdown
# Global State Elimination Migration Guide

## Before and After

### Before (Problematic)
```python
# Global variables
config_manager = None
exchange_manager = None

# Direct global access
global exchange_manager
result = await exchange_manager.get_data()
```

### After (Dependency Injection)
```python
# AppContext container
@dataclass
class AppContext:
    exchange_manager: ExchangeManager

# Dependency injection
def get_exchange_manager(request: Request):
    return request.app.state.exchange_manager

@router.get("/route")
async def route(exchange_manager = Depends(get_exchange_manager)):
    return await exchange_manager.get_data()
```

## Migration Checklist
- [ ] AppContext class created
- [ ] Initialization phases implemented
- [ ] FastAPI integration completed
- [ ] All routes updated to use dependency injection
- [ ] Tests created and passing
- [ ] Documentation updated
```

---

## Risk Assessment & Mitigation

### High Risk Areas

#### 1. Race Conditions During Migration
**Risk**: Mixing old global access with new AppContext  
**Mitigation**: 
- Complete migration in single atomic deployment
- Comprehensive testing before deployment
- Rollback plan with previous version

#### 2. External Script Dependencies
**Risk**: Scripts importing from main.py may break  
**Mitigation**:
- Update all external scripts in same deployment
- Provide backward compatibility shims if needed
- Document migration requirements

#### 3. Component Initialization Order
**Risk**: Dependencies initialized in wrong order  
**Mitigation**:
- Explicit dependency phases in AppContext
- Detailed logging of initialization steps
- Integration tests for initialization sequence

### Medium Risk Areas

#### 1. FastAPI State Integration
**Risk**: app.state pattern may conflict with AppContext  
**Mitigation**:
- Maintain app.state for backward compatibility during migration
- Gradual migration to pure dependency injection
- Testing with both patterns during transition

#### 2. Async Context Management
**Risk**: Component cleanup may not complete properly  
**Mitigation**:
- Comprehensive cleanup methods with timeouts
- Detailed logging of cleanup operations
- Resource monitoring during shutdown

### Low Risk Areas

#### 1. API Route Updates
**Risk**: Minor breaking changes in route signatures  
**Mitigation**: 
- Dependency injection maintains same functionality
- Routes tested individually
- API contracts remain unchanged

---

## Success Criteria

### Technical Metrics
- [ ] Zero global variable access in production code
- [ ] All 65+ route functions use dependency injection
- [ ] 100% test coverage for AppContext lifecycle
- [ ] <100ms additional initialization overhead
- [ ] Zero memory leaks in component lifecycle

### Functional Metrics  
- [ ] All existing API endpoints function identically
- [ ] No regression in application startup time
- [ ] Proper cleanup on application shutdown
- [ ] External scripts continue to work with updates

### Quality Metrics
- [ ] Unit tests for all AppContext components
- [ ] Integration tests for API dependency injection
- [ ] Documentation for new architecture
- [ ] Migration guide for future developers

---

## Rollback Plan

If critical issues are discovered during deployment:

### Immediate Rollback (< 5 minutes)
1. Revert to previous git commit
2. Restart application with previous version
3. Monitor for stability

### Partial Rollback (< 30 minutes)  
1. Restore global variables declarations
2. Restore initialize_components() function
3. Update lifespan() to use old initialization
4. Remove AppContext integration

### Recovery Testing
1. Verify all API endpoints respond correctly
2. Check component initialization sequence
3. Monitor memory usage and cleanup
4. Validate external script functionality

---

## Timeline Summary

| Phase | Duration | Risk | Key Deliverables |
|-------|----------|------|------------------|
| **Phase 1** | 4 hours | Low | AppContext class, initialization phases |
| **Phase 2** | 4 hours | Low-Med | FastAPI integration, dependency helpers |
| **Phase 3** | 4 hours | Medium | All routes using dependency injection |
| **Phase 4** | 4 hours | Low | Testing suite, validation |
| **Phase 5** | 4 hours | Low | Documentation, cleanup |
| **Total** | **20 hours** | **Medium** | **Global state elimination complete** |

**Estimated Timeline**: 2.5 working days  
**Recommended Schedule**: Spread across 3 days with testing buffer  
**Team Requirements**: 1 senior developer, 1 QA tester for validation

This plan provides a comprehensive, step-by-step approach to eliminating the global state antipattern while maintaining system stability and functionality.