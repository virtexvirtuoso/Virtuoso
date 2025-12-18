#!/usr/bin/env python3
"""
Import Historical Signal Data

Imports existing signal JSON files from reports/json/ into the trading_signals table.
This populates the database with historical data for analytics.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.signal_storage import store_trading_signal


def import_signal_from_json(json_path: str) -> bool:
    """
    Import a single signal from JSON file.

    Args:
        json_path: Path to the signal JSON file

    Returns:
        True if imported successfully, False otherwise
    """
    try:
        with open(json_path, 'r') as f:
            signal_data = json.load(f)

        # Extract component scores from nested structure
        if 'results' in signal_data or 'analysis_components' in signal_data:
            components = {}

            # Try results first (newer format)
            if 'results' in signal_data:
                for comp_name, comp_data in signal_data['results'].items():
                    if isinstance(comp_data, dict) and 'score' in comp_data:
                        components[f"{comp_name}_score"] = comp_data['score']

            # Try analysis_components (alternative format)
            elif 'analysis_components' in signal_data:
                for comp_name, comp_data in signal_data['analysis_components'].items():
                    if isinstance(comp_data, dict) and 'score' in comp_data:
                        components[f"{comp_name}_score"] = comp_data['score']

            # Add to signal_data
            if components:
                signal_data['components'] = components

        # Store the signal
        result = store_trading_signal(
            signal_data=signal_data,
            json_path=json_path,
            pdf_path=None,  # PDF path not available in historical import
            sent_to_discord=False  # Historical signals weren't sent
        )

        if result:
            print(f"✓ Imported: {Path(json_path).name}")
            return True
        else:
            print(f"✗ Skipped (duplicate or error): {Path(json_path).name}")
            return False

    except Exception as e:
        print(f"✗ Error importing {Path(json_path).name}: {str(e)}")
        return False


def main():
    """Import all signal JSON files from reports/json/"""

    # Get project root
    project_root = Path(__file__).parent.parent
    reports_dir = project_root / 'reports' / 'json'

    if not reports_dir.exists():
        print(f"Reports directory not found: {reports_dir}")
        return

    # Find all signal JSON files
    json_files = sorted(reports_dir.glob('*_LONG_*.json')) + sorted(reports_dir.glob('*_SHORT_*.json'))

    if not json_files:
        print("No signal JSON files found")
        return

    print(f"Found {len(json_files)} signal files to import\n")

    # Import each file
    imported = 0
    skipped = 0
    errors = 0

    for json_path in json_files:
        result = import_signal_from_json(str(json_path))
        if result:
            imported += 1
        else:
            skipped += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Import Complete:")
    print(f"  ✓ Imported: {imported}")
    print(f"  ⊘ Skipped:  {skipped}")
    print(f"  Total:      {len(json_files)}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
