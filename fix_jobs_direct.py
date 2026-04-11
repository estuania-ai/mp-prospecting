with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Encontrar el bloque completo del schedulerJobs
start = content.find("schedulerJobs').innerHTML")
# Buscar el cierre del bloque
end = content.find("|| '<div style=\"color:var(--mp-text-3);font-size:13px\">Sin jobs activos</div>';", start)
end = end + len("|| '<div style=\"color:var(--mp-text-3);font-size:13px\">Sin jobs activos</div>';")

print("Bloque encontrado:", start, "->", end)
print("Texto:", content[start:start+100])

new_block = """schedulerJobs').innerHTML = (function(){
      var jobNames = {
        'batch_0930':'Prospeccion 09:30 AM',
        'batch_1500':'Prospeccion 15:00 PM',
        'batch_1730':'Prospeccion 17:30 PM',
        'fidelizacion_weekly':'Fidelizacion Sellers',
        'prospecting_daily':'Prospeccion L-V'
      };
      var msgs = {'batch_0930':'15 mensajes','batch_1500':'10 mensajes','batch_1730':'15 mensajes'};
      var jobs = (waStatus.jobs||[]).sort(function(a,b){return new Date(a.next_run)-new Date(b.next_run);});
      return jobs.slice(0,6).map(function(j){
        var titulo = jobNames[j.id] || j.id;
        var nextDate = j.next_run ? new Date(j.next_run) : null;
        var nextStr = nextDate ? nextDate.toLocaleDateString('es-CL',{weekday:'long',day:'numeric',month:'short'}) + ' ' + nextDate.toLocaleTimeString('es-CL',{hour:'2-digit',minute:'2-digit'}) : 'Sin programar';
        var isFidel = j.id === 'fidelizacion_weekly';
        var msgsStr = msgs[j.id] ? ' - ' + msgs[j.id] : '';
        var subtitulo = isFidel ? nextStr + ' - Etapas dias 7, 14, 15, 30, 35' : nextStr + msgsStr + ' - leads no enviados';
        var ico = isFidel ? '💌' : '📤';
        var badge = isFidel ? 'badge-reunion' : 'badge-interesado';
        var tipo = isFidel ? 'Fidelizacion' : 'Prospeccion';
        return '<div class="log-item" style="margin-bottom:8px"><div class="log-ico">' + ico + '</div><div class="log-info"><div class="log-title">' + titulo + '</div><div class="log-meta">' + subtitulo + '</div></div><span class="badge ' + badge + '">' + tipo + '</span></div>';
      }).join('') || '<div style="color:var(--mp-text-3);font-size:13px">Sin jobs activos</div>';
    })();"""

content = content[:start] + new_block + content[end:]

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK - scheduler reemplazado")