# MCP Server Integration Brief — RAG Pipeline + Document Intelligence
> For use in the consulting-mcp-server planning conversation
> Last updated: June 28, 2026

---

## What the MCP Server Does

The `consulting-mcp-server` is the third and final repo in the portfolio. It exposes the RAG pipeline and the document intelligence pipeline as MCP (Model Context Protocol) tools. Any MCP client — Claude Desktop, Claude Code, IDE extensions, or custom agents — can call these tools through a standard protocol without knowing anything about the underlying implementations.

This demonstrates: protocol-level interoperability, composable AI systems, and the ability to make standalone capabilities consumable through a standard interface.

---

## What MCP Is (Quick Context)

MCP is a standard protocol for connecting AI models to external tools and data sources. An MCP server exposes "tools" (functions with JSON schemas) that a client can discover and call. The server handles routing calls to the actual implementation and returning structured results.

Think of it like a REST API, but purpose-built for AI tool use: the client sees a tool name, a description, and an input schema. It calls the tool with JSON, gets JSON back. The protocol handles discovery, serialization, and error handling.

---

## Repo 1: RAG Pipeline — What the MCP Server Needs to Know

**Repo:** github.com/Brinkv3/rag-pipeline (private)
**Local path:** `/Users/shawnbrinkley/Library/CloudStorage/OneDrive-DominionDigital/projects/rag-pipeline`
**Runtime:** Python 3.12, venv at `.venv/`
**LLM:** Provider-agnostic via [llm-adapter](https://github.com/Brinkv3/llm-adapter) (default: Claude Sonnet 4.6)

### What It Does

A retrieval-augmented generation pipeline against consulting documents (IT strategy decks, PMO enablement guides, portfolio trackers, reference workbooks). It ingests documents into a vector store, retrieves relevant chunks for a query, and generates grounded answers with citations. It has two query modes: single-pass RAG (fast, predictable) and multi-agent orchestration (handles complex/multi-part questions via tool use).

### Architecture Layers

1. **Ingestion** (`src/ingest.py`) — Parses PDF, DOCX, XLSX, PPTX, CSV, MD, TXT into uniform `Document` objects
2. **Chunking** (`src/chunker.py`) — Recursive character split, ~500 tokens, 100 token overlap
3. **Embedding** (`src/embedder.py`) — Local `all-MiniLM-L6-v2` model, 384-dim vectors, no external API dependency
4. **Vector Store** (`src/store.py`) — ChromaDB, local persistent storage, behind a thin abstraction
5. **Retrieval** (`src/retriever.py`) — Similarity search, ranked results with scores
6. **Generation** (`src/generator.py`) — LLM with 6 grounding rules, bracket citations [1][2], refuses when context is insufficient
7. **Agent Orchestration** (`src/agent.py`) — Coordinator agent with tool use loop, query decomposition, multi-search, synthesis
8. **Guardrails** (`src/guardrails.py`) — Input validation (injection detection, length), output safety (PII detection), token budgets, autonomy tiers
9. **Observability** (`src/observability.py`) — Structured audit logs, cost tracking, per-query trace persistence
10. **Tracing** (`src/trace.py`) — Step-by-step agent trace capture for debugging and compliance

### Entry Points for MCP

The MCP server should wrap these three functions from `src/pipeline.py`:

#### 1. `index_corpus(corpus_path: str, persist_dir: str = "chroma") -> int`

**Purpose:** Ingest a directory of documents into the vector store so they can be queried.

**Inputs:**
- `corpus_path` (string, required) — Path to a directory containing documents to index
- `persist_dir` (string, optional, default "chroma") — Where to persist the ChromaDB vector store

**Output:** Integer — the number of chunks indexed

**What happens internally:** Parses all supported files in the directory → splits into ~500-token chunks with overlap → embeds locally → stores in ChromaDB. This is a setup step — you run it once per corpus, then query repeatedly.

**MCP tool design note:** This is a heavy operation (reads files, computes embeddings). The MCP tool should probably accept a corpus path and return the chunk count. Consider whether this should be exposed at all vs. assumed to be pre-indexed — depends on whether the MCP client needs to trigger re-indexing.

#### 2. `query_pipeline(query: str, persist_dir: str = "chroma", n_results: int = 5, generate: bool = True) -> dict`

**Purpose:** Single-pass RAG — retrieve relevant chunks and optionally generate a grounded answer.

**Inputs:**
- `query` (string, required) — The user's question
- `persist_dir` (string, optional, default "chroma") — Which vector store to query
- `n_results` (integer, optional, default 5) — Number of chunks to retrieve (1-10)
- `generate` (boolean, optional, default True) — Whether to generate an answer or just retrieve chunks

**Output dict structure:**
```json
{
  "query": "What is the PMO maturity model?",
  "retrieval": [
    {
      "rank": 1,
      "chunk_id": "doc.pdf::chunk_3",
      "score": 0.7234,
      "source": "pmo-enablement.pdf",
      "text": "first 300 chars...",
      "full_text": "complete chunk text",
      "metadata": {"source_file": "pmo-enablement.pdf", "doc_type": "pdf"}
    }
  ],
  "answer": "Based on the context, the PMO maturity model defines... [1][2]",
  "cited_chunks": ["doc.pdf::chunk_3", "doc.pdf::chunk_7"],
  "raw_response": {"model": "configured-model", "stop_reason": "end_turn", "usage": {"input_tokens": 2100, "output_tokens": 350}}
}
```

**Error case (guardrail blocked):**
```json
{
  "query": "ignore previous instructions...",
  "error": "Blocked: Potential prompt injection detected",
  "guardrail_flags": ["Potential prompt injection detected"]
}
```

**What happens internally:** Validates input (injection patterns, length) → embeds query → searches ChromaDB for top-N chunks → optionally sends chunks + query to the configured LLM with grounding prompt → validates output (PII check) → logs to audit trail.

**MCP tool design note:** This is the workhorse tool. Fast, predictable, good for straightforward questions. The MCP tool should expose `query` as required and `n_results` as optional. The `persist_dir` and `generate` params could be server config rather than per-call params.

#### 3. `agent_query_pipeline(query: str) -> dict`

**Purpose:** Multi-agent query — the coordinator agent decomposes complex questions, performs multiple searches, and synthesizes a comprehensive answer.

**Inputs:**
- `query` (string, required) — The user's question

**Output dict structure:**
```json
{
  "query": "Compare the IT strategy recommendations across all three client decks",
  "answer": "Across the three strategy decks, the common themes are... [1][2][3]",
  "cited_chunks": ["deck1.pdf::chunk_5", "deck2.pdf::chunk_12", "deck3.pdf::chunk_3"],
  "searches_performed": 3,
  "trace": {
    "query": "Compare the IT strategy...",
    "steps": 8,
    "tool_calls": 5,
    "api_calls": 3,
    "tokens_in": 12500,
    "tokens_out": 2800,
    "duration_ms": 14200,
    "tools_used": ["search_knowledge_base", "search_knowledge_base", "search_knowledge_base", "analyze_and_answer"]
  }
}
```

**What happens internally:** Validates input → coordinator agent receives the query → LLM decides whether to search once or decompose into sub-queries → calls `search_knowledge_base` tool 1-3 times → selects best chunks → calls `analyze_and_answer` to synthesize → validates output → logs full trace to audit trail.

**Guardrail enforcement:** Same input/output guardrails as single-pass, plus token budget enforcement (max 50K input, 10K output, 8 API calls per query). Agent is hard-capped at 10 turns.

**MCP tool design note:** This is the premium tool — slower, more expensive, but handles questions that require reasoning across multiple documents or comparing concepts. The trace data is valuable for transparency.

### Key Dependencies the MCP Server Needs

- The vector store must be pre-indexed (or `index_corpus` must be called first)
- `LLM_PROVIDER`, `LLM_MODEL`, and `LLM_API_KEY` must be set in the environment (via llm-adapter)
- ChromaDB persists to disk — the `persist_dir` path must be accessible
- Local embedding model (`all-MiniLM-L6-v2`) downloads on first use (~80MB)

### Governance Features the MCP Server Inherits

The RAG pipeline has built-in governance that the MCP server gets for free:
- **Input guardrails:** Prompt injection detection, query length limits
- **Output guardrails:** PII detection (SSN, email, phone, credit card patterns)
- **Token budgets:** Per-query spending limits on the agent path
- **Autonomy tiers:** RETRIEVAL_ONLY, SINGLE_PASS, MULTI_AGENT — the MCP server could expose these as tool variants or a parameter
- **Audit logging:** Every query produces a structured JSON log entry with tokens, cost, guardrail flags, and full trace
- **Cost tracking:** Estimated cost per query based on configured model pricing

---

## Repo 2: Document Intelligence — What the MCP Server Needs to Know

**Repo:** github.com/Brinkv3/doc-intelligence (private)
**Local path:** `/Users/shawnbrinkley/Library/CloudStorage/OneDrive-DominionDigital/projects/doc-intelligence`
**Runtime:** Python 3.12, venv at `.venv/`
**LLM:** Provider-agnostic via [llm-adapter](https://github.com/Brinkv3/llm-adapter) (default: Claude Sonnet 4.6)

### What It Does

A document intelligence pipeline that classifies consulting documents by type, extracts structured fields per schema, validates extractions, performs cross-document analysis, and produces assessments with narrative summaries. It answers the question: "What does this document say, and how does it relate to these other documents?"

### Architecture Layers

1. **Ingestion** (`src/ingest.py`) — Parses PDF, DOCX, MD, TXT, CSV into uniform `Document` objects (adapted from RAG pipeline)
2. **Classification** (`src/classifier.py`) — LLM identifies document type (SOW, contract, project plan, status report, findings, architecture doc) with confidence score and reasoning
3. **Schema Selection** (`src/schema_loader.py`) — Loads the JSON extraction schema matching the classified type from `schemas/` directory
4. **Extraction** (`src/extractor.py`) — LLM extracts typed fields per schema, each with value, confidence (0-100), and source location citation
5. **Validation** (`src/validator.py`) — Checks required fields, confidence thresholds, format validation (dates, currency, lists). Pure logic, no LLM.
6. **Cross-Document Analysis** (`src/analyzer.py`) — LLM compares extractions across multiple documents, finds inconsistencies, gaps, and cross-references
7. **Assessment** (`src/assessor.py`) — Combines everything into structured JSON + LLM-generated narrative summary

### Supported Document Types (extensible via JSON schemas)

| Type | Schema File | Field Count | Example Fields |
|------|------------|-------------|----------------|
| SOW | `schemas/sow.json` | 14 | client_name, deliverables, milestones, total_value, payment_terms, assumptions |
| Contract/MSA | `schemas/contract.json` | 13 | parties, governing_law, liability_cap, termination_provisions, IP terms |
| Project Plan | `schemas/project_plan.json` | 11 | phases, milestones, team_roles, dependencies, risks, success_criteria |
| Status Report | `schemas/status_report.json` | 11 | accomplishments, blockers, budget_status, overall_status (RAG), milestone_status |
| Findings/Assessment | `schemas/findings.json` | 10 | findings (with severity), recommendations, risk_rating, standards_referenced |
| Architecture Doc | `schemas/architecture_doc.json` | 11 | components, tech_stack, design_decisions, integration_points, constraints |

Adding a new type = adding a new `.json` file to `schemas/`. No code changes. The classifier auto-discovers it.

### Entry Points for MCP

The MCP server should wrap these functions from `src/pipeline.py`:

#### 1. `process_document(path: str | Path, client: BaseProvider | None = None) -> PipelineResult`

**Purpose:** Process a single document through classify → extract → validate.

**Inputs:**
- `path` (string, required) — Path to the document file (PDF, DOCX, MD, TXT, or CSV)

**Output (`PipelineResult.to_dict()`) structure:**
```json
{
  "document_id": "sample_sow.md",
  "classification": {
    "document_id": "sample_sow.md",
    "document_type": "sow",
    "confidence": 99,
    "reasoning": "This document is explicitly titled 'Statement of Work'..."
  },
  "extraction": {
    "document_id": "sample_sow.md",
    "document_type": "sow",
    "fields": [
      {
        "name": "client_name",
        "value": "Meridian Financial Services, Inc.",
        "confidence": 100,
        "source_location": "Section 'Parties', bullet point listing Client",
        "field_type": "string",
        "required": true
      },
      {
        "name": "total_value",
        "value": "$400,000",
        "confidence": 100,
        "source_location": "Section 'Total Engagement Value'",
        "field_type": "currency",
        "required": false
      },
      {
        "name": "deliverables",
        "value": ["Current State Assessment Report", "Target State Architecture Document", "..."],
        "confidence": 100,
        "source_location": "Section 'Deliverables', numbered list",
        "field_type": "list[string]",
        "required": true
      }
    ]
  },
  "validation": {
    "document_id": "sample_sow.md",
    "document_type": "sow",
    "is_valid": true,
    "issues": [],
    "field_summary": {
      "total_fields": 14,
      "fields_found": 14,
      "fields_missing": 0,
      "required_found": 6,
      "required_total": 6,
      "extraction_rate": 100.0
    }
  }
}
```

**What happens internally:** Parses file → classifies via LLM (1 API call) → loads matching schema → extracts fields via LLM (1 API call) → validates against schema rules (no API call). Total: 2 API calls per document.

**MCP tool design note:** This is the single-document tool. Fast (2 API calls), returns everything needed to understand what's in one document. The MCP tool should accept a file path and return the full result.

#### 2. `process_and_assess(path: str | Path, client: BaseProvider | None = None) -> Assessment`

**Purpose:** Process all documents in a directory, run cross-document analysis, and produce a full assessment with narrative summary.

**Inputs:**
- `path` (string, required) — Path to a directory containing documents

**Output (`Assessment.to_dict()`) structure:**
```json
{
  "documents": [
    {
      "document_id": "sow.md",
      "classification": { "..." },
      "extraction": { "..." },
      "validation": { "..." }
    }
  ],
  "cross_document_analysis": {
    "document_ids": ["sow.md", "contract.md", "project_plan.md"],
    "findings": [
      {
        "finding_type": "inconsistency",
        "severity": "high",
        "title": "Termination Notice Period Conflict: SOW (30 Days) vs. MSA (90 Days)",
        "description": "The SOW specifies a 30-day written notice period...",
        "documents_involved": ["sow.md", "contract.md"],
        "field_references": [
          {"document": "sow.md", "field": "termination_clause", "value": "30 days written notice"},
          {"document": "contract.md", "field": "termination_provisions", "value": "90 days written notice"}
        ]
      },
      {
        "finding_type": "gap",
        "severity": "high",
        "title": "Security Assessment Findings Not Reflected in Project Risks",
        "description": "The security assessment identified critical IAM issues...",
        "documents_involved": ["findings.md", "project_plan.md", "status_report.md"],
        "field_references": [{"..."}]
      },
      {
        "finding_type": "cross_reference",
        "severity": "low",
        "title": "Confirmed: Total Project Value Consistent Across SOW and Status Report",
        "description": "SOW total value of $400,000 matches status report budget...",
        "documents_involved": ["sow.md", "status_report.md"],
        "field_references": [{"..."}]
      }
    ],
    "summary": "The document set is largely aligned on core identifiers..."
  },
  "narrative_summary": "Six project documents were analyzed for the Apex Consulting engagement...",
  "metadata": {
    "document_count": 6,
    "total_fields_extracted": 70,
    "total_fields_expected": 70,
    "extraction_rate": 100.0,
    "validation_issues": 0,
    "cross_doc_findings": 22
  }
}
```

**What happens internally:** Parses all files in directory → classifies each (N LLM calls) → extracts each (N LLM calls) → validates each (no LLM calls) → cross-document analysis (1 LLM call) → narrative generation (1 LLM call). Total: 2N + 2 LLM calls.

**MCP tool design note:** This is the premium, multi-document tool. For 6 documents, that's 14 API calls. The narrative summary is consultant-ready text that could be presented directly to users. Consider whether the MCP server should also expose the lower-level functions (classify-only, extract-only) as separate tools for more granular access.

### Additional Functions Worth Exposing as MCP Tools

These are available in the source modules and could be individually useful:

#### `classify_document(document: Document, client) -> ClassificationResult`
- Classify a single document without extracting. Useful for sorting/routing.
- Returns: document_type, confidence, reasoning

#### `extract_fields(document: Document, document_type: str, client) -> ExtractionResult`
- Extract fields for a known document type (skip classification). Useful when the caller already knows the type.
- Returns: list of fields with values, confidence, source locations

#### `analyze_documents(extractions: list[ExtractionResult], client) -> AnalysisResult`
- Cross-document analysis on pre-extracted results. Useful if the caller has already extracted documents separately.
- Returns: findings (inconsistencies, gaps, cross-references) with severity and citations

#### `get_available_types() -> list[dict]`
- List all available document types and their descriptions. No API call.
- Useful for clients that want to show what types the system can handle.

### Key Dependencies the MCP Server Needs

- `LLM_PROVIDER`, `LLM_MODEL`, and `LLM_API_KEY` must be set in the environment (via llm-adapter)
- The `schemas/` directory must be accessible (relative to the project root) for schema loading
- No vector store or pre-indexing needed — doc-intelligence processes documents on-the-fly
- No local ML models — all intelligence is via LLM API calls

---

## How the Two Pipelines Differ (Important for MCP Tool Design)

| Aspect | RAG Pipeline | Doc Intelligence |
|--------|-------------|-----------------|
| **Primary question** | "What do these documents say about X?" | "What is in this document, and how does it relate to others?" |
| **Pre-processing** | Requires corpus indexing (one-time) | No pre-processing — analyzes documents on-the-fly |
| **Input** | A natural language question | A file path or directory path |
| **Output** | A grounded answer with citations | Structured fields, validation, cross-doc findings, narrative |
| **Stateful?** | Yes — depends on ChromaDB vector store | No — each call is independent |
| **API calls per use** | 1-3 (single-pass) or 3-8 (agent) | 2 per document + 2 for cross-doc |
| **Guardrails** | Input injection detection, output PII check, token budgets | Validation layer (required fields, confidence, format) |
| **Best for** | Questions, search, synthesis across a corpus | Document review, compliance checks, gap analysis |

They're complementary: you'd use RAG to ask questions about your document corpus, and doc-intelligence to structurally analyze specific documents and compare them against each other.

---

## Suggested MCP Tool Layout

Based on both pipelines, here's a reasonable set of MCP tools the server could expose:

### RAG Tools
1. **`rag_query`** — Single-pass RAG (query → retrieve → generate). The everyday tool.
2. **`rag_agent_query`** — Multi-agent RAG for complex/multi-part questions.
3. **`rag_index`** — (Optional) Trigger corpus re-indexing.

### Document Intelligence Tools
4. **`doc_classify`** — Classify a single document (type + confidence + reasoning).
5. **`doc_extract`** — Classify + extract structured fields from a single document.
6. **`doc_assess`** — Full multi-document assessment with cross-doc analysis + narrative.
7. **`doc_types`** — List available document types and their schemas.

### Meta / Utility
8. **`health`** — Server health check (API key valid, vector store accessible, schemas loadable).

---

## Shared Technical Context

- Both projects use Python 3.12, same venv pattern
- Both use [llm-adapter](https://github.com/Brinkv3/llm-adapter) for provider-agnostic LLM calls (default: Claude Sonnet 4.6)
- Both produce structured dict/JSON output with `.to_dict()` methods on all result types
- Both have the same git identity: Brinkv3 / 223185980+Brinkv3@users.noreply.github.com
- Both are MIT licensed
- The MCP server should use the same Python version and identity

---

## What the MCP Server Project Demonstrates for the Portfolio

- **Protocol interoperability:** Wrapping standalone capabilities as standard MCP tools
- **Composability:** Two independent systems made available through one interface
- **API design:** Clean tool schemas with typed inputs and structured outputs
- **System integration:** Managing dependencies (vector stores, API keys, schemas) across components

This is the "glue" repo — it proves Shawn can make AI systems consumable, not just buildable.
