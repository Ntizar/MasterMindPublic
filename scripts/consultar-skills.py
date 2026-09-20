#!/usr/bin/env python3
"""
Consulta semántica de skills en ChromaDB — Mastermind (Windows local).

Uso:
  python scripts/consultar-skills.py "como hago un backup de skills" --json
  python scripts/consultar-skills.py "gtfs transporte" --n 10
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("CHROMA_PATH", Path.home() / ".mastermind" / "chromadb"))
COLLECTION = "mastermind-skills"
EMBED_MODEL = os.environ.get("EMBED_MODEL", "tu-modelo-de-embeddings")
DEFAULT_N = 8
THRESHOLD = 0.25  # distancia coseno máxima

def env_key(name):
    for p in [Path.home() / "AppData/Local/hermes/.env", REPO / ".env"]:
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith(f"{name}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get(name, "")

def embed(text):
    base = env_key("OPENAI_BASE_URL").rstrip("/")
    key = env_key("OPENAI_API_KEY")
    import urllib.request
    req = urllib.request.Request(
        f"{base}/embeddings",
        data=json.dumps({"model": EMBED_MODEL, "input": [text]}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                 "User-Agent": "MastermindIndexer/2.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode())
    return data["data"][0]["embedding"]

def main():
    if len(sys.argv) < 2:
        print("Uso: consultar-skills.py \"consulta\" [--json] [--n N]")
        sys.exit(1)
    query = sys.argv[1]
    as_json = "--json" in sys.argv
    n = DEFAULT_N
    if "--n" in sys.argv:
        n = int(sys.argv[sys.argv.index("--n") + 1])

    import chromadb
    client = chromadb.PersistentClient(path=str(DB_PATH))
    try:
        col = client.get_collection(COLLECTION)
    except Exception:
        msg = {"error": f"Colección '{COLLECTION}' no existe. Ejecuta indexar-skills.py primero."}
        print(json.dumps(msg, ensure_ascii=False) if as_json else msg["error"])
        sys.exit(2)

    res = col.query(query_embeddings=[embed(query)], n_results=min(n, col.count()))
    out = []
    for i, (id_, dist) in enumerate(zip(res["ids"][0], res["distances"][0])):
        meta = res["metadatas"][0][i]
        out.append({
            "name": meta.get("name"),
            "path": meta.get("path"),
            "distance": round(dist, 4),
            "score": round(1 - dist, 4),
            "relevant": dist <= (1 - THRESHOLD),
        })
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"Consulta: {query}\n")
        for o in out:
            flag = "✓" if o["relevant"] else " "
            print(f"{flag} {o['score']:>6.2f}  {o['name']:<40} {o['path']}")

if __name__ == "__main__":
    main()
