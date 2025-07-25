#!/usr/bin/env python3
"""
Daily Standup Generator for Virtuoso Project
Automatically generates daily progress reports from Trello
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.trello_integration import TrelloIntegration


class DailyStandup:
    """Generate daily standup reports from Trello activity."""
    
    def __init__(self, board_id: str = 'YBgMusBE'):
        self.board_id = board_id
        self.trello = TrelloIntegration()
        
    def get_recent_activity(self, hours: int = 24) -> Dict:
        """Get card movements and updates from the last N hours."""
        # Get board activity
        actions = self.trello.get_board_activity(self.board_id, limit=100)
        
        # Filter by time
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_actions = []
        
        for action in actions:
            action_date = datetime.fromisoformat(action['date'].replace('Z', '+00:00'))
            if action_date > cutoff_time:
                recent_actions.append(action)
            else:
                break  # Actions are in reverse chronological order
        
        # Categorize actions
        activity = {
            'cards_completed': [],
            'cards_started': [],
            'cards_created': [],
            'cards_updated': [],
            'comments_added': []
        }
        
        for action in recent_actions:
            action_type = action['type']
            
            if action_type == 'updateCard':
                if 'listAfter' in action['data'] and 'listBefore' in action['data']:
                    list_after = action['data']['listAfter']['name']
                    list_before = action['data']['listBefore']['name']
                    card_name = action['data']['card']['name']
                    
                    if 'done' in list_after.lower():
                        activity['cards_completed'].append({
                            'name': card_name,
                            'from_list': list_before,
                            'time': action['date']
                        })
                    elif 'doing' in list_after.lower():
                        activity['cards_started'].append({
                            'name': card_name,
                            'from_list': list_before,
                            'time': action['date']
                        })
                else:
                    # Other updates (description, due date, etc.)
                    if 'card' in action['data']:
                        activity['cards_updated'].append({
                            'name': action['data']['card']['name'],
                            'type': 'update',
                            'time': action['date']
                        })
            
            elif action_type == 'createCard':
                activity['cards_created'].append({
                    'name': action['data']['card']['name'],
                    'list': action['data']['list']['name'],
                    'time': action['date']
                })
            
            elif action_type == 'commentCard':
                activity['comments_added'].append({
                    'card': action['data']['card']['name'],
                    'text': action['data']['text'][:100] + '...' if len(action['data'].get('text', '')) > 100 else action['data'].get('text', ''),
                    'time': action['date']
                })
        
        return activity
    
    def get_current_status(self) -> Dict:
        """Get current board status."""
        lists = self.trello.get_lists(self.board_id)
        cards = self.trello.get_cards(self.board_id)
        
        # Create list lookup
        list_lookup = {lst['id']: lst['name'] for lst in lists}
        
        # Categorize cards
        status = {
            'in_progress': [],
            'todo_urgent': [],
            'blocked': [],
            'review': []
        }
        
        for card in cards:
            list_name = list_lookup.get(card['idList'], '').lower()
            
            # In progress cards
            if 'doing' in list_name:
                status['in_progress'].append({
                    'name': card['name'],
                    'due': card.get('due'),
                    'labels': [l['name'] for l in card.get('labels', []) if l.get('name')]
                })
            
            # Urgent todos (due soon or overdue)
            elif any(x in list_name for x in ['todo', 'to do']):
                if card.get('due'):
                    due_date = datetime.fromisoformat(card['due'].replace('Z', '+00:00'))
                    if (due_date - datetime.now()).days <= 3:
                        status['todo_urgent'].append({
                            'name': card['name'],
                            'due': card['due'],
                            'days_until': (due_date - datetime.now()).days
                        })
                
                # Check for blocked label
                if any(label.get('name', '').lower() == 'blocked' for label in card.get('labels', [])):
                    status['blocked'].append({
                        'name': card['name'],
                        'list': list_lookup.get(card['idList'], '')
                    })
        
        return status
    
    def generate_standup_report(self, hours: int = 24) -> str:
        """Generate a formatted standup report."""
        activity = self.get_recent_activity(hours)
        status = self.get_current_status()
        
        report = []
        report.append(f"# Daily Standup - {datetime.now().strftime('%Y-%m-%d')}")
        report.append(f"\n*Generated at {datetime.now().strftime('%H:%M')}*\n")
        
        # Yesterday's accomplishments
        report.append("## 🎯 Completed (Last 24 hours)")
        if activity['cards_completed']:
            for card in activity['cards_completed']:
                report.append(f"- ✅ {card['name']}")
        else:
            report.append("- No cards completed")
        
        # Currently working on
        report.append("\n## 🔄 In Progress")
        if status['in_progress']:
            for card in status['in_progress']:
                due_str = ""
                if card['due']:
                    due_date = datetime.fromisoformat(card['due'].replace('Z', '+00:00'))
                    days_left = (due_date - datetime.now()).days
                    if days_left < 0:
                        due_str = f" **[OVERDUE by {abs(days_left)} days]**"
                    elif days_left <= 3:
                        due_str = f" **[Due in {days_left} days]**"
                
                report.append(f"- {card['name']}{due_str}")
        else:
            report.append("- No cards currently in progress")
        
        # Blockers
        if status['blocked']:
            report.append("\n## 🚧 Blockers")
            for card in status['blocked']:
                report.append(f"- {card['name']} (in {card['list']})")
        
        # Today's plan
        report.append("\n## 📋 Today's Plan")
        if status['todo_urgent']:
            for card in status['todo_urgent']:
                urgency = "OVERDUE" if card['days_until'] < 0 else f"Due in {card['days_until']} days"
                report.append(f"- {card['name']} **[{urgency}]**")
        
        # New items created
        if activity['cards_created']:
            report.append("\n## 🆕 New Tasks Added")
            for card in activity['cards_created']:
                report.append(f"- {card['name']} (added to {card['list']})")
        
        # Metrics
        report.append("\n## 📊 24-Hour Metrics")
        report.append(f"- Cards completed: {len(activity['cards_completed'])}")
        report.append(f"- Cards started: {len(activity['cards_started'])}")
        report.append(f"- New cards created: {len(activity['cards_created'])}")
        report.append(f"- Comments added: {len(activity['comments_added'])}")
        
        # Velocity trend (if we have historical data)
        report.append("\n## 📈 Weekly Velocity")
        weekly_completed = self._calculate_weekly_velocity()
        report.append(f"- This week: {weekly_completed['this_week']} cards completed")
        report.append(f"- Last week: {weekly_completed['last_week']} cards completed")
        if weekly_completed['this_week'] > weekly_completed['last_week']:
            report.append("- Trend: ⬆️ Increasing velocity")
        elif weekly_completed['this_week'] < weekly_completed['last_week']:
            report.append("- Trend: ⬇️ Decreasing velocity")
        else:
            report.append("- Trend: ➡️ Stable velocity")
        
        return '\n'.join(report)
    
    def _calculate_weekly_velocity(self) -> Dict:
        """Calculate cards completed this week vs last week."""
        # Get activity for past 2 weeks
        actions = self.trello.get_board_activity(self.board_id, limit=500)
        
        now = datetime.now()
        week_start = now - timedelta(days=now.weekday())  # Monday
        last_week_start = week_start - timedelta(days=7)
        two_weeks_ago = last_week_start - timedelta(days=7)
        
        this_week_count = 0
        last_week_count = 0
        
        for action in actions:
            if action['type'] == 'updateCard' and 'listAfter' in action['data']:
                if 'done' in action['data']['listAfter']['name'].lower():
                    action_date = datetime.fromisoformat(action['date'].replace('Z', '+00:00'))
                    
                    if action_date >= week_start:
                        this_week_count += 1
                    elif action_date >= last_week_start:
                        last_week_count += 1
                    elif action_date < two_weeks_ago:
                        break  # No need to look further back
        
        return {
            'this_week': this_week_count,
            'last_week': last_week_count
        }
    
    def send_to_discord(self, webhook_url: str, report: str):
        """Send standup report to Discord."""
        import requests
        
        # Split report into sections for better Discord formatting
        sections = report.split('\n## ')
        
        embeds = []
        for section in sections[1:]:  # Skip the title
            lines = section.split('\n')
            title = lines[0]
            content = '\n'.join(lines[1:])[:1024]  # Discord embed limit
            
            embeds.append({
                "title": title,
                "description": content,
                "color": 0x2ecc71 if '✅' in title else 0x3498db
            })
        
        webhook_data = {
            "content": f"**Daily Standup - {datetime.now().strftime('%Y-%m-%d')}**",
            "embeds": embeds[:10]  # Discord limit
        }
        
        response = requests.post(webhook_url, json=webhook_data)
        return response.status_code == 204


def main():
    """Generate and save daily standup."""
    standup = DailyStandup()
    
    # Generate report
    report = standup.generate_standup_report()
    
    # Save to file
    os.makedirs('reports/standups', exist_ok=True)
    filename = f"reports/standups/standup_{datetime.now().strftime('%Y%m%d')}.md"
    
    with open(filename, 'w') as f:
        f.write(report)
    
    print(f"✅ Standup report saved to {filename}")
    print("\n" + "="*50)
    print(report)
    print("="*50)
    
    # Optional: Send to Discord
    discord_webhook = os.environ.get('DISCORD_STANDUP_WEBHOOK')
    if discord_webhook:
        if standup.send_to_discord(discord_webhook, report):
            print("\n✅ Report sent to Discord")
        else:
            print("\n❌ Failed to send to Discord")


if __name__ == '__main__':
    main()