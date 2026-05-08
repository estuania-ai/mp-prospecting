"""
Job de prospeccion diaria - 3 lotes L-V
Lote 1: 15 mensajes a las 09:30
Lote 2: 10 mensajes a las 15:00
Lote 3: 15 mensajes a las 17:30
Total: 40 mensajes diarios

PROTECCIONES CONTRA DUPLICADOS Y ENVÍOS INAPROPIADOS:
- Validación de teléfono antes de enviar (formato +56 o 56)
- Bloqueo de envíos fuera de horario permitido (07:00-20:00)
- Deduplicación de mensajes en la BD
"""

import logging
import re
from datetime import datetime
from database import get_db, get_config
from rubros_config import get_mensaje, get_imagen_url

logger = logging.getLogger(__name__)

# Horarios permitidos para envío (Santiago, Chile)
ALLOWED_SEND_HOURS = (7, 20)  # 07:00 a 20:00


def is_valid_phone(phone: str) -> bool:
    """
    Valida que sea número móvil chileno válido para WhatsApp.
    - RECHAZA: 562XXXXXXX (números fijos/landlines - no soportan WhatsApp)
    - ACEPTA: 569XXXXXXX (celulares - 9 dígitos)
    """
    if not phone:
        return False
    # Limpia espacios y guiones
    phone = phone.strip().replace(' ', '').replace('-', '')

    # RECHAZA números fijos que comienzan con 562
    if re.match(r'^(\+?56)?2\d{8}$', phone):
        return False  # Número fijo (landline), no soporta WhatsApp

    # ACEPTA solo celulares: +56 o 56 seguido de 9 dígitos (comienzan con 9)
    return bool(re.match(r'^(\+?56)?9\d{8}$', phone))


def is_allowed_send_hour() -> bool:
    """Verifica que la hora actual esté en el rango permitido"""
    current_hour = datetime.now().hour
    return ALLOWED_SEND_HOURS[0] <= current_hour < ALLOWED_SEND_HOURS[1]


def get_pending_leads(limit: int, offset: int = 0, assigned_to_user_id: int | None = None) -> list:
    """
    Devuelve leads en estado 'no_enviado' válidos para WA.
    Si se pasa `assigned_to_user_id`, filtra solo leads asignados a ese usuario.
    """
    conn = get_db()
    base_sql = '''
        SELECT l.id, l.name, l.phone, l.comuna, l.rubro, l.address
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        LEFT JOIN opt_out o ON l.phone = o.phone
        WHERE o.phone IS NULL
          AND ls.status = 'no_enviado'
          AND l.phone IS NOT NULL
    '''
    params: list = []
    if assigned_to_user_id is not None:
        base_sql += ' AND l.assigned_to = ?'
        params.append(int(assigned_to_user_id))
    base_sql += ' ORDER BY ls.updated_at ASC NULLS FIRST LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    rows = conn.execute(base_sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows if is_valid_phone(r['phone'])]


def get_users_active_for_slot(slot_field: str) -> list:
    """
    Devuelve [{'id', 'full_name', 'email', 'role', 'evolution_instance', 'daily_limit'}, ...]
    de los usuarios activos que tienen el toggle del slot encendido en user_scheduler_config.
    Si no hay ninguno → lista vacía (el caller decide si correr legacy global).
    """
    if slot_field not in (
        'prospeccion_0930_active', 'prospeccion_1500_active', 'prospeccion_1730_active',
        'seguimiento_24h_active', 'seguimiento_72h_active', 'fidelizacion_active',
        'email_lote1_active', 'email_lote2_active', 'email_lote3_active',
        'email_followup_active',
    ):
        return []
    conn = get_db()
    rows = conn.execute(f'''
        SELECT u.id, u.full_name, u.email, u.role, u.evolution_instance,
               COALESCE(c.daily_limit, 50) as daily_limit
        FROM user_scheduler_config c
        JOIN users u ON u.id = c.user_id
        WHERE c.{slot_field} = 1
          AND u.is_active = 1
          AND u.role IN ('sales','owner','tl')
    ''').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def resolve_user_instance(user: dict) -> str:
    """
    Devuelve nombre de instancia Evolution del usuario.
    Owner → instancia legacy; Sales/TL → users.evolution_instance o 'sales_<id>'.
    """
    from whatsapp import evolution_client as ev
    role = (user.get('role') or '').strip()
    if role == 'owner':
        return ev._default_instance()
    inst = (user.get('evolution_instance') or '').strip()
    if inst:
        return inst
    return ev.instance_name_for_user(user['id'], role)


def build_message(contact: dict) -> str:
    nombre    = contact.get('name', 'estimado/a')
    rubro_key = contact.get('rubro', 'almacen')
    comuna    = contact.get('comuna', '')
    return get_mensaje(rubro_key, nombre, comuna)


def build_image_url(contact: dict) -> str | None:
    return get_imagen_url(contact.get('rubro', ''))


