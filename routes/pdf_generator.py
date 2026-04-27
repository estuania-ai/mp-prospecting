"""
Generador de PDFs por rubro - Branding MercadoPago
Paleta: #009EE3 (azul MP), #1A1A2E (navy), #00A650 (verde), #FFFFFF
"""
import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Paleta MercadoPago ───────────────────────────────────────────────────────
MP_BLUE       = colors.HexColor('#009EE3')
MP_NAVY       = colors.HexColor('#1A1A2E')
MP_DARK_BLUE  = colors.HexColor('#2D3277')
MP_GREEN      = colors.HexColor('#00A650')
MP_LIGHT_BLUE = colors.HexColor('#E8F7FD')
MP_GRAY       = colors.HexColor('#F5F7FF')
MP_TEXT       = colors.HexColor('#333333')
MP_LIGHT_GRAY = colors.HexColor('#E5E7EB')
WHITE         = colors.white

W, H = A4  # 210 x 297 mm

# ── Contenido por rubro ──────────────────────────────────────────────────────
RUBRO_CONTENT = {
    'cafetería': {
        'emoji': '☕',
        'tagline': 'Moderniza los cobros de tu cafetería',
        'beneficios_titulo': 'Beneficios para tu Cafetería',
        'beneficios': [
            ('Vales de alimentación', 'Acepta Edenred, Pluxee y Junaeb directamente en el equipo — sin pasos adicionales.'),
            ('Integración con software de caja', 'Compatible con Toteat, Resto y otras plataformas de gestión de pedidos.'),
            ('Cuenta colaboradores', 'Cada trabajador tiene su propio perfil para gestionar cobros de forma independiente.'),
            ('Cobro con QR', 'Tus clientes pueden pagar desde su celular sin tarjeta.'),
            ('Liquidación el mismo día', 'El dinero de tus ventas disponible en tu cuenta sin demoras.'),
        ],
        'propuesta': 'El Smart Point de MercadoPago es la solución ideal para cafeterías que quieren ofrecer una experiencia de pago moderna. Con soporte para vales de alimentación y sin costo de arriendo mensual, maximizas tus ventas sin aumentar tus costos.',
        'cta': 'Conversa con nosotros esta semana y te hacemos una demostración sin compromiso.',
    },
    'pastelería': {
        'emoji': '🥐',
        'tagline': 'La solución de cobro ideal para tu pastelería',
        'beneficios_titulo': 'Beneficios para tu Pastelería',
        'beneficios': [
            ('Vales de alimentación', 'Acepta Edenred, Pluxee y Junaeb — aumenta tus opciones de venta.'),
            ('Sin mensualidad fija', 'Solo pagas por lo que vendes, sin costos fijos.'),
            ('Integración con Toteat o Resto', 'Gestiona pedidos y cobros desde una sola plataforma.'),
            ('Cuenta colaboradores', 'Perfil individual para cada empleado con registro de sus ventas.'),
            ('Reportes en tiempo real', 'Monitorea tus ventas desde el celular en cualquier momento.'),
        ],
        'propuesta': 'Aprovecha al máximo cada venta en tu pastelería. Con el Smart Point aceptas todos los medios de pago, incluyendo vales de alimentación, sin necesidad de múltiples terminales.',
        'cta': '¿Hablamos esta semana? Te mostramos cómo funciona en 15 minutos.',
    },
    'sushi': {
        'emoji': '🍣',
        'tagline': 'Optimiza los cobros de tu restaurante de sushi',
        'beneficios_titulo': 'Beneficios para tu Restaurante',
        'beneficios': [
            ('Vales de alimentación', 'Edenred, Pluxee y Junaeb integrados directamente.'),
            ('Delivery integrado', 'Compatible con plataformas de delivery como Toteat y Resto.'),
            ('QR para mesas', 'Tus clientes pagan desde su teléfono sin esperar al garzón.'),
            ('Cuenta colaboradores', 'Cada mozo con su perfil y registro de ventas.'),
            ('Cierre de caja simplificado', 'Todo queda registrado automáticamente.'),
        ],
        'propuesta': 'En un restaurante de sushi, la experiencia del cliente es clave. El Smart Point de MercadoPago agiliza el cobro, acepta vales de alimentación y se integra con tus plataformas de delivery.',
        'cta': 'Contáctanos y programa una visita sin costo para tu local.',
    },
    'emporio': {
        'emoji': '🏪',
        'tagline': 'Moderniza los cobros de tu emporio',
        'beneficios_titulo': 'Beneficios para tu Emporio',
        'beneficios': [
            ('Vales de alimentación', 'Recibe Edenred, Pluxee y Junaeb — amplía tu base de clientes.'),
            ('Sin costo de arriendo', 'Equipo sin mensualidad fija.'),
            ('Cobro con QR y tarjeta', 'Acepta todos los medios de pago en un solo equipo.'),
            ('Cuenta colaboradores', 'Control de acceso y registro por empleado.'),
            ('Liquidación rápida', 'Dinero en tu cuenta al siguiente día hábil.'),
        ],
        'propuesta': 'No pierdas clientes por no aceptar su medio de pago preferido. El Smart Point de MercadoPago acepta tarjetas, QR y vales de alimentación en un solo equipo, sin costo mensual.',
        'cta': 'Agenda una reunión esta semana — sin compromiso.',
    },
    'clínica dental': {
        'emoji': '🦷',
        'tagline': 'Aumenta tus cierres con cuotas sin interés',
        'beneficios_titulo': 'Beneficios para tu Clínica Dental',
        'beneficios': [
            ('Cuotas sin interés', 'Ofrece financiamiento a tus pacientes — tú recibes el total de inmediato.'),
            ('Todos los medios de pago', 'Visa, Mastercard, débito, prepago y QR.'),
            ('Cuenta colaboradores', 'Perfil individual para dentistas y recepcionistas.'),
            ('Liquidación inmediata', 'Sin esperas, el dinero disponible el mismo día.'),
            ('Sin mensualidad', 'Solo pagas por las transacciones que procesas.'),
        ],
        'propuesta': 'Los tratamientos de ortodoncia, implantes y otros procedimientos de alto valor tienen mayor cierre cuando el paciente puede pagar en cuotas. Con MercadoPago, ofreces cuotas sin interés mientras recibes el pago completo de inmediato.',
        'cta': 'Conversemos esta semana. Te explicamos cómo aumentar tu tasa de cierre.',
    },
    'pizzería': {
        'emoji': '🍕',
        'tagline': 'Acepta todos los medios de pago en tu pizzería',
        'beneficios_titulo': 'Beneficios para tu Pizzería',
        'beneficios': [
            ('Vales de alimentación', 'Acepta Edenred, Pluxee y Junaeb sin complicaciones.'),
            ('Delivery y local', 'Equipo portátil para cobrar en terreno o en mostrador.'),
            ('Integración con Toteat/Resto', 'Gestiona pedidos y cobros desde una sola plataforma.'),
            ('Cuenta colaboradores', 'Control por empleado con perfil individual.'),
            ('Sin mensualidad fija', 'Pagas solo por lo que vendes.'),
        ],
        'propuesta': 'Una pizzería no puede perder pedidos por falta de medios de pago. El Smart Point de MercadoPago acepta todo — tarjetas, vales y QR — y se integra con tus plataformas de delivery.',
        'cta': 'Te mostramos cómo funciona en 15 minutos. ¿Cuándo te viene bien?',
    },
    'librería': {
        'emoji': '📚',
        'tagline': 'Moderniza los cobros de tu librería',
        'beneficios_titulo': 'Beneficios para tu Librería',
        'beneficios': [
            ('Todos los medios de pago', 'Tarjetas de crédito, débito, prepago y QR.'),
            ('Sin costo de arriendo', 'Equipo sin mensualidad — solo pagas por ventas.'),
            ('Cobro rápido', 'Procesamiento en segundos para no hacer esperar a tus clientes.'),
            ('Cuenta colaboradores', 'Perfil individual para cada vendedor.'),
            ('Reportes de venta', 'Historial completo accesible desde tu celular.'),
        ],
        'propuesta': 'Facilita la compra a tus clientes aceptando todos los medios de pago. El Smart Point de MercadoPago es simple, rápido y sin mensualidad fija.',
        'cta': 'Contáctanos hoy y te hacemos llegar más información.',
    },
    'veterinaria': {
        'emoji': '🐾',
        'tagline': 'Facilita el pago de procedimientos veterinarios',
        'beneficios_titulo': 'Beneficios para tu Veterinaria',
        'beneficios': [
            ('Cuotas sin interés', 'Para cirugías y procedimientos de mayor valor — el dueño de mascota decide más fácil.'),
            ('Todos los medios de pago', 'Tarjetas, débito, prepago y QR.'),
            ('Cuenta colaboradores', 'Perfil para veterinarios y recepción.'),
            ('Liquidación inmediata', 'El dinero en tu cuenta el mismo día.'),
            ('Sin mensualidad fija', 'Solo pagas por lo que transaccionas.'),
        ],
        'propuesta': 'Cuando un dueño de mascota enfrenta un procedimiento de alto costo, la opción de cuotas sin interés puede ser determinante. Con MercadoPago, facilitas la decisión de compra y aumentas tu facturación.',
        'cta': 'Hablemos esta semana — sin compromiso.',
    },
    'florería': {
        'emoji': '💐',
        'tagline': 'Acepta más medios de pago en tu florería',
        'beneficios_titulo': 'Beneficios para tu Florería',
        'beneficios': [
            ('Todos los medios de pago', 'Tarjetas, QR y prepago en un solo equipo portátil.'),
            ('Cobro a domicilio', 'Equipo inalámbrico para cobrar en entregas y eventos.'),
            ('Sin costo de arriendo', 'Sin mensualidad — solo pagas por ventas.'),
            ('Cuenta colaboradores', 'Control por empleado o repartidor.'),
            ('Liquidación rápida', 'Dinero disponible al día siguiente hábil.'),
        ],
        'propuesta': 'Una florería no puede perder ventas en eventos o entregas por falta de medios de pago. El Smart Point de MercadoPago es portátil, acepta todos los medios de pago y no tiene costo mensual.',
        'cta': '¿Conversamos esta semana?',
    },
    'oftalmología': {
        'emoji': '👁️',
        'tagline': 'Aumenta el cierre en tu centro de oftalmología',
        'beneficios_titulo': 'Beneficios para tu Centro de Oftalmología',
        'beneficios': [
            ('Cuotas sin interés', 'Para lentes de alto valor, cirugías y tratamientos — el paciente decide más fácil.'),
            ('Todos los medios de pago', 'Visa, Mastercard, débito, prepago y QR.'),
            ('Cuenta colaboradores', 'Perfil para médicos y personal de recepción.'),
            ('Liquidación el mismo día', 'El monto total disponible inmediatamente.'),
            ('Sin mensualidad fija', 'Pagas solo por las transacciones procesadas.'),
        ],
        'propuesta': 'Los tratamientos de alto valor tienen mayor conversión cuando el paciente tiene opciones de financiamiento. Con MercadoPago, ofreces cuotas sin interés sin asumir el riesgo — recibes el pago completo de inmediato.',
        'cta': 'Agenda una reunión esta semana y te mostramos los números.',
    },
    'tienda de muebles': {
        'emoji': '🛋️',
        'tagline': 'Aumenta el ticket promedio con cuotas sin interés',
        'beneficios_titulo': 'Beneficios para tu Tienda de Muebles',
        'beneficios': [
            ('Cuotas sin interés', 'Tus clientes compran más cuando pueden pagar en cuotas.'),
            ('Todos los medios de pago', 'Tarjetas, débito, prepago y QR.'),
            ('Cuenta colaboradores', 'Perfil para cada vendedor con registro de sus ventas.'),
            ('Liquidación inmediata', 'Recibes el total sin esperar las cuotas del cliente.'),
            ('Sin mensualidad', 'Sin costo fijo — solo pagas por lo que transaccionas.'),
        ],
        'propuesta': 'En una tienda de muebles, el ticket promedio es alto. Cuando ofreces cuotas sin interés, aumentas la tasa de conversión y el monto de cada compra. Con MercadoPago, tú recibes el total de inmediato.',
        'cta': 'Hablemos esta semana. Te mostramos cómo impacta en tus ventas.',
    },
    'lubricentro': {
        'emoji': '🔧',
        'tagline': 'Simplifica los cobros en tu lubricentro',
        'beneficios_titulo': 'Beneficios para tu Lubricentro',
        'beneficios': [
            ('Todos los medios de pago', 'Tarjetas de crédito, débito, prepago y QR.'),
            ('Cobro rápido en caja', 'Procesamiento en segundos para atender más clientes.'),
            ('Sin mensualidad fija', 'Solo pagas por las ventas que procesas.'),
            ('Cuenta colaboradores', 'Control por empleado con perfil individual.'),
            ('Reportes de venta', 'Historial completo en tiempo real desde tu celular.'),
        ],
        'propuesta': 'Un lubricentro que acepta tarjetas y QR no pierde ventas por problemas de efectivo. El Smart Point de MercadoPago es simple, rápido y sin costo mensual.',
        'cta': '¿Te contamos más? Agendemos una visita esta semana.',
    },
    'frenos': {
        'emoji': '🚗',
        'tagline': 'Moderniza los cobros en tu taller automotriz',
        'beneficios_titulo': 'Beneficios para tu Taller de Frenos',
        'beneficios': [
            ('Todos los medios de pago', 'Tarjetas de crédito, débito, prepago y QR.'),
            ('Cobro en terreno', 'Equipo portátil para cobrar en el taller o en el mesón.'),
            ('Sin mensualidad', 'Pagas solo por las transacciones procesadas.'),
            ('Cuenta colaboradores', 'Registro por mecánico o encargado.'),
            ('Liquidación rápida', 'Dinero disponible al siguiente día hábil.'),
        ],
        'propuesta': 'Un taller que acepta tarjetas y QR genera más confianza y no pierde ventas por problemas con efectivo. El Smart Point de MercadoPago se adapta a tu forma de trabajar — sin mensualidad ni complicaciones.',
        'cta': 'Conversemos esta semana.',
    },
    'spa': {
        'emoji': '💆',
        'tagline': 'Eleva la experiencia de pago en tu spa',
        'beneficios_titulo': 'Beneficios para tu Spa y Centro de Wellness',
        'beneficios': [
            ('Cuotas sin interés', 'Para paquetes y tratamientos de mayor valor — el cliente se anima más fácil.'),
            ('Todos los medios de pago', 'Tarjetas, débito, prepago y QR.'),
            ('Cuenta colaboradores', 'Perfil para terapeuta y recepción.'),
            ('Experiencia premium', 'Cobro rápido y elegante acorde a tu servicio.'),
            ('Sin mensualidad fija', 'Solo pagas por lo que transaccionas.'),
        ],
        'propuesta': 'En un spa, la experiencia del cliente es todo. Un cobro rápido y sin fricción refuerza esa experiencia. Además, al ofrecer cuotas sin interés, tus clientes acceden más fácilmente a paquetes completos.',
        'cta': 'Hablemos esta semana — te hacemos una propuesta personalizada.',
    },
}

