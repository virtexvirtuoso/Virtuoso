# Trello API Setup Instructions

## Step 1: Get Your API Key

1. Open this URL in your browser:
   **https://trello.com/app-key**

2. Log in to Trello if prompted

3. You'll see your API Key on the page. It looks like:
   `8f6e4b3a9c2d1e5f7a8b9c0d1e2f3a4b`

4. Copy this key - you'll need it for Step 2

## Step 2: Get Your Token

1. After getting your API key, look for a link on the same page that says:
   **"Token"** or **"Get a token"**
   
   OR use this URL (replace YOUR_API_KEY with your actual key):
   ```
   https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&name=Virtuoso&key=YOUR_API_KEY
   ```

2. Click "Allow" to authorize the Virtuoso app

3. You'll see a long token like:
   `9f8e7d6c5b4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c`

4. Copy this token

## Step 3: Save Your Credentials

### Option A: Save to .env file (Recommended)

Create or update `.env` file in your project root:

```bash
TRELLO_API_KEY=your-api-key-here
TRELLO_TOKEN=your-token-here
```

### Option B: Export in Terminal (Temporary)

```bash
export TRELLO_API_KEY='your-api-key-here'
export TRELLO_TOKEN='your-token-here'
```

### Option C: Add to Shell Config (Permanent)

Add to `~/.zshrc` or `~/.bashrc`:

```bash
# Trello API Credentials for Virtuoso
export TRELLO_API_KEY='your-api-key-here'
export TRELLO_TOKEN='your-token-here'
```

Then reload:
```bash
source ~/.zshrc  # or ~/.bashrc
```

## Step 4: Test Your Setup

Run this command to test:

```bash
python -c "
import os
import requests

key = os.getenv('TRELLO_API_KEY')
token = os.getenv('TRELLO_TOKEN')

if not key or not token:
    print('❌ Credentials not found in environment')
else:
    url = f'https://api.trello.com/1/members/me?key={key}&token={token}'
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        print(f'✅ Success! Connected as: {data.get(\"fullName\")} (@{data.get(\"username\")})')
    else:
        print(f'❌ Invalid credentials: {r.status_code}')
"
```

## Step 5: Find Your Board ID

Once credentials are working, find your Virtuoso board:

```bash
python -c "
import os
import requests

key = os.getenv('TRELLO_API_KEY')
token = os.getenv('TRELLO_TOKEN')
url = f'https://api.trello.com/1/members/me/boards?key={key}&token={token}'
r = requests.get(url)
boards = r.json()

print('Your Trello Boards:')
for board in boards:
    print(f'  - {board[\"name\"]} (ID: {board[\"id\"]})')
    if 'virtuoso' in board['name'].lower():
        print(f'    ^ This looks like your Virtuoso board!')
"
```

## Quick Test Script

Save this as `test_trello.py`:

```python
import os
from scripts.trello_integration import TrelloIntegration

try:
    trello = TrelloIntegration()
    boards = trello.get_boards()
    print("✅ Connection successful!")
    print(f"Found {len(boards)} boards")
    
    # Look for Virtuoso board
    for board in boards:
        if 'virtuoso' in board['name'].lower():
            print(f"\nVirtuoso Board: {board['name']}")
            lists = trello.get_lists(board['id'])
            for lst in lists:
                print(f"  - {lst['name']}")
            break
            
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nMake sure you've set:")
    print("  export TRELLO_API_KEY='your-key'")
    print("  export TRELLO_TOKEN='your-token'")
```

---

## Need Help?

If you're having issues:

1. Make sure you're logged into Trello in your browser
2. Check that you copied the full key/token (no spaces)
3. Try the test commands to verify each step
4. The token should have read/write permissions

Your board ID from the JSON file is: `YBgMusBE`