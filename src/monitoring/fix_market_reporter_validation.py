#!/usr/bin/env python3
"""
Fix field mismatches and validation issues in market_reporter.py

This script fixes:
1. Changes 'smi_value' to 'index' in smart money calculation
2. Improves validation logic to be more intelligent
3. Ensures data structure consistency
"""

import re
import shutil
from pathlib import Path

def fix_market_reporter():
    """Fix the market reporter validation and field issues."""
    
    # Create backup
    original_file = Path("src/monitoring/market_reporter.py")
    backup_file = Path("src/monitoring/market_reporter.py.backup_validation_fix")
    
    if original_file.exists():
        shutil.copy2(original_file, backup_file)
        print(f"Created backup: {backup_file}")
    
    # Read the original file
    with open(original_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Change 'smi_value' to 'index' in smart money calculation
    print("Fixing smart money index field names...")
    
    # Replace the initial result structure
    content = content.replace(
        "'smi_value': 50,  # Default neutral value",
        "'index': 50,  # Default neutral value (changed from smi_value)"
    )
    
    # Replace variable assignments and references
    content = re.sub(
        r'smi_value = buy_ratio \* 100\s*\n\s*result\[\'smi_value\'\] = smi_value',
        'index_value = buy_ratio * 100\n                            result[\'index\'] = index_value',
        content
    )
    
    # Replace conditional checks
    content = re.sub(
        r'if smi_value > 60:\s*\n\s*result\[\'trend\'\] = \'bullish\'\s*\n\s*elif smi_value < 40:\s*\n\s*result\[\'trend\'\] = \'bearish\'',
        'if index_value > 60:\n                                result[\'trend\'] = \'bullish\'\n                            elif index_value < 40:\n                                result[\'trend\'] = \'bearish\'',
        content
    )
    
    # Replace value references in change entries
    content = content.replace(
        "'value': smi_value,",
        "'value': index_value,"
    )
    
    # Replace the check for default value
    content = content.replace(
        "if result.get('smi_value', 50) == 50:",
        "if result.get('index', 50) == 50:"
    )
    
    # Replace the final error return structure
    content = content.replace(
        "'smi_value': 50,",
        "'index': 50,"
    )
    
    # Fix 2: Improve validation logic
    print("Improving validation logic...")
    
    # Replace the problematic validation condition
    old_validation = """            # If section exists but is empty (None or empty dict/list)
            elif not validated[section]:
                self.logger.warning(f"Empty section '{section}' in report, using fallback")
                validated[section] = self._get_fallback_content(section)
                section_statuses[section] = "Added fallback (empty section)" """
    
    new_validation = """            # Check if section has meaningful data based on its type
            elif self._is_section_invalid(section, validated[section]):
                self.logger.warning(f"Invalid or empty section '{section}' in report, using fallback")
                validated[section] = self._get_fallback_content(section)
                section_statuses[section] = "Added fallback (invalid section)" """
    
    content = content.replace(old_validation, new_validation)
    
    # Add the new validation helper method before _get_fallback_content
    validation_helper = '''
    def _is_section_invalid(self, section: str, section_data: Dict[str, Any]) -> bool:
        """Check if a section is invalid based on its specific requirements."""
        if section_data is None:
            return True
        
        if not isinstance(section_data, dict):
            return True
            
        # Check section-specific requirements
        if section == 'market_overview':
            # Market overview should have regime field
            return not section_data.get('regime') or section_data.get('regime') == 'UNKNOWN'
            
        elif section == 'futures_premium':
            # Futures premium should have premiums dict with data or timestamp
            premiums = section_data.get('premiums', {})
            timestamp = section_data.get('timestamp')
            return not premiums and not timestamp
            
        elif section == 'smart_money_index':
            # Smart money index should have either 'index' or 'smi_value' field
            has_index = 'index' in section_data
            has_smi_value = 'smi_value' in section_data  
            has_timestamp = 'timestamp' in section_data
            return not (has_index or has_smi_value) and not has_timestamp
            
        elif section == 'whale_activity':
            # Whale activity should have whale_activity dict or timestamp
            whale_data = section_data.get('whale_activity', {})
            timestamp = section_data.get('timestamp')
            return not whale_data and not timestamp
            
        elif section == 'performance_metrics':
            # Performance metrics should have metrics dict or timestamp
            metrics = section_data.get('metrics', {})
            timestamp = section_data.get('timestamp')
            return not metrics and not timestamp
            
        return False
'''
    
    # Insert the helper method before _get_fallback_content
    content = content.replace(
        "    def _get_fallback_content(self, section_name: str) -> Dict[str, Any]:",
        validation_helper + "\n    def _get_fallback_content(self, section_name: str) -> Dict[str, Any]:"
    )
    
    # Fix 3: Update smart money index normalization to handle both field names
    print("Updating smart money index normalization...")
    
    # Find and replace the smart money index normalization section
    smi_normalization_old = """        elif section == 'smart_money_index':
            # Ensure required fields exist
            if 'current_value' not in normalized and 'value' in normalized:
                normalized['current_value'] = normalized['value']
                
            if 'current_value' not in normalized and 'index' in normalized:
                normalized['current_value'] = normalized['index']
                
            if 'current_value' not in normalized:
                normalized['current_value'] = 50.0  # Neutral value
                
            # Make sure index field exists too for template compatibility
            if 'index' not in normalized:
                normalized['index'] = normalized['current_value']"""
    
    smi_normalization_new = """        elif section == 'smart_money_index':
            # Handle field name transitions: smi_value -> index
            if 'smi_value' in normalized and 'index' not in normalized:
                normalized['index'] = normalized['smi_value']
                
            # Ensure required fields exist
            if 'current_value' not in normalized and 'value' in normalized:
                normalized['current_value'] = normalized['value']
                
            if 'current_value' not in normalized and 'index' in normalized:
                normalized['current_value'] = normalized['index']
                
            if 'current_value' not in normalized:
                normalized['current_value'] = 50.0  # Neutral value
                
            # Make sure index field exists too for template compatibility
            if 'index' not in normalized:
                normalized['index'] = normalized['current_value']"""
    
    content = content.replace(smi_normalization_old, smi_normalization_new)
    
    # Write the fixed content
    with open(original_file, 'w') as f:
        f.write(content)
    
    print(f"Market reporter validation fixes applied!")
    print(f"Original file backed up to: {backup_file}")
    
    # Summary of changes
    print("\nChanges made:")
    print("1. Changed 'smi_value' to 'index' in smart money calculation")
    print("2. Improved validation logic to check meaningful data")
    print("3. Added field name transition handling")
    print("4. Enhanced section-specific validation")

if __name__ == "__main__":
    fix_market_reporter() 