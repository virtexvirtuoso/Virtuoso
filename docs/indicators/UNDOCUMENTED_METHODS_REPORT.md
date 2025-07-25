# Undocumented Methods Report

This report lists all public and important private methods from each indicator module that are not documented in their corresponding .md files in docs/indicators/.

## Summary

After comprehensive analysis of all indicator modules and their documentation, here are the key findings:

### Overall Documentation Status
- **Orderbook Indicators**: Missing 28 methods in documentation
- **Orderflow Indicators**: Missing 23 methods in documentation  
- **Price Structure Indicators**: Missing 70 methods in documentation
- **Sentiment Indicators**: Missing 23 methods in documentation
- **Technical Indicators**: Missing 23 methods in documentation
- **Volume Indicators**: Missing 25 methods in documentation

**Total**: 192 undocumented methods across all indicator modules

## Detailed Analysis by Module

### 1. Orderbook Indicators (orderbook_indicators.py)

**Documented Enhanced Methods:**
- ✅ `_enhanced_oir_transform()`
- ✅ `_enhanced_di_transform()`
- ✅ `_enhanced_liquidity_transform()`
- ✅ `_enhanced_price_impact_transform()`
- ✅ `_enhanced_depth_transform()`
- ❌ `_enhanced_spread_transform()` (mentioned but not found in code)

**Undocumented Methods:**
1. `__init__()` - Constructor
2. `_validate_weights()` - Weight validation
3. `_apply_sigmoid_transformation()` - Sigmoid transformation utility
4. `_update_historical_metrics()` - Historical metric updates
5. `calculate_absorption_exhaustion()` - Absorption/exhaustion calculation
6. `calculate_spread_score()` - Spread score calculation
7. `calculate_slope_score()` - Slope score calculation
8. `calculate_obps()` - Order Book Pressure Score
9. `calculate_dom_momentum()` - Depth of Market momentum
10. `detect_large_aggressive_orders()` - Large order detection
11. `calculate_pressure()` - General pressure calculation
12. `_get_imbalance_ratio()` - Imbalance ratio getter
13. `_get_liquidity_ratio()` - Liquidity ratio getter
14. `_get_price_impact()` - Price impact getter
15. `_calculate_price_impact()` - Price impact calculation
16. `_get_depth_ratio()` - Depth ratio getter
17. `_calculate_sr_from_orderbook()` - Support/resistance from orderbook
18. `_get_sr_strength()` - Support/resistance strength
19. `required_data()` - Required data definition
20. `validate_input()` - Input validation
21. `_validate_base_requirements()` - Base requirement validation
22. `_log_data_quality_metrics()` - Data quality logging
23. `_log_performance_metrics()` - Performance metrics logging
24. `log_indicator_results()` - Result logging
25. `_log_trading_context()` - Trading context logging
26. `_log_component_influence()` - Component influence logging
27. `_log_threshold_alerts()` - Threshold alert logging
28. `_calculate_confidence_level()` - Confidence level calculation
29. `_get_confidence_label()` - Confidence label getter
30. `_calculate_orderbook_depth()` - Orderbook depth calculation
31. `_get_historical_spreads()` - Historical spread getter
32. `_calculate_spread_percentile()` - Spread percentile calculation
33. `_calculate_volatility_context()` - Volatility context calculation
34. `_detect_market_regime()` - Market regime detection

### 2. Orderflow Indicators (orderflow_indicators.py)

**Documented Enhanced Methods:**
- ✅ `_enhanced_cvd_transform()`
- ✅ `_enhanced_trade_flow_transform()`
- ✅ `_enhanced_trades_imbalance_transform()`
- ✅ `_enhanced_trades_pressure_transform()`
- ✅ `_enhanced_liquidity_zones_transform()`
- ❌ `_enhanced_order_block_transform()` (mentioned but not found in this module)

