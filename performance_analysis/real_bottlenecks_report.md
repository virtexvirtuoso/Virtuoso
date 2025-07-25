# Real Performance Bottlenecks Report

Found 598 real performance issues

## Priority Summary
- 🔴 High Priority: 383 (fix these first!)
- 🟡 Medium Priority: 215

## Issues by Category
- nested_loop: 286
- calculation_bottleneck: 211
- loop_bottleneck: 46
- blocking_in_async: 37
- pandas_bottleneck: 14
- memory_bottleneck: 4

## 🔴 High Priority Issues (Fix These First!)

### resource_manager.py

**Line 250** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `process = psutil.Process()`

### system.py

**Line 139** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `cpu_times = psutil.cpu_times()`

**Line 140** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `cpu_freq = psutil.cpu_freq()`

**Line 141** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `cpu_stats = psutil.cpu_stats()`

**Line 144** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `memory = psutil.virtual_memory()`

**Line 145** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `swap = psutil.swap_memory()`

**Line 148** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `disk_io = psutil.disk_io_counters()`

**Line 151** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `net_io = psutil.net_io_counters()`

**Line 155** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `'percent': psutil.cpu_percent(interval=1),`

### binance_monitor.py

**Line 159** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `memory_info = psutil.virtual_memory()`

**Line 160** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `cpu_percent = psutil.cpu_percent(interval=1)`

### resource_manager.py

**Line 127** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `memory_percent=psutil.virtual_memory().percent,`

**Line 128** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `cpu_percent=psutil.cpu_percent(),`

### resource_monitor.py

**Line 40** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `memory_task = loop.run_in_executor(None, lambda: psutil.virtual_memory().percent)`

**Line 41** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `cpu_task = loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=1))`

**Line 81** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `mem_task = loop.run_in_executor(None, lambda: psutil.virtual_memory().percent)`

**Line 82** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `cpu_task = loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=1))`

### main.py

**Line 2228** - blocking_in_async
- Issue: Blocking subprocess call
- Code: `result = subprocess.run(['lsof', '-i', f':{port}'], capture_output=True, text=True)`

**Line 2240** - blocking_in_async
- Issue: Blocking subprocess call
- Code: `subprocess.run(['kill', '-9', pid], check=True)`

### metrics_manager.py

**Line 358** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `cpu_percent = psutil.cpu_percent(interval=1)`

**Line 359** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `cpu_times = psutil.cpu_times_percent()`

**Line 360** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `memory = psutil.virtual_memory()`

**Line 361** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `disk = psutil.disk_usage('/')`

### monitor.py

**Line 3330** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `memory = psutil.virtual_memory()`

**Line 3342** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `cpu_percent = psutil.cpu_percent(interval=1)`

### monitor_original.py

**Line 2531** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `memory = psutil.virtual_memory()`

**Line 2543** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `cpu_percent = psutil.cpu_percent(interval=1)`

**Line 5777** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `memory = psutil.virtual_memory()`

**Line 5789** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `cpu_percent = psutil.cpu_percent(interval=1)`

### run_diagnostics.py

**Line 230** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `cpu_percent = psutil.cpu_percent(interval=None)`

**Line 231** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `memory = psutil.virtual_memory()`

**Line 237** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `process = psutil.Process(self.process_pid)`

**Line 243** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `except (psutil.NoSuchProcess, psutil.AccessDenied):`

### performance.py

**Line 127** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `start_memory = psutil.Process().memory_info().rss`

**Line 128** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `start_cpu = psutil.Process().cpu_percent()`

**Line 136** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `memory_used = psutil.Process().memory_info().rss - start_memory`

**Line 137** - blocking_in_async
- Issue: Blocking psutil operations
- Code: `cpu_used = psutil.Process().cpu_percent() - start_cpu`

### correlation.py

**Line 328** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `scores = [data["score"] for data in matrix_data[symbol].values() if isinstance(data, dict)]`

**Line 473** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `scores = [data["score"] for data in matrix_data[symbol].values() if isinstance(data, dict)]`

### market.py

**Line 976** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `buy_signals = sum(1 for comp in components.values() if isinstance(comp, dict) and comp.get("score", 50) > 60)`

**Line 977** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `sell_signals = sum(1 for comp in components.values() if isinstance(comp, dict) and comp.get("score", 50) < 40)`

**Line 1002** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `"data_quality": len([c for c in components.values() if isinstance(c, dict) and c.get("score") is not None]) / max(len(components), 1) * 100`

### signal_tracking.py

**Line 232** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `active_buy_signals = sum(1 for s in active_signals.values() if s['action'] == 'BUY')`

**Line 233** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `active_sell_signals = sum(1 for s in active_signals.values() if s['action'] == 'SELL')`

### feature_flags.py

**Line 285** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `deprecated_count = len([f for f in self.flags.values() if f.deprecated])`

**Line 292** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `'enabled': len([f for f in category_flags.values() if f.enabled]),`

**Line 293** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `'experimental': len([f for f in category_flags.values() if f.experimental])`

### confluence.py

**Line 1480** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `valid_scores = sum(1 for score in scores.values() if score != 50.0)`

**Line 1495** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for indicator_type in self.indicators.keys():`

**Line 2598** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `valid_scores = sum(1 for score in scores.values() if score != 50.0)`

### interpretation_generator.py

**Line 1242** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `values = [v for v in component_dict.values() if isinstance(v, (int, float))]`

### interpretation_manager.py

**Line 1737** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `'overall_bias': sum(data['bias'] * data['impact'] for data in component_data.values()) / total_impact if total_impact > 0 else 0`

### market_data_manager.py

**Line 371** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for tf in refresh_intervals['kline'].keys():`

