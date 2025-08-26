#!/usr/bin/env python3
"""
Automated Trello Board Creator for Chart Consolidation Project
Creates the complete board structure with lists, cards, and labels
"""

import requests
import json
import time
from typing import Dict, List, Any

class TrelloAutomation:
    def __init__(self, api_key: str, token: str):
        self.api_key = api_key
        self.token = token
        self.base_url = "https://api.trello.com/1"
        self.auth_params = {"key": api_key, "token": token}
    
    def create_board(self, name: str, description: str = "") -> str:
        """Create a new Trello board"""
        url = f"{self.base_url}/boards"
        data = {
            **self.auth_params,
            "name": name,
            "desc": description,
            "defaultLists": "false"  # We'll create custom lists
        }
        
        response = requests.post(url, data=data)
        if response.status_code == 200:
            board_data = response.json()
            print(f"✅ Created board: {name}")
            return board_data["id"]
        else:
            raise Exception(f"Failed to create board: {response.text}")
    
    def create_list(self, board_id: str, name: str, pos: str = "bottom") -> str:
        """Create a list on the board"""
        url = f"{self.base_url}/lists"
        data = {
            **self.auth_params,
            "name": name,
            "idBoard": board_id,
            "pos": pos
        }
        
        response = requests.post(url, data=data)
        if response.status_code == 200:
            list_data = response.json()
            print(f"📋 Created list: {name}")
            return list_data["id"]
        else:
            raise Exception(f"Failed to create list: {response.text}")
    
    def create_card(self, list_id: str, name: str, desc: str = "", labels: List[str] = None) -> str:
        """Create a card in a list"""
        url = f"{self.base_url}/cards"
        data = {
            **self.auth_params,
            "name": name,
            "desc": desc,
            "idList": list_id
        }
        
        if labels:
            data["idLabels"] = ",".join(labels)
        
        response = requests.post(url, data=data)
        if response.status_code == 200:
            card_data = response.json()
            print(f"📇 Created card: {name}")
            return card_data["id"]
        else:
            raise Exception(f"Failed to create card: {response.text}")
    
    def create_label(self, board_id: str, name: str, color: str) -> str:
        """Create a colored label on the board"""
        url = f"{self.base_url}/labels"
        data = {
            **self.auth_params,
            "name": name,
            "color": color,
            "idBoard": board_id
        }
        
        response = requests.post(url, data=data)
        if response.status_code == 200:
            label_data = response.json()
            print(f"🏷️  Created label: {name} ({color})")
            return label_data["id"]
        else:
            raise Exception(f"Failed to create label: {response.text}")

