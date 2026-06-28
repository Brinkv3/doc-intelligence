"""Document classifier.

Uses Claude to classify a document into one of the predefined types.
Returns the classified type, confidence score, and reasoning. The classifier
uses the schema definitions to know what types exist and their distinguishing
characteristics — adding a new schema file automatically makes it a
classifiable type.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import anthropic

from .ingest import Document
from .schema_loader import get_available_types

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"


def _parse_json_response(text: str) -> dict[str, Any]:
    """Extract a JSON object from a model response, handling markdown fences."""
    import re

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
MAX_DOC_CHARS = 50_000


@dataclass
class ClassificationResult:
    """Result of classifying a single document."""

    document_id: str
    document_type: str
    confidence: int
    reasoning: str
    raw_response: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_type": self.document_type,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


def classify_document(
    document: Document,
    client: anthropic.Anthropic | None = None,
) -> ClassificationResult:
    """Classify a document into one of the predefined types.

    Uses the extraction schemas to determine available types and their
    distinguishing characteristics.
    """
    client = client or anthropic.Anthropic()
    available_types = get_available_types()

    type_descriptions = "\n\n".join(
        f"**{t['document_type']}** ({t['display_name']})\n"
        f"Description: {t['description']}\n"
        f"Distinguishing characteristics:\n"
        + "\n".join(f"  - {c}" for c in t.get("distinguishing_characteristics", []))
        for t in available_types
    )

    valid_types = [t["document_type"] for t in available_types]

    doc_text = document.text[:MAX_DOC_CHARS]
    if len(document.text) > MAX_DOC_CHARS:
        doc_text += f"\n\n[... truncated, {len(document.text) - MAX_DOC_CHARS} chars remaining]"

    system_prompt = (
        "You are a document classification system. You classify documents into "
        "predefined types based on their content and structure. You return structured "
        "JSON output, never prose."
    )

    user_prompt = f"""Classify the following document into one of these types:

{type_descriptions}

---

DOCUMENT (source: {document.metadata.get('source_file', document.doc_id)}):

{doc_text}

---

Respond with a JSON object containing exactly these fields:
- "document_type": one of {json.dumps(valid_types)}
- "confidence": integer 0-100 representing how confident you are in the classification
- "reasoning": 1-2 sentences explaining why this document matches the chosen type

Return ONLY the JSON object, no markdown formatting or extra text."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    response_text = response.content[0].text.strip()

    result = _parse_json_response(response_text)

    doc_type = result["document_type"]
    if doc_type not in valid_types:
        logger.warning(
            "Classifier returned unknown type '%s' for %s, falling back to closest match",
            doc_type,
            document.doc_id,
        )

    return ClassificationResult(
        document_id=document.doc_id,
        document_type=doc_type,
        confidence=int(result.get("confidence", 0)),
        reasoning=result.get("reasoning", ""),
        raw_response=result,
    )


def classify_documents(
    documents: list[Document],
    client: anthropic.Anthropic | None = None,
) -> list[ClassificationResult]:
    """Classify multiple documents. Returns results in the same order."""
    client = client or anthropic.Anthropic()
    results = []
    for doc in documents:
        try:
            result = classify_document(doc, client)
            results.append(result)
            logger.info(
                "Classified %s → %s (confidence: %d)",
                doc.doc_id,
                result.document_type,
                result.confidence,
            )
        except Exception:
            logger.exception("Failed to classify %s", doc.doc_id)
            results.append(
                ClassificationResult(
                    document_id=doc.doc_id,
                    document_type="unknown",
                    confidence=0,
                    reasoning="Classification failed due to an error.",
                )
            )
    return results
