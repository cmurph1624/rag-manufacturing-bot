#!/usr/bin/env python3
"""
TruLens Dashboard Launcher

This script starts the TruLens dashboard for viewing evaluation results.
The dashboard will open in your default browser at http://localhost:8501
"""

from trulens.dashboard import run_dashboard
from trulens.core import TruSession

def main():
    print("=" * 60)
    print("   TruLens Evaluation Dashboard")
    print("=" * 60)
    print()
    print("Starting TruLens dashboard...")
    print("Database: data/databases/trulens_eval.db")
    print()
    print("The dashboard will open in your default browser.")
    print("URL: http://localhost:8501")
    print()
    print("Press Ctrl+C in this terminal to stop the dashboard server.")
    print("=" * 60)
    print()

    # Initialize session (connects to existing database)
    session = TruSession(database_url="sqlite:///data/databases/trulens_eval.db")

    # Launch dashboard
    # This will block and keep the dashboard running
    try:
        run_dashboard(session=session, port=8501, force=True)
    except KeyboardInterrupt:
        print("\n\nDashboard stopped by user.")
    except Exception as e:
        print(f"\n\nError launching dashboard: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure data/databases/trulens_eval.db exists")
        print("2. Try: pip install --upgrade trulens trulens-providers-langchain")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
