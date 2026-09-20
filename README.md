# MasterMind

**Un sistema de orquestación multi-agente que aprende solo.** Un orquestador, cientos de skills especializados por dominio, memoria persistente entre sesiones y un pipeline nocturno que descubre, destila y publica conocimiento nuevo mientras duermes.

Este repositorio es la **versión pública y clonable**: explica cómo funciona el sistema y te da todo lo necesario para montar el tuyo. No es un framework — es una arquitectura, un conjunto de scripts y unas convenciones que llevan meses funcionando a diario.

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
| **Ciclo de aprendizaje** | Un cron explora fuentes, destila skills nuevos, sincroniza la instalación y hace commit. El sistema crece sin que lo toques. |

## Quickstart

```bash
# 1. Clona
git clone https://github.com/Ntizar/MasterMindPublic.git
cd MasterMindPublic

# 2. Lee la guía completa
docs/GUIA-COMPLETA.md

# 3. Copia las plantillas a tu instalación de Hermes y configura tu proveedor
cp plantillas/SOUL.md ~/.hermes/SOUL.md
cp plantillas/config.yaml ~/.hermes/config.yaml
```

Requisitos: **Hermes Agent** (el motor de ejecución), Python 3.11+, `git`, y una API compatible con OpenAI (cualquiera sirve — el sistema no está casado con ningún proveedor).

## Qué hay aquí

```
docs/
  GUIA-COMPLETA.md      ← empieza por aquí: monta el sistema paso a paso
  ARQUITECTURA.md       ← cómo encajan orquestador, skills, ChromaDB y cron
  FILOSOFIA.md          ← las reglas que mantienen el sistema honesto
  FORMATO-SKILLS.md     ← cómo se escribe un SKILL.md (y por qué importa)
  onboarding/           ← manual de operación diaria, reposición desde cero
plantillas/
  SOUL.md AGENTS.md MEMORY.md USER.md config.yaml .env.example
scripts/                ← motor: indexado, búsqueda, sync, doctor, router, aprendizaje
ejemplos/skills/        ← dos skills de ejemplo con el formato real
index.html              ← landing explicativa (servida en GitHub Pages)
```

## Por qué esto funciona

1. **Contexto acotado**: solo se cargan los skills del dominio relevante. El resto no ocupa ventana.
2. **Conocimiento versionado**: los skills son markdown en git — diffeables, revisables, portables. Sin magia propietaria.
3. **Aprendizaje con evidencia**: cada skill nuevo entra con su fuente y su registro; el `doctor` vigila que el sistema no se rompa en silencio.
4. **El sistema se explica a sí mismo**: la documentación no promete lo que el código no hace.

## Licencia

MIT — úsalo, modifícalo, móntate el tuyo. Si te sirve, cuéntalo.

Hecho con ❤️ por **David Antizar**.
