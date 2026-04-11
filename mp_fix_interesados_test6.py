"""
mp_fix_interesados_test6.py
Agrega al dashboard_test6:
1. Nav item Interesados
2. Pagina de interesados con formulario completo
3. Widget Tareas en sidebar
4. Campana de alertas en header
5. Auto-crear prospect cuando lead pasa a interesado
"""
with open('templates/dashboard_test6.html', 'r', encoding='utf-8') as f:
    content = f.read()

# ── 1. NAV ITEM ───────────────────────────────────────
if 'page-interesados' not in content:
    content = content.replace(
        'onclick="showPage(\'intel\',this,\'Inteligencia\')',
        'onclick="showPage(\'interesados\',this,\'Interesados\')" style="position:relative"><span class="nav-icon">⭐</span> Interesados<span id="badgeInteresados" style="position:absolute;top:6px;right:8px;background:var(--mp-warn);color:#fff;font-size:10px;font-weight:700;padding:1px 5px;border-radius:10px;display:none">0</span></div>\n  <div class="nav-item" onclick="showPage(\'intel\',this,\'Inteligencia\')'
    )
    print("1. Nav interesados OK")

# ── 2. CAMPANA ALERTAS EN HEADER ─────────────────────
old_header = '<div class="topbar">'
new_header = '''<div class="topbar">
  <div id="alertaCampana" onclick="showPage('interesados',document.querySelector('[onclick*=interesados]'),\'Interesados\')" style="display:none;position:fixed;top:12px;right:16px;z-index:9999;background:var(--mp-warn);color:#fff;padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,0.2)">
    🔔 <span id="alertaCount">0</span> tareas pendientes hoy
  </div>'''
content = content.replace(old_header, new_header)
print("2. Campana alertas OK:", 'alertaCampana' in content)

