# Static Bottleneck Analysis Report

Total issues found: 3373

## Summary by Severity
- 🔴 High: 2365
- 🟡 Medium: 1008
- 🟢 Low: 0

## Summary by Type
- api_in_loop: 2189
- blocking_in_async: 99
- blocking_io: 161
- memory_concern: 557
- nested_loops: 315
- pandas_inefficiency: 17
- sequential_api_calls: 35

## Detailed Issues

### src/analysis/resource_manager.py

🔴 **Line 148** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `metrics = self._metrics.get(component_name)`

🔴 **Line 250** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `process = psutil.Process()`

🔴 **Line 261** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `metrics = self._metrics.get(component)`

🔴 **Line 261** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `metrics = self._metrics.get(component)`

🔴 **Line 274** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `metrics = self._metrics.get(component)`

🔴 **Line 281** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._metrics.get(component_name)`

### src/analysis/validation.py

🔴 **Line 32** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = data.get('symbol', '')`

🔴 **Line 85** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if settings.get('enabled', False):`

🔴 **Line 218** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_min = data.get('price_min')`

🔴 **Line 218** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_min = data.get('price_min')`

🔴 **Line 218** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_min = data.get('price_min')`

🔴 **Line 241** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `value = data.get(self.field_name)`

🔴 **Line 290** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._rule_cache.get(data_type, {}).get(rule_type)`

🔴 **Line 290** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._rule_cache.get(data_type, {}).get(rule_type)`

🔴 **Line 290** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._rule_cache.get(data_type, {}).get(rule_type)`

### src/api/routes/alerts.py

🔴 **Line 44** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/", response_model=List[AlertData])`

🔴 **Line 73** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if alert_type and alert.get('details', {}).get('type') != alert_type:`

🔴 **Line 125** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `id=alert.get('id', str(int(alert.get('timestamp', time.time()) * 1000000))),`

🔴 **Line 125** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `id=alert.get('id', str(int(alert.get('timestamp', time.time()) * 1000000))),`

🔴 **Line 138** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `alert_data.sort(key=lambda x: x.timestamp, reverse=True)`

🔴 **Line 205** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `level = alert.get('level', 'INFO')`

🔴 **Line 205** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `level = alert.get('level', 'INFO')`

🔴 **Line 298** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alert_type = alert.get('details', {}).get('type')`

### src/api/routes/alpha.py

🔴 **Line 105** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/opportunities/{symbol}", response_model=Optional[AlphaOpportunity])`

🔴 **Line 130** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/scan/status")`

### src/api/routes/correlation.py

🔴 **Line 99** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)`

🔴 **Line 104** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(file_path, 'r') as f:`

🔴 **Line 126** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `row = {"symbol": signal.get("symbol"), "timestamp": signal.get("timestamp")}`

🔴 **Line 134** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `row[signal_type] = comp_data.get("score", 50.0)`

🔴 **Line 173** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal.get("symbol")`

🔴 **Line 173** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal.get("symbol")`

🔴 **Line 173** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal.get("symbol")`

🔴 **Line 186** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `components = signal.get("components", {})`

🔴 **Line 186** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `components = signal.get("components", {})`

🔴 **Line 186** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `components = signal.get("components", {})`

🔴 **Line 260** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signals_data = dashboard_data.get("signals", []) if isinstance(dashboard_data, dict) else []`

🔴 **Line 269** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(signal, dict) and signal.get("symbol") == symbol:`

🔴 **Line 269** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(signal, dict) and signal.get("symbol") == symbol:`

🔴 **Line 269** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(signal, dict) and signal.get("symbol") == symbol:`

🔴 **Line 283** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"score": float(signal_data.get("confidence", 50.0)),`

🔴 **Line 405** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signals_data = dashboard_data.get("signals", []) if isinstance(dashboard_data, dict) else []`

🔴 **Line 405** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signals_data = dashboard_data.get("signals", []) if isinstance(dashboard_data, dict) else []`

🔴 **Line 405** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signals_data = dashboard_data.get("signals", []) if isinstance(dashboard_data, dict) else []`

🔴 **Line 414** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(signal, dict) and signal.get("symbol") == symbol:`

🔴 **Line 414** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(signal, dict) and signal.get("symbol") == symbol:`

🔴 **Line 414** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(signal, dict) and signal.get("symbol") == symbol:`

🔴 **Line 428** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"score": float(signal_data.get("confidence", 50.0)),`

🔴 **Line 550** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/asset-correlations")`

🔴 **Line 594** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `corr_data = correlations.get("signal_correlations", {})`

🔴 **Line 615** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"statistics": correlations.get("statistics", {}),`

🔴 **Line 615** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"statistics": correlations.get("statistics", {}),`

🔴 **Line 615** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"statistics": correlations.get("statistics", {}),`

🔴 **Line 615** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"statistics": correlations.get("statistics", {}),`

### src/api/routes/dashboard.py

🔴 **Line 60** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/overview")`

🔴 **Line 60** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/overview")`

🔴 **Line 107** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/alerts/recent")`

🔴 **Line 133** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/alpha-opportunities")`

🔴 **Line 148** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/market-overview")`

🔴 **Line 416** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbols_data.sort(key=lambda x: x['turnover_24h'], reverse=True)`

🔴 **Line 441** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession() as session:`

🔴 **Line 470** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/health")`

🔴 **Line 514** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/api/liquidation/alerts")`

🔴 **Line 623** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbols = scan_request.get('symbols', ['BTCUSDT', 'ETHUSDT'])`

### src/api/routes/interactive_reports.py

🔴 **Line 101** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(report_path, 'r', encoding='utf-8') as f:`

🔴 **Line 139** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/{report_id}/metadata")`

🔴 **Line 168** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/{report_id}/download")`

🔴 **Line 343** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.post("/cleanup")`

### src/api/routes/liquidation.py

🔴 **Line 132** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if severity_order.get(event.severity, 1) >= severity_order[min_severity]`

🔴 **Line 136** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `filtered_events.sort(key=lambda x: x.timestamp, reverse=True)`

🔴 **Line 371** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/leverage-metrics/{symbol}", response_model=LeverageMetrics)`

🔴 **Line 371** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/leverage-metrics/{symbol}", response_model=LeverageMetrics)`

🔴 **Line 387** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current_funding = funding_info.get('fundingRate', 0) if funding_info else 0`

🔴 **Line 391** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_leverage = market_info.get('limits', {}).get('leverage', {}).get('max', 100) if market_info else 100`

🔴 **Line 431** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.post("/monitor", response_model=Dict[str, str])`

🔴 **Line 491** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/history/{symbol}")`

🔴 **Line 514** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_events.sort(key=lambda x: x.timestamp, reverse=True)`

### src/api/routes/manipulation.py

🔴 **Line 99** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"id": alert.get("id", ""),`

🔴 **Line 99** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"id": alert.get("id", ""),`

### src/api/routes/market.py

🔴 **Line 123** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"price": ticker_data.get('last', 0),`

🔴 **Line 123** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"price": ticker_data.get('last', 0),`

🔴 **Line 154** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.post("/ticker/batch")`

🔴 **Line 219** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker_data = exchange_data.get('ticker', {})`

🔴 **Line 280** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `elif result.get("status") == "success":`

🔴 **Line 280** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `elif result.get("status") == "success":`

🔴 **Line 416** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/{exchange_id}/{symbol}/orderbook", response_model=OrderBook)`

🔴 **Line 432** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/{exchange_id}/{symbol}/trades", response_model=List[Trade])`

🔴 **Line 442** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trades = data[exchange_id].get('recent_trades', [])`

🔴 **Line 449** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/compare/{symbol}", response_model=MarketComparison)`

🔴 **Line 472** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `bid=ticker.get('bid'),`

🔴 **Line 472** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `bid=ticker.get('bid'),`

🔴 **Line 565** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"data_quality": "high" if len(futures_analysis.get('premiums', {})) > 0 else "low"`

🔴 **Line 590** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `contango_status = futures_data.get('contango_status', 'NEUTRAL')`

🔴 **Line 590** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `contango_status = futures_data.get('contango_status', 'NEUTRAL')`

🔴 **Line 645** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol_data = futures_data.get('premiums', {}).get(symbol, {})`

🔴 **Line 645** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol_data = futures_data.get('premiums', {}).get(symbol, {})`

🔴 **Line 645** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol_data = futures_data.get('premiums', {}).get(symbol, {})`

🔴 **Line 670** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/futures-premium/{symbol}")`

🔴 **Line 698** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol_data = futures_data.get('premiums', {}).get(symbol_formatted, {})`

🔴 **Line 698** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol_data = futures_data.get('premiums', {}).get(symbol_formatted, {})`

🔴 **Line 698** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol_data = futures_data.get('premiums', {}).get(symbol_formatted, {})`

🔴 **Line 704** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `spot_premium = symbol_data.get('spot_premium', 0.0)`

🔴 **Line 774** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/analysis/{symbol}")`

🔴 **Line 774** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/analysis/{symbol}")`

🔴 **Line 852** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `bid_volume = sum(float(bid[1]) for bid in orderbook.get('bids', [])[:10])`

🔴 **Line 853** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ask_volume = sum(float(ask[1]) for ask in orderbook.get('asks', [])[:10])`

🔴 **Line 856** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"best_bid": float(orderbook['bids'][0][0]) if orderbook.get('bids') else 0,`

🔴 **Line 880** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol_data = futures_data.get('premiums', {}).get(symbol_formatted, {})`

🔴 **Line 880** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol_data = futures_data.get('premiums', {}).get(symbol_formatted, {})`

🔴 **Line 937** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if analysis["analysis"]["market_data"].get("price"):`

🔴 **Line 937** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if analysis["analysis"]["market_data"].get("price"):`

🔴 **Line 977** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sell_signals = sum(1 for comp in components.values() if isinstance(comp, dict) and comp.get("score", 50) < 40)`

🔴 **Line 988** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"technical": components.get("technical", {}).get("score", 50) if "technical" in components else 50,`

🔴 **Line 1015** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current_price = analysis["analysis"]["market_data"].get("price", 0)`

🔴 **Line 1015** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current_price = analysis["analysis"]["market_data"].get("price", 0)`

🔴 **Line 1076** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price = analysis["analysis"]["market_data"].get("price", 0)`

### src/api/routes/sentiment.py

🔴 **Line 103** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `sentiments.sort(key=lambda x: x.sentiment_score, reverse=True)`

🔴 **Line 105** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `sentiments.sort(key=lambda x: x.fear_greed_index, reverse=True)`

🔴 **Line 115** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/fear-greed")`

### src/api/routes/signal_tracking.py

🔴 **Line 51** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `created_time = signal_data.get('created_at', 0)`

🔴 **Line 51** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `created_time = signal_data.get('created_at', 0)`

🔴 **Line 69** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/active")`

🔴 **Line 93** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `duration_seconds = current_time - signal_data.get('created_at', current_time)`

🔴 **Line 174** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'confidence': signal_data.get('confidence', 0),`

🔴 **Line 174** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'confidence': signal_data.get('confidence', 0),`

🔴 **Line 202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/history")`

🔴 **Line 202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/history")`

🔴 **Line 202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/history")`

🔴 **Line 236** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `profitable_signals = sum(1 for s in signal_history if s.get('pnl_percentage', 0) > 0)`

🔴 **Line 236** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `profitable_signals = sum(1 for s in signal_history if s.get('pnl_percentage', 0) > 0)`

🔴 **Line 237** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `losing_signals = sum(1 for s in signal_history if s.get('pnl_percentage', 0) < 0)`

🔴 **Line 297** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not signal_data.get('action') or signal_data.get('action') == 'NEUTRAL':`

🔴 **Line 307** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'entry_price': float(signal_data.get('price', 0)),`

### src/api/routes/signals.py

🔴 **Line 41** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signal_tracking_config = config.get('signal_tracking', {})`

🔴 **Line 59** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/signals/latest", response_model=LatestSignals)`

🔴 **Line 94** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)`

🔴 **Line 98** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `all_files.sort(key=lambda x: x.name, reverse=True)`

🔴 **Line 107** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(file_path, 'r') as f:`

🔴 **Line 114** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(signal_data, dict) and signal_data.get('symbol'):`

🔴 **Line 114** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(signal_data, dict) and signal_data.get('symbol'):`

🔴 **Line 164** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(file_path, 'r') as f:`

🔴 **Line 168** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if signal_data.get('symbol', '').upper() == symbol:`

🔴 **Line 168** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if signal_data.get('symbol', '').upper() == symbol:`

🔴 **Line 168** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if signal_data.get('symbol', '').upper() == symbol:`

🔴 **Line 168** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if signal_data.get('symbol', '').upper() == symbol:`

🔴 **Line 180** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `signals.sort(key=lambda x: x.get('timestamp', x.get('filename', '')), reverse=True)`

🔴 **Line 228** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(file_path, 'r') as f:`

🔴 **Line 236** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if symbol and signal_data.get('symbol', '').upper() != symbol.upper():`

🔴 **Line 275** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `filtered_signals.sort(key=lambda x: x.get('timestamp', x.get('filename', '')), reverse=True)`

🔴 **Line 305** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(file_path, 'r') as f:`

🔴 **Line 352** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `duration_seconds = current_time - signal_data.get('created_at', current_time)`

🔴 **Line 398** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)`

🔴 **Line 404** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(file_path, 'r') as f:`

🔴 **Line 408** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get("symbol")`

🔴 **Line 408** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get("symbol")`

🔴 **Line 415** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"id": signal_data.get("filename", file_path.stem),`

### src/api/routes/system.py

🔴 **Line 24** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `cpu_percent = psutil.cpu_percent(interval=1)`

🔴 **Line 25** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `memory = psutil.virtual_memory()`

🔴 **Line 26** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `disk = psutil.disk_usage('/')`

🔴 **Line 34** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'online': status.get('online', False),`

🔴 **Line 89** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/exchanges/status")`

🔴 **Line 105** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'min_amount': market.get('limits', {}).get('amount', {}).get('min'),`

🔴 **Line 105** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'min_amount': market.get('limits', {}).get('amount', {}).get('min'),`

🔴 **Line 116** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'online': exchange_status.get('online', False),`

🔴 **Line 139** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `cpu_times = psutil.cpu_times()`

🔴 **Line 140** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `cpu_freq = psutil.cpu_freq()`

🔴 **Line 141** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `cpu_stats = psutil.cpu_stats()`

🔴 **Line 144** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `memory = psutil.virtual_memory()`

🔴 **Line 145** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `swap = psutil.swap_memory()`

🔴 **Line 148** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `disk_io = psutil.disk_io_counters()`

🔴 **Line 151** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `net_io = psutil.net_io_counters()`

🔴 **Line 155** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `'percent': psutil.cpu_percent(interval=1),`

### src/api/routes/test_api_endpoints.py

🔴 **Line 136** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `prefix = prefixes.get(module, 'N/A')`

🔴 **Line 136** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `prefix = prefixes.get(module, 'N/A')`

🔴 **Line 145** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `full_path = route.get('full_path', route['path'])`

### src/api/routes/test_api_endpoints_summary.py

🔴 **Line 151** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `prefix = prefixes.get(module, 'N/A')`

🔴 **Line 151** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `prefix = prefixes.get(module, 'N/A')`

🔴 **Line 157** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `full_path = route.get('full_path', route['path'])`

🔴 **Line 178** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if any(kw in r.get('full_path', r['path']).lower() for kw in keywords)]`

🔴 **Line 178** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if any(kw in r.get('full_path', r['path']).lower() for kw in keywords)]`

### src/api/routes/top_symbols.py

🔴 **Line 110** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/gainers")`

🔴 **Line 134** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/losers")`

🔴 **Line 158** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/volume")`

🔴 **Line 182** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/health")`

### src/api/routes/trading.py

🔴 **Line 68** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/{exchange_id}/positions", response_model=List[Position])`

🔴 **Line 68** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/{exchange_id}/positions", response_model=List[Position])`

🔴 **Line 91** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.post("/{exchange_id}/position/update")`

🔴 **Line 91** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.post("/{exchange_id}/position/update")`

🔴 **Line 129** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/portfolio", response_model=PortfolioSummary)`

🔴 **Line 168** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/orders")`

🔴 **Line 168** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/orders")`

🔴 **Line 188** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `all_orders.sort(key=lambda x: x.timestamp or 0, reverse=True)`

🔴 **Line 194** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/positions")`

🔴 **Line 194** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/positions")`

🔴 **Line 217** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/portfolio/summary", response_model=PortfolioSummary)`

🔴 **Line 217** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/portfolio/summary", response_model=PortfolioSummary)`

### src/api/routes/whale_activity.py

🔴 **Line 118** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@router.get("/summary")`

🔴 **Line 210** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `large_orders.sort(key=lambda x: x['timestamp'], reverse=True)`

### src/config/manager.py

🔴 **Line 204** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `exchanges = config.get('exchanges', {})`

🔴 **Line 204** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `exchanges = config.get('exchanges', {})`

🔴 **Line 210** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if exchange_config.get('enabled', False):`

🔴 **Line 259** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `exchanges = self.config.get('exchanges', {})`

🔴 **Line 259** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `exchanges = self.config.get('exchanges', {})`

🔴 **Line 300** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weights = self.config.get('confluence', {}).get('weights', {}).get('sub_components', {}).get(indicator_type, {})`

🔴 **Line 300** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weights = self.config.get('confluence', {}).get('weights', {}).get('sub_components', {}).get(indicator_type, {})`

🔴 **Line 320** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self.config.get('database', {})`

### src/core/analysis/alpha_scanner.py

🔴 **Line 75** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.min_volume_24h = self.config.get('alpha_scanner', {}).get('min_volume_24h', 100000)`

🔴 **Line 125** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `opportunities.sort(key=lambda x: x.score, reverse=True)`

🔴 **Line 152** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not confluence_result or confluence_result.get('score', 0) < 40:`

🔴 **Line 152** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not confluence_result or confluence_result.get('score', 0) < 40:`

🔴 **Line 167** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `components = confluence_result.get('components', {})`

🔴 **Line 167** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `components = confluence_result.get('components', {})`

🔴 **Line 208** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `limit = self.lookback_periods.get(timeframe, 100)`

🔴 **Line 208** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `limit = self.lookback_periods.get(timeframe, 100)`

🔴 **Line 208** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `limit = self.lookback_periods.get(timeframe, 100)`

🔴 **Line 240** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volume_24h = ticker.get('quoteVolume', 0) or ticker.get('baseVolume', 0) * ticker.get('last', 1)`

🔴 **Line 240** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volume_24h = ticker.get('quoteVolume', 0) or ticker.get('baseVolume', 0) * ticker.get('last', 1)`

🔴 **Line 240** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volume_24h = ticker.get('quoteVolume', 0) or ticker.get('baseVolume', 0) * ticker.get('last', 1)`

🔴 **Line 269** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score = confluence_result.get('score', 50.0)`

🔴 **Line 269** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score = confluence_result.get('score', 50.0)`

🔴 **Line 311** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sub_components = technical.get('sub_components', {})`

🔴 **Line 366** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 440** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signal_direction = confluence_result.get('signal', 'NEUTRAL')`

🔴 **Line 440** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signal_direction = confluence_result.get('signal', 'NEUTRAL')`

🔴 **Line 490** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `components = confluence_result.get('components', {})`

🔴 **Line 490** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `components = confluence_result.get('components', {})`

🔴 **Line 548** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `components = confluence_result.get('components', {})`

🔴 **Line 559** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `indicators['confluence_score'] = confluence_result.get('score', 50.0)`

🔴 **Line 595** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `comp_score = component_data.get('score', 50.0)`

🔴 **Line 619** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `usdt_pairs = [market['symbol'] for market in markets if market.get('symbol', '').endswith('USDT') and market.get('active', True)]`

🔴 **Line 619** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `usdt_pairs = [market['symbol'] for market in markets if market.get('symbol', '').endswith('USDT') and market.get('active', True)]`

### src/core/analysis/basis_analysis.py

🔴 **Line 145** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `for price, amount in orderbook.get('asks', []):`

### src/core/analysis/confluence.py

🔴 **Line 85** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.weights = confluence_config.get('components', {`

🔴 **Line 96** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.sub_component_weights = confluence_config.get('sub_components', {})`

🔴 **Line 197** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `scores[indicator_type] = result.get('score', 50.0)`

🔴 **Line 222** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `flow_status = self.data_flow_tracker.flow.get(indicator_type, {})`

🔴 **Line 222** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `flow_status = self.data_flow_tracker.flow.get(indicator_type, {})`

🔴 **Line 222** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `flow_status = self.data_flow_tracker.flow.get(indicator_type, {})`

🔴 **Line 252** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'score': component_result.get('score', 0),`

🔴 **Line 252** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'score': component_result.get('score', 0),`

🔴 **Line 261** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sub_name = sub_comp.get('name', '')`

🔴 **Line 261** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sub_name = sub_comp.get('name', '')`

🔴 **Line 277** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `parent_name = sub_comp.get('parent', '')`

🔴 **Line 342** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component_weight = weights.get(component_name, 0)`

🔴 **Line 342** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component_weight = weights.get(component_name, 0)`

🔴 **Line 402** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if flow_id not in self.data_flow_tracker.data_flow.get('component_stats', {}):`

🔴 **Line 486** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'ohlcv': market_data.get('ohlcv', {}),`

🔴 **Line 486** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'ohlcv': market_data.get('ohlcv', {}),`

🔴 **Line 486** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'ohlcv': market_data.get('ohlcv', {}),`

🔴 **Line 522** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'ohlcv': market_data.get('ohlcv', {}),`

🔴 **Line 522** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'ohlcv': market_data.get('ohlcv', {}),`

🔴 **Line 559** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'orderbook': market_data.get('orderbook', {}),`

🔴 **Line 559** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'orderbook': market_data.get('orderbook', {}),`

🔴 **Line 559** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'orderbook': market_data.get('orderbook', {}),`

🔴 **Line 559** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'orderbook': market_data.get('orderbook', {}),`

🔴 **Line 559** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'orderbook': market_data.get('orderbook', {}),`

🔴 **Line 562** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': market_data.get('symbol', 'UNKNOWN'),`

🔴 **Line 702** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': market_data.get('symbol', ''),`

🔴 **Line 707** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'orderbook': market_data.get('orderbook', {}),`

🔴 **Line 712** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'open_interest': market_data.get('open_interest', {})`

🔴 **Line 789** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': market_data.get('symbol', ''),`

🔴 **Line 804** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'ohlcv': market_data.get('ohlcv', {}),`

🔴 **Line 826** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': market_data.get('symbol', ''),`

🔴 **Line 826** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': market_data.get('symbol', ''),`

🔴 **Line 894** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf: str(self.config.get('timeframes', {}).get(tf, {}).get('interval', 60))`

🔴 **Line 896** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if tf in self.config.get('timeframes', {})`

🔴 **Line 1112** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `interval_value = indicator.timeframe_map.get(missing_tf)`

🔴 **Line 1112** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `interval_value = indicator.timeframe_map.get(missing_tf)`

🔴 **Line 1112** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `interval_value = indicator.timeframe_map.get(missing_tf)`

🔴 **Line 1112** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `interval_value = indicator.timeframe_map.get(missing_tf)`

🔴 **Line 1213** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol')`

🔴 **Line 1467** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `scores[indicator] * self.weights.get(indicator, 0)`

🔴 **Line 1467** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `scores[indicator] * self.weights.get(indicator, 0)`

🔴 **Line 1467** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `scores[indicator] * self.weights.get(indicator, 0)`

🔴 **Line 1496** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `flow_status = self.data_flow_tracker.flow.get(indicator_type, {})`

🔴 **Line 1496** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `flow_status = self.data_flow_tracker.flow.get(indicator_type, {})`

🔴 **Line 1820** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': market_data.get('symbol', ''),`

🔴 **Line 1825** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'orderbook': market_data.get('orderbook', {}),`

🔴 **Line 1830** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'open_interest': market_data.get('open_interest', {})`

🔴 **Line 1907** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': market_data.get('symbol', ''),`

🔴 **Line 1922** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'ohlcv': market_data.get('ohlcv', {}),`

🔴 **Line 1944** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': market_data.get('symbol', ''),`

🔴 **Line 1944** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': market_data.get('symbol', ''),`

🔴 **Line 2012** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf: str(self.config.get('timeframes', {}).get(tf, {}).get('interval', 60))`

🔴 **Line 2014** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if tf in self.config.get('timeframes', {})`

🔴 **Line 2230** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `interval_value = indicator.timeframe_map.get(missing_tf)`

🔴 **Line 2230** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `interval_value = indicator.timeframe_map.get(missing_tf)`

🔴 **Line 2230** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `interval_value = indicator.timeframe_map.get(missing_tf)`

🔴 **Line 2230** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `interval_value = indicator.timeframe_map.get(missing_tf)`

🔴 **Line 2331** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol')`

🔴 **Line 2585** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `scores[indicator] * self.weights.get(indicator, 0)`

🔴 **Line 2585** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `scores[indicator] * self.weights.get(indicator, 0)`

🔴 **Line 2585** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `scores[indicator] * self.weights.get(indicator, 0)`

🔴 **Line 2999** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not isinstance(tf_data.get('data'), pd.DataFrame):`

🔴 **Line 3063** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `('trades_df' in data and not data['trades_df'].empty if isinstance(data.get('trades_df'), pd.DataFrame) else False)`

🔴 **Line 3146** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `name: result.get('signals', {})`

🔴 **Line 3152** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signals.get(ind, {}).get('trend', {}).get('signal') == 'bullish'`

🔴 **Line 3157** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signals.get(ind, {}).get('trend', {}).get('signal') == 'bearish'`

🔴 **Line 3162** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sentiment_bullish = signals.get('sentiment', {}).get('trend', {}).get('signal') == 'bullish'`

🔴 **Line 3230** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df = market_data['ohlcv'].get(tf)`

🔴 **Line 3230** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df = market_data['ohlcv'].get(tf)`

🔴 **Line 3230** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df = market_data['ohlcv'].get(tf)`

🔴 **Line 3230** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df = market_data['ohlcv'].get(tf)`

🔴 **Line 3699** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alternatives = field_mapping.get(req_field, [req_field])`

🔴 **Line 3699** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alternatives = field_mapping.get(req_field, [req_field])`

🔴 **Line 3699** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alternatives = field_mapping.get(req_field, [req_field])`

🔴 **Line 3755** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker_data = market_data.get('ticker', {})`

🔴 **Line 3755** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker_data = market_data.get('ticker', {})`

🔴 **Line 3791** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `funding_rate = sentiment_data.get('funding_rate')`

🔴 **Line 3791** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `funding_rate = sentiment_data.get('funding_rate')`

🔴 **Line 3791** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `funding_rate = sentiment_data.get('funding_rate')`

🔴 **Line 3791** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `funding_rate = sentiment_data.get('funding_rate')`

🔴 **Line 3903** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `side = liq.get('side', '').lower()`

🔴 **Line 4061** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trades = market_data.get('trades', [])`

🔴 **Line 4061** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trades = market_data.get('trades', [])`

🔴 **Line 4061** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trades = market_data.get('trades', [])`

🔴 **Line 4353** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker_price = self.market_data['ticker'].get('last', self.market_data['ticker'].get('last_price', 0))`

🔴 **Line 4376** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_value = trade.get(price_field)`

🔴 **Line 4376** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_value = trade.get(price_field)`

🔴 **Line 4376** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_value = trade.get(price_field)`

🔴 **Line 4376** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_value = trade.get(price_field)`

🔴 **Line 4435** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `processed_trade['side'] = 'buy' if processed_trade.get('id', '')[-1].isdigit() and int(processed_trade['id'][-1]) % 2 == 0 else 'sell'`

### src/core/analysis/indicator_utils.py

🔴 **Line 28** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = weights.get(component, 0)`

🔴 **Line 28** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = weights.get(component, 0)`

🔴 **Line 28** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = weights.get(component, 0)`

🔴 **Line 28** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = weights.get(component, 0)`

🔴 **Line 170** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = component_weights.get(component, 0) if component_weights else 0`

🔴 **Line 170** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = component_weights.get(component, 0) if component_weights else 0`

🔴 **Line 170** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = component_weights.get(component, 0) if component_weights else 0`

🔴 **Line 170** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = component_weights.get(component, 0) if component_weights else 0`

🔴 **Line 180** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weighted_sum = sum(scores.get(comp, 0) * component_weights.get(comp, 0)`

🔴 **Line 182** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight_sum = sum(component_weights.get(comp, 0) for comp in scores if comp in component_weights)`

🔴 **Line 186** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf_weight = timeframe_weights.get(tf, 0) if timeframe_weights else 0`

🔴 **Line 195** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `div_type = div_info.get('type', 'unknown')`

### src/core/analysis/integrated_analysis.py

🔴 **Line 242** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `bias = component_signals.get('bias', 'neutral').lower()`

🔴 **Line 290** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data_timestamp = market_data.get('timestamp', 0)`

🔴 **Line 307** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if any(pd.isna(market_data['ohlcv'].get(field, 0)) for field in ['open', 'high', 'low', 'close', 'volume']):`

🔴 **Line 311** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not market_data['orderbook'].get('bids') or not market_data['orderbook'].get('asks'):`

### src/core/analysis/interpretation_generator.py

🔴 **Line 60** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = float(data.get('score', 50))`

🔴 **Line 60** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = float(data.get('score', 50))`

🔴 **Line 60** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = float(data.get('score', 50))`

🔴 **Line 124** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ma_cross = components.get('ma_cross', None)`

🔴 **Line 256** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = data.get('score', 50)`

🔴 **Line 256** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = data.get('score', 50)`

🔴 **Line 338** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `vol_distribution = components.get('volume_distribution', None)`

🔴 **Line 413** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = data.get('score', 50)`

🔴 **Line 413** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = data.get('score', 50)`

🔴 **Line 466** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `spread = components.get('spread', 50)`

🔴 **Line 495** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `mpi = components.get('mpi', 50)`

🔴 **Line 504** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `oir = components.get('oir', None)`

🔴 **Line 523** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `di = components.get('di', None)`

🔴 **Line 523** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `di = components.get('di', None)`

🔴 **Line 590** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = float(data.get('score', 50))`

🔴 **Line 590** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = float(data.get('score', 50))`

🔴 **Line 590** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = float(data.get('score', 50))`

🔴 **Line 708** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `vol_concentration = components.get('volume_concentration', None)`

🔴 **Line 708** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `vol_concentration = components.get('volume_concentration', None)`

🔴 **Line 722** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sweeps = components.get('sweeps', 50)`

🔴 **Line 732** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `icebergs = components.get('iceberg_orders', None)`

🔴 **Line 801** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = float(data.get('score', 50))`

🔴 **Line 801** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = float(data.get('score', 50))`

🔴 **Line 801** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = float(data.get('score', 50))`

🔴 **Line 835** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `funding_rate = components.get('funding_rate', 50)`

🔴 **Line 853** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `lsr = components.get('long_short_ratio', 50)`

🔴 **Line 879** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volatility = components.get('volatility', 50)`

🔴 **Line 920** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = data.get('score', 50)`

🔴 **Line 920** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = data.get('score', 50)`

🔴 **Line 1048** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `vwap = safe_float_convert(components.get('vwap', 50))`

🔴 **Line 1048** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `vwap = safe_float_convert(components.get('vwap', 50))`

🔴 **Line 1108** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `patterns = signals.get('patterns', [])`

🔴 **Line 1108** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `patterns = signals.get('patterns', [])`

🔴 **Line 1142** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `divergences = data.get('divergences', {})`

🔴 **Line 1142** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `divergences = data.get('divergences', {})`

🔴 **Line 1149** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `strength = safe_float_convert(div_data.get('strength', 0))`

🔴 **Line 1202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = data.get('score', 50)`

🔴 **Line 1202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = data.get('score', 50)`

🔴 **Line 1219** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `base_avg = self._average_components(timeframe_scores.get('base', {}))`

🔴 **Line 1219** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `base_avg = self._average_components(timeframe_scores.get('base', {}))`

🔴 **Line 1219** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `base_avg = self._average_components(timeframe_scores.get('base', {}))`

🔴 **Line 1261** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `technical_score = results.get('technical', {}).get('score', 50)`

🔴 **Line 1261** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `technical_score = results.get('technical', {}).get('score', 50)`

🔴 **Line 1297** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tech_trend = results.get('technical', {}).get('signals', {}).get('trend', 'neutral')`

🔴 **Line 1375** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sentiment = results.get('sentiment', {})`

🔴 **Line 1443** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_structure = results.get('price_structure', {})`

🔴 **Line 1443** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_structure = results.get('price_structure', {})`

🔴 **Line 1443** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_structure = results.get('price_structure', {})`

🔴 **Line 1443** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_structure = results.get('price_structure', {})`

🔴 **Line 1501** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `technical = results.get('technical', {})`

🔴 **Line 1516** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderflow = results.get('orderflow', {})`

🔴 **Line 1516** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderflow = results.get('orderflow', {})`

🔴 **Line 1516** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderflow = results.get('orderflow', {})`

🔴 **Line 1516** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderflow = results.get('orderflow', {})`

🔴 **Line 1516** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderflow = results.get('orderflow', {})`

🔴 **Line 1516** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderflow = results.get('orderflow', {})`

🔴 **Line 1519** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `elif 'pressure_score' in orderflow.get('components', {}) and orderflow['components']['pressure_score'] > 70:`

🔴 **Line 1527** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `technical = results.get('technical', {})`

### src/core/analysis/liquidation_detector.py

🔴 **Line 112** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `detected_events.sort(key=lambda x: (x.severity.value, x.timestamp), reverse=True)`

🔴 **Line 492** (pandas_inefficiency)
- Issue: iterrows() is slow - consider vectorization
- Code: `for idx, row in recent_data.iterrows():`

🔴 **Line 550** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not orderbook or not orderbook.get('bids') or not orderbook.get('asks'):`

### src/core/analysis/models.py

🔴 **Line 77** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'derived_features': self.derived_features.get('technical', {})`

🔴 **Line 93** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'derived_features': self.derived_features.get('orderbook', {})`

### src/core/analysis/portfolio.py

🔴 **Line 53** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `target = self.target_allocation.get(asset, 0)`

🔴 **Line 53** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `target = self.target_allocation.get(asset, 0)`

🔴 **Line 79** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not self.rebalancing_config.get('enabled', False):`

🔴 **Line 84** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current = current_allocation.get(asset, 0)`

🔴 **Line 96** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `free = float(data.get('free', 0))`

🔴 **Line 169** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if turnover_ratio > perf_config.get('max_turnover', 2.0):`

🔴 **Line 169** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if turnover_ratio > perf_config.get('max_turnover', 2.0):`

🔴 **Line 169** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if turnover_ratio > perf_config.get('max_turnover', 2.0):`

🔴 **Line 256** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tolerance = self.rebalancing_config.get('threshold', 0.05)`

🔴 **Line 261** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current = current_allocation.get(asset, 0)`

### src/core/component_factory.py

🔴 **Line 46** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `existing_config = self._component_configs.get(name, {})`

### src/core/component_manager.py

🔴 **Line 62** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self.components.get(name)`

🔴 **Line 62** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self.components.get(name)`

### src/core/component_registry.py

🔴 **Line 99** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._components.get(name)`

🔴 **Line 134** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `for dep in graph.get(node, set()):`

🔴 **Line 134** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `for dep in graph.get(node, set()):`

🔴 **Line 134** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `for dep in graph.get(node, set()):`

### src/core/components/manager.py

🔴 **Line 83** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `health = self._health.get(name) or ComponentHealth(`

🔴 **Line 83** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `health = self._health.get(name) or ComponentHealth(`

🔴 **Line 144** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if self._states.get(dep) != ComponentState.RUNNING:`

🔴 **Line 179** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component = self._components.get(name)`

🔴 **Line 211** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._components.get(name)`

🔴 **Line 219** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._health.get(name)`

### src/core/config/config_manager.py

🔴 **Line 181** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `value = value.get(part, {})`

🔴 **Line 254** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(exchange_config, dict) and exchange_config.get('enabled', False):`

🔴 **Line 278** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeframes = config.get('timeframes', {})`

### src/core/config/validators/binance_validator.py

🔴 **Line 221** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `rpm = rate_limits.get('requests_per_minute', 0)`

🔴 **Line 221** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `rpm = rate_limits.get('requests_per_minute', 0)`

🔴 **Line 411** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if config.get('primary', False) and config.get('data_only', True):`

🔴 **Line 411** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if config.get('primary', False) and config.get('data_only', True):`

### src/core/error/handlers.py

🔴 **Line 91** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `handlers = self._error_handlers.get(event.severity, [])`

### src/core/error/manager.py

🔴 **Line 63** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._error_counts[type(error)] = self._error_counts.get(type(error), 0) + 1`

🔴 **Line 91** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._error_counts.get(error_type, 0)`

### src/core/exchanges/base.py

🔴 **Line 159** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.session = aiohttp.ClientSession(timeout=timeout)`

🔴 **Line 242** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `except aiohttp.ClientError as e:`

🔴 **Line 389** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `page_size = min(limit, self.pagination_limits.get(data_key, 100))`

🔴 **Line 402** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `items = response.get('result', {}).get(data_key, [])`

🔴 **Line 468** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._ws_callbacks.get(channel)`

🔴 **Line 468** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._ws_callbacks.get(channel)`

🔴 **Line 487** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if msg.type == aiohttp.WSMsgType.TEXT:`

🔴 **Line 699** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `required_candles = self.min_required_candles.get(interval, 200)`

### src/core/exchanges/binance.py

🔴 **Line 54** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `exchanges_config = config.get('exchanges', {})`

🔴 **Line 437** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': ticker.get('symbol', ''),`

🔴 **Line 437** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': ticker.get('symbol', ''),`

🔴 **Line 465** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if s.get('status') == 'TRADING' and s.get('contractType') == 'PERPETUAL']`

🔴 **Line 473** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': ticker.get('symbol', ''),`

🔴 **Line 694** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if symbol_info.get('status') != 'TRADING':`

### src/core/exchanges/bybit.py

🔴 **Line 175** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.testnet = testnet_env or self.exchange_config.get('testnet', False)`

🔴 **Line 175** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.testnet = testnet_env or self.exchange_config.get('testnet', False)`

🔴 **Line 275** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.market_data_config = self.exchange_config.get('market_data', {})`

🔴 **Line 275** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.market_data_config = self.exchange_config.get('market_data', {})`

🔴 **Line 275** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.market_data_config = self.exchange_config.get('market_data', {})`

🔴 **Line 447** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.session = aiohttp.ClientSession()`

🔴 **Line 531** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession() as session:`

🔴 **Line 588** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ret_code = response.get('retCode', 'N/A')`

🔴 **Line 688** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeout = aiohttp.ClientTimeout(`

🔴 **Line 688** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeout = aiohttp.ClientTimeout(`

🔴 **Line 818** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if message.type == aiohttp.WSMsgType.TEXT:`

🔴 **Line 818** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if message.type == aiohttp.WSMsgType.TEXT:`

🔴 **Line 818** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if message.type == aiohttp.WSMsgType.TEXT:`

🔴 **Line 893** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': liq.get('s'),`

🔴 **Line 986** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbols = self.config.get('websocket', {}).get('symbols', [])`

🔴 **Line 986** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbols = self.config.get('websocket', {}).get('symbols', [])`

🔴 **Line 1223** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `api_key = self.credentials.get('apiKey')`

🔴 **Line 1223** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `api_key = self.credentials.get('apiKey')`

🔴 **Line 1490** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'id': market.get('symbol', ''),`

🔴 **Line 1490** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'id': market.get('symbol', ''),`

🔴 **Line 1583** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession() as session:`

🔴 **Line 1583** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession() as session:`

🔴 **Line 1663** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'free': float(balance.get('free', 0)),`

🔴 **Line 1769** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `for ask in result.get('a', []):`

🔴 **Line 1780** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = response.get('result', {})`

🔴 **Line 1815** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'id': str(trade.get('execId', '')),`

🔴 **Line 1897** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if response.get('retCode') == 0:`

🔴 **Line 1986** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not message.get('topic', '').startswith('allLiquidation.'):`

🔴 **Line 1986** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not message.get('topic', '').startswith('allLiquidation.'):`

🔴 **Line 1998** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = data.get('s')`

🔴 **Line 2496** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `size = float(trade.get('size', 0))`

🔴 **Line 2722** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"Open interest data: current={oi.get('current', 0)}, previous={oi.get('previous', 0)}, history entries={len(oi.get('history', []))}")`

🔴 **Line 3107** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeframe_minutes = minutes_map.get(bybit_interval, 1)`

🔴 **Line 3107** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeframe_minutes = minutes_map.get(bybit_interval, 1)`

🔴 **Line 3123** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not response or response.get('retCode') != 0:`

🔴 **Line 3295** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `credentials = config.get('api_credentials', {})`

🔴 **Line 3295** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `credentials = config.get('api_credentials', {})`

🔴 **Line 3295** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `credentials = config.get('api_credentials', {})`

🔴 **Line 3344** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `markets[symbol.get('symbol')] = symbol`

🔴 **Line 3354** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = ticker.get('symbol')`

🔴 **Line 3368** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'turnover24h': float(data.get('turnover24h', 0)),`

🔴 **Line 3411** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"API error: {response.get('retMsg', 'Unknown error')}")`

🔴 **Line 3493** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `f"Types: {{symbol: {type(market.get('symbol'))}, turnover24h: {type(market.get('turnover24h'))}}}\n"`

🔴 **Line 3493** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `f"Types: {{symbol: {type(market.get('symbol'))}, turnover24h: {type(market.get('turnover24h'))}}}\n"`

🔴 **Line 3614** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `base_url = self.config.get('ws_url', 'wss://stream.bybit.com')`

🔴 **Line 3683** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf = self.TIMEFRAME_MAP.get(timeframe, timeframe)`

🔴 **Line 3686** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `original_symbol = symbol if isinstance(symbol, str) else symbol.get('symbol', '')`

🔴 **Line 3725** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `ohlcv_data.sort(key=lambda x: x[0])`

🔴 **Line 3841** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `result = response.get('result', {})`

🔴 **Line 3841** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `result = response.get('result', {})`

🔴 **Line 3856** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `for ask in result.get('a', []):`

🔴 **Line 3867** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': int(result.get('ts', time.time() * 1000)),`

🔴 **Line 3867** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': int(result.get('ts', time.time() * 1000)),`

🔴 **Line 3922** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if response.get('retCode') != 0:`

🔴 **Line 3922** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if response.get('retCode') != 0:`

🔴 **Line 3952** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `buy_ratio = float(latest.get('buyRatio', '0.5')) * 100`

🔴 **Line 3952** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `buy_ratio = float(latest.get('buyRatio', '0.5')) * 100`

🔴 **Line 4011** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not response or response.get('retCode') != 0:`

🔴 **Line 4011** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not response or response.get('retCode') != 0:`

🔴 **Line 4045** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if tier.get('isLowestRisk', 0) == 1:`

🔴 **Line 4045** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if tier.get('isLowestRisk', 0) == 1:`

🔴 **Line 4171** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker_list = response.get('result', {}).get('list', [])`

🔴 **Line 4171** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker_list = response.get('result', {}).get('list', [])`

🔴 **Line 4171** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker_list = response.get('result', {}).get('list', [])`

🔴 **Line 4171** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker_list = response.get('result', {}).get('list', [])`

🔴 **Line 4182** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `next_funding_time = int(ticker.get('nextFundingTime', 0))`

🔴 **Line 4296** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"Open interest API response: status={response.get('retCode')}, msg={response.get('retMsg')}")`

🔴 **Line 4307** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"API error fetching open interest: code={response['retCode']}, msg={response.get('retMsg', 'No message')}")`

🔴 **Line 4307** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"API error fetching open interest: code={response['retCode']}, msg={response.get('retMsg', 'No message')}")`

🔴 **Line 4332** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = int(item.get('timestamp', 0))`

