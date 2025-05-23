# Trading System Architecture

This document provides a detailed overview of the `TradingSystem` class implemented in `src/trade_execution/trading/trading_system.py`.

## Overview

The `TradingSystem` class serves as the central coordinator for all trading activities in the Virtuoso platform. It follows a modular architecture pattern where specialized components handle specific aspects of trading operations.

## Core Components

The `TradingSystem` coordinates five specialized manager components:

1. **DataManager**: Responsible for market data acquisition and processing
2. **PositionManager**: Manages active trading positions
3. **OrderManager**: Handles order creation, submission, and tracking
4. **RiskManager**: Enforces risk limits and validates trading decisions
5. **StrategyManager**: Generates trading signals based on market conditions

## Initialization Process

The system follows a careful initialization sequence:

```python
async def initialize(self) -> bool:
    # Initialize each component in sequence
    if not await self.data_manager.initialize():
        return False
        
    if not await self.position_manager.initialize():
        return False
        
    if not await self.order_manager.initialize():
        return False
        
    if not await self.risk_manager.initialize():
        return False
        
    if not await self.strategy_manager.initialize():
        return False
        
    self.initialized = True
    return True
```

Each component is initialized in order, with failure at any step preventing the system from starting.

## Trading Control Flow

### Starting Trading

When trading is started, two asynchronous loops are launched:

1. **Update Loop**: Regularly processes market data and generates signals
2. **Risk Check Loop**: Periodically validates risk exposure

```python
async def start_trading(self) -> bool:
    # Start trading tasks
    self.trading_enabled = True
    asyncio.create_task(self._update_loop())
    asyncio.create_task(self._risk_check_loop())
    return True
```

### Update Loop

The update loop processes each active symbol through a sequence of operations:

1. Get latest market data
2. Generate trading signals
3. Validate risk limits
4. Execute trades when appropriate

```python
async def _update_loop(self) -> None:
    while self.trading_enabled:
        for symbol in self.active_symbols:
            # Update market data
            data = await self.data_manager.get_initial_data(symbol)
            
            # Update strategy
            signals = await self.strategy_manager.update(symbol, data)
            
            # Check risk limits
            if not await self.risk_manager.check_limits(symbol):
                continue
                
            # Execute trades
            if signals:
                await self.execute_trades(symbol, signals)
                
        await asyncio.sleep(self.update_interval)
```

### Risk Check Loop

The risk check loop independently monitors risk exposure and intervenes when limits are exceeded:

```python
async def _risk_check_loop(self) -> None:
    while self.trading_enabled:
        for symbol in self.active_symbols:
            if not await self.risk_manager.check_limits(symbol):
                # Close positions if risk limits exceeded
                await self.close_positions(symbol)
                
        await asyncio.sleep(self.risk_check_interval)
```

## Symbol Management

The system carefully tracks which symbols are actively traded:

- **Adding Symbols**: Each component must successfully add the symbol
- **Removing Symbols**: Positions are closed and orders canceled before removal
- **Maximum Symbols**: A configurable limit prevents overextension

```python
async def add_symbol(self, symbol: str) -> bool:
    if len(self.active_symbols) >= self.max_symbols:
        return False
        
    # Add to each component
    if not await self.data_manager.add_symbol(symbol):
        return False
    # ... and other components
        
    self.active_symbols.add(symbol)
    return True
```

## Trade Execution

Trade execution follows a careful validation sequence:

```python
async def execute_trades(self, symbol: str, signals: Dict[str, Any]) -> bool:
    # Validate signals
    if not signals:
        return True
        
    # Check risk limits
    if not await self.risk_manager.check_limits(symbol):
        return False
        
    # Execute orders
    return await self.order_manager.execute_signals(symbol, signals)
```

## Position and Order Management

The system provides methods to manage positions and orders:

- **close_positions**: Close all positions for a symbol
- **close_all_positions**: Close all positions across all symbols
- **cancel_orders**: Cancel all orders for a symbol
- **cancel_all_orders**: Cancel all orders across all symbols

## Error Handling

The system implements comprehensive error handling:

- Each method is wrapped in try/except blocks
- Errors are logged with full tracebacks in debug mode
- Component failures are carefully tracked and reported
- Operations continue for other symbols when one fails

## Configuration

The system is highly configurable:

- Each component receives its own configuration section
- System-wide parameters include:
  - `max_symbols`: Maximum number of concurrently traded symbols
  - `update_interval`: How frequently to process market data
  - `risk_check_interval`: How frequently to validate risk limits

## Integration with Score-Based Risk Management

The TradingSystem works seamlessly with the score-based stop loss and position sizing functionality through:

1. **Configuration Flow**: The system passes configuration to its components during initialization, which automatically incorporates risk management parameters
   
2. **Component Delegation**: Actual trade execution and risk management are delegated to specialized components (OrderManager, PositionManager) that would utilize the TradeExecutor

3. **Risk Validation**: The RiskManager component enforces limits before trade execution, ensuring compliance with risk management rules

## Shutdown Process

When shutting down, the system follows a careful sequence:

1. Disable trading to stop processing loops
2. Close all open positions
3. Cancel all pending orders
4. Clean up each component
5. Mark system as uninitialized

This ensures a clean and safe shutdown with minimal market exposure. 