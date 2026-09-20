# 05 — Reglas y human loop

## Las reglas del repo

1. Un orquestador, muchos especialistas.
2. Skills bajo demanda por dominio (ChromaDB primero).
3. Memoria persistente entre sesiones.
4. GitHub como fuente de verdad.
5. **NUNCA borrar del repo MasterMind** — solo crear o modificar.
6. Notas significativas → `notes/YYYY-MM-DD-titulo.md`.
7. Skills nuevos → `agent/skills/` (y sincronizar a la instalación local).
8. Cada aprendizaje importante → commit al repo.
9. No crear secrets en notes/commits/chat — solo en `.env`.
10. SOUL.md es la fuente de verdad de la identidad del sistema.
11. TODO en castellano — NUNCA inglés en repos, scripts, informes.
12. Human loop en cambios críticos — presentar diffs y esperar aprobación ✅.

## Cuándo se activa el human loop

- Se modifican más de 5 archivos
- Decisiones de arquitectura
- Deploy a producción
- Migraciones de datos o plataforma
- El usuario lo solicita

## Patrón

Planificar → Esperar ✅ → Implementar → Esperar ✅ → Sintetizar → Esperar ✅

- Nunca silenciar: terminar fase, presentar resultado, continuar.
- Máximo 2 reintentos por fase.
- Rollback siempre disponible (`git reset --hard`).
- Diffs siempre visibles: nunca commit sin mostrar cambios.
