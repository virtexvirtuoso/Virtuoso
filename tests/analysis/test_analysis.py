import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from core.analysis.technical import TechnicalAnalysis
from core.analysis.confluence import ConfluenceAnalyzer, ConfluenceConfig
from core.exchanges.bybit import BybitExchange

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_market_data(exchange: BybitExchange, symbol: str) -> Dict[str, Any]:
    """Fetch market data from exchange"""
    try:
        # Convert symbol format for Bybit (BTC/USDT -> BTCUSDT)
        bybit_symbol = symbol.replace('/', '')
        
        # Fetch different types of market data
        market_data = await exchange.fetch_market_data(bybit_symbol)
        
        # Fetch historical klines
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
        klines = await exchange.fetch_historical_klines(
            symbol=bybit_symbol,
            interval='240',  # 4h timeframe
            start_time=start_time,
            end_time=end_time
        )
        
        market_data['klines'] = klines
        return market_data
        
    except Exception as e:
        logger.error(f"Error fetching market data: {str(e)}")
        raise

async def analyze_market_data(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze market data and calculate confluence score"""
    try:
        # Initialize analyzers
        technical_analyzer = TechnicalAnalysis()
        
        # Calculate technical indicators
        technical_signals = await technical_analyzer.calculate_indicators(market_data['klines'])
        
        # Prepare orderflow signals
        orderflow_signals = {
            'orderbook_imbalance': calculate_orderbook_imbalance(market_data['orderbook']),
            'volume_analysis': analyze_volume(market_data['ticker']),
            'large_orders': analyze_large_orders(market_data['orderbook'])
        }
        
        # Prepare exchange signals (mock data for now)
        exchange_signals = {
            'bybit': {
                'price': float(market_data['ticker']['last']),
                'volume': float(market_data['ticker']['baseVolume']),
                'bid': float(market_data['ticker']['bid']),
                'ask': float(market_data['ticker']['ask'])
            }
        }
        
        # Initialize confluence analyzer
        config = ConfluenceConfig()
        confluence_analyzer = ConfluenceAnalyzer(config)
        
        # Calculate confluence score
        confluence_score = await confluence_analyzer.calculate_confluence_score(
            technical_signals=technical_signals,
            orderflow_signals=orderflow_signals,
            exchange_signals=exchange_signals
        )
        
        return confluence_score
        
    except Exception as e:
        logger.error(f"Error analyzing market data: {str(e)}")
        raise

def calculate_orderbook_imbalance(orderbook: Dict[str, Any]) -> float:
    """Calculate orderbook imbalance"""
    try:
        bids = orderbook['bids']
        asks = orderbook['asks']
        
        bid_volume = sum(float(bid[1]) for bid in bids[:5])  # Top 5 levels
        ask_volume = sum(float(ask[1]) for ask in asks[:5])
        
        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            return 0.0
            
        return (bid_volume - ask_volume) / total_volume
        
    except Exception as e:
        logger.error(f"Error calculating orderbook imbalance: {str(e)}")
        return 0.0

def analyze_volume(ticker: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze trading volume"""
    try:
        volume = float(ticker.get('volume24h', 0))
        volume_change = float(ticker.get('volume24hPcnt', 0))
        
        return {
            'current': volume,
            'change': volume_change,
            'is_increasing': volume_change > 0,
            'analysis': {
                'volume_trend': 'increasing' if volume_change > 0 else 'decreasing',
                'significance': 'high' if volume > 1000 else 'medium' if volume > 100 else 'low'
            }
        }
    except Exception as e:
        logger.error(f"Error analyzing volume: {str(e)}")
        return {
            'current': 0,
            'change': 0,
            'is_increasing': False,
            'analysis': {
                'volume_trend': 'neutral',
                'significance': 'low'
            }
        }

def analyze_large_orders(orderbook: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze large orders in the orderbook"""
    try:
        # Define thresholds
        large_order_threshold = 1.0  # 1 BTC
        significant_orders = 3  # Number of orders to consider significant
        
        # Analyze bids
        large_bids = [
            order for order in orderbook['bids']
            if float(order[1]) > large_order_threshold
        ]
        
        # Analyze asks
        large_asks = [
            order for order in orderbook['asks']
            if float(order[1]) > large_order_threshold
        ]
        
        # Calculate metrics
        num_large_bids = len(large_bids)
        num_large_asks = len(large_asks)
        total_bid_volume = sum(float(bid[1]) for bid in large_bids)
        total_ask_volume = sum(float(ask[1]) for ask in large_asks)
        
        return {
            'orders': {
                'large_bids': num_large_bids,
                'large_asks': num_large_asks,
                'total_bid_volume': total_bid_volume,
                'total_ask_volume': total_ask_volume
            },
            'analysis': {
                'buy_pressure': 'high' if num_large_bids > significant_orders else 'medium' if num_large_bids > 0 else 'low',
                'sell_pressure': 'high' if num_large_asks > significant_orders else 'medium' if num_large_asks > 0 else 'low',
                'imbalance': total_bid_volume - total_ask_volume
            }
        }
    except Exception as e:
        logger.error(f"Error analyzing large orders: {str(e)}")
        return {
            'orders': {
                'large_bids': 0,
                'large_asks': 0,
                'total_bid_volume': 0,
                'total_ask_volume': 0
            },
            'analysis': {
                'buy_pressure': 'low',
                'sell_pressure': 'low',
                'imbalance': 0
            }
        }

def interpret_technical_signals(signals: Dict[str, Any]) -> str:
    """Interpret technical analysis signals"""
    interpretations = []
    
    # Moving Averages
    ma_signals = []
    if 'sma' in signals:
        for ma_name, ma_info in signals['sma'].items():
            if ma_info['signal'] != 'neutral':
                ma_signals.append(f"{ma_name} is {ma_info['signal']}")
    if 'ema' in signals:
        for ema_name, ema_info in signals['ema'].items():
            if ema_info['signal'] != 'neutral':
                ma_signals.append(f"{ema_name} is {ema_info['signal']}")
    
    if ma_signals:
        interpretations.append("Moving Averages: " + ", ".join(ma_signals))
    
    # RSI
    if 'rsi' in signals:
        rsi_data = signals['rsi']['RSI']
        rsi_value = float(rsi_data['value'])
        if rsi_value > 70:
            interpretations.append(f"RSI ({rsi_value:.2f}) indicates overbought conditions")
        elif rsi_value < 30:
            interpretations.append(f"RSI ({rsi_value:.2f}) indicates oversold conditions")
        elif rsi_value > 60:
            interpretations.append(f"RSI ({rsi_value:.2f}) shows bullish momentum")
        elif rsi_value < 40:
            interpretations.append(f"RSI ({rsi_value:.2f}) shows bearish momentum")
    
    # MACD
    if 'macd' in signals:
        macd_data = signals['macd']['MACD']
        if macd_data['signal'] == 'bullish':
            interpretations.append("MACD shows bullish momentum")
        elif macd_data['signal'] == 'bearish':
            interpretations.append("MACD shows bearish momentum")
    
    # Stochastic
    if 'stoch' in signals:
        stoch_data = signals['stoch']['Stochastic']
        k_value = float(stoch_data['k'])
        d_value = float(stoch_data['d'])
        if k_value > 80 and d_value > 80:
            interpretations.append(f"Stochastic ({k_value:.2f}, {d_value:.2f}) indicates overbought conditions")
        elif k_value < 20 and d_value < 20:
            interpretations.append(f"Stochastic ({k_value:.2f}, {d_value:.2f}) indicates oversold conditions")
    
    # ADX
    if 'adx' in signals:
        adx_data = signals['adx']['ADX']
        adx_value = float(adx_data['value'])
        if adx_value > 25:
            interpretations.append(f"ADX ({adx_value:.2f}) indicates a strong trend")
        else:
            interpretations.append(f"ADX ({adx_value:.2f}) indicates a weak trend")
    
    return "\n".join(interpretations)

def interpret_orderflow_signals(signals: Dict[str, Any]) -> str:
    """Interpret orderflow analysis signals"""
    interpretations = []
    
    # Volume Analysis
    if 'volume_analysis' in signals:
        volume_data = signals['volume_analysis']
        volume_trend = volume_data['analysis']['volume_trend']
        significance = volume_data['analysis']['significance']
        interpretations.append(f"Volume is {volume_trend} with {significance} significance")
    
    # Large Orders
    if 'large_orders' in signals:
        order_data = signals['large_orders']
        buy_pressure = order_data['analysis']['buy_pressure']
        sell_pressure = order_data['analysis']['sell_pressure']
        imbalance = order_data['analysis']['imbalance']
        
        if buy_pressure == 'high':
            interpretations.append("Strong buying pressure from large orders")
        elif sell_pressure == 'high':
            interpretations.append("Strong selling pressure from large orders")
        
        if imbalance > 0:
            interpretations.append(f"Order book shows net buying pressure ({imbalance:.2f})")
        elif imbalance < 0:
            interpretations.append(f"Order book shows net selling pressure ({imbalance:.2f})")
    
    # Orderbook Imbalance
    if 'orderbook_imbalance' in signals:
        imbalance = float(signals['orderbook_imbalance'])
        if abs(imbalance) > 0.2:
            direction = "buying" if imbalance > 0 else "selling"
            interpretations.append(f"Strong {direction} pressure in order book")
        elif abs(imbalance) > 0.1:
            direction = "buying" if imbalance > 0 else "selling"
            interpretations.append(f"Moderate {direction} pressure in order book")
    
    return "\n".join(interpretations)

def interpret_score(score: float) -> str:
    """Interpret the confluence score"""
    if score >= 0.8:
        return "Very Strong Bullish Signal"
    elif score >= 0.7:
        return "Strong Bullish Signal"
    elif score >= 0.6:
        return "Moderate Bullish Signal"
    elif score >= 0.5:
        return "Weak Bullish Signal"
    elif score >= 0.4:
        return "Neutral Signal"
    elif score >= 0.3:
        return "Weak Bearish Signal"
    elif score >= 0.2:
        return "Moderate Bearish Signal"
    else:
        return "Strong Bearish Signal"

async def main():
    try:
        # Initialize exchange
        config = {
            'testnet': True,  # Use testnet for testing
            'api_credentials': {
                'api_key': 'PQXFQYRLVZJNKWJNXK',  # Testnet API key
                'api_secret': 'ZXKWNQRLPVJNKYFQYX'  # Testnet API secret
            }
        }
        exchange = BybitExchange(config)
        await exchange.initialize()
        
        # Fetch and analyze market data
        symbol = 'BTC/USDT'
        market_data = await fetch_market_data(exchange, symbol)
        
        # Log market data
        logger.info("\n=== Market Data ===")
        logger.info(f"Last Price: {market_data['ticker']['last']}")
        logger.info(f"24h Volume: {market_data['ticker']['baseVolume']}")
        logger.info(f"24h Change: {market_data['ticker']['percentage']}%")
        logger.info(f"Bid/Ask Spread: {float(market_data['ticker']['ask']) - float(market_data['ticker']['bid'])}")
        logger.info(f"Number of Trades: {len(market_data['recent_trades'])}")
        logger.info(f"Number of Klines: {len(market_data['klines'])}")
        logger.info("=================\n")
        
        # Calculate confluence score
        confluence_score = await analyze_market_data(market_data)
        
        # Log detailed analysis
        logger.info("\n=== Technical Analysis ===")
        logger.info(interpret_technical_signals(confluence_score['details']['technical_analysis']))
        
        logger.info("\n=== Orderflow Analysis ===")
        logger.info(interpret_orderflow_signals(confluence_score['details']['orderflow_analysis']))
        
        # Final Scores
        logger.info("\n=== Final Analysis ===")
        logger.info(f"Symbol: {symbol}")
        logger.info(f"Total Score: {confluence_score['total_score']:.2f} - {interpret_score(confluence_score['total_score'])}")
        logger.info(f"Technical Score: {confluence_score['technical_score']:.2f} - {interpret_score(confluence_score['technical_score'])}")
        logger.info(f"Orderflow Score: {confluence_score['orderflow_score']:.2f} - {interpret_score(confluence_score['orderflow_score'])}")
        logger.info(f"Exchange Score: {confluence_score['exchange_score']:.2f} - {interpret_score(confluence_score['exchange_score'])}")
        logger.info(f"Signal: {confluence_score['signal']}")
        logger.info("=====================\n")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(main()) 