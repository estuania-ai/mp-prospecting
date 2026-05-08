"""
Email Prospecting Tool - Routes
Búsqueda, contactos, campañas, seguimientos, inteligencia, reuniones, PDFs
"""
from flask import Blueprint, request, jsonify, send_file, render_template_string
from flask_login import current_user, login_required
from database import get_db
import asyncio
import logging
import re
import time
import uuid
import io
from datetime import datetime, timedelta
from urllib.parse import urlparse

MANUAL_SEND_THROTTLE_SECS = 2   # Regla 6: pausa entre envíos manuales masivos

logger = logging.getLogger(__name__)
email_bp = Blueprint('email_tool', __name__)

_jobs = {}

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', re.IGNORECASE)
SKIP_DOMAINS = {
    'sentry.io', 'wixpress.com', 'example.com', 'domain.com',
    'yourcompany.com', 'googleapis.com', 'gstatic.com', 'w3.org',
    'schema.org', 'mercadopago.com', 'mercadolibre.com',
    'facebook.com', 'instagram.com', 'twitter.com', 'youtube.com', 'google.com',
}
SKIP_PREFIXES = ('noreply', 'no-reply', 'donotreply', 'mailer', 'bounce',
                 'spam', 'webmaster', 'postmaster')

RUBROS = [
    'cafetería', 'pastelería', 'sushi', 'emporio', 'clínica dental',
    'pizzería', 'librería', 'veterinaria', 'florería', 'oftalmología',
    'tienda de muebles', 'lubricentro', 'frenos', 'spa',
    'restaurant de pollos asados', 'clínica de belleza', 'gimnasio',
    'ferretería',
]

# ── Per-rubro email content ───────────────────────────────────────────────────

_FOOD_BENEFITS = [
    {'icon': '📅', 'text': 'Mismo día',       'sub': 'Empiezas a cobrar hoy'},
    {'icon': '🚫', 'text': 'Sin contrato',    'sub': 'Ni mensualidad'},
    {'icon': '🎫', 'text': 'Pluxee · Edenred','sub': 'Vales de alimentación'},
    {'icon': '📊', 'text': 'Panel claro',     'sub': 'Tus ventas al día'},
]
_STD_BENEFITS = [
    {'icon': '📅', 'text': 'Mismo día',       'sub': 'Empiezas a cobrar hoy'},
    {'icon': '🚫', 'text': 'Sin contrato',    'sub': 'Ni mensualidad'},
    {'icon': '💳', 'text': 'Cuotas 3-6-12',  'sub': 'Sin interés para tus clientes'},
    {'icon': '📊', 'text': 'Panel claro',     'sub': 'Tus ventas al día'},
]
_AUTO_BENEFITS = [
    {'icon': '📅', 'text': 'Mismo día',       'sub': 'Empiezas a cobrar hoy'},
    {'icon': '🚫', 'text': 'Sin contrato',    'sub': 'Ni mensualidad'},
    {'icon': '⚡', 'text': 'Cobro en segundos','sub': 'Débito, crédito y QR'},
    {'icon': '📊', 'text': 'Panel claro',     'sub': 'Tus ventas al día'},
]

