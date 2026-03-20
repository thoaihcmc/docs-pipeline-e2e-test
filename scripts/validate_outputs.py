#!/usr/bin/env python3
"""
Validation gate: fail if required outputs are missing, any element is untraceable,
or any modified file is outside approved paths.
"""
import argparse
import json
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import config as pipeline_config


def _load_generation_output(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_manifest(manifest_path: str) -> dict:
    path = Path(manifest_path)
    if not path.exists():
        return {"evidence_ids": [], "evidence": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_required_outputs(repo_path: str) -> list[str]:
    """Return list of missing required file paths."""
    repo = Path(repo_path)
    missing = []
    for f in pipeline_config.REQUIRED_DOCS:
        if not (repo / pipeline_config.APPROVED_DOCS_DIR / f).exists():
            missing.append(pipeline_config.get_approved_docs_path(f))
    for f in pipeline_config.REQUIRED_DIAGRAMS:
        if not (repo / pipeline_config.get_approved_diagram_path(f)).exists():
            missing.append(pipeline_config.get_approved_diagram_path(f))
    return missing


def validate_paths_only_approved(paths_written: list[str]) -> list[str]:
    """Return list of paths that are outside approved output locations."""
    approved = set(pipeline_config.get_all_approved_output_paths())
    # Allow .tmp/generation_output.json for validation artifact
    approved.add(".tmp/generation_output.json")
    disallowed = []
    for p in paths_written or []:
        norm = p.replace("\\", "/")
        if norm in approved:
            continue
        # Check if under approved dirs
        if norm.startswith(pipeline_config.APPROVED_DOCS_DIR + "/") or norm == pipeline_config.APPROVED_DOCS_DIR:
            continue
        if norm.startswith(".tmp/"):
            continue
        disallowed.append(p)
    return disallowed


def validate_traceability(
    generation_output: dict,
    evidence_ids: list[str],
    require_traceability: bool,
) -> list[str]:
    """Return list of traceability errors (element_id or evidence_path not in manifest)."""
    errors = []
    evidence_set = set(evidence_ids or [])
    trace = generation_output.get("traceability") or []

    for t in trace:
        eid = t.get("element_id")
        etype = t.get("element_type")
        path = t.get("evidence_path")
        if not path:
            errors.append(f"Missing evidence_path for element_id={eid}")
            continue
        if require_traceability and path not in evidence_set:
            errors.append(f"evidence_path not in manifest: {path} (element_id={eid}, type={etype})")

    if require_traceability and not trace:
        errors.append("No traceability entries; at least one element must reference manifest evidence.")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="Repository root (with docs/ and optional manifest)")
    parser.add_argument("--generation-output", default=".tmp/generation_output.json", help="Path to generation_output.json")
    parser.add_argument("--require-traceability", action="store_true", help="Fail if traceability is missing or invalid")
    parser.add_argument("--manifest", default=None, help="Path to manifest (default: repo/manifest.json if present)")
    args = parser.parse_args()

    repo = Path(args.repo)
    gen_path = repo / args.generation_output
    if not gen_path.exists():
        print(f"ERROR: Generation output not found: {gen_path}", file=sys.stderr)
        sys.exit(1)

    gen = _load_generation_output(str(gen_path))
    manifest_path = args.manifest or str(repo / "manifest.json")
    manifest = _load_manifest(manifest_path)
    evidence_ids = manifest.get("evidence_ids", [])

    failed = False

    # 1. Required outputs present
    missing = validate_required_outputs(str(repo))
    if missing:
        print("ERROR: Missing required outputs:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        failed = True

    # 2. No file outside approved paths
    paths_written = gen.get("paths_written") or []
    disallowed = validate_paths_only_approved(paths_written)
    if disallowed:
        print("ERROR: Modified files outside approved paths:", file=sys.stderr)
        for d in disallowed:
            print(f"  - {d}", file=sys.stderr)
        failed = True

    # 3. Traceability
    if args.require_traceability or os.environ.get("FAIL_ON_UNTRACEABLE"):
        trace_errors = validate_traceability(gen, evidence_ids, require_traceability=True)
        if trace_errors:
            print("ERROR: Traceability validation failed:", file=sys.stderr)
            for e in trace_errors:
                print(f"  - {e}", file=sys.stderr)
            failed = True

    if failed:
        sys.exit(1)
    print("Validation passed: required outputs present, paths approved, traceability OK.", file=sys.stderr)


if __name__ == "__main__":
    main()
