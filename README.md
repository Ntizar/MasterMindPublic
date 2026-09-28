# MasterMind

**Un sistema de orquestación multi-agente.** Un orquestador, cientos de skills especializados por dominio, memoria persistente entre sesiones.

Este repositorio es la **versión pública y clonable**: explica cómo funciona el sistema y te da todo lo necesario para montar el tuyo. No es un framework — es una arquitectura, un conjunto de scripts y unas convenciones que llevan meses funcionando a diario.

> 🔗 **Landing explicativa:** https://ntizar.github.io/MasterMindPublic/
> 📖 **Guía paso a paso:** [docs/GUIA-COMPLETA.md](docs/GUIA-COMPLETA.md)

> Hecho con ❤️ por David Antizar

---

## La idea en una frase

En lugar de un chatbot gigante que lo sabe todo a medias, tienes **un orquestador que clasifica y delega** + **skills especializados que ejecutan**. El orquestador no necesita saber de faros, de GTFS ni de sombras solares: necesita saber *a quién* llamar. Ese reparto es lo que hace que el sistema escale sin que el contexto se desborde.

## Cómo funciona (5 piezas)

| Pieza | Qué hace |
|---|---|
| **Orquestador** | Clasifica la tarea, decide el nivel de ejecución (1 directo → 4 orquestación) y delega. No lo sabe todo: sabe a quién llamar. |
| **Skills** | Ficheros `SKILL.md` por dominio con procedimientos, comandos exactos y pitfalls. Son la memoria procedimental del sistema. |
| **Búsqueda semántica** | ChromaDB indexa las descripciones de los skills: el agente encuentra el skill correcto *por significado*, no por nombre. |
| **Memoria** | `MEMORY.md` (notas del sistema) + `USER.md` (quién eres) + `notes/` (aprendizajes) + búsqueda en el historial de sesiones, todo versionado en git. |
| **Ciclo de aprendizaje** | Un script explora fuentes y registra candidatos a nuevos skills. Los destila, revisa y publica es trabajo manual (ver `docs/ARQUITECTURA.md`). |

## Quickstart

```bash
# 1. Clona
git clone https://github.com/Ntizar/MasterMindPublic.git
cd MasterMindPublic

# 2. Instala dependencias
pip install -r requirements.txt

# 3. Ejecuta la demo (sin API key, sin configuración)
python scripts/demo.py
```

La demo muestra indexación de skills, recuperación por significado y routing con receipt. Todo funciona en un clon limpio en menos de un minuto.

Para configurar tu agente real, sigue [docs/GUIA-COMPLETA.md](docs/GUIA-COMPLETA.md).

## Qué hace cada script

| Script | Qué hace |
|---|---|
| `demo.py` | Demo completa: indexación, recuperación y routing (sin API key) |
| `indexar-skills.py` | Indexa SKILL.md en ChromaDB con embeddings |
| `consultar-skills.py` | Busca skills por significado en ChromaDB |
| `router-jev.py` | Routing: clasifica consulta y decide ruta (ejecutar/delegar/escalar) |
| `sync-skills.py` | Sincroniza skills del repo → agente (un solo sentido) |
| `doctor.py` | Health check del sistema completo |
| `test-doctor.py` | Tests que inyectan bugs y verifican que el doctor los detecta |
| `skill-lifecycle.py` | Análisis de uso de skills (git log + notas) |
| `explorar-stars.py` | Explora repos stars y registra candidatos a nuevos skills |

## Estructura del repo

```
agent/
  skills/                  ← skills reales del sistema (copialos a ~/.hermes/skills/)
    sistema/               ← skills del sistema (indexar, consultar)
    utilidades/            ← utilidades generales
plantillas/                ← SOUL.md, config.yaml, etc. para tu instalacion
scripts/                   ← motor: indexacion, busqueda, sync, doctor, router
docs/                      ← guia completa, arquitectura, filosofia
ejemplos/skills/           ← ejemplos de formato de skill
```

## Licencia

MIT — usalo, modificalo, móntate el tuyo. Si te sirve, cuéntalo.

Hecho con ❤️ por **David Antizar**.