**Line 841** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for tf_name in timeframe_intervals.keys():`

### binance_exchange.py

**Line 670** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `'spot_markets': len([m for m in markets.values() if m.get('spot', False)]),`

**Line 671** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `'futures_markets': len([m for m in markets.values() if m.get('future', False)]),`

### data_processor.py

**Line 333** - loop_bottleneck
- Issue: While loop with len() - consider for loop
- Code: `while len(self._reorder_buffers[symbol]) > self._reorder_buffer_size:`

### sentiment_indicators_backup.py

**Line 1328** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for component in self.component_weights.keys():`

### base_indicator.py

**Line 491** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for key in ohlcv_data.keys():`

### price_structure_indicators.py

**Line 1357** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `alignment_count = sum(1 for d in distances.values() if d < 0.001)  # 0.1% threshold`

**Line 2912** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for tf in self.timeframe_weights.keys():`

### sentiment_indicators.py

**Line 637** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for key in sentiment_data.keys():`

### technical_indicators.py

**Line 254** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `valid_scores = [val for val in adjusted_component_scores.values() if not pd.isna(val)]`

### alert_manager.py

**Line 4631** - loop_bottleneck
- Issue: While loop with len() - consider for loop
- Code: `while payload_size > 5000 and len(payload["embeds"][0]["fields"]) > 3:`

### market_reporter.py

**Line 1120** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for key in report_data.keys():`

**Line 2786** - loop_bottleneck
- Issue: Large range loop
- Code: `first_lines = [next(f) for _ in range(10)]`

**Line 3637** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for existing_price in price_groups.keys():`

### market_reporter_enhanced_test.py

**Line 944** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for key in report_data.keys():`

**Line 3486** - loop_bottleneck
- Issue: Large range loop
- Code: `first_lines = [next(f) for _ in range(10)]`

### metrics_manager.py

**Line 389** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for operation in self._metrics[component].keys():`

**Line 414** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for metric_name in self._metrics['system'].keys():`

### bitcoin_beta_7day_report.py

**Line 764** - loop_bottleneck
- Issue: Large range loop
- Code: `for attempt in range(3):`

**Line 851** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for tf_name in self.timeframes.keys():`

**Line 866** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for symbol in market_data.keys():`

**Line 1172** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for symbol in market_data.keys():`

**Line 1907** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for symbol in market_data.keys():`

### bitcoin_beta_report.py

**Line 677** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for tf_name in self.timeframes.keys():`

**Line 692** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for symbol in market_data.keys():`

**Line 918** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for symbol in market_data.keys():`

**Line 1614** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for symbol in market_data.keys():`

### signal_generator.py

**Line 1379** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `component_scores = [score for score in components.values() if isinstance(score, (int, float))]`

**Line 1611** - loop_bottleneck
- Issue: Iterating over .keys() - iterate directly
- Code: `for component_name in components.keys():`

**Line 1629** - loop_bottleneck
- Issue: Filter in loop - use dict comprehension
- Code: `sub_component_count = len([s for s in sub_components.values() if isinstance(s, (int, float))])`

### dataframe_utils.py

**Line 23** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for column in result.select_dtypes(include=['int']).columns: ... for dtype in DataFrameOptimizer.INT_TYPES:`

### validation.py

**Line 302** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for rule in self._rules[data_type]: ... for error in errors:`

### correlation.py

**Line 97** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in symbols: ... for file_path in symbol_files[:periods]:`

**Line 125** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for signal in signal_data: ... for signal_type in SIGNAL_TYPES:`

**Line 156** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, signal1 in enumerate(signal_cols): ... for j, signal2 in enumerate(signal_cols):`

**Line 172** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for signal in signal_data: ... for signal_type in SIGNAL_TYPES:`

**Line 181** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, signals in symbol_signals.items(): ... for signal_type in SIGNAL_TYPES:`

**Line 183** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for signal_type in SIGNAL_TYPES: ... for signal in signals:`

**Line 210** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, symbol1 in enumerate(symbols): ... for j, symbol2 in enumerate(symbols):`

**Line 263** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in symbols_list: ... for signal in signals_data:`

**Line 268** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for signal in signals_data: ... for signal_type in SIGNAL_TYPES:`

**Line 341** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in symbols_list: ... for signal_type in SIGNAL_TYPES:`

**Line 408** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in symbols_list: ... for signal in signals_data:`

**Line 413** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for signal in signals_data: ... for signal_type in SIGNAL_TYPES:`

**Line 486** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in symbols_list: ... for signal_type in SIGNAL_TYPES:`

**Line 602** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, label1 in enumerate(labels): ... for j, label2 in enumerate(labels):`

### test_api_endpoints.py

**Line 72** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for pattern in patterns: ... for match in re.finditer(pattern, content):`

**Line 110** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for file in sorted(route_files): ... for route in routes:`

**Line 135** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for module, routes in sorted(routes_by_module.items()): ... for route in sorted(routes, key=lambda x: (x['method'], x['path'])):`

**Line 156** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for module in sorted(registered_modules & route_modules): ... for module in sorted(unregistered):`

### test_api_endpoints_simple.py

**Line 80** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for file in route_files: ... for route in routes:`

