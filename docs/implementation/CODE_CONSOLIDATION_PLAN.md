# Code Consolidation Plan

## Overview
This document outlines the plan to consolidate duplicate class implementations and reorganize code structure for better maintainability.

## 1. SimpleErrorHandler Consolidation

### Current Implementations Analysis:

#### A. `/src/core/error/handlers.py` (BEST - KEEP THIS)
- **Features**: Most comprehensive implementation
  - Error event storage with history
  - Error statistics tracking
  - Handler registration system
  - Async support
  - Proper dataclass structure
- **Decision**: This is the canonical implementation

#### B. `/src/data_acquisition/error_handler.py` (MERGE FEATURES)
- **Unique Features**: Discord webhook notifications
- **Decision**: Extract Discord notification feature and add to canonical

#### C. `/src/data_processing/error_handler.py` (DELETE)
- **Features**: Basic implementation, no unique features
- **Decision**: Delete and replace with canonical

### Action Plan:
1. Add Discord notification feature to `/src/core/error/handlers.py`
2. Update all imports to use `/src/core/error/handlers.py`
3. Delete the other two implementations

## 2. ValidationError Consolidation

### Current Implementations Analysis:

#### A. `/src/core/error/exceptions.py` (KEEP THIS)
- **Inheritance**: SystemError (most appropriate for validation)
- **Location**: Proper location in error module
- **Decision**: This is the canonical implementation

#### B. `/src/utils/error_handling.py` (DELETE)
- **Inheritance**: TradingError
- **Decision**: Delete, use canonical

#### C. `/src/utils/validation_types.py` (DELETE)
- **Inheritance**: Exception
- **Decision**: Delete, use canonical

#### D. `/src/indicators/base_indicator.py` (DELETE)
- **Line**: 2045
- **Decision**: Delete, use canonical

#### E. `/src/core/validation/models.py` (RENAME)
- **Type**: Not an exception, appears to be a dataclass
- **Decision**: Rename to avoid confusion (e.g., ValidationErrorData)

#### F. `/src/core/config/validators/binance_validator.py` (RENAME)
- **Type**: Standalone class
- **Decision**: Rename to BinanceValidationError if it's an exception

### Action Plan:
1. Keep `/src/core/error/exceptions.py` ValidationError
2. Rename non-exception classes to avoid confusion
3. Update all imports
4. Delete duplicates

## 3. Other Duplicate Classes

### ValidationResult (Keep `/src/core/validation/models.py`)
- Most comprehensive with proper typing
- Delete others

### HealthStatus (Keep `/src/core/models/health.py`)
- Centralized location
- Delete others

### ErrorSeverity (Keep `/src/core/error/models.py`)
- Proper enum implementation
- Delete others

### ResourceManager (Keep `/src/core/resources/manager.py`)
- Most feature-complete
- Delete others

### MarketDataValidator (Keep `/src/core/validation/market_data.py`)
- Most comprehensive validation logic
- Delete others

## 4. Directory Structure Reorganization

### Target Structure:
```
src/
├── core/
│   ├── error/
│   │   ├── __init__.py
│   │   ├── handlers.py         # SimpleErrorHandler (with Discord)
│   │   ├── exceptions.py       # All custom exceptions
│   │   ├── models.py          # ErrorContext, ErrorSeverity, etc.
│   │   └── decorators.py      # Error handling decorators
│   │
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── base.py            # Base validation interfaces
│   │   ├── models.py          # ValidationResult, etc.
│   │   ├── market_data.py     # MarketDataValidator
│   │   └── validators/        # Specific validators
│   │
│   └── models/
│       ├── __init__.py
│       ├── health.py          # HealthStatus
│       ├── market.py          # MarketData
│       ├── component.py       # ComponentState
│       └── resource.py        # ResourceLimits

## 5. Import Update Strategy

### Step 1: Create Import Mapping
```python
IMPORT_MAPPING = {
    # Error Handlers
    'from src.data_processing.error_handler import SimpleErrorHandler': 
        'from src.core.error.handlers import SimpleErrorHandler',
    'from src.data_acquisition.error_handler import SimpleErrorHandler': 
        'from src.core.error.handlers import SimpleErrorHandler',
    
    # ValidationError
    'from src.utils.error_handling import ValidationError':
        'from src.core.error.exceptions import ValidationError',
    'from src.utils.validation_types import ValidationError':
        'from src.core.error.exceptions import ValidationError',
    # ... etc
}
```

### Step 2: Automated Import Update Script
- Create script to automatically update all imports
- Use AST parsing for safety
- Create backup before changes

## 6. Implementation Phases

### Phase 1: Preparation (Day 1)
1. Create comprehensive import mapping
2. Backup all files
3. Create migration script
4. Set up testing environment

### Phase 2: Error Handler Consolidation (Day 2)
1. Add Discord feature to canonical SimpleErrorHandler
2. Update all SimpleErrorHandler imports
3. Test error handling functionality
4. Delete duplicate implementations

### Phase 3: ValidationError Consolidation (Day 3)
1. Rename non-exception ValidationError classes
2. Update all ValidationError imports
3. Test validation functionality
4. Delete duplicates

### Phase 4: Other Classes (Day 4-5)
1. Consolidate remaining duplicate classes
2. Update imports for each
3. Test affected functionality
4. Delete duplicates

### Phase 5: Reorganization (Day 6)
1. Move classes to proper directories
2. Update imports for new locations
3. Update __init__.py files
4. Final testing

### Phase 6: Cleanup (Day 7)
1. Remove empty directories
2. Update documentation
3. Update import statements in tests
4. Final validation

## 7. Risk Mitigation

1. **Backup Strategy**: Git branch + full backup before each phase
2. **Testing**: Run full test suite after each phase
3. **Rollback Plan**: Git revert if issues arise
4. **Gradual Migration**: One class type at a time
5. **Import Validation**: Script to verify all imports resolve

## 8. Success Metrics

- Zero duplicate class definitions
- All imports use canonical paths
- Consistent directory structure
- All tests passing
- No runtime import errors

## 9. Long-term Benefits

1. **Clarity**: One source of truth for each class
2. **Maintainability**: Bug fixes only needed in one place
3. **Onboarding**: New developers know where to find things
4. **Testing**: Simpler test structure
5. **Performance**: Reduced memory from duplicate definitions