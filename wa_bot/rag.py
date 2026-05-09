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
import re
import math
import logging
import struct
from collections import Counter
from typing import List, Tuple

logger = logging.getLogger(__name__)


# ─── TF-IDF puro Python (sin embeddings externos) ──────────────────
# Si no tenés Voyage ni OpenAI, este retrieval funciona razonablemente bien
# para matching de preguntas similares en el KB. Es 100% gratis.

_STOPWORDS_ES = {
    'a','al','algo','algunos','algunas','ante','antes','aquel','aquella','aquello',
    'aqui','aquí','ahora','así','bajo','bien','cada','como','cómo','con','contra',
    'cual','cuál','cuando','cuándo','de','del','desde','donde','dónde','el','él',
    'ella','ellas','ellos','en','entre','era','eran','eres','es','esa','ese','eso',
    'esos','está','están','este','esta','esto','estos','fue','fueron','ha','han',
    'hace','hacia','hasta','hay','la','las','le','les','lo','los','más','me','mi',
    'mis','muy','ni','no','nos','nosotros','o','os','para','pero','poco','por',
    'porque','que','qué','quien','quién','se','sea','sean','ser','si','sí','sin',
    'sobre','solo','sólo','son','soy','su','sus','también','tan','te','tengo',
    'ti','tiene','todo','todos','tu','tus','un','una','unas','unos','uno','y',
    'ya','yo',
}


def _tokenize(text: str) -> list[str]:
    """Tokeniza a lower + remueve stopwords + filtra tokens muy cortos."""
    if not text:
        return []
    text = text.lower()
    # Reemplaza puntuación por espacios
    text = re.sub(r'[^a-záéíóúñü0-9\s]', ' ', text)
    tokens = [t for t in text.split() if len(t) >= 3 and t not in _STOPWORDS_ES]
    return tokens


def _bm25_score(query_tokens: list[str], doc_tokens: list[str],
                 doc_freq: dict[str, int], total_docs: int,
                 avg_doc_len: float, k1: float = 1.5, b: float = 0.75) -> float:
    """
    BM25 — variante mejorada de TF-IDF, mejor performance para retrieval.
    Implementación pura Python.
    """
    if not query_tokens or not doc_tokens:
        return 0.0
    doc_len = len(doc_tokens)
    doc_tf  = Counter(doc_tokens)
    score   = 0.0
    for term in query_tokens:
        df = doc_freq.get(term, 0)
        if df == 0:
            continue
        idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1)
        tf  = doc_tf.get(term, 0)
        if tf == 0:
            continue
        norm = 1 - b + b * (doc_len / (avg_doc_len or 1))
        score += idf * (tf * (k1 + 1)) / (tf + k1 * norm)
    return score


