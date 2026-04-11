with open('templates/dashboard_test7.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Reemplazar campos readonly por editables
old_rubro = '''      <div class="form-row">
        <label class="form-lbl">Rubro</label>
        <input class="form-input" id="pRubro" readonly style="background:#f8f9fa">
      </div>
      <div class="form-row">
        <label class="form-lbl">Categoria</label>
        <input class="form-input" id="pCategoria" readonly style="background:#f8f9fa">
      </div>
      <div class="form-row">
        <label class="form-lbl">Comuna</label>
        <input class="form-input" id="pComuna" readonly style="background:#f8f9fa">
      </div>'''

new_rubro = '''      <div class="form-row">
        <label class="form-lbl">Rubro</label>
        <select class="form-input" id="pRubro" onchange="onRubroChange(this.value)">
          <option value="">Selecciona rubro...</option>
          <option value="almacen">Almacen</option>
          <option value="bazar">Bazar</option>
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
          <option value="otro">Otro</option>
        </select>
      </div>
      <div class="form-row">
        <label class="form-lbl">Categoria</label>
        <input class="form-input" id="pCategoria" placeholder="Se completa automaticamente">
      </div>
      <div class="form-row">
        <label class="form-lbl">Comuna</label>
        <input class="form-input" id="pComuna" placeholder="Ej: Puente Alto">
      </div>'''

if old_rubro in content:
    content = content.replace(old_rubro, new_rubro)
    print("Campos formulario OK")
else:
    print("No encontrado - buscando alternativa...")
    idx = content.find('id="pRubro"')
    print("pRubro pos:", idx)
    print("Contexto:", repr(content[idx-50:idx+150]))

# 2. Agregar funcion onRubroChange
js_fn = """
function onRubroChange(rubro){
  var mapa = {
    'almacen':'Comercio de Barrio Diario',
    'bazar':'Retail Especializado y Hogar',
    'botilleria':'Comercio de Alta Demanda Fin de Semana',
    'cafeteria':'Gastronomia y Comida Rapida',
    'carniceria':'Comercio de Alta Demanda Fin de Semana',
    'clinica_dental':'Servicios de Alto Ticket',
    'emporio':'Comercio de Barrio Diario',
    'farmacia':'Salud y Farmacia',
    'ferreteria':'Retail Especializado y Hogar',
    'fruteria':'Comercio de Barrio Diario',
    'fuente_de_soda':'Gastronomia y Comida Rapida',
    'gimnasio':'Membresias y Entrenamientos',
    'lavanderia':'Servicios Personales Diario',
    'libreria':'Retail Especializado y Hogar',
    'minimarket':'Comercio de Barrio Diario',
    'muebleria':'Retail Especializado y Hogar',
    'panaderia':'Comercio de Barrio Diario',
    'peluqueria':'Servicios Personales Diario',
    'pizzeria':'Gastronomia y Comida Rapida',
    'sandwicheria':'Gastronomia y Comida Rapida',
    'spa':'Servicios de Alto Ticket',
    'sushi':'Gastronomia y Comida Rapida',
    'taller':'Servicios de Alto Ticket',
    'verduleria':'Comercio de Barrio Diario',
    'veterinaria':'Servicios de Alto Ticket'
  };
  var catInput = document.getElementById('pCategoria');
  if(rubro === 'otro'){
    catInput.value = '';
    catInput.removeAttribute('readonly');
    catInput.placeholder = 'Ingresa la categoria...';
    catInput.style.background = '';
  } else if(mapa[rubro]){
    catInput.value = mapa[rubro];
    catInput.setAttribute('readonly', true);
    catInput.style.background = '#f8f9fa';
  } else {
    catInput.value = '';
    catInput.removeAttribute('readonly');
    catInput.placeholder = 'Se completa automaticamente';
  }
}

"""

if 'function onRubroChange' not in content:
    content = content.replace('setInterval(checkWaStatus, 30000);', js_fn + 'setInterval(checkWaStatus, 30000);')
    print("JS onRubroChange OK")
else:
    print("JS ya existe")

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test7.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")
