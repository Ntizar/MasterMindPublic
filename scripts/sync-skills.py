#!/usr/bin/env python3
"""
Sync idempotente instalación<->repo — Mastermind (v5, canónico; sustituye a sincronizar-skills.py).

Compara TODOS los ficheros de skills/ (no solo SKILL.md: también references/,
templates/, scripts/) entre la instalación Hermes y el repo. Copia solo lo que
difiere; empate de contenido no toca nada; conflicto de contenido lo gana el
mtime más reciente. Nunca borra: es unión. Re-ejecutar no cambia nada.

Uso:
  python scripts/sync-skills.py              # sincroniza ambas direcciones
  python scripts/sync-skills.py --dry-run    # solo reporta, no copia (--dry como alias)
"""
import argparse
import hashlib
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HERMES_SKILLS = Path.home() / "AppData" / "Local" / "hermes" / "skills"
REPO_SKILLS = REPO / "agent" / "skills"
JUNK_DIRS = {"__pycache__"}
JUNK_FILES = {".DS_Store", "Thumbs.db"}


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def collect(root: Path) -> dict:
    """{ruta_relativa_min: (path, mtime, md5)} de todos los ficheros, sin basura."""
    out = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in JUNK_DIRS for part in p.parts) or p.name in JUNK_FILES or p.suffix == ".pyc":
            continue
        key = p.relative_to(root).as_posix().lower()
        out[key] = (p, p.stat().st_mtime, md5(p))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", "--dry", dest="dry", action="store_true")
    args = ap.parse_args()

    hermes, repo = collect(HERMES_SKILLS), collect(REPO_SKILLS)
    acciones = []

    for key in sorted(set(hermes) | set(repo)):
        h, r = hermes.get(key), repo.get(key)
        if h and not r:
            acciones.append(("hermes->repo", key, "solo en instalacion"))
        elif r and not h:
            acciones.append(("repo->hermes", key, "solo en repo"))
        elif h and r and h[2] != r[2]:
            if h[1] >= r[1]:
                acciones.append(("hermes->repo", key, "difieren, gana instalacion (mas reciente)"))
            else:
                acciones.append(("repo->hermes", key, "difieren, gana repo (mas reciente)"))

    if not acciones:
        print(f"OK — todo sincronizado ({len(hermes)} ficheros en instalacion, {len(repo)} en repo). Nada que copiar.")
        return 0

    for d, key, motivo in acciones:
        src, dst = (HERMES_SKILLS / key, REPO_SKILLS / key) if d == "hermes->repo" else (REPO_SKILLS / key, HERMES_SKILLS / key)
        print(f"[{'DRY' if args.dry else 'COPY'}] {d}: {key} ({motivo})")
        if not args.dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    print((f"[DRY] {len(acciones)} ficheros se copiarian" if args.dry
           else f"OK — {len(acciones)} ficheros sincronizados."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