**Undocumented Methods:**
1. `__init__()` - Constructor
2. `required_data()` - Required data definition
3. `_log_intelligent_debug()` - Intelligent debug logging
4. `_log_cache_hit()` - Cache hit logging
5. `_log_performance_summary()` - Performance summary logging
6. `_get_timeframe_display_name()` - Timeframe display name getter
7. `_compute_weighted_score()` - Weighted score computation
8. `log_indicator_results()` - Result logging
9. `validate_input()` - Input validation
10. `_validate_input()` - Internal input validation
11. `_calculate_confidence()` - Confidence calculation
12. `_validate_weights()` - Weight validation
13. `_cached_compute()` - Cached computation utility
14. `_get_processed_trades()` - Processed trades getter
15. `_analyze_cvd_price_relationship()` - CVD-price relationship analysis
16. `_calculate_base_cvd_score()` - Base CVD score calculation
17. `_calculate_trade_flow_score()` - Trade flow score calculation
18. `_get_open_interest_values()` - Open interest values getter
19. `_calculate_open_interest_score()` - Open interest score calculation
20. `_get_price_direction()` - Price direction getter
21. `_get_open_interest_change()` - Open interest change getter
22. `_get_trade_pressure()` - Trade pressure getter
23. `_calculate_price_cvd_divergence()` - Price-CVD divergence calculation
24. `_calculate_price_oi_divergence()` - Price-OI divergence calculation
25. `_calculate_trade_flow()` - Trade flow calculation
26. `_detect_liquidity_zones()` - Liquidity zone detection
27. `_detect_swing_highs_lows()` - Swing high/low detection
28. `_cluster_swing_points()` - Swing point clustering
29. `_create_liquidity_zone()` - Liquidity zone creation
30. `_check_liquidity_sweeps()` - Liquidity sweep checking
31. `_score_liquidity_proximity()` - Liquidity proximity scoring
32. `_apply_divergence_bonuses()` - Divergence bonus application
33. `_analyze_timeframe_divergence()` - Timeframe divergence analysis
34. `_calculate_price_trend()` - Price trend calculation
35. `_detect_timeframe_divergence()` - Timeframe divergence detection
36. `_calculate_zone_proximity()` - Zone proximity calculation
37. `_calculate_sweep_activity()` - Sweep activity calculation
38. `_calculate_zone_strength()` - Zone strength calculation
39. `_log_trading_context()` - Trading context logging
40. `_log_component_influence()` - Component influence logging
41. `_log_threshold_alerts()` - Threshold alert logging
42. `_calculate_confidence_level()` - Confidence level calculation
43. `_get_confidence_label()` - Confidence label getter

### 3. Price Structure Indicators (price_structure_indicators.py)

**Note**: This documentation file appears to be for "Position Indicators" in the first part, then switches to "Price Structure Indicators". This is a documentation inconsistency.

**Documented Enhanced Methods:**
- ✅ `_enhanced_order_blocks_transform()`
- ✅ `_enhanced_trend_position_transform()`
- ✅ `_enhanced_sr_alignment_transform()`
- ❌ `_enhanced_range_position_transform()` (mentioned but not found)

