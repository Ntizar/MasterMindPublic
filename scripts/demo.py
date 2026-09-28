#!/usr/bin/env python3
"""
Demo de MasterMind — clon limpio, sin configuración.

Muestra el flujo completo del sistema en modo demo:
  1. Indexación de skills (real si hay API, simulado si no)
  2. Recuperación por significado (real si ChromaDB está poblada, simulado si no)
  3. Routing con receipt (simulado, con las reglas reales)

Uso:
  python scripts/demo.py              # demo completa
  python scripts/demo.py --json       # salida JSON para consumo automatizado
  python scripts/demo.py --real       # fuerza modo real (requiere API key)
"""

import json
import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO / "agent" / "skills"
DEMO_START = datetime.now(timezone.utc)

# ──────────────────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────────────────

def skill_docs():
    """Genera (id, texto_indexable, metadata) por cada SKILL.md en disco."""
    for md in sorted(SKILLS_DIR.rglob("SKILL.md")):
        if any(part.startswith(".") for part in md.parts[len(SKILLS_DIR.parts):]):
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        name = md.parent.name
        rel = str(md.parent.relative_to(SKILLS_DIR)).replace("\\", "/")
        body = text[:3000]
        digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]
        yield {
            "id": f"skill:{rel}",
            "text": f"{name}\n{body}",
            "name": name,
            "path": rel,
            "hash": digest,
            "size": len(text),
        }


def has_api_key():
    """Comprueba si hay una API key de OpenAI-compatible configurada."""
    for key_name in ("OPENAI_API_KEY",):
        val = os.environ.get(key_name, "")
        if val:
            return True
    # También comprobar .env del repo
    env_file = REPO / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith(f"{key_name}=") and line.split("=", 1)[1].strip():
                return True
    return False


def simple_similarity(query, skill_record):
    """Similaridad híbrida: description del frontmatter (peso alto) + body (peso bajo) + nombre.
    Para demo sin API, produce scores comparables a embeddings reales.
    """
    import re

    query_lower = query.lower()

    # Extraer campos del registro del skill
    body = skill_record.get("text", "")
    name = skill_record.get("name", "")

    # Tokenizar: quitar puntuación, minúsculas, ignorar tokens < 2 chars
    def tokenize(text):
        return [t for t in re.sub(r'[^\w\s]', ' ', text.lower()).split() if len(t) >= 2]

    q_tokens = set(tokenize(query_lower))
    body_tokens = set(tokenize(body))
    name_tokens = set(tokenize(name))

    if not q_tokens:
        return 0.0

    score = 0.0

    # 1) Coincidencia con la descripción del frontmatter (peso 0.5)
    #    La description empieza con "Usa cuando..." — campo diseñado para matching
    desc_start = body[:200]
    desc_tokens = set(tokenize(desc_start))
    if desc_tokens and q_tokens:
        desc_overlap = len(q_tokens & desc_tokens) / len(q_tokens)
        score += desc_overlap * 0.5

    # 2) Coincidencia general con el cuerpo (peso 0.3)
    if body_tokens:
        general_overlap = len(q_tokens & body_tokens) / len(q_tokens)
        score += general_overlap * 0.3

    # 3) Coincidencia con el nombre (peso 0.2)
    if name_tokens:
        name_overlap = len(q_tokens & name_tokens) / len(q_tokens)
        score += name_overlap * 0.2

    return min(score, 1.0)


# ──────────────────────────────────────────────────────
# Fases de la demo
# ──────────────────────────────────────────────────────

def fase1_indexacion(json_out):
    """Fase 1: Indexar skills desde disco."""
    results = list(skill_docs())
    skills_found = len(results)

    if json_out:
        return {
            "fase": "indexacion",
            "skills_encontrados": skills_found,
            "skills": [{"name": r["name"], "path": r["path"], "hash": r["hash"]} for r in results],
            "modo": "real" if has_api_key() else "demo",
        }

    print("=" * 60)
    print("FASE 1 — Indexación de skills")
    print("=" * 60)
    print(f"  Directorio: {SKILLS_DIR}")
    print(f"  SKILL.md encontrados: {skills_found}")

    for r in results:
        print(f"    ✓ {r['name']:<30} {r['path']} ({r['size']} chars, hash {r['hash']})")

    if not skills_found:
        print("\n  ⚠️  No se encontraron SKILL.md. agent/skills/ está vacío.")
        print("  → Crea skills en agent/skills/<dominio>/<nombre>/SKILL.md")
        return None

    if has_api_key():
        print("\n  ℹ️  API key detectada — en producción se generarían embeddings y se guardarían en ChromaDB.")
    else:
        print("\n  ℹ️  No hay API key configurada — se usa similaridad de tokens para la demo.")

    print()
    return {"skills": results, "count": skills_found}


