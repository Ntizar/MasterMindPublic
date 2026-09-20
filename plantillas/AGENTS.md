# AGENTS.md — referencia rápida (plantilla)

Lo que cualquier agente debe saber al abrir este repo. Cópialo a la raíz de tu proyecto.

## Qué es este repo
Sistema de orquestación: orquestador + skills por dominio + memoria + aprendizaje continuo.

## Flujo de una tarea
1. Clasifica la tarea y decide el nivel de ejecución (1 directo → 4 orquestación).
2. Consulta los skills relevantes con búsqueda semántica (no por nombre).
3. Ejecuta o delega.
4. Verifica y reporta con evidencia.

## Búsqueda semántica (ChromaDB)
```bash
python scripts/consultar-skills.py "<consulta en lenguaje natural>"
```
Devuelve los skills más relevantes con score. Un score bajo = no hay skill para eso: resuélvelo y *escribe el skill*.

## Reglas rápidas
- Idioma único en el repo (el que uses tú).
- Secretos solo en `.env`; jamás en notas, commits o informes.
- No borrar sin lista exacta y aprobación.
- Notas nuevas → `notes/YYYY-MM-DD-titulo.md`.
- Skill nuevo → carpeta de skills + `scripts/sync-skills.py`.
- Antes de desplegar: verificación visual y `scripts/doctor.py`.

## Rutas
- Skills: `agent/skills/<dominio>/<skill>/SKILL.md`
- Memoria: `agent/MEMORY.md`, `agent/USER.md`
- Notas: `notes/`
- Config: `config.yaml` (una sola fuente para modelo y proveedor)
