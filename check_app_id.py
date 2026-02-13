import sqlite3
import os

def check_app_in_db(db_path, app_id):
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables in {db_path}: {tables}")

        if 'apps' in tables:
            query = f"SELECT app_id FROM apps WHERE app_id = ? OR app_json LIKE ?"
            cursor.execute(query, (app_id, f'%{app_id}%'))
            result = cursor.fetchall()
            if result:
                print(f"FOUND: App ID '{app_id}' found in {db_path} (apps table)")
                for row in result:
                    print(f"  - Match: {row}")
                conn.close()
                return True
        elif 'trulens_apps' in tables:
            query = f"SELECT app_id FROM trulens_apps WHERE app_id = ? OR app_json LIKE ?"
            cursor.execute(query, (app_id, f'%{app_id}%'))
            result = cursor.fetchall()
            if result:
                print(f"FOUND: App ID '{app_id}' found in {db_path} (trulens_apps table)")
                for row in result:
                    print(f"  - Match: {row}")
                conn.close()
                return True
        
        # Also check feedback or similar tables if apps table doesn't exist or not found
        # But 'apps' is the standard table for TrueLens
        
        conn.close()
    except Exception as e:
        print(f"Error checking {db_path}: {e}")
    
    print(f"NOT FOUND: App ID '{app_id}' not found in {db_path} as a direct app_id")
    
    # List all apps and check their JSON content
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row # Access columns by name
        cursor = conn.cursor()
        
        if 'trulens_apps' in tables:
            cursor.execute("SELECT * FROM trulens_apps")
            apps = cursor.fetchall()
            print(f"\n--- Inspecting {len(apps)} apps in {db_path} ---")
            for app in apps:
                print(f"ID: {app['app_id']}")
                # Check if our target string is anywhere in the row
                row_str = str(dict(app))
                if app_id in row_str:
                     print(f"  !!! FOUND MATCH in row data !!!")
                
                # Print the full app_json to be sure (it might be at the end)
                if 'app_json' in app.keys():
                    print(f"  FULL JSON: {app['app_json']}")
                print("-" * 20)
        
        if 'trulens_records' in tables:
            cursor.execute("SELECT count(*) FROM trulens_records")
            count = cursor.fetchone()[0]
            print(f"\nTotal Records in DB: {count}")
            
            # Show latest record timestamp
            cursor.execute("SELECT ts FROM trulens_records ORDER BY ts DESC LIMIT 1")
            last_ts = cursor.fetchone()
            if last_ts:
                print(f"Latest Record Timestamp: {last_ts[0]}")

        if 'trulens_events' in tables:
             cursor.execute("SELECT count(*) FROM trulens_events")
             count = cursor.fetchone()[0]
             print(f"\nTotal Events in DB: {count}")
                
        conn.close()
    except Exception as e:
        print(f"Error listing apps: {e}")

    return False

if __name__ == "__main__":
    app_id_to_check = "eval_semantic-rerank_llama_20260213_155222"
    
    # Check default location
    check_app_in_db("data/databases/default.sqlite", app_id_to_check)
    
    # Check explicit TrueLens db if it exists
    check_app_in_db("trulens_eval.db", app_id_to_check) # local in root
    check_app_in_db("data/databases/trulens_eval.db", app_id_to_check) # inside data/databases
