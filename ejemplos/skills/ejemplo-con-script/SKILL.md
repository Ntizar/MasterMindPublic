---
name: ejemplo-con-script
description: Usa cuando un skill necesite código de apoyo. Muestra cómo empaquetar un script dentro del propio skill.
---

# Ejemplo: skill con script de apoyo

## Cuándo usarlo
Cuando el procedimiento tiene lógica que no conviene reescribir cada vez: un parser, un cálculo, un cliente de API.

## Estructura
```
ejemplo-con-script/
├── SKILL.md
└── scripts/
    └── cuenta-lineas.py
```

## Pasos
1. Escribe el script en `scripts/` **dentro** del skill (así viaja con él).
2. Hazlo configurable por variables de entorno o argumentos; sin rutas personales.
3. Ejecútalo con la ruta relativa al propio skill.
4. Documenta en el SKILL.md qué hace y qué devuelve.

## Uso
```bash
python scripts/cuenta-lineas.py README.md
# → líneas, palabras y caracteres del fichero
```

## Pitfalls
- **Rutas absolutas de tu máquina**: el skill deja de funcionar en otro equipo.
- **Dependencias no declaradas**: si necesita un paquete, dilo en el SKILL.md.

## Verificación
```bash
python scripts/cuenta-lineas.py README.md
# Debe imprimir un recuento coherente sin error.
```
