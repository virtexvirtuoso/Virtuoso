#!/usr/bin/env python3
"""Fix data validation errors by adding proper error handling."""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def fix_empty_dataframe_handling():
    """Add better handling for empty DataFrames in confluence analysis."""
    
    file_path = PROJECT_ROOT / "src/analysis/core/confluence.py"
    
    if not file_path.exists():
        print(f"Warning: {file_path} not found")
        return
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add graceful handling for empty DataFrames
    validation_improvement = '''        # Early return with neutral scores for empty data
        if base_df.empty or (ltf_df is not None and ltf_df.empty) or (mtf_df is not None and mtf_df.empty) or (htf_df is not None and htf_df.empty):
            self.logger.warning(f"Empty DataFrame detected - returning neutral scores")
            return self._get_neutral_scores()'''
    
    # Find a good place to insert this (typically after DataFrame validation)
    marker = "def calculate_confluence"
    if marker in content:
        # Insert after the method definition and initial checks
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if marker in line:
                # Find the first validation section
                for j in range(i, min(i + 50, len(lines))):
                    if "validation" in lines[j].lower() or "validate" in lines[j].lower():
                        # Insert our improvement after validation
                        indent = "        "  # Adjust based on actual indentation
                        lines.insert(j + 1, validation_improvement)
                        break
                break
        content = '\n'.join(lines)
    
    # Add the neutral scores method if it doesn't exist
    if "_get_neutral_scores" not in content:
        neutral_method = '''
    def _get_neutral_scores(self) -> Dict[str, Any]:
        """Return neutral scores when data is unavailable."""
        return {
            'technical': {'score': 50.0, 'interpretation': 'No data available'},
            'volume': {'score': 50.0, 'interpretation': 'No data available'},
            'orderbook': {'score': 50.0, 'interpretation': 'No data available'},
            'orderflow': {'score': 50.0, 'interpretation': 'No data available'},
            'sentiment': {'score': 50.0, 'interpretation': 'No data available'},
            'price_structure': {'score': 50.0, 'interpretation': 'No data available'},
            'overall': {
                'score': 50.0,
                'signal': 'NEUTRAL',
                'confidence': 0.0,
                'interpretation': 'Insufficient data for analysis'
            }
        }'''
        
        # Add before the last method or at the end of the class
        class_end = content.rfind('\nclass')
        if class_end > 0:
            # Find the end of the confluence class
            next_class = content.find('\nclass', class_end + 1)
            if next_class > 0:
                content = content[:next_class] + neutral_method + '\n' + content[next_class:]
            else:
                content = content + neutral_method
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✓ Added graceful handling for empty DataFrames")

def fix_orderbook_validation():
    """Fix orderbook validation errors."""
    
    # Search for orderbook-related files
    import glob
    orderbook_files = glob.glob(str(PROJECT_ROOT / "src/**/*orderbook*.py"), recursive=True)
    
    for file_path in orderbook_files:
        if "indicators" in file_path:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Add validation for empty orderbook
            if "Empty orderbook data" not in content:
                validation_code = '''        # Validate orderbook has data
        if not bids or not asks:
            self.logger.warning("Empty orderbook data - returning neutral score")
            return {
                'score': 50.0,
                'interpretation': 'No orderbook data available',
                'bid_count': 0,
                'ask_count': 0,
                'total_bid_volume': 0.0,
                'total_ask_volume': 0.0
            }'''
                
                # Find calculate method
                marker = "def calculate"
                if marker in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if marker in line and "orderbook" in lines[i:i+10]:
                            # Insert validation after method definition
                            for j in range(i, min(i + 20, len(lines))):
                                if ":" in lines[j] and "def" in lines[j]:
                                    lines.insert(j + 1, validation_code)
                                    break
                            break
                    content = '\n'.join(lines)
                    
                    with open(file_path, 'w') as f:
                        f.write(content)
                    
                    print(f"✓ Added orderbook validation to {Path(file_path).name}")

def add_market_data_validation():
    """Add validation in market data manager."""
    
    file_path = PROJECT_ROOT / "src/core/market/market_data_manager.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add validation helper method
    validation_helper = '''
    def _validate_market_data(self, data: Dict[str, Any], symbol: str) -> bool:
        """Validate market data before processing.
        
        Returns:
            bool: True if data is valid, False otherwise
        """
        if not data:
            self.logger.warning(f"No market data for {symbol}")
            return False
            
        # Check for required fields
        required_fields = ['ticker', 'timestamp']
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"Missing required field '{field}' for {symbol}")
                return False
        
        # Validate ticker data
        ticker = data.get('ticker', {})
        if not ticker or ticker.get('last_price', 0) <= 0:
            self.logger.warning(f"Invalid ticker data for {symbol}")
            return False
            
        return True'''
    
    # Add the method if it doesn't exist
    if "_validate_market_data" not in content:
        # Find a good place to insert (after other helper methods)
        marker = "def _update_open_interest_history"
        if marker in content:
            pos = content.find(marker)
            if pos > 0:
                # Find the end of the previous method
                prev_method_end = content.rfind('\n\n', 0, pos)
                if prev_method_end > 0:
                    content = content[:prev_method_end] + '\n' + validation_helper + '\n' + content[prev_method_end:]
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        print("✓ Added market data validation helper")

def main():
    """Apply all data validation fixes."""
    print("Fixing data validation errors...")
    
    # Apply fixes
    fix_empty_dataframe_handling()
    fix_orderbook_validation()
    add_market_data_validation()
    
    print("\n✅ All data validation fixes applied!")
    print("\nThese changes will:")
    print("- Return neutral scores instead of errors for empty data")
    print("- Validate data before processing")
    print("- Prevent cascading errors from missing data")

if __name__ == "__main__":
    main()