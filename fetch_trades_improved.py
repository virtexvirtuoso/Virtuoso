"""
Improved fetch_trades_data function for test_market_monitor_btcusdt.py
"""

async def fetch_trades_data():
    """Fetch recent trades with enhanced processing to ensure proper format for orderflow analysis"""
    max_retries = 5
    retry_delay = 1.5
    all_trades = []
    
    for attempt in range(max_retries):
        try:
            # Apply rate limiting
            await rate_limiter.wait_if_needed("v5/market/recent-trade")
            
            # Fetch trades with maximum limit (1000 for Bybit)
            trades = []
            
            if hasattr(exchange, 'fetch_trades'):
                # First, try to fetch from regular trades endpoint
                trades = await exchange.fetch_trades(symbol, limit=1000)
                await log_raw_api_response(trades, "trades")
                
                # If we didn't get enough trades, try the history-trades endpoint
                if not trades or len(trades) < 100:
                    logger.info("Not enough trades from regular endpoint, trying history-trades endpoint...")
                    try:
                        # Direct API call for history trades
                        params = {'category': 'linear', 'symbol': symbol, 'limit': 1000}
                        history_response = await exchange._make_request('GET', 'v5/market/history-trades', params=params)
                        await log_raw_api_response(history_response, "history-trades")
                        
                        if isinstance(history_response, dict) and 'result' in history_response and 'list' in history_response['result']:
                            history_trades = history_response['result']['list']
                            logger.info(f"Fetched {len(history_trades)} additional trades from history endpoint")
                            
                            # Convert history trades to standard format and add to trades list
                            for trade in history_trades:
                                std_trade = {
                                    'id': trade.get('execId', ''),
                                    'price': float(trade.get('price', 0)),
                                    'amount': float(trade.get('size', 0)),
                                    'cost': float(trade.get('price', 0)) * float(trade.get('size', 0)),
                                    'side': trade.get('side', '').lower(),
                                    'timestamp': int(trade.get('time', 0)),
                                    'datetime': datetime.fromtimestamp(int(trade.get('time', 0))/1000).isoformat(),
                                    'symbol': symbol,
                                    'exchange': 'bybit'
                                }
                                trades.append(std_trade)
                    except Exception as history_e:
                        logger.warning(f"Failed to fetch history trades: {str(history_e)}")
                
                # Process trades to ensure proper format for orderflow analysis
                if trades:
                    processed_trades = []
                    logger.info(f"Processing {len(trades)} fetched trades")
                    
                    for trade in trades:
                        # Ensure all required fields are present
                        processed_trade = {
                            'id': trade.get('id', str(time.time() * 1000)),
                            'price': float(trade.get('price', 0)),
                            'amount': float(trade.get('amount', 0)),
                            'cost': float(trade.get('cost', 0)) if 'cost' in trade else float(trade.get('price', 0)) * float(trade.get('amount', 0)),
                            'side': trade.get('side', '').lower(),
                            'timestamp': int(trade.get('timestamp', time.time() * 1000)),
                            'datetime': trade.get('datetime', datetime.fromtimestamp(int(trade.get('timestamp', time.time() * 1000))/1000).isoformat()),
                            'symbol': symbol,
                            'exchange': 'bybit',
                            # Add alternative field names used in orderflow analysis
                            'size': float(trade.get('amount', 0)),
                            'time': int(trade.get('timestamp', time.time() * 1000)),
                            'p': float(trade.get('price', 0)),
                            'v': float(trade.get('amount', 0)),
                            'S': trade.get('side', '').lower(),
                            'T': int(trade.get('timestamp', time.time() * 1000))
                        }
                        processed_trades.append(processed_trade)
                    
                    logger.info(f"Successfully processed {len(processed_trades)} trades")
                    all_trades.extend(processed_trades)
                    break  # Success, exit the retry loop
            else:
                # Direct API call
                params = {'category': 'linear', 'symbol': symbol, 'limit': 1000}
                response = await exchange._make_request('GET', 'v5/market/recent-trade', params=params)
                await log_raw_api_response(response, "trades")
                
                if isinstance(response, dict) and 'result' in response and 'list' in response['result']:
                    trades = response['result']['list']
                    if not trades:
                        logger.warning(f"Empty trades list on attempt {attempt+1}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                    
                    # Convert to the format expected by orderflow analysis
                    processed_trades = []
                    logger.info(f"Processing {len(trades)} fetched trades from direct API")
                    
                    for trade in trades:
                        # Calculate timestamp from time string
                        try:
                            time_val = int(trade.get('time', 0))
                        except (ValueError, TypeError):
                            time_val = int(time.time() * 1000)
                            
                        # Calculate cost if not provided
                        try:
                            price = float(trade.get('price', 0))
                            amount = float(trade.get('size', 0))
                            cost = price * amount
                        except (ValueError, TypeError):
                            price = 0.0
                            amount = 0.0
                            cost = 0.0
                        
                        processed_trade = {
                            'id': trade.get('execId', str(time.time() * 1000)),
                            'price': price,
                            'amount': amount,
                            'cost': cost,
                            'side': trade.get('side', '').lower(),
                            'timestamp': time_val,
                            'datetime': datetime.fromtimestamp(time_val/1000).isoformat() if time_val else None,
                            'symbol': symbol,
                            'exchange': 'bybit',
                            # Add alternative field names used in orderflow analysis
                            'size': amount,
                            'time': time_val,
                            'p': price,
                            'v': amount,
                            'S': trade.get('side', '').lower(),
                            'T': time_val
                        }
                        processed_trades.append(processed_trade)
                    
                    logger.info(f"Successfully processed {len(processed_trades)} trades from direct API")
                    all_trades.extend(processed_trades)
                    break  # Success, exit the retry loop
                else:
                    logger.warning(f"Invalid trades response format on attempt {attempt+1}")
                    # Try to fetch history trades as fallback
                    try:
                        params = {'category': 'linear', 'symbol': symbol, 'limit': 1000}
                        history_response = await exchange._make_request('GET', 'v5/market/history-trades', params=params)
                        await log_raw_api_response(history_response, "history-trades fallback")
                        
                        if isinstance(history_response, dict) and 'result' in history_response and 'list' in history_response['result']:
                            history_trades = history_response['result']['list']
                            logger.info(f"Fetched {len(history_trades)} trades from history endpoint as fallback")
                            
                            # Process history trades
                            for trade in history_trades:
                                try:
                                    time_val = int(trade.get('time', 0))
                                    price = float(trade.get('price', 0))
                                    amount = float(trade.get('size', 0))
                                    
                                    processed_trade = {
                                        'id': trade.get('execId', str(time.time() * 1000)),
                                        'price': price,
                                        'amount': amount,
                                        'cost': price * amount,
                                        'side': trade.get('side', '').lower(),
                                        'timestamp': time_val,
                                        'datetime': datetime.fromtimestamp(time_val/1000).isoformat() if time_val else None,
                                        'symbol': symbol,
                                        'exchange': 'bybit',
                                        # Add alternative field names
                                        'size': amount,
                                        'time': time_val,
                                        'p': price,
                                        'v': amount,
                                        'S': trade.get('side', '').lower(),
                                        'T': time_val
                                    }
                                    all_trades.append(processed_trade)
                                except Exception as e:
                                    logger.error(f"Error processing history trade: {e}")
                            
                            if all_trades:
                                break  # Success with history trades, exit retry loop
                    except Exception as history_e:
                        logger.error(f"Failed to fetch history trades as fallback: {str(history_e)}")
                    
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                
        except Exception as e:
            logger.error(f"Error fetching trades (attempt {attempt+1}): {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
    
    # Generate mock trades if we didn't get any real ones
    if not all_trades:
        logger.warning("No trades fetched after all attempts, generating mock trades")
        # Get current price from ticker or other sources
        current_price = await get_current_price(exchange, symbol)
        
        # Generate 100 mock trades around the current price
        now_ms = int(time.time() * 1000)
        for i in range(100):
            # Random price near current price (±0.1%)
            price_offset = (np.random.random() - 0.5) * 0.002 * current_price
            trade_price = current_price + price_offset
            
            # Random size between 0.001 and 0.5 BTC
            trade_size = 0.001 + 0.499 * np.random.random()
            
            # Random timestamp in the last hour
            trade_timestamp = now_ms - int(np.random.random() * 3600 * 1000)
            
            # Random side
            side = 'buy' if np.random.random() > 0.5 else 'sell'
            
            mock_trade = {
                'id': f'mock_trade_{i}',
                'price': trade_price,
                'amount': trade_size,
                'cost': trade_price * trade_size,
                'side': side,
                'timestamp': trade_timestamp,
                'datetime': datetime.fromtimestamp(trade_timestamp/1000).isoformat(),
                'symbol': symbol,
                'exchange': 'bybit',
                # Add alternative field names
                'size': trade_size,
                'time': trade_timestamp,
                'p': trade_price,
                'v': trade_size,
                'S': side,
                'T': trade_timestamp
            }
            all_trades.append(mock_trade)
        
        logger.info(f"Generated {len(all_trades)} mock trades for analysis")
    
    # Sort trades by timestamp (newest first by default)
    all_trades.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    
    logger.info(f"Returning {len(all_trades)} trades for analysis")
    if all_trades:
        logger.debug(f"Timespan: {datetime.fromtimestamp(all_trades[-1].get('timestamp', 0)/1000)} to {datetime.fromtimestamp(all_trades[0].get('timestamp', 0)/1000)}")
    
    return all_trades 