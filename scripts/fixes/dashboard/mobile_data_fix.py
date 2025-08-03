"""Fix for mobile-data endpoint to show confluence scores"""

# Add this code after line 566 in dashboard.py, before the top movers section:

                # If no confluence scores from signals, try to get from confluence cache
                if not confluence_scores and hasattr(integration, '_confluence_cache'):
                    logger.info("No signals found, getting data from confluence cache")
                    for symbol, cache_data in integration._confluence_cache.items():
                        # Skip if data is too old (more than 60 seconds)
                        if time.time() - cache_data.get('timestamp', 0) > 60:
                            continue
                            
                        score = cache_data.get('score', 50)
                        components = cache_data.get('components', {})
                        
                        # Try to get market data for price/volume
                        price = 0
                        change_24h = 0
                        volume_24h = 0
                        
                        # You could fetch this from market data or Bybit API
                        # For now, we'll use placeholder values
                        
                        confluence_scores.append({
                            "symbol": symbol,
                            "score": round(score, 2),
                            "price": price,
                            "change_24h": change_24h,
                            "volume_24h": volume_24h,
                            "components": {
                                "technical": round(components.get('technical', 50), 2),
                                "volume": round(components.get('volume', 50), 2),
                                "orderflow": round(components.get('orderflow', 50), 2),
                                "sentiment": round(components.get('sentiment', 50), 2),
                                "orderbook": round(components.get('orderbook', 50), 2),
                                "price_structure": round(components.get('price_structure', 50), 2)
                            }
                        })
                    
                    # Sort by score descending
                    confluence_scores.sort(key=lambda x: x['score'], reverse=True)
                    confluence_scores = confluence_scores[:15]  # Limit to top 15
                    
                response["confluence_scores"] = confluence_scores