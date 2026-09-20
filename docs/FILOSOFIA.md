# Filosofía — las reglas que mantienen el sistema honesto

Un sistema multi-agente no se rompe por falta de potencia: se rompe por falta de disciplina. Estas son las reglas que hacen que este funcione meses después de montarlo.

## Principios

1. **Un orquestador, muchos especialistas.** El orquestador clasifica y delega; los skills ejecutan.
2. **Skills bajo demanda por dominio.** Solo se cargan los del dominio relevante (búsqueda semántica primero).
3. **Memoria persistente.** Lo importante se guarda *cuando ocurre*, no "luego". Y se busca antes de preguntar.
4. **Git como fuente de verdad.** Markdown plano. Sin wikilinks, sin dependencias externas, sin lock-in.
5. **Nada se borra a la ligera.** Crear y modificar sí; borrar requiere lista exacta y aprobación.
6. **Notas significativas** → `notes/YYYY-MM-DD-titulo.md`.
7. **Skills nuevos** → carpeta de skills + sincronización a la instalación.
8. **Cada aprendizaje importante** → commit.
9. **Secretos solo en `.env`.** Nunca en notas, commits, informes ni en el chat.
10. **El documento de identidad manda.** Un único SOUL.md como fuente de verdad.
11. **Un idioma.** El que uses tú, pero uno: mezclar idiomas en repo y scripts envejece fatal.
12. **Human loop en cambios críticos.** Diff visible y aprobación explícita antes de publicar.

## Estados públicos y receipts

Todo trabajo se reporta en uno de estos cuatro estados — se pide el resultado, no el proceso:

| Estado | Significado |
|---|---|
| **Trabajando** | El resultado aún puede cambiar |
| **Comprobando** | Verificación funcional en curso |
| **Listo** | Hay evidencia suficiente para entregar — *siempre con receipt* |
| **Necesito tu decisión** | Causa, impacto y opciones concretas |

**Contrato de receipts:** «Listo» sin receipt es humo. El receipt es la prueba verificable del cambio: SHA del commit, test que pasó, comando ejecutado, URL viva. Sin evidencia no se declara Listo.

## Cuándo preguntar (y cuándo no)

Pregunta **solo** cuando la respuesta cambia el alcance, el impacto es destructivo o irreversible, hay seguridad o dinero de por medio, o hay efectos externos. Todo lo demás se decide solo y se reporta.

## Human loop: el sistema de control

Se activa cuando se tocan más de 5 archivos, hay decisiones de arquitectura, se despliega a producción, o se migran datos.

Patrón: **planificar → ✅ → implementar → ✅ → sintetizar → ✅**
Reglas: nunca silenciar, máximo 2 reintentos por fase, rollback siempre disponible, diffs siempre visibles, aprobación explícita (nunca asumir).

## Por qué esto importa más que el modelo

Un modelo mejor no arregla un sistema que miente en su documentación, que duplica configuraciones hasta que divergen, o que publica lo que no debe. La disciplina es lo que hace que el sistema siga siendo útil dentro de seis meses.
