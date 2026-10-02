import sqlite3

conn = sqlite3.connect('backend/retrieval/balbharati/data/chunks.db')
cur = conn.cursor()
cur.execute("SELECT DISTINCT chapter FROM chunks WHERE standard = 5 AND medium = 'Marathi' AND subject = 'Science'")
rows = cur.fetchall()
print("Standard 5 Marathi Science Chapters:", [r[0] for r in rows])

cur.execute("SELECT chapter, text FROM chunks WHERE standard = 5 AND subject = 'Science' LIMIT 3")
rows = cur.fetchall()
for r in rows:
    print("Chap:", r[0], "| Text:", r[1][:120])
conn.close()
