#!/bin/bash

# =============================================================================
# RAGAS Evaluation Runner (formerly TrueLens)
# =============================================================================
# This script provides a convenient wrapper around evaluate_ragas.py
# with common usage patterns and helpful defaults.
#
# Usage:
#   ./run_evaluation.sh [options]
#
# Examples:
#   ./run_evaluation.sh                    # Full evaluation (all questions in test set)
#   ./run_evaluation.sh --test             # Quick test (5 questions)
#   ./run_evaluation.sh --model llama3.2   # Specify generation model
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
RUN_NAME=""
CATEGORY=""
TEST_ID=""

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
RAGAS Evaluation Runner

Usage: $0 [options]

Options:
    -t, --test              Quick test with 5 questions
    -l, --limit N           Evaluate N questions
    -m, --model MODEL       Use specific generation model (e.g., llama3.2, mistral)
    -r, --retrieval STRAT   Use retrieval strategy (semantic, standard, semantic-rerank)
    -n, --name NAME         Name/Tag for this run (default: 'run')
    -c, --category CAT      Filter by category (e.g., 'Adversarial')
    -i, --id ID             Filter by specific Test ID
    -h, --help              Show this help message

Presets:
    --quick                 5 questions
    --full                  All questions (default)

Examples:
    $0                              # Full evaluation
    $0 --test                       # Quick test (5 questions)
    $0 --limit 10 --model mistral   # 10 questions with Mistral
    $0 --category Adversarial       # Run only adversarial questions

Environment:
    Reads configuration from .env file
    Ensure ANTHROPIC_API_KEY is set for the Judge
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -t|--test|--quick)
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
        -n|--name|--app-id) # Support app-id legacy flag
            RUN_NAME="$2"
            shift 2
            ;;
        -c|--category)
            CATEGORY="$2"
            shift 2
            ;;
        -i|--id)
            TEST_ID="$2"
            shift 2
            ;;
        --full)
            LIMIT=""
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
print_header "RAGAS Evaluation Pre-flight Checks"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi
print_success "Python 3 found"

# Check if evaluate_ragas.py exists
if [ ! -f "scripts/evaluate_ragas.py" ]; then
    print_error "scripts/evaluate_ragas.py not found"
    exit 1
fi
print_success "evaluate_ragas.py found"

# Check if .env exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found (will use defaults)"
else
    print_success ".env file found"
fi

# Export Environment Variables for Model/Retrieval override
if [ -n "$MODEL" ]; then
    export LLM_MODEL_NAME="$MODEL"
    print_info "Overriding Model: $MODEL"
fi

if [ -n "$RETRIEVAL" ]; then
    export RETRIEVAL_STRATEGY="$RETRIEVAL"
    print_info "Overriding Retrieval Strategy: $RETRIEVAL"
fi

# Build command
CMD="python3 scripts/evaluate_ragas.py"

if [ -n "$LIMIT" ]; then
    CMD="$CMD --limit $LIMIT"
fi

if [ -n "$RUN_NAME" ]; then
    CMD="$CMD --name $RUN_NAME"
fi

if [ -n "$CATEGORY" ]; then
    CMD="$CMD --category $CATEGORY"
fi

if [ -n "$TEST_ID" ]; then
    CMD="$CMD --id $TEST_ID"
fi

# Show configuration
print_header "Evaluation Configuration"
echo "Command: $CMD"
echo ""
echo "Settings:"
[ -n "$LIMIT" ] && echo "  - Questions: $LIMIT" || echo "  - Questions: All"
[ -n "$MODEL" ] && echo "  - Gen Model: $MODEL" || echo "  - Gen Model: from .env ($LLM_MODEL_NAME)"
[ -n "$RETRIEVAL" ] && echo "  - Retrieval: $RETRIEVAL" || echo "  - Retrieval: from .env ($RETRIEVAL_STRATEGY)"
echo ""

# Run evaluation
print_header "Running Evaluation"
echo ""

if $CMD; then
    echo ""
    print_header "Evaluation Complete"
    print_success "Ragas evaluation finished successfully."
    
    # Show latest results file
    LATEST_RESULT=$(ls -t evaluation_results/ragas_results_*.csv 2>/dev/null | head -1)
    if [ -n "$LATEST_RESULT" ]; then
        print_info "Results saved to: $LATEST_RESULT"
    fi

    echo ""
    print_info "Next steps:"
    echo "  1. Launch dashboard: ./scripts/dashboard/start_dashboard.sh"
    echo ""

    exit 0
else
    echo ""
    print_header "Evaluation Failed"
    print_error "Evaluation encountered errors"
    print_info "Check the error messages above for details"
    exit 1
fi
