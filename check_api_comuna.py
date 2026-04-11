import urllib.request, json
try:
    r = urllib.request.urlopen('http://localhost:5000/api/dashboard/kpis')
    data = json.loads(r.read())
    print("top_comunas:", data.get('top_comunas', []))
    print("weekly_sends:", data.get('weekly_sends', []))
    print("by_status:", data.get('by_status', {}))
except Exception as e:
    print("Error:", e)