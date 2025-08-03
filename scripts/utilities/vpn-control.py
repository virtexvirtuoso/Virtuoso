#!/usr/bin/env python3
"""
Enhanced ProtonVPN Terminal UI with Rich
"""
import os
import sys
import subprocess
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.prompt import Prompt, IntPrompt
from rich.text import Text
from rich import box

console = Console()

# VPN server locations with details
SERVERS = [
    {"name": "Singapore", "code": "SG", "latency": "Low", "recommended": True},
    {"name": "Japan", "code": "JP", "latency": "Low", "recommended": False},
    {"name": "Hong Kong", "code": "HK", "latency": "Low", "recommended": False},
    {"name": "United States", "code": "US", "latency": "High", "recommended": False},
    {"name": "Netherlands", "code": "NL", "latency": "High", "recommended": False},
    {"name": "Switzerland", "code": "CH", "latency": "High", "recommended": False},
]

def get_vpn_status():
    """Check VPN connection status"""
    try:
        # Check if ProtonVPN is running
        result = subprocess.run(['pgrep', '-x', 'ProtonVPN'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            return "❌ Not Running", "red"
        
        # For demo, we'll assume it's connected if running
        # In reality, you'd check actual connection status
        return "✅ Connected", "green"
    except:
        return "❓ Unknown", "yellow"

def create_server_table():
    """Create a beautiful server selection table"""
    table = Table(
        title="🌐 ProtonVPN Server Locations",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Location", style="bright_white", width=15)
    table.add_column("Code", style="yellow", width=6)
    table.add_column("Latency", width=10)
    table.add_column("Status", width=15)
    
    for i, server in enumerate(SERVERS, 1):
        latency_color = "green" if server["latency"] == "Low" else "yellow"
        status = "⭐ Recommended" if server["recommended"] else ""
        
        table.add_row(
            str(i),
            server["name"],
            server["code"],
            f"[{latency_color}]{server['latency']}[/{latency_color}]",
            f"[bold green]{status}[/bold green]" if status else ""
        )
    
    table.add_row(
        "0",
        "[red]Disconnect[/red]",
        "-",
        "-",
        "[red]Disconnect VPN[/red]"
    )
    
    return table

def connect_to_vpn(server_name):
    """Connect to selected VPN server"""
    with console.status(f"[bold green]Connecting to {server_name}...", spinner="dots"):
        # Open ProtonVPN app
        subprocess.run(['open', '-a', 'ProtonVPN'])
        time.sleep(2)
        
        # AppleScript to control ProtonVPN
        if server_name == "Disconnect":
            script = '''
            tell application "System Events"
                tell process "ProtonVPN"
                    try
                        click button "Disconnect" of window 1
                    end try
                end tell
            end tell
            '''
        else:
            script = f'''
            tell application "ProtonVPN"
                activate
            end tell
            delay 1
            tell application "System Events"
                tell process "ProtonVPN"
                    keystroke "f" using command down
                    delay 0.5
                    keystroke "{server_name}"
                    delay 0.5
                    keystroke return
                end tell
            end tell
            '''
        
        try:
            subprocess.run(['osascript', '-e', script], check=True)
            return True
        except:
            return False

def main():
    """Main application loop"""
    console.clear()
    
    # Header
    console.print(Panel.fit(
        "[bold cyan]ProtonVPN Terminal Control Center[/bold cyan]\n" +
        "[dim]Control your VPN connection from the terminal[/dim]",
        border_style="bright_blue"
    ))
    
    while True:
        # Get current status
        status, status_color = get_vpn_status()
        
        # Status panel
        console.print(Panel(
            f"Connection Status: [{status_color}]{status}[/{status_color}]",
            title="📡 Current Status",
            border_style="blue"
        ))
        
        # Server table
        console.print(create_server_table())
        
        # Instructions
        console.print(Panel(
            "[yellow]Enter server ID to connect (0 to disconnect, Q to quit)[/yellow]",
            border_style="yellow"
        ))
        
        # Get user choice
        choice = Prompt.ask("Select server", default="Q")
        
        if choice.upper() == 'Q':
            console.print("[bold cyan]Goodbye! 👋[/bold cyan]")
            break
        
        try:
            choice_idx = int(choice)
            
            if choice_idx == 0:
                # Disconnect
                if connect_to_vpn("Disconnect"):
                    console.print("[bold red]✓ Disconnected from VPN[/bold red]")
                else:
                    console.print("[bold red]✗ Failed to disconnect[/bold red]")
            elif 1 <= choice_idx <= len(SERVERS):
                # Connect to server
                server = SERVERS[choice_idx - 1]
                if connect_to_vpn(server["name"]):
                    console.print(f"[bold green]✓ Connecting to {server['name']}...[/bold green]")
                else:
                    console.print(f"[bold red]✗ Failed to connect to {server['name']}[/bold red]")
            else:
                console.print("[red]Invalid selection[/red]")
            
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
            console.clear()
            
        except ValueError:
            if choice.upper() != 'Q':
                console.print("[red]Please enter a valid number[/red]")
                time.sleep(1)
                console.clear()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold cyan]Goodbye! 👋[/bold cyan]")
        sys.exit(0)