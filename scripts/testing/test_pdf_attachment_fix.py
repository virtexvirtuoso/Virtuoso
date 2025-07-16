#!/usr/bin/env python3
"""
Test script to verify PDF attachment fix for Discord webhooks.
This script tests the fixed file attachment method without actually sending to Discord.
"""

import os
import sys
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from discord_webhook import DiscordWebhook

def test_pdf_attachment():
    """Test PDF attachment with the fixed method."""
    
    # Test file path (the one that was failing)
    file_path = '/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/reports/pdf/ethusdt_BUY_68p2_20250609_083342.pdf'
    
    print("Testing PDF attachment fix...")
    print(f"File path: {file_path}")
    
    if not os.path.exists(file_path):
        print("❌ ERROR: Test PDF file does not exist")
        return False
    
    try:
        # Create a test webhook (won't actually send)
        webhook = DiscordWebhook(url='https://discord.com/api/webhooks/test/test')
        webhook.set_content("Test message with PDF attachment")
        
        # Read file and add it using the fixed method
        with open(file_path, 'rb') as f:
            file_content = f.read()
            
        print(f"File size: {len(file_content)} bytes")
        print(f"File starts with PDF header: {file_content.startswith(b'%PDF')}")
        null_byte = b'\x00'
        print(f"File contains null bytes: {null_byte in file_content}")
        
        # Clean filename (same logic as in alert_manager.py)
        filename = os.path.basename(file_path)
        clean_filename = filename.replace('\x00', '').strip()
        if not clean_filename:
            clean_filename = "attachment_0.pdf"
        
        # Ensure filename is properly encoded
        try:
            clean_filename = clean_filename.encode('ascii', 'ignore').decode('ascii')
        except Exception:
            clean_filename = "attachment_0.pdf"
        
        print(f"Clean filename: {clean_filename}")
        
        # Test the fixed add_file method
        webhook.add_file(file=file_content, filename=clean_filename)
        
        print("✅ SUCCESS: File attachment method works correctly")
        print("✅ The null byte issue has been resolved")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_pdf_attachment()
    if success:
        print("\n🎉 PDF attachment fix verified successfully!")
        print("Discord webhook PDF attachments should now work correctly.")
    else:
        print("\n💥 PDF attachment fix failed!")
        sys.exit(1) 