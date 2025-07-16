# Virtuoso Trading System - Integrated Dashboard

## 🎯 Overview

The Virtuoso Trading System now features a **fully integrated dashboard** that combines the live trading system with real-time web-based monitoring and analysis interfaces. The integration provides seamless access to all trading data, signals, and analytics through a modern web interface.

## 🏗️ Architecture

### Unified Application Structure
```
main.py (FastAPI App)
├── Trading System Core
│   ├── Exchange Manager
│   ├── Market Monitor
│   ├── Signal Generator
│   ├── Alert Manager
│   └── Market Reporter
├── Dashboard Web Server (Port 8000)
│   ├── Template Routes
│   ├── API Endpoints
│   ├── WebSocket Streams
│   └── Static Assets
└── Concurrent Execution
    ├── Trading System Loop
    └── Web Server Loop
```

## 🚀 Quick Start

### Option 1: Using the Startup Script (Recommended)
```bash
python scripts/start_dashboard.py
```

### Option 2: Direct Execution
```bash
cd src && python main.py
```

### Option 3: Background Execution
```bash
nohup python scripts/start_dashboard.py > system.log 2>&1 &
```

## 🌐 Dashboard Access Points

Once running, access the system at:

| Component | URL | Description |
|-----------|-----|-------------|
| **Main Dashboard** | http://localhost:8000/dashboard | v10 Signal Confluence Matrix |
| **Market Analysis** | http://localhost:8000/market-analysis | Market Reporter Dashboard |
| **Beta Analysis** | http://localhost:8000/beta-analysis | Bitcoin Beta Analysis |
| **System Status** | http://localhost:8000/ | Live system health & metrics |
| **API Health** | http://localhost:8000/health | Service health check |

## 🔌 API Endpoints

### Trading Data APIs
- `GET /api/top-symbols` - Live top symbols with confluence scores
- `GET /api/market-report` - Latest market analysis report
- `GET /api/dashboard/overview` - System overview metrics

### Analysis APIs
- `GET /analysis/{symbol}` - Symbol-specific confluence analysis
- `WS /ws/analysis/{symbol}` - Real-time analysis stream

### System APIs
- `GET /health` - System health status
- `GET /version` - Application version

## 📊 Features

### 🎯 Live Trading Integration
- **Real-time Data**: Dashboard pulls live data from trading system
- **Confluence Scores**: Live signal confluence calculations
- **Market Monitoring**: Real-time market condition analysis
- **Alpha Opportunities**: Live detection and alerts

### 🎨 Dashboard Components
- **Signal Matrix**: 12-factor confluence scoring system
- **Market Analysis**: Comprehensive market reports
- **Beta Analysis**: Bitcoin correlation analysis
- **Live Metrics**: System performance monitoring

### 🔔 Alert Integration
- **Discord Alerts**: Real-time notifications
- **System Alerts**: Performance and error monitoring
- **Trading Signals**: Buy/sell signal notifications

## 🛠️ Technical Details

### Data Flow
```
Exchange APIs → Market Monitor → Confluence Analyzer → Dashboard APIs → Web Interface
                      ↓
               Alert Manager → Discord/Notifications
```

### Component Integration
- **Exchange Manager**: Provides live market data to dashboard
- **Top Symbols Manager**: Dynamic symbol selection for analysis
- **Confluence Analyzer**: Real-time signal scoring
- **Market Reporter**: Generates comprehensive market reports
- **Alert Manager**: Handles real-time notifications

### Fallback Behavior
- **Live Data Priority**: Uses real trading data when available
- **Mock Data Fallback**: Graceful fallback to mock data for testing
- **Error Handling**: Comprehensive error handling and logging

## 🔧 Configuration

### Environment Variables
Configured via `config/env/.env`:
- `DISCORD_WEBHOOK_URL`: Discord alert notifications
- `EXCHANGE_*`: Exchange API configurations
- Trading system parameters

### Dashboard Settings
- **Port**: 8000 (configurable in main.py)
- **Host**: 0.0.0.0 (accepts external connections)
- **CORS**: Enabled for cross-origin requests

## 📱 Navigation Flow

```
Main Dashboard (v10 Signal Confluence Matrix)
├── MARKET ANALYSIS → Market Reporter Dashboard
│   └── ← TRADING DASHBOARD (back to main)
├── BETA ANALYSIS → Bitcoin Beta Analysis
│   └── ← TRADING DASHBOARD (back to main)
└── Live Signal Matrix (main view)
```

## 🐛 Troubleshooting

### Common Issues

1. **Port 8000 in use**
```bash
   # Find and kill process using port 8000
   lsof -ti:8000 | xargs kill -9
   ```

2. **Dashboard not loading**
   - Check if main.py is running: `ps aux | grep main.py`
   - Verify port accessibility: `curl http://localhost:8000/health`

3. **No live data in dashboard**
   - Check exchange connectivity in logs
   - Verify API keys in config
   - Check system status at http://localhost:8000/

4. **Navigation not working**
   - Ensure templates have correct `/dashboard` links
   - Check browser console for JavaScript errors

### Log Files
- **System Logs**: Check console output for detailed information
- **Background Logs**: If running with nohup, check `system.log`

## 🎯 Development

### Adding New Dashboard Routes
```python
@app.get("/my-new-route")
async def my_new_route():
    return FileResponse("src/dashboard/templates/my_template.html")
```

### Adding New API Endpoints
```python
@app.get("/api/my-endpoint")
async def my_api_endpoint():
    # Access trading system components
    if top_symbols_manager:
        data = await top_symbols_manager.get_data()
    return {"data": data}
```

### Template Development
- Templates located in `src/dashboard/templates/`
- Use `/dashboard` for back navigation
- Follow Terminal Amber + Navy Blue theme

## 📈 Performance

### Optimizations
- **Concurrent Execution**: Trading system and web server run independently
- **Efficient Data Flow**: Direct access to trading system components
- **Caching**: Intelligent caching of frequently accessed data
- **Error Isolation**: Web server errors don't affect trading system

### Resource Usage
- **Memory**: Shared components reduce memory footprint
- **CPU**: Concurrent execution optimizes CPU usage
- **Network**: Efficient API design minimizes bandwidth

## 🔐 Security Considerations

- **Internal Access**: Default configuration for internal network use
- **API Keys**: Secure storage in environment variables
- **CORS**: Configured for development (restrict for production)
- **Logging**: Sensitive data excluded from logs

---

## 📞 Support

For integration issues or questions:
1. Check the troubleshooting section above
2. Review logs for detailed error information
3. Verify configuration settings
4. Test individual components (trading system vs. web server)

The integrated dashboard system provides a powerful, unified interface for monitoring and controlling your Virtuoso Trading System with real-time data and comprehensive analytics. 