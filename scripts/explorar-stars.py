#!/usr/bin/env python3
"""
Explorador de Stars de GitHub — Mastermind Stars Explorer
Fetch repos from user's stars, extract key info, and prepare for skill generation.

Output: JSON to stdout with batch of repos to analyze.
The agent then reads this output and creates skills from interesting patterns.

Usage:
  python3 explorar-stars.py                    # Process next batch (default 3)
  python3 explorar-stars.py --batch 5          # Process 5 repos
  python3 explorar-stars.py --all              # Process ALL unprocessed stars
  python3 explorar-stars.py --include-own      # Include own repos too
  python3 explorar-stars.py --status           # Show registry stats
  python3 explorar-stars.py --reprocess REPO   # Force reprocess a specific repo
"""

import json
import os
import sys
import time
import re
import base64
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# --- Config ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER = "Ntizar"
REGISTRY_PATH = os.environ.get(
    "STARS_REGISTRY", "data/stars-registry.json"
)
DEFAULT_BATCH = 3
API_BASE = "https://api.github.com"
README_MAX_CHARS = 8000  # Truncate long READMEs
TREE_MAX_FILES = 30  # Max files to show from repo tree


def api_get(url, token=None):
    """Make authenticated GitHub API request."""
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "MastermindStarsExplorer/1.0"}
    if token:
        headers["Authorization"] = f"token {token}"
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code == 403:
            # Rate limited
            reset_time = e.headers.get("X-RateLimit-Reset", "?")
            remaining = e.headers.get("X-RateLimit-Remaining", "?")
            print(f"[WARN] Rate limited. Remaining: {remaining}, reset: {reset_time}", file=sys.stderr)
            return None
        elif e.code == 404:
            return None
        else:
            print(f"[ERROR] HTTP {e.code} for {url}: {e.reason}", file=sys.stderr)
            return None
    except (URLError, TimeoutError) as e:
        print(f"[ERROR] Network error for {url}: {e}", file=sys.stderr)
        return None


def load_registry():
    """Load processed repos registry."""
    if os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH, "r") as f:
            return json.load(f)
    return {
        "processed": {},
        "last_run": None,
        "total_skills_created": 0,
        "stats": {"runs": 0, "repos_explored": 0, "skills_generated": 0},
    }


def sync_roots(registry):
    """Recalcula los campos raiz desde la verdad de `processed` (auto-curacion).

    En el pasado estos campos se escribian a mano y se desfasaban. Ahora cada
    guardado los deriva del mapa `processed` real, asi que no pueden mentir.
    """
    processed = registry.get("processed", {}) or {}
    skills = sum(1 for v in processed.values() if isinstance(v, dict) and v.get("skill_created"))
    registry["total_skills_created"] = skills
    stats = registry.setdefault("stats", {})
    stats["repos_explored"] = len(processed)
    stats["skills_created"] = skills
    return registry


def save_registry(registry):
    """Save registry to disk (roots recomputed first)."""
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    sync_roots(registry)
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def get_readme(repo_full_name, token):
    """Get README content (decoded from base64)."""
    data = api_get(f"{API_BASE}/repos/{repo_full_name}/readme", token)
    if not data or "content" not in data:
        return ""
    try:
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        # Truncate
        if len(content) > README_MAX_CHARS:
            content = content[:README_MAX_CHARS] + "\n... [truncated]"
        return content
    except Exception:
        return ""


def get_repo_tree(repo_full_name, token):
    """Get top-level file structure."""
    data = api_get(f"{API_BASE}/repos/{repo_full_name}/git/trees/HEAD?recursive=0", token)
    if not data or "tree" not in data:
        return []
    files = []
    for item in data["tree"][:TREE_MAX_FILES]:
        files.append({"path": item["path"], "type": item["type"], "size": item.get("size", 0)})
    return files


