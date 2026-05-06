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
            updated_at  TEXT DEFAULT (datetime('now','localtime')),
            assigned_to INTEGER,
            assigned_at TEXT,
            assigned_by INTEGER
        )
    ''')
    # Migración no-destructiva: si la tabla ya existía sin las columnas nuevas, agregarlas
    for col, decl in [
        ('assigned_to', 'INTEGER'),
        ('assigned_at', 'TEXT'),
        ('assigned_by', 'INTEGER'),
    ]:
        try:
            c.execute(f'ALTER TABLE leads ADD COLUMN {col} {decl}')
        except sqlite3.OperationalError:
            pass  # ya existe

    c.execute('CREATE INDEX IF NOT EXISTS idx_leads_assigned_to ON leads(assigned_to)')

    # ─── USUARIOS (TL y Sales) ─────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            email           TEXT NOT NULL UNIQUE,
            username        TEXT NOT NULL UNIQUE,
            password_hash   TEXT NOT NULL,
            role            TEXT,                            -- 'tl' | 'sales' | NULL=pending
            name            TEXT,
            evolution_instance TEXT,                         -- nombre de instancia Evolution API
            whatsapp_number TEXT,                            -- numero del Sales (informativo)
            fast_local_url  TEXT,                            -- URL del tunnel del Sales para Fast
            fast_local_token TEXT,                           -- token compartido con su servidor local
            smtp_user       TEXT,                            -- email del Sales para SMTP
            smtp_pass_enc   TEXT,                            -- App password (encriptado)
            status          TEXT DEFAULT 'pending'           -- 'pending' | 'active' | 'disabled'
                            CHECK(status IN ('pending','active','disabled')),
            password_changed INTEGER DEFAULT 0,              -- 0 hasta que cambie su password inicial
            created_at      TEXT DEFAULT (datetime('now','localtime')),
            last_login      TEXT,
            failed_logins   INTEGER DEFAULT 0,               -- contador para rate-limit por usuario
            locked_until    TEXT                             -- bloqueo por intentos fallidos
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)')

    # ─── LOG DE ASIGNACIONES (auditoría) ───────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS lead_assignments_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id         INTEGER NOT NULL,
            from_user_id    INTEGER,                         -- NULL si es asignación inicial
            to_user_id      INTEGER NOT NULL,
            assigned_by     INTEGER NOT NULL,
            reason          TEXT,                            -- obligatorio en reasignaciones
            assigned_at     TEXT DEFAULT (datetime('now','localtime'))
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_assign_log_lead ON lead_assignments_log(lead_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_assign_log_to ON lead_assignments_log(to_user_id)')

    # ─── LOG DE ACCESO TL A LEADS (auditoría de coaching) ──────
    # Cuando el TL abre un lead específico, queda registrado.
    c.execute('''
        CREATE TABLE IF NOT EXISTS tl_lead_access_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,                   -- TL que ingresó
            lead_id     INTEGER NOT NULL,
            accessed_at TEXT DEFAULT (datetime('now','localtime')),
            view_type   TEXT                                -- 'detail' | 'whatsapp_log' | 'metrics'
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_tl_access_lead ON tl_lead_access_log(lead_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_tl_access_user ON tl_lead_access_log(user_id)')

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
            image_path      TEXT,
            error_detail    TEXT
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
        ('outscraper_monthly_budget_usd', '10'),
        ('outscraper_credits_per_usd',    '500'),
    ]
    c.executemany('INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)', defaults)

    # ─── EMAIL TOOL TABLES ────────────────────────────────────

    c.execute('''
        CREATE TABLE IF NOT EXISTS et_contacts (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name       TEXT,
            email               TEXT,
            phone               TEXT,
            website             TEXT,
            rubro               TEXT,
            ciudad              TEXT,
            comuna              TEXT,
            source_query        TEXT,
            created_at          TEXT,
            campaign_status     TEXT DEFAULT 'pendiente',
            estado_interes      TEXT DEFAULT 'pendiente',
            notas               TEXT,
            proximo_seguimiento TEXT,
            reunion_fecha       TEXT,
            seguimiento_count   INTEGER DEFAULT 0,
            last_followup_at    TEXT,
            fecha_envio         TEXT
        )
    ''')

    # Migrar columnas si la tabla ya existía sin ellas
    _add_col(c, 'et_contacts', 'estado_interes',      "TEXT DEFAULT 'pendiente'")
    _add_col(c, 'et_rubro_templates', 'pdf_path', 'TEXT')
    _add_col(c, 'et_contacts', 'opt_out',             'INTEGER DEFAULT 0')
    _add_col(c, 'et_contacts', 'opt_out_token',       'TEXT')
    _add_col(c, 'et_contacts', 'notas',               'TEXT')
    _add_col(c, 'et_contacts', 'proximo_seguimiento', 'TEXT')
    _add_col(c, 'et_contacts', 'reunion_fecha',        'TEXT')
    _add_col(c, 'et_contacts', 'seguimiento_count',   'INTEGER DEFAULT 0')
    _add_col(c, 'et_contacts', 'last_followup_at',    'TEXT')
    _add_col(c, 'et_contacts', 'fecha_envio',         'TEXT')
    _add_col(c, 'et_contacts', 'comuna',              'TEXT')
    _add_col(c, 'et_seguimientos', 'batch_id',        'INTEGER')
    # Prospects: unificación email → gestión CRM
    _add_col(c, 'prospects', 'email',         'TEXT')
    _add_col(c, 'prospects', 'et_contact_id', 'INTEGER')
    _add_col(c, 'prospects', 'source',        "TEXT DEFAULT 'whatsapp'")
    _add_col(c, 'prospects', 'direccion',     'TEXT')

    c.execute('''
        CREATE TABLE IF NOT EXISTS et_campaigns (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT,
            subject       TEXT,
            body          TEXT,
            rubro         TEXT,
            schedule_time TEXT,
            status        TEXT DEFAULT 'borrador',
            created_at    TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS et_sends (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            contact_id  INTEGER,
            sent_at     TEXT,
            status      TEXT DEFAULT 'pendiente',
            opened      INTEGER DEFAULT 0,
            replied     INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS et_seguimientos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id  INTEGER REFERENCES et_contacts(id),
            tipo        TEXT DEFAULT 'email',
            fecha       TEXT,
            notas       TEXT,
            resultado   TEXT DEFAULT 'sin_respuesta',
            batch_id    INTEGER
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS et_campaign_batches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id      TEXT,
            fecha       TEXT,
            rubro       TEXT,
            comunas     TEXT,
            total_sent  INTEGER DEFAULT 0,
            total_err   INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS et_reuniones (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id  INTEGER REFERENCES et_contacts(id),
            fecha       TEXT NOT NULL,
            hora        TEXT,
            lugar       TEXT,
            notas       TEXT,
            estado      TEXT DEFAULT 'pendiente',
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS et_rubro_templates (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            rubro      TEXT UNIQUE,
            subject    TEXT,
            body       TEXT,
            updated_at TEXT
        )
    ''')

    _seed_templates(c)

    # ─── JOB RUNS — historial de ejecuciones de jobs programados ──
    c.execute('''
        CREATE TABLE IF NOT EXISTS job_runs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id       TEXT    NOT NULL,
            started_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            finished_at  TEXT,
            status       TEXT    NOT NULL DEFAULT 'running',
            result_count INTEGER DEFAULT 0,
            error        TEXT
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_job_runs_job_date ON job_runs(job_id, started_at)')

    # ─── OUTSCRAPER QUERIES — historial de búsquedas manuales ─────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS et_outscraper_queries (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            query        TEXT NOT NULL,
            rubro        TEXT,
            comuna       TEXT,
            limit_req    INTEGER DEFAULT 10,
            total_found  INTEGER DEFAULT 0,
            with_email   INTEGER DEFAULT 0,
            credits_est  INTEGER DEFAULT 0,
            source       TEXT DEFAULT 'manual',
            results_json TEXT,
            created_at   TEXT DEFAULT (datetime('now','localtime'))
        )
    ''')

    # ─── WHATSAPP — mensajes Evolution API ────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS wa_messages (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id       INTEGER REFERENCES leads(id),
            et_contact_id INTEGER REFERENCES et_contacts(id),
            phone         TEXT NOT NULL,
            message_type  TEXT DEFAULT 'prospecting',
            message_text  TEXT,
            status        TEXT DEFAULT 'sent',
            wa_message_id TEXT,
            sent_at       TEXT DEFAULT (datetime('now','localtime')),
            delivered_at  TEXT,
            read_at       TEXT,
            replied_at    TEXT,
            reply_text    TEXT,
            rubro         TEXT,
            comuna        TEXT,
            campaign_id   INTEGER,
            source        TEXT DEFAULT 'evolution'
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_wa_messages_phone ON wa_messages(phone)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_wa_messages_sent  ON wa_messages(sent_at)')

    # ─── WHATSAPP — conversaciones entrantes ──────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS wa_incoming (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            phone         TEXT NOT NULL,
            message_id    TEXT UNIQUE,
            message_text  TEXT,
            media_url     TEXT,
            received_at   TEXT DEFAULT (datetime('now','localtime')),
            lead_id       INTEGER REFERENCES leads(id),
            et_contact_id INTEGER REFERENCES et_contacts(id),
            processed     INTEGER DEFAULT 0
        )
    ''')

    # Configuración por defecto para Evolution API
    wa_defaults = [
        ('evolution_api_url',      'http://localhost:8080'),
        ('evolution_api_key',      ''),
        ('evolution_instance',     'mp_prospecting'),
        ('wa_daily_limit',         '150'),
        ('wa_delay_min_sec',       '30'),
        ('wa_delay_max_sec',       '60'),
        ('wa_followup_days',       '3'),
        ('wa_followup_enabled',    '1'),
    ]
    c.executemany('INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)', wa_defaults)

    # Migraciones para tablas WA existentes
    _add_col(c, 'wa_messages', 'et_contact_id', 'INTEGER')
    _add_col(c, 'wa_messages', 'reply_text',    'TEXT')
    _add_col(c, 'wa_messages', 'source',        "TEXT DEFAULT 'evolution'")

    # Migración: detalle de error en mensajes WA
    _add_col(c, 'messages', 'error_detail', 'TEXT')

    conn.commit()
    conn.close()
    print("[OK] Base de datos inicializada correctamente")


import contextlib as _ctx

@_ctx.contextmanager
def job_run(job_id: str):
    """
    Context manager para registrar la ejecución de un job en job_runs.
    Uso:
        with job_run('auto_scraping') as run:
            resultado = hacer_algo()
            run['count'] = resultado
    """
    conn = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cur = conn.execute(
        'INSERT INTO job_runs (job_id, started_at, status) VALUES (?, ?, ?)',
        (job_id, now, 'running')
    )
    run_id = cur.lastrowid
    conn.commit()
    conn.close()

    meta = {'count': 0}
    try:
        yield meta
        fin = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn2 = get_db()
        conn2.execute(
            'UPDATE job_runs SET status=?, finished_at=?, result_count=? WHERE id=?',
            ('done', fin, meta['count'], run_id)
        )
        conn2.commit()
        conn2.close()
    except Exception as exc:
        fin = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn2 = get_db()
        conn2.execute(
            'UPDATE job_runs SET status=?, finished_at=?, error=? WHERE id=?',
            ('error', fin, str(exc)[:500], run_id)
        )
        conn2.commit()
        conn2.close()
        raise


def _add_col(cursor, table, col, col_def):
    """Agrega columna si no existe."""
    try:
        cursor.execute(f'ALTER TABLE {table} ADD COLUMN {col} {col_def}')
    except Exception:
        pass


def _seed_templates(c):
    """Inserta templates de email por rubro si no existen."""
    templates = [
        ('cafetería', '¿Tu cafetería ya acepta todos los medios de pago?',
         '''Hola {nombre},

