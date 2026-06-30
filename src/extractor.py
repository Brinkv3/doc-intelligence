"""Structured field extraction.

Uses Claude to extract typed fields from a document according to its
extraction schema. Every extracted field includes a value, confidence score,
and source location citing where in the document the value was found.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from llm_adapter import create_client
from llm_adapter.providers.base import BaseProvider

from .ingest import Document
from .schema_loader import load_schema

logger = logging.getLogger(__name__)
MAX_DOC_CHARS = 80_000


@dataclass
class ExtractedField:
    """A single extracted field with provenance."""

    name: str
    value: Any
    confidence: int
    source_location: str
    field_type: str
    required: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "confidence": self.confidence,
            "source_location": self.source_location,
            "field_type": self.field_type,
            "required": self.required,
        }


@dataclass
class ExtractionResult:
    """Complete extraction result for a single document."""

    document_id: str
    document_type: str
    fields: list[ExtractedField] = field(default_factory=list)
    raw_response: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_type": self.document_type,
            "fields": [f.to_dict() for f in self.fields],
        }

    def get_field(self, name: str) -> ExtractedField | None:
        for f in self.fields:
            if f.name == name:
                return f
        return None


def extract_fields(
    document: Document,
    document_type: str,
    client: BaseProvider | None = None,
) -> ExtractionResult:
    """Extract structured fields from a document according to its schema."""
    client = client or create_client()
    schema = load_schema(document_type)

    fields_spec = "\n".join(
        f"- **{f['name']}** (type: {f['type']}, {'REQUIRED' if f.get('required') else 'optional'}): "
        f"{f.get('description', '')}"
        for f in schema["fields"]
    )

    doc_text = document.text[:MAX_DOC_CHARS]
    if len(document.text) > MAX_DOC_CHARS:
        doc_text += f"\n\n[... truncated, {len(document.text) - MAX_DOC_CHARS} chars remaining]"

    system_prompt = (
        "You are a document field extraction system. You extract structured data "
        "from documents according to a provided schema. You return structured JSON "
        "output. You only extract what is explicitly present in the document — never "
        "fabricate or infer values that aren't stated. Every extracted value must cite "
        "where in the document it was found."
    )

    user_prompt = f"""Extract the following fields from this {schema.get('display_name', document_type)} document.

FIELDS TO EXTRACT:
{fields_spec}

DOCUMENT (source: {document.metadata.get('source_file', document.doc_id)}):

{doc_text}

---

For each field, return a JSON object with this structure:
{{
  "fields": [
    {{
      "name": "field_name",
      "value": <extracted value — string, number, list, or object as appropriate for the type>,
      "confidence": <integer 0-100>,
      "source_location": "brief citation of where in the document this was found (e.g., 'Section 3, paragraph 2' or 'Page 1, under Parties')"
    }}
  ]
}}

Rules:
- Extract ONLY what is explicitly stated in the document
- If a field is not present in the document, set value to null and confidence to 0
- For list types, extract all items found
- For object types within lists (like milestones), extract available sub-fields
- source_location should help a human find the value in the original document
- Return ONLY the JSON object"""

    response = client.complete(
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
        max_tokens=4096,
    )

    response_text = response.text.strip()
    parsed = _parse_json_response(response_text)

    schema_fields = {f["name"]: f for f in schema["fields"]}
    extracted_fields = []

    for raw_field in parsed.get("fields", []):
        name = raw_field.get("name", "")
        schema_field = schema_fields.get(name, {})
        extracted_fields.append(
            ExtractedField(
                name=name,
                value=raw_field.get("value"),
                confidence=int(raw_field.get("confidence", 0)),
                source_location=raw_field.get("source_location", ""),
                field_type=schema_field.get("type", "unknown"),
                required=schema_field.get("required", False),
            )
        )

    for name, schema_field in schema_fields.items():
        if not any(f.name == name for f in extracted_fields):
            extracted_fields.append(
                ExtractedField(
                    name=name,
                    value=None,
                    confidence=0,
                    source_location="not found in document",
                    field_type=schema_field.get("type", "unknown"),
                    required=schema_field.get("required", False),
                )
            )

    return ExtractionResult(
        document_id=document.doc_id,
        document_type=document_type,
        fields=extracted_fields,
        raw_response=parsed,
    )


def _parse_json_response(text: str) -> dict[str, Any]:
    """Extract a JSON object from a model response, handling markdown fences."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    brace_start = text.find("{")
    if brace_start != -1:
        depth = 0
        for i, ch in enumerate(text[brace_start:], brace_start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[brace_start : i + 1])

    raise ValueError(f"Could not parse JSON from response: {text[:200]}")
