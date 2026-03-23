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


def _read_existing_docs(repo_path: str) -> dict[str, str]:
    """Read current docs/diagrams from disk so the model can see what exists and update it."""
    repo = Path(repo_path)
    existing = {}
    files_to_read = {
        "fdd": repo / pipeline_config.APPROVED_DOCS_DIR / "fdd.md",
        "bdd": repo / pipeline_config.APPROVED_DOCS_DIR / "bdd.md",
        "add": repo / pipeline_config.APPROVED_DOCS_DIR / "add.md",
        "architecture_diagram": repo / pipeline_config.APPROVED_DIAGRAMS_DIR / "architecture.mmd",
        "state_machine_diagram": repo / pipeline_config.APPROVED_DIAGRAMS_DIR / "state-machine.mmd",
        "class_diagram": repo / pipeline_config.APPROVED_DIAGRAMS_DIR / "class.mmd",
        "database_entity_diagram": repo / pipeline_config.APPROVED_DIAGRAMS_DIR / "database-entity.mmd",
    }
    for key, path in files_to_read.items():
        if path.exists():
            try:
                existing[key] = path.read_text(encoding="utf-8", errors="replace")[:12000]
            except OSError:
                pass
    return existing


def _build_system_prompt(manifest: dict, existing_docs: dict[str, str]) -> str:
    evidence_ids = manifest.get("evidence_ids", [])
    primary_evidence_ids = manifest.get("primary_evidence_ids", [])
    evidence = manifest.get("evidence", {})
    commit = manifest.get("commit", "unknown")
    changed = manifest.get("changed_files", [])

    parts = [
        "You are a solution architect generating technical design documentation and diagrams for the ENTIRE repository.",
        "",
        "CRITICAL RULES:",
        "1. Your output must reflect the COMPLETE current state of the repository, not just one file.",
        "2. ALL 7 outputs (FDD, BDD, ADD, architecture diagram, state-machine diagram, class diagram, database-entity diagram) must reflect ALL evidence files.",
        "3. Every product source file in evidence must appear in at least one of the 7 outputs.",
        "4. Do not invent components, functions, classes, states, entities, or relationships not supported by evidence.",
        "5. Every element must be traceable to at least one evidence_path from evidence_ids.",
        "6. Use concrete names from the actual code (function names, class names, module names), never generic placeholders.",
        "7. If evidence is insufficient for a diagram type, write 'Not enough repository evidence' as a comment in the Mermaid source.",
        "8. DATABASE DETECTION: look for CREATE TABLE, ALTER TABLE, INSERT, sqlite3, SQLAlchemy, Django models, "
        "Sequelize, Prisma, TypeORM, Mongoose schemas, or any ORM/SQL embedded inside source files (Python, JS, etc.). "
        "These count as database evidence even when the SQL is inside string literals or executescript() calls.",
        "",
        f"Commit: {commit}.",
        f"Changed files in this commit: {', '.join(changed) if changed else 'none'}.",
        "",
        "Primary evidence paths (changed product files — these MUST be covered in ALL relevant outputs):",
        json.dumps(primary_evidence_ids, indent=2),
        "",
        "All evidence paths (use these exact strings in traceability.evidence_path):",
        json.dumps(evidence_ids, indent=2),
        "",
        "Evidence content (key = file path):",
    ]
    # Include ALL evidence: primary first, then the rest.
    primary_set = set(primary_evidence_ids)
    secondary_paths = [p for p in evidence.keys() if p not in primary_set]
    ordered_paths = list(primary_evidence_ids) + secondary_paths

    for path in ordered_paths[:200]:
        data = evidence.get(path, {})
        snippet = (data.get("content_snippet") or "")[:8000]
        parts.append(f"\n--- {path} ---\n{snippet}")

    # Feed existing docs so model can see what needs updating.
    if existing_docs:
        parts.append("\n\n=== EXISTING DOCUMENTATION (update these, do NOT regenerate from scratch) ===")
        parts.append("Compare the code evidence above against these existing docs. "
                      "Add any new modules/functions/classes that are missing. "
                      "Remove anything that no longer exists in the code. "
                      "Update anything that changed.")
        for doc_key, doc_content in existing_docs.items():
            parts.append(f"\n--- EXISTING {doc_key} ---\n{doc_content}")

    return "\n".join(parts)