Te escribo desde MercadoPago para contarte cómo podemos ayudar a tu cafetería a vender más.

Con el Smart Point de MercadoPago puedes:
✓ Aceptar tarjetas de crédito y débito (Visa, Mastercard, Redcompra)
✓ Cobrar vales de alimentación Edenred, Pluxee y Junaeb directamente en el equipo
✓ Integrar con Toteat o Resto para gestionar tu caja de forma eficiente
✓ Crear cuentas colaboradores para que cada trabajador tenga su perfil

Sin costo de arriendo mensual y con depósito en tu cuenta el mismo día.

¿Te interesa saber más? Me encantaría mostrarte cómo funciona.

Saludos,
Juan Sebastián Pinto
Ejecutivo MercadoPago'''),

        ('pastelería', '¿Tu pastelería acepta todos los medios de pago?',
         '''Hola {nombre},

Te escribo desde MercadoPago para ayudarte a modernizar los cobros de tu pastelería.

Con el Smart Point de MercadoPago puedes:
✓ Aceptar tarjetas de crédito, débito y prepago
✓ Cobrar vales Edenred, Pluxee y Junaeb sin complicaciones
✓ Gestionar pedidos y caja con integración a Toteat o Resto
✓ Cuentas colaboradores con perfil individual para tu equipo