**Undocumented Methods:** (70 methods)
1. `__init__()` - Constructor
2. `_validate_weights()` - Weight validation
3. `_validate_input()` - Input validation
4. `_interpolate_htf_candles()` - HTF candle interpolation
5. `_validate_timeframe_data()` - Timeframe data validation
6. `_validate_dataframe()` - DataFrame validation
7. `_analyze_sr_levels()` - S/R level analysis
8. `_find_sr_levels()` - S/R level finding
9. `_analyze_trend_position()` - Trend position analysis
10. `_calculate_volume_profile_score()` - Volume profile score
11. `_calculate_vwap_score()` - VWAP score calculation
12. `_calculate_composite_value_score()` - Composite value score
13. `_calculate_value_areas()` - Value area calculation
14. `calculate_trend_score()` - Trend score calculation
15. `calculate_support_score()` - Support score calculation
16. `_calculate_dynamic_thresholds()` - Dynamic threshold calculation
17. `_calculate_imbalance_strength()` - Imbalance strength calculation
18. `_calculate_volume_score()` - Volume score calculation
19. `_calculate_momentum_score()` - Momentum score calculation
20. `_calculate_volatility_score()` - Volatility score calculation
21. `_calculate_imbalance_score()` - Imbalance score calculation
22. `_calculate_value_area_score()` - Value area score calculation
23. `_identify_swing_points()` - Swing point identification
24. `_calculate_timeframe_score()` - Timeframe score calculation
25. `_calculate_structural_score()` - Structural score calculation
26. `_calculate_sr_alignment_score()` - S/R alignment score
27. `_calculate_volume_node_score()` - Volume node score
28. `_calculate_short_term_trend()` - Short-term trend calculation
29. `_calculate_weighted_score()` - Weighted score calculation
30. `_calculate_volume_profile()` - Volume profile calculation
31. `_calculate_composite_value()` - Composite value calculation
32. `_calculate_sr_levels()` - S/R level calculation
33. `_calculate_level_alignment()` - Level alignment calculation
34. `_calculate_price_position()` - Price position calculation
35. `_identify_price_clusters()` - Price cluster identification
36. `_calculate_alignment_score()` - Alignment score calculation
37. `_calculate_value_area()` - Value area calculation
38. `_interpret_timeframe_score()` - Timeframe score interpretation
39. `_get_position_interpretation()` - Position interpretation
40. `_calculate_confidence()` - Confidence calculation
41. `_calculate_price_volume_correlation()` - Price-volume correlation
42. `_analyze_market_structure()` - Market structure analysis
43. `_calculate_order_blocks_score()` - Order blocks score
44. `_calculate_trend_position_score()` - Trend position score
45. `_analyze_orderblock_zones()` - Order block zone analysis
46. `_find_bullish_order_blocks()` - Bullish order block finding
47. `_find_bearish_order_blocks()` - Bearish order block finding
48. `_calculate_order_block_proximity()` - Order block proximity
49. `_get_default_scores()` - Default scores getter
50. `_calculate_level_proximity()` - Level proximity calculation
51. `_analyze_volume()` - Volume analysis
52. `_calculate_order_blocks()` - Order blocks calculation
53. `_interpret_component_score()` - Component score interpretation
54. `_compute_weighted_score()` - Weighted score computation
55. `log_indicator_results()` - Result logging
56. `_verify_score_not_default()` - Score verification
57. `_identify_range()` - Range identification
58. `_detect_sweep_deviation()` - Sweep deviation detection
59. `_detect_msb()` - Market structure break detection
60. `_analyze_range_position()` - Range position analysis
61. `_analyze_range()` - Range analysis
62. `_calculate_single_vwap_score()` - Single VWAP score
63. `_log_component_specific_alerts()` - Component alert logging
64. `_calculate_support_strength()` - Support strength calculation
65. `_calculate_resistance_strength()` - Resistance strength calculation
66. `_identify_support_levels()` - Support level identification
67. `_identify_resistance_levels()` - Resistance level identification
68. `_calculate_level_strength()` - Level strength calculation
69. `_detect_fair_value_gaps()` - FVG detection
70. `_detect_liquidity_sweeps()` - Liquidity sweep detection
71. `_get_mtf_confirmation()` - MTF confirmation getter
72. `_check_block_mitigation()` - Block mitigation checking
73. `_cluster_order_blocks()` - Order block clustering
74. `_cluster_blocks_by_type()` - Block clustering by type
75. `_consolidate_cluster()` - Cluster consolidation
76. `_calculate_enhanced_block_strength()` - Enhanced block strength
77. `_identify_order_blocks()` - Order block identification
78. `_validate_bullish_block()` - Bullish block validation
79. `_validate_bearish_block()` - Bearish block validation
80. `_detect_market_regime()` - Market regime detection
81. `_calculate_volatility_context()` - Volatility context calculation

