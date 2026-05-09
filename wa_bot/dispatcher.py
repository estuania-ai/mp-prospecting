"""
Bot WhatsApp - Dispatcher principal.

Recibe mensajes entrantes (vía webhook de Evolution) y decide:
1. Si el bot está activo para ese user.
2. Si la conversación está en hand-off humano → ignora.
3. Si es opt-out → marca y responde despedida.
4. Si matchea una regla → responde con template.
5. Si LLM está activo y no hay match → consulta RAG (Fase 2).
6. Si nada matchea → hand-off al humano.

Capa de abstracción: el cliente WhatsApp (Evolution hoy, Cloud API mañana)
se inyecta vía un objeto que cumpla la interfaz BotClient.
"""
from __future__ import annotations
import logging
import re
from datetime import datetime
from typing import Protocol, Optional

logger = logging.getLogger(__name__)


# ─── Interfaz cliente WhatsApp (abstrae Evolution / Cloud API) ──────
class BotClient(Protocol):
    """Cualquier implementación que mande mensajes por WA."""
    def send_text(self, phone: str, message: str, instance: Optional[str] = None) -> dict: ...
    def send_image(self, phone: str, image_url: str, caption: str = "",
                   instance: Optional[str] = None) -> dict: ...


# ─── Patrones de opt-out (override hand-off) ────────────────────────
_OPT_OUT_KEYWORDS = {
    'baja', 'baj', 'bajar', 'stop', 'parar', 'no quiero', 'no me interesa',
    'no escribir', 'no contactar', 'no me llames', 'no me hables', 'unsubscribe',
    'borrar', 'eliminar', 'spam',
}

_HANDOFF_KEYWORDS = {
    'humano', 'persona real', 'asesor', 'hablar con alguien', 'no eres real',
    'eres un bot', 'sos un bot', 'no es un bot', 'me hablas como robot',
}


def _normalize(text: str) -> str:
    """Lower + strip + collapse espacios, mantiene tildes."""
    if not text:
        return ''
    return ' '.join(text.lower().strip().split())


def _matches_any(text: str, keywords: set) -> bool:
    norm = _normalize(text)
    return any(kw in norm for kw in keywords)


# ─── Persistencia ───────────────────────────────────────────────────
def _get_or_create_conversation(conn, user_id: int, client_phone: str) -> dict:
    """Recupera o crea la conversación bot ↔ cliente."""
    row = conn.execute(
        'SELECT * FROM wa_bot_conversations WHERE user_id=? AND client_phone=?',
        (user_id, client_phone)
    ).fetchone()
    if row:
        return dict(row)
    # Buscar lead_id si tenemos coincidencia de teléfono
    lead_id = None
    lead_row = conn.execute(
        'SELECT id FROM leads WHERE phone = ?', (client_phone,)
    ).fetchone()
    if lead_row:
        lead_id = lead_row['id']
    cur = conn.execute(
        'INSERT INTO wa_bot_conversations (user_id, client_phone, lead_id, last_msg_at) '
        'VALUES (?, ?, ?, datetime("now","localtime"))',
        (user_id, client_phone, lead_id)
    )
    conv_id = cur.lastrowid
    conn.commit()
    row = conn.execute('SELECT * FROM wa_bot_conversations WHERE id = ?', (conv_id,)).fetchone()
    return dict(row)


def _log_message(conn, conv_id: int, direction: str, text: str,
                 matched_rule_id: int | None = None,
                 response_source: str | None = None) -> None:
    conn.execute(
        'INSERT INTO wa_bot_messages (conv_id, direction, text, matched_rule_id, response_source) '
        'VALUES (?, ?, ?, ?, ?)',
        (conv_id, direction, text, matched_rule_id, response_source)
    )
    conn.execute(
        'UPDATE wa_bot_conversations SET messages_count = messages_count + 1, '
        'last_msg_at = datetime("now","localtime") WHERE id = ?',
        (conv_id,)
    )
    conn.commit()


def _set_conversation_state(conn, conv_id: int, state: str, reason: str = '') -> None:
    conn.execute(
        'UPDATE wa_bot_conversations SET state = ?, hand_off_reason = ? WHERE id = ?',
        (state, reason, conv_id)
    )
    conn.commit()


