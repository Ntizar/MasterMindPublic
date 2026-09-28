---
name: cuenta-lineas
description: Usa al contar líneas, palabras y caracteres de un fichero de texto. Recibe una ruta a un fichero y devuelve un resumen estadístico sin dependencias externas.
---

# Cuenta Líneas, Palabras y Caracteres

## Cuándo usarlo
Cuando necesites un resumen rápido de un fichero de texto: tamaño, estructura y densidad de contenido. Útil para validar que un documento no está vacío o tiene el tamaño esperado.

## Pasos
1. El script está en `agent/skills/utilidades/cuenta-lineas/scripts/cuenta-lineas.py`
2. Ejecutar desde la raíz del repo:
   ```bash
   python agent/skills/utilidades/cuenta-lineas/scripts/cuenta-lineas.py README.md
   ```
3. O con un fichero arbitrario:
   ```bash
   python agent/skills/utilidades/cuenta-lineas/scripts/cuenta-lineas.py docs/GUIA-COMPLETA.md
   ```

## Pitfalls
- **Ruta relativa**: el script usa `Path(sys.argv[1])` relativo al working directory actual. Ejecutar desde la raíz del repo o usar ruta absoluta.
- **Fichero binario**: el script intenta leer como UTF-8 con `errors="replace"`, pero la estadística será irrelevante para ficheros no de texto.

## Verificación
```bash
python agent/skills/utilidades/cuenta-lineas/scripts/cuenta-lineas.py README.md
# Debe imprimir: README.md: X lineas, Y palabras, Z caracteres
```
