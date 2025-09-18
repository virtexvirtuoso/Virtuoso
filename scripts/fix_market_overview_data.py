#!/usr/bin/env python3
"""
Fix market_overview to properly include gainers/losers data
"""

import os
import re

def fix_dashboard_integration():
    """Fix the dashboard integration to properly calculate gainers/losers"""
    
    dashboard_integration_path = "src/dashboard/dashboard_integration.py"
    
    if not os.path.exists(dashboard_integration_path):
        print(f"Error: {dashboard_integration_path} not found")
        return False
    
    with open(dashboard_integration_path, 'r') as f:
        content = f.read()
    
    # Find the _update_market_overview method
    pattern = r'(async def _update_market_overview\(self\):.*?try:)(.*?)(self\._dashboard_data\[\'market_overview\'\] = overview)'
    
    replacement_code = r'''\1
            # Calculate gainers and losers from top movers data
            top_movers = self._dashboard_data.get('top_movers', {})
            gainers_list = top_movers.get('gainers', [])
            losers_list = top_movers.get('losers', [])
            
            # Also check signals for price changes
            signals = self._dashboard_data.get('signals', [])
            gainers_count = 0
            losers_count = 0
            
            # Count from top movers
            for mover in gainers_list:
                if mover.get('change_24h', 0) > 0:
                    gainers_count += 1
            
            for mover in losers_list:
                if mover.get('change_24h', 0) < 0:
                    losers_count += 1
            
            # If no movers data, estimate from signals
            if gainers_count == 0 and losers_count == 0:
                for signal in signals:
                    if signal.get('type') == 'BUY':
                        gainers_count += 1
                    elif signal.get('type') == 'SELL':
                        losers_count += 1
            
            overview = {
                'total_symbols': len(getattr(self.monitor, 'symbols', [])),
                'active_signals': len(self._dashboard_data.get('signals', [])),
                'strong_signals': len([s for s in self._dashboard_data.get('signals', []) if s.get('strength') == 'strong']),
                'alpha_opportunities': len(self._dashboard_data.get('alpha_opportunities', [])),
                'total_alerts': len(self._dashboard_data.get('alerts', [])),
                'gainers': gainers_count,
                'losers': losers_count,
                'neutral': max(0, len(getattr(self.monitor, 'symbols', [])) - gainers_count - losers_count),
                'market_regime': self._calculate_market_regime(gainers_count, losers_count),
                'sentiment': {
                    'label': 'Bulls Leading' if gainers_count > losers_count else 'Bears Leading' if losers_count > gainers_count else 'Neutral',
                    'percentage': round((gainers_count / (gainers_count + losers_count) * 100) if (gainers_count + losers_count) > 0 else 50, 1),
                    'rising_count': gainers_count,
                    'falling_count': losers_count,
                    'breadth_indicator': 'BULLISH' if gainers_count > losers_count * 1.1 else 'BEARISH' if losers_count > gainers_count * 1.1 else 'NEUTRAL'
                },
                'timestamp': int(time.time() * 1000)
            }
            
            \3'''
    
    # Apply the fix
    content = re.sub(pattern, replacement_code, content, flags=re.DOTALL)
    
    # Add helper method for market regime if not exists
    if '_calculate_market_regime' not in content:
        # Add the method after _update_market_overview
        helper_method = '''
    
    def _calculate_market_regime(self, gainers: int, losers: int) -> str:
        """Calculate market regime based on gainers/losers ratio"""
        if gainers + losers == 0:
            return "NEUTRAL"
        
        ratio = gainers / (gainers + losers)
        if ratio > 0.6:
            return "BULLISH"
        elif ratio < 0.4:
            return "BEARISH"
        else:
            return "NEUTRAL"
'''
        # Insert after _update_market_overview method
        insert_pos = content.find('async def _extract_confluence_score')
        if insert_pos > 0:
            content = content[:insert_pos] + helper_method + '\n' + content[insert_pos:]
    
    # Write the fixed content
    with open(dashboard_integration_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed {dashboard_integration_path}")
    return True

def fix_market_data_manager():
    """Ensure market_data_manager properly returns gainers/losers"""
    
    market_data_manager_path = "src/core/market/market_data_manager.py"
    
    if not os.path.exists(market_data_manager_path):
        print(f"Warning: {market_data_manager_path} not found")
        return False
    
    with open(market_data_manager_path, 'r') as f:
        content = f.read()
    
    # Check if get_market_overview exists and returns proper data
    if 'async def get_market_overview' in content:
        print(f"{market_data_manager_path} already has get_market_overview")
    else:
        # Add the method if it doesn't exist
        method_code = '''
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get market overview with gainers/losers"""
        try:
            gainers = []
            losers = []
            
            # Get price changes for all symbols
            for symbol in self.symbols[:30]:  # Limit to first 30 symbols
                try:
                    ticker = await self.get_ticker(symbol)
                    if ticker and 'percentage' in ticker:
                        change = ticker['percentage']
                        if change > 0:
                            gainers.append({
                                'symbol': symbol,
                                'change': change,
                                'price': ticker.get('last', 0)
                            })
                        elif change < 0:
                            losers.append({
                                'symbol': symbol,
                                'change': change,
                                'price': ticker.get('last', 0)
                            })
                except Exception:
                    continue
            
            # Sort by change percentage
            gainers.sort(key=lambda x: x['change'], reverse=True)
            losers.sort(key=lambda x: x['change'])
            
            return {
                'gainers': gainers[:5],  # Top 5 gainers
                'losers': losers[:5],    # Top 5 losers
                'total_gainers': len(gainers),
                'total_losers': len(losers),
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting market overview: {e}")
            return {}
'''
        # Add before the last method or at the end of class
        class_end = content.rfind('\n\nclass ')
        if class_end == -1:
            class_end = len(content) - 1
        
        content = content[:class_end] + method_code + content[class_end:]
        
        with open(market_data_manager_path, 'w') as f:
            f.write(content)
        
        print(f"Added get_market_overview to {market_data_manager_path}")
    
    return True

if __name__ == "__main__":
    print("Fixing market overview data collection...")
    
    success = True
    success = fix_dashboard_integration() and success
    success = fix_market_data_manager() and success
    
    if success:
        print("\nMarket overview fixes applied successfully!")
        print("The dashboard should now properly display gainers/losers data")
    else:
        print("\nSome fixes could not be applied. Please check the errors above.")