🔴 **Line 4332** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = int(item.get('timestamp', 0))`

🔴 **Line 4332** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = int(item.get('timestamp', 0))`

🔴 **Line 4353** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `history.sort(key=lambda x: x['timestamp'], reverse=True)`

🔴 **Line 4500** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `value = data.get(key)`

🔴 **Line 4558** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ws_config = self.config.get('websocket', {})`

### src/core/exchanges/bybit_demo.py

🔴 **Line 60** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.warning(f"Failed to apply for demo funds: {response.get('retMsg')}")`

### src/core/exchanges/ccxt_exchange.py

🔴 **Line 44** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.ccxt_options = self.exchange_config.get('ccxt_options', {})`

🔴 **Line 136** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.fees[symbol] = market.get('fees', {})`

🔴 **Line 136** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.fees[symbol] = market.get('fees', {})`

🔴 **Line 491** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `params = {'category': 'linear', 'symbol': self.market_id_map.get(symbol, symbol)}`

🔴 **Line 541** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `params = {'category': 'linear', 'symbol': self.market_id_map.get(symbol, symbol)}`

🔴 **Line 541** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `params = {'category': 'linear', 'symbol': self.market_id_map.get(symbol, symbol)}`

🔴 **Line 604** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': self.market_id_map.get(symbol, symbol),`

🔴 **Line 616** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = int(item.get('timestamp', 0))`

🔴 **Line 625** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `history_list.sort(key=lambda x: x['timestamp'], reverse=True)`

🔴 **Line 893** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'open_interest_history': open_interest_history.get('history', []) if open_interest_history else [],`

🔴 **Line 893** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'open_interest_history': open_interest_history.get('history', []) if open_interest_history else [],`

### src/core/exchanges/coinbase.py

🔴 **Line 147** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'free': float(account.get('available_balance', {}).get('value', 0)),`

🔴 **Line 184** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession() as session:`

🔴 **Line 241** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'bids': [[float(bid[0]), float(bid[1])] for bid in response.get('bids', [])],`

🔴 **Line 242** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'asks': [[float(ask[0]), float(ask[1])] for ask in response.get('asks', [])],`

🔴 **Line 245** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'nonce': response.get('sequence')`

🔴 **Line 261** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'id': trade.get('trade_id', str(i)),`

🔴 **Line 375** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'size': float(position.get('position_size', 0)),`

🔴 **Line 396** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'status': response.get('status', 'unknown'),`

🔴 **Line 430** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'price': self._get_precision(product.get('quote_increment', '0.00000001')),`

### src/core/exchanges/exchange_mappings.py

🔴 **Line 228** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return CCXT_TO_EXCHANGE_MAPPINGS[exchange_id]['timeframe'].get(timeframe, timeframe)`

🔴 **Line 228** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return CCXT_TO_EXCHANGE_MAPPINGS[exchange_id]['timeframe'].get(timeframe, timeframe)`

🔴 **Line 228** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return CCXT_TO_EXCHANGE_MAPPINGS[exchange_id]['timeframe'].get(timeframe, timeframe)`

🔴 **Line 228** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return CCXT_TO_EXCHANGE_MAPPINGS[exchange_id]['timeframe'].get(timeframe, timeframe)`

🔴 **Line 228** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return CCXT_TO_EXCHANGE_MAPPINGS[exchange_id]['timeframe'].get(timeframe, timeframe)`

🔴 **Line 228** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return CCXT_TO_EXCHANGE_MAPPINGS[exchange_id]['timeframe'].get(timeframe, timeframe)`

🔴 **Line 228** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return CCXT_TO_EXCHANGE_MAPPINGS[exchange_id]['timeframe'].get(timeframe, timeframe)`

🔴 **Line 379** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `standardized['side'] = side_mappings.get(standardized['side'], 'none')`

🔴 **Line 379** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `standardized['side'] = side_mappings.get(standardized['side'], 'none')`

### src/core/exchanges/factory.py

🔴 **Line 38** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if exchange_id == 'bybit' and config.get('demo_mode', False):`

🔴 **Line 51** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `exchange_class = cls.EXCHANGE_MAP.get(exchange_id)`

🔴 **Line 51** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `exchange_class = cls.EXCHANGE_MAP.get(exchange_id)`

🔴 **Line 76** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config['websocket']['testnet_endpoint'] = config.get('testnet_endpoint', 'wss://stream-testnet.bybit.com/v5/public')`

### src/core/exchanges/hyperliquid.py

🔴 **Line 84** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with self.session.post(f"{self.base_url}", json={"type": "allMids"}) as response:`

🔴 **Line 96** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with self.session.post(f"{self.base_url}", json={"type": "l2Book", "coin": coin}) as book_response:`

🔴 **Line 96** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with self.session.post(f"{self.base_url}", json={"type": "l2Book", "coin": coin}) as book_response:`

🔴 **Line 96** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with self.session.post(f"{self.base_url}", json={"type": "l2Book", "coin": coin}) as book_response:`

🔴 **Line 143** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with self.session.post(f"{self.base_url}", json={"type": "l2Book", "coin": coin}) as response:`

🔴 **Line 180** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with self.session.post(f"{self.base_url}", json={"type": "recentTrades", "coin": coin}) as response:`

🔴 **Line 191** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'id': str(trade.get('tid', '')),`

🔴 **Line 343** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with self.session.post(f"{self.base_url}", json={"type": "meta"}) as response:`

### src/core/exchanges/liquidation_collector.py

🔴 **Line 185** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `for liq in liquidations.get('data', []):`

🔴 **Line 185** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `for liq in liquidations.get('data', []):`

🔴 **Line 185** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `for liq in liquidations.get('data', []):`

🔴 **Line 227** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not message.get('topic', '').startswith('allLiquidation'):`

🔴 **Line 227** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not message.get('topic', '').startswith('allLiquidation'):`

🔴 **Line 227** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not message.get('topic', '').startswith('allLiquidation'):`

🔴 **Line 239** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not liq.get('s'):`

### src/core/exchanges/manager.py

🔴 **Line 45** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not config.get('enabled', False):`

🔴 **Line 101** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if exchange_config.get('primary', False) and exchange_id in self.exchanges:`

🔴 **Line 224** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(obj, aiohttp.ClientSession):`

🔴 **Line 224** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(obj, aiohttp.ClientSession):`

🔴 **Line 361** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `limit = tf_config.get('required', 1000)`

🔴 **Line 395** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'name': exchange_config.get('name', exchange_id),`

🔴 **Line 442** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not config.get('enabled', False):`

🔴 **Line 532** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"Ticker data for {symbol}: volume={ticker.get('baseVolume', 'N/A')}, turnover={ticker.get('quoteVolume', 'N/A')}")`

🔴 **Line 532** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"Ticker data for {symbol}: volume={ticker.get('baseVolume', 'N/A')}, turnover={ticker.get('quoteVolume', 'N/A')}")`

🔴 **Line 552** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'last': float(ticker.get('last', 0)),`

🔴 **Line 552** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'last': float(ticker.get('last', 0)),`

🔴 **Line 552** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'last': float(ticker.get('last', 0)),`

🔴 **Line 881** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'nextFundingTime': ticker.get('nextFundingTime', None),`

🔴 **Line 938** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if response and response.get('retCode') == 0:`

🔴 **Line 938** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if response and response.get('retCode') == 0:`

🔴 **Line 979** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return status.get('status') == 'ok' or status.get('online', False)`

🔴 **Line 979** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return status.get('status') == 'ok' or status.get('online', False)`

### src/core/exchanges/rate_limiter.py

🔴 **Line 85** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `endpoint_limit = self.endpoint_limits.get(endpoint_key, self.endpoint_limits['default'])`

🔴 **Line 85** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `endpoint_limit = self.endpoint_limits.get(endpoint_key, self.endpoint_limits['default'])`

### src/core/exchanges/websocket_manager.py

🔴 **Line 49** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ws_logging_config = config.get('market_data', {}).get('websocket_logging', {})`

🔴 **Line 162** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `session = aiohttp.ClientSession()`

🔴 **Line 206** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if msg.type == aiohttp.WSMsgType.TEXT:`

🔴 **Line 243** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `elif msg.type == aiohttp.WSMsgType.ERROR:`

🔴 **Line 368** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `queue = self.message_queues.get(symbol)`

🔴 **Line 368** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `queue = self.message_queues.get(symbol)`

🔴 **Line 368** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `queue = self.message_queues.get(symbol)`

🔴 **Line 368** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `queue = self.message_queues.get(symbol)`

🔴 **Line 374** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `message = await queue.get()`

🔴 **Line 501** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if "ret_msg" in data and data.get("ret_msg") == "pong":`

### src/core/formatting.py

🔴 **Line 193** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `comp_name = component_names.get(comp_key, comp_key.replace('_', ' ').title())`

🔴 **Line 269** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `comp_name = component_names.get(comp_key, comp_key.replace('_', ' ').title())`

🔴 **Line 319** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = analysis_result.get('score', analysis_result.get('confluence_score', 0))`

🔴 **Line 319** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = analysis_result.get('score', analysis_result.get('confluence_score', 0))`

🔴 **Line 339** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `results = analysis_result.get('results', {})`

🔴 **Line 452** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = analysis_result.get('score', analysis_result.get('confluence_score', 0))`

### src/core/formatting/formatter.py

🔴 **Line 198** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = analysis_result.get('score', analysis_result.get('confluence_score', 0))`

🔴 **Line 198** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = analysis_result.get('score', analysis_result.get('confluence_score', 0))`

🔴 **Line 826** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = weights.get(component, 0)`

🔴 **Line 1003** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `indicator_score = indicator_data.get('score', 0)`

🔴 **Line 1003** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `indicator_score = indicator_data.get('score', 0)`

🔴 **Line 1003** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `indicator_score = indicator_data.get('score', 0)`

🔴 **Line 1003** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `indicator_score = indicator_data.get('score', 0)`

🔴 **Line 1070** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `indicator_score = indicator_data.get('score', 0)`

🔴 **Line 1070** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `indicator_score = indicator_data.get('score', 0)`

🔴 **Line 1102** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sorted_components.append((key, value.get('score', 0)))`

🔴 **Line 1781** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = weights.get(component, 0)`

🔴 **Line 1893** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `display_name = interp_data.get('display_name', interp_data.get('component', 'Unknown')).replace('_', ' ').title()`

🔴 **Line 2055** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `div_value = divergence_adjustments.get(component, 0.0)`

🔴 **Line 2055** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `div_value = divergence_adjustments.get(component, 0.0)`

🔴 **Line 2055** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `div_value = divergence_adjustments.get(component, 0.0)`

🔴 **Line 2189** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = weights.get(component, 0)`

🔴 **Line 2301** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `display_name = interp_data.get('display_name', interp_data.get('component', 'Unknown')).replace('_', ' ').title()`

🔴 **Line 2545** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sentiment_score = components.get('sentiment', 50.0)`

🔴 **Line 2545** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sentiment_score = components.get('sentiment', 50.0)`

### src/core/interpretation/interpretation_manager.py

🔴 **Line 46** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_overview = market_data.get('market_overview', {})`

🔴 **Line 268** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `dict_component_name = item.get('component', f"{source_component}_{i}")`

🔴 **Line 404** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `nested_text = interpretation_data.get('text',`

🔴 **Line 585** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `reliability = base_reliability.get(component_type, 0.7)`

🔴 **Line 585** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `reliability = base_reliability.get(component_type, 0.7)`

🔴 **Line 1041** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `}.get(interpretation.severity, "⚪ UNKNOWN")`

🔴 **Line 1041** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `}.get(interpretation.severity, "⚪ UNKNOWN")`

🔴 **Line 1041** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `}.get(interpretation.severity, "⚪ UNKNOWN")`

🔴 **Line 1041** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `}.get(interpretation.severity, "⚪ UNKNOWN")`

🔴 **Line 1092** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'market_context': serialized_metadata.get('market_context'),`

🔴 **Line 1174** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'market_enhanced': interpretation.metadata.get('context_enhanced', False),`

🔴 **Line 1259** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `}.get(interpretation.severity, 1.0)`

🔴 **Line 1364** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `}.get(risk_level, 0.5)`

🔴 **Line 1500** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component_types[comp_type] = component_types.get(comp_type, 0) + 1`

🔴 **Line 1523** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'enhanced_interpretations': sum(1 for i in interpretation_set.interpretations if i.metadata.get('context_enhanced', False)),`

🔴 **Line 1523** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'enhanced_interpretations': sum(1 for i in interpretation_set.interpretations if i.metadata.get('context_enhanced', False)),`

🔴 **Line 1523** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'enhanced_interpretations': sum(1 for i in interpretation_set.interpretations if i.metadata.get('context_enhanced', False)),`

🔴 **Line 1523** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'enhanced_interpretations': sum(1 for i in interpretation_set.interpretations if i.metadata.get('context_enhanced', False)),`

### src/core/lifecycle/manager.py

🔴 **Line 121** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `lifecycle = self._components.get(name)`

🔴 **Line 211** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `dep_lifecycle = self._components.get(dep)`

🔴 **Line 211** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `dep_lifecycle = self._components.get(dep)`

🔴 **Line 211** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `dep_lifecycle = self._components.get(dep)`

🔴 **Line 211** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `dep_lifecycle = self._components.get(dep)`

### src/core/market/data_manager.py

🔴 **Line 36** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'weight': float(tf_config.get('weight', 0.25)),  # Default equal weights`

🔴 **Line 52** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.update_intervals = config.get('data_collection', {}).get('update_intervals', {`

🔴 **Line 52** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.update_intervals = config.get('data_collection', {}).get('update_intervals', {`

🔴 **Line 74** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `interval = str(tf_config.get('interval'))  # Convert to string for consistency`

🔴 **Line 75** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = float(tf_config.get('weight', 0.0))`

🔴 **Line 118** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if timeframe in market_data.get('ohlcv', {}):`

🔴 **Line 118** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if timeframe in market_data.get('ohlcv', {}):`

🔴 **Line 118** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if timeframe in market_data.get('ohlcv', {}):`

🔴 **Line 118** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if timeframe in market_data.get('ohlcv', {}):`

🔴 **Line 196** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._market_data.get(symbol)`

🔴 **Line 196** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._market_data.get(symbol)`

🔴 **Line 196** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._market_data.get(symbol)`

🔴 **Line 271** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_data = self._market_data.get(symbol, {})`

🔴 **Line 271** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_data = self._market_data.get(symbol, {})`

🔴 **Line 287** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_data = self._market_data.get(symbol, {})`

🔴 **Line 287** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_data = self._market_data.get(symbol, {})`

🔴 **Line 378** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_data = self._market_data.get(symbol, {})`

🔴 **Line 378** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_data = self._market_data.get(symbol, {})`

🔴 **Line 378** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_data = self._market_data.get(symbol, {})`

🔴 **Line 378** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_data = self._market_data.get(symbol, {})`

🔴 **Line 394** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_data = self._market_data.get(symbol, {})`

🔴 **Line 394** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_data = self._market_data.get(symbol, {})`

🔴 **Line 410** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_data = self._market_data.get(symbol, {})`

🔴 **Line 410** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_data = self._market_data.get(symbol, {})`

### src/core/market/market_data_manager.py

🔴 **Line 46** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._cache_enabled = self.config.get('market_data', {}).get('cache', {}).get('enabled', True)`

🔴 **Line 46** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._cache_enabled = self.config.get('market_data', {}).get('cache', {}).get('enabled', True)`

🔴 **Line 134** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if ws_config.get('enabled', True) and not self.delay_websocket:`

🔴 **Line 278** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current_time - self.stats['last_refresh_log'].get(symbol, 0) > log_threshold):`

🔴 **Line 313** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component_time = last_refresh['components'].get(component, 0)`

🔴 **Line 322** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf_time = kline_times.get(tf, 0)`

🔴 **Line 498** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `oi_data = market_data.get('open_interest')`

🔴 **Line 498** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `oi_data = market_data.get('open_interest')`

🔴 **Line 498** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `oi_data = market_data.get('open_interest')`

🔴 **Line 498** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `oi_data = market_data.get('open_interest')`

🔴 **Line 498** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `oi_data = market_data.get('open_interest')`

🔴 **Line 546** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if market_data.get('ticker') and 'open_interest' in market_data['ticker']:`

🔴 **Line 546** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if market_data.get('ticker') and 'open_interest' in market_data['ticker']:`

🔴 **Line 546** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if market_data.get('ticker') and 'open_interest' in market_data['ticker']:`

🔴 **Line 595** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if market_data.get('ticker'):`

🔴 **Line 595** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if market_data.get('ticker'):`

🔴 **Line 603** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if (price <= 0 or volume_24h <= 0) and market_data.get('kline'):`

🔴 **Line 655** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': int(oi_record.get('timestamp', now)),`

🔴 **Line 663** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `history_list.sort(key=lambda x: x['timestamp'], reverse=True)`

🔴 **Line 688** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'is_synthetic': len(history_list) == 1 and history_list[0].get('data_source') == 'synthetic_fallback',`

🔴 **Line 924** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ws_log_level = self.config.get('market_data', {}).get('websocket_log_level', 'INFO')`

🔴 **Line 924** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ws_log_level = self.config.get('market_data', {}).get('websocket_log_level', 'INFO')`

🔴 **Line 934** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data = message.get("data", {})`

🔴 **Line 1354** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = int(orderbook_data.get('ts', time.time() * 1000))`

🔴 **Line 1354** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = int(orderbook_data.get('ts', time.time() * 1000))`

🔴 **Line 1448** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'price': float(trade.get('p', trade.get('price', 0))),`

🔴 **Line 1467** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `existing_trades = self.data_cache[symbol].get('trades', [])`

🔴 **Line 1484** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trade_ids.add(t.get('id'))`

🔴 **Line 1484** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trade_ids.add(t.get('id'))`

🔴 **Line 1551** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': liq_data.get('s', symbol),`

🔴 **Line 1643** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_data['ticker'] = self.data_cache[symbol].get('ticker')`

🔴 **Line 1698** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_summary = ', '.join([f"{tf}: {len(df)}" for tf, df in market_data.get('ohlcv', {}).items()])`

🔴 **Line 1698** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_summary = ', '.join([f"{tf}: {len(df)}" for tf, df in market_data.get('ohlcv', {}).items()])`

🔴 **Line 1698** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_summary = ', '.join([f"{tf}: {len(df)}" for tf, df in market_data.get('ohlcv', {}).items()])`

🔴 **Line 1699** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"Market data for {symbol} includes: ticker={bool(market_data.get('ticker'))}, "`

🔴 **Line 1700** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `f"orderbook={bool(market_data.get('orderbook'))}, "`

🔴 **Line 1932** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': int(oi_record.get('timestamp', timestamp)),`

🔴 **Line 1932** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': int(oi_record.get('timestamp', timestamp)),`

🔴 **Line 1932** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': int(oi_record.get('timestamp', timestamp)),`

🔴 **Line 1932** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': int(oi_record.get('timestamp', timestamp)),`

🔴 **Line 1957** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `history.sort(key=lambda x: x['timestamp'], reverse=True)`

### src/core/market/market_regime_detector.py

🔴 **Line 168** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv = market_data.get('ohlcv', {})`

🔴 **Line 199** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `bid_volume = sum(float(level[1]) for level in orderbook.get('bids', [])[:5])`

🔴 **Line 199** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `bid_volume = sum(float(level[1]) for level in orderbook.get('bids', [])[:5])`

🔴 **Line 200** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ask_volume = sum(float(level[1]) for level in orderbook.get('asks', [])[:5])`

🔴 **Line 371** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv = market_data.get('ohlcv', {})`

🔴 **Line 371** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv = market_data.get('ohlcv', {})`

🔴 **Line 502** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'dynamic_thresholds': traditional_result.get('dynamic_thresholds', {}),`

### src/core/market/smart_intervals.py

🔴 **Line 136** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `multiplier = component_multipliers.get(component, 1.0)`

🔴 **Line 136** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `multiplier = component_multipliers.get(component, 1.0)`

🔴 **Line 136** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `multiplier = component_multipliers.get(component, 1.0)`

🔴 **Line 136** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `multiplier = component_multipliers.get(component, 1.0)`

🔴 **Line 225** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data['bybit'].get('ticker', {})`

### src/core/market/top_symbols.py

🔴 **Line 47** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.market_config = config.get('market', {}).get('symbols', {})`

🔴 **Line 148** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbols = self._symbols_cache.get('symbols', [])`

🔴 **Line 202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"Sample raw symbols: {[m.get('symbol','') for m in raw_markets[:5]]}")`

🔴 **Line 202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"Sample raw symbols: {[m.get('symbol','') for m in raw_markets[:5]]}")`

🔴 **Line 205** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_symbols = self.market_config.get('max_symbols', 10)`

🔴 **Line 217** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market.get('symbol', '')`

🔴 **Line 217** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market.get('symbol', '')`

🔴 **Line 219** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `turnover = float(market.get('quoteVolume', market.get('turnover24h', 0)))`

🔴 **Line 227** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol_strings = [m.get('symbol', '') for m in sorted_markets if m.get('symbol')]`

🔴 **Line 227** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol_strings = [m.get('symbol', '') for m in sorted_markets if m.get('symbol')]`

🔴 **Line 243** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market.get('symbol', '')`

🔴 **Line 262** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `min_turnover = self.market_config.get('min_turnover', 500000)`

🔴 **Line 502** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.warning(f"Missing required field '{field}' in symbol {entry.get('symbol', 'unknown')}")`

🔴 **Line 502** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.warning(f"Missing required field '{field}' in symbol {entry.get('symbol', 'unknown')}")`

🔴 **Line 502** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.warning(f"Missing required field '{field}' in symbol {entry.get('symbol', 'unknown')}")`

🔴 **Line 519** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.warning(f"Type conversion failed for {e.get('symbol')}: {str(conv_error)}")`

🔴 **Line 581** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = ticker.get('symbol', '')`

🔴 **Line 622** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `valid_markets.sort(key=lambda x: x.get('turnover_for_sorting', 0), reverse=True)`

🔴 **Line 622** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `valid_markets.sort(key=lambda x: x.get('turnover_for_sorting', 0), reverse=True)`

🔴 **Line 622** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `valid_markets.sort(key=lambda x: x.get('turnover_for_sorting', 0), reverse=True)`

🔴 **Line 622** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `valid_markets.sort(key=lambda x: x.get('turnover_for_sorting', 0), reverse=True)`

🔴 **Line 628** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `total_turnover = sum(market.get('turnover_for_sorting', 0) for market in valid_markets)`

🔴 **Line 633** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market.get('symbol', '')`

🔴 **Line 633** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market.get('symbol', '')`

🔴 **Line 834** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 834** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 914** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbols_data.sort(key=lambda x: x['turnover_24h'], reverse=True)`

### src/core/models/interpretation_schema.py

🔴 **Line 162** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `for interp_data in data.get('interpretations', []):`

🔴 **Line 171** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `metadata=interp_data.get('metadata', {})`

### src/core/monitoring/binance_monitor.py

🔴 **Line 69** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.monitoring_config = config.get('monitoring', {})`

🔴 **Line 159** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `memory_info = psutil.virtual_memory()`

🔴 **Line 160** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `cpu_percent = psutil.cpu_percent(interval=1)`

### src/core/reporting/export_manager.py

🔴 **Line 137** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = data.get('symbol', 'unknown')`

🔴 **Line 137** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = data.get('symbol', 'unknown')`

### src/core/reporting/interactive_web_report.py

🔴 **Line 74** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(report_path, 'w', encoding='utf-8') as f:`

🔴 **Line 94** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(metadata_path, 'w') as f:`

🔴 **Line 319** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"navigation": report_data.get("navigation", {}),`

🔴 **Line 319** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"navigation": report_data.get("navigation", {}),`

🔴 **Line 404** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"navigation": metadata.get("navigation", {}),`

### src/core/reporting/pdf_generator.py

🔴 **Line 246** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._max_retries = self.config.get('pdf_generation', {}).get('max_retries', 3)`

🔴 **Line 381** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', 'UNKNOWN')`

🔴 **Line 381** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', 'UNKNOWN')`

🔴 **Line 381** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', 'UNKNOWN')`

🔴 **Line 381** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', 'UNKNOWN')`

🔴 **Line 564** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', '')`

🔴 **Line 564** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', '')`

🔴 **Line 564** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', '')`

🔴 **Line 668** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', 'UNKNOWN')`

🔴 **Line 668** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', 'UNKNOWN')`

🔴 **Line 973** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `key=lambda x: abs(float(x[1].get("score", 0))),`

🔴 **Line 973** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `key=lambda x: abs(float(x[1].get("score", 0))),`

🔴 **Line 983** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `scores = [float(comp[1].get("score", 0)) for comp in sorted_components]`

🔴 **Line 989** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `impacts.append(float(comp[1].get("impact", 0)))`

🔴 **Line 989** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `impacts.append(float(comp[1].get("impact", 0)))`

🔴 **Line 1573** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `target_name = target.get("name", f"Target {i+1}")`

🔴 **Line 1909** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get("symbol", "UNKNOWN")`

🔴 **Line 2031** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `comp_value = components.get(key, {})`

🔴 **Line 2035** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = comp_value.get("score", 50)`

🔴 **Line 2057** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get("symbol", "UNKNOWN")`

🔴 **Line 2117** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score_value = float(data.get("score", 0))`

🔴 **Line 2117** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score_value = float(data.get("score", 0))`

🔴 **Line 2202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `raw_interpretations = signal_data.get("market_interpretations", signal_data.get("insights", []))`

🔴 **Line 2202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `raw_interpretations = signal_data.get("market_interpretations", signal_data.get("insights", []))`

🔴 **Line 2241** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `insights = [item.get('interpretation', '') for item in insights]`

🔴 **Line 2241** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `insights = [item.get('interpretation', '') for item in insights]`

🔴 **Line 2241** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `insights = [item.get('interpretation', '') for item in insights]`

🔴 **Line 2252** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trade_params = signal_data.get("trade_params", {})`

🔴 **Line 2274** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `target_price = target_data.get("price", 0)`

🔴 **Line 2301** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `target_price = target_data.get("price", 0)`

🔴 **Line 2589** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `report_type = market_data.get("report_type", "MARKET").upper()`

🔴 **Line 2589** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `report_type = market_data.get("report_type", "MARKET").upper()`

🔴 **Line 2832** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = item.get("symbol", "N/A")`

🔴 **Line 2832** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = item.get("symbol", "N/A")`

🔴 **Line 3002** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal.get("symbol", "N/A")`

🔴 **Line 3002** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal.get("symbol", "N/A")`

🔴 **Line 3100** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `title = item.get("title", "N/A")`

🔴 **Line 3287** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not isinstance(performers.get("gainers"), list):`

🔴 **Line 3287** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not isinstance(performers.get("gainers"), list):`

🔴 **Line 3301** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `change = item.get("change_percent", 0)`

🔴 **Line 3301** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `change = item.get("change_percent", 0)`

🔴 **Line 3318** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"total_analyzed": performers.get("total_analyzed", len(gainers) + len(losers)),`

🔴 **Line 3330** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `change = item.get("change_percent", 0)`

🔴 **Line 3437** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(template_path, "r") as f:`

🔴 **Line 3646** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `watermark_text = market_data.get("watermark_text", "VIRTUOSO CRYPTO")`

🔴 **Line 4046** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(html_path, 'r', encoding='utf-8') as f:`

🔴 **Line 4231** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', 'UNKNOWN')`

🔴 **Line 4292** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', 'UNKNOWN')`

🔴 **Line 4353** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `raw_interpretations = signal_data.get('market_interpretations', [])`

🔴 **Line 4378** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component = interp.get('display_name', interp.get('component', 'Unknown'))`

🔴 **Line 4378** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component = interp.get('display_name', interp.get('component', 'Unknown'))`

🔴 **Line 4804** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `target_name = target.get("name", f"Target {i+1}")`

🔴 **Line 5060** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `premiums = futures_premium_data.get('premiums', {})`

🔴 **Line 5060** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `premiums = futures_premium_data.get('premiums', {})`

🔴 **Line 5184** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `quarterly_futures = futures_premium_data.get('quarterly_futures', {})`

🔴 **Line 5202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sorted_contracts = sorted(contracts, key=lambda x: x.get('months_to_expiry', 12))`

🔴 **Line 5202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sorted_contracts = sorted(contracts, key=lambda x: x.get('months_to_expiry', 12))`

🔴 **Line 5208** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `months = contract.get('months_to_expiry', 0)`

### src/core/reporting/report_manager.py

🔴 **Line 56** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.base_dir = self.config.get('base_dir', os.path.join(os.getcwd(), 'reports'))`

🔴 **Line 56** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.base_dir = self.config.get('base_dir', os.path.join(os.getcwd(), 'reports'))`

🔴 **Line 65** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `template_dir = self.config.get('template_dir')`

🔴 **Line 133** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"""Initialize HTTP session for requests."""`

🔴 **Line 135** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.session = aiohttp.ClientSession()`

🔴 **Line 170** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', 'UNKNOWN')`

🔴 **Line 170** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', 'UNKNOWN')`

🔴 **Line 170** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', 'UNKNOWN')`

🔴 **Line 276** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `form_data = aiohttp.FormData()`

🔴 **Line 304** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `file_handle = open(file_path, 'rb')`

🔴 **Line 316** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with self.session.post(webhook_url, data=form_data) as response:`

🔴 **Line 363** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', 'Unknown')`

🔴 **Line 484** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(html_path, 'w', encoding='utf-8') as f:`

### src/core/reporting/test_report_manager.py

🔴 **Line 130** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if signal_data.get('signal_type', '').upper() == 'BULLISH':`

🔴 **Line 141** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `entry = signal_data.get('entry_price', 0)`

🔴 **Line 219** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')`

### src/core/resource_manager.py

🔴 **Line 91** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `available_memory = psutil.virtual_memory().available`

🔴 **Line 127** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `memory_percent=psutil.virtual_memory().percent,`

🔴 **Line 128** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `cpu_percent=psutil.cpu_percent(),`

### src/core/resource_monitor.py

🔴 **Line 40** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `memory_task = loop.run_in_executor(None, lambda: psutil.virtual_memory().percent)`

🔴 **Line 41** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `cpu_task = loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=1))`

🔴 **Line 81** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `mem_task = loop.run_in_executor(None, lambda: psutil.virtual_memory().percent)`

🔴 **Line 82** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `cpu_task = loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=1))`

### src/core/resources/manager.py

🔴 **Line 57** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._operation_counts[component] = self._operation_counts.get(component, 0) + 1`

🔴 **Line 57** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._operation_counts[component] = self._operation_counts.get(component, 0) + 1`

🔴 **Line 75** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'memory_usage_mb': self._memory_usage.get(component, 0.0),`

🔴 **Line 75** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'memory_usage_mb': self._memory_usage.get(component, 0.0),`

### src/core/scoring/unified_scoring_framework.py

🔴 **Line 25** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.debug_mode = kwargs.get('debug_mode', False)`

🔴 **Line 25** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.debug_mode = kwargs.get('debug_mode', False)`

🔴 **Line 52** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self.config.get(key, default)`

### src/core/state_manager.py

🔴 **Line 97** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `while self._states.get(component_name) != target_state:`

🔴 **Line 136** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `history = self._history.get(component_name, [])`

🔴 **Line 136** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `history = self._history.get(component_name, [])`

🔴 **Line 136** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `history = self._history.get(component_name, [])`

🔴 **Line 148** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `validators = self._transition_validators.get((from_state, to_state), [])`

🔴 **Line 158** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `handlers = self._state_handlers.get(state, [])`

🔴 **Line 158** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `handlers = self._state_handlers.get(state, [])`

### src/core/system_manager.py

🔴 **Line 88** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self.components.get(name)`

### src/core/validation/rules.py

🔴 **Line 86** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = data.get('symbol', '')`

### src/core/validation/service.py

🔴 **Line 71** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `validator = self._validators.get(context.data_type)`

🔴 **Line 71** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `validator = self._validators.get(context.data_type)`

🔴 **Line 94** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `rules = self._rules.get(context.data_type, [])`

🔴 **Line 186** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `validator = self._validators.get(context.data_type)`

🔴 **Line 186** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `validator = self._validators.get(context.data_type)`

🔴 **Line 209** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `rules = self._rules.get(context.data_type, [])`

🔴 **Line 262** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `*[rule.check(item) for rule in self._rules.get(item['symbol'], [])]`

🔴 **Line 262** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `*[rule.check(item) for rule in self._rules.get(item['symbol'], [])]`

### src/dashboard/dashboard_integration.py

🔴 **Line 175** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'price': market_data.get('ticker', {}).get('last', 0),`

🔴 **Line 175** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'price': market_data.get('ticker', {}).get('last', 0),`

🔴 **Line 211** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signals = self._dashboard_data.get('signals', [])`

🔴 **Line 214** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if signal.get('score', 0) > 75:  # High confidence threshold`

🔴 **Line 265** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'alpha_opportunities': len(self._dashboard_data.get('alpha_opportunities', [])),`

🔴 **Line 345** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = signal.get('score', 50)`

🔴 **Line 366** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = signal.get('score', 50)`

🔴 **Line 366** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = signal.get('score', 50)`

🔴 **Line 366** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = signal.get('score', 50)`

🔴 **Line 366** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = signal.get('score', 50)`

🔴 **Line 409** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signals_data = self._dashboard_data.get('signals', [])`

🔴 **Line 415** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': signal.get('symbol'),`

🔴 **Line 415** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': signal.get('symbol'),`

🔴 **Line 440** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'medium': len([s for s in signals_data if s.get('strength') == 'medium']),`

🔴 **Line 441** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'weak': len([s for s in signals_data if s.get('strength') == 'weak'])`

🔴 **Line 444** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'total': len(self._dashboard_data.get('alerts', [])),`

🔴 **Line 446** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'warning': len([a for a in self._dashboard_data.get('alerts', []) if a.get('severity') == 'WARNING'])`

🔴 **Line 449** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'total': len(self._dashboard_data.get('alpha_opportunities', [])),`

🔴 **Line 451** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'medium_confidence': len([o for o in self._dashboard_data.get('alpha_opportunities', []) if 70 <= o.get('confidence', 0) < 85])`

🔴 **Line 453** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'system_status': self._dashboard_data.get('system_status', {}),`

🔴 **Line 481** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signals = self._dashboard_data.get('signals', [])`

🔴 **Line 484** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal.get('symbol')`

🔴 **Line 538** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 538** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 600** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbols_data.sort(key=lambda x: x['turnover_24h'], reverse=True)`

### src/dashboard/dashboard_manager.py

🔴 **Line 215** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `signal_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)`

🔴 **Line 221** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(file_path, 'r') as f:`

### src/dashboard/integration_service.py

🔴 **Line 14** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.base_url = config.get('dashboard_url', 'http://localhost:8000')`

🔴 **Line 14** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.base_url = config.get('dashboard_url', 'http://localhost:8000')`

🔴 **Line 44** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"symbol": signal_data.get('symbol'),`

🔴 **Line 79** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = components.get('momentum', {}).get('score', 50.0)`

### src/data_acquisition/binance/binance_exchange.py

🔴 **Line 45** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `binance_config = config.get('exchanges', {}).get('binance', {})`

🔴 **Line 45** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `binance_config = config.get('exchanges', {}).get('binance', {})`

🔴 **Line 45** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `binance_config = config.get('exchanges', {}).get('binance', {})`

🔴 **Line 671** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'futures_markets': len([m for m in markets.values() if m.get('future', False)]),`

### src/data_acquisition/binance/data_fetcher.py

🔴 **Line 73** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.binance_config = config.get('exchanges', {}).get('binance', {})`

🔴 **Line 73** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.binance_config = config.get('exchanges', {}).get('binance', {})`

🔴 **Line 123** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `api_credentials = self.binance_config.get('api_credentials', {})`

🔴 **Line 161** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `if self._is_circuit_breaker_open():`

### src/data_acquisition/binance/futures_client.py

🔴 **Line 64** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.session = aiohttp.ClientSession()`

🔴 **Line 99** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"""Apply rate limiting between requests."""`

🔴 **Line 99** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"""Apply rate limiting between requests."""`

🔴 **Line 159** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `retry_after = int(response.headers.get('Retry-After', 60))`

🔴 **Line 180** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `except aiohttp.ClientError as e:`

🔴 **Line 180** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `except aiohttp.ClientError as e:`

🔴 **Line 180** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `except aiohttp.ClientError as e:`

🔴 **Line 400** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.info(f"Leverage bracket for {symbol}: max leverage {standardized.get('maxLeverage', 'N/A')}x")`

🔴 **Line 400** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.info(f"Leverage bracket for {symbol}: max leverage {standardized.get('maxLeverage', 'N/A')}x")`

🔴 **Line 400** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.info(f"Leverage bracket for {symbol}: max leverage {standardized.get('maxLeverage', 'N/A')}x")`

🔴 **Line 400** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.info(f"Leverage bracket for {symbol}: max leverage {standardized.get('maxLeverage', 'N/A')}x")`

### src/data_acquisition/binance/websocket_handler.py

🔴 **Line 270** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `handler = self.stream_handlers.get(stream_type)`

🔴 **Line 282** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `result = message.get('result')`

🔴 **Line 429** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = data.get('s')`

🔴 **Line 429** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = data.get('s')`

### src/data_processing/data_batcher.py

🔴 **Line 36** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.batch_size = int(self.config.get('batch_size', 100))`

🔴 **Line 36** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.batch_size = int(self.config.get('batch_size', 100))`

🔴 **Line 36** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.batch_size = int(self.config.get('batch_size', 100))`

🔴 **Line 189** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return len(self.batches.get(data_type, []))`

🔴 **Line 200** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return bool(self.batches.get(data_type, []))`

🔴 **Line 200** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return bool(self.batches.get(data_type, []))`

### src/data_processing/data_manager.py

🔴 **Line 145** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_klines = self.config.get('max_klines', 1000)`

🔴 **Line 172** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_trades = self.config.get('max_trades', 1000)`

🔴 **Line 278** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = data.get('symbol')`

🔴 **Line 326** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_trades = self.config.get('max_trades', 1000)`

🔴 **Line 340** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeframe = kline.get('timeframe', 'base')`

🔴 **Line 399** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._market_data.get(symbol, {})`

🔴 **Line 399** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._market_data.get(symbol, {})`

🔴 **Line 411** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = symbol_data.get('ticker', {})`

🔴 **Line 411** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = symbol_data.get('ticker', {})`

### src/data_processing/data_processor.py

🔴 **Line 88** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'interval': tf_data.get('interval'),`

🔴 **Line 182** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'data': data.get('data', pd.DataFrame()),`

🔴 **Line 277** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `pipeline_config = config.get('data_processing', {}).get('pipeline', [])`

🔴 **Line 342** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"Processing market data for {market_data.get('symbol')}")`

🔴 **Line 342** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"Processing market data for {market_data.get('symbol')}")`

