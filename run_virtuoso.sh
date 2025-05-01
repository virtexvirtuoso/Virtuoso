#!/bin/bash

# Change to the project directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv311/bin/activate

# Source InfluxDB environment variables
source set_influxdb_env.sh

# Note: Matplotlib logs are now silenced automatically in src/__init__.py
# when the application starts, so we don't need the PYTHONCODE export anymore

# Run the application from the project root directory
python -m src.main "$@" 