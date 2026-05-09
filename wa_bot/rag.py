"""
RAG (Retrieval Augmented Generation) para el Bot WhatsApp.

Flujo:
1. Indexar: cuando el Owner sube un .txt de WhatsApp, se parsean los pares
   (cliente → owner) y se generan embeddings para cada client_msg.
   Se guardan en wa_bot_kb con embedding como BLOB (np.float32).

2. Responder: cuando llega un mensaje sin match de reglas, generar embedding
   del mensaje, buscar los top-5 más similares en wa_bot_kb (cosine similarity),
   pasarle eso como contexto a Claude Haiku, y responder imitando el estilo
   del Owner.

Embeddings: usamos Voyage AI a través de Anthropic SDK (voyage-3-large) o
fallback a OpenAI text-embedding-3-small si solo hay OPENAI_API_KEY.

LLM: Claude Haiku 3.5 (claude-haiku-4-5 o claude-3-5-haiku-latest).
"""
from __future__ import annotations
import os
import logging
import struct
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Configuración
ANTHROPIC_MODEL = os.getenv('ANTHROPIC_BOT_MODEL', 'claude-3-5-haiku-latest')
EMBEDDING_DIM   = 1024  # voyage-3-lite default; ajustar si usás otro modelo
TOP_K           = 5     # cuántos ejemplos similares pasar al LLM


# ─── Embeddings ────────────────────────────────────────────────────
def _get_embedding(text: str) -> list[float] | None:
    """
    Genera embedding del texto. Prioriza Voyage AI (mejor para multi-idioma),
    fallback a OpenAI.
    """
    if not text or not text.strip():
        return None
    text = text.strip()[:8000]  # truncar inputs muy largos

    # Opción A: Voyage AI (recomendado, mejor en español)
    voyage_key = os.getenv('VOYAGE_API_KEY', '').strip()
    if voyage_key:
        try:
            import requests
            r = requests.post(
                'https://api.voyageai.com/v1/embeddings',
                headers={
                    'Authorization': f'Bearer {voyage_key}',
                    'Content-Type':  'application/json',
                },
                json={'input': text, 'model': 'voyage-3-lite'},
                timeout=15,
            )
            if r.status_code == 200:
                return r.json()['data'][0]['embedding']
            logger.warning(f'[RAG] Voyage embeddings fail {r.status_code}: {r.text[:200]}')
        except Exception as e:
            logger.warning(f'[RAG] Voyage error: {e}')

    # Opción B: OpenAI
    openai_key = os.getenv('OPENAI_API_KEY', '').strip()
    if openai_key:
        try:
            import requests
            r = requests.post(
                'https://api.openai.com/v1/embeddings',
                headers={
                    'Authorization': f'Bearer {openai_key}',
                    'Content-Type':  'application/json',
                },
                json={
                    'input': text,
                    'model': 'text-embedding-3-small',
                },
                timeout=15,
            )
            if r.status_code == 200:
                return r.json()['data'][0]['embedding']
            logger.warning(f'[RAG] OpenAI embeddings fail {r.status_code}')
        except Exception as e:
            logger.warning(f'[RAG] OpenAI error: {e}')

    logger.error('[RAG] Sin VOYAGE_API_KEY ni OPENAI_API_KEY — no puedo generar embeddings')
    return None


def _serialize_embedding(emb: list[float]) -> bytes:
    """Serializa lista de floats a bytes (np.float32 binary)."""
    return struct.pack(f'{len(emb)}f', *emb)


def _deserialize_embedding(b: bytes) -> list[float]:
    n = len(b) // 4
    return list(struct.unpack(f'{n}f', b))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ─── Indexar pares Q→A ─────────────────────────────────────────────
def index_qa_pairs(user_id: int, source_chat: str,
                    pairs: list[dict]) -> int:
    """
    Inserta los pares (client_msg, owner_response) con embeddings en wa_bot_kb.
    Retorna cuántos se indexaron.
    """
    from database import get_db
    if not pairs:
        return 0
    conn = get_db()
    saved = 0
    for p in pairs:
        client_msg = p.get('client_msg', '').strip()
        owner_resp = p.get('owner_response', '').strip()
        if not client_msg or not owner_resp:
            continue
        # Skip muy cortos (saludos sueltos, "ok", etc.)
        if len(client_msg) < 8 or len(owner_resp) < 15:
            continue
        # Dedup: si ya tenemos esta exacta combinación, skip
        existing = conn.execute(
            'SELECT id FROM wa_bot_kb WHERE user_id = ? AND client_msg = ? AND owner_response = ?',
            (user_id, client_msg, owner_resp)
        ).fetchone()
        if existing:
            continue
        emb = _get_embedding(client_msg)
        if not emb:
            logger.warning('[RAG] sin embedding, skip pair')
            continue
        emb_blob = _serialize_embedding(emb)
        conn.execute(
            'INSERT INTO wa_bot_kb (user_id, source_chat, client_msg, owner_response, embedding) '
            'VALUES (?, ?, ?, ?, ?)',
            (user_id, source_chat, client_msg, owner_resp, emb_blob)
        )
        saved += 1
    conn.commit()
    conn.close()
    logger.info(f'[RAG] indexados {saved} pares para user {user_id} desde "{source_chat}"')
    return saved


