/**
 * MP Prospecting — Inbox Monitor via Google Apps Script
 * =====================================================
 * Pega este código en: script.google.com → Nuevo proyecto
 *
 * SETUP (5 minutos):
 *  1. Ve a https://script.google.com → "Nuevo proyecto"
 *  2. Pega TODO este código (reemplaza lo que hay)
 *  3. Cambia SHEET_ID por el ID de tu Google Sheet (creado abajo)
 *  4. Guarda (Ctrl+S)
 *  5. Ejecuta "setupSheet" una sola vez (botón ▶ con esa función seleccionada)
 *     → Esto crea las columnas en el Sheet
 *  6. Ve a Reloj (⏰ ícono izquierdo) → Añadir trigger:
 *     Función: checkInbox | Tipo: Basado en tiempo | Minutos: Cada 10 minutos
 *  7. Comparte el Sheet: Compartir → "Cualquiera con el enlace" → Lector
 *  8. Copia el ID del Sheet (la parte larga de la URL entre /d/ y /edit)
 *  9. En el servidor Flask, guarda ese ID en:
 *     data/gmail_sheet.json → {"sheet_id": "TU_ID_AQUI"}
 *
 * El script detecta automáticamente respuestas y rebotes de los últimos 3 días.
 */

// ── CONFIGURACIÓN ────────────────────────────────────────────────────────────
var SHEET_ID     = 'PEGA_AQUI_EL_ID_DE_TU_GOOGLE_SHEET';  // ← CAMBIA ESTO
var SHEET_NAME   = 'Inbox';
var DAYS_BACK    = 3;    // cuántos días hacia atrás revisar
var MAX_MESSAGES = 200;  // máximo de mensajes a procesar por ejecución

// Remitentes/asuntos que indican rebote
var BOUNCE_FROMS = [
  'mailer-daemon', 'postmaster', 'mail delivery subsystem',
  'delivery status notification', 'undeliverable'
];
var BOUNCE_SUBJECTS = [
  'delivery status notification', 'undeliverable', 'mail delivery failed',
  'returned mail', 'failure notice', 'delivery failure',
  'correo no entregado', 'mensaje no entregado'
];

// ── SETUP (ejecutar una sola vez) ─────────────────────────────────────────────
function setupSheet() {
  var ss    = SpreadsheetApp.openById(SHEET_ID);
  var sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(['timestamp', 'email', 'tipo', 'subject', 'snippet', 'message_id']);
    sheet.setFrozenRows(1);
    sheet.getRange('A1:F1').setFontWeight('bold');
  }
  Logger.log('Sheet configurado correctamente en: ' + ss.getUrl());
}

// ── LÓGICA PRINCIPAL ──────────────────────────────────────────────────────────
function checkInbox() {
  var ss    = SpreadsheetApp.openById(SHEET_ID);
  var sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    setupSheet();
    sheet = ss.getSheetByName(SHEET_NAME);
  }

  // Cargar IDs ya registrados para evitar duplicados
  var existingIds = {};
  var lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    var ids = sheet.getRange(2, 6, lastRow - 1, 1).getValues();
    ids.forEach(function(row) { if (row[0]) existingIds[row[0]] = true; });
  }

  var cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - DAYS_BACK);
  var query = 'in:inbox newer_than:' + DAYS_BACK + 'd';

  var threads = GmailApp.search(query, 0, 50);
  var newRows = [];

  threads.forEach(function(thread) {
    var messages = thread.getMessages();
    messages.forEach(function(msg) {
      if (msg.getDate() < cutoff) return;
      var msgId = msg.getId();
      if (existingIds[msgId]) return;  // ya procesado

      var from    = msg.getFrom().toLowerCase();
      var subject = msg.getSubject() || '';
      var snippet = msg.getPlainBody().substring(0, 250).replace(/\n/g, ' ');
      var subjectLower = subject.toLowerCase();
      var timestamp = Utilities.formatDate(msg.getDate(), 'America/Santiago', 'yyyy-MM-dd HH:mm:ss');

      // Detectar rebote
      var isBounce = BOUNCE_FROMS.some(function(b) { return from.indexOf(b) >= 0; }) ||
                     BOUNCE_SUBJECTS.some(function(b) { return subjectLower.indexOf(b) >= 0; });

      if (isBounce) {
        // Intentar extraer el email del destinatario original del cuerpo
        var body      = msg.getPlainBody();
        var emailMatch = body.match(/[\w._%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}/);
        var recipient  = emailMatch ? emailMatch[0].toLowerCase() : from;
        newRows.push([timestamp, recipient, 'bounce', subject, snippet, msgId]);
        return;
      }

      // Detectar respuesta: el remitente NO es nosotros mismos
      var myEmail = Session.getEffectiveUser().getEmail().toLowerCase();
      if (from.indexOf(myEmail) >= 0) return;  // mensaje enviado por nosotros

      // Es una respuesta de un contacto externo
      var emailMatch2 = from.match(/[\w._%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}/);
      var senderEmail = emailMatch2 ? emailMatch2[0] : from;

      newRows.push([timestamp, senderEmail, 'reply', subject, snippet, msgId]);
    });
  });

  if (newRows.length > 0) {
    sheet.getRange(sheet.getLastRow() + 1, 1, newRows.length, 6).setValues(newRows);
    Logger.log('Registradas ' + newRows.length + ' filas nuevas.');
  } else {
    Logger.log('Sin eventos nuevos.');
  }
}

// ── UTILIDAD: ver estado ──────────────────────────────────────────────────────
function showStatus() {
  var ss    = SpreadsheetApp.openById(SHEET_ID);
  var sheet = ss.getSheetByName(SHEET_NAME);
  var rows  = sheet ? sheet.getLastRow() - 1 : 0;
  Logger.log('Total filas en Sheet: ' + rows);
  Logger.log('URL Sheet: ' + ss.getUrl());
}
