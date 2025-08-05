#!/bin/bash

echo "🔧 Fixing Template Configuration Issue"
echo "====================================="

cd ~/trading/Virtuoso_ccxt

# Check current config
echo "📋 Current template configuration:"
grep -A10 "^reporting:" config/config.yaml || echo "No reporting section found"

# Backup config
cp config/config.yaml config/config.yaml.backup_$(date +%Y%m%d_%H%M%S)

# Check if reporting section exists
if ! grep -q "^reporting:" config/config.yaml; then
    echo -e "\n📝 Adding reporting configuration..."
    cat >> config/config.yaml << 'EOF'

# Reporting configuration
reporting:
  template_dir: src/core/reporting/templates
  output_dir: reports
  enable_pdf: true
EOF
else
    echo "📝 Reporting section exists, checking template_dir..."
    # Check if template_dir exists
    if ! grep -q "template_dir:" config/config.yaml; then
        # Add template_dir under reporting section
        sed -i '/^reporting:/a\  template_dir: src/core/reporting/templates' config/config.yaml
    fi
fi

echo -e "\n✅ Updated configuration:"
grep -A5 "^reporting:" config/config.yaml

echo -e "\n📁 Verifying templates exist:"
ls -la src/core/reporting/templates/*.html | head -5

echo -e "\n🚀 Starting bot with fixed config..."
source venv/bin/activate
python src/main.py