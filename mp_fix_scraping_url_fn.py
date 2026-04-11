with open('templates/dashboard_test11.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = """async function runScrapingUrl(){
  var maps_url = document.getElementById('scraUrl').value.trim();
  var rubro = document.getElementById('scraUrlRubro').value;
  if(!maps_url){ toast('Pega una URL de Google Maps primero','error'); return; }
  var btn = document.getElementById('scrapeBtnUrl');
  btn.disabled = true; btn.textContent = '⏳ Iniciando...';
  var r = await api('/api/scraping/run', {method:'POST', body:JSON.stringify({maps_url:maps_url, rubro:rubro, comuna:''})});
  if(r&&r.ok){
    toast('Scraping iniciado. Los leads apareceran en 2-4 minutos en Leads.', 'success');
    document.getElementById('scraUrl').value = '';
  } else {
    toast((r&&r.error)||'Error - verifica el token Apify','error');
  }
  btn.disabled = false; btn.textContent = '🔗 Scraping por URL';
}"""

new = """function runScrapingUrl(){
  var maps_url = document.getElementById('scraUrl').value.trim();
  var rubro = document.getElementById('scraUrlRubro').value;
  if(!maps_url){ toast('Pega una URL de Google Maps primero','error'); return; }
  var btn = document.getElementById('scrapeBtnUrl');
  btn.disabled = true; btn.textContent = '⏳ Iniciando...';
  api('/api/scraping/run', {method:'POST', body:JSON.stringify({maps_url:maps_url, rubro:rubro, comuna:''})}).then(function(r){
    if(r&&r.ok){
      toast('Scraping iniciado. Los leads apareceran en 2-4 minutos en Leads.', 'success');
      document.getElementById('scraUrl').value = '';
    } else {
      toast((r&&r.error)||'Error - verifica el token Apify','error');
    }
    btn.disabled = false; btn.textContent = '🔗 Scraping por URL';
  });
}"""

if old in content:
    content = content.replace(old, new)
    print("OK - sin async")
else:
    print("No encontrado")

print("async runScrapingUrl:", 'async function runScrapingUrl' in content)
print("checkWaStatus:", 'function checkWaStatus' in content)

with open('templates/dashboard_test11.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")