def _mark_lead_opt_out(conn, client_phone: str) -> None:
    """Marca el lead como opt_out en lead_status si existe."""
    try:
        from database import update_lead_status
        update_lead_status(client_phone, 'opt_out',
                           notes='Auto: opt-out por bot WA',
                           optout_motivo='Cliente solicitó dejar de recibir mensajes')
    except Exception as e:
        logger.warning(f'[BotWA] update_lead_status fail: {e}')


# ─── Matching de reglas ────────────────────────────────────────────
def _find_matching_rule(conn, user_id: int, text: str) -> dict | None:
    """Retorna la regla activa de mayor prioridad cuyo keyword aparece en text."""
    norm = _normalize(text)
    rules = conn.execute(
        'SELECT * FROM wa_bot_rules WHERE user_id = ? AND active = 1 '
        'ORDER BY priority ASC, id ASC',
        (user_id,)
    ).fetchall()
    logger.info(
        f'[BotWA-rules] msg_norm="{norm[:80]}" rules_count={len(rules)}'
    )
    for r in rules:
        kws = [k.strip() for k in (r['keywords'] or '').lower().split(',') if k.strip()]
        for kw in kws:
            if kw in norm:
                logger.info(f'[BotWA-rules] MATCH "{kw}" -> rule "{r["label"]}"')
                return dict(r)
    logger.info(f'[BotWA-rules] NO MATCH para "{norm[:80]}"')
    return None


# ─── Helpers de envío ──────────────────────────────────────────────
def _add_footer(text: str, footer: str | None) -> str:
    """Agrega el footer opt-out al final, si no está ya presente."""
    if not footer:
        return text
    if footer.strip() in (text or ''):
        return text
    return f'{text}\n\n{footer}'


def _send_response(client: BotClient, instance: str | None, phone: str,
                    text: str, send_pdf: bool = False,
                    pdf_url: str | None = None) -> None:
    """Enviar respuesta del bot. Si send_pdf, manda imagen primero."""
    if send_pdf and pdf_url:
        try:
            client.send_image(phone, pdf_url, caption=text, instance=instance)
            return
        except Exception as e:
            logger.warning(f'[BotWA] send_image fail, fallback texto: {e}')
    client.send_text(phone, text, instance=instance)


