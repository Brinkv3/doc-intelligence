"""Classification evaluation.

Tests the classifier against the sample documents with known ground truth.
Reports accuracy and per-document results.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest import parse_file
from src.classifier import classify_document

EVAL_DIR = Path(__file__).parent
TEST_DOCS_DIR = EVAL_DIR / "test_documents"
GROUND_TRUTH_PATH = EVAL_DIR / "ground_truth.json"


def main() -> None:
    with open(GROUND_TRUTH_PATH) as f:
        ground_truth = json.load(f)

    correct = 0
    total = 0
    results = []

    for entry in ground_truth["classifications"]:
        doc_path = TEST_DOCS_DIR / entry["document"]
        expected = entry["expected_type"]

        print(f"\n{'='*60}")
        print(f"Document: {entry['document']}")
        print(f"Expected: {expected}")

        doc = parse_file(doc_path)
        result = classify_document(doc)

        match = result.document_type == expected
        if match:
            correct += 1
        total += 1

        print(f"Predicted: {result.document_type}")
        print(f"Confidence: {result.confidence}")
        print(f"Reasoning: {result.reasoning}")
        print(f"Result: {'✓ CORRECT' if match else '✗ WRONG'}")

        results.append({
            "document": entry["document"],
            "expected": expected,
            "predicted": result.document_type,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "correct": match,
        })

    print(f"\n{'='*60}")
    print(f"CLASSIFICATION ACCURACY: {correct}/{total} ({correct/total*100:.0f}%)")
    print(f"{'='*60}")

    output_path = EVAL_DIR / "classification_results.json"
    with open(output_path, "w") as f:
        json.dump({"accuracy": correct / total, "correct": correct, "total": total, "results": results}, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
