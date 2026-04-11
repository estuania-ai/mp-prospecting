with open('routes/leads.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = """        LEFT JOIN (
            SELECT lead_id, message_type, sent_at
            FROM messages
            WHERE message_type IN ('seguimiento_24h','seguimiento_72h')
            AND status = 'sent'
            ORDER BY sent_at DESC
        ) seg ON l.id = seg.lead_id"""

new = """        LEFT JOIN (
            SELECT lead_id, sent_at
            FROM messages
            WHERE message_type = 'seguimiento_24h' AND status = 'sent'
            GROUP BY lead_id
        ) seg24 ON l.id = seg24.lead_id
        LEFT JOIN (
            SELECT lead_id, sent_at
            FROM messages
            WHERE message_type = 'seguimiento_72h' AND status = 'sent'
            GROUP BY lead_id
        ) seg72 ON l.id = seg72.lead_id"""

content = content.replace(old, new)

old2 = """               seg.message_type as seguimiento_tipo,
               seg.sent_at as seguimiento_fecha"""

new2 = """               seg24.sent_at as seguimiento_24h_fecha,
               CASE WHEN seg24.lead_id IS NOT NULL THEN 1 ELSE 0 END as seguimiento_24h,
               seg72.sent_at as seguimiento_72h_fecha,
               CASE WHEN seg72.lead_id IS NOT NULL THEN 1 ELSE 0 END as seguimiento_72h"""

content = content.replace(old2, new2)

with open('routes/leads.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK leads.py - seguimiento doble OK")