**Line 94** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for file, routes in sorted(routes_by_file.items()): ... for route in routes:`

**Line 138** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for module, expected_paths in expected_patterns.items(): ... for path in expected_paths:`

**Line 147** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for path in expected_paths: ... for path in extra_routes:`

### test_api_endpoints_summary.py

**Line 86** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for file in sorted(route_files): ... for route in routes:`

**Line 141** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for method, path, desc in core_routes: ... for route in sorted(routes, key=lambda x: (x['method'], x['path'])):`

**Line 149** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for module, routes in sorted(routes_by_module.items()): ... for route in sorted(routes, key=lambda x: (x['method'], x['path'])):`

### trading.py

**Line 177** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for exchange_id, exchange in exchange_manager.exchanges.items(): ... for order in orders:`

**Line 202** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for exchange_id, exchange in exchange_manager.exchanges.items(): ... for pos in positions:`

### whale_activity.py

**Line 190** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, sym in enumerate(symbols): ... for j in range(limit // len(symbols)):`

### handler.py

**Line 91** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for client_id in client_ids: ... for websocket in self.active_connections[client_id]:`

### feature_flags.py

**Line 97** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for category_name, category_flags in self.feature_flags_config.items(): ... for flag_name, flag_enabled in category_flags.items():`

**Line 318** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for category in self.categories: ... for flag_name, flag in category_flags.items():`

### manager.py

**Line 188** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for section, subsections in required_sections.items(): ... for subsection in subsections:`

### validator.py

**Line 273** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for config_path in config_locations: ... for match in matches:`

### alpha_scanner.py

**Line 98** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for exchange_id in scan_exchanges: ... for symbol in scan_symbols:`

### confluence.py

**Line 337** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for component_name, component_result in results.items(): ... for sub_name, sub_score in sub_components.items():`

**Line 967** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf in ['base', 'ltf', 'mtf', 'htf']: ... for named_tf, interval_value in indicator.timeframe_map.items():`

**Line 1033** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf in required_timeframes: ... for col in required_columns:`

**Line 1096** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for missing_tf in missing_after_direct: ... for avail_tf, mapped_tf in available_to_required.items():`

**Line 1100** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for avail_tf, mapped_tf in available_to_required.items(): ... for avail_tf in available_timeframes:`

**Line 1673** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf, data in standardized.items(): ... for missing_tf in missing:`

**Line 2085** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf in ['base', 'ltf', 'mtf', 'htf']: ... for named_tf, interval_value in indicator.timeframe_map.items():`

**Line 2151** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf in required_timeframes: ... for col in required_columns:`

**Line 2214** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for missing_tf in missing_after_direct: ... for avail_tf, mapped_tf in available_to_required.items():`

**Line 2218** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for avail_tf, mapped_tf in available_to_required.items(): ... for avail_tf in available_timeframes:`

**Line 2772** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf, data in standardized.items(): ... for missing_tf in missing:`

**Line 3091** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i1 in scores: ... for i2 in scores:`

**Line 3213** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for name, result in results.items(): ... for tf in ['base', 'ltf', 'mtf', 'htf']:`

**Line 3262** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for key1, value1 in metrics_dict.items(): ... for key2, value2 in metrics_dict.items():`

**Line 3698** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for req_field in required_fields: ... if not any(alt in trade_fields for alt in alternatives):`

**Line 4371** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for trade in trades_data: ... for price_field in ['price', 'p', 'trade_price', 'last_price', 'lastPrice']:`

### indicator_utils.py

**Line 160** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf, scores in timeframe_scores.items(): ... for component, score in scores.items():`

### liquidation_detector.py

**Line 96** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for exchange_id in target_exchanges: ... for symbol in symbols:`

**Line 145** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for exchange_id in target_exchanges: ... for symbol in symbols:`

**Line 348** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in symbols: ... for exchange_id in (exchanges or list(self.exchange_manager.exchanges.keys())):`

**Line 820** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in symbols: ... for exchange in exchanges:`

**Line 821** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for exchange in exchanges: ... for exchange in exchanges:`

**Line 830** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in symbols: ... for exchange in exchanges:`

### portfolio.py

**Line 83** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for asset, target in self.target_allocation.items(): ... for asset, data in balance.items():`

### config_manager.py

**Line 214** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for section, subsections in required_sections.items(): ... for subsection in subsections:`

**Line 253** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for exchange_id, exchange_config in exchanges.items(): ... for field in recommended_fields:`

### base.py

**Line 456** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for attempt in range(self.options['ws']['reconnect_attempts']): ... for channel, symbols in getattr(self, '_ws_subscriptions', {}).items():`

**Line 544** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for data_type, fields in core_fields.items(): ... for item in data:`

### bybit.py

**Line 1018** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for attempt in range(max_attempts): ... for topic in previous_subscriptions:`

**Line 2758** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for bybit_interval, tf_name in timeframes.items(): ... for attempt in range(max_retries):`

**Line 3184** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for trade in trades: ... if all(k in trade for k in ['execId', 'price', 'size', 'side', 'time']):`

### exchange_mappings.py

**Line 239** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for trade in trades: ... for exchange_field, ccxt_field in mappings.items():`

**Line 294** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for field in numeric_fields: ... for exchange_field, ccxt_field in mappings.items():`

**Line 310** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for candle in ohlcv: ... for exchange_field, ccxt_field in mappings.items():`

### liquidation_collector.py

**Line 111** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in symbols: ... for liq_data in liquidations:`

**Line 141** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in symbols: ... for liq in liquidations:`

**Line 176** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in symbols: ... for liq in liquidations.get('data', []):`

### websocket_manager.py

**Line 404** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for task in tasks: ... for task in pending:`

**Line 409** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for task in list(self.reconnect_tasks): ... for task in pending:`

### formatting.py

**Line 265** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for comp_key, details in detailed_components.items(): ... for indicator, value in sorted_details:`

**Line 488** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for component_name, component_data in results.items(): ... for component_name, component_data in results.items():`

**Line 498** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for component_name, component_data in results.items(): ... for sub_name, sub_score in sorted_subcomponents:`

**Line 531** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for component_name, component_data in results.items(): ... for component_name, component_data in results.items():`

### formatter.py

**Line 986** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for indicator_name, indicator_data in results.items(): ... for comp_name, comp_score in indicator_data['components'].items():`

**Line 1363** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for interpretation in interpretation_set.interpretations: ... for subsequent_line in wrapped_lines[1:]:`

**Line 1469** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for insight in cross_insights: ... for subsequent_line in wrapped_lines[1:]:`

**Line 1512** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for insight in actionable_insights: ... for subsequent_line in wrapped_lines[1:]:`

**Line 1845** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for insight in insights: ... for comp_name, comp_score in top_influential['components'].items():`

**Line 1861** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for comp_name, comp_score in top_influential['components'].items(): ... for sub_name, sub_score in sub_components.items():`

**Line 1868** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for component_name, component_data in results.items(): ... for sub_name, sub_score in sub_components.items():`

**Line 2299** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for interp_data in market_interpretations: ... for subsequent_line in wrapped_lines[1:]:`

**Line 2378** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for interpretation in interpretation_set.interpretations: ... for subsequent_line in wrapped_lines[1:]:`

**Line 2437** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for component_name, component_data in results.items(): ... for sub_name, sub_data in sub_components.items():`

**Line 2793** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for section_type, content in sections: ... for item in driver_items:`

### interpretation_manager.py

**Line 740** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for interp in interpretations: ... if any(word in text_lower for word in ['bullish', 'buy', 'long', 'positive', 'strength']):`

**Line 1025** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for interpretation in interpretation_set.interpretations: ... for interpretation in interpretations:`

**Line 1032** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for component_type, interpretations in grouped_interpretations.items(): ... for interpretation in interpretations:`

**Line 1221** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for interpretation in interpretation_set.interpretations: ... if any(word in text_lower for word in ['bullish', 'buy', 'long', 'positive', 'strength']):`

**Line 1709** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, comp1 in enumerate(components): ... for comp2 in components[i+1:]:`

### data_manager.py

**Line 32** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_name, tf_config in config['timeframes'].items(): ... for tf in self.timeframes.values():`

**Line 73** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for category, tf_config in timeframes_config.items(): ... for tf in self.timeframe_weights:`

### market_data_manager.py

**Line 1665** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf in ['base', 'ltf', 'mtf', 'htf']: ... for key in possible_keys:`

**Line 1765** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in self.symbols: ... for component, timestamp in last_refresh['components'].items():`

**Line 1800** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for batch_idx, symbol_batch in enumerate(symbol_batches): ... for symbol in symbol_batch:`

### top_symbols.py

**Line 498** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for entry in market_data: ... for field in required_fields:`

**Line 689** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for field in volume_field_names: ... for field in volume_field_names + ['volume24', 'vol24h']:`

**Line 716** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for field in turnover_field_names: ... for field in turnover_field_names + ['turnover24h', 'notional_24h']:`

**Line 754** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for field in oi_field_names: ... for field in oi_field_names + ['openInterest24h']:`

### export_manager.py

**Line 180** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for fmt, directory in dirs_to_scan: ... for filename in os.listdir(directory):`

### interactive_web_report.py

**Line 217** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for category in ["gainers", "losers"]: ... for item in performers[category]:`

### pdf_generator.py

**Line 946** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for key, value in components.items(): ... for k, v in value.items():`

**Line 2873** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i in range(1, len(data)): ... elif any(char.isdigit() for char in change_text):`

**Line 3296** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for category, items in performers.items(): ... for item in items:`

**Line 5197** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, contracts in quarterly_futures.items(): ... for contract in sorted_contracts:`

**Line 5207** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for contract in sorted_contracts: ... for x, y in zip(months_to_expiry, basis_values):`

### report_manager.py

**Line 289** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, file_path in enumerate(files): ... for i, (orig_index, file_path) in enumerate(valid_files):`

### service_container.py

**Line 116** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for service_name in self._services: ... for service_name in self._initialization_order:`

### validators.py

**Line 153** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for field in required_fields: ... for order in orders:`

**Line 165** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for side in ['bids', 'asks']: ... for order in orders:`

### bybit_data_fetcher.py

**Line 60** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for result in results: ... for key, value in result.items():`

### websocket_handler.py

**Line 206** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in symbols: ... for timeframe in self.timeframes:`

### data_manager.py

**Line 173** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for key in ['trades', 'momentum.trades', 'volume.trades', 'position.trades', 'sentiment.trades']: ... for part in parts[:-1]:`

**Line 235** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in symbols: ... for tf in timeframes:`

### data_processor.py

**Line 67** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for timeframe, tf_data in ohlcv_data.items(): ... for col in ['open', 'high', 'low', 'close', 'volume']:`

**Line 1148** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for timeframe, data in ohlcv_data.items(): ... for col in ['open', 'high', 'low', 'close', 'volume']:`

### storage_manager.py

**Line 296** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for format in StorageFormat: ... for compression in CompressionType:`

### database.py

**Line 210** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for key, value in analysis.items(): ... for sub_key, sub_value in value.items():`

**Line 226** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, signal in enumerate(signals): ... for key, value in signal.items():`

**Line 308** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for index, row in df.iterrows(): ... for column in df.columns:`

**Line 494** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for index, row in df.iterrows(): ... for column in df.columns:`

### demo_trading_runner.py

**Line 261** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in ws_symbols: ... if any(m['symbol'] == symbol for m in markets):`

**Line 270** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in top_symbols: ... if any(m['symbol'] == symbol for m in markets):`

### fix_pdf_alerts_comprehensive.py

**Line 186** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for pdf_dir in pdf_directories: ... for file in os.listdir(pdf_dir):`

**Line 282** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for pdf_dir in pdf_dirs: ... for file in os.listdir(pdf_dir):`

### sentiment_indicators_backup.py

**Line 201** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for item in funding_history: ... for r in rates_list:`

### base_indicator.py

**Line 597** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf in ['ltf', 'mtf', 'htf']: ... for component in self.component_weights:`

**Line 1315** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf, scores in timeframe_scores.items(): ... for component, score in scores.items():`

### orderflow_indicators.py

**Line 222** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for component, count in self._debug_stats['calculation_counts'].items(): ... for scenario, count in self._debug_stats['scenario_counts'].items():`

**Line 703** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for req_field in required_trade_fields: ... if not any(alt in trade for alt in alternatives):`

**Line 1875** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for std_col, possible_cols in column_mappings.items(): ... for col in possible_cols:`

**Line 2271** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf in ['base', 'ltf', '1', '5']: ... for tf in ['base_direct', 'ltf_direct', '1_direct', '5_direct']:`

**Line 2580** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for j in range(0, first_non_zero_idx): ... for j in range(start_idx + 1, end_idx):`

**Line 2585** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for idx_pos in range(len(non_zero_indices) - 1): ... for j in range(start_idx + 1, end_idx):`

**Line 2804** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf in ['base', 'ltf', '1', '5']: ... for tf in ['base_direct', 'ltf_direct', '1_direct', '5_direct']:`

**Line 3219** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for std_col, possible_cols in column_mappings.items(): ... for col in possible_cols:`

**Line 3451** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i in range(swing_length, len(df) - swing_length): ... for j in range(i - swing_length, i + swing_length + 1):`

**Line 3533** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for zone in liquidity_zones['bullish']: ... for i in range(start_idx, len(df)):`

**Line 3538** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i in range(start_idx, len(df)): ... for j in range(i + 1, min(i + 10, len(df))):`

**Line 3551** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for zone in liquidity_zones['bearish']: ... for i in range(start_idx, len(df)):`

**Line 3556** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i in range(start_idx, len(df)): ... for j in range(i + 1, min(i + 10, len(df))):`

**Line 3685** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf, tf_divergence in timeframe_divergences.items(): ... for component in ['cvd', 'trade_flow_score', 'imbalance_score']:`

### price_structure_indicators.py

**Line 138** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for component, default_weight in default_weights.items(): ... for component in self.component_weights:`

**Line 512** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for col in required_cols: ... if not any(alt_col in df.columns for alt_col in column_mapping[col]):`

**Line 653** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i in range(window, len(data) - window): ... any(highs[i] > highs[j] * (1 + threshold) for j in range(i+1, i+window+1)):`

**Line 662** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i in range(window, len(data) - window): ... any(lows[i] < lows[j] * (1 - threshold) for j in range(i+1, i+window+1)):`

**Line 935** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf, tf_data in data.items(): ... if all(v != 0 for v in volume_profile.values()):`

**Line 1999** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for idx, label in enumerate(clustering.labels_): ... for i, p in enumerate(prices):`

**Line 2068** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for t in range(time_blocks): ... for _, row in block_data.iterrows():`

**Line 4886** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for level in all_levels: ... for i, level1 in enumerate(all_levels):`

**Line 4904** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, level1 in enumerate(all_levels): ... for j, level2 in enumerate(all_levels):`

### technical_indicators.py

**Line 73** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for component, default_weight in default_weights.items(): ... for component in self.component_weights:`

**Line 603** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_name, tf_scores in data.items(): ... for component, score in tf_scores.items():`

**Line 617** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for component, score in tf_scores.items(): ... for comp, score in tf_scores.items():`

**Line 630** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_name, tf_scores in data.items(): ... for comp, score in tf_scores.items():`

### volume_indicators.py

**Line 93** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for component, default_weight in default_weights.items(): ... for component in self.component_weights:`

### main.py

**Line 988** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for exchange_id, data in market_data.items(): ... for key, value in data.items():`

**Line 1196** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_name, interval in timeframes.items(): ... for k in klines:`

### alert_manager.py

**Line 4951** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, (price, size, usd_value) in enumerate(top_bids[:3], 1): ... for price, size, usd_value in top_bids[:2]:`

**Line 4956** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, (price, size, usd_value) in enumerate(top_asks[:3], 1): ... for price, size, usd_value in top_bids[:2]:`

### alpha_integration.py

**Line 480** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for timeframe, ohlcv in ohlcv_data.items(): ... if formatted_tf_data and any(v > 0 for v in formatted_tf_data.values()):`

### alpha_scanner.py

**Line 248** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in symbols: ... for timeframe in self.timeframes:`

### health_monitor.py

**Line 719** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for map_source, alert_types in source_type_map.items(): ... for a_type in alert_types:`

**Line 743** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for alert_category, alert_types_list in source_type_map.items(): ... for alert_type in alert_types_list:`

**Line 967** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for metric_name, metric in self.metrics.items(): ... for metric_name, metric in self.metrics.items():`

**Line 973** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for ts in all_timestamps: ... for metric_name, metric in self.metrics.items():`

### health_monitor.py

**Line 693** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for metric_name, metric in self.metrics.items(): ... for metric_name, metric in self.metrics.items():`

**Line 699** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for ts in all_timestamps: ... for metric_name, metric in self.metrics.items():`

### manipulation_detector.py

**Line 512** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, symbol_history in self._manipulation_history.items(): ... for alert_data in symbol_history:`

**Line 575** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, symbol_history in self._manipulation_history.items(): ... for alert_data in symbol_history:`

### market_reporter.py

**Line 1407** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in limited_symbols: ... for result in results:`

**Line 2603** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for key, fallback in fallbacks.items(): ... for subkey, value in fallback.items():`

**Line 3367** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in limited_symbols: ... for result in results:`

**Line 3628** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for order in orders: ... for existing_price in price_groups.keys():`

**Line 3685** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in limited_symbols: ... for result in results:`

**Line 4209** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf, data in beta_analysis_data.items(): ... for symbol, metrics in data.items():`

### market_reporter_enhanced_test.py

**Line 2295** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for key in ['average_premium', 'max_premium', 'min_premium']: ... for symbol, premium in normalized['premiums'].items():`

**Line 3303** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for key, fallback in fallbacks.items(): ... for subkey, value in fallback.items():`

### metrics_manager.py

**Line 1308** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for label, snapshot in self.memory_snapshots.items(): ... for i, stat in enumerate(top_stats[:10]):`

### monitor.py

**Line 1511** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, trade in enumerate(data[:3]): ... for trade in data:`

**Line 3093** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for side in ['bids', 'asks']: ... for i, level in enumerate(levels):`

**Line 5365** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, trade in enumerate(data[:3]): ... for trade in data:`

### monitor_original.py

**Line 856** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, trade in enumerate(data[:3]): ... for trade in data:`

**Line 2195** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for side in ['bids', 'asks']: ... for i, level in enumerate(processed['orderbook'][side]):`

**Line 2256** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, trade in enumerate(trades_list): ... for field in trade:`

**Line 2313** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for key, value in original_trades.items(): ... for key, value in potential_trade_lists:`

**Line 2323** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for key, value in potential_trade_lists: ... if any(field in first_item for field in trade_fields):`

**Line 2337** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for trade in trades_list: ... for field in trade:`

**Line 2672** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for interp in market_interpretations: ... for comp_key, comp_name in component_mappings.items():`

**Line 2977** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for interp in market_interpretations: ... for comp_key, comp_name in component_mappings.items():`

**Line 4541** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, trade in enumerate(data[:3]): ... for trade in data:`

### optimized_alpha_scanner.py

**Line 399** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, symbol_data in market_data.items(): ... for pattern in patterns:`

### bitcoin_beta_7day_report.py

**Line 759** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_name, tf_interval in self.timeframes.items(): ... for attempt in range(3):`

**Line 851** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_name in self.timeframes.keys(): ... for symbol in market_data.keys():`

**Line 1080** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i in range(0, len(chart_tasks), batch_size): ... for task in batch:`

**Line 1172** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in market_data.keys(): ... for symbol in symbols_to_plot:`

**Line 1267** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, (tf_name, tf_display) in enumerate(timeframe_names.items()): ... for symbol, stats in beta_analysis[tf_name].items():`

**Line 1275** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, stats in beta_analysis[tf_name].items(): ... for bar, beta in zip(bars, betas):`

**Line 1340** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values(): ... for symbol in symbols:`

**Line 1363** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in sorted_symbols: ... for tf in timeframes:`

**Line 1388** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i in range(len(sorted_symbols)): ... for j in range(len(timeframes)):`

**Line 1435** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values(): ... for symbol in all_symbols:`

**Line 1477** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, symbol in enumerate(sorted_symbols[:n_symbols]): ... for tf in timeframes:`

**Line 1545** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values(): ... for symbol in symbols:`

**Line 1603** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i in range(len(headers)): ... for j in range(len(headers)):`

**Line 1609** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i in range(1, len(table_data) + 1): ... for j in range(len(headers)):`

**Line 1818** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for opportunity in alpha_opportunities: ... for timeframe in ['base', 'ltf', 'mtf', 'htf']:`

**Line 1907** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in market_data.keys(): ... for symbol in symbols_to_plot:`

**Line 2021** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, (tf_name, tf_display) in enumerate(timeframe_names.items()): ... for symbol, stats in beta_analysis[tf_name].items():`

**Line 2029** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, stats in beta_analysis[tf_name].items(): ... for bar, beta in zip(bars, betas):`

**Line 2099** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values(): ... for symbol in symbols:`

**Line 2119** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in sorted_symbols: ... for tf in timeframes:`

**Line 2146** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i in range(len(sorted_symbols)): ... for j in range(len(timeframes)):`

**Line 2745** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, timeframes in market_data.items(): ... for tf_name, df in timeframes.items():`

**Line 2833** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_name, btc_df in btc_data.items(): ... for symbol, timeframes in market_data.items():`

**Line 2878** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, timeframes in market_data.items(): ... for tf_name, df in timeframes.items():`

### bitcoin_beta_alpha_detector.py

**Line 661** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_name, tf_data in beta_analysis.items(): ... for tf_name, tf_data in data.items():`

**Line 669** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values(): ... for tf_name, tf_data in data.items():`

**Line 757** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_name, tf_data in beta_analysis.items(): ... for symbol, stats in tf_data.items():`

### bitcoin_beta_report.py

**Line 617** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in symbols: ... for tf_name, tf_interval in self.timeframes.items():`

**Line 677** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_name in self.timeframes.keys(): ... for symbol in market_data.keys():`

**Line 918** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in market_data.keys(): ... for symbol in symbols_to_plot:`

**Line 1011** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, (tf_name, tf_display) in enumerate(timeframe_names.items()): ... for symbol, stats in beta_analysis[tf_name].items():`

**Line 1019** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, stats in beta_analysis[tf_name].items(): ... for bar, beta in zip(bars, betas):`

**Line 1084** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values(): ... for symbol in symbols:`

**Line 1102** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in sorted_symbols: ... for tf in timeframes:`

**Line 1127** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i in range(len(sorted_symbols)): ... for j in range(len(timeframes)):`

**Line 1173** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values(): ... for symbol in all_symbols:`

**Line 1209** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, symbol in enumerate(sorted_symbols[:n_symbols]): ... for tf in timeframes:`

**Line 1276** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values(): ... for symbol in symbols:`

**Line 1329** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i in range(len(headers)): ... for j in range(len(headers)):`

**Line 1335** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i in range(1, len(table_data) + 1): ... for j in range(len(headers)):`

**Line 1539** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for opportunity in alpha_opportunities: ... for timeframe in ['base', 'ltf', 'mtf', 'htf']:`

**Line 1614** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in market_data.keys(): ... for symbol in symbols_to_plot:`

**Line 1721** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i, (tf_name, tf_display) in enumerate(timeframe_names.items()): ... for symbol, stats in beta_analysis[tf_name].items():`

**Line 1729** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, stats in beta_analysis[tf_name].items(): ... for bar, beta in zip(bars, betas):`

**Line 1799** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values(): ... for symbol in symbols:`

**Line 1819** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in sorted_symbols: ... for tf in timeframes:`

**Line 1846** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for i in range(len(sorted_symbols)): ... for j in range(len(timeframes)):`

### fix_market_reporter.py

**Line 73** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for base_asset in base_assets: ... for month in [6, 9, 12]:`

**Line 77** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for month in [6, 9, 12]: ... for symbol, category, format_type in formats_to_try:`

**Line 131** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for asset, contracts in results.items(): ... for contract in contracts:`

### get_bybit_instruments.py

**Line 30** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for category in categories: ... for asset in assets:`

**Line 49** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for asset in assets: ... for future in asset_futures:`

**Line 88** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for asset, contracts in results.items(): ... for contract in contracts:`

**Line 110** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for asset, contracts in results.items(): ... for contract in contracts:`

**Line 111** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for contract in contracts: ... elif any(code in symbol for code in ['H', 'M', 'U', 'Z']) and symbol[-2:].isdigit():`

### get_bybit_quarterly.py

**Line 73** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for category in categories: ... for future in futures:`

### test_bybit_api.py

**Line 116** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for category in ["linear", "inverse"]: ... for symbol in ["BTC", "ETH", "SOL", "XRP", "AVAX"]:`

**Line 133** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in ["BTC", "ETH", "SOL", "XRP", "AVAX"]: ... for contract in symbol_futures:`

### test_futures_formats.py

**Line 73** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for base_asset in base_assets: ... for symbol, category, format_name in formats:`

**Line 114** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for format_name, symbols in results.items(): ... for symbol, price in symbols.items():`

**Line 124** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for base_asset in base_assets: ... for format_name in formats_to_check:`

**Line 129** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for format_name in formats_to_check: ... for symbol in results[format_name]:`

### verify_bybit_tickers.py

**Line 54** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, category in test_symbols: ... elif category == "inverse" and any(code in symbol for code in ['M', 'U', 'Z', 'H']):`

**Line 106** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, data in results["base_only_hyphenated"].items(): ... for symbol in results["linear_hyphenated"]:`

**Line 110** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, data in results["inverse_month_code"].items(): ... for symbol in results["linear_hyphenated"]:`

**Line 114** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in results["invalid"]: ... for symbol in results["linear_hyphenated"]:`

**Line 121** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for asset in assets: ... for symbol in results["linear_hyphenated"]:`

### signal_generator.py

**Line 1611** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for component_name in components.keys(): ... for sub_name, sub_score in sub_components.items():`

### run_diagnostics.py

**Line 162** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, operations in self.symbol_operations.items(): ... for i, op in enumerate(operations):`

**Line 441** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for log_file in log_files: ... for line_num, line in enumerate(f, 1):`

**Line 444** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for line_num, line in enumerate(f, 1): ... for pattern in MARKET_MONITOR_PATTERNS['duplicate_data_fetch']:`

**Line 556** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, timestamps in fetch_timestamps.items(): ... for i in range(1, len(timestamps)):`

**Line 623** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for location in log_locations: ... for root, _, files in os.walk(location):`

**Line 627** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for root, _, files in os.walk(location): ... for file in files:`

**Line 650** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for log_file in log_files: ... for line_num, line in enumerate(f, 1):`

**Line 661** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for log_file in log_files: ... for line_num, line in enumerate(f, 1):`

**Line 665** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for line_num, line in enumerate(f, 1): ... for pattern in LOG_PATTERNS['error']:`

**Line 731** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, data in market_monitor_analysis['duplicate_fetches'].items(): ... for prev, curr, time_diff in data['examples']:`

**Line 755** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for log_file, line_num, line in market_monitor_analysis['websocket_issues'][:5]: ... for log_file, line_num, line in metrics['examples']:`

**Line 762** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol, metrics in market_monitor_analysis['cache_metrics'].items(): ... for log_file, line_num, line in metrics['examples']:`

**Line 805** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for log_file, line_num, line in errors: ... if error_filter and not any(re.search(pattern, error_type) for pattern in error_filter):`

**Line 820** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for error_type, occurrences in errors_by_type.items(): ... if error_filter and not any(re.search(pattern, error_type) for pattern in error_filter):`

**Line 1042** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for location in log_locations: ... for file in os.listdir(location):`

### trade_executor.py

**Line 922** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for account in account_info: ... for coin in coins:`

### trading_system.py

**Line 325** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for symbol in self.active_symbols: ... for symbol in self.active_symbols:`

### helpers.py

**Line 218** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for category, df_names in categories.items(): ... for df_name in df_names:`

**Line 284** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_name, tf_config in config['timeframes'].items(): ... for tf in self.timeframe_weights:`

**Line 293** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for tf_name, tf_config in config['timeframes'].items(): ... for tf in self.timeframe_weights:`

### validation.py

**Line 79** - nested_loop
- Issue: Nested loops - potential O(n²) complexity
- Code: `for timeframe, df in price_data.items(): ... if not all(col in df.columns for col in required_columns):`

### liquidation_detector.py

**Line 492** - pandas_bottleneck
- Issue: iterrows() is extremely slow - use vectorization
- Code: `for idx, row in recent_data.iterrows():`

### database.py

**Line 308** - pandas_bottleneck
- Issue: iterrows() is extremely slow - use vectorization
- Code: `for index, row in df.iterrows():`

**Line 494** - pandas_bottleneck
- Issue: iterrows() is extremely slow - use vectorization
- Code: `for index, row in df.iterrows():`

### orderflow_indicators.py

**Line 2521** - pandas_bottleneck
- Issue: iterrows() is extremely slow - use vectorization
- Code: `for idx, trade in sample_trades.iterrows():`

### price_structure_indicators.py

**Line 1123** - pandas_bottleneck
- Issue: iterrows() is extremely slow - use vectorization
- Code: `for idx, row in grouped.iterrows():`

**Line 2073** - pandas_bottleneck
- Issue: iterrows() is extremely slow - use vectorization
- Code: `for _, row in block_data.iterrows():`

**Line 5587** - pandas_bottleneck
- Issue: iterrows() is extremely slow - use vectorization
- Code: `for _, candle in future_window.iterrows():`

**Line 5617** - pandas_bottleneck
- Issue: iterrows() is extremely slow - use vectorization
- Code: `for _, candle in future_window.iterrows():`

### volume_indicators.py

**Line 801** - pandas_bottleneck
- Issue: iloc in loop - vectorize or use .values
- Code: `self.logger.debug(f"OBV stats before normalization - min: {obv.min():.2f}, max: {obv.max():.2f}, current: {obv.iloc[-1]:.2f}")`

**Line 1537** - pandas_bottleneck
- Issue: iloc in loop - vectorize or use .values
- Code: `self.logger.debug(f"ADL stats before normalization - min: {adl.min():.2f}, max: {adl.max():.2f}, current: {adl.iloc[-1]:.2f}")`

### monitor.py

**Line 5576** - pandas_bottleneck
- Issue: iterrows() is extremely slow - use vectorization
- Code: `colors = ['green' if row['close'] >= row['open'] else 'red' for _, row in df.iterrows()]`

**Line 5579** - pandas_bottleneck
- Issue: iterrows() is extremely slow - use vectorization
- Code: `for i, (timestamp, row) in enumerate(df.iterrows()):`

### monitor_original.py

**Line 4752** - pandas_bottleneck
- Issue: iterrows() is extremely slow - use vectorization
- Code: `colors = ['green' if row['close'] >= row['open'] else 'red' for _, row in df.iterrows()]`

**Line 4755** - pandas_bottleneck
- Issue: iterrows() is extremely slow - use vectorization
- Code: `for i, (timestamp, row) in enumerate(df.iterrows()):`

## 💡 Optimization Recommendations

### pandas_bottleneck
- Replace .iterrows() with vectorized operations
- Use .values or .to_numpy() for numerical operations
- Batch operations instead of row-by-row processing

### nested_loop
- Consider using numpy operations for numerical data
- Use dictionary lookups instead of nested searches
- Implement early break conditions where possible

### blocking_in_async
- Use asyncio.sleep() instead of time.sleep()
- Replace requests with aiohttp for HTTP calls
- Use asyncio.run_in_executor() for blocking operations

### memory_bottleneck
- Use generators instead of large list comprehensions
- Process data in chunks for large files
- Consider using numpy arrays for numerical data
