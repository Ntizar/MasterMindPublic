---
name: consultar-skills
description: Usa al buscar skills por significado en ChromaDB. Recibe una consulta natural y devuelve los skills más relevantes con su score de similitud y ruta al fichero SKILL.md.
---

# Consultar Skills — Búsqueda Semántica

## Cuándo usarlo
Cuando el orquestador necesita encontrar el skill correcto para una tarea, pero no sabe su nombre exacto. Se usa por significado, no por texto literal.

## Pasos
1. Asegurarse de que el índice existe: `python scripts/indexar-skills.py`
2. Ejecutar la consulta desde la raíz del repo:
   ```bash
   python scripts/consultar-skills.py "cómo convertir GTFS a NeTEx"
   ```
3. El script devuelve una lista ordenada por relevancia. El primer resultado es el más apropiado.

## Pitfalls
- **Índice desactualizado**: si se editó un SKILL.md y no se reindexó, la búsqueda devolverá la versión vieja. Reindexar después de cualquier cambio.
- **Consulta ambigua**: si la consulta no menciona ningún dominio, puede devolver skills genéricos. Ser específico: "GTFS", "sombras solares", "TTS clonado".
- **ChromaDB no instalado**: el script falla silenciosamente si chromadb no está en el path. Verificar con `pip install chromadb`.

## Verificación
```bash
python scripts/consultar-skills.py "skill de ejemplo"
# Debe devolver al menos ejemplo-basico y ejemplo-con-script
```
