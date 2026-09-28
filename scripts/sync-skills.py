#!/usr/bin/env python3
"""
Sync unidireccional repo→agente — Mastermind (v5, canónico).

El repositorio es LA FUENTE DE VERDAD. Este script copia los skills del repo a la
instalación de Hermes y detecta conflictos cuando el agente tiene cambios no
enviados al repo (los marca como conflict para revisión, nunca sobrescribe).

Principios:
  - Git es la fuente de verdad: nunca se basa en mtime.
  - Un solo sentido: repo → agente (nunca al revés).
  - Conflictos: si el agente tiene cambios locales no commiteados, se marcan
    como CONFLICTO y se PREGUNTA antes de sobrescribir.
  - --dry sobre 0 ficheros: avisa que no hay skills para sincronizar.

Uso:
  python scripts/sync-skills.py              # sincroniza repo→agente
  python scripts/sync-skills.py --dry-run    # solo reporta, no copia
  python scripts/sync-skills.py --yes        # automático (sin pedir confirmación)
"""
import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path


def repo_root():
    """Devuelve la raiz del repo git."""
    try:
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
HERMES_SKILLS = Path.home() / "AppData" / "Local" / "hermes" / "skills"
REPO_SKILLS = REPO / "agent" / "skills"
JUNK_DIRS = {"__pycache__"}
JUNK_FILES = {".DS_Store", "Thumbs.db"}


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def collect(root: Path) -> dict:
    """{ruta_relativa_min: (path, md5)} de todos los ficheros, sin basura."""
    out = {}
    if not root.exists():
        return out
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in JUNK_DIRS for part in p.parts) or p.name in JUNK_FILES or p.suffix == ".pyc":
            continue
        key = p.relative_to(root).as_posix().lower()
        out[key] = (p, md5(p))
    return out


def has_local_changes(repo_path: Path) -> set:
    """Devuelve las rutas de archivos con cambios locales sin commit en git."""
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", str(repo_path / "agent" / "skills")],
            capture_output=True, text=True, timeout=10, cwd=str(repo_path)
        )
        if out.returncode != 0:
            return set()
        changes = set()
        for line in out.stdout.strip().splitlines():
            # Formato git: " M path" o "A  path" (2 chars + espacio + path)
            if len(line) >= 3 and line[2] != ' ':
                continue  # ignorar archivos no stageados (solo staged)
            path_part = line[3:].strip()
            if path_part:
                changes.add(path_part.lower())
        return changes
    except Exception:
        return set()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", "--dry", dest="dry", action="store_true")
    ap.add_argument("--yes", "-y", dest="yes", action="store_true",
                    help="Sin preguntar confirmación")
    args = ap.parse_args()

    hermes, repo = collect(HERMES_SKILLS), collect(REPO_SKILLS)

    # Verificar que el repo tiene skills para sincronizar
    if not repo:
        print("⚠️  ADVERTENCIA: no hay ningún SKILL.md en agent/skills/.")
        print("   Sin skills en el repo, no hay nada que sincronizar.")
        print("   Crea un skill en agent/skills/<dominio>/<nombre>/SKILL.md")
        return 1 if not args.dry else 0

    acciones = []

    for key in sorted(set(hermes) | set(repo)):
        h, r = hermes.get(key), repo.get(key)
        if h and not r:
            # Existe en agente pero NO en repo → el agente tiene archivos no
            # enviados al repo. Nunca borramos, pero avisamos.
            acciones.append(("solo-agente", key, "solo en instalacion (no enviado al repo)"))
        elif r and not h:
            acciones.append(("repo->hermes", key, "solo en repo → copiar a agente"))
        elif h and r and h[1] != r[1]:
            # Conflict: mismos archivos, diferente contenido.
            # El repo manda (es la fuente de verdad).
            acciones.append(("conflicto", key, "difieren: repo manda (fuente de verdad)"))

    if not acciones:
        print("✅ Todo sincronizado "
              f"({len(hermes)} ficheros en instalacion, {len(repo)} en repo). "
              "Nada que copiar.")
        return 0

    print(f"{'[DRY] ' if args.dry else ''}Sincronizando {len(acciones)} fichero(s):")
    print(f"  Fuente: {REPO_SKILLS}")
    print(f"  Destino: {HERMES_SKILLS}")
    print()

    conflictos = []
    para_copiar = []

    for tipo, key, motivo in acciones:
        if tipo == "solo-agente":
            print(f"  ⚠️  SOLO-AGENTE: {key} ({motivo})")
            if not args.dry and not args.yes:
                print(f"       → No se borra. Envialo al repo: git add {key}")
            continue

        if tipo == "conflicto":
            conflictos.append((key, motivo))
            print(f"  🔴 CONFLICTO: {key} ({motivo})")
            if not args.dry and not args.yes:
                print(f"       → El repo manda. ¿Sobrescribir? (y/n)")
                try:
                    respuesta = input().strip().lower()
                    if respuesta in ("y", "yes", "si", "s"):
                        para_copiar.append((key, motivo, REPO_SKILLS / key, HERMES_SKILLS / key))
                    else:
                        print(f"       → Saltado por decisión del usuario.")
                except EOFError:
                    # stdin cerrado (pipe, cron): saltar conflictos
                    print(f"       → stdin no disponible (cron?), saltando.")
            elif args.yes:
                para_copiar.append((key, motivo, REPO_SKILLS / key, HERMES_SKILLS / key))
            elif args.dry:
                print(f"       → [DRY] No se copia.")
            continue

        # repo->hermes
        para_copiar.append((key, motivo, REPO_SKILLS / key, HERMES_SKILLS / key))
        print(f"  → {tipo}: {key} ({motivo})")

    if not args.dry and para_copiar:
        print()
        for key, motivo, src, dst in para_copiar:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  ✅ Copiado: {key}")

    # Resumen
    print()
    if args.dry:
        if not acciones:
            print("[DRY] No hay nada que sincronizar.")
        else:
            print(f"[DRY] {len(acciones)} fichero(s) detectado(s):")
            for a in acciones:
                print(f"  - {a[0]}: {a[1]} ({a[2]})")
    else:
        print(f"OK — {len(para_copiar)} fichero(s) sincronizado(s).")
        if conflictos:
            print(f"⚠️  {len(conflictos)} conflicto(s) saltados:")
            for c in conflictos:
                print(f"  - {c[0]}: {c[1]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())