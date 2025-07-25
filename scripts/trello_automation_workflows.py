#!/usr/bin/env python3
"""
Automated Trello Workflows for Virtuoso Project
Includes task automation, progress tracking, and smart suggestions
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.trello_integration import TrelloIntegration


class TrelloAutomation:
    """Automated workflows for Trello board management."""
    
    def __init__(self, board_id: str = 'YBgMusBE'):
        self.board_id = board_id
        self.trello = TrelloIntegration()
        self._cache_lists()
    
    def _cache_lists(self):
        """Cache list IDs for quick access."""
        lists = self.trello.get_lists(self.board_id)
        self.list_ids = {}
        for lst in lists:
            name_lower = lst['name'].lower()
            if 'todo' in name_lower or 'to do' in name_lower:
                self.list_ids['todo'] = lst['id']
            elif 'doing' in name_lower:
                self.list_ids['doing'] = lst['id']
            elif 'done' in name_lower:
                self.list_ids['done'] = lst['id']
            elif 'blocked' in name_lower:
                self.list_ids['blocked'] = lst['id']
            
            # Store all lists by exact name too
            self.list_ids[lst['name']] = lst['id']
    
    async def auto_prioritize_tasks(self):
        """Automatically add priority labels based on task characteristics."""
        cards = self.trello.get_cards(self.board_id)
        updates_made = 0
        
        for card in cards:
            # Skip if already has priority label
            existing_labels = [l['color'] for l in card.get('labels', [])]
            if any(color in ['red', 'orange', 'yellow'] for color in existing_labels):
                continue
            
            # Determine priority
            priority = self._calculate_auto_priority(card)
            
            if priority == 'critical':
                # Add red label
                self.trello.update_card(card['id'], idLabels=','.join(existing_labels + ['red']))
                updates_made += 1
            elif priority == 'high':
                # Add orange label
                self.trello.update_card(card['id'], idLabels=','.join(existing_labels + ['orange']))
                updates_made += 1
            elif priority == 'medium':
                # Add yellow label
                self.trello.update_card(card['id'], idLabels=','.join(existing_labels + ['yellow']))
                updates_made += 1
        
        return updates_made
    
    def _calculate_auto_priority(self, card: Dict) -> str:
        """Calculate priority based on card attributes."""
        text = (card.get('name', '') + ' ' + card.get('desc', '')).lower()
        
        # Critical keywords
        if any(word in text for word in ['critical', 'urgent', 'broken', 'fix', 'bug', 'crash', 'error']):
            return 'critical'
        
        # Due date check
        if card.get('due'):
            due_date = datetime.fromisoformat(card['due'].replace('Z', '+00:00'))
            days_until = (due_date - datetime.now()).days
            if days_until < 0:
                return 'critical'
            elif days_until <= 3:
                return 'high'
            elif days_until <= 7:
                return 'medium'
        
        # High priority keywords
        if any(word in text for word in ['high priority', 'important', 'asap']):
            return 'high'
        
        # In doing list
        if card['idList'] == self.list_ids.get('doing'):
            return 'high'
        
        return 'low'
    
    async def move_overdue_cards(self):
        """Move overdue cards to a special attention list or add labels."""
        cards = self.trello.get_cards(self.board_id)
        overdue_cards = []
        
        for card in cards:
            if card.get('due') and card['idList'] != self.list_ids.get('done'):
                due_date = datetime.fromisoformat(card['due'].replace('Z', '+00:00'))
                if due_date < datetime.now():
                    overdue_cards.append(card)
        
        for card in overdue_cards:
            # Add overdue comment
            self.trello.add_comment(
                card['id'],
                f"⚠️ This card is overdue by {(datetime.now() - datetime.fromisoformat(card['due'].replace('Z', '+00:00'))).days} days"
            )
            
            # Add red label if not present
            if not any(l['color'] == 'red' for l in card.get('labels', [])):
                labels = [l['id'] for l in card.get('labels', [])]
                # Note: You'd need to get the actual label ID for red label
                # This is a simplified version
                self.trello.update_card(card['id'], name=f"[OVERDUE] {card['name']}")
        
        return len(overdue_cards)
    
    async def suggest_next_tasks(self, max_tasks: int = 5) -> List[Dict]:
        """Suggest next tasks based on priority and current workload."""
        cards = self.trello.get_cards(self.board_id)
        
        # Count current workload
        in_progress = sum(1 for c in cards if c['idList'] == self.list_ids.get('doing'))
        
        if in_progress >= 3:
            return [{
                'suggestion': 'High workload detected',
                'message': f"You have {in_progress} tasks in progress. Consider completing some before starting new ones.",
                'cards': []
            }]
        
        # Find best candidates
        todo_cards = [c for c in cards if c['idList'] == self.list_ids.get('todo')]
        
        # Score each card
        scored_cards = []
        for card in todo_cards:
            score = 0
            
            # Due date scoring
            if card.get('due'):
                due_date = datetime.fromisoformat(card['due'].replace('Z', '+00:00'))
                days_until = (due_date - datetime.now()).days
                if days_until < 0:
                    score += 1000  # Overdue
                elif days_until <= 3:
                    score += 500
                elif days_until <= 7:
                    score += 200
                else:
                    score += 50
            
            # Label scoring
            for label in card.get('labels', []):
                if label['color'] == 'red':
                    score += 300
                elif label['color'] == 'orange':
                    score += 200
                elif label['color'] == 'yellow':
                    score += 100
            
            # Keyword scoring
            text = card['name'].lower()
            if any(word in text for word in ['fix', 'bug', 'broken']):
                score += 250
            if any(word in text for word in ['deploy', 'production']):
                score += 150
            
            scored_cards.append((score, card))
        
        # Sort by score
        scored_cards.sort(key=lambda x: x[0], reverse=True)
        
        suggestions = []
        for score, card in scored_cards[:max_tasks]:
            reason = self._get_suggestion_reason(card, score)
            suggestions.append({
                'card': card['name'],
                'score': score,
                'reason': reason,
                'id': card['id']
            })
        
        return suggestions
    
    def _get_suggestion_reason(self, card: Dict, score: int) -> str:
        """Generate human-readable reason for suggestion."""
        reasons = []
        
        if card.get('due'):
            due_date = datetime.fromisoformat(card['due'].replace('Z', '+00:00'))
            days_until = (due_date - datetime.now()).days
            if days_until < 0:
                reasons.append(f"Overdue by {abs(days_until)} days")
            elif days_until <= 3:
                reasons.append(f"Due in {days_until} days")
        
        if any(l['color'] == 'red' for l in card.get('labels', [])):
            reasons.append("High priority")
        
        text = card['name'].lower()
        if any(word in text for word in ['fix', 'bug']):
            reasons.append("Bug fix")
        
        return " | ".join(reasons) if reasons else "Good next task"
    
    async def generate_sprint_plan(self, sprint_days: int = 7) -> Dict:
        """Generate a sprint plan based on velocity and priorities."""
        # Calculate velocity
        velocity = self._calculate_velocity(sprint_days)
        
        # Get available tasks
        cards = self.trello.get_cards(self.board_id)
        todo_cards = [c for c in cards if c['idList'] == self.list_ids.get('todo')]
        
        # Score and select tasks for sprint
        suggestions = await self.suggest_next_tasks(max_tasks=velocity * 2)
        
        sprint_tasks = suggestions[:velocity]
        
        sprint_plan = {
            'sprint_start': datetime.now().strftime('%Y-%m-%d'),
            'sprint_end': (datetime.now() + timedelta(days=sprint_days)).strftime('%Y-%m-%d'),
            'velocity_target': velocity,
            'selected_tasks': sprint_tasks,
            'total_points': sum(s['score'] for s in sprint_tasks),
            'stretch_goals': suggestions[velocity:velocity+3] if len(suggestions) > velocity else []
        }
        
        return sprint_plan
    
    def _calculate_velocity(self, days: int) -> int:
        """Calculate average cards completed per sprint period."""
        actions = self.trello.get_board_activity(self.board_id, limit=500)
        
        cutoff_date = datetime.now() - timedelta(days=days*4)  # Look at 4 sprint periods
        completed_by_period = [0] * 4
        
        for action in actions:
            if action['type'] == 'updateCard' and 'listAfter' in action['data']:
                if 'done' in action['data']['listAfter']['name'].lower():
                    action_date = datetime.fromisoformat(action['date'].replace('Z', '+00:00'))
                    
                    if action_date < cutoff_date:
                        break
                    
                    # Determine which period
                    days_ago = (datetime.now() - action_date).days
                    period = min(days_ago // days, 3)
                    completed_by_period[period] += 1
        
        # Average of last 3 periods (exclude current)
        avg_velocity = sum(completed_by_period[1:]) / 3
        return max(int(avg_velocity), 3)  # Minimum velocity of 3
    
    async def cleanup_done_list(self, archive_after_days: int = 30):
        """Archive cards that have been in Done list for too long."""
        cards = self.trello.get_cards(self.board_id)
        done_list_id = self.list_ids.get('done')
        
        if not done_list_id:
            return 0
        
        archived_count = 0
        cutoff_date = datetime.now() - timedelta(days=archive_after_days)
        
        for card in cards:
            if card['idList'] == done_list_id:
                # Check last activity
                last_modified = datetime.fromisoformat(card['dateLastActivity'].replace('Z', '+00:00'))
                if last_modified < cutoff_date:
                    # Archive the card
                    self.trello.update_card(card['id'], closed=True)
                    archived_count += 1
        
        return archived_count
    
    def generate_progress_report(self) -> str:
        """Generate a comprehensive progress report."""
        cards = self.trello.get_cards(self.board_id)
        lists = self.trello.get_lists(self.board_id)
        
        # Count cards by list
        list_counts = {}
        for lst in lists:
            list_counts[lst['name']] = sum(1 for c in cards if c['idList'] == lst['id'])
        
        # Calculate metrics
        total_cards = len(cards)
        done_cards = sum(1 for c in cards if 'done' in self._get_list_name(c['idList']).lower())
        completion_rate = (done_cards / total_cards * 100) if total_cards > 0 else 0
        
        # Velocity trends
        velocity_1w = self._calculate_velocity(7)
        velocity_2w = self._calculate_velocity(14)
        
        report = f"""# Virtuoso Project Progress Report
        
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Overview
- Total Cards: {total_cards}
- Completed: {done_cards} ({completion_rate:.1f}%)
- Weekly Velocity: {velocity_1w} cards/week
- Velocity Trend: {'📈 Increasing' if velocity_1w > velocity_2w else '📉 Decreasing' if velocity_1w < velocity_2w else '➡️ Stable'}

