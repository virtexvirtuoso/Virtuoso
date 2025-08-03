#!/usr/bin/env python3
"""
ProtonVPN Terminal UI Controller
"""
import os
import sys
import subprocess
import time
from typing import List, Tuple

# ANSI color codes
BLUE = '\033[94m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'

# VPN server locations
SERVERS = [
    ("Singapore", "SG"),
    ("Japan", "JP"),
    ("Hong Kong", "HK"),
    ("United States", "US"),
    ("Netherlands", "NL"),
    ("Switzerland", "CH"),
    ("Disconnect", "DISCONNECT")
]

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def print_header():
    """Print the header"""
    clear_screen()
    print(f"{CYAN}{BOLD}")
    print("╔═══════════════════════════════════════╗")
    print("║       ProtonVPN Terminal Control      ║")
    print("╚═══════════════════════════════════════╝")
    print(f"{RESET}\n")

def get_vpn_status() -> str:
    """Check if ProtonVPN is running and connected"""
    try:
        # Check if ProtonVPN app is running
        result = subprocess.run(['pgrep', '-x', 'ProtonVPN'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            return "Not Running"
        
        # Try to get connection status via AppleScript
        script = '''
        tell application "System Events"
            if exists process "ProtonVPN" then
                return "Running"
            else
                return "Not Running"
            end if
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True)
        return "Connected" if "Running" in result.stdout else "Disconnected"
    except:
        return "Unknown"

def print_menu(current_status: str):
    """Print the server selection menu"""
    print(f"{YELLOW}Current Status: {GREEN if 'Connected' in current_status else RED}{current_status}{RESET}\n")
    print(f"{BOLD}Select a Server Location:{RESET}\n")
    
    for i, (location, code) in enumerate(SERVERS, 1):
        if location == "Singapore":
            print(f"{GREEN}  {i}. {location} (Recommended for Trading){RESET}")
        elif location == "Disconnect":
            print(f"{RED}  {i}. {location}{RESET}")
        else:
            print(f"  {i}. {location}")
    
    print(f"\n  {YELLOW}0. Exit{RESET}")

def connect_to_server(location: str):
    """Connect to selected VPN server using AppleScript"""
    print(f"\n{YELLOW}Connecting to {location}...{RESET}")
    
    if location == "Disconnect":
        script = '''
        tell application "ProtonVPN"
            activate
        end tell
        delay 1
        tell application "System Events"
            tell process "ProtonVPN"
                try
                    click button "Disconnect" of window 1
                end try
            end tell
        end tell
        '''
    else:
        # First ensure ProtonVPN is open
        subprocess.run(['open', '-a', 'ProtonVPN'])
        time.sleep(2)
        
        script = f'''
        tell application "ProtonVPN"
            activate
        end tell
        delay 2
        tell application "System Events"
            tell process "ProtonVPN"
                try
                    -- Try to open country list
                    click button "Quick Connect" of window 1
                    delay 1
                end try
                
                -- Search for country
                keystroke "f" using command down
                delay 0.5
                keystroke "{location}"
                delay 1
                keystroke return
                delay 0.5
                
                -- Click connect button
                try
                    click button "Connect" of window 1
                end try
            end tell
        end tell
        '''
    
    try:
        subprocess.run(['osascript', '-e', script], check=True)
        print(f"{GREEN}✓ Command sent successfully!{RESET}")
        print(f"{YELLOW}Please check ProtonVPN window to confirm connection.{RESET}")
    except subprocess.CalledProcessError:
        print(f"{RED}✗ Failed to send command. Please connect manually.{RESET}")
    except Exception as e:
        print(f"{RED}✗ Error: {e}{RESET}")

def main():
    """Main menu loop"""
    while True:
        print_header()
        status = get_vpn_status()
        print_menu(status)
        
        try:
            choice = input(f"\n{BOLD}Enter your choice (0-{len(SERVERS)}): {RESET}")
            
            if choice == '0':
                print(f"\n{CYAN}Goodbye!{RESET}")
                break
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(SERVERS):
                location, code = SERVERS[choice_idx]
                connect_to_server(location)
                input(f"\n{YELLOW}Press Enter to continue...{RESET}")
            else:
                print(f"{RED}Invalid choice. Please try again.{RESET}")
                time.sleep(1)
                
        except ValueError:
            print(f"{RED}Invalid input. Please enter a number.{RESET}")
            time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n\n{CYAN}Goodbye!{RESET}")
            break

if __name__ == "__main__":
    # Check if running on macOS
    if sys.platform != 'darwin':
        print(f"{RED}This script is designed for macOS with ProtonVPN app.{RESET}")
        sys.exit(1)
    
    # Check if ProtonVPN app is installed
    if not os.path.exists('/Applications/ProtonVPN.app'):
        print(f"{RED}ProtonVPN app not found. Please install it first.{RESET}")
        sys.exit(1)
    
    main()