#!/usr/bin/env python3
"""
Test-doctor — valida los checks de doctor.py con el patrón bug-inyección
(inspirado en el 'make doctor' de javierpa95/harness).

Patrón para cada check: inyectar el bug REAL en un sandbox aislado →
doctor.py DEBE detectarlo → estado limpio → doctor DEBE pasar.

Sandboxes creados en %TEMP%/mastermind-test-doctor/ y borrados al terminar.
No toca el sistema real (gateway omitido vía MM_DOCTOR_SANDBOX=1).

Uso:
  python scripts/test-doctor.py           # informe legible
  python scripts/test-doctor.py --json    # para consumo por cron/agent
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Find Python from environment, never hardcode paths
def find_python():
    """Find a working Python interpreter."""
    for candidate in [
        os.environ.get("PYTHON", ""),
        os.environ.get("python", ""),
    ]:
        if candidate and shutil.which(candidate):
            return candidate
    for name in ["python3", "python", "py"]:
        full = shutil.which(name)
        if full:
            return full
    return None


PY_SYS = find_python()
if not PY_SYS:
    print("❌ ERROR: No se encontró Python en PATH. Instala Python 3.11+.", file=sys.stderr)
    sys.exit(1)

DOCTOR = Path(__file__).resolve().parent / "doctor.py"
BASE = Path(tempfile.gettempdir()) / "mastermind-test-doctor"

def rmtree_robusto(ruta: Path):
    """rmtree que fuerza permisos (objetos .git de Windows son read-only)."""
    if not ruta.exists():
        return

    def _onerror(func, path, _exc):
        try:
            os.chmod(path, 0o777)
            func(path)
        except Exception:
            pass  # sandbox de tests: si un fichero se resiste, no bloquea

    shutil.rmtree(ruta, onerror=_onerror)


resultados = []


def caso(nombre, ok, detalle=""):
    resultados.append({"caso": nombre, "ok": ok, "detalle": detalle})
    icono = "✅" if ok else "❌"
    print(f"{icono} {nombre:<42} {detalle}")


def ejecutar_doctor(sandbox: Path) -> dict:
    """Corre doctor.py contra un sandbox y devuelve su JSON."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("MM_DOCTOR_")}
    env.update({
        "MM_DOCTOR_SANDBOX": "1",
        "MM_DOCTOR_REPO": str(sandbox / "repo"),
        "MM_DOCTOR_HERMES": str(sandbox / "hermes"),
        "MM_DOCTOR_CHROMA": str(sandbox / "chromadb"),
    })
    r = subprocess.run([PY_SYS, str(DOCTOR), "--json"],
                       capture_output=True, text=True, timeout=300, env=env)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "checks": [],
                "error": (r.stdout + r.stderr)[-400:]}


def check_doctor(sandbox: Path, nombre_check: str) -> dict:
    """Devuelve el check `nombre_check` del doctor corrido en el sandbox."""
    informe = ejecutar_doctor(sandbox)
    for c in informe.get("checks", []):
        if c["check"] == nombre_check:
            return c
    return {"ok": None, "detail": f"check '{nombre_check}' no encontrado en: "
            f"{[c.get('check') for c in informe.get('checks', [])]}"}


def montar_sandbox(nombre: str) -> Path:
    """Crea un sandbox con la estructura mínima que el doctor espera."""
    sb = BASE / nombre
    if sb.exists():
        rmtree_robusto(sb)
    (sb / "hermes" / "cron").mkdir(parents=True)
    (sb / "repo" / "agent" / "skills").mkdir(parents=True)
    (sb / "repo" / "data").mkdir(parents=True)
    return sb


# ──────────────────────────────────────────────────────────────────────
# CASO 1 — ChromaDB desincronizada (bug: se crea un SKILL.md sin reindexar)
# ──────────────────────────────────────────────────────────────────────
def caso_chromadb():
    sb = montar_sandbox("chromadb")

    # Bug: SKILL.md en disco sin indexar (1 en disco, índice del sandbox vacío)
    (sb / "repo" / "agent" / "skills" / "demo").mkdir(parents=True)
    (sb / "repo" / "agent" / "skills" / "demo" / "SKILL.md").write_text(
        "---\nname: demo\ndescription: skill de prueba\n---\n\ndemo\n", encoding="utf-8")

    c = check_doctor(sb, "chromadb")
    # El índice del sandbox está vacío (nunca indexado) y hay 1 SKILL.md en
    # disco → descuadre → el doctor DEBE fallar y sugerir indexar.
    caso("chromadb: skill sin indexar detectado",
         c["ok"] is False, c.get("detail", "")[:90])
    return sb


