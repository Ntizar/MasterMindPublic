#!/usr/bin/env python3
"""
Indexador de skills en ChromaDB — Mastermind (Windows local).
Indexa todos los SKILL.md de agent/skills/ con embeddings de EMBED_MODEL (default tu-modelo-de-embeddings, tu proveedor API).

Uso:
  python scripts/indexar-skills.py            # indexa los nuevos
  python scripts/indexar-skills.py --reset    # borra colección y re-indexa todo
"""
import json
import os
import sys
import base64
import hashlib
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

# --- Config ---
REPO = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO / "agent" / "skills"
DB_PATH = Path(os.environ.get("CHROMA_PATH", Path.home() / ".mastermind" / "chromadb"))
COLLECTION = "mastermind-skills"
EMBED_MODEL = os.environ.get("EMBED_MODEL", "tu-modelo-de-embeddings")
THRESHOLD_DOC_CHARS = 30

def env_key(name):
    """Lee una key del .env de Hermes sin exponerla."""
    for p in [Path.home() / "AppData/Local/hermes/.env", REPO / ".env"]:
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith(f"{name}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get(name, "")

def embed(texts):
    """Embeddings via API OpenAI-compatible (tu proveedor)."""
    base = env_key("OPENAI_BASE_URL").rstrip("/")
    key = env_key("OPENAI_API_KEY")
    req = urllib.request.Request(
        f"{base}/embeddings",
        data=json.dumps({"model": EMBED_MODEL, "input": texts}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                 "User-Agent": "MastermindIndexer/2.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode())
    return [d["embedding"] for d in sorted(data["data"], key=lambda x: x["index"])]

def skill_docs():
    """Genera (id, texto_indexable, metadata) por cada SKILL.md."""
    for md in sorted(SKILLS_DIR.rglob("SKILL.md")):
        # ignorar backups del curator
        if any(part.startswith(".") for part in md.parts[len(SKILLS_DIR.parts):]):
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        name = md.parent.name
        rel = str(md.parent.relative_to(SKILLS_DIR)).replace("\\", "/")
        # texto indexable: frontmatter + primeras secciones
        body = text[:4000]
        digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]
        yield (f"skill:{rel}", f"{name}\n{body}", {"name": name, "path": rel, "hash": digest})

def main():
    import chromadb
    reset = "--reset" in sys.argv
    DB_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(DB_PATH))
    col = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    if reset:
        client.delete_collection(COLLECTION)
        col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
        print("Colección reiniciada")

    # Comparar por CONTENIDO (hash), no solo por ID: los SKILL.md parcheados
    # deben re-indexarse; el bug histórico era "id en existing → skip" eterno.
    stored = {}
    if col.count():
        got = col.get(include=["metadatas"])
        for i, m in zip(got["ids"], got["metadatas"] or [None] * len(got["ids"])):
            stored[i] = (m or {}).get("hash")
    docs = list(skill_docs())
    todo = [(i, t, m) for i, t, m in docs if stored.get(i) != m["hash"]]
    nuevos = sum(1 for i, _, _ in todo if i not in stored)
    total = len(docs)
    print(f"Skills encontrados: {total} | al día: {total - len(todo)} | a indexar: {len(todo)} "
          f"({nuevos} nuevos, {len(todo) - nuevos} modificados)")
    if not todo:
        print("Nada que indexar.")
        return

    BATCH = 12
    for start in range(0, len(todo), BATCH):
        chunk = todo[start:start + BATCH]
        texts = [t[:3000] for _, t, _ in chunk]
        embs = embed(texts)
        col.upsert(
            ids=[i for i, _, _ in chunk],
            documents=[t for _, t, _ in chunk],
            embeddings=embs,
            metadatas=[m for _, _, m in chunk],
        )
        print(f"  indexados {min(start + BATCH, len(todo))}/{len(todo)}")

    print(f"OK — colección '{COLLECTION}' con {col.count()} documentos en {DB_PATH}")

if __name__ == "__main__":
    main()
