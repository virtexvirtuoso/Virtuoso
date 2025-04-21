#!/bin/bash

# Change to the project directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv311/bin/activate

# Run the application
cd src
python main.py 