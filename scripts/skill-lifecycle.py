#!/usr/bin/env python3
"""
Skill Lifecycle Manager para Mastermind.
Analiza uso de skills vía git log, notas recientes y ChromaDB.
Re-prioriza automáticamente basado en actividad real.
"""
import os
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

SKILLS_DIR = "agent/skills"
REPO_DIR = "/root/workspace/Mastermind"
NOTES_DIR = "/root/workspace/Mastermind/notes"
PRIORITY_FILE = "/root/workspace/Mastermind/config/skill-priority.json"

def get_recent_git_activity(days=30):
    """Obtener skills mencionadas en commits recientes."""
    try:
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--pretty=format:%s", "--all"],
            capture_output=True, text=True, cwd=REPO_DIR, timeout=10
        )
        mentions = defaultdict(int)
        for line in result.stdout.split("\n"):
            # Buscar nombres de skills en mensajes de commit
            for match in re.finditer(r'[a-z][a-z0-9-]{3,}', line.lower()):
                word = match.group()
                mentions[word] += 1
        return mentions
    except:
        return {}

def get_notes_mentions(days=30):
    """Obtener skills mencionadas en notas recientes."""
    mentions = defaultdict(int)
    cutoff = datetime.now() - timedelta(days=days)
    
    for md_file in Path(NOTES_DIR).glob("*.md"):
        if md_file.name.startswith("."):
            continue
        
        # Extraer fecha
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", md_file.name)
        if date_match:
            file_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
            if file_date < cutoff:
                continue
        
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore").lower()
            for match in re.finditer(r'[a-z][a-z0-9-]{3,}', content):
                word = match.group()
                mentions[word] += 1
        except:
            pass
    
    return mentions

def get_all_skills():
    """Listar todas las skills con metadatos."""
    skills = {}
    
    for skill_md in Path(SKILLS_DIR).rglob("SKILL.md"):
        skill_name = skill_md.parent.name
        category = skill_md.parent.parent.name
        
        try:
            content = skill_md.read_text(encoding="utf-8", errors="ignore")
        except:
            continue
        
        # Extraer frontmatter
        version = "1.0.0"
        description = ""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].split("\n"):
                    if line.strip().startswith("version:"):
                        version = line.split(":", 1)[1].strip().strip('"').strip("'")
                    elif line.strip().startswith("description:"):
                        description = line.split(":", 1)[1].strip().strip('"').strip("'")[:200]
        
        skills[skill_name] = {
            "path": str(skill_md),
            "category": category,
            "version": version,
            "description": description,
            "size_bytes": skill_md.stat().st_size
        }
    
    return skills

def calculate_usage_score(skill_name, git_mentions, notes_mentions):
    """Calcular score de uso combinando git y notas."""
    git_score = min(git_mentions.get(skill_name, 0) / 5, 1.0)  # Normalizado a 1.0
    notes_score = min(notes_mentions.get(skill_name, 0) / 10, 1.0)
    
    # También buscar menciones parciales (e.g., "tu-dominio" para "tu-dominio-dashboard")
    partial_git = sum(v for k, v in git_mentions.items() if skill_name in k or k in skill_name)
    partial_notes = sum(v for k, v in notes_mentions.items() if skill_name in k or k in skill_name)
    
    combined = (git_score * 0.4 + notes_score * 0.4 + 
                min(partial_git / 10, 0.1) + min(partial_notes / 10, 0.1))
    
    return round(min(combined, 1.0), 4)

def reclassify_skill(usage_score, current_priority, category):
    """Re-clasificar skill basado en uso real."""
    # Skills de mastermind/ siempre son HIGH
    if category == "mastermind":
        return "high"
    
    if usage_score >= 0.6:
        return "high"
    elif usage_score >= 0.3:
        return "medium"
    else:
        return "low"

def main():
    print("🔄 Skill Lifecycle Analysis")
    print("=" * 50)
    
    # Obtener actividad reciente
    print("\n📊 Analizando actividad reciente (30 días)...")
    git_mentions = get_recent_git_activity(30)
    notes_mentions = get_notes_mentions(30)
    
    print(f"  Menciones en git: {sum(git_mentions.values())}")
    print(f"  Menciones en notas: {sum(notes_mentions.values())}")
    
    # Obtener skills
    print("\n🔧 Indexando skills...")
    skills = get_all_skills()
    print(f"  Total: {len(skills)}")
    
    # Calcular uso y re-clasificar
    print("\n🎯 Calculando uso y re-clasificando...")
    
    reclassification = {
        "high": [],
        "medium": [],
        "low": []
    }
    
    changes = []
    
    for name, data in skills.items():
        usage = calculate_usage_score(name, git_mentions, notes_mentions)
        new_priority = reclassify_skill(usage, "medium", data["category"])
        
        reclassification[new_priority].append({
            "name": name,
            "usage_score": usage,
            "category": data["category"]
        })
        
        changes.append({
            "name": name,
            "usage_score": usage,
            "new_priority": new_priority,
            "category": data["category"]
        })
    
    # Ordenar por uso
    changes.sort(key=lambda x: x["usage_score"], reverse=True)
    
    # Actualizar skill-priority.json
    print("\n📝 Actualizando skill-priority.json...")
    new_priority = {
        "version": "2.0.0",
        "generated": datetime.now().strftime("%Y-%m-%d"),
        "note": "Auto-generado por skill-lifecycle.py. Basado en uso real (git + notas, 30 días).",
        "high": {
            "label": "🔥 Core — Uso activo",
            "description": "Skills con uso score >= 0.6 o de categoría mastermind/",
            "skills": [c["name"] for c in reclassification["high"]]
        },
        "medium": {
            "label": "📦 Dominio — Uso moderado",
            "description": "Skills con uso score 0.3-0.6",
            "skills": [c["name"] for c in reclassification["medium"]]
        },
        "low": {
            "label": "🗄️ Archivo — Uso bajo o ninguno",
            "description": "Skills con uso score < 0.3",
            "skills": [c["name"] for c in reclassification["low"]]
        }
    }
    
    with open(PRIORITY_FILE, "w", encoding="utf-8") as f:
        json.dump(new_priority, f, indent=2, ensure_ascii=False)
    
    print(f"  HIGH: {len(reclassification['high'])}")
    print(f"  MEDIUM: {len(reclassification['medium'])}")
    print(f"  LOW: {len(reclassification['low'])}")
    
    # Top 10 más usadas
    print("\n🏆 Top 10 skills más usadas:")
    for c in changes[:10]:
        bar = "█" * int(c["usage_score"] * 20) + "░" * (20 - int(c["usage_score"] * 20))
        print(f"  {c['name']:30s} [{bar}] {c['usage_score']:.2f}")
    
    # Bottom 5 menos usadas
    print("\n⚠️ Bottom 5 menos usadas:")
    for c in changes[-5:]:
        print(f"  {c['name']:30s} score={c['usage_score']:.2f}")
    
    # Guardar informe
    report = {
        "generated": datetime.now().isoformat(),
        "total_skills": len(skills),
        "reclassification": {
            "high": len(reclassification["high"]),
            "medium": len(reclassification["medium"]),
            "low": len(reclassification["low"])
        },
        "top_10": [c["name"] for c in changes[:10]],
        "bottom_5": [c["name"] for c in changes[-5:]],
        "all_changes": changes
    }
    
    with open("/root/workspace/Mastermind/learning/skill-lifecycle-report.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print("\n✅ Lifecycle analysis completado")

if __name__ == "__main__":
    main()
