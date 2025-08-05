#!/usr/bin/env python3
"""
Quick fix for syntax error in market_reporter.py
"""

def fix_syntax_error():
    """Fix the syntax error by moving premium calculation inside try block"""
    
    # Read the file
    with open('src/monitoring/market_reporter.py', 'r') as f:
        content = f.read()
    
    # Find the problematic section and fix it
    # The issue is that premium calculation is outside try block but before except
    
    # Remove the misplaced premium calculation
    lines_to_remove = [
        "                    # Calculate premium if we have valid prices",
        "                    if mark_price and mark_price > 0 and (index_price and index_price > 0):",
        "                        premium = ((mark_price - index_price) / index_price) * 100",
        "                        ",
        "                        # Determine premium type",
        "                        premium_type = \"📉 Backwardation\" if premium < 0 else \"📈 Contango\"",
        "                        ",
        "                        premiums[symbol] = {",
        "                            'premium': f\"{premium:.4f}%\",",
        "                            'premium_value': premium,",
        "                            'premium_type': premium_type,",
        "                            'mark_price': mark_price,",
        "                            'index_price': index_price,",
        "                            'last_price': last_price,",
        "                            'quarterly_price': quarterly_price,",
        "                            'quarterly_basis': f\"{quarterly_basis:.4f}%\",",
        "                            'timestamp': int(datetime.now().timestamp() * 1000)",
        "                        }",
        "                    else:",
        "                        self.logger.warning(f\"Missing price data for futures premium: {symbol} (mark: {mark_price}, index: {index_price})\")",
        "                        failed_symbols.append(symbol)",
        "                        "
    ]
    
    for line in lines_to_remove:
        content = content.replace(line + "\n", "")
    
    # Find the right place to insert the premium calculation (inside the try block)
    # Look for the quarterly futures section and add premium calculation after it
    
    insertion_point = "                                    quarterly_basis = ((quarterly_price - index_price) / index_price) * 100"
    
    premium_calculation = """
                    
                    # Calculate premium if we have valid prices
                    if mark_price and mark_price > 0 and (index_price and index_price > 0):
                        premium = ((mark_price - index_price) / index_price) * 100
                        
                        # Determine premium type
                        premium_type = "📉 Backwardation" if premium < 0 else "📈 Contango"
                        
                        premiums[symbol] = {
                            'premium': f"{premium:.4f}%",
                            'premium_value': premium,
                            'premium_type': premium_type,
                            'mark_price': mark_price,
                            'index_price': index_price,
                            'last_price': last_price,
                            'quarterly_price': quarterly_price,
                            'quarterly_basis': f"{quarterly_basis:.4f}%",
                            'timestamp': int(datetime.now().timestamp() * 1000)
                        }
                    else:
                        self.logger.warning(f"Missing price data for futures premium: {symbol} (mark: {mark_price}, index: {index_price})")
                        failed_symbols.append(symbol)"""
    
    if insertion_point in content:
        content = content.replace(insertion_point, insertion_point + premium_calculation)
        print("✅ Fixed syntax error by moving premium calculation inside try block")
    else:
        print("❌ Could not find insertion point")
        return False
    
    # Write the fixed content back
    with open('src/monitoring/market_reporter.py', 'w') as f:
        f.write(content)
    
    return True

if __name__ == "__main__":
    success = fix_syntax_error()
    if success:
        print("✅ Syntax error fixed successfully")
    else:
        print("❌ Failed to fix syntax error") 