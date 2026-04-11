"""
Base de datos SQLite con todos los modelos del sistema
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = 'data/prospecting.db'


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs('data', exist_ok=True)
    conn = get_db()
    c = conn.cursor()

    # ─── LEADS (prospectos) ────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            phone       TEXT NOT NULL UNIQUE,
            address     TEXT,
            comuna      TEXT NOT NULL,
            rubro       TEXT NOT NULL,
            source      TEXT DEFAULT 'google_maps',
            created_at  TEXT DEFAULT (datetime('now','localtime')),
            updated_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    ''')

    # ─── MENSAJES ENVIADOS ─────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id         INTEGER REFERENCES leads(id),
            phone           TEXT NOT NULL,
            message_type    TEXT DEFAULT 'prospecting',
            status          TEXT DEFAULT 'sent',
            sent_at         TEXT DEFAULT (datetime('now','localtime')),
            opened_at       TEXT,
            responded_at    TEXT,
            response_text   TEXT,
            campaign_id     INTEGER,
            rubro           TEXT,
            comuna          TEXT,
            image_path      TEXT
        )
    ''')

    # ─── ESTADOS DE LEADS ──────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS lead_status (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id     INTEGER UNIQUE REFERENCES leads(id),
            status      TEXT DEFAULT 'enviado',
            stage       TEXT DEFAULT 'prospecting',
            notes       TEXT,
            updated_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    ''')
    # status: enviado | abierto | interesado | quiere_reunion | cerrado | no_interesado | opt_out

    # ─── SELLERS (clientes activos) ────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS sellers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            contact_name    TEXT,
            phone           TEXT NOT NULL UNIQUE,
            pos_type        TEXT,
            comuna          TEXT,
            email           TEXT,
            notes           TEXT,
            active          INTEGER DEFAULT 1,
            created_at      TEXT DEFAULT (datetime('now','localtime')),
            last_msg_at     TEXT
        )
    ''')

    # ─── OPT-OUT LIST ─────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS opt_out (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            phone       TEXT NOT NULL UNIQUE,
            added_at    TEXT DEFAULT (datetime('now','localtime')),
            reason      TEXT
        )
    ''')

    # ─── CAMPAÑAS ─────────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            rubro           TEXT,
            comuna          TEXT,
            total_sent      INTEGER DEFAULT 0,
            total_opened    INTEGER DEFAULT 0,
            total_interested INTEGER DEFAULT 0,
            total_closed    INTEGER DEFAULT 0,
            sent_at         TEXT,
            status          TEXT DEFAULT 'scheduled'
        )
    ''')

    # ─── CONFIGURACIÓN ────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key     TEXT PRIMARY KEY,
            value   TEXT
        )
    ''')

    # Valores por defecto
    defaults = [
        ('daily_limit', '50'),
        ('min_delay_sec', '45'),
        ('max_delay_sec', '120'),
        ('prospecting_hour', '10'),
        ('fidelizacion_hour', '11'),
        ('whatsapp_session', 'mp_prospecting'),
        ('calendar_link', 'https://calendar.google.com/calendar/appointments/schedules/YOUR_LINK'),
        ('exec_name', 'Juan Sebastián Pinto'),
        ('exec_phone', '+56912345678'),
    ]
    c.executemany('INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)', defaults)

    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada correctamente")


# ─── HELPERS ──────────────────────────────────────────────────

def get_config(key):
    conn = get_db()
    row = conn.execute('SELECT value FROM config WHERE key = ?', (key,)).fetchone()
    conn.close()
    return row['value'] if row else None


def set_config(key, value):
    conn = get_db()
    conn.execute('INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()


def is_opt_out(phone):
    phone_clean = clean_phone(phone)
    conn = get_db()
    row = conn.execute('SELECT id FROM opt_out WHERE phone = ?', (phone_clean,)).fetchone()
    conn.close()
    return row is not None


def add_opt_out(phone, reason='usuario solicitó'):
    phone_clean = clean_phone(phone)
    conn = get_db()
    conn.execute(
        'INSERT OR IGNORE INTO opt_out (phone, reason) VALUES (?, ?)',
        (phone_clean, reason)
    )
    conn.commit()
    conn.close()


def clean_phone(phone: str) -> str:
    """Normaliza número chileno al formato 569XXXXXXXX"""
    digits = ''.join(filter(str.isdigit, phone))
    if digits.startswith('569') and len(digits) == 11:
        return digits
    if digits.startswith('9') and len(digits) == 9:
        return '56' + digits
    if digits.startswith('56') and len(digits) == 11:
        return digits
    return digits


def update_lead_status(phone, status, notes=None):
    conn = get_db()
    lead = conn.execute('SELECT id FROM leads WHERE phone = ?', (phone,)).fetchone()
    if lead:
        conn.execute('''
            INSERT INTO lead_status (lead_id, status, notes, updated_at)
            VALUES (?, ?, ?, datetime('now','localtime'))
            ON CONFLICT(lead_id) DO UPDATE SET
                status = excluded.status,
                notes = COALESCE(excluded.notes, lead_status.notes),
                updated_at = excluded.updated_at
        ''', (lead['id'], status, notes))
        conn.execute("UPDATE leads SET updated_at = datetime('now','localtime') WHERE id = ?", (lead['id'],))
    conn.commit()
    conn.close()
