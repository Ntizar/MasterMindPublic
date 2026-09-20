#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skills-nunca-usados.py — Reporte de skills NO cargados y clusters de casi-duplicados.

Cruce dos fuentes:
  1. Los skills existentes (instalación).
  2. Los que SÍ se han cargado (skill_view en state.db).

Y sobre los NO cargados, detecta CLUSTERS de casi-duplicados (misma descripción
en lo esencial) → candidatos a fusionar/podar, frente a los de nicho único.

Uso:
  python skills-nunca-usados.py                 # reporte
  python skills-nunca-usados.py --json          # JSON
  python skills-nunca-usados.py --sim 0.35      # umbral de similitud de cluster

NOTA: el "no usado" se mide en la ventana de sesiones de state.db (~3 semanas);
no es "nunca en la vida". El reporte lo dice explícitamente.
"""

import argparse
import json
import os
import re
import sys
import sqlite3
import unicodedata
from collections import defaultdict
from pathlib import Path

# stopwords de contenido genérico (para similitud)
STOP = set("""de la el los las al a un una y o en con que del para por completa completo
ecosistema patrones procedimiento guia serie catalogo indice usar usa use cuando
trabajar ejecutar como como sobre tema todo toda todos todas uso u e para una
se su sus mas esta este esto estos estas hacer ha haz usa use""".split())


def norm(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def tokens(desc):
    words = re.findall(r"[a-z]{3,}", norm(desc))
    return set(w for w in words if w not in STOP)


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def walk_skills(root):
    import yaml
    out = []
    for sp in sorted(Path(root).rglob("SKILL.md")):
        txt = sp.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^---\n(.*?)\n---\n", txt, re.DOTALL)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1))
        except Exception:
            continue
        if not isinstance(fm, dict):
            continue
        desc = str(fm.get("description", "") or "").strip()
        name = sp.parent.name
        # categoría = carpeta padre del skill (si hay una carpeta por encima)
        rel = sp.relative_to(root)
        parts = rel.parts
        category = parts[0] if len(parts) > 1 else "(root)"
        out.append({"name": name, "category": category, "desc": desc, "path": str(sp)})
    return out


def used_skills(db):
    con = sqlite3.connect("file:" + db + "?mode=ro", uri=True)
    cur = con.cursor()
    rows = cur.execute(
        "SELECT content FROM messages WHERE tool_name='skill_view' "
        "AND content LIKE '%\"name\"%'"
    ).fetchall()
    used = set()
    for (content,) in rows:
        if not content:
            continue
        try:
            parsed = json.loads(content)
        except Exception:
            continue
        nm = parsed.get("name")
        if nm:
            used.add(nm)
    con.close()
    return used


def clusters(items, sim_threshold):
    """Agrupa skills por similitud de tokens de descripción (transitivo)."""
    tk = {i["name"]: tokens(i["desc"]) for i in items}
    # union-find
    parent = {i["name"]: i["name"] for i in items}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    names = [i["name"] for i in items]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if jaccard(tk[names[i]], tk[names[j]]) >= sim_threshold:
                union(names[i], names[j])

    groups = defaultdict(list)
    for n in names:
        groups[find(n)].append(n)
    return [g for g in groups.values() if len(g) > 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sim", type=float, default=0.4)
    ap.add_argument("--dir", default=os.path.expandvars(r"%LOCALAPPDATA%\hermes\skills"))
    args = ap.parse_args()

    db = os.path.expandvars(r"%LOCALAPPDATA%\hermes\state.db")
    skills = walk_skills(args.dir)
    used = used_skills(db)

    never = [s for s in skills if s["name"] not in used]
    never_names = {s["name"] for s in never}

    # clusters entre los NUNCA usados
    cl = clusters(never, args.sim)

    by_cat = defaultdict(int)
    for s in never:
        by_cat[s["category"]] += 1

    if args.json:
        print(json.dumps({
            "total_skills": len(skills),
            "usados": len(used),
            "nunca_usados": len(never),
            "nota": "ventana state.db (~3 semanas), no histórico completo",
            "clusters_duplicados": cl,
            "por_categoria": dict(sorted(by_cat.items(), key=lambda kv: kv[1], reverse=True)),
            "nunca": [{"name": s["name"], "category": s["category"],
                       "desc": s["desc"][:80]} for s in never],
        }, ensure_ascii=False, indent=2))
        return

    print(f"=== SKILLS NO CARGADOS (ventana state.db ~3 semanas) ===")
    print(f"Total skills: {len(skills)} | usados: {len(used)} | NO cargados: {len(never)}")
    print(f"NOTA: 'no cargado' = no hubo skill_view en la ventana de sesiones de state.db, "
          f"no significa 'nunca en la vida'.\n")
    print("--- Clusters de casi-duplicados (candidatos a FUSIONAR/PODAR) ---")
    for g in sorted(cl, key=len, reverse=True):
        print(f"  ({len(g)}) {', '.join(g)}")
    print(f"\n--- No cargados por categoría ---")
    for c, n in sorted(by_cat.items(), key=lambda kv: kv[1], reverse=True):
        print(f"  {n:>3}  {c}")


if __name__ == "__main__":
    main()
