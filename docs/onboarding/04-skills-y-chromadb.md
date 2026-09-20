# 04 — Skills y ChromaDB

## Búsqueda semántica, no por nombre

Los skills se consultan por SIGNIFICADO con ChromaDB (colección `mastermind-skills`,
embeddings vía `EMBED_MODEL` — el modelo y su dimensión los fija la config, no el código; threshold score > 0.25):

```bash
~/AppData/Local/Programs/Python/Python312/python.exe scripts/consultar-skills.py "consulta" --json
```

**PITFALL**: el `python` del PATH es el venv de Hermes y NO tiene chromadb.
Usar SIEMPRE el Python del sistema de la ruta anterior.

**PITFALL**: toda petición urllib/requests a `tu-proveedor.example` sin header
`User-Agent` custom devuelve 403 (curl sí funciona sin él).

Tras crear o modificar skills: `python scripts/indexar-skills.py` (con el Python
del sistema) para que la búsqueda semántica los vea.

## Memoria por especialista

Los skills con estado acumulativo mantienen memoria de dominio comiteada en el repo:
`agent/skills/<dominio>/<skill>/references/estado-<tema>.md`. Ver
`mastermind/memoria-especialistas.md` y la plantilla en
`agent/skills/mastermind/templates/estado-especialista.md`.

La memoria del orquestador (memories/ de Hermes) es global y del usuario; la del
especialista es de dominio y viaja con el skill. No duplicar entre ambas.

## Ciclo de vida

Skills nuevos entran por dos vías: trabajo directo de Mastermind o el scout nocturno
de stars (`scripts/run-stars-explorer.sh`), que propone skills desde los stars de
GitHub con criterio v2 (los pitfalls de un repo son contenido válido del skill).
