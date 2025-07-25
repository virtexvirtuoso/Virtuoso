#!/usr/bin/env python3
"""
Trello Integration for Virtuoso Project
Provides direct API access to Trello boards for task management
"""

import os
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd


class TrelloIntegration:
    """Integrate with Trello API for task management."""
    
    def __init__(self, api_key: str = None, token: str = None):
        """
        Initialize Trello integration.
        
        To get credentials:
        1. Get API Key: https://trello.com/app-key
        2. Get Token: Use the link on the API key page
        """
        self.api_key = api_key or os.getenv('TRELLO_API_KEY')
        self.token = token or os.getenv('TRELLO_TOKEN')
        self.base_url = 'https://api.trello.com/1'
        
        if not self.api_key or not self.token:
            raise ValueError(
                "Trello API credentials required. "
                "Set TRELLO_API_KEY and TRELLO_TOKEN environment variables or pass them as parameters."
            )
    
    def _make_request(self, endpoint: str, method: str = 'GET', data: dict = None) -> dict:
        """Make authenticated request to Trello API."""
        url = f"{self.base_url}/{endpoint}"
        params = {
            'key': self.api_key,
            'token': self.token
        }
        
        if method == 'GET':
            response = requests.get(url, params=params)
        elif method == 'POST':
            response = requests.post(url, params=params, json=data)
        elif method == 'PUT':
            response = requests.put(url, params=params, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, params=params)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    def get_boards(self) -> List[Dict]:
        """Get all boards for the authenticated user."""
        return self._make_request('members/me/boards')
    
    def get_board(self, board_id: str) -> Dict:
        """Get specific board details."""
        return self._make_request(f'boards/{board_id}')
    
    def get_lists(self, board_id: str) -> List[Dict]:
        """Get all lists in a board."""
        return self._make_request(f'boards/{board_id}/lists')
    
    def get_cards(self, board_id: str, include_closed: bool = False) -> List[Dict]:
        """Get all cards in a board."""
        endpoint = f'boards/{board_id}/cards'
        if not include_closed:
            endpoint += '?filter=open'
        return self._make_request(endpoint)
    
    def create_card(self, list_id: str, name: str, desc: str = '', due: str = None) -> Dict:
        """Create a new card in a list."""
        data = {
            'idList': list_id,
            'name': name,
            'desc': desc
        }
        if due:
            data['due'] = due
        
        return self._make_request('cards', method='POST', data=data)
    
    def update_card(self, card_id: str, **kwargs) -> Dict:
        """Update card properties (name, desc, due, idList, etc.)."""
        return self._make_request(f'cards/{card_id}', method='PUT', data=kwargs)
    
    def move_card(self, card_id: str, list_id: str) -> Dict:
        """Move card to different list."""
        return self.update_card(card_id, idList=list_id)
    
    def add_comment(self, card_id: str, text: str) -> Dict:
        """Add comment to a card."""
        return self._make_request(
            f'cards/{card_id}/actions/comments',
            method='POST',
            data={'text': text}
        )
    
    def get_board_activity(self, board_id: str, limit: int = 50) -> List[Dict]:
        """Get recent activity on a board."""
        return self._make_request(f'boards/{board_id}/actions?limit={limit}')
    
    def export_to_markdown(self, board_id: str, output_file: str = None) -> str:
        """Export board to markdown format with priority analysis."""
        lists = self.get_lists(board_id)
        cards = self.get_cards(board_id)
        board = self.get_board(board_id)
        
        # Group cards by list
        cards_by_list = {}
        for card in cards:
            list_id = card['idList']
            if list_id not in cards_by_list:
                cards_by_list[list_id] = []
            cards_by_list[list_id].append(card)
        
        # Build markdown
        markdown = f"# {board['name']}\n\n"
        markdown += f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        
        # Statistics
        total_cards = len(cards)
        markdown += f"## Statistics\n"
        markdown += f"- Total cards: {total_cards}\n"
        
        for lst in lists:
            count = len(cards_by_list.get(lst['id'], []))
            markdown += f"- {lst['name']}: {count} cards\n"
        
        markdown += "\n---\n\n"
        
        # Cards by list
        for lst in lists:
            list_cards = cards_by_list.get(lst['id'], [])
            if not list_cards:
                continue
                
            markdown += f"## {lst['name']} ({len(list_cards)} cards)\n\n"
            
            # Sort by due date if available
            list_cards.sort(key=lambda x: x.get('due') or 'zzz')
            
            for card in list_cards:
                # Card name
                markdown += f"### {card['name']}\n"
                
                # Due date
                if card.get('due'):
                    due_date = datetime.fromisoformat(card['due'].replace('Z', '+00:00'))
                    markdown += f"**Due:** {due_date.strftime('%Y-%m-%d')}\n"
                
                # Description
                if card.get('desc'):
                    markdown += f"\n{card['desc']}\n"
                
                # Labels
                if card.get('labels'):
                    labels = ', '.join([label['name'] for label in card['labels'] if label.get('name')])
                    if labels:
                        markdown += f"\n**Labels:** {labels}\n"
                
                markdown += "\n---\n\n"
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(markdown)
            print(f"Exported to {output_file}")
        
        return markdown
    
    def analyze_priorities(self, board_id: str) -> pd.DataFrame:
        """Analyze and prioritize tasks based on various factors."""
        cards = self.get_cards(board_id)
        lists = self.get_lists(board_id)
        
        # Create list lookup
        list_names = {lst['id']: lst['name'] for lst in lists}
        
        # Build dataframe
        data = []
        for card in cards:
            priority_score = 0
            
            # Factors for priority scoring
            has_due_date = bool(card.get('due'))
            if has_due_date:
                due_date = datetime.fromisoformat(card['due'].replace('Z', '+00:00'))
                days_until_due = (due_date - datetime.now()).days
                if days_until_due < 0:
                    priority_score += 100  # Overdue
                elif days_until_due < 7:
                    priority_score += 50   # Due soon
                elif days_until_due < 14:
                    priority_score += 25   # Due in 2 weeks
            
            # List-based priority
            list_name = list_names.get(card['idList'], '')
            if 'doing' in list_name.lower():
                priority_score += 75
            elif 'todo' in list_name.lower() or 'to do' in list_name.lower():
                priority_score += 50
            
            # Label-based priority
            for label in card.get('labels', []):
                if label.get('color') == 'red':
                    priority_score += 30
                elif label.get('color') == 'orange':
                    priority_score += 20
                elif label.get('color') == 'yellow':
                    priority_score += 10
            
            # Keywords in name
            name_lower = card['name'].lower()
            if any(word in name_lower for word in ['urgent', 'critical', 'bug', 'fix']):
                priority_score += 40
            if any(word in name_lower for word in ['high priority', 'important']):
                priority_score += 30
            
            data.append({
                'name': card['name'],
                'list': list_names.get(card['idList'], 'Unknown'),
                'due': card.get('due'),
                'has_description': bool(card.get('desc')),
                'labels': ', '.join([l['name'] for l in card.get('labels', []) if l.get('name')]),
                'priority_score': priority_score,
                'url': card['url']
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('priority_score', ascending=False)
        
        return df


def main():
    """Example usage of Trello integration."""
    # Initialize (you'll need to set your API credentials)
    # Get them from: https://trello.com/app-key
    try:
        trello = TrelloIntegration()
        
        # List all boards
        print("Your Trello Boards:")
        boards = trello.get_boards()
        for board in boards:
            print(f"- {board['name']} (ID: {board['id']})")
        
        # If you know your board ID (from the JSON filename: YBgMusBE)
        board_id = 'YBgMusBE'  # Your Virtuoso board
        
        # Export to markdown
        trello.export_to_markdown(board_id, 'docs/TRELLO_EXPORT.md')
        
        # Analyze priorities
        priorities = trello.analyze_priorities(board_id)
        print("\nTop 10 Priority Tasks:")
        print(priorities.head(10)[['name', 'list', 'priority_score']])
        
        # Save priority analysis
        priorities.to_csv('reports/trello_priorities.csv', index=False)
        
    except ValueError as e:
        print(f"Error: {e}")
        print("\nTo use Trello integration:")
        print("1. Go to https://trello.com/app-key")
        print("2. Get your API key")
        print("3. Click 'Generate a Token' link on that page")
        print("4. Set environment variables:")
        print("   export TRELLO_API_KEY='your-api-key'")
        print("   export TRELLO_TOKEN='your-token'")


if __name__ == '__main__':
    main()