### 4. Sentiment Indicators (sentiment_indicators.py)

**Documented Enhanced Methods:**
- ✅ `_enhanced_funding_transform()`
- ✅ `_enhanced_lsr_transform()`
- ✅ `_enhanced_liquidation_transform()`
- ✅ `_enhanced_volatility_transform()`
- ✅ `_enhanced_open_interest_transform()`
- ❌ `_enhanced_market_mood_transform()` (mentioned but not found)

**Undocumented Methods:**
1. `__init__()` - Constructor
2. `_validate_weights()` - Weight validation
3. `calculate_long_short_ratio()` - LSR calculation
4. `calculate_funding_rate()` - Funding rate calculation
5. `calculate_funding_rate_volatility()` - Funding rate volatility
6. `calculate_liquidation_events()` - Liquidation event calculation
7. `calculate_volume_sentiment()` - Volume sentiment calculation
8. `_adjust_volume_score()` - Volume score adjustment
9. `_calculate_funding_score()` - Funding score calculation
10. `calculate_market_mood()` - Market mood calculation
11. `_calculate_risk_score()` - Risk score calculation
12. `_calculate_volatility_score()` - Volatility score calculation
13. `calculate_historical_volatility()` - Historical volatility
14. `_prepare_risk_data()` - Risk data preparation
15. `_process_sentiment_data()` - Sentiment data processing
16. `_apply_sigmoid_transformation()` - Sigmoid transformation
17. `_log_component_breakdown()` - Component breakdown logging
18. `_get_component_interpretation()` - Component interpretation
19. `_get_detailed_sentiment_interpretation()` - Detailed interpretation
20. `_get_default_scores()` - Default scores getter
21. `validate_input()` - Input validation
22. `required_data()` - Required data definition
23. `reset_cache()` - Cache reset
24. `_calculate_sync()` - Synchronous calculation
25. `calculate()` - Main calculation method
26. `_get_signals_sync()` - Synchronous signal getter
27. `_combine_similar_signals()` - Signal combination
28. `_get_volume_sentiment_ratio()` - Volume sentiment ratio
29. `_compute_weighted_score()` - Weighted score computation
30. `_calculate_enhanced_metrics()` - Enhanced metrics calculation
31. `_calculate_liquidation_score()` - Liquidation score
32. `_calculate_market_mood()` - Market mood calculation
33. `_safe_get()` - Safe data getter
34. `_calculate_lsr_score()` - LSR score calculation
35. `_calculate_open_interest_score()` - OI score calculation
36. `_interpret_sentiment()` - Sentiment interpretation
37. `_generate_signals()` - Signal generation
38. `_calculate_market_activity()` - Market activity calculation
39. `_log_component_specific_alerts()` - Component alert logging
40. `_assess_market_sentiment()` - Market sentiment assessment
41. `_get_historical_lsr()` - Historical LSR getter
42. `_calculate_percentile()` - Percentile calculation
43. `_calculate_enhanced_funding_score()` - Enhanced funding score
44. `_calculate_enhanced_lsr_score()` - Enhanced LSR score
45. `_calculate_enhanced_liquidation_score()` - Enhanced liquidation score
46. `_calculate_enhanced_volatility_score()` - Enhanced volatility score
47. `_calculate_enhanced_open_interest_score()` - Enhanced OI score
48. `_calculate_volatility_context()` - Volatility context
49. `_detect_market_regime()` - Market regime detection

### 5. Technical Indicators (technical_indicators.py)

**Documented Enhanced Methods:**
- ✅ `_enhanced_rsi_transform()`
- ✅ `_enhanced_macd_transform()`
- ✅ `_enhanced_ao_transform()`
- ✅ `_enhanced_williams_r_transform()`
- ✅ `_enhanced_cci_transform()`

