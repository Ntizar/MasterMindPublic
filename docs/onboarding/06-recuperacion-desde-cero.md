# 06 — Recuperación desde cero

Si se pierde el PC, el sistema se reconstruye desde el repo. Orden exacto:

1. **Instalar Hermes Agent** (desktop) y clonar el repo:
   `git clone https://github.com/Ntizar/MasterMindPublic.git ~/Projects/MasterMind`
2. **Instalar Python del sistema + chromadb**:
   usar `~/AppData/Local/Programs/Python/Python312/python.exe`
   (el python del PATH de Hermes no tiene pip) → `pip install chromadb`
3. **Sincronizar identidad y memorias**: copiar `agent/skills/` →
   `%LOCALAPPDATA%\hermes\skills\` y `agent/MEMORY.md` / `agent/USER.md` →
   `%LOCALAPPDATA%\hermes\memories\`
4. **Configurar .env** de Hermes con `OPENAI_API_KEY` / `OPENAI_BASE_URL` de tu proveedor
   (los secrets NO viven en el repo, por diseño).
5. **Indexar skills**: `python scripts/indexar-skills.py --reset`
6. **Gateway**: `hermes gateway install` (activa los crons) y arrancar
   `Hermes_Gateway.vbs` como startup item.
7. **Bot de Telegram**: David crea/valida el bot en @BotFather, pide `/token`
   y se escribe en `%LOCALAPPDATA%\hermes\.env` como `TELEGRAM_BOT_TOKEN`
   (el secret NO vive en el repo). David hace `/start` al bot para habilitar
   la entrega a su chat (`TELEGRAM_HOME_CHANNEL` del `.env`). Verificar: `curl api.telegram.org/bot<TOKEN>/getMe`.
8. **Watchdog del gateway**: `powershell -File scripts/registrar-vigia-gateway.ps1`
   (tarea Task Scheduler que revive el gateway si muere — ver 03-operacion-diaria).
9. **Verificar**: `python scripts/doctor.py` (todos los checks en verde, incluido
   `telegram-token`) y `python scripts/test-doctor.py` (12 casos de bug-inyección).

Con eso el sistema queda idéntico: skills, memorias de especialistas (van dentro
del repo), crons y búsqueda semántica operativos.

## Qué NO se recupera del repo (y es intencional)

- Secrets (`.env`) — regenerar a mano.
- Caches locales (`~/.mastermind/chromadb` se regenera con `--reset`).
- Estado efímero de sesiones.
