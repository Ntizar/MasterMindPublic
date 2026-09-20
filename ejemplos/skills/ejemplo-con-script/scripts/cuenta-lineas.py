#!/usr/bin/env python3
"""Cuenta lineas, palabras y caracteres de un fichero de texto.

Uso: python cuenta-lineas.py <fichero>
"""
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    p = Path(sys.argv[1])
    if not p.is_file():
        print(f"No existe o no es un fichero: {p}")
        return 1
    texto = p.read_text(encoding="utf-8", errors="replace")
    lineas = texto.count("\n") + (0 if texto.endswith("\n") or not texto else 1)
    print(f"{p}: {lineas} lineas, {len(texto.split())} palabras, {len(texto)} caracteres")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
