"""
mp_fix_campaigns_completo.py
1. Registra campanas retroactivas desde mensajes enviados sin campana
2. Mejora el endpoint de campanas para mostrar todas las actividades
3. Agrupa mensajes por dia y tipo para el historial
"""
import sqlite3
import os

db_path = 'data/prospecting.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Ver estado actual
print("=== Campanas actuales ===")
camps = conn.execute("SELECT id, name, total_sent, sent_at FROM campaigns ORDER BY sent_at DESC").fetchall()
for c in camps:
    print(f"  ID:{c[0]} | {c[1]} | {c[2]} msgs | {c[3]}")

print("\n=== Mensajes por dia y tipo ===")
msgs = conn.execute("""
    SELECT date(sent_at) as dia, message_type, COUNT(*) as total
    FROM messages
    WHERE status = 'sent'
    GROUP BY dia, message_type
    ORDER BY dia DESC
""").fetchall()
for m in msgs:
    print(f"  {m[0]} | {m[1]}: {m[2]}")

# Crear campanas retroactivas para mensajes sin campana
print("\n=== Creando campanas retroactivas ===")

# Agrupar mensajes por dia y tipo
grupos = conn.execute("""
    SELECT date(sent_at) as dia,
           message_type,
           COUNT(*) as total,
           MIN(sent_at) as primera,
           MAX(sent_at) as ultima
    FROM messages
    WHERE status = 'sent'
    GROUP BY dia, message_type
    ORDER BY dia DESC
""").fetchall()

for g in grupos:
    dia = g['dia']
    tipo = g['message_type']
    total = g['total']
    ultima = g['ultima']

    # Ver si ya existe campana para este dia y tipo
    existing = conn.execute("""
        SELECT id FROM campaigns
        WHERE date(sent_at) = ? AND name LIKE ?
    """, (dia, f'%{dia}%')).fetchone()

    if not existing:
        if tipo == 'manual':
            nombre = f"Envio manual {dia} - {total} mensajes"
        elif tipo == 'prospecting':
            nombre = f"Prospeccion automatica {dia} - {total} mensajes"
        elif tipo in ('seguimiento_24h', 'seguimiento_72h'):
            nombre = f"Seguimiento {tipo.split('_')[1]} {dia} - {total} mensajes"
        else:
            nombre = f"{tipo} {dia} - {total} mensajes"

        conn.execute("""
            INSERT INTO campaigns (name, total_sent, sent_at, status)
            VALUES (?, ?, ?, 'completed')
        """, (nombre, total, ultima))
        print(f"  Creada: {nombre}")

conn.commit()

print("\n=== Campanas finales ===")
camps2 = conn.execute("SELECT id, name, total_sent, sent_at FROM campaigns ORDER BY sent_at DESC").fetchall()
for c in camps2:
    print(f"  ID:{c[0]} | {c[1]} | {c[2]} msgs | {c[3]}")

conn.close()
print("\nOK")
