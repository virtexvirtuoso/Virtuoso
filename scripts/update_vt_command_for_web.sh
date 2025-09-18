#!/bin/bash

echo "🔧 Updating vt command to manage both services..."

# Create updated control script
cat << 'EOF' > /tmp/update_vt_control.sh
#!/bin/bash

# Find the virtuoso_control.sh file and update it
CONTROL_FILE="/home/linuxuser/virtuoso_control.sh"

# Backup the original
cp $CONTROL_FILE ${CONTROL_FILE}.backup.$(date +%Y%m%d_%H%M%S)

# Update start command (option 7)
sed -i 's|sudo systemctl start virtuoso|sudo systemctl start virtuoso virtuoso-web|g' $CONTROL_FILE

# Update stop command (option 8)  
sed -i 's|sudo systemctl stop virtuoso|sudo systemctl stop virtuoso virtuoso-web|g' $CONTROL_FILE

# Update restart to handle both services
sed -i 's|sudo systemctl restart virtuoso|sudo systemctl restart virtuoso virtuoso-web|g' $CONTROL_FILE

# Add status check for both services
if ! grep -q "virtuoso-web" $CONTROL_FILE; then
    # Find the status section and update it
    sed -i '/systemctl status virtuoso/a\    echo "Web Server Status:"\n    sudo systemctl status virtuoso-web --no-pager | head -5' $CONTROL_FILE
fi

echo "✅ Updated vt command to manage both services"
echo ""
echo "Testing commands:"
echo "1. Status check:"
sudo systemctl status virtuoso --no-pager | head -3
sudo systemctl status virtuoso-web --no-pager | head -3

echo ""
echo "2. Available commands:"
echo "   vt start  - Starts both monitoring and web server"
echo "   vt stop   - Stops both services"
echo "   vt restart - Restarts both services"
echo "   vt status - Shows status of both services"
EOF

# Deploy to VPS
scp /tmp/update_vt_control.sh linuxuser@${VPS_HOST}:/tmp/

ssh linuxuser@${VPS_HOST} << 'REMOTE'
chmod +x /tmp/update_vt_control.sh
/tmp/update_vt_control.sh

# Test the updated command
echo ""
echo "🧪 Testing updated vt command..."
echo "Checking current status:"
vt status 2>/dev/null | head -10 || echo "Status command may need updating"
REMOTE

echo "✅ vt command updated to manage both services!"