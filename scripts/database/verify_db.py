import sqlite3
import os

DB_PATH = "evaluation_history.db"

def check_db():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n--- Runs Table ---")
    try:
        cursor.execute("SELECT * FROM runs")
        rows = cursor.fetchall()
        if not rows:
            print("No rows found in 'runs' table.")
        else:
            print(f"{'ID':<5} {'Timestamp':<25} {'Model':<15} {'Acc':<10} {'Qs':<5} {'Latency':<10}")
            print("-" * 75)
            for row in rows:
                print(f"{row[0]:<5} {row[1]:<25} {row[2]:<15} {row[3]:<10.2f} {row[4]:<5} {row[5]:<10.2f}")
    except Exception as e:
        print(f"Error reading DB: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_db()
