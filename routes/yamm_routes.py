"""
Blueprint: /api/yamm
Integración YAMM (Yet Another Mail Merge) para campañas email vía Google Sheets.

Flujo:
  1. POST /preview      → preview de leads filtrados que se van a exportar
  2. POST /export       → crea campaña + devuelve CSV listo para Google Sheet + YAMM
  3. POST /import       → recibe CSV con resultados YAMM + actualiza métricas
  4. GET  /campaigns    → lista campañas
  5. GET  /campaigns/<id> → detalle + resultados
  6. DELETE /campaigns/<id> → archiva (no borra históricos)

Seguridad:
  - Solo Owner/TL pueden exportar (los CSV contienen PII)
  - Audit log de cada export: quién, cuándo, cuántos contactos
  - CSV de subida validado: tamaño máx 5MB, mime tipo, parseo defensivo
"""
from __future__ import annotations
import io
import logging
import time
from flask import Blueprint, jsonify, request, send_file
from flask_login import current_user, login_required

from database import get_db
from services.yamm_service import (
    build_csv_for_yamm,
    parse_yamm_results_csv,
)

logger = logging.getLogger(__name__)
bp = Blueprint("yamm", __name__, url_prefix="/api/yamm")


# ── HELPERS ───────────────────────────────────────────────────
def _owner_or_tl_required():
    """True si el rol está autorizado a operar YAMM."""
    return getattr(current_user, "role", "") in ("owner", "tl")


def _filter_clauses(filters: dict) -> tuple[str, list]:
    """
    Construye WHERE clause con parámetros bindeados (anti SQL injection).
    Acepta: rubro, comuna, estado, has_email (default true).
    """
    where = ["1=1"]
    params: list = []

    # Siempre exigimos email no vacío para YAMM
    where.append("email IS NOT NULL AND email != ''")

    if filters.get("rubro"):
        where.append("LOWER(rubro) = LOWER(?)")
        params.append(filters["rubro"].strip())

    if filters.get("comuna"):
        where.append("(LOWER(comuna) = LOWER(?) OR LOWER(ciudad) = LOWER(?))")
        params.append(filters["comuna"].strip())
        params.append(filters["comuna"].strip())

    if filters.get("estado"):
        # 'pendiente' = nunca enviado; 'todos' = sin filtro
        st = filters["estado"].strip().lower()
        if st == "pendiente":
            where.append("(campaign_status IS NULL OR campaign_status = 'pendiente')")
        elif st == "no_optout":
            where.append("(opt_out IS NULL OR opt_out = 0)")
        elif st != "todos":
            where.append("campaign_status = ?")
            params.append(st)
    else:
        # Default: excluir opt-outs siempre
        where.append("(opt_out IS NULL OR opt_out = 0)")

    return " AND ".join(where), params


# ── ENDPOINTS ─────────────────────────────────────────────────
@bp.post("/preview")
@login_required
def preview():
    """
    Preview de leads que matchearían los filtros. NO crea campaña.
    Body: { rubro, comuna, estado, limit }
    """
    if not _owner_or_tl_required():
        return jsonify({"error": "Solo Owner/TL"}), 403

    filters = request.get_json(silent=True) or {}
    limit   = min(int(filters.get("limit") or 100), 1000)

    where_clause, params = _filter_clauses(filters)
    conn = get_db()
    rows = conn.execute(
        f"SELECT id, business_name, email, rubro, comuna, ciudad, phone "
        f"FROM et_contacts WHERE {where_clause} "
        f"ORDER BY id ASC LIMIT ?",
        params + [limit],
    ).fetchall()

    total = conn.execute(
        f"SELECT COUNT(*) FROM et_contacts WHERE {where_clause}",
        params,
    ).fetchone()[0]
    conn.close()

    return jsonify({
        "total_match": total,
        "preview":     [dict(r) for r in rows[:25]],
        "preview_count": min(len(rows), 25),
    })


