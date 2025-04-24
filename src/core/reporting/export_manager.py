"""
Export Manager Module

This module handles the export of trading data to various formats, 
including JSON files and PDF reports with charts.
"""

import os
import json
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import traceback

# Import the PDF generator
from src.core.reporting.pdf_generator import PDFGenerator

# Set up logging
logger = logging.getLogger(__name__)

class ExportManager:
    """
    Manages the export of trading data to various formats.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the Export Manager with configuration options.
        
        Args:
            config: Configuration dictionary with export settings
        """
        self.config = config or {}
        
        # Setup export directories
        self.export_dir = self.config.get('export_dir', 'exports')
        self.json_dir = os.path.join(self.export_dir, 'json')
        self.pdf_dir = os.path.join(self.export_dir, 'pdf')
        
        # Ensure export directories exist
        os.makedirs(self.json_dir, exist_ok=True)
        os.makedirs(self.pdf_dir, exist_ok=True)
        
        # Initialize PDF generator
        pdf_config = self.config.get('pdf', {})
        pdf_config['reports_dir'] = self.pdf_dir
        self.pdf_generator = PDFGenerator(config=pdf_config)
        
        logger.info("ExportManager initialized with export directory: %s", self.export_dir)
    
    def export_signal_data(self, 
                          symbol: str, 
                          signal_type: str, 
                          price_data: pd.DataFrame,
                          analysis_data: Dict,
                          components: Dict = None,
                          entry_exit: Dict = None,
                          formats: List[str] = None) -> Dict[str, str]:
        """
        Export signal data to specified formats.
        
        Args:
            symbol: Trading pair symbol
            signal_type: Type of signal (BUY, SELL, NEUTRAL)
            price_data: DataFrame with OHLCV data for charting
            analysis_data: Dictionary containing analysis results
            components: Dictionary of signal components and their scores (optional)
            entry_exit: Dictionary with entry/exit levels and risk management info (optional)
            formats: List of export formats ('json', 'pdf'). Defaults to both if None.
            
        Returns:
            Dict[str, str]: Dictionary with paths to exported files by format
        """
        if formats is None:
            formats = ['json', 'pdf']
        
        results = {}
        
        try:
            # Prepare signal data dictionary for export
            signal_data = {
                'symbol': symbol,
                'signal_type': signal_type,
                'timestamp': datetime.now().isoformat(),
                'analysis': analysis_data
            }
            
            # Add components if available
            if components:
                signal_data['components'] = components
                
            # Add entry/exit if available
            if entry_exit:
                signal_data['entry_exit'] = entry_exit
            
            # Export to each format
            if 'json' in formats:
                json_path = self._export_to_json(signal_data)
                if json_path:
                    results['json'] = json_path
            
            if 'pdf' in formats:
                try:
                    pdf_path = self.pdf_generator.generate_report(
                        symbol=symbol,
                        signal_type=signal_type,
                        price_data=price_data,
                        analysis_data=analysis_data,
                        components=components,
                        entry_exit=entry_exit
                    )
                    if pdf_path:
                        results['pdf'] = pdf_path
                except Exception as e:
                    logger.error(f"Error generating PDF report: {str(e)}", exc_info=True)
            
            logger.info(f"Exported signal data for {symbol} to formats: {list(results.keys())}")
            return results
            
        except Exception as e:
            logger.error(f"Error exporting signal data: {str(e)}", exc_info=True)
            return results
    
    def _export_to_json(self, data: Dict) -> str:
        """
        Export data to a JSON file.
        
        Args:
            data: Dictionary containing data to export
            
        Returns:
            str: Path to the exported JSON file
        """
        try:
            # Extract key elements for filename
            symbol = data.get('symbol', 'unknown')
            signal_type = data.get('signal_type', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create filename
            filename = f"{symbol}_{signal_type}_{timestamp}.json"
            filepath = os.path.join(self.json_dir, filename)
            
            # Write JSON file
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Exported JSON file: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting to JSON: {str(e)}", exc_info=True)
            return ""
    
    def get_export_history(self, symbol: str = None, format_type: str = None, 
                         max_items: int = 100) -> List[Dict]:
        """
        Get a list of previously exported files.
        
        Args:
            symbol: Filter by symbol (optional)
            format_type: Filter by format type ('json' or 'pdf') (optional)
            max_items: Maximum number of items to return
            
        Returns:
            List[Dict]: List of export records with metadata
        """
        exports = []
        
        try:
            # Determine which directories to scan
            dirs_to_scan = []
            if format_type == 'json' or format_type is None:
                dirs_to_scan.append(('json', self.json_dir))
            if format_type == 'pdf' or format_type is None:
                dirs_to_scan.append(('pdf', self.pdf_dir))
            
            # Scan each directory
            for fmt, directory in dirs_to_scan:
                if not os.path.exists(directory):
                    continue
                
                for filename in os.listdir(directory):
                    # Check file extension matches format
                    if not filename.endswith(f'.{fmt}'):
                        continue
                    
                    # Parse filename to extract metadata
                    try:
                        # Expected format: SYMBOL_TYPE_TIMESTAMP.EXT
                        parts = filename.split('_')
                        if len(parts) >= 3:
                            file_symbol = parts[0]
                            
                            # Skip if filtering by symbol
                            if symbol and symbol != file_symbol:
                                continue
                            
                            signal_type = parts[1]
                            # The timestamp might contain additional underscores
                            timestamp_ext = '_'.join(parts[2:])
                            timestamp = timestamp_ext.split('.')[0]
                            
                            filepath = os.path.join(directory, filename)
                            file_info = os.stat(filepath)
                            
                            exports.append({
                                'symbol': file_symbol,
                                'signal_type': signal_type,
                                'timestamp': timestamp,
                                'format': fmt,
                                'path': filepath,
                                'size': file_info.st_size,
                                'created': datetime.fromtimestamp(file_info.st_ctime).isoformat()
                            })
                    except Exception as e:
                        logger.warning(f"Could not parse export filename {filename}: {str(e)}")
            
            # Sort by created date (newest first) and limit
            exports.sort(key=lambda x: x['created'], reverse=True)
            exports = exports[:max_items]
            
            return exports
            
        except Exception as e:
            logger.error(f"Error getting export history: {str(e)}", exc_info=True)
            return []
    
    def get_export_file(self, export_id: str) -> Dict:
        """
        Get details about a specific export file.
        
        Args:
            export_id: ID or path of the export file
            
        Returns:
            Dict: Details about the export file, including content if JSON
        """
        try:
            # Check if export_id is a path or just a filename
            if os.path.exists(export_id):
                filepath = export_id
            else:
                # Try to find the file in known directories
                for directory in [self.json_dir, self.pdf_dir]:
                    potential_path = os.path.join(directory, export_id)
                    if os.path.exists(potential_path):
                        filepath = potential_path
                        break
                else:
                    logger.error(f"Export file not found: {export_id}")
                    return {}
            
            # Get file info
            file_info = os.stat(filepath)
            filename = os.path.basename(filepath)
            file_ext = os.path.splitext(filename)[1].lower()[1:]  # Remove the dot
            
            result = {
                'path': filepath,
                'filename': filename,
                'format': file_ext,
                'size': file_info.st_size,
                'created': datetime.fromtimestamp(file_info.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(file_info.st_mtime).isoformat()
            }
            
            # If JSON, include content
            if file_ext == 'json':
                try:
                    with open(filepath, 'r') as f:
                        result['content'] = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not read JSON content: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting export file: {str(e)}", exc_info=True)
            return {}
    
    def delete_export(self, export_id: str) -> bool:
        """
        Delete an export file.
        
        Args:
            export_id: ID or path of the export file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if export_id is a path or just a filename
            if os.path.exists(export_id):
                filepath = export_id
            else:
                # Try to find the file in known directories
                for directory in [self.json_dir, self.pdf_dir]:
                    potential_path = os.path.join(directory, export_id)
                    if os.path.exists(potential_path):
                        filepath = potential_path
                        break
                else:
                    logger.error(f"Export file not found for deletion: {export_id}")
                    return False
            
            # Delete the file
            os.remove(filepath)
            logger.info(f"Deleted export file: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting export file: {str(e)}", exc_info=True)
            return False 