RUBRO_EMAIL_CONTENT = {
    'cafetería': {
        'subject': 'Esto tarda menos que preparar un espresso — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que preparar', 'h3': 'un espresso',
        'preheader': 'En serio, es así de fácil.',
        'icon': '⏱️', 'icon_strip': 'Empiezas a cobrar el mismo día — sin trámites',
        'header_bg': '#1A1A2E',
        'pain_bg': '#FFF8E1',
        'pain': 'Sé que los dueños de cafetería no tienen tiempo para procesos complicados — por eso te escribo directo y sin rodeos.',
        'body': 'Sumarte a Mercado Pago toma menos de lo que crees. Nada que instalar. Nada que esperar.',
        'benefits': [
            {'icon': '📅', 'text': 'Mismo día',        'sub': 'Empiezas a cobrar hoy'},
            {'icon': '🚫', 'text': 'Sin contrato',     'sub': 'Ni mensualidad'},
            {'icon': '🎫', 'text': 'Pluxee · Edenred', 'sub': 'Sin trámite extra'},
            {'icon': '📊', 'text': 'Panel claro',      'sub': 'Tus ventas al día'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+cafeter%C3%ADa',
    },
    'pastelería': {
        'subject': 'Esto tarda menos que decorar una torta — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que decorar', 'h3': 'una torta',
        'preheader': 'Y puede proteger cada venta pequeña de tu día.',
        'icon': '🎂', 'icon_strip': 'Para pastelerías que quieren cobrar sin perder margen en cada café y trozo de torta',
        'header_bg': '#4A1C3A',
        'pain_bg': '#FFF0F8',
        'pain': 'Sé que en una pastelería la venta promedio es baja — un café, un pastel, una empanada. Si cada vez que alguien paga con tarjeta te descuentan un cargo fijo, en las ventas pequeñas prácticamente no ganas nada. Eso se acumula mucho al final del mes.',
        'body': 'Mercado Pago no cobra cargo fijo por transacción ni mensualidad por tener la máquina. Cobras cada café y cada torta sin perder margen, aceptas vales de alimentación para el almuerzo corporativo y el dinero entra al instante para reponer insumos.',
        'benefits': [
            {'icon': '🚫', 'text': 'Sin cargo fijo por venta',      'sub': 'Cada café y trozo de torta protege su margen'},
            {'icon': '🎫', 'text': 'Acepta Edenred, Pluxee y Junaeb','sub': 'Captura el almuerzo y la once corporativa'},
            {'icon': '⚡', 'text': 'Plata al instante',             'sub': 'Repone harina, mantequilla y cremas sin esperar'},
            {'icon': '👥', 'text': 'Cuentas de colaboradores',      'sub': 'Cada cajero con acceso propio y restringido'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+paster%C3%ADa',
    },
    'sushi': {
        'subject': 'Esto tarda menos que preparar un roll — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que preparar', 'h3': 'un roll',
        'preheader': 'Y puede cubrir el salmón de mañana sin problema.',
        'icon': '🍣', 'icon_strip': 'Para restaurantes de sushi que necesitan liquidez diaria para insumos frescos',
        'header_bg': '#0D2B2B',
        'pain_bg': '#F0FFFE',
        'pain': 'Sé que en un sushi el insumo más caro — el salmón, el atún, el camarón — hay que comprarlo fresco cada uno o dos días. Esperar 48 horas hábiles para que te depositen las ventas del fin de semana no es una opción cuando el proveedor llega el lunes.',
        'body': 'Con Mercado Pago la plata de tus ventas entra al instante, incluso el domingo por la noche, lista para reponer el stock del día siguiente. Y atraes al cliente corporativo del almuerzo con vales de alimentación.',
        'benefits': [
            {'icon': '⚡', 'text': 'Liquidez inmediata',              'sub': 'Compra insumos frescos sin esperar depósitos'},
            {'icon': '🎫', 'text': 'Acepta Edenred, Pluxee y Junaeb', 'sub': 'El almuerzo de oficinas y estudiantes'},
            {'icon': '🚫', 'text': 'Sin arriendo mensual',            'sub': 'Sin costo fijo aunque baje la semana'},
            {'icon': '👥', 'text': 'Cuentas de colaboradores',        'sub': 'Garzones cobran de forma independiente'},
        ],
        'cta_text': '→ Conversemos 15 minutos esta semana',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+restaurante+de+sushi',
    },
    'emporio': {
        'subject': 'Esto tarda menos que cortar un trozo de queso — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que cortar', 'h3': 'un trozo de queso',
        'preheader': 'Y puede ahorrarte dinero en cada venta pequeña.',
        'icon': '🧀', 'icon_strip': 'Para emporios que tienen muchas ventas de ticket bajo y no quieren perder margen',
        'header_bg': '#1F3320',
        'pain_bg': '#F2FFF3',
        'pain': 'Sé que en un emporio vendes decenas de cosas pequeñas al día — un café, una bebida, un trozo de queso, unos fiambres. El problema es cuando el cobro de cada una tiene un cargo fijo que se te va directo del bolsillo, especialmente en las ventas más chicas.',
        'body': 'Mercado Pago no cobra cargo fijo por transacción ni arriendo mensual por la máquina. Cobras cada venta pequeña sin perder margen, aceptas vales de alimentación y el dinero entra al instante para reponer stock fresco.',
        'benefits': [
            {'icon': '🚫', 'text': 'Sin cargo fijo por transacción', 'sub': 'Cuida el margen en ventas de ticket bajo'},
            {'icon': '🎫', 'text': 'Acepta Edenred y Pluxee',        'sub': 'El trabajador del barrio te elige a ti'},
            {'icon': '⚡', 'text': 'Liquidez inmediata',             'sub': 'Repone fiambres y frescos sin esperar'},
            {'icon': '👥', 'text': 'Cuentas de colaboradores',       'sub': 'Cada cajero con su acceso restringido'},
        ],
        'cta_text': '→ Hablemos 15 minutos esta semana',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+emporio',
    },
    'pizzería': {
        'subject': 'Esto tarda menos que hornear una pizza — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que hornear', 'h3': 'una pizza',
        'preheader': 'Y puede cambiar cómo cobras cada noche.',
        'icon': '🍕', 'icon_strip': 'Para pizzerías que quieren cobrar más, perder menos y reponer insumos sin esperar',
        'header_bg': '#6B1A0F',
        'pain_bg': '#FFF5F0',
        'pain': 'Sé que en una pizzería el viernes en la noche es tu momento de oro — pero si los cobros del fin de semana no entran hasta el martes, el lunes compras harina, queso y salsa con lo que quedó en caja. Eso no debería ser así.',
        'body': 'Con Mercado Pago el dinero entra al instante — incluso sábado y domingo — para que puedas reponer stock el lunes sin problema. Y además atrapas al almuerzo corporativo con vales Edenred y Pluxee.',
        'benefits': [
            {'icon': '⚡', 'text': 'Plata al instante',        'sub': 'Incluso fines de semana y feriados'},
            {'icon': '🎫', 'text': 'Acepta Edenred y Pluxee',  'sub': 'Captura el almuerzo de oficinas y empresas'},
            {'icon': '🚫', 'text': 'Sin cargo fijo por venta', 'sub': 'Protege tu margen en pedidos pequeños'},
            {'icon': '👥', 'text': 'Cuentas de colaboradores', 'sub': 'Cada cajero cobra sin ver el saldo total'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+pizzer%C3%ADa',
    },
    'restaurant de pollos asados': {
        'subject': 'Esto tarda menos que asar un pollo completo — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que asar', 'h3': 'un pollo completo',
        'preheader': 'En serio, es así de rápido sumarse.',
        'icon': '🍗', 'icon_strip': 'Para restaurantes de pollos asados que quieren cobrar cada almuerzo sin perder una venta',
        'header_bg': '#5C3000',
        'pain_bg': '#FFF8EE',
        'pain': 'Sé que en un restaurante de pollos asados el almuerzo es tu peak del día — 45 minutos donde entra todo. Si un cliente quiere pagar con su vale de alimentación o tarjeta y no puedes cobrarle, la mesa se pierde y no vuelve.',
        'body': 'Con Mercado Pago aceptas Edenred, Pluxee y Junaeb en el almuerzo corporativo, el dinero entra al instante para comprar el pollo del día siguiente, y cada garzonero cobra de forma independiente desde la máquina.',
        'benefits': [
            {'icon': '🎫', 'text': 'Acepta vales de alimentación', 'sub': 'Edenred, Pluxee y Junaeb en cada almuerzo'},
            {'icon': '⚡', 'text': 'Plata al instante',            'sub': 'Compra insumos frescos sin esperar'},
            {'icon': '🚫', 'text': 'Sin cargo fijo por venta',     'sub': 'Protege el margen en ventas de ticket bajo'},
            {'icon': '👥', 'text': 'Cuentas de colaboradores',     'sub': 'Control por turno sin exponer el saldo'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+restaurant+de+pollos',
    },
    'clínica dental': {
        'subject': 'Esto tarda menos que una limpieza dental — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que una', 'h3': 'limpieza dental',
        'preheader': 'En serio, es así de simple.',
        'icon': '🦷', 'icon_strip': 'Para clínicas dentales que quieren cobrar sin complicaciones',
        'header_bg': '#0F2A4A',
        'pain_bg': '#EAF4FF',
        'pain': 'Sé que en una clínica dental los gastos son altos — implantes, ortodoncia, blanqueamientos — y perder una venta porque el paciente no puede pagar todo de una sola vez es algo que pasa todos los días.',
        'body': 'Con Mercado Pago tus pacientes pueden pagar en cuotas sin interés y tú recibes la plata completa al instante. Sin trámites. Sin esperas.',
        'benefits': [
            {'icon': '💳', 'text': 'Cuotas sin interés',     'sub': 'Tu paciente paga en partes, tú cobras al tiro'},
            {'icon': '⚡', 'text': 'Abono inmediato',         'sub': 'Sin esperar 48 hrs como Transbank'},
            {'icon': '🚫', 'text': '$0 arriendo mensual',    'sub': 'Sin cobro fijo aunque tengas meses bajos'},
            {'icon': '🔗', 'text': 'Link de pago WhatsApp',  'sub': 'Asegura reservas y abonos antes de la cita'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+cl%C3%ADnica+dental',
    },
    'frenos': {
        'subject': 'Esto tarda menos que cambiar unos frenos — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que cambiar', 'h3': 'unos frenos',
        'preheader': 'Y es igual de importante para tu negocio.',
        'icon': '🔧', 'icon_strip': 'Para talleres de frenos que quieren cobrar sin perder ventas grandes',
        'header_bg': '#1A1A1A',
        'pain_bg': '#FFF9E6',
        'pain': 'Sé que en un taller de frenos las reparaciones importantes pueden costar bastante — y cuando el cliente dice que no tiene todo ahora la venta se va o la pospones, y el auto sale sin el trabajo completo.',
        'body': 'Con Mercado Pago el cliente paga en cuotas sin interés y tú recibes la plata completa al instante para cubrir repuestos y mano de obra. Sin esperar, sin riesgos.',
        'benefits': [
            {'icon': '💳', 'text': 'Cuotas sin interés',    'sub': 'Repuestos caros, pagados en partes'},
            {'icon': '🔗', 'text': 'Link de pago WhatsApp', 'sub': 'Abono por repuesto antes de pedirlo'},
            {'icon': '⚡', 'text': 'Plata al instante',     'sub': 'Sin los 48 hrs de Transbank'},
            {'icon': '🚫', 'text': '$0 arriendo mensual',   'sub': 'Sin costo fijo en tu taller'},
        ],
        'cta_text': '→ Conversemos 15 minutos esta semana',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+taller+de+frenos',
    },
    'lubricentro': {
        'subject': 'Esto tarda menos que un cambio de aceite — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que un', 'h3': 'cambio de aceite',
        'preheader': 'Cobrar con Mercado Pago es así de simple.',
        'icon': '🛢️', 'icon_strip': 'Para lubricentros que quieren cobrar rápido y sin costos fijos',
        'header_bg': '#1C2B1A',
        'pain_bg': '#F0FFF4',
        'pain': 'Sé que en un lubricentro el flujo de caja diario es clave — repones aceite, filtros y líquidos todo el tiempo. Esperar 48 horas para que Transbank te deposite es plata que no puedes usar para reabastecerte hoy.',
        'body': 'Con Mercado Pago el dinero entra al instante, incluso los fines de semana, y tus clientes pueden pagar servicios mayores en cuotas. Sin mensualidad ni letra chica.',
        'benefits': [
            {'icon': '⚡', 'text': 'Abono inmediato',        'sub': 'Repone stock sin esperar depósitos'},
            {'icon': '💳', 'text': 'Cuotas sin interés',    'sub': 'Servicios grandes, pagados en partes'},
            {'icon': '🚫', 'text': '$0 mensualidad',        'sub': 'Sin cobro fijo aunque baje la venta'},
            {'icon': '🔗', 'text': 'Link de pago WhatsApp', 'sub': 'Abono por repuesto antes de pedirlo'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+lubricentro',
    },
    'oftalmología': {
        'subject': 'Esto tarda menos que un examen de vista — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que un', 'h3': 'examen de vista',
        'preheader': 'Cobrar bien no requiere lentes especiales.',
        'icon': '👁️', 'icon_strip': 'Para centros de oftalmología que quieren cobrar sin perder pacientes',
        'header_bg': '#0A2744',
        'pain_bg': '#EAF4FF',
        'pain': 'Sé que en oftalmología los costos son reales — lentes de marca, cirugías refractivas, lentes de contacto anuales. Cuando el paciente dice que es mucho de una vez la venta se pierde o se fracciona a mano sin garantías.',
        'body': 'Con Mercado Pago tus pacientes pagan en cuotas sin interés y tú recibes la plata completa al instante. Además, aseguras las horas con un link de pago previo por WhatsApp.',
        'benefits': [
            {'icon': '💳', 'text': 'Cuotas sin interés',    'sub': 'Cirugías y lentes al alcance de todos'},
            {'icon': '🔗', 'text': 'Link de pago WhatsApp', 'sub': 'Asegura la consulta antes de la hora'},
            {'icon': '⚡', 'text': 'Abono inmediato',       'sub': 'Sin demoras para reponer insumos'},
            {'icon': '🚫', 'text': '$0 mensualidad',        'sub': 'Sin costos fijos en recepción'},
        ],
        'cta_text': '→ Agenda una llamada de 15 minutos',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+centro+de+oftalmolog%C3%ADa',
    },
    'spa': {
        'subject': 'Esto tarda menos que un masaje de relajación — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que un', 'h3': 'masaje de relajación',
        'preheader': 'Cobrar bien también es bienestar para tu negocio.',
        'icon': '🌿', 'icon_strip': 'Para spas que quieren asegurar reservas y cobrar sin fricción',
        'header_bg': '#2A3A30',
        'pain_bg': '#F0FFF6',
        'pain': 'Sé que en un spa el problema no es conseguir clientes — es cuando cancelan a última hora una sesión que reservaron hace días y tú ya asignaste la hora, la terapeuta y los insumos.',
        'body': 'Con Mercado Pago aseguras cada reserva con un abono previo por WhatsApp y tus clientes pueden pagar paquetes completos en cuotas sin interés. Tú recibes la plata al instante.',
        'benefits': [
            {'icon': '🔗', 'text': 'Link de pago WhatsApp', 'sub': 'Reserva asegurada con abono previo'},
            {'icon': '💳', 'text': 'Cuotas sin interés',    'sub': 'Paquetes completos, pagados en partes'},
            {'icon': '⚡', 'text': 'Abono inmediato',       'sub': 'Plata en tu cuenta el mismo día'},
            {'icon': '🚫', 'text': '$0 mensualidad',        'sub': 'Sin costo fijo en recepción'},
        ],
        'cta_text': '→ Conversemos 15 minutos esta semana',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+spa',
    },
    'tienda de muebles': {
        'subject': 'Esto tarda menos que elegir un sofá — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que elegir', 'h3': 'un sofá',
        'preheader': 'Y puede salvar ventas que creías perdidas.',
        'icon': '🛋️', 'icon_strip': 'Para tiendas de muebles que quieren vender más sin perder pedidos a medida',
        'header_bg': '#2D1F0E',
        'pain_bg': '#FFF8F0',
        'pain': 'Sé que en una tienda de muebles el riesgo más grande es fabricar a medida y que el cliente se arrepienta. Un sofá personalizado, un closet o una cocina puede tomar semanas — y sin abono de por medio, el riesgo lo asumes tú.',
        'body': 'Con Mercado Pago cobras un abono por WhatsApp antes de fabricar, y el cliente paga el saldo en cuotas sin interés. Tú recibes la plata completa al instante para cubrir materiales.',
        'benefits': [
            {'icon': '🔗', 'text': 'Link de pago WhatsApp', 'sub': 'Abono antes de fabricar — protege tu taller'},
            {'icon': '💳', 'text': 'Cuotas sin interés',   'sub': 'Muebles caros, accesibles para tu cliente'},
            {'icon': '⚡', 'text': 'Abono inmediato',      'sub': 'Cubre materiales sin esperar'},
            {'icon': '🚫', 'text': '$0 mensualidad',       'sub': 'Sin costo fijo aunque el mes sea lento'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+tienda+de+muebles',
    },
    'veterinaria': {
        'subject': 'Esto tarda menos que una consulta veterinaria — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que una', 'h3': 'consulta veterinaria',
        'preheader': 'Y puede salvar la venta cuando más importa.',
        'icon': '🐾', 'icon_strip': 'Para veterinarias que no quieren perder una cirugía por problemas de pago',
        'header_bg': '#1A3040',
        'pain_bg': '#EAF6FF',
        'pain': 'Sé que en una veterinaria los momentos más difíciles son cuando el dueño del animal dice que no tiene todo ahora en medio de una urgencia — una cirugía, una hospitalización, un tratamiento largo. Es un momento muy incómodo para todos.',
        'body': 'Con Mercado Pago tus clientes pagan en cuotas sin interés y tú recibes la plata completa al instante para cubrir medicamentos e insumos. Sin esperas, sin fricciones.',
        'benefits': [
            {'icon': '💳', 'text': 'Cuotas sin interés',    'sub': 'Cirugías urgentes sin barreras de pago'},
            {'icon': '⚡', 'text': 'Abono inmediato',        'sub': 'Cubre insumos y medicamentos al tiro'},
            {'icon': '🔗', 'text': 'Link de pago WhatsApp', 'sub': 'Abono para reservar horas de especialista'},
            {'icon': '🚫', 'text': '$0 mensualidad',        'sub': 'Sin costo fijo en tu clínica'},
        ],
        'cta_text': '→ Hablemos 15 minutos esta semana',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+veterinaria',
    },
    'florería': {
        'subject': 'Esto tarda menos que armar un ramo de flores — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que armar', 'h3': 'un ramo de flores',
        'preheader': 'Y puede proteger cada venta pequeña que haces al día.',
        'icon': '🌸', 'icon_strip': 'Para florerías que compran flores frescas todos los días y no pueden esperar depósitos',
        'header_bg': '#2D1040',
        'pain_bg': '#FDF0FF',
        'pain': 'Sé que en una florería el desafío más concreto es este: las flores hay que comprarlas frescas casi todos los días en el terminal, y si las ventas del fin de semana no entran hasta el martes hábil, el lunes temprano no tienes la liquidez para abastecerte bien.',
        'body': 'Con Mercado Pago la plata de tus ventas entra al instante — el domingo por la noche, el feriado, cuando sea — lista para que vayas al terminal el lunes con capital en la cuenta. Y en fechas especiales como el Día de la Madre, ofreces cuotas sin interés para arreglos grandes y cobras el domicilio por anticipado con un link de pago por WhatsApp.',
        'benefits': [
            {'icon': '⚡', 'text': 'Plata al instante',     'sub': 'Compra flores frescas sin esperar depósitos'},
            {'icon': '🔗', 'text': 'Link de pago WhatsApp', 'sub': 'Cobra el domicilio antes de preparar el arreglo'},
            {'icon': '💳', 'text': 'Cuotas sin interés',   'sub': 'Arreglos para eventos y Día de la Madre en partes'},
            {'icon': '🚫', 'text': '$0 mensualidad',       'sub': 'Sin costo fijo en los meses más tranquilos'},
        ],
        'cta_text': '→ Conversemos 15 minutos esta semana',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+florer%C3%ADa',
    },
    'librería': {
        'subject': 'Esto tarda menos que encontrar un libro buscado — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que encontrar', 'h3': 'un libro buscado',
        'preheader': 'Y puede cambiar cómo gestionas tu caja cada día.',
        'icon': '📚', 'icon_strip': 'Para librerías que quieren cobrar mejor y no perder ventas grandes ni chicas',
        'header_bg': '#1E2D4A',
        'pain_bg': '#EEF4FF',
        'pain': 'Sé que en una librería hay dos momentos críticos al año — la vuelta a clases y las fiestas — donde el ticket sube mucho. Pero el resto del año, cada venta es un destacador, una goma o una tarjeta. Si cada cobro pequeño tiene un cargo fijo, al final del día ya perdiste margen sin darte cuenta.',
        'body': 'Con Mercado Pago no pagas cargo fijo por transacción ni arriendo mensual — cobras cada venta pequeña con margen protegido. Y en temporada alta, ofreces cuotas sin interés para la lista completa de textos escolares y recibes la plata al instante.',
        'benefits': [
            {'icon': '🚫', 'text': 'Sin cargo fijo por venta', 'sub': 'Cada goma y destacador conserva su margen'},
            {'icon': '💳', 'text': 'Cuotas sin interés',       'sub': 'Lista de textos completa, pagada en partes'},
            {'icon': '🔗', 'text': 'Link de pago WhatsApp',    'sub': 'Cobra la reserva de un libro antes de encargarlo'},
            {'icon': '⚡', 'text': 'Plata al instante',        'sub': 'Liquidez inmediata para encargar a editoriales'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+librer%C3%ADa',
    },
    'clínica de belleza': {
        'subject': 'Esto tarda menos que aplicar un botox — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que aplicar', 'h3': 'un botox',
        'preheader': 'En serio, es así de rápido.',
        'icon': '💎', 'icon_strip': 'Para clínicas de belleza que quieren cobrar más y perder menos citas',
        'header_bg': '#3D1A4A',
        'pain_bg': '#F9F0FF',
        'pain': 'Sé que en una clínica de belleza el dolor más grande no es el láser — es cuando una paciente cancela a última hora una sesión que ya preparaste y no puedes recuperar ese tiempo.',
        'body': 'Con Mercado Pago tus clientes aseguran su reserva con un abono por WhatsApp y pagan el resto en cuotas sin interés. Tú recibes la plata al instante, sin esperar.',
        'benefits': [
            {'icon': '💳', 'text': 'Cuotas sin interés',    'sub': 'Tratamientos caros, accesibles para tu cliente'},
            {'icon': '🔗', 'text': 'Link de pago WhatsApp', 'sub': 'Asegura reservas antes de la sesión'},
            {'icon': '⚡', 'text': 'Abono inmediato',       'sub': 'Plata en tu cuenta el mismo día'},
            {'icon': '🚫', 'text': '$0 mensualidad',        'sub': 'Sin costo fijo en meses tranquilos'},
        ],
        'cta_text': '→ Agenda 15 minutos conmigo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+cl%C3%ADnica+de+belleza',
    },
    'gimnasio': {
        'subject': 'Esto tarda menos que tu calentamiento — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que tu', 'h3': 'calentamiento',
        'preheader': 'Cobrar bien también es parte del entrenamiento.',
        'icon': '💪', 'icon_strip': 'Para gimnasios que quieren cobrar membresías y servicios sin fricción',
        'header_bg': '#1A1A2E',
        'pain_bg': '#FFF5E6',
        'pain': 'Sé que en un gimnasio enero y marzo son meses de oro — pero julio y agosto bajan. Igual tienes que pagar arriendo, instructores y equipos. Un cobro fijo mensual por la máquina en esos meses es la última cuenta que necesitas.',
        'body': 'Con Mercado Pago cobras membresías, sesiones de personal trainer y planes anuales en cuotas sin interés. El dinero entra al instante y no pagas nada fijo por tener el datáfono.',
        'benefits': [
            {'icon': '💳', 'text': 'Cuotas sin interés',    'sub': 'Planes anuales pagados en partes'},
            {'icon': '🚫', 'text': '$0 mensualidad',        'sub': 'Sin cobro fijo en meses de baja'},
            {'icon': '⚡', 'text': 'Abono inmediato',       'sub': 'Plata disponible el mismo día'},
            {'icon': '🔗', 'text': 'Link de pago WhatsApp', 'sub': 'Reserva clases con abono previo'},
        ],
        'cta_text': '→ Agenda 15 minutos conmigo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+gimnasio',
    },
    'ferretería': {
        'subject': 'Esto tarda menos que buscar una llave inglesa — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que buscar', 'h3': 'una llave inglesa',
        'preheader': 'El punto de venta que se adapta a tu ferretería.',
        'icon': '🔩', 'icon_strip': 'Para ferreterías que quieren cobrar más rápido y sin costos fijos',
        'header_bg': '#2C1A00',
        'pain_bg': '#FFF8E1',
        'pain': 'Sé que en una ferretería los montos son variados — desde un tornillo hasta una partida de materiales de construcción. El problema es cuando el cliente quiere pagar en cuotas o no lleva efectivo y la venta grande se cae en el mesón.',
        'body': 'Con Mercado Pago tus clientes pagan en cuotas sin interés en ventas grandes, y en las ventas chicas no pierdes margen porque no cobramos cargo fijo por transacción ni mensualidad. Nada que instalar. Empiezas el mismo día.',
        'benefits': [
            {'icon': '💳', 'text': 'Cuotas sin interés',       'sub': 'Venta grande de materiales sin excusas'},
            {'icon': '🚫', 'text': 'Sin cargo fijo',            'sub': 'Cada venta pequeña conserva su margen'},
            {'icon': '🔗', 'text': 'Link de pago WhatsApp',     'sub': 'Cobra presupuestos antes de entregar'},
            {'icon': '⚡', 'text': 'Plata al instante',         'sub': 'Repone stock sin esperar depósitos'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+ferreter%C3%ADa',
    },
    'propuesta': {
        'subject': 'Una propuesta para tu negocio — Mercado Pago',
        'h1': 'Una propuesta', 'h2': 'para tu', 'h3': 'negocio 🌿',
        'preheader': 'Cobros más rápidos · Más medios de pago · Más ventas.',
        'icon': '🌿', 'icon_strip': 'Propuesta comercial personalizada · Mercado Pago',
        'header_bg': '#1E3328',
        'pain_bg': '#F0FFF4',
        'pain': 'Estuve revisando tu negocio y creo que puedo ayudarte a agilizar los cobros en tienda y aumentar conversión incorporando Mercado Pago Point — sin costo mensual ni cambios en tu operación actual.',
        'body': 'Con Mercado Pago Point puedes aceptar todos los medios de pago presenciales y a distancia, con acreditación inmediata los 365 días del año:',
        'benefits': [
            {'icon': '💳', 'text': 'Tarjeta débito/crédito',   'sub': 'Todos los medios de pago presenciales'},
            {'icon': '📱', 'text': 'Pagos NFC sin contacto',   'sub': 'Sin fricción en caja, más rápido'},
            {'icon': '🔗', 'text': 'Links de pago WhatsApp',   'sub': 'Vende a distancia por Instagram y WA'},
            {'icon': '⚡', 'text': 'Acreditación inmediata',   'sub': 'Plata disponible el mismo día, 365 días'},
        ],
        'cta_text': '→ Agendar una llamada de 15 minutos',
        'wa_text': 'Hola+Juan%2C+me+interesa+saber+m%C3%A1s+sobre+la+propuesta+de+Mercado+Pago',
        'next_steps': {
            'title': '📋 Propuesta de siguiente paso',
            'intro': '¿Les parece si agendamos una llamada de 15 minutos para entender:',
            'items': [
                'Volumen estimado de transacciones / ticket promedio',
                'Si necesitan 1 o más POS',
                'Si quieren sumar pagos a distancia (links de pago)',
            ],
            'closing': 'Con esa info, les envío una propuesta cerrada (modelo recomendado + condiciones).',
        },
    },
    'tienda ecológica': {
        'subject': 'Una propuesta para tu tienda — Mercado Pago',
        'h1': 'Más ventas,', 'h2': 'menos', 'h3': 'fricción en caja 🌿',
        'preheader': 'Cobros digitales sin costo mensual para tu tienda.',
        'icon': '🌱', 'icon_strip': 'Para tiendas que quieren cobrar mejor y vender más',
        'header_bg': '#1E3328',
        'pain_bg': '#F0FFF4',
        'pain': 'Sé que en una tienda el flujo de clientes es constante — cada cliente que no puede pagar con tarjeta es una venta que se pierde. Y pagar mensualidad fija por la máquina en los meses tranquilos duele.',
        'body': 'Con Mercado Pago Point aceptas todos los medios de pago presenciales y a distancia. Sin costo mensual, con plata disponible el mismo día.',
        'benefits': [
            {'icon': '💳', 'text': 'Todos los medios de pago', 'sub': 'Débito, crédito, prepago y NFC'},
            {'icon': '🚫', 'text': '$0 mensualidad',           'sub': 'Sin cobro fijo en meses tranquilos'},
            {'icon': '🔗', 'text': 'Links de pago WhatsApp',   'sub': 'Vende pedidos a distancia por redes'},
            {'icon': '⚡', 'text': 'Plata al instante',        'sub': 'Liquidez inmediata los 365 días'},
        ],
        'cta_text': '→ Conversemos 15 minutos esta semana',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+tienda',
    },
    # ── Nuevos rubros ──────────────────────────────────────────────────────────
    'peluquería': {
        'subject': 'Esto tarda menos que un corte de cabello — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que un corte', 'h3': 'de cabello ✂️',
        'preheader': 'Acepta tarjetas, vales y más desde el primer día.',
        'icon': '✂️', 'icon_strip': 'Para peluquerías y salones que quieren cobrar sin complicaciones',
        'header_bg': '#2A0A2E',
        'pain_bg': '#FDF5FF',
        'pain': 'Sé que en una peluquería cada hora cuenta y no puedes perder tiempo en cobros lentos. Cuando un cliente no puede pagar con tarjeta, la venta se pierde — y con ella el margen del día.',
        'body': 'Mercado Pago te da el terminal sin arriendo, con plata disponible al instante y la posibilidad de cobrar vales de alimentación para tus clientes de oficina.',
        'benefits': [
            {'icon': '📅', 'text': 'Mismo día',          'sub': 'Empiezas a cobrar hoy'},
            {'icon': '🚫', 'text': 'Sin contrato',        'sub': 'Ni mensualidad'},
            {'icon': '🎫', 'text': 'Pluxee · Edenred',    'sub': 'Vales de alimentación'},
            {'icon': '📊', 'text': 'Panel claro',         'sub': 'Tus ventas al día'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+peluquer%C3%ADa',
    },
    'lavandería': {
        'subject': 'Esto tarda menos que un ciclo de lavado — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que un ciclo', 'h3': 'de lavado 👕',
        'preheader': 'Cobra con tarjeta desde el primer día, sin mensualidad.',
        'icon': '👕', 'icon_strip': 'Para lavanderías que quieren agilizar el cobro y retener clientes',
        'header_bg': '#0A1F3A',
        'pain_bg': '#F0F8FF',
        'pain': 'Sé que en una lavandería el cliente quiere dejar su ropa y pagar rápido. Si no aceptas tarjeta, pierde tiempo buscando efectivo — y a veces simplemente se va.',
        'body': 'Con Mercado Pago cobras en segundos con cualquier tarjeta o vale. Sin costo mensual, con liquidez al instante para cubrir detergentes, insumos y servicios.',
        'benefits': [
            {'icon': '⚡', 'text': 'Cobro en segundos',  'sub': 'Débito, crédito y prepago'},
            {'icon': '🚫', 'text': 'Sin mensualidad',    'sub': '$0 arriendo por el equipo'},
            {'icon': '📅', 'text': 'Plata al instante',  'sub': 'Los 365 días del año'},
            {'icon': '📊', 'text': 'Panel claro',        'sub': 'Tus ventas al día'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+lavander%C3%ADa',
    },
    'almacén': {
        'subject': 'Esto tarda menos que atender la caja — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que atender', 'h3': 'la caja 🏪',
        'preheader': 'Acepta vales Edenred, Pluxee y Junaeb en tu almacén.',
        'icon': '🏪', 'icon_strip': 'Para almacenes y minimarkets que quieren captar más clientes',
        'header_bg': '#1A2B1A',
        'pain_bg': '#F4FFF4',
        'pain': 'Sé que en un almacén el margen es ajustado y cada venta perdida duele. Los clientes de oficinas cercanas pagan con vales de alimentación — si no los aceptas, van a la competencia.',
        'body': 'Con el Point Smart de Mercado Pago aceptas Edenred, Pluxee y Junaeb junto con cualquier tarjeta, en un solo equipo. Sin arriendo mensual y con plata disponible al instante.',
        'benefits': [
            {'icon': '🎫', 'text': 'Edenred · Pluxee · Junaeb', 'sub': 'Captura el almuerzo del barrio'},
            {'icon': '🚫', 'text': 'Sin mensualidad',            'sub': '$0 arriendo por el equipo'},
            {'icon': '⚡', 'text': 'Plata al instante',          'sub': 'Para reponer stock sin esperar'},
            {'icon': '📊', 'text': 'Panel claro',                'sub': 'Tus ventas al día'},
        ],
        'cta_text': '→ Conversemos esta semana',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+almac%C3%A9n',
    },
    'ferretería': {
        'subject': 'Esto tarda menos que buscar un tornillo — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que buscar', 'h3': 'un tornillo 🔩',
        'preheader': 'Cobra en cuotas, recibe el total al instante.',
        'icon': '🔩', 'icon_strip': 'Para ferreterías que quieren cobrar más y reponer stock sin esperar',
        'header_bg': '#2B1A00',
        'pain_bg': '#FFFBF0',
        'pain': 'Sé que en una ferretería las ventas varían mucho: desde un tornillo hasta una herramienta de $200.000. En las ventas grandes el cliente pide cuotas — y si no puedes ofrecerlas, pierde la venta.',
        'body': 'Con Mercado Pago cobras en cuotas con cualquier tarjeta y recibes el total de inmediato. Sin mensualidad fija y con plata disponible para reponer inventario el mismo día.',
        'benefits': [
            {'icon': '💳', 'text': 'Cuotas 3-6-12',    'sub': 'Tú cobras el total desde el día 1'},
            {'icon': '🚫', 'text': 'Sin mensualidad',   'sub': '$0 arriendo por el equipo'},
            {'icon': '⚡', 'text': 'Plata al instante', 'sub': 'Repone inventario sin esperar'},
            {'icon': '📊', 'text': 'Panel claro',       'sub': 'Tus ventas al día'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+ferreter%C3%ADa',
    },
    'farmacia': {
        'subject': 'Esto tarda menos que despachar una receta — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que despachar', 'h3': 'una receta 💊',
        'preheader': 'Cobra con tarjeta y vales desde el primer día, sin mensualidad.',
        'icon': '💊', 'icon_strip': 'Para farmacias independientes que quieren cobrar sin complicaciones',
        'header_bg': '#0A2A1A',
        'pain_bg': '#F0FFF8',
        'pain': 'Sé que en una farmacia independiente el cliente compara con las cadenas grandes. Si no aceptas tarjeta o el proceso de cobro es lento, te costará retener a quienes pasan a buscar sus medicamentos.',
        'body': 'Con Mercado Pago cobras con cualquier tarjeta y vales de alimentación sin contratos. Sin mensualidad fija, con plata disponible el mismo día para reponer tus medicamentos.',
        'benefits': [
            {'icon': '💳', 'text': 'Todos los medios de pago', 'sub': 'Débito, crédito, prepago y NFC'},
            {'icon': '🚫', 'text': 'Sin mensualidad',          'sub': '$0 arriendo por el equipo'},
            {'icon': '⚡', 'text': 'Plata al instante',        'sub': 'Los 365 días del año'},
            {'icon': '📊', 'text': 'Panel claro',              'sub': 'Tus ventas al día'},
        ],
        'cta_text': '→ Conversemos 15 minutos esta semana',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+farmacia',
    },
    'taller': {
        'subject': 'Esto tarda menos que cambiar un neumático — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que cambiar', 'h3': 'un neumático 🔨',
        'preheader': 'Cobra reparaciones en cuotas, recibe el total desde el día 1.',
        'icon': '🔨', 'icon_strip': 'Para talleres mecánicos que quieren cobrar más y crecer sin esperar',
        'header_bg': '#1A1000',
        'pain_bg': '#FFFDF0',
        'pain': 'Sé que en un taller las reparaciones pueden ser de $150.000 a $500.000 — montos donde el cliente pide cuotas. Si no puedes ofrecerlas, o tardas en cobrar, pierdes esa venta.',
        'body': 'Con Mercado Pago cobras en cuotas y recibes el total de inmediato. Sin mensualidad por el terminal y con liquidez para comprar repuestos el mismo día.',
        'benefits': [
            {'icon': '💳', 'text': 'Cuotas 3-6-12',    'sub': 'Tú cobras el total desde el día 1'},
            {'icon': '🚫', 'text': 'Sin mensualidad',   'sub': '$0 arriendo por el equipo'},
            {'icon': '⚡', 'text': 'Plata al instante', 'sub': 'Compra repuestos sin esperar'},
            {'icon': '📊', 'text': 'Panel claro',       'sub': 'Tus ventas al día'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+taller',
    },
    'mueblería': {
        'subject': 'Esto tarda menos que elegir un sillón — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que elegir', 'h3': 'un sillón 🛋️',
        'preheader': 'Ofrece cuotas sin interés y cierra más ventas hoy.',
        'icon': '🛋️', 'icon_strip': 'Para mueblerías que quieren vender en cuotas y cobrar completo al instante',
        'header_bg': '#2D1F0E',
        'pain_bg': '#FFFAF5',
        'pain': 'Sé que en una mueblería el ticket promedio es alto y casi siempre el cliente pregunta si puede pagar en cuotas. Si no tienes esa opción, muchas veces el cliente se va a buscar financiamiento en otro lado.',
        'body': 'Con Mercado Pago ofreces cuotas 3, 6 o 12 meses sin interés y recibes el total de inmediato. Sin mensualidad fija y con liquidez para reponer tu stock sin esperar.',
        'benefits': [
            {'icon': '💳', 'text': 'Cuotas 3-6-12',    'sub': 'Sin interés para tus clientes'},
            {'icon': '🚫', 'text': 'Sin mensualidad',   'sub': '$0 arriendo por el equipo'},
            {'icon': '⚡', 'text': 'Plata al instante', 'sub': 'Repone stock sin descapitalizarte'},
            {'icon': '📊', 'text': 'Panel claro',       'sub': 'Tus ventas al día'},
        ],
        'cta_text': '→ Conversemos esta semana',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+muebler%C3%ADa',
    },
    'panadería': {
        'subject': 'Esto tarda menos que hornear una marraqueta — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que hornear', 'h3': 'una marraqueta 🥖',
        'preheader': 'Acepta vales Edenred y Pluxee en tu panadería desde hoy.',
        'icon': '🥖', 'icon_strip': 'Para panaderías y amasanderías que quieren captar más clientes en hora punta',
        'header_bg': '#3A2000',
        'pain_bg': '#FFFBF0',
        'pain': 'Sé que en una panadería el ritmo es intenso desde la madrugada y la hora del desayuno es crítica. Los clientes de oficinas y colegios cercanos pagan con vales — si no los aceptas, van a la competencia.',
        'body': 'Con el Point Smart cobras vales Edenred, Pluxee y Junaeb junto con cualquier tarjeta. Sin mensualidad y con plata disponible al instante para comprar harina y insumos cada día.',
        'benefits': [
            {'icon': '🎫', 'text': 'Edenred · Pluxee · Junaeb', 'sub': 'Capta el desayuno y la colación'},
            {'icon': '🚫', 'text': 'Sin mensualidad',            'sub': '$0 arriendo por el equipo'},
            {'icon': '⚡', 'text': 'Plata al instante',          'sub': 'Compra insumos frescos sin esperar'},
            {'icon': '📊', 'text': 'Panel claro',                'sub': 'Tus ventas al día'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+panader%C3%ADa',
    },
    'bazar': {
        'subject': 'Esto tarda menos que envolver un regalo — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que envolver', 'h3': 'un regalo 🎁',
        'preheader': 'Cobra con tarjeta sin mensualidad desde hoy.',
        'icon': '🎁', 'icon_strip': 'Para bazares y tiendas de regalos que quieren cobrar sin fricciones',
        'header_bg': '#2A0A1A',
        'pain_bg': '#FFF5F8',
        'pain': 'Sé que en un bazar las ventas van desde pequeños detalles hasta regalos de alto valor. Cuando el cliente no puede pagar con tarjeta porque no llevas efectivo, la venta se pierde — y con ella una posible venta recurrente.',
        'body': 'Con Mercado Pago cobras con cualquier tarjeta sin mensualidad. Plata disponible al instante para reponer tu inventario antes de fechas especiales.',
        'benefits': [
            {'icon': '💳', 'text': 'Todos los medios de pago', 'sub': 'Débito, crédito y prepago'},
            {'icon': '🚫', 'text': 'Sin mensualidad',          'sub': '$0 arriendo por el equipo'},
            {'icon': '⚡', 'text': 'Plata al instante',        'sub': 'Los 365 días del año'},
            {'icon': '📊', 'text': 'Panel claro',              'sub': 'Tus ventas al día'},
        ],
        'cta_text': '→ Conversemos 15 minutos esta semana',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+bazar',
    },
    'carnicería': {
        'subject': 'Esto tarda menos que cortar un costillar — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que cortar', 'h3': 'un costillar 🥩',
        'preheader': 'Liquida las ventas al instante para comprar mercadería fresca.',
        'icon': '🥩', 'icon_strip': 'Para carnicerías que necesitan liquidez diaria para mercadería fresca',
        'header_bg': '#3A0000',
        'pain_bg': '#FFF5F5',
        'pain': 'Sé que en una carnicería la mercadería se compra fresca cada uno o dos días — y no puedes esperar 48 horas hábiles para que el banco te deposite las ventas del fin de semana.',
        'body': 'Con Mercado Pago la plata de cada venta llega al instante, incluso el domingo. Sin mensualidad por el terminal, con cobro de vales de alimentación incluido.',
        'benefits': [
            {'icon': '⚡', 'text': 'Plata al instante',          'sub': 'Compra mercadería fresca sin esperar'},
            {'icon': '🎫', 'text': 'Edenred · Pluxee · Junaeb',  'sub': 'Vales de alimentación incluidos'},
            {'icon': '🚫', 'text': 'Sin mensualidad',            'sub': '$0 arriendo por el equipo'},
            {'icon': '📊', 'text': 'Panel claro',                'sub': 'Tus ventas al día'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+carnicer%C3%ADa',
    },
    'botillería': {
        'subject': 'Esto tarda menos que descorchar una botella — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que descorchar', 'h3': 'una botella 🍾',
        'preheader': 'Cobra con tarjeta sin mensualidad desde el primer día.',
        'icon': '🍾', 'icon_strip': 'Para botillerías que quieren cobrar más y perder menos ventas',
        'header_bg': '#1A0A2E',
        'pain_bg': '#F8F5FF',
        'pain': 'Sé que en una botillería las ventas son frecuentes y de monto variado, y muchos clientes llegan sin efectivo. Cada vez que no puedes cobrar con tarjeta, pierdes esa venta — y el cliente puede no volver.',
        'body': 'Con Mercado Pago cobras con cualquier tarjeta sin mensualidad. La plata entra al instante, incluso fines de semana y festivos cuando más vendes.',
        'benefits': [
            {'icon': '💳', 'text': 'Todos los medios de pago', 'sub': 'Débito, crédito y prepago'},
            {'icon': '🚫', 'text': 'Sin mensualidad',          'sub': '$0 arriendo por el equipo'},
            {'icon': '⚡', 'text': 'Plata al instante',        'sub': 'Fines de semana y festivos'},
            {'icon': '📊', 'text': 'Panel claro',              'sub': 'Tus ventas al día'},
        ],
        'cta_text': '→ Dame 15 minutos para mostrártelo',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+botiller%C3%ADa',
    },
    'fuente de soda': {
        'subject': 'Esto tarda menos que preparar un completo — Mercado Pago',
        'h1': 'Esto tarda menos', 'h2': 'que preparar', 'h3': 'un completo 🥤',
        'preheader': 'Acepta vales Edenred y Pluxee en tu fuente de soda desde hoy.',
        'icon': '🥤', 'icon_strip': 'Para fuentes de soda que quieren captar el almuerzo y la colación',
        'header_bg': '#1A2A3A',
        'pain_bg': '#F0F8FF',
        'pain': 'Sé que en una fuente de soda la hora de almuerzo es el momento crítico. Tus clientes — muchos de ellos trabajadores de oficinas o colegios cercanos — pagan con vales de alimentación. Si no los aceptas, van a otro lado.',
        'body': 'Con el Point Smart cobras vales Edenred, Pluxee y Junaeb junto con cualquier tarjeta. Sin mensualidad y con plata disponible al instante para reponer insumos del día.',
        'benefits': [
            {'icon': '🎫', 'text': 'Edenred · Pluxee · Junaeb', 'sub': 'Capta el almuerzo del barrio'},
            {'icon': '🚫', 'text': 'Sin mensualidad',            'sub': '$0 arriendo por el equipo'},
            {'icon': '⚡', 'text': 'Plata al instante',          'sub': 'Los 365 días del año'},
            {'icon': '📊', 'text': 'Panel claro',                'sub': 'Tus ventas al día'},
        ],
        'cta_text': '→ Conversemos esta semana',
        'wa_text': 'Hola+Juan%2C+me+interesa+Mercado+Pago+para+mi+fuente+de+soda',
    },
}

# Lookup normalizado sin acentos para matching robusto
import unicodedata as _ud
def _norm(s):
    return _ud.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower().strip()

_RUBRO_NORM_MAP = {_norm(k): v for k, v in RUBRO_EMAIL_CONTENT.items()}

def _get_rubro_content(rubro: str) -> dict:
    """Busca contenido del rubro con fallback sin acentos ni guiones bajos."""
    key = (rubro or '').lower().strip().replace('_', ' ')
    return RUBRO_EMAIL_CONTENT.get(key) or _RUBRO_NORM_MAP.get(_norm(key)) or {}


def _rubro_match(template_rubro: str, contact_rubro: str) -> bool:
    """Compara rubros con tolerancia a acentos, mayúsculas y plural/singular.
    Ej: 'clínica dental' matchea 'clinicas dentales', 'Clínica Dental', etc.
    """
    t = _norm(template_rubro)
    c = _norm(contact_rubro)
    if not t:
        return True   # sin rubro en template → enviar a todos
    if t == c or t in c or c in t:
        return True
    # Word-level prefix: cada palabra significativa del template aparece como
    # prefijo en alguna palabra del contacto (maneja plural: dental/dentales)
    t_words = [w for w in t.split() if len(w) > 3]
    c_words = c.split()
    return bool(t_words) and all(
        any(cw.startswith(tw) or tw.startswith(cw) for cw in c_words)
        for tw in t_words
    )


COMUNAS_SANTIAGO = [
    'Santiago Centro', 'Providencia', 'Las Condes', 'Vitacura', 'La Florida',
    'Maipú', 'Pudahuel', 'Quilicura', 'Huechuraba', 'Recoleta',
    'Independencia', 'Conchalí', 'Renca', 'Cerro Navia', 'Lo Prado',
    'Quinta Normal', 'Estación Central', 'Cerrillos', 'Peñalolén',
    'Macul', 'Ñuñoa', 'La Reina', 'Lo Barnechea', 'Colina',
    'San Bernardo', 'El Bosque', 'La Granja', 'La Pintana',
    'San Ramón', 'Pedro Aguirre Cerda', 'Lo Espejo', 'Talagante',
    'Padre Hurtado', 'Peñaflor', 'Melipilla', 'Pirque', 'Buin',
    'Calera de Tango', 'Lampa', 'Til Til',
]


# ── Helpers ─────────────────────────────────────────────────────────────────

def _clean_emails(emails, site_domain=''):
    clean = []
    for e in emails:
        e = e.lower().strip()
        domain = e.split('@')[-1]
        if domain in SKIP_DOMAINS:
            continue
        if any(e.startswith(p) for p in SKIP_PREFIXES):
            continue
        if e.endswith(('.png', '.jpg', '.svg')):
            continue
        if e not in clean:
            clean.append(e)
    return clean


async def _extract_emails_from_url(page, url):
    try:
        await page.goto(url, timeout=15_000, wait_until='domcontentloaded')
        html = await page.content()
        emails = EMAIL_RE.findall(html)
        domain = urlparse(url).netloc.replace('www.', '')
        return _clean_emails(emails, domain)
    except Exception:
        return []


async def _try_contact_page(page, base_url):
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    for path in ['/contacto', '/contact', '/contactanos', '/nosotros', '/about']:
        try:
            await page.goto(base + path, timeout=10_000, wait_until='domcontentloaded')
            html = await page.content()
            found = EMAIL_RE.findall(html)
            clean = _clean_emails(found)
            if clean:
                return clean
        except Exception:
            continue
    return []


def _render_header_frames(c: dict):
    """
    Renderiza los frames del header a 2× resolución (1160×460) para nitidez máxima,
    luego escala a 580×230. Devuelve lista de imágenes RGB listas para exportar.
    """
    from PIL import Image, ImageDraw, ImageFont
    import pathlib, math

    assets = pathlib.Path(__file__).parent.parent / 'static' / 'email_assets'

    # Dimensiones finales y factor de escala para nitidez
    W, H   = 580, 230
    SCALE  = 2                          # renderizar a 2×
    RW, RH = W * SCALE, H * SCALE      # 1160 × 460

    # ── Fondo fuente ──────────────────────────────────────────────────────────
    bg_src = Image.open(assets / 'hdr_bg_src.jpg').convert('RGB')
    bw, bh = bg_src.size
    crop_h = int(bw * H / W)
    if crop_h > bh:
        crop_h = bh
    top = max(0, (bh - crop_h) // 3)
    # Base a 2×: margen extra para Ken Burns
    bg_base = bg_src.crop((0, top, bw, top + crop_h)).resize(
        (RW + 80, RH + 40), Image.LANCZOS)

    # ── Logo a 2× ─────────────────────────────────────────────────────────────
    logo_size = 42 * SCALE              # 84 px a 2×
    logo_img  = Image.open(assets / 'mp_logo.jpeg').convert('RGBA')
    logo_img  = logo_img.resize((logo_size, logo_size), Image.LANCZOS)
    mask = Image.new('L', (logo_size, logo_size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, logo_size - 1, logo_size - 1), fill=255)
    logo_img.putalpha(mask)

    # ── Fuentes a 2× — busca en multiples paths para Windows + Linux/nixpacks ──
    f_bold_sm = f_bold_h1 = f_bold_h2 = f_reg_pre = None

    def _find_font(candidates_bold, candidates_reg):
        """Devuelve (path_bold, path_reg) o (None, None)."""
        import os as _os, glob as _glob
        bold_path = reg_path = None
        for c in candidates_bold:
            if '*' in c:
                matches = _glob.glob(c)
                if matches:
                    bold_path = matches[0]; break
            elif _os.path.isfile(c):
                bold_path = c; break
        for c in candidates_reg:
            if '*' in c:
                matches = _glob.glob(c)
                if matches:
                    reg_path = matches[0]; break
            elif _os.path.isfile(c):
                reg_path = c; break
        return bold_path, reg_path

    bold_p, reg_p = _find_font(
        candidates_bold=[
            # PRIORIDAD: fuentes en el repo (funcionan en Windows + Linux Railway)
            str(assets / 'fonts' / 'Montserrat-Black.ttf'),    # mas impacto que Bold
            str(assets / 'fonts' / 'Montserrat-Bold.ttf'),
            str(assets / 'fonts' / 'proximanova-bold.otf'),
            # Linux nixpacks - DejaVu paths posibles
            '/nix/store/*/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/nix/store/*/share/fonts/truetype/DejaVuSans-Bold.ttf',
            '/nix/store/*/share/fonts/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            # Linux Liberation Sans (similar a Arial)
            '/nix/store/*/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            # Windows
            'C:/Windows/Fonts/arialbd.ttf',
        ],
        candidates_reg=[
            str(assets / 'fonts' / 'Montserrat-Regular.ttf'),
            str(assets / 'fonts' / 'proximanova-regular.otf'),
            '/nix/store/*/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/nix/store/*/share/fonts/truetype/DejaVuSans.ttf',
            '/nix/store/*/share/fonts/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/nix/store/*/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            'C:/Windows/Fonts/arial.ttf',
        ],
    )

    try:
        if bold_p:
            f_bold_sm = ImageFont.truetype(bold_p, 13 * SCALE)
            f_bold_h1 = ImageFont.truetype(bold_p, 22 * SCALE)
            f_bold_h2 = ImageFont.truetype(bold_p, 22 * SCALE)
        if reg_p:
            f_reg_pre = ImageFont.truetype(reg_p, 12 * SCALE)
        if not (f_bold_sm and f_reg_pre):
            raise FileNotFoundError("No se encontraron fuentes en el sistema")
        logger.info(f"[EmailTool] Fuentes header: bold={bold_p}, reg={reg_p}")
    except Exception as _e:
        logger.warning(f"[EmailTool] Fallback a fuente default: {_e}")
        f_bold_sm = f_bold_h1 = f_bold_h2 = f_reg_pre = ImageFont.load_default()

    h1  = c.get('h1', 'Esto tarda menos')
    h2  = c.get('h2', 'que imaginas')
    h3  = c.get('h3', '')
    pre = c.get('preheader', '')

    # ── Overlay a 2× ──────────────────────────────────────────────────────────
    ov_static = Image.new('RGBA', (RW, RH), (0, 0, 0, 0))
    _dov = ImageDraw.Draw(ov_static)
    for x in range(RW):
        a = int(155 - (x / RW) * 85)
        _dov.line([(x, 0), (x, RH)], fill=(0, 0, 0, a))

    FRAMES   = 4      # 4 frames × 300ms = 1.2s total — suficiente para Ken Burns suave
    frames_out = []
    for i in range(FRAMES):
        t    = i / FRAMES
        zoom = 1.0 + 0.025 * math.sin(t * math.pi)
        zw   = int((RW + 80) * zoom)
        zh   = int((RH + 40) * zoom)
        bg_z = bg_base.resize((zw, zh), Image.LANCZOS)
        ox   = (zw - RW) // 2
        oy   = (zh - RH) // 2
        frame = bg_z.crop((ox, oy, ox + RW, oy + RH)).convert('RGBA')
        frame = Image.alpha_composite(frame, ov_static)

        # Logo
        frame.paste(logo_img, (16 * SCALE, 14 * SCALE), logo_img)

        d = ImageDraw.Draw(frame)
        lx = (16 + 42 + 9) * SCALE
        d.text((lx, 15 * SCALE), 'mercado', font=f_bold_sm, fill=(255, 255, 255))
        d.text((lx, 30 * SCALE), 'pago',    font=f_bold_sm, fill=(255, 255, 255))

        y = RH - 22 * SCALE
        if pre:
            d.text((20 * SCALE, y), pre, font=f_reg_pre, fill=(190, 190, 190))
            y -= 18 * SCALE
        if h3:
            d.text((20 * SCALE, y - 26 * SCALE), h3, font=f_bold_h2, fill=(255, 230, 0))
            y -= 26 * SCALE
        d.text((20 * SCALE, y - 26 * SCALE), h2, font=f_bold_h2, fill=(255, 255, 255))
        d.text((20 * SCALE, y - 50 * SCALE), h1, font=f_bold_h1, fill=(255, 255, 255))

        # Escalar de vuelta a 1× (supersampling = nitidez máxima)
        frame_1x = frame.convert('RGB').resize((W, H), Image.LANCZOS)
        frames_out.append(frame_1x)

    return frames_out


def _compose_header_gif(c: dict) -> bytes:
    """
    WebP animado (preview browser) — color full 24-bit, Ken Burns suave.
    """
    import io
    DURATION = 200
    frames = _render_header_frames(c)
    buf = io.BytesIO()
    frames[0].save(
        buf, format='WEBP', save_all=True,
        append_images=frames[1:],
        duration=DURATION, loop=0,
        quality=92, method=6,
    )
    return buf.getvalue()


def _compose_header_gif_desktop(c: dict) -> bytes:
    """
    GIF animado — anima en Gmail desktop Y mobile.
    Paleta global derivada de todos los frames para eliminar flickering de colores.
    256 colores FASTOCTREE + dithering para máxima calidad fotográfica.
    """
    from PIL import Image
    import io
    DURATION = 300  # 4 frames × 300ms = 1.2s total
    frames = _render_header_frames(c)

    # Construir paleta global a partir de una muestra de todos los frames
    # (tomar frames 0, 4, 9 para cubrir inicio/medio/fin del Ken Burns)
    sample_indices = [0, len(frames) // 2, len(frames) - 1]
    combined_w     = frames[0].width * len(sample_indices)
    combined       = Image.new('RGB', (combined_w, frames[0].height))
    for idx, fi in enumerate(sample_indices):
        combined.paste(frames[fi], (frames[fi].width * idx, 0))
    global_palette = combined.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=0)

    # Cuantizar cada frame usando la paleta global
    frames_q = [f.quantize(colors=256, palette=global_palette, dither=1) for f in frames]

    buf = io.BytesIO()
    frames_q[0].save(
        buf, format='GIF', save_all=True,
        append_images=frames_q[1:],
        duration=DURATION, loop=0, optimize=True,
    )
    return buf.getvalue()


def _compose_pos_gif() -> bytes:
    """
    GIF animado del terminal POS con efecto float (sube/baja suavemente).
    Renderizado a 2× para nitidez máxima y escalado a 80px final.
    GIF anima en Gmail desktop Y mobile.
    """
    from PIL import Image
    import io, pathlib, math

    assets = pathlib.Path(__file__).parent.parent / 'static' / 'email_assets'
    pos_src = Image.open(assets / 'pos_terminal.png').convert('RGBA')

    # Renderizar a 2× y escalar al final (supersampling)
    SCALE    = 2
    TARGET_W = 80
    ratio    = TARGET_W / pos_src.width
    TARGET_H = int(pos_src.height * ratio)
    RW       = TARGET_W * SCALE
    RH       = TARGET_H * SCALE
    CANVAS_H = TARGET_H + 12    # margen para el float a 1×

    pos_2x   = pos_src.resize((RW, RH), Image.LANCZOS)
    CANVAS_H_2x = RH + 12 * SCALE

    FRAMES   = 16
    DURATION = 90

    frames_out = []
    for i in range(FRAMES):
        t      = i / FRAMES
        offset = int(5 * SCALE * math.sin(t * 2 * math.pi))   # oscila ±10px a 2×
        canvas = Image.new('RGBA', (RW, CANVAS_H_2x), (255, 255, 255, 255))
        canvas.paste(pos_2x, (0, 6 * SCALE + offset), pos_2x)
        # Escalar de 2× a 1×
        frame_1x = canvas.convert('RGB').resize((TARGET_W, CANVAS_H), Image.LANCZOS)
        frames_out.append(frame_1x)

    # GIF — anima en Gmail desktop Y mobile
    frames_q = [f.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=1)
                for f in frames_out]
    buf = io.BytesIO()
    frames_q[0].save(
        buf, format='GIF', save_all=True,
        append_images=frames_q[1:],
        duration=DURATION, loop=0, optimize=True,
    )
    return buf.getvalue()


def _build_html_email(body_text: str, unsubscribe_url: str, rubro: str = '',
                      contact_name: str = '', booking_url: str = '') -> str:
    """Email HTML con 100% inline styles — compatible Gmail/mobile."""
    import os
    from_name      = os.getenv('EMAIL_FROM_NAME',  'Juan Sebastián Pinto')
    from_phone_raw = os.getenv('EMAIL_FROM_PHONE', '+569 3198 5364')
    wa_number      = from_phone_raw.replace('+', '').replace(' ', '')

    c = _get_rubro_content(rubro) or {
        'h1': 'Esto tarda menos', 'h2': 'que imaginas', 'h3': '',
        'preheader': 'Empieza a cobrar con tarjeta desde hoy.',
        'icon': '💳', 'icon_strip': 'Para negocios que quieren cobrar más y mejor',
        'pain': 'Muchos negocios pierden ventas cada día solo por no tener opciones de pago digital.',
        'body': 'Con Mercado Pago lo cambias hoy, sin costo mensual ni complicaciones:',
        'benefits': _STD_BENEFITS,
        'wa_text': 'Hola+Juan%2C+me+interesa+saber+m%C3%A1s+sobre+Mercado+Pago',
        'header_bg': '#1A1A2E', 'pain_bg': '#FFF8E1',
        'cta_text': '→ Dame 15 minutos para mostrártelo',
    }

    pain_bg       = c.get('pain_bg', '#FFF8E1')
    cta_text      = c.get('cta_text', '→ Dame 15 minutos para mostrártelo')
    cta_href      = booking_url or '#'
    wa_href       = f'https://wa.me/{wa_number}?text={c.get("wa_text", "")}'
    greeting_name = contact_name or 'estimado/a'
    h3_line       = f'<br><span style="font-style:normal;color:#FFE600;">{c["h3"]}</span>' if c.get('h3') else ''

    # Next-steps box (optional — solo rubros que lo definan, e.g. 'propuesta')
    ns = c.get('next_steps')
    if ns:
        ns_items_html = ''.join(
            f'<tr><td style="padding:3px 0 3px 0;font-size:13.5px;color:#1A1A2E;line-height:1.6;">'
            f'<span style="color:#2D7A4F;font-weight:700;margin-right:7px;">✓</span>{item}'
            f'</td></tr>'
            for item in ns.get('items', [])
        )
        next_steps_html = f"""
    <!-- siguiente paso -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
      <tr><td style="background:#F0FFF4;border:1.5px solid #B7E4C7;border-radius:12px;padding:18px 20px;">
        <p style="margin:0 0 10px;font-size:14px;font-weight:700;color:#1E3328;letter-spacing:.01em;">
          {ns['title']}
        </p>
        <p style="margin:0 0 10px;font-size:13.5px;color:#333;line-height:1.6;">{ns['intro']}</p>
        <table cellpadding="0" cellspacing="0" style="margin-left:4px;">
          {ns_items_html}
        </table>
        <p style="margin:12px 0 0;font-size:13px;color:#555;line-height:1.6;font-style:italic;">
          {ns['closing']}
        </p>
      </td></tr>
    </table>"""
    else:
        next_steps_html = ''

    # Benefits — tabla 2 columnas (Gmail-safe)
    benefits = c.get('benefits', _STD_BENEFITS)
    def _bcell(b):
        return (
            f'<td width="50%" style="padding:4px;vertical-align:top;">'
            f'<table width="100%" cellpadding="0" cellspacing="0">'
            f'<tr><td style="background:#F8F6F2;border-radius:10px;padding:12px 13px;">'
            f'<table cellpadding="0" cellspacing="0"><tr>'
            f'<td style="width:28px;height:28px;background:#1A1A2E;border-radius:7px;'
            f'text-align:center;vertical-align:middle;font-size:13px;color:#fff;">{b["icon"]}</td>'
            f'<td style="padding-left:9px;vertical-align:middle;">'
            f'<p style="margin:0;font-size:12px;font-weight:700;color:#1A1A2E;line-height:1.35;">{b["text"]}</p>'
            f'<p style="margin:2px 0 0;font-size:10.5px;color:#888;">{b["sub"]}</p>'
            f'</td></tr></table>'
            f'</td></tr></table></td>'
        )
    benefits_html = (
        f'<tr>{_bcell(benefits[0])}{_bcell(benefits[1])}</tr>'
        f'<tr>{_bcell(benefits[2])}{_bcell(benefits[3])}</tr>'
    ) if len(benefits) >= 4 else ''

    # Outer wrapper
    W = 'max-width:580px;width:100%;margin:0 auto;'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Mercado Pago</title>
</head>
<body style="margin:0;padding:24px 8px;background:#F0EDE6;font-family:Arial,Helvetica,sans-serif;">
<table cellpadding="0" cellspacing="0" border="0" style="{W}">
<tr><td>

<!-- ══ HEADER — GIF animado pre-compuesto (funciona en Gmail desktop y mobile) ══ -->
<table width="580" cellpadding="0" cellspacing="0" border="0"
  style="max-width:580px;width:100%;border-radius:16px 16px 0 0;overflow:hidden;border-collapse:collapse;">
<tr>
  <td style="padding:0;line-height:0;font-size:0;">
    <img src="cid:email_hdr_anim" alt="Mercado Pago" width="580" height="230"
      style="display:block;width:100%;max-width:580px;height:auto;border:0;
             border-radius:16px 16px 0 0;">
  </td>
</tr>
<!-- barra amarilla -->
<tr>
  <td bgcolor="#FFE600" height="4"
    style="background-color:#FFE600;height:4px;font-size:0;line-height:0;">&nbsp;</td>
</tr>
</table>

<!-- ══ CARD ══ -->
<table cellpadding="0" cellspacing="0" border="0" width="100%"
  style="background:#fff;border:1.5px solid #E0D9CC;border-top:none;
         border-radius:0 0 16px 16px;overflow:hidden;">

  <!-- strip amarillo -->
  <tr><td style="background:#FFE600;padding:9px 26px;">
    <p style="margin:0;font-size:12.5px;font-weight:700;color:#1A1A2E;letter-spacing:.02em;">
      {c["icon"]} {c["icon_strip"]}
    </p>
  </td></tr>

  <!-- cuerpo -->
  <tr><td style="padding:28px 32px 26px;">

    <p style="margin:0 0 14px;font-size:15px;color:#555;">
      Hola Equipo de <strong style="font-weight:700;color:#1A1A2E;">{greeting_name}</strong>,
    </p>

    <!-- pain block -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr><td style="background:{pain_bg};border-left:3px solid #FFE600;border-radius:0 8px 8px 0;
                     padding:13px 16px;font-size:14px;color:#333;line-height:1.65;">
        {c["pain"]}
      </td></tr>
    </table>

    <p style="margin:0 0 20px;font-size:14px;color:#444;line-height:1.7;">{c["body"]}</p>

    <!-- benefits 2×2 -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
      {benefits_html}
    </table>
    {next_steps_html}
    <!-- CTA -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr><td align="center">
        <a href="{cta_href}"
          style="display:inline-block;background:#1A1A2E;color:#FFE600;
                 font-size:14px;font-weight:700;letter-spacing:.04em;
                 padding:15px 34px;border-radius:100px;text-decoration:none;">
          {cta_text}
        </a>
        <p style="margin:7px 0 0;font-size:11px;color:#aaa;">Una sola reunión, cero compromiso</p>
      </td></tr>
    </table>

    <!-- WhatsApp -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:26px;">
      <tr><td align="center">
        <a href="{wa_href}"
          style="display:inline-block;font-size:12px;color:#555;text-decoration:none;
                 padding:7px 14px;border:1px solid #E0D9CC;border-radius:100px;">
          💬 Escríbeme por WhatsApp
        </a>
      </td></tr>
    </table>

    <!-- divider -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr><td style="border-top:1px solid #EEE;font-size:0;line-height:0;">&nbsp;</td></tr>
    </table>

    <!-- firma -->
    <table cellpadding="0" cellspacing="0" border="0" width="100%">
      <tr>
        <td style="width:50px;vertical-align:middle;">
          <img src="cid:email_sig_photo" alt="" width="50" height="50"
            style="width:50px;height:50px;border-radius:50%;display:block;border:2px solid #E8E8E8;">
        </td>
        <td style="padding-left:12px;vertical-align:middle;">
          <p style="margin:0 0 2px;font-size:14px;font-weight:700;color:#1A1A2E;">{from_name}</p>
          <p style="margin:0 0 4px;font-size:11px;color:#009EE3;font-weight:500;line-height:1.35;">
            Longtail Acquisition - Direct &amp; New Channels Sales Executive
          </p>
          <p style="margin:0 0 2px;font-size:11.5px;color:#444;">Teléfono: {from_phone_raw}</p>
          <p style="margin:0;font-size:11.5px;color:#888;">Mercado Pago</p>
        </td>
        <td style="width:1px;background:#E0D9CC;" width="1">&nbsp;</td>
        <td style="width:96px;padding-left:14px;vertical-align:bottom;text-align:center;">
          <img src="cid:email_pos_anim" alt="" width="80"
            style="width:80px;height:auto;display:block;margin:0 auto;">
        </td>
      </tr>
    </table>

  </td></tr>

  <!-- footer -->
  <tr><td style="background:#F8F6F2;padding:12px 32px;border-top:1px solid #EEE;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="font-size:10.5px;color:#bbb;">© 2025 Mercado Pago · Santiago, Chile</td>
      <td align="right">
        <a href="#" style="font-size:10.5px;color:#bbb;text-decoration:none;margin-left:8px;">Privacidad</a>
        <a href="#" style="font-size:10.5px;color:#bbb;text-decoration:none;margin-left:8px;">Términos</a>
        <a href="{unsubscribe_url}" style="font-size:10.5px;color:#bbb;text-decoration:none;margin-left:8px;">Desuscribirse</a>
      </td>
    </tr></table>
  </td></tr>

</table>

</td></tr>
</table>
</body></html>"""


def _get_or_create_tracking_token(to_email: str) -> str:
    """Obtiene o genera el tracking token para un contacto dado su email."""
    conn = get_db()
    row = conn.execute(
        'SELECT tracking_token FROM et_contacts WHERE LOWER(TRIM(email)) = ?',
        (to_email.lower().strip(),)
    ).fetchone()
    if row and row[0]:
        conn.close()
        return row[0]
    # Generar nuevo token
    token = uuid.uuid4().hex[:24]
    conn.execute(
        'UPDATE et_contacts SET tracking_token = ? WHERE LOWER(TRIM(email)) = ?',
        (token, to_email.lower().strip())
    )
    conn.commit()
    conn.close()
    return token


def _get_base_url() -> str:
    """Retorna la URL base del servidor para los links de tracking."""
    import os
    return os.getenv('APP_BASE_URL', 'http://localhost:5000')


def _inject_tracking(html: str, token: str, booking_url: str) -> str:
    """
    Inyecta en el HTML del email:
    1. Tracking pixel (1x1 GIF) al final del body
    2. Wrapping del link de Calendly a través del endpoint /track/click/<token>
    """
    base = _get_base_url()
    pixel_url  = f'{base}/api/email-tool/track/open/{token}'
    click_url  = f'{base}/api/email-tool/track/click/{token}?url={booking_url}'

    # Sustituir href del Calendly por el link de tracking
    if booking_url and booking_url != '#':
        from urllib.parse import quote
        click_url = f'{base}/api/email-tool/track/click/{token}?url={quote(booking_url, safe="")}'
        html = html.replace(f'href="{booking_url}"', f'href="{click_url}"')
        html = html.replace(f"href='{booking_url}'", f"href='{click_url}'")

    # Insertar pixel de apertura justo antes del </body>
    pixel_tag = (
        f'<img src="{pixel_url}" width="1" height="1" '
        f'style="display:block;width:1px;height:1px;border:0;" alt="">'
    )
    if '</body>' in html:
        html = html.replace('</body>', f'{pixel_tag}</body>')
    else:
        html += pixel_tag

    return html


def _send_via_api(to_email: str, subject: str, html_body: str,
                  from_email: str, from_name: str,
                  hdr_bytes: bytes, pos_bytes: bytes, sig_bytes: bytes) -> dict:
    """
    Envía via API HTTP (SendGrid o Resend) — no requiere acceso SMTP directo.
    Prioridad: SENDGRID_API_KEY > RESEND_API_KEY
    """
    import os, base64, requests as _req

    # Reemplazar referencias CID por data URIs base64 en el HTML
    def _b64_uri(data: bytes, mime: str) -> str:
        return f'data:{mime};base64,{base64.b64encode(data).decode()}'

    html = html_body
    if hdr_bytes:
        html = html.replace('cid:email_hdr_anim', _b64_uri(hdr_bytes, 'image/gif'))
    if pos_bytes:
        html = html.replace('cid:email_pos_anim', _b64_uri(pos_bytes, 'image/gif'))
    if sig_bytes:
        html = html.replace('cid:email_sig_photo', _b64_uri(sig_bytes, 'image/jpeg'))

    # ── SendGrid ──────────────────────────────────────────────────────────────
    sg_key = os.getenv('SENDGRID_API_KEY', '')
    if sg_key:
        payload = {
            'personalizations': [{'to': [{'email': to_email}]}],
            'from':    {'email': from_email, 'name': from_name},
            'subject': subject,
            'content': [{'type': 'text/html', 'value': html}],
        }
        try:
            resp = _req.post(
                'https://api.sendgrid.com/v3/mail/send',
                headers={'Authorization': f'Bearer {sg_key}', 'Content-Type': 'application/json'},
                json=payload,
                timeout=30,
            )
            if resp.status_code in (200, 202):
                return {'ok': True}
            return {'ok': False, 'error': f'SendGrid HTTP {resp.status_code}: {resp.text[:200]}'}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:200]}

    # ── Resend (fallback) ─────────────────────────────────────────────────────
    resend_key = os.getenv('RESEND_API_KEY', '')
    if resend_key:
        payload = {
            'from':    f'{from_name} <{from_email}>',
            'to':      [to_email],
            'subject': subject,
            'html':    html,
        }
        try:
            resp = _req.post(
                'https://api.resend.com/emails',
                headers={'Authorization': f'Bearer {resend_key}', 'Content-Type': 'application/json'},
                json=payload,
                timeout=30,
            )
            if resp.status_code in (200, 201):
                return {'ok': True, 'id': resp.json().get('id')}
            return {'ok': False, 'error': f'Resend HTTP {resp.status_code}: {resp.text[:200]}'}
        except Exception as e:
            return {'ok': False, 'error': str(e)[:200]}

    return {'ok': False, 'error': 'Sin API de envío configurada (SENDGRID_API_KEY o RESEND_API_KEY)'}


def _send_smtp(to_email: str, subject: str, body_text: str,
               unsubscribe_url: str = '', rubro: str = '',
               contact_name: str = '', booking_url: str = '',
               # Pre-generados por _do_send_campaign para no repetir Pillow por contacto
               _hdr_gif: bytes = None, _pos_gif: bytes = None,
               _sig_bytes: bytes = None,
               _smtp_conn=None,
               # Override per-user (Sales/TL): si se pasa, usa estas creds en
               # lugar de las env vars del Owner. `user_creds` es un dict con:
               # { 'smtp_user', 'smtp_pass', 'from_name', 'sig_bytes' (opcional) }
               user_creds: dict | None = None) -> dict:
    import os, smtplib, ssl, pathlib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.image import MIMEImage

    smtp_host  = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port  = int(os.getenv('SMTP_PORT', '587'))
    if user_creds and user_creds.get('smtp_user') and user_creds.get('smtp_pass'):
        smtp_user  = user_creds['smtp_user']
        smtp_pass  = user_creds['smtp_pass']
        from_email = user_creds.get('from_email') or smtp_user
        from_name  = user_creds.get('from_name') or os.getenv('EMAIL_FROM_NAME', 'MercadoPago')
        # Si el usuario trajo bytes de su firma propia, los usamos en lugar
        # del archivo global static/email_assets/sig_photo.jpeg
        if user_creds.get('sig_bytes') is not None:
            _sig_bytes = user_creds['sig_bytes']
    else:
        smtp_user  = os.getenv('SMTP_USER', '')
        smtp_pass  = os.getenv('SMTP_PASS', '')
        from_email = os.getenv('EMAIL_FROM', smtp_user)
        from_name  = os.getenv('EMAIL_FROM_NAME', 'Juan Sebastián Pinto')

    if not smtp_user and not os.getenv('RESEND_API_KEY'):
        return {'ok': False, 'error': 'SMTP no configurado'}

    static_dir      = pathlib.Path(__file__).parent.parent / 'static' / 'images'
    email_assets_dir = pathlib.Path(__file__).parent.parent / 'static' / 'email_assets'

    # Tracking token para este contacto
    tracking_token = _get_or_create_tracking_token(to_email)

    # Estructura: mixed > alternative + related(html + images)
    msg_root = MIMEMultipart('mixed')
    msg_root['Subject'] = subject
    msg_root['From']    = f'{from_name} <{from_email}>'
    msg_root['To']      = to_email
    if unsubscribe_url:
        msg_root['List-Unsubscribe'] = f'<{unsubscribe_url}>'

    msg_alt = MIMEMultipart('alternative')
    msg_root.attach(msg_alt)

    # Parte texto plano
    msg_alt.attach(MIMEText(body_text, 'plain', 'utf-8'))

    # Parte HTML con CID references
    msg_related = MIMEMultipart('related')
    msg_alt.attach(msg_related)

    c_content = _get_rubro_content(rubro)
    html_body = _build_html_email(body_text, unsubscribe_url,
                                  rubro=rubro, contact_name=contact_name, booking_url=booking_url)
    # Inyectar pixel de apertura y tracking de clic en CTA
    html_body = _inject_tracking(html_body, tracking_token, booking_url)
    msg_related.attach(MIMEText(html_body, 'html', 'utf-8'))

    # Header animado — usa bytes pre-generados si están disponibles (campaña masiva),
    # si no, genera en el momento (envío individual)
    try:
        hdr_bytes = _hdr_gif if _hdr_gif is not None else _compose_header_gif_desktop(c_content)
        hdr_img = MIMEImage(hdr_bytes, _subtype='gif')
        hdr_img.add_header('Content-ID', '<email_hdr_anim>')
        hdr_img.add_header('Content-Disposition', 'inline', filename='header.gif')
        msg_related.attach(hdr_img)
    except Exception as e:
        logger.warning(f'[EmailTool] No se pudo adjuntar header GIF: {e}')

    # POS animado — ídem, reutiliza bytes pre-generados
    try:
        pos_bytes = _pos_gif if _pos_gif is not None else _compose_pos_gif()
        pos_img = MIMEImage(pos_bytes, _subtype='gif')
        pos_img.add_header('Content-ID', '<email_pos_anim>')
        pos_img.add_header('Content-Disposition', 'inline', filename='pos.gif')
        msg_related.attach(pos_img)
    except Exception as e:
        logger.warning(f'[EmailTool] No se pudo adjuntar POS GIF: {e}')

    # Imagen de firma — usa bytes pre-leídos si están disponibles
    try:
        if _sig_bytes is not None:
            raw_sig = _sig_bytes
        else:
            sig_path = email_assets_dir / 'sig_photo.jpeg'
            raw_sig = sig_path.read_bytes() if sig_path.exists() else None
        if raw_sig:
            sig_img = MIMEImage(raw_sig, _subtype='jpeg')
            sig_img.add_header('Content-ID', '<email_sig_photo>')
            sig_img.add_header('Content-Disposition', 'inline', filename='sig_photo.jpeg')
            msg_related.attach(sig_img)
    except Exception as e:
        logger.warning(f'[EmailTool] No se pudo adjuntar foto firma: {e}')

    # ── EMAIL_LOCAL_URL: proxy al servidor local de la PC (PRIORIDAD MÁXIMA) ──
    # Si está configurado, ignoramos cualquier API/SMTP de Railway porque Workspace
    # bloquea SMTP de Railway por Context-Aware Access. El servidor local manda
    # desde la IP corporativa habitual del usuario.
    email_local_url = os.getenv('EMAIL_LOCAL_URL', '').strip()
    email_local_token = os.getenv('EMAIL_LOCAL_TOKEN', '').strip() or os.getenv('FAST_LOCAL_TOKEN', '').strip()
    if email_local_url and _smtp_conn is None:
        logger.info(f'[EmailTool] Proxy a servidor local: {email_local_url}')
        try:
            import requests as _req
            msg_bytes = msg_root.as_string()
            resp = _req.post(
                email_local_url.rstrip('/') + '/send-email',
                json={
                    'to_email': to_email,
                    'from_email': from_email,
                    'subject': subject,
                    'raw_message': msg_bytes,
                },
                headers={'X-Fast-Token': email_local_token},
                timeout=120,
            )
            if resp.status_code == 401:
                return {'ok': False, 'error': 'Token inválido en servidor local'}
            data = resp.json()
            logger.info(f'[EmailTool] Respuesta local: {data}')
            if data.get('ok'):
                return {'ok': True, 'tracking_token': tracking_token}
            if data.get('bounced'):
                _register_bounce(to_email, data.get('error', 'unknown'))
            return {'ok': False, 'error': data.get('error', 'Error servidor local')[:300], 'bounced': data.get('bounced', False)}
        except _req.exceptions.ConnectionError:
            return {'ok': False, 'error': 'Servidor local de email no disponible (PC apagada o tunnel caído)'}
        except Exception as e:
            logger.error(f'[EmailTool] Error proxy local: {e}', exc_info=True)
            return {'ok': False, 'error': f'Error proxy local: {str(e)[:200]}'}

    # ── Resend API (si SMTP no disponible o bloqueado) ───────────────────────
    if (os.getenv('SENDGRID_API_KEY') or os.getenv('RESEND_API_KEY')) and _smtp_conn is None:
        result = _send_via_api(
            to_email=to_email, subject=subject, html_body=html_body,
            from_email=from_email, from_name=from_name,
            hdr_bytes=hdr_bytes if 'hdr_bytes' in dir() else None,
            pos_bytes=pos_bytes if 'pos_bytes' in dir() else None,
            sig_bytes=raw_sig   if 'raw_sig'   in dir() else None,
        )
        if result.get('ok'):
            result['tracking_token'] = tracking_token
        return result

    # ── SMTP directo ─────────────────────────────────────────────────────────
    try:
        msg_bytes = msg_root.as_string()
        if _smtp_conn is not None:
            # Reutilizar conexión existente (campaña masiva)
            refused = _smtp_conn.sendmail(from_email, to_email, msg_bytes)
        else:
            # Conexión individual (envío único)
            ctx = ssl.create_default_context()
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as s:
                s.ehlo(); s.starttls(context=ctx); s.login(smtp_user, smtp_pass)
                refused = s.sendmail(from_email, to_email, msg_bytes)
        # sendmail retorna dict de rechazos por dirección
        if refused:
            reason = str(refused.get(to_email, 'unknown'))
            _register_bounce(to_email, reason)
            return {'ok': False, 'error': f'Rebotado: {reason}', 'bounced': True}
        return {'ok': True, 'tracking_token': tracking_token}
    except smtplib.SMTPRecipientsRefused as e:
        reason = str(e.recipients.get(to_email, e))
        _register_bounce(to_email, reason)
        return {'ok': False, 'error': f'Destinatario rechazado: {reason}', 'bounced': True}
    except smtplib.SMTPException as e:
        return {'ok': False, 'error': str(e)[:200]}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:200]}


def _register_bounce(email: str, reason: str):
    """Registra un rebote SMTP directamente en la BD."""
    try:
        conn = get_db()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        row = conn.execute('SELECT id FROM et_contacts WHERE LOWER(TRIM(email))=?',
                           (email.lower().strip(),)).fetchone()
        if row:
            conn.execute(
                'UPDATE et_contacts SET email_bounced=1, campaign_status=? WHERE id=?',
                ('rebotado', row[0])
            )
            conn.execute(
                '''INSERT INTO et_seguimientos (contact_id, tipo, fecha, notas, resultado)
                   VALUES (?,\'bounce\',?,?,\'rebotado\')''',
                (row[0], now, f'Rebote SMTP: {reason[:200]}')
            )
            conn.commit()
        conn.close()
    except Exception as ex:
        logger.debug(f'[Track] bounce register error: {ex}')


# ── Contenido de seguimiento 48h / 96h ───────────────────────────────────────

_FOLLOWUP_CONTENT = {
    48: {
        'timer_icon':  '⏰',
        'timer_label': 'Seguimiento — 48 horas',
        'pain': (
            'Hace un par de días te escribí sobre cómo Mercado Pago puede ayudar a tu '
            '<strong>{rubro}</strong> a cobrar mejor y sin costos fijos. '
            'Quizás el correo se perdió en la bandeja de entrada — pasa seguido.'
        ),
        'body': (
            'Solo quería asegurarme de que llegó la información. '
            'No te pido que decidas hoy — solo 15 minutos para mostrarte cómo otros negocios '
            'como tu <strong>{rubro}</strong> ya están cobrando mejor.'
        ),
        'cta_text':   '→ Agenda aquí los 15 minutos',
        'cta_sub':    'Elige el horario que te acomode',
        'preheader':  '¿Todo bien? Solo quería asegurarme de que recibiste mi mensaje anterior.',
    },
    96: {
        'timer_icon':  '🔔',
        'timer_label': 'Segundo seguimiento — 96 horas',
        'pain': (
            'Te escribí dos veces esta semana sobre Mercado Pago para tu '
            '<strong>{rubro}</strong>. Entiendo que estás ocupado — '
            'la operación diaria no da respiro. Si no es el momento adecuado, sin ningún problema.'
        ),
        'body': (
            'Si te interesa retomar la conversación en el futuro, quedo a disposición. '
            'Pero si quieres ver en 15 minutos cómo tu <strong>{rubro}</strong> puede '
            'cobrar mejor desde hoy mismo, aún estoy aquí.'
        ),
        'cta_text':   '→ Sí, me interesa — agenda aquí',
        'cta_sub':    'O responde este mail y coordino yo',
        'preheader':  'Último mensaje. Si no es el momento, sin problema — solo dímelo.',
    },
}


def _build_html_followup_email(rubro: str, contact_name: str, hours: int,
                                booking_url: str = '') -> str:
    """
    Construye el HTML del email de seguimiento (48h ó 96h) usando exactamente
    la misma estructura CID que _build_html_email:
      cid:email_hdr_anim  → header GIF animado
      cid:email_pos_anim  → POS GIF en pie de firma
      cid:email_sig_photo → foto de firma
    Así el formato de recepción es idéntico al email de prospección original.
    """
    import os
    from_name      = os.getenv('EMAIL_FROM_NAME',  'Juan Sebastián Pinto')
    from_phone_raw = os.getenv('EMAIL_FROM_PHONE', '+569 3198 5364')
    wa_number      = from_phone_raw.replace('+', '').replace(' ', '')

    fc = _FOLLOWUP_CONTENT.get(hours, _FOLLOWUP_CONTENT[48])

    # Rubro content base (para ícono, colores de header, etc.)
    c = _get_rubro_content(rubro) or {}
    icon       = c.get('icon', '💳')
    pain_bg    = c.get('pain_bg', '#FFF8E1')
    greeting   = contact_name or 'estimado/a'
    cta_href   = booking_url or '#'
    wa_text    = c.get('wa_text', 'Hola+Juan%2C+me+interesa+saber+m%C3%A1s+sobre+Mercado+Pago')
    wa_href    = f'https://wa.me/{wa_number}?text={wa_text}'

    pain_html  = fc['pain'].replace('{rubro}', rubro)
    body_html  = fc['body'].replace('{rubro}', rubro)
    timer_line = f'{fc["timer_icon"]} {fc["timer_label"]}'
    strip_text = f'{icon} Seguimiento · Mercado Pago para tu {rubro}'

    W = 'max-width:580px;width:100%;margin:0 auto;'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Mercado Pago — Seguimiento</title>
</head>
<body style="margin:0;padding:24px 8px;background:#F0EDE6;font-family:Arial,Helvetica,sans-serif;">
<table cellpadding="0" cellspacing="0" border="0" style="{W}">
<tr><td>

<!-- preheader invisible -->
<div style="display:none;max-height:0;overflow:hidden;font-size:1px;color:#F0EDE6;">
  {fc['preheader']}
</div>

<!-- HEADER — mismo GIF animado CID que prospección -->
<table width="580" cellpadding="0" cellspacing="0" border="0"
  style="max-width:580px;width:100%;border-radius:16px 16px 0 0;overflow:hidden;border-collapse:collapse;">
<tr>
  <td style="padding:0;line-height:0;font-size:0;">
    <img src="cid:email_hdr_anim" alt="Mercado Pago" width="580" height="230"
      style="display:block;width:100%;max-width:580px;height:auto;border:0;border-radius:16px 16px 0 0;">
  </td>
</tr>
<tr>
  <td bgcolor="#FFE600" height="4"
    style="background-color:#FFE600;height:4px;font-size:0;line-height:0;">&nbsp;</td>
</tr>
</table>

<!-- CARD -->
<table cellpadding="0" cellspacing="0" border="0" width="100%"
  style="background:#fff;border:1.5px solid #E0D9CC;border-top:none;
         border-radius:0 0 16px 16px;overflow:hidden;">

  <!-- strip amarillo con badge de rubro -->
  <tr><td style="background:#FFE600;padding:9px 26px;">
    <p style="margin:0;font-size:12.5px;font-weight:700;color:#1A1A2E;letter-spacing:.02em;">
      {strip_text}
    </p>
  </td></tr>

  <!-- timer badge oscuro (48h / 96h) -->
  <tr><td style="background:#1A1A2E;padding:6px 26px;">
    <p style="margin:0;font-size:11px;font-weight:600;color:#FFE600;letter-spacing:.03em;">
      {timer_line}
    </p>
  </td></tr>

  <!-- cuerpo -->
  <tr><td style="padding:28px 32px 26px;">

    <p style="margin:0 0 14px;font-size:15px;color:#555;">
      Hola Equipo de <strong style="font-weight:700;color:#1A1A2E;">{greeting}</strong>,
    </p>

    <!-- pain block -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr><td style="background:{pain_bg};border-left:3px solid #FFE600;border-radius:0 8px 8px 0;
                     padding:13px 16px;font-size:14px;color:#333;line-height:1.65;">
        {pain_html}
      </td></tr>
    </table>

    <p style="margin:0 0 24px;font-size:14px;color:#444;line-height:1.7;">{body_html}</p>

    <!-- CTA -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr><td align="center">
        <a href="{cta_href}"
          style="display:inline-block;background:#1A1A2E;color:#FFE600;
                 font-size:14px;font-weight:700;letter-spacing:.04em;
                 padding:15px 34px;border-radius:100px;text-decoration:none;">
          {fc['cta_text']}
        </a>
        <p style="margin:7px 0 0;font-size:11px;color:#aaa;">{fc['cta_sub']}</p>
      </td></tr>
    </table>

    <!-- WhatsApp -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:26px;">
      <tr><td align="center">
        <a href="{wa_href}"
          style="display:inline-block;font-size:12px;color:#555;text-decoration:none;
                 padding:7px 14px;border:1px solid #E0D9CC;border-radius:100px;">
          💬 Escríbeme por WhatsApp
        </a>
      </td></tr>
    </table>

    <!-- divider -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr><td style="border-top:1px solid #EEE;font-size:0;line-height:0;">&nbsp;</td></tr>
    </table>

    <!-- FIRMA — idéntica a prospección: foto CID + POS GIF CID -->
    <table cellpadding="0" cellspacing="0" border="0" width="100%">
      <tr>
        <td style="width:50px;vertical-align:middle;">
          <img src="cid:email_sig_photo" alt="" width="50" height="50"
            style="width:50px;height:50px;border-radius:50%;display:block;border:2px solid #E8E8E8;">
        </td>
        <td style="padding-left:12px;vertical-align:middle;">
          <p style="margin:0 0 2px;font-size:14px;font-weight:700;color:#1A1A2E;">{from_name}</p>
          <p style="margin:0 0 4px;font-size:11px;color:#009EE3;font-weight:500;line-height:1.35;">
            Longtail Acquisition - Direct &amp; New Channels Sales Executive
          </p>
          <p style="margin:0 0 2px;font-size:11.5px;color:#444;">Teléfono: {from_phone_raw}</p>
          <p style="margin:0;font-size:11.5px;color:#888;">Mercado Pago</p>
        </td>
        <td style="width:1px;background:#E0D9CC;" width="1">&nbsp;</td>
        <td style="width:96px;padding-left:14px;vertical-align:bottom;text-align:center;">
          <img src="cid:email_pos_anim" alt="" width="80"
            style="width:80px;height:auto;display:block;margin:0 auto;">
        </td>
      </tr>
    </table>

  </td></tr>

  <!-- footer -->
  <tr><td style="background:#F8F6F2;padding:12px 32px;border-top:1px solid #EEE;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="font-size:10.5px;color:#bbb;">© 2025 Mercado Pago · Santiago, Chile</td>
      <td align="right">
        <a href="#" style="font-size:10.5px;color:#bbb;text-decoration:none;margin-left:8px;">Privacidad</a>
        <a href="#" style="font-size:10.5px;color:#bbb;text-decoration:none;margin-left:8px;">Términos</a>
      </td>
    </tr></table>
  </td></tr>
</table>

</td></tr>
</table>
</body>
</html>"""


def _send_smtp_followup(to_email: str, subject: str, rubro: str,
                         contact_name: str, hours: int,
                         booking_url: str = '',
                         user_creds: dict | None = None) -> dict:
    """
    Envía el email de seguimiento (48h ó 96h) con exactamente el mismo
    formato que los emails de prospección:
      - Header GIF animado (cid:email_hdr_anim) compuesto con Pillow
      - POS GIF animado en pie de firma (cid:email_pos_anim)
      - Foto de firma (cid:email_sig_photo)
    Solo cambia el cuerpo del mensaje con el texto de seguimiento.
    """
    import os, smtplib, ssl, pathlib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.image import MIMEImage

    smtp_host  = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port  = int(os.getenv('SMTP_PORT', '587'))
    if user_creds and user_creds.get('smtp_user') and user_creds.get('smtp_pass'):
        smtp_user  = user_creds['smtp_user']
        smtp_pass  = user_creds['smtp_pass']
        from_email = user_creds.get('from_email') or smtp_user
        from_name  = user_creds.get('from_name') or os.getenv('EMAIL_FROM_NAME', 'MercadoPago')
        _user_sig_bytes = user_creds.get('sig_bytes')
    else:
        smtp_user  = os.getenv('SMTP_USER', '')
        smtp_pass  = os.getenv('SMTP_PASS', '')
        from_email = os.getenv('EMAIL_FROM', smtp_user)
        from_name  = os.getenv('EMAIL_FROM_NAME', 'Juan Sebastián Pinto')
        _user_sig_bytes = None

    if not smtp_user and not os.getenv('RESEND_API_KEY'):
        return {'ok': False, 'error': 'SMTP no configurado'}

    email_assets_dir = pathlib.Path(__file__).parent.parent / 'static' / 'email_assets'
    tracking_token   = _get_or_create_tracking_token(to_email)

    # Estructura MIME idéntica a _send_smtp: mixed > alternative > related
    msg_root = MIMEMultipart('mixed')
    msg_root['Subject'] = subject
    msg_root['From']    = f'{from_name} <{from_email}>'
    msg_root['To']      = to_email

    msg_alt = MIMEMultipart('alternative')
    msg_root.attach(msg_alt)

    fc = _FOLLOWUP_CONTENT.get(hours, _FOLLOWUP_CONTENT[48])
    plain_text = (
        f'Hola Equipo de {contact_name or "estimado/a"},\n\n'
        f'{fc["pain"].replace("{rubro}", rubro).replace("<strong>","").replace("</strong>","")}\n\n'
        f'{fc["body"].replace("{rubro}", rubro).replace("<strong>","").replace("</strong>","")}\n\n'
        f'{fc["cta_text"]}: {booking_url}\n\n'
        f'Saludos,\n{from_name}\nMercado Pago'
    )
    msg_alt.attach(MIMEText(plain_text, 'plain', 'utf-8'))

    msg_related = MIMEMultipart('related')
    msg_alt.attach(msg_related)

    html_body = _build_html_followup_email(rubro, contact_name, hours, booking_url)
    html_body = _inject_tracking(html_body, tracking_token, booking_url)
    msg_related.attach(MIMEText(html_body, 'html', 'utf-8'))

    # Header GIF animado (mismo pipeline que prospección)
    try:
        c_content = _get_rubro_content(rubro)
        hdr_gif_bytes = _compose_header_gif_desktop(c_content)
        hdr_img = MIMEImage(hdr_gif_bytes, _subtype='gif')
        hdr_img.add_header('Content-ID', '<email_hdr_anim>')
        hdr_img.add_header('Content-Disposition', 'inline', filename='header.gif')
        msg_related.attach(hdr_img)
    except Exception as e:
        logger.warning(f'[FollowUp] No se pudo generar header GIF: {e}')

    # POS GIF animado en pie de firma (mismo pipeline que prospección)
    try:
        pos_gif_bytes = _compose_pos_gif()
        pos_img = MIMEImage(pos_gif_bytes, _subtype='gif')
        pos_img.add_header('Content-ID', '<email_pos_anim>')
        pos_img.add_header('Content-Disposition', 'inline', filename='pos.gif')
        msg_related.attach(pos_img)
    except Exception as e:
        logger.warning(f'[FollowUp] No se pudo generar POS GIF: {e}')

    # Foto de firma — usa la del Sales si vino en user_creds
    sig_bytes_to_use = _user_sig_bytes
    if sig_bytes_to_use is None:
        sig_path = email_assets_dir / 'sig_photo.jpeg'
        if sig_path.exists():
            sig_bytes_to_use = sig_path.read_bytes()
    if sig_bytes_to_use:
        sig_img = MIMEImage(sig_bytes_to_use, _subtype='jpeg')
        sig_img.add_header('Content-ID', '<email_sig_photo>')
        sig_img.add_header('Content-Disposition', 'inline', filename='sig_photo.jpeg')
        msg_related.attach(sig_img)

    # ── Resend API (si SMTP no disponible o bloqueado) ───────────────────────
    if os.getenv('SENDGRID_API_KEY') or os.getenv('RESEND_API_KEY'):
        result = _send_via_api(
            to_email=to_email, subject=subject, html_body=html_body,
            from_email=from_email, from_name=from_name,
            hdr_bytes=hdr_gif_bytes if 'hdr_gif_bytes' in dir() else None,
            pos_bytes=pos_gif_bytes if 'pos_gif_bytes' in dir() else None,
            sig_bytes=sig_path.read_bytes() if sig_path.exists() else None,
        )
        if result.get('ok'):
            result['tracking_token'] = tracking_token
        return result

    # ── SMTP directo ─────────────────────────────────────────────────────────
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.ehlo(); s.starttls(context=ctx); s.login(smtp_user, smtp_pass)
            refused = s.sendmail(from_email, to_email, msg_root.as_string())
            if refused:
                reason = str(refused.get(to_email, 'unknown'))
                _register_bounce(to_email, reason)
                return {'ok': False, 'error': f'Rebotado: {reason}', 'bounced': True}
        return {'ok': True, 'tracking_token': tracking_token}
    except smtplib.SMTPRecipientsRefused as e:
        reason = str(e.recipients.get(to_email, e))
        _register_bounce(to_email, reason)
        return {'ok': False, 'error': f'Destinatario rechazado: {reason}', 'bounced': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:200]}


# ── Scraping job ─────────────────────────────────────────────────────────────

async def _google_search_and_scrape(job_id, query, ciudad, comuna, rubro, max_results):
    from playwright.async_api import async_playwright
    import uuid as _uuid

    job = _jobs[job_id]
    job['status'] = 'running'
    job['progress'] = 0
    job['found'] = 0

    # Log scraping run start
    run_id = str(_uuid.uuid4())[:12]
    _scrape_db = get_db()
    _scrape_db.execute(
        '''INSERT INTO scraping_jobs (run_id, tipo, rubro, comuna, status, started_at)
           VALUES (?, 'google_search', ?, ?, 'running', datetime('now','localtime'))''',
        (run_id, rubro, comuna)
    )
    _scrape_db.commit()
    _scrape_db.close()

    search_query = f"{query} {ciudad} {comuna} contacto email"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox',
                  '--disable-dev-shm-usage']
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            locale='es-CL',
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            )
        )
        page = await context.new_page()
        try:
            await page.goto(
                f'https://www.google.com/search?q={search_query.replace(" ", "+")}&num=30',
                timeout=20_000
            )
            await page.wait_for_load_state('domcontentloaded', timeout=10_000)
            await asyncio.sleep(2)

            try:
                await page.get_by_role('button', name=re.compile('Aceptar|Accept|Agree', re.I)).first.click(timeout=3_000)
                await asyncio.sleep(1)
            except Exception:
                pass

            links = await page.evaluate("""
                () => {
                    const anchors = [...document.querySelectorAll('#search a[href]')];
                    const urls = [];
                    for (const a of anchors) {
                        const href = a.href;
                        if (href && href.startsWith('http') &&
                            !href.includes('google.com') && !href.includes('youtube.com') &&
                            !href.includes('facebook.com') && !href.includes('instagram.com') &&
                            !href.includes('twitter.com') && !href.includes('maps.google')) {
                            const clean = href.split('&')[0].split('#')[0];
                            if (!urls.includes(clean)) urls.push(clean);
                        }
                    }
                    return urls.slice(0, 30);
                }
            """)

            job['total_urls'] = len(links)
            job['message'] = f"Encontradas {len(links)} URLs. Extrayendo emails..."

            conn = get_db()
            results = []

            for i, url in enumerate(links[:max_results]):
                job['progress'] = int((i / max(len(links[:max_results]), 1)) * 100)
                job['current_url'] = url

                try:
                    await page.goto(url, timeout=15_000, wait_until='domcontentloaded')
                    title = await page.title()
                    business_name = title.split('|')[0].split('-')[0].strip()[:80]
                    html = await page.content()
                    emails = _clean_emails(EMAIL_RE.findall(html))

                    if not emails:
                        emails = await _try_contact_page(page, url)

                    if emails:
                        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        followup_dt = (datetime.now() + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
                        for email in emails[:3]:
                            existing = conn.execute(
                                'SELECT id FROM et_contacts WHERE email = ?', (email,)
                            ).fetchone()
                            if existing:
                                continue
                            conn.execute(
                                '''INSERT INTO et_contacts
                                   (business_name, email, website, rubro, ciudad, comuna,
                                    source_query, created_at, campaign_status, proximo_seguimiento)
                                   VALUES (?,?,?,?,?,?,?,?,?,?)''',
                                (business_name, email, url, rubro, ciudad, comuna,
                                 query, now, 'pendiente', followup_dt)
                            )
                            results.append({
                                'business_name': business_name,
                                'email': email,
                                'website': url,
                                'rubro': rubro,
                                'comuna': comuna,
                            })
                        conn.commit()
                        job['found'] = job.get('found', 0) + len(emails[:3])

                except Exception as e:
                    logger.debug(f'[EmailTool] Error en {url}: {e}')
                    continue

                await asyncio.sleep(1.5)

            job['status'] = 'done'
            job['progress'] = 100
            job['results'] = results
            job['message'] = f"Completado: {job['found']} emails encontrados"
            # Update scraping_jobs log — success
            _fin_db = get_db()
            _fin_db.execute(
                '''UPDATE scraping_jobs SET status='done', leads_found=?,
                   leads_inserted=?, leads_skipped=?,
                   finished_at=datetime('now','localtime') WHERE run_id=?''',
                (job['found'], len(results), job['found'] - len(results), run_id)
            )
            _fin_db.commit()
            _fin_db.close()

        except Exception as e:
            logger.error(f'[EmailTool] Job {job_id} error: {e}', exc_info=True)
            job['status'] = 'error'
            job['error'] = str(e)
            try:
                _err_db = get_db()
                _err_db.execute(
                    '''UPDATE scraping_jobs SET status='error', error=?,
                       finished_at=datetime('now','localtime') WHERE run_id=?''',
                    (str(e)[:300], run_id)
                )
                _err_db.commit()
                _err_db.close()
            except Exception:
                pass
        finally:
            await browser.close()


# ── Search endpoints ──────────────────────────────────────────────────────────

@email_bp.route('/search', methods=['POST'])
def start_search():
    data = request.get_json() or {}
    query   = data.get('query', '').strip()
    ciudad  = data.get('ciudad', 'Santiago').strip()
    comuna  = data.get('comuna', '').strip()
    rubro   = data.get('rubro', query).strip()
    max_res = min(int(data.get('max_results', 20)), 50)

    if not query:
        return jsonify({'ok': False, 'error': 'query requerido'}), 400

    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {'status': 'queued', 'progress': 0, 'found': 0,
                     'message': 'Iniciando...', 'results': []}

    def run():
        try:
            asyncio.run(_google_search_and_scrape(job_id, query, ciudad, comuna, rubro, max_res))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_google_search_and_scrape(job_id, query, ciudad, comuna, rubro, max_res))
            finally:
                loop.close()

    import threading
    threading.Thread(target=run, daemon=True).start()
    return jsonify({'ok': True, 'job_id': job_id})


@email_bp.route('/search/status/<job_id>', methods=['GET'])
def search_status(job_id):
    job = _jobs.get(job_id)
    if not job:
        return jsonify({'ok': False, 'error': 'job no encontrado'}), 404
    return jsonify({'ok': True, **job})


# ── Contacts ──────────────────────────────────────────────────────────────────

@email_bp.route('/contacts', methods=['GET'])
def get_contacts():
    conn = get_db()
    rubro  = request.args.get('rubro', '')
    ciudad = request.args.get('ciudad', '')
    comuna = request.args.get('comuna', '')
    status = request.args.get('status', '')
    estado = request.args.get('estado_interes', '')
    assigned_to = request.args.get('assigned_to_user_id', '').strip()

    q = 'SELECT * FROM et_contacts WHERE 1=1'
    params = []
    if rubro:  q += ' AND rubro LIKE ?';          params.append(f'%{rubro}%')
    if ciudad: q += ' AND ciudad LIKE ?';          params.append(f'%{ciudad}%')
    if comuna: q += ' AND comuna LIKE ?';          params.append(f'%{comuna}%')
    if status:
        if status == 'no_enviado':
            # Incluye también registros residuales con 'pendiente'
            q += " AND campaign_status IN ('no_enviado','pendiente')"
        else:
            q += ' AND campaign_status = ?'
            params.append(status)
    if estado: q += ' AND estado_interes = ?';     params.append(estado)
    if assigned_to:
        if assigned_to == 'unassigned':
            q += ' AND (assigned_to IS NULL)'
        else:
            try:
                q += ' AND assigned_to = ?'; params.append(int(assigned_to))
            except ValueError:
                pass
    q += ' ORDER BY created_at DESC LIMIT 500'

    cur = conn.execute(q, params)
    cols = [d[0] for d in cur.description]
    rows = []
    for r in cur.fetchall():
        d = dict(zip(cols, r))
        # Columna calculada: fuente legible desde source_query
        sq = (d.get('source_query') or '').lower().strip()
        if sq.startswith('outscraper:'):
            d['fuente'] = 'Outscraper'
        elif sq.startswith('brave:'):
            d['fuente'] = 'Brave'
        elif sq.startswith('serper:'):
            d['fuente'] = 'Serper'
        elif sq.startswith('cse:'):
            d['fuente'] = 'Google'
        elif sq.startswith('manual'):
            d['fuente'] = 'Manual'
        elif any(kw in sq for kw in ('contacto email', 'correo', 'contacto web',
                                      'correo electronico', 'santiago chile',
                                      'contacto', 'email')):
            # Leads scrapeados con formato antiguo (Brave/Serper sin prefijo)
            d['fuente'] = 'Web'
        elif sq:
            # source_query corto = ingresado/importado manualmente
            d['fuente'] = 'Manual'
        else:
            d['fuente'] = '—'
        rows.append(d)
    return jsonify(rows)


@email_bp.route('/contacts/assign', methods=['POST'])
@login_required
def assign_contacts():
    """
    Asigna contactos a un Sales (o desasigna pasando user_id=null).
    Body: { "contact_ids": [int,...], "user_id": int|null }
    Solo Owner/TL pueden asignar.
    """
    if current_user.role not in ('owner', 'tl'):
        return jsonify({'error': 'Solo Owner/TL pueden asignar'}), 403

    data = request.get_json() or {}
    raw_ids = data.get('contact_ids') or []
    if not isinstance(raw_ids, list) or not raw_ids:
        return jsonify({'error': 'contact_ids requerido (lista)'}), 400
    try:
        cids = [int(x) for x in raw_ids]
    except (TypeError, ValueError):
        return jsonify({'error': 'contact_ids inválidos'}), 400

    user_id = data.get('user_id', None)
    if user_id is not None:
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'user_id inválido'}), 400
        # Verificar que el usuario existe y está activo
        conn = get_db()
        u = conn.execute(
            "SELECT id, role, status FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        conn.close()
        if not u or u['status'] != 'active' or u['role'] not in ('sales', 'owner'):
            return jsonify({'error': 'Usuario destino inválido'}), 400

    placeholders = ','.join('?' for _ in cids)
    conn = get_db()
    if user_id is None:
        conn.execute(
            f'UPDATE et_contacts SET assigned_to = NULL WHERE id IN ({placeholders})',
            cids
        )
    else:
        params = [user_id] + cids
        conn.execute(
            f'UPDATE et_contacts SET assigned_to = ? WHERE id IN ({placeholders})',
            params
        )
    affected = conn.total_changes
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'affected': affected, 'user_id': user_id})


@email_bp.route('/contacts/stats-by-sales', methods=['GET'])
@login_required
def contacts_stats_by_sales():
    """Métricas de et_contacts agrupadas por Sales asignado + globales."""
    conn = get_db()
    role = current_user.role

    if role == 'sales':
        rows = conn.execute("""
            SELECT u.id as user_id, u.name as full_name, u.email,
                   COUNT(DISTINCT c.id) as total,
                   SUM(CASE WHEN c.campaign_status IN ('no_enviado','pendiente') THEN 1 ELSE 0 END) as pendientes,
                   SUM(CASE WHEN c.campaign_status='enviado' THEN 1 ELSE 0 END) as enviados,
                   SUM(CASE WHEN c.estado_interes='respondido' THEN 1 ELSE 0 END) as respondidos,
                   SUM(CASE WHEN c.estado_interes='interesado' THEN 1 ELSE 0 END) as interesados
            FROM users u
            LEFT JOIN et_contacts c ON c.assigned_to = u.id
            WHERE u.id = ?
            GROUP BY u.id
        """, (current_user.id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT u.id as user_id, u.name as full_name, u.email,
                   COUNT(DISTINCT c.id) as total,
                   SUM(CASE WHEN c.campaign_status IN ('no_enviado','pendiente') THEN 1 ELSE 0 END) as pendientes,
                   SUM(CASE WHEN c.campaign_status='enviado' THEN 1 ELSE 0 END) as enviados,
                   SUM(CASE WHEN c.estado_interes='respondido' THEN 1 ELSE 0 END) as respondidos,
                   SUM(CASE WHEN c.estado_interes='interesado' THEN 1 ELSE 0 END) as interesados
            FROM users u
            LEFT JOIN et_contacts c ON c.assigned_to = u.id
            WHERE u.status = 'active' AND u.role IN ('sales','owner')
            GROUP BY u.id
            ORDER BY total DESC, u.name ASC
        """).fetchall()

    by_sales = [dict(r) for r in rows]

    g = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN assigned_to IS NULL THEN 1 ELSE 0 END) as unassigned,
            SUM(CASE WHEN campaign_status IN ('no_enviado','pendiente') THEN 1 ELSE 0 END) as pendientes,
            SUM(CASE WHEN campaign_status='enviado' THEN 1 ELSE 0 END) as enviados,
            SUM(CASE WHEN estado_interes='respondido' THEN 1 ELSE 0 END) as respondidos
        FROM et_contacts
    """).fetchone()
    conn.close()
    return jsonify({'by_sales': by_sales, 'globals': dict(g) if g else {}})


@email_bp.route('/contacts/<int:cid>', methods=['GET'])
def get_contact(cid):
    conn = get_db()
    cur = conn.execute('SELECT * FROM et_contacts WHERE id=?', (cid,))
    cols = [d[0] for d in cur.description]
    row = cur.fetchone()
    if not row:
        return jsonify({'error': 'no encontrado'}), 404
    return jsonify(dict(zip(cols, row)))


@email_bp.route('/contacts/<int:cid>/conversation', methods=['GET'])
def get_contact_conversation(cid):
    """Timeline de conversación: emails enviados, aperturas, respuestas, seguimientos."""
    conn = get_db()
    c = conn.execute('SELECT * FROM et_contacts WHERE id=?', (cid,)).fetchone()
    if not c:
        conn.close()
        return jsonify({'error': 'no encontrado'}), 404
    contact = dict(c)

    segs = conn.execute(
        'SELECT * FROM et_seguimientos WHERE contact_id=? ORDER BY fecha ASC', (cid,)
    ).fetchall()
    conn.close()

    timeline = []

    for s in segs:
        s = dict(s)
        tipo = s.get('tipo', 'email')
        if tipo == 'email':
            # Extraer subject del campo notas: "Batch send — SUBJECT"
            notas = s.get('notas') or ''
            subject = notas.replace('Batch send — ', '').strip() if 'Batch send' in notas else notas
            timeline.append({'tipo': 'email_sent', 'fecha': s['fecha'],
                              'subject': subject, 'batch_id': s.get('batch_id')})
        elif tipo == 'click_cta':
            timeline.append({'tipo': 'click_cta', 'fecha': s['fecha'], 'notas': 'Clic en enlace de agenda'})
        else:
            timeline.append({'tipo': tipo, 'fecha': s['fecha'], 'notas': s.get('notas','')})

    # Insertar eventos de tracking desde et_contacts
    if contact.get('email_opened_at'):
        timeline.append({'tipo': 'opened', 'fecha': contact['email_opened_at'], 'notas': 'Email abierto'})
    if contact.get('email_replied'):
        timeline.append({'tipo': 'replied', 'fecha': contact.get('last_followup_at',''), 'notas': 'Respuesta registrada'})
    if contact.get('email_bounced'):
        timeline.append({'tipo': 'bounced', 'fecha': '', 'notas': 'Email rebotado'})

    # Ordenar cronológicamente
    timeline.sort(key=lambda x: (x.get('fecha') or ''))

    # Próximo seguimiento pendiente
    if contact.get('proximo_seguimiento') and (contact.get('seguimiento_count') or 0) < 3 \
            and not contact.get('email_bounced') and not contact.get('opt_out'):
        seg_num = (contact.get('seguimiento_count') or 0) + 1
        timeline.append({'tipo': 'upcoming', 'fecha': contact['proximo_seguimiento'],
                         'notas': f'Seguimiento #{seg_num} programado'})

    return jsonify({
        'contact': {k: contact.get(k) for k in
                    ['id','business_name','email','rubro','comuna',
                     'campaign_status','estado_interes','seguimiento_count',
                     'email_replied','email_bounced','email_opened_at','proximo_seguimiento']},
        'timeline': timeline
    })


def _promote_to_prospect(conn, cid):
    """Cuando un email contact se marca interesado, crea un prospecto en gestión CRM.
    Si ya existe (et_contact_id coincide) no duplica.
    """
    contact = conn.execute('SELECT * FROM et_contacts WHERE id = ?', (cid,)).fetchone()
    if not contact:
        return
    # Evitar duplicado
    if conn.execute('SELECT id FROM prospects WHERE et_contact_id = ?', (cid,)).fetchone():
        return
    # Phone real si existe, sino placeholder para satisfacer NOT NULL
    phone = (contact['phone'] or '').strip() or f'em_{cid}'
    now   = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        cur = conn.execute(
            '''INSERT OR IGNORE INTO prospects
               (lead_id, name, phone, email, negocio, rubro, comuna,
                procedencia, notas, source, et_contact_id, created_at, updated_at)
               VALUES (NULL, ?, ?, ?, ?, ?, ?, 'Email', 'Prospecto generado por email', 'email', ?, ?, ?)''',
            (contact['business_name'] or 'Sin nombre',
             phone,
             contact['email'] or '',
             contact['business_name'] or '',
             contact['rubro'] or '',
             contact['comuna'] or '',
             cid, now, now)
        )
        conn.commit()
        logger.info(f'[email→gestión] Contacto {cid} ({contact["business_name"]}) promovido a prospecto #{cur.lastrowid}')
    except Exception as e:
        logger.warning(f'[email→gestión] Error promoviendo contacto {cid}: {e}')


@email_bp.route('/contacts/<int:cid>', methods=['PATCH'])
def update_contact(cid):
    data = request.get_json() or {}
    allowed = ['estado_interes', 'notas', 'proximo_seguimiento', 'reunion_fecha',
               'campaign_status', 'business_name', 'phone']
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'ok': False, 'error': 'nada que actualizar'}), 400

    set_clause = ', '.join(f'{k} = ?' for k in updates)
    values = list(updates.values()) + [cid]
    conn = get_db()
    conn.execute(f'UPDATE et_contacts SET {set_clause} WHERE id = ?', values)
    conn.commit()
    # Unificación Opción B: si se marcó interesado, crear prospecto en gestión
    if updates.get('campaign_status') == 'interesado':
        _promote_to_prospect(conn, cid)
    conn.close()
    return jsonify({'ok': True})


@email_bp.route('/contacts/<int:cid>', methods=['DELETE'])
def delete_contact(cid):
    conn = get_db()
    conn.execute('DELETE FROM et_contacts WHERE id = ?', (cid,))
    conn.commit()
    return jsonify({'ok': True})


@email_bp.route('/contacts/<int:cid>/mark-reply', methods=['POST'])
def mark_reply_manual(cid):
    """Marca manualmente que un contacto respondió el email."""
    conn = get_db()
    now  = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        '''UPDATE et_contacts
           SET email_replied   = 1,
               estado_interes  = CASE WHEN estado_interes IN ('pendiente','no_enviado','enviado')
                                      THEN 'respondido' ELSE estado_interes END,
               campaign_status = CASE WHEN campaign_status NOT IN ('cerrado','no_interesado','opt_out')
                                      THEN 'respondido' ELSE campaign_status END
           WHERE id = ?''',
        (cid,)
    )
    conn.execute(
        '''INSERT OR IGNORE INTO et_seguimientos (contact_id, tipo, fecha, notas, resultado)
           VALUES (?, 'reply', ?, 'Respuesta registrada manualmente', 'respondido')''',
        (cid, now)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@email_bp.route('/contacts/<int:cid>/mark-bounce', methods=['POST'])
def mark_bounce_manual(cid):
    """Marca manualmente que un email rebotó (entrega fallida)."""
    conn = get_db()
    now  = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        'UPDATE et_contacts SET email_bounced=1, campaign_status=? WHERE id=?',
        ('rebotado', cid)
    )
    conn.execute(
        '''INSERT INTO et_seguimientos (contact_id, tipo, fecha, notas, resultado)
           VALUES (?, 'bounce', ?, 'Rebote registrado manualmente', 'rebotado')''',
        (cid, now)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@email_bp.route('/contacts/change-rubro', methods=['PATCH'])
def change_rubro_bulk():
    """
    Cambia el rubro de uno o más contactos.
    Body: { contact_ids: [1,2,3], rubro: "veterinaria" }
    El rubro nuevo debe existir en et_rubro_templates.
    """
    data = request.get_json() or {}
    ids  = data.get('contact_ids') or []
    nuevo_rubro = (data.get('rubro') or '').strip()

    if not ids or not nuevo_rubro:
        return jsonify({'ok': False, 'error': 'contact_ids y rubro son requeridos'}), 400

    # Validar que el rubro existe en et_rubro_templates
    conn = get_db()
    valido = conn.execute(
        'SELECT id FROM et_rubro_templates WHERE LOWER(TRIM(rubro)) = LOWER(TRIM(?))',
        (nuevo_rubro,)
    ).fetchone()
    if not valido:
        conn.close()
        return jsonify({'ok': False, 'error': f'Rubro "{nuevo_rubro}" no existe en las campañas'}), 400

    # Solo IDs enteros para evitar inyección
    ids_safe = [int(i) for i in ids if str(i).isdigit() or isinstance(i, int)]
    if not ids_safe:
        conn.close()
        return jsonify({'ok': False, 'error': 'IDs inválidos'}), 400

    ph = ','.join('?' * len(ids_safe))
    cur = conn.execute(
        f'UPDATE et_contacts SET rubro = ? WHERE id IN ({ph})',
        [nuevo_rubro] + ids_safe
    )
    conn.commit()
    conn.close()
    logger.info(f'[ChangeRubro] {cur.rowcount} contactos → rubro="{nuevo_rubro}"')
    return jsonify({'ok': True, 'updated': cur.rowcount, 'rubro': nuevo_rubro})


@email_bp.route('/contacts/clear', methods=['POST'])
def clear_contacts():
    data = request.get_json() or {}
    rubro = data.get('rubro', '')
    conn = get_db()
    if rubro:
        conn.execute('DELETE FROM et_contacts WHERE rubro = ?', (rubro,))
    else:
        conn.execute('DELETE FROM et_contacts')
    conn.commit()
    return jsonify({'ok': True})


# ── Seguimientos ─────────────────────────────────────────────────────────────

@email_bp.route('/contacts/<int:cid>/seguimientos', methods=['GET'])
def get_seguimientos(cid):
    conn = get_db()
    cur = conn.execute(
        'SELECT * FROM et_seguimientos WHERE contact_id=? ORDER BY fecha DESC', (cid,)
    )
    cols = [d[0] for d in cur.description]
    return jsonify([dict(zip(cols, r)) for r in cur.fetchall()])


@email_bp.route('/contacts/<int:cid>/seguimientos', methods=['POST'])
def add_seguimiento(cid):
    data = request.get_json() or {}
    conn = get_db()
    conn.execute(
        '''INSERT INTO et_seguimientos (contact_id, tipo, fecha, notas, resultado)
           VALUES (?,?,?,?,?)''',
        (cid, data.get('tipo', 'email'),
         data.get('fecha', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
         data.get('notas', ''), data.get('resultado', 'sin_respuesta'))
    )
    conn.commit()
    return jsonify({'ok': True})


# ── Reuniones ─────────────────────────────────────────────────────────────────

@email_bp.route('/reuniones', methods=['GET'])
def get_reuniones():
    conn = get_db()
    cur = conn.execute(
        '''SELECT r.*, c.business_name, c.email, c.rubro
           FROM et_reuniones r
           JOIN et_contacts c ON r.contact_id = c.id
           ORDER BY r.fecha ASC'''
    )
    cols = [d[0] for d in cur.description]
    return jsonify([dict(zip(cols, row)) for row in cur.fetchall()])


@email_bp.route('/reuniones', methods=['POST'])
def create_reunion():
    data = request.get_json() or {}
    required = ['contact_id', 'fecha']
    if not all(data.get(k) for k in required):
        return jsonify({'ok': False, 'error': 'contact_id y fecha requeridos'}), 400

    conn = get_db()
    cur = conn.execute(
        '''INSERT INTO et_reuniones (contact_id, fecha, hora, lugar, notas, estado)
           VALUES (?,?,?,?,?,?)''',
        (data['contact_id'], data['fecha'], data.get('hora', ''),
         data.get('lugar', ''), data.get('notas', ''), data.get('estado', 'pendiente'))
    )
    conn.execute(
        "UPDATE et_contacts SET estado_interes='en_negociacion', reunion_fecha=? WHERE id=?",
        (data['fecha'], data['contact_id'])
    )
    conn.commit()
    return jsonify({'ok': True, 'id': cur.lastrowid})


@email_bp.route('/reuniones/<int:rid>', methods=['PATCH'])
def update_reunion(rid):
    data = request.get_json() or {}
    allowed = ['estado', 'notas', 'hora', 'lugar', 'fecha']
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'ok': False}), 400
    set_clause = ', '.join(f'{k} = ?' for k in updates)
    values = list(updates.values()) + [rid]
    conn = get_db()
    conn.execute(f'UPDATE et_reuniones SET {set_clause} WHERE id = ?', values)
    conn.commit()
    return jsonify({'ok': True})


@email_bp.route('/reuniones/<int:rid>', methods=['DELETE'])
def delete_reunion(rid):
    conn = get_db()
    conn.execute('DELETE FROM et_reuniones WHERE id=?', (rid,))
    conn.commit()
    return jsonify({'ok': True})


# ── Email Tracking ───────────────────────────────────────────────────────────

# 1x1 GIF transparente (estándar para tracking pixels)
_TRACKING_PIXEL = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00'
    b'!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01'
    b'\x00\x00\x02\x02D\x01\x00;'
)


@email_bp.route('/track/open/<token>', methods=['GET'])
def track_open(token):
    """Pixel de apertura: 1x1 GIF transparente. Se activa cuando el cliente abre el email."""
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT id, campaign_status FROM et_contacts WHERE tracking_token = ?', (token,)
        ).fetchone()
        if row:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                '''UPDATE et_contacts
                   SET email_opened_at = COALESCE(email_opened_at, ?),
                       campaign_status = CASE WHEN campaign_status = 'enviado'
                                              THEN 'abierto' ELSE campaign_status END
                   WHERE tracking_token = ?''',
                (now, token)
            )
            conn.commit()
            logger.info(f'[Track] Email abierto — contact_id={row[0]}')
    except Exception as e:
        logger.debug(f'[Track] open error: {e}')
    finally:
        conn.close()

    from flask import Response
    return Response(
        _TRACKING_PIXEL,
        mimetype='image/gif',
        headers={
            'Cache-Control': 'no-store, no-cache, must-revalidate',
            'Pragma':        'no-cache',
            'Expires':       '0',
        }
    )


@email_bp.route('/track/click/<token>', methods=['GET'])
def track_click(token):
    """Tracking de clic en CTA (Calendly). Registra el clic y redirige al URL destino."""
    from flask import redirect
    dest = request.args.get('url', '#')
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT id FROM et_contacts WHERE tracking_token = ?', (token,)
        ).fetchone()
        if row:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                '''UPDATE et_contacts
                   SET email_opened_at = COALESCE(email_opened_at, ?),
                       estado_interes  = CASE WHEN estado_interes IN ('pendiente','enviado')
                                              THEN 'interesado' ELSE estado_interes END,
                       campaign_status = CASE WHEN campaign_status IN ('enviado','abierto','seguimiento_48h','seguimiento_96h')
                                              THEN 'interesado' ELSE campaign_status END
                   WHERE tracking_token = ?''',
                (now, token)
            )
            conn.execute(
                '''INSERT INTO et_seguimientos (contact_id, tipo, fecha, notas, resultado)
                   VALUES (?, 'click_cta', ?, 'Clic en botón de agenda (Calendly)', 'interesado')''',
                (row[0], now)
            )
            conn.commit()
            logger.info(f'[Track] CTA click — contact_id={row[0]}')
            # Opción B: promover automáticamente a gestión CRM
            _promote_to_prospect(conn, row[0])
    except Exception as e:
        logger.debug(f'[Track] click error: {e}')
    finally:
        conn.close()
    return redirect(dest, code=302)


@email_bp.route('/track/bounce', methods=['POST'])
def track_bounce():
    """Endpoint para registrar rebotes (llamado internamente al detectar error SMTP)."""
    data = request.get_json() or {}
    email   = data.get('email', '')
    reason  = data.get('reason', '')[:300]
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT id FROM et_contacts WHERE email = ?', (email,)
        ).fetchone()
        if row:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                '''UPDATE et_contacts
                   SET email_bounced   = 1,
                       campaign_status = 'rebotado'
                   WHERE email = ?''',
                (email,)
            )
            conn.execute(
                '''INSERT INTO et_seguimientos (contact_id, tipo, fecha, notas, resultado)
                   VALUES (?, 'bounce', ?, ?, 'rebotado')''',
                (row[0], now, f'Rebote: {reason}')
            )
            conn.commit()
    except Exception as e:
        logger.debug(f'[Track] bounce error: {e}')
    finally:
        conn.close()
    return jsonify({'ok': True})


@email_bp.route('/track/reply', methods=['POST'])
def track_reply():
    """Endpoint para registrar respuestas detectadas via Gmail API (llamado por inbox_monitor)."""
    data = request.get_json() or {}
    from_email  = data.get('from_email', '').lower().strip()
    subject     = data.get('subject', '')
    snippet     = data.get('snippet', '')[:500]
    message_id  = data.get('message_id', '')
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT id, estado_interes FROM et_contacts WHERE LOWER(TRIM(email)) = ?',
            (from_email,)
        ).fetchone()
        if row:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                '''UPDATE et_contacts
                   SET email_replied   = 1,
                       estado_interes  = CASE WHEN estado_interes IN ('pendiente','no_enviado')
                                              THEN 'respondido' ELSE estado_interes END,
                       campaign_status = 'respondido'
                   WHERE id = ?''',
                (row[0],)
            )
            conn.execute(
                '''INSERT INTO et_seguimientos (contact_id, tipo, fecha, notas, resultado)
                   VALUES (?, 'reply', ?, ?, 'respondido')''',
                (row[0], now, f'Asunto: {subject} | {snippet}')
            )
            conn.commit()
            logger.info(f'[Track] Respuesta registrada de {from_email} — contact_id={row[0]}')
            return jsonify({'ok': True, 'contact_id': row[0]})
        else:
            return jsonify({'ok': False, 'reason': 'contact_not_found'})
    except Exception as e:
        logger.error(f'[Track] reply error: {e}')
        return jsonify({'ok': False, 'error': str(e)})
    finally:
        conn.close()


# ── KPIs ─────────────────────────────────────────────────────────────────────

@email_bp.route('/kpis', methods=['GET'])
def get_kpis():
    conn = get_db()
    total_contacts  = conn.execute('SELECT COUNT(*) FROM et_contacts').fetchone()[0]
    total_campaigns = conn.execute('SELECT COUNT(*) FROM et_campaigns').fetchone()[0]

    # Métricas de tracking reales (de et_contacts)
    total_sent     = conn.execute("SELECT COUNT(*) FROM et_contacts WHERE campaign_status NOT IN ('pendiente','no_enviado')").fetchone()[0]
    total_opened   = conn.execute("SELECT COUNT(*) FROM et_contacts WHERE email_opened_at IS NOT NULL").fetchone()[0]
    total_replied  = conn.execute("SELECT COUNT(*) FROM et_contacts WHERE email_replied = 1").fetchone()[0]
    total_bounced  = conn.execute("SELECT COUNT(*) FROM et_contacts WHERE email_bounced = 1").fetchone()[0]
    total_clicks   = conn.execute("SELECT COUNT(*) FROM et_seguimientos WHERE tipo = 'click_cta'").fetchone()[0]
    interesados    = conn.execute("SELECT COUNT(*) FROM et_contacts WHERE estado_interes='interesado'").fetchone()[0]
    respondidos    = conn.execute("SELECT COUNT(*) FROM et_contacts WHERE estado_interes='respondido' OR email_replied=1").fetchone()[0]
    quiere_reunion = conn.execute("SELECT COUNT(*) FROM et_contacts WHERE estado_interes='quiere_reunion'").fetchone()[0]
    cerrados       = conn.execute("SELECT COUNT(*) FROM et_contacts WHERE estado_interes='cerrado'").fetchone()[0]
    reuniones      = conn.execute("SELECT COUNT(*) FROM et_reuniones WHERE estado='pendiente'").fetchone()[0]
    seguimientos_48h = conn.execute("SELECT COUNT(*) FROM et_contacts WHERE campaign_status='seguimiento_48h'").fetchone()[0]
    seguimientos_96h = conn.execute("SELECT COUNT(*) FROM et_contacts WHERE campaign_status='no_responde'").fetchone()[0]
    seguimientos_hoy = conn.execute(
        "SELECT COUNT(*) FROM et_contacts WHERE proximo_seguimiento <= ? AND campaign_status NOT IN ('no_responde','opt_out','rebotado')",
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),)
    ).fetchone()[0]

    rubros = conn.execute(
        'SELECT rubro, COUNT(*) as n FROM et_contacts GROUP BY rubro ORDER BY n DESC LIMIT 14'
    ).fetchall()
    comunas = conn.execute(
        'SELECT COALESCE(comuna, ciudad) as c, COUNT(*) as n FROM et_contacts GROUP BY c ORDER BY n DESC LIMIT 10'
    ).fetchall()

    # Envíos por día (últimos 14 días)
    daily = conn.execute(
        """SELECT DATE(created_at) as d, COUNT(*) as n
           FROM et_contacts WHERE created_at >= DATE('now','-14 days')
           GROUP BY d ORDER BY d""",
    ).fetchall()

    conn.close()
    return jsonify({
        'total_contacts':  total_contacts,
        'total_campaigns': total_campaigns,
        'total_sent':      total_sent,
        'opened':          total_opened,
        'replied':         total_replied,
        'bounced':         total_bounced,
        'clicks_cta':      total_clicks,
        'interesados':     interesados,
        'respondidos':     respondidos,
        'quiere_reunion':  quiere_reunion,
        'cerrados':        cerrados,
        'reuniones_pendientes': reuniones,
        'seguimientos_48h': seguimientos_48h,
        'seguimientos_96h': seguimientos_96h,
        'seguimientos_hoy': seguimientos_hoy,
        'open_rate':    round(total_opened  / total_sent * 100, 1) if total_sent else 0,
        'reply_rate':   round(total_replied / total_sent * 100, 1) if total_sent else 0,
        'bounce_rate':  round(total_bounced / total_sent * 100, 1) if total_sent else 0,
        'click_rate':   round(total_clicks  / total_sent * 100, 1) if total_sent else 0,
        'conversion_rate': round(interesados / total_contacts * 100, 1) if total_contacts else 0,
        'rubros':  [{'rubro': r[0], 'count': r[1]} for r in rubros],
        'comunas': [{'comuna': c[0], 'count': c[1]} for c in comunas],
        'daily':   [{'date': d[0], 'count': d[1]} for d in daily],
    })


# ── Inteligencia ─────────────────────────────────────────────────────────────

@email_bp.route('/intelligence', methods=['GET'])
def get_intelligence():
    conn = get_db()

    # ── Comunas stats ─────────────────────────────────────────────────────────
    prospected_comunas = conn.execute(
        '''SELECT COALESCE(NULLIF(TRIM(comuna),''), ciudad) as c,
                  COUNT(*) as n,
                  COUNT(CASE WHEN campaign_status='enviado' THEN 1 END) as enviados,
                  COUNT(CASE WHEN estado_interes IN ('interesado','quiere_reunion','cerrado') THEN 1 END) as interesados
           FROM et_contacts
           GROUP BY c ORDER BY n DESC'''
    ).fetchall()
    prospected_set = {r[0].lower().strip(): r for r in prospected_comunas if r[0]}

    comunas_data = []
    for c in COMUNAS_SANTIAGO:
        row = prospected_set.get(c.lower().strip())
        n = row[1] if row else 0
        env = row[2] if row else 0
        inter = row[3] if row else 0
        tasa = round(inter / env * 100, 1) if env else 0
        comunas_data.append({
            'comuna': c,
            'count': n,
            'enviados': env,
            'interesados': inter,
            'tasa_respuesta': tasa,
            'prospectada': c.lower().strip() in prospected_set,
        })

    # ── Rubros stats ──────────────────────────────────────────────────────────
    prospected_rubros = conn.execute(
        '''SELECT LOWER(TRIM(rubro)) as r,
                  COUNT(*) as n,
                  COUNT(CASE WHEN campaign_status='enviado' THEN 1 END) as enviados,
                  COUNT(CASE WHEN estado_interes IN ('interesado','quiere_reunion','cerrado') THEN 1 END) as interesados,
                  COUNT(CASE WHEN estado_interes='cerrado' THEN 1 END) as cerrados
           FROM et_contacts WHERE rubro IS NOT NULL GROUP BY r'''
    ).fetchall()
    rubro_map = {r[0]: {'count': r[1], 'enviados': r[2], 'interesados': r[3], 'cerrados': r[4]}
                 for r in prospected_rubros if r[0]}

    rubros_data = []
    for rubro in RUBROS:
        d = rubro_map.get(rubro.lower().strip(), {})
        env = d.get('enviados', 0)
        inter = d.get('interesados', 0)
        tasa = round(inter / env * 100, 1) if env else 0
        # Prioridad: sin leads = alta, tasa baja = media, resto = baja
        cnt = d.get('count', 0)
        if cnt == 0:
            prioridad = 'alta'
        elif tasa < 5:
            prioridad = 'media'
        else:
            prioridad = 'baja'
        rubros_data.append({
            'rubro': rubro,
            'count': cnt,
            'enviados': env,
            'interesados': inter,
            'cerrados': d.get('cerrados', 0),
            'tasa_respuesta': tasa,
            'prioridad': prioridad,
            'prospectado': rubro.lower().strip() in rubro_map,
        })

    # ── KPI summary ───────────────────────────────────────────────────────────
    rubros_con_leads   = len([r for r in rubros_data if r['count'] > 0])
    rubros_sin_leads   = len(RUBROS) - rubros_con_leads
    comunas_cubiertas  = len([c for c in comunas_data if c['prospectada']])
    # Acciones urgentes: rubros prioritarios o comunas con tasa 0 y enviados > 5
    urgentes = len([r for r in rubros_data if r['prioridad'] == 'alta']) + \
               len([c for c in comunas_data if c['enviados'] > 5 and c['tasa_respuesta'] == 0])

    # ── "Dónde buscar" — rubro×comuna combos sin cubrir ──────────────────────
    # For each rubro, find comunas not yet prospected for that specific rubro
    rubro_comunas_rows = conn.execute(
        '''SELECT LOWER(TRIM(rubro)) as r, LOWER(TRIM(COALESCE(NULLIF(TRIM(comuna),''), ciudad))) as c, COUNT(*) as n
           FROM et_contacts GROUP BY r, c'''
    ).fetchall()
    rubro_comunas_covered = {}
    for row in rubro_comunas_rows:
        if row[0] not in rubro_comunas_covered:
            rubro_comunas_covered[row[0]] = set()
        rubro_comunas_covered[row[0]].add(row[1])

    proximas_busquedas = []
    for rubro in RUBROS:
        covered = rubro_comunas_covered.get(rubro.lower().strip(), set())
        for comuna in COMUNAS_SANTIAGO:
            if comuna.lower().strip() not in covered:
                proximas_busquedas.append({'rubro': rubro, 'comuna': comuna})
                if len(proximas_busquedas) >= 20:
                    break
        if len(proximas_busquedas) >= 20:
            break

    # ── Scraping history ──────────────────────────────────────────────────────
    historial = conn.execute(
        '''SELECT run_id, tipo, rubro, comuna, status, leads_found, leads_inserted,
                  leads_skipped, error, started_at, finished_at
           FROM scraping_jobs ORDER BY started_at DESC LIMIT 50'''
    ).fetchall()
    hist_cols = ['run_id','tipo','rubro','comuna','status','leads_found',
                 'leads_inserted','leads_skipped','error','started_at','finished_at']
    historial_data = [dict(zip(hist_cols, r)) for r in historial]

    # ── Estado distribution ───────────────────────────────────────────────────
    estados_rows = conn.execute(
        '''SELECT COALESCE(estado_interes,'pendiente') as e, COUNT(*) as n
           FROM et_contacts GROUP BY e'''
    ).fetchall()
    estados = {r[0]: r[1] for r in estados_rows}

    # ── Comunas sin prospectar ────────────────────────────────────────────────
    sin_prospectar = [c['comuna'] for c in comunas_data if not c['prospectada']]
    rubros_sin     = [r['rubro'] for r in rubros_data if not r['prospectado']]

    conn.close()

    return jsonify({
        # KPIs
        'rubros_con_leads':  rubros_con_leads,
        'rubros_sin_leads':  rubros_sin_leads,
        'comunas_cubiertas': comunas_cubiertas,
        'acciones_urgentes': urgentes,
        'cobertura_comunas_pct': round(comunas_cubiertas / len(COMUNAS_SANTIAGO) * 100, 1),
        'cobertura_rubros_pct':  round(rubros_con_leads / len(RUBROS) * 100, 1),
        # Tables
        'rubros': rubros_data,
        'comunas': comunas_data,
        # Suggestions
        'sin_prospectar': sin_prospectar,
        'rubros_sin_prospectar': rubros_sin,
        'proximas_busquedas': proximas_busquedas,
        # History
        'historial': historial_data,
        # Estado distribution
        'estados': estados,
    })


# ── Inteligencia: decisiones explicadas ──────────────────────────────────────

@email_bp.route('/intel-targets-explained', methods=['GET'])
def intel_targets_explained():
    """
    Devuelve los objetivos del próximo scraping con el razonamiento completo:
    - Por qué se eligió cada rubro (prioridad 1 = sin datos, prioridad 2 = pocos pendientes)
    - Por qué se eligió cada comuna (menos prospectada para ese rubro)
    - Datos de soporte: total, pendientes, enviados, tasa de respuesta
    - Conteo de comunas ya prospectadas vs total
    """
    import secrets as _secrets

    conn = get_db()

    # ── Datos de et_contacts por rubro ────────────────────────────────────────
    email_stats = conn.execute(
        """SELECT LOWER(TRIM(rubro)) as r,
                  COUNT(*) as total,
                  COUNT(CASE WHEN campaign_status IN ('pendiente','no_enviado') THEN 1 END) as pendientes,
                  COUNT(CASE WHEN campaign_status = 'enviado' THEN 1 END) as enviados,
                  COUNT(CASE WHEN estado_interes IN ('interesado','quiere_reunion','cerrado') THEN 1 END) as respondidos
           FROM et_contacts
           WHERE rubro IS NOT NULL AND rubro != ''
           GROUP BY LOWER(TRIM(rubro))"""
    ).fetchall()
    stats_map = {r['r']: dict(r) for r in email_stats}

    # ── Comunas ya prospectadas por rubro ─────────────────────────────────────
    rubro_comunas = conn.execute(
        """SELECT LOWER(TRIM(rubro)) as r,
                  LOWER(TRIM(COALESCE(NULLIF(TRIM(comuna),''), ciudad))) as c,
                  COUNT(*) as n
           FROM et_contacts
           WHERE rubro IS NOT NULL AND rubro != ''
           GROUP BY r, c"""
    ).fetchall()
    # rubro → {comuna: count}
    rubro_comunas_map = {}
    for row in rubro_comunas:
        rubro_comunas_map.setdefault(row['r'], {})[row['c']] = row['n']

    # ── Comunas top por tasa de respuesta (tabla leads) ───────────────────────
    top_comunas_rows = conn.execute('''
        SELECT l.comuna,
               COUNT(DISTINCT CASE WHEN ls.status='interesado' THEN l.id END) AS interesados
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        WHERE l.comuna IS NOT NULL AND l.comuna != ''
        GROUP BY l.comuna
        ORDER BY interesados DESC LIMIT 20
    ''').fetchall()

    _COMUNAS_LOWER = {c.lower() for c in COMUNAS_SANTIAGO}
    mejores_comunas = [r['comuna'] for r in top_comunas_rows
                       if r['comuna'].lower().strip() in _COMUNAS_LOWER]
    if not mejores_comunas:
        mejores_comunas = COMUNAS_SANTIAGO[:8]

    # ── Rubros activos ────────────────────────────────────────────────────────
    rubros_rows = conn.execute(
        'SELECT rubro FROM et_rubro_templates ORDER BY id'
    ).fetchall()
    active_rubros = [r['rubro'] for r in rubros_rows] if rubros_rows else RUBROS
    n_rubros = max(len(active_rubros), 1)

    conn.close()

    TARGET = 100
    targets_explained = []
    seen = set()

    for rubro in active_rubros:
        rk = rubro.lower().strip()
        s  = stats_map.get(rk, {})
        total     = s.get('total',      0)
        pendientes = s.get('pendientes', 0)
        enviados  = s.get('enviados',   0)
        respondidos = s.get('respondidos', 0)
        tasa = round(respondidos / enviados * 100, 1) if enviados else 0

        # ── Determinar prioridad y razón ──────────────────────────────────────
        if total == 0:
            prioridad = 1
            razon_rubro = 'Sin contactos aún — nunca se ha prospectado este rubro'
            razon_icono = '🚨'
            max_items   = 15
            # Comuna: aleatoria de las mejores (sin datos propios aún)
            target_comunas = [(_secrets.choice(mejores_comunas[:6]), 'Top por tasa de respuesta general')]
        elif pendientes < 10:
            prioridad = 2
            razon_rubro = f'Solo {pendientes} contacto{"s" if pendientes!=1 else ""} pendiente{"s" if pendientes!=1 else ""} — necesita restock'
            razon_icono = '⚠️'
            max_items   = max(8, TARGET // n_rubros)
            # Comunas menos prospectadas para este rubro
            cc_map = rubro_comunas_map.get(rk, {})
            target_comunas_list = sorted(
                COMUNAS_SANTIAGO,
                key=lambda c: (cc_map.get(c.lower(), 0), c)
            )[:2]
            target_comunas = []
            for tc in target_comunas_list:
                n_tc = cc_map.get(tc.lower(), 0)
                if n_tc == 0:
                    razon_c = f'Nunca prospectada para {rubro}'
                else:
                    razon_c = f'Solo {n_tc} contacto{"s" if n_tc!=1 else ""} — la menos cubierta'
                target_comunas.append((tc, razon_c))
        else:
            continue  # No entra en el próximo scraping

        # Datos de comunas ya cubiertas para este rubro
        comunas_cubiertas = len(rubro_comunas_map.get(rk, {}))
        comunas_total     = len(COMUNAS_SANTIAGO)

        for (comuna, razon_comuna) in target_comunas:
            key = (rk, comuna.lower())
            if key in seen:
                continue
            seen.add(key)

            # Cuánto ya se prospectó esta combo específica
            n_esta_combo = rubro_comunas_map.get(rk, {}).get(comuna.lower(), 0)

            targets_explained.append({
                'rubro':             rubro,
                'comuna':            comuna,
                'prioridad':         prioridad,
                'prioridad_label':   '🚨 Urgente' if prioridad == 1 else '⚠️ Restock',
                'razon_rubro':       razon_rubro,
                'razon_rubro_icono': razon_icono,
                'razon_comuna':      razon_comuna,
                'max_items':         max_items,
                'stats': {
                    'total':          total,
                    'pendientes':     pendientes,
                    'enviados':       enviados,
                    'respondidos':    respondidos,
                    'tasa':           tasa,
                    'n_esta_combo':   n_esta_combo,
                    'comunas_cubiertas': comunas_cubiertas,
                    'comunas_total':  comunas_total,
                },
            })

    # Ordenar: prioridad 1 primero, luego prioridad 2
    targets_explained.sort(key=lambda x: x['prioridad'])

    return jsonify({
        'targets':    targets_explained,
        'total_rubros':  len(active_rubros),
        'target_emails': TARGET,
        'mejores_comunas': mejores_comunas[:6],
        'logica': {
            'paso1': 'Rubros sin ningún contacto en la base → Prioridad máxima, 15 leads por búsqueda',
            'paso2': 'Rubros con menos de 10 contactos pendientes → Restock en las 2 comunas menos cubiertas',
            'paso3': 'Comunas elegidas: primero las que nunca se han prospectado para ese rubro; en empate, las con menos contactos totales',
            'objetivo': f'Objetivo diario: {TARGET} emails · vía Outscraper google_maps_search + enrichment domains_service',
        },
    })


# ── Scheduler / job runs (checktask) ─────────────────────────────────────────

@email_bp.route('/scheduler/job-runs', methods=['GET'])
def get_job_runs():
    """
    Retorna el estado de hoy para los 4 jobs de email:
    auto_scraping, email_daily, email_followup, inbox_monitor.
    Para cada job: último run del día (status, result_count, hora).
    """
    conn = get_db()
    today = datetime.now().strftime('%Y-%m-%d')

    JOB_IDS = ['auto_scraping', 'email_daily', 'email_followup', 'inbox_monitor']
    result = {}
    for jid in JOB_IDS:
        row = conn.execute(
            '''SELECT status, result_count, started_at, finished_at, error
               FROM job_runs
               WHERE job_id = ? AND DATE(started_at) = ?
               ORDER BY started_at DESC LIMIT 1''',
            (jid, today)
        ).fetchone()
        if row:
            result[jid] = {
                'status':       row['status'],
                'count':        row['result_count'] or 0,
                'started_at':   row['started_at'],
                'finished_at':  row['finished_at'],
                'error':        row['error'],
            }
        else:
            result[jid] = None   # no corrió hoy

    conn.close()
    return jsonify(result)


# ── Scheduler / upcoming ──────────────────────────────────────────────────────

@email_bp.route('/scheduler/upcoming', methods=['GET'])
def get_upcoming():
    conn = get_db()
    now = datetime.now()

    # Próximos seguimientos
    followups = conn.execute(
        '''SELECT c.id, c.business_name, c.email, c.rubro, c.comuna,
                  c.proximo_seguimiento, c.seguimiento_count, c.estado_interes
           FROM et_contacts c
           WHERE c.proximo_seguimiento IS NOT NULL
             AND c.proximo_seguimiento >= ?
             AND c.estado_interes = 'pendiente'
             AND c.seguimiento_count < 3
           ORDER BY c.proximo_seguimiento ASC LIMIT 50''',
        (now.strftime('%Y-%m-%d %H:%M:%S'),)
    ).fetchall()

    # Próximas reuniones
    reuniones = conn.execute(
        '''SELECT r.id, r.fecha, r.hora, r.lugar, r.estado,
                  c.business_name, c.email, c.rubro
           FROM et_reuniones r
           JOIN et_contacts c ON r.contact_id = c.id
           WHERE r.fecha >= ? AND r.estado != 'cancelada'
           ORDER BY r.fecha ASC LIMIT 20''',
        (now.strftime('%Y-%m-%d'),)
    ).fetchall()

    def row_to_dict(row):
        return dict(row) if hasattr(row, 'keys') else {}

    return jsonify({
        'followups': [dict(r) for r in followups],
        'reuniones': [dict(r) for r in reuniones],
        'total_followups': len(followups),
        'total_reuniones': len(reuniones),
    })


@email_bp.route('/scheduler/run-followup', methods=['POST'])
def trigger_followup():
    from jobs.email_automation import run_followup_in_thread
    run_followup_in_thread()
    return jsonify({'ok': True, 'message': 'Seguimiento iniciado en background'})


@email_bp.route('/scheduler/run-daily', methods=['POST'])
def trigger_daily():
    from jobs.email_automation import run_daily_in_thread
    run_daily_in_thread()
    return jsonify({'ok': True, 'message': 'Prospección diaria iniciada en background'})


@email_bp.route('/scheduler/check-inbox', methods=['POST'])
def trigger_inbox_check():
    """Ejecuta manualmente el monitoreo de bandeja de entrada."""
    from jobs.inbox_monitor import check_inbox
    result = check_inbox(max_messages=200)
    return jsonify({'ok': True, **result})


@email_bp.route('/tracking/stats', methods=['GET'])
def get_tracking_stats():
    """Retorna las métricas de tracking de la última semana con detalle por día."""
    conn = get_db()
    # Actividad reciente de seguimientos
    recent = conn.execute(
        '''SELECT s.tipo, s.fecha, s.notas, s.resultado,
                  c.business_name, c.email, c.rubro, c.comuna
           FROM et_seguimientos s
           LEFT JOIN et_contacts c ON s.contact_id = c.id
           ORDER BY s.fecha DESC LIMIT 100'''
    ).fetchall()
    cols = ['tipo','fecha','notas','resultado','business_name','email','rubro','comuna']

    # Contactos respondidos recientes
    respondidos = conn.execute(
        '''SELECT id, business_name, email, rubro, comuna, campaign_status,
                  email_opened_at, email_replied, email_bounced, last_followup_at
           FROM et_contacts
           WHERE email_replied=1 OR email_bounced=1 OR email_opened_at IS NOT NULL
           ORDER BY COALESCE(email_opened_at, last_followup_at) DESC LIMIT 50'''
    ).fetchall()
    rcols = ['id','business_name','email','rubro','comuna','campaign_status',
             'email_opened_at','email_replied','email_bounced','last_followup_at']
    conn.close()

    return jsonify({
        'activity': [dict(zip(cols, r)) for r in recent],
        'engaged_contacts': [dict(zip(rcols, r)) for r in respondidos],
    })


# ── Campaigns ─────────────────────────────────────────────────────────────────

@email_bp.route('/campaigns', methods=['GET'])
def get_campaigns():
    conn = get_db()
    cur = conn.execute('SELECT * FROM et_campaigns ORDER BY created_at DESC')
    cols = [d[0] for d in cur.description]
    return jsonify([dict(zip(cols, r)) for r in cur.fetchall()])


@email_bp.route('/campaigns', methods=['POST'])
def create_campaign():
    data = request.get_json() or {}
    if not all(data.get(k) for k in ['name', 'subject', 'body']):
        return jsonify({'ok': False, 'error': 'name, subject y body requeridos'}), 400
    conn = get_db()
    cur = conn.execute(
        '''INSERT INTO et_campaigns (name, subject, body, rubro, schedule_time, status, created_at)
           VALUES (?,?,?,?,?,?,?)''',
        (data['name'], data['subject'], data['body'],
         data.get('rubro', ''), data.get('schedule_time', ''),
         'borrador', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    return jsonify({'ok': True, 'id': cur.lastrowid})


@email_bp.route('/campaigns/<int:cid>', methods=['DELETE'])
def delete_campaign(cid):
    conn = get_db()
    conn.execute('DELETE FROM et_campaigns WHERE id=?', (cid,))
    conn.commit()
    return jsonify({'ok': True})


@email_bp.route('/campaigns/<int:cid>/send', methods=['POST'])
def send_campaign(cid):
    data = request.get_json() or {}
    test_address = data.get('test_email', '').strip()

    import threading
    result_holder = {}

    def run():
        result_holder['r'] = _do_send_campaign(cid, test_address)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout=300)
    return jsonify(result_holder.get('r', {'ok': False, 'error': 'Timeout — envío demoró más de 5 min'}))


@email_bp.route('/campaigns/<int:tid>/send-selected', methods=['POST'])
def send_campaign_selected(tid):
    """Envía el template a una lista específica de contact_ids (selección manual)."""
    data = request.get_json() or {}
    contact_ids = [int(i) for i in data.get('contact_ids', []) if str(i).isdigit()]
    if not contact_ids:
        return jsonify({'ok': False, 'error': 'Sin contactos seleccionados'}), 400

    import threading
    result_holder = {}

    def run():
        result_holder['r'] = _do_send_campaign(tid, contact_ids_filter=contact_ids)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout=300)
    return jsonify(result_holder.get('r', {'ok': False, 'error': 'Timeout'}))


@email_bp.route('/campaigns/<int:cid>/send-test', methods=['POST'])
def send_test(cid):
    data = request.get_json() or {}
    test_email = data.get('email', '').strip()
    if not test_email:
        return jsonify({'ok': False, 'error': 'email requerido'}), 400
    r = _do_send_campaign(cid, test_address=test_email)
    return jsonify(r)


def _do_send_campaign(campaign_id, test_address='', contact_ids_filter=None):
    """
    contact_ids_filter: list[int] — si se pasa, envía solo a esos contactos
                        (ignora filtro de rubro y estado pendiente).
    """
    conn = get_db()
    # Primero buscar en et_campaigns (campañas manuales guardadas)
    cur = conn.execute('SELECT * FROM et_campaigns WHERE id=?', (campaign_id,))
    cols = [d[0] for d in cur.description]
    row = cur.fetchone()
    if not row:
        # Fallback: el frontend pasa el ID del template (et_rubro_templates)
        cur = conn.execute('SELECT * FROM et_rubro_templates WHERE id=?', (campaign_id,))
        cols = [d[0] for d in cur.description]
        row = cur.fetchone()
        if not row:
            return {'ok': False, 'error': 'Campaña no encontrada'}
    camp = dict(zip(cols, row))

    if test_address:
        contacts = [{'id': 0, 'email': test_address, 'business_name': 'Test'}]
    elif contact_ids_filter:
        # Envío manual — solo los IDs seleccionados, sin restricción de estado
        placeholders = ','.join('?' * len(contact_ids_filter))
        rows = conn.execute(
            f'SELECT id, email, business_name FROM et_contacts '
            f'WHERE id IN ({placeholders}) AND (opt_out IS NULL OR opt_out = 0)',
            contact_ids_filter
        ).fetchall()
        contacts = [{'id': r[0], 'email': r[1], 'business_name': r[2]} for r in rows]
    else:
        # Traer todos los pendientes y filtrar en Python (tolerante a acentos y plural)
        all_rows = conn.execute(
            "SELECT id, email, business_name, rubro FROM et_contacts "
            "WHERE campaign_status IN ('pendiente','no_enviado') "
            "AND (opt_out IS NULL OR opt_out = 0)"
        ).fetchall()
        if camp.get('rubro'):
            contacts = [
                {'id': r[0], 'email': r[1], 'business_name': r[2]}
                for r in all_rows
                if _rubro_match(camp['rubro'], r[3] or '')
            ]
        else:
            contacts = [{'id': r[0], 'email': r[1], 'business_name': r[2]}
                        for r in all_rows]

    import os, smtplib, ssl, pathlib
    base_url   = os.getenv('APP_BASE_URL', 'http://127.0.0.1:5000')
    camp_rubro = camp.get('rubro', '')

    # ── Pre-generar assets UNA sola vez para toda la campaña ──────────────────
    c_content = _get_rubro_content(camp_rubro)
    try:
        hdr_gif = _compose_header_gif_desktop(c_content)
    except Exception as e:
        logger.warning(f'[EmailTool] header GIF falló: {e}'); hdr_gif = None
    try:
        pos_gif = _compose_pos_gif()
    except Exception as e:
        logger.warning(f'[EmailTool] POS GIF falló: {e}'); pos_gif = None
    sig_path = pathlib.Path(__file__).parent.parent / 'static' / 'email_assets' / 'sig_photo.jpeg'
    sig_bytes = sig_path.read_bytes() if sig_path.exists() else None

    # ── Abrir UNA conexión SMTP para toda la campaña ──────────────────────────
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_pass = os.getenv('SMTP_PASS', '')
    smtp_conn = None
    # Si EMAIL_LOCAL_URL esta seteado, NO abrir conexion SMTP en Railway
    # Cada email va via proxy local
    use_local_proxy = bool(os.getenv('EMAIL_LOCAL_URL', '').strip())
    if use_local_proxy:
        logger.info('[EmailTool] Modo proxy local activo (EMAIL_LOCAL_URL set)')
    elif smtp_user and smtp_pass and contacts:
        try:
            ctx = ssl.create_default_context()
            smtp_conn = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            smtp_conn.ehlo()
            smtp_conn.starttls(context=ctx)
            smtp_conn.login(smtp_user, smtp_pass)
            logger.info('[EmailTool] Conexión SMTP abierta para campaña masiva')
        except Exception as e:
            logger.warning(f'[EmailTool] SMTP no disponible ({e}) — usando SendGrid API')
            smtp_conn = None  # continuar sin SMTP; _send_smtp usará SendGrid

    rubro_data = RUBRO_EMAIL_CONTENT.get(camp_rubro.lower().strip())

    sent = errors = 0
    try:
        for c in contacts:
            token           = _ensure_opt_out_token(c['id']) if c['id'] else str(uuid.uuid4())[:16]
            unsubscribe_url = f"{base_url}/api/email-tool/unsubscribe/{token}"
            booking_url_c   = f"{base_url}/api/email-tool/booking/{token}" if c['id'] else ''

            subject = rubro_data['subject'] if rubro_data else camp.get('subject','').replace('{nombre}', c['business_name'] or '')
            body    = camp.get('body','').replace('{nombre}', c['business_name'] or '')

            res = _send_smtp(
                c['email'], subject, body, unsubscribe_url,
                rubro=camp_rubro, contact_name=c['business_name'] or '',
                booking_url=booking_url_c,
                _hdr_gif=hdr_gif, _pos_gif=pos_gif, _sig_bytes=sig_bytes,
                _smtp_conn=smtp_conn,
            )
            status = 'enviado' if res['ok'] else 'error'
            if not test_address:
                conn.execute(
                    'INSERT INTO et_sends (campaign_id, contact_id, sent_at, status) VALUES (?,?,?,?)',
                    (campaign_id, c['id'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), status)
                )
                if res['ok']:
                    followup_dt = (datetime.now() + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
                    conn.execute(
                        "UPDATE et_contacts SET campaign_status='enviado', fecha_envio=?, proximo_seguimiento=? WHERE id=?",
                        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), followup_dt, c['id'])
                    )
            if res['ok']:
                sent += 1
                time.sleep(MANUAL_SEND_THROTTLE_SECS)   # Regla 6: throttle entre envíos
            else:
                errors += 1
                logger.warning(f'[EmailTool] Error enviando a {c["email"]}: {res.get("error")}')
    finally:
        if smtp_conn:
            try: smtp_conn.quit()
            except Exception: pass

    conn.commit()
    return {'ok': True, 'sent': sent, 'errors': errors, 'total': len(contacts)}


# ── Preview HTML real del email ───────────────────────────────────────────────

@email_bp.route('/preview-email/header.gif')
def preview_header_gif():
    """GIF animado del header — anima en Gmail desktop y mobile."""
    from flask import make_response as _mr
    rubro = request.args.get('rubro', '')
    c = _get_rubro_content(rubro)
    gif_bytes = _compose_header_gif_desktop(c)
    resp = _mr(gif_bytes)
    resp.headers['Content-Type'] = 'image/gif'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@email_bp.route('/preview-email/header.webp')
def preview_header_webp():
    """WebP animado del header — preview en browser (no usar para email)."""
    from flask import make_response as _mr
    rubro = request.args.get('rubro', '')
    c = _get_rubro_content(rubro)
    webp_bytes = _compose_header_gif(c)
    resp = _mr(webp_bytes)
    resp.headers['Content-Type'] = 'image/webp'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@email_bp.route('/preview-email/pos.gif')
def preview_pos_gif():
    """GIF animado del POS — anima en Gmail desktop y mobile."""
    from flask import make_response as _mr
    gif_bytes = _compose_pos_gif()
    resp = _mr(gif_bytes)
    resp.headers['Content-Type'] = 'image/gif'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@email_bp.route('/preview-email/pos.webp')
def preview_pos_webp():
    """Alias legacy — redirige al GIF."""
    from flask import redirect
    return redirect('/api/email-tool/preview-email/pos.gif')


@email_bp.route('/preview-email', methods=['GET'])
def preview_email():
    """Retorna el HTML completo del email para un rubro dado (para mostrar en iframe)."""
    rubro = request.args.get('rubro', '')
    html = _build_html_email('', '', rubro=rubro, contact_name='[Nombre]', booking_url='#')
    # GIFs animados servidos por endpoints dedicados
    html = html.replace('src="cid:email_hdr_anim"',
                        f'src="/api/email-tool/preview-email/header.gif?rubro={rubro}"')
    html = html.replace('src="cid:email_pos_anim"',
                        'src="/api/email-tool/preview-email/pos.gif"')
    html = html.replace('src="cid:email_sig_photo"',
                        'src="/static/email_assets/sig_photo.jpeg"')
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


@email_bp.route('/preview-email/send-test', methods=['POST'])
def preview_send_test():
    """Envía email de prueba para un rubro directamente, sin necesitar campaign ID."""
    data = request.get_json() or {}
    rubro      = data.get('rubro', '').strip()
    test_email = data.get('email', '').strip()
    if not test_email:
        return jsonify({'ok': False, 'error': 'email requerido'}), 400

    c       = _get_rubro_content(rubro)
    subject = c.get('subject', 'Mercado Pago para tu negocio')
    body    = c.get('body', 'Este es un email de prueba.')

    base_url = request.url_root.rstrip('/')
    import os
    from_name = os.getenv('EMAIL_FROM_NAME', 'Juan Sebastián Pinto')
    result = _send_smtp(
        test_email, f'[TEST] {subject}', body,
        unsubscribe_url='#', rubro=rubro,
        contact_name='[Nombre]', booking_url=f'{base_url}/api/email-tool/booking-demo'
    )
    return jsonify(result)


# ── Templates por rubro ───────────────────────────────────────────────────────

@email_bp.route('/templates', methods=['GET'])
def get_templates():
    conn = get_db()
    cur = conn.execute('SELECT * FROM et_rubro_templates ORDER BY rubro')
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    # Enrich with RUBRO_EMAIL_CONTENT fields for frontend preview
    for row in rows:
        key = (row.get('rubro') or '').lower().strip()
        c = RUBRO_EMAIL_CONTENT.get(key, {})
        row['h1']         = c.get('h1', 'Esto tarda menos')
        row['h2']         = c.get('h2', '')
        row['h3']         = c.get('h3', '')
        row['preheader']  = c.get('preheader', '')
        row['icon_strip'] = c.get('icon_strip', '')
        row['cta_text']   = c.get('cta_text', '→ Dame 15 minutos para mostrártelo')
        row['pain']       = c.get('pain', '')
        row['body_text']  = c.get('body', '')
        row['header_bg']  = c.get('header_bg', '#1A1A2E')
        row['pain_bg']    = c.get('pain_bg', '#FFF8E1')
        row['benefits_data'] = c.get('benefits', [])
    return jsonify(rows)


@email_bp.route('/templates/<rubro>', methods=['GET'])
def get_template(rubro):
    conn = get_db()
    cur = conn.execute(
        'SELECT * FROM et_rubro_templates WHERE rubro LIKE ? LIMIT 1',
        (f'%{rubro}%',)
    )
    cols = [d[0] for d in cur.description]
    row = cur.fetchone()
    if not row:
        return jsonify({'error': 'no encontrado'}), 404
    return jsonify(dict(zip(cols, row)))


@email_bp.route('/templates/<int:tid>/upload-pdf', methods=['POST'])
def upload_template_pdf(tid):
    import pathlib
    if 'pdf' not in request.files:
        return jsonify({'ok': False, 'error': 'No se envió archivo'}), 400
    f = request.files['pdf']
    if not f.filename.lower().endswith('.pdf'):
        return jsonify({'ok': False, 'error': 'Solo se aceptan archivos PDF'}), 400

    conn = get_db()
    row = conn.execute('SELECT rubro FROM et_rubro_templates WHERE id=?', (tid,)).fetchone()
    if not row:
        return jsonify({'ok': False, 'error': 'Template no encontrado'}), 404

    safe_rubro = row['rubro'].replace(' ', '_').replace('/', '_')
    pdf_dir = pathlib.Path(__file__).parent.parent / 'static' / 'pdfs'
    pdf_dir.mkdir(exist_ok=True)
    dest = pdf_dir / f'{safe_rubro}.pdf'
    f.save(str(dest))

    conn.execute('UPDATE et_rubro_templates SET pdf_path=? WHERE id=?', (str(dest), tid))
    conn.commit()
    return jsonify({'ok': True, 'path': str(dest)})


@email_bp.route('/templates/<int:tid>', methods=['PATCH'])
def update_template(tid):
    data = request.get_json() or {}
    allowed = ['subject', 'body']
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'ok': False}), 400
    updates['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    set_clause = ', '.join(f'{k} = ?' for k in updates)
    conn = get_db()
    conn.execute(f'UPDATE et_rubro_templates SET {set_clause} WHERE id = ?',
                 list(updates.values()) + [tid])
    conn.commit()
    return jsonify({'ok': True})


# ── PDF por rubro ─────────────────────────────────────────────────────────────

@email_bp.route('/pdf/<rubro>', methods=['GET'])
def get_pdf(rubro):
    try:
        from routes.pdf_generator import generate_pdf
        pdf_bytes = generate_pdf(rubro)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=False,
            download_name=f'MercadoPago_{rubro.replace(" ", "_")}.pdf'
        )
    except Exception as e:
        logger.error(f'[PDF] Error generando PDF para {rubro}: {e}')
        return jsonify({'error': str(e)}), 500


# ── Opt-out / unsubscribe ────────────────────────────────────────────────────

def _ensure_opt_out_token(contact_id: int) -> str:
    conn = get_db()
    row = conn.execute('SELECT opt_out_token FROM et_contacts WHERE id=?', (contact_id,)).fetchone()
    if row and row['opt_out_token']:
        return row['opt_out_token']
    token = str(uuid.uuid4()).replace('-', '')[:24]
    conn.execute('UPDATE et_contacts SET opt_out_token=? WHERE id=?', (token, contact_id))
    conn.commit()
    return token


@email_bp.route('/unsubscribe/<token>', methods=['GET'])
def unsubscribe(token):
    conn = get_db()
    row = conn.execute(
        'SELECT id, business_name, email FROM et_contacts WHERE opt_out_token=?', (token,)
    ).fetchone()
    if not row:
        return '<h2>Link inválido o ya procesado.</h2>', 404

    conn.execute(
        "UPDATE et_contacts SET opt_out=1, estado_interes='no_interesado', campaign_status='opt_out' WHERE opt_out_token=?",
        (token,)
    )
    conn.commit()
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Dado de baja</title></head>
<body style="font-family:sans-serif;text-align:center;padding:60px;background:#F0F4F8;">
  <div style="max-width:480px;margin:0 auto;background:#fff;padding:40px;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
    <div style="font-size:40px;margin-bottom:16px;">✅</div>
    <h2 style="color:#1A1A2E;">Dado de baja correctamente</h2>
    <p style="color:#6B7280;font-size:14px;margin-top:12px;">
      El email <strong>{row['email']}</strong> no recibirá más mensajes de MercadoPago.<br>
      Si fue un error, puedes contactarnos a <a href="mailto:juansebastian.pinto@mercadolibre.cl">juansebastian.pinto@mercadolibre.cl</a>.
    </p>
  </div>
</body></html>"""


# ── Envío individual por contacto ─────────────────────────────────────────────

@email_bp.route('/contacts/<int:cid>/send-email', methods=['POST'])
def send_contact_email(cid):
    import os
    conn = get_db()
    row = conn.execute('SELECT * FROM et_contacts WHERE id=?', (cid,)).fetchone()
    if not row:
        return jsonify({'ok': False, 'error': 'Contacto no encontrado'}), 404

    contact = dict(row)
    if contact.get('opt_out'):
        return jsonify({'ok': False, 'error': 'Este contacto se dio de baja'}), 400

    rubro = contact.get('rubro', '')
    tpl_row = conn.execute(
        'SELECT subject, body FROM et_rubro_templates WHERE rubro LIKE ? LIMIT 1',
        (f'%{(rubro or "").split()[0]}%',)
    ).fetchone() if rubro else None

    if tpl_row:
        subject = tpl_row['subject']
        body    = tpl_row['body'].replace('{nombre}', contact.get('business_name') or '')
    else:
        name    = contact.get('business_name') or 'estimado'
        subject = 'Solución de cobro para tu negocio — MercadoPago'
        body    = (f'Hola Equipo de {name},\n\nTe escribo desde MercadoPago para presentarte el Smart Point, '
                   f'nuestra terminal de cobro sin costo mensual.\n\n'
                   f'¿Tienes 10 minutos esta semana para una llamada?\n\n'
                   f'Saludos,\nJuan Sebastián Pinto\nEjecutivo MercadoPago')

    token = _ensure_opt_out_token(cid)
    base_url = os.getenv('APP_BASE_URL', 'http://127.0.0.1:5000')
    unsubscribe_url = f"{base_url}/api/email-tool/unsubscribe/{token}"
    booking_url     = f"{base_url}/api/email-tool/booking/{token}"

    c_rubro = RUBRO_EMAIL_CONTENT.get(rubro.lower().strip()) if rubro else None
    subject = (c_rubro['subject'] if c_rubro else subject)

    res = _send_smtp(contact['email'], subject, body, unsubscribe_url,
                     rubro=rubro, contact_name=contact.get('business_name', ''),
                     booking_url=booking_url)

    if res['ok']:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        followup = (datetime.now() + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            "UPDATE et_contacts SET campaign_status='enviado', fecha_envio=?, proximo_seguimiento=? WHERE id=?",
            (now, followup, cid)
        )
        conn.execute(
            "INSERT INTO et_seguimientos (contact_id, tipo, fecha, notas, resultado) VALUES (?,?,?,?,?)",
            (cid, 'email', now, f'Email manual enviado — {subject}', 'enviado')
        )
        conn.commit()

    return jsonify(res)


# ── Booking / agendamiento ────────────────────────────────────────────────────

def _generate_ics(summary: str, dt_start: datetime, dt_end: datetime,
                  organizer_email: str, attendee_email: str, description: str = '') -> str:
    uid = str(uuid.uuid4())
    now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    start = dt_start.strftime('%Y%m%dT%H%M%S')
    end   = dt_end.strftime('%Y%m%dT%H%M%S')
    desc_safe = description.replace('\n', '\\n').replace(',', '\\,')
    return (
        'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//MP Prospecting//ES\r\nMETHOD:REQUEST\r\n'
        'BEGIN:VEVENT\r\n'
        f'UID:{uid}\r\nDTSTAMP:{now}\r\n'
        f'DTSTART;TZID=America/Santiago:{start}\r\n'
        f'DTEND;TZID=America/Santiago:{end}\r\n'
        f'SUMMARY:{summary}\r\nDESCRIPTION:{desc_safe}\r\n'
        f'ORGANIZER;CN={organizer_email}:MAILTO:{organizer_email}\r\n'
        f'ATTENDEE;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:MAILTO:{attendee_email}\r\n'
        'STATUS:CONFIRMED\r\n'
        'BEGIN:VALARM\r\nTRIGGER:-PT30M\r\nACTION:DISPLAY\r\n'
        f'DESCRIPTION:Recordatorio: {summary}\r\nEND:VALARM\r\n'
        'END:VEVENT\r\nEND:VCALENDAR\r\n'
    )


_BOOKING_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Agendar reunión — Mercado Pago</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#F5F0E8;font-family:'DM Sans',sans-serif;min-height:100vh;display:flex;
     align-items:center;justify-content:center;padding:32px 16px}
.card{background:#fff;border-radius:20px;overflow:hidden;width:100%;max-width:480px;
      border:1.5px solid #E0D9CC;box-shadow:6px 6px 0 #C8BFA8}
.card-header{background:#1A1A2E;padding:28px 32px 24px}
.logo-row{display:flex;align-items:center;gap:10px;margin-bottom:20px}
.logo-icon{width:32px;height:32px;background:#FFE600;border-radius:8px;display:flex;
           align-items:center;justify-content:center;font-weight:800;font-size:14px;color:#1A1A2E}
.logo-text{font-size:13px;font-weight:700;color:#FFE600;letter-spacing:.05em}
h1{font-size:22px;font-weight:700;color:#fff;line-height:1.2}
h1 span{color:#FFE600}
.sub{margin-top:8px;font-size:13px;color:rgba(255,255,255,.5)}
.card-body{padding:28px 32px}
.form-group{margin-bottom:16px}
label{display:block;font-size:12px;font-weight:600;color:#374151;text-transform:uppercase;
      letter-spacing:.04em;margin-bottom:6px}
input,select{width:100%;border:1.5px solid #E5E7EB;border-radius:10px;padding:10px 14px;
             font-size:14px;color:#1A1A2E;background:#fff;outline:none;font-family:inherit;
             transition:border-color .15s}
input:focus,select:focus{border-color:#FFE600}
.time-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:6px}
.time-btn{border:1.5px solid #E5E7EB;border-radius:8px;padding:8px;text-align:center;
          font-size:13px;cursor:pointer;background:#fff;transition:all .15s;color:#374151}
.time-btn:hover,.time-btn.sel{background:#1A1A2E;color:#FFE600;border-color:#1A1A2E}
.btn-submit{width:100%;background:#1A1A2E;color:#FFE600;border:none;border-radius:100px;
            padding:14px;font-size:14px;font-weight:700;cursor:pointer;letter-spacing:.05em;
            box-shadow:3px 3px 0 #C8BFA8;margin-top:8px;transition:all .15s}
.btn-submit:hover{transform:translate(-2px,-2px);box-shadow:5px 5px 0 #C8BFA8}
.success{text-align:center;padding:40px 32px}
.success .emoji{font-size:48px;margin-bottom:16px}
.success h2{font-size:20px;font-weight:700;color:#1A1A2E}
.success p{font-size:14px;color:#6B7280;margin-top:8px;line-height:1.6}
.hidden{display:none}
</style>
</head>
<body>
<div class="card">
  <div class="card-header">
    <div class="logo-row">
      <div class="logo-icon">MP</div>
      <div class="logo-text">MERCADO PAGO</div>
    </div>
    <h1>Elige cuándo <span>llamarte</span></h1>
    <div class="sub">{{ business_name }} — elige el día y horario que te acomode</div>
  </div>
  <div class="card-body" id="form-wrap">
    <form id="booking-form">
      <div class="form-group">
        <label>Nombre de contacto</label>
        <input type="text" id="contact_person" placeholder="Tu nombre" value="{{ business_name }}">
      </div>
      <div class="form-group">
        <label>Teléfono</label>
        <input type="tel" id="phone" placeholder="+56 9 XXXX XXXX" value="{{ phone }}">
      </div>
      <div class="form-group">
        <label>Fecha preferida</label>
        <input type="date" id="fecha" min="{{ min_date }}">
      </div>
      <div class="form-group">
        <label>Horario preferido</label>
        <div class="time-grid" id="time-grid">
          <div class="time-btn" onclick="selTime(this,'09:00')">09:00</div>
          <div class="time-btn" onclick="selTime(this,'10:00')">10:00</div>
          <div class="time-btn" onclick="selTime(this,'11:00')">11:00</div>
          <div class="time-btn" onclick="selTime(this,'12:00')">12:00</div>
          <div class="time-btn" onclick="selTime(this,'14:00')">14:00</div>
          <div class="time-btn" onclick="selTime(this,'15:00')">15:00</div>
          <div class="time-btn" onclick="selTime(this,'16:00')">16:00</div>
          <div class="time-btn" onclick="selTime(this,'17:00')">17:00</div>
          <div class="time-btn" onclick="selTime(this,'18:00')">18:00</div>
        </div>
        <input type="hidden" id="hora" value="">
      </div>
      <button type="submit" class="btn-submit">&#8594; Confirmar fecha</button>
    </form>
  </div>
  <div class="success hidden" id="success-wrap">
    <div class="emoji">🎉</div>
    <h2>¡Perfecto, quedamos!</h2>
    <p id="success-msg"></p>
  </div>
</div>

<script>
var selHora = '';
function selTime(el, h) {
  document.querySelectorAll('.time-btn').forEach(function(b){b.classList.remove('sel')});
  el.classList.add('sel');
  selHora = h;
  document.getElementById('hora').value = h;
}

document.getElementById('booking-form').addEventListener('submit', function(e) {
  e.preventDefault();
  var fecha = document.getElementById('fecha').value;
  var hora  = document.getElementById('hora').value;
  var name  = document.getElementById('contact_person').value;
  var phone = document.getElementById('phone').value;
  if (!fecha) { alert('Por favor elige una fecha.'); return; }
  if (!hora)  { alert('Por favor elige un horario.'); return; }

  fetch('', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({fecha:fecha, hora:hora, contact_person:name, phone:phone})
  })
  .then(function(r){ return r.json(); })
  .then(function(data) {
    if (data.ok) {
      document.getElementById('form-wrap').classList.add('hidden');
      document.getElementById('success-wrap').classList.remove('hidden');
      document.getElementById('success-msg').textContent =
        'Te llamaremos el ' + fecha + ' a las ' + hora + ' hrs. ¡Hasta pronto!';
    } else {
      alert('Error: ' + (data.error || 'intenta de nuevo'));
    }
  })
  .catch(function(){ alert('Error de conexión, intenta de nuevo.'); });
});
</script>
</body>
</html>"""


@email_bp.route('/booking-demo', methods=['GET'])
def booking_demo():
    """Página de agenda para emails de test — sin token real."""
    from flask import make_response
    html = _BOOKING_PAGE.replace('{{CONTACT_NAME}}', 'Cliente').replace('{{RUBRO}}', '')
    return make_response(html, 200)


@email_bp.route('/booking/<token>', methods=['GET'])
def booking_page(token):
    conn = get_db()
    row = conn.execute(
        'SELECT id, business_name, phone, rubro, opt_out FROM et_contacts WHERE opt_out_token=?',
        (token,)
    ).fetchone()
    if not row or row['opt_out']:
        return '<h2 style="font-family:sans-serif;padding:40px;">Link inválido o expirado.</h2>', 404

    from datetime import date, timedelta as td
    min_date = (date.today() + td(days=1)).isoformat()
    html = (_BOOKING_PAGE
            .replace('{{ business_name }}', row['business_name'] or '')
            .replace('{{ phone }}',         row['phone'] or '')
            .replace('{{ min_date }}',       min_date))
    return html, 200


@email_bp.route('/booking/<token>', methods=['POST'])
def booking_submit(token):
    import os, smtplib, ssl
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email import encoders

    conn = get_db()
    row = conn.execute(
        'SELECT id, business_name, email, phone, rubro, opt_out FROM et_contacts WHERE opt_out_token=?',
        (token,)
    ).fetchone()
    if not row or row['opt_out']:
        return jsonify({'ok': False, 'error': 'Link inválido'}), 404

    data   = request.get_json() or {}
    fecha  = data.get('fecha', '').strip()        # YYYY-MM-DD
    hora   = data.get('hora',  '').strip()        # HH:MM
    person = data.get('contact_person', row['business_name'] or '').strip()
    phone  = data.get('phone', row['phone'] or '').strip()

    if not fecha or not hora:
        return jsonify({'ok': False, 'error': 'fecha y hora requeridos'}), 400

    # Parse datetime
    try:
        dt_start = datetime.strptime(f'{fecha} {hora}', '%Y-%m-%d %H:%M')
        dt_end   = dt_start + timedelta(minutes=30)
    except ValueError:
        return jsonify({'ok': False, 'error': 'Fecha/hora inválida'}), 400

    contact_id = row['id']

    # Save to et_reuniones
    conn.execute(
        '''INSERT INTO et_reuniones (contact_id, fecha, hora, lugar, notas, estado)
           VALUES (?,?,?,?,?,?)''',
        (contact_id, fecha, hora, 'A coordinar',
         f'Contacto: {person} | Teléfono: {phone} | Rubro: {row["rubro"]}',
         'pendiente')
    )
    conn.execute(
        "UPDATE et_contacts SET estado_interes='en_negociacion', reunion_fecha=? WHERE id=?",
        (fecha, contact_id)
    )
    conn.commit()

    # Send ICS calendar invite
    exec_email = os.getenv('EMAIL_FROM', 'juansebastian.pinto@mercadolibre.cl')
    smtp_user  = os.getenv('SMTP_USER', '')
    smtp_pass  = os.getenv('SMTP_PASS', '')
    smtp_host  = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port  = int(os.getenv('SMTP_PORT', '587'))
    from_name  = os.getenv('EMAIL_FROM_NAME', 'Juan Sebastián Pinto')

    if smtp_user and smtp_pass:
        try:
            ics_content = _generate_ics(
                summary=f'Llamada Mercado Pago — {person} ({row["rubro"]})',
                dt_start=dt_start, dt_end=dt_end,
                organizer_email=exec_email,
                attendee_email=row['email'] or exec_email,
                description=f'Solicitud de llamada de {person}\nTeléfono: {phone}\nNegocio: {row["business_name"]}\nRubro: {row["rubro"]}'
            )
            msg = MIMEMultipart('mixed')
            msg['Subject'] = f'📅 Reunión agendada: {person} — {fecha} {hora}'
            msg['From']    = f'{from_name} <{exec_email}>'
            msg['To']      = exec_email
            msg.attach(MIMEText(
                f'Reunión solicitada por:\n\nNegocio: {row["business_name"]}\n'
                f'Contacto: {person}\nTeléfono: {phone}\nRubro: {row["rubro"]}\n'
                f'Fecha: {fecha} {hora} hrs\n\nRevisalo en el dashboard de prospección.',
                'plain', 'utf-8'
            ))
            ics_part = MIMEBase('text', 'calendar', method='REQUEST', charset='utf-8')
            ics_part.set_payload(ics_content.encode('utf-8'))
            encoders.encode_base64(ics_part)
            ics_part.add_header('Content-Disposition', 'attachment', filename='reunion.ics')
            msg.attach(ics_part)

            ctx = ssl.create_default_context()
            with smtplib.SMTP(smtp_host, smtp_port) as s:
                s.ehlo(); s.starttls(context=ctx); s.login(smtp_user, smtp_pass)
                s.sendmail(exec_email, exec_email, msg.as_string())
            logger.info(f'[Booking] ICS enviado a {exec_email} para {person} — {fecha} {hora}')
        except Exception as e:
            logger.warning(f'[Booking] Error enviando ICS: {e}')

    return jsonify({'ok': True, 'fecha': fecha, 'hora': hora})


# ── Config / rubros list ──────────────────────────────────────────────────────

@email_bp.route('/rubros', methods=['GET'])
def get_rubros():
    # Merge static list with any rubros added dynamically to the DB
    try:
        conn = get_db()
        db_rubros = [r[0].lower().strip() for r in conn.execute('SELECT rubro FROM et_rubro_templates').fetchall() if r[0]]
        conn.close()
        merged = list(RUBROS)
        for r in db_rubros:
            if r not in merged:
                merged.append(r)
        return jsonify(sorted(merged))
    except Exception:
        return jsonify(RUBROS)


@email_bp.route('/comunas', methods=['GET'])
def get_comunas():
    return jsonify(COMUNAS_SANTIAGO)


# ── Crear nuevo rubro (template) ──────────────────────────────────────────────

@email_bp.route('/templates', methods=['POST'])
def create_template():
    data = request.get_json() or {}
    rubro = (data.get('rubro') or '').strip().lower()
    if not rubro:
        return jsonify({'ok': False, 'error': 'rubro requerido'}), 400

    conn = get_db()
    exists = conn.execute(
        'SELECT id FROM et_rubro_templates WHERE LOWER(TRIM(rubro))=?', (rubro,)
    ).fetchone()
    if exists:
        conn.close()
        return jsonify({'ok': False, 'error': 'Ya existe un template para este rubro'}), 409

    subject = data.get('subject') or f'Cobra de forma más fácil en tu {rubro} — MercadoPago'
    body    = data.get('body') or ''
    now     = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cur = conn.execute(
        'INSERT INTO et_rubro_templates (rubro, subject, body, updated_at) VALUES (?,?,?,?)',
        (rubro, subject, body, now)
    )
    tid = cur.lastrowid
    conn.commit()
    conn.close()

    # Inyectar en memoria para que preview y envío funcionen sin reiniciar
    icon       = data.get('icon', '📧')
    header_bg  = data.get('header_bg', '#1A1A2E')
    pain_bg    = data.get('pain_bg', '#FFF8E1')
    RUBRO_EMAIL_CONTENT[rubro] = {
        'subject':    subject,
        'h1':         data.get('h1', 'Cobra sin complicaciones con MercadoPago'),
        'h2':         data.get('h2', ''),
        'h3':         data.get('h3', ''),
        'preheader':  data.get('preheader', ''),
        'icon_strip': icon,
        'cta_text':   data.get('cta_text', '→ Dame 15 minutos para mostrártelo'),
        'wa_text':    data.get('wa_text', ''),
        'pain':       data.get('pain', ''),
        'body':       body,
        'header_bg':  header_bg,
        'pain_bg':    pain_bg,
        'benefits':   data.get('benefits', _STD_BENEFITS),
    }
    # Agregar al listado de rubros disponibles para scraping
    if rubro not in RUBROS:
        RUBROS.append(rubro)

    return jsonify({'ok': True, 'id': tid, 'rubro': rubro,
                    'icon': icon, 'header_bg': header_bg, 'pain_bg': pain_bg})


# ── Envío batch auto-rubro (desde Leads) ──────────────────────────────────────

# Progreso de envíos en memoria: {job_id: {sent, errors, total, done, last_email}}
_batch_progress: dict = {}


def _do_send_batch_auto_rubro(contact_ids: list, job_id: str):
    """
    Envía email a una lista de contactos agrupando por rubro.
    Auto-detecta el template más cercano para cada rubro.
    Pre-genera GIFs una vez por rubro. Reutiliza una sola conexión SMTP.
    Actualiza _batch_progress[job_id] en cada envío para polling del frontend.
    """
    import os, smtplib, ssl, pathlib

    conn = get_db()
    placeholders = ','.join('?' * len(contact_ids))
    rows = conn.execute(
        f'SELECT * FROM et_contacts WHERE id IN ({placeholders})',
        contact_ids
    ).fetchall()
    contacts = [dict(r) for r in rows]

    tpl_rows = conn.execute('SELECT * FROM et_rubro_templates').fetchall()
    templates = [dict(r) for r in tpl_rows]
    conn.close()

    def _find_tpl(rubro):
        for t in templates:
            if _rubro_match(t.get('rubro', ''), rubro):
                return t
        return None

    # Filtrar opt_out / rebotados y agrupar por template
    groups = {}
    no_tpl = []
    for c in contacts:
        if c.get('opt_out') or c.get('email_bounced'):
            continue
        rubro = (c.get('rubro') or '').strip()
        tpl = _find_tpl(rubro)
        if tpl:
            tid = tpl['id']
            if tid not in groups:
                groups[tid] = (tpl, [])
            groups[tid][1].append(c)
        else:
            no_tpl.append(c)

    total = sum(len(g[1]) for g in groups.values())
    _batch_progress[job_id] = {
        'sent': 0, 'errors': 0, 'total': total,
        'done': False, 'last_email': ''
    }
    _batch_seg_ids: list = []  # IDs de et_seguimientos para asociar al lote

    if no_tpl:
        logger.info(f'[BatchSend] {len(no_tpl)} contactos sin template: '
                    + ', '.join(c.get('rubro', '?') for c in no_tpl[:5]))

    base_url  = os.getenv('APP_BASE_URL', 'http://127.0.0.1:5000')
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_pass = os.getenv('SMTP_PASS', '')
    sig_path  = pathlib.Path(__file__).parent.parent / 'static' / 'email_assets' / 'sig_photo.jpeg'
    sig_bytes = sig_path.read_bytes() if sig_path.exists() else None

    sent = errors = 0
    conn2 = get_db()

    # Si hay EMAIL_LOCAL_URL → cada email va via proxy local, NO abrir SMTP en Railway
    use_local_proxy = bool(os.getenv('EMAIL_LOCAL_URL', '').strip())
    smtp = None
    try:
        if not use_local_proxy:
            ctx  = ssl.create_default_context()
            smtp = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            smtp.ehlo(); smtp.starttls(context=ctx); smtp.login(smtp_user, smtp_pass)
            logger.info('[BatchSend] Conexión SMTP abierta (modo Railway directo)')
        else:
            logger.info('[BatchSend] Modo proxy local (EMAIL_LOCAL_URL set)')

        for tid, (tpl, group_contacts) in groups.items():
            rubro = (tpl.get('rubro') or '').lower().strip()
            c_content = _get_rubro_content(rubro)

            try:
                hdr_gif = _compose_header_gif_desktop(c_content)
            except Exception as e:
                logger.warning(f'[BatchSend] Header GIF falló ({rubro}): {e}')
                hdr_gif = None
            try:
                pos_gif = _compose_pos_gif()
            except Exception as e:
                logger.warning(f'[BatchSend] POS GIF falló: {e}')
                pos_gif = None

            for c in group_contacts:
                try:
                    token           = _ensure_opt_out_token(c['id'])
                    unsubscribe_url = f"{base_url}/api/email-tool/unsubscribe/{token}"
                    booking_url     = f"{base_url}/api/email-tool/booking/{token}"

                    subject = c_content.get('subject') or tpl.get('subject') or 'Cobro fácil — MercadoPago'
                    body    = (tpl.get('body') or '').replace('{nombre}', c.get('business_name') or '')

                    res = _send_smtp(
                        c['email'], subject, body, unsubscribe_url,
                        rubro=rubro, contact_name=c.get('business_name', ''),
                        booking_url=booking_url,
                        _hdr_gif=hdr_gif, _pos_gif=pos_gif, _sig_bytes=sig_bytes,
                        _smtp_conn=smtp,  # None si proxy local, conexion abierta si Railway directo
                    )

                    if res.get('ok'):
                        now      = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        followup = (datetime.now() + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
                        conn2.execute(
                            "UPDATE et_contacts SET campaign_status='enviado', fecha_envio=?, proximo_seguimiento=? WHERE id=?",
                            (now, followup, c['id'])
                        )
                        cur_seg = conn2.execute(
                            "INSERT INTO et_seguimientos (contact_id, tipo, fecha, notas, resultado) VALUES (?,?,?,?,?)",
                            (c['id'], 'email', now, f'Batch send — {subject}', 'enviado')
                        )
                        _batch_seg_ids.append(cur_seg.lastrowid)
                        conn2.commit()
                        sent += 1
                        time.sleep(MANUAL_SEND_THROTTLE_SECS)   # Regla 6: throttle entre envíos
                    else:
                        errors += 1
                        if res.get('bounced'):
                            conn2.execute(
                                "UPDATE et_contacts SET email_bounced=1, campaign_status='rebotado' WHERE id=?",
                                (c['id'],)
                            )
                            conn2.commit()
                        logger.warning(f'[BatchSend] Error {c["email"]}: {res.get("error")}')

                except Exception as e:
                    logger.error(f'[BatchSend] Contacto {c.get("id")}: {e}')
                    errors += 1

                # Actualizar progreso después de cada intento
                _batch_progress[job_id].update({
                    'sent': sent, 'errors': errors,
                    'last_email': c.get('email', '')
                })

        if smtp is not None:
            smtp.quit()

    except Exception as e:
        logger.error(f'[BatchSend] Error SMTP: {e}')
        _batch_progress[job_id]['errors'] = errors + 1
    finally:
        conn2.close()

    _batch_progress[job_id]['done'] = True
    logger.info(f'[BatchSend] Completado: {sent} enviados, {errors} errores')

    # ── Registrar lote en historial ──────────────────────────
    if sent > 0 or errors > 0:
        try:
            rubros_list  = list({(tpl.get('rubro') or 'Sin rubro') for _, (tpl, _) in groups.items()})
            comunas_list = list({(c.get('comuna') or '') for _, (_, grp) in groups.items() for c in grp if c.get('comuna')})
            rubro_str    = rubros_list[0] if len(rubros_list) == 1 else 'Varios rubros'
            comunas_str  = (', '.join(comunas_list[:4]) + ('…' if len(comunas_list) > 4 else '')) if comunas_list else 'Varias comunas'
            conn3 = get_db()
            cur3  = conn3.execute(
                "INSERT INTO et_campaign_batches (job_id, fecha, rubro, comunas, total_sent, total_err) VALUES (?,?,?,?,?,?)",
                (job_id, datetime.now().strftime('%Y-%m-%d %H:%M'), rubro_str, comunas_str, sent, errors)
            )
            batch_id = cur3.lastrowid
            for sid in _batch_seg_ids:
                conn3.execute("UPDATE et_seguimientos SET batch_id=? WHERE id=?", (batch_id, sid))
            conn3.commit()
            conn3.close()
            logger.info(f'[BatchSend] Lote #{batch_id} registrado en historial')
        except Exception as _he:
            logger.warning(f'[BatchSend] Historial error: {_he}')


@email_bp.route('/contacts/send-email-batch', methods=['POST'])
def send_email_batch():
    data = request.get_json() or {}
    contact_ids = data.get('contact_ids', [])
    if not contact_ids:
        return jsonify({'ok': False, 'error': 'No se indicaron contactos'}), 400

    job_id = str(uuid.uuid4())[:12]

    import threading
    t = threading.Thread(
        target=_do_send_batch_auto_rubro,
        args=(list(contact_ids), job_id),
        daemon=True
    )
    t.start()
    return jsonify({
        'ok': True,
        'job_id': job_id,
        'total': len(contact_ids),
        'message': f'Enviando {len(contact_ids)} emails en segundo plano…'
    })


@email_bp.route('/contacts/send-progress/<job_id>', methods=['GET'])
def send_progress(job_id):
    p = _batch_progress.get(job_id)
    if not p:
        return jsonify({'ok': False, 'error': 'Job no encontrado'}), 404
    # Limpiar trabajos completados hace más de 5 min para no acumular en memoria
    if p.get('done'):
        import threading
        def _cleanup():
            import time; time.sleep(300)
            _batch_progress.pop(job_id, None)
        threading.Thread(target=_cleanup, daemon=True).start()
    return jsonify({'ok': True, **p})


# ── Historial de campañas (lotes) ─────────────────────────────────────────────

@email_bp.route('/run-campaign-intel', methods=['POST'])
def run_campaign_intel():
    """
    Campaña inmediata guiada por Inteligencia: scraping + envío en un solo paso.
    Pasos:
      1) Consulta _get_intel_targets(target) para determinar qué rubro/comunas scrape
      2) Para cada par, ejecuta _scrape_rubro_comuna(..., send_emails=True) → scrape + envío inmediato
      3) Registra todo en et_campaign_batches y vincula seguimientos via batch_id
    POST body: { "target": 50 }
    Retorna job_id para polling via GET /api/email-tool/search/status/<job_id>
    """
    data   = request.get_json() or {}
    target = max(1, min(int(data.get('target', 50)), 200))

    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        'status':    'running',
        'progress':  0,
        'message':   'Iniciando campaña inteligente...',
        'sent':      0,
        'errors':    0,
        'scraped':   0,
        'batch_id':  None,
        'detalle':   [],
    }

    def _scrape_one_safe(rubro, comuna, max_items, log):
        """
        Ejecuta _scrape_rubro_comuna con un event loop limpio por intento.
        FIX: _run_async reutiliza el mismo objeto coroutine en sus reintentos,
        pero una coroutine Python solo se puede ejecutar UNA vez.
        Aquí creamos una coroutine FRESCA en cada intento y limpiamos el loop
        correctamente para que el siguiente Chrome abra sin conflictos.
        """
        import asyncio, time
        from jobs.email_automation import _scrape_rubro_comuna

        for attempt in range(3):
            if attempt > 0:
                time.sleep(5 * attempt)   # 5s, 10s entre reintentos
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Coroutine FRESCA en cada intento (no reutilizar)
                coro = _scrape_rubro_comuna(rubro, comuna, max_items, send_emails=True)
                return loop.run_until_complete(coro)
            except Exception as e:
                err = str(e)
                if any(k in err for k in ('Target page', 'TargetClosedError', 'process did exit',
                                           'browser has been closed', 'Connection closed')):
                    log.warning(f'[CampaignIntel] Playwright crash {rubro}/{comuna} (intento {attempt+1}/3): {e}')
                else:
                    raise   # error distinto → propagar
            finally:
                # Cancelar tasks pendientes antes de cerrar el loop
                try:
                    pending = asyncio.all_tasks(loop)
                    for t in pending:
                        t.cancel()
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass
                loop.close()
                asyncio.set_event_loop(None)
            time.sleep(2)   # pausa entre Chrome instances

        return 0   # todos los intentos fallaron

    def _run():
        import logging as _log
        import time
        log = _log.getLogger(__name__)

        from jobs.email_automation import _get_intel_targets
        from database import get_db as _db
        from datetime import datetime

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = _db()
        batch_id = None

        try:
            # ── 1. Whitelist: SOLO los 17 rubros de et_rubro_templates ──────────
            _jobs[job_id]['message'] = 'Cargando whitelist de rubros activos...'
            tmpl_rubros = {
                r[0].lower().strip()
                for r in conn.execute(
                    'SELECT LOWER(TRIM(rubro)) FROM et_rubro_templates'
                ).fetchall()
            }
            logger.info(
                f'[CampaignIntel] Whitelist de {len(tmpl_rubros)} rubros: '
                + ', '.join(sorted(tmpl_rubros))
            )

            # ── 2. Obtener targets y filtrar estrictamente a la whitelist ────
            _jobs[job_id]['message'] = 'Consultando inteligencia de scraping...'
            targets_raw = _get_intel_targets(target)
            targets = [
                (r, c, n) for r, c, n in targets_raw
                if r.lower().strip() in tmpl_rubros
            ]
            skipped = len(targets_raw) - len(targets)
            if skipped:
                logger.warning(
                    f'[CampaignIntel] {skipped} par(es) fuera de whitelist descartados.'
                )
            logger.info(
                f'[CampaignIntel] {len(targets)} pares validados para scraping'
            )
            if not targets:
                _jobs[job_id].update({
                    'status': 'done', 'progress': 100,
                    'message': ('Sin targets disponibles para los rubros con template. '
                                'Verifica que existan plantillas en la ventana de Campañas.')
                })
                conn.close()
                return

            # ── 3. Crear registro en et_campaign_batches ─────────────────────
            rubros_str  = ', '.join(sorted({t[0] for t in targets})[:8])
            comunas_str = ', '.join(sorted({t[1] for t in targets})[:8])
            cur = conn.execute(
                """INSERT INTO et_campaign_batches (job_id, fecha, rubro, comunas, total_sent, total_err)
                   VALUES (?, ?, ?, ?, 0, 0)""",
                (job_id, now, rubros_str, comunas_str)
            )
            conn.commit()
            batch_id = cur.lastrowid
            _jobs[job_id]['batch_id'] = batch_id

            # ── 4. Marca de agua: max seguimiento id antes de empezar ────────
            max_seg = conn.execute(
                'SELECT COALESCE(MAX(id),0) FROM et_seguimientos'
            ).fetchone()[0]
            conn.close()

            total_scraped = 0
            total_err     = 0
            n_targets     = len(targets)

            for i, (rubro, comuna, max_items) in enumerate(targets):
                if total_scraped >= target:
                    break
                pct = int(i / n_targets * 90)
                _jobs[job_id].update({
                    'progress': pct,
                    'message':  f'[{i+1}/{n_targets}] {rubro} / {comuna}...',
                })
                try:
                    # Usar wrapper seguro (coroutine fresca + loop limpio por intento)
                    saved = _scrape_one_safe(rubro, comuna, max_items, log)
                    total_scraped += saved
                    _jobs[job_id]['detalle'].append(
                        {'rubro': rubro, 'comuna': comuna, 'enviados': saved, 'ok': True}
                    )
                    log.info(f'[CampaignIntel] {rubro}/{comuna}: {saved} enviados')
                except Exception as e:
                    total_err += 1
                    _jobs[job_id]['detalle'].append(
                        {'rubro': rubro, 'comuna': comuna, 'enviados': 0, 'ok': False, 'error': str(e)}
                    )
                    log.error(f'[CampaignIntel] Error {rubro}/{comuna}: {e}')

                time.sleep(2)   # pausa entre pairs para que Chrome libere recursos

            # ── 4. Contar seguimientos nuevos y asignar batch_id ─────────────
            conn2 = _db()
            new_rows = conn2.execute(
                'SELECT id FROM et_seguimientos WHERE id > ?', (max_seg,)
            ).fetchall()
            total_sent = len(new_rows)

            if new_rows:
                ids_str = ','.join(str(r[0]) for r in new_rows)
                conn2.execute(
                    f'UPDATE et_seguimientos SET batch_id=? WHERE id IN ({ids_str})',
                    (batch_id,)
                )

            # ── 5. Actualizar batch con totales reales ───────────────────────
            conn2.execute(
                'UPDATE et_campaign_batches SET total_sent=?, total_err=? WHERE id=?',
                (total_sent, total_err, batch_id)
            )
            conn2.commit()
            conn2.close()

            _jobs[job_id].update({
                'status':   'done',
                'progress': 100,
                'sent':     total_sent,
                'errors':   total_err,
                'scraped':  total_scraped,
                'message':  (f'Campaña completada: {total_sent} emails enviados '
                             f'en {total_scraped} contactos scrapeados.'),
            })
            log.info(f'[CampaignIntel] Lote {batch_id} → {total_sent} enviados, {total_err} errores')

        except Exception as e:
            log.error(f'[CampaignIntel] Error fatal: {e}', exc_info=True)
            if batch_id:
                try:
                    c = _db()
                    c.execute('UPDATE et_campaign_batches SET total_err=total_err+1 WHERE id=?', (batch_id,))
                    c.commit(); c.close()
                except Exception:
                    pass
            try: conn.close()
            except Exception: pass
            _jobs[job_id].update({
                'status':  'error',
                'message': f'Error: {str(e)}',
            })

    import threading
    threading.Thread(target=_run, daemon=True, name=f'campaign_intel_{job_id}').start()
    return jsonify({'ok': True, 'job_id': job_id})


@email_bp.route('/campaign-batches', methods=['GET'])
def get_campaign_batches():
    """Retorna el historial de lotes de envío."""
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM et_campaign_batches ORDER BY created_at DESC LIMIT 100'
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@email_bp.route('/scheduler-pending', methods=['GET'])
def scheduler_pending():
    """
    Retorna datos para el panel Scheduler:
      - interesados: contactos con campaign_status='interesado' agrupados por rubro
      - seguimientos: contactos con seguimiento pendiente (<= próximas 48h), agrupados
                      por rubro y tipo (48h / 96h)
    """
    conn = get_db()
    now  = datetime.now()
    window = (now + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')

    # ── Interesados ──────────────────────────────────────────────────────────
    int_rows = conn.execute(
        """SELECT rubro, COUNT(*) as cnt
           FROM et_contacts
           WHERE campaign_status = 'interesado'
           GROUP BY rubro
           ORDER BY cnt DESC"""
    ).fetchall()

    # ── Seguimientos pendientes (≤ 48 h desde ahora) ─────────────────────────
    seg_rows = conn.execute(
        """SELECT rubro, campaign_status, COUNT(*) as cnt
           FROM et_contacts
           WHERE proximo_seguimiento IS NOT NULL
             AND proximo_seguimiento <= ?
             AND campaign_status NOT IN ('opt_out','rebotado','cerrado','no_interesado','interesado')
           GROUP BY rubro, campaign_status
           ORDER BY rubro ASC""",
        (window,)
    ).fetchall()

    # ── Totales globales ──────────────────────────────────────────────────────
    total_int  = conn.execute(
        "SELECT COUNT(*) FROM et_contacts WHERE campaign_status='interesado'"
    ).fetchone()[0]
    total_seg48 = conn.execute(
        "SELECT COUNT(*) FROM et_contacts WHERE campaign_status='seguimiento_48h'"
    ).fetchone()[0]
    total_seg96 = conn.execute(
        "SELECT COUNT(*) FROM et_contacts WHERE campaign_status='no_responde'"
    ).fetchone()[0]

    conn.close()

    # Normalizar tipo de seguimiento a etiqueta legible
    def _seg_label(status):
        mapping = {
            'seguimiento_48h': '48h', 'no_responde': '96h',
            'enviado': '48h', 'abierto': '48h',
        }
        return mapping.get(status, status)

    return jsonify({
        'interesados': [{'rubro': r['rubro'], 'count': r['cnt']} for r in int_rows],
        'seguimientos': [
            {'rubro': r['rubro'], 'tipo': _seg_label(r['campaign_status']),
             'status': r['campaign_status'], 'count': r['cnt']}
            for r in seg_rows
        ],
        'totales': {
            'interesados': total_int,
            'seguimiento_48h': total_seg48,
            'seguimiento_96h': total_seg96,
        }
    })


@email_bp.route('/scheduler-next-runs', methods=['GET'])
def scheduler_next_runs():
    """
    Retorna todos los datos necesarios para el nuevo panel Scheduler:
      - next_scraping: próximo run de scraping (08:00 hoy o mañana)
      - next_seguimiento: próximo run de seguimiento (cada 2h)
      - config: prospeccion_activa, scraping_activo, dias_prospeccion
      - rubros_activos: lista de rubros en et_rubro_templates
      - seguimientos_pendientes: por rubro (48h + 96h)
      - historial: últimos batches con bandera outscraper
    """
    from jobs.email_automation import _get_intel_targets
    from database import get_config

    conn = get_db()
    now  = datetime.now()

    # ── Próximo scraping (08:00 AM) ──────────────────────────────────────────
    today_scraping = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now >= today_scraping:
        next_scraping_dt = today_scraping + timedelta(days=1)
    else:
        next_scraping_dt = today_scraping

    # Verificar si ya corrió hoy
    scraping_today = conn.execute(
        "SELECT status, started_at FROM job_runs WHERE job_id='auto_scraping' AND DATE(started_at)=? ORDER BY started_at DESC LIMIT 1",
        (now.strftime('%Y-%m-%d'),)
    ).fetchone()
    scraping_ran_today = bool(scraping_today and scraping_today['status'] in ('ok', 'running'))

    # Targets de inteligencia (top 5 para mostrar)
    try:
        intel_targets = _get_intel_targets(100)[:5]
        targets_preview = [{'rubro': t[0], 'comuna': t[1], 'max': t[2]} for t in intel_targets]
    except Exception:
        targets_preview = []

    # ── Próximo seguimiento (cada 2h) ────────────────────────────────────────
    # Ventana: próximo múltiplo de 2h
    current_hour   = now.hour
    next_2h_hour   = ((current_hour // 2) + 1) * 2
    if next_2h_hour >= 24:
        next_seg_dt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        next_seg_dt = now.replace(hour=next_2h_hour, minute=0, second=0, microsecond=0)

    # Pendientes de seguimiento por rubro y tipo
    seg48_rows = conn.execute(
        """SELECT COALESCE(TRIM(rubro), 'Sin rubro') as rubro, COUNT(*) as cnt
           FROM et_contacts
           WHERE campaign_status = 'seguimiento_48h'
           GROUP BY LOWER(TRIM(rubro))
           ORDER BY cnt DESC"""
    ).fetchall()

    seg96_rows = conn.execute(
        """SELECT COALESCE(TRIM(rubro), 'Sin rubro') as rubro, COUNT(*) as cnt
           FROM et_contacts
           WHERE campaign_status = 'no_responde'
           GROUP BY LOWER(TRIM(rubro))
           ORDER BY cnt DESC"""
    ).fetchall()

    total_48 = sum(r['cnt'] for r in seg48_rows)
    total_96 = sum(r['cnt'] for r in seg96_rows)

    # Determinar etapa próximo envío
    if total_48 > 0 and total_96 > 0:
        next_seg_stage = '48h + 96h'
    elif total_48 > 0:
        next_seg_stage = '48h'
    elif total_96 > 0:
        next_seg_stage = '96h'
    else:
        next_seg_stage = None

    # ── Config ───────────────────────────────────────────────────────────────
    prospeccion_activa = get_config('prospeccion_activa') or '1'
    scraping_activo    = get_config('scraping_activo')    or '1'
    dias_prospeccion   = get_config('dias_prospeccion')   or 'lun,mar,mie,jue,vie,sab,dom'

    # ── Rubros activos ───────────────────────────────────────────────────────
    rubros_rows = conn.execute(
        "SELECT DISTINCT LOWER(TRIM(rubro)) as rubro FROM et_rubro_templates ORDER BY rubro"
    ).fetchall()
    rubros_activos = [r['rubro'] for r in rubros_rows if r['rubro']]

    # ── Seguimientos pendientes agrupados por rubro ──────────────────────────
    seg_merge = {}
    for r in seg48_rows:
        k = r['rubro']
        seg_merge.setdefault(k, {'rubro': k, 'count_48': 0, 'count_96': 0})
        seg_merge[k]['count_48'] = r['cnt']
    for r in seg96_rows:
        k = r['rubro']
        seg_merge.setdefault(k, {'rubro': k, 'count_48': 0, 'count_96': 0})
        seg_merge[k]['count_96'] = r['cnt']

    seguimientos_pendientes = [
        {
            'rubro': v['rubro'],
            'total': v['count_48'] + v['count_96'],
            'count_48': v['count_48'],
            'count_96': v['count_96'],
        }
        for v in sorted(seg_merge.values(), key=lambda x: -(x['count_48'] + x['count_96']))
    ]

    # ── Historial de campañas (con flag outscraper via et_seguimientos) ─────
    batches = conn.execute(
        """SELECT b.id, b.fecha, b.rubro, b.comunas, b.total_sent, b.total_err,
                  COUNT(DISTINCT CASE WHEN c.source_query LIKE 'outscraper:%' THEN c.id END) as outscraper_count
           FROM et_campaign_batches b
           LEFT JOIN et_seguimientos s ON s.batch_id = b.id
           LEFT JOIN et_contacts c ON c.id = s.contact_id
           GROUP BY b.id
           ORDER BY b.created_at DESC LIMIT 50"""
    ).fetchall()

    conn.close()

    return jsonify({
        'next_scraping': {
            'datetime': next_scraping_dt.strftime('%Y-%m-%d %H:%M'),
            'ran_today': scraping_ran_today,
            'targets': targets_preview,
            'target_emails': 100,
        },
        'next_seguimiento': {
            'datetime': next_seg_dt.strftime('%Y-%m-%d %H:%M'),
            'stage': next_seg_stage,
            'total_48': total_48,
            'total_96': total_96,
        },
        'config': {
            'prospeccion_activa': prospeccion_activa == '1',
            'scraping_activo':    scraping_activo    == '1',
            'dias_prospeccion':   dias_prospeccion,
        },
        'rubros_activos': rubros_activos,
        'seguimientos_pendientes': seguimientos_pendientes,
        'historial': [
            {
                'id':              dict(b)['id'],
                'fecha':           dict(b)['fecha'],
                'rubro':           dict(b)['rubro'],
                'comunas':         dict(b)['comunas'],
                'total_sent':      dict(b)['total_sent'] or 0,
                'total_err':       dict(b)['total_err']  or 0,
                'outscraper_count': dict(b)['outscraper_count'] or 0,
            }
            for b in batches
        ],
    })


@email_bp.route('/scheduler-config', methods=['PATCH'])
def update_scheduler_config():
    """
    Guarda configuración del scheduler en la tabla config:
      prospeccion_activa, scraping_activo, dias_prospeccion
    """
    from database import set_config
    data = request.get_json(silent=True) or {}
    saved = []
    if 'prospeccion_activa' in data:
        set_config('prospeccion_activa', '1' if data['prospeccion_activa'] else '0')
        saved.append('prospeccion_activa')
    if 'scraping_activo' in data:
        set_config('scraping_activo', '1' if data['scraping_activo'] else '0')
        saved.append('scraping_activo')
    if 'dias_prospeccion' in data:
        dias = data['dias_prospeccion']
        if isinstance(dias, list):
            dias = ','.join(dias)
        set_config('dias_prospeccion', str(dias))
        saved.append('dias_prospeccion')
    return jsonify({'ok': True, 'saved': saved})


@email_bp.route('/campaign-batches/<int:bid>/excel', methods=['GET'])
def campaign_batch_excel(bid):
    """Descarga Excel con el detalle de contactos del lote."""
    import io
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        return jsonify({'error': 'openpyxl no disponible'}), 500

    conn = get_db()
    batch = conn.execute(
        'SELECT * FROM et_campaign_batches WHERE id=?', (bid,)
    ).fetchone()
    if not batch:
        conn.close()
        return jsonify({'error': 'Lote no encontrado'}), 404

    rows = conn.execute(
        '''SELECT s.fecha, c.business_name, c.email, c.rubro, c.comuna,
                  s.resultado, c.campaign_status, c.estado_interes
           FROM et_seguimientos s
           JOIN et_contacts c ON s.contact_id = c.id
           WHERE s.batch_id = ?
           ORDER BY s.fecha ASC''',
        (bid,)
    ).fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f'Lote {bid}'

    # Cabecera
    header = ['Fecha/Hora', 'Negocio', 'Email', 'Rubro', 'Comuna',
              'Resultado', 'Estado campaña', 'Estado interés']
    hdr_fill = PatternFill('solid', fgColor='009EE3')
    hdr_font = Font(bold=True, color='FFFFFF')
    ws.append(header)
    for cell in ws[1]:
        cell.fill = hdr_fill
        cell.font = hdr_font
        cell.alignment = Alignment(horizontal='center')

    for row in rows:
        ws.append([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]])

    # Ancho automático
    for col in ws.columns:
        max_len = max((len(str(cell.value or '')) for cell in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    from flask import send_file
    filename = f'lote_{bid}_{(dict(batch).get("fecha","") or "").replace(" ","_").replace(":","-")}.xlsx'
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


# ── Scraping stats & history ──────────────────────────────────────────────────

@email_bp.route('/scraping-stats', methods=['GET'])
def scraping_stats():
    """
    Retorna datos para la sección Scraping:
      - kpis: total_leads, rubros_cubiertos, comunas_cubiertas, ultimo_scraping
      - chart_rubros:  [{ rubro, count }]  — top 14 por cantidad de contactos
      - chart_comunas: [{ comuna, count }] — top 15 por cantidad de contactos
      - historial:     filas de et_campaign_batches con campo 'estado' derivado
    """
    conn = get_db()

    # ── KPIs ────────────────────────────────────────────────────────────────
    total_leads = conn.execute(
        "SELECT COUNT(*) FROM et_contacts"
    ).fetchone()[0]

    rubros_cubiertos = conn.execute(
        "SELECT COUNT(DISTINCT LOWER(TRIM(rubro))) FROM et_contacts WHERE rubro IS NOT NULL AND rubro != ''"
    ).fetchone()[0]

    comunas_cubiertas = conn.execute(
        """SELECT COUNT(DISTINCT LOWER(TRIM(COALESCE(NULLIF(TRIM(comuna),''), ciudad))))
           FROM et_contacts
           WHERE COALESCE(NULLIF(TRIM(comuna),''), ciudad) IS NOT NULL"""
    ).fetchone()[0]

    ultimo_row = conn.execute(
        "SELECT MAX(fecha) FROM et_campaign_batches"
    ).fetchone()[0]
    ultimo_scraping = ultimo_row or '—'

    total_enviados = conn.execute(
        "SELECT COALESCE(SUM(total_sent), 0) FROM et_campaign_batches"
    ).fetchone()[0]

    # ── Chart: rubros ────────────────────────────────────────────────────────
    rubros_rows = conn.execute(
        """SELECT TRIM(rubro) as rubro, COUNT(*) as cnt
           FROM et_contacts
           WHERE rubro IS NOT NULL AND rubro != ''
           GROUP BY LOWER(TRIM(rubro))
           ORDER BY cnt DESC LIMIT 14"""
    ).fetchall()

    # ── Chart: comunas ───────────────────────────────────────────────────────
    comunas_rows = conn.execute(
        """SELECT TRIM(COALESCE(NULLIF(TRIM(comuna),''), ciudad)) as c, COUNT(*) as cnt
           FROM et_contacts
           WHERE COALESCE(NULLIF(TRIM(comuna),''), ciudad) IS NOT NULL
           GROUP BY LOWER(TRIM(COALESCE(NULLIF(TRIM(comuna),''), ciudad)))
           ORDER BY cnt DESC LIMIT 15"""
    ).fetchall()

    # ── Historial: et_campaign_batches (últimos 60) ──────────────────────────
    batch_rows = conn.execute(
        """SELECT id, job_id, fecha, rubro, comunas, total_sent, total_err, created_at
           FROM et_campaign_batches
           ORDER BY created_at DESC LIMIT 60"""
    ).fetchall()

    conn.close()

    def _batch_estado(total_sent, total_err):
        if total_sent and total_sent > 0:
            if total_err and total_err > 0:
                return 'parcial'
            return 'exitoso'
        if total_err and total_err > 0:
            return 'error'
        return 'sin_envio'

    historial = []
    for r in batch_rows:
        b = dict(r)
        b['estado'] = _batch_estado(b.get('total_sent'), b.get('total_err'))
        historial.append(b)

    return jsonify({
        'kpis': {
            'total_leads':      total_leads,
            'rubros_cubiertos': rubros_cubiertos,
            'comunas_cubiertas': comunas_cubiertas,
            'ultimo_scraping':  ultimo_scraping,
            'total_enviados':   total_enviados,
        },
        'chart_rubros':  [{'rubro': r['rubro'], 'count': r['cnt']} for r in rubros_rows],
        'chart_comunas': [{'comuna': r['c'],    'count': r['cnt']} for r in comunas_rows],
        'historial':     historial,
    })


# ── OUTSCRAPER MONITOR ────────────────────────────────────────────────────────

def _next_month_name() -> str:
    """Retorna el nombre del mes siguiente, ej: 'mayo 2026'."""
    now  = datetime.now()
    if now.month == 12:
        nxt = now.replace(year=now.year+1, month=1, day=1)
    else:
        nxt = now.replace(month=now.month+1, day=1)
    MESES = ['enero','febrero','marzo','abril','mayo','junio',
             'julio','agosto','septiembre','octubre','noviembre','diciembre']
    return f'{MESES[nxt.month-1]} {nxt.year}'


@email_bp.route('/outscraper-status', methods=['GET'])
def outscraper_status():
    """Verifica si la API key de Outscraper está configurada."""
    import os
    key = os.getenv('OUTSCRAPER_API_KEY', '').strip()
    return jsonify({
        'configured': bool(key),
        'key_preview': (key[:8] + '…' + key[-4:]) if len(key) > 12 else ('*' * len(key) if key else ''),
    })


@email_bp.route('/outscraper-budget', methods=['GET'])
def outscraper_budget():
    """Retorna el estado del presupuesto mensual de Outscraper."""
    from jobs.email_automation import _get_outscraper_budget_status
    return jsonify(_get_outscraper_budget_status())


@email_bp.route('/outscraper-budget', methods=['PATCH'])
def update_outscraper_budget():
    """Actualiza el presupuesto mensual (budget_usd y/o credits_per_usd)."""
    from database import set_config
    data = request.get_json(silent=True) or {}
    saved = []
    if 'budget_usd' in data:
        val = float(data['budget_usd'])
        if val <= 0:
            return jsonify({'ok': False, 'error': 'El presupuesto debe ser mayor a 0'}), 400
        set_config('outscraper_monthly_budget_usd', str(val))
        saved.append('budget_usd')
    if 'credits_per_usd' in data:
        val = int(data['credits_per_usd'])
        if val <= 0:
            return jsonify({'ok': False, 'error': 'credits_per_usd debe ser > 0'}), 400
        set_config('outscraper_credits_per_usd', str(val))
        saved.append('credits_per_usd')
    from jobs.email_automation import _get_outscraper_budget_status
    return jsonify({'ok': True, 'saved': saved, 'status': _get_outscraper_budget_status()})


@email_bp.route('/outscraper-query', methods=['POST'])
def outscraper_query():
    """
    Ejecuta una búsqueda real en Outscraper para un rubro+comuna.
    POST body: { rubro, comuna, limit }
    Retorna: { ok, api_connected, query, places, stats }
    """
    import os

    data   = request.json or {}
    rubro  = (data.get('rubro')  or '').strip()
    comuna = (data.get('comuna') or '').strip()
    limit  = min(int(data.get('limit', 10)), 20)

    if not rubro or not comuna:
        return jsonify({'ok': False, 'error': 'Rubro y comuna son requeridos'}), 400

    api_key = os.getenv('OUTSCRAPER_API_KEY', '').strip()
    if not api_key:
        return jsonify({'ok': False, 'api_connected': False,
                        'error': 'OUTSCRAPER_API_KEY no configurada en .env'}), 400

    # ── Verificar presupuesto antes de consultar ──────────────────────────────
    from jobs.email_automation import _get_outscraper_budget_status
    budget = _get_outscraper_budget_status()
    if budget['blocked']:
        return jsonify({
            'ok': False,
            'budget_blocked': True,
            'error': f'Presupuesto mensual agotado — ${budget["usd_used"]:.2f} / ${budget["budget_usd"]:.2f} USD. '
                     f'Se reanudará el 1° de {_next_month_name()}.',
        }), 402

    query = f'{rubro} {comuna} Santiago Chile'
    logger.info(f'[OutscraperMonitor] Query: "{query}" limit={limit}')

    try:
        from outscraper import ApiClient
        client  = ApiClient(api_key=api_key)
        results = client.google_maps_search(
            [query],
            limit=limit,
            enrichment=['domains_service'],
            language='es',
            region='CL',
        )
    except Exception as exc:
        logger.error(f'[OutscraperMonitor] Error API: {exc}')
        return jsonify({'ok': False, 'api_connected': True, 'error': str(exc)}), 500

    places_raw = results[0] if results and isinstance(results[0], list) else (results or [])

    places      = []
    emails_total = 0

    for p in places_raw:
        if not isinstance(p, dict):
            continue

        emails = [p[f'email_{i}'] for i in range(1, 6) if p.get(f'email_{i}')]
        if emails:
            emails_total += 1

        # Determinar si ya existe alguno de sus emails en et_contacts
        already_saved = False
        if emails:
            conn = get_db()
            for em in emails:
                row = conn.execute('SELECT id FROM et_contacts WHERE email = ?', (em.lower(),)).fetchone()
                if row:
                    already_saved = True
                    break
            conn.close()

        places.append({
            'name':         (p.get('name') or '')[:80],
            'emails':       emails,
            'phone':        p.get('phone')   or '',
            'website':      p.get('website') or p.get('site') or '',
            'address':      (p.get('address') or p.get('full_address') or '')[:120],
            'category':     p.get('type')   or p.get('subtypes') or p.get('category') or '',
            'rating':       p.get('rating'),
            'reviews':      p.get('reviews'),
            'has_email':    bool(emails),
            'already_saved': already_saved,
        })

    n      = len(places)
    rate   = round(emails_total / n * 100) if n else 0
    # Estimación créditos: ~3 cr/place (search) + ~2 cr/place con web (enrichment)
    credits_est = n * 3 + emails_total * 2

    # ── Guardar en historial ──────────────────────────────────────────
    import json as _json
    conn_h = get_db()
    cur_h = conn_h.execute(
        """INSERT INTO et_outscraper_queries
           (query, rubro, comuna, limit_req, total_found, with_email, credits_est, source, results_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'manual', ?)""",
        (query, rubro, comuna, limit, n, emails_total, credits_est, _json.dumps(places, ensure_ascii=False))
    )
    query_id = cur_h.lastrowid
    conn_h.commit()
    conn_h.close()

    return jsonify({
        'ok':            True,
        'api_connected': True,
        'query':         query,
        'query_id':      query_id,
        'places':        places,
        'stats': {
            'total':          n,
            'with_email':     emails_total,
            'without_email':  n - emails_total,
            'email_rate':     rate,
            'credits_est':    credits_est,
        }
    })


@email_bp.route('/outscraper-history', methods=['GET'])
def outscraper_history():
    """
    Retorna el historial de búsquedas Outscraper:
    1. Consultas manuales guardadas en et_outscraper_queries
    2. Jobs automáticos reconstruidos desde et_contacts.source_query
    """
    conn = get_db()

    # ── 1. Consultas manuales ──────────────────────────────────────────
    manual_rows = conn.execute(
        """SELECT id, query, rubro, comuna, total_found, with_email,
                  credits_est, source, created_at
           FROM et_outscraper_queries
           ORDER BY created_at DESC LIMIT 100"""
    ).fetchall()

    # ── 2. Jobs automáticos desde et_contacts ─────────────────────────
    auto_rows = conn.execute(
        """SELECT source_query,
                  COUNT(*)                                          AS total_found,
                  COUNT(CASE WHEN email IS NOT NULL AND email != '' THEN 1 END) AS with_email,
                  MIN(created_at)                                   AS created_at
           FROM et_contacts
           WHERE source_query LIKE 'outscraper:%'
           GROUP BY source_query
           ORDER BY created_at DESC"""
    ).fetchall()

    conn.close()

    history = []

    for r in manual_rows:
        history.append({
            'id':          r['id'],
            'type':        'manual',
            'source':      r['source'] or 'manual',
            'query':       r['query'],
            'rubro':       r['rubro'] or '',
            'comuna':      r['comuna'] or '',
            'total_found': r['total_found'] or 0,
            'with_email':  r['with_email'] or 0,
            'credits_est': r['credits_est'] or 0,
            'created_at':  (r['created_at'] or '')[:16],
            'excel_url':   f'/api/email-tool/outscraper-history/{r["id"]}/excel',
        })

    for r in auto_rows:
        sq = r['source_query']          # e.g. "outscraper:ferretería Puente Alto Santiago Chile"
        raw_q = sq[len('outscraper:'):] if sq.startswith('outscraper:') else sq
        parts = raw_q.split(' ')
        history.append({
            'id':          None,
            'type':        'auto',
            'source':      'auto_job',
            'query':       raw_q,
            'rubro':       parts[0] if parts else '',
            'comuna':      parts[1] if len(parts) > 1 else '',
            'total_found': r['total_found'] or 0,
            'with_email':  r['with_email'] or 0,
            'credits_est': (r['total_found'] or 0) * 5,
            'created_at':  (r['created_at'] or '')[:16],
            'excel_url':   f'/api/email-tool/outscraper-history/auto/excel?q={sq}',
        })

    # Ordenar combinado por fecha desc
    history.sort(key=lambda x: x['created_at'], reverse=True)

    return jsonify(history)


@email_bp.route('/outscraper-history/<query_id>/excel', methods=['GET'])
def outscraper_history_excel(query_id):
    """
    Descarga Excel con el detalle de una consulta Outscraper.
    query_id = int  → consulta manual de et_outscraper_queries
    query_id = 'auto' → reconstruye desde et_contacts por source_query
    """
    import json as _json
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        return jsonify({'error': 'openpyxl no disponible'}), 500

    wb = openpyxl.Workbook()
    ws = wb.active

    header_fill = PatternFill('solid', fgColor='009EE3')
    header_font = Font(bold=True, color='FFFFFF')

    if query_id == 'auto':
        # Reconstruir desde et_contacts
        sq = request.args.get('q', '')
        conn = get_db()
        rows = conn.execute(
            """SELECT business_name, email, phone, website, rubro, comuna, source_query, created_at
               FROM et_contacts WHERE source_query = ? ORDER BY created_at DESC""",
            (sq,)
        ).fetchall()
        conn.close()

        ws.title = 'Job automático'
        headers = ['Negocio', 'Email', 'Teléfono', 'Web', 'Rubro', 'Comuna', 'Query', 'Fecha']
        ws.append(headers)
        for cell in ws[1]:
            cell.fill = header_fill; cell.font = header_font

        for r in rows:
            ws.append([
                r['business_name'] or '', r['email'] or '',
                r['phone'] or '',        r['website'] or '',
                r['rubro'] or '',        r['comuna'] or '',
                r['source_query'] or '', (r['created_at'] or '')[:16],
            ])

        filename = 'outscraper_auto_' + sq[11:30].replace(' ', '_').replace(':', '-') + '.xlsx'

    else:
        # Consulta manual
        conn = get_db()
        row = conn.execute(
            'SELECT * FROM et_outscraper_queries WHERE id = ?', (int(query_id),)
        ).fetchone()
        conn.close()

        if not row:
            return jsonify({'error': 'Consulta no encontrada'}), 404

        places = _json.loads(row['results_json'] or '[]')
        ws.title = f'Consulta {query_id}'
        headers = ['Negocio', 'Emails', 'Teléfono', 'Sitio web', 'Dirección', 'Categoría',
                   'Rating', 'Reviews', 'Estado']
        ws.append(headers)
        for cell in ws[1]:
            cell.fill = header_fill; cell.font = header_font

        for p in places:
            estado = 'Ya guardado' if p.get('already_saved') else ('Con email' if p.get('has_email') else 'Sin email')
            ws.append([
                p.get('name', '')    or '',
                ', '.join(p.get('emails', [])),
                p.get('phone', '')   or '',
                p.get('website', '') or '',
                p.get('address', '') or '',
                str(p.get('category', '') or ''),
                p.get('rating')      or '',
                p.get('reviews')     or '',
                estado,
            ])

        fecha_safe = (dict(row).get('created_at') or '')[:16].replace(' ', '_').replace(':', '-')
        filename = f'outscraper_{(row["rubro"] or "query").replace(" ", "_")}_{fecha_safe}.xlsx'

    # Ajustar anchos
    for col in ws.columns:
        max_len = max((len(str(cell.value or '')) for cell in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    from flask import send_file
    return send_file(buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@email_bp.route('/outscraper-history/<int:query_id>/import-leads', methods=['POST'])
def outscraper_import_leads(query_id):
    """
    Importa los resultados de una consulta manual de Outscraper a et_contacts.
    Lee results_json de et_outscraper_queries, filtra emails válidos,
    desduplicca contra et_contacts y guarda como 'no_enviado'.
    """
    import json as _json

    conn = get_db()
    row = conn.execute(
        'SELECT * FROM et_outscraper_queries WHERE id = ?', (query_id,)
    ).fetchone()

    if not row:
        conn.close()
        return jsonify({'ok': False, 'error': 'Consulta no encontrada'}), 404

    places  = _json.loads(row['results_json'] or '[]')
    rubro   = row['rubro']   or ''
    comuna  = row['comuna']  or ''
    source  = f'outscraper:{row["query"]}'
    now     = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    imported = 0
    skipped  = 0
    errors   = 0

    for p in places:
        emails = p.get('emails') or []
        if not emails:
            skipped += 1
            continue

        name    = (p.get('name')    or '')[:80]
        phone   = (p.get('phone')   or '')[:30]
        website = (p.get('website') or '')[:255]

        for email in emails[:2]:   # máx 2 por negocio (igual que el job automático)
            email = email.lower().strip()
            if not email:
                continue

            existing = conn.execute(
                'SELECT id FROM et_contacts WHERE email = ?', (email,)
            ).fetchone()
            if existing:
                skipped += 1
                continue

            try:
                conn.execute(
                    '''INSERT INTO et_contacts
                       (business_name, email, phone, website, rubro, ciudad, comuna,
                        source_query, created_at, campaign_status)
                       VALUES (?,?,?,?,?,?,?,?,?,?)''',
                    (name, email, phone, website, rubro,
                     'Santiago', comuna, source, now, 'no_enviado')
                )
                conn.commit()
                imported += 1
            except Exception as e:
                logger.error(f'[ImportLeads] Error insertando {email}: {e}')
                errors += 1

    # Marcar la consulta como importada en et_outscraper_queries
    conn.execute(
        "UPDATE et_outscraper_queries SET source = 'manual_imported' WHERE id = ?",
        (query_id,)
    )
    conn.commit()
    conn.close()

    logger.info(f'[ImportLeads] query_id={query_id}: {imported} importados, {skipped} saltados, {errors} errores')
    return jsonify({
        'ok':       True,
        'imported': imported,
        'skipped':  skipped,
        'errors':   errors,
    })


# ── Test batch manual ─────────────────────────────────────────────────────────

@email_bp.route('/smtp-check', methods=['GET'])
def smtp_check():
    """Verifica si las variables SMTP están configuradas (sin exponer valores)."""
    import os, smtplib, ssl
    host  = os.getenv('SMTP_HOST', '')
    port  = os.getenv('SMTP_PORT', '')
    user  = os.getenv('SMTP_USER', '')
    pwd   = os.getenv('SMTP_PASS', '')
    frm   = os.getenv('EMAIL_FROM', '')
    configured = bool(user and pwd)
    sg_key = os.getenv('SENDGRID_API_KEY', '')
    result = {
        'SMTP_HOST':         bool(host),
        'SMTP_PORT':         bool(port),
        'SMTP_USER':         bool(user),
        'SMTP_PASS':         bool(pwd),
        'EMAIL_FROM':        bool(frm),
        'SENDGRID_API_KEY':  bool(sg_key),
        'canal':             'sendgrid' if sg_key else ('smtp' if configured else 'ninguno'),
        'configured':        configured or bool(sg_key),
    }
    if sg_key:
        try:
            import requests as _req
            resp = _req.post(
                'https://api.sendgrid.com/v3/mail/send',
                headers={'Authorization': f'Bearer {sg_key}', 'Content-Type': 'application/json'},
                json={'personalizations': [{'to': [{'email': 'test@test.com'}]}],
                      'from': {'email': frm or 'test@test.com'}, 'subject': 'test',
                      'content': [{'type': 'text/plain', 'value': 'test'}]},
                timeout=10
            )
            result['sendgrid_login'] = 'OK' if resp.status_code in (200, 202) else f'HTTP {resp.status_code}: {resp.text[:100]}'
        except Exception as e:
            result['sendgrid_login'] = str(e)
        return jsonify(result)
    if configured:
        try:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(host or 'smtp.gmail.com', int(port or 587), timeout=10) as s:
                s.ehlo(); s.starttls(context=ctx); s.login(user, pwd)
            result['smtp_login'] = 'OK'
        except Exception as e:
            result['smtp_login'] = str(e)
    else:
        result['smtp_login'] = 'Skipped — credenciales vacías'
    return jsonify(result)


@email_bp.route('/run-batch', methods=['POST'])
def run_batch_manual():
    """
    Disparo manual de un lote de emails del pool no_enviado.
    Body JSON: { "size": 30 }  (default 30, máx 100)
    """
    import threading
    from jobs.email_automation import run_email_batch

    data = request.get_json() or {}
    size = min(int(data.get('size', 30)), 100)

    def _run():
        run_email_batch(size, f'Manual-{size}')

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({
        'ok':      True,
        'message': f'Lote de {size} emails iniciado en background. Revisa logs para resultado.',
        'size':    size,
    })
