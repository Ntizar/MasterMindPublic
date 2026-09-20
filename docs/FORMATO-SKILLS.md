# Formato de los skills

Un skill es **conocimiento procedimental en markdown**. No es una idea, no es una descripción: es *cómo se hace aquí*, con los comandos exactos.

## Estructura mínima

```markdown
---
name: nombre-del-skill
description: Usa cuando <trigger>. <qué hace en una línea>.
---

# Título

## Cuándo usarlo
## Pasos
1. ...
2. ...
## Pitfalls (lo que ya nos hemos comido)
- ...
## Verificación
```bash
# comando que demuestra que funcionó
```
```

### Las tres reglas de la descripción

La descripción es lo **único** que lee el buscador semántico: de ella depende que el skill aparezca o no.

1. **Empieza por el trigger**: «Usa cuando…», «Úsalo si…». El primer tercio de la frase es lo que más pesa.
2. **Sé específico**: «Usa al parsear PDFs con tablas» recupera; «Ayuda con documentos» no.
3. **Sin jerga privada**: si solo tú entiendes la frase, el índice no la encontrará cuando no la recuerdes.

## Qué hace bueno a un skill (y qué lo hace inútil)

| Bueno | Inútil |
|---|---|
| Comandos literales, copiables | «Configura el entorno adecuadamente» |
| Pitfalls con el error exacto | Descripción genérica del dominio |
| Verificación concreta | Promesas sin prueba |
| Autocontenido | «Como decíamos en el otro fichero…» |

## Organización en carpetas

```
agent/skills/
├── mapas/            ← dominio
│   ├── igm-wmts/     ← skill
│   │   └── SKILL.md
│   └── isocronas/
│       └── SKILL.md
└── datos/
    └── gtfs-parser/
        ├── SKILL.md
        └── scripts/  ← código de apoyo del skill (opcional)
```

## Ciclo de vida

1. **Alta**: nace de un problema real resuelto, o de una fuente externa destilada (con revisión).
2. **Indexado**: entra en ChromaDB con su descripción.
3. **Uso**: aparece en las búsquedas por significado.
4. **Poda**: `scripts/skills-nunca-usados.py` detecta los que nunca se recuperan. Un skill que nadie usa resta: sigue en el índice y compite en las búsquedas.

## Sincronización

Los skills viven en el repo (fuente de verdad) y en la instalación del motor (lo que se carga). `scripts/sync-skills.py` compara por hash y copia lo que difiere: nunca edites solo un lado, o vivirás en la deriva.
