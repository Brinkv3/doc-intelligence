"""End-to-end pipeline orchestration.

Ties together ingestion, classification, extraction, and validation into a
single callable pipeline. Designed with clean typed interfaces for external
consumption (e.g., by the MCP server repo).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm_adapter import create_client
from llm_adapter.providers.base import BaseProvider

from .ingest import Document, parse_file, parse_directory
from .classifier import classify_document, ClassificationResult
from .extractor import extract_fields, ExtractionResult
from .validator import validate_extraction, ValidationReport
from .analyzer import analyze_documents, AnalysisResult
from .assessor import build_assessment, Assessment

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Complete result from processing a single document through the pipeline."""

    document_id: str
    classification: ClassificationResult
    extraction: ExtractionResult
    validation: ValidationReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "classification": self.classification.to_dict(),
            "extraction": self.extraction.to_dict(),
            "validation": self.validation.to_dict(),
        }


def process_document(
    path: str | Path,
    client: BaseProvider | None = None,
) -> PipelineResult:
    """Process a single document through the full pipeline.

    This is the primary entry point for external consumers. Takes a file path,
    returns a structured result with classification, extraction, and validation.
    """
    client = client or create_client()

    doc = parse_file(path)
    classification = classify_document(doc, client)
    extraction = extract_fields(doc, classification.document_type, client)
    validation = validate_extraction(extraction)

    logger.info(
        "Processed %s → %s (confidence: %d, fields: %d/%d, valid: %s)",
        doc.doc_id,
        classification.document_type,
        classification.confidence,
        validation.field_summary["fields_found"],
        validation.field_summary["total_fields"],
        validation.is_valid,
    )

    return PipelineResult(
        document_id=doc.doc_id,
        classification=classification,
        extraction=extraction,
        validation=validation,
    )


def process_directory(
    path: str | Path,
    client: BaseProvider | None = None,
) -> list[PipelineResult]:
    """Process all supported documents in a directory."""
    client = client or create_client()
    documents = parse_directory(path)
    results = []

    for doc in documents:
        try:
            classification = classify_document(doc, client)
            extraction = extract_fields(doc, classification.document_type, client)
            validation = validate_extraction(extraction)

            results.append(PipelineResult(
                document_id=doc.doc_id,
                classification=classification,
                extraction=extraction,
                validation=validation,
            ))
        except Exception:
            logger.exception("Failed to process %s", doc.doc_id)

    return results


def process_and_assess(
    path: str | Path,
    client: BaseProvider | None = None,
) -> Assessment:
    """Process a directory of documents and produce a full assessment.

    This is the highest-level entry point: processes all documents, runs
    cross-document analysis, and generates a narrative assessment.
    """
    client = client or create_client()
    results = process_directory(path, client)

    classifications = [r.classification for r in results]
    extractions = [r.extraction for r in results]
    validations = [r.validation for r in results]

    analysis = analyze_documents(extractions, client) if len(results) >= 2 else None

    return build_assessment(
        classifications, extractions, validations, analysis, client
    )
