#!/bin/bash
# scripts/dashboard/start_dashboard.sh

# Ensure we are in the project root (assuming script is run from project root or scripts/dashboard)
# Get the absolute path of the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$PROJECT_ROOT"

echo "Starting RAGAS Dashboard..."
# Check if venv exists and activate if needed, or just use direct path
if [ -d "venv" ]; then
    source venv/bin/activate
fi

streamlit run scripts/dashboard/app.py
