#!/bin/bash

echo "🔐 SSH Key Generation for Vultr VPS"
echo "===================================="
echo ""

# Check if SSH key already exists
if [ -f ~/.ssh/id_ed25519 ]; then
    echo "⚠️  Ed25519 SSH key already exists!"
    echo ""
    echo "Your public key is:"
    echo "-------------------"
    cat ~/.ssh/id_ed25519.pub
    echo "-------------------"
    echo ""
    echo "Copy the above key and paste it in Vultr's SSH Keys section"
    exit 0
fi

# Generate new Ed25519 key (more secure than RSA)
echo "Generating new Ed25519 SSH key..."
ssh-keygen -t ed25519 -C "vultr-trading-bot" -f ~/.ssh/id_ed25519 -N ""

echo ""
echo "✅ SSH Key Generated Successfully!"
echo ""
echo "Your public key (copy this entire line for Vultr):"
echo "=================================================="
cat ~/.ssh/id_ed25519.pub
echo "=================================================="
echo ""
echo "📋 Instructions:"
echo "1. Copy the key above (the entire line starting with 'ssh-ed25519')"
echo "2. Go back to Vultr deployment page"
echo "3. Click 'Manage SSH Keys' or 'Add New'"
echo "4. Paste the key and give it a name like 'Mac Mini Trading Key'"
echo "5. Select it during deployment"
echo ""
echo "🔒 Your private key is stored at: ~/.ssh/id_ed25519"
echo "⚠️  Keep this private key secure - never share it!"
echo ""
echo "To connect to your VPS later:"
echo "ssh -i ~/.ssh/id_ed25519 root@YOUR_VPS_IP"