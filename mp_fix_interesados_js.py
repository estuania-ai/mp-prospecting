"""
mp_fix_interesados_js.py
Agrega el JS completo para la pestaña Interesados
"""
with open('templates/dashboard_test6.html', 'r', encoding='utf-8') as f:
    content = f.read()

MSG_INFO = "Hola! Claro que si, muchas gracias por el interes. Para resumirte lo mas importante de la imagen: Es que tienes beneficios para cualquier necesidad de tu negocio, ya sea liquidez, creditos, Cuotas sin interes, Boletas, etc lo que necesites segun tu negocio. Dime, Que necesitas hoy en dia?, te tinca si te pego una llamadita corta de 5 minutos, tu me dices cuando o bien agendamos un dia en la semana para vernos, lo que sea mas comodo para ti, revisamos de forma super transparente si realmente te conviene el cambio. La idea es asesorarte. Me avisas que tengas un gran dia."

MSG_SEG = "Hola, como estas? Te escribo cortito porque de la ultima vez que conversamos no tuve respuesta y queria saber si te quedo alguna duda. Te parece si agendamos una llamada rapida o paso a visitarte al local para revisarlo sin compromiso? Quedo super atento a lo que te acomode!"

js_interesados = f'''
// ─── INTERESADOS ─────────────────────────────────────
var prospectoActual = null;
var semanaOffset = 0;

const MSG_INFO_PRESET = "{MSG_INFO}";
const MSG_SEG_PRESET = "{MSG_SEG}";

async function loadInteresados(){{
  const [prospects, tasks] = await Promise.all([
    api('/api/prospects/'),
    api('/api/prospects/tasks/today')
  ]);
  if(!prospects) return;

  // KPIs
  document.getElementById('int-total').textContent = prospects.length;
  var hoy = (tasks||[]).filter(t=>!t.completada).length;
  var atrasadas = (tasks||[]).filter(t=>t.completada==0 && t.fecha < new Date().toISOString().slice(0,10)).length;
  document.getElementById('int-hoy').textContent = hoy;
  document.getElementById('int-atrasadas').textContent = atrasadas;

  // Badge campana
  if(hoy > 0){{
    document.getElementById('alertaCampana').style.display='block';
    document.getElementById('alertaCount').textContent = hoy;
    document.getElementById('tareasBadge').textContent = hoy;
  }} else {{
    document.getElementById('alertaCampana').style.display='none';
    document.getElementById('tareasBadge').textContent = '0';
  }}

  // Render prospectos
  if(!prospects.length){{
    document.getElementById('prospectosList').innerHTML = '<div style="text-align:center;padding:24px;color:var(--mp-text-3)">Sin prospectos interesados aun</div>';
  }} else {{
    document.getElementById('prospectosList').innerHTML = prospects.map(function(p){{
      var pendientes = p.tareas_pendientes || 0;
      return '<div class="log-item" style="cursor:pointer;border-left:3px solid '+(pendientes>0?'var(--mp-warn)':'var(--mp-border)')+';margin-bottom:6px" onclick="abrirProspecto('+p.id+')">' +
        '<div class="log-ico">⭐</div>' +
        '<div class="log-info">' +
        '<div class="log-title">'+p.negocio+'</div>' +
        '<div class="log-meta">'+p.name+' · '+p.rubro+(p.competencia?' · '+p.competencia:'')+'</div>' +
        '</div>' +
        (pendientes>0?'<span style="background:var(--mp-warn);color:#fff;font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px">'+pendientes+' tareas</span>':'') +
        '</div>';
    }}).join('');
  }}

  // Widget sidebar tareas
  renderTareasWidget(tasks||[]);

  // Calendario
  renderCalendario();
}}

function renderTareasWidget(tasks){{
  var pendientes = tasks.filter(function(t){{return !t.completada;}});
  if(!pendientes.length){{
    document.getElementById('tareasWidget').innerHTML = '<div style="font-size:11px;color:var(--mp-text-3);text-align:center;padding:8px">Sin tareas pendientes hoy</div>';
    return;
  }}
  document.getElementById('tareasWidget').innerHTML = pendientes.slice(0,5).map(function(t){{
    var icoTipo = {{llamada:'📞',reunion:'🤝',seguimiento:'💬',visita:'🏪'}}[t.tipo] || '📋';
    var atrasada = t.fecha < new Date().toISOString().slice(0,10);
    return '<div style="background:'+(atrasada?'#fff5f5':'#f8f9fa')+';border-radius:8px;padding:8px 10px;font-size:11px">' +
      '<div style="display:flex;justify-content:space-between;align-items:center">' +
      '<span style="font-weight:600;color:'+(atrasada?'var(--mp-red)':'var(--mp-text-1)')+'">'+icoTipo+' '+t.negocio+'</span>' +
      '<div style="display:flex;gap:4px">' +
      '<button onclick="event.stopPropagation();completarTareaWidget('+t.id+')" style="background:var(--mp-green);color:#fff;border:none;border-radius:6px;padding:2px 6px;cursor:pointer;font-size:10px">✓</button>' +
      '<button onclick="event.stopPropagation();abrirReagendar('+t.id+')" style="background:var(--mp-blue-lt);color:var(--mp-blue);border:none;border-radius:6px;padding:2px 6px;cursor:pointer;font-size:10px">↻</button>' +
      '<a href="https://wa.me/'+t.phone+'?text=Hola+'+encodeURIComponent(t.name)+'!" target="_blank" style="background:#25D366;color:#fff;border:none;border-radius:6px;padding:2px 6px;cursor:pointer;font-size:10px;text-decoration:none">💬</a>' +
      '</div></div>' +
      '<div style="color:var(--mp-text-3);margin-top:2px">'+t.tipo+' · '+(t.hora||'')+' · '+(t.fecha||'')+'</div>' +
      '</div>';
  }}).join('');
}}

async function abrirProspecto(pid){{
  var p = await api('/api/prospects/'+pid+'/tasks');
  var prospects = await api('/api/prospects/');
  var prospect = (prospects||[]).find(function(x){{return x.id==pid;}});
  if(!prospect) return;
  prospectoActual = prospect;
  document.getElementById('prospectoId').value = prospect.id;
  document.getElementById('prospectoLeadId').value = prospect.lead_id||'';
  document.getElementById('pNombre').value = prospect.name||'';
  document.getElementById('pTelefono').value = prospect.phone||'';
  document.getElementById('pNegocio').value = prospect.negocio||'';
  document.getElementById('pRubro').value = prospect.rubro||'';
  document.getElementById('pCategoria').value = prospect.categoria||'';
  document.getElementById('pComuna').value = prospect.comuna||'';
  document.getElementById('pCompetencia').value = prospect.competencia||'';
  document.getElementById('pProcedencia').value = prospect.procedencia||'Online';
  document.getElementById('pNotas').value = prospect.notas||'';
  document.getElementById('pMsgTipo').value = '';
  document.getElementById('pMsgTexto').value = '';
  document.getElementById('modalProspectoTitle').textContent = prospect.negocio || 'Prospecto';
  document.getElementById('modalProspecto').classList.add('open');
}}

function showModalNuevoProspecto(){{
  prospectoActual = null;
  document.getElementById('prospectoId').value = '';
  document.getElementById('prospectoLeadId').value = '';
  document.getElementById('pNombre').value = '';
  document.getElementById('pTelefono').value = '';
  document.getElementById('pNegocio').value = '';
  document.getElementById('pRubro').value = '';
  document.getElementById('pCategoria').value = '';
  document.getElementById('pComuna').value = '';
  document.getElementById('pCompetencia').value = '';
  document.getElementById('pProcedencia').value = 'Terreno';
  document.getElementById('pNotas').value = '';
  document.getElementById('pMsgTipo').value = '';
  document.getElementById('pMsgTexto').value = '';
  document.getElementById('modalProspectoTitle').textContent = 'Nuevo Prospecto';
  document.getElementById('modalProspecto').classList.add('open');
}}

function onMsgTipoChange(){{
  var tipo = document.getElementById('pMsgTipo').value;
  if(tipo==='info') document.getElementById('pMsgTexto').value = MSG_INFO_PRESET;
  else if(tipo==='seguimiento') document.getElementById('pMsgTexto').value = MSG_SEG_PRESET;
  else if(tipo==='custom') document.getElementById('pMsgTexto').value = '';
}}

async function enviarMsgProspecto(){{
  var pid = document.getElementById('prospectoId').value;
  var msg = document.getElementById('pMsgTexto').value.trim();
  if(!msg){{ toast('Escribe o selecciona un mensaje','error'); return; }}
  if(!pid){{ toast('Guarda el prospecto primero','error'); return; }}
  var r = await api('/api/prospects/'+pid+'/send', {{method:'POST',body:JSON.stringify({{message:msg}})}});
  if(r&&r.ok) toast('Mensaje enviado','success');
  else toast('Error enviando mensaje','error');
}}

async function guardarProspecto(){{
  var pid = document.getElementById('prospectoId').value;
  var data = {{
    name: document.getElementById('pNombre').value,
    phone: document.getElementById('pTelefono').value,
    negocio: document.getElementById('pNegocio').value,
    rubro: document.getElementById('pRubro').value,
    categoria: document.getElementById('pCategoria').value,
    comuna: document.getElementById('pComuna').value,
    competencia: document.getElementById('pCompetencia').value,
    procedencia: document.getElementById('pProcedencia').value,
    notas: document.getElementById('pNotas').value,
    lead_id: document.getElementById('prospectoLeadId').value||null
  }};
  var r;
  if(pid) r = await api('/api/prospects/'+pid, {{method:'PUT',body:JSON.stringify(data)}});
  else r = await api('/api/prospects/', {{method:'POST',body:JSON.stringify(data)}});
  if(r&&r.ok){{
    toast('Prospecto guardado','success');
    loadInteresados();
  }} else toast('Error guardando','error');
}}

async function agendarTarea(){{
  var pid = document.getElementById('prospectoId').value;
  var fecha = document.getElementById('taskFecha').value;
  if(!pid){{ toast('Guarda el prospecto primero','error'); return; }}
  if(!fecha){{ toast('Selecciona una fecha','error'); return; }}
  var r = await api('/api/prospects/'+pid+'/tasks', {{
    method:'POST',
    body:JSON.stringify({{
      tipo: document.getElementById('taskTipo').value,
      descripcion: document.getElementById('taskDesc').value,
      fecha: fecha,
      hora: document.getElementById('taskHora').value
    }})
  }});
  if(r&&r.ok){{
    toast('Tarea agendada','success');
    document.getElementById('taskDesc').value = '';
    loadInteresados();
  }} else toast('Error agendando','error');
}}

async function completarTareaWidget(tid){{
  await api('/api/prospects/tasks/'+tid+'/complete', {{method:'PUT'}});
  toast('Tarea completada','success');
  loadInteresados();
}}

function abrirReagendar(tid){{
  document.getElementById('reagendarTaskId').value = tid;
  document.getElementById('reagendarFecha').value = '';
  document.getElementById('reagendarHora').value = '10:00';
  document.getElementById('reagendarNota').value = '';
  document.getElementById('modalReagendar').classList.add('open');
}}

async function confirmarReagendar(){{
  var tid = document.getElementById('reagendarTaskId').value;
  var fecha = document.getElementById('reagendarFecha').value;
  if(!fecha){{ toast('Selecciona una fecha','error'); return; }}
  var r = await api('/api/prospects/tasks/'+tid+'/reagendar', {{
    method:'PUT',
    body:JSON.stringify({{
      fecha: fecha,
      hora: document.getElementById('reagendarHora').value,
      nota: document.getElementById('reagendarNota').value
    }})
  }});
  if(r&&r.ok){{
    toast('Tarea reagendada','success');
    closeModal('modalReagendar');
    loadInteresados();
  }} else toast('Error','error');
}}

async function renderCalendario(){{
  var today = new Date();
  today.setDate(today.getDate() + semanaOffset*7);
  var lunes = new Date(today);
  var dia = today.getDay();
  var diff = dia===0 ? -6 : 1-dia;
  lunes.setDate(today.getDate() + diff);

  var dias = [];
  for(var i=0;i<7;i++){{
    var d = new Date(lunes);
    d.setDate(lunes.getDate()+i);
    dias.push(d);
  }}

  var desde = dias[0].toISOString().slice(0,10);
  var hasta = dias[6].toISOString().slice(0,10);
  document.getElementById('semanaLabel').textContent = desde + ' al ' + hasta;

  var tasks = await api('/api/prospects/tasks/calendar');
  var tasksPorDia = {{}};
  (tasks||[]).forEach(function(t){{
    var d = (t.fecha||'').slice(0,10);
    if(!tasksPorDia[d]) tasksPorDia[d] = [];
    tasksPorDia[d].push(t);
  }});

  var nombres = ['Lun','Mar','Mie','Jue','Vie','Sab','Dom'];
  var todayStr = new Date().toISOString().slice(0,10);
  document.getElementById('calendarioSemana').innerHTML = dias.map(function(d,i){{
    var dStr = d.toISOString().slice(0,10);
    var tareas = tasksPorDia[dStr] || [];
    var esHoy = dStr === todayStr;
    return '<div style="border-radius:8px;border:1px solid '+(esHoy?'var(--mp-blue)':'var(--mp-border)')+';padding:8px;background:'+(esHoy?'var(--mp-blue-lt)':'#fff')+'">' +
      '<div style="font-size:11px;font-weight:700;color:'+(esHoy?'var(--mp-blue)':'var(--mp-text-2)')+';margin-bottom:4px">'+nombres[i]+' '+d.getDate()+(tareas.length?' · <span style=\\'color:var(--mp-warn)\\'>'+tareas.length+' tareas</span>':'')+'</div>' +
      (tareas.length ? tareas.map(function(t){{
        var icoTipo = {{llamada:'📞',reunion:'🤝',seguimiento:'💬',visita:'🏪'}}[t.tipo]||'📋';
        return '<div style="font-size:11px;padding:3px 6px;border-radius:6px;background:'+(t.completada?'#d4edda':'#fff3cd')+';margin-bottom:2px;display:flex;justify-content:space-between">' +
          '<span>'+icoTipo+' '+t.negocio+(t.hora?' '+t.hora:'')+'</span>' +
          (!t.completada?'<button onclick="completarTareaWidget('+t.id+')" style="background:var(--mp-green);color:#fff;border:none;border-radius:4px;padding:0 4px;cursor:pointer;font-size:9px">✓</button>':'<span style=\\'color:var(--mp-green)\\'>✓</span>') +
          '</div>';
      }}).join('') : '<div style="font-size:10px;color:var(--mp-text-3)">Sin tareas</div>') +
      '</div>';
  }}).join('');
}}

function cambiarSemana(dir){{
  semanaOffset += dir;
  renderCalendario();
}}

// Auto-crear prospect cuando lead pasa a interesado
var _origSubmitStatus = typeof submitStatus !== 'undefined' ? submitStatus : null;
async function submitStatus(){{
  var status = document.getElementById('newStatus').value;
  var id = document.getElementById('statusLeadId').value;
  if(status === 'interesado' && id){{
    setTimeout(async function(){{
      var leads = allLeads || [];
      var lead = leads.find(function(l){{return l.id==id;}});
      if(lead){{
        await api('/api/prospects/',{{
          method:'POST',
          body:JSON.stringify({{
            lead_id:lead.id, name:lead.name, phone:lead.phone,
            negocio:lead.name, rubro:lead.rubro, categoria:lead.categoria,
            comuna:lead.comuna||lead.commune||'', procedencia:'Online'
          }})
        }});
        var badge = document.getElementById('badgeInteresados');
        if(badge) badge.style.display='inline';
      }}
    }}, 1000);
  }}
  if(_origSubmitStatus) return _origSubmitStatus.apply(this, arguments);
  var notes = document.getElementById('statusNotes').value;
  var optout_motivo = '';
  var camposOpt = document.getElementById('camposOptout');
  if(camposOpt && camposOpt.style.display!=='none'){{
    optout_motivo = document.getElementById('optoutMotivo').value;
    if(!optout_motivo){{document.getElementById('optoutMotivo').style.border='2px solid red';toast('Selecciona un motivo','error');return;}}
  }}
  var r = await api('/api/leads/'+id+'/status',{{method:'PUT',body:JSON.stringify({{status:status,notes:notes,optout_motivo:optout_motivo}})}});
  if(r&&r.ok){{toast('Estado actualizado','success');closeModal('modalStatus');loadLeads();}}
  else toast('Error','error');
}}

'''

# Agregar JS antes del setInterval
content = content.replace(
    'setInterval(checkWaStatus, 30000);',
    js_interesados + 'setInterval(checkWaStatus, 30000);'
)
print("JS interesados OK:", 'loadInteresados' in content)

# Setear fecha de hoy por defecto en taskFecha cuando se abra
# Ya está en el HTML con id="taskFecha"

with open('templates/dashboard_test6.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO JS")
