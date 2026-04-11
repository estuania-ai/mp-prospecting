import requests, sqlite3, re, sys
sys.path.insert(0,'.')
from database import get_db

def validate(phone):
    if not phone: return None
    digits = re.sub(r'\D','',str(phone))
    if re.match(r'^569\d{8}$',digits): return digits
    if re.match(r'^9\d{8}$',digits): return '56'+digits
    return None

conn2 = sqlite3.connect('data/prospecting.db')
token = conn2.execute("SELECT value FROM config WHERE key='apify_token'").fetchone()[0]
conn2.close()

run_id = 'XjTeADKVKYBO45wiT'
resp = requests.get(
    f'https://api.apify.com/v2/actor-runs/{run_id}/dataset/items',
    headers={'Authorization': 'Bearer '+token},
    params={'format':'json','clean':'true'},
    timeout=30
)
items = resp.json()
print('Items:', len(items))
if isinstance(items, list) and len(items) > 0:
    print('Primer item keys:', list(items[0].keys())[:8])
    print('Phone del primero:', items[0].get('phone',''))

inserted = skipped = 0
conn = get_db()
for item in items:
    if not isinstance(item, dict): continue
    phone = validate(item.get('phone','') or item.get('phoneNumber','') or '')
    if not phone:
        skipped += 1
        continue
    name = (item.get('title') or item.get('name','')).strip()
    if not name:
        skipped += 1
        continue
    before = conn.total_changes
    conn.execute('INSERT OR IGNORE INTO leads (name,phone,address,comuna,rubro,source) VALUES (?,?,?,?,?,?)',
        (name, phone, item.get('address',''), 'Puente Alto', 'pizzeria', 'apify_gmaps'))
    if conn.total_changes > before: inserted += 1
    else: skipped += 1

conn.commit()
conn.close()
print('Insertados:', inserted)
print('Descartados (fijos/duplicados):', skipped)
