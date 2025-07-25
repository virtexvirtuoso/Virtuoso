#!/usr/bin/env python3
"""
Simple runner for the book finder script.
"""

import sys
import os
from pathlib import Path

# Add the scripts directory to the Python path
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

try:
    from book_finder import BookFinder, main
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"❌ Error importing book_finder: {e}")
    print("Make sure book_finder.py is in the same directory")
except Exception as e:
    print(f"❌ Unexpected error: {e}") 