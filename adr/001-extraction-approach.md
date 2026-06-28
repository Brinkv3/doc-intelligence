# ADR 001: Structured Extraction Approach

## Status
Accepted

## Context
The document intelligence pipeline needs to extract structured fields from classified documents. The extraction must produce typed values with confidence scores and source citations for auditability.

## Decision
Use Claude with schema-driven prompting for extraction. Each document type has a JSON schema defining the fields to extract. The extraction prompt includes the schema definition, the document text, and explicit instructions to extract only what is present (no fabrication).

Key design choices:
- **One API call per document.** The full schema is included in a single extraction prompt rather than making separate calls per field. This reduces latency and cost while letting the model reason across fields (e.g., recognizing that "parties" and "client_name" come from the same section).
- **Confidence + source citation per field.** Every extracted value includes a 0-100 confidence score and a human-readable source location. This enables downstream validation and makes extractions auditable.
- **Null for missing fields.** Fields not found in the document are returned as null with confidence 0, rather than omitted. This ensures the output schema is consistent regardless of document completeness.
- **Validation as a separate stage.** Extraction produces raw results; validation checks them against schema requirements (required fields, confidence thresholds, format checks). Keeping these separate allows the validator to be tested independently and reused across extraction methods.

## Consequences
- Adding a new document type requires only a new JSON schema file — no changes to extraction code
- Extraction quality depends on prompt design and model capability — evaluated via the test corpus
- Single-call extraction may miss nuance in very long documents; MAX_DOC_CHARS truncation is the trade-off for cost/latency
- Source citations are model-generated and approximate — they point to the right area but aren't exact character offsets
