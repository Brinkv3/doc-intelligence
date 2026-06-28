"""Schema loader.

Loads extraction schemas from the schemas/ directory. Each schema is a JSON
file defining the fields to extract for a given document type. Adding a new
document type means adding a new JSON file — no code changes required.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"


def load_schema(document_type: str, schemas_dir: Path | None = None) -> dict[str, Any]:
    """Load the extraction schema for a given document type.

    Returns the full schema dict including fields, description, and
    distinguishing characteristics.
    """
    schemas_dir = schemas_dir or SCHEMAS_DIR
    schema_path = schemas_dir / f"{document_type}.json"
    if not schema_path.is_file():
        raise FileNotFoundError(
            f"No schema found for document type '{document_type}' "
            f"(expected {schema_path})"
        )
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    logger.info("Loaded schema for '%s' (%d fields)", document_type, len(schema.get("fields", [])))
    return schema


def load_all_schemas(schemas_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load all available extraction schemas.

    Returns a dict mapping document_type -> schema.
    """
    schemas_dir = schemas_dir or SCHEMAS_DIR
    schemas: dict[str, dict[str, Any]] = {}
    for path in sorted(schemas_dir.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                schema = json.load(f)
            doc_type = schema.get("document_type", path.stem)
            schemas[doc_type] = schema
            logger.info("Loaded schema: %s (%d fields)", doc_type, len(schema.get("fields", [])))
        except Exception:
            logger.exception("Failed to load schema: %s", path.name)
    return schemas


def get_available_types(schemas_dir: Path | None = None) -> list[dict[str, str]]:
    """Return a list of available document types with their descriptions.

    Used by the classifier to know what types exist and how to distinguish them.
    """
    schemas = load_all_schemas(schemas_dir)
    return [
        {
            "document_type": schema["document_type"],
            "display_name": schema.get("display_name", schema["document_type"]),
            "description": schema.get("description", ""),
            "distinguishing_characteristics": schema.get("distinguishing_characteristics", []),
        }
        for schema in schemas.values()
    ]
