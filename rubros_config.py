"""
Configuracion de rubros basada en la tabla de mensajes de prospeccion.
Cada rubro tiene: categoria, mensaje personalizado, link de imagen.
La imagen se descarga segun categoria (no por rubro individual).
"""

# Mapa rubro_label → rubro_key del sistema
RUBRO_LABEL_TO_KEY = {
    "botilleria": "botilleria",
    "botillería": "botilleria",
    "carniceria": "carniceria",
    "carnicería": "carniceria",
    "almacen de barrio": "almacen",
    "almacén de barrio": "almacen",
    "emporio": "emporio",
    "fruteria": "fruteria",
    "frutería": "fruteria",
    "minimarket": "minimarket",
    "panaderia": "panaderia",
    "panadería": "panaderia",
    "verduleria": "verduleria",
    "verdulería": "verduleria",
    "cafeteria": "cafeteria",
    "cafetería": "cafeteria",
    "fuente de soda": "fuente_de_soda",
    "pizzeria": "pizzeria",
    "pizzería": "pizzeria",
    "sandwicheria": "sandwicheria",
    "sandwichería": "sandwicheria",
    "sushi": "sushi",
    "gimnasio / box": "gimnasio",
    "gimnasio": "gimnasio",
    "jugueterias": "bazar",
    "jugueterías": "bazar",
    "jugueteria": "bazar",
    "juguetería": "bazar",
    "regalos": "bazar",
    "bazar_regalos": "bazar",
    "ferreteria": "ferreteria",
    "ferretería": "ferreteria",
    "libreria": "libreria",
    "librería": "libreria",
    "tienda de muebles": "muebleria",
    "farmacia independiente": "farmacia",
    "centro de estetica / spa": "spa",
    "centro de estética / spa": "spa",
    "clinica dental": "clinica_dental",
    "clínica dental": "clinica_dental",
    "taller mecanico": "taller",
    "taller mecánico": "taller",
    "veterinaria / pets": "veterinaria",
    "lavanderia": "lavanderia",
    "lavandería": "lavanderia",
    "peluqueria / barberia": "peluqueria",
    "peluquería / barbería": "peluqueria",
}

