#!/usr/bin/env python3
"""
Script to deprecate legacy formatter methods in monitor.py
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

def add_deprecation_note(content, method_name):
    """Add deprecation note to a method."""
    # Define the pattern to match the method definition
    pattern = rf"(\s+)def {method_name}\(self, analysis_result, symbol_str\):"
    
    # Define the replacement with deprecation note
    replacement = r"""\1def {}(self, analysis_result, symbol_str):
\1    """
    replacement += r'''"""
\1    Legacy format analysis results method.
\1    
\1    DEPRECATED: This method is kept only for fallback purposes.
\1    The new formatting system in core.formatting should be used instead.
\1    
\1    Args:
\1        analysis_result (dict): The analysis result dictionary
\1        symbol_str (str): The symbol being analyzed
\1        
\1    Returns:
\1        str: Formatted analysis output
\1    """'''
    
    replacement = replacement.format(method_name)
    
    # Replace the method definition in the content
    modified_content = re.sub(pattern, replacement, content, count=1)
    
    # If no replacement was made, the content will be unchanged
    if modified_content == content:
        print(f"Warning: Couldn't find method {method_name} to add deprecation note")
        return content
    
    return modified_content

def remove_duplicate_imports(content):
    """Remove duplicate imports for formatting utilities."""
    # Count occurrences of the import statement
    import_pattern = r"from core\.formatting import AnalysisFormatter, format_analysis_result"
    import_count = len(re.findall(import_pattern, content))
    
    # If there are multiple occurrences, keep only the first one and add a comment
    if import_count > 1:
        print(f"Found {import_count} duplicate imports, keeping only the first one")
        # Find the first occurrence
        match = re.search(import_pattern, content)
        if match:
            # Replace the first occurrence with a commented version
            commented_import = "# Import formatting utilities (single import)\n" + match.group(0)
            content = content.replace(match.group(0), commented_import, 1)
            
            # Remove all other occurrences
            content = re.sub(import_pattern, "", content)
            
    return content

def consolidate_log_methods(content):
    """Identify and mark duplicate log_analysis_result methods."""
    log_method_pattern = r"(\s+def log_analysis_result\s*\([^)]+\):.*?)(?=\s+def|\s+class|\Z)"
    matches = list(re.finditer(log_method_pattern, content, re.DOTALL))
    
    if len(matches) > 1:
        print(f"Found {len(matches)} implementations of log_analysis_result")
        
        # Add a comment to all but the first implementation
        for i, match in enumerate(matches[1:], 1):
            # Create a replacement that adds a comment before the method
            replacement = f"\n    # DUPLICATE METHOD: This is a duplicate of the log_analysis_result method\n    # in the MarketMonitor class. Consider consolidating these implementations.\n{match.group(0)}"
            content = content.replace(match.group(0), replacement)
    
    return content

def main():
    """Main function to process the monitor.py file."""
    # Define the path to the monitor.py file
    monitor_path = "src/monitoring/monitor.py"
    
    # Create a backup of the file
    backup_file(monitor_path)
    
    # Read the current content
    with open(monitor_path, "r") as f:
        content = f.read()
    
    # Process the content
    content = remove_duplicate_imports(content)
    content = add_deprecation_note(content, "_format_analysis_results")
    content = consolidate_log_methods(content)
    
    # Write the modified content back to the file
    with open(monitor_path, "w") as f:
        f.write(content)
    
    print(f"Successfully updated {monitor_path}")

if __name__ == "__main__":
    main() 