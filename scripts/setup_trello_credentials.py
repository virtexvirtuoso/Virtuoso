#!/usr/bin/env python3
"""
Trello API Credential Setup Helper
Guides you through getting and testing Trello API credentials
"""

import os
import sys
import json
import requests
import webbrowser
from pathlib import Path


def test_credentials(api_key: str, token: str) -> bool:
    """Test if the credentials are valid."""
    try:
        url = f"https://api.trello.com/1/members/me?key={api_key}&token={token}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Credentials valid! Connected as: {data.get('fullName', 'Unknown')} (@{data.get('username', 'unknown')})")
            return True
        else:
            print(f"❌ Invalid credentials. Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing credentials: {e}")
        return False


def save_to_env_file(api_key: str, token: str):
    """Save credentials to .env file."""
    env_path = Path.cwd() / '.env'
    
    # Read existing content
    existing_content = []
    if env_path.exists():
        with open(env_path, 'r') as f:
            existing_content = f.readlines()
    
    # Remove old Trello entries
    new_content = [line for line in existing_content 
                   if not line.startswith('TRELLO_API_KEY=') 
                   and not line.startswith('TRELLO_TOKEN=')]
    
    # Add new entries
    new_content.extend([
        f"TRELLO_API_KEY={api_key}\n",
        f"TRELLO_TOKEN={token}\n"
    ])
    
    # Write back
    with open(env_path, 'w') as f:
        f.writelines(new_content)
    
    print(f"✅ Credentials saved to {env_path}")


def save_to_shell_config(api_key: str, token: str):
    """Save credentials to shell configuration."""
    shell = os.environ.get('SHELL', '').split('/')[-1]
    
    if shell == 'zsh':
        config_file = Path.home() / '.zshrc'
    elif shell == 'bash':
        config_file = Path.home() / '.bashrc'
    else:
        config_file = Path.home() / '.profile'
    
    export_lines = [
        f"\n# Trello API Credentials for Virtuoso",
        f"export TRELLO_API_KEY='{api_key}'",
        f"export TRELLO_TOKEN='{token}'\n"
    ]
    
    # Check if already exists
    if config_file.exists():
        with open(config_file, 'r') as f:
            content = f.read()
            if 'TRELLO_API_KEY' in content:
                print(f"⚠️  Trello credentials already exist in {config_file}")
                response = input("Replace existing credentials? (y/n): ")
                if response.lower() != 'y':
                    return
                
                # Remove old entries
                lines = content.split('\n')
                new_lines = []
                skip_next = False
                for line in lines:
                    if 'Trello API Credentials' in line:
                        skip_next = True
                        continue
                    if skip_next and ('TRELLO_API_KEY' in line or 'TRELLO_TOKEN' in line):
                        continue
                    skip_next = False
                    new_lines.append(line)
                
                content = '\n'.join(new_lines)
                
                with open(config_file, 'w') as f:
                    f.write(content)
    
    # Append new credentials
    with open(config_file, 'a') as f:
        f.write('\n'.join(export_lines))
    
    print(f"✅ Credentials saved to {config_file}")
    print(f"   Run 'source {config_file}' to load them in current session")