def register_send(contact: dict, success: bool, error: str = None):
    conn = get_db()
    lead_id = contact.get('id')
    phone = contact.get('phone')

    # ── DEDUPLICACIÓN: Verifica si ya existe un mensaje hoy para este lead ──
    today = datetime.now().strftime('%Y-%m-%d')
    existing = conn.execute('''
        SELECT COUNT(*) as cnt FROM messages
        WHERE lead_id = ? AND message_type = 'prospecting'
          AND date(sent_at) = ?
    ''', (lead_id, today)).fetchone()

    if existing and existing['cnt'] > 0:
        logger.warning(f"[DEDUP] Ya existe mensaje hoy para lead {lead_id} ({phone}) - evitando duplicado")
        conn.close()
        return

    status = 'sent' if success else 'failed'
    if error == 'phone_not_exists':
        status = 'phone_not_exists'

    conn.execute('''
        INSERT INTO messages (lead_id, phone, message_type, status, sent_at, rubro, comuna)
        VALUES (?, ?, 'prospecting', ?, datetime('now','localtime'), ?, ?)
    ''', (
        lead_id, phone, status,
        contact.get('rubro'), contact.get('comuna')
    ))

    lead_status = 'enviado' if success else ('telefono_no_existe' if error == 'phone_not_exists' else 'no_enviado')
    conn.execute('''
        INSERT INTO lead_status (lead_id, status, updated_at)
        VALUES (?, ?, datetime('now','localtime'))
        ON CONFLICT(lead_id) DO UPDATE SET
            status = excluded.status,
            updated_at = excluded.updated_at
    ''', (lead_id, lead_status))

    conn.commit()
    conn.close()


def _send_leads_via_evolution(leads: list, batch_name: str, owner_label: str = "",
                               instance: str | None = None) -> tuple[int, int, int]:
    """Envía la lista de leads via Evolution API. Retorna (sent, no_phone, failed).
    Si `instance` se pasa, se usa esa instancia (multi-WA per Sales)."""
    import time, random
    from whatsapp import evolution_client as ev

    conn = get_db()
    delay_min = int(conn.execute("SELECT value FROM config WHERE key='wa_delay_min_sec'").fetchone()[0] or 30)
    delay_max = int(conn.execute("SELECT value FROM config WHERE key='wa_delay_max_sec'").fetchone()[0] or 60)
    conn.close()

    sent = failed = no_phone = 0
    for i, contact in enumerate(leads):
        phone     = contact.get('phone', '')
        message   = build_message(contact)
        image_url = build_image_url(contact)

        result = ev.send_message(phone, message, image_url, instance=instance)
        ok     = result.get("ok", False)
        error  = result.get("error", "")

        register_send(contact, ok, None if ok else error)

        if ok:
            sent += 1
        elif 'phone' in str(error).lower():
            no_phone += 1
        else:
            failed += 1

        logger.info(f"[{batch_name}{owner_label}] [{i+1}/{len(leads)}] {phone} → {'OK' if ok else 'FAIL'}")

        if i < len(leads) - 1:
            delay = random.uniform(delay_min, delay_max)
            time.sleep(delay)
    return sent, no_phone, failed


def run_prospecting_batch(limit: int, batch_name: str = "", slot_field: str | None = None):
    """
    Ejecuta el lote de prospección.
    - Si hay usuarios con `slot_field` activo en user_scheduler_config:
        corre por cada usuario filtrando solo sus leads asignados,
        aplicando min(limit, user.daily_limit, leads_disponibles).
    - Si no hay ninguno con toggle activo: NO corre legacy global
      (los nuevos jobs son explícitamente per-user; el toggle es la fuente de verdad).
    """
    current_time = datetime.now().strftime('%H:%M')
    logger.info(f"[PROSPECCION {batch_name}] Iniciando - default {limit} - {current_time}")

    if not is_allowed_send_hour():
        logger.warning(f"[{batch_name}] ❌ BLOQUEADO: Intento de envío a las {current_time} (solo permitido 07:00-20:00)")
        return

    from whatsapp import evolution_client as ev

    users = get_users_active_for_slot(slot_field) if slot_field else []
    if not users:
        logger.info(f"[{batch_name}] Ningún usuario con toggle activo para '{slot_field}' — skip")
        return

    total_sent = total_failed = total_no_phone = 0
    for u in users:
        instance = resolve_user_instance(u)
        label = f" · {u.get('full_name') or u.get('email')} [{instance}]"
        # Gate por instancia: solo enviamos si la WA del Sales está conectada
        if not ev.is_connected(instance=instance):
            logger.warning(f"[{batch_name}{label}] WhatsApp desconectado — skip")
            continue
        per_user_limit = min(limit, int(u.get('daily_limit') or limit))
        leads = get_pending_leads(per_user_limit, assigned_to_user_id=u['id'])
        if not leads:
            logger.info(f"[{batch_name}{label}] Sin leads asignados pendientes")
            continue
        logger.info(f"[{batch_name}{label}] {len(leads)} leads (limit={per_user_limit})")
        s, n, f = _send_leads_via_evolution(leads, batch_name, owner_label=label, instance=instance)
        total_sent += s
        total_no_phone += n
        total_failed += f

    logger.info(f"[{batch_name}] TOTAL: {total_sent} enviados, {total_no_phone} sin tel, {total_failed} fallidos")

    if total_sent > 0:
        conn = get_db()
        conn.execute('''
            INSERT INTO campaigns (name, total_sent, sent_at, status)
            VALUES (?, ?, datetime('now','localtime'), 'completed')
        ''', (f"Lote {batch_name} {datetime.now().strftime('%d/%m/%Y %H:%M')}", total_sent))
        conn.commit()
        conn.close()


# Funciones llamadas por el scheduler
def run_batch1(): run_prospecting_batch(15, "09:30", slot_field='prospeccion_0930_active')
def run_batch2(): run_prospecting_batch(10, "15:00", slot_field='prospeccion_1500_active')
def run_batch3(): run_prospecting_batch(15, "17:30", slot_field='prospeccion_1730_active')

# Compatibilidad con llamada directa: dispara los 3 lotes en secuencia.
def run_prospecting():
    run_batch1()
    run_batch2()
    run_batch3()