# ─── Punto de entrada principal ────────────────────────────────────
def handle_incoming_message(
    user_id: int,
    client_phone: str,
    text: str,
    client: BotClient,
    instance: str | None = None,
    is_from_me: bool = False,
) -> dict:
    """
    Procesa un mensaje entrante. Retorna dict con resumen de la acción.

    Args:
        user_id: dueño del bot (Owner por ahora)
        client_phone: teléfono del cliente
        text: texto del mensaje
        client: instancia que cumple BotClient (evolution_client wrapper)
        instance: nombre de la instancia Evolution (None = legacy default)
        is_from_me: True si el mensaje lo mandó el propio Owner desde su WA
                    (en ese caso, hand-off automático para ese chat)
    """
    from database import get_db
    conn = get_db()
    try:
        conv = _get_or_create_conversation(conn, user_id, client_phone)
        conv_id = conv['id']

        # ── Cargar config del bot ────────────────────────────────
        cfg_row = conn.execute(
            'SELECT * FROM wa_bot_config WHERE user_id = ?', (user_id,)
        ).fetchone()
        if not cfg_row:
            logger.info(f'[BotWA] sin config para user {user_id}, ignoro')
            return {'action': 'no_config'}
        cfg = dict(cfg_row)

        # ── Hand-off: si el OWNER respondió manual ───────────────
        if is_from_me:
            _set_conversation_state(conn, conv_id, 'hand_off',
                                     reason='Owner respondió manual')
            _log_message(conn, conv_id, 'out', text,
                         response_source='manual')
            logger.info(f'[BotWA] {client_phone}: hand_off (owner manual)')
            return {'action': 'hand_off_manual'}

        # ── Bot deshabilitado ────────────────────────────────────
        if not cfg.get('enabled'):
            _log_message(conn, conv_id, 'in', text)
            logger.info(f'[BotWA] bot disabled para user {user_id}, solo logueo')
            return {'action': 'disabled'}

        # ── Conversación ya en estado especial ───────────────────
        state = conv.get('state', 'active')
        if state == 'opt_out':
            _log_message(conn, conv_id, 'in', text)
            logger.info(f'[BotWA] {client_phone}: ya opt_out, ignoro')
            return {'action': 'already_opt_out'}
        if state == 'hand_off':
            _log_message(conn, conv_id, 'in', text)
            logger.info(f'[BotWA] {client_phone}: hand_off activo, ignoro')
            return {'action': 'hand_off_active'}
        if state == 'closed':
            _log_message(conn, conv_id, 'in', text)
            return {'action': 'closed'}

        _log_message(conn, conv_id, 'in', text)

        # ── Detectar opt-out ─────────────────────────────────────
        if _matches_any(text, _OPT_OUT_KEYWORDS):
            response = cfg.get('opt_out_response') or 'Listo, no te volvemos a contactar.'
            _send_response(client, instance, client_phone, response)
            _log_message(conn, conv_id, 'out', response,
                         response_source='opt_out')
            _set_conversation_state(conn, conv_id, 'opt_out', reason='cliente solicitó baja')
            _mark_lead_opt_out(conn, client_phone)
            logger.info(f'[BotWA] {client_phone}: OPT-OUT')
            return {'action': 'opt_out'}

        # ── Detectar hand-off explícito ──────────────────────────
        if _matches_any(text, _HANDOFF_KEYWORDS):
            response = cfg.get('handoff_response') or 'Te paso con un asesor.'
            _send_response(client, instance, client_phone, response)
            _log_message(conn, conv_id, 'out', response,
                         response_source='handoff')
            _set_conversation_state(conn, conv_id, 'hand_off',
                                     reason='cliente pidió humano')
            logger.info(f'[BotWA] {client_phone}: HAND-OFF (cliente pidió)')
            return {'action': 'handoff_explicit'}

        # ── Match contra reglas ──────────────────────────────────
        rule = _find_matching_rule(conn, user_id, text)
        if rule:
            response = rule['response_text']
            response_with_footer = _add_footer(response, cfg.get('footer_optout'))
            import os
            base_url = os.getenv('APP_BASE_URL', '').rstrip('/')
            pdf_url = (base_url + '/static/email_assets/beneficios_mp.pdf') if base_url \
                      else None
            _send_response(client, instance, client_phone, response_with_footer,
                            send_pdf=bool(rule.get('send_pdf')),
                            pdf_url=pdf_url)
            _log_message(conn, conv_id, 'out', response_with_footer,
                         matched_rule_id=rule['id'], response_source='rule')
            conn.execute(
                'UPDATE wa_bot_conversations SET last_bot_reply_at = datetime("now","localtime") '
                'WHERE id = ?', (conv_id,)
            )
            conn.commit()
            logger.info(f'[BotWA] {client_phone}: rule "{rule["label"]}"')
            return {'action': 'rule_matched', 'rule': rule['label']}

        # ── LLM (Fase 2) ─────────────────────────────────────────
        if cfg.get('llm_enabled'):
            try:
                from wa_bot.rag import generate_response
                response = generate_response(user_id, text)
                if response:
                    response_with_footer = _add_footer(response, cfg.get('footer_optout'))
                    _send_response(client, instance, client_phone, response_with_footer)
                    _log_message(conn, conv_id, 'out', response_with_footer,
                                 response_source='llm')
                    logger.info(f'[BotWA] {client_phone}: LLM')
                    return {'action': 'llm_replied'}
            except Exception as e:
                logger.warning(f'[BotWA] RAG fail: {e}')

        # ── Sin match: hand-off al humano ────────────────────────
        response = cfg.get('handoff_response') or 'Te paso con un asesor.'
        _send_response(client, instance, client_phone, response)
        _log_message(conn, conv_id, 'out', response,
                     response_source='handoff')
        _set_conversation_state(conn, conv_id, 'hand_off',
                                 reason='no se entendió mensaje')
        logger.info(f'[BotWA] {client_phone}: HAND-OFF (no match)')
        return {'action': 'handoff_no_match'}

    finally:
        conn.close()
