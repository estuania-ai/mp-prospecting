"""
Parser de exports de WhatsApp (.txt).

WhatsApp exporta cada chat con un formato tipo:
    [10/10/24, 09:30:15] Juan Sebastián: Hola! ¿Cómo estás?
    [10/10/24, 09:32:01] Cliente: Bien Juan, vi tu mensaje sobre MercadoPago
    [10/10/24, 09:32:45] Juan Sebastián: Genial. Te paso info...

Esta función toma ese .txt y extrae pares (cliente_msg → owner_response)
para entrenar el RAG.

El "owner" es el usuario logueado al exportar (el que recibe los mensajes
en su lado izquierdo en la app). El "cliente" es el otro participante.
"""
from __future__ import annotations
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Regex que captura líneas de formato WhatsApp:
# [DD/MM/YY, HH:MM:SS] Autor: mensaje
# o variantes con/sin segundos, AM/PM, fechas con guión, etc.
_LINE_RE = re.compile(
    r'^\[?(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}),?\s+'
    r'(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[ap]\.?m\.?)?)\]?\s*-?\s*'
    r'([^:]+?):\s*(.+)$',
    re.IGNORECASE
)

# Mensajes del sistema (no son conversación real)
_SYSTEM_HINTS = (
    'creó este grupo', 'unió usando', 'añadió a', 'cambió',
    'eliminó', 'salió del', 'cifrados de extremo', 'mensaje eliminado',
    '<archivo omitido>', '<media omitted>', 'imagen omitida',
)


def parse_whatsapp_export(text: str, owner_name_hint: str | None = None) -> list[dict]:
    """
    Parsea texto de export y retorna lista de mensajes:
        [ { 'date': str, 'time': str, 'author': str, 'text': str }, ... ]

    Mensajes multi-línea se concatenan (WhatsApp permite saltos en un mensaje).
    """
    if not text:
        return []
    messages = []
    current = None
    for raw_line in text.split('\n'):
        line = raw_line.rstrip('\r')
        # Eliminar caracteres de control LRM/RLM/embedded WhatsApp
        line = line.replace('‎', '').replace('‏', '').replace('‪', '').replace('‬', '')
        m = _LINE_RE.match(line)
        if m:
            if current:
                messages.append(current)
            date_s, time_s, author, text_s = m.groups()
            current = {
                'date':   date_s,
                'time':   time_s,
                'author': author.strip(),
                'text':   text_s.strip(),
            }
        else:
            # Continuación del mensaje anterior (multilinea)
            if current and line.strip():
                current['text'] += '\n' + line.strip()
    if current:
        messages.append(current)

    # Filtrar mensajes del sistema
    filtered = []
    for m in messages:
        low = m['text'].lower()
        if any(h in low for h in _SYSTEM_HINTS):
            continue
        if not m['text'].strip():
            continue
        filtered.append(m)
    return filtered


def detect_owner(messages: list[dict], hint: str | None = None) -> str | None:
    """
    Detecta cuál de los autores es el "owner" del bot (el que vamos a imitar).
    Si hay hint (ej. 'Juan Sebastián'), prioriza match con eso.
    Si no, asume el autor con más mensajes (suele ser el vendedor en chats outbound).
    """
    if not messages:
        return None
    counts = {}
    for m in messages:
        counts[m['author']] = counts.get(m['author'], 0) + 1
    if hint:
        h_low = hint.lower()
        for author in counts:
            if h_low in author.lower() or author.lower() in h_low:
                return author
    # Fallback: el más activo (suele ser quien vende)
    return max(counts.items(), key=lambda x: x[1])[0]


