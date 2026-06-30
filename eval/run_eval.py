"""Full pipeline evaluation.

Runs the complete pipeline: ingest → classify → extract → validate →
cross-document analysis → assessment. Produces structured results and
a narrative summary.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_adapter import create_client
from src.ingest import parse_file
from src.classifier import classify_document, ClassificationResult
from src.extractor import extract_fields, ExtractionResult
from src.validator import validate_extraction, ValidationReport
from src.analyzer import analyze_documents
from src.assessor import build_assessment

EVAL_DIR = Path(__file__).parent
TEST_DOCS_DIR = EVAL_DIR / "test_documents"
GROUND_TRUTH_PATH = EVAL_DIR / "ground_truth.json"


def main() -> None:
    client = create_client()

    with open(GROUND_TRUTH_PATH) as f:
        ground_truth = json.load(f)

    classifications: list[ClassificationResult] = []
    extractions: list[ExtractionResult] = []
    validations: list[ValidationReport] = []
    classification_correct = 0

    print("=" * 70)
    print("DOCUMENT INTELLIGENCE PIPELINE — FULL EVALUATION")
    print("=" * 70)

    for entry in ground_truth["classifications"]:
        doc_path = TEST_DOCS_DIR / entry["document"]
        expected_type = entry["expected_type"]

        print(f"\n--- {entry['document']} ---")

        doc = parse_file(doc_path)

        cls = classify_document(doc, client)
        classifications.append(cls)
        match = cls.document_type == expected_type
        if match:
            classification_correct += 1
        print(f"  Classification: {cls.document_type} "
              f"({'✓' if match else '✗ expected ' + expected_type}, "
              f"confidence: {cls.confidence})")

        ext = extract_fields(doc, cls.document_type, client)
        extractions.append(ext)

        val = validate_extraction(ext)
        validations.append(val)
        s = val.field_summary
        print(f"  Extraction: {s['fields_found']}/{s['total_fields']} fields "
              f"({s['extraction_rate']}%)")
        print(f"  Validation: {'✓ valid' if val.is_valid else '✗ invalid'}, "
              f"{len(val.issues)} issue(s)")

    total = len(ground_truth["classifications"])
    print(f"\n{'='*70}")
    print(f"CLASSIFICATION: {classification_correct}/{total} "
          f"({classification_correct/total*100:.0f}%)")

    total_fields = sum(v.field_summary["total_fields"] for v in validations)
    found_fields = sum(v.field_summary["fields_found"] for v in validations)
    print(f"EXTRACTION: {found_fields}/{total_fields} fields "
          f"({found_fields/total_fields*100:.0f}%)")
    print(f"VALIDATION: {sum(1 for v in validations if v.is_valid)}/{total} valid")

    print(f"\n{'='*70}")
    print("CROSS-DOCUMENT ANALYSIS")
    print("=" * 70)

    analysis = analyze_documents(extractions, client)

    if analysis.findings:
        for f in analysis.findings:
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(f.severity, "⚪")
            print(f"\n  {icon} [{f.finding_type.upper()}] {f.title}")
            print(f"     {f.description}")
            print(f"     Documents: {', '.join(f.documents_involved)}")
    else:
        print("  No findings.")

    if analysis.summary:
        print(f"\n  Summary: {analysis.summary}")

    print(f"\n{'='*70}")
    print("GENERATING NARRATIVE ASSESSMENT")
    print("=" * 70)

    assessment = build_assessment(
        classifications, extractions, validations, analysis, client
    )

    print(f"\n{assessment.narrative_summary}")

    output_path = EVAL_DIR / "full_eval_results.json"
    with open(output_path, "w") as f:
        json.dump(assessment.to_dict(), f, indent=2, default=str)
    print(f"\n{'='*70}")
    print(f"Full results saved to {output_path}")
    print(f"Metadata: {json.dumps(assessment.metadata, indent=2)}")


if __name__ == "__main__":
    main()