Sin mensualidad fija y con liquidación inmediata.

¿Conversamos esta semana?

Saludos,
Juan Sebastián Pinto
Ejecutivo MercadoPago'''),

        ('sushi', '¿Tu restaurante de sushi optimiza sus cobros?',
         '''Hola {nombre},

Desde MercadoPago quiero presentarte una solución que se adapta perfectamente a tu restaurante.

Con el Smart Point puedes:
✓ Aceptar todos los medios de pago (crédito, débito, prepago, QR)
✓ Procesar vales de alimentación Edenred, Pluxee y Junaeb
✓ Integrarte con Toteat, Resto u otras plataformas de delivery
✓ Asignar cuentas colaboradores a cada mozo

Sin costo fijo mensual.

¿Te cuento más detalles?

Saludos,
Juan Sebastián Pinto
Ejecutivo MercadoPago'''),

        ('emporio', 'Moderniza los cobros de tu emporio con MercadoPago',
         '''Hola {nombre},

Te contacto desde MercadoPago para contarte cómo podemos simplificar los cobros de tu emporio.

Con el Smart Point puedes:
✓ Aceptar tarjetas, QR y todos los medios de pago
✓ Cobrar vales de alimentación Edenred, Pluxee y Junaeb
✓ Cuentas colaboradores para cada trabajador
✓ Ver tus ventas en tiempo real desde el celular

