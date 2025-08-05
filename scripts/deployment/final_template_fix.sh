#!/bin/bash

echo "🔧 Final Template Configuration Fix"
echo "==================================="

cd ~/trading/Virtuoso_ccxt

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "\n${YELLOW}1. Checking current state:${NC}"
echo "Current directory: $(pwd)"
echo ""

echo "Templates in root directory:"
ls -la templates/ 2>/dev/null || echo "❌ No templates/ directory"
echo ""

echo "Templates in src/core/reporting/templates:"
ls -la src/core/reporting/templates/ 2>/dev/null || echo "❌ No src/core/reporting/templates/ directory"
echo ""

echo -e "${YELLOW}2. Current config settings:${NC}"
echo "reporting section from config.yaml:"
grep -A10 "^reporting:" config/config.yaml | grep -E "(template_dir|template_directory)" || echo "No template settings found"
echo ""

echo -e "${YELLOW}3. Fixing configuration:${NC}"
# Backup config
cp config/config.yaml config/config.yaml.backup_$(date +%Y%m%d_%H%M%S)

# Fix all template references to point to root templates directory
sed -i 's|template_dir: src/core/reporting/templates|template_dir: templates|g' config/config.yaml
sed -i 's|template_directory: src/core/reporting/templates|template_directory: templates|g' config/config.yaml

# Also handle any other variations
sed -i 's|template_dir: .*/templates|template_dir: templates|g' config/config.yaml
sed -i 's|template_directory: .*/templates|template_directory: templates|g' config/config.yaml

echo "✅ Updated config to use root templates directory"
echo ""

echo -e "${YELLOW}4. Verifying templates exist:${NC}"
# Ensure templates directory exists and has files
if [ ! -d "templates" ]; then
    echo "❌ templates/ directory missing, creating it..."
    mkdir -p templates
    
    # Copy from src location if it exists
    if [ -d "src/core/reporting/templates" ]; then
        echo "📁 Copying templates from src/core/reporting/templates..."
        cp -r src/core/reporting/templates/* templates/
    fi
fi

# List templates
echo "Templates available:"
ls -la templates/*.html 2>/dev/null || echo "❌ No HTML templates found!"
echo ""

echo -e "${YELLOW}5. Final configuration check:${NC}"
grep -A10 "^reporting:" config/config.yaml | grep -E "(template_dir|template_directory)"
echo ""

echo -e "${YELLOW}6. Testing ReportManager path resolution:${NC}"
python3 << 'EOF'
import os
import yaml

# Load config
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

reporting_config = config.get('reporting', {})
template_dir = reporting_config.get('template_dir') or reporting_config.get('template_directory')

print(f"Template directory from config: {template_dir}")
print(f"Current working directory: {os.getcwd()}")
print(f"Full template path: {os.path.join(os.getcwd(), template_dir) if template_dir else 'None'}")
print(f"Template directory exists: {os.path.exists(template_dir) if template_dir else False}")

if template_dir and os.path.exists(template_dir):
    print(f"Templates found: {len([f for f in os.listdir(template_dir) if f.endswith('.html')])}")
EOF
echo ""

echo -e "${GREEN}==================================="
echo "✅ Template configuration fixed!"
echo "===================================${NC}"
echo ""
echo "Now run your bot:"
echo "  python src/main.py"
echo ""
echo "The templates are now in: $(pwd)/templates/"
echo "Config points to: templates"
echo ""

# Activate venv if not already
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Don't forget to activate your virtual environment:"
    echo "  source venv/bin/activate"
fi