🔴 **Line 345** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trades = market_data.get('trades', [])`

🔴 **Line 356** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv = market_data.get('ohlcv', {}).get(timeframe)`

🔴 **Line 403** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'price': float(trade.get('p', 0)),`

🔴 **Line 492** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = ticker.get('symbol')`

🔴 **Line 492** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = ticker.get('symbol')`

🔴 **Line 565** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'bids': [[float(p), float(s)] for p, s in data.get('b', [])],`

🔴 **Line 566** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'asks': [[float(p), float(s)] for p, s in data.get('a', [])],`

🔴 **Line 567** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': int(data.get('ts', 0))`

🔴 **Line 603** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': data.get('symbol')`

🔴 **Line 785** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data['data'].get('symbol')`

🔴 **Line 884** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'lastPrice': ticker_data.get('lastPrice', 0),`

🔴 **Line 930** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timeframe': data.get('timeframe', 'base'),`

🔴 **Line 1009** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.batch_size = self.config.get('data_processing', {}).get('batch_size', 100)`

🔴 **Line 1058** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'symbol': market_data.get('symbol'),`

🔴 **Line 1066** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not step.get('enabled', True):`

🔴 **Line 1132** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"symbol": market_data.get('symbol'),`

🔴 **Line 1181** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'asks': [[float(p), float(s)] for p, s in orderbook_data.get('asks', [])],`

🔴 **Line 1182** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': int(orderbook_data.get('timestamp', time.time() * 1000))`

🔴 **Line 1204** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'price': float(trade.get('price', trade.get('p', 0))),`

### src/data_processing/data_store.py

🔴 **Line 60** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'asks': [[float(p), float(s)] for p, s in data.get('asks', [])],`

🔴 **Line 61** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': int(data.get('timestamp', datetime.now().timestamp() * 1000))`

🔴 **Line 122** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': int(data.get('timestamp', 0)),`

🔴 **Line 159** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._orderbook_data.get(symbol)`

🔴 **Line 159** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._orderbook_data.get(symbol)`

🔴 **Line 159** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._orderbook_data.get(symbol)`

🔴 **Line 159** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._orderbook_data.get(symbol)`

🔴 **Line 163** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._ticker_data.get(symbol)`

### src/data_processing/storage_manager.py

🔴 **Line 104** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.storage_config = config.get('data_processing', {}).get('storage', {})`

🔴 **Line 446** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(file_path, 'wb') as f:`

🔴 **Line 463** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(file_path, 'rb') as f:`

🔴 **Line 493** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(file_path, 'wb') as f:`

🔴 **Line 496** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(file_path, 'w') as f:`

🔴 **Line 508** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(file_path, 'rb') as f:`

🔴 **Line 512** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(file_path, 'r') as f:`

🔴 **Line 579** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = self.cache_timestamps.get(key)`

### src/data_storage/database.py

🔴 **Line 64** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config.get('database', {}).get('influxdb', {}) or`

🔴 **Line 179** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `.field("signal_type", signal_data.get('type', 'unknown'))\`

🔴 **Line 308** (pandas_inefficiency)
- Issue: iterrows() is slow - consider vectorization
- Code: `for index, row in df.iterrows():`

🔴 **Line 494** (pandas_inefficiency)
- Issue: iterrows() is slow - consider vectorization
- Code: `for index, row in df.iterrows():`

### src/demo_trading_runner.py

🔴 **Line 238** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if self.config.get('trading', {}).get('use_signals', True):`

🔴 **Line 338** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.info(f"Added signal to queue for processing: {signal_data.get('symbol')} - {signal_data.get('signal')}")`

🔴 **Line 351** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signal_data = await asyncio.wait_for(self.signal_queue.get(), timeout=10)`

🔴 **Line 351** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signal_data = await asyncio.wait_for(self.signal_queue.get(), timeout=10)`

🔴 **Line 351** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signal_data = await asyncio.wait_for(self.signal_queue.get(), timeout=10)`

🔴 **Line 385** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': signal_data.get('timestamp', time.time())`

🔴 **Line 385** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': signal_data.get('timestamp', time.time())`

### src/examples/analysis_example.py

🔴 **Line 20** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open('config/analysis_config.yaml', 'r') as f:`

🔴 **Line 48** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'open': float(exchange_data['ticker'].get('open', 0)),`

### src/fixes/fix_pdf_alerts_comprehensive.py

🔴 **Line 49** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open('config/config.yaml', 'r') as f:`

🔴 **Line 143** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(actual_pdf_path, 'rb') as f:`

🔴 **Line 199** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `recent_pdfs.sort(key=lambda x: x['mtime'], reverse=True)`

### src/fixes/fix_pdf_attachment.py

🔴 **Line 62** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(config_path, 'r') as f:`

🔴 **Line 188** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(pdf_path, 'rb') as f:`

🔴 **Line 244** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"report_manager_initialized": hasattr(locals().get('report_manager', {}), 'pdf_generator'),`

🔴 **Line 271** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(diagnostic_path, 'w') as f:`

### src/fixes/fix_signal_pdf_generation.py

🔴 **Line 46** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(config_path, 'r') as f:`

🔴 **Line 64** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(config_path, 'w') as f:`

🔴 **Line 166** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.info("   if reporting_config.get('enabled', False):")`

🔴 **Line 209** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(patch_path, "w") as f:`

### src/indicators/backups/debug_mixin_backup.py

🔴 **Line 117** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = market_data.get('timestamp', time.time() * 1000)`

🔴 **Line 212** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.component_weights.get(component, 0)`

### src/indicators/backups/sentiment_indicators_backup.py

🔴 **Line 102** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.funding_threshold = sentiment_config.get('funding_threshold', 0.01)`

🔴 **Line 102** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.funding_threshold = sentiment_config.get('funding_threshold', 0.01)`

🔴 **Line 102** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.funding_threshold = sentiment_config.get('funding_threshold', 0.01)`

🔴 **Line 140** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sentiment_data = market_data.get('sentiment', {})`

🔴 **Line 203** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `rate = item.get('rate')`

🔴 **Line 219** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `history_list = funding_history.get('history', [])`

🔴 **Line 223** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `rate = item.get('rate')`

🔴 **Line 230** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `rate = value.get('rate')`

🔴 **Line 697** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = weights.get(component, 0)`

🔴 **Line 822** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.component_weights.get(component, 0.1)`

🔴 **Line 822** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.component_weights.get(component, 0.1)`

🔴 **Line 1138** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `lsr = market_data['sentiment'].get('long_short_ratio', {})`

🔴 **Line 1300** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return data.get(key, default_value)`

### src/indicators/base_indicator.py

🔴 **Line 162** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'min_trades': config.get('validation_requirements', {}).get('trades', {}).get('min_trades', 50),`

🔴 **Line 202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'min_trades': config.get('validation_requirements', {}).get('trades', {}).get('min_trades', 50),`

🔴 **Line 202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'min_trades': config.get('validation_requirements', {}).get('trades', {}).get('min_trades', 50),`

🔴 **Line 255** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `scoring_config_dict = config.get('scoring', {})`

🔴 **Line 261** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `mode=config.get('scoring', {}).get('mode', 'auto_detect'),`

🔴 **Line 575** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df = data['ohlcv'].get(timeframe)`

🔴 **Line 575** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df = data['ohlcv'].get(timeframe)`

🔴 **Line 575** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df = data['ohlcv'].get(timeframe)`

🔴 **Line 595** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `base_scores = timeframe_scores.get('base', {})`

🔴 **Line 595** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `base_scores = timeframe_scores.get('base', {})`

🔴 **Line 598** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf_scores = timeframe_scores.get(tf, {})`

🔴 **Line 604** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `base_score = base_scores.get(component, 50.0)`

🔴 **Line 662** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not self._validate_ohlcv_data(data.get('ohlcv', {})):`

🔴 **Line 728** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `asks = np.array([[float(price), float(size)] for price, size in orderbook.get('asks', [])])`

🔴 **Line 741** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `available_components = data.get('sentiment', {})`

🔴 **Line 878** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._REQUIRED_DATA.get(self.indicator_type, [])`

🔴 **Line 878** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._REQUIRED_DATA.get(self.indicator_type, [])`

🔴 **Line 878** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return self._REQUIRED_DATA.get(self.indicator_type, [])`

🔴 **Line 903** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.component_weights.get(component, 0)`

🔴 **Line 1320** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf_friendly = self.TIMEFRAME_CONFIG.get(tf, {}).get('friendly_name', tf.upper())`

🔴 **Line 1320** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf_friendly = self.TIMEFRAME_CONFIG.get(tf, {}).get('friendly_name', tf.upper())`

🔴 **Line 1327** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.component_weights.get(component, 0)`

🔴 **Line 1327** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.component_weights.get(component, 0)`

🔴 **Line 1332** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf_weight = self.timeframe_weights.get(tf, 0)`

🔴 **Line 1341** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `div_type = div_info.get('type', 'unknown')`

🔴 **Line 1455** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = market_data.get('timestamp', time.time() * 1000)`

🔴 **Line 1522** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if hasattr(self, 'config') and self.config.get('debug_mode', False):`

### src/indicators/orderbook_indicators.py

🔴 **Line 80** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.weight_imbalance = config.get('orderbook', {}).get('weights', {}).get('imbalance', 0.3)`

🔴 **Line 80** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.weight_imbalance = config.get('orderbook', {}).get('weights', {}).get('imbalance', 0.3)`

🔴 **Line 80** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.weight_imbalance = config.get('orderbook', {}).get('weights', {}).get('imbalance', 0.3)`

🔴 **Line 80** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.weight_imbalance = config.get('orderbook', {}).get('weights', {}).get('imbalance', 0.3)`

🔴 **Line 1209** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `bids = orderbook.get('bids', [])`

🔴 **Line 1533** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 1533** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 1575** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 1575** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 1723** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 1756** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 1756** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 2033** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', '')`

🔴 **Line 2396** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.component_weights.get(component, 0)`

🔴 **Line 2437** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `oir_score = component_scores.get('oir', 50)`

🔴 **Line 2475** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `oir_score = component_scores.get('oir', 50)`

🔴 **Line 2833** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 2833** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 2902** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 2975** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 3030** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 3065** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `depth_factor = 1000 if 'volatile' in market_regime.get('primary_regime', '').lower() else 500`

🔴 **Line 3107** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 3171** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

### src/indicators/orderflow_indicators.py

🔴 **Line 59** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_weights = config.get('confluence', {}).get('weights', {}).get('sub_components', {}).get('orderflow', {})`

🔴 **Line 82** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.divergence_lookback = config.get('divergence_lookback', 20)`

🔴 **Line 121** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.volume_threshold = config.get('volume_threshold', 1.5)`

🔴 **Line 189** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `scenario_count = self._debug_stats['scenario_counts'].get(scenario, 0)`

🔴 **Line 223** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cache_hits = self._debug_stats['cache_hits'].get(component, 0)`

🔴 **Line 223** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cache_hits = self._debug_stats['cache_hits'].get(component, 0)`

🔴 **Line 248** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `}.get(scenario, scenario)`

🔴 **Line 268** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `}.get(scenario, scenario)`

🔴 **Line 289** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', '')`

🔴 **Line 582** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight_key = component_mapping.get(score_key, score_key)`

🔴 **Line 620** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.component_weights.get(component, 0)`

🔴 **Line 668** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = data.get('orderbook', {})`

🔴 **Line 704** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alternatives = field_mappings.get(req_field, [req_field])`

🔴 **Line 704** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alternatives = field_mappings.get(req_field, [req_field])`

🔴 **Line 729** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trades = data.get('trades', [])`

🔴 **Line 1519** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current_oi = float(ticker.get('openInterest', 0))`

🔴 **Line 2148** (pandas_inefficiency)
- Issue: apply(lambda) can be slow - consider vectorized operations
- Code: `trades_df['size'] = trades_df['size'].apply(lambda x: float(x) if isinstance(x, str) else x)`

🔴 **Line 2322** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trades = market_data.get('trades', [])`

🔴 **Line 2322** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trades = market_data.get('trades', [])`

🔴 **Line 2322** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trades = market_data.get('trades', [])`

🔴 **Line 2460** (pandas_inefficiency)
- Issue: apply(lambda) can be slow - consider vectorized operations
- Code: `candle_trades.loc[:, 'amount'] = candle_trades['amount'].apply(lambda x: float(x) if isinstance(x, str) else x)`

🔴 **Line 2521** (pandas_inefficiency)
- Issue: iterrows() is slow - consider vectorization
- Code: `for idx, trade in sample_trades.iterrows():`

🔴 **Line 2522** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.warning(f"Trade {idx}: side={trade['side']}, amount={trade['amount']}, is_buy={trade.get('is_buy', False)}, is_sell={trade.get('is_sell', False)}")`

🔴 **Line 2522** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.warning(f"Trade {idx}: side={trade['side']}, amount={trade['amount']}, is_buy={trade.get('is_buy', False)}, is_sell={trade.get('is_sell', False)}")`

🔴 **Line 2776** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `history_count = len(oi_dump.get('history', []))`

🔴 **Line 2882** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = first_entry.get('timestamp', 'N/A')`

🔴 **Line 2882** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = first_entry.get('timestamp', 'N/A')`

🔴 **Line 2882** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = first_entry.get('timestamp', 'N/A')`

🔴 **Line 3108** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `history_count = len(oi_data.get('history', []))`

🔴 **Line 3361** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_data = market_data.get('ohlcv', {})`

🔴 **Line 3643** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_cvd_divergence = divergences.get('price_cvd', {})`

🔴 **Line 3686** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if tf_divergence.get('type') != 'neutral':`

🔴 **Line 4199** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 4274** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 4611** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `zone_price = zone.get('price', 0)`

🔴 **Line 4637** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `zone_price = zone.get('price', 0)`

🔴 **Line 4724** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.component_weights.get(component, 0)`

🔴 **Line 4782** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cvd_score = component_scores.get('cvd', 50)`

🔴 **Line 4782** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cvd_score = component_scores.get('cvd', 50)`

🔴 **Line 4782** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cvd_score = component_scores.get('cvd', 50)`

### src/indicators/price_structure_indicators.py

🔴 **Line 128** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_structure_config = config.get('analysis', {}).get('indicators', {}).get('price_structure', {})`

🔴 **Line 144** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.component_weights[component] = components_config.get(component, {}).get('weight', default_weight)`

🔴 **Line 170** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.order_block_lookback = price_structure_config.get('parameters', {}).get('order_block', {}).get('lookback', 20)`

🔴 **Line 176** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.sfp_threshold = price_structure_config.get('parameters', {}).get('range', {}).get('sfp_threshold', 0.005)  # 0.5% deviation for SFP detection`

🔴 **Line 177** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.msb_window = price_structure_config.get('parameters', {}).get('range', {}).get('msb_window', 5)  # Candles for MSB confirmation`

🔴 **Line 180** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.vol_threshold = price_structure_config.get('parameters', {}).get('volume_confirmation', {}).get('threshold', 1.5)  # Volume multiplier for validation`

🔴 **Line 180** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.vol_threshold = price_structure_config.get('parameters', {}).get('volume_confirmation', {}).get('threshold', 1.5)  # Volume multiplier for validation`

🔴 **Line 181** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.vol_sweep_threshold = price_structure_config.get('parameters', {}).get('volume_confirmation', {}).get('sweep_threshold', 1.5)  # Volume threshold for sweep validation`

🔴 **Line 182** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.vol_range_threshold = price_structure_config.get('parameters', {}).get('volume_confirmation', {}).get('range_threshold', 1.2)  # Volume threshold for range validation`

🔴 **Line 185** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `order_block_params = price_structure_config.get('parameters', {}).get('order_block', {})`

🔴 **Line 189** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.mtf_confirmation_window = order_block_params.get('mtf_confirmation_window', 5)  # ±5 candles for MTF confirmation`

🔴 **Line 190** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.mitigation_threshold = order_block_params.get('mitigation_threshold', 0.5)  # 50% penetration for mitigation`

🔴 **Line 191** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.cluster_max_distance = order_block_params.get('cluster_max_distance', 0.02)  # 2% max distance for clustering`

🔴 **Line 192** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.min_cluster_size = order_block_params.get('min_cluster_size', 2)  # Minimum blocks per cluster`

🔴 **Line 196** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.consolidation_window = order_block_params.get('consolidation_window', 8)  # Extended consolidation check`

🔴 **Line 204** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if tf in self.config.get('timeframes', {})`

🔴 **Line 289** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv = market_data.get('ohlcv', {})`

🔴 **Line 300** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf_key = self.timeframe_map.get(tf_name, tf_name)`

🔴 **Line 300** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf_key = self.timeframe_map.get(tf_name, tf_name)`

🔴 **Line 310** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `mtf_data = ohlcv.get('mtf')`

🔴 **Line 310** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `mtf_data = ohlcv.get('mtf')`

🔴 **Line 341** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `missing_weight = self.timeframe_weights.get(missing_tf, 0)`

🔴 **Line 341** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `missing_weight = self.timeframe_weights.get(missing_tf, 0)`

🔴 **Line 341** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `missing_weight = self.timeframe_weights.get(missing_tf, 0)`

🔴 **Line 376** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf_key = self.timeframe_map.get(tf_name, tf_name)`

🔴 **Line 376** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf_key = self.timeframe_map.get(tf_name, tf_name)`

🔴 **Line 524** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `min_required = self.validation_requirements.get('timeframes', {}).get('min_candles', {}).get(timeframe_name, 50)`

🔴 **Line 524** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `min_required = self.validation_requirements.get('timeframes', {}).get('min_candles', {}).get(timeframe_name, 50)`

🔴 **Line 879** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df = timeframe_data[tf].get('data', pd.DataFrame())`

🔴 **Line 879** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df = timeframe_data[tf].get('data', pd.DataFrame())`

🔴 **Line 920** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"- POC: {area.get('poc', 0):.2f}")`

🔴 **Line 920** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"- POC: {area.get('poc', 0):.2f}")`

🔴 **Line 937** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df = tf_data.get('data', pd.DataFrame())`

🔴 **Line 1065** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `base_volume_threshold = settings.get('volume_threshold', 1.5)`

🔴 **Line 1116** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df['price_row'] = (df['close'] / settings.get('ticks_per_row', 50)).round() * settings.get('ticks_per_row', 50)`

🔴 **Line 1123** (pandas_inefficiency)
- Issue: iterrows() is slow - consider vectorization
- Code: `for idx, row in grouped.iterrows():`

🔴 **Line 1148** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `bullish_levels.sort(key=lambda x: x['strength'], reverse=True)`

🔴 **Line 1149** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `bearish_levels.sort(key=lambda x: x['strength'], reverse=True)`

🔴 **Line 1291** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `window = self.config.get('analysis', {}).get('position_analysis', {}).get('imbalance', {}).get('window', 20)`

🔴 **Line 2073** (pandas_inefficiency)
- Issue: iterrows() is slow - consider vectorization
- Code: `for _, row in block_data.iterrows():`

🔴 **Line 2209** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `support = swing_points.get('support', {}).get('price')`

🔴 **Line 2209** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `support = swing_points.get('support', {}).get('price')`

🔴 **Line 2487** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_data = market_data.get('ohlcv', {})`

🔴 **Line 2499** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', '')`

🔴 **Line 2537** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component = div_info.get('component')`

🔴 **Line 2556** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', '')`

🔴 **Line 2567** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_component = self.component_mapping.get(component, component)`

🔴 **Line 2567** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_component = self.component_mapping.get(component, component)`

🔴 **Line 2598** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_data = market_data.get('ohlcv', {})`

🔴 **Line 2882** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.timeframe_weights.get(tf, 0.0)`

🔴 **Line 2882** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.timeframe_weights.get(tf, 0.0)`

🔴 **Line 2882** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.timeframe_weights.get(tf, 0.0)`

🔴 **Line 2949** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_component = self.component_mapping.get(component, component)`

🔴 **Line 2949** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_component = self.component_mapping.get(component, component)`

🔴 **Line 2949** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_component = self.component_mapping.get(component, component)`

🔴 **Line 2957** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_component = self.component_mapping.get(component, component)`

🔴 **Line 3079** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `base_df = ohlcv_data.get('base', None)`

🔴 **Line 3079** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `base_df = ohlcv_data.get('base', None)`

🔴 **Line 3103** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `strength = block.get('enhanced_strength', block.get('strength', 0.5))`

🔴 **Line 3103** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `strength = block.get('enhanced_strength', block.get('strength', 0.5))`

🔴 **Line 3112** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if block.get('mtf_confirmation', {}).get('confirmed', False):`

🔴 **Line 3123** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if block.get('sweep_info', {}).get('has_sweep', False):`

🔴 **Line 3658** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_component = self.component_mapping.get(component, component)`

🔴 **Line 3658** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_component = self.component_mapping.get(component, component)`

🔴 **Line 3658** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_component = self.component_mapping.get(component, component)`

🔴 **Line 3661** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.component_weights.get(config_component, 0.0)`

🔴 **Line 3703** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_component = self.component_mapping.get(component, component)`

🔴 **Line 3703** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_component = self.component_mapping.get(component, component)`

🔴 **Line 3703** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_component = self.component_mapping.get(component, component)`

🔴 **Line 4127** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `vol_mult = sweep_info.get('volume_multiplier', 1.0)`

🔴 **Line 4127** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `vol_mult = sweep_info.get('volume_multiplier', 1.0)`

🔴 **Line 4127** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `vol_mult = sweep_info.get('volume_multiplier', 1.0)`

🔴 **Line 4570** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 4713** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_data = market_data.get('ohlcv', {})`

🔴 **Line 4719** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `base_data = ohlcv_data.get('base')`

🔴 **Line 4751** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `strength = block.get('enhanced_strength', block.get('strength', 0.5))`

🔴 **Line 5126** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confirmation['total_weight'] += self.timeframe_weights.get(tf, 0.1)`

🔴 **Line 5126** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confirmation['total_weight'] += self.timeframe_weights.get(tf, 0.1)`

🔴 **Line 5587** (pandas_inefficiency)
- Issue: iterrows() is slow - consider vectorization
- Code: `for _, candle in future_window.iterrows():`

🔴 **Line 5617** (pandas_inefficiency)
- Issue: iterrows() is slow - consider vectorization
- Code: `for _, candle in future_window.iterrows():`

### src/indicators/sentiment_indicators.py

🔴 **Line 104** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.funding_threshold = sentiment_config.get('funding_threshold', 0.01)`

🔴 **Line 104** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.funding_threshold = sentiment_config.get('funding_threshold', 0.01)`

🔴 **Line 104** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.funding_threshold = sentiment_config.get('funding_threshold', 0.01)`

🔴 **Line 165** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `long_ratio = float(long_short_data.get('long', 50.0))`

🔴 **Line 244** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `rates = [float(rate.get('fundingRate', 0)) for rate in funding_history]`

🔴 **Line 250** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `rates = [float(rate.get(rate_key, 0)) for rate in funding_history]`

🔴 **Line 250** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `rates = [float(rate.get(rate_key, 0)) for rate in funding_history]`

🔴 **Line 362** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `short_liq = sum(float(event.get('size', event.get('amount', 0)))`

🔴 **Line 405** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volume_data = market_data.get('volume', {})`

🔴 **Line 405** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volume_data = market_data.get('volume', {})`

🔴 **Line 405** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volume_data = market_data.get('volume', {})`

🔴 **Line 650** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = sentiment_data.get('ticker', {})`

🔴 **Line 650** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = sentiment_data.get('ticker', {})`

🔴 **Line 650** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = sentiment_data.get('ticker', {})`

🔴 **Line 830** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `risk_levels = sorted(risk_levels, key=lambda x: int(x.get('id', 0)))`

🔴 **Line 1169** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.component_weights.get(component, 0.0)`

🔴 **Line 1169** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.component_weights.get(component, 0.0)`

🔴 **Line 1186** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.component_weights.get(component, 0.0)`

🔴 **Line 1186** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.component_weights.get(component, 0.0)`

🔴 **Line 1385** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `mood_data = processed_data.get('market_mood')`

🔴 **Line 1439** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `oi_data = processed_data.get('open_interest')`

🔴 **Line 1458** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._log_component_breakdown(components, market_data.get('symbol', ''))`

🔴 **Line 1585** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = result.get('score', 50.0)`

🔴 **Line 1585** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = result.get('score', 50.0)`

🔴 **Line 1645** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sentiment_score = sentiment_scores.get('sentiment', 50.0)`

🔴 **Line 1645** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sentiment_score = sentiment_scores.get('sentiment', 50.0)`

🔴 **Line 1680** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `funding_score = sentiment_scores.get('funding_rate', 50.0)`

🔴 **Line 1765** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sentiment_scores = sentiment_result.get('components', {})`

🔴 **Line 1765** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sentiment_scores = sentiment_result.get('components', {})`

🔴 **Line 1803** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `funding_score = sentiment_scores.get('funding_rate', 50.0)`

🔴 **Line 1892** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `strongest = max(buy_signals, key=lambda x: strengths.get(x.get('strength', 'WEAK'), 0))`

🔴 **Line 1892** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `strongest = max(buy_signals, key=lambda x: strengths.get(x.get('strength', 'WEAK'), 0))`

🔴 **Line 1898** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `reasons = [s.get('reason', '') for s in buy_signals]`

🔴 **Line 1904** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'strength': strongest.get('strength', 'MEDIUM'),`

🔴 **Line 1907** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'components': [s.get('component', 'multiple') for s in buy_signals]`

🔴 **Line 1918** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `strongest = max(sell_signals, key=lambda x: strengths.get(x.get('strength', 'WEAK'), 0))`

🔴 **Line 1924** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `reasons = [s.get('reason', '') for s in sell_signals]`

🔴 **Line 1930** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'strength': strongest.get('strength', 'MEDIUM'),`

🔴 **Line 1933** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'components': [s.get('component', 'multiple') for s in sell_signals]`

🔴 **Line 1966** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `side = trade.get('side', '').lower()`

🔴 **Line 2036** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_data = market_data.get('ohlcv', {})`

🔴 **Line 2109** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `result = result.get(k, default)`

🔴 **Line 2177** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current_oi = float(ticker.get('openInterest', 0))`

🔴 **Line 2271** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `funding_score = components.get('funding_rate', 50)`

🔴 **Line 2556** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 2556** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 2556** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 2694** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 2761** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 2831** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 3101** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `funding_rate = sentiment_data.get('funding_rate', 0)`

🔴 **Line 3101** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `funding_rate = sentiment_data.get('funding_rate', 0)`

### src/indicators/technical_indicators.py

🔴 **Line 79** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.component_weights[component] = components_config.get(component, {}).get('weight', default_weight)`

🔴 **Line 150** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', '')`

🔴 **Line 150** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', '')`

🔴 **Line 174** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not validation_result.get('valid', False):`

🔴 **Line 279** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', '')`

🔴 **Line 279** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', '')`

🔴 **Line 279** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', '')`

🔴 **Line 1223** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `min_data_points = timeframe_min_points.get(timeframe, timeframe_min_points['base'])`

🔴 **Line 1223** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `min_data_points = timeframe_min_points.get(timeframe, timeframe_min_points['base'])`

🔴 **Line 1223** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `min_data_points = timeframe_min_points.get(timeframe, timeframe_min_points['base'])`

🔴 **Line 1223** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `min_data_points = timeframe_min_points.get(timeframe, timeframe_min_points['base'])`

🔴 **Line 1839** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_data = market_data.get('ohlcv', {})`

🔴 **Line 1886** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `min_points = self.TIMEFRAME_CONFIG.get(tf_name, {}).get('validation', {}).get('min_candles', 50)`

🔴 **Line 2097** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `rsi_score = component_scores.get('rsi', 50)`

🔴 **Line 2125** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `atr_score = component_scores.get('atr', 50)`

🔴 **Line 2164** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime = regime_result.get('primary_regime', 'RANGE_LOW_VOL')`

🔴 **Line 2282** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.component_weights.get(component, 0)`

### src/indicators/volume_indicators.py

🔴 **Line 98** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `elif isinstance(components_config.get(component), dict):`

🔴 **Line 165** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_value = parameters.get(param, default_value)`

🔴 **Line 165** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_value = parameters.get(param, default_value)`

🔴 **Line 165** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_value = parameters.get(param, default_value)`

🔴 **Line 165** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_value = parameters.get(param, default_value)`

🔴 **Line 165** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_value = parameters.get(param, default_value)`

🔴 **Line 165** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `config_value = parameters.get(param, default_value)`

🔴 **Line 193** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volume_profile_params = volume_config.get('parameters', {}).get('volume_profile', {})`

🔴 **Line 245** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_data = data.get('ohlcv', {})`

🔴 **Line 261** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df = ohlcv_data.get(tf)`

🔴 **Line 261** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df = ohlcv_data.get(tf)`

🔴 **Line 261** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df = ohlcv_data.get(tf)`

🔴 **Line 289** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `min_candles = self.params.get(min_param_name)`

🔴 **Line 289** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `min_candles = self.params.get(min_param_name)`

🔴 **Line 410** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `significant_threshold = self.params.get('rel_vol_significant', 2.0)`

🔴 **Line 679** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight_sum = sum(self.component_weights.get(name, 0)`

🔴 **Line 877** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_divergence = self.params.get('max_divergence', 0.5)`

🔴 **Line 877** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_divergence = self.params.get('max_divergence', 0.5)`

🔴 **Line 877** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_divergence = self.params.get('max_divergence', 0.5)`

🔴 **Line 877** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_divergence = self.params.get('max_divergence', 0.5)`

🔴 **Line 961** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', '')`

🔴 **Line 1215** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_data = timeframe_data.get('ohlcv', {})`

🔴 **Line 1431** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `divergence_value = divergence_bonus.get('strength', 0.0)`

🔴 **Line 1687** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `period = self.config.get('cmf_period', 20)`

🔴 **Line 2040** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `period = self.params.get('rel_vol_period', 20)`

🔴 **Line 2040** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `period = self.params.get('rel_vol_period', 20)`

🔴 **Line 2107** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `period = self.config.get('relative_volume_period', 30)`

🔴 **Line 2230** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `period = self.config.get('relative_volume_period', 30)`

🔴 **Line 2230** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `period = self.config.get('relative_volume_period', 30)`

🔴 **Line 2440** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `period = self.params.get('rel_vol_period', 20)`

🔴 **Line 2440** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `period = self.params.get('rel_vol_period', 20)`

🔴 **Line 2440** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `period = self.params.get('rel_vol_period', 20)`

🔴 **Line 2440** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `period = self.params.get('rel_vol_period', 20)`

🔴 **Line 2487** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_aware_mode = self.config.get('price_aware_mode', False)`

🔴 **Line 2487** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_aware_mode = self.config.get('price_aware_mode', False)`

🔴 **Line 2487** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_aware_mode = self.config.get('price_aware_mode', False)`

🔴 **Line 2514** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `period = self.config.get('relative_volume_period', 20)`

🔴 **Line 2514** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `period = self.config.get('relative_volume_period', 20)`

🔴 **Line 3105** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 3105** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 3105** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 3185** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 3185** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime_type = market_regime.get('primary_regime', 'ranging')`

🔴 **Line 3248** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confidence = market_regime.get('confidence', 0.5)`

🔴 **Line 3248** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confidence = market_regime.get('confidence', 0.5)`

🔴 **Line 3400** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component = div_info.get('component')`

🔴 **Line 3400** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component = div_info.get('component')`

🔴 **Line 3400** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component = div_info.get('component')`

🔴 **Line 3422** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf1, tf2 = div_info.get('timeframes', ['', ''])`

🔴 **Line 3511** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.component_weights.get(component, 0)`

### src/integrated_server.py

🔴 **Line 203** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `web_config = self.config_manager.config.get('web_server', {})`

### src/main.py

🔴 **Line 253** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(obj, aiohttp.ClientSession):`

🔴 **Line 253** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(obj, aiohttp.ClientSession):`

🔴 **Line 253** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(obj, aiohttp.ClientSession):`

🔴 **Line 325** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(run_info_path, 'w') as f:`

🔴 **Line 814** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component.get("status") in ["inactive", "disconnected"]`

🔴 **Line 835** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@app.get("/health")`

🔴 **Line 965** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@app.get("/version")`

🔴 **Line 1023** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'open': [float(ticker.get('open', 0))],`

🔴 **Line 1043** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score=analysis.get('confluence_score', 0),`

🔴 **Line 1089** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score=analysis.get('confluence_score', 0),`

🔴 **Line 1089** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score=analysis.get('confluence_score', 0),`

🔴 **Line 1271** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'orderbook': market_data.get('orderbook', {}),`

🔴 **Line 1415** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@app.get("/ui")`

🔴 **Line 1415** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@app.get("/ui")`

🔴 **Line 1415** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@app.get("/ui")`

🔴 **Line 1415** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@app.get("/ui")`

🔴 **Line 1415** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@app.get("/ui")`

🔴 **Line 1415** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@app.get("/ui")`

🔴 **Line 1498** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@app.get("/api/bybit-direct/top-symbols")`

🔴 **Line 1557** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbols_data.sort(key=lambda x: x['turnover_24h'], reverse=True)`

🔴 **Line 1601** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score = analysis.get('confluence_score', 0)`

🔴 **Line 1601** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score = analysis.get('confluence_score', 0)`

🔴 **Line 1619** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `change_24h = symbol_info.get('change_24h', 0)`

🔴 **Line 1619** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `change_24h = symbol_info.get('change_24h', 0)`

🔴 **Line 1780** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"confluence_score": analysis.get('confluence_score', 50),`

🔴 **Line 1780** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"confluence_score": analysis.get('confluence_score', 50),`

🔴 **Line 1870** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@app.get("/api/alpha/opportunities")`

🔴 **Line 1888** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score = analysis.get('confluence_score', 50)`

🔴 **Line 1909** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@app.post("/api/alpha/scan")`

🔴 **Line 1915** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbols = request.get('symbols', [])`

🔴 **Line 1927** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score = analysis.get('confluence_score', 50) / 100`

🔴 **Line 2048** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"manipulation_type": latest.get('manipulation_type', 'UNKNOWN'),`

🔴 **Line 2048** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"manipulation_type": latest.get('manipulation_type', 'UNKNOWN'),`

🔴 **Line 2103** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score = analysis.get('confluence_score', 50)`

🔴 **Line 2124** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@app.get("/api/dashboard/alerts/recent")`

🔴 **Line 2163** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@app.post("/api/bitcoin-beta/generate")`

🔴 **Line 2228** (blocking_in_async)
- Issue: subprocess.run() without async (in async function)
- Code: `result = subprocess.run(['lsof', '-i', f':{port}'], capture_output=True, text=True)`

🔴 **Line 2240** (blocking_in_async)
- Issue: subprocess.run() without async (in async function)
- Code: `subprocess.run(['kill', '-9', pid], check=True)`

🔴 **Line 2442** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `@app.post("/api/websocket/initialize")`

### src/models/market_data.py

🔴 **Line 220** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `order_id=data.get('order'),`

🔴 **Line 237** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `nonce=data.get('nonce'),`

🔴 **Line 237** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `nonce=data.get('nonce'),`

### src/models/schema.py

🔴 **Line 127** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = values.get('confluence_score', 50)`

### src/models/signal_schema.py

🔴 **Line 189** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.components[comp].score * weights.get(comp, 0)`

🔴 **Line 189** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.components[comp].score * weights.get(comp, 0)`

🔴 **Line 226** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `existing_components = set(data.get('components', {}).keys())`

### src/monitoring/alert_manager.py

🔴 **Line 146** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.mock_mode = config.get('monitoring', {}).get('alerts', {}).get('mock_mode', False)`

🔴 **Line 146** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.mock_mode = config.get('monitoring', {}).get('alerts', {}).get('mock_mode', False)`

🔴 **Line 146** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.mock_mode = config.get('monitoring', {}).get('alerts', {}).get('mock_mode', False)`

🔴 **Line 146** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.mock_mode = config.get('monitoring', {}).get('alerts', {}).get('mock_mode', False)`

🔴 **Line 208** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.webhook_max_retries = config.get('monitoring', {}).get('alerts', {}).get('webhook_max_retries', 3)`

🔴 **Line 208** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.webhook_max_retries = config.get('monitoring', {}).get('alerts', {}).get('webhook_max_retries', 3)`

🔴 **Line 208** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.webhook_max_retries = config.get('monitoring', {}).get('alerts', {}).get('webhook_max_retries', 3)`

🔴 **Line 208** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.webhook_max_retries = config.get('monitoring', {}).get('alerts', {}).get('webhook_max_retries', 3)`

🔴 **Line 568** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `system_alerts_config = self.config.get('monitoring', {}).get('alerts', {}).get('system_alerts', {})`

🔴 **Line 581** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `should_mirror_market_report = should_mirror and mirror_config.get('types', {}).get('market_report', False)`

🔴 **Line 596** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if details and details.get('type') == 'large_aggressive_order':`

🔴 **Line 608** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `large_order_system_webhook = use_system_webhook and types_config.get('large_aggressive_order', False)`

🔴 **Line 694** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1`

🔴 **Line 701** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if details and details.get('type') == 'whale_activity':`

🔴 **Line 714** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if throttle and (current_time - self._last_whale_activity_alert.get(f"{symbol}:{subtype}", 0) < self.whale_activity_cooldown):`

🔴 **Line 721** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `whale_system_webhook = use_system_webhook and types_config.get('whale_activity', False)`

🔴 **Line 743** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `activity_data = details.get('data', {})`

🔴 **Line 743** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `activity_data = details.get('data', {})`

🔴 **Line 804** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trades_details = self._format_whale_trades(activity_data.get('top_whale_trades', []))`

🔴 **Line 863** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1`

🔴 **Line 871** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if "cpu_usage" in message.lower() or (details and details.get('type') == 'cpu'):`

🔴 **Line 879** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `should_mirror_cpu = should_mirror and mirror_config.get('types', {}).get('cpu', False)`

🔴 **Line 896** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if "memory_usage" in message.lower() or "memory usage" in message.lower() or (details and details.get('type') == 'memory'):`

🔴 **Line 902** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `should_mirror_memory = should_mirror and mirror_config.get('types', {}).get('memory', False)`

🔴 **Line 922** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `warning_system_webhook = use_system_webhook and types_config.get('warning', False)`

🔴 **Line 925** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `should_mirror_warning = should_mirror and mirror_config.get('types', {}).get('warning', False)`

🔴 **Line 945** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `(details and details.get('type') == 'performance')):`

🔴 **Line 951** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `should_mirror_performance = should_mirror and mirror_config.get('types', {}).get('performance', False)`

🔴 **Line 971** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `(details and details.get('type') == 'api')):`

🔴 **Line 977** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `should_mirror_api = should_mirror and mirror_config.get('types', {}).get('api', False)`

🔴 **Line 997** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `(details and details.get('type') == 'database')):`

🔴 **Line 1003** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `should_mirror_database = should_mirror and mirror_config.get('types', {}).get('database', False)`

🔴 **Line 1024** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `(details and details.get('type') == 'data_processing')):`

🔴 **Line 1030** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `should_mirror_data_processing = should_mirror and mirror_config.get('types', {}).get('data_processing', False)`

🔴 **Line 1050** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `(details and details.get('type') == 'health')):`

🔴 **Line 1056** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `should_mirror_health = should_mirror and mirror_config.get('types', {}).get('health', False)`

🔴 **Line 1076** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `error_system_webhook = use_system_webhook and types_config.get('error', False)`

🔴 **Line 1079** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `should_mirror_error = should_mirror and mirror_config.get('types', {}).get('error', False)`

🔴 **Line 1181** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `level_count = int(stats.get(level.lower(), 0))`

🔴 **Line 1210** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_time = float(self._last_alert.get(alert_key, 0))`

