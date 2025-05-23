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

- **Default Stop Loss**: 3% (`trailing_stop_pct = 0.03`)
- **Minimum Stop Loss**: 2% (two-thirds of default)

### Stop Loss Calculation

1. **Base Positions** (3% of balance):
   - Stop loss = 3% (default)

2. **Scaled Positions** (between 3% and 20% of balance):
   - Stop loss scales linearly between 3% and 2%
   - Formula: `stop_loss = default_stop - (position_scale * (default_stop - min_stop))`
   - Where `position_scale` is how far the position is between base and max (0.0 to 1.0)

3. **Examples**:
   - 3% position: 3.00% stop loss
   - 5% position: 2.88% stop loss
   - 10% position: 2.59% stop loss
   - 15% position: 2.29% stop loss
   - 20% position: 2.00% stop loss

## Benefits

1. **Position Sizing by Confidence**:
   - Allocates more capital to high-confidence trades
   - Maintains minimum allocations for base-level signals
   - Caps maximum risk per trade

2. **Scaled Risk Management**:
   - Balances risk and reward across different position sizes
   - Provides tighter protection for larger positions
   - Allows for aggressive position scaling with appropriate risk control 

## Score-Based Stop Loss Management

A new approach to stop loss management has been implemented that scales stop loss percentages directly based on the confluence score rather than position size.

### Core Principles

1. **Higher Confidence = Wider Stop**:
   - Higher confidence trades (stronger signals) receive wider stops to allow more room for the trade to develop
   - Lower confidence trades (weaker signals) receive tighter stops to limit potential losses

2. **Stop Loss Parameters**:
   - **Base Stop Loss**: Configured value (3% by default)
   - **Maximum Stop Loss**: 150% of base stop (4.5% for highest confidence trades)
   - **Minimum Stop Loss**: 80% of base stop (2.4% for threshold-level trades)

### Stop Loss Calculation

1. **For Long Positions**:
   - Confluence scores at or below buy threshold (70) receive minimum stop loss (2.4%)
   - Confluence scores at 100 receive maximum stop loss (4.5%)
   - Scores between threshold and 100 receive proportionally scaled stops

2. **For Short Positions**:
   - Confluence scores at or above sell threshold (30) receive minimum stop loss (2.4%)
   - Confluence scores at 0 receive maximum stop loss (4.5%)
   - Scores between 0 and threshold receive proportionally scaled stops

### Examples

* **Long Position, Score = 70 (threshold)**: 2.4% stop loss (tight)
* **Long Position, Score = 85 (strong)**: 3.5% stop loss (medium)
* **Long Position, Score = 95 (very strong)**: 4.2% stop loss (wide)
* **Short Position, Score = 30 (threshold)**: 2.4% stop loss (tight)  
* **Short Position, Score = 15 (strong)**: 3.5% stop loss (medium)
* **Short Position, Score = 5 (very strong)**: 4.2% stop loss (wide)

### Detailed Examples with Trade Simulations

Let's examine how position sizing and stop loss management work together for different confidence levels:

#### Long Position Examples (Bitcoin at $60,000)

| Confluence Score | Position Size | Stop Loss % | Position Amount | Account Capital | Risk per Trade | Stop Price | P&L at 5% Move |
|-----------------|--------------|------------|----------------|----------------|---------------|------------|---------------|
| 70 (threshold)  | 3.0%         | 2.4%       | $3,000         | $100,000       | $72           | $58,560    | +$150 / -$72   |
| 75 (moderate)   | 8.0%         | 2.7%       | $8,000         | $100,000       | $216          | $58,380    | +$400 / -$216  |
| 85 (strong)     | 18.0%        | 3.5%       | $18,000        | $100,000       | $630          | $57,900    | +$900 / -$630  |
| 95 (very strong)| 20.0%        | 4.2%       | $20,000        | $100,000       | $840          | $57,480    | +$1,000 / -$840|

#### Short Position Examples (Ethereum at $3,000)

| Confluence Score | Position Size | Stop Loss % | Position Amount | Account Capital | Risk per Trade | Stop Price | P&L at 5% Move |
|-----------------|--------------|------------|----------------|----------------|---------------|------------|---------------|
| 30 (threshold)  | 3.0%         | 2.4%       | $3,000         | $100,000       | $72           | $3,072     | +$150 / -$72   |
| 20 (moderate)   | 13.0%        | 3.0%       | $13,000        | $100,000       | $390          | $3,090     | +$650 / -$390  |
| 10 (strong)     | 20.0%        | 3.8%       | $20,000        | $100,000       | $760          | $3,114     | +$1,000 / -$760|
| 5 (very strong) | 20.0%        | 4.1%       | $20,000        | $100,000       | $820          | $3,123     | +$1,000 / -$820|

### Market Scenario Examples

#### Example 1: Strong Bullish Signal on Bitcoin

* **Market Context**: Bitcoin showing multiple bullish confirmation signals
* **Confluence Score**: 88/100
* **Position Sizing**: 
  * Base position: 3% ($3,000 on $100K account)
  * Scaling factor: 1% per point above threshold
  * Confidence adjustment: +18% (88 - 70) × 1% = 18%
  * Total allocation: 3% + 18% = 21% (capped at 20% = $20,000)
* **Stop Loss Calculation**:
  * Base stop: 3.0%
  * Confidence normalized: (88-70)/(100-70) = 0.6
  * Stop adjustment: 0.6 × (4.5% - 2.4%) = 1.26%
  * Final stop: 2.4% + 1.26% = 3.66% ($1,732 at risk)