**Undocumented Methods:**
1. `__init__()` - Constructor
2. `_determine_optimization_level()` - Optimization level determination
3. `_calculate_rsi_optimized()` - Optimized RSI calculation
4. `_calculate_rsi_pandas()` - Pandas RSI calculation
5. `_calculate_macd_optimized()` - Optimized MACD calculation
6. `_calculate_macd_pandas()` - Pandas MACD calculation
7. `_calculate_williams_r_optimized()` - Optimized Williams %R
8. `_calculate_williams_r_pandas()` - Pandas Williams %R
9. `_calculate_atr_optimized()` - Optimized ATR calculation
10. `_calculate_atr_pandas()` - Pandas ATR calculation
11. `_calculate_cci_optimized()` - Optimized CCI calculation
12. `_calculate_cci_pandas()` - Pandas CCI calculation
13. `_calculate_sma_optimized()` - Optimized SMA calculation
14. `_calculate_sma_pandas()` - Pandas SMA calculation
15. `_calculate_medprice_optimized()` - Optimized median price
16. `_calculate_medprice_pandas()` - Pandas median price
17. `_calculate_adx_optimized()` - Optimized ADX calculation
18. `_calculate_adx_pandas()` - Pandas ADX calculation
19. `get_performance_report()` - Performance report getter
20. `calculate_enhanced_macd()` - Enhanced MACD calculation
21. `calculate_all_moving_averages()` - All MA calculation
22. `calculate_momentum_suite()` - Momentum suite calculation
23. `calculate_math_functions()` - Math functions calculation
24. `required_data()` - Required data definition
25. `_analyze_timeframe_divergences()` - Timeframe divergence analysis
26. `_calculate_component_scores()` - Component score calculation
27. `_calculate_rsi_score()` - RSI score calculation
28. `_calculate_atr_score()` - ATR score calculation
29. `_calculate_cci_score()` - CCI score calculation
30. `_calculate_rsi_divergence()` - RSI divergence calculation
31. `_calculate_ao_divergence()` - AO divergence calculation
32. `_apply_divergence_adjustments()` - Divergence adjustment application
33. `_validate_input()` - Input validation
34. `_calculate_indicator_values()` - Indicator value calculation
35. `_visualize_timeframe_divergence()` - Timeframe divergence visualization
36. `_log_component_specific_alerts()` - Component alert logging
37. `_calculate_volatility_context()` - Volatility context calculation
38. `_log_trading_context()` - Trading context logging
39. `_log_component_influence()` - Component influence logging
40. `_log_threshold_alerts()` - Threshold alert logging
41. `_calculate_confidence_level()` - Confidence level calculation
42. `_get_confidence_label()` - Confidence label getter

### 6. Volume Indicators (volume_indicators.py)

**Documented Enhanced Methods:**
- ✅ `_enhanced_adl_transform()`
- ✅ `_enhanced_cmf_transform()`
- ✅ `_enhanced_obv_transform()`
- ✅ `_enhanced_volume_trend_transform()`
- ✅ `_enhanced_volume_volatility_transform()`
- ✅ `_enhanced_relative_volume_transform()`
- ❌ `_enhanced_volume_profile_transform()` (mentioned but not found)
- ❌ `_enhanced_volume_delta_transform()` (mentioned but not found)

