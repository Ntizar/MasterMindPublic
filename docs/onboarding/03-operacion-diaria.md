# 03 — Operación diaria

## Comandos clave

```bash
cd ~/Projects/MasterMind
python scripts/consultar-skills.py "consulta" --json   # búsqueda semántica de skills
python scripts/indexar-skills.py [--reset]             # reindexar tras crear skills
python scripts/doctor.py                               # health check del sistema
python scripts/test-doctor.py                          # tests del doctor (bug-inyección)
bash scripts/run-stars-explorer.sh --batch 3 --json    # explorar stars manual
```

## El doctor

`doctor.py` verifica: gateway vivo, **cada cron** (jobs reales de `cron/jobs.json`:
run en error, ENTREGA caída tipo token revocado, y sin disparar >2h = gateway muerto),
ChromaDB sincronizada, stars-registry fresco, git limpio, **token de Telegram vivo**
(`getMe` en directo) y **vigías declarados** (`vigia-cron` + tarea Watchdog en
Task Scheduler). `--json` para consumo por cron.

`test-doctor.py` valida al doctor con el patrón bug-inyección (inspirado en
javierpa95/harness): inyecta cada bug REAL en sandboxes aislados bajo `%TEMP%` y
verifica que el doctor lo detecta (12 casos, incluido token revocado).
Ejecutar tras tocar `doctor.py`.

> **Pitfall histórico**: el check de crons leía `cron/jobs/*/job.json`, que nunca
> existió (Hermes guarda todo en `cron/jobs.json`) → el doctor pasaba los crons en
> silencio mientras el token de Telegram estaba muerto. Verificado 2026-09-02.

## Gateway, crons y el watchdog externo

El gateway autoarranca al login (`Hermes_Gateway.vbs` en Startup). Comprobar:
`hermes gateway status`. Los crons (scout de stars cada 6h, digest semanal los
lunes, doctor diario) viven si el gateway está vivo.

**Si el gateway muere**, lo revive `Hermes_Gateway_Watchdog` (Task Scheduler,
cada 10 min, `scripts/vigia-gateway.ps1` en la instalación): relanza, comprueba
si Telegram conecta de verdad y **avisa por Telegram o alerta del token revocado**.
Vive fuera del gateway a propósito: un cron de Hermes no puede vigilar al gateway
que lo ejecuta. Registrar tras reinstalar el PC:
`powershell -File scripts/registrar-vigia-gateway.ps1`.

**Colapso 2026-09-02 (lección)**: token de @NtizarBot revocado → gateway caído al
arranque + todos los crons sin entregar, nada de esto lo detectaba el doctor. Hoy
lo cubren: check `telegram-token`, checks `cron:*` con entrega, y el watchdog.

## Reglas de git

- El scout pushea cada 6h: si un push propio se rechaza con "fetch first",
  resolver SIEMPRE con `git pull --rebase origin master && git push` (nunca merge, nunca force).
- Commits atómicos, mensajes en castellano.
