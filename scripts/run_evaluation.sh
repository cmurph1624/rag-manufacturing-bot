#!/bin/bash

# =============================================================================
# TruLens RAG Evaluation Runner
# =============================================================================
# This script provides a convenient wrapper around evaluate_trulens.py
# with common usage patterns and helpful defaults.
#
# Usage:
#   ./run_evaluation.sh [options]
#
# Examples:
#   ./run_evaluation.sh                    # Full evaluation (50 questions)
#   ./run_evaluation.sh --test             # Quick test (5 questions)
#   ./run_evaluation.sh --model llama3.2   # Specify model
#   ./run_evaluation.sh --help             # Show help
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
LIMIT=""
MODEL=""
RETRIEVAL=""
APP_ID=""
SKIP_FEEDBACK=""
EXTRA_ARGS=""

# Helper functions
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

show_help() {
    cat << EOF
TruLens RAG Evaluation Runner

Usage: $0 [options]

Options:
    -t, --test              Quick test with 5 questions
    -l, --limit N           Evaluate N questions
    -m, --model MODEL       Use specific model (e.g., llama3.2, mistral)
    -r, --retrieval STRAT   Use retrieval strategy (semantic, lexical, semantic-rerank)
    -a, --app-id ID         Custom app identifier
    -s, --skip-feedback     Skip feedback function evaluation (faster)
    -h, --help              Show this help message

Presets:
    --quick                 5 questions, skip feedback (fastest)
    --standard              20 questions, all feedback
    --full                  50 questions, all feedback (default)
    --comprehensive         100 questions, all feedback

Examples:
    $0                              # Full evaluation (50 questions)
    $0 --test                       # Quick test (5 questions)
    $0 --quick                      # 5 questions, no feedback
    $0 --limit 10 --model mistral   # 10 questions with Mistral
    $0 --comprehensive              # Full comprehensive evaluation

Environment:
    Reads configuration from .env file
    Ensure SLACK tokens and model settings are configured

For more information, see TRULENS_QUICKSTART.md
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -t|--test)
            LIMIT="5"
            shift
            ;;
        -l|--limit)
            LIMIT="$2"
            shift 2
            ;;
        -m|--model)
            MODEL="$2"
            shift 2
            ;;
        -r|--retrieval)
            RETRIEVAL="$2"
            shift 2
            ;;
        -a|--app-id)
            APP_ID="$2"
            shift 2
            ;;
        -s|--skip-feedback)
            SKIP_FEEDBACK="--skip-feedback"
            shift
            ;;
        --quick)
            LIMIT="5"
            SKIP_FEEDBACK="--skip-feedback"
            shift
            ;;
        --standard)
            LIMIT="20"
            shift
            ;;
        --full)
            LIMIT="50"
            shift
            ;;
        --comprehensive)
            LIMIT="100"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Pre-flight checks
print_header "TruLens Evaluation Pre-flight Checks"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi
print_success "Python 3 found"

# Check if evaluate_trulens.py exists
if [ ! -f "scripts/evaluation/evaluate_trulens.py" ]; then
    print_error "scripts/evaluation/evaluate_trulens.py not found"
    exit 1
fi
print_success "evaluate_trulens.py found"

# Check if .env exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found (will use defaults)"
    print_info "Copy .env.example to .env and configure if needed"
else
    print_success ".env file found"
fi

# Check if Ollama is running (if using local models)
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    print_warning "Ollama does not appear to be running on localhost:11434"
    print_info "If using Ollama models, start it with: ollama serve"
    echo -n "Continue anyway? [y/N] "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_error "Evaluation cancelled"
        exit 1
    fi
fi

# Build command
CMD="python3 scripts/evaluation/evaluate_trulens.py"

if [ -n "$LIMIT" ]; then
    CMD="$CMD --limit $LIMIT"
fi

if [ -n "$MODEL" ]; then
    CMD="$CMD --model $MODEL"
fi

if [ -n "$RETRIEVAL" ]; then
    CMD="$CMD --retrieval $RETRIEVAL"
fi

if [ -n "$APP_ID" ]; then
    CMD="$CMD --app-id $APP_ID"
fi

if [ -n "$SKIP_FEEDBACK" ]; then
    CMD="$CMD $SKIP_FEEDBACK"
fi

# Show configuration
print_header "Evaluation Configuration"
echo "Command: $CMD"
echo ""
echo "Settings:"
[ -n "$LIMIT" ] && echo "  - Questions: $LIMIT" || echo "  - Questions: 50 (default)"
[ -n "$MODEL" ] && echo "  - Model: $MODEL" || echo "  - Model: from .env or llama3.2"
[ -n "$RETRIEVAL" ] && echo "  - Retrieval: $RETRIEVAL" || echo "  - Retrieval: from .env or semantic"
[ -n "$APP_ID" ] && echo "  - App ID: $APP_ID" || echo "  - App ID: auto-generated"
[ -n "$SKIP_FEEDBACK" ] && echo "  - Feedback: DISABLED (faster)" || echo "  - Feedback: enabled"
echo ""

# Confirm if comprehensive
if [ "$LIMIT" = "100" ]; then
    print_warning "Comprehensive evaluation may take 15-30 minutes"
    echo -n "Continue? [y/N] "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_error "Evaluation cancelled"
        exit 1
    fi
fi

# Run evaluation
print_header "Running Evaluation"
echo ""

if $CMD; then
    echo ""
    print_header "Evaluation Complete"
    print_success "Results saved to data/databases/trulens_eval.db"
    print_info "View results: ./scripts/dashboard/start_dashboard.sh"

    # Show latest results file
    LATEST_RESULT=$(ls -t evaluation_results/trulens_eval_*.json 2>/dev/null | head -1)
    if [ -n "$LATEST_RESULT" ]; then
        print_info "JSON export: $LATEST_RESULT"
    fi

    echo ""
    print_info "Next steps:"
    echo "  1. Launch dashboard: ./scripts/dashboard/start_dashboard.sh"
    echo "  2. Analyze results: python scripts/evaluation/analyze_trulens_results.py"
    echo "  3. Compare runs: use the dashboard leaderboard"
    echo ""

    exit 0
else
    echo ""
    print_header "Evaluation Failed"
    print_error "Evaluation encountered errors"
    print_info "Check the error messages above for details"
    exit 1
fi