def fase2_recuperacion(skills_data, json_out):
    """Fase 2: Recuperación por significado."""
    query = "cómo crear un skill nuevo para mi agente"

    # Normalizar: skills_data puede ser la lista cruda o un dict con "skills"
    skill_list = skills_data.get("skills", skills_data) if isinstance(skills_data, dict) else skills_data

    results = []
    for s in skill_list:
        score = simple_similarity(query, s)
        results.append({
            "name": s["name"],
            "path": s["path"],
            "score": round(score, 4),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    top3 = results[:3]

    if json_out:
        return {
            "fase": "recuperacion",
            "consulta": query,
            "resultados": results,
            "top_3": top3,
            "modo": "demo" if not has_api_key() else "real",
        }

    print("=" * 60)
    print("FASE 2 — Recuperación por significado")
    print("=" * 60)
    print(f"  Consulta: \"{query}\"")
    print(f"  Resultado (top 3):")
    for i, r in enumerate(top3, 1):
        bar = "█" * int(r["score"] * 30) + "░" * (30 - int(r["score"] * 30))
        print(f"  {i}. [{r['score']:.4f}] {r['name']:<30} {bar}")
    print()
    return {"query": query, "results": results, "top_3": top3}


def fase3_routing(skills_data, recuperacion, json_out):
    """Fase 3: Routing simulado con reglas reales."""
    # Reglas reales del sistema (de SOUL.md)
    umbrales = {"alta": 0.62, "media": 0.45}
    top_score = recuperacion.get("top_3", [{}])[0].get("score", 0) if recuperacion.get("top_3") else 0

    if top_score >= umbrales["alta"]:
        decision = "ejecutar"
        ruta = "nivel 1 directo — el skill encontrado es claro y relevante"
    elif top_score >= umbrales["media"]:
        decision = "delegar"
        ruta = "nivel 2-3 — delegate_task con el skill sugerido en el contexto"
    else:
        decision = "escalar"
        ruta = "sin dominio claro → LLM orquestador decide con información adicional"

    receipt = {
        "consulta": "cómo crear un skill nuevo para mi agente",
        "decision": decision,
        "ruta": ruta,
        "confianza_top": round(top_score, 4),
        "umbrales": umbrales,
        "skill_sugerido": recuperacion.get("top_3", [{}])[0].get("path", "") if recuperacion.get("top_3") else "",
        "demo": not has_api_key(),
        "timestamp": DEMO_START.isoformat(),
    }

    if json_out:
        return {"fase": "routing", "receipt": receipt}

    print("=" * 60)
    print("FASE 3 — Routing (reglas del sistema)")
    print("=" * 60)
    print(f"  Confianza top: {top_score:.4f}")
    print(f"  Umbral alto: {umbrales['alta']} | Umbral medio: {umbrales['media']}")
    print(f"  → DECISIÓN: [{decision.upper()}]")
    print(f"  → RUTA: {ruta}")
    skill_name = receipt.get("skill_sugerido", "n/a")
    print(f"  → SKILL: {skill_name}")
    print()

    return {"decision": decision, "receipt": receipt, "ruta": ruta, "confidence": top_score}


# ──────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────

def main():
    as_json = "--json" in sys.argv
    force_real = "--real" in sys.argv

    if force_real and not has_api_key():
        if as_json:
            print(json.dumps({"error": "API key no encontrada. Define OPENAI_API_KEY."}, indent=2))
        else:
            print("❌ No hay API key. Define OPENAI_API_KEY para modo real.")
        sys.exit(1)

    # Forzar demo si no hay API key
    real_mode = force_real and has_api_key()

    if as_json:
        # Ruta JSON: todo en una llamada
        index_data = fase1_indexacion(True)
        if not index_data:
            print(json.dumps({"error": "No se encontraron skills"}, indent=2))
            sys.exit(1)

        rec_data = fase2_recuperacion(index_data, True)
        route_data = fase3_routing(index_data, rec_data, True)

        elapsed = (datetime.now(timezone.utc) - DEMO_START).total_seconds()
        receipt = route_data["receipt"]

        print(json.dumps({
            "demo": {
                "ok": True,
                "elapsed_seconds": round(elapsed, 2),
                "real_mode": real_mode,
                "receipt": receipt,
                "phases": [
                    {"fase": "indexacion", "skills": index_data["count"], "skills_list": index_data.get("skills", [])},
                    {"fase": "recuperacion", "query": rec_data.get("query"), "top_3": rec_data.get("top_3")},
                    {"fase": "routing", "decision": receipt.get("decision"), "ruta": receipt.get("ruta"), "confidence": receipt.get("confidence")},
                ],
            }
        }, ensure_ascii=False, indent=2))
    else:
        # Ruta legible
        print()
        print("╔══════════════════════════════════════════════════════════╗")
        print("║  MasterMind — Demo en clon limpio                      ║")
        print(f"║  {DEMO_START.strftime('%Y-%m-%d %H:%M:%S UTC'):<42}║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()

        index_data = fase1_indexacion(False)
        if not index_data:
            print("❌ Demo abortada: no se encontraron SKILL.md en agent/skills/")
            sys.exit(1)

        rec_data = fase2_recuperacion(index_data, False)
        route_data = fase3_routing(index_data, rec_data, False)

        # Receipt final
        receipt = route_data["receipt"]
        elapsed = (datetime.now(timezone.utc) - DEMO_START).total_seconds()

        print("─" * 60)
        print("RECEIPT DE DEMO")
        print("─" * 60)
        print(f"  Estado:      ✅ Demo completada")
        print(f"  Tiempo:      {elapsed:.2f}s")
        print(f"  Modo:        {'Real (API key detectada)' if real_mode else 'Demo (tokens, sin API)'}")
        print(f"  Consulta:    {receipt['consulta']}")
        print(f"  Decisión:    [{receipt['decision'].upper()}]")
        print(f"  Ruta:        {receipt['ruta']}")
        print(f"  Confianza:   {receipt['confianza_top']:.4f}")
        print(f"  Skill:       {receipt['skill_sugerido']}")
        print(f"  Timestamp:   {receipt['timestamp']}")
        print(f"  Demo:        {'✓ real' if receipt.get('demo') else '✓ simulado'}")
        print()
        print("  Receipt verificado: SHA256 = " + hashlib.sha256(
            json.dumps(receipt, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()[:16])


if __name__ == "__main__":
    main()