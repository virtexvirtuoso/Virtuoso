#!/usr/bin/env python3
"""
Debug script to check which files are actually being loaded and find the source of the log message.
"""

import sys
import os
import inspect
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def find_log_message_source():
    """Find where the exact log message is coming from"""
    print("🔍 Debugging Module Source and Log Message Location")
    print("=" * 60)
    
    try:
        # Import the confluence analyzer
        from core.analysis.confluence import ConfluenceAnalyzer
        
        # Get the source file for the confluence analyzer
        source_file = inspect.getfile(ConfluenceAnalyzer)
        print(f"✅ ConfluenceAnalyzer loaded from: {source_file}")
        
        # Check if the file contains the problematic message
        with open(source_file, 'r') as f:
            content = f.read()
            if "Skipping htf - invalid DataFrame" in content:
                print("❌ Found problematic message in current confluence file!")
            elif "Skipping" in content and "invalid DataFrame" in content:
                print("⚠️  Found similar message patterns in confluence file")
                # Find the lines
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if "Skipping" in line and "invalid" in line:
                        print(f"   Line {i+1}: {line.strip()}")
            else:
                print("✅ No problematic message found in current confluence file")
        
        # Check volume indicators
        try:
            from indicators.volume_indicators import VolumeIndicators
            vol_source_file = inspect.getfile(VolumeIndicators)
            print(f"✅ VolumeIndicators loaded from: {vol_source_file}")
            
            with open(vol_source_file, 'r') as f:
                content = f.read()
                if "Skipping htf - invalid DataFrame" in content:
                    print("❌ Found problematic message in current volume_indicators file!")
                elif "Skipping" in content and "invalid DataFrame" in content:
                    print("⚠️  Found similar message patterns in volume_indicators file")
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if "Skipping" in line and "invalid" in line:
                            print(f"   Line {i+1}: {line.strip()}")
                else:
                    print("✅ No problematic message found in current volume_indicators file")
                    
        except ImportError as e:
            print(f"❌ Could not import VolumeIndicators: {e}")
        
        # Check if there are any methods that contain the problematic logging
        print(f"\n🔬 Analyzing ConfluenceAnalyzer methods...")
        
        analyzer = ConfluenceAnalyzer()
        
        # Look for methods that might contain VWAP logic
        methods = [method for method in dir(analyzer) if 'vwap' in method.lower() or 'calculate' in method.lower()]
        print(f"Methods containing 'vwap' or 'calculate': {methods}")
        
        # Try to find the exact method that's causing the issue
        for method_name in methods:
            if hasattr(analyzer, method_name):
                method = getattr(analyzer, method_name)
                if callable(method):
                    try:
                        method_source = inspect.getsource(method)
                        if "Skipping" in method_source and "invalid" in method_source:
                            print(f"🎯 Found problematic code in method: {method_name}")
                            print(f"Method source location: {inspect.getfile(method)}")
                            
                            # Show the problematic lines
                            lines = method_source.split('\n')
                            for i, line in enumerate(lines):
                                if "Skipping" in line and ("invalid" in line or "DataFrame" in line):
                                    print(f"   Problematic line {i+1}: {line.strip()}")
                    except:
                        pass
                        
        print(f"\n📁 Current working directory: {os.getcwd()}")
        print(f"📁 Python path: {sys.path}")
        
        # Check if there are any pyc files that might be cached
        print(f"\n🗂️  Checking for cached pyc files...")
        import glob
        pyc_files = glob.glob("**/*.pyc", recursive=True)
        if pyc_files:
            print(f"Found {len(pyc_files)} pyc files - these might contain old code")
            for pyc in pyc_files[:10]:  # Show first 10
                print(f"   {pyc}")
        else:
            print("✅ No pyc files found")
            
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_log_message_source()