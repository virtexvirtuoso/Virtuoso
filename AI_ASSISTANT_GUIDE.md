# Virtuoso CCXT Trading System - AI Assistant Guide

## Project Overview
Virtuoso CCXT is a sophisticated quantitative trading system featuring:
- 6-dimensional market analysis (Order Flow, Sentiment, Liquidity, Bitcoin Beta, Smart Money Flow, Machine Learning)
- 253x performance optimization with advanced caching layers
- Real-time signal generation with confluence scoring
- Multi-exchange support (Primary: Bybit, Secondary: Binance)
- Web-based dashboards (Desktop & Mobile)

## Local Development
- **Virtual Environment**: Always use `venv311` when running locally
  ```bash
  source venv311/bin/activate  # Activate virtual environment
  python src/main.py           # Run the main application
  ```
- **Testing Commands**:
  ```bash
  # Test specific components
  ./venv311/bin/python scripts/test_cache_performance.sh
  ./venv311/bin/python scripts/test_mobile_dashboard_complete.sh
  
  # Check system health
  curl http://localhost:8003/health
  curl http://localhost:8001/api/monitoring/status
  ```

## VPS Configuration
- **VPS Access**: Connect using `ssh linuxuser@${VPS_HOST}` or `ssh vps`
- **Project Path**: `/home/linuxuser/trading/Virtuoso_ccxt/`
- **Important**: Always save local changes before deploying to VPS
- **Python on VPS**: Uses system Python 3.11

## Technology Stack
### Core Frameworks
- **FastAPI**: Main API framework (ports 8003, 8001)
- **CCXT**: Exchange connectivity (v4.4.24+)
- **Pandas & NumPy**: Data analysis
- **TA-Lib**: Technical indicators
- **AsyncIO**: Asynchronous operations

### Caching Systems - PHASE 2 MULTI-TIER ARCHITECTURE
- **Layer 1 (L1) - In-Memory Cache**: Ultra-fast cache (0.01ms reads)
  - TTL: 15-45 seconds (trading data volatility optimized)
  - Capacity: 1000 items with LRU eviction
  - Hit Rate: 85%+ of all requests
  
- **Layer 2 (L2) - Memcached**: Primary distributed cache (port 11211)
  - TTL: 30-90 seconds (volatility-based TTL strategy)
  - Connection Pool: 20 connections (optimized)
  - Configuration: 4GB memory, 2048 max connections
  - Hit Rate: ~10% of requests (L1 misses)
  
- **Layer 3 (L3) - Redis**: Persistent cache & pub/sub (port 6379)
  - TTL: 120-600 seconds (long-term persistence)
  - Use: Alert persistence, session management, L1/L2 fallback
  - Hit Rate: ~5% of requests (L1/L2 misses)

- **Intelligent Cache Warming**: Market-aware scheduling
  - Market hours: 15s refresh interval (peak performance)
  - Pre-market: 60s refresh interval
  - After-hours: 120s refresh interval  
  - Overnight: 300s refresh interval
  - Warming Efficiency: 100% (all keys warmed successfully)

### Data Storage
- **SQLite**: Local development database
- **InfluxDB**: Time-series metrics (optional)
- **PostgreSQL**: Production database (optional)

## Critical Environment Variables
```bash
# Exchange API Keys (Required)
BYBIT_API_KEY=your_key
BYBIT_API_SECRET=your_secret
BINANCE_API_KEY=your_key  # Optional
BINANCE_SECRET=your_secret

# Application Settings
APP_PORT=8003              # Main API port
MONITORING_PORT=8001       # Monitoring API port
CACHE_TYPE=memcached       # or redis
MEMCACHED_HOST=localhost
MEMCACHED_PORT=11211
REDIS_HOST=localhost
REDIS_PORT=6379

# External Services
DISCORD_WEBHOOK_URL=your_webhook
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_token
```

## API Architecture & Access URLs

### Production URLs (Hetzner VPS - ${VPS_HOST})
- **Desktop Dashboard**: http://${VPS_HOST}:8003/
- **Mobile Dashboard**: http://${VPS_HOST}:8003/mobile
- **Health Check**: http://${VPS_HOST}:8003/health
- **Monitoring API**: http://${VPS_HOST}:8001/api/monitoring/status
- **Dashboard Data**: http://${VPS_HOST}:8003/api/dashboard/data
- **Mobile Data**: http://${VPS_HOST}:8003/api/dashboard/mobile

### Local Development URLs
- **Desktop Dashboard**: http://localhost:8003/
- **Mobile Dashboard**: http://localhost:8003/mobile
- **Health Check**: http://localhost:8003/health
- **Monitoring API**: http://localhost:8001/api/monitoring/status
- **Dashboard Data**: http://localhost:8003/api/dashboard/data
- **Mobile Data**: http://localhost:8003/api/dashboard/mobile

