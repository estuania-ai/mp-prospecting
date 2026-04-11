with open('templates/dashboard_test11.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    <div style="margin-top:10px;font-size:12px;color:var(--mp-text-3)">
      ℹ️ El scraping corre en segundo plano. Los leads quedan disponibles automáticamente.
    </div>
  </div>'''

new = '''    <div style="margin-top:10px;font-size:12px;color:var(--mp-text-3)">
      ℹ️ El scraping corre en segundo plano. Los leads quedan disponibles automáticamente.
    </div>
  </div>

  <div class="card" style="margin-bottom:20px">
    <div class="card-title"><span class="card-icon">🔗</span>Scraping por link de Google Maps</div>
    <div style="font-size:12px;color:var(--mp-text-3);margin-bottom:12px">
      Pega el link de busqueda de Google Maps directamente para extraer negocios
    </div>
    <div style="display:grid;grid-template-columns:1fr auto;gap:12px;align-items:end">
      <div>
        <label class="form-lbl">Link de Google Maps</label>
        <input class="form-input" id="scraUrl" placeholder="https://www.google.com/maps/search/pizzerias+puente+alto...">
      </div>
      <button class="btn btn-primary" onclick="runScrapingUrl()" id="scrapeBtnUrl">
        🔗 Scraping por URL
      </button>
    </div>
    <div style="margin-top:8px">
      <label class="form-lbl">Rubro asignar <span style="color:var(--mp-text-3)">(opcional - para el mensaje)</span></label>
      <select class="form-input" id="scraUrlRubro" style="max-width:300px">
        <option value="">Selecciona rubro...</option>
        <option value="almacen">Almacen</option>
        <option value="bazar">Jugueteria / Regalos</option>
        <option value="botilleria">Botilleria</option>
        <option value="cafeteria">Cafeteria</option>
        <option value="carniceria">Carniceria</option>
        <option value="clinica_dental">Clinica Dental</option>
        <option value="emporio">Emporio</option>
        <option value="farmacia">Farmacia</option>
        <option value="ferreteria">Ferreteria</option>
        <option value="fruteria">Fruteria</option>
        <option value="fuente_de_soda">Fuente de Soda</option>
        <option value="gimnasio">Gimnasio</option>
        <option value="lavanderia">Lavanderia</option>
        <option value="libreria">Libreria</option>
        <option value="minimarket">Minimarket</option>
        <option value="muebleria">Muebleria</option>
        <option value="panaderia">Panaderia</option>
        <option value="peluqueria">Peluqueria</option>
        <option value="pizzeria">Pizzeria</option>
        <option value="sandwicheria">Sandwicheria</option>
        <option value="spa">Spa</option>
        <option value="sushi">Sushi</option>
        <option value="taller">Taller</option>
        <option value="verduleria">Verduleria</option>
        <option value="veterinaria">Veterinaria</option>
      </select>
    </div>
    <div style="margin-top:8px;font-size:12px;color:var(--mp-text-3)">
      💡 Busca en Google Maps, copia el link de la barra del navegador y pegalo aqui
    </div>
  </div>'''

if old in content:
    content = content.replace(old, new)
    print("Card scraping URL OK")
else:
    print("No encontrado")

# Verificar que runScrapingUrl existe en JS
print("runScrapingUrl JS:", 'function runScrapingUrl' in content)
print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test11.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")