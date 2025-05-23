import re

# Path to the file we need to fix
file_path = 'market_reporter.py'

# Read the content of the file
with open(file_path, 'r') as file:
    content = file.read()

# Find and fix the problematic section
# The issue is with the import aiohttp line and indentation
pattern = r'(.*if result\.get\(\'smi_value\', 50\) == 50:.+?\n.*self\.logger\.info.*\n[ \t]*)(import aiohttp)(\n[ \t]*try:)'
replacement = r'\1                import aiohttp\3'

# Apply the replacement
fixed_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Find and fix the indentation for the 'if response.status == 200:' line
pattern2 = r'(.*async with session\.get\(url, timeout=10\) as response:.*\n[ \t]*)(if response\.status == 200:)'
replacement2 = r'\1                            if response.status == 200:'

fixed_content = re.sub(pattern2, replacement2, fixed_content, flags=re.DOTALL)

# Write the fixed content back to the file
with open(file_path, 'w') as file:
    file.write(fixed_content)

print("Fixed indentation issues in market_reporter.py") 