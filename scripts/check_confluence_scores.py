#!/usr/bin/env python3
"""Check confluence scores data"""

import requests
import json

# Get mobile data
response = requests.get("http://VPS_HOST_REDACTED:8002/api/dashboard/mobile")
data = response.json()

confluence_scores = data.get('confluence_scores', [])

print("=" * 60)
print("CONFLUENCE SCORES DATA CHECK")
print("=" * 60)
print(f"\nTotal scores: {len(confluence_scores)}")

# Show first 3 scores
for i, score in enumerate(confluence_scores[:3], 1):
    print(f"\n{i}. {score.get('symbol', 'N/A')}:")
    print(f"   Score: {score.get('score', 'N/A')}")
    print(f"   Price: ${score.get('price', 0)}")
    print(f"   Change 24h: {score.get('change_24h', 0)}%")
    print(f"   Volume 24h: ${score.get('volume_24h', 0):,.0f}")
    print(f"   High 24h: ${score.get('high_24h', 0)}")
    print(f"   Low 24h: ${score.get('low_24h', 0)}")
    print(f"   Range 24h: {score.get('range_24h', 0)}%")
    print(f"   Has breakdown: {score.get('has_breakdown', False)}")
    
    # Check components
    components = score.get('components', {})
    if components:
        print(f"   Components: {list(components.keys())[:3]}...")

print("\n" + "=" * 60)
print("RAW JSON for first score:")
print(json.dumps(confluence_scores[0] if confluence_scores else {}, indent=2))