def get_key_files(repo_full_name, token, file_names=None):
    """Fetch content of specific key files (package.json, requirements.txt, etc.)."""
    if not file_names:
        file_names = ["package.json", "requirements.txt", "pyproject.toml", "Cargo.toml", 
                       "docker-compose.yml", "Dockerfile", "tsconfig.json", "vite.config.ts",
                       "Makefile", "CMakeLists.txt", "setup.py", "setup.cfg"]
    
    results = {}
    for fname in file_names:
        data = api_get(f"{API_BASE}/repos/{repo_full_name}/contents/{fname}", token)
        if data and "content" in data:
            try:
                content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                if len(content) > 3000:
                    content = content[:3000] + "\n... [truncated]"
                results[fname] = content
            except Exception:
                pass
    return results


def analyze_repo(repo_data, readme, tree, key_files):
    """Extract patterns, tools, and potential skill angles from a repo."""
    analysis = {
        "name": repo_data["name"],
        "full_name": repo_data["full_name"],
        "description": repo_data.get("description", ""),
        "language": repo_data.get("language"),
        "stars": repo_data.get("stargazers_count", 0),
        "topics": repo_data.get("topics", []),
        "url": repo_data.get("html_url", ""),
        "created_at": repo_data.get("created_at", ""),
        "updated_at": repo_data.get("updated_at", ""),
        "pushed_at": repo_data.get("pushed_at", ""),
        "license": (repo_data.get("license") or {}).get("spdx_id", ""),
        "archived": repo_data.get("archived", False),
        # Derived analysis
        "file_types": {},
        "tech_stack": [],
        "potential_patterns": [],
        "skill_angles": [],
    }
    
    # File type distribution
    for f in tree:
        ext = Path(f["path"]).suffix.lower() or "(no ext)"
        analysis["file_types"][ext] = analysis["file_types"].get(ext, 0) + 1
    
    # Detect tech stack from key files + language + topics
    stack_signals = set()
    if analysis["language"]:
        stack_signals.add(analysis["language"])
    stack_signals.update(analysis["topics"])
    
    for fname, content in key_files.items():
        if fname == "package.json":
            try:
                pkg = json.loads(content)
                for dep_name in list(pkg.get("dependencies", {}).keys())[:15]:
                    stack_signals.add(dep_name)
                for dep_name in list(pkg.get("devDependencies", {}).keys())[:10]:
                    stack_signals.add(dep_name)
            except json.JSONDecodeError:
                pass
        elif fname == "requirements.txt" or fname == "pyproject.toml":
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("["):
                    pkg_name = re.split(r"[>=<!\[]", line)[0].strip()
                    if pkg_name:
                        stack_signals.add(pkg_name)
    
    analysis["tech_stack"] = sorted(stack_signals)[:30]
    
    # Extract patterns from README
    if readme:
        readme_lower = readme.lower()
        pattern_hints = [
            ("architecture", ["architecture", "arquitectura", "design pattern", "pattern"]),
            ("pipeline", ["pipeline", "workflow", "flujo"]),
            ("real-time", ["real-time", "realtime", "en tiempo real", "live"]),
            ("3d", ["three.js", "threejs", "3d", "webgl", "webgpu"]),
            ("ai/ml", ["machine learning", "deep learning", "neural", "model", "inference", "llm", "transformer"]),
            ("cv", ["computer vision", "yolo", "detection", "segmentation", "opencv"]),
            ("geospatial", ["gis", "geospatial", "map", "leaflet", "geojson", "topojson", "gtfs"]),
            ("crm/erp", ["crm", "erp", "business", "enterprise"]),
            ("dashboard", ["dashboard", "visualization", "chart", "analytics"]),
            ("voice/audio", ["voice", "speech", "audio", "tts", "stt", "whisper"]),
            ("security", ["security", "auth", "encrypt", "token"]),
            ("api", ["api", "rest", "graphql", "endpoint"]),
            ("deploy", ["deploy", "docker", "kubernetes", "ci/cd", "vercel"]),
            ("performance", ["performance", "optimization", "cache", "worker"]),
            ("testing", ["test", "testing", "jest", "pytest", "vitest"]),
        ]
        
        for pattern_name, keywords in pattern_hints:
            if any(kw in readme_lower for kw in keywords):
                analysis["potential_patterns"].append(pattern_name)
    
    # Suggest skill angles based on combination of signals
    if analysis["potential_patterns"]:
        # High-value combinations
        if "3d" in analysis["potential_patterns"] and "geospatial" in analysis["potential_patterns"]:
            analysis["skill_angles"].append("geospatial-3d-visualization")
        if "ai/ml" in analysis["potential_patterns"] and "cv" in analysis["potential_patterns"]:
            analysis["skill_angles"].append("ai-cv-pipeline")
        if "pipeline" in analysis["potential_patterns"] and "deploy" in analysis["potential_patterns"]:
            analysis["skill_angles"].append("ci-cd-pipeline-patterns")
        if "crm/erp" in analysis["potential_patterns"] and "api" in analysis["potential_patterns"]:
            analysis["skill_angles"].append("crm-erp-patterns")
        if "voice/audio" in analysis["potential_patterns"] and "ai/ml" in analysis["potential_patterns"]:
            analysis["skill_angles"].append("voice-ai-integration")
        if "real-time" in analysis["potential_patterns"] and "dashboard" in analysis["potential_patterns"]:
            analysis["skill_angles"].append("realtime-dashboard")
        if "performance" in analysis["potential_patterns"] and "3d" in analysis["potential_patterns"]:
            analysis["skill_angles"].append("3d-performance")
        
        # Generic fallback: if many patterns, suggest a general skill
        if len(analysis["potential_patterns"]) >= 3 and not analysis["skill_angles"]:
            analysis["skill_angles"].append(f"pattern-{analysis['potential_patterns'][0]}")
    
    # Add README excerpt (first 2000 chars for context)
    analysis["readme_excerpt"] = readme[:2000] if readme else "(no README)"
    
    return analysis


