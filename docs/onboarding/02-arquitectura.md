# 02 — Arquitectura

## Dos sitios, un sistema

| Dónde | Qué | Rol |
|-------|-----|-----|
| `~/Projects/MasterMind` (→ github.com/Ntizar/MasterMindPublic) | Repo completo | **Fuente de verdad** |
| `~/.hermes\` | Instalación Hermes: config.yaml, skills/, memories/ | **Ejecución** |

Los skills viven en AMBOS: la instalación local es la que Hermes carga; el repo es
la copia canónica que se sincroniza.

## Estructura del repo

```
MasterMind/
├── agent/          ← skills, memorias, identidad (SOUL.md, MEMORY.md, USER.md)
├── scripts/        ← motor: ChromaDB, stars-explorer, doctor, backup
├── notes/          ← notas de aprendizaje continuo (YYYY-MM-DD-titulo.md)
├── mastermind/     ← docs del sistema (este onboarding, patrones)
├── data/           ← stars-registry.json y datos de pipelines
├── index.html      ← web pública (GitHub Pages, consume tu-proyecto v6 vía CDN)
└── AGENTS.md / README.md / CHANGELOG.md
```

## Stack técnico

- **Hermes Agent (desktop, Windows)** — motor, memoria persistente, delegate_task, gateway, cron
- **GitHub** — fuente de verdad y backup
- **tu proveedor compatible con OpenAI** — modelos vía API OpenAI-compatible (los activos se configuran en `config.yaml`/`.env` vía `model.default` y `EMBED_MODEL`; nunca hardcodear modelos en el código)
- **ChromaDB** — base vectorial local (`~/.mastermind/chromadb`), búsqueda semántica de skills
