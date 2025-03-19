from fastapi import Depends
from typing import Dict, Any
import ccxt
import pandas_ta as ta
from ..core.analysis.technical import TechnicalAnalysis
from ..core.analysis.position_calculator import PositionCalculator
from ..core.analysis.portfolio import PortfolioAnalyzer

async def get_exchange():
    """
    Get the exchange instance.
    For now, we'll use Bybit as the default exchange.
    """
    exchange = ccxt.bybit({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
        }
    })
    return exchange

async def get_analysis_engine(exchange: ccxt.Exchange = Depends(get_exchange)):
    """
    Get the technical analysis engine instance.
    """
    analysis_engine = TechnicalAnalysis()
    return analysis_engine

async def get_position_calculator(exchange: ccxt.Exchange = Depends(get_exchange)):
    """
    Get the position calculator instance.
    """
    position_calculator = PositionCalculator()
    return position_calculator

async def get_portfolio_analyzer(
    exchange: ccxt.Exchange = Depends(get_exchange),
    position_calculator: PositionCalculator = Depends(get_position_calculator)
):
    """
    Get the portfolio analyzer instance.
    """
    portfolio_analyzer = PortfolioAnalyzer(position_calculator)
    return portfolio_analyzer 