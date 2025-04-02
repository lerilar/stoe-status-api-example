#!/bin/bash

# Absolute path to the project directory
PROJECT_DIR="/home/erik/stoe.status"

# Navigate to project directory
cd "$PROJECT_DIR" || exit 1

# Activate the virtual environment
source venv/bin/activate

# Run the status checker script
python3 status_checker.py

# Deactivate the virtual environment
deactivate