## Cards by List
"""
        for list_name, count in list_counts.items():
            report += f"- {list_name}: {count} cards\n"
        
        return report
    
    def _get_list_name(self, list_id: str) -> str:
        """Get list name from ID."""
        for name, lid in self.list_ids.items():
            if lid == list_id:
                return name
        return "Unknown"


async def main():
    """Run automation workflows."""
    automation = TrelloAutomation()
    
    print("🤖 Running Trello Automation Workflows...\n")
    
    # 1. Auto-prioritize tasks
    print("1. Auto-prioritizing tasks...")
    updates = await automation.auto_prioritize_tasks()
    print(f"   ✅ Updated {updates} cards with priority labels\n")
    
    # 2. Check for overdue cards
    print("2. Checking for overdue cards...")
    overdue = await automation.move_overdue_cards()
    print(f"   {'⚠️' if overdue > 0 else '✅'} Found {overdue} overdue cards\n")
    
    # 3. Suggest next tasks
    print("3. Suggested next tasks:")
    suggestions = await automation.suggest_next_tasks()
    for i, suggestion in enumerate(suggestions, 1):
        print(f"   {i}. {suggestion['card']}")
        print(f"      Reason: {suggestion['reason']}")
        print(f"      Score: {suggestion['score']}\n")
    
    # 4. Generate sprint plan
    print("4. Sprint Plan (7 days):")
    sprint_plan = await automation.generate_sprint_plan()
    print(f"   Velocity target: {sprint_plan['velocity_target']} cards")
    print(f"   Selected tasks: {len(sprint_plan['selected_tasks'])}")
    print(f"   Total priority points: {sprint_plan['total_points']}\n")
    
    # 5. Generate progress report
    print("5. Generating progress report...")
    report = automation.generate_progress_report()
    
    # Save report
    os.makedirs('reports', exist_ok=True)
    with open('reports/trello_progress_report.md', 'w') as f:
        f.write(report)
    print("   ✅ Report saved to reports/trello_progress_report.md\n")
    
    # 6. Cleanup old done cards (optional)
    # archived = await automation.cleanup_done_list()
    # print(f"6. Archived {archived} old completed cards\n")
    
    print("✅ Automation complete!")


if __name__ == '__main__':
    asyncio.run(main())