@bp.post("/export")
@login_required
def export():
    """
    Crea una campaña YAMM y devuelve el CSV listo para pegar en Google Sheets.

    Body: {
      name: "Campaña Pizzerías Las Condes - 2026-05",
      rubro, comuna, estado, limit, template_subject
    }
    """
    if not _owner_or_tl_required():
        return jsonify({"error": "Solo Owner/TL"}), 403

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name or len(name) > 120:
        return jsonify({"error": "name requerido (max 120 chars)"}), 400

    limit = min(int(data.get("limit") or 200), 2000)  # tope duro 2000
    template_subject = (data.get("template_subject") or "").strip()[:200]

    where_clause, params = _filter_clauses(data)
    conn = get_db()
    rows = conn.execute(
        f"SELECT id, business_name, email, rubro, comuna, ciudad, phone "
        f"FROM et_contacts WHERE {where_clause} "
        f"ORDER BY id ASC LIMIT ?",
        params + [limit],
    ).fetchall()

    if not rows:
        conn.close()
        return jsonify({"error": "No hay leads que matcheen los filtros"}), 400

    contacts = [dict(r) for r in rows]

    # Crear la campaña en DB
    cur = conn.execute(
        "INSERT INTO yamm_campaigns "
        "(name, created_by, rubro_filter, comuna_filter, estado_filter, "
        " contact_count, template_subject, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'exportada')",
        (
            name,
            current_user.id,
            (data.get("rubro") or "").strip() or None,
            (data.get("comuna") or "").strip() or None,
            (data.get("estado") or "").strip() or None,
            len(contacts),
            template_subject or None,
        ),
    )
    campaign_id = cur.lastrowid

    # Snapshot de los contactos en yamm_campaign_contacts
    for c in contacts:
        conn.execute(
            "INSERT OR IGNORE INTO yamm_campaign_contacts "
            "(campaign_id, contact_id, email, business_name, rubro, comuna) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                campaign_id,
                c.get("id"),
                (c.get("email") or "").strip().lower(),
                (c.get("business_name") or "").strip(),
                (c.get("rubro") or "").strip(),
                (c.get("comuna") or c.get("ciudad") or "").strip(),
            ),
        )
    conn.commit()
    conn.close()

    # Generar CSV
    csv_content = build_csv_for_yamm(contacts, campaign_id)

    # Audit log
    logger.info(
        f"[YAMM] EXPORT campaign={campaign_id} user={current_user.id} "
        f"count={len(contacts)} name='{name[:50]}'"
    )

    # Devolver como descarga
    buffer = io.BytesIO(csv_content.encode("utf-8"))
    filename = f"yamm_campaign_{campaign_id}_{int(time.time())}.csv"
    return send_file(
        buffer,
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name=filename,
    )


@bp.post("/campaigns/<int:campaign_id>/import")
@login_required
def import_results(campaign_id: int):
    """
    Recibe un CSV exportado desde el Sheet (post-envío YAMM) y actualiza
    los resultados de cada contacto en la campaña.

    Multipart form-data:
      file: el CSV exportado del Google Sheet
    """
    if not _owner_or_tl_required():
        return jsonify({"error": "Solo Owner/TL"}), 403

    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "Archivo requerido (campo 'file')"}), 400

    # Validación de tamaño · evita DoS por upload masivo (CWE-400)
    f.seek(0, 2)
    size = f.tell()
    f.seek(0)
    if size > 5 * 1024 * 1024:
        return jsonify({"error": "Archivo >5MB no soportado"}), 400
    if size == 0:
        return jsonify({"error": "Archivo vacío"}), 400

    # Validación tipo (defensiva · el contenido ya se valida por parser)
    if not (f.filename.lower().endswith(".csv") or f.filename.lower().endswith(".xlsx")):
        return jsonify({"error": "Solo .csv o .xlsx"}), 400

    # Decodificar como UTF-8 con fallback latin-1
    raw = f.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            content = raw.decode("latin-1")
        except Exception:
            return jsonify({"error": "Encoding no soportado"}), 400

    # Verificar que la campaña exista
    conn = get_db()
    camp = conn.execute(
        "SELECT id, status FROM yamm_campaigns WHERE id = ?",
        (campaign_id,),
    ).fetchone()
    if not camp:
        conn.close()
        return jsonify({"error": "Campaña no encontrada"}), 404

    try:
        results = parse_yamm_results_csv(content)
    except ValueError as e:
        conn.close()
        return jsonify({"error": f"CSV inválido: {e}"}), 400

    # Actualizar yamm_campaign_contacts + et_contacts en transacción
    updated = 0
    bounced_count = 0
    opened_count = 0
    replied_count = 0
    for r in results:
        # Solo actualizamos contactos que pertenecen a esta campaña
        cid = r.get("contact_id")
        if not cid:
            continue
        cur = conn.execute(
            "UPDATE yamm_campaign_contacts SET "
            "merge_status = ?, sent_at = ?, opened_at = ?, clicked_at = ?, "
            "replied_at = ?, bounced = ? "
            "WHERE campaign_id = ? AND contact_id = ?",
            (
                r["merge_status"], r["sent_at"], r["opened_at"],
                r["clicked_at"], r["replied_at"], r["bounced"],
                campaign_id, cid,
            ),
        )
        if cur.rowcount > 0:
            updated += 1

        # Propagar a et_contacts (métricas globales del dashboard)
        if r["opened_at"]:
            conn.execute(
                "UPDATE et_contacts SET email_opened_at = COALESCE(email_opened_at, ?) "
                "WHERE id = ?",
                (r["opened_at"], cid),
            )
            opened_count += 1
        if r["bounced"]:
            conn.execute(
                "UPDATE et_contacts SET email_bounced = 1 WHERE id = ?",
                (cid,),
            )
            bounced_count += 1
        if r["replied_at"]:
            conn.execute(
                "UPDATE et_contacts SET email_replied = 1 WHERE id = ?",
                (cid,),
            )
            replied_count += 1

    # Marcar campaña como enviada
    conn.execute(
        "UPDATE yamm_campaigns SET status = 'enviada', "
        "results_imported_at = datetime('now', 'localtime') WHERE id = ?",
        (campaign_id,),
    )
    conn.commit()
    conn.close()

    logger.info(
        f"[YAMM] IMPORT campaign={campaign_id} user={current_user.id} "
        f"updated={updated} opened={opened_count} "
        f"replied={replied_count} bounced={bounced_count}"
    )

    return jsonify({
        "ok":      True,
        "updated": updated,
        "stats":   {
            "opened":  opened_count,
            "replied": replied_count,
            "bounced": bounced_count,
            "total_in_csv": len(results),
        },
    })


