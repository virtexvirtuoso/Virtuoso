#!/usr/bin/env python3
"""
Preview what the Discord market report format would look like
Generate a sample report and show the Discord formatting
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime
import json

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

async def generate_sample_market_report():
    """Generate a sample market report to preview the format"""
    print("📊 Generating Sample Market Report")
    print("=" * 60)
    
    try:
        from monitoring.market_reporter import MarketReporter
        from monitoring.alert_manager import AlertManager
        
        # Create config for alert manager
        config = {
            'monitoring': {
                'alerts': {
                    'discord_webhook': {
                        'max_retries': 3,
                        'timeout_seconds': 30,
                        'exponential_backoff': True
                    }
                }
            }
        }
        
        # Initialize components
        alert_manager = AlertManager(config)
        reporter = MarketReporter(alert_manager=alert_manager)
        
        print("🔄 Generating comprehensive market summary...")
        
        # Generate a real market report (this will use mock/fallback data if APIs aren't available)
        market_report = await reporter.generate_market_summary()
        
        if market_report:
            print("✅ Market report generated successfully!")
            print(f"📋 Report sections: {list(market_report.keys())}")
            
            # Show the raw report structure
            print("\n" + "="*60)
            print("📄 RAW MARKET REPORT STRUCTURE")
            print("="*60)
            
            for section, data in market_report.items():
                print(f"\n🔸 {section.upper()}:")
                if isinstance(data, dict):
                    for key, value in list(data.items())[:3]:  # Show first 3 items
                        if isinstance(value, (str, int, float)):
                            print(f"   {key}: {value}")
                        elif isinstance(value, dict):
                            print(f"   {key}: {{dict with {len(value)} items}}")
                        elif isinstance(value, list):
                            print(f"   {key}: [list with {len(value)} items]")
                        else:
                            print(f"   {key}: {type(value).__name__}")
                    if len(data) > 3:
                        print(f"   ... and {len(data) - 3} more items")
                else:
                    print(f"   {type(data).__name__}: {str(data)[:100]}...")
            
            return market_report
        else:
            print("❌ Failed to generate market report")
            return None
            
    except Exception as e:
        print(f"❌ Error generating market report: {e}")
        import traceback
        traceback.print_exc()
        return None

async def format_for_discord_preview(market_report):
    """Format the market report for Discord and show preview"""
    print("\n" + "="*60)
    print("🎨 DISCORD FORMATTING PREVIEW")
    print("="*60)
    
    try:
        
        # Create config
        config = {
            'monitoring': {
                'alerts': {
                    'discord_webhook': {
                        'max_retries': 3,
                        'timeout_seconds': 30
                    }
                }
            }
        }
        
        # Initialize components
        alert_manager = AlertManager(config)
        reporter = MarketReporter(alert_manager=alert_manager)
        
        # Extract data for formatting
        market_overview = market_report.get('market_overview', {})
        smart_money = market_report.get('smart_money_index', {})
        whale_activity = market_report.get('whale_activity', {})
        top_pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT']
        
        print("🔄 Formatting market report for Discord...")
        
        # Use the actual Discord formatting method
        formatted_report = await reporter.format_market_report(
            overview=market_overview,
            top_pairs=top_pairs,
            market_regime=market_overview.get('regime', 'Unknown'),
            smart_money=smart_money,
            whale_activity=whale_activity
        )
        
        if formatted_report:
            print("✅ Discord formatting completed!")
            
            # Show the Discord message structure
            print(f"\n📨 Discord Message Structure:")
            print(f"   Content: {len(formatted_report.get('content', ''))} characters")
            print(f"   Embeds: {len(formatted_report.get('embeds', []))} embed(s)")
            
            # Show the main content
            if 'content' in formatted_report and formatted_report['content']:
                print(f"\n💬 **MAIN MESSAGE CONTENT:**")
                print(f"```")
                print(formatted_report['content'])
                print(f"```")
            
            # Show each embed
            if 'embeds' in formatted_report:
                for i, embed in enumerate(formatted_report['embeds'], 1):
                    print(f"\n📋 **EMBED {i}:**")
                    print(f"   Title: {embed.get('title', 'No title')}")
                    print(f"   Description: {embed.get('description', 'No description')[:100]}...")
                    print(f"   Color: #{embed.get('color', 0):06x}")
                    print(f"   Fields: {len(embed.get('fields', []))}")
                    
                    # Show fields
                    if 'fields' in embed:
                        for j, field in enumerate(embed['fields'][:3], 1):  # Show first 3 fields
                            name = field.get('name', 'No name')
                            value = field.get('value', 'No value')
                            inline = field.get('inline', False)
                            print(f"     Field {j}: {name} = {value} (inline: {inline})")
                        if len(embed['fields']) > 3:
                            print(f"     ... and {len(embed['fields']) - 3} more fields")
            
            return formatted_report
        else:
            print("❌ Failed to format for Discord")
            return None
            
    except Exception as e:
        print(f"❌ Error formatting for Discord: {e}")
        import traceback
        traceback.print_exc()
        return None

async def preview_actual_discord_appearance(formatted_report):
    """Show how the message would actually appear in Discord"""
    print("\n" + "="*60)
    print("👀 HOW IT LOOKS IN DISCORD")
    print("="*60)
    
    if not formatted_report:
        print("❌ No formatted report to preview")
        return
    
    # Simulate Discord appearance
    print("📱 **Discord Channel Preview:**")
    print("─" * 50)
    
    # Main content
    if 'content' in formatted_report and formatted_report['content']:
        print(formatted_report['content'])
        print()
    
    # Each embed as it would appear
    if 'embeds' in formatted_report:
        for i, embed in enumerate(formatted_report['embeds'], 1):
            # Embed border (simulated)
            color_code = embed.get('color', 0)
            print(f"┃  **{embed.get('title', 'Untitled')}**")
            if 'description' in embed:
                print(f"┃  {embed['description']}")
            print("┃")
            
            # Fields
            if 'fields' in embed:
                # Group inline fields
                inline_group = []
                for field in embed['fields']:
                    if field.get('inline', False):
                        inline_group.append(field)
                        if len(inline_group) == 3:  # Discord shows 3 inline fields per row
                            # Show inline fields side by side (simulated)
                            names = [f"**{f['name']}**" for f in inline_group]
                            values = [f"{f['value']}" for f in inline_group]
                            print(f"┃  {' | '.join(names)}")
                            print(f"┃  {' | '.join(values)}")
                            inline_group = []
                    else:
                        # Show any remaining inline fields first
                        if inline_group:
                            names = [f"**{f['name']}**" for f in inline_group]
                            values = [f"{f['value']}" for f in inline_group]
                            print(f"┃  {' | '.join(names)}")
                            print(f"┃  {' | '.join(values)}")
                            inline_group = []
                        
                        # Show non-inline field
                        print(f"┃  **{field['name']}**")
                        print(f"┃  {field['value']}")
                
                # Show any remaining inline fields
                if inline_group:
                    names = [f"**{f['name']}**" for f in inline_group]
                    values = [f"{f['value']}" for f in inline_group]
                    print(f"┃  {' | '.join(names)}")
                    print(f"┃  {' | '.join(values)}")
            
            print("┃")
            if i < len(formatted_report['embeds']):
                print("┃")  # Space between embeds
    
    print("─" * 50)
    print("🤖 VirtuosoBot - Today at", datetime.now().strftime("%I:%M %p"))

async def save_sample_report(market_report, formatted_report):
    """Save sample reports for inspection"""
    print("\n" + "="*60)
    print("💾 SAVING SAMPLE REPORTS")
    print("="*60)
    
    try:
        # Create output directory
        output_dir = Path("sample_reports")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw market report
        if market_report:
            raw_file = output_dir / f"raw_market_report_{timestamp}.json"
            with open(raw_file, 'w') as f:
                json.dump(market_report, f, indent=2, default=str)
            print(f"✅ Raw report saved: {raw_file}")
        
        # Save formatted Discord report
        if formatted_report:
            discord_file = output_dir / f"discord_formatted_report_{timestamp}.json"
            with open(discord_file, 'w') as f:
                json.dump(formatted_report, f, indent=2, default=str)
            print(f"✅ Discord format saved: {discord_file}")
            
            # Save as human-readable text
            text_file = output_dir / f"discord_preview_{timestamp}.txt"
            with open(text_file, 'w') as f:
                f.write("DISCORD MARKET REPORT PREVIEW\n")
                f.write("=" * 40 + "\n\n")
                
                if formatted_report.get('content'):
                    f.write(f"MAIN MESSAGE:\n{formatted_report['content']}\n\n")
                
                for i, embed in enumerate(formatted_report.get('embeds', []), 1):
                    f.write(f"EMBED {i}:\n")
                    f.write(f"Title: {embed.get('title', 'No title')}\n")
                    f.write(f"Description: {embed.get('description', 'No description')}\n")
                    f.write(f"Fields:\n")
                    for field in embed.get('fields', []):
                        f.write(f"  - {field.get('name', 'No name')}: {field.get('value', 'No value')}\n")
                    f.write("\n")
            
            print(f"✅ Human-readable preview saved: {text_file}")
        
    except Exception as e:
        print(f"⚠️ Error saving files: {e}")

async def main():
    """Main preview function"""
    print("🎨 Discord Market Report Format Preview")
    print("=" * 80)
    
    # Set up logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise
    
    # Generate sample report
    market_report = await generate_sample_market_report()
    
    if not market_report:
        print("❌ Cannot preview format without a market report")
        return
    
    # Format for Discord
    formatted_report = await format_for_discord_preview(market_report)
    
    if not formatted_report:
        print("❌ Cannot preview Discord format")
        return
    
    # Show Discord appearance preview
    await preview_actual_discord_appearance(formatted_report)
    
    # Save samples
    await save_sample_report(market_report, formatted_report)
    
    print("\n" + "=" * 80)
    print("✅ PREVIEW COMPLETE")
    print("=" * 80)
    print("📋 What you've seen:")
    print("   • Raw market report data structure")
    print("   • Discord formatting process")
    print("   • Actual Discord message appearance simulation")
    print("   • Sample files saved for inspection")
    print()
    print("🚀 This is exactly what gets sent to Discord during scheduled reports!")
    print("   Run 'python src/main.py' to start receiving these automatically")

if __name__ == "__main__":
    asyncio.run(main())