# ─── Retrieval ─────────────────────────────────────────────────────
def find_similar_qa(user_id: int, query_text: str, top_k: int = TOP_K) -> list[dict]:
    """
    Encuentra los top-k pares más similares en wa_bot_kb para este user.
    Cosine similarity sobre los embeddings.
    """
    from database import get_db
    query_emb = _get_embedding(query_text)
    if not query_emb:
        return []
    conn = get_db()
    rows = conn.execute(
        'SELECT id, client_msg, owner_response, embedding FROM wa_bot_kb WHERE user_id = ?',
        (user_id,)
    ).fetchall()
    conn.close()
    scored = []
    for r in rows:
        if not r['embedding']:
            continue
        emb = _deserialize_embedding(r['embedding'])
        score = _cosine_similarity(query_emb, emb)
        scored.append({
            'id':             r['id'],
            'client_msg':     r['client_msg'],
            'owner_response': r['owner_response'],
            'score':          score,
        })
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:top_k]


# ─── LLM con Claude ────────────────────────────────────────────────
_BOT_SYSTEM_PROMPT = """Sos Juan Sebastián Pinto, ejecutivo de ventas de MercadoPago Chile. Hablás por WhatsApp con clientes interesados en máquinas POS.

Estilo de comunicación:
- Tono cercano, chileno, profesional pero relajado.
- Frases cortas, directas, con emojis ocasionales (sin abusar).
- Mensajes de 1-3 líneas máximo, salvo que pidan info detallada.
- Usás "tú" y "vos" mezclado según contexto.
- No vendés agresivo: ayudás, preguntás, escuchás.

Reglas duras:
- Si el cliente pregunta algo que NO sabés con certeza (ej. comisión exacta de un rubro raro), respondé: "Te chequeo eso y te confirmo en un toque" — NO inventes datos.
- Si pide hablar con persona / no entiende lo que decís, sugerí agenda: "Te dejo mi link para coordinar una llamada corta: https://calendly.com/juansebastian-pinto/mercadopago"
- Si el cliente se enoja o se queja, primero validás el sentimiento: "Te entiendo, perdoná la molestia" — después ofrecés solución.
- NUNCA prometas plazos exactos de entrega, instalación o pagos sin verificar.
- NUNCA des comisiones o tarifas exactas en la primera conversación — siempre derivá a la reunión.

Datos clave (mencioná solo si pregunta directamente):
- Point Smart 2: $0 arriendo mensual, equipo es del cliente.
- Cobros al instante (incluso fines de semana y feriados).
- Cuotas sin interés Mastercard/Visa.
- Acepta valeras: Edenred, Pluxee, Junaeb.
- 4G + Wi-Fi + multiadquirencia.

Acá tenés ejemplos de cómo respondiste antes a preguntas similares. Imitá tu propio estilo:
{ejemplos}

Mensaje actual del cliente: {mensaje_cliente}

Respondé como respondería Juan Sebastián, en español chileno informal-profesional. SOLO la respuesta, sin meta-comentarios. Máximo 4 líneas."""


def generate_rag_response(user_id: int, client_msg: str) -> str | None:
    """
    Genera respuesta usando RAG + Claude:
    1. Busca top-5 pares similares en KB del user.
    2. Arma prompt con esos ejemplos + el msg actual.
    3. Llama a Claude Haiku.
    4. Retorna la respuesta o None si falla.
    """
    api_key = os.getenv('ANTHROPIC_API_KEY', '').strip()
    if not api_key:
        logger.warning('[RAG] ANTHROPIC_API_KEY no configurada')
        return None

    similar = find_similar_qa(user_id, client_msg, top_k=TOP_K)
    if not similar:
        # Sin KB del usuario, no podemos personalizar — pasamos al hand-off
        logger.info(f'[RAG] sin KB para user {user_id}')
        return None

    # Filtrar por score mínimo (si la mejor está muy baja, mejor no responder)
    if similar[0]['score'] < 0.40:
        logger.info(f'[RAG] best score {similar[0]["score"]:.3f} < 0.40, hand-off')
        return None

    ejemplos_txt = '\n\n'.join([
        f'CLIENTE: {s["client_msg"]}\nOWNER: {s["owner_response"]}'
        for s in similar
    ])
    prompt = _BOT_SYSTEM_PROMPT.format(
        ejemplos=ejemplos_txt,
        mensaje_cliente=client_msg
    )

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=400,
            system=prompt,
            messages=[{'role': 'user', 'content': client_msg}],
        )
        if response and response.content:
            text = response.content[0].text.strip()
            return text or None
    except Exception as e:
        logger.error(f'[RAG] Claude API fail: {e}')
    return None
