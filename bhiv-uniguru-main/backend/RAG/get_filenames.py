import sqlite3

conn = sqlite3.connect('chunks.db')
cursor = conn.cursor()

try:
    cursor.execute("SELECT DISTINCT file_name FROM chunks")
    sources = cursor.fetchall()
    print("DISTINCT file_names in chunks.db:")
    for s in sources:
        print("  -", s[0])
except Exception as e:
    print("Err", e)