🔴 **Line 1245** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_alert = self._last_liquidation_alert.get(symbol, 0)`

🔴 **Line 1245** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_alert = self._last_liquidation_alert.get(symbol, 0)`

🔴 **Line 1369** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1`

🔴 **Line 1437** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `log_level = config.get('logging', {}).get('root', {}).get('level', 'DEBUG')`

🔴 **Line 1630** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `call_source = results.get('call_source', 'UNKNOWN_SOURCE') if isinstance(results, dict) else 'UNKNOWN_SOURCE'`

🔴 **Line 1630** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `call_source = results.get('call_source', 'UNKNOWN_SOURCE') if isinstance(results, dict) else 'UNKNOWN_SOURCE'`

🔴 **Line 1630** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `call_source = results.get('call_source', 'UNKNOWN_SOURCE') if isinstance(results, dict) else 'UNKNOWN_SOURCE'`

🔴 **Line 1630** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `call_source = results.get('call_source', 'UNKNOWN_SOURCE') if isinstance(results, dict) else 'UNKNOWN_SOURCE'`

🔴 **Line 1770** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `display_name = weight_labels.get(component_name, component_name.capitalize())`

🔴 **Line 1770** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `display_name = weight_labels.get(component_name, component_name.capitalize())`

🔴 **Line 1770** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `display_name = weight_labels.get(component_name, component_name.capitalize())`

🔴 **Line 1912** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component_name = component_type_display_map.get(component_type_value,`

🔴 **Line 1912** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component_name = component_type_display_map.get(component_type_value,`

🔴 **Line 1931** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component = interp_obj.get('display_name', interp_obj.get('component', 'Unknown'))`

🔴 **Line 1931** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component = interp_obj.get('display_name', interp_obj.get('component', 'Unknown'))`

🔴 **Line 1991** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `real_subcomps = [s for s in top_weighted_subcomponents if not s.get('name', '').startswith('overall_')]`

🔴 **Line 2000** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `subcomps_to_display.sort(key=lambda x: x.get('weighted_impact', 0), reverse=True)`

🔴 **Line 2000** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `subcomps_to_display.sort(key=lambda x: x.get('weighted_impact', 0), reverse=True)`

🔴 **Line 2003** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sub_name = sub_comp.get('display_name', 'Unknown')`

🔴 **Line 2151** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `except aiohttp.ClientError as ce:`

🔴 **Line 2222** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1`

🔴 **Line 2222** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1`

🔴 **Line 2333** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', '')`

🔴 **Line 2333** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', '')`

🔴 **Line 2511** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `level = alert.get('level', 'INFO')`

🔴 **Line 2511** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `level = alert.get('level', 'INFO')`

🔴 **Line 2594** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1`

🔴 **Line 2617** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1`

🔴 **Line 2642** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `except (requests.exceptions.ConnectionError,`

🔴 **Line 2695** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.webhook_timeout)) as session:`

🔴 **Line 2695** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.webhook_timeout)) as session:`

🔴 **Line 2695** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.webhook_timeout)) as session:`

🔴 **Line 2756** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `mirror_config = system_alerts_config.get('mirror_alerts', {})`

🔴 **Line 2774** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `elif use_system_webhook and types_config.get(alert_type, False) and self.system_webhook_url:`

🔴 **Line 2850** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `name=author.get('name', ''),`

🔴 **Line 2882** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `inline=field.get('inline', False)`

🔴 **Line 2918** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(file_path, 'rb') as f:`

🔴 **Line 3035** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `file_path = file_item.get('path', '')`

🔴 **Line 3035** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `file_path = file_item.get('path', '')`

🔴 **Line 3247** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.info(f"[FREQUENCY_ALERT] Processing frequency alert for {frequency_alert.get('symbol', 'UNKNOWN')}")`

🔴 **Line 3250** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signal_data = frequency_alert.get('signal_data', {})`

🔴 **Line 3270** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol=signal_data.get('symbol', 'UNKNOWN'),`

🔴 **Line 3291** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `pdf_path = signal_data.get('pdf_path')`

🔴 **Line 3318** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.info(f"[FREQUENCY_ALERT] No valid PDF to attach for {signal_data.get('symbol', 'UNKNOWN')}")`

🔴 **Line 3455** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `transaction_id = signal_data.get('transaction_id', str(uuid.uuid4())[:8])`

🔴 **Line 3455** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `transaction_id = signal_data.get('transaction_id', str(uuid.uuid4())[:8])`

🔴 **Line 3455** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `transaction_id = signal_data.get('transaction_id', str(uuid.uuid4())[:8])`

🔴 **Line 3488** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(pdf_path, 'rb') as f:`

🔴 **Line 3508** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', 'UNKNOWN')`

🔴 **Line 3540** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(json_path, 'w') as f:`

🔴 **Line 3563** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `transaction_id=signal_data.get('transaction_id'),`

🔴 **Line 3832** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `color = severity_color_map.get(severity, 0x95a5a6)  # Default gray`

🔴 **Line 4144** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1`

🔴 **Line 4144** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1`

🔴 **Line 4144** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._alert_stats['total'] = int(self._alert_stats.get('total', 0)) + 1`

🔴 **Line 4192** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._alert_stats['errors'] = int(self._alert_stats.get('errors', 0)) + 1`

🔴 **Line 4227** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `description=f"**Sophisticated trading pattern detected**\n{alert.get('message', '')}",`

🔴 **Line 4227** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `description=f"**Sophisticated trading pattern detected**\n{alert.get('message', '')}",`

🔴 **Line 4227** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `description=f"**Sophisticated trading pattern detected**\n{alert.get('message', '')}",`

🔴 **Line 4227** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `description=f"**Sophisticated trading pattern detected**\n{alert.get('message', '')}",`

🔴 **Line 4227** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `description=f"**Sophisticated trading pattern detected**\n{alert.get('message', '')}",`

🔴 **Line 4358** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1`

🔴 **Line 4374** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `details = alert.get('details', {})`

🔴 **Line 4450** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._alert_stats['sent'] = int(self._alert_stats.get('sent', 0)) + 1`

🔴 **Line 4633** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"Removed field '{removed_field.get('name')}' to reduce payload size")`

🔴 **Line 4633** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"Removed field '{removed_field.get('name')}' to reduce payload size")`

🔴 **Line 4860** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confidence = base_confidence.get(signal_strength, 50)`

🔴 **Line 4860** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confidence = base_confidence.get(signal_strength, 50)`

### src/monitoring/alpha_integration.py

🔴 **Line 42** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alpha_config = self.config.get('alpha_detection', {})`

🔴 **Line 187** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_check = self.last_alpha_check.get(symbol_str, 0)`

🔴 **Line 239** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `asset_data = market_data.get('asset', {})`

🔴 **Line 239** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `asset_data = market_data.get('asset', {})`

🔴 **Line 239** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `asset_data = market_data.get('asset', {})`

🔴 **Line 251** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `asset_ohlcv = asset_data.get('ohlcv', {})`

🔴 **Line 289** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `asset_data.get('price', 0),`

🔴 **Line 289** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `asset_data.get('price', 0),`

🔴 **Line 289** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `asset_data.get('price', 0),`

🔴 **Line 324** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `asset_close = asset_ohlcv.get('close', asset_price)`

🔴 **Line 324** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `asset_close = asset_ohlcv.get('close', asset_price)`

🔴 **Line 334** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `asset_return = (asset_close - asset_ohlcv.get('open', asset_close)) / asset_ohlcv.get('open', asset_close) if asset_ohlcv.get('open', 0) > 0 else 0`

🔴 **Line 398** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not asset_formatted.get('price', 0) and not asset_formatted.get('ohlcv', {}):`

🔴 **Line 398** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not asset_formatted.get('price', 0) and not asset_formatted.get('ohlcv', {}):`

🔴 **Line 401** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not bitcoin_formatted.get('price', 0) and not bitcoin_formatted.get('ohlcv', {}):`

🔴 **Line 434** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price = ticker.get('last', ticker.get('close', ticker.get('price', ticker.get('bid', ticker.get('ask', 0)))))`

🔴 **Line 434** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price = ticker.get('last', ticker.get('close', ticker.get('price', ticker.get('bid', ticker.get('ask', 0)))))`

🔴 **Line 434** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price = ticker.get('last', ticker.get('close', ticker.get('price', ticker.get('bid', ticker.get('ask', 0)))))`

🔴 **Line 434** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price = ticker.get('last', ticker.get('close', ticker.get('price', ticker.get('bid', ticker.get('ask', 0)))))`

🔴 **Line 434** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price = ticker.get('last', ticker.get('close', ticker.get('price', ticker.get('bid', ticker.get('ask', 0)))))`

🔴 **Line 471** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volume = ticker.get('baseVolume', ticker.get('volume', ticker.get('quoteVolume', 0)))`

🔴 **Line 471** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volume = ticker.get('baseVolume', ticker.get('volume', ticker.get('quoteVolume', 0)))`

🔴 **Line 700** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_data = market_data.get('ohlcv', {})`

🔴 **Line 700** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_data = market_data.get('ohlcv', {})`

🔴 **Line 700** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_data = market_data.get('ohlcv', {})`

🔴 **Line 738** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_alert_time = self.last_alpha_check.get(symbol, 0)`

🔴 **Line 738** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_alert_time = self.last_alpha_check.get(symbol, 0)`

🔴 **Line 751** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `daily_count = self.daily_alert_counts.get(daily_key, 0)`

🔴 **Line 751** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `daily_count = self.daily_alert_counts.get(daily_key, 0)`

🔴 **Line 777** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.daily_alert_counts[daily_key] = self.daily_alert_counts.get(daily_key, 0) + 1`

🔴 **Line 864** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 864** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 864** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 894** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_data = market_data.get('ohlcv', {})`

🔴 **Line 894** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ohlcv_data = market_data.get('ohlcv', {})`

### src/monitoring/alpha_integration_manager.py

🔴 **Line 92** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `legacy_enabled = self.legacy_config.get('enabled', True)`

🔴 **Line 131** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alpha_alerts_enabled = self.optimized_config.get('alpha_alerts_enabled', True)`

🔴 **Line 292** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alpha = result.get('alpha_potential', 0)`

🔴 **Line 292** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alpha = result.get('alpha_potential', 0)`

🔴 **Line 355** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `total_alpha += result.get('alpha_potential', 0)`

🔴 **Line 366** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alpha = result.get('alpha_potential', 0)`

🔴 **Line 437** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'comparison_metrics': self.comparison_metrics.get('latest', {}),`

🔴 **Line 437** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'comparison_metrics': self.comparison_metrics.get('latest', {}),`

🔴 **Line 437** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'comparison_metrics': self.comparison_metrics.get('latest', {}),`

### src/monitoring/alpha_scanner.py

🔴 **Line 87** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.alpha_config = config.get('alpha_scanning', {})`

🔴 **Line 105** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.timeframe_thresholds = self.alpha_config.get('timeframe_thresholds', {})`

🔴 **Line 108** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.performance_tiers = self.alpha_config.get('performance_tiers', {`

🔴 **Line 121** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.timeframes = self.alpha_config.get('timeframes', ['htf', 'mtf', 'ltf', 'base'])`

🔴 **Line 292** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `btc_data = market_data.get('BTCUSDT', {})`

🔴 **Line 432** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `correlation = data.get('correlation', 0)`

🔴 **Line 489** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = data.get('beta', 0)`

🔴 **Line 489** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = data.get('beta', 0)`

🔴 **Line 543** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alpha = data.get('alpha', 0)`

🔴 **Line 543** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alpha = data.get('alpha', 0)`

🔴 **Line 595** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `params = timeframe_map.get(timeframe, timeframe_map['mtf'])`

🔴 **Line 640** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_alert_time = self.last_alerts.get(opp.symbol, 0)`

🔴 **Line 672** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeframe_config = self.timeframe_thresholds.get(timeframe, {})`

### src/monitoring/components/health_monitor.py

🔴 **Line 359** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cpu_alerts_config = self.config.get('monitoring', {}).get('alerts', {}).get('cpu_alerts', {})`

🔴 **Line 359** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cpu_alerts_config = self.config.get('monitoring', {}).get('alerts', {}).get('cpu_alerts', {})`

🔴 **Line 359** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cpu_alerts_config = self.config.get('monitoring', {}).get('alerts', {}).get('cpu_alerts', {})`

🔴 **Line 722** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if mirror_config.get('enabled', False) and mirror_config.get('types', {}).get(a_type, False):`

🔴 **Line 722** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if mirror_config.get('enabled', False) and mirror_config.get('types', {}).get(a_type, False):`

🔴 **Line 746** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if alert_types.get(alert_type, False):`

🔴 **Line 746** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if alert_types.get(alert_type, False):`

🔴 **Line 746** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if alert_types.get(alert_type, False):`

🔴 **Line 912** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `response = requests.post(`

🔴 **Line 1012** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'warning_threshold': self.metrics['cpu'].thresholds.get('warning'),`

🔴 **Line 1012** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'warning_threshold': self.metrics['cpu'].thresholds.get('warning'),`

🔴 **Line 1039** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alert = self.alerts.get(alert_id)`

🔴 **Line 1039** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alert = self.alerts.get(alert_id)`

🔴 **Line 1105** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `base_warning = self.config.get('memory_warning_threshold', 98)`

### src/monitoring/enhanced_market_report.py

🔴 **Line 200** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if 'open_interest' not in market_data or not market_data['open_interest'].get('current'):`

🔴 **Line 200** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if 'open_interest' not in market_data or not market_data['open_interest'].get('current'):`

🔴 **Line 200** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if 'open_interest' not in market_data or not market_data['open_interest'].get('current'):`

🔴 **Line 203** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if oi_history and oi_history.get('history') and len(oi_history['history']) > 0:`

🔴 **Line 225** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not market_data.get('price') or all(v == 0 for v in market_data.get('price', {}).values()):`

🔴 **Line 226** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

### src/monitoring/fix_market_reporter_validation.py

🔴 **Line 61** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"if result.get('smi_value', 50) == 50:",`

### src/monitoring/health_monitor.py

🔴 **Line 358** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `memory_tracking_config = self.config.get('monitoring', {}).get('memory_tracking', {})`

🔴 **Line 358** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `memory_tracking_config = self.config.get('monitoring', {}).get('memory_tracking', {})`

🔴 **Line 400** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `log_level = memory_tracking_config.get('log_level', 'WARNING').upper()`

🔴 **Line 400** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `log_level = memory_tracking_config.get('log_level', 'WARNING').upper()`

🔴 **Line 738** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'warning_threshold': self.metrics['cpu'].thresholds.get('warning'),`

🔴 **Line 738** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'warning_threshold': self.metrics['cpu'].thresholds.get('warning'),`

🔴 **Line 765** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alert = self.alerts.get(alert_id)`

🔴 **Line 765** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alert = self.alerts.get(alert_id)`

### src/monitoring/liquidation_monitor.py

🔴 **Line 208** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `liquidations = market_data.get('liquidations', [])`

🔴 **Line 208** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `liquidations = market_data.get('liquidations', [])`

🔴 **Line 216** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if liq.get('timestamp', 0) / 1000 > self.last_check_time`

### src/monitoring/manipulation_detector.py

🔴 **Line 138** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not self.manipulation_config.get('enabled', True):`

🔴 **Line 205** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `historical_data = self._historical_data.get(symbol, [])`

🔴 **Line 289** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `oi_threshold = self.manipulation_config.get('divergence_oi_threshold', 0.01)`

🔴 **Line 314** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weights = self.manipulation_config.get('weights', {})`

🔴 **Line 438** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 462** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 462** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 470** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `min_points = self.manipulation_config.get('min_data_points', 15)`

🔴 **Line 514** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(alert_data, dict) and alert_data.get('timestamp', 0) >= since_timestamp:`

🔴 **Line 514** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if isinstance(alert_data, dict) and alert_data.get('timestamp', 0) >= since_timestamp:`

🔴 **Line 544** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `alerts.sort(key=lambda x: x['timestamp'], reverse=True)`

🔴 **Line 578** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = alert_data.get('timestamp', 0)`

🔴 **Line 578** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = alert_data.get('timestamp', 0)`

🔴 **Line 614** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"accuracy": self.stats.get('avg_confidence', 0.0),`

🔴 **Line 651** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `historical_data = self._historical_data.get(symbol, [])`

🔴 **Line 651** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `historical_data = self._historical_data.get(symbol, [])`

🔴 **Line 651** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `historical_data = self._historical_data.get(symbol, [])`

🔴 **Line 663** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if len(historical_data) < self.manipulation_config.get('min_data_points', 15):`

### src/monitoring/market_reporter.py

🔴 **Line 384** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `result['volume'] = float(ticker.get('baseVolume', 0.0))  # Changed from 'volume' to 'baseVolume'`

🔴 **Line 407** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `result['volume'] = float(ticker.get('baseVolume', 0.0))  # Changed from 'volume' to 'baseVolume'`

🔴 **Line 845** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `field_names = self.BYBIT_FIELD_MAPPINGS.get(field_type, [field_type])`

🔴 **Line 1006** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `transactions = whale_data.get('transactions', [])`

🔴 **Line 1006** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `transactions = whale_data.get('transactions', [])`

🔴 **Line 1011** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `usd_value = abs(tx.get('usd_value', 0))`

🔴 **Line 1011** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `usd_value = abs(tx.get('usd_value', 0))`

🔴 **Line 1055** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if report.get('quality_score', 100) < self.quality_score_threshold:`

🔴 **Line 1055** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if report.get('quality_score', 100) < self.quality_score_threshold:`

🔴 **Line 1055** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if report.get('quality_score', 100) < self.quality_score_threshold:`

🔴 **Line 1055** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if report.get('quality_score', 100) < self.quality_score_threshold:`

🔴 **Line 1519** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_change_raw = ticker['info'].get('price24hPcnt', '0')`

🔴 **Line 1519** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price_change_raw = ticker['info'].get('price24hPcnt', '0')`

🔴 **Line 1556** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `avg_premium = normalized.get('average_premium', 0)`

🔴 **Line 1645** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sell_vol = sum(abs(float(t['usd_value'])) for t in txs if t.get('side', '').lower() == 'sell')`

🔴 **Line 1713** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sorted_performers = sorted(normalized['top_performers'], key=lambda x: x.get('change_percent', 0), reverse=True)`

🔴 **Line 1719** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `change = performer.get('change_percent', 0)`

🔴 **Line 1804** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'signal': report['market_overview'].get('regime', 'NEUTRAL'),`

🔴 **Line 1804** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'signal': report['market_overview'].get('regime', 'NEUTRAL'),`

🔴 **Line 1840** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'signal': report['market_overview'].get('regime', 'NEUTRAL'),`

🔴 **Line 1882** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_overview = report.get('market_overview', {})`

🔴 **Line 1882** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_overview = report.get('market_overview', {})`

🔴 **Line 1906** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.info(f"Webhook message content length: {len(formatted_report.get('content', ''))}")`

🔴 **Line 1993** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `daily_change = self._safe_float_from_percentage(overview.get('daily_change', 0))`

🔴 **Line 1993** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `daily_change = self._safe_float_from_percentage(overview.get('daily_change', 0))`

🔴 **Line 1993** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `daily_change = self._safe_float_from_percentage(overview.get('daily_change', 0))`

🔴 **Line 2077** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `direction = "📈 BUY" if data.get('net_whale_volume', 0) > 0 else "📉 SELL"`

🔴 **Line 2411** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(reports_json_path, 'w') as f:`

🔴 **Line 2414** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(export_json_path, 'w') as f:`

🔴 **Line 2636** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `report['market_overview']['regime_description'] = regime_map.get(`

🔴 **Line 2647** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_regime = report['market_overview'].get('regime', 'NEUTRAL')`

🔴 **Line 2724** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(debug_log_path, 'w') as f:`

🔴 **Line 2737** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = validated_data.get('timestamp', int(time.time()))`

🔴 **Line 2737** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = validated_data.get('timestamp', int(time.time()))`

🔴 **Line 2881** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(json_path, 'w') as f:`

🔴 **Line 2886** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(export_path, 'w') as f:`

🔴 **Line 3004** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if cache_key not in self.cache or time.time() > self.cache.get(f"{cache_key}_expiry", 0):`

🔴 **Line 3004** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if cache_key not in self.cache or time.time() > self.cache.get(f"{cache_key}_expiry", 0):`

🔴 **Line 3018** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `all_markets = self.cache.get(cache_key, {})`

🔴 **Line 3018** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `all_markets = self.cache.get(cache_key, {})`

🔴 **Line 3179** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `mark_price = float(perp_ticker.get('last', 0))`

🔴 **Line 3254** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current_errors = self.error_counts.get('quarterly_futures_errors', 0)`

🔴 **Line 3260** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if quarterly_ticker and quarterly_ticker.get('last'):`

🔴 **Line 3316** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `futures_contracts.sort(key=lambda x: x.get('months_to_expiry', 12))`

🔴 **Line 3316** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `futures_contracts.sort(key=lambda x: x.get('months_to_expiry', 12))`

🔴 **Line 3500** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volume_24h = float(ticker.get('baseVolume', 0))`

🔴 **Line 3500** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volume_24h = float(ticker.get('baseVolume', 0))`

🔴 **Line 3500** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volume_24h = float(ticker.get('baseVolume', 0))`

🔴 **Line 3504** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not order_book or not order_book.get('bids') or not order_book.get('asks'):`

🔴 **Line 3709** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `whale_transactions.sort(key=lambda x: x.get('usd_value', 0), reverse=True)`

🔴 **Line 3709** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `whale_transactions.sort(key=lambda x: x.get('usd_value', 0), reverse=True)`

🔴 **Line 3709** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `whale_transactions.sort(key=lambda x: x.get('usd_value', 0), reverse=True)`

🔴 **Line 3713** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = tx.get('symbol', 'UNKNOWN')`

🔴 **Line 3836** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volume_24h = float(ticker.get('baseVolume', 0)) if ticker else 0`

🔴 **Line 3836** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volume_24h = float(ticker.get('baseVolume', 0)) if ticker else 0`

🔴 **Line 3836** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `volume_24h = float(ticker.get('baseVolume', 0)) if ticker else 0`

🔴 **Line 3854** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `amount = float(trade.get('amount', trade.get('size', trade.get('qty', 0))))`

🔴 **Line 3854** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `amount = float(trade.get('amount', trade.get('size', trade.get('qty', 0))))`

🔴 **Line 3854** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `amount = float(trade.get('amount', trade.get('size', trade.get('qty', 0))))`

🔴 **Line 3877** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `elif side == 'sell' and order_book.get('bids'):`

🔴 **Line 3962** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `amount = float(trade.get('amount', 0))`

🔴 **Line 3987** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `elif side == 'sell' and order_book.get('bids'):`

🔴 **Line 4258** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `change_percent = float(ticker_data.get('percentage', 0))`

🔴 **Line 4258** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `change_percent = float(ticker_data.get('percentage', 0))`

🔴 **Line 4275** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `performers.sort(key=lambda x: x['change_percent'], reverse=True)`

🔴 **Line 4339** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if 'failed_symbols' in report.get('market_overview', {}):`

🔴 **Line 4339** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if 'failed_symbols' in report.get('market_overview', {}):`

🔴 **Line 4339** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if 'failed_symbols' in report.get('market_overview', {}):`

🔴 **Line 4796** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if data.get('retCode') != 0:`

🔴 **Line 4800** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `result = data.get('result', {})`

🔴 **Line 4810** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `oi_raw = ticker.get('openInterest') or ticker.get('openInterestValue')`

🔴 **Line 4837** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'mark_price': data.get('perpetual_price', data.get('index_price', 0)),`

🔴 **Line 4837** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'mark_price': data.get('perpetual_price', data.get('index_price', 0)),`

🔴 **Line 4837** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'mark_price': data.get('perpetual_price', data.get('index_price', 0)),`

🔴 **Line 4837** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'mark_price': data.get('perpetual_price', data.get('index_price', 0)),`

🔴 **Line 4841** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'premium_type': 'Contango' if data.get('perpetual_basis', 0) >= 0 else 'Backwardation',`

🔴 **Line 5061** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'data_timestamp': raw_data.get('timestamp', int(time.time() * 1000))`

🔴 **Line 5061** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'data_timestamp': raw_data.get('timestamp', int(time.time() * 1000))`

🔴 **Line 5061** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'data_timestamp': raw_data.get('timestamp', int(time.time() * 1000))`

🔴 **Line 5123** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `change_24h = price_info.get('change_24h', 0)`

🔴 **Line 5301** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trend = analysis_report['technical_analysis'].get('trend_analysis', 'neutral')`

🔴 **Line 5336** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trend = analysis_report['technical_analysis'].get('trend_analysis', 'neutral')`

🔴 **Line 5409** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime = raw_data['market_overview'].get('regime', 'Unknown')`

🔴 **Line 5435** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'api_performance': raw_data.get('performance_metrics', {}),`

🔴 **Line 5435** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'api_performance': raw_data.get('performance_metrics', {}),`

🔴 **Line 5453** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'regime': raw_data['market_overview'].get('regime', 'Unknown'),`

🔴 **Line 5508** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'data_sources': self._extract_metadata(raw_data).get('data_sources', [])`

🔴 **Line 5508** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'data_sources': self._extract_metadata(raw_data).get('data_sources', [])`

🔴 **Line 5514** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'market_summary': raw_data.get('market_overview', {}),`

🔴 **Line 5552** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if formatted_data.get('status') == 'success' and 'data' in formatted_data:`

🔴 **Line 5552** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if formatted_data.get('status') == 'success' and 'data' in formatted_data:`

🔴 **Line 5552** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if formatted_data.get('status') == 'success' and 'data' in formatted_data:`

🔴 **Line 5552** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if formatted_data.get('status') == 'success' and 'data' in formatted_data:`

🔴 **Line 5603** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `regime = data['market_overview'].get('regime', '')`

### src/monitoring/market_reporter_enhanced_test.py

🔴 **Line 57** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async def _get_aiohttp_session(self) -> 'aiohttp.ClientSession':`

🔴 **Line 60** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._aiohttp_session = aiohttp.ClientSession()`

🔴 **Line 94** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `mark_price = float(perpetual_data.get('markPrice', 0))`

🔴 **Line 94** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `mark_price = float(perpetual_data.get('markPrice', 0))`

🔴 **Line 114** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `bybit_premium = validation_data.get('bybit_premium_index', 0) * 100`

🔴 **Line 114** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `bybit_premium = validation_data.get('bybit_premium_index', 0) * 100`

🔴 **Line 129** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'last_price': float(perpetual_data.get('lastPrice', mark_price)),`

🔴 **Line 199** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get(url, params=params, timeout=3) as response:`

🔴 **Line 725** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `field_names = self.BYBIT_FIELD_MAPPINGS.get(field_type, [field_type])`

🔴 **Line 896** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if report.get('quality_score', 100) < self.quality_score_threshold:`

🔴 **Line 896** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if report.get('quality_score', 100) < self.quality_score_threshold:`

🔴 **Line 896** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if report.get('quality_score', 100) < self.quality_score_threshold:`

🔴 **Line 1369** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `all_markets = self.cache.get(cache_key, {})`

🔴 **Line 1369** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `all_markets = self.cache.get(cache_key, {})`

🔴 **Line 1405** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data_source = result.get('data_source', 'unknown')`

🔴 **Line 1405** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data_source = result.get('data_source', 'unknown')`

🔴 **Line 1405** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data_source = result.get('data_source', 'unknown')`

🔴 **Line 1405** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data_source = result.get('data_source', 'unknown')`

🔴 **Line 1405** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data_source = result.get('data_source', 'unknown')`

🔴 **Line 1669** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession() as session:`

🔴 **Line 1669** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession() as session:`

🔴 **Line 1792** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `futures_contracts.sort(key=lambda x: x.get('months_to_expiry', 12))`

🔴 **Line 1792** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `futures_contracts.sort(key=lambda x: x.get('months_to_expiry', 12))`

🔴 **Line 1792** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `futures_contracts.sort(key=lambda x: x.get('months_to_expiry', 12))`

🔴 **Line 1797** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `futures_price = nearest.get('price', 0)`

🔴 **Line 1896** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `buy_ratio = float(recent.get('buyRatio', 0.5))`

🔴 **Line 1896** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `buy_ratio = float(recent.get('buyRatio', 0.5))`

🔴 **Line 1950** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession() as session:`

🔴 **Line 1994** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.warning(f"Direct API call for long-short ratio for {clean_symbol} failed or returned unexpected data: {api_data.get('retMsg')}")`

🔴 **Line 1994** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.warning(f"Direct API call for long-short ratio for {clean_symbol} failed or returned unexpected data: {api_data.get('retMsg')}")`

🔴 **Line 1997** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `except aiohttp.ClientError as ce:`

🔴 **Line 1997** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `except aiohttp.ClientError as ce:`

🔴 **Line 2073** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if data.get('significant', False)}`

🔴 **Line 2073** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if data.get('significant', False)}`

🔴 **Line 2073** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if data.get('significant', False)}`

🔴 **Line 2111** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'price_change_24h': f"{float(ticker['info'].get('price24hPcnt', 0)) * 100:.2f}%",`

🔴 **Line 2111** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'price_change_24h': f"{float(ticker['info'].get('price24hPcnt', 0)) * 100:.2f}%",`

🔴 **Line 2111** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'price_change_24h': f"{float(ticker['info'].get('price24hPcnt', 0)) * 100:.2f}%",`

🔴 **Line 2111** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'price_change_24h': f"{float(ticker['info'].get('price24hPcnt', 0)) * 100:.2f}%",`

🔴 **Line 2184** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return not section_data.get('regime') or section_data.get('regime') == 'UNKNOWN'`

🔴 **Line 2184** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return not section_data.get('regime') or section_data.get('regime') == 'UNKNOWN'`

🔴 **Line 2318** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `avg_premium = normalized.get('average_premium', 0)`

🔴 **Line 2407** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sell_vol = sum(abs(float(t['usd_value'])) for t in txs if t.get('side', '').lower() == 'sell')`

🔴 **Line 2476** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sorted_performers = sorted(normalized['top_performers'], key=lambda x: x.get('change_percent', 0), reverse=True)`

🔴 **Line 2482** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `change = performer.get('change_percent', 0)`

🔴 **Line 2548** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'signal': report['market_overview'].get('regime', 'NEUTRAL'),`

🔴 **Line 2548** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'signal': report['market_overview'].get('regime', 'NEUTRAL'),`

🔴 **Line 2548** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'signal': report['market_overview'].get('regime', 'NEUTRAL'),`

🔴 **Line 2604** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_overview = report.get('market_overview', {})`

🔴 **Line 2604** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_overview = report.get('market_overview', {})`

🔴 **Line 2604** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_overview = report.get('market_overview', {})`

