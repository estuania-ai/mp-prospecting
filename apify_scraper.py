"""
Integración con Apify Google Maps Scraper
Soporta dos modos:
  1. URL directa de Google Maps (igual que el flujo manual)
  2. Búsqueda por rubro + comuna (modo automático)
"""

import requests
import logging
import time
import re
from database import get_db, clean_phone, is_opt_out

logger = logging.getLogger(__name__)

APIFY_BASE = "https://api.apify.com/v2"

COMUNAS_RM = [
    "Santiago Centro", "Providencia", "Las Condes", "Vitacura", "Lo Barnechea",
    "Ñuñoa", "La Reina", "Peñalolén", "Macul", "San Joaquín",
    "La Florida", "Puente Alto", "La Pintana", "San Ramón", "El Bosque",
    "La Cisterna", "San Miguel", "Pedro Aguirre Cerda", "Lo Espejo",
    "Estación Central", "Cerrillos", "Maipú", "Pudahuel", "Quilicura",
    "Huechuraba", "Conchalí", "Renca", "Quinta Normal", "Lo Prado",
    "Cerro Navia", "Recoleta", "Independencia", "Buin", "Calera de Tango",
    "San Bernardo", "Paine", "Melipilla", "Talagante", "Peñaflor"
]

RUBRO_QUERIES = {
    "botilleria":     "Botillería",
    "carniceria":     "Carnicería",
    "verduleria":     "Verdulería",
    "almacen":        "Almacén de barrio",
    "emporio":        "Emporio",
    "clinica_dental": "Clínica dental",
    "sandwicheria":   "Sandwichería",
    "sushi":          "Sushi restaurante",
    "pizzeria":       "Pizzería",
    "panaderia":      "Panadería",
    "minimarket":     "Minimarket",
    "cafeteria":      "Cafetería",
    "veterinaria":    "Veterinaria",
    "libreria":       "Librería",
    "ferreteria":     "Ferretería",
    "muebleria":      "Mueblería",
    "peluqueria":     "Peluquería barbería",
    "gimnasio":       "Gimnasio",
    "taller":         "Taller mecánico",
    "farmacia":       "Farmacia",
    "lavanderia":     "Lavandería",
    "spa":            "Spa estética",
    "bazar":          "Bazar regalos",
    "fruteria":       "Frutería",
    "fuente_de_soda": "Fuente de soda",
}


def validate_chilean_phone(phone: str) -> str | None:
    if not phone:
        return None
    digits = re.sub(r'\D', '', str(phone))
    if re.match(r'^569\d{8}$', digits):
        return digits
    if re.match(r'^9\d{8}$', digits):
        return '56' + digits
    if re.match(r'^56[2-9]\d{7,8}$', digits):
        return digits
    return None


def extract_comuna_from_url(maps_url: str) -> str:
    try:
        from urllib.parse import unquote
        decoded = unquote(maps_url).lower()
        for comuna in COMUNAS_RM:
            if comuna.lower() in decoded:
                return comuna
    except Exception:
        pass
    return "Sin clasificar"


def extract_rubro_from_url(maps_url: str) -> str:
    try:
        from urllib.parse import unquote
        decoded = unquote(maps_url).lower()
        for key, label in RUBRO_QUERIES.items():
            if label.lower().split()[0] in decoded:
                return key
    except Exception:
        pass
    return "otro"


