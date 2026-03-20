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
    primary_evidence_ids = manifest.get("primary_evidence_ids", [])
    evidence = manifest.get("evidence", {})
    commit = manifest.get("commit", "unknown")
    changed = manifest.get("changed_files", [])

    parts = [
        "You are a solution architect generating technical design documentation and diagrams.",
        "Your output must be based ONLY on the repository evidence provided. Do not invent components, functions, classes, states, entities, or relationships that are not supported by the evidence.",
        "Every element you generate must be traceable to at least one evidence path in the manifest (evidence_ids).",
        "Focus FIRST on primary_evidence_ids (changed product code). Do not use CI/pipeline files as the main architecture source.",
        "If primary_evidence_ids is non-empty, architecture/business/functional details MUST be derived from those files first.",
        "Prefer concrete module/function/class names from changed files (for example calculator functions), not generic placeholders.",
        "If evidence is insufficient for a section, explicitly say 'Not enough repository evidence' for that section instead of inventing details.",
        f"Commit: {commit}. Changed files in this commit: " + (", ".join(changed) if changed else "none"),
        "",
        "Primary evidence paths (prioritize these):",
        json.dumps(primary_evidence_ids, indent=2),
        "",
        "Evidence paths (use these exact strings in traceability.evidence_path):",
        json.dumps(evidence_ids, indent=2),
        "",
        "Evidence content snippets (key = path):",
    ]
    # Put primary evidence first. If available, heavily bias prompt to changed files.
    primary_set = set(primary_evidence_ids)
    secondary_paths = [p for p in evidence.keys() if p not in primary_set]
    if primary_evidence_ids:
        ordered_paths = list(primary_evidence_ids) + secondary_paths[:20]
    else:
        ordered_paths = secondary_paths[:120]

    for path in ordered_paths:
        data = evidence.get(path, {})
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
    primary_python_modules = [
        p
        for p in manifest.get("primary_evidence_ids", [])
        if p.endswith(".py") and not p.endswith("__init__.py") and "/test" not in p and not p.startswith("test")
    ]

    user = (
        "Generate the full documentation output: FDD, BDD, ADD in Markdown, and four Mermaid diagrams "
        "(architecture, state-machine, class, database-entity). Use only evidence from the manifest. "
        "Populate traceability so every section and every diagram node/edge/entity references an evidence_path from the manifest. "
        "If there are changed files in primary_evidence_ids, explicitly reflect their logic in FDD/BDD/ADD and diagram nodes/edges. "
        "For changed Python modules, include each one explicitly in the documentation (or state not enough evidence for that module), "
        "and include traceability entries for each changed module."
    )

    def _request(messages: list[dict]) -> dict:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format=DOCUMENTATION_OUTPUT_SCHEMA,
        )
        choice = resp.choices[0]
        if getattr(choice, "refusal", None):
            raise SystemExit("Model refused the request")
        return json.loads(choice.message.content)

    def _invalid_traceability_paths(data: dict, valid_ids: set[str]) -> list[str]:
        invalid = []
        for t in data.get("traceability", []):
            p = t.get("evidence_path")
            if p and p not in valid_ids:
                invalid.append(p)
        return sorted(set(invalid))

    def _uncovered_primary_modules(data: dict, required_modules: list[str]) -> list[str]:
        if not required_modules:
            return []
        covered = {t.get("evidence_path") for t in data.get("traceability", []) if t.get("evidence_path")}
        return sorted([m for m in required_modules if m not in covered])

    valid_ids = set(manifest.get("evidence_ids", []))
    data = _request(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    )

    # Retry once if traceability paths are outside manifest evidence IDs.
    invalid = _invalid_traceability_paths(data, valid_ids)
    missing_module_coverage = _uncovered_primary_modules(data, primary_python_modules)
    if invalid:
        repair_user = (
            "Your previous output used traceability evidence_path values that are not in the manifest.\n"
            "Return the full schema again, preserving content where possible, but fix ALL traceability.evidence_path "
            "to use ONLY values from evidence_ids.\n"
            "Invalid evidence paths were:\n"
            + json.dumps(invalid, indent=2)
            + "\nAllowed evidence_ids are:\n"
            + json.dumps(manifest.get("evidence_ids", []), indent=2)
        )
        data = _request(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
                {"role": "user", "content": repair_user},
            ]
        )
        invalid = _invalid_traceability_paths(data, valid_ids)
        missing_module_coverage = _uncovered_primary_modules(data, primary_python_modules)
        if invalid:
            raise SystemExit(
                "Traceability repair failed; still invalid evidence_path values: "
                + ", ".join(invalid[:10])
            )
    if missing_module_coverage:
        coverage_user = (
            "Your previous output did not include traceability coverage for all changed Python modules.\n"
            "Return the full schema again, preserving content where possible, and ensure each module below appears "
            "in traceability.evidence_path at least once and is reflected in docs/diagrams.\n"
            "Modules missing coverage:\n"
            + json.dumps(missing_module_coverage, indent=2)
        )
        data = _request(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
                {"role": "user", "content": coverage_user},
            ]
        )
        invalid = _invalid_traceability_paths(data, valid_ids)
        missing_module_coverage = _uncovered_primary_modules(data, primary_python_modules)
        if invalid:
            raise SystemExit(
                "Coverage repair produced invalid traceability evidence_path values: "
                + ", ".join(invalid[:10])
            )
        if missing_module_coverage:
            raise SystemExit(
                "Coverage repair failed; missing changed module coverage for: "
                + ", ".join(missing_module_coverage[:10])
            )

    return data


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
