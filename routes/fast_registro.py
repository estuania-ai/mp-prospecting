"""
Rutas Flask: Fast Registro
Registra comercios en MercadoPago Fast usando Playwright.
Requiere sesion previa guardada con fast_login_manual.py
"""
from flask import Blueprint, request, jsonify
from database import get_db
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

fast_bp = Blueprint('fast', __name__)

MP_EMAIL    = os.getenv("MP_FAST_EMAIL", "")
MP_PASSWORD = os.getenv("MP_FAST_PASSWORD", "")
FAST_URL    = "https://www.mercadopago.cl/point-fast/home"
SESSION_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'fast_session.json')


def _ensure_session_from_env() -> bool:
    """
    Garantiza que fast_session.json exista en disco como JSON válido sin BOM.
    Siempre reescribe desde FAST_SESSION_JSON env var si está disponible,
    parseando el JSON y serializando de cero (elimina cualquier BOM/caracter raro).
    """
    import json as _json

    session_json = os.getenv("FAST_SESSION_JSON", "")

    if session_json:
        # Eliminar BOM y whitespace en cualquier forma
        # ﻿ es el BOM Unicode, también puede aparecer como bytes \xef\xbb\xbf
        session_json = session_json.lstrip("﻿￾ \t\r\n").strip()

        try:
            # Parsear y reserializar — esto elimina cualquier carácter problemático
            session_obj = _json.loads(session_json)
            os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
            # Escribir como JSON limpio sin BOM (utf-8 sin firma)
            with open(SESSION_FILE, "w", encoding="utf-8", newline="") as f:
                _json.dump(session_obj, f, ensure_ascii=False)
            logger.info("[Fast] Sesión escrita desde FAST_SESSION_JSON (parseada y limpia)")
            return True
        except Exception as e:
            logger.error(f"[Fast] FAST_SESSION_JSON no es JSON válido: {e}")
            # Caer al fallback: usar archivo existente si lo hay
            pass

    # Fallback: usar archivo existente si ya está en disco y es válido
    if os.path.isfile(SESSION_FILE) and os.path.getsize(SESSION_FILE) > 100:
        try:
            with open(SESSION_FILE, encoding="utf-8-sig") as _f:
                _json.load(_f)
            return True
        except Exception:
            try:
                os.remove(SESSION_FILE)
            except Exception:
                pass
    return False


def _formatear_telefono(raw: str) -> str:
    """Antepone 9 al teléfono de la BD después de eliminar el prefijo 56."""
    digits = "".join(c for c in raw if c.isdigit())
    if digits.startswith("56"):
        digits = digits[2:]  # quitar código de país → 930560400
    return "9" + digits      # siempre anteponer 9 → 9930560400


FALLBACK_ADDRESS = "Parque Ibérico 1474, Puente Alto"

def _limpiar_direccion(raw: str) -> str:
    """Extrae solo 'Calle NNN' de una dirección completa de Google Maps.

    Ejemplos:
      'Araucaria 666, 8180740 Puente Alto, Región Metropolitana, Chile' → 'Araucaria 666'
      'Parque Ibérico 1474, Puente Alto, Chile'                         → 'Parque Ibérico 1474'
    """
    import re as _re
    if not raw:
        return FALLBACK_ADDRESS
    # Tomar solo la primera parte antes de la primera coma
    parte = raw.split(",")[0].strip()
    # Eliminar códigos postales (secuencias de 5-7 dígitos solos)
    parte = _re.sub(r'\b\d{5,7}\b', '', parte).strip()
    # Si quedó vacío o muy corto, usar fallback
    if len(parte) < 5:
        return FALLBACK_ADDRESS
    return parte


def _session_exists() -> bool:
    return _ensure_session_from_env()


