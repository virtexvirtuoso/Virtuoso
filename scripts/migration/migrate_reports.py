#!/usr/bin/env python3
"""
Script to migrate existing report files to the new directory structure.
This script moves files from the old format (all in reports/pdf/) 
to the new structure based on file extension:
- JSON files to reports/json/
- HTML files to reports/html/
- PDF files stay in reports/pdf/
"""

import os
import shutil
import glob
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("report_migration")

def main():
    # Define directories
    reports_base_dir = 'reports'
    old_pdf_dir = os.path.join(reports_base_dir, 'pdf')
    json_dir = os.path.join(reports_base_dir, 'json')
    html_dir = os.path.join(reports_base_dir, 'html')
    charts_dir = os.path.join(reports_base_dir, 'charts')
    
    # Ensure all directories exist
    for directory in [json_dir, html_dir, old_pdf_dir, charts_dir]:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")
    
    # Find all files in reports/pdf directory
    try:
        pdf_files = glob.glob(os.path.join(old_pdf_dir, "*.pdf"))
        html_files = glob.glob(os.path.join(old_pdf_dir, "*.html"))
        json_files = glob.glob(os.path.join(old_pdf_dir, "*.json"))
        png_files = glob.glob(os.path.join(old_pdf_dir, "*.png"))
        
        logger.info(f"Found {len(pdf_files)} PDF files")
        logger.info(f"Found {len(html_files)} HTML files")
        logger.info(f"Found {len(json_files)} JSON files")
        logger.info(f"Found {len(png_files)} PNG files")
        
        # Move HTML files to reports/html
        for file_path in html_files:
            filename = os.path.basename(file_path)
            destination = os.path.join(html_dir, filename)
            
            # Skip if destination already exists
            if os.path.exists(destination):
                logger.warning(f"Skipping {filename} - already exists in destination")
                continue
                
            try:
                shutil.move(file_path, destination)
                logger.info(f"Moved {filename} to {html_dir}")
            except Exception as e:
                logger.error(f"Error moving {filename}: {str(e)}")
        
        # Move JSON files to reports/json
        for file_path in json_files:
            filename = os.path.basename(file_path)
            destination = os.path.join(json_dir, filename)
            
            # Skip if destination already exists
            if os.path.exists(destination):
                logger.warning(f"Skipping {filename} - already exists in destination")
                continue
                
            try:
                shutil.move(file_path, destination)
                logger.info(f"Moved {filename} to {json_dir}")
            except Exception as e:
                logger.error(f"Error moving {filename}: {str(e)}")
        
        # Move PNG files to reports/charts
        for file_path in png_files:
            filename = os.path.basename(file_path)
            destination = os.path.join(charts_dir, filename)
            
            # Skip if destination already exists
            if os.path.exists(destination):
                logger.warning(f"Skipping {filename} - already exists in destination")
                continue
                
            try:
                shutil.move(file_path, destination)
                logger.info(f"Moved {filename} to {charts_dir}")
            except Exception as e:
                logger.error(f"Error moving {filename}: {str(e)}")
        
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code) 