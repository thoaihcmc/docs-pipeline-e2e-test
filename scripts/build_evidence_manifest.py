#!/usr/bin/env python3
"""
Build an evidence manifest from the repository (deterministic, non-AI).
Used as input for the AI generation step so all outputs are traceable to repo evidence.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Allow importing config from repo root when run as scripts/build_evidence_manifest.py
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    import config as pipeline_config
except ImportError:
    pipeline_config = None

# Paths we consider as evidence (relative to repo root)
SOURCE_GLOBS = [
    "**/*.py",
    "**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx",
    "**/*.go", "**/*.rs", "**/*.java", "**/*.kt",
    "**/*.cs", "**/*.rb", "**/*.php",
    "**/package.json", "**/requirements*.txt", "**/pyproject.toml", "**/Cargo.toml", "**/go.mod",
    "**/*.yaml", "**/*.yml", "**/*.json", "**/*.toml", "**/*.env*",
    "**/migrations/**", "**/schema*.sql", "**/models/**", "**/orm/**",
]
DOCS_GLOB = "docs/**/*.md"
DIAGRAMS_GLOB = "docs/diagrams/**/*.mmd"
IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".tmp"}
EXCLUDE_EVIDENCE_PREFIXES = (
    ".github/",
    ".ci-build/",
    "scripts/",
)


def _get_changed_files(repo_path: str, commit: str) -> list[str]:
    """Return list of files changed in the given commit (relative paths)."""
    try:
        out = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return [f.strip() for f in out.stdout.strip().splitlines() if f.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def _read_file_snippet(path: Path, max_chars: int = 50000) -> str:
    """Read file content up to max_chars; skip binary."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(max_chars)
    except OSError:
        return ""


def _collect_evidence(repo_path: str, commit: str) -> dict:
    repo = Path(repo_path)
    if not repo.is_dir():
        return {"error": "repo path is not a directory", "evidence": {}, "changed_files": []}

    changed = _get_changed_files(repo_path, commit)

    evidence = {}
    for pattern in SOURCE_GLOBS + [DOCS_GLOB, DIAGRAMS_GLOB]:
        for p in repo.glob(pattern):
            if not p.is_file():
                continue
            rel = p.relative_to(repo).as_posix()
            parts = Path(rel).parts
            if any(ign in parts for ign in IGNORE_DIRS):
                continue
            key = rel
            if key in evidence:
                continue
            # Exclude pipeline implementation files; they bias output away from product logic.
            if key.startswith(EXCLUDE_EVIDENCE_PREFIXES):
                continue
            evidence[key] = {
                "path": key,
                "content_snippet": _read_file_snippet(p),
                "changed": rel in changed,
            }

    changed_evidence_ids = [f for f in changed if f in evidence]
    unchanged_evidence_ids = [f for f in evidence.keys() if f not in set(changed_evidence_ids)]

    return {
        "commit": commit,
        "repo_path": repo_path,
        "changed_files": changed,
        "evidence": evidence,
        "evidence_ids": list(evidence.keys()),
        # Primary evidence should drive generation to reflect newly added logic.
        "primary_evidence_ids": changed_evidence_ids if changed_evidence_ids else unchanged_evidence_ids[:30],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build evidence manifest from repository.")
    parser.add_argument("--repo", default=".", help="Repository root path")
    parser.add_argument("--commit", required=True, help="Commit SHA to analyze")
    parser.add_argument("--output", default="manifest.json", help="Output JSON path")
    args = parser.parse_args()

    manifest = _collect_evidence(args.repo, args.commit)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Wrote {out_path} with {len(manifest.get('evidence', {}))} evidence entries.", file=sys.stderr)


if __name__ == "__main__":
    main()
