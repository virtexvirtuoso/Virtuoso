#!/usr/bin/env python3
"""
Quick test script to verify Trello API connection
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if credentials are set
api_key = os.getenv('TRELLO_API_KEY')
token = os.getenv('TRELLO_TOKEN')

print("🔍 Checking Trello credentials...\n")

if not api_key:
    print("❌ TRELLO_API_KEY not found in .env file")
    print("   Please add your API key to the .env file")
    print("   Example: TRELLO_API_KEY=8f6e4b3a9c2d1e5f7a8b9c0d1e2f3a4b")
    exit(1)

if not token:
    print("❌ TRELLO_TOKEN not found in .env file")
    print("   Please add your token to the .env file")
    print("   Example: TRELLO_TOKEN=9f8e7d6c5b4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c...")
    exit(1)

print("✅ Credentials found in .env file")
print(f"   API Key: {api_key[:8]}... (hidden)")
print(f"   Token: {token[:8]}... (hidden)")

# Test the connection
print("\n🔌 Testing connection to Trello API...")

try:
    import requests
    url = f"https://api.trello.com/1/members/me?key={api_key}&token={token}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Successfully connected to Trello!")
        print(f"   Logged in as: {data.get('fullName', 'Unknown')} (@{data.get('username', 'unknown')})")
        print(f"   Email: {data.get('email', 'Not available')}")
        
        # Get boards
        boards_url = f"https://api.trello.com/1/members/me/boards?key={api_key}&token={token}"
        boards_response = requests.get(boards_url)
        
        if boards_response.status_code == 200:
            boards = boards_response.json()
            print(f"\n📋 Found {len(boards)} boards:")
            
            virtuoso_board = None
            for board in boards:
                is_virtuoso = 'virtuoso' in board['name'].lower()
                marker = " ← Your Virtuoso board!" if is_virtuoso else ""
                print(f"   - {board['name']} (ID: {board['id']}){marker}")
                
                if is_virtuoso or board['id'] == 'YBgMusBE':
                    virtuoso_board = board
            
            if virtuoso_board:
                print(f"\n🎯 Virtuoso Board Details:")
                print(f"   Name: {virtuoso_board['name']}")
                print(f"   ID: {virtuoso_board['id']}")
                print(f"   URL: {virtuoso_board['url']}")
                
                # Get lists in the board
                lists_url = f"https://api.trello.com/1/boards/{virtuoso_board['id']}/lists?key={api_key}&token={token}"
                lists_response = requests.get(lists_url)
                
                if lists_response.status_code == 200:
                    lists = lists_response.json()
                    print(f"\n📑 Lists in Virtuoso board:")
                    for lst in lists:
                        # Count cards in each list
                        cards_url = f"https://api.trello.com/1/lists/{lst['id']}/cards?key={api_key}&token={token}"
                        cards_response = requests.get(cards_url)
                        card_count = len(cards_response.json()) if cards_response.status_code == 200 else 0
                        print(f"   - {lst['name']}: {card_count} cards")
            
            print("\n✅ Everything is working! You can now use the Trello integration scripts.")
            print("\nTry running:")
            print("   python scripts/trello_sync_tasks.py")
            print("   python scripts/trello_daily_standup.py")
            
    else:
        print(f"\n❌ Failed to connect to Trello API")
        print(f"   Status code: {response.status_code}")
        print(f"   Response: {response.text}")
        print("\nPlease check your credentials are correct.")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nMake sure you have installed requests:")
    print("   pip install requests python-dotenv")