@bp.get("/campaigns")
@login_required
def list_campaigns():
    """Lista todas las campañas YAMM."""
    if not _owner_or_tl_required():
        return jsonify({"error": "Solo Owner/TL"}), 403

    conn = get_db()
    rows = conn.execute(
        "SELECT c.*, u.name as creator_name "
        "FROM yamm_campaigns c "
        "LEFT JOIN users u ON u.id = c.created_by "
        "ORDER BY c.created_at DESC LIMIT 200"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@bp.get("/campaigns/<int:campaign_id>")
@login_required
def campaign_detail(campaign_id: int):
    """Detalle de una campaña + resultados por contacto."""
    if not _owner_or_tl_required():
        return jsonify({"error": "Solo Owner/TL"}), 403

    conn = get_db()
    camp = conn.execute(
        "SELECT * FROM yamm_campaigns WHERE id = ?",
        (campaign_id,),
    ).fetchone()
    if not camp:
        conn.close()
        return jsonify({"error": "no encontrado"}), 404

    contacts = conn.execute(
        "SELECT * FROM yamm_campaign_contacts WHERE campaign_id = ? "
        "ORDER BY id ASC",
        (campaign_id,),
    ).fetchall()

    stats = conn.execute(
        "SELECT "
        "SUM(CASE WHEN merge_status='SENT' THEN 1 ELSE 0 END)     AS sent, "
        "SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END)   AS opened, "
        "SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END)  AS clicked, "
        "SUM(CASE WHEN replied_at IS NOT NULL THEN 1 ELSE 0 END)  AS replied, "
        "SUM(CASE WHEN bounced=1 THEN 1 ELSE 0 END)               AS bounced "
        "FROM yamm_campaign_contacts WHERE campaign_id = ?",
        (campaign_id,),
    ).fetchone()
    conn.close()

    return jsonify({
        "campaign": dict(camp),
        "contacts": [dict(c) for c in contacts],
        "stats":    dict(stats) if stats else {},
    })


@bp.delete("/campaigns/<int:campaign_id>")
@login_required
def archive_campaign(campaign_id: int):
    """Archiva la campaña (no borra datos · solo cambia status)."""
    if not _owner_or_tl_required():
        return jsonify({"error": "Solo Owner/TL"}), 403

    conn = get_db()
    cur = conn.execute(
        "UPDATE yamm_campaigns SET status = 'archivada' WHERE id = ?",
        (campaign_id,),
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return jsonify({"error": "no encontrado"}), 404
    logger.info(f"[YAMM] ARCHIVE campaign={campaign_id} user={current_user.id}")
    return jsonify({"ok": True})
