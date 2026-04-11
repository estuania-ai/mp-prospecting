with open('routes/leads.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = """        SELECT l.id, l.name, l.phone, l.comuna, l.rubro, l.categoria,
               l.created_at, l.updated_at,
               ls.status, ls.notes,
               m.sent_at, m.opened_at"""

new = """        SELECT l.id, l.name, l.phone, l.comuna, l.rubro, l.categoria,
               l.created_at, l.updated_at,
               ls.status, ls.notes,
               m.sent_at, m.opened_at,
               seg.message_type as seguimiento_tipo,
               seg.sent_at as seguimiento_fecha"""

content = content.replace(old, new)

old2 = """        LEFT JOIN (
            SELECT lead_id, sent_at, opened_at, message_type
            FROM messages
            WHERE message_type IN ('prospecting','manual')
            GROUP BY lead_id
        ) m ON l.id = m.lead_id"""

new2 = """        LEFT JOIN (
            SELECT lead_id, sent_at, opened_at, message_type
            FROM messages
            WHERE message_type IN ('prospecting','manual')
            GROUP BY lead_id
        ) m ON l.id = m.lead_id
        LEFT JOIN (
            SELECT lead_id, message_type, sent_at
            FROM messages
            WHERE message_type IN ('seguimiento_24h','seguimiento_72h')
            AND status = 'sent'
            ORDER BY sent_at DESC
        ) seg ON l.id = seg.lead_id"""

content = content.replace(old2, new2)

with open('routes/leads.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK leads.py - seguimiento_tipo agregado")