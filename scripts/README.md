# scripts/ — el motor

Scripts independientes: cada uno hace una cosa y se puede ejecutar suelto. Todos leen su configuración de variables de entorno.

## Búsqueda semántica

| Script | Qué hace |
|---|---|
| `indexar-skills.py` | Indexa todos los `SKILL.md` en ChromaDB (descripción + metadatos: hash, nombre, ruta). |
| `consultar-skills.py` | Búsqueda por significado. Devuelve los skills más relevantes con su score de similitud. |
| `router-jev.py` | Router en dos etapas: recupera del índice y decide si la tarea se resuelve directa o requiere delegación. |

## Sincronización y salud

| Script | Qué hace |
|---|---|
| `sync-skills.py` | Sincroniza repo ↔ instalación por hash. `--dry` para simular. |
| `doctor.py` | Chequeo de salud: repo, índice, crons, gateway, sincronización. `--json` para automatizar. |
| `test-doctor.py` | Testea al doctor inyectando fallos en un sandbox: un vigilante que no se vigila es teatro. |
| `test-cobertura.py` | Detecta skills en la instalación que no están en el repo (o al revés). |

## Ciclo de vida y aprendizaje

| Script | Qué hace |
|---|---|
| `explorar-stars.py` | Explora fuentes externas, destila candidatos a skill y actualiza el registro. |
| `skill-lifecycle.py` | Estados de un skill (activo, cuarentena, retirado) y transiciones. |
| `ebbinghaus-decay.py` | Decaimiento por olvido: prioriza qué revisar según cuándo se usó por última vez. |
| `skills-nunca-usados.py` | Poda: lista los skills que nunca se han recuperado. |

## Variables de entorno

```bash
OPENAI_BASE_URL    # endpoint compatible con OpenAI
OPENAI_API_KEY     # tu clave (solo en .env, nunca en el repo)
EMBED_MODEL        # modelo de embeddings para el índice
CHROMA_PATH        # ruta de la base vectorial (por defecto ~/.mastermind/chromadb)
GITHUB_TOKEN       # solo si usas el explorador de fuentes
```

## Uso típico

```bash
export OPENAI_BASE_URL="https://tu-proveedor.example/v1"
export OPENAI_API_KEY="..."
export EMBED_MODEL="tu-modelo-de-embeddings"

python scripts/indexar-skills.py
python scripts/consultar-skills.py "lo que necesito hacer"
python scripts/sync-skills.py --dry && python scripts/sync-skills.py
python scripts/doctor.py
```