def setup_credentials():
    """Interactive setup for Trello credentials."""
    print("🔧 Trello API Credential Setup\n")
    
    # Check if credentials already exist
    existing_key = os.environ.get('TRELLO_API_KEY')
    existing_token = os.environ.get('TRELLO_TOKEN')
    
    if existing_key and existing_token:
        print("📌 Found existing credentials in environment")
        if test_credentials(existing_key, existing_token):
            response = input("\nCredentials are valid. Do you want to replace them? (y/n): ")
            if response.lower() != 'y':
                return existing_key, existing_token
    
    print("\n📋 Steps to get your Trello API credentials:\n")
    print("1. Opening Trello API key page in your browser...")
    print("   (If it doesn't open, go to: https://trello.com/app-key)")
    
    webbrowser.open("https://trello.com/app-key")
    
    print("\n2. Log in to Trello if needed")
    print("3. Copy your API Key from the page")
    
    api_key = input("\n🔑 Paste your API Key here: ").strip()
    
    if not api_key:
        print("❌ API Key is required!")
        return None, None
    
    print("\n4. Now click the 'Token' link on that same page")
    print("   (Or visit: https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&name=Virtuoso&key=" + api_key + ")")
    
    token_url = f"https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&name=Virtuoso&key={api_key}"
    webbrowser.open(token_url)
    
    print("\n5. Click 'Allow' to authorize Virtuoso")
    print("6. Copy the token from the page")
    
    token = input("\n🎫 Paste your Token here: ").strip()
    
    if not token:
        print("❌ Token is required!")
        return None, None
    
    # Test credentials
    print("\n🔍 Testing credentials...")
    if not test_credentials(api_key, token):
        print("❌ Failed to validate credentials. Please check and try again.")
        return None, None
    
    # Save credentials
    print("\n💾 Where would you like to save the credentials?")
    print("1. Environment file (.env) - Recommended for project")
    print("2. Shell configuration (~/.zshrc or ~/.bashrc)")
    print("3. Both")
    print("4. Don't save (just display)")
    
    choice = input("\nChoice (1-4): ").strip()
    
    if choice == '1' or choice == '3':
        save_to_env_file(api_key, token)
    
    if choice == '2' or choice == '3':
        save_to_shell_config(api_key, token)
    
    if choice == '4':
        print("\n📝 Add these to your environment:")
        print(f"export TRELLO_API_KEY='{api_key}'")
        print(f"export TRELLO_TOKEN='{token}'")
    
    return api_key, token


def verify_board_access(api_key: str, token: str):
    """Verify access to the Virtuoso board."""
    print("\n🔍 Checking board access...")
    
    # Get all boards
    url = f"https://api.trello.com/1/members/me/boards?key={api_key}&token={token}"
    response = requests.get(url)
    
    if response.status_code != 200:
        print("❌ Failed to get boards")
        return
    
    boards = response.json()
    virtuoso_board = None
    
    print("\n📋 Your Trello boards:")
    for board in boards:
        print(f"   - {board['name']} (ID: {board['id']})")
        if 'virtuoso' in board['name'].lower():
            virtuoso_board = board
    
    if virtuoso_board:
        print(f"\n✅ Found Virtuoso board: {virtuoso_board['name']} (ID: {virtuoso_board['id']})")
        
        # Get lists
        lists_url = f"https://api.trello.com/1/boards/{virtuoso_board['id']}/lists?key={api_key}&token={token}"
        lists_response = requests.get(lists_url)
        
        if lists_response.status_code == 200:
            lists = lists_response.json()
            print("\n📑 Lists in Virtuoso board:")
            for lst in lists:
                # Get card count
                cards_url = f"https://api.trello.com/1/lists/{lst['id']}/cards?key={api_key}&token={token}"
                cards_response = requests.get(cards_url)
                card_count = len(cards_response.json()) if cards_response.status_code == 200 else 0
                print(f"   - {lst['name']} ({card_count} cards)")
    else:
        print("\n⚠️  No board with 'virtuoso' in the name found")
        board_id = input("Enter your Virtuoso board ID (or press Enter to skip): ").strip()
        if board_id:
            print(f"\n💡 Add this to your scripts: board_id = '{board_id}'")


def main():
    """Main setup process."""
    print("=" * 50)
    print("🚀 Virtuoso Trello Integration Setup")
    print("=" * 50)
    
    api_key, token = setup_credentials()
    
    if api_key and token:
        verify_board_access(api_key, token)
        
        print("\n✅ Setup complete!")
        print("\n📚 Next steps:")
        print("1. Test the integration:")
        print("   python scripts/trello_sync_tasks.py")
        print("\n2. View available commands:")
        print("   python scripts/trello_integration.py")
        print("\n3. Create custom automations using the TrelloIntegration class")
    else:
        print("\n❌ Setup incomplete. Please run again with valid credentials.")


if __name__ == '__main__':
    main()