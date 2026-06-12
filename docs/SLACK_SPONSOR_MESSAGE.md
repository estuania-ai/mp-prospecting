# Mensaje Slack · Solicitud de sponsor Engineering para migración a Fury

> Listo para copiar/pegar en Slack. Pensado para enviar a un Tech Lead / Engineering Manager del área comercial o de plataformas.
> Tono: cercano, claro, sin pedir demasiado en el primer mensaje.

---

## Versión 1 · Para Tech Lead del área comercial (más cercana)

```
Hola [NOMBRE], ¿cómo estás?

Te escribo porque vengo trabajando en una herramienta interna de
prospección para el equipo Sales POS de MP Chile (lo uso yo y la
idea es escalarla al equipo). Hoy corre en Railway (externo) y
necesito migrarla a Fury para que cumpla con las políticas de
seguridad y datos de MELI.

Para crear el namespace y avanzar formalmente necesito un sponsor
de Engineering · ¿podríamos conversar 20 min cuando tengas un
hueco? Te llevo un brief de 1 página con el estado del proyecto,
la categorización Fury propuesta (Tier 2 · PII no financiera) y
el roadmap de migración.

Quedo atento, sin apuro.

Saludos!
Juan
```

---

## Versión 2 · Para alguien que no te conoce (más formal)

```
Hola [NOMBRE], buenas tardes.

Soy Juan Sebastián Pinto, Sales Executive de MercadoPago Chile.
Vengo trabajando en una herramienta interna de prospección
comercial llamada "MP Prospecting System" — opera como capa previa
a Fast (no lo reemplaza), automatizando captura de leads desde
fuentes públicas y seguimiento comercial.

Hoy está desplegada en Railway (infra externa) y la quiero migrar
a Fury para alinearla con las políticas corporativas de PII y
seguridad. Para abrir el namespace necesito el sponsor de un Tech
Lead / Engineering Manager.

Tengo un brief ejecutivo de 1 página con:
· Categorización Fury (Tier 2 · PII no financiera · audiencia
  interna solamente)
· Frameworks regulatorios aplicables (Ley 19.628 / 21.719 CL,
  políticas MELI)
· DPA status de procesadores terceros
· Top 5 gaps de compliance + plan de remediación
· Roadmap de migración en 4 fases (~8 semanas)

¿Tenés 20 minutos esta semana o la próxima para que te lo cuente
y vemos si tiene sentido que apadrines? Si no es tu área pero sabés
quién podría serlo, también me orienta mucho.

Quedo atento.

Saludos cordiales,
Juan Sebastián Pinto
juansebastian.pinto@mercadolibre.cl
```

---

## Versión 3 · Si querés mandarlo en un canal abierto (#tech-help o similar)

```
👋 Hola equipo!

Soy Juan Sebastián, Sales Executive de MP Chile. Vengo armando una
herramienta interna de prospección comercial (capa previa a Fast,
no lo reemplaza) que hoy corre en Railway y quiero migrar a Fury
para cumplir las políticas corporativas.

🧭 ¿A quién le pediría sponsor de Engineering para abrir el
namespace? La categorización es Tier 2 · PII no financiera · solo
usuarios internos. Tengo brief ejecutivo de 1 página listo.

Cualquier orientación se agradece 🙏
```

---

## Tips para mandar el mensaje

### Antes de enviar
- [ ] Adjuntar el brief ejecutivo `FURY_EXECUTIVE_BRIEF.md` (1 página) · NO el ARCHITECTURE.md completo (intimida)
- [ ] Si conocés a la persona, usar Versión 1
- [ ] Si no la conocés, Versión 2
- [ ] Si no sabés a quién apuntar, Versión 3 en canal abierto

### Mejores momentos para enviar
- Martes a jueves, 10-12am o 2-4pm
- Evitar lunes temprano y viernes tarde
- Evitar viernes con bloqueos por release

### Si responden interesado
Coordinar 20 min de call · llevar el brief en pantalla · objetivos
del call:
1. Explicar qué hace el proyecto en 5 min
2. Mostrar categorización Tier 2 y por qué
3. Decir lo que pedís: sponsor para abrir namespace en Fury
4. Aclarar que la implementación la hacés vos, no le pedís horas
   técnicas a su equipo
5. Cerrar con próximos pasos concretos (ej: "te mando link
   Fury cuando esté listo para que apruebes")

### Si te derivan a otra persona
Genial · pedile que te haga la presentación por Slack o mail
(*"¿podrías presentarme a [persona] con dos líneas de contexto?"*)
para no llegar frío al siguiente contacto.

### Si te dicen "no es mi área pero hablá con X"
Anotá a X y pedí intro. No insistas con el primer contacto.

### Si te dicen "ahora no puedo"
Respondé corto y dejá la puerta abierta: *"genial, cuando se
acomode me avisás. Mientras tanto sigo el camino institucional"*.

---

## Documentos para tener a mano cuando respondan

| Doc | Cuándo usarlo |
|---|---|
| `docs/FURY_EXECUTIVE_BRIEF.md` | Adjuntar al primer Slack o mail · 1 página |
| `docs/ARCHITECTURE.md` | Si piden detalle técnico · referenciás sin enviarlo entero |
| `docs/STATUS.md` | Si preguntan por el estado actual del sistema |
| `docs/YAMM_SETUP.md` | Si preguntan específicamente sobre el flujo email |

---

*Última actualización: 2026-06-12*
