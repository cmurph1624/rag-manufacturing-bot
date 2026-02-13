
import sqlite3

def list_tables(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()
    return tables

if __name__ == "__main__":
    db_path = "data/databases/trulens_eval.db"
    try:
        tables = list_tables(db_path)
        print(f"Tables in {db_path}:")
        for table in tables:
            print(table[0])
    except Exception as e:
        print(f"Error: {e}")
