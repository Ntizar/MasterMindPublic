# Arquitectura

## Vista general

```
                      ┌──────────────────────────────────┐
   chat / cron ──────►│   ORQUESTADOR (agente principal) │
                      │  clasifica → decide nivel 1-4    │
                      └──────────┬───────────────────────┘
                                 │ delegate_task / tool calls
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
  ┌───────────┐           ┌────────────┐          ┌─────────────┐
  │  SKILLS   │           │  MEMORIA   │          │   CRONS     │
  │ por domi- │◄─────────►│ MEMORY/USER│          │ aprendizaje │
  │ nio (.md) │  búsqueda │ notes/     │          │ doctor      │
  └─────┬─────┘  semántica└────────────┘          └──────┬──────┘
        │                                                │
        ▼                                                ▼
  ┌───────────┐                                   ┌─────────────┐
  │ ChromaDB  │  indexa descripciones             │  GitHub     │
  │ local     │  (embeddings configurables)       │  (fuente de │
  └───────────┘                                   │   verdad)   │
                                                  └─────────────┘
```

## Los cuatro niveles de ejecución

El orquestador no lanza agentes a lo loco: clasifica la tarea y elige el coste adecuado.

| Nivel | Tool calls | Archivos | Patrón | Ejemplo |
|-------|-----------|----------|--------|---------|
| **1 — Directo** | 1-3 | 1-2 | El orquestador solo | Buscar, leer, commit |
| **2 — Simple** | 4-8 | 3-5 | 1 delegación | Refactor de un módulo |
| **3 — Paralelo** | 8+ | 5+ | 2-3 delegaciones | Frontend + backend + tests |
| **4 — Orquestación** | Proyecto completo | Multi-PR | Planner → implementers → reviewer | Feature completa |

## Por qué skills y no "un agente que lo sabe todo"

Un agente monolítico con 500 dominios en el prompt pierde precisión y quema contexto. Con skills:

- **Recuperación por significado**: ChromaDB guarda la descripción de cada skill; ante una petición se buscan los 3-5 más relevantes por similitud semántica (coseno) y solo esos se cargan.
- **Conocimiento procedimental exacto**: cada skill lleva comandos literales, rutas, pitfall y verificación. No "cómo se hace en general", sino *cómo se hace aquí*.
- **Crecimiento sin entropía**: un skill nuevo no degrada a los demás; entra indexado, se revisa y, si no se usa nunca, se detecta y se retira.

## El ciclo de aprendizaje

```
  fuentes externas            destilación               verificación
  (repos, docs, feeds)  ──►  skill candidato  ──►  indexado + doctor  ──► commit
        ▲                                                                │
        └──────────────── registro de lo aprendido ◄─────────────────────┘
```

Puntos clave de diseño:

- **Todo pasa por git**: la fuente de verdad es markdown plano en un repositorio. Sin base de datos propietaria, sin lock-in.
- **Evidencia antes que promesa**: cada skill o cambio deja rastro (qué se leyó, qué se decidió, qué se verificó).
- **El doctor vigila**: comprueba salud del repo, del índice, de los crons y de la sincronización. Si algo se desvía, avisa.
- **Un tema, una fuente**: sin duplicar información entre documentos. La duplicación es la semilla de la mentira documental.

## Memoria: cuatro capas

| Capa | Dónde | Para qué |
|---|---|---|
| Notas del sistema | `MEMORY.md` | Rutas, quirks de herramientas, convenciones, lecciones |
| Perfil del usuario | `USER.md` | Quién eres, preferencias, estilo |
| Aprendizajes | `notes/YYYY-MM-DD-*.md` | Reflexiones fechadas, decisiones, descubrimientos |
| Historial | base de sesiones | Búsqueda en conversaciones pasadas antes de preguntar |

## Multi-modelo desde el diseño

El sistema **no está casado con un proveedor**: todos los scripts leen modelo, endpoint y clave de variables de entorno, y el modelo por defecto vive en un único fichero de configuración. Cambiar de proveedor es cambiar una línea (o ninguna: el modelo puede heredarse del config del motor).
