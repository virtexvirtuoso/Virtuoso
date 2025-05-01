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

# Local imports
from src.core.reporting.pdf_generator import ReportGenerator

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
        
        # Initialize PDF generator
        self.pdf_generator = ReportGenerator(self.config)
        
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
        ohlcv_data: Optional[pd.DataFrame] = None,
        webhook_message: Optional[Dict[str, Any]] = None,
        webhook_url: Optional[str] = None,
        signal_type: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        """
        Generate PDF report and attach it to webhook message.
        
        Args:
            signal_data: Trading signal data
            ohlcv_data: OHLCV price data for charts
            webhook_message: Discord webhook message to modify
            webhook_url: Discord webhook URL
            signal_type: Type of signal ('alert', 'report', etc.)
            output_path: Optional explicit output path for the PDF
            
        Returns:
            Tuple of (success, pdf_path, json_path)
        """
        if not signal_data:
            return False, "", ""
            
        try:
            # Get timestamp of signal for filename
            timestamp = signal_data.get('timestamp', int(time.time() * 1000))
            if isinstance(timestamp, str):
                try:
                    timestamp = int(timestamp)
                except ValueError:
                    timestamp = int(time.time() * 1000)
            
            # Convert to datetime for filename
            dt = datetime.fromtimestamp(timestamp / 1000)
            timestamp_str = dt.strftime("%Y%m%d_%H%M%S")
            
            # Generate filenames for reports
            if signal_type is None or signal_type == 'signal':
                base_filename = f"{signal_data.get('symbol', 'UNKNOWN')}_{timestamp_str}"
            elif signal_type == 'market_report':
                base_filename = f"market_report_{timestamp_str}"
            else:
                base_filename = f"{signal_type}_{signal_data.get('symbol', 'UNKNOWN')}_{timestamp_str}"
                
            # Determine export directory
            if signal_type == 'market_report':
                export_dir = os.path.join('exports', 'market_reports')
            else:
                export_dir = os.path.join('exports')
                
            os.makedirs(export_dir, exist_ok=True)
            
            # If output_path is provided, use it instead of generating one
            if output_path:
                pdf_path = output_path
            else:
                pdf_path = os.path.join(export_dir, f"{base_filename}.pdf")
                
            # Export JSON data
            json_path = os.path.join(export_dir, f"{base_filename}.json")
            try:
                # Define custom JSON serializer function to handle non-serializable types
                def json_serializer(obj):
                    if isinstance(obj, (datetime, pd.Timestamp)):
                        return obj.isoformat()
                    elif hasattr(pd, 'Timestamp') and isinstance(obj, pd.Timestamp):
                        return obj.isoformat()
                    elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
                        return int(obj)
                    elif isinstance(obj, (np.float64, np.float32, np.float16)):
                        return float(obj)
                    elif isinstance(obj, np.ndarray):
                        return obj.tolist()
                    elif isinstance(obj, pd.DataFrame):
                        return obj.to_dict(orient='records')
                    elif isinstance(obj, pd.Series):
                        return obj.to_dict()
                    return str(obj)  # Default: convert to string for any other type
                
                with open(json_path, 'w') as f:
                    json.dump(signal_data, f, indent=2, default=json_serializer)
                self.logger.info(f"JSON report saved to {json_path}")
            except Exception as e:
                self.logger.error(f"Failed to save JSON report: {str(e)}")
                self.logger.debug(traceback.format_exc())
                
            # Get PDF generator instance
            generator = self.pdf_generator
            
            # Generate the PDF
            if signal_type == 'market_report':
                self.logger.info(f"Generating market report PDF for {signal_data.get('symbol', 'MARKET')}")
                success = await generator.generate_market_html_report(signal_data, output_path=pdf_path)
            else:
                self.logger.info(f"Generating signal report PDF for {signal_data.get('symbol', 'UNKNOWN')}")
                # Default to regular signal report generation
                success = await generator.generate_report(signal_data, ohlcv_data, output_path=pdf_path)
                
            if success:
                self.logger.info(f"PDF report generated successfully: {pdf_path}")
                
                # If webhook message is provided, attach the file to it
                if webhook_message and os.path.exists(pdf_path):
                    if 'files' not in webhook_message:
                        webhook_message['files'] = []
                        
                    webhook_message['files'].append({
                        'path': pdf_path,
                        'filename': os.path.basename(pdf_path),
                        'description': f"Report for {signal_data.get('symbol', 'UNKNOWN')}"
                    })
                    
                    # If webhook URL is provided, send the message directly
                    if webhook_url and self.discord_webhook_url:
                        await self._attach_files_to_webhook(
                            webhook_message=webhook_message,
                            webhook_url=webhook_url,
                            files=[pdf_path],
                            file_descriptions=["PDF Report"]
                        )
                        
                return True, pdf_path, json_path
            else:
                self.logger.error("Failed to generate PDF report")
                return False, "", json_path
                
        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")
            self.logger.debug(traceback.format_exc())
            return False, "", ""
    
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
                webhook_message=webhook_message,
                webhook_url=webhook_url,
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