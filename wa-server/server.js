// PRIMER LOG — si esto no aparece, el archivo no se ejecuta
process.stdout.write('[WA] === ARRANQUE === PID=' + process.pid + '\n');
process.stdout.write('[WA] Node ' + process.version + ' | CWD=' + process.cwd() + '\n');
process.stdout.write('[WA] __dirname=' + __dirname + '\n');

/**
 * wa-server: servidor HTTP local compatible con Evolution API.
 */

process.stdout.write('[WA] Cargando módulos...\n');
const express    = require('express');
process.stdout.write('[WA] express OK\n');
const { default: makeWASocket, DisconnectReason, useMultiFileAuthState, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
process.stdout.write('[WA] baileys OK\n');
const QRCode     = require('qrcode');
process.stdout.write('[WA] qrcode OK\n');
const pino       = require('pino');
const fs         = require('fs');
const path       = require('path');
const https      = require('https');
process.stdout.write('[WA] Todos los módulos cargados\n');

const app        = express();
app.use(express.json());

const PORT       = process.env.PORT || 8080;
const API_KEY    = process.env.WA_API_KEY || 'mp_secret_key';
const AUTH_DIR   = process.env.WA_AUTH_DIR || path.join(__dirname, 'auth_info');
const WEBHOOK_FILE = process.env.WA_WEBHOOK_FILE || path.join(__dirname, 'webhook_url.txt');
process.stdout.write('[WA] AUTH_DIR=' + AUTH_DIR + '\n');

let sock         = null;
let qrBase64     = null;
let connState    = 'close';  // close | connecting | open
let webhookUrl   = fs.existsSync(WEBHOOK_FILE) ? fs.readFileSync(WEBHOOK_FILE,'utf8').trim() : null;

const logger = pino({ level: 'silent' });

// ── Health check — ANTES del auth (Railway necesita respuesta 200) ──
app.get('/health', (req, res) => {
  res.json({ status: 'ok', state: connState, version: '1.0.0' });
});

// ── Auth middleware ──────────────────────────────────────────────
function checkApiKey(req, res, next) {
  const key = req.headers['apikey'] || req.headers['x-api-key'] || req.query.apikey;
  if (key !== API_KEY) return res.status(401).json({ error: 'Unauthorized' });
  next();
}
app.use(checkApiKey);

// ── Iniciar WhatsApp ─────────────────────────────────────────────
// Contador de reconexiones para backoff progresivo
let reconnectCount = 0;

async function startSock() {
  console.log('[WA] startSock() llamado — cargando auth...');
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  console.log('[WA] Auth cargado — obteniendo versión Baileys...');

  let version;
  try {
    const result = await fetchLatestBaileysVersion();
    version = result.version;
    console.log('[WA] Versión Baileys:', version);
  } catch (e) {
    version = [2, 3000, 1023767085];  // fallback versión conocida
    console.warn('[WA] fetchLatestBaileysVersion falló, usando fallback:', version, '—', e.message);
  }

  connState = 'connecting';
  qrBase64  = null;

  console.log('[WA] Creando socket...');
  sock = makeWASocket({
    version,
    auth: state,
    logger,
    printQRInTerminal: false,
    browser: ['Chrome (Linux)', '', ''],
    connectTimeoutMs: 120000,
    defaultQueryTimeoutMs: 60000,
    keepAliveIntervalMs: 25000,
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      qrBase64      = await QRCode.toDataURL(qr);
      connState     = 'connecting';
      reconnectCount = 0;           // reset al recibir QR nuevo
      console.log('[WA] QR listo para escanear — tienes 2 minutos');
      sendWebhook({ event: 'CONNECTION_UPDATE', data: { state: 'connecting' } });
    }

    if (connection === 'open') {
      connState      = 'open';
      qrBase64       = null;
      reconnectCount = 0;
      console.log('[WA] ✅ Conectado!');
      sendWebhook({ event: 'CONNECTION_UPDATE', data: { state: 'open' } });
    }

    if (connection === 'close') {
      connState = 'close';
      const code = lastDisconnect?.error?.output?.statusCode;
      console.log(`[WA] Desconectado (code=${code})`);
      sendWebhook({ event: 'CONNECTION_UPDATE', data: { state: 'close' } });

      if (code === DisconnectReason.loggedOut) {
        // Sesión invalidada por WhatsApp → borrar archivos (no el directorio: puede ser un volumen)
        console.log('[WA] Sesión cerrada remotamente. Limpiando archivos de auth...');
        try {
          if (fs.existsSync(AUTH_DIR)) {
            for (const f of fs.readdirSync(AUTH_DIR)) {
              fs.rmSync(path.join(AUTH_DIR, f), { recursive: true, force: true });
            }
          }
        } catch(e) { console.error('[WA] Error limpiando auth:', e.message); }
        reconnectCount = 0;
        setTimeout(startSock, 3000);
      } else {
        // Desconexión normal → backoff progresivo
        reconnectCount++;
        const delay = Math.min(5000 * reconnectCount, 60000);
        console.log(`[WA] Reintento ${reconnectCount} en ${delay/1000}s`);
        setTimeout(startSock, delay);
      }
    }
  });

  // Mensajes entrantes → webhook
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;
    for (const msg of messages) {
      if (msg.key.fromMe) continue;
      sendWebhook({ event: 'MESSAGES_UPSERT', data: { key: msg.key, message: msg.message } });
    }
  });

  // Actualizaciones de estado (delivery, read)
  sock.ev.on('message-receipt.update', updates => {
    sendWebhook({ event: 'MESSAGES_UPDATE', data: updates });
  });
}

