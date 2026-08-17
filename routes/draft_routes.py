"""
Blueprint: /api/email/drafts

Genera borradores Gmail vía Apps Script Web App.
Ver docs/APPS_SCRIPT_DRAFTS.md
"""
from __future__ import annotations
import logging
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from database import get_db
from services.apps_script_client import (
    create_drafts, health_check, AppsScriptError,
    MAX_DRAFTS_PER_REQUEST,
)
from services.draft_renderer import render_email, valid_email

logger = logging.getLogger(__name__)
bp = Blueprint("drafts", __name__, url_prefix="/api/email/drafts")


# ── HELPERS ───────────────────────────────────────────────────
def _owner_or_tl_required() -> bool:
    return getattr(current_user, "role", "") in ("owner", "tl")


def _get_template(rubro: str) -> dict | None:
    """Recupera el template del rubro (o el genérico si no existe)."""
    conn = get_db()
    row = conn.execute(
        "SELECT rubro, subject, body FROM et_rubro_templates WHERE rubro = ?",
        (rubro.strip().lower(),),
    ).fetchone()
    if not row:
        # Fallback: primer template disponible
        row = conn.execute(
            "SELECT rubro, subject, body FROM et_rubro_templates ORDER BY id ASC LIMIT 1"
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def _filter_contacts(filters: dict, limit: int) -> list[dict]:
    """
    Selecciona contactos aplicando filtros con params bindeados.
    Excluye opt-outs y contactos sin email válido.
    """
    where = ["email IS NOT NULL AND email != ''", "(opt_out IS NULL OR opt_out = 0)"]
    params: list = []

    if filters.get("rubro"):
        where.append("LOWER(rubro) = LOWER(?)")
        params.append(filters["rubro"].strip())
    if filters.get("comuna"):
        where.append("(LOWER(comuna) = LOWER(?) OR LOWER(ciudad) = LOWER(?))")
        params.append(filters["comuna"].strip())
        params.append(filters["comuna"].strip())
    if filters.get("estado"):
        st = filters["estado"].strip().lower()
        if st == "pendiente":
            where.append("(campaign_status IS NULL OR campaign_status = 'pendiente')")
        elif st and st != "todos":
            where.append("campaign_status = ?")
            params.append(st)

    where_clause = " AND ".join(where)
    conn = get_db()
    rows = conn.execute(
        f"SELECT id, business_name, email, rubro, comuna, ciudad, phone "
        f"FROM et_contacts WHERE {where_clause} "
        f"ORDER BY id ASC LIMIT ?",
        params + [limit],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── ENDPOINTS ─────────────────────────────────────────────────
@bp.get("/health")
@login_required
def health():
    """Verifica que Apps Script esté configurado y reachable."""
    if not _owner_or_tl_required():
        return jsonify({"error": "Solo Owner/TL"}), 403
    return jsonify(health_check())


@bp.post("/preview")
@login_required
def preview():
    """
    Preview de contactos + HTML renderizado del primer contacto.
    Body: { rubro, comuna, estado, limit, template_rubro }
    """
    if not _owner_or_tl_required():
        return jsonify({"error": "Solo Owner/TL"}), 403

    data = request.get_json(silent=True) or {}
    limit = min(int(data.get("limit") or 20), 100)

    contacts = _filter_contacts(data, limit)
    total_available = len(contacts)  # aprox · para preview usamos limit

    # Recuperar template
    template_rubro = (data.get("template_rubro") or data.get("rubro") or "").strip()
    template = _get_template(template_rubro) if template_rubro else None
    if not template:
        # Traer el primero disponible
        template = _get_template("__any__")

    if not template:
        return jsonify({
            "error": "No hay templates disponibles en et_rubro_templates",
            "contacts_preview": [],
        }), 400

    # Renderizar preview del primer contacto (si hay)
    preview_html = None
    preview_subject = None
    if contacts:
        try:
            preview_subject, preview_html = render_email(
                template["body"], template["subject"], contacts[0]
            )
        except Exception as e:
            logger.warning(f"Preview render fail: {e}")
            preview_html = f"<p style='color:red'>Error renderizando: {str(e)[:200]}</p>"

    return jsonify({
        "total_match":      total_available,
        "template_rubro":   template.get("rubro"),
        "template_subject": template.get("subject"),
        "preview_first":    {
            "contact":  contacts[0] if contacts else None,
            "subject":  preview_subject,
            "html":     preview_html,
        },
        "contacts_preview": [
            {"email": c.get("email"), "business_name": c.get("business_name"),
             "rubro": c.get("rubro"), "comuna": c.get("comuna")}
            for c in contacts[:25]
        ],
        "max_per_batch": MAX_DRAFTS_PER_REQUEST,
    })


@bp.post("/generate")
@login_required
def generate():
    """
    Crea el batch y llama al Apps Script para generar drafts.

    Body: { name, rubro, comuna, estado, limit, template_rubro }
    """
    if not _owner_or_tl_required():
        return jsonify({"error": "Solo Owner/TL"}), 403

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name or len(name) > 120:
        return jsonify({"error": "name requerido (max 120 chars)"}), 400

    limit = min(int(data.get("limit") or 50), MAX_DRAFTS_PER_REQUEST)

    contacts = _filter_contacts(data, limit)
    if not contacts:
        return jsonify({"error": "No hay contactos que matcheen los filtros"}), 400

    template_rubro = (data.get("template_rubro") or data.get("rubro") or "").strip()
    template = _get_template(template_rubro) if template_rubro else _get_template("__any__")
    if not template:
        return jsonify({"error": "No hay template disponible"}), 400

    # Crear batch en DB (estado: pending)
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO email_draft_batches "
        "(name, created_by, rubro_filter, comuna_filter, estado_filter, "
        " template_rubro, subject_used, requested_count, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')",
        (
            name, current_user.id,
            (data.get("rubro") or "").strip() or None,
            (data.get("comuna") or "").strip() or None,
            (data.get("estado") or "").strip() or None,
            template.get("rubro"),
            template.get("subject"),
            len(contacts),
        ),
    )
    batch_id = cur.lastrowid

    # Registrar los contactos del batch
    for c in contacts:
        conn.execute(
            "INSERT INTO email_draft_batch_contacts "
            "(batch_id, contact_id, email, business_name, status) "
            "VALUES (?, ?, ?, ?, 'pending')",
            (batch_id, c.get("id"), (c.get("email") or "").strip().lower(),
             (c.get("business_name") or "").strip()),
        )
    conn.commit()

    # Renderizar y armar payload para Apps Script
    drafts_payload = []
    skipped = 0
    for c in contacts:
        email = (c.get("email") or "").strip()
        if not valid_email(email):
            skipped += 1
            continue
        try:
            subj, html = render_email(template["body"], template["subject"], c)
        except Exception as e:
            logger.warning(f"Render fail contact {c.get('id')}: {e}")
            skipped += 1
            continue
        drafts_payload.append({
            "to":       email,
            "subject":  subj,
            "htmlBody": html,
        })

    if not drafts_payload:
        conn.execute(
            "UPDATE email_draft_batches SET status='error', "
            "error_message=? WHERE id=?",
            ("Ningún contacto quedó válido tras renderizar", batch_id),
        )
        conn.commit(); conn.close()
        return jsonify({"error": "Ningún contacto quedó válido tras renderizar"}), 400

    # Llamar al Apps Script
    try:
        result = create_drafts(
            drafts_payload,
            sender_name=(current_user.name or "Juan Sebastián Pinto"),
        )
    except AppsScriptError as e:
        conn.execute(
            "UPDATE email_draft_batches SET status='error', "
            "error_message=? WHERE id=?",
            (str(e)[:400], batch_id),
        )
        conn.commit(); conn.close()
        logger.error(f"[drafts] Apps Script error batch={batch_id}: {e}")
        return jsonify({"error": f"Apps Script: {e}", "batch_id": batch_id}), 502

    # Persistir resultados
    created_count = int(result.get("created") or 0)
    failed_count  = int(result.get("failed") or 0)
    status = "created" if failed_count == 0 else ("partial" if created_count > 0 else "error")

    # Actualizar contactos individuales con draft_id
    for r in (result.get("results") or []):
        conn.execute(
            "UPDATE email_draft_batch_contacts SET draft_id=?, status='created' "
            "WHERE batch_id=? AND email=?",
            (r.get("draftId"), batch_id, (r.get("to") or "").lower()),
        )
    for e in (result.get("errors") or []):
        conn.execute(
            "UPDATE email_draft_batch_contacts SET status='error', error=? "
            "WHERE batch_id=? AND email=?",
            (str(e.get("error", ""))[:400], batch_id, (e.get("to") or "").lower()),
        )
    conn.execute(
        "UPDATE email_draft_batches SET "
        "created_count=?, failed_count=?, status=?, gmail_drafts_url=? "
        "WHERE id=?",
        (created_count, failed_count, status,
         result.get("gmail_drafts_url"), batch_id),
    )
    conn.commit(); conn.close()

    logger.info(
        f"[drafts] batch {batch_id} · user={current_user.id} · "
        f"created={created_count} failed={failed_count} skipped={skipped}"
    )

    return jsonify({
        "ok":               True,
        "batch_id":         batch_id,
        "created":          created_count,
        "failed":           failed_count,
        "skipped":          skipped,
        "status":           status,
        "gmail_drafts_url": result.get("gmail_drafts_url"),
    })


@bp.get("/batches")
@login_required
def list_batches():
    if not _owner_or_tl_required():
        return jsonify({"error": "Solo Owner/TL"}), 403
    conn = get_db()
    rows = conn.execute(
        "SELECT b.*, u.name as creator_name FROM email_draft_batches b "
        "LEFT JOIN users u ON u.id = b.created_by "
        "ORDER BY b.created_at DESC LIMIT 100"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@bp.get("/batches/<int:batch_id>")
@login_required
def batch_detail(batch_id: int):
    if not _owner_or_tl_required():
        return jsonify({"error": "Solo Owner/TL"}), 403
    conn = get_db()
    batch = conn.execute(
        "SELECT * FROM email_draft_batches WHERE id = ?",
        (batch_id,),
    ).fetchone()
    if not batch:
        conn.close()
        return jsonify({"error": "no encontrado"}), 404
    contacts = conn.execute(
        "SELECT * FROM email_draft_batch_contacts WHERE batch_id = ? "
        "ORDER BY id ASC",
        (batch_id,),
    ).fetchall()
    conn.close()
    return jsonify({
        "batch":    dict(batch),
        "contacts": [dict(c) for c in contacts],
    })
