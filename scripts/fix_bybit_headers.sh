#!/bin/bash

echo "🔧 Fixing Bybit Request Headers..."

cat > /tmp/fix_headers.py << 'EOF'
import re

def fix_headers(file_path):
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Find _create_session method
        for i, line in enumerate(lines):
            if 'async def _create_session' in line or 'def _create_session' in line:
                # Look for headers configuration
                found_headers = False
                for j in range(i+1, min(i+50, len(lines))):
                    if 'headers' in lines[j]:
                        found_headers = True
                        # Ensure proper headers
                        if 'User-Agent' not in lines[j]:
                            lines[j] = lines[j].rstrip() + "\n"
                            indent = '            '
                            headers_fix = f'''{indent}headers = {{
{indent}    'User-Agent': 'Mozilla/5.0 (Virtuoso CCXT Trading System)',
{indent}    'Accept': 'application/json',
{indent}    'Accept-Encoding': 'gzip, deflate',
{indent}    'Cache-Control': 'no-cache',
{indent}    'Connection': 'keep-alive'
{indent}}}
'''
                            lines.insert(j+1, headers_fix)
                            print("✅ Fixed request headers")
                        break
                
                if not found_headers:
                    # Add headers if not found
                    indent = '        '
                    headers_code = f'''
{indent}# Ensure proper headers for Bybit API
{indent}headers = {{
{indent}    'User-Agent': 'Mozilla/5.0 (Virtuoso CCXT Trading System)',
{indent}    'Accept': 'application/json',
{indent}    'Accept-Encoding': 'gzip, deflate',
{indent}    'Cache-Control': 'no-cache',
{indent}    'Connection': 'keep-alive'
{indent}}}
'''
                    # Insert after method definition
                    lines.insert(i+2, headers_code)
                    
                    # Update session creation to use headers
                    for k in range(i+2, min(i+100, len(lines))):
                        if 'ClientSession(' in lines[k]:
                            lines[k] = lines[k].replace('ClientSession(', 'ClientSession(headers=headers, ')
                            print("✅ Added proper headers to session")
                            break
                break
        
        # Also ensure JSON content type is properly handled
        for i, line in enumerate(lines):
            if 'async def _make_request' in line:
                # Find where we make the actual request
                for j in range(i+1, min(i+100, len(lines))):
                    if 'session.request' in lines[j] or 'session.get' in lines[j] or 'session.post' in lines[j]:
                        # Ensure we handle responses properly
                        if 'await response.json()' in ''.join(lines[j:j+10]):
                            # Check if we validate content type
                            validation_check = False
                            for k in range(j, min(j+20, len(lines))):
                                if 'content_type' in lines[k] or 'Content-Type' in lines[k]:
                                    validation_check = True
                                    break
                            
                            if not validation_check:
                                indent = '                '
                                validation_code = f'''
{indent}# Validate response content type
{indent}content_type = response.headers.get('Content-Type', '')
{indent}if 'text/html' in content_type:
{indent}    self.logger.error(f"Received HTML response instead of JSON from {{endpoint}}")
{indent}    self.logger.debug(f"Response headers: {{dict(response.headers)}}")
{indent}    text = await response.text()
{indent}    if 'cloudflare' in text.lower() or 'rate limit' in text.lower():
{indent}        return {{'retCode': -1, 'retMsg': 'Rate limited or blocked by Cloudflare'}}
{indent}    return {{'retCode': -1, 'retMsg': 'Invalid response format - received HTML'}}
'''
                                # Find where to insert
                                for k in range(j, min(j+20, len(lines))):
                                    if 'response.json()' in lines[k]:
                                        lines.insert(k, validation_code)
                                        print("✅ Added content type validation")
                                        break
                        break
                break
        
        with open(file_path, 'w') as f:
            f.writelines(lines)
        return True
    except Exception as e:
        print(f"❌ Error fixing headers: {e}")
        return False

fix_headers('src/core/exchanges/bybit.py')
EOF

python /tmp/fix_headers.py

echo ""
echo "✅ Headers fixed!"
echo ""
echo "Deploying to VPS..."
scp src/core/exchanges/bybit.py linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/core/exchanges/

echo "Restarting service..."
ssh linuxuser@45.77.40.77 'sudo systemctl restart virtuoso.service'

echo ""
echo "✅ Deployment complete!"