🔴 **Line 2628** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.info(f"Webhook message content length: {len(formatted_report.get('content', ''))}")`

🔴 **Line 2710** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `daily_change = overview.get('daily_change', 0)`

🔴 **Line 2710** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `daily_change = overview.get('daily_change', 0)`

🔴 **Line 2710** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `daily_change = overview.get('daily_change', 0)`

🔴 **Line 2794** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `direction = "📈 BUY" if data.get('net_whale_volume', 0) > 0 else "📉 SELL"`

🔴 **Line 3111** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(reports_json_path, 'w') as f:`

🔴 **Line 3114** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(export_json_path, 'w') as f:`

🔴 **Line 3336** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `report['market_overview']['regime_description'] = regime_map.get(`

🔴 **Line 3347** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `market_regime = report['market_overview'].get('regime', 'NEUTRAL')`

🔴 **Line 3424** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(debug_log_path, 'w') as f:`

🔴 **Line 3437** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = validated_data.get('timestamp', int(time.time()))`

🔴 **Line 3437** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = validated_data.get('timestamp', int(time.time()))`

🔴 **Line 3581** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(json_path, 'w') as f:`

🔴 **Line 3586** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(export_path, 'w') as f:`

🔴 **Line 3713** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `change_percent = float(ticker_data.get('percentage', 0))`

🔴 **Line 3713** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `change_percent = float(ticker_data.get('percentage', 0))`

🔴 **Line 3730** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `performers.sort(key=lambda x: x['change_percent'], reverse=True)`

### src/monitoring/metrics.py

🔴 **Line 56** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `metrics = self.metrics.get(metric_name, [])`

🔴 **Line 56** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `metrics = self.metrics.get(metric_name, [])`

🔴 **Line 56** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `metrics = self.metrics.get(metric_name, [])`

### src/monitoring/metrics_manager.py

🔴 **Line 121** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if len(times) >= self.performance_config.get('min_samples', 10):`

🔴 **Line 128** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `slow_op_threshold = float(self.performance_config.get('slow_operation_threshold', 2.0))`

🔴 **Line 232** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if len(values) >= self.system_config.get('min_samples', 10):`

🔴 **Line 240** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `invalid_threshold = float(self.system_config.get('invalid_messages_threshold', 100.0))`

🔴 **Line 305** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if len(values) >= self.system_config.get('min_samples', 10):`

🔴 **Line 314** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `memory_config = self.config.get('monitoring', {}).get('memory_tracking', {})`

🔴 **Line 314** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `memory_config = self.config.get('monitoring', {}).get('memory_tracking', {})`

🔴 **Line 318** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cpu_config = self.config.get('monitoring', {}).get('alerts', {}).get('cpu_alerts', {})`

🔴 **Line 358** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `cpu_percent = psutil.cpu_percent(interval=1)`

🔴 **Line 359** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `cpu_times = psutil.cpu_times_percent()`

🔴 **Line 360** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `memory = psutil.virtual_memory()`

🔴 **Line 361** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `disk = psutil.disk_usage('/')`

🔴 **Line 636** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if len(values) >= self.system_config.get('min_samples', 10):`

🔴 **Line 726** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'score': metrics.get('score', 0),`

🔴 **Line 852** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `is_high_frequency = op_context.get("is_high_frequency", False)`

🔴 **Line 861** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if self.memory_tracking_enabled and op_context.get("tracemalloc_snapshot"):`

🔴 **Line 952** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_history = self.config.get('monitoring', {}).get('max_metric_history', 1000)`

🔴 **Line 1044** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `log_level = memory_tracking_config.get('log_level', 'WARNING').upper()`

🔴 **Line 1377** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `for label, trend in memory_report.get("trends", {}).items():`

🔴 **Line 1377** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `for label, trend in memory_report.get("trends", {}).items():`

🔴 **Line 1425** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signal_type = signal_data.get('signal', 'NEUTRAL')`

🔴 **Line 1451** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `components = signal_data.get('components', {})`

### src/monitoring/monitor.py

🔴 **Line 161** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = data.get('timestamp')`

🔴 **Line 161** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = data.get('timestamp')`

🔴 **Line 371** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'bids': result_data.get('b', []),`

🔴 **Line 813** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = data.get('timestamp')`

🔴 **Line 813** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = data.get('timestamp')`

🔴 **Line 1023** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'bids': result_data.get('b', []),`

🔴 **Line 1521** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `prices.append(float(trade.get('price', 0)))`

🔴 **Line 1521** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `prices.append(float(trade.get('price', 0)))`

🔴 **Line 1550** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `side = trade.get('side')`

🔴 **Line 1550** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `side = trade.get('side')`

🔴 **Line 1839** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if self.debug_config.get('save_visualizations', False):`

🔴 **Line 1885** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.large_order_config = self.config.get('monitoring', {}).get('large_orders', {`

🔴 **Line 1896** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.whale_activity_config = self.config.get('monitoring', {}).get('whale_activity', {`

🔴 **Line 1896** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.whale_activity_config = self.config.get('monitoring', {}).get('whale_activity', {`

🔴 **Line 1927** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._max_concurrent_analyses = self.config.get('monitoring', {}).get('max_concurrent_analyses', 10)`

🔴 **Line 1967** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if self.config.get('exchanges', {}).get('bybit', {}).get('websocket', {}).get('enabled', False):`

🔴 **Line 2078** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data = message.get('data', {})`

🔴 **Line 2078** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data = message.get('data', {})`

🔴 **Line 2156** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': int(candle.get('timestamp', 0) or candle.get('start', 0)),`

🔴 **Line 2299** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'id': trade.get('tradeId', str(timestamp) + str(len(self.ws_data['trades']))),`

🔴 **Line 2337** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `liquidation_data_array = message.get('data', [])`

🔴 **Line 2346** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price = float(liquidation_data.get('p', 0))`

🔴 **Line 2474** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'enabled': self.websocket_config.get('enabled', False)`

🔴 **Line 2722** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = analysis_result.get('confluence_score', 0)`

🔴 **Line 2884** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if status.get('status') == 'critical'`

🔴 **Line 2884** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if status.get('status') == 'critical'`

🔴 **Line 2900** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'rest_calls': mdm_stats.get('rest_calls', 0),`

🔴 **Line 2978** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeframe_results = await self.validate_timeframes(market_data.get('ohlcv', {}))`

🔴 **Line 3064** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"Preprocessing market data for {market_data.get('symbol', 'unknown')}")`

🔴 **Line 3064** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"Preprocessing market data for {market_data.get('symbol', 'unknown')}")`

🔴 **Line 3086** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `isinstance(level[0], str) for level in orderbook_data.get('bids', [])[:5] if isinstance(level, (list, tuple)) and len(level) >= 2`

🔴 **Line 3116** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `isinstance(first_trade.get(field), str)`

🔴 **Line 3166** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'price': float(trade.get('execPrice', trade.get('price', 0))),`

🔴 **Line 3166** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'price': float(trade.get('execPrice', trade.get('price', 0))),`

🔴 **Line 3242** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if status.get('status') != 'healthy':`

🔴 **Line 3297** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `age = freshness.get('age_seconds', 0)`

🔴 **Line 3330** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `memory = psutil.virtual_memory()`

🔴 **Line 3342** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `cpu_percent = psutil.cpu_percent(interval=1)`

🔴 **Line 3428** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score = result.get('confluence_score', 0)`

🔴 **Line 3446** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `formatter_results = result.get('results', {})`

🔴 **Line 3509** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not result.get('market_interpretations') and hasattr(self, 'signal_generator') and self.signal_generator:`

🔴 **Line 3525** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"Successfully added enhanced data: market_interpretations={len(enhanced_data.get('market_interpretations', []))}, actionable_insights={len(enhanced_data.get('actionable_insights', []))}")`

🔴 **Line 3538** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `display_results = result.get('results', formatter_results)`

🔴 **Line 3604** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `transaction_id = analysis_result.get('transaction_id', str(uuid.uuid4()))`

🔴 **Line 3604** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `transaction_id = analysis_result.get('transaction_id', str(uuid.uuid4()))`

🔴 **Line 3604** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `transaction_id = analysis_result.get('transaction_id', str(uuid.uuid4()))`

🔴 **Line 3616** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score = analysis_result.get('confluence_score', 0)`

🔴 **Line 3616** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score = analysis_result.get('confluence_score', 0)`

🔴 **Line 3634** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price = ticker.get('last', ticker.get('close', None))`

🔴 **Line 3880** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `pdf_path = signal_data.get('pdf_path')`

🔴 **Line 3963** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trading_config = self.config.get('trading', {})`

🔴 **Line 3963** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trading_config = self.config.get('trading', {})`

🔴 **Line 4158** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = symbol or market_data.get('symbol', 'unknown')`

🔴 **Line 4158** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = symbol or market_data.get('symbol', 'unknown')`

🔴 **Line 4168** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 4168** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 4191** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 4191** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 4291** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', 'unknown')`

🔴 **Line 4291** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', 'unknown')`

🔴 **Line 4291** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', 'unknown')`

🔴 **Line 4392** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current_time - self._last_ohlcv_update.get(symbol, 0) < self._cache_ttl):`

🔴 **Line 4419** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `limit = timeframe_limits.get(tf_name, 100)`

🔴 **Line 4419** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `limit = timeframe_limits.get(tf_name, 100)`

🔴 **Line 4419** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `limit = timeframe_limits.get(tf_name, 100)`

🔴 **Line 4419** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `limit = timeframe_limits.get(tf_name, 100)`

🔴 **Line 4458** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data_length = len(data.get("data", [])) if isinstance(data, dict) and "data" in data else 0`

🔴 **Line 4458** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data_length = len(data.get("data", [])) if isinstance(data, dict) and "data" in data else 0`

🔴 **Line 4458** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data_length = len(data.get("data", [])) if isinstance(data, dict) and "data" in data else 0`

🔴 **Line 4458** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data_length = len(data.get("data", [])) if isinstance(data, dict) and "data" in data else 0`

🔴 **Line 4566** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_update = self._last_ohlcv_update.get(symbol, 0)`

🔴 **Line 4566** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_update = self._last_ohlcv_update.get(symbol, 0)`

🔴 **Line 4566** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_update = self._last_ohlcv_update.get(symbol, 0)`

🔴 **Line 4710** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', 'unknown')`

🔴 **Line 4710** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', 'unknown')`

🔴 **Line 4721** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"OHLCV keys: {market_data.get('ohlcv', {}).keys()}")`

🔴 **Line 4721** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"OHLCV keys: {market_data.get('ohlcv', {}).keys()}")`

🔴 **Line 4790** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"Error in confluence analysis for {market_data.get('symbol')}: {str(e)}", exc_info=True)`

🔴 **Line 4790** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"Error in confluence analysis for {market_data.get('symbol')}: {str(e)}", exc_info=True)`

🔴 **Line 4790** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"Error in confluence analysis for {market_data.get('symbol')}: {str(e)}", exc_info=True)`

🔴 **Line 4790** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"Error in confluence analysis for {market_data.get('symbol')}: {str(e)}", exc_info=True)`

🔴 **Line 4790** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"Error in confluence analysis for {market_data.get('symbol')}: {str(e)}", exc_info=True)`

🔴 **Line 4792** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `analysis_result = self._get_default_scores(market_data.get('symbol'))`

🔴 **Line 4855** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current_time - self._market_data_cache[symbol].get('fetch_time', 0) < self._cache_ttl):`

🔴 **Line 4867** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cached_data['ohlcv'] = market_data.get('ohlcv', cached_data['ohlcv'])`

🔴 **Line 4894** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'raw_responses': market_data.get('raw_responses', {}),`

🔴 **Line 4894** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'raw_responses': market_data.get('raw_responses', {}),`

🔴 **Line 5026** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeframe_config = self.config.get('timeframes', {`

🔴 **Line 5026** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeframe_config = self.config.get('timeframes', {`

🔴 **Line 5026** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeframe_config = self.config.get('timeframes', {`

🔴 **Line 5125** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ltf = timeframe_config.get('ltf', {}).get('interval', '5m')`

🔴 **Line 5375** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `prices.append(float(trade.get('price', 0)))`

🔴 **Line 5375** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `prices.append(float(trade.get('price', 0)))`

🔴 **Line 5404** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `side = trade.get('side')`

🔴 **Line 5404** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `side = trade.get('side')`

🔴 **Line 5479** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol_str', 'unknown')`

🔴 **Line 5576** (pandas_inefficiency)
- Issue: iterrows() is slow - consider vectorization
- Code: `colors = ['green' if row['close'] >= row['open'] else 'red' for _, row in df.iterrows()]`

🔴 **Line 5579** (pandas_inefficiency)
- Issue: iterrows() is slow - consider vectorization
- Code: `for i, (timestamp, row) in enumerate(df.iterrows()):`

🔴 **Line 5702** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': pd.to_datetime(trade.get('timestamp', 0), unit='ms'),`

🔴 **Line 5702** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': pd.to_datetime(trade.get('timestamp', 0), unit='ms'),`

🔴 **Line 6011** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_retries = self.retry_config.get('max_retries', 3)`

🔴 **Line 6011** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_retries = self.retry_config.get('max_retries', 3)`

🔴 **Line 6093** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_requests = self.rate_limit_config.get('max_requests_per_second', 5)`

🔴 **Line 6150** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = analysis_result.get('confluence_score', 0)`

🔴 **Line 6150** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = analysis_result.get('confluence_score', 0)`

🔴 **Line 6218** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `interpretation = analysis_result.get('overall_interpretation', '')`

🔴 **Line 6513** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if status.get('status') != 'healthy':`

🔴 **Line 6568** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `age = freshness.get('age_seconds', 0)`

🔴 **Line 6658** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_alert_time = self._last_whale_alert.get(symbol, 0)`

🔴 **Line 6666** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook')`

🔴 **Line 6677** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 6677** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 6684** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `bids = orderbook.get('bids', [])`

🔴 **Line 6770** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trade_time = float(trade.get('timestamp', 0)) / 1000 if isinstance(trade.get('timestamp'), int) else 0`

🔴 **Line 6851** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trades_count = current_activity.get('whale_trades_count', 0)`

🔴 **Line 6902** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trades_count = current_activity.get('whale_trades_count', 0)`

🔴 **Line 6971** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `whale_trades_count = current_activity.get('whale_trades_count', 0)`

🔴 **Line 6971** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `whale_trades_count = current_activity.get('whale_trades_count', 0)`

🔴 **Line 7115** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = formatted_data.get('symbol', 'UNKNOWN')`

🔴 **Line 7115** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = formatted_data.get('symbol', 'UNKNOWN')`

🔴 **Line 7115** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = formatted_data.get('symbol', 'UNKNOWN')`

🔴 **Line 7150** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"SCHEDULE_ANALYSIS: Error in schedule_market_analysis for {formatted_data.get('symbol', 'UNKNOWN')}: {str(e)}")`

🔴 **Line 7150** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"SCHEDULE_ANALYSIS: Error in schedule_market_analysis for {formatted_data.get('symbol', 'UNKNOWN')}: {str(e)}")`

🔴 **Line 7150** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"SCHEDULE_ANALYSIS: Error in schedule_market_analysis for {formatted_data.get('symbol', 'UNKNOWN')}: {str(e)}")`

🔴 **Line 7360** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not component_diagnostic.get('issues'):`

🔴 **Line 7360** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not component_diagnostic.get('issues'):`

🔴 **Line 7360** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not component_diagnostic.get('issues'):`

🔴 **Line 7387** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'quality_score': full_report.get('quality_score') if full_report else None,`

### src/monitoring/monitor_original.py

🔴 **Line 158** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = data.get('timestamp')`

🔴 **Line 158** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = data.get('timestamp')`

🔴 **Line 368** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'bids': result_data.get('b', []),`

🔴 **Line 866** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `prices.append(float(trade.get('price', 0)))`

🔴 **Line 866** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `prices.append(float(trade.get('price', 0)))`

🔴 **Line 895** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `side = trade.get('side')`

🔴 **Line 895** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `side = trade.get('side')`

🔴 **Line 1180** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if self.debug_config.get('save_visualizations', False):`

🔴 **Line 1226** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.large_order_config = self.config.get('monitoring', {}).get('large_orders', {`

🔴 **Line 1237** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.whale_activity_config = self.config.get('monitoring', {}).get('whale_activity', {`

🔴 **Line 1373** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data = message.get('data', {})`

🔴 **Line 1373** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data = message.get('data', {})`

🔴 **Line 1451** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': int(candle.get('timestamp', 0) or candle.get('start', 0)),`

🔴 **Line 1555** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'id': trade.get('tradeId', str(timestamp) + str(len(self.ws_data['trades']))),`

🔴 **Line 1589** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `liquidation_data = data.get('data', {})`

🔴 **Line 1655** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'enabled': self.websocket_config.get('enabled', False)`

🔴 **Line 1898** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = analysis_result.get('confluence_score', 0)`

🔴 **Line 1998** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if status.get('status') == 'critical'`

🔴 **Line 1998** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if status.get('status') == 'critical'`

🔴 **Line 2014** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'rest_calls': mdm_stats.get('rest_calls', 0),`

🔴 **Line 2092** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeframe_results = await self.validate_timeframes(market_data.get('ohlcv', {}))`

🔴 **Line 2443** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if status.get('status') != 'healthy':`

🔴 **Line 2498** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `age = freshness.get('age_seconds', 0)`

🔴 **Line 2531** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `memory = psutil.virtual_memory()`

🔴 **Line 2543** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `cpu_percent = psutil.cpu_percent(interval=1)`

🔴 **Line 2629** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score = result.get('confluence_score', 0)`

🔴 **Line 2647** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `formatter_results = result.get('results', {})`

🔴 **Line 2686** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `identified_component = component_mappings.get(first_words.strip().lower(), 'Analysis')`

🔴 **Line 2686** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `identified_component = component_mappings.get(first_words.strip().lower(), 'Analysis')`

🔴 **Line 2741** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"Successfully added enhanced data: market_interpretations={len(enhanced_data.get('market_interpretations', []))}, actionable_insights={len(enhanced_data.get('actionable_insights', []))}")`

🔴 **Line 2798** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `transaction_id = analysis_result.get('transaction_id', str(uuid.uuid4()))`

🔴 **Line 2798** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `transaction_id = analysis_result.get('transaction_id', str(uuid.uuid4()))`

🔴 **Line 2798** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `transaction_id = analysis_result.get('transaction_id', str(uuid.uuid4()))`

🔴 **Line 2810** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score = analysis_result.get('confluence_score', 0)`

🔴 **Line 2810** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score = analysis_result.get('confluence_score', 0)`

🔴 **Line 2991** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `identified_component = component_mappings.get(first_words.strip().lower(), 'Analysis')`

🔴 **Line 2991** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `identified_component = component_mappings.get(first_words.strip().lower(), 'Analysis')`

🔴 **Line 3098** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `pdf_path = signal_data.get('pdf_path')`

🔴 **Line 3181** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trading_config = self.config.get('trading', {})`

🔴 **Line 3181** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trading_config = self.config.get('trading', {})`

🔴 **Line 3376** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = symbol or market_data.get('symbol', 'unknown')`

🔴 **Line 3376** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = symbol or market_data.get('symbol', 'unknown')`

🔴 **Line 3386** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 3386** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 3409** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 3409** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 3467** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', 'unknown')`

🔴 **Line 3467** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', 'unknown')`

🔴 **Line 3467** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', 'unknown')`

🔴 **Line 3568** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current_time - self._last_ohlcv_update.get(symbol, 0) < self._cache_ttl):`

🔴 **Line 3595** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `limit = timeframe_limits.get(tf_name, 100)`

🔴 **Line 3595** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `limit = timeframe_limits.get(tf_name, 100)`

🔴 **Line 3595** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `limit = timeframe_limits.get(tf_name, 100)`

🔴 **Line 3595** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `limit = timeframe_limits.get(tf_name, 100)`

🔴 **Line 3634** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data_length = len(data.get("data", [])) if isinstance(data, dict) and "data" in data else 0`

🔴 **Line 3634** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data_length = len(data.get("data", [])) if isinstance(data, dict) and "data" in data else 0`

🔴 **Line 3634** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data_length = len(data.get("data", [])) if isinstance(data, dict) and "data" in data else 0`

🔴 **Line 3634** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `data_length = len(data.get("data", [])) if isinstance(data, dict) and "data" in data else 0`

🔴 **Line 3742** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_update = self._last_ohlcv_update.get(symbol, 0)`

🔴 **Line 3742** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_update = self._last_ohlcv_update.get(symbol, 0)`

🔴 **Line 3742** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_update = self._last_ohlcv_update.get(symbol, 0)`

🔴 **Line 3886** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', 'unknown')`

🔴 **Line 3886** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol', 'unknown')`

🔴 **Line 3897** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"OHLCV keys: {market_data.get('ohlcv', {}).keys()}")`

🔴 **Line 3897** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.debug(f"OHLCV keys: {market_data.get('ohlcv', {}).keys()}")`

🔴 **Line 3966** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"Error in confluence analysis for {market_data.get('symbol')}: {str(e)}", exc_info=True)`

🔴 **Line 3966** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"Error in confluence analysis for {market_data.get('symbol')}: {str(e)}", exc_info=True)`

🔴 **Line 3966** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"Error in confluence analysis for {market_data.get('symbol')}: {str(e)}", exc_info=True)`

🔴 **Line 3966** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"Error in confluence analysis for {market_data.get('symbol')}: {str(e)}", exc_info=True)`

🔴 **Line 3966** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.error(f"Error in confluence analysis for {market_data.get('symbol')}: {str(e)}", exc_info=True)`

🔴 **Line 3968** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `analysis_result = self._get_default_scores(market_data.get('symbol'))`

🔴 **Line 4031** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current_time - self._market_data_cache[symbol].get('fetch_time', 0) < self._cache_ttl):`

🔴 **Line 4043** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cached_data['ohlcv'] = market_data.get('ohlcv', cached_data['ohlcv'])`

🔴 **Line 4070** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'raw_responses': market_data.get('raw_responses', {}),`

🔴 **Line 4070** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'raw_responses': market_data.get('raw_responses', {}),`

🔴 **Line 4202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeframe_config = self.config.get('timeframes', {`

