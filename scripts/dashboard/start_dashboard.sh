#!/bin/bash

# =============================================================================
# TruLens Dashboard Launcher
# =============================================================================
# This script starts the TruLens dashboard for viewing evaluation results
#
# Usage:
#   ./start_dashboard.sh [port]
#
# Examples:
#   ./start_dashboard.sh        # Start on default port (8501)
#   ./start_dashboard.sh 8502   # Start on custom port
# =============================================================================

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default port
PORT=${1:-8501}

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  TruLens Dashboard${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗${NC} Python 3 is not installed"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python 3 found"

# Check if start_dashboard.py exists
if [ ! -f "scripts/dashboard/start_dashboard.py" ]; then
    echo -e "${RED}✗${NC} scripts/dashboard/start_dashboard.py not found"
    exit 1
fi
echo -e "${GREEN}✓${NC} start_dashboard.py found"

# Check if database exists
if [ ! -f "data/databases/trulens_eval.db" ]; then
    echo -e "${YELLOW}⚠${NC} data/databases/trulens_eval.db not found"
    echo -e "${YELLOW}⚠${NC} Run an evaluation first: ./scripts/run_evaluation.sh --test"
    echo ""
    echo -n "Start dashboard anyway? [y/N] "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo -e "${RED}✗${NC} Dashboard launch cancelled"
        exit 1
    fi
else
    # Show database info
    DB_SIZE=$(du -h data/databases/trulens_eval.db | cut -f1)
    echo -e "${GREEN}✓${NC} Database found (${DB_SIZE})"
fi

echo ""
echo -e "${BLUE}Starting TruLens dashboard on port ${PORT}...${NC}"
echo ""
echo -e "${GREEN}Dashboard URL: http://localhost:${PORT}${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the dashboard${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Run the Python launcher script
python3 scripts/dashboard/start_dashboard.py "$PORT"