def _call_openai(manifest: dict, repo_path: str) -> dict:
    try:
        from openai import OpenAI
    except ImportError:
        raise SystemExit("openai package required. pip install openai")

    client = OpenAI()
    existing_docs = _read_existing_docs(repo_path)
    system = _build_system_prompt(manifest, existing_docs)

    # ALL product source files in the repo (not just changed ones).
    NON_PRODUCT_NAMES = {
        "__init__.py", "requirements.txt", "package.json", "go.mod",
        "Cargo.toml", "pyproject.toml", "setup.py", "setup.cfg",
    }
    NON_PRODUCT_PREFIXES = ("docs/", ".github/", ".ci-build/", "scripts/", ".tmp/")
    all_product_files = [
        p for p in manifest.get("evidence_ids", [])
        if p.split("/")[-1] not in NON_PRODUCT_NAMES
        and not any(p.startswith(prefix) for prefix in NON_PRODUCT_PREFIXES)
    ]
    primary_modules = [
        p for p in manifest.get("primary_evidence_ids", [])
        if p.split("/")[-1] not in NON_PRODUCT_NAMES
    ]

    module_list_hint = ""
    if all_product_files:
        module_list_hint = (
            "\n\nThe following source files exist in the repository and MUST ALL be reflected "
            "in the documentation and diagrams (each must appear in at least one traceability entry):\n"
            + "\n".join(f"  - {m}" for m in all_product_files)
        )
    if primary_modules:
        module_list_hint += (
            "\n\nThe following files were CHANGED in this commit and need special attention "
            "(ensure they are up to date in all outputs):\n"
            + "\n".join(f"  - {m}" for m in primary_modules)
        )

    has_existing = bool(existing_docs)
    if has_existing:
        update_instruction = (
            "EXISTING DOCUMENTATION WAS PROVIDED. You must UPDATE it, not regenerate from scratch.\n"
            "- Keep all existing content that is still accurate.\n"
            "- ADD sections/nodes for any new modules, functions, classes, or files found in the code evidence.\n"
            "- REMOVE sections/nodes for anything no longer present in the code.\n"
            "- UPDATE sections/nodes where the code has changed.\n"
            "- The result must reflect the COMPLETE CURRENT state of the repository.\n\n"
        )
    else:
        update_instruction = (
            "No existing documentation found. Generate fresh documentation from scratch.\n\n"
        )

    user = (
        update_instruction
        + "Produce ALL 7 outputs reflecting the ENTIRE repository:\n\n"
        "1. FDD (Functional Design Document): describe every functional capability found in ALL source files. "
        "Each source file must appear as a section or subsection.\n"
        "2. BDD (Business Design Document): describe the business logic and processes from ALL source files.\n"
        "3. ADD (Architecture Design Document): describe the system architecture covering ALL modules/components.\n"
        "4. Architecture diagram (Mermaid): show ALL modules and their relationships.\n"
        "5. State Machine diagram (Mermaid): show states/transitions from ALL relevant modules.\n"
        "6. Class diagram (Mermaid): show classes/functions from ALL source files.\n"
        "7. Database Entity diagram (Mermaid erDiagram): extract ALL tables/entities from SQL statements "
        "(CREATE TABLE, ALTER TABLE), ORM model definitions, or schema files found ANYWHERE in the evidence — "
        "including inside Python/JS/TS string literals, executescript() calls, or migration files. "
        "Show columns, types, and relationships (FK, references). "
        "Only state 'No database evidence' if there are truly zero SQL or ORM patterns in ANY evidence file.\n\n"
        "Populate traceability so every section and every diagram node/edge references an evidence_path from evidence_ids.\n"
        "Every source file in primary_evidence_ids MUST be explicitly covered in ALL relevant outputs (docs AND diagrams)."
        + module_list_hint
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

    def _uncovered_modules(data: dict, required_modules: list[str]) -> list[str]:
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

    # Retry once if traceability paths are outside manifest evidence IDs
    # or any product file is missing from coverage.
    invalid = _invalid_traceability_paths(data, valid_ids)
    missing = _uncovered_modules(data, all_product_files)
    if invalid or missing:
        repair_parts = []
        if invalid:
            repair_parts.append(
                "Your previous output used traceability evidence_path values that are not in the manifest.\n"
                "Fix ALL traceability.evidence_path to use ONLY values from evidence_ids.\n"
                "Invalid evidence paths were:\n"
                + json.dumps(invalid, indent=2)
                + "\nAllowed evidence_ids are:\n"
                + json.dumps(manifest.get("evidence_ids", []), indent=2)
            )
        if missing:
            repair_parts.append(
                "Your previous output did not include traceability coverage for all product source files.\n"
                "Ensure each file below appears in traceability.evidence_path at least once "
                "and is reflected in docs/diagrams:\n"
                + json.dumps(missing, indent=2)
            )
        data = _request(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
                {"role": "user", "content": "\n\n".join(repair_parts)},
            ]
        )
        invalid = _invalid_traceability_paths(data, valid_ids)
        missing = _uncovered_modules(data, all_product_files)
        if invalid:
            raise SystemExit(
                "Traceability repair failed; invalid evidence_path values: "
                + ", ".join(invalid[:10])
            )
        if missing:
            print(
                "WARNING: coverage repair incomplete; missing coverage for: "
                + ", ".join(missing[:10]),
                file=sys.stderr,
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

    # Strip traceability entries where the model returned an empty evidence_path
    # (happens when the repo has no real evidence for a required output, e.g. database diagrams).
    clean_trace = [
        t for t in data.get("traceability", [])
        if t.get("evidence_path", "").strip()
    ]

    out = {
        "commit": commit,
        "paths_written": paths_written,
        "traceability": clean_trace,
        "evidence_ids": [],
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

    data = _call_openai(manifest, args.repo)
    _write_outputs(args.repo, data, commit)
    print("Generated FDD, BDD, ADD and 4 diagrams in approved paths.", file=sys.stderr)


if __name__ == "__main__":
    main()
