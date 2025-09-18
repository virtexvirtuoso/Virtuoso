#!/bin/bash

# Fix the DI registration syntax issue in main.py

cat > /tmp/fix_di.py << 'EOF'
with open('/home/linuxuser/trading/Virtuoso_ccxt/src/main.py', 'r') as f:
    lines = f.readlines()

# Find and fix the broken try block
fixed_lines = []
for i, line in enumerate(lines):
    if "# Register configured SignalGenerator in DI container as singleton" in line and i < len(lines) - 1:
        # This is our marker comment
        fixed_lines.append(line)
        # Skip the next few lines until we find the try block content
        i += 1
        while i < len(lines) and "from src.signal_generation.signal_generator import" not in lines[i]:
            fixed_lines.append(lines[i])
            i += 1
        # Now add the proper try block
        fixed_lines.append("    try:\n")
        fixed_lines.append("        container.register_instance(SignalGenerator, signal_generator)\n")
        fixed_lines.append("        logger.info(\"✅ Registered configured SignalGenerator in DI container as singleton\")\n")
        fixed_lines.append("    except Exception as e:\n")
        fixed_lines.append("        logger.warning(f\"Could not register SignalGenerator in DI container: {e}\")\n")
        fixed_lines.append("        # This is not critical - the system will still work but might not share OHLCV cache\n")
        # Skip the broken lines
        while i < len(lines) and "# This is not critical" not in lines[i]:
            i += 1
        if i < len(lines) and "# This is not critical" in lines[i]:
            i += 1  # Skip this line too
        # Continue with remaining lines
        while i < len(lines):
            if "from src.signal_generation.signal_generator import SignalGenerator" not in lines[i]:
                fixed_lines.append(lines[i])
            i += 1
        break
    else:
        fixed_lines.append(line)

# Write the fixed file
with open('/home/linuxuser/trading/Virtuoso_ccxt/src/main.py', 'w') as f:
    f.writelines(fixed_lines)

print("Fixed DI registration syntax")
EOF

python3 /tmp/fix_di.py