#!/bin/bash

# Change to the project directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv311/bin/activate

# Source environment variables for InfluxDB if the script exists
if [ -f "scripts/set_influxdb_env.sh" ]; then
    echo "Sourcing InfluxDB environment variables..."
    source scripts/set_influxdb_env.sh
else
    echo "InfluxDB environment setup script not found, skipping."
fi

# Ensure templates are up-to-date
if [ -f "scripts/ensure_templates.py" ]; then
    echo "Ensuring templates are up-to-date..."
    python scripts/ensure_templates.py
else
    echo "Template ensure script not found, skipping."
fi

# Note: Matplotlib logs are now silenced automatically in src/__init__.py
# when the application starts, so we don't need the PYTHONCODE export anymore

# Run the application from the project root directory
python -m src.main "$@" 