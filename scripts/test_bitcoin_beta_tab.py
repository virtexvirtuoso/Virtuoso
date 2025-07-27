#!/usr/bin/env python3
"""Test script to verify Bitcoin Beta tab implementation."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_bitcoin_beta_tab():
    """Check if Bitcoin Beta tab is properly implemented in the mobile dashboard."""
    
    print("🔍 Checking Bitcoin Beta Tab Implementation")
    print("=" * 50)
    
    # Check if the HTML file exists
    html_file = project_root / "src" / "dashboard" / "templates" / "dashboard_mobile_v1.html"
    
    if not html_file.exists():
        print("❌ Dashboard HTML file not found!")
        return False
    
    # Read the file content
    content = html_file.read_text()
    
    # Check for Bitcoin Beta tab components
    checks = [
        ("Beta Tab Content", 'id="betaTab"', "Beta tab content section"),
        ("Beta Navigation Button", '₿ Beta', "Beta button in navigation"),
        ("Beta Coefficient Display", 'id="betaCoefficient"', "Beta coefficient element"),
        ("Correlation Display", 'id="btcCorrelation"', "BTC correlation element"),
        ("Market Regime Display", 'id="betaMarketRegime"', "Market regime element"),
        ("Volatility Ratio Display", 'id="volatilityRatio"', "Volatility ratio element"),
        ("Beta Rankings List", 'id="betaSymbolsList"', "Beta rankings container"),
        ("Load Beta Data Function", 'loadBetaData()', "JavaScript function to load beta data"),
        ("Update Beta Overview Function", 'updateBetaOverview', "Function to update beta display"),
        ("Sort Beta Symbols Function", 'sortBetaSymbols', "Function to sort beta rankings")
    ]
    
    all_passed = True
    
    for check_name, search_string, description in checks:
        if search_string in content:
            print(f"✅ {check_name}: Found {description}")
        else:
            print(f"❌ {check_name}: Missing {description}")
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("✅ All Bitcoin Beta tab components are properly implemented!")
        print("\nNext Steps:")
        print("1. Deploy to VPS using: ./scripts/deploy_bitcoin_beta_tab.sh")
        print("2. Test on mobile device at: http://your-vps-ip:8080/dashboard")
        print("3. Click on '₿ Beta' tab in bottom navigation")
    else:
        print("❌ Some components are missing. Please review the implementation.")
    
    return all_passed


if __name__ == "__main__":
    check_bitcoin_beta_tab()