def _bm25_retrieve(user_id: int, query_text: str, top_k: int) -> list[dict]:
    """
    Retrieval con BM25 sobre todos los pares Q→A del usuario.
    No requiere API externa. Funciona en Python puro.
    """
    from database import get_db
    query_tokens = _tokenize(query_text)
    if not query_tokens:
        return []
    conn = get_db()
    rows = conn.execute(
        'SELECT id, client_msg, owner_response FROM wa_bot_kb WHERE user_id = ?',
        (user_id,)
    ).fetchall()
    conn.close()
    if not rows:
        return []

    # Pre-tokenizar todos los docs y calcular doc_freq
    docs = []
    doc_freq: Counter = Counter()
    for r in rows:
        toks = _tokenize(r['client_msg'])
        docs.append({
            'id':             r['id'],
            'client_msg':     r['client_msg'],
            'owner_response': r['owner_response'],
            'tokens':         toks,
        })
        for term in set(toks):
            doc_freq[term] += 1

    total_docs  = len(docs)
    avg_doc_len = (sum(len(d['tokens']) for d in docs) / total_docs) if total_docs else 0

    scored = []
    for d in docs:
        score = _bm25_score(query_tokens, d['tokens'],
                             doc_freq, total_docs, avg_doc_len)
        if score > 0:
            scored.append({
                'id':             d['id'],
                'client_msg':     d['client_msg'],
                'owner_response': d['owner_response'],
                'score':          score,
            })
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:top_k]


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
    Inserta los pares (client_msg, owner_response) en wa_bot_kb.

    Embedding es OPCIONAL: si hay Voyage o OpenAI configurado, lo genera y guarda.
    Si no, guarda solo el texto y el retrieval usa BM25 (puro Python, gratis).
    """
    from database import get_db
    if not pairs:
        return 0

    has_emb_provider = bool(
        os.getenv('VOYAGE_API_KEY', '').strip() or
        os.getenv('OPENAI_API_KEY', '').strip()
    )

    conn = get_db()
    saved = 0
    skipped_short = 0
    for p in pairs:
        client_msg = p.get('client_msg', '').strip()
        owner_resp = p.get('owner_response', '').strip()
        if not client_msg or not owner_resp:
            continue
        if len(client_msg) < 8 or len(owner_resp) < 15:
            skipped_short += 1
            continue
        existing = conn.execute(
            'SELECT id FROM wa_bot_kb WHERE user_id = ? AND client_msg = ? AND owner_response = ?',
            (user_id, client_msg, owner_resp)
        ).fetchone()
        if existing:
            continue

        emb_blob = None
        if has_emb_provider:
            emb = _get_embedding(client_msg)
            if emb:
                emb_blob = _serialize_embedding(emb)

        conn.execute(
            'INSERT INTO wa_bot_kb (user_id, source_chat, client_msg, owner_response, embedding) '
            'VALUES (?, ?, ?, ?, ?)',
            (user_id, source_chat, client_msg, owner_resp, emb_blob)
        )
        saved += 1
    conn.commit()
    conn.close()
    mode = 'embeddings' if has_emb_provider else 'BM25 (sin embeddings, gratis)'
    logger.info(
        f'[RAG] indexados {saved} pares para user {user_id} desde "{source_chat}" — modo {mode}'
    )
    return saved


# ─── Retrieval ─────────────────────────────────────────────────────
def find_similar_qa(user_id: int, query_text: str, top_k: int = TOP_K) -> list[dict]:
    """
    Encuentra los top-k pares más similares en wa_bot_kb para este user.

    Estrategia:
    1. Si hay embedding provider configurado Y los items del KB tienen embeddings
       → cosine similarity (mejor calidad semántica).
    2. Si no → BM25 puro Python sobre el texto (gratis, sin APIs externas,
       funciona razonablemente bien para matching de preguntas).
    """
    from database import get_db
    has_emb_provider = bool(
        os.getenv('VOYAGE_API_KEY', '').strip() or
        os.getenv('OPENAI_API_KEY', '').strip()
    )

    if has_emb_provider:
        query_emb = _get_embedding(query_text)
        if query_emb:
            conn = get_db()
            rows = conn.execute(
                'SELECT id, client_msg, owner_response, embedding FROM wa_bot_kb '
                'WHERE user_id = ? AND embedding IS NOT NULL',
                (user_id,)
            ).fetchall()
            conn.close()
            if rows:
                scored = []
                for r in rows:
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

    # Fallback: BM25 (sin APIs)
    return _bm25_retrieve(user_id, query_text, top_k)


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
        logger.info(f'[RAG] sin KB para user {user_id}')
        return None

    # Threshold según el método usado:
    # - Cosine (embeddings): valores 0-1, threshold 0.40
    # - BM25 (sin embeddings): valores 0-+inf, threshold 1.0 (1+ palabras coincidentes)
    using_embeddings = bool(
        os.getenv('VOYAGE_API_KEY', '').strip() or
        os.getenv('OPENAI_API_KEY', '').strip()
    )
    min_score = 0.40 if using_embeddings else 1.0
    if similar[0]['score'] < min_score:
        logger.info(f'[RAG] best score {similar[0]["score"]:.3f} < {min_score}, hand-off')
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


def generate_rag_response_openai(user_id: int, client_msg: str) -> str | None:
    """
    Misma idea que generate_rag_response pero con OpenAI GPT-4o-mini.
    Se usa como fallback cuando ANTHROPIC_API_KEY no está disponible.
    Más barato que Claude Haiku ($0.0001 vs $0.001 por respuesta).
    """
    api_key = os.getenv('OPENAI_API_KEY', '').strip()
    if not api_key:
        return None

    similar = find_similar_qa(user_id, client_msg, top_k=TOP_K)
    if not similar:
        return None
    if similar[0]['score'] < 0.40:
        logger.info(f'[RAG/OpenAI] best score {similar[0]["score"]:.3f} < 0.40, hand-off')
        return None

    ejemplos_txt = '\n\n'.join([
        f'CLIENTE: {s["client_msg"]}\nOWNER: {s["owner_response"]}'
        for s in similar
    ])
    system_prompt = _BOT_SYSTEM_PROMPT.format(
        ejemplos=ejemplos_txt,
        mensaje_cliente=client_msg
    )

    try:
        import requests
        r = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type':  'application/json',
            },
            json={
                'model': os.getenv('OPENAI_BOT_MODEL', 'gpt-4o-mini'),
                'max_tokens': 400,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user',   'content': client_msg},
                ],
            },
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            text = (data.get('choices') or [{}])[0].get('message', {}).get('content', '').strip()
            return text or None
        logger.warning(f'[RAG/OpenAI] {r.status_code}: {r.text[:200]}')
    except Exception as e:
        logger.error(f'[RAG/OpenAI] fail: {e}')
    return None


def generate_response(user_id: int, client_msg: str) -> str | None:
    """
    Punto de entrada unificado: prueba Anthropic primero, si no está configurado
    cae a OpenAI. Si ninguno está configurado, retorna None (el dispatcher
    hace hand-off al humano).
    """
    if os.getenv('ANTHROPIC_API_KEY', '').strip():
        result = generate_rag_response(user_id, client_msg)
        if result:
            return result
    if os.getenv('OPENAI_API_KEY', '').strip():
        return generate_rag_response_openai(user_id, client_msg)
    logger.warning('[RAG] Ni ANTHROPIC_API_KEY ni OPENAI_API_KEY configuradas')
    return None
