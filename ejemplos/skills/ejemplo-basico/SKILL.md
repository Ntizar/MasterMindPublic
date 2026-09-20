---
name: ejemplo-basico
description: Usa cuando necesites la plantilla mínima de un skill. Muestra frontmatter, pasos, pitfalls y verificación.
---

# Ejemplo: skill mínimo

## Cuándo usarlo
Como esqueleto al crear un skill nuevo. Sustituye el contenido por tu dominio real.

## Pasos
1. Copia este fichero a `agent/skills/<dominio>/<nombre-skill>/SKILL.md`.
2. Reescribe `name` y `description` (la descripción empieza por el trigger).
3. Escribe los pasos con **comandos literales**, copiables y verificables.
4. Añade los pitfalls que ya te has comido, con el mensaje de error exacto.
5. Reindexa: `python scripts/indexar-skills.py`.
6. Sincroniza: `python scripts/sync-skills.py`.

## Pitfalls
- **Descripción genérica** («ayuda con X»): el buscador semántico no lo recuperará nunca. Empieza por «Usa cuando…».
- **Pasos sin comando**: se convierten en interpretación libre del modelo.
- **Sin verificación**: no puedes saber si funcionó.

## Verificación
```bash
python scripts/consultar-skills.py "plantilla mínima de un skill"
# Debe aparecer este skill entre los primeros resultados.
```
