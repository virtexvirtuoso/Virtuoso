import pytest
from unittest.mock import Mock
import pandas as pd
import numpy as np
from src.indicators.base_indicator import BaseIndicator
from src.core.logger import Logger

class TestIndicator(BaseIndicator):
    """Test implementation of BaseIndicator."""
    
    def __init__(self, config, logger=None):
        super().__init__(config, logger)
        self.component_weights = {
            'test_component': 1.0
        }
        
    def _validate_input(self, data):
        return isinstance(data, dict)
        
    async def _calculate_component_scores(self, data):
        return {'test_component': 75.0}

@pytest.fixture
def test_indicator():
    config = {'test': True}
    return TestIndicator(config, Logger(__name__))

async def test_calculate_score_valid_data(test_indicator):
    """Test score calculation with valid data."""
    result = await test_indicator.calculate_score({'test': 'data'})
    
    assert isinstance(result, dict)
    assert 'score' in result
    assert 'components' in result
    assert result['score'] == 75.0

async def test_calculate_score_invalid_data(test_indicator):
    """Test score calculation with invalid data."""
    result = await test_indicator.calculate_score("invalid")
    
    assert isinstance(result, dict)
    assert result['score'] == 50.0
    assert 'error' in result

async def test_weighted_score_calculation(test_indicator):
    """Test weighted score calculation."""
    scores = {'test_component': 75.0}
    score = test_indicator._calculate_weighted_score(scores)
    assert score == 75.0

async def test_default_scores(test_indicator):
    """Test default score generation."""
    result = test_indicator._get_default_scores("Test error")
    
    assert isinstance(result, dict)
    assert result['score'] == 50.0
    assert result['error'] == "Test error"
    assert 'components' in result 