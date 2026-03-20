"""
Pipeline configuration: approved paths and constants.
All outputs must be under these paths; validation fails otherwise.
"""
import os

# Approved paths (relative to repo root)
APPROVED_DOCS_DIR = "docs"
APPROVED_DIAGRAMS_DIR = os.path.join(APPROVED_DOCS_DIR, "diagrams")

# Required documentation files (under APPROVED_DOCS_DIR)
REQUIRED_DOCS = ["fdd.md", "bdd.md", "add.md"]

# Required diagram files (under APPROVED_DIAGRAMS_DIR)
REQUIRED_DIAGRAMS = [
    "architecture.mmd",
    "state-machine.mmd",
    "class.mmd",
    "database-entity.mmd",
]

def get_approved_docs_path(filename: str) -> str:
    return os.path.join(APPROVED_DOCS_DIR, filename)

def get_approved_diagram_path(filename: str) -> str:
    return os.path.join(APPROVED_DIAGRAMS_DIR, filename)

def get_all_approved_output_paths() -> list[str]:
    paths = [get_approved_docs_path(f) for f in REQUIRED_DOCS]
    paths.extend([get_approved_diagram_path(f) for f in REQUIRED_DIAGRAMS])
    return paths
