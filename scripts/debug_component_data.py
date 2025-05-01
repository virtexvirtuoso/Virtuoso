#!/usr/bin/env python3
"""
Debug Component Data Script

This script helps to visualize and analyze the component data stored in JSON files.
It can be used to debug issues with component breakdown in alerts and PDFs.
"""

import os
import json
import argparse
import glob
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load a JSON file and return its contents."""
    with open(file_path, 'r') as f:
        return json.load(f)

def list_component_files(directory: str = None) -> List[str]:
    """List all component data files in the given directory."""
    if directory is None:
        # Check both possible locations
        signal_dir = os.path.join(os.getcwd(), 'exports', 'signal_data')
        component_dir = os.path.join(os.getcwd(), 'exports', 'component_data')
        
        signal_files = glob.glob(os.path.join(signal_dir, '*.json')) if os.path.exists(signal_dir) else []
        component_files = glob.glob(os.path.join(component_dir, '*.json')) if os.path.exists(component_dir) else []
        
        return sorted(signal_files + component_files, key=os.path.getmtime, reverse=True)
    else:
        return sorted(glob.glob(os.path.join(directory, '*.json')), key=os.path.getmtime, reverse=True)

def print_component_summary(data: Dict[str, Any]) -> None:
    """Print a summary of the component data."""
    symbol = data.get('symbol', 'UNKNOWN')
    score = data.get('score', 0)
    
    # Print header
    print(f"\n{'=' * 60}")
    print(f"COMPONENT SUMMARY FOR {symbol}")
    print(f"Overall Score: {score:.2f}")
    print(f"{'=' * 60}")
    
    # Print components
    components = data.get('components', {})
    if components:
        print("\nCOMPONENT SCORES:")
        print(f"{'Component':<20} {'Score':<10} {'Impact':<10}")
        print(f"{'-' * 20} {'-' * 10} {'-' * 10}")
        
        for name, value in components.items():
            if isinstance(value, dict):
                score = value.get('score', 0)
                impact = value.get('impact', 0)
                print(f"{name.ljust(20)} {score:<10.2f} {impact:<10.2f}")
            else:
                # If just a numeric value
                score = float(value)
                impact = abs(score - 50) * 2
                print(f"{name.ljust(20)} {score:<10.2f} {impact:<10.2f}")
    else:
        print("\nNo component data found.")
    
    # Print interpretations if available
    results = data.get('results', {})
    if results:
        print("\nCOMPONENT INTERPRETATIONS:")
        for name, details in results.items():
            interpretation = details.get('interpretation', 'No interpretation available')
            if isinstance(interpretation, str):
                print(f"\n{name.replace('_', ' ').title()}:")
                print(f"  {interpretation}")
    
    print(f"\n{'=' * 60}\n")

def compare_components(file1: str, file2: str) -> None:
    """Compare component data between two files."""
    data1 = load_json_file(file1)
    data2 = load_json_file(file2)
    
    # Extract components
    components1 = data1.get('components', {})
    components2 = data2.get('components', {})
    
    # Create a DataFrame for comparison
    comp1_data = []
    for name, value in components1.items():
        if isinstance(value, dict):
            score = value.get('score', 0)
        else:
            score = float(value)
        comp1_data.append({'component': name, 'score': score})
    
    comp2_data = []
    for name, value in components2.items():
        if isinstance(value, dict):
            score = value.get('score', 0)
        else:
            score = float(value)
        comp2_data.append({'component': name, 'score': score})
    
    df1 = pd.DataFrame(comp1_data)
    df2 = pd.DataFrame(comp2_data)
    
    # Merge DataFrames
    df = pd.merge(df1, df2, on='component', how='outer', suffixes=('_1', '_2'))
    df['diff'] = df['score_1'] - df['score_2']
    
    # Print comparison
    file1_name = os.path.basename(file1)
    file2_name = os.path.basename(file2)
    
    print(f"\n{'=' * 80}")
    print(f"COMPONENT COMPARISON")
    print(f"File 1: {file1_name}")
    print(f"File 2: {file2_name}")
    print(f"{'=' * 80}")
    
    print(f"\n{'Component':<20} {'Score 1':<10} {'Score 2':<10} {'Difference':<10}")
    print(f"{'-' * 20} {'-' * 10} {'-' * 10} {'-' * 10}")
    
    for _, row in df.iterrows():
        component = row['component']
        score1 = row.get('score_1', float('nan'))
        score2 = row.get('score_2', float('nan'))
        diff = row.get('diff', float('nan'))
        
        print(f"{component.ljust(20)} {score1:<10.2f} {score2:<10.2f} {diff:<10.2f}")
    
    print(f"\n{'=' * 80}\n")

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Debug Component Data')
    parser.add_argument('--list', action='store_true', help='List all component data files')
    parser.add_argument('--file', type=str, help='Path to a specific component data file to analyze')
    parser.add_argument('--compare', type=str, nargs=2, help='Compare two component data files')
    parser.add_argument('--latest', action='store_true', help='Show the latest component data file')
    parser.add_argument('--dir', type=str, help='Directory to search for component data files')
    
    args = parser.parse_args()
    
    if args.list:
        files = list_component_files(args.dir)
        if files:
            print(f"\nFound {len(files)} component data files:")
            for i, file in enumerate(files):
                file_time = datetime.fromtimestamp(os.path.getmtime(file)).strftime('%Y-%m-%d %H:%M:%S')
                file_name = os.path.basename(file)
                print(f"{i+1}. {file_name} - {file_time}")
        else:
            print("No component data files found.")
    
    elif args.file:
        if os.path.exists(args.file):
            data = load_json_file(args.file)
            print_component_summary(data)
        else:
            print(f"File not found: {args.file}")
    
    elif args.compare:
        file1, file2 = args.compare
        if os.path.exists(file1) and os.path.exists(file2):
            compare_components(file1, file2)
        else:
            if not os.path.exists(file1):
                print(f"File not found: {file1}")
            if not os.path.exists(file2):
                print(f"File not found: {file2}")
    
    elif args.latest:
        files = list_component_files(args.dir)
        if files:
            latest_file = files[0]
            print(f"Latest file: {os.path.basename(latest_file)}")
            data = load_json_file(latest_file)
            print_component_summary(data)
        else:
            print("No component data files found.")
    
    else:
        # Default action: list files
        files = list_component_files(args.dir)
        if files:
            print(f"\nFound {len(files)} component data files:")
            for i, file in enumerate(files[:10]):  # Show only the first 10
                file_time = datetime.fromtimestamp(os.path.getmtime(file)).strftime('%Y-%m-%d %H:%M:%S')
                file_name = os.path.basename(file)
                print(f"{i+1}. {file_name} - {file_time}")
            
            if len(files) > 10:
                print(f"... and {len(files) - 10} more files.")
        else:
            print("No component data files found.")

if __name__ == '__main__':
    main() 