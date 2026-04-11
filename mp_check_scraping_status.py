import sqlite3
conn = sqlite3.connect('data/prospecting.db')

print("=== Jobs de scraping ===")
try:
    rows = conn.execute("SELECT * FROM scraping_jobs ORDER BY created_at DESC LIMIT 5").fetchall()
    for r in rows:
        print(f"  {dict(r)}")
except Exception as e:
    print(f"Error tabla scraping_jobs: {e}")

print("\n=== Config Apify ===")
try:
    rows2 = conn.execute("SELECT key, value FROM config WHERE key LIKE '%apify%' OR key LIKE '%scraping%'").fetchall()
    for r in rows2:
        print(f"  {r[0]}: {r[1][:50] if r[1] else 'None'}")
except Exception as e:
    print(f"Error: {e}")

conn.close()