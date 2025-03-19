#!/usr/bin/env python3
"""
Script to update the log_analysis_result method in monitor.py to use the new formatting
"""

import re
import os
import shutil
from datetime import datetime

def backup_file(file_path):
    """Create a backup of the file with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.bak_{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def update_monitor_file():
    """Update the log_analysis_result method in monitor.py"""
    monitor_path = "src/monitoring/monitor.py"
    
    # Create a backup of the file
    backup_file(monitor_path)
    
    # Read the current content
    with open(monitor_path, "r") as f:
        content = f.read()
    
    # The new implementation of log_analysis_result
    new_method = '''    def log_analysis_result(self, analysis_result, symbol_str):
        """Log the analysis result for a symbol with enhanced formatting.
        
        This method uses the AnalysisFormatter to create a visually appealing
        representation of the analysis results.
        
        Args:
            analysis_result (dict): The analysis result dictionary
            symbol_str (str): Symbol being analyzed
        """
        if not analysis_result:
            self.logger.info(f"No analysis results available for {symbol_str}")
            return
        
        # Use the formatter utility for better visual output
        formatter = AnalysisFormatter()
        
        # Get the formatted analysis result
        formatted_result = formatter.format_analysis_result(analysis_result, symbol_str)
        
        # Log the formatted result
        self.logger.info(f"\\n{formatted_result}")
        
        # Also log a compact version of component scores for easy reference
        components = analysis_result.get('components', {})
        if components:
            component_breakdown = formatter.format_component_breakdown(components, analysis_result.get('results', {}))
            self.logger.debug(f"\\nComponent Breakdown:\\n{component_breakdown}")'''
    
    # Pattern to match the log_analysis_result method
    pattern = r'    def log_analysis_result\(self, analysis_result, symbol_str\):.*?(?=    def|\Z)'
    
    # Replace the method in the content
    modified_content = re.sub(pattern, new_method, content, flags=re.DOTALL)
    
    # Write the modified content back to the file
    with open(monitor_path, "w") as f:
        f.write(modified_content)
    
    print(f"Successfully updated log_analysis_result method in {monitor_path}")

if __name__ == "__main__":
    update_monitor_file() 