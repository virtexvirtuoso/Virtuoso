# Virtuoso Dashboard Access Guide

## Problem Solved ✅

The dashboard was hardcoded to use port 8002, but your server was running on port 8003. This has been fixed by making the dashboard port-agnostic.

## Dashboard URLs

Your server is currently running on port **8003**. Access the dashboard at:

- **Main Dashboard**: http://localhost:8003/dashboard
- **API Overview**: http://localhost:8003/api/dashboard/overview
- **Health Check**: http://localhost:8003/health

## Alternative Dashboard Views

- **Original Dashboard**: http://localhost:8003/dashboard/v1
- **Beta Analysis**: http://localhost:8003/beta-analysis  
- **Market Analysis**: http://localhost:8003/market-analysis

## How to Find Your Server Port

If you're unsure which port your server is running on:

```bash
# Check listening ports
lsof -i -P | grep LISTEN | grep Python

# Check running Python processes
ps aux | grep python | grep main.py
```

## Port Configuration

The server uses automatic port fallback. Default ports in order:
1. 8000 (primary)
2. 8001, 8002, 8003, 8080, 3000, 5000 (fallbacks)

## Fixed Issues

1. ✅ **Port Mismatch**: Dashboard now detects server port automatically
2. ✅ **API Endpoints**: All API calls now use dynamic base URL
3. ✅ **WebSocket**: Real-time updates now work on any port
4. ✅ **Signal Tracking**: All tracking endpoints updated

## Dashboard Features

- **Real-time Signal Matrix**: Live confluence analysis
- **Alpha Opportunities**: High-probability trading signals  
- **Performance Metrics**: System and trading statistics
- **Live Signals**: Active trading alerts
- **Signal Tracking**: Monitor active positions
- **WebSocket Updates**: Real-time data streaming

## Troubleshooting

If the dashboard still doesn't load:

1. **Check Server Status**: Ensure `src/main.py` is running
2. **Verify Port**: Use `lsof -i -P | grep LISTEN` to find the correct port
3. **Check Browser Console**: Look for API connection errors
4. **Test API Directly**: Visit `http://localhost:PORT/api/dashboard/overview`

## Next Steps

The dashboard is now fully functional and port-agnostic. You can:

1. Access it at http://localhost:8003/dashboard
2. Explore the real-time signal confluence matrix
3. Monitor alpha opportunities and trading signals
4. Use the signal tracking features for active positions 