Sin costo de arriendo.

¿Tienes 10 minutos para una llamada esta semana?

Saludos,
Juan Sebastián Pinto
Ejecutivo MercadoPago'''),

        ('clínica dental', 'Ofrece cuotas sin interés en tu clínica dental',
         '''Hola {nombre},

Desde MercadoPago quiero presentarte una solución que puede aumentar la conversión en tu clínica.

Con el Smart Point puedes:
✓ Ofrecer cuotas sin interés a tus pacientes en tratamientos de alto valor
✓ Aceptar todos los medios de pago (Visa, Mastercard, débito, QR)
✓ Cuentas colaboradores para cada profesional de la clínica
✓ Liquidación inmediata en tu cuenta

Los pacientes toman decisiones más fácilmente cuando pueden pagar en cuotas.

¿Conversamos esta semana?

Saludos,
Juan Sebastián Pinto
Ejecutivo MercadoPago'''),

        ('pizzería', '¿Tu pizzería acepta todos los medios de pago?',
         '''Hola {nombre},

Desde MercadoPago quiero mostrarte cómo podemos ayudar a tu pizzería a no perder ninguna venta.

Con el Smart Point puedes:
✓ Aceptar tarjetas, QR y vales de alimentación Edenred/Pluxee/Junaeb
✓ Integrar con Toteat, Resto u otros sistemas de delivery
✓ Cuentas colaboradores para tu equipo
✓ Cobrar en terreno o en mostrador

Sin mensualidad fija.

¿Te interesa conocer más?

Saludos,
Juan Sebastián Pinto
Ejecutivo MercadoPago'''),

        ('librería', 'Moderniza los cobros de tu librería',
         '''Hola {nombre},

Desde MercadoPago me comunico para contarte cómo podemos facilitar los cobros en tu librería.

Con el Smart Point puedes:
✓ Aceptar tarjetas de crédito, débito y prepago
✓ Cobrar con QR desde el celular del cliente
✓ Ver el historial de ventas en tiempo real
✓ Cuentas colaboradores para cada vendedor

Sin costo de arriendo mensual.

¿Tienes unos minutos para conocer más?

Saludos,
Juan Sebastián Pinto
Ejecutivo MercadoPago'''),

        ('veterinaria', 'Ofrece cuotas sin interés en tu veterinaria',
         '''Hola {nombre},

Desde MercadoPago quiero presentarte una solución que puede hacer la diferencia en tu veterinaria.

Con el Smart Point puedes:
✓ Ofrecer cuotas sin interés para procedimientos y cirugías de mayor valor
✓ Aceptar todos los medios de pago
✓ Cuentas colaboradores para veterinarios y recepción
✓ Liquidación rápida en tu cuenta

Cuando los dueños de mascotas pueden pagar en cuotas, deciden más rápido.

¿Conversamos esta semana?

Saludos,
Juan Sebastián Pinto
Ejecutivo MercadoPago'''),

        ('florería', 'Acepta más medios de pago en tu florería',
         '''Hola {nombre},

Desde MercadoPago quiero mostrarte cómo podemos ayudar a tu florería a no perder ventas por falta de pago.

Con el Smart Point puedes:
✓ Aceptar tarjetas de crédito, débito, QR y prepago
✓ Cobrar sin efectivo en eventos y entregas a domicilio
✓ Ver tus ventas en tiempo real
✓ Sin costo de arriendo mensual

