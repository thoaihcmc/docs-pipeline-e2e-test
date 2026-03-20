#!/usr/bin/env python3
"""
Generate FDD, BDD, ADD and 4 Mermaid diagrams using OpenAI Structured Outputs.
Writes only to approved docs/ and docs/diagrams/ paths. Saves generation_output.json for validation.
"""
import argparse
import json
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
for _p in (str(_REPO_ROOT), str(_SCRIPT_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import config as pipeline_config
from schemas.documentation_schema import DOCUMENTATION_OUTPUT_SCHEMA


def _load_manifest(manifest_path: str) -> dict:
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_system_prompt(manifest: dict) -> str:
    evidence_ids = manifest.get("evidence_ids", [])
    evidence = manifest.get("evidence", {})
    commit = manifest.get("commit", "unknown")
    changed = manifest.get("changed_files", [])

    parts = [
        "You are a solution architect generating technical design documentation and diagrams.",
        "Your output must be based ONLY on the repository evidence provided. Do not invent components, functions, classes, states, entities, or relationships that are not supported by the evidence.",
        "Every element you generate must be traceable to at least one evidence path in the manifest (evidence_ids).",
        f"Commit: {commit}. Changed files in this commit: " + (", ".join(changed) if changed else "none"),
        "",
        "Evidence paths (use these exact strings in traceability.evidence_path):",
        json.dumps(evidence_ids, indent=2),
        "",
        "Evidence content snippets (key = path):",
    ]
    for path, data in list(evidence.items())[:200]:  # cap size for context
        snippet = (data.get("content_snippet") or "")[:8000]
        parts.append(f"\n--- {path} ---\n{snippet}")

    return "\n".join(parts)


def _call_openai(manifest: dict) -> dict:
    try:
        from openai import OpenAI
    except ImportError:
        raise SystemExit("openai package required. pip install openai")

    client = OpenAI()
    system = _build_system_prompt(manifest)
    user = (
        "Generate the full documentation output: FDD, BDD, ADD in Markdown, and four Mermaid diagrams "
        "(architecture, state-machine, class, database-entity). Use only evidence from the manifest. "
        "Populate traceability so every section and every diagram node/edge/entity references an evidence_path from the manifest."
    )

    # Structured Outputs: response_format with json_schema
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format=DOCUMENTATION_OUTPUT_SCHEMA,
    )
    choice = resp.choices[0]
    if getattr(choice, "refusal", None):
        raise SystemExit("Model refused the request")
    text = choice.message.content
    return json.loads(text)


def _write_outputs(repo_path: str, data: dict, commit: str) -> None:
    repo = Path(repo_path)
    docs_dir = repo / pipeline_config.APPROVED_DOCS_DIR
    diagrams_dir = repo / pipeline_config.APPROVED_DIAGRAMS_DIR
    docs_dir.mkdir(parents=True, exist_ok=True)
    diagrams_dir.mkdir(parents=True, exist_ok=True)

    paths_written = []

    # Docs
    for key, filename in [
        ("fdd_markdown", "fdd.md"),
        ("bdd_markdown", "bdd.md"),
        ("add_markdown", "add.md"),
    ]:
        content = data.get(key) or ""
        path = docs_dir / filename
        path.write_text(content, encoding="utf-8")
        paths_written.append(str(path.relative_to(repo)))

    # Diagrams (Mermaid)
    for key, filename in [
        ("architecture_mermaid", "architecture.mmd"),
        ("state_machine_mermaid", "state-machine.mmd"),
        ("class_mermaid", "class.mmd"),
        ("database_entity_mermaid", "database-entity.mmd"),
    ]:
        content = data.get(key) or ""
        path = diagrams_dir / filename
        path.write_text(content, encoding="utf-8")
        paths_written.append(str(path.relative_to(repo)))

    # Save generation output for validation (traceability + paths)
    out = {
        "commit": commit,
        "paths_written": paths_written,
        "traceability": data.get("traceability", []),
        "evidence_ids": [],  # validator will inject from manifest if needed
    }
    tmp = repo / ".tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    gen_path = tmp / "generation_output.json"
    with open(gen_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    paths_written.append(str(gen_path.relative_to(repo)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, help="Path to evidence manifest JSON")
    parser.add_argument("--repo", default=".", help="Repository root")
    parser.add_argument("--commit", default="", help="Commit SHA")
    args = parser.parse_args()

    manifest = _load_manifest(args.manifest)
    commit = args.commit or manifest.get("commit", "unknown")

    data = _call_openai(manifest)
    _write_outputs(args.repo, data, commit)
    print("Generated FDD, BDD, ADD and 4 diagrams in approved paths.", file=sys.stderr)


if __name__ == "__main__":
    main()
