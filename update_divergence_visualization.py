#!/usr/bin/env python3
"""
Update Indicator Classes for Enhanced Divergence Visualization

This script updates the calculate methods in all indicator classes to use the
enhanced divergence visualization features added through the patching mechanism
in src/indicators/__init__.py.
"""

import os
import re
import glob
from typing import Dict, List, Tuple

# Pattern to identify divergence application code
DIVERGENCE_PATTERN = r"""for\s+key,\s*div_info\s+in\s+divergences\.items\(\):
\s+component\s*=\s*div_info\.get\(['"]component['"]\)
\s+if\s+component\s+in\s+component_scores:
\s+# Calculate bonus based on divergence strength and type
\s+strength\s*=\s*div_info\.get\(['"]strength['"]\,\s*0\)
\s+div_type\s*=\s*div_info\.get\(['"]type['"]\,\s*['"]neutral['"]\)
\s+
\s+# Bullish divergence increases score, bearish decreases
\s+bonus\s*=\s*strength\s*\*\s*0\.1\s*\*\s*\(1\s+if\s+div_type\s*==\s*['"]bullish['"]\s+else\s*-1\)
\s+
\s+# Apply bonus with limits
\s+component_scores\[component\]\s*=\s*np\.clip\(component_scores\[component\]\s*\+\s*bonus,\s*0,\s*100\)
\s+
\s+# Store bonus in divergence info for logging
\s+div_info\['bonus'\]\s*=\s*bonus"""

# Replacement code that uses _apply_divergence_bonuses
REPLACEMENT_CODE = """# Apply divergence bonuses using enhanced method
adjusted_scores = self._apply_divergence_bonuses(component_scores, divergences)

# Calculate final score using component weights
final_score = self._compute_weighted_score(adjusted_scores)"""

# Pattern to identify the calculate method return statement
RETURN_PATTERN = r"return\s*{\s*'score':\s*float\(np\.clip\(final_score,\s*0,\s*100\)\),\s*'components':\s*component_scores,"

# Replacement for return statement
RETURN_REPLACEMENT = "return {\n                'score': float(np.clip(final_score, 0, 100)),\n                'components': adjusted_scores,"

# Pattern to identify log_indicator_results call
LOG_PATTERN = r"self\.log_indicator_results\(final_score,\s*component_scores,\s*symbol\)"

# Replacement for log_indicator_results call
LOG_REPLACEMENT = "self.log_indicator_results(final_score, adjusted_scores, symbol)"


def update_file(filepath: str) -> Tuple[bool, str]:
    """
    Update a single indicator file to use enhanced divergence visualization.
    
    Args:
        filepath: Path to the indicator file
        
    Returns:
        Tuple of (success, message)
    """
    # Skip files that don't need updating
    if 'technical_indicators.py' in filepath:
        return True, "Already uses enhanced divergence visualization"
    
    # Read the file
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except Exception as e:
        return False, f"Error reading {filepath}: {str(e)}"
        
    # Check if file contains calculate method
    if 'async def calculate(' not in content and 'def calculate(' not in content:
        return False, f"No calculate method found in {filepath}"
        
    # Replace divergence application code
    updated_content = re.sub(DIVERGENCE_PATTERN, REPLACEMENT_CODE, content, flags=re.MULTILINE)
    
    # Replace return statement
    updated_content = re.sub(RETURN_PATTERN, RETURN_REPLACEMENT, updated_content)
    
    # Replace log_indicator_results call
    updated_content = re.sub(LOG_PATTERN, LOG_REPLACEMENT, updated_content)
    
    # Write the updated content back to the file
    if content != updated_content:
        try:
            with open(filepath, 'w') as f:
                f.write(updated_content)
            return True, "Successfully updated"
        except Exception as e:
            return False, f"Error writing to {filepath}: {str(e)}"
    else:
        return True, "No changes needed"


def main():
    """Main function to update all indicator files."""
    # Get all indicator files
    indicator_dir = os.path.join('src', 'indicators')
    indicator_files = glob.glob(os.path.join(indicator_dir, '*_indicators.py'))
    
    print(f"Found {len(indicator_files)} indicator files to process")
    
    # Update each file
    results = {}
    for filepath in indicator_files:
        filename = os.path.basename(filepath)
        success, message = update_file(filepath)
        results[filename] = {'success': success, 'message': message}
        
    # Print summary
    print("\nUpdate Summary:")
    print("=" * 50)
    for filename, result in results.items():
        status = "SUCCESS" if result['success'] else "FAILED"
        print(f"{filename:<30} {status:<10} {result['message']}")
    print("=" * 50)
    
    # Check if any failures
    failures = [f for f, r in results.items() if not r['success']]
    if failures:
        print(f"\nWARNING: Failed to update {len(failures)} files.")
        print("You might need to manually update these files.")
    else:
        print("\nAll files were successfully processed!")
        print("To see the divergence visualization in action, run your analysis on a symbol ")
        print("with significant timeframe divergences.")


if __name__ == "__main__":
    main() 