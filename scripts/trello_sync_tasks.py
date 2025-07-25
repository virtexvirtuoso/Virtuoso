#!/usr/bin/env python3
"""
Automated Trello Task Sync for Virtuoso Project
Syncs tasks with local tracking and provides real-time updates
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.trello_integration import TrelloIntegration


class TrelloTaskSync:
    """Sync and monitor Trello tasks for development workflow."""
    
    def __init__(self, board_id: str = 'YBgMusBE'):
        self.board_id = board_id
        self.trello = TrelloIntegration()
        self.logger = logging.getLogger(__name__)
        
        # Task priority mapping
        self.priority_keywords = {
            'high': ['critical', 'urgent', 'bug', 'fix', 'broken', 'error', 'crash'],
            'medium': ['improve', 'enhance', 'optimize', 'refactor'],
            'low': ['future', 'maybe', 'consider', 'research']
        }
        
        # List priority mapping
        self.list_priorities = {
            'doing': 100,
            'to do': 80,
            'todo': 80,
            'implementations': 40,
            'backlog': 20,
            'done': 0
        }
    
    def calculate_priority(self, card: Dict, list_name: str) -> Dict:
        """Calculate priority score and category for a card."""
        score = 0
        category = 'low'
        
        # Check list priority
        list_name_lower = list_name.lower()
        for list_key, list_score in self.list_priorities.items():
            if list_key in list_name_lower:
                score += list_score
                break
        
        # Check due date
        if card.get('due'):
            due_date = datetime.fromisoformat(card['due'].replace('Z', '+00:00'))
            days_until = (due_date - datetime.now()).days
            
            if days_until < 0:
                score += 200  # Overdue
                category = 'critical'
            elif days_until <= 3:
                score += 150
                category = 'high'
            elif days_until <= 7:
                score += 100
                category = 'high'
            elif days_until <= 14:
                score += 50
                category = 'medium'
        
        # Check card name and description for keywords
        text_to_check = (card.get('name', '') + ' ' + card.get('desc', '')).lower()
        
        for priority, keywords in self.priority_keywords.items():
            if any(keyword in text_to_check for keyword in keywords):
                if priority == 'high':
                    score += 100
                    if category == 'low':
                        category = 'high'
                elif priority == 'medium' and category == 'low':
                    score += 50
                    category = 'medium'
                break
        
        # Check labels
        for label in card.get('labels', []):
            color = label.get('color', '')
            if color == 'red':
                score += 80
                if category != 'critical':
                    category = 'high'
            elif color == 'orange':
                score += 40
                if category == 'low':
                    category = 'medium'
            elif color == 'yellow':
                score += 20
        
        return {'score': score, 'category': category}
    
    async def sync_tasks(self) -> Dict:
        """Sync all tasks from Trello board."""
        try:
            # Get board data
            lists = self.trello.get_lists(self.board_id)
            cards = self.trello.get_cards(self.board_id)
            
            # Create list lookup
            list_lookup = {lst['id']: lst['name'] for lst in lists}
            
            # Process cards
            tasks = {
                'critical': [],
                'high': [],
                'medium': [],
                'low': [],
                'in_progress': [],
                'completed': []
            }
            
            for card in cards:
                list_name = list_lookup.get(card['idList'], 'Unknown')
                
                # Skip closed cards
                if card.get('closed', False):
                    continue
                
                # Calculate priority
                priority_info = self.calculate_priority(card, list_name)
                
                task = {
                    'id': card['id'],
                    'name': card['name'],
                    'description': card.get('desc', ''),
                    'list': list_name,
                    'due': card.get('due'),
                    'labels': [l['name'] for l in card.get('labels', []) if l.get('name')],
                    'url': card['url'],
                    'priority_score': priority_info['score'],
                    'priority_category': priority_info['category']
                }
                
                # Categorize task
                if 'done' in list_name.lower():
                    tasks['completed'].append(task)
                elif 'doing' in list_name.lower():
                    tasks['in_progress'].append(task)
                else:
                    tasks[priority_info['category']].append(task)
            
            # Sort each category by priority score
            for category in tasks:
                tasks[category].sort(key=lambda x: x['priority_score'], reverse=True)
            
            return tasks
            
        except Exception as e:
            self.logger.error(f"Error syncing tasks: {e}")
            raise
    
    def generate_task_report(self, tasks: Dict) -> str:
        """Generate a formatted task report."""
        report = []
        report.append("# Virtuoso Task Status Report")
        report.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        # Summary
        total_tasks = sum(len(tasks[cat]) for cat in tasks if cat != 'completed')
        report.append("## Summary")
        report.append(f"- Total active tasks: {total_tasks}")
        report.append(f"- In Progress: {len(tasks['in_progress'])}")
        report.append(f"- Critical: {len(tasks['critical'])}")
        report.append(f"- High Priority: {len(tasks['high'])}")
        report.append(f"- Medium Priority: {len(tasks['medium'])}")
        report.append(f"- Low Priority: {len(tasks['low'])}")
        report.append(f"- Completed: {len(tasks['completed'])}")
        
        # In Progress Tasks
        if tasks['in_progress']:
            report.append("\n## 🔄 In Progress")
            for task in tasks['in_progress']:
                report.append(f"\n### {task['name']}")
                if task['due']:
                    due_date = datetime.fromisoformat(task['due'].replace('Z', '+00:00'))
                    report.append(f"**Due:** {due_date.strftime('%Y-%m-%d')}")
                if task['description']:
                    report.append(f"\n{task['description'][:200]}...")
        
        # Critical Tasks
        if tasks['critical']:
            report.append("\n## 🚨 Critical Priority")
            for task in tasks['critical']:
                report.append(f"\n### {task['name']}")
                report.append(f"**List:** {task['list']}")
                if task['due']:
                    due_date = datetime.fromisoformat(task['due'].replace('Z', '+00:00'))
                    days_until = (due_date - datetime.now()).days
                    if days_until < 0:
                        report.append(f"**OVERDUE by {abs(days_until)} days!**")
                    else:
                        report.append(f"**Due in {days_until} days**")
        
        # High Priority Tasks
        if tasks['high']:
            report.append("\n## 🔴 High Priority")
            for i, task in enumerate(tasks['high'][:5]):  # Top 5
                report.append(f"\n{i+1}. **{task['name']}**")
                report.append(f"   - List: {task['list']}")
                if task['labels']:
                    report.append(f"   - Labels: {', '.join(task['labels'])}")
        
        # Next Actions
        report.append("\n## 📋 Recommended Next Actions")
        
        # Combine all active tasks and sort by priority
        all_active = []
        for cat in ['critical', 'high', 'medium']:
            all_active.extend(tasks[cat])
        all_active.sort(key=lambda x: x['priority_score'], reverse=True)
        
        for i, task in enumerate(all_active[:10]):  # Top 10
            report.append(f"\n{i+1}. **{task['name']}** ({task['priority_category'].upper()})")
            report.append(f"   - Current list: {task['list']}")
            report.append(f"   - Priority score: {task['priority_score']}")
            if task['due']:
                due_date = datetime.fromisoformat(task['due'].replace('Z', '+00:00'))
                report.append(f"   - Due: {due_date.strftime('%Y-%m-%d')}")
        
        return '\n'.join(report)
    
    async def create_development_plan(self, tasks: Dict) -> str:
        """Create a development plan based on current tasks."""
        plan = []
        plan.append("# Development Execution Plan")
        plan.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        # Week 1 Plan
        plan.append("## Week 1 - Critical & Infrastructure")
        week1_tasks = tasks['critical'] + [t for t in tasks['high'] if 'infrastructure' in t['name'].lower() or 'deploy' in t['name'].lower()]
        for task in week1_tasks[:5]:
            plan.append(f"- [ ] {task['name']}")
        
        # Week 2 Plan
        plan.append("\n## Week 2 - Core Features & Fixes")
        week2_tasks = [t for t in tasks['high'] if t not in week1_tasks] + tasks['medium'][:3]
        for task in week2_tasks[:5]:
            plan.append(f"- [ ] {task['name']}")
        
        # Week 3 Plan
        plan.append("\n## Week 3 - Enhancements & Optimization")
        week3_tasks = tasks['medium'][3:8]
        for task in week3_tasks:
            plan.append(f"- [ ] {task['name']}")
        
        # Daily standup template
        plan.append("\n## Daily Progress Template")
        plan.append("```")
        plan.append("Date: YYYY-MM-DD")
        plan.append("Completed:")
        plan.append("- Task 1")
        plan.append("In Progress:")
        plan.append("- Task 2")
        plan.append("Blockers:")
        plan.append("- None")
        plan.append("Next:")
        plan.append("- Task 3")
        plan.append("```")
        
        return '\n'.join(plan)


async def main():
    """Main execution function."""
    logging.basicConfig(level=logging.INFO)
    
    try:
        sync = TrelloTaskSync()
        
        print("Syncing tasks from Trello...")
        tasks = await sync.sync_tasks()
        
        # Generate reports
        task_report = sync.generate_task_report(tasks)
        dev_plan = await sync.create_development_plan(tasks)
        
        # Save reports
        os.makedirs('reports', exist_ok=True)
        
        with open('reports/TRELLO_TASK_STATUS.md', 'w') as f:
            f.write(task_report)
        print("✓ Task status report saved to reports/TRELLO_TASK_STATUS.md")
        
        with open('reports/DEVELOPMENT_PLAN.md', 'w') as f:
            f.write(dev_plan)
        print("✓ Development plan saved to reports/DEVELOPMENT_PLAN.md")
        
        # Save JSON for programmatic access
        with open('reports/trello_tasks.json', 'w') as f:
            json.dump(tasks, f, indent=2)
        print("✓ Task data saved to reports/trello_tasks.json")
        
        # Print summary
        print(f"\nTask Summary:")
        print(f"- In Progress: {len(tasks['in_progress'])}")
        print(f"- Critical: {len(tasks['critical'])}")
        print(f"- High Priority: {len(tasks['high'])}")
        print(f"- Medium Priority: {len(tasks['medium'])}")
        print(f"- Low Priority: {len(tasks['low'])}")
        
        if tasks['critical']:
            print("\n⚠️  CRITICAL TASKS REQUIRE IMMEDIATE ATTENTION!")
            for task in tasks['critical'][:3]:
                print(f"   - {task['name']}")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you have set up Trello credentials:")
        print("export TRELLO_API_KEY='your-api-key'")
        print("export TRELLO_TOKEN='your-token'")


if __name__ == '__main__':
    asyncio.run(main())