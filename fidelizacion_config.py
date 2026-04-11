"""
Mensajes de fidelizacion por etapa y categoria de rubro.
Etapas segun dias desde estado cerrado:
  Dia 7:  Activacion y Liquidez
  Dia 14: Potenciar Ventas
  Dia 15: Seguimiento
  Dia 30: Gestion y Seguridad
  Dia 35: Fidelizacion y Upselling
"""

# Mapa categoria → mensajes por etapa
FIDELIZACION = {
    "Comercio de Alta Demanda Fin de Semana": {
        "activacion":    "Hola! Llego el finde y tu Point Smart 2 lo sabe. Recuerda que la plata de tus ventas de sabado y domingo te llega al instante para reponer stock el lunes. Exito en las ventas!",
        "potenciar":     "Hola! Si tu local se llena, cobra tranquilo. Tu maquina es multiprocesador (tiene 3 carreteras de pago) para asegurar que nunca se caiga. A vender con todo sin interrupciones!",
        "seguimiento":   "Hola! Como va todo? Soy Sebastian Pinto, tu ejecutivo de Mercado Pago. Te escribo cortito para saludarte y recordarte que cuenta conmigo para lo que necesites. Si tienes cualquier duda con tu maquina o la app, escribeme nomas y lo vemos. Ah, y si tienes algun amigo, colega o familiar con negocio que ande buscando mejorar sus cobros y ahorrar plata, pasale mi contacto con toda confianza! Yo feliz de ayudarlos. Que tengas una excelente semana y muchas ventas!",
        "gestion":       "Hola! Si tienes cajeros de turno el finde, creales una Cuenta Colaborador. Cobran desde la maquina, pero tu plata y tu saldo quedan 100% privados y seguros.",
        "fidelizacion":  "Hola! Las altas ventas del finde pueden darte mas plata. Recuerda que si eres rut persona Natural, Activa Haz crecer tu dinero en la App y tu saldo generara rentabilidad diaria (4,6%). Sacale provecho a tus ganancias!",
    },
    "Comercio de Barrio Diario": {
        "activacion":    "Hola! Espero que tu Point Smart 2 este a full. Recuerda que la emision de boletas electronicas es ilimitada y se conecta directo al SII. Cualquier duda, me escribes!",
        "potenciar":     "Hola! No olvides activar Junaeb, Edenred y Pluxee desde tu App. Muchos vecinos buscan donde usar su saldo de alimentacion, aprovecha esas ventas extras!",
        "seguimiento":   "Hola! Como va todo? Soy Sebastian Pinto, tu ejecutivo de Mercado Pago. Te escribo cortito para saludarte y recordarte que cuenta conmigo para lo que necesites. Si tienes cualquier duda con tu maquina o la app, escribeme nomas y lo vemos. Ah, y si tienes algun amigo, colega o familiar con negocio que ande buscando mejorar sus cobros y ahorrar plata, pasale mi contacto con toda confianza! Yo feliz de ayudarlos. Que tengas una excelente semana y muchas ventas!",
        "gestion":       "Hola! Ya pediste tu Tarjeta Mercado Pago fisica y gratis? Usa la plata de tus ventas al instante para ir a La Vega o comprar a proveedores. Pidela en la app!",
        "fidelizacion":  "Hola! Haz que tu plata trabaje por ti. Recuerda que si eres rut persona Natural, Activa Haz crecer tu dinero en la App y tu saldo generara rentabilidad diaria (4,6%). Sacale provecho a tus ganancias!",
    },
    "Gastronomia y Comida Rapida": {
        "activacion":    "Hola! Llevas una semana con tu Point Smart 2. Recuerda que tu plata esta disponible al instante para reponer insumos frescos a diario. Avisa si tienes dudas con tus primeros cobros!",
        "potenciar":     "Hola! Sabias que puedes activar Valeras (Edenred, Pluxee y Junaeb) desde tu app? Es ideal para atraer oficinistas y estudiantes al almuerzo. Avisa si te ayudo a activarlo!",
        "seguimiento":   "Hola! Como va todo? Soy Sebastian Pinto, tu ejecutivo de Mercado Pago. Te escribo cortito para saludarte y recordarte que cuenta conmigo para lo que necesites. Si tienes cualquier duda con tu maquina o la app, escribeme nomas y lo vemos. Ah, y si tienes algun amigo, colega o familiar con negocio que ande buscando mejorar sus cobros y ahorrar plata, pasale mi contacto con toda confianza! Yo feliz de ayudarlos. Que tengas una excelente semana y muchas ventas!",
        "gestion":       "Hola! Para mayor seguridad con tu equipo, crea Cuentas de Colaboradores. Tus garzones podran cobrar sin ver el saldo de tu negocio. Pruebalo, es super util!",
        "fidelizacion":  "Hola! Ya llevas un tiempito con nosotros. Recuerda que al transaccionar con nosotros, vas generando historial para acceder a Creditos a tu medida. Ideal para innovar en tu local!",
    },
    "Gastronomía y Comida Rápida": {
        "activacion":    "Hola! Llevas una semana con tu Point Smart 2. Recuerda que tu plata esta disponible al instante para reponer insumos frescos a diario. Avisa si tienes dudas con tus primeros cobros!",
        "potenciar":     "Hola! Sabias que puedes activar Valeras (Edenred, Pluxee y Junaeb) desde tu app? Es ideal para atraer oficinistas y estudiantes al almuerzo. Avisa si te ayudo a activarlo!",
        "seguimiento":   "Hola! Como va todo? Soy Sebastian Pinto, tu ejecutivo de Mercado Pago. Te escribo cortito para saludarte y recordarte que cuenta conmigo para lo que necesites. Si tienes cualquier duda con tu maquina o la app, escribeme nomas y lo vemos. Ah, y si tienes algun amigo, colega o familiar con negocio que ande buscando mejorar sus cobros y ahorrar plata, pasale mi contacto con toda confianza! Yo feliz de ayudarlos. Que tengas una excelente semana y muchas ventas!",
        "gestion":       "Hola! Para mayor seguridad con tu equipo, crea Cuentas de Colaboradores. Tus garzones podran cobrar sin ver el saldo de tu negocio. Pruebalo, es super util!",
        "fidelizacion":  "Hola! Ya llevas un tiempito con nosotros. Recuerda que al transaccionar con nosotros, vas generando historial para acceder a Creditos a tu medida. Ideal para innovar en tu local!",
    },
    "Membresias y Entrenamientos": {
        "activacion":    "Hola! Vender el plan anual es clave. Ofrecelo en cuotas sin interes; tu alumno paga comodo a plazo y tu recibes todo el dinero del ano al instante. Asegura la rentabilidad!",
        "potenciar":     "Hola! Automatiza el cobro de mensualidades con la herramienta de Suscripciones de Mercado Pago. Tu alumno inscribe su tarjeta una vez y se cobra solo cada mes. Menos morosidad!",
        "seguimiento":   "Hola! Como va todo? Soy Sebastian Pinto, tu ejecutivo de Mercado Pago. Te escribo cortito para saludarte y recordarte que cuenta conmigo para lo que necesites. Si tienes cualquier duda con tu maquina o la app, escribeme nomas y lo vemos. Ah, y si tienes algun amigo, colega o familiar con negocio que ande buscando mejorar sus cobros y ahorrar plata, pasale mi contacto con toda confianza! Yo feliz de ayudarlos. Que tengas una excelente semana y muchas ventas!",
        "gestion":       "Hola! Para mayor orden, dale acceso de cajero a las personas de recepcion usando Cuentas Colaborador. Ellos cobran mensualidades sin ver tu saldo ni ganancias.",
        "fidelizacion":  "Hola! La plata de esos planes anuales puede generarte intereses diarios. Recuerda que si eres rut persona Natural, Activa Haz crecer tu dinero en la App y tu saldo generara rentabilidad diaria (4,6%). Sacale provecho a tus ganancias!",
    },
    "Membresías y Entrenamientos": {
        "activacion":    "Hola! Vender el plan anual es clave. Ofrecelo en cuotas sin interes; tu alumno paga comodo a plazo y tu recibes todo el dinero del ano al instante. Asegura la rentabilidad!",
        "potenciar":     "Hola! Automatiza el cobro de mensualidades con la herramienta de Suscripciones de Mercado Pago. Tu alumno inscribe su tarjeta una vez y se cobra solo cada mes. Menos morosidad!",
        "seguimiento":   "Hola! Como va todo? Soy Sebastian Pinto, tu ejecutivo de Mercado Pago. Te escribo cortito para saludarte y recordarte que cuenta conmigo para lo que necesites. Si tienes cualquier duda con tu maquina o la app, escribeme nomas y lo vemos. Ah, y si tienes algun amigo, colega o familiar con negocio que ande buscando mejorar sus cobros y ahorrar plata, pasale mi contacto con toda confianza! Yo feliz de ayudarlos. Que tengas una excelente semana y muchas ventas!",
        "gestion":       "Hola! Para mayor orden, dale acceso de cajero a las personas de recepcion usando Cuentas Colaborador. Ellos cobran mensualidades sin ver tu saldo ni ganancias.",
        "fidelizacion":  "Hola! La plata de esos planes anuales puede generarte intereses diarios. Recuerda que si eres rut persona Natural, Activa Haz crecer tu dinero en la App y tu saldo generara rentabilidad diaria (4,6%). Sacale provecho a tus ganancias!",
    },
    "Retail Especializado y Hogar": {
        "activacion":    "Hola! Recuerda ofrecer a tus clientes pagar articulos de mayor valor en cuotas sin interes. Tu recibes tu plata al instante y, por nueva normativa, el adelantamiento ya no paga IVA.",
        "potenciar":     "Hola! Agiliza tu caja recordando que tu equipo emite boleta electronica ilimitada sin doble digitacion. Si tienes dudas con el portal de boletas, me avisas y lo revisamos!",
        "seguimiento":   "Hola! Como va todo? Soy Sebastian Pinto, tu ejecutivo de Mercado Pago. Te escribo cortito para saludarte y recordarte que cuenta conmigo para lo que necesites. Si tienes cualquier duda con tu maquina o la app, escribeme nomas y lo vemos. Ah, y si tienes algun amigo, colega o familiar con negocio que ande buscando mejorar sus cobros y ahorrar plata, pasale mi contacto con toda confianza! Yo feliz de ayudarlos. Que tengas una excelente semana y muchas ventas!",
        "gestion":       "Hola! Si haces despachos a domicilio, usa el Link de Pago. Lo envias por WhatsApp, aseguras la venta antes de despachar y evitas fraudes. Super seguro y practico!",
        "fidelizacion":  "Hola! Tras unas semanas vendiendo con nosotros, pronto se te habilitaran Creditos para pymes. Es la inyeccion de capital perfecta para comprar stock de temporada. Sigue asi!",
    },
    "Salud y Farmacia": {
        "activacion":    "Hola! Tu Point Smart 2 se integra con tu sistema de caja (SmartFarma) para llevar tu stock perfecto. Ademas, tienes tu plata al instante para reponer medicamentos vitales.",
        "potenciar":     "Hola! Ofrece cuotas sin interes en medicamentos de alto costo. Ayudas mucho a tus pacientes y tu recibes tu plata completa de inmediato. Ambos ganan!",
        "seguimiento":   "Hola! Como va todo? Soy Sebastian Pinto, tu ejecutivo de Mercado Pago. Te escribo cortito para saludarte y recordarte que cuenta conmigo para lo que necesites. Si tienes cualquier duda con tu maquina o la app, escribeme nomas y lo vemos. Ah, y si tienes algun amigo, colega o familiar con negocio que ande buscando mejorar sus cobros y ahorrar plata, pasale mi contacto con toda confianza! Yo feliz de ayudarlos. Que tengas una excelente semana y muchas ventas!",
        "gestion":       "Hola! Tienen delivery de medicamentos? Cobra seguro enviando un Link de Pago por WhatsApp antes de que salga el repartidor. 100% integrado a tu caja!",
        "fidelizacion":  "Hola! Transaccionar con nosotros te genera un buen historial. Pronto podras acceder a Creditos a medida para surtir tu farmacia con mayor volumen de stock. Sigue asi!",
    },
    "Servicios de Alto Ticket": {
        "activacion":    "Hola! Vender tratamientos o reparaciones es mas facil ofreciendo cuotas sin interes. Tus clientes pagan a plazo, pero tu recibes el total al instante. Cualquier duda, me avisas!",
        "potenciar":     "Hola! Necesitas asegurar reservas o pedir adelantos? Envia un Link de Pago por WhatsApp. Es rapido, seguro y el cliente paga desde su celular. Pruebalo hoy!",
        "seguimiento":   "Hola! Como va todo? Soy Sebastian Pinto, tu ejecutivo de Mercado Pago. Te escribo cortito para saludarte y recordarte que cuenta conmigo para lo que necesites. Si tienes cualquier duda con tu maquina o la app, escribeme nomas y lo vemos. Ah, y si tienes algun amigo, colega o familiar con negocio que ande buscando mejorar sus cobros y ahorrar plata, pasale mi contacto con toda confianza! Yo feliz de ayudarlos. Que tengas una excelente semana y muchas ventas!",
        "gestion":       "Hola! Configura accesos restringidos para tus recepcionistas con Cuentas Colaborador. Podran usar la maquina sin ver tu saldo ni informacion confidencial de tus ventas.",
        "fidelizacion":  "Hola! Vender con Mercado Pago te ayuda a construir historial financiero. Pronto podras acceder a Creditos de Cuota Fija, perfectos para renovar tu equipamiento o cualquier otra necesidad.",
    },
    "Servicios Personales Diario": {
        "activacion":    "Hola! Espero que tu semana vaya excelente. Recuerda emitir la boleta electronica directo desde tu maquina, asi agilizas la atencion y simplificas tu contabilidad.",
        "potenciar":     "Hola! Si arriendas sillas a otros barberos o peluqueros, creales accesos de Colaborador. Asi todos usan la misma maquina de forma independiente, ordenada y segura.",
        "seguimiento":   "Hola! Como va todo? Soy Sebastian Pinto, tu ejecutivo de Mercado Pago. Te escribo cortito para saludarte y recordarte que cuenta conmigo para lo que necesites. Si tienes cualquier duda con tu maquina o la app, escribeme nomas y lo vemos. Ah, y si tienes algun amigo, colega o familiar con negocio que ande buscando mejorar sus cobros y ahorrar plata, pasale mi contacto con toda confianza! Yo feliz de ayudarlos. Que tengas una excelente semana y muchas ventas!",
        "gestion":       "Hola! Evita las cancelaciones sorpresa. Pide un abono previo para reservar la cita enviando un Link de Pago por WhatsApp. Asegura tu tiempo y tu trabajo!",
        "fidelizacion":  "Hola! Ya pediste tu Tarjeta Mercado Pago gratis en la App? Usa la plata de tus ventas de inmediato para comprar insumos o pagar tus cuentas directamente desde el celular.",
    },
}