**Undocumented Methods:**
1. `__init__()` - Constructor
2. `validate_input()` - Input validation
3. `_generate_rvol_signal()` - RVOL signal generation
4. `_calculate_confidence()` - Confidence calculation
5. `_calculate_volume_sma_score()` - Volume SMA score
6. `_calculate_volume_trend_score()` - Volume trend score
7. `_calculate_volume_volatility()` - Volume volatility
8. `normalize_volume()` - Volume normalization
9. `calculate_historical_average()` - Historical average calculation
10. `_normalize_value()` - Value normalization
11. `_compute_weighted_score()` - Weighted score computation
12. `_calculate_volume_indicators()` - Volume indicator calculation
13. `calculate_obv()` - OBV calculation
14. `calculate_adx()` - ADX calculation
15. `_calculate_volume_divergence_bonus()` - Volume divergence bonus
16. `required_data()` - Required data definition
17. `_calculate_vwap_score()` - VWAP score calculation
18. `_calculate_single_vwap_score()` - Single VWAP score
19. `_verify_score_not_default()` - Score verification
20. `_calculate_volume_profile_score()` - Volume profile score
21. `calculate_volume_delta()` - Volume delta calculation
22. `calculate_adl()` - ADL calculation
23. `_calculate_base_volume_score()` - Base volume score
24. `_calculate_cmf_score()` - CMF score calculation
25. `_get_cmf_value()` - CMF value getter
26. `_calculate_obv_score()` - OBV score calculation
27. `_calculate_volume_delta()` - Volume delta calculation
28. `_get_raw_volume_delta()` - Raw volume delta getter
29. `_validate_weights()` - Weight validation
30. `_get_default_scores()` - Default scores getter
31. `_get_obv_trend()` - OBV trend getter
32. `_get_relative_volume_ratio()` - Relative volume ratio
33. `_calculate_price_aware_relative_volume()` - Price-aware RVOL
34. `_calculate_directional_volume_score()` - Directional volume score
35. `_log_component_specific_alerts()` - Component alert logging
36. `_detect_price_trend()` - Price trend detection
37. `_calculate_enhanced_volume_trend_score()` - Enhanced volume trend
38. `_calculate_enhanced_volume_volatility_score()` - Enhanced volatility
39. `_calculate_enhanced_relative_volume_score()` - Enhanced RVOL
40. `_calculate_relative_volume()` - Relative volume calculation
41. `_detect_market_regime()` - Market regime detection
42. `_calculate_volatility_context()` - Volatility context
43. `_calculate_price_trend()` - Price trend calculation
44. `_calculate_volume_trend()` - Volume trend calculation
45. `calculate_relative_volume()` - Relative volume calculation
46. `_calculate_adl_score()` - ADL score calculation
47. `_get_adl_trend()` - ADL trend getter
48. `_apply_divergence_bonuses()` - Divergence bonus application
49. `_log_trading_context()` - Trading context logging
50. `_log_component_influence()` - Component influence logging
51. `_log_threshold_alerts()` - Threshold alert logging
52. `_calculate_confidence_level()` - Confidence level calculation
53. `_get_confidence_label()` - Confidence label getter

## Recommendations

1. **Priority Documentation Areas:**
   - Price Structure Indicators has the most undocumented methods (70)
   - Focus on documenting core calculation methods first
   - Document enhanced scoring methods that are missing

2. **Documentation Consistency:**
   - Fix the Price Structure documentation that starts as "Position Indicators"
   - Ensure all enhanced methods mentioned in docs actually exist in code
   - Add missing enhanced methods to documentation

3. **Method Organization:**
   - Consider grouping similar methods in documentation
   - Add sections for utility methods, logging methods, and validation methods
   - Create a standard template for documenting private methods

4. **Missing Enhanced Methods to Implement:**
   - `_enhanced_spread_transform()` for orderbook indicators
   - `_enhanced_order_block_transform()` for orderflow indicators
   - `_enhanced_range_position_transform()` for price structure
   - `_enhanced_market_mood_transform()` for sentiment indicators
   - `_enhanced_volume_profile_transform()` for volume indicators
   - `_enhanced_volume_delta_transform()` for volume indicators

5. **Documentation Structure Improvements:**
   - Add a "Utility Methods" section for helper functions
   - Add a "Logging and Debugging" section for diagnostic methods
   - Add an "Internal Methods" section for important private methods
   - Create API reference documentation for all public methods