### Main API Endpoints (Port 8003)
- `/` - Desktop dashboard
- `/mobile` - Mobile dashboard
- `/api/dashboard/data` - Real-time market data
- `/api/dashboard/mobile` - Mobile-specific data
- `/api/alerts` - Alert management
- `/api/config` - Configuration editor
- `/api/bitcoin-beta` - Bitcoin correlation data
- `/ws` - WebSocket for real-time updates

### Monitoring API Endpoints (Port 8001)
- `/api/monitoring/status` - System health
- `/api/monitoring/metrics` - Performance metrics
- `/api/monitoring/symbols` - Active symbol monitoring

## System Architecture
### Analysis Engine
- **6 Dimensional Analysis**:
  1. Order Flow Analysis - Volume patterns, buy/sell pressure
  2. Sentiment Analysis - Market mood indicators
  3. Liquidity Analysis - Support/resistance zones
  4. Bitcoin Beta - BTC correlation tracking
  5. Smart Money Flow - Institutional activity
  6. Machine Learning - Predictive patterns

### Performance Features
- Connection pooling with automatic retry
- Rate limiting per exchange
- Circuit breaker pattern for resilience
- Async/await throughout
- Batch data fetching
- Smart caching with TTL management

### Trading Configuration
- **Timeframes**: 1m, 5m, 30m, 4h (configurable)
- **Default Symbols**: 30+ crypto pairs
- **Risk Management**: 
  - Max position size limits
  - Stop-loss enforcement
  - Exposure monitoring

## Systemd Service Management
- **View Real-time Logs**: 
  ```bash
  sudo journalctl -u virtuoso.service -f
  ```
- **Service Control**:
  ```bash
  sudo systemctl restart virtuoso.service  # Restart service
  sudo systemctl status virtuoso.service   # Check status
  sudo systemctl stop virtuoso.service     # Stop service
  sudo systemctl start virtuoso.service    # Start service
  ```

## Deployment Workflow
1. Test changes locally with `venv311` activated
2. Save/commit local changes
3. Deploy to VPS using deployment scripts:
   ```bash
   ./scripts/deploy_to_vps.sh          # Full deployment
   ./scripts/deploy_updates_to_vps.sh  # Incremental updates
   ```
4. Verify deployment with systemd logs

## Common Development Commands
```bash
# Cache Management - Phase 2 Commands
./venv311/bin/python scripts/phase2_validation.py      # Validate Phase 2 performance
./venv311/bin/python scripts/load_test.py              # Load testing (633.6 RPS)
./venv311/bin/python scripts/populate_dashboard_cache_async.py  # Cache warming

# VPS Cache Testing
ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && ./venv311/bin/python scripts/phase2_validation.py"
ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && ./venv311/bin/python scripts/load_test.py"

# Dashboard Testing
./scripts/test_mobile_dashboard_complete.sh
curl http://localhost:8003/api/dashboard/mobile
curl http://${VPS_HOST}:8003/api/dashboard/data          # Production test

# Cache Performance Monitoring
curl http://localhost:8003/cache-metrics               # Cache statistics
curl http://${VPS_HOST}:8003/api/dashboard/data        # Production API test

# VPS Operations
./scripts/sync_vps_structure.sh
./scripts/monitor_vps_performance.sh
ssh vps "sudo systemctl status virtuoso-web.service"   # Service status

# Debug Modes
PYTHONPATH=/Users/ffv_macmini/Desktop/Virtuoso_ccxt python src/main.py
DEBUG=1 python src/main.py
```

## Project Structure
```
Virtuoso_ccxt/
├── src/
│   ├── main.py                 # Main entry point
│   ├── api/                    # FastAPI routes & middleware
│   │   ├── cache_adapter_direct.py      # Phase 2 multi-tier cache adapter
│   │   └── cache_adapter_direct.py.phase1_backup  # Phase 1 backup
│   ├── core/                   # Core trading logic
│   │   ├── cache/              # Phase 2 cache architecture (NEW)
│   │   │   ├── multi_tier_cache.py      # L1/L2/L3 cache system
│   │   │   ├── intelligent_warmer.py    # Market-aware warming
│   │   │   └── monitoring.py            # Performance monitoring
│   │   ├── exchanges/          # Exchange integrations
│   │   ├── analysis/           # Market analysis
│   │   └── market/             # Market data processing
│   ├── monitoring/             # System monitoring
│   ├── dashboard/              # Web dashboard
│   └── web_server.py          # Dashboard server
├── scripts/                    # Deployment & utilities
│   ├── phase2_validation.py   # Phase 2 comprehensive testing (NEW)
│   ├── load_test.py           # Load testing (633.6 RPS capacity) (NEW)
│   ├── populate_dashboard_cache_async.py  # Cache warming
│   ├── deploy_*.sh            # Deployment scripts
│   ├── test_*.py/sh           # Testing scripts
│   └── fix_*.py/sh            # Fix scripts
├── config/                     # Configuration files
├── alpha_system/              # Alpha generation strategies
├── venv311/                   # Python virtual environment (local)
├── PHASE2_IMPLEMENTATION_COMPLETE.md    # Phase 2 documentation (NEW)
├── CACHE_OPTIMIZATION_IMPLEMENTATION_GUIDE.md  # Cache guide (UPDATED)
├── PHASE1_PHASE2_DEPLOYMENT_SUMMARY.md  # Deployment summary (NEW)
└── requirements.txt           # Python dependencies
```

