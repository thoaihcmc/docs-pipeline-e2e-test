"""
JSON Schema for OpenAI Structured Outputs: FDD, BDD, ADD and 4 diagram types.
Every generated element must be traceable via traceability references to evidence in the manifest.
"""

# OpenAI Structured Outputs expect this shape; "strict" mode with additionalProperties: false
DOCUMENTATION_OUTPUT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "documentation_output",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "fdd_markdown": {"type": "string", "description": "Functional Design Document in Markdown"},
                "bdd_markdown": {"type": "string", "description": "Business Design Document in Markdown"},
                "add_markdown": {"type": "string", "description": "Architecture Design Document in Markdown"},
                "architecture_mermaid": {"type": "string", "description": "Mermaid source for Architecture diagram"},
                "state_machine_mermaid": {"type": "string", "description": "Mermaid source for State Machine diagram"},
                "class_mermaid": {"type": "string", "description": "Mermaid source for Class diagram"},
                "database_entity_mermaid": {"type": "string", "description": "Mermaid source for Database Entity diagram"},
                "traceability": {
                    "type": "array",
                    "description": "Each generated element must reference at least one evidence path from the manifest",
                    "items": {
                        "type": "object",
                        "properties": {
                            "element_id": {"type": "string", "description": "Identifier of the generated element (e.g. section title, node id)"},
                            "element_type": {
                                "type": "string",
                                "enum": ["fdd_section", "bdd_section", "add_section", "architecture_node", "architecture_edge", "state_machine_state", "state_machine_transition", "class_diagram_class", "class_diagram_relation", "database_entity", "database_relation"],
                                "description": "Type of the generated element",
                            },
                            "evidence_path": {"type": "string", "description": "Path from evidence manifest (must exist in manifest.evidence_ids)"},
                        },
                        "required": ["element_id", "element_type", "evidence_path"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": [
                "fdd_markdown",
                "bdd_markdown",
                "add_markdown",
                "architecture_mermaid",
                "state_machine_mermaid",
                "class_mermaid",
                "database_entity_mermaid",
                "traceability",
            ],
            "additionalProperties": False,
        },
    },
}