// ── Webhook ──────────────────────────────────────────────────────
function sendWebhook(payload) {
  if (!webhookUrl) return;
  try {
    const body = Buffer.from(JSON.stringify(payload));
    const url  = new URL(webhookUrl);
    const opts = {
      hostname: url.hostname,
      port:     url.port || (url.protocol === 'https:' ? 443 : 80),
      path:     url.pathname,
      method:   'POST',
      headers:  { 'Content-Type':'application/json', 'Content-Length': body.length },
    };
    const req = (url.protocol === 'https:' ? https : require('http')).request(opts);
    req.on('error', () => {});
    req.write(body);
    req.end();
  } catch(e) {}
}

// ── Helpers ──────────────────────────────────────────────────────
function normalizeJid(phone) {
  const digits = phone.replace(/\D/g,'');
  const full   = digits.startsWith('56') ? digits : '56' + digits;
  return full + '@s.whatsapp.net';
}

// ══════════════════════════════════════════════════════════════════
// ENDPOINTS
// ══════════════════════════════════════════════════════════════════

// Estado de conexión
app.get('/instance/connectionState/:instance', (req, res) => {
  res.json({ instance: { state: connState } });
});

// QR code
app.get('/instance/connect/:instance', (req, res) => {
  if (connState === 'open') return res.json({ state: 'open', base64: null });
  if (qrBase64) return res.json({ base64: qrBase64, code: qrBase64 });
  res.json({ base64: null, message: 'QR no disponible aún. Reintenta en 5 segundos.' });
});

// Crear instancia (o reiniciar si ya existe)
app.post('/instance/create', async (req, res) => {
  if (sock) {
    try { sock.end(); } catch(e) {}
    sock = null;
  }
  await startSock();
  res.json({ instance: { instanceName: req.body.instanceName || 'mp_prospecting', state: connState } });
});

// Logout
app.delete('/instance/logout/:instance', async (req, res) => {
  try {
    if (sock) { await sock.logout(); sock = null; }
    if (fs.existsSync(AUTH_DIR)) {
      for (const f of fs.readdirSync(AUTH_DIR)) {
        fs.rmSync(path.join(AUTH_DIR, f), { recursive: true, force: true });
      }
    }
    connState = 'close';
    qrBase64  = null;
    res.json({ ok: true });
  } catch(e) {
    res.json({ ok: false, error: e.message });
  }
});

// Restart
app.put('/instance/restart/:instance', async (req, res) => {
  try {
    if (sock) { try { sock.end(); } catch(e) {} sock = null; }
    await startSock();
    res.json({ ok: true });
  } catch(e) {
    res.json({ ok: false, error: e.message });
  }
});

// Enviar texto
app.post('/message/sendText/:instance', async (req, res) => {
  if (connState !== 'open') return res.status(503).json({ ok: false, error: 'not_connected' });
  const { number, textMessage, options } = req.body;
  if (!number || !textMessage?.text) return res.status(400).json({ ok: false, error: 'number y textMessage.text requeridos' });

  try {
    const jid  = normalizeJid(number);
    const sent = await sock.sendMessage(jid, { text: textMessage.text });
    res.json({ key: sent.key, status: 'sent' });
  } catch(e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

// Enviar imagen con caption
app.post('/message/sendMedia/:instance', async (req, res) => {
  if (connState !== 'open') return res.status(503).json({ ok: false, error: 'not_connected' });
  const { number, mediaMessage } = req.body;
  if (!number) return res.status(400).json({ ok: false, error: 'number requerido' });

  try {
    const jid = normalizeJid(number);
    const msg = mediaMessage?.media
      ? { image: { url: mediaMessage.media }, caption: mediaMessage.caption || '' }
      : { text: mediaMessage?.caption || '' };
    const sent = await sock.sendMessage(jid, msg);
    res.json({ key: sent.key, status: 'sent' });
  } catch(e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

// Configurar webhook
app.post('/webhook/set/:instance', (req, res) => {
  const { url, enabled } = req.body;
  if (enabled && url) {
    webhookUrl = url;
    fs.writeFileSync(WEBHOOK_FILE, url, 'utf8');
    console.log(`[WA] Webhook configurado: ${url}`);
  } else {
    webhookUrl = null;
    if (fs.existsSync(WEBHOOK_FILE)) fs.unlinkSync(WEBHOOK_FILE);
  }
  res.json({ ok: true, webhook: webhookUrl });
});

// ══════════════════════════════════════════════════════════════════
// MANEJO DE ERRORES GLOBALES — evita que el proceso muera silenciosamente
// ══════════════════════════════════════════════════════════════════
process.on('uncaughtException', (err) => {
  console.error('[WA] uncaughtException:', err.message, err.stack);
});
process.on('unhandledRejection', (reason) => {
  console.error('[WA] unhandledRejection:', reason);
});

// ══════════════════════════════════════════════════════════════════
// ARRANQUE
// ══════════════════════════════════════════════════════════════════
process.stdout.write('[WA] Llamando app.listen en PORT=' + (process.env.PORT || 8080) + '\n');
app.listen(PORT, () => {
  console.log(`[WA Server] ✅ Corriendo en http://localhost:${PORT}`);
  console.log(`[WA Server] API Key: ${API_KEY}`);
  // Iniciar conexión WhatsApp automáticamente
  startSock().catch(e => console.error('[WA] Error iniciando:', e.message));

  // Auto-configurar webhook si está definido en env
  const autoWebhook = process.env.WA_WEBHOOK_URL;
  if (autoWebhook) {
    setTimeout(() => {
      webhookUrl = autoWebhook;
      fs.writeFileSync(WEBHOOK_FILE, autoWebhook, 'utf8');
      console.log(`[WA Server] Webhook auto-configurado: ${autoWebhook}`);
    }, 3000);
  }
});
