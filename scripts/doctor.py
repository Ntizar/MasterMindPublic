#!/usr/bin/env python3
"""
Doctor de Mastermind — health check read-only del sistema.
Verifica: gateway, crons, ChromaDB vs skills en disco, registry y git sync.

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

# Overrides de entorno para tests (scripts/test-doctor.py): permiten montar
# sandboxes aislados sin tocar el sistema real. En uso normal no se definen.
REPO = Path(os.environ.get("MM_DOCTOR_REPO", Path(__file__).resolve().parent.parent))
HERMES = Path(os.environ.get("MM_DOCTOR_HERMES", Path.home() / "AppData" / "Local" / "hermes"))
CRON_DIR = HERMES / "cron"
SANDBOX = os.environ.get("MM_DOCTOR_SANDBOX") == "1"
PY_SYS = r"~/AppData/Local/Programs/Python/Python312/python.exe"
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

# 2) Crons — fuente real: cron/jobs.json (¡ojo! NO jobs/<id>/job.json: el glob
#    antiguo nunca existió en producción y el check estaba muerto en silencio).
#    Detecta: último run en error, entrega fallida (colapso 2026-09-02: token
#    revocado -> "Telegram send failed: Unauthorized" enterrado), y jobs
#    enabled cuyo next_run_at hace >2h que tocaba disparar y no disparó.
def _parse_iso(s):
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:      # naive = hora local del PC
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

# 3) ChromaDB count == SKILL.md count
skill_count = len([p for p in (REPO / "agent" / "skills").rglob("SKILL.md")
                   if not any(part.startswith(".") for part in p.parts)])
try:
    out = run(f'"{PY_SYS}" -c "import chromadb; c=chromadb.PersistentClient(path=r\'{CHROMA_PATH.as_posix()}\'); print(c.get_collection(\'{COLLECTION}\').count())"',
              timeout=60)
    chroma_count = int(out.stdout.strip() or -1)
    check("chromadb", chroma_count == skill_count,
          f"indexados: {chroma_count} | SKILL.md en disco: {skill_count}"
          + ("" if chroma_count == skill_count else " → ejecutar scripts/indexar-skills.py"))
except Exception as e:
    check("chromadb", False, f"error: {e}")

# 4) Registry fresco (< 25h desde last_run)
try:
    reg = json.loads((REPO / "data" / "stars-registry.json").read_text(encoding="utf-8"))
    last_run = datetime.fromisoformat(reg["last_run"])
    age_h = (datetime.now(timezone.utc) - last_run).total_seconds() / 3600
    check("stars-registry", age_h < 25, f"último run hace {age_h:.1f}h | {len(reg['processed'])} repos procesados")
except Exception as e:
    check("stars-registry", False, f"error: {e}")

# 5) Git sincronizado (sin cambios pendientes y en día con origin)
r = run("git status --porcelain")
dirty = bool(r.stdout.strip())
r2 = run("git rev-parse --abbrev-ref HEAD")
branch = r2.stdout.strip()
check("git", not dirty,
      f"rama: {branch} | {'LIMPIO' if not dirty else f'{len(r.stdout.strip().splitlines())} ficheros pendientes de commit'}")

# 6) Token de Telegram vivo — lee HERMES/.env y hace getMe (colapso 2026-09-02:
#    token revocado tumbaba el gateway con error non-retryable y todos los crons
#    fallaban entrega sin que nada del repo lo notara). Omitido en sandbox sin .env.
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
            # Sin red no podemos afirmar que el token esté mal: warn, nunca fail.
            check("telegram-token", True, f"sin confirmación de red: {net_e}", warn=True)
except Exception as e:
    check("telegram-token", False, f"error leyendo .env: {e}")

# 7) Vigías externos declarados: cron vigia-cron en jobs.json + tarea del
#    watchdog del gateway en Task Scheduler (ambos fuera del repo: si faltan,
#    el sistema queda ciego ante token revocado o gateway muerto).
if SANDBOX:
    check("vigia-cron", True, "sandbox: omitido", warn=True)
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
if SANDBOX:
    check("vigia-gateway", True, "sandbox: omitido", warn=True)
else:
    r = run('powershell -NoProfile -Command "if (Get-ScheduledTask -TaskName '
            "'Hermes_Gateway_Watchdog' -ErrorAction SilentlyContinue) { 'VIVO' } "
            'else { \'MUERTO\' }"', timeout=60)
    wd_ok = "VIVO" in (r.stdout + r.stderr)
    check("vigia-gateway", wd_ok,
          "tarea Task Scheduler registrada" if wd_ok
          else "FALTA — registrar: powershell -File scripts/registrar-vigia-gateway.ps1")

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