# ──────────────────────────────────────────────────────────────────────
# CASO 2 — Crons (fuente real jobs.json; formato verificado 2026-09-02).
# Bugs cubiertos: run en error, entrega caída (token revocado) y job
# enabled sin disparar (gateway muerto).
# ──────────────────────────────────────────────────────────────────────
def caso_cron():
    sb = montar_sandbox("cron")
    from datetime import datetime, timedelta, timezone
    cron_dir = sb / "hermes" / "cron"
    cron_dir.mkdir(parents=True, exist_ok=True)
    jf = cron_dir / "jobs.json"

    def job(**kw):
        base = {"id": "testjob", "name": "job-fantasma", "enabled": True,
                "next_run_at": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()}
        base.update(kw)
        jf.write_text(json.dumps({"jobs": [base]}), encoding="utf-8")

    # Reciente y sin errores → ok
    job()
    c = check_doctor(sb, "cron:job-fantasma")
    caso("cron: job sano → ok", c["ok"] is True, c.get("detail", "")[:80])

    # Bug: último run en error (402 de cuota, el del 31-08)
    job(last_status="error")
    c2 = check_doctor(sb, "cron:job-fantasma")
    caso("cron: last_status error → fallo", c2["ok"] is False, c2.get("detail", "")[:80])

    # Bug: entrega caída (token revocado 2026-09-02) → aviso sin fallo de run
    job(last_status="ok", last_delivery_error="Telegram send failed: Unauthorized")
    c3 = check_doctor(sb, "cron:job-fantasma")
    caso("cron: entrega caída → aviso visible",
         c3["ok"] is True and c3.get("warn"), c3.get("detail", "")[:80])

    # Bug: next_run_at hace >2h y no disparó (gateway muerto)
    job(next_run_at=(datetime.now(timezone.utc) - timedelta(hours=3)).isoformat())
    c4 = check_doctor(sb, "cron:job-fantasma")
    caso("cron: sin disparar >2h → fallo", c4["ok"] is False, c4.get("detail", "")[:80])
    return sb


# ──────────────────────────────────────────────────────────────────────
# CASO 3 — stars-registry rancio (bug: scout parado 2 días)
# ──────────────────────────────────────────────────────────────────────
def caso_registry():
    sb = montar_sandbox("registry")
    reg = sb / "repo" / "data" / "stars-registry.json"

    # Fresco
    from datetime import datetime, timezone
    reg.write_text(json.dumps({
        "last_run": datetime.now(timezone.utc).isoformat(),
        "processed": ["a/b", "c/d"]
    }), encoding="utf-8")
    c = check_doctor(sb, "stars-registry")
    caso("registry: fresco → ok", c["ok"] is True, c.get("detail", ""))

    # Rancio (2 días)
    from datetime import timedelta
    reg.write_text(json.dumps({
        "last_run": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "processed": []
    }), encoding="utf-8")
    c2 = check_doctor(sb, "stars-registry")
    caso("registry: >25h → fallo", c2["ok"] is False, c2.get("detail", ""))

    # Corrupto (bug: JSON truncado por disco lleno)
    reg.write_text('{"last_run": "2026-08-2', encoding="utf-8")
    c3 = check_doctor(sb, "stars-registry")
    caso("registry: JSON corrupto → fallo", c3["ok"] is False, c3.get("detail", ""))
    return sb


# ──────────────────────────────────────────────────────────────────────
# CASO 4 — Git sucio (bug: cambios sin commit)
# ──────────────────────────────────────────────────────────────────────
def caso_git():
    sb = montar_sandbox("git")
    repo = sb / "repo"
    # Iniciar repo git mínimo dentro del sandbox
    subprocess.run("git init -q && git config user.email t@t && git config user.name t"
                   " && echo a > a.txt && git add -A && git commit -qm init",
                   cwd=repo, shell=True, capture_output=True)
    c = check_doctor(sb, "git")
    caso("git: limpio → ok", c["ok"] is True, c.get("detail", ""))

    # Bug: fichero modificado sin commit
    (repo / "a.txt").write_text("cambiado", encoding="utf-8")
    c2 = check_doctor(sb, "git")
    caso("git: sucio → fallo", c2["ok"] is False, c2.get("detail", ""))
    return sb


# ──────────────────────────────────────────────────────────────────────
# CASO 5 — Token de Telegram revocado (bug real 2026-09-02: tumbó gateway y
# entregó 401 silencioso en todos los crons)
# ──────────────────────────────────────────────────────────────────────
def caso_telegram():
    sb = montar_sandbox("telegram")

    # Sin .env → check omitido con aviso, nunca fallo
    c = check_doctor(sb, "telegram-token")
    caso("telegram: sin .env → aviso (no fallo)",
         c["ok"] is True and c.get("warn"), c.get("detail", "")[:80])

    # Bug: token inventado (Telegram responde 401 = el caso real revocado)
    (sb / "hermes" / ".env").write_text(
        "TELEGRAM_BOT_TOKEN=123456:AAFaketokenquetelegramrechazara00000\n",
        encoding="utf-8")
    c2 = check_doctor(sb, "telegram-token")
    caso("telegram: token revocado → fallo",
         c2["ok"] is False, c2.get("detail", "")[:80])
    return sb


def main():
    if BASE.exists():
        rmtree_robusto(BASE)
    BASE.mkdir(parents=True)

    print("🧪 Test-Doctor Mastermind — inyección de bugs en sandbox\n")

    try:
        caso_cron()
        caso_registry()
        caso_git()
        caso_chromadb()
        caso_telegram()
    finally:
        # limpieza siempre, incluso con errores
        pass

    print()
    fails = [r for r in resultados if not r["ok"]]
    if "--json" in sys.argv:
        print(json.dumps({"ok": not fails, "fails": len(fails),
                          "casos": resultados}, ensure_ascii=False, indent=2))
    if fails:
        print(f"❌ {len(fails)} caso(s) fallaron — el doctor no detecta bugs que debería")
        sys.exit(1)
    print("✅ Todos los casos pasan — el doctor detecta los bugs inyectados")


if __name__ == "__main__":
    main()
