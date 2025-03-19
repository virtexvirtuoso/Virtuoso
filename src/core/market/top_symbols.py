"""Top symbols management functionality."""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import asyncio
import time
import traceback
import pandas as pd
import numpy as np
import json

from src.core.analysis.data_validator import DataValidator
from src.core.exchanges.manager import ExchangeManager
from src.data_processing.data_processor import DataProcessor
from src.core.exchanges.base import RateLimitError
from src.core.validation.service import AsyncValidationService
from src.core.validation.context import ValidationContext
from src.data_processing.error_handler import SimpleErrorHandler

logger = logging.getLogger(__name__)

class TopSymbolsManager:
    """Manages top trading symbols.
    
    This class handles the management of trading symbols including:
    - Symbol filtering based on turnover and inclusion lists
    - Market data caching and updates
    - Symbol validation and processing
    """
    
    def __init__(
        self, 
        exchange_manager,
        config: Dict[str, Any],
        validation_service: AsyncValidationService
    ):
        """Initialize the TopSymbolsManager.
        
        Args:
            exchange_manager: The exchange manager instance
            config: Configuration dictionary containing market.symbols settings
            validation_service: Service for validating market data
        """
        self.exchange_manager = exchange_manager
        self.config = config
        self.market_config = config.get('market', {}).get('symbols', {})
        self.logger = logging.getLogger(__name__)
        self.data_validator = DataValidator()
        
        # Initialize DataProcessor with the required parameters
        error_handler = SimpleErrorHandler()
        self.data_processor = DataProcessor(
            config=config,
            error_handler=error_handler
        )
        
        self.validation_service = validation_service
        
        # Initialize caching
        self._symbols_cache = {}
        self._cache_ttl = self.market_config.get('cache_ttl', 300)  # 5 minutes default
        self._last_update = 0
        self.symbol_ranking = {}
        
        # Debug log the configuration
        self.logger.debug(f"Initialized with market config: {self.market_config}")

    async def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get market data for a symbol using centralized fetching."""
        try:
            # Check cache first
            current_time = time.time()
            if symbol in self._symbols_cache:
                cache_entry = self._symbols_cache[symbol]
                if current_time - cache_entry['timestamp'] < self._cache_ttl:
                    return cache_entry['data']

            # Use centralized fetching with retries
            max_retries = 3
            retry_delay = 1.0

            for attempt in range(max_retries):
                try:
                    # Use exchange manager's centralized fetching
                    market_data = await self.exchange_manager.fetch_market_data(symbol)
                    
                    # Validate using centralized validator
                    validation_ctx = ValidationContext(
                        data_type="symbol_data", 
                        metadata={"symbol": symbol}
                    )
                    if not await self.validation_service.validate(market_data, validation_ctx):
                        continue
                    
                    # Process using centralized processor
                    processed_data = await self.data_processor.process(market_data)
                    if not processed_data:
                        self.logger.error(f"Failed to process market data for {symbol}")
                        if attempt == max_retries - 1:
                            return None
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue

                    # Update cache
                    self._symbols_cache[symbol] = {
                        'timestamp': current_time,
                        'data': processed_data
                    }
                    
                    return processed_data

                except RateLimitError as e:
                    if attempt == max_retries - 1:
                        raise
                    retry_after = getattr(e, 'retry_after', retry_delay * (attempt + 1))
                    self.logger.warning(f"Rate limit hit for {symbol}, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                    
                except Exception as e:
                    self.logger.error(f"Error fetching market data for {symbol}: {str(e)}")
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue

        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {str(e)}")
            return None

    def _cache_expired(self) -> bool:
        """Check if cache needs refresh based on TTL"""
        return time.time() - self._last_update > self._cache_ttl

    async def get_symbols(self, force_refresh: bool = False) -> List[str]:
        """Get symbols with cache validation"""
        if force_refresh or self._cache_expired() or not self._symbols_cache:
            await self.update_top_symbols()
            self._last_update = time.time()
        return self._symbols_cache.get('symbols', [])

    async def update_top_symbols(self) -> None:
        """Update the list of top symbols based on configured criteria."""
        try:
            self.logger.info("Starting top symbols update")
            exchange = await self.exchange_manager.get_primary_exchange()
            if not exchange:
                self.logger.error("No primary exchange available")
                return
            
            # Check if using static symbols
            if self.market_config.get('use_static_list', False):
                static_symbols = self.market_config.get('static_symbols', [])
                self.logger.info(f"Using static symbol list with {len(static_symbols)} symbols")
                valid_markets = []
                
                # Fetch data for static symbols
                for symbol in static_symbols:
                    try:
                        market_data = await exchange.fetch_ticker(symbol)
                        if market_data:
                            valid_markets.append(market_data)
                        else:
                            self.logger.warning(f"Static symbol {symbol} returned no data")
                    except Exception as e:
                        self.logger.error(f"Error fetching static symbol {symbol}: {str(e)}")
                
                if not valid_markets:
                    self.logger.error("No valid markets found in static symbols list")
                    return
            else:
                # Dynamic selection block
                self.logger.info("Fetching market data for dynamic symbol selection")
                try:
                    raw_markets = await exchange.fetch_market_tickers()
                    if not raw_markets:
                        self.logger.error("Empty or invalid market data")
                        return
                except Exception as e:
                    self.logger.error(f"Failed to fetch raw markets: {str(e)}")
                    return
            
                # Debug logging for response structure
                self.logger.debug(f"Raw markets response type: {type(raw_markets)}")
                self.logger.debug(f"Response keys: {list(raw_markets.keys()) if isinstance(raw_markets, dict) else ''}")
                if isinstance(raw_markets, dict) and 'result' in raw_markets:
                    self.logger.debug(f"Result keys: {list(raw_markets['result'].keys())}")
                
                # Log pre-filtered symbols
                self.logger.debug(f"Pre-filtered symbol count: {len(raw_markets)}")
                self.logger.debug(f"Sample raw symbols: {[m.get('symbol','') for m in raw_markets[:5]]}")
                
                # Sort and limit to max symbols
                max_symbols = self.market_config.get('max_symbols', 10)
                sorted_markets = sorted(
                    raw_markets,
                    key=lambda x: float(x.get('turnover24h', 0)),
                    reverse=True
                )[:max_symbols]

                # Log turnover statistics
                total_turnover = sum(float(m.get('turnover24h', 0)) for m in raw_markets)
                for market in sorted_markets:
                    symbol = market.get('symbol', '')
                    turnover = float(market.get('turnover24h', 0))
                    percentage = (turnover / total_turnover * 100) if total_turnover > 0 else 0
                    self.logger.info(f"Selected {symbol} with turnover {turnover:.2f} ({percentage:.2f}%)")

                # Log post-filtered symbols
                self.logger.debug(f"Selected {len(sorted_markets)} symbols: {[m.get('symbol', '') for m in sorted_markets]}")
                
                # Extract only the symbol strings for the cache
                symbol_strings = [m.get('symbol', '') for m in sorted_markets if m.get('symbol')]
                
                # Update cache
                self._symbols_cache = {
                    'last_updated': time.time(),
                    'symbols': symbol_strings  # Store only the symbol strings, not the dictionaries
                }
                self.logger.info(f"Updated top symbols cache with {len(symbol_strings)} symbols")
            
        except Exception as e:
            self.logger.error(f"Error updating top symbols: {str(e)}")
            self.logger.debug(traceback.format_exc())

    def _should_include_symbol(self, market: Dict[str, Any]) -> bool:
        """Determine if a symbol should be included based on criteria."""
        try:
            symbol = market.get('symbol', '')
            
            # Check if it's a USDT pair
            if not symbol.endswith('USDT'):
                self.logger.debug(f"Excluding {symbol} - not a USDT pair")
                return False
            
            # Check if it's a PERP contract
            if 'PERP' in symbol:
                self.logger.debug(f"Excluding {symbol} - PERP contract")
                return False
            
            # Check explicit inclusion
            included_symbols = [s.upper() for s in self.market_config.get('static_symbols', [])]
            if included_symbols and symbol in included_symbols:
                self.logger.debug(f"Including {symbol} - found in static_symbols list")
                return True
            
            # Check turnover requirement
            min_turnover = self.market_config.get('min_turnover', 500000)
            turnover = float(market.get('turnover24h', 0))
            
            if turnover < min_turnover:
                self.logger.debug(f"Excluding {symbol} - insufficient turnover ({turnover} < {min_turnover})")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking symbol inclusion for {market.get('symbol', 'unknown')}: {str(e)}")
            return False

    def set_exchange(self, exchange: Any) -> None:
        """Set the exchange instance."""
        try:
            self.logger.debug(f"Setting exchange: {exchange.__class__.__name__}")
            self.exchange = exchange
            
            # Set market type to linear for perpetual futures
            if hasattr(self.exchange, 'set_market_type'):
                self.exchange.set_market_type('linear')
                self.logger.info("Set exchange to linear perpetual market type")
            
        except Exception as e:
            self.logger.error(f"Error setting exchange: {str(e)}", exc_info=True)
            raise

    async def initialize(self) -> bool:
        """Initialize the top symbols manager.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            self.logger.info("Initializing top symbols manager")
            
            # Ensure exchange or exchange_manager is available
            if not hasattr(self, 'exchange') or not self.exchange:
                if hasattr(self, 'exchange_manager') and self.exchange_manager:
                    # Store a reference to the primary exchange for direct access
                    primary_exchange = await self.exchange_manager.get_primary_exchange()
                    if primary_exchange:
                        self.exchange = primary_exchange
                        self.logger.info(f"Set primary exchange: {primary_exchange.__class__.__name__}")
                    else:
                        self.logger.warning("No primary exchange found in exchange manager")
                        
                        # Try to use any available exchange as fallback
                        exchanges = self.exchange_manager.get_exchanges()
                        if exchanges:
                            self.exchange = next(iter(exchanges.values()))
                            self.logger.info(f"Using fallback exchange: {self.exchange.__class__.__name__}")
                
                # Add compatibility for older code that might use _exchange_manager
                if not hasattr(self, '_exchange_manager') and hasattr(self, 'exchange_manager'):
                    self._exchange_manager = self.exchange_manager
                    self.logger.debug("Set _exchange_manager attribute for compatibility")
            
            # Validate exchange configuration
            valid = await self._validate_exchange()
            if not valid:
                self.logger.warning("Exchange validation failed during initialization")
                return False
                
            # Initialize cache
            if not hasattr(self, '_market_data_cache'):
                self._market_data_cache = {}
                
            if not hasattr(self, '_symbols_cache'):
                self._symbols_cache = {'symbols': [], 'timestamp': 0}
                
            if not hasattr(self, '_top_traded_symbols'):
                self._top_traded_symbols = []
                self._last_top_traded_update = 0
                
            # Refresh symbols cache
            await self.update_top_symbols()
            
            self.logger.info("Top symbols manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing top symbols manager: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    async def _validate_exchange(self) -> bool:
        """Validate that we have a working exchange connection.
        
        Returns:
            bool: True if exchange is validated, False otherwise
        """
        try:
            if not hasattr(self, 'exchange') or not self.exchange:
                self.logger.warning("No exchange instance available")
                return False
                
            # Try a basic API call to verify the exchange is working
            try:
                # Get some basic data from the exchange
                test_symbol = "BTCUSDT"  # Common symbol for testing
                ticker = await self.exchange.fetch_ticker(test_symbol)
                
                if not ticker:
                    self.logger.warning(f"Failed to fetch test ticker for {test_symbol}")
                    return False
                    
                self.logger.debug(f"Successfully validated exchange with {test_symbol} ticker")
                return True
                
            except Exception as e:
                self.logger.error(f"Exchange validation failed: {str(e)}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in exchange validation: {str(e)}")
            return False

    async def invalidate_cache(self, symbol: Optional[str] = None) -> None:
        """Invalidate market data cache."""
        try:
            if symbol:
                if symbol in self._symbols_cache:
                    del self._symbols_cache[symbol]
                    self.logger.debug(f"Invalidated cache for {symbol}")
            else:
                self._symbols_cache.clear()
                self._last_update = 0
                self.logger.debug("Invalidated all cache data")
            
        except Exception as e:
            self.logger.error(f"Error invalidating cache: {str(e)}")

    async def refresh_market_data(self, symbols: Optional[List[str]] = None) -> None:
        """Refresh market data for specified symbols or all cached symbols.
        
        Args:
            symbols: List of symbols to refresh (optional, defaults to all cached symbols)
        """
        try:
            # Get exchange from attribute or from exchange manager
            exchange = None
            
            if hasattr(self, 'exchange') and self.exchange:
                exchange = self.exchange
            elif hasattr(self, 'exchange_manager') and self.exchange_manager:
                exchange = await self.exchange_manager.get_primary_exchange()
            elif hasattr(self, '_exchange_manager') and self._exchange_manager:
                exchange = await self._exchange_manager.get_primary_exchange()
            
            if not exchange:
                self.logger.error("No exchange or exchange manager available for refresh")
                # Fall back to direct attributes if possible
                for attr_name in ['_exchange', 'exchange_instance']:
                    if hasattr(self, attr_name) and getattr(self, attr_name):
                        self.logger.info(f"Found fallback exchange via {attr_name}")
                        exchange = getattr(self, attr_name)
                        break
                        
                if not exchange:
                    # Try one more approach - check if we can get exchange from validation service
                    if hasattr(self, 'validation_service') and self.validation_service:
                        if hasattr(self.validation_service, 'exchange'):
                            exchange = self.validation_service.exchange
                            self.logger.info("Found fallback exchange via validation service")
            
            if not exchange:
                self.logger.error("Could not locate any exchange instance for market data refresh")
                return
                
            # Determine which symbols to refresh
            symbols_to_refresh = []
            if symbols and isinstance(symbols, list):
                symbols_to_refresh = symbols
                self.logger.info(f"Refreshing {len(symbols_to_refresh)} specified symbols")
            else:
                # If no symbols provided, refresh all cached symbols
                if self._symbols_cache and 'symbols' in self._symbols_cache and self._symbols_cache['symbols']:
                    symbols_to_refresh = self._symbols_cache['symbols']
                else:
                    # If cache is empty, try to get available symbols from exchange
                    try:
                        available_symbols = await exchange.fetch_tickers()
                        symbols_to_refresh = list(available_symbols.keys())[:15]  # Limit to top 15 for efficiency
                        self.logger.info(f"No cached symbols, using {len(symbols_to_refresh)} symbols from exchange")
                    except Exception as e:
                        self.logger.error(f"Failed to get symbols from exchange: {str(e)}")
                        return
            
            self.logger.info(f"Refreshing market data for {len(symbols_to_refresh)} symbols")
            
            # Refresh each symbol
            refresh_count = 0
            error_count = 0
            
            for symbol in symbols_to_refresh:
                try:
                    # Invalidate cache for this symbol
                    await self.invalidate_cache(symbol)
                    
                    # Fetch fresh market data
                    market_data = await exchange.fetch_ticker(symbol)
                    
                    if market_data:
                        # Normalize the data for consistent field access
                        normalized_data = self._normalize_market_data(market_data, symbol)
                        
                        # Update the cache
                        self._market_data_cache[symbol] = {
                            'data': normalized_data,
                            'timestamp': time.time()
                        }
                        refresh_count += 1
                        self.logger.debug(f"Refreshed market data for {symbol}")
                    else:
                        self.logger.warning(f"No market data returned for {symbol}")
                        error_count += 1
                except Exception as e:
                    self.logger.error(f"Error refreshing market data for {symbol}: {str(e)}")
                    error_count += 1
            
            self.logger.info(f"Market data refresh complete: {refresh_count} successes, {error_count} failures")
            
        except Exception as e:
            self.logger.error(f"Error refreshing market data: {str(e)}")
            self.logger.debug(traceback.format_exc())

    def select_top_symbols(self, market_data: List[Dict[str, Any]], config: Dict[str, Any], limit: int = None) -> List[Dict[str, Any]]:
        try:
            logger.debug(f"Raw market data received: {json.dumps(market_data[:3], indent=2)}")  # Sample first 3 entries
            
            # Add field existence validation
            required_fields = ['symbol', 'turnover24h', 'volume24h']
            missing_fields = []
            for entry in market_data:
                for field in required_fields:
                    if field not in entry:
                        missing_fields.append(field)
                        logger.warning(f"Missing required field '{field}' in symbol {entry.get('symbol', 'unknown')}")
            
            if missing_fields:
                logger.error(f"Critical data missing: {set(missing_fields)} fields not found in {len(missing_fields)} cases")
                return []

            # Add type validation
            type_issues = 0
            valid_markets = []
            for e in market_data:
                try:
                    # Ensure numerical values are floats
                    e['turnover24h'] = float(e['turnover24h'])
                    e['volume24h'] = float(e['volume24h'])
                    valid_markets.append(e)
                except (ValueError, KeyError) as conv_error:
                    type_issues += 1
                    logger.warning(f"Type conversion failed for {e.get('symbol')}: {str(conv_error)}")
            
            logger.debug(f"Data validation passed: {len(valid_markets)}/{len(market_data)} entries remain after type checks")
            
            # Existing sorting logic
            sorted_symbols = sorted(
                valid_markets,
                key=lambda x: (x['turnover24h'], x['volume24h']),
                reverse=True
            )
            
            # Apply limit if provided
            if limit is not None and isinstance(limit, int) and limit > 0:
                sorted_symbols = sorted_symbols[:limit]
                logger.debug(f"Applied limit of {limit}, returning {len(sorted_symbols)} symbols")
            
            return sorted_symbols
            
        except Exception as e:
            logger.error(f"Symbol selection error: {str(e)}")
            logger.debug(f"Error context - Market data count: {len(market_data)}, Config: {config}")
            logger.debug(f"Stack trace:\n{traceback.format_exc()}")
            return []

    async def get_top_traded_symbols(self, limit: int = 15) -> List[str]:
        """Get the top traded symbols by turnover.
        
        Retrieves market data for all symbols and selects the top N symbols
        by trading turnover (quote volume).
        
        Args:
            limit: Maximum number of symbols to return
            
        Returns:
            List of top traded symbol strings
        """
        try:
            self.logger.info(f"Getting top {limit} traded symbols by turnover")
            
            # Refresh top symbols first
            await self.update_top_symbols()
            
            # Get all available market data
            markets = []
            
            # First try to get data from exchange manager
            exchange = None
            if hasattr(self, 'exchange') and self.exchange:
                exchange = self.exchange
            elif hasattr(self, 'exchange_manager') and self.exchange_manager:
                exchange = await self.exchange_manager.get_primary_exchange()
            elif hasattr(self, '_exchange_manager') and self._exchange_manager:
                exchange = await self._exchange_manager.get_primary_exchange()
                
            if exchange:
                try:
                    # Try to get tickers from exchange
                    self.logger.debug("Fetching tickers from exchange")
                    tickers = await exchange.fetch_tickers()
                    
                    for symbol, data in tickers.items():
                        # Skip symbols that don't match our criteria
                        if not self._should_include_symbol({'symbol': symbol}):
                            continue
                            
                        # Normalize the data
                        normalized = self._normalize_market_data(data, symbol)
                        if normalized:
                            markets.append(normalized)
                except Exception as e:
                    self.logger.error(f"Error fetching tickers: {str(e)}")
            
            # If we couldn't get data from exchange or found no valid markets,
            # fall back to the cached symbols
            if not markets and self._symbols_cache and 'symbols' in self._symbols_cache:
                self.logger.info("Using cached symbols for top traded selection")
                return self._symbols_cache['symbols'][:limit]
                
            # Process the markets and select top by turnover
            valid_markets = []
            for market in markets:
                # Ensure market has required fields for sorting
                if not market:
                    continue
                    
                # Look for turnover in various fields
                turnover = 0
                if 'turnover' in market and market['turnover']:
                    turnover = float(market['turnover'])
                elif 'quoteVolume' in market and market['quoteVolume']:
                    turnover = float(market['quoteVolume'])
                    
                # Skip markets with zero turnover
                if turnover <= 0:
                    continue
                    
                # Add turnover for sorting
                market['turnover_for_sorting'] = turnover
                valid_markets.append(market)
                
            # Sort by turnover (descending)
            valid_markets.sort(key=lambda x: x.get('turnover_for_sorting', 0), reverse=True)
            
            # Take top N markets
            top_markets = valid_markets[:limit]
            
            # Calculate total turnover for percentage display
            total_turnover = sum(market.get('turnover_for_sorting', 0) for market in valid_markets)
            
            # Extract symbols and log selections
            result = []
            for market in top_markets:
                symbol = market.get('symbol', '')
                turnover = market.get('turnover_for_sorting', 0)
                percentage = (turnover / total_turnover * 100) if total_turnover > 0 else 0
                
                self.logger.info(f"Selected {symbol} with turnover {turnover:.2f} ({percentage:.2f}%)")
                result.append(symbol)
                
            self.logger.info(f"Retrieved {len(result)} symbols for top traded selection")
            
            # Cache the results for future use
            if result:
                self._top_traded_symbols = result
                self._last_top_traded_update = time.time()
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting top traded symbols: {str(e)}")
            self.logger.error(traceback.format_exc())
            
            # Return cached results if available
            if self._top_traded_symbols:
                self.logger.warning("Returning cached top traded symbols due to error")
                return self._top_traded_symbols[:limit]
                
            # Last resort - return from symbols cache
            if self._symbols_cache and 'symbols' in self._symbols_cache:
                return self._symbols_cache['symbols'][:limit]
                
            # Really last resort - empty list
            return []

    def _normalize_market_data(self, data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """Normalize market data to ensure consistent format regardless of source.
        
        This method handles different exchange data formats and ensures that critical
        fields like volume and turnover are properly extracted or calculated.
        
        Args:
            data: The market data to normalize
            symbol: The symbol this data belongs to
            
        Returns:
            Dict containing normalized market data with consistent field names
        """
        try:
            normalized = data.copy()
            
            # Add symbol if not present
            if 'symbol' not in normalized:
                normalized['symbol'] = symbol
                
            # Extract volume - try multiple possible field names
            volume = None
            volume_field_names = ['volume', 'baseVolume', 'vol', 'amount', 'quoteVolume', 'volume24h']
            
            for field in volume_field_names:
                if field in normalized and normalized[field] is not None:
                    try:
                        volume = float(normalized[field])
                        if volume > 0:
                            normalized['volume'] = volume
                            break
                    except (ValueError, TypeError):
                        continue
                        
            # If volume still not found, check for nested structures
            if volume is None and 'info' in normalized:
                info = normalized['info']
                for field in volume_field_names + ['volume24', 'vol24h']:
                    if field in info and info[field] is not None:
                        try:
                            volume = float(info[field])
                            if volume > 0:
                                normalized['volume'] = volume
                                break
                        except (ValueError, TypeError):
                            continue
                            
            # Extract or calculate turnover (quoteVolume)
            turnover = None
            turnover_field_names = ['turnover', 'quoteVolume', 'volumeUsd', 'notional', 'notionalValue']
            
            for field in turnover_field_names:
                if field in normalized and normalized[field] is not None:
                    try:
                        turnover = float(normalized[field])
                        if turnover > 0:
                            normalized['turnover'] = turnover
                            break
                    except (ValueError, TypeError):
                        continue
                        
            # If turnover not found directly, check nested structures
            if turnover is None and 'info' in normalized:
                info = normalized['info']
                for field in turnover_field_names + ['turnover24h', 'notional_24h']:
                    if field in info and info[field] is not None:
                        try:
                            turnover = float(info[field])
                            if turnover > 0:
                                normalized['turnover'] = turnover
                                break
                        except (ValueError, TypeError):
                            continue
                            
            # If still no turnover but we have volume and last price, calculate it
            if turnover is None and volume is not None and 'last' in normalized and normalized['last'] is not None:
                try:
                    last_price = float(normalized['last'])
                    if last_price > 0:
                        calculated_turnover = volume * last_price
                        normalized['turnover'] = calculated_turnover
                        self.logger.debug(f"Calculated turnover for {symbol}: {calculated_turnover}")
                except (ValueError, TypeError):
                    pass
                    
            # Extract open interest if available
            oi = None
            oi_field_names = ['openInterest', 'oi', 'open_interest']
            
            for field in oi_field_names:
                if field in normalized and normalized[field] is not None:
                    try:
                        oi = float(normalized[field])
                        if oi > 0:
                            normalized['openInterest'] = oi
                            break
                    except (ValueError, TypeError):
                        continue
                        
            # Try to extract from info
            if oi is None and 'info' in normalized:
                info = normalized['info']
                for field in oi_field_names + ['openInterest24h']:
                    if field in info and info[field] is not None:
                        try:
                            oi = float(info[field])
                            if oi > 0:
                                normalized['openInterest'] = oi
                                break
                        except (ValueError, TypeError):
                            continue
            
            # Log the extracted data
            extracted_fields = []
            if 'volume' in normalized:
                extracted_fields.append(f"volume={normalized['volume']}")
            if 'turnover' in normalized:
                extracted_fields.append(f"turnover={normalized['turnover']}")
            if 'openInterest' in normalized:
                extracted_fields.append(f"openInterest={normalized['openInterest']}")
                
            if extracted_fields:
                self.logger.debug(f"Extracted market data for {symbol}: {', '.join(extracted_fields)}")
            else:
                self.logger.warning(f"Could not extract any key metrics for {symbol}")
                
            return normalized
            
        except Exception as e:
            self.logger.error(f"Error normalizing market data for {symbol}: {str(e)}")
            return data  # Return original data if normalization fails