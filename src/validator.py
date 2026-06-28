"""Extraction validation.

Checks extracted fields against schema requirements and produces a validation
report. This is the quality gate before cross-document analysis — it flags
missing required fields, low-confidence extractions, and type mismatches.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from .extractor import ExtractionResult, ExtractedField

logger = logging.getLogger(__name__)

LOW_CONFIDENCE_THRESHOLD = 60


@dataclass
class ValidationIssue:
    """A single validation issue."""

    field_name: str
    issue_type: str  # missing_required, low_confidence, invalid_format
    severity: str  # error, warning
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "message": self.message,
        }


@dataclass
class ValidationReport:
    """Complete validation report for an extraction result."""

    document_id: str
    document_type: str
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    field_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_type": self.document_type,
            "is_valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues],
            "field_summary": self.field_summary,
        }


def validate_extraction(extraction: ExtractionResult) -> ValidationReport:
    """Validate an extraction result against schema requirements."""
    issues: list[ValidationIssue] = []

    total_fields = len(extraction.fields)
    found_fields = 0
    required_found = 0
    required_total = 0

    for f in extraction.fields:
        if f.required:
            required_total += 1

        if f.value is None:
            if f.required:
                issues.append(ValidationIssue(
                    field_name=f.name,
                    issue_type="missing_required",
                    severity="error",
                    message=f"Required field '{f.name}' was not found in the document",
                ))
        else:
            found_fields += 1
            if f.required:
                required_found += 1

            if f.confidence < LOW_CONFIDENCE_THRESHOLD:
                issues.append(ValidationIssue(
                    field_name=f.name,
                    issue_type="low_confidence",
                    severity="warning",
                    message=f"Field '{f.name}' extracted with low confidence ({f.confidence}/100)",
                ))

            format_issue = _check_format(f)
            if format_issue:
                issues.append(format_issue)

    has_errors = any(i.severity == "error" for i in issues)

    return ValidationReport(
        document_id=extraction.document_id,
        document_type=extraction.document_type,
        is_valid=not has_errors,
        issues=issues,
        field_summary={
            "total_fields": total_fields,
            "fields_found": found_fields,
            "fields_missing": total_fields - found_fields,
            "required_found": required_found,
            "required_total": required_total,
            "extraction_rate": round(found_fields / total_fields * 100, 1) if total_fields else 0,
        },
    )


DATE_PATTERNS = [
    r"\d{4}-\d{2}-\d{2}",
    r"\d{1,2}/\d{1,2}/\d{2,4}",
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
    r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
]

CURRENCY_PATTERN = r"[\$£€]?\s*[\d,]+(?:\.\d{2})?"


def _check_format(f: ExtractedField) -> ValidationIssue | None:
    """Check if the extracted value matches the expected format for its type."""
    if f.value is None:
        return None

    if f.field_type == "date" and isinstance(f.value, str):
        if not any(re.search(p, f.value, re.IGNORECASE) for p in DATE_PATTERNS):
            return ValidationIssue(
                field_name=f.name,
                issue_type="invalid_format",
                severity="warning",
                message=f"Field '{f.name}' value '{f.value}' may not be a valid date format",
            )

    if f.field_type == "currency" and isinstance(f.value, str):
        if not re.search(CURRENCY_PATTERN, f.value):
            return ValidationIssue(
                field_name=f.name,
                issue_type="invalid_format",
                severity="warning",
                message=f"Field '{f.name}' value '{f.value}' may not be a valid currency format",
            )

    if f.field_type.startswith("list") and not isinstance(f.value, list):
        return ValidationIssue(
            field_name=f.name,
            issue_type="invalid_format",
            severity="warning",
            message=f"Field '{f.name}' expected a list but got {type(f.value).__name__}",
        )

    return None
