"""
Installation script for integrating the enhanced formatting utilities.

This script:
1. Makes a backup of monitor.py
2. Updates monitor.py to use the new formatting utilities
3. Runs a test to verify everything works

The enhanced formatter includes:
- Structured dashboard layout with box-drawing characters
- Color-coded scores and visual gauges
- Trend indicators (↑, →, ↓) showing direction of change
- Detailed component breakdown tables
"""

import os
import sys
import shutil
import re
import logging
import importlib.util
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('formatter_installer')

def backup_file(file_path):
    """Creates a backup of the specified file."""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{file_path}.bak_{timestamp}"
    
    if os.path.exists(file_path):
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup of {file_path} at {backup_path}")
        return True
    else:
        logger.error(f"File {file_path} not found, cannot create backup")
        return False

def update_monitor_file():
    """Updates the monitor.py file to use the new formatting utilities."""
    monitor_path = 'monitoring/monitor.py'
    
    if not os.path.exists(monitor_path):
        monitor_path = os.path.join('src', 'monitoring', 'monitor.py')
        
    if not os.path.exists(monitor_path):
        logger.error(f"Could not find monitor.py. Please check the path.")
        return False
    
    # Create backup
    if not backup_file(monitor_path):
        return False
    
    # Read file content
    with open(monitor_path, 'r') as f:
        content = f.read()
    
    # Import regex pattern
    import_pattern = r'(import\s+[^\n]+\n)+'
    match = re.search(import_pattern, content)
    
    if not match:
        logger.error("Could not find import section in monitor.py")
        return False
    
    # Add import for formatting utilities
    formatter_import = "\nfrom core.formatting import AnalysisFormatter, format_analysis_result\n"
    imports_end = match.end()
    updated_content = content[:imports_end] + formatter_import + content[imports_end:]
    
    # Find and update the log_analysis_result method
    log_method_pattern = r'def\s+log_analysis_result\s*\([^)]+\):.*?(?=\n\s*def|\n\s*class|\Z)'
    match = re.search(log_method_pattern, updated_content, re.DOTALL)
    
    if not match:
        logger.error("Could not find log_analysis_result method in monitor.py")
        return False
    
    # Check if we need to update for trend tracking
    should_update_for_trends = "previous_analysis_results" not in match.group(0)
    
    if should_update_for_trends:
        logger.info("Updating log_analysis_result to support trend indicators")
        
        # New implementation of log_analysis_result with trend tracking
        new_method = '''
    def log_analysis_result(self, analysis_result, symbol_str):
        """
        Log analysis results with enhanced formatting.
        
        Args:
            analysis_result (dict): The analysis result dictionary
            symbol_str (str): The symbol being analyzed
        """
        if not analysis_result:
            self.logger.warning(f"No analysis results available for {symbol_str}")
            return
        
        try:
            # Get previous analysis result for trends if available
            previous_result = None
            if hasattr(self, '_previous_analysis_results') and symbol_str in self._previous_analysis_results:
                previous_result = self._previous_analysis_results[symbol_str]
            
            # Use the new formatting utility with trends
            formatted_analysis = format_analysis_result(
                analysis_result, 
                symbol_str,
                previous_result=previous_result
            )
            
            # Store current result for future trend comparison
            if not hasattr(self, '_previous_analysis_results'):
                self._previous_analysis_results = {}
            self._previous_analysis_results[symbol_str] = analysis_result
        except Exception as e:
            # Fall back to original formatter if there's an error
            self.logger.warning(f"Error using new formatter: {str(e)}. Falling back to original.")
            formatted_analysis = self._format_analysis_results(analysis_result, symbol_str)
            
        self.logger.info(formatted_analysis)
    '''
    else:
        # Standard implementation without trend tracking
        new_method = '''
    def log_analysis_result(self, analysis_result, symbol_str):
        """
        Log analysis results with enhanced formatting.
        
        Args:
            analysis_result (dict): The analysis result dictionary
            symbol_str (str): The symbol being analyzed
        """
        if not analysis_result:
            self.logger.warning(f"No analysis results available for {symbol_str}")
            return
        
        try:
            # Use the new formatting utility
            formatted_analysis = format_analysis_result(analysis_result, symbol_str)
        except Exception as e:
            # Fall back to original formatter if there's an error
            self.logger.warning(f"Error using new formatter: {str(e)}. Falling back to original.")
            formatted_analysis = self._format_analysis_results(analysis_result, symbol_str)
            
        self.logger.info(formatted_analysis)
    '''
    
    # Replace the old method with the new one
    updated_content = updated_content.replace(match.group(0), new_method.strip())
    
    # Write updated content back to file
    with open(monitor_path, 'w') as f:
        f.write(updated_content)
    
    logger.info(f"Successfully updated {monitor_path} to use new formatting utilities")
    return True