🔴 **Line 4202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeframe_config = self.config.get('timeframes', {`

🔴 **Line 4202** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeframe_config = self.config.get('timeframes', {`

🔴 **Line 4301** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ltf = timeframe_config.get('ltf', {}).get('interval', '5m')`

🔴 **Line 4551** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `prices.append(float(trade.get('price', 0)))`

🔴 **Line 4551** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `prices.append(float(trade.get('price', 0)))`

🔴 **Line 4580** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `side = trade.get('side')`

🔴 **Line 4580** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `side = trade.get('side')`

🔴 **Line 4655** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = market_data.get('symbol_str', 'unknown')`

🔴 **Line 4752** (pandas_inefficiency)
- Issue: iterrows() is slow - consider vectorization
- Code: `colors = ['green' if row['close'] >= row['open'] else 'red' for _, row in df.iterrows()]`

🔴 **Line 4755** (pandas_inefficiency)
- Issue: iterrows() is slow - consider vectorization
- Code: `for i, (timestamp, row) in enumerate(df.iterrows()):`

🔴 **Line 4878** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': pd.to_datetime(trade.get('timestamp', 0), unit='ms'),`

🔴 **Line 4878** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timestamp': pd.to_datetime(trade.get('timestamp', 0), unit='ms'),`

🔴 **Line 5187** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_retries = self.retry_config.get('max_retries', 3)`

🔴 **Line 5187** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_retries = self.retry_config.get('max_retries', 3)`

🔴 **Line 5269** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `max_requests = self.rate_limit_config.get('max_requests_per_second', 5)`

🔴 **Line 5326** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = analysis_result.get('confluence_score', 0)`

🔴 **Line 5326** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = analysis_result.get('confluence_score', 0)`

🔴 **Line 5394** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `interpretation = analysis_result.get('overall_interpretation', '')`

🔴 **Line 5689** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if status.get('status') != 'healthy':`

🔴 **Line 5744** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `age = freshness.get('age_seconds', 0)`

🔴 **Line 5777** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `memory = psutil.virtual_memory()`

🔴 **Line 5789** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `cpu_percent = psutil.cpu_percent(interval=1)`

🔴 **Line 5810** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = formatted_data.get('symbol', 'UNKNOWN')`

🔴 **Line 5947** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not component_diagnostic.get('issues'):`

🔴 **Line 5947** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not component_diagnostic.get('issues'):`

🔴 **Line 5947** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not component_diagnostic.get('issues'):`

🔴 **Line 5974** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'quality_score': full_report.get('quality_score') if full_report else None,`

🔴 **Line 6221** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_alert_time = self._last_whale_alert.get(symbol, 0)`

🔴 **Line 6229** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook')`

🔴 **Line 6240** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 6240** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 6247** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `bids = orderbook.get('bids', [])`

🔴 **Line 6333** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trade_time = float(trade.get('timestamp', 0)) / 1000 if isinstance(trade.get('timestamp'), int) else 0`

🔴 **Line 6414** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trades_count = current_activity.get('whale_trades_count', 0)`

🔴 **Line 6465** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trades_count = current_activity.get('whale_trades_count', 0)`

🔴 **Line 6534** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `whale_trades_count = current_activity.get('whale_trades_count', 0)`

🔴 **Line 6534** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `whale_trades_count = current_activity.get('whale_trades_count', 0)`

### src/monitoring/optimized_alpha_scanner.py

🔴 **Line 134** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not self.alpha_config.get('alpha_alerts_enabled', True):`

🔴 **Line 154** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if extreme_mode and not self.tiers[tier].get('enabled', True):`

🔴 **Line 190** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `silent_config = self.alpha_config.get('silent_mode', {})`

🔴 **Line 203** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `daily_limit = self.alpha_config.get('throttling', {}).get('max_total_alerts_per_day', 20)`

🔴 **Line 212** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if hard_blocks.get(pattern, False):`

🔴 **Line 267** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cooldown_hours = self.tiers[tier].get('symbol_cooldown_hours', 4)`

🔴 **Line 267** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cooldown_hours = self.tiers[tier].get('symbol_cooldown_hours', 4)`

🔴 **Line 376** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if (self.pattern_weights.get('beta_expansion', 0) > 0 and`

🔴 **Line 394** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `pattern_enabled = self.pattern_configs.get(pattern, {}).get('enabled', True)`

🔴 **Line 415** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `pattern_config = self.pattern_configs.get(pattern, {})`

🔴 **Line 415** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `pattern_config = self.pattern_configs.get(pattern, {})`

🔴 **Line 415** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `pattern_config = self.pattern_configs.get(pattern, {})`

🔴 **Line 457** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `pattern_weight = self.pattern_weights.get(pattern, 0.2)`

🔴 **Line 457** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `pattern_weight = self.pattern_weights.get(pattern, 0.2)`

🔴 **Line 503** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not tier_config.get('cooldown_override', False):`

🔴 **Line 503** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not tier_config.get('cooldown_override', False):`

🔴 **Line 533** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cooldown_seconds = tier_config.get('cooldown_minutes', 60) * 60`

🔴 **Line 594** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta_change = data.get('beta_change', 0)`

🔴 **Line 594** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta_change = data.get('beta_change', 0)`

🔴 **Line 648** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `correlation_drop = data.get('correlation_drop', 0)`

🔴 **Line 648** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `correlation_drop = data.get('correlation_drop', 0)`

🔴 **Line 648** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `correlation_drop = data.get('correlation_drop', 0)`

🔴 **Line 696** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trend_strength = data.get('trend_strength', 0.5)`

🔴 **Line 696** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trend_strength = data.get('trend_strength', 0.5)`

🔴 **Line 696** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `trend_strength = data.get('trend_strength', 0.5)`

🔴 **Line 733** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `breakdown_magnitude = data.get('breakdown_magnitude', 0.3)`

🔴 **Line 733** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `breakdown_magnitude = data.get('breakdown_magnitude', 0.3)`

🔴 **Line 733** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `breakdown_magnitude = data.get('breakdown_magnitude', 0.3)`

🔴 **Line 733** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `breakdown_magnitude = data.get('breakdown_magnitude', 0.3)`

🔴 **Line 762** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeframe_alignment = data.get('timeframe_alignment', 0.6)`

### src/monitoring/report_generator.py

🔴 **Line 41** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.reports_dir = Path(config.get('reports_dir', 'reports'))`

🔴 **Line 63** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal.get('symbol', 'UNKNOWN')`

🔴 **Line 63** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal.get('symbol', 'UNKNOWN')`

🔴 **Line 63** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal.get('symbol', 'UNKNOWN')`

🔴 **Line 63** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal.get('symbol', 'UNKNOWN')`

🔴 **Line 164** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal.get('symbol', 'UNKNOWN')`

🔴 **Line 272** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `color=style.get('color', 'black'),`

🔴 **Line 272** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `color=style.get('color', 'black'),`

🔴 **Line 272** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `color=style.get('color', 'black'),`

🔴 **Line 272** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `color=style.get('color', 'black'),`

🔴 **Line 299** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal.get('symbol', 'UNKNOWN')`

🔴 **Line 456** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `entry_price = signal.get('entry_price', price)`

🔴 **Line 484** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `target_price = target_data.get("price", 0)`

### src/monitoring/signal_frequency_tracker.py

🔴 **Line 106** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `frequency_config = config.get('signal_frequency_tracking', {})`

🔴 **Line 106** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `frequency_config = config.get('signal_frequency_tracking', {})`

🔴 **Line 115** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.score_improvement_threshold = frequency_config.get('score_improvement_threshold', 3.0)  # Updated default`

🔴 **Line 115** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.score_improvement_threshold = frequency_config.get('score_improvement_threshold', 3.0)  # Updated default`

🔴 **Line 115** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.score_improvement_threshold = frequency_config.get('score_improvement_threshold', 3.0)  # Updated default`

🔴 **Line 154** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `notification_style = self.signal_updates.get('notification_style', {})`

🔴 **Line 217** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `signal_type_str = signal_data.get('signal_type', signal_data.get('signal', 'NEUTRAL'))`

🔴 **Line 324** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.volume_history[symbol].append(components.get('volume', 0))`

🔴 **Line 324** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.volume_history[symbol].append(components.get('volume', 0))`

🔴 **Line 324** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.volume_history[symbol].append(components.get('volume', 0))`

🔴 **Line 349** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cooldown_period = self.cooldown_periods.get(current_signal.signal_type.value, 1800)`

🔴 **Line 488** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cooldown_period = self.cooldown_periods.get('BUY', 1800)`

🔴 **Line 488** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cooldown_period = self.cooldown_periods.get('BUY', 1800)`

🔴 **Line 488** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cooldown_period = self.cooldown_periods.get('BUY', 1800)`

🔴 **Line 500** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if frequency_count >= self.frequency_thresholds.get('high_frequency', 3):`

🔴 **Line 558** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_update_time = self.last_signal_updates.get(symbol, 0)`

🔴 **Line 627** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `prev_val = prev_components.get(component, 0)`

🔴 **Line 827** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol_history = self.signal_history.get(symbol, [])`

🔴 **Line 884** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `frequency_config = new_config.get('signal_frequency_tracking', {})`

🔴 **Line 884** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `frequency_config = new_config.get('signal_frequency_tracking', {})`

### src/monitoring/smart_money_detector.py

🔴 **Line 137** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if not self.smart_money_config.get('enabled', True):`

🔴 **Line 184** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 184** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 184** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 184** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderbook = market_data.get('orderbook', {})`

🔴 **Line 201** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 201** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `ticker = market_data.get('ticker', {})`

🔴 **Line 224** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `oi = market_data.get('open_interest', 0)`

🔴 **Line 224** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `oi = market_data.get('open_interest', 0)`

🔴 **Line 673** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_alert_time = self.last_alerts.get(symbol, 0)`

🔴 **Line 673** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `last_alert_time = self.last_alerts.get(symbol, 0)`

### src/optimization/confluence_parameter_spaces.py

🔴 **Line 338** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if thresholds.get('buy_threshold', 70) <= thresholds.get('sell_threshold', 35):`

### src/optimization/objectives.py

🔴 **Line 62** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.risk_free_rate = config.get('risk_free_rate', 0.02)  # 2% annual`

### src/optimization/optuna_engine.py

🔴 **Line 193** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `study = self.studies.get(study_name)`

🔴 **Line 193** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `study = self.studies.get(study_name)`

🔴 **Line 207** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `study = self.studies.get(study_name)`

🔴 **Line 207** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `study = self.studies.get(study_name)`

🔴 **Line 207** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `study = self.studies.get(study_name)`

🔴 **Line 243** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `study = self.studies.get(study_name)`

🔴 **Line 243** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `study = self.studies.get(study_name)`

### src/optimization/parameter_spaces.py

🔴 **Line 333** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `params = spaces.parameter_registry.get(parameter_space, {})`

🔴 **Line 342** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `step = param_config.get('step', (max_val - min_val) / 100)`

🔴 **Line 353** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return len(self.parameter_registry.get(parameter_space, {}))`

### src/portfolio/portfolio_manager.py

🔴 **Line 364** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sleep_seconds = frequency_map.get(self.rebalancing_frequency, 86400)`

🔴 **Line 364** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sleep_seconds = frequency_map.get(self.rebalancing_frequency, 86400)`

### src/reports/bitcoin_beta_7day_report.py

🔴 **Line 87** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.symbols = kwargs.get('symbols', [`

🔴 **Line 87** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.symbols = kwargs.get('symbols', [`

🔴 **Line 109** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.min_data_points = kwargs.get('min_data_points', 20)`

🔴 **Line 554** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return positions.get(requested_position, positions['bottom-right'])`

🔴 **Line 722** (blocking_in_async)
- Issue: Cryptographic operations can be slow (in async function)
- Code: `cache_key = hashlib.md5(`

🔴 **Line 732** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(cache_file, 'rb') as f:`

🔴 **Line 822** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(cache_file, 'wb') as f:`

🔴 **Line 1075** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `chart_tasks.sort(key=lambda x: x['priority'])`

🔴 **Line 1186** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 1280** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 1351** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 1450** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 1560** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 1726** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1]['beta'], reverse=True)`

🔴 **Line 1786** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(html_path, 'w', encoding='utf-8') as f:`

🔴 **Line 1812** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alpha_config = self.config.get('bitcoin_beta_analysis', {}).get('alpha_detection', {})`

🔴 **Line 1812** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alpha_config = self.config.get('bitcoin_beta_analysis', {}).get('alpha_detection', {})`

🔴 **Line 1812** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alpha_config = self.config.get('bitcoin_beta_analysis', {}).get('alpha_detection', {})`

🔴 **Line 1927** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 1966** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timeframe_display = {'htf': '4H', 'mtf': '1H', 'ltf': '15M', 'base': '5M'}.get(timeframe, timeframe.upper())`

🔴 **Line 2035** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 2112** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 2271** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(html_path, 'r', encoding='utf-8') as f:`

🔴 **Line 2407** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1]['beta'], reverse=True)`

🔴 **Line 2582** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `btc_data = market_data.get('BTC/USDT', {})`

🔴 **Line 2816** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'diversification_ratio': len(symbols) / (1 + risk_metrics['portfolio_risk'].get('avg_correlation', 0) * (len(symbols) - 1))`

🔴 **Line 2831** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `btc_data = market_data.get('BTC/USDT', {})`

🔴 **Line 2889** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = beta_analysis.get(symbol, {}).get(tf_name, {}).get('beta', 0)`

🔴 **Line 2889** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = beta_analysis.get(symbol, {}).get(tf_name, {}).get('beta', 0)`

🔴 **Line 2889** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = beta_analysis.get(symbol, {}).get(tf_name, {}).get('beta', 0)`

🔴 **Line 2895** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `btc_data = market_data.get('BTC/USDT', {}).get(tf_name)`

### src/reports/bitcoin_beta_alpha_detector.py

🔴 **Line 194** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `short_term_betas = [betas.get('base', 0), betas.get('ltf', 0)]`

🔴 **Line 194** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `short_term_betas = [betas.get('base', 0), betas.get('ltf', 0)]`

🔴 **Line 240** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 240** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 240** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 294** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `correlations = {tf: data[tf].get('correlation', 0) for tf in data.keys()}`

🔴 **Line 294** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `correlations = {tf: data[tf].get('correlation', 0) for tf in data.keys()}`

🔴 **Line 299** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current_beta = np.mean([data[tf].get('beta', 0) for tf in data.keys()])`

🔴 **Line 299** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current_beta = np.mean([data[tf].get('beta', 0) for tf in data.keys()])`

🔴 **Line 304** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 304** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 431** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 431** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 431** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 431** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 431** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 431** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 532** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 532** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 532** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 532** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 614** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `correlations = [data.get('correlation', 0) for data in symbol_data.values()]`

🔴 **Line 615** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alphas = [data.get('alpha', 0) for data in symbol_data.values()]`

🔴 **Line 680** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 680** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 680** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 721** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 721** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta = tf_data.get('beta', 0)`

🔴 **Line 766** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'beta': stats.get('beta', 0),`

🔴 **Line 766** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'beta': stats.get('beta', 0),`

### src/reports/bitcoin_beta_report.py

🔴 **Line 105** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta_config = config.get('bitcoin_beta_analysis', {})`

🔴 **Line 105** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta_config = config.get('bitcoin_beta_analysis', {})`

🔴 **Line 105** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta_config = config.get('bitcoin_beta_analysis', {})`

🔴 **Line 121** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf_config = timeframe_config.get(tf_key, default_tf)`

🔴 **Line 121** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `tf_config = timeframe_config.get(tf_key, default_tf)`

🔴 **Line 458** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `return positions.get(requested_position, positions['bottom-right'])`

🔴 **Line 932** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 1024** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 1095** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 1188** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 1291** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 1447** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1]['beta'], reverse=True)`

🔴 **Line 1507** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(html_path, 'w', encoding='utf-8') as f:`

🔴 **Line 1533** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alpha_config = self.config.get('bitcoin_beta_analysis', {}).get('alpha_detection', {})`

🔴 **Line 1533** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alpha_config = self.config.get('bitcoin_beta_analysis', {}).get('alpha_detection', {})`

🔴 **Line 1533** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alpha_config = self.config.get('bitcoin_beta_analysis', {}).get('alpha_detection', {})`

🔴 **Line 1630** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 1735** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 1812** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1], reverse=True)`

🔴 **Line 1970** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(html_path, 'r', encoding='utf-8') as f:`

🔴 **Line 2092** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `symbol_beta_pairs.sort(key=lambda x: x[1]['beta'], reverse=True)`

### src/reports/bitcoin_beta_scheduler.py

🔴 **Line 49** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `beta_config = config.get('bitcoin_beta_analysis', {})`

### src/scripts/fix_market_reporter.py

🔴 **Line 101** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get(url, params=params) as response:`

🔴 **Line 123** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.info(f"❌ ERROR for {symbol}: {result.get('retMsg', 'Unknown error')}")`

### src/scripts/get_bybit_instruments.py

🔴 **Line 29** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession() as session:`

🔴 **Line 35** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get(url, params=params) as response:`

🔴 **Line 43** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if item.get('contractType') != 'LinearPerpetual'`

🔴 **Line 43** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if item.get('contractType') != 'LinearPerpetual'`

🔴 **Line 50** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `asset_futures = [f for f in futures if f.get('symbol', '').startswith(asset)]`

🔴 **Line 55** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = future.get('symbol')`

🔴 **Line 55** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = future.get('symbol')`

### src/scripts/get_bybit_quarterly.py

🔴 **Line 44** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession() as session:`

🔴 **Line 44** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession() as session:`

🔴 **Line 44** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession() as session:`

🔴 **Line 50** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get(url, params=params) as response:`

🔴 **Line 55** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if result.get('retCode') == 0 and result.get('result') and result['result'].get('list'):`

🔴 **Line 61** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.info(f"❌ ERROR for {symbol}: {result.get('retMsg', 'Unknown error')}")`

🔴 **Line 75** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get("https://api.bybit.com/v5/market/instruments-info", params=params) as response:`

🔴 **Line 75** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get("https://api.bybit.com/v5/market/instruments-info", params=params) as response:`

🔴 **Line 75** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get("https://api.bybit.com/v5/market/instruments-info", params=params) as response:`

🔴 **Line 75** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get("https://api.bybit.com/v5/market/instruments-info", params=params) as response:`

🔴 **Line 75** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get("https://api.bybit.com/v5/market/instruments-info", params=params) as response:`

🔴 **Line 80** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if item.get('symbol', '').startswith('BTC') and`

🔴 **Line 85** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.info(f"Symbol: {future.get('symbol')}, Type: {future.get('contractType')}")`

### src/scripts/test_bybit_api.py

🔴 **Line 95** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get(url, params=params) as response:`

🔴 **Line 105** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.info(f"❌ ERROR for {symbol}: {result.get('retMsg', 'Unknown error')}")`

🔴 **Line 120** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get(url, params=params) as response:`

🔴 **Line 120** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get(url, params=params) as response:`

🔴 **Line 120** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get(url, params=params) as response:`

🔴 **Line 120** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get(url, params=params) as response:`

🔴 **Line 120** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get(url, params=params) as response:`

🔴 **Line 128** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `futures = [i for i in instruments if i.get('contractType') != 'LinearPerpetual' and i.get('contractType') != 'InversePerpetual']`

🔴 **Line 134** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol_futures = [f for f in futures if f.get('symbol', '').startswith(symbol)]`

🔴 **Line 134** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol_futures = [f for f in futures if f.get('symbol', '').startswith(symbol)]`

🔴 **Line 134** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol_futures = [f for f in futures if f.get('symbol', '').startswith(symbol)]`

🔴 **Line 139** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = contract.get('symbol')`

🔴 **Line 139** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = contract.get('symbol')`

### src/scripts/test_futures_formats.py

🔴 **Line 72** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession() as session:`

🔴 **Line 98** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get(url, params=params) as response:`

🔴 **Line 106** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.info(f"❌ ERROR for {symbol}: {result.get('retMsg', 'Unknown error')}")`

### src/scripts/verify_bybit_tickers.py

🔴 **Line 53** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with aiohttp.ClientSession() as session:`

🔴 **Line 59** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `async with session.get(url, params=params) as response:`

🔴 **Line 79** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `"bid": float(data.get('bid1Price', 0)),`

🔴 **Line 89** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.info(f"❌ ERROR for {symbol}: {result.get('retMsg', 'Unknown error')}")`

### src/signal_generation/signal_generator.py

🔴 **Line 69** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_config = config.get('confluence', {})`

🔴 **Line 69** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_config = config.get('confluence', {})`

🔴 **Line 143** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `reporting_config = config.get('reporting', {})`

🔴 **Line 244** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight_key: indicators.get(score_key, 50.0)`

🔴 **Line 261** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = indicators.get('timestamp', datetime.utcnow())`

🔴 **Line 261** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = indicators.get('timestamp', datetime.utcnow())`

🔴 **Line 261** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `timestamp = indicators.get('timestamp', datetime.utcnow())`

🔴 **Line 286** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timeframe': indicators.get('timeframe', '1m'),`

🔴 **Line 286** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'timeframe': indicators.get('timeframe', '1m'),`

🔴 **Line 320** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = indicators.get('symbol', 'UNKNOWN')`

🔴 **Line 320** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = indicators.get('symbol', 'UNKNOWN')`

🔴 **Line 414** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alt = alternative_mappings.get(missing)`

🔴 **Line 414** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alt = alternative_mappings.get(missing)`

🔴 **Line 414** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `alt = alternative_mappings.get(missing)`

🔴 **Line 431** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `value = indicators.get(field)`

🔴 **Line 441** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = indicators.get(field)`

🔴 **Line 470** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signal_data.get('symbol', 'UNKNOWN')`

🔴 **Line 494** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = indicators.get('symbol', 'UNKNOWN')`

🔴 **Line 566** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'futures_premium': indicators.get('futures_premium_score', 50.0)  # Add futures premium`

🔴 **Line 566** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'futures_premium': indicators.get('futures_premium_score', 50.0)  # Add futures premium`

🔴 **Line 566** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'futures_premium': indicators.get('futures_premium_score', 50.0)  # Add futures premium`

🔴 **Line 711** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `transaction_id = signal.get('transaction_id', str(uuid.uuid4())[:8])`

🔴 **Line 725** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `price = signal.get('price')`

🔴 **Line 801** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.logger.info(f"[DIAGNOSTICS] [ALERT_DATA] [TXN:{transaction_id}][SIG:{signal_id}] - Influential components count: {len(enhanced_data.get('influential_components', []))}")`

🔴 **Line 883** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component_score = indicators.get(score_key, indicators.get('momentum_score', 50))`

🔴 **Line 883** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component_score = indicators.get(score_key, indicators.get('momentum_score', 50))`

🔴 **Line 954** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'volume_delta': indicators.get('volume_delta'),`

🔴 **Line 954** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'volume_delta': indicators.get('volume_delta'),`

🔴 **Line 954** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'volume_delta': indicators.get('volume_delta'),`

🔴 **Line 954** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'volume_delta': indicators.get('volume_delta'),`

🔴 **Line 1021** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'trade_flow_score': indicators.get('trade_flow_score'),`

🔴 **Line 1021** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'trade_flow_score': indicators.get('trade_flow_score'),`

🔴 **Line 1021** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'trade_flow_score': indicators.get('trade_flow_score'),`

🔴 **Line 1021** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'trade_flow_score': indicators.get('trade_flow_score'),`

🔴 **Line 1083** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'support_resistance': indicators.get('support_resistance'),`

🔴 **Line 1083** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'support_resistance': indicators.get('support_resistance'),`

🔴 **Line 1083** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'support_resistance': indicators.get('support_resistance'),`

🔴 **Line 1083** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'support_resistance': indicators.get('support_resistance'),`

🔴 **Line 1138** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'rsi': indicators.get('rsi'),`

🔴 **Line 1138** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'rsi': indicators.get('rsi'),`

🔴 **Line 1205** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'risk_score': indicators.get('risk_score'),`

🔴 **Line 1205** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'risk_score': indicators.get('risk_score'),`

🔴 **Line 1205** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'risk_score': indicators.get('risk_score'),`

🔴 **Line 1205** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'risk_score': indicators.get('risk_score'),`

🔴 **Line 1267** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'support_resistance': indicators.get('support_resistance'),`

🔴 **Line 1267** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'support_resistance': indicators.get('support_resistance'),`

🔴 **Line 1267** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'support_resistance': indicators.get('support_resistance'),`

🔴 **Line 1267** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'support_resistance': indicators.get('support_resistance'),`

🔴 **Line 1456** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'volatility': results.get('volatility', {}).get('atr_percentage', 2.0),`

🔴 **Line 1456** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'volatility': results.get('volatility', {}).get('atr_percentage', 2.0),`

🔴 **Line 1520** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if components.get('volume', 0) > 60:`

🔴 **Line 1520** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if components.get('volume', 0) > 60:`

🔴 **Line 1547** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if components.get('volume', 0) > 60:`

🔴 **Line 1547** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if components.get('volume', 0) > 60:`

🔴 **Line 1592** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'weight': self.confluence_weights.get(component_name, 1.0)`

🔴 **Line 1592** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `'weight': self.confluence_weights.get(component_name, 1.0)`

🔴 **Line 1605** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.confluence_weights.get(component_name, 1.0)`

🔴 **Line 1605** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `weight = self.confluence_weights.get(component_name, 1.0)`

🔴 **Line 1616** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `component_weight = self.confluence_weights.get(component_name, 1.0)`

🔴 **Line 1762** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `premium_value = data.get('premium_value', 0.0)`

🔴 **Line 1789** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `quarterly_futures = futures_premium.get('quarterly_futures', {})`

🔴 **Line 1797** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sorted_contracts = sorted(contracts, key=lambda x: x.get('months_to_expiry', 12))`

🔴 **Line 1797** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sorted_contracts = sorted(contracts, key=lambda x: x.get('months_to_expiry', 12))`

🔴 **Line 1817** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `current_rate = funding_data.get('current_rate', 0.0)`

🔴 **Line 1838** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `futures_premium = indicators.get('futures_premium', {})`

🔴 **Line 1863** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `premiums = futures_premium.get('premiums', {})`

🔴 **Line 1868** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `premium_value = data.get('premium_value', 0.0)`

🔴 **Line 1888** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `quarterly_futures = futures_premium.get('quarterly_futures', {})`

🔴 **Line 1894** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `sorted_contracts = sorted(contracts, key=lambda x: x.get('months_to_expiry', 12))`

### src/tools/run_diagnostics.py

🔴 **Line 230** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `cpu_percent = psutil.cpu_percent(interval=None)`

🔴 **Line 231** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `memory = psutil.virtual_memory()`

🔴 **Line 237** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `process = psutil.Process(self.process_pid)`

🔴 **Line 243** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `except (psutil.NoSuchProcess, psutil.AccessDenied):`

🔴 **Line 443** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(log_file, 'r', encoding='utf-8') as f:`

🔴 **Line 558** (blocking_in_async)
- Issue: Complex sorting operations (in async function)
- Code: `timestamps.sort(key=lambda x: x[0])`

🔴 **Line 663** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(log_file, 'r', encoding='utf-8') as f:`

🔴 **Line 708** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(txt_report_file, 'w', encoding='utf-8') as f:`

🔴 **Line 838** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `with open(market_visualization_file, 'w', encoding='utf-8') as f:`

### src/trade_execution/confluence_position_manager.py

🔴 **Line 38** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.scaling_threshold = position_config.get('scaling_threshold', {`

🔴 **Line 348** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `position = self.active_positions.get(order_id)`

### src/trade_execution/confluence_trading_strategy.py

🔴 **Line 28** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.long_threshold = strategy_config.get('long_threshold', 70)`

🔴 **Line 151** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `score = analysis.get('score', 50)`

🔴 **Line 198** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = signals.get('symbol')`

### src/trade_execution/trade_executor.py

🔴 **Line 100** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self._session = aiohttp.ClientSession()`

🔴 **Line 140** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if response.get('retCode') == 0:`

🔴 **Line 143** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.warning(f"Failed to apply for demo funds: {response.get('retMsg')}")`

🔴 **Line 151** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if response.get('retCode') == 0:`

🔴 **Line 151** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if response.get('retCode') == 0:`

🔴 **Line 185** (blocking_in_async)
- Issue: Cryptographic operations can be slow (in async function)
- Code: `hashlib.sha256`

🔴 **Line 255** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `technical_score = technical_result.get('score', 50.0)`

🔴 **Line 255** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `technical_score = technical_result.get('score', 50.0)`

🔴 **Line 270** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderflow_score = orderflow_result.get('score', 50.0)`

🔴 **Line 270** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `orderflow_score = orderflow_result.get('score', 50.0)`

🔴 **Line 278** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `bids = market_data['orderbook'].get('bids', [])`

🔴 **Line 672** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.error(f"Failed to set stop loss: {result.get('retMsg')}")`

🔴 **Line 728** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.error(f"Failed to set take profit: {result.get('retMsg')}")`

🔴 **Line 765** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.error(f"Failed to cancel orders: {result.get('retMsg')}")`

🔴 **Line 921** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `account_info = balance_info.get('list', [])`

🔴 **Line 923** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `coins = account.get('coin', [])`

🔴 **Line 925** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if coin.get('coin') == 'USDT':`

🔴 **Line 981** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.error(f"Trade execution failed: {result.get('error')}")`

🔴 **Line 981** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `logger.error(f"Trade execution failed: {result.get('error')}")`

🔴 **Line 1120** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if order_result.get('retCode') != 0:`

### src/utils/async_json.py

🔴 **Line 38** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:`

🔴 **Line 76** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:`

🔴 **Line 103** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `async with aiofiles.open(filepath, 'a', encoding='utf-8') as f:`

🔴 **Line 127** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:`

### src/utils/cache.py

🔴 **Line 61** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `result = cache_manager.get(key)`

### src/utils/caching.py

🔴 **Line 112** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cached_result = cache.get(cache_key)`

🔴 **Line 112** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cached_result = cache.get(cache_key)`

🔴 **Line 145** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cached_result = cache.get(cache_key)`

🔴 **Line 145** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cached_result = cache.get(cache_key)`

### src/utils/formatters/update_formatter.py

🔴 **Line 55** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `components = analysis_result.get('components', {})`

🔴 **Line 55** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `components = analysis_result.get('components', {})`

🔴 **Line 55** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `components = analysis_result.get('components', {})`

### src/utils/helpers.py

🔴 **Line 98** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `async with aiofiles.open(config_path, 'r') as file:`

🔴 **Line 108** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives (in async context!)
- Code: `async with aiofiles.open(metadata_path, 'w') as f:`

🔴 **Line 223** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df = dataframes.get(df_name)`

🔴 **Line 223** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `df = dataframes.get(df_name)`

🔴 **Line 234** (pandas_inefficiency)
- Issue: apply(lambda) can be slow - consider vectorized operations
- Code: `df['bids'] = df['bids'].apply(lambda x: json.dumps(x))`

🔴 **Line 236** (pandas_inefficiency)
- Issue: apply(lambda) can be slow - consider vectorized operations
- Code: `df['asks'] = df['asks'].apply(lambda x: json.dumps(x))`

🔴 **Line 241** (pandas_inefficiency)
- Issue: apply(lambda) can be slow - consider vectorized operations
- Code: `df['blocks'] = df['blocks'].apply(lambda x: json.dumps(x))`

🔴 **Line 286** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.required_points[tf_name] = int(tf_config.get('required', 200))`

🔴 **Line 286** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.required_points[tf_name] = int(tf_config.get('required', 200))`

🔴 **Line 286** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.required_points[tf_name] = int(tf_config.get('required', 200))`

🔴 **Line 286** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.required_points[tf_name] = int(tf_config.get('required', 200))`

🔴 **Line 295** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.timeframe_weights[tf_name] = float(tf_config.get('weight', 0.25))`

🔴 **Line 295** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `self.timeframe_weights[tf_name] = float(tf_config.get('weight', 0.25))`

🔴 **Line 312** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `minutes = self.timeframe_minutes.get(timeframe_type)`

🔴 **Line 312** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `minutes = self.timeframe_minutes.get(timeframe_type)`

🔴 **Line 312** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `minutes = self.timeframe_minutes.get(timeframe_type)`

### src/utils/liquidation_cache.py

🔴 **Line 93** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if cache_data.get("symbol") != symbol:`

🔴 **Line 107** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if event.get('timestamp', 0) > expiry_time`

🔴 **Line 107** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if event.get('timestamp', 0) > expiry_time`

🔴 **Line 146** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = liquidation.get('symbol', 'unknown')`

🔴 **Line 146** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = liquidation.get('symbol', 'unknown')`

🔴 **Line 146** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `symbol = liquidation.get('symbol', 'unknown')`

🔴 **Line 207** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `if event.get('timestamp', 0) > expiry_time`

🔴 **Line 225** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `short_count = sum(1 for e in valid_data if e.get('side', '').lower() == 'short')`

🔴 **Line 254** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `cache_time = cache_data.get("timestamp", 0)`

### src/utils/optimized_logging.py

🔴 **Line 80** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `record = self.log_queue.get(timeout=0.01)`

🔴 **Line 80** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `record = self.log_queue.get(timeout=0.01)`

🔴 **Line 80** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `record = self.log_queue.get(timeout=0.01)`

🔴 **Line 80** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `record = self.log_queue.get(timeout=0.01)`

🔴 **Line 143** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `log_data['request_id'] = request_id_var.get()`

🔴 **Line 204** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `level_color = self.COLORS.get(record.levelname, '')`

🔴 **Line 204** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `level_color = self.COLORS.get(record.levelname, '')`

🔴 **Line 204** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `level_color = self.COLORS.get(record.levelname, '')`

🔴 **Line 210** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `bg_color = self.BG_COLORS.get(record.levelname, '')`

### src/utils/performance.py

🔴 **Line 127** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `start_memory = psutil.Process().memory_info().rss`

🔴 **Line 128** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `start_cpu = psutil.Process().cpu_percent()`

🔴 **Line 136** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `memory_used = psutil.Process().memory_info().rss - start_memory`

🔴 **Line 137** (blocking_in_async)
- Issue: psutil operations can be blocking (in async function)
- Code: `cpu_used = psutil.Process().cpu_percent() - start_cpu`

### src/web_server.py

🔴 **Line 126** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `confluence_score = symbol_data[symbol].get('confluence_score', 0)`

🔴 **Line 142** (api_in_loop)
- Issue: API call in loop - consider batching or rate limiting
- Code: `change_24h = symbol_info.get('change_24h', 0)`

### src/analysis/dataframe_utils.py

🟡 **Line 23** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for column in result.select_dtypes(include=['int']).columns:`

🟡 **Line 28** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for dtype in DataFrameOptimizer.INT_TYPES:`

### src/analysis/market_analyzer.py

🟡 **Line 161** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_depth = sum(float(bid[1]) for bid in bids[:10])`

🟡 **Line 162** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_depth = sum(float(ask[1]) for ask in asks[:10])`

🟡 **Line 302** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_liquidity = sum(float(bid[1]) for bid in bids[:10]) if bids else 0`

🟡 **Line 303** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_liquidity = sum(float(ask[1]) for ask in asks[:10]) if asks else 0`

### src/analysis/validation.py

🟡 **Line 302** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for rule in self._rules[data_type]:`

### src/api/routes/correlation.py

🟡 **Line 97** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols:`

🟡 **Line 125** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for signal in signal_data:`

🟡 **Line 148** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `signal_cols = [col for col in df.columns if col in SIGNAL_TYPES]`

🟡 **Line 156** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, signal1 in enumerate(signal_cols):`

🟡 **Line 172** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for signal in signal_data:`

🟡 **Line 181** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, signals in symbol_signals.items():`

🟡 **Line 183** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for signal_type in SIGNAL_TYPES:`

🟡 **Line 210** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, symbol1 in enumerate(symbols):`

🟡 **Line 263** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols_list:`

🟡 **Line 268** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for signal in signals_data:`

🟡 **Line 311** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for signal_type in SIGNAL_TYPES:`

🟡 **Line 328** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `scores = [data["score"] for data in matrix_data[symbol].values() if isinstance(data, dict)]`

🟡 **Line 341** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols_list:`

🟡 **Line 391** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbols_list = [s.strip() for s in symbols.split(',') if s.strip()]`

🟡 **Line 408** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols_list:`

🟡 **Line 413** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for signal in signals_data:`

🟡 **Line 456** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for signal_type in SIGNAL_TYPES:`

🟡 **Line 473** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `scores = [data["score"] for data in matrix_data[symbol].values() if isinstance(data, dict)]`

🟡 **Line 486** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols_list:`

🟡 **Line 536** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbols_list = [s.strip() for s in symbols.split(',') if s.strip()]`

🟡 **Line 602** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, label1 in enumerate(labels):`

🟡 **Line 640** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbols_list = [s.strip() for s in symbols.split(',') if s.strip()]`

### src/api/routes/dashboard.py

🟡 **Line 46** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for connection in self.active_connections:`

### src/api/routes/liquidation.py

🟡 **Line 187** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `high_severity_events = len([e for e in recent_events if e.severity in [LiquidationSeverity.HIGH, LiquidationSeverity.CRITICAL]])`

🟡 **Line 386** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `funding_info = await exchange_obj.fetch_funding_rate(symbol.upper())`

### src/api/routes/market.py

🟡 **Line 265** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `*[fetch_with_semaphore(symbol) for symbol in clean_symbols],`

🟡 **Line 443** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [Trade(**trade) for trade in trades[:limit]]`

🟡 **Line 552** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbol_list = [s.strip() for s in symbols.split(',')]`

🟡 **Line 852** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_volume = sum(float(bid[1]) for bid in orderbook.get('bids', [])[:10])`

🟡 **Line 853** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_volume = sum(float(ask[1]) for ask in orderbook.get('asks', [])[:10])`

🟡 **Line 879** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `futures_data = await market_reporter._calculate_futures_premium([symbol_formatted])`

🟡 **Line 1002** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `"data_quality": len([c for c in components.values() if isinstance(c, dict) and c.get("score") is not None]) / max(len(components), 1) * 100`

### src/api/routes/sentiment.py

🟡 **Line 171** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `"volatility": _calculate_volatility([h["index"] for h in historical_data])`

### src/api/routes/signal_tracking.py

🟡 **Line 30** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_path, 'r') as f:`

🟡 **Line 50** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for signal_id, signal_data in active_signals.items():`

### src/api/routes/signals.py

🟡 **Line 39** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_path, 'r') as f:`

🟡 **Line 46** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `logger.warning(f"Config file not found in any of these paths: {[str(p) for p in possible_paths]}")`

🟡 **Line 154** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `all_files = [f for f in SIGNALS_DIR.glob(f"{symbol}_*.json") if f.is_file()]`

🟡 **Line 158** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `all_files = [f for f in SIGNALS_DIR.glob(f"*{symbol}*.json") if f.is_file()]`

🟡 **Line 210** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `all_files = [f for f in SIGNALS_DIR.glob("*.json") if f.is_file()]`

🟡 **Line 395** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `all_files = [f for f in SIGNALS_DIR.glob("*.json") if f.is_file()]`

### src/api/routes/system.py

🟡 **Line 32** (sequential_api_calls)
- Issue: Multiple sequential API calls (5) - consider concurrent execution
- Code: `status = await exchange.fetch_status()`

🟡 **Line 102** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `markets = await exchange.fetch_markets()`

### src/api/routes/test_api_endpoints.py

🟡 **Line 17** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(file_path, 'r') as f:`

🟡 **Line 61** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(api_init_path, 'r') as f:`

🟡 **Line 72** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for pattern in patterns:`

🟡 **Line 110** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for file in sorted(route_files):`

🟡 **Line 135** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for module, routes in sorted(routes_by_module.items()):`

🟡 **Line 156** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for module in sorted(registered_modules & route_modules):`

### src/api/routes/test_api_endpoints_simple.py

🟡 **Line 25** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(file_path, 'r') as f:`

🟡 **Line 73** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for file in route_files:`

🟡 **Line 94** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for file, routes in sorted(routes_by_file.items()):`

🟡 **Line 108** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(api_init_path, 'r') as f:`

🟡 **Line 138** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for module, expected_paths in expected_patterns.items():`

🟡 **Line 141** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `actual_paths = [r['path'] for r in routes_by_file[module_file]]`

🟡 **Line 147** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for path in expected_paths:`

### src/api/routes/test_api_endpoints_summary.py

🟡 **Line 16** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(file_path, 'r') as f:`

🟡 **Line 51** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(api_init_path, 'r') as f:`

🟡 **Line 86** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for file in sorted(route_files):`

🟡 **Line 141** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for method, path, desc in core_routes:`

🟡 **Line 149** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for module, routes in sorted(routes_by_module.items()):`

🟡 **Line 178** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `if any(kw in r.get('full_path', r['path']).lower() for kw in keywords)]`

### src/api/routes/trading.py

🟡 **Line 61** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `orders = [order for order in orders if order['status'] == status]`

🟡 **Line 63** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [OrderResponse(**order) for order in orders[:limit]]`

🟡 **Line 84** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `positions = [pos for pos in positions if pos['symbol'] == symbol]`

🟡 **Line 86** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [Position(**pos) for pos in positions]`

🟡 **Line 177** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for exchange_id, exchange in exchange_manager.exchanges.items():`

🟡 **Line 202** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for exchange_id, exchange in exchange_manager.exchanges.items():`

### src/api/routes/whale_activity.py

🟡 **Line 190** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, sym in enumerate(symbols):`

### src/api/websocket/handler.py

🟡 **Line 91** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for client_id in client_ids:`

🟡 **Line 156** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `prices = [float(k['close']) for k in klines]`

🟡 **Line 157** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `volumes = [float(k['volume']) for k in klines]`

🟡 **Line 161** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `'rsi': self.analysis.calculate_rsi(prices).tolist(),`

### src/config/__init__.py

🟡 **Line 24** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_path, 'r') as f:`

### src/config/feature_flags.py

🟡 **Line 97** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for category_name, category_flags in self.feature_flags_config.items():`

🟡 **Line 166** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `matching_flags = [name for name in self.flags.keys() if name.endswith(f".{flag_name}")]`

🟡 **Line 285** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `deprecated_count = len([f for f in self.flags.values() if f.deprecated])`

🟡 **Line 292** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'enabled': len([f for f in category_flags.values() if f.enabled]),`

🟡 **Line 293** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'experimental': len([f for f in category_flags.values() if f.experimental])`

🟡 **Line 318** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for category in self.categories:`

🟡 **Line 332** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(file_path, 'w') as f:`

### src/config/manager.py

🟡 **Line 77** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_path, 'r') as f:`

🟡 **Line 108** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [ConfigManager._process_env_variables(item) for item in config]`

🟡 **Line 148** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(env_path, 'r') as f:`

🟡 **Line 188** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for section, subsections in required_sections.items():`

🟡 **Line 242** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [f for f in fields if f not in section_config]`

### src/config/validator.py

🟡 **Line 44** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_path, 'r') as f:`

🟡 **Line 133** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `section_errors = [err for err in errors if err.startswith(config_section)]`

🟡 **Line 309** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [resolve_value(item) for item in value]`

### src/core/analysis/alpha_scanner.py

🟡 **Line 98** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for exchange_id in scan_exchanges:`

🟡 **Line 619** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `usdt_pairs = [market['symbol'] for market in markets if market.get('symbol', '').endswith('USDT') and market.get('active', True)]`

### src/core/analysis/basis_analysis.py

🟡 **Line 86** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_depth = sum(float(bid[1]) for bid in bids[:5])  # Top 5 levels`

🟡 **Line 87** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_depth = sum(float(ask[1]) for ask in asks[:5])`

🟡 **Line 116** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `buy_trades = [t for t in trades if t['side'].lower() == 'buy']`

🟡 **Line 117** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sell_trades = [t for t in trades if t['side'].lower() == 'sell']`

### src/core/analysis/confluence.py

🟡 **Line 600** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for bid in orderbook['bids']:`

🟡 **Line 967** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf in ['base', 'ltf', 'mtf', 'htf']:`

🟡 **Line 972** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for named_tf, interval_value in indicator.timeframe_map.items():`

🟡 **Line 1043** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in ohlcv_data[tf].columns]`

🟡 **Line 1091** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_after_direct = [tf for tf in required_timeframes if tf not in prepared_data]`

🟡 **Line 1096** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for missing_tf in missing_after_direct:`

🟡 **Line 1115** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for avail_tf in available_timeframes:`

🟡 **Line 1202** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in market_data]`

🟡 **Line 1283** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in data.columns]`

🟡 **Line 1342** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ob_missing = [f for f in ob_required if f not in orderbook]`

🟡 **Line 1629** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in tf_data.columns]`

🟡 **Line 1644** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `for col in [c for c in required_columns if c in tf_data.columns]:`

🟡 **Line 1680** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing = [tf for tf, data in standardized.items() if not isinstance(data, pd.DataFrame)]`

🟡 **Line 1685** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for missing_tf in missing:`

🟡 **Line 1691** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `valid_timeframes = [tf for tf, data in standardized.items() if isinstance(data, pd.DataFrame) and not data.empty]`

🟡 **Line 1723** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sources = [tf for tf in derivation_map[missing_tf]['source']`

🟡 **Line 1788** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'bids': [[float(p), float(s)] for p, s in orderbook['bids']] if orderbook['bids'] else [],`

🟡 **Line 1789** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'asks': [[float(p), float(s)] for p, s in orderbook['asks']] if orderbook['asks'] else [],`

🟡 **Line 2085** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf in ['base', 'ltf', 'mtf', 'htf']:`

🟡 **Line 2090** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for named_tf, interval_value in indicator.timeframe_map.items():`

🟡 **Line 2161** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in ohlcv_data[tf].columns]`

🟡 **Line 2209** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_after_direct = [tf for tf in required_timeframes if tf not in prepared_data]`

🟡 **Line 2214** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for missing_tf in missing_after_direct:`

🟡 **Line 2233** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for avail_tf in available_timeframes:`

🟡 **Line 2320** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in market_data]`

🟡 **Line 2401** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in data.columns]`

🟡 **Line 2460** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ob_missing = [f for f in ob_required if f not in orderbook]`

🟡 **Line 2728** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in tf_data.columns]`

🟡 **Line 2743** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `for col in [c for c in required_columns if c in tf_data.columns]:`

🟡 **Line 2779** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing = [tf for tf, data in standardized.items() if not isinstance(data, pd.DataFrame)]`

🟡 **Line 2784** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for missing_tf in missing:`

🟡 **Line 2790** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `valid_timeframes = [tf for tf, data in standardized.items() if isinstance(data, pd.DataFrame) and not data.empty]`

🟡 **Line 2822** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sources = [tf for tf in derivation_map[missing_tf]['source']`

🟡 **Line 2956** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in base_data.columns]`

🟡 **Line 2977** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [f for f in required_fields if f not in timeframe_data]`

🟡 **Line 3034** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [f for f in required_fields if f not in data]`

🟡 **Line 3091** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i1 in scores:`

🟡 **Line 3238** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `trade_times = [t.get('timestamp', 0) for t in market_data['trades']]`

🟡 **Line 3262** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for key1, value1 in metrics_dict.items():`

🟡 **Line 3310** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for name, indicator in self.indicators.items():`

🟡 **Line 3369** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in df.columns]`

🟡 **Line 3414** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing = [f for f in required_fields if f not in orderbook]`

🟡 **Line 3502** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [f for f in required_fields if f not in trade]`

🟡 **Line 3556** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in df.columns]`

🟡 **Line 3618** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in df.columns]`

🟡 **Line 4371** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for trade in trades_data:`

### src/core/analysis/data_validator.py

🟡 **Line 65** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing = [k for k, v in results.items() if not v and k != 'is_valid']`

### src/core/analysis/indicator_utils.py

🟡 **Line 160** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf, scores in timeframe_scores.items():`

### src/core/analysis/integrated_analysis.py

🟡 **Line 307** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `if any(pd.isna(market_data['ohlcv'].get(field, 0)) for field in ['open', 'high', 'low', 'close', 'volume']):`

### src/core/analysis/interpretation_generator.py

🟡 **Line 1242** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `values = [v for v in component_dict.values() if isinstance(v, (int, float))]`

### src/core/analysis/liquidation_detector.py

🟡 **Line 96** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for exchange_id in target_exchanges:`

🟡 **Line 97** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols:`

🟡 **Line 145** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for exchange_id in target_exchanges:`

🟡 **Line 348** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols:`

🟡 **Line 357** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `high_risk_symbols = [r for r in risk_assessments if r.liquidation_probability > 0.6]`

🟡 **Line 361** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `avg_risk = np.mean([r.liquidation_probability for r in high_risk_symbols])`

🟡 **Line 371** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `affected_symbols=[r.symbol for r in high_risk_symbols],`

🟡 **Line 394** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `monitoring_priorities=[s.symbol for s in high_risk_symbols[:5]]`

🟡 **Line 553** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_volume = sum(bid[1] for bid in orderbook['bids'][:10])`

🟡 **Line 554** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_volume = sum(ask[1] for ask in orderbook['asks'][:10])`

🟡 **Line 724** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `support_levels = [level for level in support_levels if level < current_price][-5:]`

🟡 **Line 725** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `resistance_levels = [level for level in resistance_levels if level > current_price][-5:]`

🟡 **Line 820** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols:`

🟡 **Line 821** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for exchange in exchanges:`

🟡 **Line 830** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols:`

🟡 **Line 861** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `pattern_events = [e for e in events if 'pattern_detection' in e.suspected_triggers]`

🟡 **Line 878** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for event in events:`

🟡 **Line 910** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `severities = [e.severity for e in events]`

### src/core/analysis/models.py

🟡 **Line 43** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_cols = [col for col in required_cols if col not in df.columns]`

🟡 **Line 62** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [f for f in required_trade_fields if f not in sample_trade]`

🟡 **Line 125** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_volume = sum(level[1] for level in self.orderbook['bids'])`

🟡 **Line 126** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_volume = sum(level[1] for level in self.orderbook['asks'])`

### src/core/analysis/portfolio.py

🟡 **Line 83** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for asset, target in self.target_allocation.items():`

### src/core/component_registry.py

🟡 **Line 134** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for dep in graph.get(node, set()):`

### src/core/config.py

🟡 **Line 47** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_path, 'r') as f:`

### src/core/config/config_manager.py

🟡 **Line 82** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_path, 'r') as f:`

🟡 **Line 115** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [ConfigManager._process_env_variables(item) for item in config]`

🟡 **Line 127** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(env_path, 'r') as f:`

🟡 **Line 214** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for section, subsections in required_sections.items():`

🟡 **Line 253** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for exchange_id, exchange_config in exchanges.items():`

### src/core/config/validators/binance_validator.py

🟡 **Line 195** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for field in required_fields:`

🟡 **Line 246** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for field in required_fields:`

🟡 **Line 447** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for error in result.errors:`

### src/core/error/manager.py

🟡 **Line 103** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `errors = [e for e in errors if e.severity == severity]`

🟡 **Line 106** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `errors = [e for e in errors if isinstance(e.error, error_type)]`

### src/core/exchanges/base.py

🟡 **Line 456** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for attempt in range(self.options['ws']['reconnect_attempts']):`

🟡 **Line 544** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for data_type, fields in core_fields.items():`

🟡 **Line 556** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_core = [f for f in fields if f not in item]`

🟡 **Line 564** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_recommended = [f for f in recommended_fields[data_type] if f not in item]`

🟡 **Line 569** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_core = [f for f in fields if f not in data]`

🟡 **Line 577** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_recommended = [f for f in recommended_fields[data_type] if f not in data]`

🟡 **Line 590** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `pong = await self.ws.ping()`

### src/core/exchanges/binance.py

