# Risk Management Features

This document details the risk management features implemented in the Virtuoso trading system.

## Position Sizing

Position sizing is a critical risk management feature that determines how much capital to allocate to each trade.

### Position Size Parameters

- **Base Position Size**: 3% of available balance (`base_position_pct = 0.03`)
- **Maximum Position Size**: 20% of available balance (`max_position_pct = 0.20`)
- **Scale Factor**: 1% per point (`scale_factor = 0.01`)

### Position Size Calculation

1. For **Long** positions (buy):
   - Positions are only taken when confluence score ≥ buy threshold (68)
   - Position size increases by 1% of balance for each point above 68
   - At score 68: position = 3% of balance (base)
   - At score 75: position = 3% + (75-68) × 1% = 10% of balance
   - At score 85: position = 20% of balance (maximum cap)

2. For **Short** positions (sell):
   - Positions are only taken when confluence score ≤ sell threshold (35)
   - Position size increases by 1% of balance for each point below 35
   - At score 35: position = 3% of balance (base)
   - At score 28: position = 3% + (35-28) × 1% = 10% of balance
   - At score 15: position = 20% of balance (maximum cap)

## Scaled Stop Loss

The system implements a dynamic stop loss that scales with position size. Larger positions get tighter stops for better risk management.

### Stop Loss Parameters

- **Default Stop Loss**: 2% (`trailing_stop_pct = 0.02`)
- **Minimum Stop Loss**: 1% (half of default)

### Stop Loss Calculation

1. **Base Positions** (3% of balance):
   - Stop loss = 2% (default)

2. **Scaled Positions** (between 3% and 20% of balance):
   - Stop loss scales linearly between 2% and 1%
   - Formula: `stop_loss = default_stop - (position_scale * (default_stop - min_stop))`
   - Where `position_scale` is how far the position is between base and max (0.0 to 1.0)

3. **Examples**:
   - 3% position: 2.00% stop loss
   - 5% position: 1.88% stop loss
   - 10% position: 1.59% stop loss
   - 15% position: 1.29% stop loss
   - 20% position: 1.00% stop loss

## Benefits

1. **Position Sizing by Confidence**:
   - Allocates more capital to high-confidence trades
   - Maintains minimum allocations for base-level signals
   - Caps maximum risk per trade

2. **Scaled Risk Management**:
   - Balances risk and reward across different position sizes
   - Provides tighter protection for larger positions
   - Allows for aggressive position scaling with appropriate risk control 