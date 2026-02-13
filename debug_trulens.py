import os
import sys
from src.trulens_config import initialize_trulens
from trulens.core import TruSession

def debug_trulens():
    # Use absolute path to match evaluate_trulens.py
    db_path = os.path.abspath("data/databases/trulens_eval.db")
    print(f"Testing DB Path: {db_path}")
    
    if not os.path.exists(db_path):
        print("Error: DB file does not exist!")
        return

    try:
        # Initialize
        print("Initializing session...")
        import logging
        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        
        session, feedbacks = initialize_trulens(database_path=db_path, reset=False)
        print("Session initialized.")
        
        # Check existing apps
        print("Listing apps via Session...")
        try:
             # Depending on TruLens version, getting apps might vary
             # Try direct DB access through session engine if exposed, or usage of get_apps
             if hasattr(session, 'get_apps'):
                 apps = session.get_apps()
                 print(f"Found {len(apps)} apps via TruSession")
             else:
                 print("Session does not have get_apps method")
                 
             # Verify records
             if hasattr(session, 'get_records_and_feedback'):
                 # app_ids=[] means all?
                 records, _ = session.get_records_and_feedback(app_ids=[])
                 print(f"Found {len(records)} records via TruSession")
                 
             # Try to add a dummy app/record?
             # This is complex with TruLens internal API.
             # But if session is valid, maybe just check if it's in WAL mode?
             cursor = session.sqlalchemy_engine.connect()
             result = cursor.execute("PRAGMA journal_mode")
             print(f"Journal Mode: {result.fetchone()[0]}")
             cursor.close()

        except Exception as e:
            print(f"Error querying session: {e}")

    except Exception as e:
        print(f"Initialization failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_trulens()
