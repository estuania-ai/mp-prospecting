with open('templates/dashboard_test6.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = 'nextSendLabel"></div>\n    </div>\n  </div>\n</div>\n\n<!-- ══════════════ MAIN ══════════════ -->'

new = '''nextSendLabel"></div>
    </div>
  </div>

  <div class="sidebar-card" style="border-left:3px solid var(--mp-warn);margin-top:12px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
      <div class="sidebar-lbl">Tareas de Prospectos</div>
      <span id="tareasBadge" style="background:var(--mp-warn);color:#fff;font-size:10px;font-weight:700;padding:1px 7px;border-radius:10px">0</span>
    </div>
    <div id="tareasWidget" style="display:flex;flex-direction:column;gap:6px;max-height:200px;overflow-y:auto">
      <div style="font-size:11px;color:var(--mp-text-3);text-align:center;padding:8px">Sin tareas pendientes</div>
    </div>
    <button class="btn btn-ghost" onclick="showPage('interesados',document.querySelector('[onclick*=interesados]'),'Interesados')" style="width:100%;margin-top:8px;font-size:11px">Ver todas las tareas →</button>
  </div>

</div>

<!-- ══════════════ MAIN ══════════════ -->'''

if old in content:
    content = content.replace(old, new)
    print("Widget sidebar OK")
else:
    print("No encontrado - verificando duplicados")
    print("tareasWidget count:", content.count('tareasWidget'))

with open('templates/dashboard_test6.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")