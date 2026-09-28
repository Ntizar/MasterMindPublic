#!/usr/bin/env python3
"""
Router System One — Mastermind (DEMO / SCALFFOLD).

FASE 1 — DEMO: este script calcula la decision de routing (ejecutar/delegar/escalar)
usando similaridad de tokens sobre la lista de SKILL.md en agent/skills/.
**NO invoca ninguna API de ChromaDB ni de Jev.** Solo imprime la decision
y el receipt.

FASE 2 (futuro): se conectara a ChromaDB para usar embeddings reales y,
opcionalemte, a Jev (typesafe-ai/jev via Vercel AI Gateway) como segunda
opinion.

Queda por implementar:
  1. [ ] Lectura de ChromaDB (chromadb.PersistentClient + collection.query)
  2. [ ] Generacion de embeddings (OpenAI-compatible /v1/embeddings)
  3. [ ] Invocacion de Jev si JEV_API_KEY esta configurada
  4. [ ] Ejecucion del handler de skill seleccionado (subprocess.run)

Uso:
  python scripts/router-jev.py "convertir GTFS a NeTEx" [--json] [--k 5] [--alta 0.62] [--media 0.45]

NOTA: en modo demo (sin ChromaDB), los scores se calculan con similaridad
de tokens sobre el contenido de los SKILL.md. No esperes scores altos como
con embeddings reales.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path


def repo_root():
    """Devuelve la raiz del repo git."""
    try:
        import subprocess
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5, cwd="."
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except (subprocess.TimeoutExpired, OSError):
        pass
    return Path.cwd().resolve()


REPO = repo_root()
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


def tokenize(text):
    """Tokenizar: quitar puntuacion, minusculas, ignorar tokens < 2 chars."""
    return [t for t in re.sub(r'[^\w\s]', ' ', text.lower()).split() if len(t) >= 2]


def simple_similarity(query, text):
    """Similaridad de tokens (modo demo sin ChromaDB)."""
    q_tokens = set(tokenize(query))
    if not q_tokens:
        return 0.0
    t_tokens = set(tokenize(text))
    if not t_tokens:
        return 0.0
    overlap = len(q_tokens & t_tokens) / len(q_tokens)
    return overlap


def has_chromadb():
    """Comprueba si ChromaDB existe y tiene datos."""
    import shutil
    py = shutil.which("python") or shutil.which("python3")
    if not py:
        return False
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(DB_PATH))
        col = client.get_collection(COLLECTION)
        return col.count() > 0
    except Exception:
        return False


def chromadb_query(query, k=5):
    """Consulta ChromaDB con embeddings reales."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(DB_PATH))
        col = client.get_collection(COLLECTION)

        # Obtener embedding via API OpenAI-compatible
        base = env_key("OPENAI_BASE_URL").rstrip("/")
        key = env_key("OPENAI_API_KEY")
        import urllib.request
        req = urllib.request.Request(
            f"{base}/embeddings",
            data=json.dumps({"model": EMBED_MODEL, "input": [query]}).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                     "User-Agent": "MastermindRouter/1.0"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
        embedding = data["data"][0]["embedding"]

        res = col.query(
            query_embeddings=[embedding],
            n_results=min(k, col.count())
        )
        skills = []
        for m, d in zip(res["metadatas"][0], res["distances"][0]):
            name = m.get("name", "?") if m else "?"
            path = m.get("path", "?") if m else "?"
            score = round(1 - d, 4)
            skills.append({"name": name, "path": path, "score": score})
        return sorted(skills, key=lambda s: s["score"], reverse=True)
    except Exception as e:
        print(f"  ⚠️  ChromaDB query failed: {e}", file=sys.stderr)
        return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Router H4: clasifica consulta y decide ruta (demo token-based sin ChromaDB).",
        epilog="Modo demo: sin ChromaDB/Embeddings, usa similaridad de tokens sobre SKILL.md"
    )
    ap.add_argument("consulta")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--alta", type=float, default=0.62)
    ap.add_argument("--media", type=float, default=0.45)
    args = ap.parse_args()

    # ── Determinar modo ──────────────────────────────────────────
    chromadb_ok = has_chromadb()
    mode = "REAL (ChromaDB + embeddings)" if chromadb_ok else "DEMO (tokens sobre SKILL.md)"

    # ── Consultar ────────────────────────────────────────────────
    if chromadb_ok:
        print("ℹ️  ChromaDB activo — usando embeddings reales.")
        skills = chromadb_query(args.consulta, args.k)
    else:
        # Modo demo: similaridad de tokens sobre todos los SKILL.md
        print("ℹ️  ChromaDB no disponible — usando similaridad de tokens (DEMO).")
        skills_data = []
        for md in sorted((REPO / "agent" / "skills").rglob("SKILL.md")):
            if any(part.startswith(".") for part in md.parts):
                continue
            try:
                text = md.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            name = md.parent.name
            rel = str(md.parent.relative_to(REPO / "agent" / "skills")).replace("\\", "/")
            score = simple_similarity(args.consulta, text)
            skills_data.append({"name": name, "path": rel, "score": round(score, 4)})
        skills = sorted(skills_data, key=lambda s: s["score"], reverse=True)

    top = skills[0]["score"] if skills else 0.0

    if top >= args.alta:
        decision, ruta = "ejecutar", "nivel-1 directo con los skills sugeridos"
    elif top >= args.media:
        decision, ruta = "delegar", "nivel 2-3 (delegate_task) con los skills sugeridos en el contexto"
    else:
        decision, ruta = "escalar", "sin dominio claro → LLM orquestador (config model.default) decide"

    jev_status = env_key("JEV_API_KEY")
    jev_note = ("FASE 2: la cabeza Jev (type-safe) no esta implementada "
                "aun. Quedan por desarrollar: lectura ChromaDB, generacion "
                "de embeddings, invocacion Jev y ejecucion del handler.")

    out = {
        "consulta": args.consulta,
        "decision": decision,
        "ruta": ruta,
        "confianza_top": top,
        "modo": mode,
        "umbral_alta": args.alta,
        "umbral_media": args.media,
        "cabeza_jev": f"{jev_note} (JEV_API_KEY={'configurada' if jev_status else 'no-configurada'})",
        "skills": skills,
        "nota": "DEMO: los scores son de similaridad de tokens, no de embeddings reales.",
    }

    print(json.dumps(out, ensure_ascii=False, indent=2) if args.json else
          f"\n{top:>6.2f} [{decision.upper():<7}] {args.consulta}\n        {ruta}\n        " +
          "\n        ".join(f"{s['score']:.2f} {s['name']} ({s.get('path', '?')})" for s in skills) +
          f"\n\nModo: {mode}\n{jev_note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())