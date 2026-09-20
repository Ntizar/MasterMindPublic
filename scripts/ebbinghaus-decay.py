#!/usr/bin/env python3
"""
Sistema de memoria con decaimiento Ebbinghaus para Mastermind.
Analiza notas y skills, calcula relevancia temporal, archiva lo obsoleto.
"""
import os
import re
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

# Configuración de decay por tipo
DECAY_PROFILES = {
    "permanente": {"a": 1.0, "b": 0.0, "c": 0.0},   # Siempre 100%
    "lento":      {"a": 1.0, "b": 0.5, "c": 0.0},   # 71% a 30d
    "normal":     {"a": 1.0, "b": 1.0, "c": 0.0},   # 52% a 30d
    "rapido":     {"a": 1.0, "b": 2.0, "c": 0.0},   # 30% a 30d
}

def ebbinghaus_score(days_old, profile="normal"):
    """Calcular score de relevancia según decaimiento Ebbinghaus."""
    p = DECAY_PROFILES.get(profile, DECAY_PROFILES["normal"])
    if days_old <= 0:
        return 1.0
    score = p["a"] / (math.log(days_old + 1)) ** p["b"] + p["c"]
    return min(max(score, 0.0), 1.0)

def classify_note(filepath):
    """Clasificar una nota en perfil de decay basado en contenido."""
    content = Path(filepath).read_text(encoding="utf-8", errors="ignore").lower()
    
    # Patrones que indican permanencia
    permanent_patterns = ["soul.md", "arquitectura", "patrón fundamental", "regla del sistema"]
    if any(p in content for p in permanent_patterns):
        return "permanente"
    
    # Patrones de decay rápido
    fast_patterns = ["fix", "error temporal", "urgente", "hoy", "resultado de sesión"]
    if any(p in content for p in fast_patterns):
        return "rapido"
    
    # Patrones de decay lento
    slow_patterns = ["skill", "patrón reutilizable", "arquitectura", "diseño", "referencia"]
    if any(p in content for p in slow_patterns):
        return "lento"
    
    return "normal"

def analyze_notes(notes_dir):
    """Analizar todas las notas y calcular sus scores de relevancia."""
    results = []
    now = datetime.now()
    
    for md_file in Path(notes_dir).glob("*.md"):
        if md_file.name.startswith(".") or md_file.name == "_template.md":
            continue
        
        # Extraer fecha del nombre del archivo
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", md_file.name)
        if date_match:
            file_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
            days_old = (now - file_date).days
        else:
            days_old = 90  # Default para archivos sin fecha
        
        profile = classify_note(md_file)
        score = ebbinghaus_score(days_old, profile)
        
        results.append({
            "file": md_file.name,
            "path": str(md_file),
            "days_old": days_old,
            "profile": profile,
            "score": round(score, 4),
            "action": "archive" if score < 0.2 else "keep"
        })
    
    return sorted(results, key=lambda x: x["score"])

def analyze_skills(skills_dir):
    """Analizar skills y calcular relevancia basada en metadatos."""
    results = []
    
    for skill_md in Path(skills_dir).rglob("SKILL.md"):
        content = skill_md.read_text(encoding="utf-8", errors="ignore")
        
        # Extraer version y categoría del frontmatter
        version = "1.0.0"
        category = skill_md.parent.parent.name
        
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].split("\n"):
                    if line.strip().startswith("version:"):
                        version = line.split(":", 1)[1].strip().strip('"').strip("'")
                    elif line.strip().startswith("category:"):
                        category = line.split(":", 1)[1].strip().strip('"').strip("'")
        
        # Skills de mastermind/ son permanentes
        if "mastermind" in str(skill_md):
            profile = "permanente"
        elif category in ["software-development", "backend", "infraestructura"]:
            profile = "lento"
        else:
            profile = "normal"
        
        # Score basado en existencia (no en uso real, que requeriría git log)
        score = ebbinghaus_score(0, profile)  # Recién creado = score alto
        
        results.append({
            "file": skill_md.parent.name,
            "path": str(skill_md),
            "category": category,
            "version": version,
            "profile": profile,
            "score": round(score, 4)
        })
    
    return results

def main():
    notes_dir = "/root/workspace/Mastermind/notes"
    skills_dir = "agent/skills"
    output_dir = "/root/workspace/Mastermind/learning"
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("🧠 Ebbinghaus Decay Analysis")
    print("=" * 50)
    
    # Analizar notas
    print("\n📝 Analizando notas...")
    notes = analyze_notes(notes_dir)
    
    # Clasificar por acción
    to_archive = [n for n in notes if n["action"] == "archive"]
    to_keep = [n for n in notes if n["action"] != "archive"]
    
    print(f"  Total notas: {len(notes)}")
    print(f"  ✅ Mantener: {len(to_keep)}")
    print(f"  📦 Archivar: {len(to_archive)}")
    
    # Analizar skills
    print("\n🔧 Analizando skills...")
    skills = analyze_skills(skills_dir)
    print(f"  Total skills: {len(skills)}")
    
    # Generar informe
    report = {
        "generated": datetime.now().isoformat(),
        "notes": {
            "total": len(notes),
            "to_keep": len(to_keep),
            "to_archive": len(to_archive),
            "archive_list": [n["file"] for n in to_archive],
            "details": notes
        },
        "skills": {
            "total": len(skills),
            "by_profile": {},
            "details": skills
        }
    }
    
    # Contar skills por perfil
    for s in skills:
        p = s["profile"]
        report["skills"]["by_profile"][p] = report["skills"]["by_profile"].get(p, 0) + 1
    
    # Guardar informe
    output_file = os.path.join(output_dir, "ebbinghaus-decay-report.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Informe guardado en: {output_file}")
    
    # Archivar notas obsoletas
    if to_archive:
        archive_dir = os.path.join(notes_dir, "archive")
        os.makedirs(archive_dir, exist_ok=True)
        
        print(f"\n📦 Archivando {len(to_archive)} notas obsoletas...")
        for note in to_archive:
            src = note["path"]
            dst = os.path.join(archive_dir, note["file"])
            if os.path.exists(src):
                os.rename(src, dst)
                print(f"  → {note['file']} (score: {note['score']})")
    
    # Resumen
    print("\n" + "=" * 50)
    print("RESUMEN:")
    print(f"  Notas analizadas: {len(notes)}")
    print(f"  Notas archivadas: {len(to_archive)}")
    print(f"  Skills analizadas: {len(skills)}")
    print(f"  Perfiles: {report['skills']['by_profile']}")

if __name__ == "__main__":
    main()
