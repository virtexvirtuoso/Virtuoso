#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Report Manager for the trading system.
Handles generating PDF reports and attaching them to Discord messages.
"""

import os
import json
import time
import logging
import asyncio
import aiohttp
import traceback
from typing import Dict, Any, List, Tuple, Optional, Union
from pathlib import Path
import pandas as pd
from datetime import datetime
import numpy as np
import shutil

# Local imports
try:
    from .pdf_generator import ReportGenerator
except ImportError:
    from core.reporting.pdf_generator import ReportGenerator

class ReportManager:
    """
    Manages the generation and attachment of PDF reports to trading signals.
    
    This class handles:
    1. Generating PDF reports with charts for trading signals
    2. Creating structured JSON exports of signal data
    3. Attaching files to Discord webhook messages
    4. Managing report file cleanup
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the ReportManager.
        
        Args:
            config: Optional configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Set up base directories for reports
        self.base_dir = self.config.get('base_dir', os.path.join(os.getcwd(), 'reports'))
        self.pdf_dir = os.path.join(self.base_dir, 'pdf')
        self.json_dir = os.path.join(self.base_dir, 'json')
        
        # Ensure directories exist
        for directory in [self.base_dir, self.pdf_dir, self.json_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Find the template directory using canonical configuration approach
        template_dir = self.config.get('template_dir')
        if not template_dir:
            # Check for centralized template configuration
            config_file = os.path.join(os.getcwd(), "config", "templates_config.json")
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r') as f:
                        config_data = json.load(f)
                        if 'template_directory' in config_data and os.path.exists(config_data['template_directory']):
                            template_dir = config_data['template_directory']
                            self.logger.info(f"Using template directory from config file: {template_dir}")
                        else:
                            raise ValueError("Template directory not found in config or does not exist")
                except Exception as e:
                    self.logger.error(f"Error loading template config: {str(e)}")
                    raise RuntimeError("Template configuration is required but not found or invalid")
            else:
                # Use canonical template directory with robust path detection
                # Check if we're already in src directory
                current_dir = os.getcwd()
                if current_dir.endswith('/src') or current_dir.endswith('\\src'):
                    # Already in src directory
                    template_dir = os.path.join(current_dir, 'core/reporting/templates')
                else:
                    # In root directory
                    template_dir = os.path.join(current_dir, 'src/core/reporting/templates')
                
                # Fallback search if primary path doesn't exist
                if not os.path.exists(template_dir):
                    possible_paths = [
                        os.path.join(current_dir, 'core/reporting/templates'),
                        os.path.join(current_dir, 'reporting/templates'),
                        os.path.join(current_dir, 'templates'),
                        os.path.join(os.path.dirname(current_dir), 'src/core/reporting/templates'),
                        os.path.join(os.path.dirname(__file__), 'templates')
                    ]
                    
                    for path in possible_paths:
                        if os.path.exists(path):
                            template_dir = path
                            break
                    else:
                        raise RuntimeError(f"Template directory not found. Searched paths: {[template_dir] + possible_paths}")
                
                self.logger.info(f"Using canonical template directory: {template_dir}")
        
        # Verify template directory exists
        if not template_dir or not os.path.exists(template_dir):
            raise RuntimeError(f"Template directory is invalid or does not exist: {template_dir}")
            
        self.logger.info(f"Template directory verified: {template_dir}")
        
        # Initialize PDF generator with proper template directory
        self.pdf_generator = ReportGenerator(config=self.config, template_dir=template_dir)
        
        # Explicitly set the template_dir to ensure it's available
        if template_dir and os.path.exists(template_dir):
            self.pdf_generator.template_dir = template_dir
        
        # Default Discord webhook config
        self.discord_webhook_url = self.config.get('discord_webhook_url', None)
        
        # Session for HTTP requests
        self.session = None
        
        self.logger.info("ReportManager initialized")

    async def start(self):
        """Initialize HTTP session for requests."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            self.logger.debug("HTTP session initialized")
    
    async def stop(self):
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.logger.debug("HTTP session closed")
    
    async def generate_and_attach_report(
        self,
        signal_data: Dict[str, Any],
        signal_type: str = 'buy',
        ohlcv_data: Optional[pd.DataFrame] = None,
        output_path: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate a report for a signal and optionally attach it to an alert.
        
        Args:
            signal_data: The signal data dictionary
            signal_type: Type of signal (buy, sell, neutral)
            ohlcv_data: Optional OHLCV dataframe for charts
            output_path: Optional path for the output PDF file
            
        Returns:
            Tuple containing (success flag, PDF path, JSON path)
        """
        try:
            self._log("Generating signal report", level=logging.INFO)
            
            if not signal_data:
                self._log("No signal data provided", level=logging.ERROR)
                return False, None, None
                
            symbol = signal_data.get('symbol', 'UNKNOWN')
            
            # Sanitize symbol for filenames
            if isinstance(symbol, str):
                symbol_safe = symbol.lower().replace('/', '_')
            else:
                self._log(f"Invalid symbol type: {type(symbol)}", level=logging.WARNING)
                symbol_safe = "unknown"
                
            # Create timestamp string
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"{symbol_safe}_{timestamp_str}"
            
            # Create export directory
            export_dir = "exports"
            os.makedirs(export_dir, exist_ok=True)
            
            # Export signal data as JSON for tracking
            json_path = os.path.join(export_dir, f"{signal_type}_{symbol_safe}_{timestamp_str}.json")
            with open(json_path, 'w') as f:
                json.dump(signal_data, f, indent=2, default=str)
            self._log(f"JSON report saved to {json_path}", level=logging.INFO)
            
            # Validate output_path to make sure it's a file path ending with .pdf
            if output_path:
                # If path exists and is a directory, modify it
                if os.path.exists(output_path) and os.path.isdir(output_path):
                    self._log(f"Output path is a directory: {output_path}", level=logging.WARNING)
                    pdf_path = os.path.join(output_path, f"{base_filename}.pdf")
                elif not output_path.lower().endswith('.pdf'):
                    # It's not a proper PDF file path, add .pdf extension
                    pdf_path = f"{output_path}.pdf"
                else:
                    # It's a file path ending with .pdf
                    pdf_path = output_path
                    # Ensure parent directory exists
                    parent_dir = os.path.dirname(pdf_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
            else:
                # No output path provided, generate default
                pdf_path = os.path.join(export_dir, f"{base_filename}.pdf")
            
            # Generate the PDF report
            self._log(f"Generating signal report PDF for {symbol}", level=logging.INFO)
            
            # Call the PDF generator
            try:
                result_pdf_path = self.pdf_generator.generate_trading_report(
                    signal_data=signal_data,
                    ohlcv_data=ohlcv_data,
                    output_dir=pdf_path
                )
                # Verify the PDF was generated and exists
                if result_pdf_path and os.path.exists(result_pdf_path[0]) and not os.path.isdir(result_pdf_path[0]):
                    self._log(f"PDF report generated successfully: {pdf_path}", level=logging.INFO)
                    return True, result_pdf_path[0], json_path
                else:
                    self._log(f"Error generating PDF report: Result path is {result_pdf_path}", level=logging.ERROR)
                    # Try to recover if the path was created as a directory
                    if pdf_path and os.path.exists(pdf_path) and os.path.isdir(pdf_path):
                        self._log(f"PDF path is a directory: {pdf_path}", level=logging.ERROR)
                        return await self._generate_fallback_pdf(signal_data, ohlcv_data, pdf_path, json_path)
            except Exception as e:
                self._log(f"Error generating PDF report: {str(e)}", level=logging.ERROR)
                self._log(traceback.format_exc(), level=logging.DEBUG)
                return await self._generate_fallback_pdf(signal_data, ohlcv_data, pdf_path, json_path)
                
            return False, None, json_path
            
        except Exception as e:
            self._log(f"Error in generate_and_attach_report: {str(e)}", level=logging.ERROR)
            self._log(traceback.format_exc(), level=logging.DEBUG)
            return False, None, None
    
    async def _attach_files_to_webhook(
        self,
        webhook_message: Dict[str, Any],
        webhook_url: str,
        files: List[str],
        file_descriptions: Optional[List[str]] = None
    ) -> bool:
        """
        Attach files to a Discord webhook message.
        
        Args:
            webhook_message: Discord webhook message to modify
            webhook_url: Discord webhook URL
            files: List of file paths to attach
            file_descriptions: Optional descriptions for files
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not webhook_url:
                self.logger.warning("No webhook URL provided")
                return False
            
            if not files:
                self.logger.warning("No files to attach")
                return False
            
            # Initialize session if needed
            await self.start()
            
            # Prepare form data
            form_data = aiohttp.FormData()
            
            # Add payload JSON
            form_data.add_field(
                name='payload_json',
                value=json.dumps(webhook_message),
                content_type='application/json'
            )
            
            # Validate files
            valid_files = []
            file_handles = []  # Keep track of open file handles
            
            for i, file_path in enumerate(files):
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    valid_files.append((i, file_path))
                else:
                    self.logger.warning(f"File {file_path} does not exist or is empty")
            
            # Add files
            try:
                for i, (orig_index, file_path) in enumerate(valid_files):
                    # Get file description or use default
                    description = "File"
                    if file_descriptions and orig_index < len(file_descriptions):
                        description = file_descriptions[orig_index]
                    
                    # Add file to form data (leave the file handle open)
                    file_handle = open(file_path, 'rb')
                    file_handles.append(file_handle)  # Store the handle to close later
                    
                    form_data.add_field(
                        name=f'file{i}',
                        value=file_handle,
                        filename=os.path.basename(file_path),
                        content_type='application/octet-stream'
                    )
                    self.logger.debug(f"Added {file_path} to form data")
                
                # Send the webhook
                async with self.session.post(webhook_url, data=form_data) as response:
                    if response.status in (200, 204):
                        self.logger.info(f"Successfully sent webhook with files, status: {response.status}")
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Error sending webhook: {response.status} - {error_text}")
                        return False
            finally:
                # Close all file handles
                for handle in file_handles:
                    if not handle.closed:
                        handle.close()
        
        except Exception as e:
            self.logger.error(f"Error attaching files to webhook: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    async def generate_and_send_report(
        self,
        signal_data: Dict[str, Any],
        ohlcv_data: Optional[pd.DataFrame] = None,
        webhook_url: Optional[str] = None,
        signal_type: str = 'report'
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate PDF report and send it directly to Discord.
        
        Args:
            signal_data: Trading signal data
            ohlcv_data: OHLCV price data for charts
            webhook_url: Discord webhook URL (overrides default)
            signal_type: Type of signal ('alert', 'report', etc.)
            
        Returns:
            Tuple of (success, pdf_path, json_path)
        """
        try:
            # Use provided webhook URL or default
            webhook_url = webhook_url or self.discord_webhook_url
            
            if not webhook_url:
                self.logger.warning("No webhook URL provided")
                return False, None, None
            
            # Get symbol and signal type
            symbol = signal_data.get('symbol', 'Unknown')
            signal_value = signal_data.get('signal', 'NEUTRAL')
            
            # Create basic webhook message
            webhook_message = {
                "username": "Virtuoso Trading Reports",
                "content": f"📊 Trading Report: {symbol} ({signal_value})",
                "embeds": [
                    {
                        "title": f"{symbol} Trading Report",
                        "description": f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        "color": self._get_color_for_signal(signal_value),
                        "footer": {
                            "text": "Virtuoso Trading System"
                        }
                    }
                ]
            }
            
            # Generate and attach report
            return await self.generate_and_attach_report(
                signal_data=signal_data,
                ohlcv_data=ohlcv_data,
                signal_type=signal_type
            )
        
        except Exception as e:
            self.logger.error(f"Error generating and sending report: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False, None, None
    
    def _get_color_for_signal(self, signal_type: str) -> int:
        """
        Get Discord embed color for signal type.
        
        Args:
            signal_type: Signal type (BULLISH, BEARISH, NEUTRAL)
            
        Returns:
            Discord color integer
        """
        signal_type = signal_type.upper()
        
        if signal_type == 'BULLISH' or signal_type == 'BUY':
            return 0x00FF00  # Green
        elif signal_type == 'BEARISH' or signal_type == 'SELL':
            return 0xFF0000  # Red
        else:
            return 0xFFAA00  # Amber/Yellow for neutral
    
    def cleanup_old_reports(self, max_age_days: int = 7) -> Tuple[int, int]:
        """
        Delete reports older than max_age_days.
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Tuple of (pdf_deleted, json_deleted)
        """
        try:
            now = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            pdf_deleted = 0
            json_deleted = 0
            
            # Clean up PDF files
            for file in os.listdir(self.pdf_dir):
                file_path = os.path.join(self.pdf_dir, file)
                if os.path.isfile(file_path):
                    file_age = now - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        pdf_deleted += 1
            
            # Clean up JSON files
            for file in os.listdir(self.json_dir):
                file_path = os.path.join(self.json_dir, file)
                if os.path.isfile(file_path):
                    file_age = now - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        json_deleted += 1
            
            self.logger.info(f"Cleaned up {pdf_deleted} PDF and {json_deleted} JSON files")
            return pdf_deleted, json_deleted
        
        except Exception as e:
            self.logger.error(f"Error cleaning up old reports: {str(e)}")
            self.logger.error(traceback.format_exc())
            return 0, 0
    
    async def _generate_fallback_pdf(
        self,
        signal_data: Dict[str, Any],
        ohlcv_data: Optional[pd.DataFrame],
        pdf_path: str,
        json_path: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate a fallback PDF when the primary method fails.
        
        Args:
            signal_data: Signal data dictionary
            ohlcv_data: OHLCV dataframe for charts
            pdf_path: Path where the PDF should be saved
            json_path: Path to the saved JSON data
            
        Returns:
            Tuple of (success, pdf_path, json_path)
        """
        try:
            # Create a fixed path by appending _fixed.pdf
            fixed_pdf_path = f"{pdf_path}_fixed.pdf" if not pdf_path.endswith('_fixed.pdf') else pdf_path
            
            # Generate HTML content directly
            html_content = self.pdf_generator._generate_html_content(signal_data, ohlcv_data)
            html_path = fixed_pdf_path.replace('.pdf', '.html_fixed.html')
            
            # Write HTML to file
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            # Generate PDF from HTML
            self._log(f"Generating PDF from HTML: {html_path}", level=logging.INFO)
            await self.pdf_generator.generate_pdf(html_path, fixed_pdf_path)
            
            # Check if fixed PDF was created successfully
            if os.path.exists(fixed_pdf_path) and not os.path.isdir(fixed_pdf_path) and os.path.getsize(fixed_pdf_path) > 0:
                self._log(f"Created fixed PDF at: {fixed_pdf_path}", level=logging.INFO)
                return True, fixed_pdf_path, json_path
            else:
                self._log(f"Failed to create fixed PDF at: {fixed_pdf_path}", level=logging.ERROR)
                return False, None, json_path
                
        except Exception as e:
            self._log(f"Error generating fallback PDF: {str(e)}", level=logging.ERROR)
            self._log(traceback.format_exc(), level=logging.DEBUG)
            return False, None, json_path
    
    def _log(self, message: str, level: int = logging.INFO) -> None:
        """Log messages with the appropriate logger."""
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger(__name__)
        self.logger.log(level, message) 