def create_chart_consolidation_board(api_key: str, token: str) -> str:
    """Create the complete Chart Consolidation board"""
    
    trello = TrelloAutomation(api_key, token)
    
    # Board description
    board_desc = """
🎯 **GOAL**: Consolidate Canvas, Plotly, Matplotlib into unified Chart.js system

📊 **BENEFITS**:
• Consistent Virtuoso navy/amber theming
• Performance optimized rendering  
• Single maintainable codebase
• Mobile responsive design
• Real-time data updates

⏱️ **TIMELINE**: 28 days (4 phases)
🔄 **STATUS**: Implementation in progress

**Key Files**:
- `src/dashboard/static/js/unified-charts.js`
- `src/core/charts/chart_generator.py` 
- `src/dashboard/templates/unified_dashboard_template.html`

**Success Metrics**:
- Chart rendering: <100ms
- Memory stable over 24h
- Zero production incidents
- 30% faster chart development
    """
    
    # Create board
    board_id = trello.create_board(
        "Virtuoso Chart Consolidation - 28 Day Implementation", 
        board_desc
    )
    
    # Create labels
    labels = {
        "backend": trello.create_label(board_id, "backend", "blue"),
        "frontend": trello.create_label(board_id, "frontend", "green"), 
        "testing": trello.create_label(board_id, "testing", "yellow"),
        "deployment": trello.create_label(board_id, "deployment", "orange"),
        "blocked": trello.create_label(board_id, "blocked", "red"),
        "documentation": trello.create_label(board_id, "documentation", "purple"),
        "p0-critical": trello.create_label(board_id, "P0-Critical", "red"),
        "p1-high": trello.create_label(board_id, "P1-High", "orange"),
        "p2-medium": trello.create_label(board_id, "P2-Medium", "yellow"),
        "p3-low": trello.create_label(board_id, "P3-Low", "green")
    }
    
    # Create lists
    lists = {}
    list_names = [
        "📋 BACKLOG",
        "🔄 PHASE 1 - Foundation (Week 1)", 
        "🚀 PHASE 2 - Frontend Migration (Week 2)",
        "🎯 PHASE 3 - Template Consolidation (Week 3)",
        "🚢 PHASE 4 - Production (Week 4)",
        "🔄 IN PROGRESS",
        "👀 CODE REVIEW", 
        "🧪 TESTING",
        "✅ DONE",
        "🚨 BLOCKED/ISSUES"
    ]
    
    for list_name in list_names:
        lists[list_name] = trello.create_list(board_id, list_name)
        time.sleep(0.5)  # Rate limiting
    
    # Phase 1 Cards
    phase1_cards = [
        {
            "name": "🏗️ Environment Setup",
            "desc": """**Tasks:**
• Create directory structure: `src/core/charts`, `src/dashboard/static/js`
• Install Chart.js 4.4.0 dependencies
• Set up development environment
• Prepare testing infrastructure

**Acceptance Criteria:**
- [ ] Directory structure created
- [ ] Dependencies installed
- [ ] Import tests passing
- [ ] No console errors

**Estimated Time:** 4 hours""",
            "labels": [labels["backend"], labels["p1-high"]]
        },
        {
            "name": "📁 Deploy Unified Chart Files", 
            "desc": """**Tasks:**
• Copy `unified-charts.js` to `src/dashboard/static/js/`
• Deploy `chart_generator.py` to `src/core/charts/`
• Test basic imports and functionality
• Verify file permissions

**Acceptance Criteria:**
- [ ] Files deployed to correct locations
- [ ] Backend imports work: `from src.core.charts.chart_generator import chart_generator`
- [ ] Frontend loads without errors
- [ ] Basic chart creation tests pass

**Estimated Time:** 2 hours""",
            "labels": [labels["backend"], labels["frontend"], labels["p0-critical"]]
        },
        {
            "name": "💾 Create Comprehensive Backup",
            "desc": """**Tasks:**
• Run migration analysis: `python scripts/migrate_to_unified_charts.py`
• Backup existing chart implementations
• Document rollback procedures
• Create restore verification checklist

**Files to Backup:**
- `src/dashboard/templates/`
- `src/core/reporting/pdf_generator.py`
- `src/monitoring/monitor.py`

**Acceptance Criteria:**
- [ ] Complete backup created in timestamped directory
- [ ] Rollback procedures documented
- [ ] Backup integrity verified

**Estimated Time:** 3 hours""",
            "labels": [labels["backend"], labels["p1-high"]]
        },
        {
            "name": "🔧 Update PDF Generator",
            "desc": """**Tasks:**
• Replace matplotlib calls in `src/core/reporting/pdf_generator.py`
• Integrate `chart_generator.create_price_chart()` methods
• Test PDF report generation
• Verify no visual regression

**Code Changes:**
```python
# Before:
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
# After: 
from src.core.charts.chart_generator import chart_generator
chart_base64 = chart_generator.create_price_chart(data)
```

**Acceptance Criteria:**
- [ ] PDF reports generate correctly
- [ ] Charts maintain consistent styling
- [ ] No performance regression
- [ ] All tests passing

**Estimated Time:** 8 hours""",
            "labels": [labels["backend"], labels["p0-critical"]]
        },
        {
            "name": "📊 Update Monitor System",
            "desc": """**Tasks:**
• Refactor `src/monitoring/monitor.py` chart generation
• Replace direct matplotlib usage with unified system
• Test signal chart creation
• Verify monitoring alerts work

**Acceptance Criteria:**
- [ ] Monitor charts use unified system
- [ ] Signal generation unchanged
- [ ] Alert charts render correctly
- [ ] Performance maintained

**Estimated Time:** 6 hours""",
            "labels": [labels["backend"], labels["p1-high"]]
        },
        {
            "name": "🧪 Create Test Suite",
            "desc": """**Tasks:**
• Unit tests for `chart_generator` methods
• Performance benchmarks (rendering time <100ms)
• Visual regression tests
• Integration tests

**Test Coverage:**
- `create_price_chart()`
- `create_volume_chart()` 
- `create_confluence_indicator()`
- Theme consistency
- Performance benchmarks

**Acceptance Criteria:**
- [ ] >90% test coverage
- [ ] All tests passing
- [ ] Performance benchmarks established
- [ ] Visual regression suite

**Estimated Time:** 8 hours""",
            "labels": [labels["testing"], labels["p1-high"]]
        }
    ]
    
    # Phase 2 Cards
    phase2_cards = [
        {
            "name": "🎨 Replace Canvas Chart Implementations",
            "desc": """**Tasks:**
• Update `src/dashboard/templates/dashboard_mobile_v1.html`
• Replace manual canvas drawing with unified charts
• Update smart money liquidation gallery
• Test all chart types render correctly

**Code Changes:**
```javascript
// Before: Manual canvas
const ctx = canvas.getContext('2d');
ctx.beginPath();

// After: Unified system
window.virtuosoCharts.createPriceChart('chartId', data);
```

**Acceptance Criteria:**
- [ ] All canvas charts replaced
- [ ] Consistent Virtuoso theming
- [ ] Mobile responsive
- [ ] No JavaScript errors

**Estimated Time:** 10 hours""",
            "labels": [labels["frontend"], labels["p0-critical"]]
        },
        {
            "name": "📱 Standardize Chart Templates",
            "desc": """**Tasks:**
• Add unified chart scripts to templates
• Standardize chart container HTML structure
• Test responsive behavior across devices
• Update PWA manifest if needed

**Template Updates:**
- Add Chart.js 4.4.0 CDN
- Add `unified-charts.js` script
- Standardize `.chart-container` CSS
- Test on mobile/desktop

**Acceptance Criteria:**
- [ ] Consistent chart containers
- [ ] Scripts load correctly
- [ ] Responsive on all screen sizes
- [ ] PWA functionality maintained

**Estimated Time:** 6 hours""",
            "labels": [labels["frontend"], labels["p2-medium"]]
        },
        {
            "name": "🔌 API Integration & Data Flow",
            "desc": """**Tasks:**
• Update API endpoints to provide data in expected format
• Test data flow from API to charts
• Implement error handling and fallbacks
• Validate data transformation

**Expected Data Format:**
```json
{
  "timestamps": ["2024-01-01T00:00:00Z"],
  "prices": [45000.0],
  "symbol": "BTCUSDT"
}
```

**Acceptance Criteria:**
- [ ] APIs return correct format
- [ ] Charts display real data
- [ ] Error handling works
- [ ] Fallback data available

**Estimated Time:** 8 hours""",
            "labels": [labels["backend"], labels["p0-critical"]]
        },
        {
            "name": "⚡ WebSocket Real-time Updates",
            "desc": """**Tasks:**
• Implement efficient real-time chart updates
• WebSocket integration for live data
• Performance optimization (throttling)
• Connection stability and reconnection

**WebSocket Message Format:**
```json
{
  "type": "price_update",
  "symbol": "BTCUSDT",
  "price": 45500.0,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**Acceptance Criteria:**
- [ ] Real-time updates working
- [ ] No memory leaks
- [ ] Smooth chart transitions
- [ ] Connection resilience

**Estimated Time:** 8 hours""",
            "labels": [labels["frontend"], labels["p1-high"]]
        }
    ]
    
    # Add cards to Phase 1
    for card in phase1_cards:
        trello.create_card(
            lists["🔄 PHASE 1 - Foundation (Week 1)"],
            card["name"],
            card["desc"],
            card["labels"]
        )
        time.sleep(0.3)
    
    # Add cards to Phase 2  
    for card in phase2_cards:
        trello.create_card(
            lists["🚀 PHASE 2 - Frontend Migration (Week 2)"],
            card["name"], 
            card["desc"],
            card["labels"]
        )
        time.sleep(0.3)
    
    # Add some backlog cards
    backlog_cards = [
        {
            "name": "📊 Performance Baseline Measurements",
            "desc": "Measure current chart rendering performance before migration",
            "labels": [labels["testing"], labels["p2-medium"]]
        },
        {
            "name": "📚 Update Developer Documentation", 
            "desc": "Document unified chart system usage and API",
            "labels": [labels["documentation"], labels["p3-low"]]
        },
        {
            "name": "🔍 Code Analysis & Audit",
            "desc": "Complete audit of all chart implementations across codebase",
            "labels": [labels["backend"], labels["p2-medium"]]
        }
    ]
    
    for card in backlog_cards:
        trello.create_card(
            lists["📋 BACKLOG"],
            card["name"],
            card["desc"], 
            card["labels"]
        )
        time.sleep(0.3)
    
    # Add some completed cards to show progress
    completed_cards = [
        {
            "name": "✅ Implementation Plan Created",
            "desc": "Comprehensive 28-day implementation plan completed",
            "labels": [labels["documentation"]]
        },
        {
            "name": "✅ Chart System Architecture Designed",
            "desc": "Unified chart system architecture designed and approved",
            "labels": [labels["backend"], labels["frontend"]]
        },
        {
            "name": "✅ Unified Chart Files Created", 
            "desc": "unified-charts.js and chart_generator.py created and ready for deployment",
            "labels": [labels["backend"], labels["frontend"]]
        }
    ]
    
    for card in completed_cards:
        trello.create_card(
            lists["✅ DONE"],
            card["name"],
            card["desc"],
            card["labels"] 
        )
        time.sleep(0.3)
    
    print(f"""
🎉 **BOARD CREATED SUCCESSFULLY!**

📋 **Board ID**: {board_id}
🔗 **URL**: https://trello.com/b/{board_id}

📊 **Summary**:
• 4 Phase lists created
• 10+ detailed task cards
• Color-coded labels for organization
• Complete project roadmap

🚀 **Next Steps**:
1. Visit the board URL above
2. Assign team members to cards
3. Set due dates for each phase
4. Start with Phase 1 tasks!

💡 **Pro Tips**:
• Use card comments for daily updates
• Move cards between lists as progress is made
• Use labels to filter by type/priority
• Set up board notifications for the team
    """)
    
    return board_id

if __name__ == "__main__":
    # Configuration
    API_KEY = input("Enter your Trello API Key: ").strip()
    TOKEN = input("Enter your Trello Token: ").strip()
    
    if not API_KEY or not TOKEN:
        print("❌ API Key and Token are required!")
        print("Get them from: https://trello.com/app-key")
        exit(1)
    
    try:
        board_id = create_chart_consolidation_board(API_KEY, TOKEN)
        print(f"\n🎯 Board ready for Chart Consolidation Implementation!")
    except Exception as e:
        print(f"❌ Error creating board: {e}")
        exit(1)