#!/bin/bash

# Sync local changes to VPS
# This bypasses git authentication issues

echo "Syncing local changes to VPS..."

# Key directories and files to sync
rsync -avz --exclude='.git' \
  --exclude='venv*' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='logs/*' \
  --exclude='*.log' \
  --exclude='.DS_Store' \
  --exclude='node_modules' \
  --exclude='*.sqlite' \
  --exclude='*.db' \
  src/ \
  scripts/ \
  config/ \
  CHANGELOG.md \
  requirements.txt \
  vps:/home/linuxuser/trading/Virtuoso_ccxt/

echo "Sync complete!"

# Restart services
echo "Restarting VPS services..."
ssh vps "sudo systemctl restart virtuoso-web.service && sudo systemctl status virtuoso-web.service | head -5"

echo "Deployment complete!"