# Configuracion completa por rubro_key
RUBROS = {
    "botilleria": {
        "label": "Botillería",
        "emoji": "🍺",
        "categoria": "Comercio de Alta Demanda Fin de Semana",
        "imagen_url": "https://i.postimg.cc/BbYhxn1j/Comercio_de_Alta_Demanda_Fin_de_Semana.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en la botillería el flujo es rápido y no puedes quedarte sin sistema. Con el Point Smart 2 tienes conexión multiadquirente para cero caídas, no pagas arriendo y recibes tu plata al instante incluso los fines de semana. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "carniceria": {
        "label": "Carnicería",
        "emoji": "🥩",
        "categoria": "Comercio de Alta Demanda Fin de Semana",
        "imagen_url": "https://i.postimg.cc/BbYhxn1j/Comercio_de_Alta_Demanda_Fin_de_Semana.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en la carnicería la agilidad y el flujo de caja diario son vitales. Con nuestro equipo emites la boleta electrónica directamente, no pagas arriendo mensual y recibes la plata al instante todos los días. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "almacen": {
        "label": "Almacén de barrio",
        "emoji": "🏪",
        "categoria": "Comercio de Barrio Diario",
        "imagen_url": "https://i.postimg.cc/MHPsypjX/Comercio_de_Barrio_Diario.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en el almacén cada peso cuenta en las ventas pequeñas. Con nosotros no pagas arriendo, recibes tu plata al instante para reponer mercadería y atraes a más vecinos cobrando con Valeras. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "emporio": {
        "label": "Emporio",
        "emoji": "🧀",
        "categoria": "Comercio de Barrio Diario",
        "imagen_url": "https://i.postimg.cc/MHPsypjX/Comercio_de_Barrio_Diario.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en tu emporio buscas agilizar la atención y cuidar el margen. Con nosotros no pagas arriendo, emites la boleta electrónica fácilmente y atraes más flujo aceptando Valeras de alimentación. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "fruteria": {
        "label": "Frutería",
        "emoji": "🍎",
        "categoria": "Comercio de Barrio Diario",
        "imagen_url": "https://i.postimg.cc/MHPsypjX/Comercio_de_Barrio_Diario.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en la frutería el flujo de caja diario es vital para ir a la vega. Con nuestro equipo no pagas arriendo, emites tu boleta electrónica fácilmente y recibes tu plata al instante. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "minimarket": {
        "label": "Minimarket",
        "emoji": "🛒",
        "categoria": "Comercio de Barrio Diario",
        "imagen_url": "https://i.postimg.cc/MHPsypjX/Comercio_de_Barrio_Diario.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en el minimarket necesitas proteger tus ganancias en compras pequeñas. Con nosotros no pagas arriendo, aceptas Valeras de alimentación y tienes tu plata al instante todos los días. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "panaderia": {
        "label": "Panadería",
        "emoji": "🥐",
        "categoria": "Comercio de Barrio Diario",
        "imagen_url": "https://i.postimg.cc/MHPsypjX/Comercio_de_Barrio_Diario.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en la panadería procesan muchísimas ventas chicas al día. Con Mercado Pago no cobramos arriendo, recibes tu plata al instante para insumos diarios y atraes más flujo cobrando con Valeras. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "verduleria": {
        "label": "Verdulería",
        "emoji": "🥬",
        "categoria": "Comercio de Barrio Diario",
        "imagen_url": "https://i.postimg.cc/MHPsypjX/Comercio_de_Barrio_Diario.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en la verdulería necesitas efectivo diario para ir a la vega. Con nuestro Point Smart 2 no pagas arriendo, recibes tu plata al instante y puedes atraer más clientes aceptando Valeras de alimentación. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "cafeteria": {
        "label": "Cafetería",
        "emoji": "☕",
        "categoria": "Gastronomía y Comida Rápida",
        "imagen_url": "https://i.postimg.cc/sx6npgZX/Gastronom%C3%ADa_y_Comida_R%C3%A1pida.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en una cafetería la agilidad en la barra lo es todo. Nuestro POS se integra a tu caja, no te cobra arriendo mensual y te permite aceptar Valeras para captar oficinistas. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "fuente_de_soda": {
        "label": "Fuente de soda",
        "emoji": "🍔",
        "categoria": "Gastronomía y Comida Rápida",
        "imagen_url": "https://i.postimg.cc/sx6npgZX/Gastronom%C3%ADa_y_Comida_R%C3%A1pida.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que sacar las mesas rápido a la hora de almuerzo es fundamental. Nuestro equipo se integra con tu software de caja, acepta Valeras para captar oficinistas y te entrega la plata al instante. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "pizzeria": {
        "label": "Pizzería",
        "emoji": "🍕",
        "categoria": "Gastronomía y Comida Rápida",
        "imagen_url": "https://i.postimg.cc/sx6npgZX/Gastronom%C3%ADa_y_Comida_R%C3%A1pida.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que una pizzería tiene un ritmo altísimo de comandas. Con nuestro Point Smart 2 puedes integrar tu sistema de pedidos, aceptar Valeras y tener tu plata al instante para reponer ingredientes. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "sandwicheria": {
        "label": "Sandwichería",
        "emoji": "🥪",
        "categoria": "Gastronomía y Comida Rápida",
        "imagen_url": "https://i.postimg.cc/sx6npgZX/Gastronom%C3%ADa_y_Comida_R%C3%A1pida.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en la sandwichería la rapidez es clave al mediodía. Nuestro equipo se integra a tu caja, atrae oficinistas aceptando Valeras y te entrega la plata al instante todos los días. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "sushi": {
        "label": "Sushi / Japonés",
        "emoji": "🍣",
        "categoria": "Gastronomía y Comida Rápida",
        "imagen_url": "https://i.postimg.cc/sx6npgZX/Gastronom%C3%ADa_y_Comida_R%C3%A1pida.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en el delivery y local de sushi el control de pedidos es vital. Nuestro POS se integra con tu software gastronómico, no te cobra arriendo y asegura que recibas tu plata al instante. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "gimnasio": {
        "label": "Gimnasio / Box",
        "emoji": "💪",
        "categoria": "Membresías y Entrenamientos",
        "imagen_url": "https://i.postimg.cc/mZ86x8pq/Membres%C3%ADas_y_Entrenamientos.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en el gimnasio vender planes anuales es clave para tu rentabilidad. Con nosotros cobras planes con cuotas sin interés recibiendo la plata al instante, o envías cobros a distancia por link de pago. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "bazar": {
        "label": "Jugueteria / Regalos",
        "emoji": "🎁",
        "categoria": "Retail Especializado y Hogar",
        "imagen_url": "https://i.postimg.cc/x10G3zSs/Retail-Especializado-y-Hogar.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en un bazar necesitas cobrar rápido y evitar costos ocultos. Con Mercado Pago no pagas arriendo, tienes tu plata al instante y puedes aceptar Valeras para captar a estudiantes y trabajadores. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "ferreteria": {
        "label": "Ferretería",
        "emoji": "🔧",
        "categoria": "Retail Especializado y Hogar",
        "imagen_url": "https://i.postimg.cc/x10G3zSs/Retail-Especializado-y-Hogar.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que vender herramientas caras es más fácil si ofreces facilidades. Tus clientes pagan en cuotas sin interés y tú recibes la plata al instante, además el equipo se integra a tu sistema de caja. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "libreria": {
        "label": "Librería",
        "emoji": "📚",
        "categoria": "Retail Especializado y Hogar",
        "imagen_url": "https://i.postimg.cc/x10G3zSs/Retail-Especializado-y-Hogar.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que las librerías tienen temporadas fuertes gracias a beneficios estudiantiles. Con nosotros puedes aceptar Junaeb y otras Valeras, no pagas arriendo de la máquina y tienes tu plata al instante. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "muebleria": {
        "label": "Tienda de muebles",
        "emoji": "🛋️",
        "categoria": "Retail Especializado y Hogar",
        "imagen_url": "https://i.postimg.cc/x10G3zSs/Retail-Especializado-y-Hogar.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en mueblería los clientes buscan cuotas para renovar su hogar. Con nosotros ofreces cuotas sin interés, recibes la plata al instante y usas un equipo por el que no pagas arriendo. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "farmacia": {
        "label": "Farmacia independiente",
        "emoji": "💊",
        "categoria": "Salud y Farmacia",
        "imagen_url": "https://i.postimg.cc/8cPKJ6c9/Salud_y_Farmacia.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en una farmacia el control de inventario es crítico. Nuestro equipo se integra con sistemas como SmartFarma, acepta Valeras y te entrega la plata al instante todos los días. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "spa": {
        "label": "Centro de estética / Spa",
        "emoji": "💆",
        "categoria": "Servicios de Alto Ticket",
        "imagen_url": "https://i.postimg.cc/fy2HxR0y/Servicios_de_Alto_Ticket.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que los tratamientos estéticos son una inversión para tus clientes. Con nosotros aseguras ventas con cuotas sin interés, recibes la plata al instante, y puedes cobrar reservas por link de pago. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "clinica_dental": {
        "label": "Clínica dental",
        "emoji": "🦷",
        "categoria": "Servicios de Alto Ticket",
        "imagen_url": "https://i.postimg.cc/fy2HxR0y/Servicios_de_Alto_Ticket.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que los tratamientos dentales son más fáciles de vender con buenas facilidades. Con nuestro equipo ofreces cuotas sin interés, recibes el pago al instante, y además puedes acceder a créditos para tu clínica. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "taller": {
        "label": "Taller mecánico",
        "emoji": "🔩",
        "categoria": "Servicios de Alto Ticket",
        "imagen_url": "https://i.postimg.cc/fy2HxR0y/Servicios_de_Alto_Ticket.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que las reparaciones son costosas y el cliente agradece las facilidades. Con nosotros ofreces cuotas sin interés, recibes la plata al instante para repuestos y puedes acceder a créditos a tu medida. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "veterinaria": {
        "label": "Veterinaria / Pets",
        "emoji": "🐾",
        "categoria": "Servicios de Alto Ticket",
        "imagen_url": "https://i.postimg.cc/fy2HxR0y/Servicios_de_Alto_Ticket.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en la veterinaria hay cirugías que los dueños necesitan parcializar. Con nosotros ofreces cuotas sin interés, recibes el pago al instante y emites la boleta electrónica desde el mismo equipo. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "lavanderia": {
        "label": "Lavandería",
        "emoji": "👕",
        "categoria": "Servicios Personales Diario",
        "imagen_url": "https://i.postimg.cc/G3qS0qgS/Servicios_Personales_Diario.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en una lavandería buscas agilidad sin sumar costos fijos. Con nuestro equipo no pagas arriendo, emites la boleta electrónica desde la máquina y recibes tu plata al instante. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
    "peluqueria": {
        "label": "Peluquería / Barbería",
        "emoji": "✂️",
        "categoria": "Servicios Personales Diario",
        "imagen_url": "https://i.postimg.cc/G3qS0qgS/Servicios_Personales_Diario.png",
        "mensaje": "Hola [Nombre], soy Sebastián Pinto de Mercado Pago. Sé que en la barbería buscas cobrar rápido y evitar costos fijos. Con nuestro equipo no pagas arriendo mensual, emites la boleta electrónica directamente y recibes la plata al instante. Sí tienes un tiempo en la semana, avisame para que agendemos una llamada o visita y pueda entregarte una propuesta que beneficie tu negocio.",
    },
}

# Mensajes de respuesta automatica segun reaccion del cliente
RESPUESTAS_AUTO = {
    "interesado": (
        "Excelente, me alegra tu interes! Te contactare a la brevedad para coordinar. "
        "Si prefieres elegir tu horario directamente, puedes agendar aqui: {calendar_link}"
    ),
    "no_interesado": (
        "Entendido, no hay problema! Si en algun momento cambias de opinion o necesitas "
        "informacion sobre MercadoPago, aqui estaré. Que tengas un excelente dia!"
    ),
    "quiere_reunion": (
        "Perfecto! Puedes agendar directamente en mi calendario segun tu disponibilidad: "
        "{calendar_link} - Te espero!"
    ),
}

# Palabras clave para deteccion automatica de respuestas
KEYWORDS_INTERESADO = [
    "si", "sí", "me interesa", "interesado", "quiero", "cuéntame", "cuentame",
    "información", "informacion", "mas info", "más info", "dale", "ok", "okay",
    "cuando", "cuándo", "visita", "llamada", "reunión", "reunion"
]

KEYWORDS_NO_INTERESADO = [
    "no", "no gracias", "no me interesa", "no quiero", "no por favor",
    "eliminar", "no molestar", "stop", "basta", "suficiente"
]

KEYWORDS_REUNION = [
    "agendar", "agenda", "calendar", "reunion", "reunión", "visita",
    "llamada", "cuando puedes", "cuándo puedes", "disponibilidad"
]


def get_mensaje(rubro_key: str, nombre: str, comuna: str = '') -> str:
    """Genera el mensaje personalizado reemplazando [Nombre]"""
    # Verificar si hay mensaje personalizado para este rubro en config BD
    try:
        from database import get_db
        conn = get_db()
        row = conn.execute("SELECT value FROM config WHERE key=?", (f'mensaje_rubro_{rubro_key}',)).fetchone()
        conn.close()
        if row:
            return row['value'].replace('{nombre}', nombre).replace('[Nombre]', nombre)
    except:
        pass

    # Si no hay comuna, usar mensaje generico
    if not comuna or comuna.strip() == '':
        return (
            f"Hola {nombre}, soy Sebastian Pinto, ayer vi tu negocio y creo que "
            "Mercado Pago puede ser una gran alternativa. Mira, te dejo una imagen de "
            "referencia en lo que te podriamos aportar. Avisame si te parece, y evaluamos "
            "en funcion de tu actual proveedor de pagos. Saludos"
        )
    rubro = RUBROS.get(rubro_key)
    if not rubro:
        # Rubro nuevo - mensaje especial para rubros importados
        return (
            f"Hola {nombre}, soy Sebastian Pinto, ayer pase por fuera de tu negocio y creo que "
            "Mercado Pago puede ser una gran alternativa. Mira, te dejo una imagen de "
            "referencia en lo que te podriamos aportar. Avisame si te parece, y evaluamos "
            "en funcion de tu actual proveedor de pagos. Saludos"
        )
    return rubro["mensaje"].replace("[Nombre]", nombre)


def get_imagen_url(rubro_key: str) -> str | None:
    """Retorna la URL de imagen segun categoria del rubro"""
    rubro = RUBROS.get(rubro_key)
    return rubro["imagen_url"] if rubro else None


def get_rubro_label(rubro_key: str) -> str:
    rubro = RUBROS.get(rubro_key)
    return rubro["label"] if rubro else rubro_key


def get_categoria(rubro_key: str) -> str:
    rubro = RUBROS.get(rubro_key)
    return rubro["categoria"] if rubro else "Sin categoría"


def list_rubros():
    return [(key, val["label"], val["emoji"]) for key, val in RUBROS.items()]


def detectar_intencion(texto: str) -> str:
    """
    Detecta automaticamente la intencion del cliente segun su respuesta.
    Retorna: 'interesado' | 'no_interesado' | 'quiere_reunion' | 'desconocido'
    """
    texto_lower = texto.lower().strip()
    if any(k in texto_lower for k in KEYWORDS_REUNION):
        return "quiere_reunion"
    if any(k in texto_lower for k in KEYWORDS_NO_INTERESADO):
        return "no_interesado"
    if any(k in texto_lower for k in KEYWORDS_INTERESADO):
        return "interesado"
    return "desconocido"


def get_respuesta_auto(intencion: str, calendar_link: str = "") -> str | None:
    """Retorna el mensaje de respuesta automatica segun intencion"""
    template = RESPUESTAS_AUTO.get(intencion)
    if not template:
        return None
    return template.format(calendar_link=calendar_link)


# Mensajes de fidelizacion para sellers activos (rotacion semanal)
FIDELIZACION_MESSAGES = [
    {
        "key": "boletas",
        "titulo": "Revisa tu declaración de boletas",
        "emoji": "📊",
        "mensaje": (
            "Hola {nombre}, Sebastian Pinto de MercadoPago aqui.\n\n"
            "Recordatorio importante: no olvides revisar tu declaracion de boletas en el SII. "
            "Si necesitas ayuda para cuadrar tus ventas con MercadoPago, estoy disponible. "
            "Puedo ayudarte a descargar el resumen de transacciones desde la app.\n\n"
            "Cualquier duda, aqui estoy!"
        )
    },
    {
        "key": "pos_update",
        "titulo": "Verifica que tu POS esté actualizado",
        "emoji": "📱",
        "mensaje": (
            "Hola {nombre}, Sebastian Pinto de MercadoPago.\n\n"
            "Checklist semanal para tu POS:\n"
            "- Pantalla sin rayaduras?\n"
            "- Bateria cargando bien?\n"
            "- Firmware actualizado?\n"
            "- Conectividad estable?\n\n"
            "Si tienes algun problema con tu equipo, cuentame y lo resolvemos rapido!"
        )
    },
    {
        "key": "disponible",
        "titulo": "Tu ejecutivo disponible para consultas",
        "emoji": "🤝",
        "mensaje": (
            "Hola {nombre}, buen inicio de semana! Soy Sebastian Pinto, tu ejecutivo de MercadoPago.\n\n"
            "Recuerda que estoy disponible para cualquier consulta:\n"
            "- Dudas sobre tu POS\n"
            "- Revision de transacciones\n"
            "- Nuevos equipos o planes\n"
            "- Cualquier otro tema\n\n"
            "No dudes en escribirme!"
        )
    },
    {
        "key": "tip_ventas",
        "titulo": "Tip de ventas de la semana",
        "emoji": "💡",
        "mensaje": (
            "Hola {nombre}, Sebastian Pinto de MercadoPago.\n\n"
            "Tip de la semana: los negocios que ofrecen cuotas "
            "aumentan su ticket promedio en un 25%.\n\n"
            "Con tu POS MercadoPago ya puedes ofrecer cuotas sin interes a tus clientes. "
            "Quieres que te explique como activarlo?"
        )
    }
]