def parse_faq_document(text: str) -> list[dict]:
    """
    Parsea un documento de texto plano y extrae pares Q→A.

    Soporta 3 formatos (auto-detectados):

    Formato A — Q&A explícito (preferido):
        P: ¿Cuánto cobran de comisión?
        R: La comisión depende del tipo de tarjeta...

    Formato B — Markdown headings:
        ## ¿Cuánto cobran de comisión?
        La comisión depende del tipo de tarjeta...

    Formato C — Free-form (fallback):
        Se splittea en bloques separados por dobles saltos de línea.
        Primer renglón se asume como "tema/pregunta", resto como "respuesta".

    Returns: list of {'client_msg': str, 'owner_response': str}
    """
    if not text:
        return []
    pairs = []
    lines = text.split('\n')

    # ── Formato A: P:/R: o Q:/A: ────────────────────────────────
    # Junto pares P+R consecutivos, soporta multilínea en R hasta el próximo P.
    formato_qa = re.compile(r'^\s*(?:P|Q|Pregunta|Question|❓|🔸)\s*[:\-]\s*(.+)', re.IGNORECASE)
    formato_a  = re.compile(r'^\s*(?:R|A|Respuesta|Answer|✅|🔹)\s*[:\-]\s*(.+)', re.IGNORECASE)

    current_q = None
    current_a_lines: list[str] = []
    in_answer = False

    def flush_pair():
        nonlocal current_q, current_a_lines
        if current_q and current_a_lines:
            ans = '\n'.join(current_a_lines).strip()
            if len(current_q) >= 5 and len(ans) >= 10:
                pairs.append({'client_msg': current_q, 'owner_response': ans})
        current_q = None
        current_a_lines = []

    for line in lines:
        m_q = formato_qa.match(line)
        m_a = formato_a.match(line)
        if m_q:
            flush_pair()
            current_q = m_q.group(1).strip()
            in_answer = False
        elif m_a:
            current_a_lines = [m_a.group(1).strip()]
            in_answer = True
        elif in_answer and current_q:
            stripped = line.strip()
            if stripped:
                current_a_lines.append(stripped)
    flush_pair()

    if pairs:
        return pairs

    # ── Formato B: Markdown ## headings ─────────────────────────
    blocks = re.split(r'\n(?=##\s)', text)
    for block in blocks:
        m = re.match(r'^##\s+(.+?)\n(.+)', block, re.DOTALL)
        if m:
            q = m.group(1).strip().rstrip('?').rstrip('.') + '?'
            a = m.group(2).strip()
            if len(q) >= 5 and len(a) >= 10:
                pairs.append({'client_msg': q, 'owner_response': a})
    if pairs:
        return pairs

    # ── Formato C: free-form con chunking inteligente ──────────
    # Para PDFs, brochures, Excel, PPT donde el texto viene corrido o por
    # líneas sueltas. Estrategia:
    # 1. Si hay párrafos (split por doble newline): usar c/u como chunk
    # 2. Si el texto es 1 sola "línea" larga: chunkear por oraciones (300-500 chars c/u)
    # 3. Si vienen muchas líneas cortas: agrupar consecutivas en chunks
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

    # Si sólo hay 1 "párrafo" pero es texto largo (PDF mal extraído),
    # forzar chunking por longitud
    if len(paragraphs) <= 2 and len(text) > 600:
        paragraphs = _chunk_long_text(text)

    # Si hay muchos párrafos cortos (cada línea suelta), agrupar en chunks de ~400 chars
    if len(paragraphs) > 50:
        paragraphs = _group_short_lines(paragraphs)

    for para in paragraphs:
        # Limpieza básica: remover marcadores tipo "--- Página N ---" y duplicados
        para_clean = re.sub(r'---\s*Página\s+\d+\s*---', '', para).strip()
        if not para_clean or len(para_clean) < 30:
            continue
        first_line = para_clean.split('\n', 1)[0].strip()
        if len(first_line) < 200 and len(para_clean) > len(first_line) + 15:
            q = first_line
            a = para_clean
        else:
            # Sin título claro: usar primeras 100 chars como "pregunta" (referencia)
            q = first_line[:100] + ('...' if len(first_line) > 100 else '')
            a = para_clean
        # Thresholds más permisivos para PDFs/Excel
        if len(q) >= 5 and len(a) >= 25:
            pairs.append({'client_msg': q, 'owner_response': a[:2500]})
    return pairs


def _chunk_long_text(text: str, target_chars: int = 400) -> list[str]:
    """Divide texto largo en chunks de ~target_chars por oración."""
    # Splitear por oración (., !, ?, salto)
    sentences = re.split(r'(?<=[.!?])\s+|\n\n+', text)
    chunks = []
    current = []
    current_len = 0
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if current_len + len(s) > target_chars and current:
            chunks.append(' '.join(current))
            current = []
            current_len = 0
        current.append(s)
        current_len += len(s)
    if current:
        chunks.append(' '.join(current))
    return chunks


def _group_short_lines(lines: list[str], target_chars: int = 400) -> list[str]:
    """Agrupa líneas consecutivas hasta llegar a ~target_chars por chunk."""
    chunks = []
    current = []
    current_len = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if current_len + len(line) > target_chars and current:
            chunks.append('\n'.join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line)
    if current:
        chunks.append('\n'.join(current))
    return chunks


def extract_qa_pairs(messages: list[dict], owner: str) -> list[dict]:
    """
    Extrae pares (cliente → owner) consecutivos.

    Lógica:
    - Itera mensajes en orden cronológico.
    - Cuando hay un mensaje del cliente seguido (eventualmente) de uno del owner,
      lo guarda como par Q→A.
    - Mensajes consecutivos del mismo autor se concatenan (representan un mismo turno).

    Retorna lista de { 'client_msg': str, 'owner_response': str, 'context': str }
    donde context son los 3-5 turnos previos para preservar contexto.
    """
    if not messages or not owner:
        return []
    # Compactar: agrupar mensajes consecutivos del mismo autor en un solo "turno"
    turns = []
    for m in messages:
        if turns and turns[-1]['author'] == m['author']:
            turns[-1]['text'] += '\n' + m['text']
        else:
            turns.append({'author': m['author'], 'text': m['text']})

    pairs = []
    for i in range(1, len(turns)):
        prev = turns[i-1]
        curr = turns[i]
        if prev['author'] != owner and curr['author'] == owner:
            # Cliente preguntó, owner respondió
            ctx_start = max(0, i-5)
            ctx_lines = []
            for t in turns[ctx_start:i-1]:
                role = 'OWNER' if t['author'] == owner else 'CLIENTE'
                ctx_lines.append(f"{role}: {t['text']}")
            pairs.append({
                'client_msg':     prev['text'][:1000],
                'owner_response': curr['text'][:2000],
                'context':        '\n'.join(ctx_lines)[-1500:],
            })
    return pairs
