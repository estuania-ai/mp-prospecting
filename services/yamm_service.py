"""
Servicio YAMM — Mail Merge vía Google Sheets + complemento YAMM.

Flujo soportado:
  1. Dashboard selecciona leads (et_contacts) con filtros
  2. Genera CSV con columnas que YAMM espera
  3. User pega CSV en un Google Sheet vacío
  4. User corre YAMM desde el Sheet (template Gmail borrador)
  5. YAMM rellena columnas con resultados (Merge status, Date sent, Opens, etc.)
  6. User exporta el Sheet a CSV y lo sube de vuelta al dashboard
  7. Dashboard actualiza yamm_campaign_contacts + et_contacts (métricas globales)

Columnas YAMM (estándar del complemento):
  - Email             (obligatoria · destino)
  - Merge status      (YAMM rellena: SENT, OPENED, CLICKED, RESPONDED, BOUNCED, ERROR)
  - Date sent
  - Date opened
  - Date clicked
  - Date responded
  - Comments
"""
from __future__ import annotations
import csv
import io
import logging
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── COLUMNAS ──────────────────────────────────────────────────
# Columnas de DATOS que el dashboard exporta (template variables)
EXPORT_COLS_DATA = [
    "Email",          # obligatoria para YAMM
    "Nombre",         # primera palabra del business_name (saludo)
    "Comercio",       # business_name completo
    "Rubro",
    "Comuna",
    "Telefono",
    "ContactId",      # ID interno · vincula con et_contacts
    "CampaignId",     # ID interno · vincula con yamm_campaigns
]

# Columnas YAMM (las rellena el complemento al enviar)
EXPORT_COLS_YAMM = [
    "Merge status",
    "Date sent",
    "Date opened",
    "Date clicked",
    "Date responded",
    "Comments",
]


# ── HELPERS ───────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def _valid_email(email: str) -> bool:
    if not email or len(email) > 200:
        return False
    return bool(_EMAIL_RE.match(email.strip()))


def _first_name(business_name: str) -> str:
    """
    Extrae primera palabra del nombre de negocio para saludo.
    Ej: 'Almacén Don Felipe' → 'Don Felipe' fallback 'Almacén'.
    Si no se puede inferir, devuelve cadena vacía (template lo manejará).
    """
    if not business_name:
        return ""
    bn = business_name.strip()
    # Heurística: si arranca con sustantivo común tipo "Almacén / Botillería / etc",
    # devolvemos el resto. Si no, primera palabra.
    palabras_genericas = {
        "almacen", "almacén", "botilleria", "botillería", "cafeteria", "cafetería",
        "carniceria", "carnicería", "panaderia", "panadería", "pizzeria", "pizzería",
        "restaurant", "minimarket", "ferreteria", "ferretería", "fruteria", "frutería",
        "peluqueria", "peluquería", "farmacia", "libreria", "librería", "lavanderia",
        "lavandería", "muebleria", "muebleria", "sandwicheria", "sandwichería",
    }
    parts = bn.split()
    if len(parts) >= 2 and parts[0].lower() in palabras_genericas:
        return " ".join(parts[1:])
    return parts[0] if parts else ""