¿Te interesa saber más?

Saludos,
Juan Sebastián Pinto
Ejecutivo MercadoPago'''),

        ('oftalmología', 'Ofrece cuotas sin interés en tu centro de oftalmología',
         '''Hola {nombre},

Desde MercadoPago quiero presentarte una solución que puede aumentar tu tasa de cierre.

Con el Smart Point puedes:
✓ Ofrecer cuotas sin interés para lentes, cirugías y tratamientos de alto valor
✓ Aceptar todos los medios de pago
✓ Cuentas colaboradores para médicos y recepción
✓ Liquidación el mismo día

Los pacientes toman decisiones más fácilmente cuando tienen la opción de cuotas.

¿Conversamos esta semana?

Saludos,
Juan Sebastián Pinto
Ejecutivo MercadoPago'''),

        ('tienda de muebles', 'Ofrece cuotas sin interés en tu tienda de muebles',
         '''Hola {nombre},

Desde MercadoPago quiero presentarte algo que puede hacer crecer las ventas de tu tienda.

Con el Smart Point puedes:
✓ Ofrecer cuotas sin interés para compras de mayor valor
✓ Aceptar todos los medios de pago (débito, crédito, QR)
✓ Cuentas colaboradores para tu equipo de ventas
✓ Sin costo de arriendo mensual

Cuando el cliente puede pagar en cuotas, el ticket de compra sube.

¿Te cuento más detalles?

Saludos,
Juan Sebastián Pinto
Ejecutivo MercadoPago'''),

        ('lubricentro', 'Simplifica los cobros en tu lubricentro',
         '''Hola {nombre},

Desde MercadoPago quiero mostrarte cómo podemos facilitar los cobros en tu lubricentro.

Con el Smart Point puedes:
✓ Aceptar tarjetas de crédito, débito y QR
✓ Cobrar rápidamente en caja o en el mismo puesto de trabajo
✓ Cuentas colaboradores para tu equipo
✓ Sin mensualidad fija

¿Te interesa conocer más?

Saludos,
Juan Sebastián Pinto
Ejecutivo MercadoPago'''),

        ('frenos', 'Moderniza los cobros en tu taller de frenos',
         '''Hola {nombre},

Desde MercadoPago quiero presentarte una solución práctica para tu taller.

Con el Smart Point puedes:
✓ Aceptar tarjetas de crédito, débito y QR
✓ Cobrar directamente en el taller o en el mesón
✓ Cuentas colaboradores para cada mecánico o encargado
✓ Ver ventas en tiempo real

Sin costo de arriendo.

¿Conversamos esta semana?

Saludos,
Juan Sebastián Pinto
Ejecutivo MercadoPago'''),

        ('spa', 'Ofrece cuotas sin interés en tu spa o centro de wellness',
         '''Hola {nombre},

Desde MercadoPago quiero presentarte una solución perfecta para tu spa o centro de bienestar.

Con el Smart Point puedes:
✓ Ofrecer cuotas sin interés para tratamientos de mayor valor
✓ Aceptar todos los medios de pago
✓ Cuentas colaboradores para terapeuta y recepción
✓ Sin mensualidad fija

Tus clientes valoran la flexibilidad de pago.

¿Conversamos esta semana?

Saludos,
Juan Sebastián Pinto
Ejecutivo MercadoPago'''),
    ]
    c.executemany(
        '''INSERT OR IGNORE INTO et_rubro_templates (rubro, subject, body, updated_at)
           VALUES (?, ?, ?, datetime('now','localtime'))''',
        templates
    )


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


def update_lead_status(phone, status, notes=None, optout_motivo=None, contact_name=None, pos_type=None, email=None):
    conn = get_db()
    lead = conn.execute('SELECT id FROM leads WHERE phone = ?', (phone,)).fetchone()
    if lead:
        conn.execute('''
            INSERT INTO lead_status (lead_id, status, notes, updated_at, optout_motivo)
            VALUES (?, ?, ?, datetime('now','localtime'), ?)
            ON CONFLICT(lead_id) DO UPDATE SET
                status = excluded.status,
                notes = COALESCE(excluded.notes, lead_status.notes),
                updated_at = excluded.updated_at,
                optout_motivo = COALESCE(excluded.optout_motivo, lead_status.optout_motivo)
        ''', (lead['id'], status, notes, optout_motivo))
        conn.execute("UPDATE leads SET updated_at = datetime('now','localtime') WHERE id = ?", (lead['id'],))
    conn.commit()
    conn.close()
