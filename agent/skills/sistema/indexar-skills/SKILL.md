---
name: indexar-skills
description: Usa al crear el índice semántico de ChromaDB a partir de los SKILL.md en agent/skills/. Lee cada SKILL.md, extrae frontmatter, genera embeddings y guarda en la colección.
---

# Indexar Skills - ChromaDB

## Cuándo usarlo
Cada vez que se añadan, modifiquen o eliminen SKILL.md en agent/skills/. Reindexar después de cada cambio.

## Pasos
1. Instalar chromadb: `pip install chromadb`
2. Variables de entorno: OPENAI_BASE_URL, OPENAI_API_KEY, EMBED_MODEL, CHROMA_PATH
3. Ejecutar:
   ```bash
   python scripts/indexar-skills.py
   ```
4. Verificar:
   ```bash
   python scripts/consultar-skills.py "plantilla de skill"
   ```

## Pitfalls
- Cambiar modelo de embeddings requiere reindexar completo.
- agent/skills/ vacío = 0 items indexados, nunca celebrar un "OK" sobre el vacío.

## Verificación
```bash
python scripts/indexar-skills.py  # debe imprimir X skill(s) indexados
```