async def _registrar_en_fast(nombre: str, telefono: str, direccion: str) -> dict:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    if not _session_exists():
        return {
            "ok": False,
            "mensaje": "Sin sesion guardada. Ejecuta: python fast_login_manual.py"
        }

    telefono_fmt = _formatear_telefono(telefono)
    nombre_parts = nombre.strip().split(" ", 1)
    first = nombre_parts[0]
    last  = nombre_parts[1] if len(nombre_parts) > 1 else first

    import shutil as _shutil
    _chromium_path = (
        _shutil.which("chromium") or
        _shutil.which("chromium-browser") or
        None
    )
    logger.info(f"[Fast] Chromium ejecutable: {_chromium_path or 'playwright default'}")

    # Si FAST_HEADLESS=false, abre Chrome con ventana visible (modo local).
    # MercadoPago detecta y rechaza sesiones en headless, así que en local
    # conviene visible (igual que fast_login_manual.py).
    _headless = os.getenv("FAST_HEADLESS", "true").lower() != "false"
    logger.info(f"[Fast] Modo headless: {_headless}")

    async with async_playwright() as p:
        launch_kwargs = dict(
            headless=_headless,
            slow_mo=200 if _headless else 100,
            args=(
                ["--disable-blink-features=AutomationControlled"]
                if not _headless else
                [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            ),
        )
        if _chromium_path and _headless:
            # Solo usar el chromium de nix en modo headless (Railway)
            launch_kwargs["executable_path"] = _chromium_path
        browser = await p.chromium.launch(**launch_kwargs)
        # Importante: no override del user_agent — debe coincidir con el que
        # se usó al crear la sesión (fast_login_manual.py usa el default).
        # Si MP detecta cambio de UA, invalida la sesión.
        context_kwargs = dict(
            storage_state=SESSION_FILE,
            viewport={"width": 1280, "height": 800},
            locale="es-CL",
            # Pre-otorgar permiso de geolocalizacion (evita popup de Chrome
            # que bloquea la automatizacion). Coordenadas: Santiago de Chile.
            permissions=["geolocation"],
            geolocation={"latitude": -33.4489, "longitude": -70.6693},
        )
        # En Railway (headless) sí necesitamos UA explícito porque el chromium
        # de nix puede tener un UA distinto al de playwright local
        if _headless:
            context_kwargs["user_agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()

        try:
            await page.goto(FAST_URL, timeout=30_000)
            await page.wait_for_load_state("networkidle", timeout=15_000)
            await page.screenshot(path="logs/fast_01_home.png")
            logger.info(f"[Fast] URL tras goto: {page.url}")

            # Verificar que estamos en point-fast (no en login ni en otra sección)
            if "login" in page.url or "identificacion" in page.url:
                await browser.close()
                os.remove(SESSION_FILE)
                return {"ok": False, "mensaje": "Sesion expirada. Ejecuta python fast_login_manual.py para renovarla."}

            if "point-fast" not in page.url:
                await browser.close()
                return {
                    "ok": False,
                    "mensaje": f"Sesion incorrecta o sin permisos Fast. URL actual: {page.url}. "
                               "Ejecuta python fast_login_manual.py desde la cuenta correcta."
                }

            # Clic en "Registrar comercio"
            await page.click('text=Registrar comercio', timeout=20_000)
            await page.wait_for_load_state("networkidle", timeout=20_000)
            await asyncio.sleep(2)  # espera extra para render completo
            await page.screenshot(path="logs/fast_02_form.png")
            logger.info(f"[Fast] URL tras Registrar comercio: {page.url}")

            # ── Sección Contacto ──────────────────────────────────────────────
            # "Nombre y apellido" — intenta varios selectores
            nombre_filled = False
            for nombre_sel in [
                lambda: page.get_by_label("Nombre y apellido"),
                lambda: page.locator('input[name*="name" i]').first,
                lambda: page.locator('input[placeholder*="nombre" i]').first,
                lambda: page.locator('input[id*="name" i]').first,
                lambda: page.locator('input[type="text"]').first,
            ]:
                try:
                    loc = nombre_sel()
                    await loc.wait_for(state="visible", timeout=15_000)
                    await loc.fill(nombre, timeout=10_000)
                    nombre_filled = True
                    logger.info(f"[Fast] Campo nombre completado")
                    break
                except Exception as _e:
                    logger.debug(f"[Fast] Selector nombre fallido: {_e}")
            if not nombre_filled:
                await page.screenshot(path="logs/fast_error_nombre.png")
                body_preview = (await page.evaluate("document.body.innerText"))[:300]
                await browser.close()
                return {"ok": False, "mensaje": f"No se encontró campo Nombre en el formulario. URL: {page.url}. Contenido: {body_preview}"}

            # Teléfono — dígitos completos (9XXXXXXXXX), escritura dígito a dígito
            phone_input = page.locator('input[type="tel"]').first
            if await phone_input.count() == 0:
                phone_input = page.locator('input[id*="phone"], input[name*="phone"]').first
            if await phone_input.count() == 0:
                phone_input = page.locator('[role="combobox"] ~ input').first
            await phone_input.click(timeout=8_000)
            await page.keyboard.press("Control+a")
            await phone_input.press_sequentially(telefono_fmt, delay=80)

            # ── Sección Comercio ──────────────────────────────────────────────
            await page.get_by_label("Nombre del comercio").fill(nombre, timeout=8_000)

            # Dirección: solo calle + número (sin código postal, región, etc.)
            direccion = _limpiar_direccion(direccion)

            # Buscar input de dirección por varios selectores
            dir_input = None
            for dir_sel in ['#address', 'input[name*="address" i]', 'input[placeholder*="direcci" i]',
                            'input[autocomplete*="address" i]', 'input[id*="address" i]']:
                loc = page.locator(dir_sel).first
                if await loc.count() > 0:
                    dir_input = loc
                    break
            if dir_input is None:
                # Último recurso: tercer input visible del formulario
                dir_input = page.locator('input[type="text"]').nth(2)

            # Scroll al campo de dirección antes de escribir
            await dir_input.scroll_into_view_if_needed()
            await dir_input.click(timeout=5_000)
            await dir_input.fill("", timeout=3_000)
            await asyncio.sleep(0.3)
            # Escribir lento para disparar eventos del autocomplete de Google Maps
            await dir_input.press_sequentially(direccion, delay=120)
            # Esperar hasta 6 segundos a que aparezca la primera opción del dropdown
            await asyncio.sleep(1.0)
            await page.screenshot(path="logs/fast_02b_address.png")

            # Esperar y seleccionar primera sugerencia del autocomplete
            suggestion_selected = False
            for sel in ['[role="option"]', '[role="listbox"] li', '.pac-item',
                        '[class*="suggestion"]', '[class*="autocomplete"]']:
                try:
                    sug = page.locator(sel).first
                    await sug.wait_for(state="visible", timeout=5_000)
                    box = await sug.bounding_box()
                    if box and box['width'] > 0:
                        await page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                        suggestion_selected = True
                        logger.info(f"[Fast] Dirección sugerencia clickeada via '{sel}'")
                        break
                except Exception as e:
                    logger.debug(f"[Fast] {sel}: {e}")

            # Si no hubo sugerencia, reintentar con fallback
            if not suggestion_selected:
                logger.warning(f"[Fast] Sin sugerencia para '{direccion}', usando fallback...")
                await dir_input.click(click_count=3, timeout=3_000)
                await dir_input.fill("", timeout=3_000)
                await asyncio.sleep(0.3)
                await dir_input.press_sequentially(FALLBACK_ADDRESS, delay=120)
                await asyncio.sleep(1.5)
                for sel in ['[role="option"]', '[role="listbox"] li', '.pac-item']:
                    try:
                        sug = page.locator(sel).first
                        await sug.wait_for(state="visible", timeout=4_000)
                        box = await sug.bounding_box()
                        if box and box['width'] > 0:
                            await page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                            suggestion_selected = True
                            logger.info(f"[Fast] Dirección fallback clickeada via '{sel}'")
                            break
                    except Exception:
                        continue

            # Tab para avanzar al siguiente campo (como hace el usuario)
            await asyncio.sleep(0.5)
            await dir_input.press("Tab")
            await asyncio.sleep(0.5)

            await page.screenshot(path="logs/fast_02c_after_address.png")

            import re as _re

            async def _click_element(loc, label):
                """Scroll + mouse click en el área de contenido (x > 250, fuera del sidebar)."""
                try:
                    await loc.scroll_into_view_if_needed(timeout=4_000)
                    box = await loc.bounding_box()
                    if box and box['x'] > 250:  # ignorar elementos del sidebar izquierdo
                        await page.mouse.click(
                            box['x'] + box['width'] / 2,
                            box['y'] + box['height'] / 2
                        )
                        logger.info(f"[Fast] '{label}' click en ({box['x']+box['width']/2:.0f},{box['y']+box['height']/2:.0f})")
                        return True
                    elif box:
                        logger.debug(f"[Fast] '{label}' ignorado — en sidebar (x={box['x']:.0f})")
                except Exception as e:
                    logger.debug(f"[Fast] _click_element '{label}': {e}")
                return False

            async def click_card(card_text, section=None):
                """Clickea un card del formulario usando locators Playwright (evita stale coords)."""
                norm_text = _re.sub(r'[\u00ae\u2122\u00a9\s]+', ' ', card_text).strip()
                # Patrón exacto — re.IGNORECASE es válido en JS (Playwright lo convierte a /i)
                pattern = _re.compile(
                    r'^[\s\u00ae\u2122\u00a9]*' + _re.escape(norm_text) + r'[\s\u00ae\u2122\u00a9]*$',
                    _re.IGNORECASE
                )

                # Estrategia 1: coincidencia exacta (con tolerancia de símbolos)
                for selector in ['button', 'td', 'li', '[role="gridcell"]']:
                    locs = page.locator(selector).filter(has_text=pattern)
                    n = await locs.count()
                    for i in range(min(n, 8)):
                        loc = locs.nth(i)
                        try:
                            box = await loc.bounding_box()
                            if box and box['x'] > 250 and box['width'] > 40 and box['height'] > 15:
                                await loc.scroll_into_view_if_needed()
                                await asyncio.sleep(0.4)
                                await loc.click(timeout=5_000)
                                logger.info(f"[Fast] '{card_text}' click OK ({selector}[{i}])")
                                return True
                        except Exception as e:
                            logger.debug(f"[Fast] click_card '{card_text}' {selector}[{i}]: {e}")

                # Estrategia 2: coincidencia parcial (para Getnet con logo/SVG)
                partial = _re.compile(_re.escape(norm_text), _re.IGNORECASE)
                for selector in ['button', 'td', 'li']:
                    locs = page.locator(selector).filter(has_text=partial)
                    n = await locs.count()
                    for i in range(min(n, 8)):
                        loc = locs.nth(i)
                        try:
                            box = await loc.bounding_box()
                            if box and box['x'] > 250 and box['width'] > 40 and box['height'] > 15:
                                await loc.scroll_into_view_if_needed()
                                await asyncio.sleep(0.4)
                                await loc.click(timeout=5_000)
                                logger.info(f"[Fast] '{card_text}' click parcial OK ({selector}[{i}])")
                                return True
                        except Exception as e:
                            logger.debug(f"[Fast] click_card parcial '{card_text}' {selector}[{i}]: {e}")

                logger.warning(f"[Fast] No se pudo marcar '{card_text}'")
                return False

            # ── Etapa de la negociación: Calificación PRIMERO ────────────────
            await click_card("Calificación")
            await asyncio.sleep(1.5)

            # ── Motivo: andes-dropdown__trigger → Considerando propuesta → Confirmar
            try:
                # El trigger del Motivo está dentro del .andes-dropdown que tiene label "Motivo:"
                motivo_coords = await page.evaluate("""
                    () => {
                        const label = [...document.querySelectorAll('span.andes-dropdown__label, label')]
                            .find(e => (e.innerText||'').trim().startsWith('Motivo'));
                        if (!label) return null;
                        const dropdown = label.closest('.andes-dropdown');
                        if (!dropdown) return null;
                        const trigger = dropdown.querySelector('.andes-dropdown__trigger, button');
                        if (!trigger) return null;
                        trigger.scrollIntoView({block: 'center', behavior: 'instant'});
                        const r = trigger.getBoundingClientRect();
                        return {x: r.left + r.width/2, y: r.top + r.height/2};
                    }
                """)
                if motivo_coords:
                    await page.mouse.click(motivo_coords['x'], motivo_coords['y'])
                    logger.info(f"[Fast] Motivo dropdown click ({motivo_coords['x']:.0f},{motivo_coords['y']:.0f})")
                else:
                    # Fallback: segundo andes-dropdown__trigger (primero = Tipo de comercio)
                    triggers = page.locator('button.andes-dropdown__trigger')
                    if await triggers.count() >= 2:
                        loc = triggers.nth(1)
                        await loc.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        await loc.click(timeout=5_000)
                        logger.info("[Fast] Motivo dropdown click (fallback nth 1)")

                await asyncio.sleep(1.2)

                # Seleccionar "Considerando propuesta" en el panel Andes
                checked = False
                for sel in [
                    '.andes-list__item:has-text("Considerando propuesta")',
                    'li.andes-list__item:has-text("Considerando propuesta")',
                    'li:has-text("Considerando propuesta")',
                    '[role="option"]:has-text("Considerando propuesta")',
                    'text=Considerando propuesta',
                ]:
                    try:
                        opt = page.locator(sel).first
                        if await opt.count() > 0 and await opt.is_visible(timeout=2_000):
                            await opt.scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await opt.click(timeout=4_000)
                            checked = True
                            logger.info(f"[Fast] 'Considerando propuesta' OK via '{sel}'")
                            break
                    except Exception:
                        continue

                if not checked:
                    logger.warning("[Fast] 'Considerando propuesta' NO encontrado")

                await asyncio.sleep(0.5)
                for btn_sel in ['button.andes-button:has-text("Confirmar")', 'button:has-text("Confirmar")']:
                    try:
                        btn = page.locator(btn_sel).first
                        if await btn.count() > 0 and await btn.is_visible(timeout=2_000):
                            await btn.click(timeout=5_000)
                            logger.info(f"[Fast] Confirmar OK")
                            break
                    except Exception:
                        continue
                await asyncio.sleep(0.8)
            except Exception as e:
                logger.warning(f"[Fast] Error en Motivo: {e}")

            # ── Forma de pago: Crédito y Débito ───────────────────────────────
            await click_card("Crédito")
            await asyncio.sleep(0.5)
            await click_card("Débito")
            await asyncio.sleep(0.5)

            # ── Productos de interés: Point ───────────────────────────────────
            await click_card("Point")
            await asyncio.sleep(0.5)

            # ── Competencia: Getnet ───────────────────────────────────────────
            # Getnet tiene innerText vacío (logo CSS), no se puede buscar por texto.
            # Buscamos el primer .multiple-selection-button debajo del heading "Competencia".
            getnet_clicked = await page.evaluate("""
                () => {
                    const headings = [...document.querySelectorAll('span, p, div, h3, h4, label')];
                    const heading = headings.find(e =>
                        e.childElementCount === 0 &&
                        (e.innerText || e.textContent || '').trim() === 'Competencia'
                    );
                    if (!heading) return 'no-heading';
                    const headingBottom = heading.getBoundingClientRect().bottom;
                    const btns = [...document.querySelectorAll('.multiple-selection-button')].filter(b => {
                        const r = b.getBoundingClientRect();
                        return r.top >= headingBottom - 15 && r.left > 250 && r.width > 40;
                    });
                    if (!btns.length) return 'no-btns';
                    const btn = btns[0];
                    btn.scrollIntoView({block: 'center', behavior: 'instant'});
                    const r = btn.getBoundingClientRect();
                    return {x: r.left + r.width / 2, y: r.top + r.height / 2};
                }
            """)
            await asyncio.sleep(0.4)
            if isinstance(getnet_clicked, dict) and 'x' in getnet_clicked:
                await page.mouse.click(getnet_clicked['x'], getnet_clicked['y'])
                logger.info(f"[Fast] Getnet click ({getnet_clicked['x']:.0f},{getnet_clicked['y']:.0f})")
            else:
                logger.warning(f"[Fast] Getnet no encontrado: {getnet_clicked}")

            # ── Registrar visita ──────────────────────────────────────────────
            await page.screenshot(path="logs/fast_03_before_submit.png", full_page=True)

            # Scroll al fondo para asegurar que el botón sea visible
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(0.8)

            # Intentar con varios selectores por si el texto varía
            submitted = False
            for btn_name in ["Registrar visita", "Registrar", "Guardar", "Confirmar visita"]:
                try:
                    btn = page.get_by_role("button", name=btn_name)
                    if await btn.count() > 0 and await btn.is_visible(timeout=2_000):
                        await btn.click(timeout=8_000)
                        submitted = True
                        logger.info(f"[Fast] Botón '{btn_name}' clickeado")
                        break
                except Exception:
                    continue

            if not submitted:
                # Fallback: buscar botón submit
                try:
                    btn = page.locator('button[type="submit"]').last
                    if await btn.count() > 0:
                        await btn.click(timeout=8_000)
                        submitted = True
                except Exception:
                    pass

            if not submitted:
                await page.screenshot(path="logs/fast_error_submit.png", full_page=True)
                await browser.close()
                return {"ok": False, "mensaje": "No se encontró el botón Registrar visita. Ver fast_error_submit.png"}

            # Esperar hasta 10 segundos a que la página cambie o aparezca mensaje de éxito
            submit_url = page.url
            success = False
            for tick in range(20):
                await asyncio.sleep(0.5)
                current_url = page.url
                if current_url != submit_url:
                    success = True
                    logger.info(f"[Fast] Redirigido a: {current_url}")
                    break
                try:
                    body = await page.evaluate("document.body.innerText")
                    body_l = body.lower()
                    if tick == 3:  # log del body a los 1.5s para diagnóstico
                        logger.info(f"[Fast] Body post-submit (1.5s): {body[:300]!r}")
                    if any(k in body_l for k in ["registrado con éxito", "visita registrada",
                                                  "¡listo", "registro exitoso", "fue registrada",
                                                  "gracias", "comercio registrado"]):
                        success = True
                        logger.info("[Fast] Texto de éxito detectado")
                        break
                    if "este campo es obligatorio" in body_l:
                        logger.warning("[Fast] Campo obligatorio vacío")
                        break
                except Exception:
                    pass

            await page.screenshot(path="logs/fast_debug.png", full_page=True)
            logger.info(f"[Fast] Post-submit URL: {page.url}, success={success}")

            await browser.close()
            if success:
                return {"ok": True, "mensaje": f"'{nombre}' registrado exitosamente en Fast"}
            return {"ok": False, "mensaje": f"Formulario enviado pero no se confirmó éxito — revisar fast_debug.png"}

        except PWTimeout as e:
            logger.error(f"[Fast] Timeout: {e}")
            try:
                await page.screenshot(path="logs/fast_error.png", full_page=True)
            except Exception:
                pass
            try:
                await browser.close()
            except Exception:
                pass
            return {"ok": False, "mensaje": f"Timeout: {str(e)[:120]}"}

        except Exception as e:
            logger.error(f"[Fast] Error: {e}", exc_info=True)
            try:
                await browser.close()
            except Exception:
                pass
            return {"ok": False, "mensaje": f"Error: {str(e)[:200]}"}


# ═══════════════════════════════════════════════════════════════════════════
# ACTUALIZAR VISITA: cambia el estado de un lead ya registrado en Fast
# ═══════════════════════════════════════════════════════════════════════════

# Mapeo de estados del dashboard → (Etapa visita Fast, Motivo Fast, TPV)
# TPV siempre 5000000 (lo pide Fast en cualquier visita post-Calificación)
STATUS_VISITA_MAPPING = {
    "interesado": {
        "etapa": "Negociación",
        "motivo": "Acuerdo de plazos",
        "tpv": "5000000",
    },
    "opt_out": {
        "etapa": "Rechazada",
        "motivo": "Competencia con mejores cargos",
        "tpv": "5000000",
    },
    "no_interesado": {
        "etapa": "Rechazada",
        "motivo": "Competencia con mejores cargos",
        "tpv": "5000000",
    },
}


async def _actualizar_visita_fast(nombre: str, telefono: str, nuevo_estado: str) -> dict:
    """
    Busca un comercio ya registrado en Fast por teléfono, hace clic en
    'Registrar visita' y actualiza Etapa + Motivo (+ TPV si aplica).
    """
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    if not _session_exists():
        return {"ok": False, "mensaje": "Sin sesion guardada. Ejecuta: python fast_login_manual.py"}

    cfg = STATUS_VISITA_MAPPING.get(nuevo_estado.lower())
    if not cfg:
        return {"ok": False, "mensaje": f"Estado '{nuevo_estado}' no mapeado para actualizar visita"}

    etapa_target = cfg["etapa"]
    motivo_target = cfg["motivo"]
    tpv_target = cfg.get("tpv")

    telefono_fmt = _formatear_telefono(telefono)

    import shutil as _shutil
    _chromium_path = (
        _shutil.which("chromium") or
        _shutil.which("chromium-browser") or
        None
    )
    _headless = os.getenv("FAST_HEADLESS", "true").lower() != "false"

    async with async_playwright() as p:
        launch_kwargs = dict(
            headless=_headless,
            slow_mo=200 if _headless else 100,
            args=(
                ["--disable-blink-features=AutomationControlled"]
                if not _headless else
                [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            ),
        )
        if _chromium_path and _headless:
            launch_kwargs["executable_path"] = _chromium_path

        browser = await p.chromium.launch(**launch_kwargs)
        context_kwargs = dict(
            storage_state=SESSION_FILE,
            viewport={"width": 1280, "height": 800},
            locale="es-CL",
            # Pre-otorgar permiso de geolocalizacion (evita popup de Chrome
            # que bloquea la automatizacion). Coordenadas: Santiago de Chile.
            permissions=["geolocation"],
            geolocation={"latitude": -33.4489, "longitude": -70.6693},
        )
        if _headless:
            context_kwargs["user_agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()

        try:
            # 1) Ir al home de Point Fast
            await page.goto(FAST_URL, timeout=30_000)
            await page.wait_for_load_state("networkidle", timeout=15_000)
            logger.info(f"[FastUpd] URL inicial: {page.url}")

            if "login" in page.url or "identificacion" in page.url:
                await browser.close()
                return {"ok": False, "mensaje": "Sesion expirada. Renueva con fast_login_manual.py"}

            # 2) Click en "Comercios" del sidebar
            comercios_clicked = False
            for sel in ['a:has-text("Comercios")', 'button:has-text("Comercios")', 'text=Comercios']:
                try:
                    loc = page.locator(sel).first
                    await loc.wait_for(state="visible", timeout=5_000)
                    await loc.click(timeout=5_000)
                    comercios_clicked = True
                    logger.info(f"[FastUpd] Click 'Comercios' OK via {sel}")
                    break
                except Exception:
                    continue

            if not comercios_clicked:
                await page.screenshot(path="logs/fastupd_no_comercios.png")
                await browser.close()
                return {"ok": False, "mensaje": "No se encontró el botón 'Comercios' en el sidebar"}

            await page.wait_for_load_state("networkidle", timeout=15_000)
            await asyncio.sleep(1.5)

            # 3) Buscar por NOMBRE (columna 'negocio' de la BD leads)
            # Espera extra para que el input este completamente listo
            await asyncio.sleep(2)
            await page.screenshot(path="logs/fastupd_pre_search.png")

            buscado = nombre
            search_filled = False
            for sel in [
                'input[placeholder*="buscar" i]',
                'input[placeholder*="search" i]',
                'input[type="search"]',
                'input[type="text"]',
            ]:
                try:
                    loc = page.locator(sel).first
                    await loc.wait_for(state="visible", timeout=4_000)
                    # Triple click para seleccionar todo + click directo
                    await loc.click(click_count=3, timeout=3_000)
                    await asyncio.sleep(0.3)
                    await page.keyboard.press("Delete")
                    await asyncio.sleep(0.2)
                    # Tipear caracter por caracter (mas confiable que fill en SPAs)
                    await loc.press_sequentially(buscado, delay=50)
                    # Verificar que el valor quedo
                    actual = await loc.input_value()
                    logger.info(f"[FastUpd] Tipeado en {sel}: esperado='{buscado}' actual='{actual}'")
                    if buscado.lower() in actual.lower():
                        search_filled = True
                        break
                except Exception as e:
                    logger.debug(f"[FastUpd] Selector {sel} fallo: {e}")
                    continue

            if not search_filled:
                # Fallback: tipear con keyboard global tras focus
                buscado = telefono_fmt
                for sel in ['input[type="text"]', 'input[type="search"]', 'input']:
                    try:
                        loc = page.locator(sel).first
                        await loc.wait_for(state="visible", timeout=4_000)
                        await loc.focus()
                        await page.keyboard.press("Control+a")
                        await page.keyboard.press("Delete")
                        await page.keyboard.type(buscado, delay=50)
                        actual = await loc.input_value()
                        if actual:
                            search_filled = True
                            logger.info(f"[FastUpd] Fallback keyboard.type OK: '{actual}'")
                            break
                    except Exception:
                        continue

            await asyncio.sleep(2.5)
            await page.screenshot(path="logs/fastupd_search.png")

            # 4) Click en el card del resultado usando MOUSE REAL
            # JS .click() no dispara la navegación del SPA - hay que usar coordenadas del mouse
            await asyncio.sleep(2)  # esperar render del resultado

            # Obtener coordenadas del card más específico que contiene el nombre
            card_info = await page.evaluate("""
                (nombre) => {
                    const norm = (s) => (s||'').trim().toLowerCase();
                    const target = norm(nombre);
                    const candidates = [...document.querySelectorAll('a, button, [role="button"], [class*="card"], [class*="item"], li, article, div')];
                    const matches = candidates.filter(el => {
                        const t = norm(el.innerText);
                        if (!t.includes(target)) return false;
                        if (t.length > 800) return false;
                        const r = el.getBoundingClientRect();
                        return r.width > 200 && r.height > 40 && r.height < 300 && r.top > 0;
                    });
                    matches.sort((a, b) => {
                        const ra = a.getBoundingClientRect();
                        const rb = b.getBoundingClientRect();
                        return (ra.width * ra.height) - (rb.width * rb.height);
                    });
                    if (matches.length === 0) return null;
                    const el = matches[0];
                    el.scrollIntoView({block: 'center', behavior: 'instant'});
                    const r = el.getBoundingClientRect();
                    return {
                        x: r.left + r.width / 2,
                        y: r.top + r.height / 2,
                        tag: el.tagName,
                        cls: (el.className || '').toString().substring(0, 80),
                        w: r.width,
                        h: r.height,
                        count: matches.length
                    };
                }
            """, nombre)

            row_clicked = False
            if isinstance(card_info, dict) and "x" in card_info:
                logger.info(f"[FastUpd] Card encontrado: {card_info}")
                await asyncio.sleep(0.5)
                # Click real con mouse en las coordenadas del centro del card
                await page.mouse.click(card_info["x"], card_info["y"])
                row_clicked = True
                logger.info(f"[FastUpd] Click mouse en ({card_info['x']:.0f}, {card_info['y']:.0f})")

            if not row_clicked:
                # Fallback: selectores Playwright tradicionales con click real
                for sel in [
                    f'a:has-text("{nombre}")',
                    f'[role="link"]:has-text("{nombre}")',
                    f'.andes-card:has-text("{nombre}")',
                    f'[class*="card"]:has-text("{nombre}")',
                    f'li:has-text("{nombre}")',
                ]:
                    try:
                        loc = page.locator(sel).first
                        await loc.wait_for(state="visible", timeout=4_000)
                        await loc.scroll_into_view_if_needed()
                        await loc.click(timeout=5_000)
                        row_clicked = True
                        logger.info(f"[FastUpd] Click card via fallback {sel}")
                        break
                    except Exception:
                        continue

            if not row_clicked:
                await page.screenshot(path="logs/fastupd_no_row.png")
                await browser.close()
                return {"ok": False, "mensaje": f"Lead '{nombre}' encontrado en buscador pero no se pudo abrir su card"}

            # Esperar navegacion: la URL deberia cambiar al detalle del comercio
            try:
                await page.wait_for_url("**/comercio/**", timeout=10_000)
            except Exception:
                # No matchea ese patron, esperar networkidle
                await page.wait_for_load_state("networkidle", timeout=10_000)
            await asyncio.sleep(1.5)
            logger.info(f"[FastUpd] URL tras click card: {page.url}")

            await page.wait_for_load_state("networkidle", timeout=10_000)
            await asyncio.sleep(1.5)

            # 5) Click en "Registrar visita"
            visita_clicked = False
            for sel in [
                'button:has-text("Registrar visita")',
                'a:has-text("Registrar visita")',
                'text=Registrar visita',
            ]:
                try:
                    loc = page.locator(sel).first
                    await loc.wait_for(state="visible", timeout=8_000)
                    await loc.click()
                    visita_clicked = True
                    logger.info(f"[FastUpd] Click 'Registrar visita' OK via {sel}")
                    break
                except Exception:
                    continue

            if not visita_clicked:
                await page.screenshot(path="logs/fastupd_no_btn.png")
                await browser.close()
                return {"ok": False, "mensaje": "No se encontró el botón 'Registrar visita' en la ficha del lead"}

            await page.wait_for_load_state("networkidle", timeout=15_000)
            await asyncio.sleep(2)
            await page.screenshot(path="logs/fastupd_form.png")

            # 6) Click en la card de Etapa de la negociación (Negociación / Rechazada)
            import re as _re

            async def click_etapa(etapa_text):
                pattern = _re.compile(r'^\s*' + _re.escape(etapa_text) + r'\s*$', _re.IGNORECASE)
                for selector in ['button', 'td', 'li', '[role="gridcell"]']:
                    locs = page.locator(selector).filter(has_text=pattern)
                    n = await locs.count()
                    for i in range(min(n, 8)):
                        loc = locs.nth(i)
                        try:
                            box = await loc.bounding_box()
                            if box and box['x'] > 250 and box['width'] > 40 and box['height'] > 15:
                                await loc.scroll_into_view_if_needed()
                                await asyncio.sleep(0.4)
                                await loc.click(timeout=5_000)
                                logger.info(f"[FastUpd] Etapa '{etapa_text}' click OK")
                                return True
                        except Exception:
                            continue
                return False

            etapa_ok = await click_etapa(etapa_target)
            if not etapa_ok:
                await page.screenshot(path="logs/fastupd_no_etapa.png")
                await browser.close()
                return {"ok": False, "mensaje": f"No se encontró la etapa '{etapa_target}' en el formulario"}

            await asyncio.sleep(1.5)

            # 7) Abrir dropdown Motivo y seleccionar la opción
            try:
                motivo_coords = await page.evaluate("""
                    () => {
                        const label = [...document.querySelectorAll('span.andes-dropdown__label, label')]
                            .find(e => (e.innerText||'').trim().startsWith('Motivo'));
                        if (!label) return null;
                        const dropdown = label.closest('.andes-dropdown');
                        if (!dropdown) return null;
                        const trigger = dropdown.querySelector('.andes-dropdown__trigger, button');
                        if (!trigger) return null;
                        trigger.scrollIntoView({block: 'center', behavior: 'instant'});
                        const r = trigger.getBoundingClientRect();
                        return {x: r.left + r.width/2, y: r.top + r.height/2};
                    }
                """)
                if motivo_coords:
                    await page.mouse.click(motivo_coords['x'], motivo_coords['y'])
                else:
                    triggers = page.locator('button.andes-dropdown__trigger')
                    if await triggers.count() >= 2:
                        await triggers.nth(1).click(timeout=5_000)

                await asyncio.sleep(1.2)

                motivo_clicked = False
                for sel in [
                    f'.andes-list__item:has-text("{motivo_target}")',
                    f'li.andes-list__item:has-text("{motivo_target}")',
                    f'li:has-text("{motivo_target}")',
                    f'[role="option"]:has-text("{motivo_target}")',
                    f'text={motivo_target}',
                ]:
                    try:
                        opt = page.locator(sel).first
                        if await opt.count() > 0 and await opt.is_visible(timeout=2_000):
                            await opt.scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await opt.click(timeout=4_000)
                            motivo_clicked = True
                            logger.info(f"[FastUpd] Motivo '{motivo_target}' OK")
                            break
                    except Exception:
                        continue

                if not motivo_clicked:
                    logger.warning(f"[FastUpd] No se pudo seleccionar motivo '{motivo_target}'")

                await asyncio.sleep(0.5)
                # Confirmar selección si hay botón "Confirmar"
                for btn_sel in ['button.andes-button:has-text("Confirmar")', 'button:has-text("Confirmar")']:
                    try:
                        btn = page.locator(btn_sel).first
                        if await btn.count() > 0 and await btn.is_visible(timeout=2_000):
                            await btn.click(timeout=5_000)
                            break
                    except Exception:
                        continue
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"[FastUpd] Error seteando motivo: {e}")

            # 8) Si hay TPV, llenarlo
            if tpv_target:
                tpv_filled = False
                for sel in [
                    'input[name*="tpv" i]',
                    'input[placeholder*="volumen" i]',
                    'input[placeholder*="tpv" i]',
                    'input[id*="tpv" i]',
                    'input[type="number"]',
                ]:
                    try:
                        loc = page.locator(sel).first
                        if await loc.count() > 0 and await loc.is_visible(timeout=2_000):
                            await loc.scroll_into_view_if_needed()
                            await loc.click()
                            await loc.fill(tpv_target)
                            tpv_filled = True
                            logger.info(f"[FastUpd] TPV '{tpv_target}' llenado via {sel}")
                            break
                    except Exception:
                        continue
                if not tpv_filled:
                    logger.info("[FastUpd] Campo TPV no encontrado (puede no aplicar para este estado)")

            # 9) Submit final
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(0.8)

            submitted = False
            for btn_name in ["Registrar visita", "Registrar", "Guardar", "Confirmar visita"]:
                try:
                    btn = page.get_by_role("button", name=btn_name)
                    if await btn.count() > 0 and await btn.is_visible(timeout=2_000):
                        await btn.click(timeout=8_000)
                        submitted = True
                        logger.info(f"[FastUpd] Botón '{btn_name}' clickeado")
                        break
                except Exception:
                    continue

            if not submitted:
                try:
                    btn = page.locator('button[type="submit"]').last
                    if await btn.count() > 0:
                        await btn.click(timeout=8_000)
                        submitted = True
                except Exception:
                    pass

            if not submitted:
                await page.screenshot(path="logs/fastupd_no_submit.png", full_page=True)
                await browser.close()
                return {"ok": False, "mensaje": "No se encontró botón submit final"}

            # Esperar éxito
            submit_url = page.url
            success = False
            for tick in range(20):
                await asyncio.sleep(0.5)
                if page.url != submit_url:
                    success = True
                    break
                try:
                    body = (await page.evaluate("document.body.innerText")).lower()
                    if any(k in body for k in ["visita registrada", "registrado con éxito",
                                                "fue registrada", "comercio actualizado"]):
                        success = True
                        break
                except Exception:
                    pass

            await page.screenshot(path="logs/fastupd_done.png", full_page=True)
            await browser.close()

            if success:
                return {"ok": True, "mensaje": f"Visita actualizada: {etapa_target} / {motivo_target}"}
            return {"ok": False, "mensaje": "Submit hecho pero no se confirmó éxito — revisar fastupd_done.png"}

        except PWTimeout as e:
            logger.error(f"[FastUpd] Timeout: {e}")
            try:
                await page.screenshot(path="logs/fastupd_timeout.png", full_page=True)
                await browser.close()
            except Exception:
                pass
            return {"ok": False, "mensaje": f"Timeout: {str(e)[:120]}"}

        except Exception as e:
            logger.error(f"[FastUpd] Error: {e}", exc_info=True)
            try:
                await browser.close()
            except Exception:
                pass
            return {"ok": False, "mensaje": f"Error: {str(e)[:200]}"}


@fast_bp.route('/<int:lead_id>/actualizar-visita', methods=['POST'])
def actualizar_visita_fast_endpoint(lead_id):
    """
    Actualiza el estado de visita en Fast para un lead que ya está registrado.
    Body: { "estado": "interesado" | "opt_out" | "no_interesado" }
    """
    data = request.get_json() or {}
    estado = (data.get("estado") or "").strip().lower()

    if estado not in STATUS_VISITA_MAPPING:
        return jsonify({"ok": False, "mensaje": f"Estado no soportado: {estado}"}), 400

    conn = get_db()
    lead = conn.execute(
        "SELECT id, name, phone, fast_ok FROM leads WHERE id = ?", (lead_id,)
    ).fetchone()
    conn.close()

    if not lead:
        return jsonify({"ok": False, "mensaje": "Lead no encontrado"}), 404

    lead = dict(lead)
    if not lead.get("fast_ok"):
        return jsonify({
            "ok": False,
            "mensaje": "Lead no está registrado en Fast (registrar primero)"
        }), 400

    nombre = lead["name"]
    telefono = lead["phone"]

    # Proxy a servidor local si está configurado
    fast_local_url = os.getenv("FAST_LOCAL_URL", "").strip()
    fast_local_token = os.getenv("FAST_LOCAL_TOKEN", "").strip()

    if fast_local_url:
        try:
            import requests
            url = fast_local_url.rstrip("/") + "/actualizar-visita-fast"
            resp = requests.post(
                url,
                json={"nombre": nombre, "telefono": telefono, "estado": estado},
                headers={"X-Fast-Token": fast_local_token},
                timeout=300,
            )
            if resp.status_code == 401:
                return jsonify({"ok": False, "mensaje": "Token inválido en servidor local"}), 500
            return jsonify(resp.json())
        except requests.exceptions.ConnectionError:
            return jsonify({
                "ok": False,
                "mensaje": "Servidor local Fast no disponible"
            }), 503
        except Exception as e:
            logger.error(f"[FastUpd] Error proxy: {e}", exc_info=True)
            return jsonify({"ok": False, "mensaje": f"Error proxy: {str(e)[:200]}"}), 500

    # Modo local directo (no recomendado en Railway)
    return jsonify({"ok": False, "mensaje": "FAST_LOCAL_URL no configurado"}), 500


@fast_bp.route('/<int:lead_id>/registrar-fast', methods=['POST'])
def registrar_en_fast(lead_id):
    if not MP_EMAIL or not MP_PASSWORD:
        return jsonify({"ok": False, "mensaje": "Faltan MP_FAST_EMAIL o MP_FAST_PASSWORD en .env"}), 500

    data      = request.get_json() or {}
    nombre    = data.get("nombre", "").strip()
    telefono  = data.get("telefono", "").strip()
    direccion = data.get("direccion", "").strip()

    if not nombre or not telefono:
        return jsonify({"ok": False, "mensaje": "nombre y telefono son obligatorios"}), 400

    # ── Si hay FAST_LOCAL_URL configurada, hacemos proxy al servidor local ──
    fast_local_url = os.getenv("FAST_LOCAL_URL", "").strip()
    fast_local_token = os.getenv("FAST_LOCAL_TOKEN", "").strip()

    if fast_local_url:
        # Modo proxy: la automatización corre en la PC del usuario via Cloudflare Tunnel
        try:
            import requests
            url = fast_local_url.rstrip("/") + "/registrar-fast"
            logger.info(f"[Fast] Proxy a servidor local: {url}")
            resp = requests.post(
                url,
                json={"nombre": nombre, "telefono": telefono, "direccion": direccion},
                headers={"X-Fast-Token": fast_local_token},
                timeout=300,
            )
            if resp.status_code == 401:
                return jsonify({"ok": False, "mensaje": "Token inválido en servidor local"}), 500
            result = resp.json()
        except requests.exceptions.ConnectionError:
            return jsonify({
                "ok": False,
                "mensaje": "Servidor local Fast no disponible. Verifica que tu PC esté prendida con fast_local_server.py corriendo."
            }), 503
        except Exception as e:
            logger.error(f"[Fast] Error proxy a local: {e}", exc_info=True)
            return jsonify({"ok": False, "mensaje": f"Error proxy local: {str(e)[:200]}"}), 500
    else:
        # Modo legacy: ejecutar playwright directamente (en Railway no funciona por IP)
        try:
            import threading as _threading
            result_holder = [None]
            error_holder  = [None]

            def _run():
                import asyncio as _asyncio
                _loop = _asyncio.new_event_loop()
                _asyncio.set_event_loop(_loop)
                try:
                    result_holder[0] = _loop.run_until_complete(
                        _registrar_en_fast(nombre, telefono, direccion)
                    )
                except Exception as exc:
                    error_holder[0] = exc
                finally:
                    _loop.close()
                    _asyncio.set_event_loop(None)

            t = _threading.Thread(target=_run, daemon=True)
            t.start()
            t.join(timeout=300)

            if error_holder[0] is not None:
                raise error_holder[0]
            if result_holder[0] is None:
                raise RuntimeError("Timeout: la automatización no completó en 5 minutos")
            result = result_holder[0]
        except Exception as e:
            logger.error(f"[Fast] Error en automatización: {e}", exc_info=True)
            return jsonify({"ok": False, "mensaje": f"Error: {str(e)[:200]}"}), 500

    try:
        conn = get_db()
        if result["ok"]:
            # Marcar fast_ok y actualizar status a 'enviado'
            conn.execute("UPDATE leads SET fast_ok=1 WHERE id=?", (lead_id,))
            conn.execute(
                """INSERT INTO lead_status (lead_id, status, notes, updated_at)
                   VALUES (?, 'enviado', ?, datetime('now','localtime'))
                   ON CONFLICT(lead_id) DO UPDATE SET
                       status = 'enviado',
                       notes  = excluded.notes,
                       updated_at = excluded.updated_at""",
                (lead_id, result["mensaje"])
            )
        else:
            # Solo guardar nota informativa sin cambiar status cuando falla
            conn.execute(
                """INSERT INTO lead_status (lead_id, status, notes, updated_at)
                   VALUES (?, 'no_enviado', ?, datetime('now','localtime'))
                   ON CONFLICT(lead_id) DO UPDATE SET
                       notes = excluded.notes,
                       updated_at = excluded.updated_at""",
                (lead_id, result["mensaje"])
            )
        conn.commit()
    except Exception as e:
        logger.warning(f"[Fast] No se pudo guardar log en BD: {e}")

    return jsonify({**result, "lead_id": lead_id})


@fast_bp.route('/fast-session-status', methods=['GET'])
def fast_session_status():
    activa = _session_exists()
    tiene_env = bool(os.getenv("FAST_SESSION_JSON", "").strip())
    return jsonify({
        "session_activa": activa,
        "tiene_env_var": tiene_env,
        "instrucciones": (
            "Sesion lista." if activa
            else "Ejecuta: python fast_login_manual.py  — luego copia el contenido de data/fast_session.json como variable FAST_SESSION_JSON en Railway"
        )
    })


@fast_bp.route('/fast-upload-session', methods=['POST'])
def fast_upload_session():
    """Sube el contenido de fast_session.json directamente (para Railway)."""
    data = request.get_json() or {}
    session_json = data.get("session_json", "").strip()
    if not session_json:
        return jsonify({"ok": False, "error": "session_json requerido"}), 400
    try:
        import json as _json
        _json.loads(session_json)  # validar que sea JSON válido
        os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            f.write(session_json)
        logger.info("[Fast] Sesión subida manualmente vía API")
        return jsonify({"ok": True, "mensaje": "Sesión guardada. Ya puedes usar el botón Fast."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400
