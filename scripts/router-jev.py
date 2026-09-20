#!/usr/bin/env python3
"""
Router System One (scaffold H4) — Mastermind.

Cabeza de ROUTING sobre ChromaDB (el "encoder" ya operativo): clasifica una
consulta en dominio+skills y decide ruta según confianza, ANTES de gastar
tokens del LLM orquestador.

  confianza alta  -> nivel 1 directo (ejecutar con skills sugeridos)
  confianza media -> delegar (nivel 2-3 con skills sugeridos)
  confianza baja  -> escalar al LLM orquestador (model.default de config.yaml)

FASE 2 (futura, sin tocar este flujo): cabeza de DECISION con Jev de TypeSafe
(typesafe-ai/jev via Vercel AI Gateway). Si existe JEV_API_KEY en .env, este
router la consultara como segunda opinion del gate; sin ella, solo ChromaDB.

Uso:
  python scripts/router-jev.py "convertir GTFS a NeTEx" [--json] [--k 5] [--alta 0.62] [--media 0.45]
"""
import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("CHROMA_PATH", Path.home() / ".mastermind" / "chromadb"))
COLLECTION = "mastermind-skills"
EMBED_MODEL = os.environ.get("EMBED_MODEL", "tu-modelo-de-embeddings")


def env_key(name: str) -> str:
    for p in [Path.home() / "AppData/Local/hermes/.env", REPO / ".env"]:
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith(f"{name}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get(name, "")


def embed(text: str) -> list:
    import urllib.request

    base = env_key("OPENAI_BASE_URL").rstrip("/")
    key = env_key("OPENAI_API_KEY")
    req = urllib.request.Request(
        f"{base}/embeddings",
        data=json.dumps({"model": EMBED_MODEL, "input": [text]}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                 "User-Agent": "MastermindRouter/0.1"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode())
    return data["data"][0]["embedding"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("consulta")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--alta", type=float, default=0.62)
    ap.add_argument("--media", type=float, default=0.45)
    args = ap.parse_args()

    import chromadb

    client = chromadb.PersistentClient(path=str(DB_PATH))
    col = client.get_collection(COLLECTION)
    res = col.query(query_embeddings=[embed(args.consulta)], n_results=min(args.k, col.count()))
    skills = [
        {"name": m.get("name"), "path": m.get("path"), "score": round(1 - d, 4)}
        for m, d in zip(res["metadatas"][0], res["distances"][0])
    ]
    top = skills[0]["score"] if skills else 0.0

    if top >= args.alta:
        decision, ruta = "ejecutar", "nivel-1 directo con los skills sugeridos"
    elif top >= args.media:
        decision, ruta = "delegar", "nivel 2-3 (delegate_task) con los skills sugeridos en el contexto"
    else:
        decision, ruta = "escalar", "sin dominio claro -> LLM orquestador (config model.default) decide"

    out = {
        "consulta": args.consulta,
        "decision": decision,
        "ruta": ruta,
        "confianza_top": top,
        "umbrales": {"alta": args.alta, "media": args.media},
        "cabeza_jev": "no-configurada (fase 2: JEV_API_KEY -> typesafe-ai/jev via Vercel AI Gateway)" if not env_key("JEV_API_KEY") else "configurada",
        "skills": skills,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2) if args.json else
          f"\n{top:>6.2f} [{decision.upper():<7}] {args.consulta}\n        {ruta}\n        " +
          "\n        ".join(f"{s['score']:.2f} {s['name']}" for s in skills))
    return 0


if __name__ == "__main__":
    sys.exit(main())
