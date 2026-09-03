import sqlite3
conn = sqlite3.connect('greenfay.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  {t}: {cur.fetchone()[0]} rows")
    cur.execute(f"PRAGMA table_info({t})")
    cols = cur.fetchall()
    print(f"  Columns: {[c[1] for c in cols]}")
conn.close()

