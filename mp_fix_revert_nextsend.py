with open('templates/dashboard_test6.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar y reemplazar la funcion async por version simple
idx = content.find('async function updateNextSendTime()')
if idx == -1:
    idx = content.find('function updateNextSendTime()')
end = content.find('\n}', idx) + 2
print("Funcion actual:")
print(content[idx:idx+100])

new_fn = """function updateNextSendTime(){
  var now = new Date();
  var day = now.getDay();
  var h = now.getHours(), mi = now.getMinutes();
  var isWeekday = day >= 1 && day <= 5;
  var horarios = [{h:9,m:30,label:'09:30'},{h:15,m:0,label:'15:00'},{h:17,m:30,label:'17:30'}];
  var nextTime = '', nextLabel = 'Proxima prospeccion';
  var opts = {weekday:'long',day:'numeric',month:'long'};
  if(isWeekday){
    var proxHoy = null;
    for(var i=0;i<horarios.length;i++){
      if(h < horarios[i].h || (h===horarios[i].h && mi < horarios[i].m)){
        proxHoy = horarios[i]; break;
      }
    }
    if(proxHoy){
      nextTime = 'Hoy ' + now.toLocaleDateString('es-CL',opts) + ' a las ' + proxHoy.label;
    } else {
      var nextDate = new Date(now);
      do { nextDate.setDate(nextDate.getDate()+1); } while(nextDate.getDay()===0||nextDate.getDay()===6);
      nextDate.setHours(9,30,0,0);
      nextTime = nextDate.toLocaleDateString('es-CL',opts) + ' a las 09:30';
    }
  } else {
    var dias = day===6?2:1;
    var nextDate2 = new Date(now);
    nextDate2.setDate(now.getDate()+dias);
    nextDate2.setHours(9,30,0,0);
    nextTime = nextDate2.toLocaleDateString('es-CL',opts) + ' a las 09:30';
  }
  document.getElementById('nextSendTime').textContent = nextTime;
  document.getElementById('nextSendLabel').textContent = nextLabel;
}"""

content = content[:idx] + new_fn + content[end:]

print("async eliminado:", 'async function updateNextSendTime' not in content)
print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test6.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")