# ── EXPORT ────────────────────────────────────────────────────
def build_csv_for_yamm(contacts: list[dict], campaign_id: int) -> str:
    """
    Genera el contenido CSV listo para pegar en Google Sheet + YAMM.

    contacts: lista de dicts con keys: id, business_name, email, rubro,
              ciudad, comuna, phone.
    campaign_id: el id de yamm_campaigns que creamos en la BD.

    Returns: string CSV completo (con header). UTF-8 con BOM para
    que Excel/Google Sheets reconozca tildes correctamente.
    """
    output = io.StringIO()
    # BOM UTF-8 para compatibilidad Excel
    output.write("﻿")

    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    # Header: primero columnas de datos, después las que YAMM completará
    writer.writerow(EXPORT_COLS_DATA + EXPORT_COLS_YAMM)

    skipped = 0
    written = 0
    for c in contacts:
        email = (c.get("email") or "").strip()
        if not _valid_email(email):
            skipped += 1
            continue
        bn = (c.get("business_name") or "").strip()
        row = [
            email,
            _first_name(bn),
            bn,
            (c.get("rubro") or "").strip(),
            (c.get("comuna") or c.get("ciudad") or "").strip(),
            (c.get("phone") or "").strip(),
            str(c.get("id") or ""),
            str(campaign_id),
            # 6 columnas vacías para que YAMM las llene:
            "", "", "", "", "", "",
        ]
        writer.writerow(row)
        written += 1

    logger.info(
        f"[YAMM] CSV generado campaign={campaign_id} "
        f"written={written} skipped_invalid_email={skipped}"
    )
    return output.getvalue()


# ── IMPORT (resultados de YAMM) ───────────────────────────────
def parse_yamm_results_csv(csv_content: str) -> list[dict]:
    """
    Parsea un CSV exportado desde el Sheet (post-YAMM) y devuelve
    lista de dicts con los resultados por contacto.

    YAMM no garantiza nombres EXACTOS de columnas (a veces cambia
    'Date sent' por 'Sent date', etc.). Detectamos por keyword.
    """
    # Strip BOM si está presente
    if csv_content.startswith("﻿"):
        csv_content = csv_content[1:]

    reader = csv.DictReader(io.StringIO(csv_content))

    # Mapear columnas con tolerancia a variaciones
    col_map = _detect_columns(reader.fieldnames or [])
    if not col_map.get("email"):
        raise ValueError("CSV no contiene columna Email")

    results = []
    for raw in reader:
        email = (raw.get(col_map["email"]) or "").strip().lower()
        if not _valid_email(email):
            continue

        merge_status = (raw.get(col_map.get("merge_status") or "") or "").strip().upper()

        results.append({
            "email":        email,
            "contact_id":   _safe_int(raw.get(col_map.get("contact_id") or "")),
            "campaign_id":  _safe_int(raw.get(col_map.get("campaign_id") or "")),
            "merge_status": merge_status,
            "sent_at":      (raw.get(col_map.get("date_sent")     or "") or "").strip() or None,
            "opened_at":    (raw.get(col_map.get("date_opened")   or "") or "").strip() or None,
            "clicked_at":   (raw.get(col_map.get("date_clicked")  or "") or "").strip() or None,
            "replied_at":   (raw.get(col_map.get("date_responded") or "") or "").strip() or None,
            "bounced":      1 if "BOUNCE" in merge_status or "ERROR" in merge_status else 0,
            "comments":     (raw.get(col_map.get("comments") or "") or "").strip() or None,
        })
    return results


def _detect_columns(fieldnames: list[str]) -> dict:
    """
    Mapea nombres reales del CSV YAMM a claves internas usando keywords.
    YAMM varía levemente entre versiones · esto lo hace tolerante.
    """
    m = {}
    for fn in fieldnames:
        if not fn:
            continue
        f_low = fn.lower().strip()
        if "email" in f_low and "email" not in m:
            m["email"] = fn
        elif "merge" in f_low and "status" in f_low:
            m["merge_status"] = fn
        elif "sent" in f_low and "date" in f_low:
            m["date_sent"] = fn
        elif "open" in f_low and "date" in f_low:
            m["date_opened"] = fn
        elif "click" in f_low and "date" in f_low:
            m["date_clicked"] = fn
        elif ("respond" in f_low or "repl" in f_low) and "date" in f_low:
            m["date_responded"] = fn
        elif "comment" in f_low:
            m["comments"] = fn
        elif f_low == "contactid":
            m["contact_id"] = fn
        elif f_low == "campaignid":
            m["campaign_id"] = fn
    return m


def _safe_int(val) -> Optional[int]:
    try:
        return int(str(val).strip())
    except Exception:
        return None
