#!/bin/bash
# Deploy admin dashboard to VPS

VPS_HOST="linuxuser@45.77.40.77"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_DIR="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

echo "🚀 Deploying Admin Dashboard to VPS..."
echo "=" 
echo "Target: $VPS_HOST:$VPS_DIR"
echo "="

# Files to deploy
ADMIN_FILES=(
    "src/api/routes/admin.py"
    "src/dashboard/templates/admin_login.html"
    "src/dashboard/templates/admin_dashboard.html"
    "src/api/__init__.py"
    "scripts/setup_fern_admin.py"
    "scripts/setup_admin_password.py"
    "docs/ADMIN_DASHBOARD_SETUP.md"
)

# Create directories on VPS if they don't exist
echo "📁 Creating directories on VPS..."
ssh $VPS_HOST "mkdir -p $VPS_DIR/src/api/routes $VPS_DIR/src/dashboard/templates $VPS_DIR/scripts $VPS_DIR/docs"

# Copy files
echo "📤 Copying admin dashboard files..."
for file in "${ADMIN_FILES[@]}"; do
    echo "   - $file"
    scp "$LOCAL_DIR/$file" "$VPS_HOST:$VPS_DIR/$file"
done

# Copy .env file if it exists (but only if ADMIN_PASSWORD_HASH is set)
if grep -q "ADMIN_PASSWORD_HASH" "$LOCAL_DIR/.env" 2>/dev/null; then
    echo "🔐 Updating .env with admin password hash..."
    # Extract just the ADMIN_PASSWORD_HASH line
    grep "ADMIN_PASSWORD_HASH" "$LOCAL_DIR/.env" > /tmp/admin_hash.txt
    
    # Check if .env exists on VPS and update it
    ssh $VPS_HOST "
        cd $VPS_DIR
        if [ -f .env ]; then
            # Remove existing ADMIN_PASSWORD_HASH if present
            grep -v 'ADMIN_PASSWORD_HASH' .env > .env.tmp || true
            mv .env.tmp .env
        fi
        echo '' >> .env
        echo '# Admin Dashboard Authentication' >> .env
        cat >> .env
    " < /tmp/admin_hash.txt
    
    rm /tmp/admin_hash.txt
    echo "✅ Admin password hash added to VPS .env"
fi

# Set permissions
echo "🔒 Setting permissions..."
ssh $VPS_HOST "
    cd $VPS_DIR
    chmod +x scripts/setup_*.py
    chmod 644 src/dashboard/templates/*.html
"

# Verify deployment
echo ""
echo "✅ Deployment complete! Verifying files..."
ssh $VPS_HOST "
    cd $VPS_DIR
    echo 'Files deployed:'
    ls -la src/api/routes/admin.py
    ls -la src/dashboard/templates/admin_*.html
    echo ''
    echo 'Admin password configured:' 
    grep -q 'ADMIN_PASSWORD_HASH' .env && echo '✅ Yes' || echo '❌ No'
"

echo ""
echo "🎉 Admin Dashboard deployed successfully!"
echo "📍 Access at: http://45.77.40.77:8003/api/dashboard/admin/login"
echo "🔐 Password: xrpsuxcock"
echo ""
echo "⚠️  Make sure the Virtuoso app is running on the VPS!"