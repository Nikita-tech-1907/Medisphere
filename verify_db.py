import os
import sqlite3

def verify():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(backend_dir, "medisphere.db")
    
    print(f"Database Path: {db_path}")
    print(f"File Exists: {os.path.exists(db_path)}")
    
    if not os.path.exists(db_path):
        print("Database file does not exist yet.")
        return False
        
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]
    print(f"\nTotal Tables Found ({len(tables)}):")
    for t in sorted(tables):
        cur.execute(f"SELECT count(*) FROM {t}")
        count = cur.fetchone()[0]
        print(f"  - {t:<26} : {count:>4} records")
        
    conn.close()
    return True

if __name__ == "__main__":
    verify()