## Troubleshooting

### Common Issues
1. **Connection Timeouts**:
   - Check VPN/proxy settings
   - Verify API keys are valid
   - Check rate limits

2. **Cache Issues - Phase 2 Troubleshooting**:
   ```bash
   # Validate Phase 2 cache performance
   ./venv311/bin/python scripts/phase2_validation.py
   
   # Test production Phase 2 cache
   ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && ./venv311/bin/python scripts/phase2_validation.py"
   
   # Clear memcached (L2 cache)
   echo 'flush_all' | nc localhost 11211
   
   # Restart Redis (L3 cache)
   brew services restart redis  # macOS
   sudo systemctl restart redis # Linux
   
   # Manual cache warming
   ./venv311/bin/python scripts/populate_dashboard_cache_async.py
   ```

3. **Dashboard Not Loading**:
   - Verify ports 8003/8001 are not in use
   - Check cache connectivity
   - Review browser console for errors

4. **VPS Deployment Failures**:
   - Ensure SSH key is configured
   - Check disk space on VPS
   - Verify systemd service status

### Debug Commands
```bash
# Check running processes
ps aux | grep python

# Monitor API calls
curl -X GET http://localhost:8001/api/monitoring/metrics

# Test exchange connectivity
./venv311/bin/python scripts/test_exchange_connection.py

# View error logs
tail -f logs/error.log
```

## Security Notes
- Never commit API keys to git
- Use environment variables for sensitive data
- Regularly rotate API credentials
- Monitor for suspicious activity in logs
- Keep dependencies updated

## Claude Code Agents
When working with Claude Code on this project, utilize these specialized agents for optimal assistance:

### Trading & Market Analysis
- **python-trading-expert**: Use for implementing CCXT-based data fetching, creating trading bots with risk management, integrating with exchange APIs (Binance, Bybit), developing backtesting frameworks, building real-time market data pipelines, or troubleshooting exchange-specific issues.
- **trading-logic-validator**: Use to validate trading-related code, financial calculations, order execution logic, position sizing, portfolio management, and risk calculations where precision and correctness are critical.

### API & Integration
- **api-expert**: Use for designing and implementing REST APIs, securing endpoints, handling webhooks, authentication mechanisms (JWT, OAuth), rate limiting, and external service integrations.
- **webhook-expert**: Use for webhook configuration, validation, processing, troubleshooting HTTP callbacks, event payloads, signature verification, or API notifications.
- **dashboard-cache-api-integrator**: Use for designing and optimizing dashboard caching mechanisms, implementing Redis/Memcached solutions, reducing API load, optimizing cache hit/miss ratios, and troubleshooting performance issues in dashboard applications.

### UI/UX Development
- **fintech-ux-designer**: Use for designing user interfaces for the trading dashboards, creating wireframes for budgeting tools, investment dashboards, transaction trackers, or visualizing financial data in clean and intuitive ways.

### General Purpose
- **general-purpose**: Use for complex multi-step tasks, researching the codebase, or executing tasks that don't fit the specialized agents above.

### Usage Examples
```bash
# When implementing new exchange integration
# Ask: "Use python-trading-expert agent to implement Kraken exchange integration"

# When optimizing dashboard performance  
# Ask: "Use dashboard-cache-api-integrator agent to optimize mobile dashboard caching"

# When validating trading logic
# Ask: "Use trading-logic-validator to review the position sizing calculation"
```

## Development Best Practices
- Always activate venv311 before running locally
- Test changes locally before deploying
- Use deployment scripts rather than manual copies
- Monitor logs during deployment
- Keep cache TTLs appropriate for data type
- Document any new environment variables
- Follow existing code patterns and structure
- Leverage specialized Claude Code agents for domain-specific tasks
- The sync script I created (sync_local_from_vps.sh) can be used in the future to quickly sync any changes from VPS to local.