# Virtuoso Trading System - Dashboard URLs Quick Reference

## 🌐 Production Server (Hetzner VPS)
**Server IP**: VPS_HOST_REDACTED

### User Interfaces
- **Desktop Dashboard**: http://VPS_HOST_REDACTED:8003/
- **Mobile Dashboard**: http://VPS_HOST_REDACTED:8003/mobile

### Health & Status
- **Health Check**: http://VPS_HOST_REDACTED:8003/health
- **System Status**: http://VPS_HOST_REDACTED:8001/api/monitoring/status

### API Endpoints
- **Dashboard Data**: http://VPS_HOST_REDACTED:8003/api/dashboard/data
- **Mobile Data**: http://VPS_HOST_REDACTED:8003/api/dashboard/mobile
- **Alerts**: http://VPS_HOST_REDACTED:8003/api/alerts
- **Configuration**: http://VPS_HOST_REDACTED:8003/api/config
- **Bitcoin Beta**: http://VPS_HOST_REDACTED:8003/api/bitcoin-beta
- **Performance Metrics**: http://VPS_HOST_REDACTED:8001/api/monitoring/metrics
- **Active Symbols**: http://VPS_HOST_REDACTED:8001/api/monitoring/symbols

---

## 💻 Local Development
**Host**: localhost

### User Interfaces
- **Desktop Dashboard**: http://localhost:8003/
- **Mobile Dashboard**: http://localhost:8003/mobile

### Health & Status
- **Health Check**: http://localhost:8003/health
- **System Status**: http://localhost:8001/api/monitoring/status

### API Endpoints
- **Dashboard Data**: http://localhost:8003/api/dashboard/data
- **Mobile Data**: http://localhost:8003/api/dashboard/mobile
- **Alerts**: http://localhost:8003/api/alerts
- **Configuration**: http://localhost:8003/api/config
- **Bitcoin Beta**: http://localhost:8003/api/bitcoin-beta
- **Performance Metrics**: http://localhost:8001/api/monitoring/metrics
- **Active Symbols**: http://localhost:8001/api/monitoring/symbols

---

## 🚀 Quick Commands

### Check if services are running:
```bash
# Production (Hetzner)
curl http://VPS_HOST_REDACTED:8003/health

# Local
curl http://localhost:8003/health
```

### SSH to production:
```bash
ssh vps
# or
ssh linuxuser@VPS_HOST_REDACTED
```

### Service control on VPS:
```bash
vt status    # Check status
vt restart   # Restart services
vt logs      # View logs
vt health    # Health check
```

### Start locally:
```bash
source venv311/bin/activate
python src/main.py
```

---

## 📊 Dashboard Features

### Desktop Dashboard
- Real-time market data for 30+ crypto pairs
- 6-dimensional confluence analysis
- Signal generation and alerts
- Order flow visualization
- Smart money flow tracking
- Bitcoin correlation analysis

### Mobile Dashboard
- Responsive design for mobile devices
- Simplified interface with key metrics
- Touch-optimized controls
- Real-time updates
- Alert notifications

---

*Last updated: August 28, 2025*  
*Server: Hetzner CCX23 (Dedicated CPU)*  
*Location: Ashburn, USA*