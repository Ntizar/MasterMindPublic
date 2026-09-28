#!/usr/bin/env python3
"""
Skill Lifecycle Manager para Mastermind.

Analiza uso de skills vía git log, notas recientes y ChromaDB.
Re-prioriza automáticamente basado en actividad real.

NOTA: Todos los caminos son relativos al REPO (no absolutos).
Se detecta automáticamente el root del repositorio git.
"""
import os
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


def repo_root():
    """Devuelve la raiz del repo git (o el directorio actual si no hay git)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5, cwd="."
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except (subprocess.TimeoutExpired, OSError):
        pass
    return Path.cwd().resolve()


REPO_DIR = repo_root()
SKILLS_DIR = REPO_DIR / "agent" / "skills"
NOTES_DIR = REPO_DIR / "notes"
PRIORITY_FILE = REPO_DIR / "config" / "skill-priority.json"


def get_recent_git_activity(days=30):
    """Obtener skills mencionadas en commits recientes."""
    try:
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--pretty=format:%s", "--all"],
            capture_output=True, text=True, cwd=str(REPO_DIR), timeout=10
        )
        mentions = defaultdict(int)
        for line in result.stdout.split("\n"):
            for match in re.finditer(r'[a-z][a-z0-9-]{3,}', line.lower()):
                word = match.group()
                mentions[word] += 1
        return mentions
    except Exception:
        return {}


def get_notes_mentions(days=30):
    """Obtener skills mencionadas en notas recientes."""
    mentions = defaultdict(int)
    cutoff = datetime.now() - timedelta(days=days)

    if not NOTES_DIR.exists():
        return mentions

    for md_file in NOTES_DIR.glob("*.md"):
        if md_file.name.startswith("."):
            continue

        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", md_file.name)
        if date_match:
            try:
                file_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                if file_date < cutoff:
                    continue
            except ValueError:
                continue

        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore").lower()
            for match in re.finditer(r'[a-z][a-z0-9-]{3,}', content):
                word = match.group()
                mentions[word] += 1
        except Exception:
            pass

    return mentions


def get_all_skills():
    """Listar todas las skills con metadatos."""
    skills = {}

    if not SKILLS_DIR.exists():
        return skills

    for skill_md in SKILLS_DIR.rglob("SKILL.md"):
        try:
            skill_name = skill_md.parent.name
            category = skill_md.parent.parent.name

            content = skill_md.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

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
            "path": str(skill_md.relative_to(REPO_DIR)),
            "category": category,
            "version": version,
            "description": description,
            "size_bytes": skill_md.stat().st_size
        }

    return skills


def calculate_usage_score(skill_name, git_mentions, notes_mentions):
    """Calcular score de uso combinando git y notas."""
    git_score = min(git_mentions.get(skill_name, 0) / 5, 1.0)
    notes_score = min(notes_mentions.get(skill_name, 0) / 10, 1.0)

    partial_git = sum(v for k, v in git_mentions.items() if skill_name in k or k in skill_name)
    partial_notes = sum(v for k, v in notes_mentions.items() if skill_name in k or k in skill_name)

    combined = (git_score * 0.4 + notes_score * 0.4 +
                min(partial_git / 10, 0.1) + min(partial_notes / 10, 0.1))

    return round(min(combined, 1.0), 4)


def reclassify_skill(usage_score, current_priority, category):
    """Re-clasificar skill basado en uso real."""
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

    print("\n📊 Analizando actividad reciente (30 días)...")
    git_mentions = get_recent_git_activity(30)
    notes_mentions = get_notes_mentions(30)

    print(f"  Menciones en git: {sum(git_mentions.values())}")
    print(f"  Menciones en notas: {sum(notes_mentions.values())}")

    print("\n🔧 Indexando skills...")
    skills = get_all_skills()
    print(f"  Total: {len(skills)}")

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

    changes.sort(key=lambda x: x["usage_score"], reverse=True)

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

    PRIORITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PRIORITY_FILE, "w", encoding="utf-8") as f:
        json.dump(new_priority, f, indent=2, ensure_ascii=False)

    print(f"\n  HIGH: {len(reclassification['high'])}")
    print(f"  MEDIUM: {len(reclassification['medium'])}")
    print(f"  LOW: {len(reclassification['low'])}")

    print("\n🏆 Top 10 skills más usadas:")
    for c in changes[:10]:
        bar = "█" * int(c["usage_score"] * 20) + "░" * (20 - int(c["usage_score"] * 20))
        print(f"  {c['name']:30s} [{bar}] {c['usage_score']:.2f}")

    print("\n⚠️ Bottom 5 menos usadas:")
    for c in changes[-5:]:
        print(f"  {c['name']:30s} score={c['usage_score']:.2f}")

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

    report_dir = REPO_DIR / "learning"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "skill-lifecycle-report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Lifecycle analysis completado (reporte: {report_path})")


if __name__ == "__main__":
    main()