🟡 **Line 464** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbols = [s['symbol'] for s in exchange_info['symbols']`

### src/core/exchanges/bybit.py

🟡 **Line 262** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `endpoint: [] for endpoint in self.RATE_LIMITS['endpoints'].keys()`

🟡 **Line 270** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [f for f in required_fields if f not in self.exchange_config]`

🟡 **Line 934** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `"args": [f"allLiquidation.{symbol}" for symbol in symbols]`

🟡 **Line 1583** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `async with aiohttp.ClientSession() as session:`

🟡 **Line 1766** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for bid in result.get('b', []):`

🟡 **Line 1827** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [f for f in required_fields if not trade_data.get(f)]`

🟡 **Line 2042** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `market_data_bucket[:] = [ts for ts in market_data_bucket if ts > now - market_data_limit['per_second']]`

🟡 **Line 2061** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `category_bucket[:] = [ts for ts in category_bucket if ts > now - category_limit['per_second']]`

🟡 **Line 2077** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `endpoint_bucket[:] = [ts for ts in endpoint_bucket if ts > now - endpoint_limit['per_second']]`

🟡 **Line 2758** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for bybit_interval, tf_name in timeframes.items():`

🟡 **Line 3289** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_keys = [key for key in required_keys if key not in config]`

🟡 **Line 3309** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_ws_keys = [key for key in required_ws_keys if key not in ws_config]`

🟡 **Line 3342** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols:`

🟡 **Line 3850** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for bid in result.get('b', []):`

### src/core/exchanges/ccxt_exchange.py

🟡 **Line 863** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `ticker = await ticker_task`

### src/core/exchanges/coinbase.py

🟡 **Line 118** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `query_string = '&'.join([f"{k}={v}" for k, v in params.items()])`

🟡 **Line 188** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `query_string = '&'.join([f"{k}={v}" for k, v in params.items()])`

🟡 **Line 241** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'bids': [[float(bid[0]), float(bid[1])] for bid in response.get('bids', [])],`

🟡 **Line 242** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'asks': [[float(ask[0]), float(ask[1])] for ask in response.get('asks', [])],`

### src/core/exchanges/exchange_mappings.py

🟡 **Line 239** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for trade in trades:`

🟡 **Line 269** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `standardized['bids'] = [[float(price), float(amount)] for price, amount in standardized['bids']]`

🟡 **Line 271** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `standardized['asks'] = [[float(price), float(amount)] for price, amount in standardized['asks']]`

🟡 **Line 285** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for exchange_field, ccxt_field in mappings.items():`

🟡 **Line 310** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for candle in ohlcv:`

🟡 **Line 363** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for exchange_field, ccxt_field in mappings.items():`

### src/core/exchanges/hyperliquid.py

🟡 **Line 155** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for bid in bid_data[:limit]:`

### src/core/exchanges/liquidation_collector.py

🟡 **Line 111** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols:`

🟡 **Line 141** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols:`

🟡 **Line 176** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols:`

🟡 **Line 400** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `events = [e for e in self.recent_liquidations[symbol_key]`

🟡 **Line 407** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `filtered_events = [e for e in events if e.timestamp >= cutoff_time]`

### src/core/exchanges/manager.py

🟡 **Line 276** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for ex_id, exchange in self.exchanges.items():`

🟡 **Line 695** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `self.logger.debug(f"Exchange methods: {[method for method in dir(exchange) if not method.startswith('_')]}")`

### src/core/exchanges/websocket_manager.py

🟡 **Line 114** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for topics in self.topics.values():`

🟡 **Line 118** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for topic in all_topics:`

🟡 **Line 404** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for task in tasks:`

🟡 **Line 409** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for task in list(self.reconnect_tasks):`

🟡 **Line 417** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for task in pending:`

### src/core/formatting.py

🟡 **Line 333** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for comp in components:`

🟡 **Line 488** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component_name, component_data in results.items():`

🟡 **Line 531** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component_name, component_data in results.items():`

### src/core/formatting/formatter.py

🟡 **Line 825** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component, score in components.items():`

🟡 **Line 986** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for indicator_name, indicator_data in results.items():`

🟡 **Line 1598** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component_data in results.values():`

🟡 **Line 1603** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component_data in results.values():`

🟡 **Line 1780** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component, score in components.items():`

🟡 **Line 1861** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for comp_name, comp_score in top_influential['components'].items():`

🟡 **Line 1868** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component_name, component_data in results.items():`

🟡 **Line 2188** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component, score in components.items():`

### src/core/interpretation/interpretation_manager.py

🟡 **Line 1025** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for interpretation in interpretation_set.interpretations:`

🟡 **Line 1032** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component_type, interpretations in grouped_interpretations.items():`

🟡 **Line 1288** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `divergence_interpretations = [i for i in interpretation_set.interpretations if 'divergence' in i.component_name.lower()]`

🟡 **Line 1510** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `confidences = [i.confidence_score for i in interpretation_set.interpretations]`

🟡 **Line 1709** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, comp1 in enumerate(components):`

🟡 **Line 1776** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `range_components = [i for i in interpretations if 'range' in i.component_name.lower()]`

🟡 **Line 1869** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `confidence_scores = [interp.confidence_score for interp in interpretations]`

### src/core/lifecycle/context.py

🟡 **Line 201** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [dep for dep in self.dependencies if dep not in completed]`

### src/core/market/data_manager.py

🟡 **Line 181** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `tasks = [self.get_market_data(symbol, force_update=True) for symbol in symbols]`

🟡 **Line 425** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [f for f in required_fields if f not in trade]`

### src/core/market/market_data_manager.py

🟡 **Line 835** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_name, df in timeframes.items():`

🟡 **Line 1193** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `total_candles = sum(s['count'] for s in self.candle_processing['symbols'].values())`

🟡 **Line 1199** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for s in self.candle_processing['symbols'].values():`

🟡 **Line 1335** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for bid in orderbook_data['b']:`

🟡 **Line 1492** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `unique_new_trades = [t for t in processed_trades if t.get('id') not in trade_ids]`

🟡 **Line 1665** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf in ['base', 'ltf', 'mtf', 'htf']:`

🟡 **Line 1698** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ohlcv_summary = ', '.join([f"{tf}: {len(df)}" for tf, df in market_data.get('ohlcv', {}).items()])`

🟡 **Line 1798** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbol_batches = [self.symbols[i:i+5] for i in range(0, len(self.symbols), 5)]`

🟡 **Line 1800** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for batch_idx, symbol_batch in enumerate(symbol_batches):`

### src/core/market/market_regime_detector.py

🟡 **Line 143** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `'transition_probabilities': self.model.weights_.tolist(),`

🟡 **Line 199** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_volume = sum(float(level[1]) for level in orderbook.get('bids', [])[:5])`

🟡 **Line 200** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_volume = sum(float(level[1]) for level in orderbook.get('asks', [])[:5])`

🟡 **Line 249** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `self.training_data = features_scaled.tolist()`

### src/core/market/top_symbols.py

🟡 **Line 202** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `self.logger.debug(f"Sample raw symbols: {[m.get('symbol','') for m in raw_markets[:5]]}")`

🟡 **Line 224** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `self.logger.debug(f"Selected {len(sorted_markets)} symbols: {[m.get('symbol', '') for m in sorted_markets]}")`

🟡 **Line 227** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbol_strings = [m.get('symbol', '') for m in sorted_markets if m.get('symbol')]`

🟡 **Line 256** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `included_symbols = [s.upper() for s in self.market_config.get('static_symbols', [])]`

🟡 **Line 498** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for entry in market_data:`

### src/core/models/interpretation_schema.py

🟡 **Line 128** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [interp for interp in self.interpretations if interp.severity == InterpretationSeverity.CRITICAL]`

🟡 **Line 132** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [interp for interp in self.interpretations if interp.severity == InterpretationSeverity.WARNING]`

🟡 **Line 136** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [interp for interp in self.interpretations if interp.confidence_score >= threshold]`

### src/core/monitoring/binance_monitor.py

🟡 **Line 398** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]`

### src/core/reporting/examples/generate_test_report.py

🟡 **Line 220** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `webbrowser.open(f"file://{os.path.abspath(pdf_path)}")`

### src/core/reporting/export_manager.py

🟡 **Line 146** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(filepath, 'w') as f:`

🟡 **Line 180** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for fmt, directory in dirs_to_scan:`

🟡 **Line 272** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(filepath, 'r') as f:`

### src/core/reporting/interactive_web_report.py

🟡 **Line 217** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for category in ["gainers", "losers"]:`

🟡 **Line 219** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for item in performers[category]:`

🟡 **Line 271** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for report_id, metadata in self.active_reports.items():`

### src/core/reporting/pdf_generator.py

🟡 **Line 274** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_file, "r") as f:`

🟡 **Line 598** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in ohlcv_data.columns]`

🟡 **Line 644** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(pdf_path, 'rb') as f:`

🟡 **Line 982** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `labels = [str(comp[0]) for comp in sorted_components]`

🟡 **Line 983** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `scores = [float(comp[1].get("score", 0)) for comp in sorted_components]`

🟡 **Line 1690** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(json_path, "w") as f:`

🟡 **Line 1694** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(reports_json_path, "w") as f:`

🟡 **Line 1733** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for k, v in obj.items():`

🟡 **Line 1758** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `return obj.tolist()`

🟡 **Line 2241** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `insights = [item.get('interpretation', '') for item in insights]`

🟡 **Line 2463** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(html_path, "w") as f:`

🟡 **Line 3296** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for category, items in performers.items():`

🟡 **Line 3639** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(debug_html_path, "w") as f:`

🟡 **Line 3683** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(html_path, "w") as f:`

🟡 **Line 3696** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(default_path, "w") as f:`

🟡 **Line 4227** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(template_path, 'r', encoding='utf-8') as f:`

🟡 **Line 4972** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(html_path, 'r', encoding='utf-8') as f:`

🟡 **Line 4983** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with os.fdopen(temp_fd, 'w', encoding='utf-8') as temp_file:`

🟡 **Line 5197** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, contracts in quarterly_futures.items():`

🟡 **Line 5361** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `targets = [target for target in targets if target["price"] > 0]`

🟡 **Line 5592** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ohlcv_data["volume"] = [random.uniform(100, 1000) for _ in range(periods)]`

### src/core/reporting/report_manager.py

🟡 **Line 71** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_file, 'r') as f:`

🟡 **Line 289** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, file_path in enumerate(files):`

🟡 **Line 431** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for file in os.listdir(self.pdf_dir):`

### src/core/reporting/test_report_manager.py

🟡 **Line 77** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'open': [base_price * (1 + random.uniform(-volatility/2, volatility/2)) for _ in range(periods)],`

🟡 **Line 78** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'close': [base_price * (1 + random.uniform(-volatility/2, volatility/2)) for _ in range(periods)]`

🟡 **Line 91** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `df['volume'] = [random.uniform(1000, 5000) for _ in range(periods)]`

🟡 **Line 251** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(json_path, 'r') as f:`

### src/core/resource_manager.py

🟡 **Line 55** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `await self._update_resource_stats()`

### src/core/services/service_container.py

🟡 **Line 108** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for dep in service_info.dependencies:`

### src/core/state_manager.py

🟡 **Line 138** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `history = [t for t in history if t.timestamp >= since]`

### src/core/validation/service.py

🟡 **Line 252** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [await self._validate_item(item) for item in data]`

🟡 **Line 262** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `*[rule.check(item) for rule in self._rules.get(item['symbol'], [])]`

### src/core/validation/validators.py

🟡 **Line 165** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for side in ['bids', 'asks']:`

### src/dashboard/dashboard_integration.py

🟡 **Line 264** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'strong_signals': len([s for s in self._dashboard_data.get('signals', []) if s.get('strength') == 'strong']),`

🟡 **Line 439** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'strong': len([s for s in signals_data if s.get('strength') == 'strong']),`

🟡 **Line 440** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'medium': len([s for s in signals_data if s.get('strength') == 'medium']),`

🟡 **Line 441** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'weak': len([s for s in signals_data if s.get('strength') == 'weak'])`

🟡 **Line 445** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'critical': len([a for a in self._dashboard_data.get('alerts', []) if a.get('severity') == 'CRITICAL']),`

🟡 **Line 446** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'warning': len([a for a in self._dashboard_data.get('alerts', []) if a.get('severity') == 'WARNING'])`

🟡 **Line 450** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'high_confidence': len([o for o in self._dashboard_data.get('alpha_opportunities', []) if o.get('confidence', 0) >= 85]),`

🟡 **Line 451** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'medium_confidence': len([o for o in self._dashboard_data.get('alpha_opportunities', []) if 70 <= o.get('confidence', 0) < 85])`

### src/dashboard/dashboard_manager.py

🟡 **Line 141** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for ws in self._websocket_connections:`

🟡 **Line 214** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `signal_files = [f for f in signals_dir.glob("*.json") if f.is_file()]`

### src/data_acquisition/binance/binance_exchange.py

🟡 **Line 670** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'spot_markets': len([m for m in markets.values() if m.get('spot', False)]),`

🟡 **Line 671** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'futures_markets': len([m for m in markets.values() if m.get('future', False)]),`

### src/data_acquisition/binance/data_fetcher.py

🟡 **Line 352** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `def _is_circuit_breaker_open(self) -> bool:`

### src/data_acquisition/binance/futures_client.py

🟡 **Line 396** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `standardized['maxLeverage'] = max(b['initialLeverage'] for b in standardized['brackets'])`

🟡 **Line 397** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `standardized['minNotional'] = min(b['notionalFloor'] for b in standardized['brackets'])`

🟡 **Line 398** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `standardized['maxNotional'] = max(b['notionalCap'] for b in standardized['brackets'] if b['notionalCap'] > 0)`

### src/data_acquisition/bybit_data_fetcher.py

🟡 **Line 60** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for result in results:`

### src/data_acquisition/websocket_handler.py

🟡 **Line 206** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols:`

### src/data_processing/data_manager.py

🟡 **Line 173** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for key in ['trades', 'momentum.trades', 'volume.trades', 'position.trades', 'sentiment.trades']:`

🟡 **Line 235** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols:`

### src/data_processing/data_processor.py

🟡 **Line 67** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for timeframe, tf_data in ohlcv_data.items():`

🟡 **Line 148** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `raise ValueError(f"Missing required columns: {[col for col in required_cols if col not in df.columns]}")`

🟡 **Line 565** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'bids': [[float(p), float(s)] for p, s in data.get('b', [])],`

🟡 **Line 566** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'asks': [[float(p), float(s)] for p, s in data.get('a', [])],`

🟡 **Line 1148** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for timeframe, data in ohlcv_data.items():`

🟡 **Line 1180** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'bids': [[float(p), float(s)] for p, s in orderbook_data.get('bids', [])],`

🟡 **Line 1181** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'asks': [[float(p), float(s)] for p, s in orderbook_data.get('asks', [])],`

### src/data_processing/data_store.py

🟡 **Line 59** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'bids': [[float(p), float(s)] for p, s in data.get('bids', [])],`

🟡 **Line 60** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'asks': [[float(p), float(s)] for p, s in data.get('asks', [])],`

🟡 **Line 197** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in list(self._ticker_data.keys()):`

### src/data_processing/storage_manager.py

🟡 **Line 296** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for format in StorageFormat:`

🟡 **Line 436** (memory_concern)
- Issue: Reading entire CSV - consider chunking for large files
- Code: `return pd.read_csv(file_path)`

🟡 **Line 560** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [self._convert_numpy_types(item) for item in obj]`

🟡 **Line 566** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `return obj.tolist()`

### src/data_storage/database.py

🟡 **Line 125** (blocking_io)
- Issue: Blocking sleep - use asyncio.sleep in async code
- Code: `time.sleep(self.config.retry_delay)`

🟡 **Line 210** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for key, value in analysis.items():`

🟡 **Line 220** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for sub_key, sub_value in value.items():`

🟡 **Line 226** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, signal in enumerate(signals):`

🟡 **Line 273** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `component_list = [f'r["_field"] == "{c}_score"' for c in components]`

🟡 **Line 308** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for index, row in df.iterrows():`

🟡 **Line 327** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for col in numeric_columns:`

🟡 **Line 494** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for index, row in df.iterrows():`

### src/demo_trading_runner.py

🟡 **Line 82** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(self.config_path, 'w') as f:`

🟡 **Line 89** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(self.config_path, 'r') as f:`

🟡 **Line 261** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in ws_symbols:`

🟡 **Line 494** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbols = [s.strip() for s in args.symbols.split(',')]`

### src/examples/analysis_example.py

🟡 **Line 57** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for exchange_id, exchange_data in market_data.items():`

### src/fixes/fix_market_monitor.py

🟡 **Line 11** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(file_path, 'r') as f:`

🟡 **Line 70** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(file_path, 'w') as f:`

### src/fixes/fix_monitor.py

🟡 **Line 11** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open('src/monitoring/monitor.py', 'r') as f:`

🟡 **Line 35** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open('src/monitoring/monitor.py', 'w') as f:`

### src/fixes/fix_ohlcv.py

🟡 **Line 24** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(file_path, 'r') as f:`

🟡 **Line 46** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(file_path, 'w') as f:`

### src/fixes/fix_pdf_alerts_comprehensive.py

🟡 **Line 186** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for pdf_dir in pdf_directories:`

🟡 **Line 282** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for pdf_dir in pdf_dirs:`

🟡 **Line 301** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open('monitor_pdf_attachments.py', 'w') as f:`

### src/indicators/backups/debug_mixin_backup.py

🟡 **Line 100** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in available_fields]`

🟡 **Line 228** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bullish_components = [c for c, s, _, _ in contributions if s > 60]`

🟡 **Line 229** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bearish_components = [c for c, s, _, _ in contributions if s < 40]`

🟡 **Line 286** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `extremity_factor = np.mean([abs(score - 50) for score in scores]) * 2`

### src/indicators/backups/sentiment_indicators_backup.py

🟡 **Line 85** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for config_key, internal_key in config_to_internal.items():`

🟡 **Line 214** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for r in rates_list:`

🟡 **Line 221** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for item in history_list:`

🟡 **Line 709** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `", ".join([f"{k}: {v:.2f}" for k, v in scores.items()]) +`

🟡 **Line 835** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `weighted_scores = [(score, weight / total_weight) for score, weight in weighted_scores]`

### src/indicators/base_indicator.py

🟡 **Line 235** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `self.logger.debug(f"Class inheritance chain: {[cls.__name__ for cls in mro]}")`

🟡 **Line 526** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]`

🟡 **Line 556** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `invalid = [k for k, v in scores.items() if not 0 <= v <= 100]`

🟡 **Line 597** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf in ['ltf', 'mtf', 'htf']:`

🟡 **Line 701** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]`

🟡 **Line 727** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bids = np.array([[float(price), float(size)] for price, size in orderbook.get('bids', [])])`

🟡 **Line 728** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `asks = np.array([[float(price), float(size)] for price, size in orderbook.get('asks', [])])`

🟡 **Line 744** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing = [comp for comp in required_components if comp not in available_components]`

🟡 **Line 837** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_sentiments = [comp for comp in required_sentiments if comp not in sentiment]`

🟡 **Line 859** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [f for f in self.required_data if f not in data]`

🟡 **Line 1438** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in available_fields]`

🟡 **Line 1609** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `'regime_probabilities': regime_probs[-1].tolist(),`

🟡 **Line 1820** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [f'REGIME_{i}' for i in range(n_regimes)]`

🟡 **Line 1827** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(len(regime_labels) - 1):`

🟡 **Line 1840** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `return transition_matrix.tolist()`

🟡 **Line 1846** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `return identity.tolist()`

### src/indicators/orderbook_indicators.py

🟡 **Line 516** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(min(5, levels)):`

🟡 **Line 773** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `final_bid_slope = np.sum([s * w for s, w in zip(bid_slopes, segment_weights)])`

🟡 **Line 774** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `final_ask_slope = np.sum([s * w for s, w in zip(ask_slopes, segment_weights)])`

🟡 **Line 1005** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `velocities = [x['velocity'] for x in self.order_flow_history]`

🟡 **Line 1125** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `largest_bid_usd = max([float(b[0]) * float(b[1]) for b in aggressive_bids], default=0)`

🟡 **Line 1126** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `largest_ask_usd = max([float(a[0]) * float(a[1]) for a in aggressive_asks], default=0)`

🟡 **Line 1406** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_depth = sum(float(bid[1]) for bid in bids if float(bid[0]) >= mid_price - depth_range)`

🟡 **Line 1407** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_depth = sum(float(ask[1]) for ask in asks if float(ask[0]) <= mid_price + depth_range)`

🟡 **Line 1454** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_volume = sum(float(bid[1]) for bid in bids[:self.depth_levels])`

🟡 **Line 1455** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_volume = sum(float(ask[1]) for ask in asks[:self.depth_levels])`

🟡 **Line 1509** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `close_bid_volume = sum(float(bid[1]) for bid in bids if float(bid[0]) >= mid_price - depth_range)`

🟡 **Line 1510** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `close_ask_volume = sum(float(ask[1]) for ask in asks if float(ask[0]) <= mid_price + depth_range)`

🟡 **Line 1683** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_depth = sum(float(bid[1]) for bid in bids if float(bid[0]) >= range_min)`

🟡 **Line 1684** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_depth = sum(float(ask[1]) for ask in asks if float(ask[0]) <= range_max)`

🟡 **Line 1738** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_depth = sum(float(bid[1]) for bid in bids if float(bid[0]) >= mid_price - depth_range)`

🟡 **Line 1739** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_depth = sum(float(ask[1]) for ask in asks if float(ask[0]) <= mid_price + depth_range)`

🟡 **Line 1986** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in data]`

🟡 **Line 2277** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_volumes = [float(bid[1]) for bid in bids[:self.depth_levels]]`

🟡 **Line 2278** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_volumes = [float(ask[1]) for ask in asks[:self.depth_levels]]`

🟡 **Line 2285** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `weights = [1.0 - (i / self.depth_levels) for i in range(self.depth_levels)]`

🟡 **Line 2412** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bullish_components = [c for c, s, _, _ in contributions if s > 60]`

🟡 **Line 2413** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bearish_components = [c for c, s, _, _ in contributions if s < 40]`

🟡 **Line 2580** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_volume = sum(float(bid[1]) for bid in bids[:10])`

🟡 **Line 2581** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_volume = sum(float(ask[1]) for ask in asks[:10])`

🟡 **Line 2708** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_depth = sum(float(bid[1]) for bid in bids if float(bid[0]) >= mid_price - depth_range)`

🟡 **Line 2709** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_depth = sum(float(ask[1]) for ask in asks if float(ask[0]) <= mid_price + depth_range)`

🟡 **Line 2847** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_volume = sum(float(bid[1]) for bid in bids[:levels])`

🟡 **Line 2848** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_volume = sum(float(ask[1]) for ask in asks[:levels])`

### src/indicators/orderflow_indicators.py

🟡 **Line 677** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [f for f in required_fields if f not in orderbook]`

🟡 **Line 723** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_keys = [key for key in required_keys if key not in data]`

🟡 **Line 808** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component in self.component_weights:`

🟡 **Line 938** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_cols = [col for col in required_cols if col not in df.columns]`

🟡 **Line 1875** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for std_col, possible_cols in column_mappings.items():`

🟡 **Line 1885** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_cols = [col for col in required_cols if col not in trades_df.columns]`

🟡 **Line 2121** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for col in time_column_variants:`

🟡 **Line 2301** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in ohlcv_df.columns]`

🟡 **Line 2348** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `self.logger.debug(f"Converted time column to numeric. Sample values: {trades_df['time'].head(3).tolist()}")`

🟡 **Line 2525** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `amounts = candle_trades['amount'].tolist()`

🟡 **Line 2569** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `non_zero_indices = [i for i, cvd in enumerate(candle_cvds) if cvd != 0]`

🟡 **Line 2580** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for j in range(0, first_non_zero_idx):`

🟡 **Line 2585** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for idx_pos in range(len(non_zero_indices) - 1):`

🟡 **Line 2617** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for j in range(last_non_zero_idx + 1, len(candle_cvds)):`

🟡 **Line 2637** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `zero_indices = [i for i, val in enumerate(candle_cvds) if val == 0]`

🟡 **Line 2834** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in ohlcv_df.columns]`

🟡 **Line 2999** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `oi_changes = [aligned_oi_values[i] - aligned_oi_values[i-1] for i in range(1, len(aligned_oi_values))]`

🟡 **Line 3219** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for std_col, possible_cols in column_mappings.items():`

🟡 **Line 3421** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `swing_lows = [(idx, level) for idx, level, swing_type in swing_data if swing_type == -1]`

🟡 **Line 3424** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for cluster in low_clusters:`

🟡 **Line 3430** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `swing_highs = [(idx, level) for idx, level, swing_type in swing_data if swing_type == 1]`

🟡 **Line 3451** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(swing_length, len(df) - swing_length):`

🟡 **Line 3490** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `cluster_avg = np.mean([s[1] for s in current_cluster])`

🟡 **Line 3508** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `levels = [point[1] for point in cluster]`

🟡 **Line 3509** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `indices = [point[0] for point in cluster]`

🟡 **Line 3533** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for zone in liquidity_zones['bullish']:`

🟡 **Line 3538** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(start_idx, len(df)):`

🟡 **Line 3542** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for j in range(i + 1, min(i + 10, len(df))):`

🟡 **Line 3551** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for zone in liquidity_zones['bearish']:`

🟡 **Line 3556** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(start_idx, len(df)):`

🟡 **Line 3685** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf, tf_divergence in timeframe_divergences.items():`

🟡 **Line 3694** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component in ['cvd', 'trade_flow_score', 'imbalance_score']:`

🟡 **Line 3703** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component in ['cvd', 'trade_flow_score', 'imbalance_score']:`

🟡 **Line 3740** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `available_timeframes = [tf for tf in timeframes if tf in ohlcv_data]`

🟡 **Line 4139** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `weights = [w / weight_sum for w in weights]`

🟡 **Line 4740** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bullish_components = [c for c, s, _, _ in contributions if s > 60]`

🟡 **Line 4741** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bearish_components = [c for c, s, _, _ in contributions if s < 40]`

🟡 **Line 4832** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `extremity_factor = np.mean([abs(score - 50) for score in scores]) * 2`

### src/indicators/price_structure_indicators.py

🟡 **Line 345** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `available_tfs = [tf for tf in self.timeframe_weights if tf != missing_tf]`

🟡 **Line 550** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_cols = [col for col in required_cols if col not in df.columns]`

🟡 **Line 653** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(window, len(data) - window):`

🟡 **Line 670** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `all_levels = [level for _, level in swing_highs] + [level for _, level in swing_lows]`

🟡 **Line 746** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ema_periods = [min(period, max_period) for period in [10, 20, 50, 100, 200] if period <= max_period]`

🟡 **Line 780** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `shorter_emas = [ma_data[f'ema{p}'] for p in [10, 20] if f'ema{p}' in ma_data]`

🟡 **Line 781** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `longer_emas = [ma_data[f'ema{p}'] for p in [50, 100, 200] if f'ema{p}' in ma_data]`

🟡 **Line 785** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `avg_short = np.mean([ema.iloc[-1] for ema in shorter_emas])`

🟡 **Line 786** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `avg_long = np.mean([ema.iloc[-1] for ema in longer_emas])`

🟡 **Line 1422** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for block in order_block['bullish']:`

🟡 **Line 1616** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `hvn_scores = [score for node_type, score in node_scores if node_type == 'hvn']`

🟡 **Line 1617** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `lvn_scores = [score for node_type, score in node_scores if node_type == 'lvn']`

🟡 **Line 1724** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing = [col for col in required_cols if col not in df.columns]`

🟡 **Line 1866** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing = [col for col in required_cols if col not in df.columns]`

🟡 **Line 1885** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `periods = [min(period, len(df_copy) - 5) for period in [20, 50] if period < len(df_copy) - 5]`

🟡 **Line 2068** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for t in range(time_blocks):`

🟡 **Line 2174** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `group_avg = np.mean([l['price'] for l in current_group])`

🟡 **Line 2261** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `prices = [p['price'] for p in points if 'price' in p]`

🟡 **Line 2772** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `swing_highs = [(idx, highs[idx]) for idx in high_idx if idx < len(highs)]`

🟡 **Line 2773** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `swing_lows = [(idx, lows[idx]) for idx in low_idx if idx < len(lows)]`

🟡 **Line 2842** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ema_values = [df_copy[f'ema{period}'].iloc[-1] for period in periods]`

🟡 **Line 2947** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component, score in timeframe_scores[tf].items():`

🟡 **Line 2988** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for block in order_block['bullish']:`

🟡 **Line 3769** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `swing_highs = [(idx, highs[idx]) for idx in high_indices]`

🟡 **Line 3770** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `swing_lows = [(idx, lows[idx]) for idx in low_indices]`

🟡 **Line 3778** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `recent_swing_highs = [price for _, price in swing_highs[-3:]]  # Last 3 swing highs`

🟡 **Line 3779** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `recent_swing_lows = [price for _, price in swing_lows[-3:]]   # Last 3 swing lows`

🟡 **Line 4895** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `distances = [abs(current_price - level) / current_price for level in all_levels]`

🟡 **Line 4904** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, level1 in enumerate(all_levels):`

🟡 **Line 5234** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `demand_blocks = [b for b in blocks if b['type'] == 'demand']`

🟡 **Line 5235** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `supply_blocks = [b for b in blocks if b['type'] == 'supply']`

🟡 **Line 5273** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `price_levels = np.array([[b['high'], b['low']] for b in blocks])`

🟡 **Line 5285** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `cluster_blocks = [blocks[i] for i in range(len(blocks)) if cluster_labels[i] == cluster_id]`

🟡 **Line 5553** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `quality_blocks = [b for b in order_blocks if b['enhanced_strength'] >= 0.3]`

### src/indicators/sentiment_indicators.py

🟡 **Line 87** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for config_key, internal_key in config_to_internal.items():`

🟡 **Line 242** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `rates = [float(rate.get('rate', 0)) for rate in funding_history]`

🟡 **Line 244** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `rates = [float(rate.get('fundingRate', 0)) for rate in funding_history]`

🟡 **Line 250** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `rates = [float(rate.get(rate_key, 0)) for rate in funding_history]`

🟡 **Line 256** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `rates = [float(rate) for rate in funding_history]`

🟡 **Line 262** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `rates = [r for r in rates if not np.isnan(r) and not np.isinf(r)]`

🟡 **Line 1883** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `buy_signals = [s for s in signals if s['signal'] == 'BUY']`

🟡 **Line 1884** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sell_signals = [s for s in signals if s['signal'] == 'SELL']`

🟡 **Line 1898** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `reasons = [s.get('reason', '') for s in buy_signals]`

🟡 **Line 1907** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'components': [s.get('component', 'multiple') for s in buy_signals]`

🟡 **Line 1924** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `reasons = [s.get('reason', '') for s in sell_signals]`

🟡 **Line 1933** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'components': [s.get('component', 'multiple') for s in sell_signals]`

### src/indicators/technical_indicators.py

🟡 **Line 254** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `valid_scores = [val for val in adjusted_component_scores.values() if not pd.isna(val)]`

🟡 **Line 259** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component in adjusted_component_scores:`

🟡 **Line 630** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_name, tf_scores in data.items():`

🟡 **Line 1878** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in df.columns]`

🟡 **Line 2298** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bullish_components = [c for c, s, _, _ in contributions if s > 60]`

🟡 **Line 2299** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bearish_components = [c for c, s, _, _ in contributions if s < 40]`

🟡 **Line 2350** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `extremity_factor = np.mean([abs(score - 50) for score in scores]) * 2`

### src/indicators/volume_indicators.py

🟡 **Line 250** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_tfs = [tf for tf in required_timeframes if tf not in ohlcv_data]`

🟡 **Line 252** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `friendly_names = [self.TIMEFRAME_CONFIG[tf]['friendly_name'] for tf in missing_tfs]`

🟡 **Line 281** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in df.columns]`

🟡 **Line 869** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `volume_cols = [col for col in df.columns if any(term in col.lower() for term in ['volume', 'size', 'amount', 'quantity', 'vol'])]`

🟡 **Line 1403** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `self.logger.debug(f"Trades DataFrame columns: {trades_df.columns.tolist()}")`

🟡 **Line 1477** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `self.logger.debug(f"ADL input DataFrame columns: {df.columns.tolist()}")`

🟡 **Line 1578** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `volume_cols = [col for col in df.columns if any(term in col.lower() for term in ['volume', 'size', 'amount', 'quantity', 'vol'])]`

🟡 **Line 1842** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `self.logger.info(f"Trades DataFrame columns: {trades_df.columns.tolist()}")`

🟡 **Line 1902** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `self.logger.debug(f"Trades DataFrame columns: {trades_df.columns.tolist()}")`

🟡 **Line 1904** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `self.logger.debug(f"Side column sample values: {trades_df['side'].head().tolist()}")`

🟡 **Line 2051** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `volume_cols = [col for col in df.columns if any(term in col.lower() for term in ['volume', 'size', 'amount', 'quantity', 'vol'])]`

🟡 **Line 3392** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component, score in component_scores.items():`

🟡 **Line 3527** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `accumulation_components = [c for c, s, _, _ in contributions if s > 60]`

🟡 **Line 3528** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `distribution_components = [c for c, s, _, _ in contributions if s < 40]`

🟡 **Line 3572** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `extremity_factor = np.mean([abs(score - 50) for score in scores]) * 2`

### src/main.py

🟡 **Line 158** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]`

🟡 **Line 272** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `tasks = [task for task in asyncio.all_tasks() if not task.done()]`

🟡 **Line 286** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `asyncio.gather(*[t for t in tasks if t != current_task], return_exceptions=True),`

🟡 **Line 442** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbol_names = [s['symbol'].replace('/', '') for s in top_symbols]`

🟡 **Line 988** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for exchange_id, data in market_data.items():`

🟡 **Line 1098** (sequential_api_calls)
- Issue: Multiple sequential API calls (5) - consider concurrent execution
- Code: `await websocket.send_json({`

🟡 **Line 1196** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_name, interval in timeframes.items():`

### src/models/market_data.py

🟡 **Line 56** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for bid in self.bids:`

🟡 **Line 235** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bids=[[float(p), float(a)] for p, a in data['bids']],`

🟡 **Line 236** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `asks=[[float(p), float(a)] for p, a in data['asks']],`

### src/models/signal_schema.py

🟡 **Line 207** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(file_path, 'r') as f:`

### src/monitoring/alert_manager.py

🟡 **Line 1151** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `alerts = [a for a in alerts if a['level'] == level]`

🟡 **Line 1155** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `alerts = [a for a in alerts if float(a['timestamp']) >= start_time]`

🟡 **Line 1428** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(logging_config_path, 'r') as f:`

🟡 **Line 1435** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_path, 'r') as f:`

🟡 **Line 1558** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [prepare_for_json(item) for item in obj]`

🟡 **Line 1570** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(filepath, 'w') as f:`

🟡 **Line 1943** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `[(k, v.get('score', 0)) for k, v in results.items() if isinstance(v, dict)],`

🟡 **Line 1991** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `real_subcomps = [s for s in top_weighted_subcomponents if not s.get('name', '').startswith('overall_')]`

🟡 **Line 3076** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(file_path, 'rb') as f:`

🟡 **Line 3269** (sequential_api_calls)
- Issue: Multiple sequential API calls (6) - consider concurrent execution
- Code: `await self.send_confluence_alert(`

🟡 **Line 3549** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `await self.send_confluence_alert(`

🟡 **Line 4951** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, (price, size, usd_value) in enumerate(top_bids[:3], 1):`

🟡 **Line 4956** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, (price, size, usd_value) in enumerate(top_asks[:3], 1):`

🟡 **Line 4963** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for price, size, usd_value in top_bids[:2]:`

### src/monitoring/alpha_integration.py

🟡 **Line 759** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `recent_alerts = [t for t in self.hourly_alert_counts if t >= current_hour]`

🟡 **Line 784** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `self.hourly_alert_counts = [t for t in self.hourly_alert_counts if t >= cutoff_time]`

### src/monitoring/alpha_integration_manager.py

🟡 **Line 377** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [self._opportunity_to_dict(opp) for opp in opportunities]`

🟡 **Line 381** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [self._alert_to_dict(alert) for alert in alerts]`

🟡 **Line 430** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `legacy_metrics = [m for m in recent_metrics if m.scanner_type == 'legacy']`

🟡 **Line 431** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `optimized_metrics = [m for m in recent_metrics if m.scanner_type == 'optimized']`

### src/monitoring/alpha_performance_monitor.py

🟡 **Line 97** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `await self._collect_metrics()`

🟡 **Line 306** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `recent_quality = [m for m in self.alert_quality_history if m.timestamp > recent_cutoff]`

🟡 **Line 307** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `recent_health = [m for m in self.system_health_history if m.timestamp > recent_cutoff]`

🟡 **Line 342** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `legacy_metrics = [m for m in metrics if m.scanner_type == 'legacy']`

🟡 **Line 343** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `optimized_metrics = [m for m in metrics if m.scanner_type == 'optimized']`

🟡 **Line 381** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `recent_metrics = [m for m in self.alert_quality_history if m.timestamp > recent_cutoff]`

🟡 **Line 383** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `legacy_metrics = [m for m in recent_metrics if m.scanner_type == 'legacy']`

🟡 **Line 384** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `optimized_metrics = [m for m in recent_metrics if m.scanner_type == 'optimized']`

🟡 **Line 468** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `recent_alerts = [m for m in self.alert_quality_history if m.timestamp > recent_cutoff]`

🟡 **Line 500** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'alert_quality_history': [asdict(m) for m in self.alert_quality_history],`

🟡 **Line 501** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'system_health_history': [asdict(m) for m in self.system_health_history],`

### src/monitoring/alpha_scanner.py

🟡 **Line 222** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbols = [s['symbol'] if isinstance(s, dict) else str(s) for s in symbols_data]`

🟡 **Line 248** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols:`

### src/monitoring/components/health_monitor.py

🟡 **Line 630** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `active_alerts=[self.alerts[alert_id].to_dict() for alert_id in self.active_alert_ids]`

🟡 **Line 652** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for a in self.alerts.values())):`

🟡 **Line 719** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for map_source, alert_types in source_type_map.items():`

🟡 **Line 743** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for alert_category, alert_types_list in source_type_map.items():`

🟡 **Line 912** (blocking_io)
- Issue: Synchronous HTTP request - consider aiohttp
- Code: `response = requests.post(`

🟡 **Line 929** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `alert_dicts = [alert.to_dict() for alert in self.alerts.values()]`

🟡 **Line 932** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(self.config['alert_log_path'], 'w') as f:`

🟡 **Line 940** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [self.alerts[alert_id] for alert_id in self.active_alert_ids]`

🟡 **Line 967** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for metric_name, metric in self.metrics.items():`

🟡 **Line 973** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for ts in all_timestamps:`

🟡 **Line 1066** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `time_diffs = [recent_times[i] - recent_times[i-1] for i in range(1, len(recent_times))]`

🟡 **Line 1071** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `value_diffs = [recent_values[i] - recent_values[i-1] for i in range(1, len(recent_values))]`

### src/monitoring/enhanced_market_report.py

🟡 **Line 190** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols:`

🟡 **Line 202** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `oi_history = await primary_exchange.fetch_open_interest_history(symbol, '5min', 10)`

### src/monitoring/error_tracker.py

🟡 **Line 165** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for pattern_name, pattern_info in self.known_patterns.items():`

🟡 **Line 203** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `recent_events = [e for e in self.error_events if e.timestamp >= cutoff]`

🟡 **Line 227** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `critical_issues = [e for e in recent_events if e.severity == ErrorSeverity.CRITICAL]`

🟡 **Line 228** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `high_severity_issues = [e for e in recent_events if e.severity == ErrorSeverity.HIGH]`

🟡 **Line 243** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `"critical_issues": [self._serialize_event(e) for e in critical_issues[:5]],`

🟡 **Line 244** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `"high_severity_issues": [self._serialize_event(e) for e in high_severity_issues[:5]],`

🟡 **Line 296** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(filepath, 'w') as f:`

### src/monitoring/fix_market_reporter.py

🟡 **Line 7** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(file_path, 'r') as file:`

🟡 **Line 25** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(file_path, 'w') as file:`

### src/monitoring/fix_market_reporter_validation.py

🟡 **Line 27** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(original_file, 'r') as f:`

🟡 **Line 179** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(original_file, 'w') as f:`

### src/monitoring/health_monitor.py

🟡 **Line 552** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `active_alerts=[self.alerts[alert_id].to_dict() for alert_id in self.active_alert_ids]`

🟡 **Line 574** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for a in self.alerts.values())):`

🟡 **Line 655** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `alert_dicts = [alert.to_dict() for alert in self.alerts.values()]`

🟡 **Line 658** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(self.config['alert_log_path'], 'w') as f:`

🟡 **Line 666** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [self.alerts[alert_id] for alert_id in self.active_alert_ids]`

🟡 **Line 693** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for metric_name, metric in self.metrics.items():`