class ApifyScraper:

    def __init__(self, api_token: str):
        self.api_token = api_token
        # Actor ID configurable desde BD - permite cambiar sin tocar codigo
        from database import get_config as _gc
        self.actor_id = _gc('apify_actor_id') or "compass/google-maps-extractor"
        self.headers   = {"Authorization": f"Bearer {api_token}"}

    def _run_actor_url(self, maps_url: str, max_items: int = 100) -> str | None:
        payload = {
            "startUrls": [{"url": maps_url}],
            "maxCrawledPlacesPerSearch": max_items,
            "language": "es",
            "countryCode": "cl",
            "includeWebResults": False,
        }
        return self._launch(payload)

    def _run_actor_search(self, query: str, max_items: int = 40) -> str | None:
        payload = {
            "searchStringsArray": [query],
            "maxCrawledPlacesPerSearch": max_items,
            "language": "es",
            "countryCode": "cl",
            "includeWebResults": False,
        }
        return self._launch(payload)

    def _launch(self, payload: dict) -> str | None:
        try:
            resp = requests.post(
                f"{APIFY_BASE}/acts/{self.actor_id}/runs",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            resp.raise_for_status()
            run_id = resp.json()['data']['id']
            logger.info(f"Actor Apify iniciado: run {run_id}")
            return run_id
        except Exception as e:
            logger.error(f"Error lanzando actor Apify: {e}")
            return None

    def _wait_for_run(self, run_id: str, timeout_sec: int = 300) -> bool:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            try:
                resp   = requests.get(
                    f"{APIFY_BASE}/actor-runs/{run_id}",
                    headers=self.headers, timeout=15
                )
                status = resp.json()['data']['status']
                if status == 'SUCCEEDED':
                    logger.info(f"Run {run_id} completado OK")
                    return True
                if status in ('FAILED', 'ABORTED', 'TIMED-OUT'):
                    logger.error(f"Run {run_id} termino: {status}")
                    return False
                logger.info(f"Run {run_id} estado: {status} - esperando...")
                time.sleep(10)
            except Exception as e:
                logger.warning(f"Error consultando run: {e}")
                time.sleep(10)
        return False

    def _fetch_dataset(self, run_id: str) -> list:
        try:
            resp = requests.get(
                f"{APIFY_BASE}/actor-runs/{run_id}/dataset/items",
                headers=self.headers,
                params={"format": "json"},
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"Dataset: {len(data)} resultados")
            return data
        except Exception as e:
            logger.error(f"Error descargando dataset: {e}")
            return []

    def _clean_results(self, raw: list, rubro: str, comuna: str) -> list:
        clean = []
        for item in raw:
            phone_raw = item.get('phone', '') or item.get('phoneNumber', '') or ''
            phone     = validate_chilean_phone(phone_raw)
            if not phone:
                continue
            if is_opt_out(phone):
                continue
            name = (item.get('title') or item.get('name', '')).strip()
            if not name:
                continue
            # Extraer comuna desde address si no viene especificada
            addr = item.get('address', '') or ''
            comuna_final = comuna
            if not comuna_final or comuna_final == 'Sin clasificar':
                comunas_rm = [
                    'Cerrillos','Cerro Navia','Conchali','Conchalí','El Bosque','Estacion Central','Estación Central',
                    'Huechuraba','Independencia','La Cisterna','La Florida','La Granja',
                    'La Pintana','La Reina','Las Condes','Lo Barnechea','Lo Espejo',
                    'Lo Prado','Macul','Maipu','Maipú','Nunoa','Ñuñoa','Penalolen','Peñalolén',
                    'Providencia','Pudahuel','Puente Alto','Quilicura','Quinta Normal',
                    'Recoleta','Renca','San Bernardo','San Joaquin','San Joaquín','San Miguel',
                    'San Ramon','San Ramón','Santiago','Vitacura','Buin','Colina','El Monte',
                    'Lampa','Melipilla','Paine','Pirque','Tiltil'
                ]
                addr_lower = addr.lower()
                for c in comunas_rm:
                    if c.lower() in addr_lower:
                        comuna_final = c
                        break
            clean.append({
                'name':    name,
                'phone':   phone,
                'address': addr,
                'comuna':  comuna_final,
                'rubro':   rubro,
                'rating':  item.get('totalScore'),
                'url':     item.get('url', ''),
            })
        logger.info(f"Resultados con telefono valido: {len(clean)}/{len(raw)}")
        return clean

    def save_leads(self, leads: list) -> dict:
        inserted = skipped = 0
        conn = get_db()
        for lead in leads:
            try:
                # Verificar duplicado por telefono
                existing = conn.execute('SELECT id FROM leads WHERE phone=?', (lead['phone'],)).fetchone()
                if existing:
                    skipped += 1
                    continue

                # Determinar categoria segun rubro
                from rubros_config import RUBROS
                rubro = lead.get('rubro','')
                categoria = RUBROS.get(rubro, {}).get('categoria', '')

                cur = conn.execute(
                    'INSERT INTO leads (name, phone, comuna, rubro, categoria) VALUES (?, ?, ?, ?, ?)',
                    (lead['name'], lead['phone'], lead.get('comuna',''), rubro, categoria)
                )
                lead_id = cur.lastrowid
                conn.execute(
                    "INSERT INTO lead_status (lead_id, status, updated_at) VALUES (?, 'no_enviado', datetime('now','localtime'))",
                    (lead_id,)
                )
                inserted += 1
            except Exception as e:
                logger.warning(f"Error insertando {lead.get('phone')}: {e}")
                skipped += 1
        conn.commit()
        conn.close()
        logger.info(f"Guardados: {inserted} nuevos, {skipped} duplicados omitidos")
        return {'inserted': inserted, 'skipped': skipped}

    def scrape_from_url(self, maps_url: str, rubro: str = None, comuna: str = None, max_items: int = 100) -> dict:
        """Pipeline completo usando URL directa de Google Maps."""
        rubro_final  = rubro  or extract_rubro_from_url(maps_url)
        comuna_final = comuna or extract_comuna_from_url(maps_url)
        logger.info(f"Scraping URL: rubro={rubro_final}, comuna={comuna_final}")
        run_id = self._run_actor_url(maps_url, max_items)
        if not run_id:
            return {'leads_found': 0, 'inserted': 0, 'skipped': 0, 'error': 'No se pudo lanzar el actor'}
        if not self._wait_for_run(run_id):
            return {'leads_found': 0, 'inserted': 0, 'skipped': 0, 'error': 'El actor fallo o tardo demasiado'}
        raw    = self._fetch_dataset(run_id)
        leads  = self._clean_results(raw, rubro_final, comuna_final)
        result = self.save_leads(leads)
        result.update({'leads_found': len(leads), 'rubro': rubro_final, 'comuna': comuna_final})
        return result

    def scrape_and_save(self, rubro_key: str, comuna: str, max_items: int = 40) -> dict:
        """Pipeline completo por texto rubro + comuna."""
        query  = RUBRO_QUERIES.get(rubro_key, rubro_key)
        q_full = f"{query} en {comuna}, Santiago, Chile"
        logger.info(f"Scraping texto: '{q_full}'")
        run_id = self._run_actor_search(q_full, max_items)
        if not run_id:
            return {'leads_found': 0, 'inserted': 0, 'skipped': 0}
        if not self._wait_for_run(run_id):
            return {'leads_found': 0, 'inserted': 0, 'skipped': 0}
        raw    = self._fetch_dataset(run_id)
        leads  = self._clean_results(raw, rubro_key, comuna)
        result = self.save_leads(leads)
        result['leads_found'] = len(leads)
        return result
