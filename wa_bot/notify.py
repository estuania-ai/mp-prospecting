"""
Notificaciones por email del Bot WhatsApp.

Cuando el bot hace hand-off (no puede responder), enviá un email al
notify_email configurado para que el humano sepa que un cliente espera
respuesta.

Reusa la infra de envío de email (routes.email_tool._send_smtp) — soporta
proxy local + SMTP env legacy.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def send_handoff_notification(
    to_email: str,
    client_phone: str,
    client_msg: str,
    conv_id: int,
    handoff_reason: str = '',
    lead_name: str | None = None,
) -> bool:
    """
    Envía un email al Owner avisando que un cliente WhatsApp espera respuesta.

    Args:
        to_email: dirección donde mandar la notificación
        client_phone: teléfono del cliente que escribió
        client_msg: el último mensaje del cliente
        conv_id: id de la conversación bot
        handoff_reason: por qué el bot hizo hand-off
        lead_name: nombre del lead si está vinculado

    Returns: True si se envió OK
    """
    if not to_email or '@' not in to_email:
        logger.warning(f'[BotNotify] notify_email invalido: {to_email!r}')
        return False
    try:
        # Construir el body simple en HTML
        wa_link = f'https://wa.me/{client_phone}'
        msg_safe = (client_msg or '').replace('<', '&lt;').replace('>', '&gt;')
        nombre = (lead_name or '').strip() or '(sin nombre — no es un lead conocido)'
        reason_safe = (handoff_reason or '').replace('<', '&lt;').replace('>', '&gt;') or 'sin entender mensaje'

        html = f"""
<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:0 auto;padding:20px;background:#FFF8E1;border-left:4px solid #F59E0B;border-radius:8px">
  <h2 style="color:#92400E;font-size:18px;margin:0 0 10px">⚠️ Cliente WhatsApp espera respuesta</h2>
  <p style="color:#1A1A2E;font-size:13px;margin:0 0 14px">El bot no pudo responder y derivó a vos. Abrí WhatsApp y respondé directamente.</p>

  <table cellpadding="0" cellspacing="0" border="0" style="width:100%;background:#fff;border-radius:8px;border:1px solid #FDE68A;margin-bottom:14px">
    <tr><td style="padding:10px 14px;border-bottom:1px solid #FDE68A">
      <div style="font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:.04em">📞 Cliente</div>
      <div style="font-size:14px;font-weight:700;color:#1A1A2E;margin-top:2px">{nombre}</div>
      <div style="font-size:13px;color:#444;margin-top:2px">+{client_phone}</div>
    </td></tr>
    <tr><td style="padding:10px 14px;border-bottom:1px solid #FDE68A">
      <div style="font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:.04em">💬 Último mensaje</div>
      <div style="font-size:13px;color:#1A1A2E;margin-top:4px;background:#F8F6F2;padding:8px 10px;border-radius:6px;font-style:italic">"{msg_safe}"</div>
    </td></tr>
    <tr><td style="padding:10px 14px">
      <div style="font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:.04em">🤖 Razón del hand-off</div>
      <div style="font-size:13px;color:#444;margin-top:4px">{reason_safe}</div>
    </td></tr>
  </table>

  <div style="text-align:center;margin-bottom:14px">
    <a href="{wa_link}" target="_blank" style="display:inline-block;background:#25D366;color:#FFFFFF;font-size:14px;font-weight:700;padding:12px 24px;border-radius:100px;text-decoration:none">
      💬 Abrir conversación en WhatsApp
    </a>
  </div>

  <p style="font-size:11px;color:#888;margin:0;text-align:center">
    Bot WhatsApp · MP Prospecting · Conversación #{conv_id}
  </p>
</div>
"""
        plain = (
            f'Cliente WhatsApp espera respuesta\n\n'
            f'Cliente: {nombre} (+{client_phone})\n'
            f'Mensaje: "{client_msg}"\n'
            f'Hand-off: {handoff_reason}\n\n'
            f'Abrí: {wa_link}'
        )

        # Reusamos _send_smtp del email_tool — soporta proxy local + SMTP env
        from routes.email_tool import _send_smtp
        # Hack: _send_smtp espera body_text plain, le pasamos texto plano y
        # contruye HTML genérico — pero queremos custom HTML, así que armamos
        # el envío directo aquí.

        import os, smtplib, ssl
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.utils import formataddr

        smtp_host  = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        smtp_port  = int(os.getenv('SMTP_PORT', '587'))
        smtp_user  = os.getenv('SMTP_USER', '')
        smtp_pass  = os.getenv('SMTP_PASS', '')
        from_email = os.getenv('EMAIL_FROM', smtp_user)
        from_name  = os.getenv('EMAIL_FROM_NAME', 'Bot WhatsApp · MP Prospecting')

        if not smtp_user:
            logger.warning('[BotNotify] SMTP_USER no configurado')
            return False

        msg_root = MIMEMultipart('alternative')
        msg_root['Subject'] = f'[Bot WA] {nombre} espera respuesta — +{client_phone}'
        msg_root['From']    = formataddr((from_name, from_email))
        msg_root['To']      = to_email
        msg_root['Reply-To']= formataddr((from_name, from_email))
        msg_root.attach(MIMEText(plain, 'plain', 'utf-8'))
        msg_root.attach(MIMEText(html, 'html', 'utf-8'))

        # Proxy local primero (igual lógica que _send_smtp)
        email_local_url = os.getenv('EMAIL_LOCAL_URL', '').strip()
        email_local_token = (os.getenv('EMAIL_LOCAL_TOKEN', '').strip()
                              or os.getenv('FAST_LOCAL_TOKEN', '').strip())
        if email_local_url:
            try:
                import requests as _req
                resp = _req.post(
                    email_local_url.rstrip('/') + '/send-email',
                    json={
                        'to_email':    to_email,
                        'from_email':  from_email,
                        'subject':     msg_root['Subject'],
                        'raw_message': msg_root.as_string(),
                    },
                    headers={'X-Fast-Token': email_local_token},
                    timeout=60,
                )
                data = resp.json()
                if data.get('ok'):
                    logger.info(f'[BotNotify] enviado a {to_email} via proxy local')
                    return True
                logger.warning(f'[BotNotify] proxy local fail: {data}')
                # caer a SMTP directo
            except Exception as e:
                logger.warning(f'[BotNotify] proxy local error: {e}')

        # SMTP directo
        try:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as s:
                s.ehlo(); s.starttls(context=ctx); s.login(smtp_user, smtp_pass)
                s.sendmail(from_email, to_email, msg_root.as_string())
            logger.info(f'[BotNotify] enviado a {to_email} via SMTP directo')
            return True
        except Exception as e:
            logger.error(f'[BotNotify] SMTP fail: {e}')
            return False

    except Exception as e:
        logger.error(f'[BotNotify] error general: {e}', exc_info=True)
        return False