DEFAULT_CONTENT = {
    'emoji': '💳',
    'tagline': 'La solución de pagos para tu negocio',
    'beneficios_titulo': 'Beneficios del Smart Point MercadoPago',
    'beneficios': [
        ('Todos los medios de pago', 'Tarjetas de crédito, débito, prepago y QR en un solo equipo.'),
        ('Sin mensualidad fija', 'Solo pagas por las transacciones que procesas.'),
        ('Liquidación inmediata', 'El dinero disponible en tu cuenta el mismo día.'),
        ('Cuenta colaboradores', 'Perfil individual para cada miembro de tu equipo.'),
        ('Soporte 24/7', 'Atención y soporte técnico cuando lo necesites.'),
    ],
    'propuesta': 'El Smart Point de MercadoPago es la solución de cobro más completa del mercado. Sin costo fijo, con liquidación inmediata y compatible con todos los medios de pago.',
    'cta': 'Contáctanos y te hacemos una propuesta sin compromiso.',
}


def generate_pdf(rubro: str) -> bytes:
    """Genera un PDF de propuesta comercial para el rubro dado."""
    rubro_key = rubro.lower().strip()
    content = RUBRO_CONTENT.get(rubro_key, DEFAULT_CONTENT)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Estilos personalizados ───────────────────────────────────────────────
    h1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=22,
                        textColor=MP_NAVY, spaceAfter=4, leading=26)
    h2 = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=14,
                        textColor=MP_BLUE, spaceAfter=6, leading=18)
    h3 = ParagraphStyle('h3', fontName='Helvetica-Bold', fontSize=11,
                        textColor=MP_NAVY, spaceAfter=3, leading=14)
    body_style = ParagraphStyle('body', fontName='Helvetica', fontSize=10,
                                textColor=MP_TEXT, spaceAfter=4, leading=14)
    small = ParagraphStyle('small', fontName='Helvetica', fontSize=9,
                           textColor=colors.HexColor('#6b7280'), leading=12)
    tagline_style = ParagraphStyle('tagline', fontName='Helvetica', fontSize=13,
                                   textColor=MP_DARK_BLUE, spaceAfter=8, leading=18)
    cta_style = ParagraphStyle('cta', fontName='Helvetica-Bold', fontSize=11,
                               textColor=WHITE, spaceAfter=4, leading=15,
                               alignment=TA_CENTER)
    footer_style = ParagraphStyle('footer', fontName='Helvetica', fontSize=8,
                                  textColor=colors.HexColor('#9ca3af'),
                                  alignment=TA_CENTER, leading=11)

    # ── HEADER ───────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph('<b><font color="#009EE3">mercado</font><font color="#1A1A2E">pago</font></b>',
                  ParagraphStyle('logo', fontName='Helvetica-Bold', fontSize=26,
                                 textColor=MP_BLUE, leading=30)),
        Paragraph(
            f'<font color="#6b7280" size="9">Propuesta Comercial</font><br/>'
            f'<font color="#1A1A2E" size="11"><b>Smart Point</b></font>',
            ParagraphStyle('hdr_right', fontName='Helvetica', fontSize=10,
                           alignment=TA_RIGHT, leading=14)
        )
    ]]
    header_table = Table(header_data, colWidths=[W * 0.55 - 40*mm, W * 0.45 - 0*mm])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, -1), MP_LIGHT_BLUE),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6*mm))

    # ── HERO ─────────────────────────────────────────────────────────────────
    emoji = content['emoji']
    story.append(Paragraph(f'{emoji} {rubro.title()}', h1))
    story.append(Paragraph(content['tagline'], tagline_style))
    story.append(HRFlowable(width='100%', thickness=2, color=MP_BLUE, spaceAfter=5*mm))

    # ── PROPUESTA ─────────────────────────────────────────────────────────────
    story.append(Paragraph('¿Por qué MercadoPago?', h2))
    story.append(Paragraph(content['propuesta'], body_style))
    story.append(Spacer(1, 4*mm))

    # ── SMART POINT HIGHLIGHT ─────────────────────────────────────────────────
    device_data = [[
        Paragraph(
            '<b><font color="#009EE3" size="13">Smart Point</font></b><br/>'
            '<font color="#1A1A2E" size="9">Terminal de cobro todo-en-uno</font><br/><br/>'
            '<font size="9" color="#374151">✓ Pantalla táctil Android<br/>'
            '✓ Impresora de tickets integrada<br/>'
            '✓ Conectividad WiFi y 4G<br/>'
            '✓ Batería recargable<br/>'
            '✓ Acepta chip, banda y contactless</font>',
            ParagraphStyle('device_text', fontName='Helvetica', fontSize=10, leading=14)
        ),
        Paragraph(
            '<font color="#009EE3" size="36">📱</font><br/>'
            '<font color="#6b7280" size="8">Smart Point<br/>MercadoPago</font>',
            ParagraphStyle('device_img', fontName='Helvetica', fontSize=10,
                           alignment=TA_CENTER, leading=14)
        ),
    ]]
    device_table = Table(device_data, colWidths=[W * 0.65 - 40*mm, W * 0.35])
    device_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), MP_GRAY),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (0, -1), 12),
        ('RIGHTPADDING', (-1, 0), (-1, -1), 12),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ('BOX', (0, 0), (-1, -1), 1, MP_LIGHT_GRAY),
    ]))
    story.append(device_table)
    story.append(Spacer(1, 5*mm))

    # ── BENEFICIOS ────────────────────────────────────────────────────────────
    story.append(Paragraph(content['beneficios_titulo'], h2))

    for titulo, descripcion in content['beneficios']:
        beneficio_data = [[
            Paragraph('●', ParagraphStyle('bullet', fontName='Helvetica-Bold',
                                          fontSize=14, textColor=MP_BLUE,
                                          alignment=TA_CENTER, leading=16)),
            Paragraph(f'<b>{titulo}</b><br/><font color="#6b7280">{descripcion}</font>',
                      ParagraphStyle('ben_text', fontName='Helvetica', fontSize=10,
                                     leading=14, textColor=MP_TEXT))
        ]]
        ben_table = Table(beneficio_data, colWidths=[8*mm, W - 48*mm - 8*mm])
        ben_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (0, -1), 0),
            ('RIGHTPADDING', (-1, 0), (-1, -1), 0),
        ]))
        story.append(ben_table)

    story.append(Spacer(1, 5*mm))

    # ── COMPARATIVA ──────────────────────────────────────────────────────────
    story.append(Paragraph('¿Por qué elegirnos?', h2))
    comp_data = [
        ['', 'MercadoPago', 'Competencia'],
        ['Sin mensualidad fija', '✓', '✗'],
        ['Vales de alimentación', '✓', 'Limitado'],
        ['Liquidación mismo día', '✓', 'Variable'],
        ['Cuotas sin interés', '✓', 'Con costo'],
        ['Soporte 24/7', '✓', 'Variable'],
        ['Integración digital', '✓', 'Limitado'],
    ]
    comp_table = Table(comp_data, colWidths=[W * 0.5 - 40*mm, (W * 0.5) / 2, (W * 0.5) / 2])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), MP_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BACKGROUND', (1, 1), (1, -1), colors.HexColor('#E8F7FD')),
        ('TEXTCOLOR', (1, 1), (1, -1), MP_GREEN),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (2, 1), (2, -1), colors.HexColor('#9ca3af')),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (0, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, MP_GRAY]),
        ('BOX', (0, 0), (-1, -1), 0.5, MP_LIGHT_GRAY),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, MP_LIGHT_GRAY),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 6*mm))

    # ── CTA ───────────────────────────────────────────────────────────────────
    cta_data = [[
        Paragraph(content['cta'], cta_style)
    ]]
    cta_table = Table(cta_data, colWidths=[W - 40*mm])
    cta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), MP_BLUE),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    story.append(cta_table)
    story.append(Spacer(1, 5*mm))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width='100%', thickness=0.5, color=MP_LIGHT_GRAY, spaceBefore=2*mm))
    story.append(Paragraph(
        'Juan Sebastián Pinto — Ejecutivo MercadoPago Chile<br/>'
        'juansebastian.pinto@mercadolibre.cl | mercadopago.cl',
        footer_style
    ))

    doc.build(story)
    return buffer.getvalue()
