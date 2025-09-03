# Contributing to Virtuoso CCXT

Thank you for your interest in contributing to the Virtuoso CCXT Trading System! This document provides guidelines and instructions for contributing to the project.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Development Workflow](#development-workflow)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Requirements](#testing-requirements)
- [Documentation Standards](#documentation-standards)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting Guidelines](#issue-reporting-guidelines)
- [Community and Support](#community-and-support)

## Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, background, or identity.

### Expected Behavior
- Be respectful and considerate in all interactions
- Accept constructive criticism gracefully
- Focus on what is best for the community and project
- Show empathy towards other community members
- Use welcoming and inclusive language

### Unacceptable Behavior
- Harassment, discrimination, or offensive comments
- Personal attacks or trolling
- Publishing private information without consent
- Any conduct that could reasonably be considered inappropriate

## Getting Started

### Prerequisites
Before contributing, ensure you have:
- Python 3.11+ installed
- Git configured with your GitHub account
- Basic understanding of the project architecture
- Reviewed the [README.md](README.md) and [Installation Guide](docs/01-getting-started/INSTALLATION.md)

### First-Time Contributors
We welcome first-time contributors! Look for issues labeled:
- `good first issue` - Simple tasks suitable for beginners
- `help wanted` - Issues where we need community assistance
- `documentation` - Documentation improvements

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/Virtuoso_ccxt.git
cd Virtuoso_ccxt

# Add upstream remote
git remote add upstream https://github.com/virtuoso/Virtuoso_ccxt.git
```

### 2. Create Virtual Environment

```bash
# Create and activate virtual environment
python3.11 -m venv venv311
source venv311/bin/activate  # On Windows: venv311\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Note: Use test API keys for development
```

### 4. Install Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run hooks on all files (optional)
pre-commit run --all-files
```

## How to Contribute

### Types of Contributions

#### 1. Bug Fixes
- Fix bugs reported in issues
- Add tests to prevent regression
- Update documentation if needed

#### 2. Feature Development
- Discuss new features in issues first
- Implement features following design patterns
- Include comprehensive tests
- Document new functionality

#### 3. Performance Improvements
- Profile code to identify bottlenecks
- Implement optimizations with benchmarks
- Ensure no functionality regression

#### 4. Documentation
- Fix typos and improve clarity
- Add missing documentation
- Create tutorials and guides
- Update API documentation

#### 5. Testing
- Add missing test cases
- Improve test coverage
- Fix flaky tests
- Add integration tests

## Development Workflow

### 1. Create Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
# Or for bugs: fix/issue-description
# For docs: docs/improvement-description
```

### 2. Make Changes

```bash
# Make your changes
# Follow code style guidelines
# Add/update tests
# Update documentation

# Run tests locally
pytest tests/

# Check code style
flake8 src/
black src/ --check
```

### 3. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add new market analysis dimension

- Implement momentum analysis
- Add unit tests for momentum calculator
- Update documentation with examples"
```

#### Commit Message Format

Follow conventional commits specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test additions or fixes
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(analysis): add volume profile indicator
fix(cache): resolve memory leak in Redis adapter
docs(api): update WebSocket examples
perf(dashboard): optimize data fetching with parallel requests
```

### 4. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create pull request on GitHub
```

## Code Style Guidelines

### Python Style Guide

We follow PEP 8 with some modifications:

#### General Rules
```python
# Line length: 88 characters (Black default)
# Use 4 spaces for indentation
# Use snake_case for functions and variables
# Use PascalCase for classes
# Use UPPER_CASE for constants
```

#### Imports
```python
# Standard library imports
import os
import sys
from datetime import datetime

# Third-party imports
import pandas as pd
import numpy as np
from fastapi import FastAPI

# Local imports
from src.core.analysis import MarketAnalyzer
from src.utils.helpers import calculate_metrics
```

#### Docstrings
```python
def analyze_market(symbol: str, timeframe: str = "5m") -> dict:
    """
    Analyze market conditions for a given symbol.
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        timeframe: Candlestick timeframe (default: '5m')
    
    Returns:
        Dictionary containing analysis results:
        {
            'trend': 'bullish' | 'bearish' | 'neutral',
            'strength': float (0-1),
            'signals': List[dict]
        }
    
    Raises:
        ValueError: If symbol format is invalid
        ConnectionError: If exchange connection fails
    
    Examples:
        >>> result = analyze_market('BTC/USDT', '15m')
        >>> print(result['trend'])
        'bullish'
    """
    # Implementation
    pass
```

#### Type Hints
```python
from typing import List, Dict, Optional, Union, Tuple

def process_signals(
    signals: List[Dict[str, Union[str, float]]],
    threshold: float = 0.7,
    max_signals: Optional[int] = None
) -> Tuple[List[dict], dict]:
    """Process and filter trading signals."""
    pass
```

#### Error Handling
```python
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    # Handle specific error
    raise
except Exception as e:
    logger.exception("Unexpected error occurred")
    # Handle general error
    raise
finally:
    # Cleanup code
    cleanup_resources()
```

### JavaScript/TypeScript Style

For frontend code:

```javascript
// Use 2 spaces for indentation
// Use camelCase for variables and functions
// Use PascalCase for components and classes
// Use const/let, avoid var

const analyzeData = async (symbol) => {
  try {
    const response = await fetch(`/api/market/${symbol}`);
    const data = await response.json();
    return processData(data);
  } catch (error) {
    console.error('Analysis failed:', error);
    throw error;
  }
};
```

## Testing Requirements

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── e2e/           # End-to-end tests
└── fixtures/      # Test data and fixtures
```

### Writing Tests

#### Unit Tests
```python
import pytest
from src.core.analysis import calculate_rsi

def test_calculate_rsi():
    """Test RSI calculation with known values."""
    prices = [44, 44.25, 44.5, 43.75, 44.65, 45.12, 45.84]
    rsi = calculate_rsi(prices, period=6)
    assert 50 < rsi < 70  # Expected range
    
def test_calculate_rsi_edge_cases():
    """Test RSI with edge cases."""
    with pytest.raises(ValueError):
        calculate_rsi([], period=14)  # Empty list
    
    with pytest.raises(ValueError):
        calculate_rsi([100], period=14)  # Insufficient data
```

#### Integration Tests
```python
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_dashboard_endpoint():
    """Test dashboard data endpoint."""
    response = client.get("/api/dashboard/data")
    assert response.status_code == 200
    data = response.json()
    assert "market_data" in data
    assert "signals" in data
```

### Test Coverage

Maintain minimum test coverage:
- Unit tests: 80% coverage
- Integration tests: 60% coverage
- Critical paths: 100% coverage

Run coverage report:
```bash
pytest --cov=src --cov-report=html
# View report in htmlcov/index.html
```

## Documentation Standards

### Code Documentation

Every module, class, and function should have documentation:

```python
"""
Module: src/core/analysis/sentiment.py

This module provides sentiment analysis functionality for market data.
It analyzes news, social media, and market indicators to determine
overall market sentiment.

Classes:
    SentimentAnalyzer: Main sentiment analysis class
    
Functions:
    calculate_sentiment_score: Calculate sentiment from text
    aggregate_sources: Combine multiple sentiment sources
"""
```

### API Documentation

Document all API endpoints:

```python
@app.get("/api/market/{symbol}", response_model=MarketData)
async def get_market_data(
    symbol: str = Path(..., description="Trading pair (e.g., BTC-USDT)"),
    interval: str = Query("5m", description="Timeframe interval")
):
    """
    Retrieve market data for a specific symbol.
    
    This endpoint returns current market data including price,
    volume, and technical indicators for the specified symbol.
    
    - **symbol**: Trading pair in exchange format
    - **interval**: Candlestick interval (1m, 5m, 15m, 30m, 1h, 4h, 1d)
    
    Returns:
        MarketData object with current market information
    """
    pass
```

### README Updates

Update README.md when adding:
- New features
- Configuration options
- Dependencies
- API endpoints

## Pull Request Process

### Before Submitting

1. **Test Thoroughly**
   ```bash
   # Run all tests
   pytest
   
   # Check code style
   flake8 src/
   black src/ --check
   
   # Run type checking
   mypy src/
   ```

2. **Update Documentation**
   - Add/update docstrings
   - Update README if needed
   - Add to CHANGELOG.md

3. **Rebase if Needed**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

### PR Template

Use this template for pull requests:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- List key changes
- Include motivation and context

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tests added/updated
- [ ] All tests passing

## Screenshots (if applicable)
Add screenshots for UI changes

## Related Issues
Closes #123
```

### Review Process

1. **Automated Checks**
   - CI/CD pipeline runs tests
   - Code style verification
   - Coverage report

2. **Code Review**
   - At least one maintainer review
   - Address feedback promptly
   - Discussion on implementation

3. **Merge Criteria**
   - All tests passing
   - Approved by maintainer
   - No conflicts with main
   - Documentation complete

## Issue Reporting Guidelines

### Bug Reports

Use the bug report template:

```markdown
**Describe the Bug**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Screenshots**
If applicable

**Environment:**
- OS: [e.g., macOS 12.0]
- Python: [e.g., 3.11.5]
- Version: [e.g., 1.0.0]

**Additional Context**
Any other relevant information

**Logs**
```
Paste relevant log output
```
```

### Feature Requests

Use the feature request template:

```markdown
**Problem Statement**
What problem does this solve?

**Proposed Solution**
Describe the solution

**Alternatives Considered**
Other approaches considered

**Additional Context**
Any other information

**Implementation Ideas**
Technical implementation suggestions
```

## Community and Support

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **Discord**: Real-time discussion and support
- **Email**: dev@virtuoso-trading.com

### Getting Help

- Read documentation first
- Search existing issues
- Ask in Discord #help channel
- Create detailed issue if needed

### Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

## Development Tips

### Performance Optimization
- Profile before optimizing
- Use async/await for I/O operations
- Implement caching strategically
- Batch API requests when possible

### Security Best Practices
- Never commit sensitive data
- Validate all user input
- Use parameterized queries
- Keep dependencies updated

### Debugging
```python
# Use logging instead of print
import logging
logger = logging.getLogger(__name__)

logger.debug("Debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
```

### Local Testing with Docker
```bash
# Build Docker image
docker build -t virtuoso-ccxt .

# Run tests in container
docker run --rm virtuoso-ccxt pytest

# Run application
docker run -p 8003:8003 --env-file .env virtuoso-ccxt
```

## Release Process

### Version Numbering
We use Semantic Versioning (SemVer):
- MAJOR.MINOR.PATCH (e.g., 2.1.3)
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Release Checklist
1. Update version in `__version__.py`
2. Update CHANGELOG.md
3. Run full test suite
4. Create release branch
5. Tag release
6. Deploy to production
7. Update documentation

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.

## Thank You!

Thank you for contributing to Virtuoso CCXT! Your efforts help make this project better for everyone in the trading community.

---

*Last updated: August 30, 2025*