# ── 3. PAGINA INTERESADOS ────────────────────────────
pagina_interesados = '''
<!-- ─── INTERESADOS ─────────────────────────────── -->
<div class="page" id="page-interesados">
  <div class="page-header">
    <div>
      <div class="page-title">Prospectos Interesados</div>
      <div class="page-sub">Seguimiento detallado de leads en estado interesado</div>
    </div>
    <div style="display:flex;gap:8px">
      <button class="btn btn-ghost" onclick="showModalNuevoProspecto()">+ Agregar Manual</button>
      <button class="btn btn-primary" onclick="loadInteresados()">↻ Actualizar</button>
    </div>
  </div>

  <!-- KPIs -->
  <div class="kpi-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:16px">
    <div class="kpi" style="--kpi-color:var(--mp-warn)"><div class="kpi-label">Interesados</div><div class="kpi-val" id="int-total">0</div></div>
    <div class="kpi" style="--kpi-color:var(--mp-purple)"><div class="kpi-label">Tareas hoy</div><div class="kpi-val" id="int-hoy">0</div></div>
    <div class="kpi" style="--kpi-color:var(--mp-red)"><div class="kpi-label">Atrasadas</div><div class="kpi-val" id="int-atrasadas">0</div></div>
    <div class="kpi" style="--kpi-color:var(--mp-green)"><div class="kpi-label">Completadas</div><div class="kpi-val" id="int-completadas">0</div></div>
  </div>

  <div class="grid-2" style="margin-bottom:0">
    <!-- Lista prospectos -->
    <div class="card" style="max-height:600px;overflow-y:auto">
      <div class="card-title">Prospectos activos</div>
      <div id="prospectosList"></div>
    </div>

    <!-- Calendario semanal -->
    <div class="card">
      <div class="card-title">
        <span class="card-icon">📅</span>Agenda semanal
        <div style="float:right;display:flex;gap:6px">
          <button class="btn btn-ghost btn-sm" onclick="cambiarSemana(-1)">←</button>
          <span id="semanaLabel" style="font-size:12px;color:var(--mp-text-2);padding:2px 8px"></span>
          <button class="btn btn-ghost btn-sm" onclick="cambiarSemana(1)">→</button>
        </div>
      </div>
      <div id="calendarioSemana" style="display:flex;flex-direction:column;gap:4px;max-height:500px;overflow-y:auto"></div>
    </div>
  </div>
</div>

<!-- Modal Prospecto -->
<div class="modal-overlay" id="modalProspecto">
  <div class="modal" style="max-width:540px">
    <div class="modal-title" id="modalProspectoTitle">Prospecto Interesado</div>
    <input type="hidden" id="prospectoId">
    <input type="hidden" id="prospectoLeadId">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div class="form-row">
        <label class="form-lbl">Nombre contacto</label>
        <input class="form-input" id="pNombre" placeholder="Nombre del contacto">
      </div>
      <div class="form-row">
        <label class="form-lbl">Telefono</label>
        <input class="form-input" id="pTelefono" placeholder="+56912345678">
      </div>
      <div class="form-row">
        <label class="form-lbl">Negocio</label>
        <input class="form-input" id="pNegocio" placeholder="Nombre del negocio">
      </div>
      <div class="form-row">
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
      </div>
      <div class="form-row">
        <label class="form-lbl">Competencia actual</label>
        <select class="form-input" id="pCompetencia">
          <option value="">Sin competencia</option>
          <option value="Tbk">Tbk</option>
          <option value="Sumup">Sumup</option>
          <option value="Getnet">Getnet</option>
          <option value="BCI">BCI</option>
          <option value="Banco Chile">Banco Chile</option>
          <option value="Compra Aqui">Compra Aqui</option>
          <option value="TUU">TUU</option>
          <option value="Otra">Otra</option>
        </select>
      </div>
      <div class="form-row">
        <label class="form-lbl">Procedencia</label>
        <select class="form-input" id="pProcedencia">
          <option value="Online">Online</option>
          <option value="Terreno">Terreno</option>
        </select>
      </div>
    </div>
    <div class="form-row" style="margin-top:4px">
      <label class="form-lbl">Notas</label>
      <textarea class="form-input" id="pNotas" rows="2" placeholder="Observaciones del prospecto..."></textarea>
    </div>
    <!-- Enviar mensaje -->
    <div style="border-top:1px solid var(--mp-border);margin-top:12px;padding-top:12px">
      <div style="font-size:12px;font-weight:600;color:var(--mp-text-2);margin-bottom:8px">Enviar mensaje WhatsApp</div>
      <div style="display:flex;gap:8px;margin-bottom:8px">
        <select class="form-input" id="pMsgTipo" onchange="onMsgTipoChange()" style="flex:1">
          <option value="">Selecciona mensaje...</option>
          <option value="info">Mas informacion</option>
          <option value="seguimiento">Seguimiento</option>
          <option value="custom">Personalizado</option>
        </select>
        <button class="btn btn-green btn-sm" onclick="enviarMsgProspecto()" style="white-space:nowrap">💬 Enviar</button>
      </div>
      <textarea class="form-input" id="pMsgTexto" rows="3" placeholder="Selecciona un mensaje predefinido o escribe uno..."></textarea>
    </div>
    <!-- Agendar tarea -->
    <div style="border-top:1px solid var(--mp-border);margin-top:12px;padding-top:12px">
      <div style="font-size:12px;font-weight:600;color:var(--mp-text-2);margin-bottom:8px">Agendar tarea</div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
        <select class="form-input" id="taskTipo">
          <option value="llamada">📞 Llamada</option>
          <option value="reunion">🤝 Reunion</option>
          <option value="seguimiento">💬 Seguimiento</option>
          <option value="visita">🏪 Visita terreno</option>
        </select>
        <input type="date" class="form-input" id="taskFecha">
        <input type="time" class="form-input" id="taskHora" value="10:00">
      </div>
      <input class="form-input" id="taskDesc" placeholder="Descripcion de la tarea (opcional)" style="margin-top:8px">
      <button class="btn btn-primary" onclick="agendarTarea()" style="margin-top:8px;width:100%">+ Agendar tarea</button>
    </div>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal('modalProspecto')">Cerrar</button>
      <button class="btn btn-primary" onclick="guardarProspecto()">Guardar</button>
    </div>
  </div>
</div>

<!-- Modal Reagendar -->
<div class="modal-overlay" id="modalReagendar">
  <div class="modal" style="max-width:380px">
    <div class="modal-title">Reagendar tarea</div>
    <input type="hidden" id="reagendarTaskId">
    <div class="form-row">
      <label class="form-lbl">Nueva fecha</label>
      <input type="date" class="form-input" id="reagendarFecha">
    </div>
    <div class="form-row">
      <label class="form-lbl">Nueva hora</label>
      <input type="time" class="form-input" id="reagendarHora" value="10:00">
    </div>
    <div class="form-row">
      <label class="form-lbl">Nota</label>
      <input class="form-input" id="reagendarNota" placeholder="Motivo del reagendamiento">
    </div>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal('modalReagendar')">Cancelar</button>
      <button class="btn btn-primary" onclick="confirmarReagendar()">Reagendar</button>
    </div>
  </div>
</div>

'''

content = content.replace('<!-- ─── LEADS', pagina_interesados + '<!-- ─── LEADS')
print("3. Pagina interesados OK:", 'page-interesados' in content)

# ── 4. WIDGET TAREAS EN SIDEBAR ───────────────────────
old_proximo = '<div class="sidebar-card" id="nextSendCard">'
new_widget = '''<div class="sidebar-card" id="tareasCard" style="border-left:3px solid var(--mp-warn)">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <div class="sidebar-lbl">Tareas de Prospectos</div>
    <span id="tareasBadge" style="background:var(--mp-warn);color:#fff;font-size:10px;font-weight:700;padding:1px 7px;border-radius:10px">0</span>
  </div>
  <div id="tareasWidget" style="display:flex;flex-direction:column;gap:6px;max-height:200px;overflow-y:auto">
    <div style="font-size:11px;color:var(--mp-text-3);text-align:center;padding:8px">Sin tareas pendientes</div>
  </div>
  <button class="btn btn-ghost" onclick="showPage('interesados',document.querySelector('[onclick*=interesados]'),\'Interesados\')" style="width:100%;margin-top:8px;font-size:11px">Ver todas las tareas →</button>
</div>

<div class="sidebar-card" id="nextSendCard">'''

content = content.replace(old_proximo, new_widget)
print("4. Widget tareas sidebar OK:", 'tareasWidget' in content)

# ── 5. LOADER EN showPage ────────────────────────────
if 'interesados: loadInteresados' not in content:
    content = content.replace(
        'intel: loadIntel,',
        'intel: loadIntel,\n    interesados: loadInteresados,'
    )
    print("5. Loader interesados OK")

with open('templates/dashboard_test6.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO HTML")
