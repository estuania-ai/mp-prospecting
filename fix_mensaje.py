with open('rubros_config.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazar la funcion get_mensaje
old = '''def get_mensaje(rubro_key: str, nombre: str) -> str:
    """Genera el mensaje personalizado reemplazando [Nombre]"""
    rubro = RUBROS.get(rubro_key)
    if not rubro:
        # Fallback generico
        return (
            f"Hola {nombre}, soy Sebastian Pinto de Mercado Pago. "
            "Te contacto para contarte sobre nuestras soluciones de pago sin arriendo. "
            "Si tienes un tiempo esta semana, avisame para agendar una llamada o visita."
        )
    return rubro["mensaje"].replace("[Nombre]", nombre)'''

new = '''def get_mensaje(rubro_key: str, nombre: str, comuna: str = "") -> str:
    """Genera el mensaje universal con nombre y comuna del negocio"""
    comuna_txt = comuna if comuna and comuna != "Sin clasificar" else "tu sector"
    return (
        f"Hola {nombre}, soy Sebastian Pinto, vi tu negocio en {comuna_txt} "
        f"y creo que Mercado Pago puede ser una gran alternativa. "
        f"Mira, te dejo una imagen de referencia en lo que te podriamos aportar. "
        f"Avisame si te parece, y evaluamos en funcion de tu actual proveedor de pagos. Saludos"
    )'''

content = content.replace(old, new)

with open('rubros_config.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK - mensaje actualizado')