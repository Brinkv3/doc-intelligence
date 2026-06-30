"""Assessment output.

Produces the final structured assessment combining classification, extraction,
validation, and cross-document analysis into a single output: structured JSON
plus a human-readable narrative summary.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from llm_adapter import create_client
from llm_adapter.providers.base import BaseProvider

from .classifier import ClassificationResult
from .extractor import ExtractionResult
from .validator import ValidationReport
from .analyzer import AnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class Assessment:
    """Complete assessment output for a document set."""

    documents: list[dict[str, Any]]
    cross_document_analysis: AnalysisResult | None
    narrative_summary: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "documents": self.documents,
            "cross_document_analysis": self.cross_document_analysis.to_dict() if self.cross_document_analysis else None,
            "narrative_summary": self.narrative_summary,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


def build_assessment(
    classifications: list[ClassificationResult],
    extractions: list[ExtractionResult],
    validations: list[ValidationReport],
    analysis: AnalysisResult | None = None,
    client: BaseProvider | None = None,
) -> Assessment:
    """Build a complete assessment from pipeline results.

    Combines all pipeline outputs into a structured assessment with a
    human-readable narrative summary suitable for a consultant reviewing
    documents for a client engagement.
    """
    client = client or create_client()

    documents = []
    for cls, ext, val in zip(classifications, extractions, validations):
        documents.append({
            "document_id": cls.document_id,
            "classification": cls.to_dict(),
            "extraction": ext.to_dict(),
            "validation": val.to_dict(),
        })

    narrative = _generate_narrative(documents, analysis, client)

    total_fields = sum(v.field_summary["total_fields"] for v in validations)
    found_fields = sum(v.field_summary["fields_found"] for v in validations)
    total_issues = sum(len(v.issues) for v in validations)

    return Assessment(
        documents=documents,
        cross_document_analysis=analysis,
        narrative_summary=narrative,
        metadata={
            "document_count": len(documents),
            "total_fields_extracted": found_fields,
            "total_fields_expected": total_fields,
            "extraction_rate": round(found_fields / total_fields * 100, 1) if total_fields else 0,
            "validation_issues": total_issues,
            "cross_doc_findings": len(analysis.findings) if analysis else 0,
        },
    )


def _generate_narrative(
    documents: list[dict[str, Any]],
    analysis: AnalysisResult | None,
    client: BaseProvider,
) -> str:
    """Generate a human-readable narrative summary of the assessment."""

    doc_summaries = []
    for doc in documents:
        cls = doc["classification"]
        val = doc["validation"]
        summary = val["field_summary"]
        doc_summaries.append(
            f"- **{doc['document_id']}** classified as {cls['document_type']} "
            f"(confidence: {cls['confidence']}). "
            f"{summary['fields_found']}/{summary['total_fields']} fields extracted. "
            f"{'Valid' if val['is_valid'] else 'INVALID — has errors'}."
        )

    findings_text = ""
    if analysis and analysis.findings:
        findings_text = "\n\nCross-document findings:\n" + "\n".join(
            f"- [{f.severity.upper()}] {f.title}: {f.description}"
            for f in analysis.findings
            if f.finding_type in ("inconsistency", "gap")
        )

    system_prompt = (
        "You are a consulting document reviewer. Write a concise, professional "
        "narrative assessment summarizing the document analysis results. The audience "
        "is a consultant or engagement manager reviewing documents for a client "
        "engagement. Be direct, highlight risks and gaps, and recommend next steps."
    )

    user_prompt = f"""Write a narrative assessment summary based on these analysis results.

DOCUMENTS ANALYZED:
{chr(10).join(doc_summaries)}

{findings_text if findings_text else "No cross-document inconsistencies or gaps found."}

{f"Cross-document summary: {analysis.summary}" if analysis else ""}

Write 3-5 paragraphs covering:
1. Overview of what was analyzed
2. Key extraction results and data quality
3. Cross-document findings (inconsistencies, gaps, risks) if any
4. Recommendations or next steps

Be specific — reference document names, field values, and finding details. Keep it under 400 words."""

    response = client.complete(
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
        max_tokens=1000,
    )

    return response.text.strip()