def verify_installation():
    """Verify that the installation was successful."""
    # Check if the formatting module can be imported
    try:
        from core.formatting import AnalysisFormatter
        logger.info("Successfully imported AnalysisFormatter from core.formatting")
        
        # Check if trend indicators are supported
        has_trend_indicators = hasattr(AnalysisFormatter, 'get_trend_indicator')
        if has_trend_indicators:
            logger.info("Verified trend indicators support")
        else:
            logger.warning("Trend indicators not found in the formatter")
    except ImportError:
        logger.error("Failed to import AnalysisFormatter. Make sure the module is in the correct path.")
        return False
    
    # Generate a sample analysis result
    sample_data = {
        'score': 65.5,
        'reliability': 0.9,
        'components': {
            'technical': 75.0,
            'volume': 60.0,
            'orderbook': 40.0,
            'orderflow': 55.0,
            'sentiment': 50.0,
            'price_structure': 45.0
        },
        'results': {
            'technical': {
                'components': {
                    'rsi': 70.5,
                    'macd': 65.2,
                    'ao': 80.1,
                }
            }
        }
    }
    
    # Test the formatter
    try:
        # Test with trend indicators if available
        if has_trend_indicators:
            # Create a slightly different previous result
            previous_data = {
                'score': 62.0,
                'components': {
                    'technical': 70.0,
                    'volume': 55.0,
                    'orderbook': 42.0,
                    'orderflow': 53.0,
                    'sentiment': 52.0,
                    'price_structure': 48.0
                }
            }
            
            formatted_output = AnalysisFormatter.format_analysis_result(
                sample_data, 
                'BTCUSDT',
                previous_result=previous_data
            )
        else:
            formatted_output = AnalysisFormatter.format_analysis_result(sample_data, 'BTCUSDT')
            
        logger.info("Successfully generated formatted output.")
        
        # Display a preview of the formatted output (first few lines)
        preview_lines = formatted_output.split('\n')[:10]
        preview_text = '\n'.join(preview_lines)
        logger.info(f"\nSample Output Preview:\n{preview_text}")
        
        # Verify detailed components are included
        has_detailed_components = "DETAILED COMPONENT BREAKDOWN" in formatted_output
        if has_detailed_components:
            logger.info("Verified detailed component breakdown support")
        else:
            logger.warning("Detailed component breakdowns not found in output")
        
        return True
    except Exception as e:
        logger.error(f"Error generating formatted output: {str(e)}")
        logger.error(f"Stack trace: {sys.exc_info()[2]}")
        return False

def copy_readme():
    """Copy the README file to a more visible location."""
    readme_path = os.path.join('src', 'core', 'README_formatting.md')
    if os.path.exists(readme_path):
        dest_path = 'README_formatting.md'
        shutil.copy2(readme_path, dest_path)
        logger.info(f"Copied README to {dest_path}")
        return True
    else:
        logger.warning(f"README file not found at {readme_path}")
        return False

def check_demo_script():
    """Check if the demo script exists and is up to date."""
    demo_path = os.path.join('src', 'demo_formatting.py')
    if os.path.exists(demo_path):
        logger.info(f"Demo script found at {demo_path}")
        return True
    else:
        logger.warning(f"Demo script not found at {demo_path}")
        return False

def main():
    logger.info("Starting installation of enhanced formatting utilities")
    logger.info("This includes trend indicators and detailed component breakdowns")
    
    # Update monitor.py
    if not update_monitor_file():
        logger.error("Failed to update monitor.py")
        return 1
    
    # Verify installation
    if not verify_installation():
        logger.warning("Installation verification failed")
        return 1
    
    # Copy README
    copy_readme()
    
    # Check demo script
    check_demo_script()
    
    logger.info("Installation completed successfully!")
    logger.info("You can now run the demo_formatting.py script to test the new formatting")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 