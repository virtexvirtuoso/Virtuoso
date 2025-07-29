# Virtuoso Trading System - Docker Deployment

This guide explains how to deploy the Virtuoso Trading System using Docker on any machine.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB+ RAM recommended
- 10GB+ disk space

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Virtuoso_ccxt
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

3. **Build and run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

## Manual Docker Commands

### Build the image
```bash
./docker-build.sh
# or
docker build -t virtuoso-trading:latest .
```

### Run the container
```bash
./docker-run.sh
# or manually with custom settings
docker run -d \
  --name virtuoso-trading \
  -p 8003:8003 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config:/app/config:ro \
  --env-file .env \
  --memory="4g" \
  --cpus="2" \
  virtuoso-trading:latest
```

## Docker Compose Options

### Basic deployment
```bash
docker-compose up -d
```

### With Redis caching
```bash
docker-compose --profile with-redis up -d
```

### With PostgreSQL database
```bash
docker-compose --profile with-database up -d
```

### With all services
```bash
docker-compose --profile with-redis --profile with-database up -d
```

## Container Management

### View logs
```bash
docker-compose logs -f virtuoso
# or
docker logs -f virtuoso-trading
```

### Stop services
```bash
docker-compose down
# or
docker stop virtuoso-trading
```

### Restart services
```bash
docker-compose restart
# or
docker restart virtuoso-trading
```

### Update and redeploy
```bash
git pull
docker-compose build
docker-compose up -d
```

## Resource Configuration

The default configuration allocates:
- Memory: 4GB limit (5GB with swap)
- CPU: 2 cores
- Logging: JSON with rotation (100MB x 10 files)

Adjust these in `docker-compose.yml`:
```yaml
mem_limit: 4g        # Change memory limit
memswap_limit: 5g    # Change swap limit
cpus: 2              # Change CPU cores
```

## Health Monitoring

Check service health:
```bash
curl http://localhost:8003/health
```

View container stats:
```bash
docker stats virtuoso-trading
```

## Volumes

The following directories are mounted:
- `./logs:/app/logs` - Application logs
- `./reports:/app/reports` - Trading reports
- `./data:/app/data` - Persistent data
- `./config:/app/config:ro` - Configuration (read-only)

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs virtuoso

# Verify environment
docker-compose config

# Check resource limits
docker system df
```

### Memory issues
```bash
# Increase memory limit in docker-compose.yml
mem_limit: 4g
memswap_limit: 5g
```

### Permission issues
```bash
# Fix ownership
docker exec virtuoso-trading chown -R virtuoso:virtuoso /app/logs
```

## Security Notes

1. Never commit `.env` files with real API keys
2. Use strong passwords for database services
3. Restrict port exposure in production
4. Regularly update base images
5. Use secrets management for sensitive data

## Production Deployment

For production use:

1. Use Docker Swarm or Kubernetes
2. Implement proper secrets management
3. Set up monitoring (Prometheus/Grafana)
4. Configure backups for volumes
5. Use a reverse proxy (nginx/traefik)
6. Enable TLS/SSL for API endpoints

## Multi-Architecture Support

The image supports:
- linux/amd64
- linux/arm64

Build for specific platform:
```bash
docker build --platform linux/amd64 -t virtuoso-trading:latest .
```

## Backup and Restore

### Backup
```bash
docker run --rm -v virtuoso_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/virtuoso-backup-$(date +%Y%m%d).tar.gz -C / data
```

### Restore
```bash
docker run --rm -v virtuoso_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/virtuoso-backup-20250728.tar.gz -C /
```