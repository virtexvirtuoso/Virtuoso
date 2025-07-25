# Trello Integration Guide for Virtuoso

## 🚀 Quick Setup

### 1. Get Your Credentials

Run the interactive setup script:
```bash
python scripts/setup_trello_credentials.py
```

This will:
- Open Trello API page in your browser
- Guide you through getting API key and token
- Test the credentials
- Save them to .env or shell config

### 2. Available Scripts

#### **Basic Integration** (`scripts/trello_integration.py`)
- Core API wrapper for all Trello operations
- Read/write cards, lists, boards
- Export to markdown
- Priority analysis

#### **Task Sync** (`scripts/trello_sync_tasks.py`)
- Syncs all tasks from your board
- Categorizes by priority (Critical/High/Medium/Low)
- Generates task status reports
- Creates development plans

#### **Daily Standup** (`scripts/trello_daily_standup.py`)
- Generates daily standup reports
- Shows completed tasks (last 24h)
- Lists current in-progress items
- Identifies blockers
- Calculates velocity metrics

#### **Automation Workflows** (`scripts/trello_automation_workflows.py`)
- Auto-prioritizes tasks based on keywords and due dates
- Identifies and flags overdue cards
- Suggests next tasks based on priority scoring
- Generates sprint plans
- Creates progress reports

## 📋 Usage Examples

### Basic Task Management

```python
from scripts.trello_integration import TrelloIntegration

trello = TrelloIntegration()

# Get all your boards
boards = trello.get_boards()
for board in boards:
    print(f"{board['name']} - {board['id']}")

# Work with Virtuoso board
board_id = 'YBgMusBE'  # Your Virtuoso board ID

# Get all lists
lists = trello.get_lists(board_id)

# Get all cards
cards = trello.get_cards(board_id)

# Create a new task
new_card = trello.create_card(
    list_id='670d378680f3e64ef7f46192',  # To Do list
    name='Implement new feature',
    desc='Detailed description here',
    due=(datetime.now() + timedelta(days=3)).isoformat()
)

# Move card to "Doing"
trello.move_card(new_card['id'], '671118fa88626b8d6c7cf1a6')

# Add a comment
trello.add_comment(new_card['id'], 'Started working on this')
```

### Daily Workflow

```bash
# Morning: Generate standup
python scripts/trello_daily_standup.py

# Check task priorities
python scripts/trello_sync_tasks.py

# Run automation workflows
python scripts/trello_automation_workflows.py
```

### Automated Reports

The scripts generate various reports in the `reports/` directory:
- `TRELLO_TASK_STATUS.md` - Current task status
- `DEVELOPMENT_PLAN.md` - Suggested development plan
- `trello_progress_report.md` - Progress metrics
- `standups/standup_YYYYMMDD.md` - Daily standups

## 🔧 Configuration

### Environment Variables

```bash
# Required
TRELLO_API_KEY=your-api-key
TRELLO_TOKEN=your-token

# Optional
DISCORD_STANDUP_WEBHOOK=https://discord.com/api/webhooks/...
```

### Board Structure

The scripts expect these list names (case-insensitive):
- **To Do** or **Todo** - Backlog tasks
- **Doing** - Current work
- **Done** - Completed tasks
- **Blocked** - (Optional) Blocked items

### Priority Labels

Use colored labels for priority:
- 🔴 **Red** - Critical/Urgent
- 🟠 **Orange** - High Priority
- 🟡 **Yellow** - Medium Priority
- 🟢 **Green** - Low Priority

## 🤖 Automation Ideas

### 1. Cron Jobs

Add to your crontab:
```bash
# Daily standup at 9 AM
0 9 * * * cd /path/to/virtuoso && python scripts/trello_daily_standup.py

# Weekly automation on Monday
0 8 * * 1 cd /path/to/virtuoso && python scripts/trello_automation_workflows.py
```

### 2. Git Hooks

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Update task status before commit
python scripts/trello_sync_tasks.py
```

### 3. CI/CD Integration

In your GitHub Actions:
```yaml
- name: Update Trello
  env:
    TRELLO_API_KEY: ${{ secrets.TRELLO_API_KEY }}
    TRELLO_TOKEN: ${{ secrets.TRELLO_TOKEN }}
  run: |
    python scripts/trello_automation_workflows.py
```

## 📊 Advanced Features

### Custom Workflows

Create your own workflows by extending the base classes:

```python
from scripts.trello_integration import TrelloIntegration

class MyCustomWorkflow(TrelloIntegration):
    def __init__(self):
        super().__init__()
        
    def my_custom_method(self):
        # Your custom logic here
        pass
```

### Webhook Integration

For real-time updates:
```python
# Register webhook
webhook_url = "https://your-server.com/trello-webhook"
trello.create_webhook(board_id, webhook_url)
```

## 🚨 Troubleshooting

### Common Issues

1. **Authentication Error**
   - Regenerate token with correct permissions
   - Ensure environment variables are set

2. **Board Not Found**
   - Check board ID is correct
   - Verify you have access to the board

3. **Rate Limiting**
   - Trello API limit: 100 requests per 10 seconds
   - Add delays between bulk operations

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 Resources

- [Trello API Documentation](https://developer.atlassian.com/cloud/trello/)
- [py-trello Library](https://github.com/sarumont/py-trello)
- [Trello Power-Ups](https://trello.com/power-ups)

---

*For Virtuoso-specific questions, check the task descriptions in your Trello board or run `python scripts/trello_sync_tasks.py` for the latest priorities.*