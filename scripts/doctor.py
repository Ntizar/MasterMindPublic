#!/usr/bin/env python3
"""
Doctor de Mastermind — health check read-only del sistema.

Verifica: gateway, crons, ChromaDB vs skills en disco (HASH, no solo número),
registry, git sync (dirty + commits sin push).

NOTA: todas las rutas son relativas al repositorio (REPO), nunca absolutas.

Uso:
  python scripts/doctor.py            # informe legible
  python scripts/doctor.py --json     # para consumo por cron/agent
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path


def repo_root():
    """Devuelve la raiz del repo git (o el directorio actual si no hay git)."""
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


# Overrides de entorno para tests (scripts/test-doctor.py): permiten montar
# sandboxes aislados sin tocar el sistema real. En uso normal no se definen.
REPO = Path(os.environ.get("MM_DOCTOR_REPO", repo_root()))
HERMES = Path(os.environ.get("MM_DOCTOR_HERMES", Path.home() / "AppData" / "Local" / "hermes"))
CRON_DIR = HERMES / "cron"
SANDBOX = os.environ.get("MM_DOCTOR_SANDBOX") == "1"
CHROMA_PATH = Path(os.environ.get("MM_DOCTOR_CHROMA", Path.home() / ".mastermind" / "chromadb"))
COLLECTION = "mastermind-skills"

results = []


def check(name, ok, detail="", warn=False):
    results.append({"check": name, "ok": ok, "warn": warn, "detail": detail})


def run(cmd, cwd=None, timeout=30):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              cwd=cwd or str(REPO), shell=True)
    except Exception as e:
        return type("R", (), {"returncode": 1, "stdout": "", "stderr": str(e)})()


# 1) Gateway vivo (omitido en sandbox de tests)
if SANDBOX:
    check("gateway", True, "sandbox: omitido", warn=True)
else:
    r = run("hermes gateway status")
    gw_up = "running" in (r.stdout + r.stderr).lower() or "✓" in r.stdout
    check("gateway", gw_up, (r.stdout + r.stderr).strip().splitlines()[0] if (r.stdout + r.stderr) else "sin salida")

# 2) Crons — fuente real: cron/jobs.json
def _parse_iso(s):
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt

try:
    jf = CRON_DIR / "jobs.json"
    if not jf.exists():
        check("crons", True, "sin jobs.json (aún no hay crons)", warn=True)
    else:
        data = json.loads(jf.read_text(encoding="utf-8"))
        jobs = data["jobs"] if isinstance(data, dict) else data
        now = datetime.now(timezone.utc)
        for job in jobs:
            name = job.get("name") or job.get("id", "?")
            if not job.get("enabled", False):
                continue
            probs, warns_j = [], []
            st = job.get("last_status")
            if st not in (None, "ok", "running"):
                probs.append(f"último run: {st} (ver cron/output/{job.get('id')})")
            if job.get("last_delivery_error"):
                warns_j.append(f"entrega fallida: {job['last_delivery_error'][:70]}")
            nra = job.get("next_run_at")
            if nra:
                try:
                    if (now - _parse_iso(nra)) > timedelta(hours=2):
                        probs.append(f"sin disparar desde {nra} — ¿gateway muerto?")
                except ValueError:
                    pass
            check(f"cron:{name}", not probs,
                  " | ".join(probs + warns_j) or f"ok (próximo: {nra or '—'})",
                  warn=bool(warns_j) and not probs)
except Exception as e:
    check("cron:lectura", False, f"error leyendo jobs.json: {e}")

# 3) ChromaDB: compara HASHES por skill, no solo el número
skill_files = list((REPO / "agent" / "skills").rglob("SKILL.md"))
skill_files = [p for p in skill_files if not any(part.startswith(".") for part in p.parts)]
skill_count = len(skill_files)

if skill_count == 0:
    check("chromadb", False,
          "agent/skills/ está vacío (0 SKILL.md). Crea skills y ejecuta scripts/indexar-skills.py")
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        col = client.get_collection(COLLECTION)
        chroma_count = col.count()
        if chroma_count > 0:
            check("chromadb", False,
                  f"ChromaDB tiene {chroma_count} items pero agent/skills/ está vacío (0 SKILL.md)")
    except Exception:
        pass
else:
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        col = client.get_collection(COLLECTION)
        chroma_count = col.count()

        # Verificar contenido: comparar hash de cada SKILL.md con lo que hay en ChromaDB
        hashes_disco = {}
        for p in skill_files:
            text = p.read_text(encoding="utf-8", errors="ignore")
            import hashlib
            h = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]
            hashes_disco[str(p.relative_to(REPO / "agent" / "skills"))] = h

        # Leer los items indexados y comparar
        all_items = col.get(include=["metadatas"])
        hashes_chroma = {}
        for i, meta in enumerate(all_items.get("metadatas", [])):
            path_key = meta.get("path", "") if meta else ""
            chroma_hash = meta.get("hash", "") if meta else ""
            if path_key and chroma_hash:
                hashes_chroma[path_key] = chroma_hash

        mismatches = []
        for path_key, disco_hash in hashes_disco.items():
            chroma_hash = hashes_chroma.get(path_key, "")
            if disco_hash and chroma_hash and disco_hash != chroma_hash:
                mismatches.append(f"{path_key}: disco={disco_hash} chroma={chroma_hash}")
            elif disco_hash and not chroma_hash:
                mismatches.append(f"{path_key}: en disco pero NO indexado en ChromaDB")

        if mismatches:
            check("chromadb", False,
                  f"{len(mismatches)} skill(s) con hash diferente o no indexado(s). "
                  f"Ejecuta scripts/indexar-skills.py. Ej: {mismatches[0][:60]}")
        elif chroma_count != skill_count:
            check("chromadb", False,
                  f"indexados: {chroma_count} | SKILL.md en disco: {skill_count} "
                  f"→ ejecutar scripts/indexar-skills.py")
        else:
            check("chromadb", True, f"indexados: {chroma_count} | SKILL.md en disco: {skill_count} ✓")
    except Exception as e:
        check("chromadb", False, f"error accediendo ChromaDB: {e}")

# 4) Registry fresco (< 25h desde last_run) — Opcional si no existe el fichero
registry_path = REPO / "data" / "stars-registry.json"
if not registry_path.exists():
    check("stars-registry", False,
          "data/stars-registry.json no existe — "
          "ejecuta scripts/explorar-stars.py primero")
else:
    try:
        reg = json.loads(registry_path.read_text(encoding="utf-8"))
        last_run = datetime.fromisoformat(reg["last_run"])
        age_h = (datetime.now(timezone.utc) - last_run).total_seconds() / 3600
        check("stars-registry", age_h < 25,
              f"último run hace {age_h:.1f}h | {len(reg['processed'])} repos procesados")
    except Exception as e:
        check("stars-registry", False, f"error: {e}")

# 5) Git sincronizado: cambios pendientes + commits sin push
r = run("git status --porcelain")
dirty = bool(r.stdout.strip())

r2 = run("git rev-parse --abbrev-ref HEAD")
branch = r2.stdout.strip()

# Comprobar commits sin push (ahead/behind contra origin)
r3 = run("git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null")
upstream_ok = r3.returncode == 0
ahead = 0
behind = 0
if upstream_ok:
    r4 = run("git rev-list --count --left-right HEAD...@{upstream} 2>/dev/null")
    if r4.returncode == 0 and r4.stdout.strip():
        parts = r4.stdout.strip().split('\t')
        if len(parts) == 2:
            try:
                behind = int(parts[0])
                ahead = int(parts[1])
            except ValueError:
                pass

git_ok = not dirty
git_detail_parts = [f"rama: {branch}"]
if dirty:
    git_ok = False
    git_detail_parts.append(f"{len(r.stdout.strip().splitlines())} ficheros pendientes de commit")
if upstream_ok and ahead > 0:
    git_ok = False
    git_detail_parts.append(f"{ahead} commit(s) sin push a origin")
if upstream_ok and behind > 0:
    git_detail_parts.append(f"{behind} commit(s) en origin no locales (pull necesario)")

check("git", git_ok, " | ".join(git_detail_parts))

# 6) Token de Telegram — omitido en sandbox sin .env
try:
    env_file = HERMES / ".env"
    tg_token = None
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                tg_token = line.split("=", 1)[1].strip()
    if not tg_token:
        check("telegram-token", True, "sin TELEGRAM_BOT_TOKEN en .env (omitido)", warn=True)
    else:
        try:
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{tg_token}/getMe",
                headers={"User-Agent": "MastermindDoctor/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                uname = (data.get("result") or {}).get("username", "?")
                check("telegram-token", True, f"vivo — bot @{uname}")
            else:
                check("telegram-token", False,
                      "REVOCADO/INVÁLIDO (Telegram 401) — pedir token en @BotFather y "
                      "actualizar TELEGRAM_BOT_TOKEN en .env, luego hermes gateway restart")
        except urllib.error.HTTPError as he:
            if he.code == 401:
                check("telegram-token", False,
                      "REVOCADO/INVÁLIDO (Telegram 401) — pedir token en @BotFather y "
                      "actualizar TELEGRAM_BOT_TOKEN en .env, luego hermes gateway restart")
            else:
                check("telegram-token", True, f"Telegram respondió HTTP {he.code} (red suspecta)", warn=True)
        except Exception as net_e:
            check("telegram-token", True, f"sin confirmación de red: {net_e}", warn=True)
except Exception as e:
    check("telegram-token", False, f"error leyendo .env: {e}")

# 7) Vigías externos (omitidos en sandbox)
if SANDBOX:
    check("vigia-cron", True, "sandbox: omitido", warn=True)
    check("vigia-gateway", True, "sandbox: omitido", warn=True)
else:
    try:
        data = json.loads((CRON_DIR / "jobs.json").read_text(encoding="utf-8"))
        jobs = data["jobs"] if isinstance(data, dict) else data
        vigia = any(j.get("name") == "vigia-cron" and j.get("enabled") for j in jobs)
        check("vigia-cron", vigia,
              "activo (alerta fallos de cron a Telegram)" if vigia
              else "FALTA — recrear: hermes cron create \"*/30 * * * *\" --name vigia-cron "
                   "--no-agent --script vigia-cron.py --deliver telegram")
    except Exception as e:
        check("vigia-cron", False, f"error leyendo jobs.json: {e}")
    try:
        r = run('powershell -NoProfile -Command "'
                'if (Get-ScheduledTask -TaskName '
                "'Hermes_Gateway_Watchdog' -ErrorAction SilentlyContinue) { 'VIVO' } "
                "else { 'MUERTO' }\"", timeout=60)
        wd_ok = "VIVO" in (r.stdout + r.stderr)
        check("vigia-gateway", wd_ok,
              "tarea Task Scheduler registrada" if wd_ok
              else "FALTA — registrar: scripts/registrar-vigia-gateway.ps1")
    except Exception:
        check("vigia-gateway", False, "no se pudo verificar Task Scheduler")

# Salida
fails = [r for r in results if not r["ok"]]
warns = [r for r in results if r["ok"] and r.get("warn")]
if "--json" in sys.argv:
    print(json.dumps({"ok": not fails, "fails": len(fails), "checks": results},
                     ensure_ascii=False, indent=2))
else:
    icon = lambda r: "✅" if r["ok"] and not r.get("warn") else ("⚠️ " if r["ok"] else "❌")
    print(f"🩺 Doctor Mastermind — {datetime.now():%Y-%m-%d %H:%M}")
    print()
    for r in results:
        print(f"{icon(r)} {r['check']:<28} {r['detail']}")
    print()
    if fails:
        print(f"❌ {len(fails)} problema(s) — revisar arriba")
        sys.exit(1)
    print("✅ Todo en orden" + (f" ({len(warns)} avisos)" if warns else ""))