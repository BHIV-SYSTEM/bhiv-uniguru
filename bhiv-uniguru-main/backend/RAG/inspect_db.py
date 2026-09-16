import sqlite3
import json

conn = sqlite3.connect('chunks.db')
cursor = conn.cursor()

cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
schema = cursor.fetchall()
print("SCHEMA:")
for row in schema:
    print(row[0])

try:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for (t,) in tables:
        print(f"\nTABLE: {t}")
        cursor.execute(f"PRAGMA table_info({t})")
        columns = cursor.fetchall()
        for col in columns:
            print("  ", col)
        
        col_names = [col[1] for col in columns]
        
        if 'source' in col_names:
            cursor.execute(f"SELECT DISTINCT source FROM {t}")
            sources = cursor.fetchall()
            print("DISTINCT SOURCES:")
            for s in sources:
                print("  ", s[0])
        elif 'metadata' in col_names:
            print("Found metadata column, let's extract sources if possible:")
            cursor.execute(f"SELECT metadata FROM {t} LIMIT 10")
            rows = cursor.fetchall()
            for r in rows:
                if r[0]:
                    print("  ", r[0])
except Exception as e:
    print("Err", e)
