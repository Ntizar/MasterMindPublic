# Guía completa — monta tu MasterMind desde cero

De cero a un sistema multi-agente con memoria y aprendizaje propio. Tiempo estimado: 2-4 horas la primera vez (la mayor parte es decidir tus dominios).

---

## 0. Requisitos

| Necesitas | Notas |
|---|---|
| **Hermes Agent** instalado y funcionando | Es el motor: ejecuta el agente, las tools, el cron y la gateway. |
| **Python 3.11+** | Para los scripts del motor (indexado, búsqueda, doctor). |
| **git** + una cuenta de GitHub | El repositorio es la fuente de verdad y el backup de la memoria. |
| **Una API compatible con OpenAI** | Cualquier proveedor vale. Necesitas: `base_url`, `api_key` y un modelo de chat + uno de embeddings. |
| ChromaDB (se instala con pip) | Búsqueda semántica de skills. |

---

## 1. Estructura que vas a construir

```
MasterMind/
├── agent/
│   ├── skills/          ← tus skills, uno por dominio (SKILL.md)
│   ├── MEMORY.md        ← notas del sistema (lo que el agente debe recordar siempre)
│   └── USER.md          ← quién eres y cómo te gusta trabajar
├── scripts/             ← motor: indexar, consultar, sync, doctor, router
├── notes/               ← aprendizajes fechados
├── config.yaml          ← una sola fuente para modelo/proveedor
└── .github/workflows/   ← cron y despliegue
```

No la inventes a medias: cópiala tal cual y ve llenándola.

---

## 2. Instala el motor Hermes

1. Instala Hermes Agent siguiendo su documentación oficial.
2. Copia las plantillas de este repo a tu instalación:

```bash
cp plantillas/SOUL.md  ~/.hermes/SOUL.md          # identidad del sistema
cp plantillas/AGENTS.md ~/Projects/MasterMind/AGENTS.md
cp plantillas/MEMORY.md ~/Projects/MasterMind/agent/MEMORY.md
cp plantillas/USER.md   ~/Projects/MasterMind/agent/USER.md
cp plantillas/config.yaml ~/.hermes/config.yaml   # ¡edita proveedor y modelo!
```

3. Crea tu `.env` con los secretos (**nunca** lo subas al repo):

```bash
cp plantillas/.env.example ~/.hermes/.env
# y rellena: OPENAI_API_KEY, OPENAI_BASE_URL, TELEGRAM_BOT_TOKEN...
```

---

## 3. Personaliza la identidad (30 min, es lo que más renta)

Abre `SOUL.md` y responde por escrito:

- **¿Quién es tu orquestador?** Nombre, propósito, tono. Sin esto, cada sesión empieza de cero.
- **¿Qué stack usa?** Motor, repositorio, proveedor de modelos, base vectorial.
- **¿Cuáles son sus reglas?** Las 12 de `docs/FILOSOFIA.md` son un buen punto de partida: quítales lo que no te represente y añade lo tuyo.
- **¿Cuándo debe parar y preguntarte?** Define aquí los cambios críticos que exigen aprobación.

Escribe `USER.md` con quién eres: preferencias, estilo, proyectos en curso, límites. Cuanto más concreto, menos tendrás que repetirte.

> Regla de oro: si te descubres repitiendo una instrucción por tercera vez, no es una instrucción — es una línea que falta en `USER.md` o `SOUL.md`.

---

## 4. Crea tus primeros skills

Empieza con **5-10 skills de tus dominios reales**, no con 200. Mira `ejemplos/skills/` y `docs/FORMATO-SKILLS.md`.

```bash
mkdir -p agent/skills/mi-dominio/mi-skill
$EDITOR agent/skills/mi-dominio/mi-skill/SKILL.md
```

Un buen skill tiene: trigger claro en la descripción, pasos numerados con **comandos exactos**, pitfalls que ya te has comido, y una sección de verificación. Un skill sin verificación es una opinión.

---

## 5. Indexa y activa la búsqueda semántica

```bash
pip install chromadb

export OPENAI_BASE_URL="https://tu-proveedor.example/v1"
export OPENAI_API_KEY="..."
export EMBED_MODEL="tu-modelo-de-embeddings"

python scripts/indexar-skills.py          # indexa todos los SKILL.md en ChromaDB
python scripts/consultar-skills.py "mapas 3D"   # prueba la recuperación por significado
```

La primera vez guarda **el modelo de embeddings que uses**: si lo cambias después, hay que reindexar.

---

## 6. Sincroniza repo ↔ instalación

Los skills viven en dos sitios: tu repo (fuente de verdad) y la carpeta que carga el motor. El script los compara por hash y copia lo que falte:

```bash
python scripts/sync-skills.py --dry   # ver qué cambiaría
python scripts/sync-skills.py         # aplicarlo
```

---

## 7. Automatiza: cron y aprendizaje

Tres automatizaciones que cambian el juego:

| Cron | Cuándo | Qué hace |
|---|---|---|
| **Doctor** | diario | Comprueba repo, índice, crons y gateway. Te avisa si algo se desvía. |
| **Aprendizaje** | cada 6 h | Explora fuentes, destila skills candidatos, sincroniza y hace commit. |
| **Digest** | diario | Resumen de la jornada a `notes/` — la mañana empieza leyendo, no re-explicando. |

Configúralos en el cron de tu motor. Empieza con el doctor: un sistema que no se vigila a sí mismo se degrada en semanas.

---

## 8. Secretos y seguridad (no te lo salte)

- **Nunca** un secreto en el repo, en las notas ni en el chat. Solo en `.env`.
- Si tu repo va a ser público, **excluye** `agent/`, tu memoria personal y cualquier `.env`. GitHub Pages publica lo que le digas: revisa qué ruta sube.
- Añade al `.gitignore` el estado de máquina: locks, logs, cachés, `*.usage.json`.
- Antes de publicar, pasa un escáner (`grep -rE 'sk-[A-Za-z0-9]{24,}|ghp_'`) sobre el árbol.

---

## 9. Verifica que el sistema está sano

```bash
python scripts/doctor.py            # informe legible
python scripts/doctor.py --json     # para automatizar
python scripts/test-doctor.py       # el doctor también se testea (inyección de fallos)
python scripts/skills-nunca-usados.py   # poda: skills que nunca se recuperan
```

---

## 10. Reposición desde cero

El escenario que casi nadie prepara: *se rompe todo, ¿cómo lo levanto?* La respuesta está en `docs/onboarding/06-recuperacion-desde-cero.md`: ritual concreto de reinstalación usando el repo como única fuente. Léelo hoy, no el día que lo necesites.

---

## Errores de novato (los que ya se han cometido aquí)

1. **Duplicar la configuración.** Dos `config.yaml` que divergen en silencio → comportamiento distinto según quién lo lea. Una fuente por tema.
2. **Documentar lo que no existe.** Un README que promete estados, permisos o presupuestos que no están implementados. La documentación aspiracional envenena el sistema.
3. **Contar cosas que cambian.** Números de skills, de notas, de commits: envejecen el mismo día que los escribes. Describe capacidades, no cifras.
4. **Dejar que el aprendizaje-automático escriba sin puerta.** Todo lo que entra automático necesita revisión o cuarentena.
5. **Confundir el backup con la verdad.** Sin push, tu memoria vive en un solo disco.