🟡 **Line 699** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for ts in all_timestamps:`

### src/monitoring/manipulation_detector.py

🟡 **Line 512** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, symbol_history in self._manipulation_history.items():`

🟡 **Line 575** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, symbol_history in self._manipulation_history.items():`

🟡 **Line 605** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `top_symbols = [{"symbol": symbol, "count": count} for symbol, count in top_symbols]`

🟡 **Line 677** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `prices = [dp['price'] for dp in recent_data if dp['price'] > 0]`

🟡 **Line 678** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `volumes = [dp['volume'] for dp in recent_data if dp['volume'] > 0]`

🟡 **Line 679** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `oi_values = [dp['open_interest'] for dp in recent_data if dp['open_interest'] > 0]`

🟡 **Line 690** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `price_changes = [abs(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]`

🟡 **Line 694** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `volume_spikes = [v for v in volumes if v > volume_avg * 2] if volume_avg > 0 else []`

🟡 **Line 709** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `oi_changes = [abs(oi_values[i] - oi_values[i-1]) / oi_values[i-1] for i in range(1, len(oi_values)) if oi_values[i-1] > 0]`

🟡 **Line 742** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `"avg_oi_volatility": round(np.mean([abs(oi_values[i] - oi_values[i-1]) / oi_values[i-1] for i in range(1, len(oi_values)) if oi_values[i-1] > 0]) * 100, 2) if len(oi_values) > 1 else 0.0`

### src/monitoring/market_reporter.py

🟡 **Line 191** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_file, 'r') as f:`

🟡 **Line 679** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_keys = [key for key in expected_keys if key not in data]`

🟡 **Line 716** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `return value.tolist()`

🟡 **Line 722** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [self._numpy_to_native(x) for x in value]`

🟡 **Line 837** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for name in field_names:`

🟡 **Line 1172** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [self._sanitize_for_logging(item) for item in data]`

🟡 **Line 1901** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `embed_titles = [e.get('title') for e in formatted_report.get('embeds', [])]`

🟡 **Line 2603** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for key, fallback in fallbacks.items():`

🟡 **Line 2776** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `templates = [f for f in os.listdir(template_dir) if f.endswith('.html')]`

🟡 **Line 2785** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(template_path, 'r') as f:`

🟡 **Line 2786** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `first_lines = [next(f) for _ in range(10)]`

🟡 **Line 2804** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_keys = [k for k in required_template_keys if k not in data]`

🟡 **Line 3025** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `tasks = [self._calculate_single_premium(symbol, all_markets) for symbol in symbols]`

🟡 **Line 3513** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_volume = sum(float(bid[1]) for bid in order_book['bids'][:20])  # Top 20 levels`

🟡 **Line 3514** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_volume = sum(float(ask[1]) for ask in order_book['asks'][:20])`

🟡 **Line 3524** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `large_bid_orders = [bid for bid in order_book['bids'][:50] if float(bid[1]) * float(bid[0]) > 10000]  # $10k+ orders`

🟡 **Line 3525** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `large_ask_orders = [ask for ask in order_book['asks'][:50] if float(ask[1]) * float(ask[0]) > 10000]`

🟡 **Line 3628** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for order in orders:`

🟡 **Line 3873** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_depth = sum(float(ask[1]) for ask in order_book['asks'][:10])`

🟡 **Line 3878** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_depth = sum(float(bid[1]) for bid in order_book['bids'][:10])`

🟡 **Line 4056** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_volumes = [float(bid[1]) * float(bid[0]) for bid in top_bids]`

🟡 **Line 4057** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_volumes = [float(ask[1]) * float(ask[0]) for ask in top_asks]`

🟡 **Line 4200** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `result['alpha_opportunities'] = [opp.to_dict() for opp in alpha_opportunities]`

🟡 **Line 4209** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf, data in beta_analysis_data.items():`

🟡 **Line 4278** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `gainers = [p for p in performers if p['change_percent'] > 0][:5]`

🟡 **Line 4279** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `losers = [p for p in performers if p['change_percent'] < 0][-5:]`

🟡 **Line 4993** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `analysis_report['technical_analysis'] = await self._create_technical_analysis(market_data)`

🟡 **Line 5591** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `present_sections = [section for section in expected_sections if section in data and data[section]]`

### src/monitoring/market_reporter_enhanced_test.py

🟡 **Line 288** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_file, 'r') as f:`

🟡 **Line 555** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_keys = [key for key in expected_keys if key not in data]`

🟡 **Line 592** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `return value.tolist()`

🟡 **Line 598** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [self._numpy_to_native(x) for x in value]`

🟡 **Line 717** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for name in field_names:`

🟡 **Line 990** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [self._sanitize_for_logging(item) for item in data]`

🟡 **Line 1376** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `tasks = [self._calculate_single_premium(symbol, all_markets) for symbol in symbols]`

🟡 **Line 1669** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `async with aiohttp.ClientSession() as session:`

🟡 **Line 1950** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `async with aiohttp.ClientSession() as session:`

🟡 **Line 2040** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `whale_bids = [order for order in order_book['bids'] if order[1] >= whale_threshold]`

🟡 **Line 2041** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `whale_asks = [order for order in order_book['asks'] if order[1] >= whale_threshold]`

🟡 **Line 2093** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `all_sizes = [order[1] for order in order_book['bids'] + order_book['asks']]`

🟡 **Line 2108** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `ticker = await self.exchange.fetch_ticker(symbol)`

🟡 **Line 2167** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `section_validation_summary = ", ".join([f"{section}: {status}" for section, status in section_statuses.items()])`

🟡 **Line 2623** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `embed_titles = [e.get('title') for e in formatted_report.get('embeds', [])]`

🟡 **Line 3303** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for key, fallback in fallbacks.items():`

🟡 **Line 3476** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `templates = [f for f in os.listdir(template_dir) if f.endswith('.html')]`

🟡 **Line 3485** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(template_path, 'r') as f:`

🟡 **Line 3486** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `first_lines = [next(f) for _ in range(10)]`

🟡 **Line 3504** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_keys = [k for k in required_template_keys if k not in data]`

🟡 **Line 3733** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `gainers = [p for p in performers if p['change_percent'] > 0][:5]`

🟡 **Line 3734** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `losers = [p for p in performers if p['change_percent'] < 0][-5:]`

### src/monitoring/metrics.py

🟡 **Line 58** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `metrics = [m for m in metrics if m.timestamp >= start_time]`

### src/monitoring/metrics_manager.py

🟡 **Line 120** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `times = [float(t) for t in self._metrics[component][operation]]`

🟡 **Line 166** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `times = [float(m['response_time']) for m in self._metrics['api'][endpoint]]`

🟡 **Line 479** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `statuses = [m['status'] for m in self._metrics['health'][component]]`

🟡 **Line 589** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `values = [float(m['value']) for m in self._metrics[name]['values']]`

🟡 **Line 1083** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `significant_stats = [stat for stat in top_stats if stat.size_diff > 1024 * 1024]`

🟡 **Line 1268** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for endpoint, api_metrics in self.api_call_counts.items():`

🟡 **Line 1278** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for context, count in self.error_counts.items():`

🟡 **Line 1349** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `[(name, data["avg_duration"]) for name, data in report["operations"].items()],`

🟡 **Line 1362** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `[(endpoint, data["count"]) for endpoint, data in report["api_calls"].items()],`

🟡 **Line 1385** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `[(context, count) for context, count in report["errors"].items()],`

### src/monitoring/monitor.py

🟡 **Line 231** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in market_data]`

🟡 **Line 303** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in data.columns]`

🟡 **Line 381** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in orderbook_data]`

🟡 **Line 411** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(len(orderbook_data['bids']) - 1):`

🟡 **Line 475** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in trades_data.columns]`

🟡 **Line 600** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_critical = [field for field in critical_fields if field not in ticker_data]`

🟡 **Line 607** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_recommended = [field for field in recommended_fields if field not in ticker_data]`

🟡 **Line 883** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in market_data]`

🟡 **Line 955** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in data.columns]`

🟡 **Line 1033** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in orderbook_data]`

🟡 **Line 1063** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(len(orderbook_data['bids']) - 1):`

🟡 **Line 1127** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in trades_data.columns]`

🟡 **Line 1252** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_critical = [field for field in critical_fields if field not in ticker_data]`

🟡 **Line 1259** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_recommended = [field for field in recommended_fields if field not in ticker_data]`

🟡 **Line 1300** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in funding_data]`

🟡 **Line 1461** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in data]`

🟡 **Line 1511** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, trade in enumerate(data[:3]):`

🟡 **Line 1990** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbols = [s['symbol'].replace('/', '') for s in top_symbols[:10]]  # Limit to top 10`

🟡 **Line 2589** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbol_display = [s['symbol'] if isinstance(s, dict) and 'symbol' in s else s for s in symbols[:5]]`

🟡 **Line 2898** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `await self.metrics_manager.update_system_metrics({`

🟡 **Line 2947** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in market_data]`

🟡 **Line 3086** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `isinstance(level[0], str) for level in orderbook_data.get('bids', [])[:5] if isinstance(level, (list, tuple)) and len(level) >= 2`

🟡 **Line 3093** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for side in ['bids', 'asks']:`

🟡 **Line 3232** (sequential_api_calls)
- Issue: Multiple sequential API calls (5) - consider concurrent execution
- Code: `'exchange': await self._check_exchange_health(),`

🟡 **Line 3233** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `'database': await self._check_database_health(),`

🟡 **Line 4198** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_quantities = np.array([float(bid[1]) for bid in bids[:5]])`

🟡 **Line 4199** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_quantities = np.array([float(ask[1]) for ask in asks[:5]])`

🟡 **Line 4538** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing = [col for col in required_columns if col not in df.columns]`

🟡 **Line 4971** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `self.logger.debug(f"Original columns: {df.columns.tolist()}")`

🟡 **Line 4974** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `self.logger.debug(f"DataFrame after column mapping: {df.shape}, columns: {df.columns.tolist()}")`

🟡 **Line 5311** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in data]`

🟡 **Line 5365** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, trade in enumerate(data[:3]):`

🟡 **Line 5576** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `colors = ['green' if row['close'] >= row['open'] else 'red' for _, row in df.iterrows()]`

🟡 **Line 5587** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ax1.set_xticklabels([timestamp.strftime('%H:%M') for timestamp in df.index[::max(1, len(df) // 10)]])`

🟡 **Line 5599** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ax2.set_xticklabels([timestamp.strftime('%H:%M') for timestamp in df.index[::max(1, len(df) // 10)]])`

🟡 **Line 5638** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_prices = [bid[0] for bid in bids[:20]]  # Limit to 20 levels`

🟡 **Line 5639** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_quantities = [bid[1] for bid in bids[:20]]`

🟡 **Line 5640** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_prices = [ask[0] for ask in asks[:20]]`

🟡 **Line 5641** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_quantities = [ask[1] for ask in asks[:20]]`

🟡 **Line 5644** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `bid_cumulative = np.cumsum(bid_quantities).tolist()`

🟡 **Line 5645** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `ask_cumulative = np.cumsum(ask_quantities).tolist()`

🟡 **Line 5770** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `pie_colors = [colors.get(side, 'gray') for side in volume_by_side.index]`

🟡 **Line 5814** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(output_path, 'wb') as f:`

🟡 **Line 6418** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `formatted_times = [f"{t.hour:02d}:{t.minute:02d} UTC" for t in report_times]`

🟡 **Line 6503** (sequential_api_calls)
- Issue: Multiple sequential API calls (5) - consider concurrent execution
- Code: `'exchange': await self._check_exchange_health(),`

🟡 **Line 6504** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `'database': await self._check_database_health(),`

🟡 **Line 6702** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `whale_bids = [order for order in bids if float(order[1]) >= whale_threshold]`

🟡 **Line 6703** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `whale_asks = [order for order in asks if float(order[1]) >= whale_threshold]`

🟡 **Line 7358** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_keys = [key for key in expected_keys[component_name] if key not in component_result]`

### src/monitoring/monitor_original.py

🟡 **Line 228** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in market_data]`

🟡 **Line 300** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in data.columns]`

🟡 **Line 378** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in orderbook_data]`

🟡 **Line 408** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(len(orderbook_data['bids']) - 1):`

🟡 **Line 472** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in trades_data.columns]`

🟡 **Line 597** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_critical = [field for field in critical_fields if field not in ticker_data]`

🟡 **Line 604** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_recommended = [field for field in recommended_fields if field not in ticker_data]`

🟡 **Line 645** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in funding_data]`

🟡 **Line 806** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in data]`

🟡 **Line 856** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, trade in enumerate(data[:3]):`

🟡 **Line 1765** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbol_display = [s['symbol'] if isinstance(s, dict) and 'symbol' in s else s for s in symbols[:5]]`

🟡 **Line 2012** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `await self.metrics_manager.update_system_metrics({`

🟡 **Line 2061** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in market_data]`

🟡 **Line 2195** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for side in ['bids', 'asks']:`

🟡 **Line 2313** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for key, value in original_trades.items():`

🟡 **Line 2337** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for trade in trades_list:`

🟡 **Line 2433** (sequential_api_calls)
- Issue: Multiple sequential API calls (5) - consider concurrent execution
- Code: `'exchange': await self._check_exchange_health(),`

🟡 **Line 2434** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `'database': await self._check_database_health(),`

🟡 **Line 2672** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for interp in market_interpretations:`

🟡 **Line 2977** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for interp in market_interpretations:`

🟡 **Line 3416** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_quantities = np.array([float(bid[1]) for bid in bids[:5]])`

🟡 **Line 3417** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_quantities = np.array([float(ask[1]) for ask in asks[:5]])`

🟡 **Line 3714** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing = [col for col in required_columns if col not in df.columns]`

🟡 **Line 4147** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `self.logger.debug(f"Original columns: {df.columns.tolist()}")`

🟡 **Line 4150** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `self.logger.debug(f"DataFrame after column mapping: {df.shape}, columns: {df.columns.tolist()}")`

🟡 **Line 4487** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_fields = [field for field in required_fields if field not in data]`

🟡 **Line 4541** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, trade in enumerate(data[:3]):`

🟡 **Line 4752** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `colors = ['green' if row['close'] >= row['open'] else 'red' for _, row in df.iterrows()]`

🟡 **Line 4763** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ax1.set_xticklabels([timestamp.strftime('%H:%M') for timestamp in df.index[::max(1, len(df) // 10)]])`

🟡 **Line 4775** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ax2.set_xticklabels([timestamp.strftime('%H:%M') for timestamp in df.index[::max(1, len(df) // 10)]])`

🟡 **Line 4814** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_prices = [bid[0] for bid in bids[:20]]  # Limit to 20 levels`

🟡 **Line 4815** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_quantities = [bid[1] for bid in bids[:20]]`

🟡 **Line 4816** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_prices = [ask[0] for ask in asks[:20]]`

🟡 **Line 4817** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_quantities = [ask[1] for ask in asks[:20]]`

🟡 **Line 4820** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `bid_cumulative = np.cumsum(bid_quantities).tolist()`

🟡 **Line 4821** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `ask_cumulative = np.cumsum(ask_quantities).tolist()`

🟡 **Line 4946** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `pie_colors = [colors.get(side, 'gray') for side in volume_by_side.index]`

🟡 **Line 4990** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(output_path, 'wb') as f:`

🟡 **Line 5594** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `formatted_times = [f"{t.hour:02d}:{t.minute:02d} UTC" for t in report_times]`

🟡 **Line 5679** (sequential_api_calls)
- Issue: Multiple sequential API calls (5) - consider concurrent execution
- Code: `'exchange': await self._check_exchange_health(),`

🟡 **Line 5680** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `'database': await self._check_database_health(),`

🟡 **Line 5945** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_keys = [key for key in expected_keys[component_name] if key not in component_result]`

🟡 **Line 6265** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `whale_bids = [order for order in bids if float(order[1]) >= whale_threshold]`

🟡 **Line 6266** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `whale_asks = [order for order in asks if float(order[1]) >= whale_threshold]`

### src/monitoring/optimized_alpha_scanner.py

🟡 **Line 70** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_path, 'r') as f:`

🟡 **Line 393** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for pattern in all_patterns:`

🟡 **Line 399** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, symbol_data in market_data.items():`

🟡 **Line 555** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `avg_alpha = np.mean([alert.alpha_magnitude for alert in alerts]) if alerts else 0`

### src/monitoring/performance.py

🟡 **Line 105** (blocking_io)
- Issue: Blocking sleep - use asyncio.sleep in async code
- Code: `time.sleep(interval)`

### src/monitoring/report_generator.py

🟡 **Line 126** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(output_path, 'w') as f:`

🟡 **Line 253** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `hlines=dict(hlines=hlines, colors=['blue' if i == 0 else 'red' if i == 1 else 'green' for i in range(len(hlines))],`

🟡 **Line 256** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `alines=dict(alines=[(df.index[0], price, df.index[-1], price) for price in hlines],`

🟡 **Line 257** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `colors=['blue' if i == 0 else 'red' if i == 1 else 'green' for i in range(len(hlines))],`

🟡 **Line 534** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(file_path, 'rb') as f:`

### src/monitoring/signal_frequency_tracker.py

🟡 **Line 861** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [asdict(alert) for alert in recent_alerts]`

### src/monitoring/smart_money_detector.py

🟡 **Line 152** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `orderflow_events = await self._detect_orderflow_imbalance(symbol, market_data, current_time)`

🟡 **Line 186** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_volume = sum(float(bid[1]) for bid in orderbook['bids'][:10])`

🟡 **Line 187** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_volume = sum(float(ask[1]) for ask in orderbook['asks'][:10])`

🟡 **Line 213** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bid_depth = sum(float(bid[1]) * float(bid[0]) for bid in orderbook['bids'][:20])`

🟡 **Line 214** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ask_depth = sum(float(ask[1]) * float(ask[0]) for ask in orderbook['asks'][:20])`

🟡 **Line 255** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `imbalances = [d['imbalance'] for d in recent_data]`

🟡 **Line 306** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `recent_volumes = [d['volume'] for d in volume_data[-20:]]`

🟡 **Line 700** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'recent_alert_rate': len([t for t in self.alert_history if time.time() - t < 3600]),`

### src/monitoring/test_market_reporter.py

🟡 **Line 61** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_sections = [section for section in required_sections if section not in market_summary]`

### src/monitoring/visualizers/confluence_visualizer.py

🟡 **Line 121** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `values = [component_scores[component] for component in components]`

### src/optimization/confluence_parameter_spaces.py

🟡 **Line 370** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(output_path, 'w') as f:`

### src/optimization/objectives.py

🟡 **Line 318** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, params in enumerate(parameter_sets):`

### src/optimization/optuna_engine.py

🟡 **Line 91** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_path, 'r') as f:`

🟡 **Line 97** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_path, 'w') as f:`

🟡 **Line 214** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'n_complete_trials': len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]),`

🟡 **Line 215** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'n_pruned_trials': len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED]),`

🟡 **Line 216** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `'n_failed_trials': len([t for t in study.trials if t.state == optuna.trial.TrialState.FAIL]),`

🟡 **Line 223** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `completed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]`

🟡 **Line 225** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `values = [t.value for t in completed_trials if t.value is not None]`

🟡 **Line 266** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(output_path, 'w') as f:`

### src/optimization/parameter_spaces.py

🟡 **Line 358** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(output_path, 'w') as f:`

### src/portfolio/portfolio_manager.py

🟡 **Line 453** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, pos in report['current_positions'].items():`

### src/reports/bitcoin_beta_7day_report.py

🟡 **Line 169** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf in self.timeframes.values():`

🟡 **Line 202** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_path, 'r') as f:`

🟡 **Line 209** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(config_path, 'w') as f:`

🟡 **Line 289** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `self.logger.warning(f"Template 'bitcoin_beta_dark.html' not found in any of: {[str(d) for d in template_dirs]}")`

🟡 **Line 421** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `watermark_img = PILImage.open(BytesIO(png_data)).convert("RGBA")`

🟡 **Line 759** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_name, tf_interval in self.timeframes.items():`

🟡 **Line 808** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `tasks = [fetch_symbol_data(symbol) for symbol in symbols]`

🟡 **Line 1080** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(0, len(chart_tasks), batch_size):`

🟡 **Line 1085** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for task in batch:`

🟡 **Line 1172** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in market_data.keys():`

🟡 **Line 1187** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sorted_symbols = [btc_symbol] + [pair[0] for pair in symbol_beta_pairs]`

🟡 **Line 1267** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, (tf_name, tf_display) in enumerate(timeframe_names.items()):`

🟡 **Line 1283** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbols = [pair[0].replace('USDT', '') for pair in symbol_beta_pairs]`

🟡 **Line 1284** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `betas = [pair[1] for pair in symbol_beta_pairs]`

🟡 **Line 1285** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `colors_list = [self._get_symbol_color(pair[0]) for pair in symbol_beta_pairs]`

🟡 **Line 1340** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values():`

🟡 **Line 1352** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sorted_symbols = [pair[0] for pair in symbol_beta_pairs]`

🟡 **Line 1363** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in sorted_symbols:`

🟡 **Line 1385** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ax.set_yticklabels([s.replace('USDT', '') for s in sorted_symbols])`

🟡 **Line 1388** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(len(sorted_symbols)):`

🟡 **Line 1435** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values():`

🟡 **Line 1451** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sorted_symbols = [pair[0] for pair in symbol_beta_pairs]`

🟡 **Line 1477** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, symbol in enumerate(sorted_symbols[:n_symbols]):`

🟡 **Line 1482** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf in timeframes:`

🟡 **Line 1506** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for spine in ax.spines.values():`

🟡 **Line 1545** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values():`

🟡 **Line 1561** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sorted_symbols = [pair[0] for pair in symbol_beta_pairs]`

🟡 **Line 1603** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(len(headers)):`

🟡 **Line 1609** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(1, len(table_data) + 1):`

🟡 **Line 1672** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `htf_betas = [stats['beta'] for symbol, stats in beta_analysis['htf'].items() if symbol != 'BTC/USDT']`

🟡 **Line 1710** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for chart_type, path in chart_paths.items():`

🟡 **Line 1720** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, stats in beta_analysis['htf'].items():`

🟡 **Line 1930** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sorted_symbols = [btc_symbol] + [pair[0] for pair in symbol_beta_pairs]`

🟡 **Line 2021** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, (tf_name, tf_display) in enumerate(timeframe_names.items()):`

🟡 **Line 2038** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbols = [pair[0].replace('USDT', '') for pair in symbol_beta_pairs]`

🟡 **Line 2039** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `betas = [pair[1] for pair in symbol_beta_pairs]`

🟡 **Line 2040** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `colors_list = [self._get_symbol_color(pair[0]) for pair in symbol_beta_pairs]`

🟡 **Line 2099** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values():`

🟡 **Line 2113** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sorted_symbols = [pair[0] for pair in symbol_beta_pairs]`

🟡 **Line 2119** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in sorted_symbols:`

🟡 **Line 2143** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ax.set_yticklabels([s.replace('USDT', '') for s in sorted_symbols])`

🟡 **Line 2146** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(len(sorted_symbols)):`

🟡 **Line 2401** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, stats in beta_analysis['htf'].items():`

🟡 **Line 2518** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `betas = {symbol: stats['beta'] for symbol, stats in beta_analysis['htf'].items()`

🟡 **Line 2529** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `correlations = {symbol: stats['correlation'] for symbol, stats in beta_analysis['htf'].items()`

🟡 **Line 2537** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `vol_ratios = {symbol: stats['volatility_ratio'] for symbol, stats in beta_analysis['htf'].items()`

🟡 **Line 2546** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `high_confidence_opps = [opp for opp in alpha_opportunities if opp.confidence > 0.8]`

🟡 **Line 2745** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, timeframes in market_data.items():`

🟡 **Line 2833** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_name, btc_df in btc_data.items():`

🟡 **Line 2857** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `correlations_over_time.extend(rolling_corr.dropna().tolist())`

🟡 **Line 2878** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, timeframes in market_data.items():`

### src/reports/bitcoin_beta_alpha_detector.py

🟡 **Line 197** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `short_avg = np.mean([b for b in short_term_betas if b != 0])`

🟡 **Line 198** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `long_avg = np.mean([b for b in long_term_betas if b != 0])`

🟡 **Line 299** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `current_beta = np.mean([data[tf].get('beta', 0) for tf in data.keys()])`

🟡 **Line 614** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `correlations = [data.get('correlation', 0) for data in symbol_data.values()]`

🟡 **Line 615** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `alphas = [data.get('alpha', 0) for data in symbol_data.values()]`

🟡 **Line 661** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_name, tf_data in beta_analysis.items():`

🟡 **Line 669** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values():`

🟡 **Line 757** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_name, tf_data in beta_analysis.items():`

🟡 **Line 782** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `betas = [entry['beta'] for entry in self._beta_history[symbol][-10:]]`

🟡 **Line 789** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `correlations = [entry['correlation'] for entry in self._beta_history[symbol][-10:]]`

### src/reports/bitcoin_beta_report.py

🟡 **Line 325** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `watermark_img = PILImage.open(BytesIO(png_data)).convert("RGBA")`

🟡 **Line 617** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in symbols:`

🟡 **Line 918** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in market_data.keys():`

🟡 **Line 933** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sorted_symbols = [btc_symbol] + [pair[0] for pair in symbol_beta_pairs]`

🟡 **Line 1011** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, (tf_name, tf_display) in enumerate(timeframe_names.items()):`

🟡 **Line 1027** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbols = [pair[0].replace('USDT', '') for pair in symbol_beta_pairs]`

🟡 **Line 1028** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `betas = [pair[1] for pair in symbol_beta_pairs]`

🟡 **Line 1029** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `colors_list = [self._get_symbol_color(pair[0]) for pair in symbol_beta_pairs]`

🟡 **Line 1084** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values():`

🟡 **Line 1096** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sorted_symbols = [pair[0] for pair in symbol_beta_pairs]`

🟡 **Line 1102** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in sorted_symbols:`

🟡 **Line 1124** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ax.set_yticklabels([s.replace('USDT', '') for s in sorted_symbols])`

🟡 **Line 1127** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(len(sorted_symbols)):`

🟡 **Line 1173** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values():`

🟡 **Line 1189** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sorted_symbols = [pair[0] for pair in symbol_beta_pairs]`

🟡 **Line 1209** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, symbol in enumerate(sorted_symbols[:n_symbols]):`

🟡 **Line 1214** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf in timeframes:`

🟡 **Line 1238** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for spine in ax.spines.values():`

🟡 **Line 1276** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values():`

🟡 **Line 1292** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sorted_symbols = [pair[0] for pair in symbol_beta_pairs]`

🟡 **Line 1329** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(len(headers)):`

🟡 **Line 1335** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(1, len(table_data) + 1):`

🟡 **Line 1393** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `htf_betas = [stats['beta'] for symbol, stats in beta_analysis['htf'].items() if symbol != 'BTCUSDT']`

🟡 **Line 1431** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for chart_type, path in chart_paths.items():`

🟡 **Line 1441** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, stats in beta_analysis['htf'].items():`

🟡 **Line 1614** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in market_data.keys():`

🟡 **Line 1633** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sorted_symbols = [btc_symbol] + [pair[0] for pair in symbol_beta_pairs]`

🟡 **Line 1721** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, (tf_name, tf_display) in enumerate(timeframe_names.items()):`

🟡 **Line 1738** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbols = [pair[0].replace('USDT', '') for pair in symbol_beta_pairs]`

🟡 **Line 1739** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `betas = [pair[1] for pair in symbol_beta_pairs]`

🟡 **Line 1740** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `colors_list = [self._get_symbol_color(pair[0]) for pair in symbol_beta_pairs]`

🟡 **Line 1799** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_data in beta_analysis.values():`

🟡 **Line 1813** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sorted_symbols = [pair[0] for pair in symbol_beta_pairs]`

🟡 **Line 1819** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in sorted_symbols:`

🟡 **Line 1843** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `ax.set_yticklabels([s.replace('USDT', '') for s in sorted_symbols])`

🟡 **Line 1846** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i in range(len(sorted_symbols)):`

🟡 **Line 2086** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, stats in beta_analysis['htf'].items():`

🟡 **Line 2203** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `betas = {symbol: stats['beta'] for symbol, stats in beta_analysis['htf'].items()`

🟡 **Line 2214** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `correlations = {symbol: stats['correlation'] for symbol, stats in beta_analysis['htf'].items()`

🟡 **Line 2222** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `vol_ratios = {symbol: stats['volatility_ratio'] for symbol, stats in beta_analysis['htf'].items()`

🟡 **Line 2231** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `high_confidence_opps = [opp for opp in alpha_opportunities if opp.confidence > 0.8]`

### src/reports/bitcoin_beta_scheduler.py

🟡 **Line 130** (blocking_io)
- Issue: Blocking sleep - use asyncio.sleep in async code
- Code: `time.sleep(60)  # Check every minute`

🟡 **Line 133** (blocking_io)
- Issue: Blocking sleep - use asyncio.sleep in async code
- Code: `time.sleep(60)`

### src/scripts/fix_market_reporter.py

🟡 **Line 73** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for base_asset in base_assets:`

🟡 **Line 131** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for asset, contracts in results.items():`

🟡 **Line 145** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `logger.info(f"  Working symbols: {', '.join([c['symbol'] for c in contracts])}")`

### src/scripts/get_bybit_instruments.py

🟡 **Line 49** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for asset in assets:`

🟡 **Line 50** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `asset_futures = [f for f in futures if f.get('symbol', '').startswith(asset)]`

🟡 **Line 88** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for asset, contracts in results.items():`

🟡 **Line 110** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for asset, contracts in results.items():`

### src/scripts/get_bybit_quarterly.py

🟡 **Line 79** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `futures = [item for item in result['result']['list']`

### src/scripts/test_bybit_api.py

🟡 **Line 128** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `futures = [i for i in instruments if i.get('contractType') != 'LinearPerpetual' and i.get('contractType') != 'InversePerpetual']`

🟡 **Line 133** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in ["BTC", "ETH", "SOL", "XRP", "AVAX"]:`

🟡 **Line 134** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `symbol_futures = [f for f in futures if f.get('symbol', '').startswith(symbol)]`

### src/scripts/test_futures_formats.py

🟡 **Line 114** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for format_name, symbols in results.items():`

🟡 **Line 117** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, price in symbols.items():`

🟡 **Line 124** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for base_asset in base_assets:`

🟡 **Line 129** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for format_name in formats_to_check:`

### src/scripts/verify_bybit_tickers.py

🟡 **Line 102** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, data in results["linear_hyphenated"].items():`

🟡 **Line 106** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, data in results["base_only_hyphenated"].items():`

🟡 **Line 110** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, data in results["inverse_month_code"].items():`

🟡 **Line 114** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in results["invalid"]:`

🟡 **Line 121** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for asset in assets:`

🟡 **Line 125** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in results["linear_hyphenated"]:`

🟡 **Line 130** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol in results["base_only_hyphenated"]:`

🟡 **Line 156** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `invalid_for_asset = [s for s in results["invalid"] if s.startswith(asset)]`

### src/signal_generation/signal_generator.py

🟡 **Line 479** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(filepath, 'w') as f:`

🟡 **Line 1379** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `component_scores = [score for score in components.values() if isinstance(score, (int, float))]`

🟡 **Line 1400** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bullish_components = [name for name, score in components.items() if isinstance(score, (int, float)) and score > 60]`

🟡 **Line 1401** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `bearish_components = [name for name, score in components.items() if isinstance(score, (int, float)) and score < 40]`

🟡 **Line 1488** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `market_interpretations = [f"{interp['display_name']}: {interp['interpretation']}" for interp in raw_interpretations]`

🟡 **Line 1579** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `[(name, score) for name, score in components.items() if isinstance(score, (int, float))],`

🟡 **Line 1603** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for component_name, score in components.items():`

🟡 **Line 1629** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `sub_component_count = len([s for s in sub_components.values() if isinstance(s, (int, float))])`

### src/tools/run_diagnostics.py

🟡 **Line 162** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, operations in self.symbol_operations.items():`

🟡 **Line 164** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for i, op in enumerate(operations):`

🟡 **Line 182** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `init_ops = [(op, i) for i, op in enumerate(self.current_sequence) if 'initializ' in op['operation'].lower()]`

🟡 **Line 441** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for log_file in log_files:`

🟡 **Line 556** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, timestamps in fetch_timestamps.items():`

🟡 **Line 623** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for location in log_locations:`

🟡 **Line 627** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for root, _, files in os.walk(location):`

🟡 **Line 628** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for file in files:`

🟡 **Line 661** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for log_file in log_files:`

🟡 **Line 665** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for line_num, line in enumerate(f, 1):`

🟡 **Line 667** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for pattern in LOG_PATTERNS['error']:`

🟡 **Line 673** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for pattern in LOG_PATTERNS['warning']:`

🟡 **Line 679** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for pattern in LOG_PATTERNS['redundant_operations']:`

🟡 **Line 685** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for pattern in LOG_PATTERNS['performance_issues']:`

🟡 **Line 731** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for symbol, data in market_monitor_analysis['duplicate_fetches'].items():`

🟡 **Line 746** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for timestamp, log_file, line_num, line in init_data['examples']:`

🟡 **Line 755** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for log_file, line_num, line in market_monitor_analysis['websocket_issues'][:5]:`

🟡 **Line 775** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for log_file, line_num, line in metrics['examples']:`

🟡 **Line 782** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for data_type, count in market_monitor_analysis['api_call_frequencies'].items():`

🟡 **Line 820** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for error_type, occurrences in errors_by_type.items():`

🟡 **Line 1042** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for location in log_locations:`

🟡 **Line 1045** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for file in os.listdir(location):`

🟡 **Line 1055** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for file in specific_log_files:`

### src/trade_execution/trade_executor.py

🟡 **Line 150** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `response = await self._signed_request("/v5/account/wallet-balance", {"accountType": "UNIFIED"}, "GET")`

🟡 **Line 922** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for account in account_info:`

🟡 **Line 924** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for coin in coins:`

### src/trade_execution/trading/trading_system.py

🟡 **Line 121** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `await self.cancel_all_orders()`

🟡 **Line 124** (sequential_api_calls)
- Issue: Multiple sequential API calls (5) - consider concurrent execution
- Code: `await self.data_manager.cleanup()`

🟡 **Line 125** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `await self.position_manager.cleanup()`

🟡 **Line 255** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `await self.cancel_orders(symbol)`

🟡 **Line 258** (sequential_api_calls)
- Issue: Multiple sequential API calls (5) - consider concurrent execution
- Code: `await self.data_manager.remove_symbol(symbol)`

🟡 **Line 259** (sequential_api_calls)
- Issue: Multiple sequential API calls (4) - consider concurrent execution
- Code: `await self.position_manager.remove_symbol(symbol)`

### src/utils/compressed_log_handler.py

🟡 **Line 89** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(self.baseFilename, 'rb') as f_in:`

🟡 **Line 90** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with gzip.open(dfn, 'wb') as f_out:`

🟡 **Line 95** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `self.stream = self._open()`

### src/utils/error_handling.py

🟡 **Line 136** (blocking_io)
- Issue: Blocking sleep - use asyncio.sleep in async code
- Code: `time.sleep(delay)`

### src/utils/formatters/deprecate_legacy_formatter.py

🟡 **Line 99** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(monitor_path, "r") as f:`

🟡 **Line 108** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(monitor_path, "w") as f:`

### src/utils/formatters/install_formatter.py

🟡 **Line 60** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(monitor_path, 'r') as f:`

🟡 **Line 158** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(monitor_path, 'w') as f:`

### src/utils/formatters/update_formatter.py

🟡 **Line 27** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(monitor_path, "r") as f:`

🟡 **Line 67** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(monitor_path, "w") as f:`

### src/utils/helpers.py

🟡 **Line 218** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for category, df_names in categories.items():`

🟡 **Line 256** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(metadata_path, 'w') as f:`

🟡 **Line 275** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_name, tf_config in config['timeframes'].items():`

🟡 **Line 284** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for tf_name, tf_config in config['timeframes'].items():`

🟡 **Line 406** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `logger.debug(f"{name} columns: {df.columns.tolist()}")`

### src/utils/indicators.py

🟡 **Line 57** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_columns = [col for col in required_columns if col not in df.columns]`

### src/utils/json_encoder.py

🟡 **Line 74** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for k, v in obj.items():`

🟡 **Line 79** (nested_loops)
- Issue: Nested loops detected - potential O(n²) complexity
- Code: `for item in obj:`

🟡 **Line 113** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `return obj.tolist()`

🟡 **Line 214** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(filepath, 'w') as f:`

🟡 **Line 241** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(filepath, 'r') as f:`

### src/utils/liquidation_cache.py

🟡 **Line 60** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(cache_file, "w") as f:`

🟡 **Line 89** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(cache_file, "r") as f:`

🟡 **Line 119** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(cache_file, 'w') as f:`

🟡 **Line 164** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(cache_file, 'r') as f:`

🟡 **Line 217** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(cache_file, 'w') as f:`

🟡 **Line 250** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(filepath, "r") as f:`

### src/utils/optimized_logging.py

🟡 **Line 324** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with open(old_file, 'rb') as f_in:`

🟡 **Line 325** (blocking_io)
- Issue: Synchronous file I/O - consider async alternatives
- Code: `with gzip.open(compressed_file, 'wb') as f_out:`

### src/utils/performance.py

🟡 **Line 230** (blocking_io)
- Issue: Blocking sleep - use asyncio.sleep in async code
- Code: `time.sleep(self.interval)`

🟡 **Line 234** (blocking_io)
- Issue: Blocking sleep - use asyncio.sleep in async code
- Code: `time.sleep(self.interval)`

### src/utils/serializers.py

🟡 **Line 41** (memory_concern)
- Issue: Converting to list - may use excessive memory
- Code: `return obj.tolist()`

🟡 **Line 61** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `return [serialize_for_json(item) for item in obj]`

### src/utils/validation.py

🟡 **Line 26** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_core = [key for key in core_keys if key not in data]`

🟡 **Line 33** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `missing_recommended = [key for key in recommended_keys if key not in data]`

### src/utils/validation_types.py

🟡 **Line 37** (memory_concern)
- Issue: Large list comprehension - consider generator
- Code: `{'available_types': [t.value for t in cls]}`