# Calendario de etapas: dias desde cierre → clave de mensaje
ETAPAS = [
    (7,  "activacion",   "Activacion y Liquidez"),
    (14, "potenciar",    "Potenciar Ventas"),
    (15, "seguimiento",  "Seguimiento"),
    (30, "gestion",      "Gestion y Seguridad"),
    (35, "fidelizacion", "Fidelizacion y Upselling"),
]

# Fallback generico para categorias no mapeadas
FALLBACK = {
    "activacion":   "Hola! Espero que todo vaya excelente con tu negocio. Recuerda que cuentas con tu Point Smart 2 para cobrar con total seguridad. Cualquier duda, me escribes!",
    "potenciar":    "Hola! Recuerda que puedes aceptar multiples medios de pago con tu equipo. Si necesitas ayuda para activar algun beneficio, estoy disponible!",
    "seguimiento":  "Hola! Como va todo? Soy Sebastian Pinto, tu ejecutivo de Mercado Pago. Te escribo cortito para saludarte y recordarte que cuenta conmigo para lo que necesites. Que tengas una excelente semana y muchas ventas!",
    "gestion":      "Hola! Recuerda crear Cuentas Colaborador para tu equipo. Cobran desde la maquina pero tu saldo queda 100% privado y seguro.",
    "fidelizacion": "Hola! Al transaccionar con nosotros vas generando historial para acceder a Creditos a tu medida. Sigue asi y pronto tendras nuevas herramientas financieras!",
}


def get_fidelizacion_mensaje(categoria: str, etapa_key: str) -> str:
    msgs = FIDELIZACION.get(categoria, FALLBACK)
    return msgs.get(etapa_key, FALLBACK.get(etapa_key, ""))


def get_etapa_por_dias(dias: int) -> tuple | None:
    for d, key, nombre in ETAPAS:
        if dias == d:
            return (d, key, nombre)
    return None


def get_etapas_pendientes(dias: int) -> list:
    pendientes = []
    for d, key, nombre in ETAPAS:
        if dias >= d:
            pendientes.append((d, key, nombre))
    return pendientes
