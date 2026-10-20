# Informe de decisiones — Project Break 2

Agente multiagente con LangGraph sobre el deporte municipal de Madrid, a partir del RAG del PB1.

| Bloque | Responsable |
|---|---|
| Grafo + CLI | Davide |
| Tools + RAG | María |
| Interfaz + multimodal | Alex |

---

## 1. Diseño del grafo y especialistas (Davide)

**Nodos.** `supervisor` → `especialista_tarifas` / `especialista_instalaciones` → `sintetizar` → `aplicar`.
Los especialistas vuelven siempre al supervisor, que decide si hace falta otro o si ya se puede sintetizar.
Diagrama y reglas completas en `specs/grafo.md`.

**Por qué dos especialistas.** Separan dos tipos de información con fuentes y riesgos distintos:

| Especialista | Información | Tools permitidas |
|---|---|---|
| `especialista_tarifas` | Estable y oficial: tarifas, abonos, descuentos, normas, centros | `rag_ask`, `hora_actual` |
| `especialista_instalaciones` | Viva: agenda de actividades, imágenes adjuntas | `api_deporte`, `hora_actual`, `describir_imagen` |

**El LLM propone, Python decide.**
- El supervisor pregunta a Gemini el siguiente nodo; si la respuesta no está en la lista, o Gemini falla
  (sin clave, 503…), decide un fallback por palabras clave y el log indica el motivo.
- El especialista pregunta a Gemini *qué* tools usar, pero los argumentos los construye Python
  y se ejecutan con `ejecutar_tool(..., permitidas=...)`: una tool ajena o inventada queda `blocked`.
- Los límites (`MAX_ITER`, `MAX_STEPS`, `MAX_TURNS`) y `done` los decide siempre Python.

**Memoria.** `MemorySaver` + `thread_id`: los mensajes se acumulan por conversación y una pregunta corta
de seguimiento se completa con la anterior. "Nueva conversación" = `thread_id` nuevo.

**Sin datos, sin plan.** Si ninguna tool devuelve datos útiles (todo error o abstención), `sintetizar`
responde directamente y el grafo termina sin pedir aprobación: no tiene sentido aprobar un plan vacío.

## 2. Human-in-the-loop (Davide)

**Momento.** El grafo se compila con `interrupt_before=["aplicar"]`: se detiene después de redactar la
respuesta y el plan, y antes de cualquier efecto (guardar el plan en `salidas/`).
`aprobar_plan(thread_id, aprobado)` escribe la decisión con `update_state` y reanuda con `invoke(None)`.
Sin aprobación explícita, `aplicar` no tiene efecto.

**Ejecución real** (`python main.py --demo`, Gemini + RAG del PB1, 19/10/2026):

*Rechazo.* Pregunta: «¿Cuánto cuesta la entrada a la piscina de verano para adultos?»

```
supervisor → especialista_tarifas (llm, iter 1)
especialista_tarifas → tools ['rag_ask'] (llm)
supervisor → sintetizar (llm, iter 2)
sintetizar → plan con 3 viñetas (llm)
pausa HITL antes de aplicar
tool rag_ask   ok   La entrada para adultos cuesta 4,5 € (Fuente: 300083-10-deportes-tarifas.xlsx)
→ rechazar → aplicar → rechazado · pendiente_hitl=False · done=False
```

*Aprobación* (mismo `thread_id`). Pregunta: «¿Y qué actividades hay esta semana?»

```
supervisor → especialista_tarifas (fallback, iter 1)
especialista_tarifas → tools ['rag_ask', 'hora_actual'] (llm)
supervisor → especialista_instalaciones (llm, iter 2)
especialista_instalaciones → tools ['api_deporte', 'hora_actual'] (llm)
supervisor → sintetizar (llm, iter 3)
pausa HITL antes de aplicar
→ aprobar → aplicar → aprobado · plan guardado en salidas/ · done=True
```

En esa ejecución `api_deporte` aún no estaba en la allowlist y salió `blocked`, y el agente lo explicó en
la respuesta en vez de inventar actividades.

## 3. Tools y RAG (María)

*Pendiente.*

## 4. Multimodal y HITL en Streamlit (Alex)

*Pendiente.*

## 5. Tres fallos observados

**Fallo 1 (Davide) · La memoria une preguntas que no estaban relacionadas.**
- *Qué pasó:* tras preguntar el precio de la piscina, «¿Y qué actividades hay esta semana?» se unió a la
  pregunta anterior porque es corta (≤ 6 palabras). El RAG contestó a medias («4,5 €… no tengo información
  de actividades») y la tool lo marcó como `abstencion` aunque contenía un dato útil.
- *Causa:* la regla "pregunta corta = seguimiento de la anterior" es demasiado simple.
- *Qué hacemos:* queda documentado; la mejora es que el LLM reescriba la pregunta usando el historial, con
  la regla actual como fallback.

**Fallo 2 (María).** *Pendiente.*

**Fallo 3 (Alex).** *Pendiente.*

## 6. Siguientes pasos (MLOps)

*Pendiente (todos).*
