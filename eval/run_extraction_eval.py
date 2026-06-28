"""Extraction + validation evaluation.

Classifies each test document, extracts fields per schema, validates the
extraction, and reports results. Tests the full classify → extract → validate
pipeline.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest import parse_file
from src.classifier import classify_document
from src.extractor import extract_fields
from src.validator import validate_extraction

EVAL_DIR = Path(__file__).parent
TEST_DOCS_DIR = EVAL_DIR / "test_documents"
GROUND_TRUTH_PATH = EVAL_DIR / "ground_truth.json"


def main() -> None:
    with open(GROUND_TRUTH_PATH) as f:
        ground_truth = json.load(f)

    all_results = []

    for entry in ground_truth["classifications"]:
        doc_path = TEST_DOCS_DIR / entry["document"]
        expected_type = entry["expected_type"]

        print(f"\n{'='*70}")
        print(f"Document: {entry['document']}")
        print(f"{'='*70}")

        doc = parse_file(doc_path)

        print(f"\n--- Classification ---")
        classification = classify_document(doc)
        print(f"Type: {classification.document_type} (confidence: {classification.confidence})")

        doc_type = classification.document_type

        print(f"\n--- Extraction ({doc_type}) ---")
        extraction = extract_fields(doc, doc_type)

        for field in extraction.fields:
            status = "✓" if field.value is not None else "✗"
            value_preview = _preview_value(field.value)
            print(f"  {status} {field.name}: {value_preview} "
                  f"(confidence: {field.confidence}, source: {field.source_location})")

        print(f"\n--- Validation ---")
        validation = validate_extraction(extraction)
        summary = validation.field_summary
        print(f"Valid: {validation.is_valid}")
        print(f"Fields: {summary['fields_found']}/{summary['total_fields']} found "
              f"({summary['extraction_rate']}%)")
        print(f"Required: {summary['required_found']}/{summary['required_total']}")

        if validation.issues:
            print(f"\nIssues ({len(validation.issues)}):")
            for issue in validation.issues:
                icon = "❌" if issue.severity == "error" else "⚠️"
                print(f"  {icon} [{issue.issue_type}] {issue.message}")
        else:
            print("No issues found.")

        all_results.append({
            "document": entry["document"],
            "classification": classification.to_dict(),
            "extraction": extraction.to_dict(),
            "validation": validation.to_dict(),
        })

    output_path = EVAL_DIR / "extraction_results.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n{'='*70}")
    print(f"Full results saved to {output_path}")


def _preview_value(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, list):
        return f"[{len(value)} items]"
    s = str(value)
    return s if len(s) <= 80 else s[:77] + "..."


if __name__ == "__main__":
    main()
