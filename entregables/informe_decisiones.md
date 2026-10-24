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

**Formato común.** Cada tool devuelve un dict `{"status", "texto", ...}`. El `texto` es lo que lee el LLM y el
`status` (`ok`, `abstencion` o `error`) permite al grafo distinguir "no hay datos" de "ha fallado", algo que con
un texto suelto habría que deducir mirando el mensaje. `ejecutar_tool` es la única puerta de ejecución y devuelve
la entrada de traza `{tool, args, status, preview, resultado}`. Añade `blocked` cuando el nombre no está en
`TOOLS_PERMITIDAS` o no está en `permitidas` (las tools del especialista), y entonces no se ejecuta nada.
Nunca lanza excepciones.

**Cómo se enchufa el RAG.** `rag_ask` envuelve `rag.responder()` del PB1, que ya devolvía la respuesta, las fuentes
y la abstención sin lanzar excepciones. Si el RAG se abstiene, la tool devuelve `abstencion` y sin fuentes (para
que no se citen documentos que no respaldan la respuesta). El RAG se importa de forma diferida: el modelo de
embeddings (torch) solo se carga en la primera consulta, así los tests y el arranque no pagan ese coste.
Coste medido: entre 8 y 11 s por consulta, incluida la carga del modelo en la primera llamada, porque cada
`rag_ask` hace una recuperación local y una generación con Gemini.

**Evidencia in-corpus y abstención** (`rag_ask` con Gemini y el índice de 1714 chunks):

```
rag_ask('cuanto cuesta la entrada a la piscina de verano para adultos')
→ status ok · "La entrada para adultos cuesta 4,5 € (Fuente: 300083-10-deportes-tarifas.xlsx)."
rag_ask('cual es la capital de francia')
→ status abstencion · "No tengo información suficiente en los documentos para responder a esa pregunta." · sin fuentes
```

En la evaluación del PB1 (13 preguntas, 10 dentro del corpus y 3 fuera) el RAG respondía bien 4 de 10 con k=3 y
5 de 10 con k=5, sin respuestas inventadas: los fallos son de recuperación (el fragmento correcto queda en
posiciones bajas del ranking), no de generación. No hemos mejorado el retrieval en este proyecto (ver siguientes pasos).

**API externa (`api_deporte`).** Usa la agenda de actividades deportivas del Ayuntamiento (dataset 212504, JSON).
La elegimos frente a una agenda general de eventos porque es específica del dominio: da información viva
(qué actividades hay, dónde, qué días y si son gratuitas) que no está en el corpus estático. La tool descarta
las actividades ya terminadas, filtra por las palabras de la consulta y devuelve un resumen corto, no el JSON.
Si falla la red, usa una copia local (`data/fallback_api.json`, 20/10/2026) y lo indica en el texto:

```
api_deporte('ajedrez')
→ Fuente: api (datos.madrid.es) · Ajedrez en los parques: Jornadas 2026 · Jardines de Pablo Sorozábal (Chamartin) · viernes 16:30, del 10/04/2026 al 20/11/2026 · gratis
api_deporte('ciclismo')  # con la URL apuntando a una dirección inexistente
→ Fuente: local (copia del 20/10/2026) · Ciclismo por Madrid 2026-2027 · lugar por confirmar · todos los días, del 01/09/2026 al 30/06/2027 · de pago (precio no indicado)
```

**Allowlist demostrada.** Un nombre inventado (`borrar_todo`) y una tool existente fuera de la lista del
especialista (`hora_actual` con `permitidas=['rag_ask']`) devuelven `blocked` sin ejecutarse. Mientras
`api_deporte` no estuvo registrada, el grafo la dio como `blocked` (ver la ejecución real de la sección 2).
Los tests de `ejecutar_tool`, `hora_actual`, `rag_ask` y `api_deporte` no necesitan red ni clave: simulan
la red y el RAG con `monkeypatch`.

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

**Fallo 2 (María) · Gemini devuelve 503 y la tool no puede responder.**
- *Qué pasó:* durante las pruebas, Gemini devolvió con frecuencia `503 UNAVAILABLE` ("high demand") al
  llamar a `rag_ask` y a `describir_imagen`.
- *Qué hace el sistema:* la tool devuelve `status: error` con el motivo, sin lanzar excepciones y sin
  inventar datos. En el grafo, el especialista no recibe información y no se pide aprobar un plan vacío.
- *Causa:* picos de demanda del modelo gratuito; el error es externo y temporal, pero hoy no se reintenta.
- *Qué haríamos:* un reintento con espera corta ante 503, solo en errores temporales (no en clave inválida),
  manteniendo `error` si vuelve a fallar.

**Fallo 3 (Alex).** *Pendiente.*

## 6. Siguientes pasos (MLOps)

*Pendiente (todos).*
