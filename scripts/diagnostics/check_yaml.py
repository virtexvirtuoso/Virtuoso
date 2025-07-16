import yaml
import sys

# Try to load the file and see what specific error we get
try:
    with open('config/alpha_optimization.yaml', 'r') as f:
        content = f.read()
    
    # Check for mixed tabs and spaces
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if '\t' in line and ' ' in line.lstrip():
            print(f'Line {i}: Mixed tabs and spaces detected')
        if i >= 10 and i <= 20:
            print(f'Line {i}: {repr(line)}')
            
    # Try to parse
    data = yaml.safe_load(content)
    print('YAML parsed successfully')
    
except yaml.YAMLError as e:
    print(f'YAML Error: {e}')
except Exception as e:
    print(f'Other Error: {e}') 