import requests, sqlite3, json

conn2 = sqlite3.connect('data/prospecting.db')
token = conn2.execute("SELECT value FROM config WHERE key='apify_token'").fetchone()[0]
conn2.close()

run_id = 'XjTeADKVKYBO45wiT'
resp = requests.get(
    f'https://api.apify.com/v2/actor-runs/{run_id}/dataset/items',
    headers={'Authorization': 'Bearer '+token},
    params={'format':'json','clean':True},
    timeout=30
)
data = resp.json()
print('Tipo de respuesta:', type(data))
print('Primeros 200 chars:', str(data)[:200])