* **Trade Outcome Scenarios**:
  * If price moves +10%: Profit = $2,000 (unrealized)
  * If price hits stop: Loss = $732 (realized)
  * Risk-reward ratio: 2.73:1

#### Example 2: Moderate Bearish Signal on Ethereum

* **Market Context**: Ethereum showing some bearish signals but with mixed indicators
* **Confluence Score**: 22/100
* **Position Sizing**:
  * Base position: 3% ($3,000 on $100K account)
  * Scaling factor: 1% per point below threshold
  * Confidence adjustment: +8% (30 - 22) × 1% = 8%
  * Total allocation: 3% + 8% = 11% ($11,000)
* **Stop Loss Calculation**:
  * Base stop: 3.0%
  * Confidence normalized: (30-22)/30 = 0.267
  * Stop adjustment: 0.267 × (4.5% - 2.4%) = 0.56%
  * Final stop: 2.4% + 0.56% = 2.96% ($325.60 at risk)
* **Trade Outcome Scenarios**:
  * If price moves -7%: Profit = $770 (unrealized)
  * If price hits stop: Loss = $325.60 (realized)
  * Risk-reward ratio: 2.36:1

#### Example 3: Extremely Strong Short Signal on Altcoin

* **Market Context**: Small-cap altcoin showing extreme bearish divergence and breakdown
* **Confluence Score**: 3/100 (highly bearish)
* **Position Sizing**:
  * Base position: 3% ($3,000 on $100K account)
  * Confidence adjustment: +27% (30 - 3) × 1% = 27%
  * Total allocation: 3% + 27% = 30% (capped at 20% = $20,000)
* **Stop Loss Calculation**:
  * Base stop: 3.0%
  * Confidence normalized: (30-3)/30 = 0.9
  * Stop adjustment: 0.9 × (4.5% - 2.4%) = 1.89%
  * Final stop: 2.4% + 1.89% = 4.29% ($858 at risk)
* **Trade Outcome Scenarios**:
  * If price crashes 25%: Profit = $5,000 (unrealized)
  * If price hits stop: Loss = $858 (realized)
  * Risk-reward ratio: 5.83:1

### Advantages

1. **Better Alignment with Signal Strength**:
   - Stop loss directly corresponds to confidence level rather than being inversely related
   - High-confidence trades get both larger positions AND more room to develop

2. **Improved Risk-Reward Dynamics**:
   - Higher conviction trades get wider stops and larger size, maximizing potential gain
   - Lower conviction trades get tighter stops and smaller size, limiting potential loss

3. **More Efficient Capital Allocation**:
   - System allocates not just more capital but also more "time equity" to high-confidence signals
   - Provides a more balanced approach to trading with the market's natural volatility

### Implementation

The `calculate_score_based_stop_loss` method replaces `calculate_scaled_stop_loss` in the trade execution flow, shifting from position-based to score-based risk management. 

## Visual Representation of Risk Management Strategy

### Position Size and Stop Loss Relationship for Long Positions

```
Confluence Score:    70     75     80     85     90     95    100
                     |      |      |      |      |      |      |
Position Size %:    3.0%    8%    13%    18%    20%    20%    20%
                     |      |      |      |      |      |      |
Stop Loss %:        2.4%   2.7%   3.0%   3.5%   3.8%   4.2%   4.5%
                     |      |      |      |      |      |      |
Risk per $100K:     $72    $216   $390   $630   $760   $840   $900
                     |      |      |      |      |      |      |
    LOW RISK <------------------------------------------------------> HIGH REWARD
    Small Position                                  Large Position
    Tight Stop                                      Wide Stop
```

### Position Size and Stop Loss Relationship for Short Positions

```
Confluence Score:   30     25     20     15     10      5      0
                     |      |      |      |      |      |      |
Position Size %:    3.0%    8%    13%    18%    20%    20%    20%
                     |      |      |      |      |      |      |
Stop Loss %:        2.4%   2.7%   3.0%   3.5%   3.8%   4.2%   4.5%
                     |      |      |      |      |      |      |
Risk per $100K:     $72    $216   $390   $630   $760   $840   $900
                     |      |      |      |      |      |      |
    LOW RISK <------------------------------------------------------> HIGH REWARD
    Small Position                                  Large Position
    Tight Stop                                      Wide Stop
```

### Risk vs. Reward Optimization

The score-based stop loss system optimizes the risk-reward profile by intelligently balancing position size against stop loss distance:

1. **Risk Control Strategy**:
   * Higher confidence signals receive both larger positions AND wider stops
   * Lower confidence signals receive both smaller positions AND tighter stops
   * Absolute risk (dollar amount) increases with confidence but at a rate slower than potential reward

2. **Risk-to-Reward Ratios by Confidence Level**:
   * Threshold signals (score = 70 for long, 30 for short): Typically 2:1 to 2.5:1 risk-reward
   * Moderate signals (score = 75-85 for long, 15-25 for short): Typically 2.5:1 to 3:1 risk-reward
   * Strong signals (score = 85-95 for long, 5-15 for short): Typically 3:1 to 5:1 risk-reward
   * Extreme signals (score > 95 for long, < 5 for short): Can exceed 5:1 risk-reward

3. **Maximum Drawdown Protection**:
   * System is designed to limit maximum account drawdown by controlling absolute risk
   * Even at maximum confidence, risk per trade is capped at approximately 0.9% of account value
   * This ensures survival through extended drawdown periods and psychological comfort for traders 