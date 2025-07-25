# 🐳 Docker Testing Guide

This guide helps you test the Virtuoso Trading System locally with Docker before deploying to production.

## Prerequisites

- Docker Desktop installed and running
- At least 4GB RAM allocated to Docker
- Ports 8000, 8001, 8003 available

## Quick Test

```bash
# 1. Restore your original .env (if needed)
mv .env.backup .env 2>/dev/null || true

# 2. Use test environment
cp .env.test .env

# 3. Run simple Docker test
./scripts/test_docker_simple.sh

# 4. Start services
docker-compose up -d
```

## Step-by-Step Testing

### 1. Prepare Test Environment

```bash
# Create test environment file
cat > .env.test << EOF
DEBUG=true
LOG_LEVEL=DEBUG
BYBIT_API_KEY=test_key
BYBIT_API_SECRET=test_secret
DISCORD_WEBHOOK_URL=
INFLUXDB_URL=http://redis:8086
INFLUXDB_TOKEN=test_token
JWT_SECRET_KEY=test_jwt_secret
EOF

# Use test environment
cp .env.test .env
```

### 2. Build Docker Image

```bash
# Build the image
docker-compose build app

# This will:
# - Install all Python dependencies
# - Set up the application structure
# - Create a non-root user for security
```

### 3. Start Services

```bash
# Start Redis first
docker-compose up -d redis

# Wait for Redis to be ready
sleep 5

# Start the main application
docker-compose up -d app

# Check if running
docker-compose ps
```

### 4. Verify Health

```bash
# Check container logs
docker-compose logs --tail=50 app

# Test health endpoint
curl http://localhost:8001/health

# Expected response:
# {"status":"healthy","timestamp":"...","services":{...}}
```

### 5. Test API Endpoints

```bash
# API Documentation
open http://localhost:8001/docs

# Dashboard (if enabled)
open http://localhost:8003

# Main application
open http://localhost:8000
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs app

# Common issues:
# - Port already in use: kill $(lsof -t -i:8001)
# - Permission issues: Check file ownership
# - Missing dependencies: Rebuild with --no-cache
```

### Build Failures

```bash
# Clean build
docker-compose down -v
docker system prune -f
docker-compose build --no-cache
```

### Debugging Inside Container

```bash
# Access container shell
docker exec -it virtuoso-trading bash

# Inside container:
cd /app
python -m src.main --help
```

## Testing Checklist

- [ ] Docker builds successfully
- [ ] Container starts without errors
- [ ] Health endpoint responds
- [ ] Logs show normal operation
- [ ] No permission errors
- [ ] API documentation loads
- [ ] Redis connection works

## Clean Up

```bash
# Stop all services
docker-compose down

# Remove volumes (careful - this deletes data)
docker-compose down -v

# Restore original .env
mv .env.backup .env

# Remove test files
rm .env.test
```

## Production Deployment

Once local testing passes:

1. Update `.env` with production credentials
2. Deploy using:
   ```bash
   ./scripts/deployment/deploy_docker.sh --full
   ```

## Common Issues & Solutions

### Issue: Build takes too long
**Solution**: Use `.dockerignore` to exclude unnecessary files

### Issue: Container exits immediately
**Solution**: Check logs for Python errors, ensure all imports work

### Issue: Can't connect to API
**Solution**: Verify ports in docker-compose.yml match your system

### Issue: Permission denied errors
**Solution**: The container runs as non-root user 'trader' (UID 1000)

## Performance Tips

1. **Allocate enough RAM** to Docker (4GB minimum)
2. **Use volumes** for persistent data
3. **Enable BuildKit** for faster builds:
   ```bash
   export DOCKER_BUILDKIT=1
   ```

## Security Notes

- Never use test credentials in production
- Always use `.env` files, never hardcode secrets
- The Docker image runs as non-root user for security
- Regularly update base images for security patches

---

## Quick Commands Reference

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f

# Stop everything
docker-compose down

# Rebuild
docker-compose build --no-cache

# Check status
docker-compose ps

# Shell access
docker exec -it virtuoso-trading bash
```