def get_unprocessed_stars(token, registry, include_own=False):
    """Fetch stars that haven't been processed yet."""
    processed = registry.get("processed", {})
    unprocessed = []
    
    # Fetch starred repos
    page = 1
    while True:
        data = api_get(f"{API_BASE}/users/{GITHUB_USER}/starred?per_page=100&page={page}", token)
        if not data:
            break
        for repo in data:
            full_name = repo["full_name"]
            if full_name not in processed:
                unprocessed.append(repo)
        if len(data) < 100:
            break
        page += 1
        time.sleep(0.5)
    
    # Optionally include own repos
    if include_own:
        page = 1
        while True:
            data = api_get(f"{API_BASE}/users/{GITHUB_USER}/repos?per_page=100&type=owner&page={page}", token)
            if not data:
                break
            for repo in data:
                full_name = repo["full_name"]
                if full_name not in processed:
                    unprocessed.append(repo)
            if len(data) < 100:
                break
            page += 1
            time.sleep(0.5)
    
    # Sort by stars (most starred first)
    unprocessed.sort(key=lambda r: r.get("stargazers_count", 0), reverse=True)
    
    return unprocessed


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Explore GitHub stars for skill extraction")
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH, help="Number of repos to process")
    parser.add_argument("--all", action="store_true", help="Process all unprocessed stars")
    parser.add_argument("--include-own", action="store_true", help="Include own repos")
    parser.add_argument("--status", action="store_true", help="Show registry stats")
    parser.add_argument("--reprocess", type=str, help="Force reprocess a specific repo")
    parser.add_argument("--json", action="store_true", help="Output raw JSON (for agent consumption)")
    args = parser.parse_args()
    
    if not GITHUB_TOKEN:
        print("[ERROR] GITHUB_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    
    registry = load_registry()
    
    if args.status:
        stats = registry.get("stats", {})
        processed = registry.get("processed", {})
        print(f"📊 Stars Explorer Registry Status:")
        print(f"   Total repos processed: {len(processed)}")
        print(f"   Total runs: {stats.get('runs', 0)}")
        print(f"   Total skills generated: {stats.get('skills_generated', 0)}")
        print(f"   Last run: {registry.get('last_run', 'never')}")
        print(f"   Registry: {REGISTRY_PATH}")
        # List categories
        categories = {}
        for repo, info in processed.items():
            cat = info.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        if categories:
            print(f"\n   Categories:")
            for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
                print(f"     {cat}: {count}")
        return
    
    # Get unprocessed repos
    if args.reprocess:
        # Force reprocess specific repo
        data = api_get(f"{API_BASE}/repos/{args.reprocess}", GITHUB_TOKEN)
        if not data:
            print(f"[ERROR] Repo {args.reprocess} not found", file=sys.stderr)
            sys.exit(1)
        batch = [data]
    else:
        unprocessed = get_unprocessed_stars(GITHUB_TOKEN, registry, args.include_own)
        if not unprocessed:
            print(json.dumps({"status": "all_done", "message": "All stars have been processed!"}))
            return
        batch_size = len(unprocessed) if args.all else min(args.batch, len(unprocessed))
        batch = unprocessed[:batch_size]
    
    # Process each repo in the batch
    results = []
    for repo in batch:
        full_name = repo["full_name"]
        print(f"[INFO] Processing {full_name} ({repo.get('stargazers_count', 0)}⭐)...", file=sys.stderr)
        
        readme = get_readme(full_name, GITHUB_TOKEN)
        tree = get_repo_tree(full_name, GITHUB_TOKEN)
        key_files = get_key_files(full_name, GITHUB_TOKEN)
        
        analysis = analyze_repo(repo, readme, tree, key_files)
        
        # Add key files summary
        analysis["key_files_present"] = list(key_files.keys())
        
        results.append(analysis)
        
        # Update registry (mark as seen, but not yet skill-created)
        registry["processed"][full_name] = {
            "explored_at": datetime.now(timezone.utc).isoformat(),
            "category": "pending",
            "stars": repo.get("stargazers_count", 0),
            "language": repo.get("language"),
            "skill_angles": analysis["skill_angles"],
            "skill_created": False,
        }
        
        time.sleep(1)  # Be nice to GitHub API
    
    # Update registry stats
    registry["last_run"] = datetime.now(timezone.utc).isoformat()
    registry["stats"]["runs"] = registry["stats"].get("runs", 0) + 1
    registry["stats"]["repos_explored"] = registry["stats"].get("repos_explored", 0) + len(results)
    save_registry(registry)
    
    # Output
    output = {
        "status": "batch_ready",
        "batch_size": len(results),
        "total_unprocessed_remaining": len(get_unprocessed_stars(GITHUB_TOKEN, registry, args.include_own)) if not args.reprocess else "unknown",
        "repos": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # Human-friendly summary for agent consumption
        print(f"🔍 Stars Explorer — Batch de {len(results)} repos procesados")
        print(f"   Repos pendientes: {output['total_unprocessed_remaining']}")
        print(f"   Timestamp: {output['timestamp']}")
        print()
        for r in results:
            print(f"📦 {r['full_name']} ({r['stars']}⭐)")
            print(f"   Lang: {r['language']} | Topics: {', '.join(r['topics'][:5]) or 'none'}")
            print(f"   Description: {r['description'][:100] or '(none)'}")
            print(f"   Patterns: {', '.join(r['potential_patterns']) or 'none detected'}")
            print(f"   Skill angles: {', '.join(r['skill_angles']) or 'no obvious angles'}")
            print(f"   Files: {', '.join(r['key_files_present'][:5]) or 'none'}")
            print()
        
        # Also output JSON for programmatic use
        print("--- JSON ---")
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
