"""Cross-document analysis.

Compares extracted fields across multiple documents to identify
inconsistencies, gaps, and cross-references. This is the high-value
capability — individual extraction is useful, but cross-document analysis
is where the real insight lives.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from llm_adapter import create_client
from llm_adapter.providers.base import BaseProvider

from .extractor import ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class CrossDocFinding:
    """A single cross-document finding."""

    finding_type: str  # inconsistency, gap, cross_reference
    severity: str  # high, medium, low
    title: str
    description: str
    documents_involved: list[str]
    field_references: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_type": self.finding_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "documents_involved": self.documents_involved,
            "field_references": self.field_references,
        }


@dataclass
class AnalysisResult:
    """Complete cross-document analysis result."""

    document_ids: list[str]
    findings: list[CrossDocFinding] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_ids": self.document_ids,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
        }


def analyze_documents(
    extractions: list[ExtractionResult],
    client: BaseProvider | None = None,
) -> AnalysisResult:
    """Perform cross-document analysis on a set of extraction results.

    Compares extracted fields across documents to find:
    - Inconsistencies: conflicting values for the same entity (dates, amounts, names)
    - Gaps: expected cross-references that are missing (SOW deliverable with no
      corresponding project plan milestone)
    - Cross-references: confirmed alignments between documents
    """
    if len(extractions) < 2:
        return AnalysisResult(
            document_ids=[e.document_id for e in extractions],
            summary="Cross-document analysis requires at least 2 documents.",
        )

    client = client or create_client()

    extractions_summary = _build_extractions_summary(extractions)

    system_prompt = (
        "You are a cross-document analysis system for consulting and enterprise "
        "documents. You compare extracted fields across multiple documents to identify "
        "inconsistencies, gaps, and cross-references. You return structured JSON output. "
        "Every finding must cite the specific documents and fields involved."
    )

    user_prompt = f"""Analyze the following extracted fields from multiple documents for inconsistencies, gaps, and cross-references.

EXTRACTED DATA FROM DOCUMENTS:

{extractions_summary}

---

Perform cross-document analysis and return a JSON object with this structure:
{{
  "findings": [
    {{
      "finding_type": "inconsistency" | "gap" | "cross_reference",
      "severity": "high" | "medium" | "low",
      "title": "Short title for the finding",
      "description": "Detailed explanation of what was found",
      "documents_involved": ["doc1.md", "doc2.md"],
      "field_references": [
        {{"document": "doc1.md", "field": "field_name", "value": "the value"}}
      ]
    }}
  ],
  "summary": "2-3 sentence overall assessment of cross-document consistency"
}}

Analysis guidelines:
- **Inconsistencies**: Look for conflicting dates, amounts, names, or terms across documents. For example, a SOW says the project ends August 31 but the project plan says August 30.
- **Gaps**: Look for expected cross-references that are missing. For example, a SOW lists a deliverable that has no corresponding milestone in the project plan, or a status report references a milestone not in the project plan.
- **Cross-references**: Note confirmed alignments — values that match correctly across documents, especially for important fields like dates, amounts, and deliverables.
- Severity: high = financial or legal impact (wrong amounts, dates, parties), medium = operational impact (missing milestones, unclear dependencies), low = minor discrepancies or informational.
- Only report findings that involve at least 2 documents.
- Be precise — cite exact values from the extractions.

Return ONLY the JSON object."""

    response = client.complete(
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
        max_tokens=8192,
    )

    response_text = response.text.strip()
    parsed = _parse_json_response(response_text)

    findings = [
        CrossDocFinding(
            finding_type=f.get("finding_type", "unknown"),
            severity=f.get("severity", "medium"),
            title=f.get("title", ""),
            description=f.get("description", ""),
            documents_involved=f.get("documents_involved", []),
            field_references=f.get("field_references", []),
        )
        for f in parsed.get("findings", [])
    ]

    return AnalysisResult(
        document_ids=[e.document_id for e in extractions],
        findings=findings,
        summary=parsed.get("summary", ""),
    )


def _build_extractions_summary(extractions: list[ExtractionResult]) -> str:
    """Build a readable summary of all extractions for the analysis prompt."""
    parts = []
    for ext in extractions:
        lines = [f"### {ext.document_id} (type: {ext.document_type})"]
        for f in ext.fields:
            if f.value is not None:
                value_str = json.dumps(f.value) if isinstance(f.value, (list, dict)) else str(f.value)
                if len(value_str) > 200:
                    value_str = value_str[:197] + "..."
                lines.append(f"- {f.name}: {value_str}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def _parse_json_response(text: str) -> dict[str, Any]:
    """Extract a JSON object from a model response, handling markdown fences."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    if text.startswith("```"):
        inner = re.sub(r"^```(?:json)?\s*\n", "", text)
        inner = re.sub(r"\n\s*```\s*$", "", inner)
        try:
            return json.loads(inner.strip())
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
