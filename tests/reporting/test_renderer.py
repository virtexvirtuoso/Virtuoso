from jinja2 import Environment, FileSystemLoader
import json
import os

# Load the JSON data
with open('reports/json/market_report_1747022239.json', 'r') as f:
    data = json.load(f)

# Add summary fields to each section
if 'market_overview' in data and 'summary' not in data['market_overview']:
    regime = data['market_overview'].get('regime', 'NEUTRAL')
    volatility = data['market_overview'].get('volatility', 0)
    data['market_overview']['summary'] = f'The market is currently in a {regime.lower()} regime with {volatility:.2f}% volatility.'

if 'futures_premium' in data and 'summary' not in data['futures_premium']:
    avg_premium = data['futures_premium'].get('average_premium_value', 0)
    data['futures_premium']['summary'] = f'Futures market is showing a premium of {avg_premium:.2f}%.'

if 'smart_money_index' in data and 'summary' not in data['smart_money_index']:
    smi_value = data['smart_money_index'].get('smi_value', 50)
    data['smart_money_index']['summary'] = f'Smart money index is at {smi_value:.2f}.'

if 'whale_activity' in data and 'summary' not in data['whale_activity']:
    has_activity = data['whale_activity'].get('has_significant_activity', False)
    data['whale_activity']['summary'] = f'Whale activity is {"significant" if has_activity else "minimal"}.'

# Set up Jinja2 environment
env = Environment(loader=FileSystemLoader('./src/templates'))
template = env.get_template('market_report_dark.html')

# Render template
output = template.render(**data)

# Save output
with open('test_rendered.html', 'w') as f:
    f.write(output)

print('Template rendered to test_rendered.html') 