from fastapi import Depends, Request
from typing import Dict, Optional
from src.core.exchanges.manager import ExchangeManager
from src.core.exchanges.base import ExchangeInterface
from src.core.analysis.technical import TechnicalAnalysis
from src.core.analysis.portfolio import PortfolioAnalyzer
from src.core.analysis.position_calculator import PositionCalculator

async def get_exchange_manager(request: Request) -> ExchangeManager:
    """Get the exchange manager instance"""
    return request.app.state.exchange_manager

async def get_exchange(
    exchange_id: str,
    manager: ExchangeManager = Depends(get_exchange_manager)
) -> Optional[ExchangeInterface]:
    """Get a specific exchange instance"""
    return await manager.get_exchange(exchange_id)

async def get_config(request: Request) -> Dict:
    """Get the application configuration"""
    return request.app.state.config

async def get_technical_analysis(request: Request) -> TechnicalAnalysis:
    """Get the technical analysis engine"""
    if not hasattr(request.app.state, "technical_analysis"):
        request.app.state.technical_analysis = TechnicalAnalysis()
    return request.app.state.technical_analysis

async def get_portfolio_analyzer(request: Request) -> PortfolioAnalyzer:
    """Get the portfolio analyzer"""
    if not hasattr(request.app.state, "portfolio_analyzer"):
        request.app.state.portfolio_analyzer = PortfolioAnalyzer()
    return request.app.state.portfolio_analyzer

async def get_position_calculator(request: Request) -> PositionCalculator:
    """Get the position calculator"""
    if not hasattr(request.app.state, "position_calculator"):
        request.app.state.position_calculator = PositionCalculator()
    return request.app.state.position_calculator 