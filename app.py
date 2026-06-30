"""Document Intelligence — Streamlit Demo.

Thin visual layer over the doc-intelligence pipeline.
Upload documents, see classification, extraction, validation,
and cross-document analysis results.
"""

import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.schema_loader import get_available_types, load_all_schemas
from src.pipeline import process_document, process_directory, PipelineResult
from src.analyzer import analyze_documents, CrossDocFinding
from src.ingest import SUPPORTED_EXTENSIONS

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Document Intelligence",
    page_icon="📄",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    .block-container { padding-top: 3rem; }
    div[data-testid="stMetric"] {
        background: #F7F5F0;
        border-radius: 8px;
        padding: 12px 16px;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #E8E4DC;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Document intelligence")
    st.caption("Carter Brinkley Consulting")
    st.divider()

    with st.expander("How it works"):
        st.markdown(
            "Upload a document and the pipeline will:\n"
            "1. **Parse** the file (PDF, DOCX, MD, TXT, CSV)\n"
            "2. **Classify** the document type using LLM\n"
            "3. **Extract** structured fields per schema\n"
            "4. **Validate** required fields and confidence\n\n"
            "In compare mode, upload 2+ documents to run "
            "cross-document analysis for inconsistencies and gaps."
        )

    st.divider()

    mode = st.radio("Mode", ["Single document", "Compare documents"], label_visibility="visible")

    st.divider()

    available_types = get_available_types()
    st.markdown(f"**{len(available_types)} document types loaded**")
    for t in available_types:
        st.caption(f"• {t['display_name']}")

    st.divider()

    extensions = sorted(ext.lstrip(".").upper() for ext in SUPPORTED_EXTENSIONS)
    st.caption(f"Supported formats: {', '.join(extensions)}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def confidence_color(conf: int) -> str:
    if conf >= 90:
        return "#2E7D32"
    if conf >= 60:
        return "#F9A825"
    return "#C62828"


def severity_icon(severity: str) -> str:
    icons = {"high": "🔴", "medium": "🟡", "low": "⚪"}
    return icons.get(severity, "⚪")


def save_uploaded_files(uploaded_files) -> list[Path]:
    """Write uploaded files to a temp directory and return their paths."""
    tmp_dir = Path(tempfile.mkdtemp())
    paths = []
    for uf in uploaded_files:
        path = tmp_dir / uf.name
        path.write_bytes(uf.getbuffer())
        paths.append(path)
    return paths


def render_classification(result: PipelineResult):
    cls = result.classification
    conf = cls.confidence
    color = confidence_color(conf)

    st.markdown("### Classification")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{cls.document_type.replace('_', ' ').title()}**")
        st.caption(cls.reasoning)
    with col2:
        st.metric("Confidence", f"{conf}%")
    st.progress(conf / 100)


def render_extraction(result: PipelineResult):
    ext = result.extraction
    st.markdown("### Extracted fields")

    rows = []
    for f in ext.fields:
        value_display = f.value
        if isinstance(value_display, list):
            if value_display and isinstance(value_display[0], dict):
                value_display = "; ".join(
                    ", ".join(f"{k}: {v}" for k, v in item.items())
                    for item in value_display
                )
            else:
                value_display = ", ".join(str(v) for v in value_display)
        elif value_display is None:
            value_display = "—"

        rows.append({
            "Field": f.name.replace("_", " ").title(),
            "Value": str(value_display),
            "Confidence": f"{f.confidence}%",
            "Source": f.source_location if f.source_location != "not found in document" else "—",
            "Required": "Yes" if f.required else "",
        })

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Confidence": st.column_config.TextColumn(width="small"),
            "Required": st.column_config.TextColumn(width="small"),
            "Source": st.column_config.TextColumn(width="medium"),
        },
    )


def render_validation(result: PipelineResult):
    val = result.validation
    summary = val.field_summary

    st.markdown("### Validation")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Fields found", f"{summary['fields_found']}/{summary['total_fields']}")
    with col2:
        st.metric("Required", f"{summary['required_found']}/{summary['required_total']}")
    with col3:
        st.metric("Extraction rate", f"{summary['extraction_rate']}%")

    if val.issues:
        for issue in val.issues:
            icon = "❌" if issue.severity == "error" else "⚠️"
            st.markdown(f"{icon} **{issue.field_name.replace('_', ' ').title()}** — {issue.message}")
    else:
        st.success("All fields validated — no issues found.")


def render_cross_doc(findings: list[CrossDocFinding], doc_ids: list[str], summary: str):
    st.markdown("### Cross-document analysis")
    st.caption(f"Comparing: {', '.join(doc_ids)}")

    if summary:
        st.info(summary)

    if not findings:
        st.success("No inconsistencies or gaps found.")
        return

    high = [f for f in findings if f.severity == "high"]
    medium = [f for f in findings if f.severity == "medium"]
    low = [f for f in findings if f.severity == "low"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("High severity", len(high))
    with col2:
        st.metric("Medium", len(medium))
    with col3:
        st.metric("Low / consistent", len(low))

    for finding in findings:
        icon = severity_icon(finding.severity)
        with st.expander(f"{icon} {finding.title} ({finding.finding_type})"):
            st.markdown(finding.description)
            if finding.field_references:
                st.markdown("**References:**")
                for ref in finding.field_references:
                    doc = ref.get("document", "")
                    field = ref.get("field", "")
                    value = ref.get("value", "")
                    st.caption(f"• {doc} → {field}: {value}")


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

if mode == "Single document":
    uploaded = st.file_uploader(
        "Upload a document",
        type=[ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS],
        key="single_upload",
    )

    if uploaded is not None:
        paths = save_uploaded_files([uploaded])
        path = paths[0]

        with st.spinner(f"Processing {uploaded.name}..."):
            try:
                result = process_document(path)
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.stop()

        st.divider()
        render_classification(result)
        st.divider()
        render_extraction(result)
        st.divider()
        render_validation(result)

else:
    uploaded_files = st.file_uploader(
        "Upload 2 or more documents to compare",
        type=[ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS],
        accept_multiple_files=True,
        key="compare_upload",
    )

    if uploaded_files and len(uploaded_files) >= 2:
        paths = save_uploaded_files(uploaded_files)

        with st.spinner(f"Processing {len(uploaded_files)} documents..."):
            try:
                results = [process_document(p) for p in paths]
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.stop()

        # Show individual results in tabs
        tabs = st.tabs([r.document_id for r in results])
        for tab, result in zip(tabs, results):
            with tab:
                render_classification(result)
                st.divider()
                render_extraction(result)
                st.divider()
                render_validation(result)

        st.divider()

        # Cross-document analysis
        with st.spinner("Running cross-document analysis..."):
            try:
                extractions = [r.extraction for r in results]
                analysis = analyze_documents(extractions)
                render_cross_doc(
                    analysis.findings,
                    analysis.document_ids,
                    analysis.summary,
                )
            except Exception as e:
                st.error(f"Cross-document analysis error: {e}")

    elif uploaded_files and len(uploaded_files) < 2:
        st.warning("Upload at least 2 documents to compare.")
