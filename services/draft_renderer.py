"""
Renderiza templates de email (et_rubro_templates) reemplazando variables
por los datos de cada contacto.

Variables soportadas:
  · {{nombre}}       → primera palabra del business_name (saludo)
  · {{comercio}}     → business_name completo
  · {{rubro}}        → rubro del contacto
  · {{comuna}}       → comuna del contacto
  · {{telefono}}     → teléfono
  · {{footer_optout}} → footer opt-out estándar (Ley 19.628 CL)

Seguridad:
  · Uso de Jinja2 con autoescape para prevenir HTML injection desde el
    business_name u otros campos que originalmente vienen de scraping.
  · Las variables se pasan como valores separados a Jinja2 (no
    concatenación de strings), por lo que un business_name malicioso
    no puede escapar del template.
"""
from __future__ import annotations
import re
from jinja2 import Environment, select_autoescape
from markupsafe import Markup

# Environment con autoescape para HTML (CWE-79 XSS)
_env = Environment(
    autoescape=select_autoescape(enabled_extensions=("html",), default=True),
    variable_start_string="{{",
    variable_end_string="}}",
)

FOOTER_OPTOUT_DEFAULT = (
    "<p style='font-size:11px;color:#888;margin-top:24px;"
    "border-top:1px solid #eee;padding-top:12px'>"
    "Si no querés recibir más mensajes comerciales, respondé este "
    "correo con la palabra <strong>BAJA</strong> y no volveremos a "
    "contactarte. Cumplimos con la Ley 19.628 de Protección de la Vida "
    "Privada (Chile)."
    "</p>"
)


def _first_name(business_name: str) -> str:
    """Extrae saludo del nombre del comercio."""
    if not business_name:
        return "amigo"
    bn = business_name.strip()
    palabras_genericas = {
        "almacen", "almacén", "botilleria", "botillería", "cafeteria",
        "cafetería", "carniceria", "carnicería", "panaderia", "panadería",
        "pizzeria", "pizzería", "restaurant", "minimarket", "ferreteria",
        "ferretería", "fruteria", "frutería", "peluqueria", "peluquería",
        "farmacia", "libreria", "librería", "lavanderia", "lavandería",
        "muebleria", "muebleria", "sandwicheria", "sandwichería",
    }
    parts = bn.split()
    if len(parts) >= 2 and parts[0].lower() in palabras_genericas:
        return " ".join(parts[1:])
    return parts[0] if parts else "amigo"


def render_email(template_body_html: str, template_subject: str,
                  contact: dict) -> tuple[str, str]:
    """
    Renderea (subject, body) para un contacto usando Jinja2 con autoescape.

    contact: dict con business_name, rubro, comuna, email, phone.

    Returns: (subject_final, html_body_final)
    """
    # nombre/comercio/rubro/comuna/telefono vienen de fuentes externas
    # (scraping, imports) · Jinja2 los va a autoescapar (protege XSS).
    # footer_optout viene de nuestro código y es HTML legítimo · lo marcamos
    # como Markup para que no se autoescape.
    ctx = {
        "nombre":        _first_name(contact.get("business_name") or ""),
        "comercio":      (contact.get("business_name") or "").strip(),
        "rubro":         (contact.get("rubro") or "").strip(),
        "comuna":        (contact.get("comuna") or contact.get("ciudad") or "").strip(),
        "telefono":      (contact.get("phone") or "").strip(),
        "footer_optout": Markup(FOOTER_OPTOUT_DEFAULT),
    }

    # Subject como plain text · sin autoescape HTML
    subj_tmpl = _env.from_string(template_subject or "", template_class=None)
    subject_out = subj_tmpl.render(**ctx)

    # Body como HTML · autoescape activo
    body_tmpl = _env.from_string(template_body_html or "")
    body_out = body_tmpl.render(**ctx)

    # Si el template no contiene el footer, lo agregamos automáticamente
    if "BAJA" not in body_out and "opt" not in body_out.lower():
        body_out = body_out + "\n" + FOOTER_OPTOUT_DEFAULT

    return subject_out, body_out


_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def valid_email(email: str) -> bool:
    if not email or len(email) > 200:
        return False
    return bool(_EMAIL_RE.match(email.strip()))
